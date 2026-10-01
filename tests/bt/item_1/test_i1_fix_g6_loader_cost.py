"""G-6 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-5): the data layer's `load`
cost about 91 µs a row on Binance 2018 (521,624 rows). cProfile (FIXES.md G-6) named three costs made once PER ROW
that depend only on the file or on nothing: (1) `seal_time_ns` built a new TimeReader for every row of a sealed file
(allowlist.py), (2) `_Cells.rest` called `spec.columns_used()` for every row (loader.py), (3) every row's identity --
the JSON text of its record -- was written although only rows sharing a key are ever compared (loader.py). Rule after
the fix: these are made once per file (1, 2) or when read (3), and (4) a sealed file's seal-time cell that is the
dataset's own ISO/UTC time column is read once, not twice; the checks' results are unchanged. Synthetic files only.
"""
from __future__ import annotations

import hashlib
import json

import pytest

import bot.bt.core.time as CT
import bot.bt.data.loader as L
import bot.bt.data.spec as SP
import bot.bt.data.timestamps as TS
from bot.bt.data import load

NS = 1_000_000_000
T2020 = 1577836800 * NS
SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
        "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
N = 300


def body(n=N, extra=""):
    rows = ["ts,o,h,l,c,vol,note"]
    for i in range(n):
        m = 1577836800 - (n - i) * 60
        import datetime as dt
        ts = dt.datetime.fromtimestamp(m, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        rows.append(f"{ts},1,2,0.5,1.5,1,x")
    return "\n".join(rows) + "\n" + extra


@pytest.fixture
def sealed_root(tmp_path):
    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    text = body()
    (tmp_path / "backtest_data" / "x" / "s.csv").write_text(text)
    rec = {"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": "backtest_data/x/s.csv", "time_column": "ts", "seal_from_ts": "2020-01-01T00:00:00+00:00",
                      "md5": hashlib.md5(text.encode()).hexdigest()}]}
    (tmp_path / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    return str(tmp_path)


def test_per_file_work_is_not_done_per_row(sealed_root, monkeypatch):
    counts = {"reader": 0, "columns_used": 0, "dumps": 0, "iso": 0}
    init, cu, dumps, iso = TS.TimeReader.__init__, SP.Spec.columns_used, L.json.dumps, CT._iso_to_nanos

    def count_iso(*a, **k):
        counts["iso"] += 1
        return iso(*a, **k)

    def count_init(self, *a, **k):
        counts["reader"] += 1
        return init(self, *a, **k)

    def count_cu(self):
        counts["columns_used"] += 1
        return cu(self)

    class J:  # loader's json, with dumps counted
        def __getattr__(self, name):
            return getattr(json, name)

        @staticmethod
        def dumps(*a, **k):
            counts["dumps"] += 1
            return dumps(*a, **k)

    monkeypatch.setattr(TS.TimeReader, "__init__", count_init)
    monkeypatch.setattr(SP.Spec, "columns_used", count_cu)
    monkeypatch.setattr(L, "json", J())
    monkeypatch.setattr(CT, "_iso_to_nanos", count_iso)
    r = load(sealed_root, [{"name": "d", "paths": ["backtest_data/x/s.csv"], "spec": SPEC,
                            "range_ns": [T2020 - N * 60 * NS, T2020]}])
    assert r.files()[0].rows_kept == N and r.files()[0].sealed_unit == "U"
    # a constant number, whatever the number of rows (before the fix: N + 2 readers, N + 1 columns_used, N dumps)
    assert counts["reader"] <= 3 and counts["columns_used"] <= 2 and counts["dumps"] <= 2, counts
    # the seal's time column is the dataset's ISO/UTC time column: each cell is read once (before the fix: twice)
    assert counts["iso"] <= N + 2, counts


def test_rows_have_no_dict_and_the_duplicate_check_reads_the_identity_when_needed(tmp_path):
    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    extra = "2019-12-31T23:59:00,1,2,0.5,1.5,1,x\n2019-12-31T23:58:00,1,2,0.5,1.25,1,x\n2019-12-31T23:57:00,1,2,0.5,1.5,1,y\n"
    (tmp_path / "backtest_data" / "x" / "d.csv").write_text(body(5, extra))
    r = load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/x/d.csv"], "spec": SPEC}])
    kinds = sorted((a["kind"], a["line"]) for a in r.anomalies("d") if a["kind"] in ("duplicate", "conflict"))
    assert kinds == [("conflict", 8), ("conflict", 9), ("duplicate", 7)]  # same row / other close / other note
    row = L.Row({"a": 1}, None, 0, 1, 0, None, (("note", "x"),))
    assert not hasattr(row, "__dict__") and row.identity == ('{"a": 1}', (("note", "x"),))


@pytest.mark.parametrize("label,cells", [("start", ["2019-12-31T23:58:00+09:00", "2019-12-31T23:59:00Z"]),
                                         ("end", ["2019-12-31 23:59:00", "2020-01-01T00:00:00"])])
def test_a_seal_time_handed_over_is_the_time_the_seal_reads(tmp_path, label, cells):
    """The cell read once (as the dataset's time) gives the seal time seal_time_ns gives by reading it itself."""
    from bot.bt.data.allowlist import seal_time_ns
    from bot.bt.data.timestamps import TimeReader
    r = TimeReader("iso", "UTC")
    for c in cells:
        assert seal_time_ns(c) == seal_time_ns(c, r.read(c))
    text = "ts,o,h,l,c,vol,note\n" + "".join(f"{c},1,2,0.5,1.5,1,x\n" for c in cells)
    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    (tmp_path / "backtest_data" / "x" / "s.csv").write_text(text)
    rec = {"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": "backtest_data/x/s.csv", "time_column": "ts", "seal_from_ts": "2020-01-01T00:00:00+00:00",
                      "md5": hashlib.md5(text.encode()).hexdigest()}]}
    (tmp_path / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    sp = {**SPEC, "bar": {**SPEC["bar"], "label": label}}
    if label == "start":  # the first row is 2019-12-31T14:58Z: kept
        got = load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/x/s.csv"], "spec": sp,
                                    "range_ns": [T2020 - 10 * 3600 * NS, T2020]}])
        assert got.files()[0].rows_kept == 2
    else:  # label end: the second row's bar ends at 2020-01-01T00:00 (its seal time): kept by the range [.., T2020)
        from bot.bt.data import SealedRangeError
        with pytest.raises(SealedRangeError, match="seal time"):
            load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/x/s.csv"], "spec": sp,
                                  "range_ns": [T2020 - 10 * 3600 * NS, T2020]}])


