"""D-2 (K1 stage A, 2026-09-27): the streaming door `bot.bt.data.stream` -- one dataset read one file at a
time, through the same allow-list, seal records, parsing and checks as `load`.

What is checked (from the module's rule text): the chunks carry exactly the events, file records and
anomalies `load` gives for files in time order; nothing of an earlier file is kept; a file whose rows do not
all come after the previous file's rows is refused (StreamOrderError); an anomaly kind the caller did not
name a policy for is refused; the declared 24x7 grid is checked across files (a gap between two files is
reported as load reports it); every path is refused before a row is read when one is not allowed; a sealed
file is refused as `load` refuses it."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from bot.bt.data import (AllowList, PathRefused, SealedRangeError, StreamOrderError, UnresolvedAnomalyError, load,
                         stream)
from bot.bt.vector import bars_from_bars

NS = 10**9
T0 = 1_483_228_800  # 2017-01-01T00:00:00Z


GAP = {"gap": "accept"}  # the files' holes, reported since G-4 (the spec names its session)


def spec(session="24x7"):  # G-4 (2026-10-01): a crypto bar spec names its session
    s = {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "XBTUSD", "asset": "crypto",
         "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
         "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
         "bar": {"interval_s": 1, "label": "start"}, "key": "start"}
    if session:
        s["bar"]["session"] = session
    return s


def iso(sec):
    return dt.datetime.fromtimestamp(sec, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def write(root, name, secs, px0=100.0):
    d = root / "backtest_data" / "s1"
    d.mkdir(parents=True, exist_ok=True)
    lines = ["ts,o,h,l,c,vol"]
    for k, s in enumerate(secs):
        p = px0 + k * 0.5
        lines.append(f"{iso(T0 + s)},{p},{p + 1},{p - 1},{p + 0.25},{k + 1}")
    (d / name).write_text("\n".join(lines) + "\n")
    return f"backtest_data/s1/{name}"


def ev_tuple(e):
    return (e.start_time_ns, e.received_time_ns, e.open, e.high, e.low, e.close, e.volume)


def test_chunks_equal_load(tmp_path):
    paths = [write(tmp_path, "a.csv", [0, 1, 2, 5]), write(tmp_path, "b.csv", [7, 8, 60, 61], 200.0),
             write(tmp_path, "c.csv", [3600, 3601])]
    ds = {"name": "d", "paths": paths, "spec": spec()}
    ref = load(str(tmp_path), [ds])
    s = stream(str(tmp_path), ds, resolve=GAP)
    chunks = list(s)
    assert [c.index for c in chunks] == [0, 1, 2]
    assert [ev_tuple(e) for c in chunks for e in c.events] == [ev_tuple(e) for e in ref.events("d", GAP)]
    assert [c.file for c in chunks] == ref.files() == s.files()
    # G-4: the spec names its session (24x7), so the holes are reported -- the same ones by both doors
    got = sorted((a["kind"], a["t_ns"]) for c in chunks for a in c.anomalies)
    assert got == sorted((a["kind"], a["t_ns"]) for a in ref.anomalies("d")) and {k for k, _ in got} == {"gap"}
    assert s._d.rows == []  # the dataset holds no row: each chunk's rows are dropped once handed out
    m = s.manifest()
    assert m["dataset"]["files_read"] == 3 and m["seal_records"] == ref.manifest()["seal_records"]


def test_fold_per_chunk_equals_fold_of_load(tmp_path):
    paths = [write(tmp_path, f"{k}.csv", [k * 3600 + s for s in (0, 1, 59, 60, 3599)], 100.0 + k) for k in range(3)]
    ds = {"name": "d", "paths": paths, "spec": spec()}
    ev = load(str(tmp_path), [ds]).events("d", GAP)
    whole = bars_from_bars([e.start_time_ns for e in ev], [e.open for e in ev], [e.high for e in ev],
                           [e.low for e in ev], [e.close for e in ev], [e.volume for e in ev], 60)
    parts = []
    for c in stream(str(tmp_path), ds, resolve=GAP):
        e = c.events
        parts += bars_from_bars([x.start_time_ns for x in e], [x.open for x in e], [x.high for x in e],
                                [x.low for x in e], [x.close for x in e], [x.volume for x in e], 60)
    assert parts == whole


def test_overlapping_files_are_refused(tmp_path):
    paths = [write(tmp_path, "a.csv", [0, 1, 10]), write(tmp_path, "b.csv", [10, 11])]  # b starts AT a's last row
    it = iter(stream(str(tmp_path), {"name": "d", "paths": paths, "spec": spec()}, resolve=GAP))
    next(it)
    with pytest.raises(StreamOrderError):
        next(it)


def test_unresolved_anomaly_is_refused_and_a_named_policy_applies(tmp_path):
    d = tmp_path / "backtest_data" / "s1"
    d.mkdir(parents=True)
    (d / "dup.csv").write_text(f"ts,o,h,l,c,vol\n{iso(T0)},1,2,0.5,1.5,1\n{iso(T0)},1,2,0.5,1.5,1\n{iso(T0 + 1)},1,2,0.5,1.5,1\n")
    ds = {"name": "d", "paths": ["backtest_data/s1/dup.csv"], "spec": spec()}
    with pytest.raises(UnresolvedAnomalyError):
        list(stream(str(tmp_path), ds))
    (c,) = list(stream(str(tmp_path), ds, resolve={"duplicate": "drop"}))
    assert [a["kind"] for a in c.anomalies] == ["duplicate"] and len(c.events) == 2
    assert c.resolution == {"duplicate": "drop"}
    assert [ev_tuple(e) for e in c.events] == [ev_tuple(e) for e in
                                               load(str(tmp_path), [ds]).events("d", {"duplicate": "drop"})]


def test_24x7_grid_is_checked_across_files(tmp_path):
    paths = [write(tmp_path, "a.csv", [0, 1, 2]), write(tmp_path, "b.csv", [5, 6])]  # seconds 3 and 4 are missing
    ds = {"name": "d", "paths": paths, "spec": spec("24x7")}
    ref = load(str(tmp_path), [ds]).anomalies("d")
    got = [a for c in stream(str(tmp_path), ds, resolve={"gap": "accept"}) for a in c.anomalies]
    assert sorted((a["kind"], a["t_ns"]) for a in got) == sorted((a["kind"], a["t_ns"]) for a in ref) == [
        ("gap", (T0 + 3) * NS), ("gap", (T0 + 4) * NS)]


def test_every_path_is_checked_before_a_row_is_read(tmp_path):
    ok = write(tmp_path, "a.csv", [0, 1])
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "x.csv").write_text("ts,o,h,l,c,vol\n")
    with pytest.raises(PathRefused):
        stream(str(tmp_path), {"name": "d", "paths": [ok, "elsewhere/x.csv"], "spec": spec()})
    only = AllowList(roots=("backtest_data/s2",))
    with pytest.raises(PathRefused):
        stream(str(tmp_path), {"name": "d", "paths": [ok], "spec": spec()}, allowlist=only)


def test_a_sealed_file_is_refused_as_load_refuses_it(tmp_path):
    p = write(tmp_path, "a.csv", [0, 1, 2])
    rec = {"unit": "U", "forward_start": iso(T0 + 86400) + "+00:00",
           "files": [{"path": p, "time_column": "ts", "seal_from_ts": iso(T0 + 1) + "+00:00"}]}
    (tmp_path / "backtest_data" / "phase2_sealed" / "U").mkdir(parents=True)
    (tmp_path / "backtest_data" / "phase2_sealed" / "U" / "SEALED.json").write_text(json.dumps(rec))
    ds = {"name": "d", "paths": [p], "spec": spec()}
    with pytest.raises(SealedRangeError):
        load(str(tmp_path), [ds])
    with pytest.raises(SealedRangeError):
        list(stream(str(tmp_path), ds))
    ok = dict(ds, range_ns=[T0 * NS, (T0 + 1) * NS])  # before the cutoff: the one unsealed row
    (c,) = list(stream(str(tmp_path), ok))
    assert len(c.events) == 1 and c.file.sealed_unit == "U"


def test_a_stream_is_iterated_once(tmp_path):
    s = stream(str(tmp_path), {"name": "d", "paths": [write(tmp_path, "a.csv", [0])], "spec": spec()})
    list(s)
    with pytest.raises(Exception, match="once"):
        list(s)