def test_a_seal_column_other_than_the_time_column_is_read_with_one_reader(tmp_path, monkeypatch):
    """The seal's time column is not the dataset's time column (here: epoch seconds as the time, ISO text sealed):
    each seal cell is read by seal_time_ns itself, with the one reader made once (before the fix: one per row)."""
    import datetime as dt
    rows = ["ts,iso,o,h,l,c,vol"]
    for i in range(N):
        sec = 1577836800 - (N - i) * 60
        rows.append(f"{sec},{dt.datetime.fromtimestamp(sec, tz=dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')},1,2,0.5,1.5,1")
    text = "\n".join(rows) + "\n"
    (tmp_path / "backtest_data" / "x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    (tmp_path / "backtest_data" / "x" / "s.csv").write_text(text)
    rec = {"unit": "U", "forward_start": "2020-01-01T00:00:00+00:00",
           "files": [{"path": "backtest_data/x/s.csv", "time_column": "iso", "seal_from_ts": "2020-01-01T00:00:00+00:00",
                      "md5": hashlib.md5(text.encode()).hexdigest()}]}
    (tmp_path / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    made = [0]
    init = TS.TimeReader.__init__

    def count_init(self, *a, **k):
        made[0] += 1
        return init(self, *a, **k)

    monkeypatch.setattr(TS.TimeReader, "__init__", count_init)
    sp = {**SPEC, "time": {"columns": ["ts"], "unit": "s", "tz": "UTC"}}
    r = load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/x/s.csv"], "spec": sp,
                              "range_ns": [T2020 - N * 60 * NS, T2020]}])
    assert r.files()[0].rows_kept == N and r.files()[0].sealed_unit == "U"
    assert made[0] <= 3, made
