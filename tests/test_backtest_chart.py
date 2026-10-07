"""The バックテスト tab's seal, price stores and chart API for road runs (src/bot/monitoring/backtest_chart.py, road_view.py).
The seal tests are written so that each layer of the cut fails on its own when removed (see the mutation list in the comments).
A run here is a small road run written by tests/road_fixture.py from a list of trades, so every number is counted by hand."""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from bot.monitoring import backtest_chart as C
from bot.monitoring import road_view as RV
from road_fixture import trade as _t, write_road_run

REPO = Path(__file__).resolve().parents[1]
BOUNDARY = int(datetime(2023, 12, 18, tzinfo=timezone.utc).timestamp())
NS = 10**9
XBT = "backtest_data/k1_newenv_a_20260927/xbtusd_1m_2017_2019.csv.gz"
RID = "2" * 64
FXDIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("BT_CHART_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("BT_LOG_PATH", str(tmp_path / "dashboard_bt.log"))
    monkeypatch.setattr(C, "BUILD_IN_CHILD", False)  # most tests patch the readers in this process; the child-process tests set it True
    for d in (C._STORES, RV._REC, C._RULES, C._PROGRESS, C._JOBS, RV._CACHE):
        d.clear()


def _ts(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())

def _seal(root: Path, p208_from="2023-12-18T00:00:00+00:00", units=("P2-08", "P2-08b")):
    """The seal records as the data layer reads them (the two units that bound crypto / fx runs)."""
    for unit, fwd, files in (("P2-08", "2026-09-06T00:00:00+00:00",
                              [{"path": "backtest_data/bf/candles_1m_2023.csv.gz", "time_column": "ts", "seal_from_ts": p208_from}]),
                             ("P2-08b", "2026-09-08T00:00:00+00:00",
                              [{"path": "backtest_data/exec.csv.gz", "time_column": "exec_date", "seal_from_ts": "2026-08-23T00:00:00+00:00"}])):
        if unit in units:
            d = root / "backtest_data" / "phase2_sealed" / unit
            d.mkdir(parents=True, exist_ok=True)
            (d / "SEALED.json").write_text(json.dumps({"unit": unit, "forward_start": fwd, "files": files}), encoding="utf-8")


def _csv(path: Path, rows, header="start_ts,o,h,l,c,vol", iso="%Y-%m-%dT%H:%M:%S"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as fh:
        fh.write(header + "\n")
        for t, o, h, l, c in rows:
            fh.write(f"{datetime.fromtimestamp(t, tz=timezone.utc).strftime(iso)},{o},{h},{l},{c},1\n")


def _minute_rows(t0: int, n: int, step: int = 60):
    return [(t0 + i * step, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(n)]


def _spec(path: str, symbol="XBTUSD", interval=60, kind="bar"):
    return {"path": path, "spec": {"kind": kind, "symbol": symbol, "bar": {"interval_s": interval, "label": "start"},
                                   "time": {"columns": ["start_ts"], "tz": "UTC", "unit": "iso"},
                                   "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"}}}



def _run(root: Path, rid: str, group="g", cfg=None, data=None, first=None, last=None, trades=None, **kw):
    """A road run (seconds in `first` / `last` are given in ns, as the old helper did)."""
    inst = (cfg or {}).get("instrument", "XBTUSD")
    return write_road_run(root, rid, trades=trades or [], group=group, instrument=inst, first=(first or 0) // NS, last=(last or 0) // NS,
                          data=data if data is not None else [], **kw)


def _trade(i, et, xt, ep, xp, side="buy"):
    return _t(et, xt, ep, xp, side)


def _world(tmp_path, n_min=3000, start="2023-01-01T00:00:00", trades=None, data_kind="bar", rid="2" * 64, first=None, last=None):
    """A root with the seal ledger, an XBTUSD 1-minute store file and one road run on it (its own file is a 15 m one)."""
    _seal(tmp_path)
    t0 = _ts(start)
    _csv(tmp_path / XBT, _minute_rows(t0, n_min))
    trades = trades if trades is not None else [_trade(1, t0 + 600, t0 + 1200, 110, 120), _trade(2, t0 + 3000, t0 + 3600, 130, 120, "sell"),
                                                _trade(3, t0 + 90000, t0 + 90600, 200, 190)]
    root = _run(tmp_path, rid, data=[_spec("backtest_data/k1_newenv_a_20260927/xbtusd_15m_2017_2019.csv.gz", interval=900, kind=data_kind)],
                first=(first if first is not None else t0 + 900) * NS, last=(last if last is not None else t0 + n_min * 60) * NS, trades=trades)
    return t0, root


# ---- the seal boundary: where it comes from -----------------------------------------------------------------
def test_boundary_is_computed_from_the_seal_ledger_not_written_in_the_code(tmp_path):
    _seal(tmp_path)
    assert C.seal_rule(tmp_path)["boundary_ns"] == BOUNDARY * NS
    _seal(tmp_path, p208_from="2023-06-01T00:00:00+00:00")
    C._RULES.clear()
    assert C.seal_rule(tmp_path)["boundary_ns"] == _ts("2023-06-01T00:00:00") * NS
    share = importlib.util.spec_from_file_location("share_backtest_runs_t", REPO / "scripts" / "share_backtest_runs.py")
    mod = importlib.util.module_from_spec(share)
    share.loader.exec_module(mod)
    assert mod.seal_rule(str(tmp_path))["boundary_ns"] == C.seal_rule(tmp_path)["boundary_ns"]
    src = (REPO / "src/bot/monitoring/backtest_chart.py").read_text()
    assert "liq_cascade_v2" not in src.split('"""', 2)[2] and "2023, 12, 18" not in src


def test_unreadable_or_unknown_ledger_fails_closed_and_no_file_is_read(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    opened = []
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: opened.append(a) or (_ for _ in ()).throw(AssertionError(a)))
    (tmp_path / "backtest_data/phase2_sealed/P2-08b/SEALED.json").write_text("{")
    s = C.run_summary(root, "2" * 64, tmp_path)
    assert "blocked" in s and "headline" not in s
    with pytest.raises(C.SealBlocked):
        C.run_chart(root, "2" * 64, root=tmp_path)
    with pytest.raises(C.SealBlocked):
        C.run_table(root, "2" * 64, "trades", root=tmp_path)
    with pytest.raises(C.SealBlocked):
        C.run_trace(root, "2" * 64, "trades", 0, root=tmp_path)
    _seal(tmp_path)
    d = tmp_path / "backtest_data/phase2_sealed/P9-99"
    d.mkdir()
    (d / "SEALED.json").write_text(json.dumps({"unit": "P9-99", "forward_start": "2026-09-06T00:00:00+00:00",
                                  "files": [{"path": "backtest_data/z.csv.gz", "time_column": "ts", "seal_from_ts": "2023-01-01T00:00:00+00:00"}]}))
    C._RULES.clear()
    assert "blocked" in C.run_summary(root, "2" * 64, tmp_path) and opened == []
    shutil_ledger = tmp_path / "backtest_data/phase2_sealed"
    for p in list(shutil_ledger.iterdir()):
        for q in p.iterdir():
            q.unlink()
        p.rmdir()
    C._RULES.clear()
    assert "blocked" in C.run_summary(root, "2" * 64, tmp_path)


# ---- the seal boundary: each layer cuts on its own -----------------------------------------------------------
def _edge_world(tmp_path, **kw):
    start = BOUNDARY - 600  # 23:50 on 12-17; rows go on to 00:19 on 12-18
    _seal(tmp_path)
    _csv(tmp_path / XBT, _minute_rows(start, 30))
    root = _run(tmp_path, "3" * 64, data=[_spec("backtest_data/k1_newenv_a_20260927/xbtusd_15m_2017_2019.csv.gz", interval=900, kind=kw.get("kind", "bar"))],
                first=(start + 60) * NS, last=(BOUNDARY + kw.get("past", 3600)) * NS,
                trades=[_trade(1, start + 120, start + 240, 100, 101), _trade(2, BOUNDARY - 60, BOUNDARY, 100, 101),
                        _trade(3, BOUNDARY + 60, BOUNDARY + 120, 100, 101)])
    return start, root


def test_M1_rows_at_or_after_the_boundary_are_dropped_when_a_file_is_parsed(tmp_path):
    start, root = _edge_world(tmp_path)
    rule = C.seal_rule(tmp_path)
    t, *_ = C._read_file(tmp_path / XBT, XBT, rule, C.MARKETS["XBTUSD"]["cols"])
    assert t.size == 10 and t.max() < BOUNDARY  # the file holds 30 rows; 20 start at or after the boundary
    C.run_chart(root, "3" * 64, root=tmp_path)
    for f in (Path(os.environ["BT_CHART_CACHE_DIR"])).glob("*/i*_t.npy"):
        assert np.load(f).max() < BOUNDARY, f  # nothing after the boundary is in the cache either


def test_cached_frames_are_cut_again_when_loaded(tmp_path):
    start, root = _edge_world(tmp_path)
    C.run_chart(root, "3" * 64, root=tmp_path)
    cdir = next(Path(os.environ["BT_CHART_CACHE_DIR"]).iterdir())
    for w in C.FRAMES:  # a cache file written with rows after the boundary (an old build, or tampering)
        for c in "tohlc":
            a = np.load(cdir / f"i{w}_{c}.npy")
            np.save(cdir / f"i{w}_{c}.npy", np.concatenate([a, a[-1:] + (BOUNDARY if c == "t" else 0)]))
    C._STORES.clear()
    d = C.run_chart(root, "3" * 64, root=tmp_path, interval_s=60, from_s=start, to_s=BOUNDARY + 5000)
    assert d["bars"] and max(b[0] for b in d["bars"]) < BOUNDARY
    rec = C._record(str(Path(root) / "g" / ("3" * 64)))
    assert max(C.get_store(C.price_plan(rec, tmp_path, C.seal_rule(tmp_path)), C.seal_rule(tmp_path)).frames[60][0]) < BOUNDARY


def test_M4_the_chart_cuts_at_the_boundary_even_if_the_store_holds_later_rows(tmp_path, monkeypatch):
    start, root = _edge_world(tmp_path)
    rule = C.seal_rule(tmp_path)
    plan = C.price_plan(C._record(str(Path(root) / "g" / ("3" * 64))), tmp_path, rule)
    real = C.get_store(plan, rule)
    t = np.arange(start, BOUNDARY + 1200, 60, dtype=np.int64)
    v = np.arange(t.size, dtype=np.float64)
    leaky = C.Store("XBTUSD", {w: (t, v, v, v, v) for w in C.FRAMES}, int(t[0]), int(t[-1]) + 60, int(t.size), 0, 0, False)
    monkeypatch.setattr(C, "get_store", lambda plan, rule: leaky)
    for kw in ({}, {"interval_s": 60}, {"from_s": start, "to_s": BOUNDARY + 99999}):
        d = C.run_chart(root, "3" * 64, root=tmp_path, **kw)
        assert d["bars"] and max(b[0] for b in d["bars"]) < BOUNDARY and d["to_s"] <= BOUNDARY
    assert real.rows == 10


def test_boundary_row_is_shown_for_a_bars_only_run_and_not_for_other_runs(tmp_path):
    start, root = _edge_world(tmp_path, kind="bar")
    d = C.run_chart(root, "3" * 64, root=tmp_path, from_s=start, to_s=BOUNDARY + 100, range_name="pessimistic")
    L = d["layers"]["pessimistic"]
    assert [t["id"] for t in L["trades"]] == ["0", "1"]  # the trade whose last fill is AT the boundary is a bar's: shown; the one after it is not
    assert all(f["t"] <= BOUNDARY for f in L["fills"]) and len(L["fills"]) == 4
    assert all(p[0] <= BOUNDARY for p in L["cum"])
    tab = C.run_table(root, "3" * 64, "fills", tmp_path, range_name="pessimistic")
    assert tab["matched"] == 4
    tmp2 = tmp_path / "other"
    tmp2.mkdir()
    start, root2 = _edge_world(tmp2, kind="trade")  # a data entry that is not a bar: a row AT the boundary is sealed
    L2 = C.run_chart(root2, "3" * 64, root=tmp2, from_s=start, to_s=BOUNDARY + 100, range_name="pessimistic")["layers"]["pessimistic"]
    assert [t["id"] for t in L2["trades"]] == ["0"] and len(L2["fills"]) == 3  # trade 1 ends AT the boundary: its row is cut; its first fill (before it) stays
    assert C.run_table(root2, "3" * 64, "fills", tmp2, range_name="pessimistic")["matched"] == 3


def test_M2_the_layers_cut_rows_even_if_the_caller_asks_for_a_later_range(tmp_path):
    start, root = _edge_world(tmp_path, kind="trade")
    data = RV.load(str(Path(root) / "g" / ("3" * 64)))
    g = data.group("XBTUSD", "pessimistic")
    wide = RV.layers(g, 0, 2**61, 2**62, 60)  # no cut asked for: everything
    assert len(wide["fills"]) == 6 and len(wide["trades"]) == 3
    cut = RV.layers(g, 0, 2**61, BOUNDARY * NS, 60)
    assert len(cut["fills"]) == 3 and [t["id"] for t in cut["trades"]] == ["0"] and all(p[0] < BOUNDARY for p in cut["cum"])
    assert RV.table_page(data, "fills", "XBTUSD", "pessimistic", BOUNDARY * NS)["matched"] == 3
    assert RV.table_page(data, "trades", "XBTUSD", "pessimistic", BOUNDARY * NS)["matched"] == 1  # a trade is cut by its last time too
    assert RV.headline(data, g, BOUNDARY * NS)["trades"]["closed"] == 1
    tr = RV.trace(data, "trades", 0, BOUNDARY * NS)
    assert all(NS * BOUNDARY > int(r[data.cols["fills"].index("t_ns")]) for l in tr["links"] if l["table"] == "fills" for r in l["rows"])


def test_numbers_of_the_headline_follow_the_same_cut(tmp_path):
    start, root = _edge_world(tmp_path, kind="trade")
    s = C.run_summary(root, "3" * 64, tmp_path)
    h = s["headline"]["pessimistic"]
    assert h["trades"]["closed"] == 1 and h["trades"]["pnl_sum"] == pytest.approx(0.1) and s["summary_cut"] is True
    assert s["summary_rows"] == [] and "境をまたぐ" in s["summary_cut_reason"]  # summary.json is the whole run's: not served
    assert s["road"]["counts_cut"] is True and s["road"]["tables"]["fills"] < 12  # the row counts are those of the rows shown
    with pytest.raises(C.ChartError, match="境をまたぐ"):
        C.run_table(root, "3" * 64, "summary", tmp_path)


def test_a_run_wholly_after_the_boundary_shows_no_number(tmp_path):
    _seal(tmp_path)
    t0 = BOUNDARY + 86400
    _csv(tmp_path / XBT, _minute_rows(BOUNDARY - 120, 5))
    root = _run(tmp_path, "7" * 64, data=[_spec("backtest_data/x.csv.gz")], first=t0 * NS, last=(t0 + 600) * NS,
                trades=[_trade(1, t0 + 60, t0 + 120, 1, 2)])
    s = C.run_summary(root, "7" * 64, tmp_path)
    assert s["after_seal"] and "封印の境" in s["blocked"] and "より後" in s["blocked"] and "headline" not in s
    for call in (lambda: C.run_chart(root, "7" * 64, root=tmp_path), lambda: C.run_table(root, "7" * 64, "trades", tmp_path),
                 lambda: C.run_trace(root, "7" * 64, "trades", 0, tmp_path)):
        with pytest.raises(C.AfterSeal):
            call()


def test_year_file_after_the_boundary_year_is_never_opened_and_sealed_dir_is_refused(tmp_path, monkeypatch):
    _seal(tmp_path)
    for y in (2023, 2024):
        _csv(tmp_path / FXDIR / f"candles_1m_{y}.csv.gz", _minute_rows(_ts(f"{y}-12-17T23:50:00"), 30), header="ts,open,high,low,close,volume",
             iso="%Y-%m-%dT%H:%M:%S+00:00")
    root = _run(tmp_path, "4" * 64, cfg={"instrument": "FX_BTC_JPY"}, data=[_spec("backtest_data/k1_newenv_g_20261001/x.csv.gz", "FX_BTC_JPY", 900)],
                first=_ts("2023-12-17T23:50:00") * NS, last=(BOUNDARY + 1200) * NS, trades=[_trade(1, BOUNDARY - 300, BOUNDARY - 200, 1, 2)],
                instrument=None) if False else _run(tmp_path, "4" * 64, cfg={"instrument": "FX_BTC_JPY"}, data=[_spec("backtest_data/k1_newenv_g_20261001/x.csv.gz", "FX_BTC_JPY", 900)],
                first=_ts("2023-12-17T23:50:00") * NS, last=(BOUNDARY + 1200) * NS, trades=[_trade(1, BOUNDARY - 300, BOUNDARY - 200, 1, 2)])
    seen = []
    orig = C._read_file
    monkeypatch.setattr(C, "_read_file", lambda path, *a, **k: seen.append(str(path)) or orig(path, *a, **k))
    d = C.run_chart(root, "4" * 64, root=tmp_path)
    assert d["price"]["available"] and C.FALLBACK_NOTE in d["price"]["note"] and d["bars"]
    assert all("2024" not in p and "phase2_sealed" not in p for p in seen) and any("2023" in p for p in seen)
    for bad in ("backtest_data/PHASE2_SEALED/P2-08/x.csv.gz", "backtest_data/QA_known/x.csv.gz", "backtest_data/o3c_x/x.csv.gz",
                "backtest_data/phase2_runs/x.csv.gz"):
        (tmp_path / bad).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / bad).write_bytes(b"x")
        assert "データ層が拒む" in C._safe(tmp_path / bad, tmp_path), bad
    (tmp_path / "outside.csv").write_bytes(b"x")
    assert C._safe(tmp_path / "outside.csv", tmp_path)


# ---- the price stores (L-D06) ---------------------------------------------------------------------------------
def test_two_runs_share_one_store_and_the_second_does_not_parse(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    _run(tmp_path, "8" * 64, data=[_spec(XBT)], first=(t0 + 60) * NS, last=(t0 + 3000) * NS, trades=[_trade(1, t0 + 120, t0 + 180, 1, 2)])
    calls = []
    orig = C._read_file
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: calls.append(1) or orig(*a, **k))
    a = C.run_chart(root, "2" * 64, root=tmp_path)
    b = C.run_chart(root, "8" * 64, root=tmp_path)
    assert len(calls) == 1 and a["price"]["available"] and b["price"]["available"]
    C._STORES.clear()  # a new process: the disk cache answers, nothing is parsed
    C.run_chart(root, "2" * 64, root=tmp_path)
    assert len(calls) == 1
    assert b["price"]["same_source"] is True and a["price"]["same_source"] is False
    assert C.FALLBACK_NOTE in a["price"]["note"] and C.FALLBACK_NOTE not in b["price"]["note"] and "同じファイル由来" in b["price"]["note"]


def test_display_frame_is_apart_from_the_measured_bar_and_the_range_may_leave_the_run(tmp_path):
    t0, root = _world(tmp_path)  # measured on 15-minute bars, run from t0+900
    d = C.run_chart(root, "2" * 64, from_s=t0 + 100, to_s=t0 + 700, interval_s=60, root=tmp_path)
    assert d["interval_s"] == 60 and d["measure_interval_s"] == 900 and d["bars"][0][0] == t0 + 60  # before the run's own start
    d = C.run_chart(root, "2" * 64, interval_s=14400, root=tmp_path)
    assert d["interval_s"] == 14400 and all(b[0] % 14400 == 0 for b in d["bars"])
    big = C.run_chart(root, "2" * 64, from_s=t0 - 10**7, to_s=t0 + 10**8, interval_s=86400, root=tmp_path)
    assert big["from_s"] == t0 and big["bars"][0][0] == t0 // 86400 * 86400
    f4 = C.run_chart(root, "2" * 64, interval_s=14400, root=tmp_path)["bars"][0]
    assert f4[2] >= f4[1] and f4[3] <= f4[4]


def test_too_many_bars_narrow_the_range_and_say_so(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    monkeypatch.setattr(C, "HARD_MAX_BARS", 100)
    d = C.run_chart(root, "2" * 64, from_s=t0, to_s=t0 + 3000 * 60, interval_s=60, root=tmp_path)
    assert d["narrowed"] == {"requested_bars": 3000, "max_bars": 100} and len(d["bars"]) <= 101 and d["interval_s"] == 60


def test_range_slices_layers_and_too_many(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    full = C.run_chart(root, "2" * 64, root=tmp_path, max_bars=100)
    L = full["layers"]["pessimistic"]
    assert L["counts"]["trades"] >= 2 and L["cum"][-1][1] == pytest.approx(1.0 + 1.0) or L["counts"]["trades"] == 3
    zoom = C.run_chart(root, "2" * 64, from_s=t0 + 500, to_s=t0 + 1500, interval_s=60, root=tmp_path)["layers"]["pessimistic"]
    assert [t["id"] for t in zoom["trades"]] == ["0"] and zoom["cum"][0][1] == 0 and [f["id"] for f in zoom["fills"]] == ["0", "1"]
    later = C.run_chart(root, "2" * 64, from_s=t0 + 3500, to_s=t0 + 3700, root=tmp_path)["layers"]["pessimistic"]
    assert later["cum"][0][1] == pytest.approx(1.0) and [t["id"] for t in later["trades"]] == ["1"]  # the value at the left edge is the one before it
    monkeypatch.setitem(RV.MAX_ITEMS, "trades", 2)
    d = C.run_chart(root, "2" * 64, from_s=t0, to_s=t0 + 99999, root=tmp_path)["layers"]["pessimistic"]
    assert d["too_many"] == {"trades": 3} and d["trades"] == [] and d["cum"] and d["counts"]["trades"] == 3


def test_no_price_still_gives_the_cumulative_profit(tmp_path):
    _seal(tmp_path)
    root = _run(tmp_path, "6" * 64, cfg={"instrument": "NOSUCH"}, data=[_spec("backtest_data/none/x.csv.gz", "NOSUCH")],
                first=100 * NS, last=900 * NS, trades=[_trade(1, 100, 200, 10, 15), _trade(2, 300, 400, 10, 5)])
    s = C.run_summary(root, "6" * 64, tmp_path)
    assert not s["price"]["available"] and "台帳" in s["price"]["reason"]
    d = C.run_chart(root, "6" * 64, root=tmp_path)
    L = d["layers"]["pessimistic"]
    assert d["bars"] == [] and L["cum"][-1][1] == pytest.approx(0.0) and L["counts"]["trades"] == 2
    h = s["headline"]["pessimistic"]["trades"]
    assert h["closed"] == 2 and h["wins"] == 1 and h["losses"] == 1 and h["win_rate"] == 0.5 and h["pnl_sum"] == pytest.approx(0.0)
    assert s["headline"]["pessimistic"]["drawdown"]["max"] == pytest.approx(0.5)
    _csv(tmp_path / XBT, [])  # a market whose files are missing says why
    root = _run(tmp_path, "5" * 64, data=[], first=100 * NS, last=900 * NS, trades=[])
    (tmp_path / XBT).unlink()
    assert "ディスクに無い" in C.run_summary(root, "5" * 64, tmp_path)["price"]["reason"]


def test_cache_lives_outside_the_repository_and_old_stores_are_evicted(tmp_path, monkeypatch):
    monkeypatch.delenv("BT_CHART_CACHE_DIR")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "lad"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert REPO not in C._cache_root().parents and C._cache_root().name == "trade_bt_chart_cache"
    monkeypatch.setenv("BT_CHART_CACHE_DIR", str(tmp_path / "cache"))
    t0, root = _world(tmp_path)
    C.run_chart(root, "2" * 64, root=tmp_path)
    monkeypatch.setenv("BT_CHART_CACHE_MAX_MB", "0")
    _csv(tmp_path / FXDIR / "candles_1m_2022.csv.gz", _minute_rows(_ts("2022-01-01T00:00:00"), 100), header="ts,open,high,low,close,volume",
         iso="%Y-%m-%dT%H:%M:%S+00:00")
    r2 = _run(tmp_path, "9" * 64, cfg={"instrument": "FX_BTC_JPY"}, data=[], first=_ts("2022-01-01T00:01:00") * NS, last=_ts("2022-01-01T01:00:00") * NS, trades=[])
    C.run_chart(r2, "9" * 64, root=tmp_path)
    left = [d.name for d in (tmp_path / "cache").iterdir()]
    assert len(left) == 1 and left[0].startswith("FX_BTC_JPY")


# ---- the dashboard routes -------------------------------------------------------------------------------------
def _dash():
    spec = importlib.util.spec_from_file_location("dashboard_for_bt_chart", REPO / "scripts" / "dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dashboard_routes_serve_catalog_summary_chart_table_trace_and_only_listed_static_files(tmp_path):
    dash = _dash()
    t0, root = _world(tmp_path)
    rid = "2" * 64
    st, ct, body = dash._backtest("/api/backtest/catalog", root, tmp_path)
    cat = json.loads(body)
    assert st == 200 and cat["n_runs"] == 1 and cat["themes"][-1]["id"] in ("fake", "unlisted")
    st, _, body = dash._backtest(f"/api/backtest/chart/{rid}?from={t0 + 500}&to={t0 + 1500}&interval=60&range=both", root, tmp_path)
    ch = json.loads(body)
    assert st == 200 and ch["interval_s"] == 60 and sorted(ch["layers"]) == ["optimistic", "pessimistic"]
    st, _, body = dash._backtest(f"/api/backtest/summary/{rid}", root, tmp_path)
    assert st == 200 and json.loads(body)["price"]["available"]
    st, _, body = dash._backtest(f"/api/backtest/table/{rid}/trades?sort=pnl_jpy&dir=desc&size=2&f=" + json.dumps([["status", "eq", "closed"]]).replace(" ", "%20"), root, tmp_path)
    t = json.loads(body)
    assert st == 200 and t["matched"] == 3 and len(t["rows"]) == 2 and len(t["columns"]) == len(RV.columns_of(RV.load(str(Path(root) / "g" / rid)).schema, "trades")) and t["pages"] == 2
    st, _, body = dash._backtest(f"/api/backtest/trace/{rid}/trades/0", root, tmp_path)
    assert st == 200 and {l["table"] for l in json.loads(body)["links"]} == {"ledger_fills", "fills", "orders", "signals"}
    assert dash._backtest(f"/api/backtest/file/{rid}/SCHEMA.json", root, tmp_path)[0] == 200
    assert dash._backtest(f"/api/backtest/file/{rid}/..%2Frepro.json", root, tmp_path)[0] == 400
    assert dash._backtest("/api/backtest/chart/" + "9" * 64, root, tmp_path)[0] == 404
    assert dash._backtest(f"/api/backtest/chart/{rid}?from=abc", root, tmp_path)[0] == 400
    assert dash._backtest(f"/api/backtest/table/{rid}/trades?f=notjson", root, tmp_path)[0] == 400
    assert dash._backtest(f"/api/backtest/table/{rid}/nosuch", root, tmp_path)[0] == 400
    assert dash._backtest(f"/api/backtest/trace/{rid}/trades/99999", root, tmp_path)[0] == 400
    assert dash._backtest(f"/api/backtest/trace/{rid}/trades/x", root, tmp_path)[0] == 400
    js = dash._backtest("/static/lightweight-charts.standalone.production.js", root, tmp_path)
    assert js[0] == 200 and b"Lightweight Charts" in js[2]
    for bad in ("/static/..%2Fbacktest_chart.py", "/static/../backtest_chart.py", "/static/nope.js", "/static/.x"):
        assert dash._backtest(bad, root, tmp_path)[0] == 404
    assert (Path(C.STATIC_DIR) / "LICENSE-lightweight-charts.txt").is_file()
    assert "/static/lightweight-charts.standalone.production.js" in dash.PAGE and "id=\"bt-frame\"" in dash.PAGE


def test_after_seal_run_is_400_over_the_route(tmp_path):
    dash = _dash()
    _seal(tmp_path)
    root = _run(tmp_path, "7" * 64, data=[], first=(BOUNDARY + 100) * NS, last=(BOUNDARY + 200) * NS, trades=[])
    assert dash._backtest(f"/api/backtest/chart/{'7' * 64}", root, tmp_path)[0] == 400
    assert dash._backtest(f"/api/backtest/table/{'7' * 64}/trades", root, tmp_path)[0] == 400
    assert json.loads(dash._backtest(f"/api/backtest/summary/{'7' * 64}", root, tmp_path)[2])["after_seal"] is True




def test_chart_request_does_not_wait_for_the_price_store_and_the_page_gets_progress_then_bars(tmp_path, monkeypatch):
    import threading
    t0, root = _world(tmp_path)
    gate, entered = threading.Event(), threading.Event()
    orig = C._read_file

    def slow(*a, **k):
        entered.set()
        gate.wait(20)
        return orig(*a, **k)
    monkeypatch.setattr(C, "_read_file", slow)
    import time
    t = time.time()
    d = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert time.time() - t < 5 and d["building"] and d["bars"] == [] and d["building"]["market"] == "XBTUSD"
    assert d["building"]["stage"] in ("starting", "reading") and "elapsed_s" in d["building"] and d["price"]["available"]
    assert d["layers"]["pessimistic"]["counts"]["trades"] == 3 and len(d["layers"]["pessimistic"]["cum"]) >= 2 and d["layers"]["pessimistic"]["trades"]  # the numbers that need no price are already there
    assert entered.wait(10)
    d2 = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert d2["building"] and len([th for th in threading.enumerate() if th.name == "bt-store-XBTUSD"]) == 1  # not built twice
    gate.set()
    for th in list(threading.enumerate()):
        if th.name.startswith("bt-store-"):
            th.join(30)
    d3 = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert not d3["building"] and d3["bars"] and d3["price"]["available"]
    assert "store_built" in (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")


def test_a_failed_background_build_is_told_to_the_page_not_polled_for_ever(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk on fire")))
    C.run_chart(root, RID, root=tmp_path, wait=False)
    import threading
    for th in list(threading.enumerate()):
        if th.name.startswith("bt-store-"):
            th.join(10)
    d = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert not d["building"] and not d["price"]["available"] and "disk on fire" in d["price"]["reason"]
    assert "store_build_failed" in (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")


def test_two_threads_asking_for_one_store_build_it_once(tmp_path, monkeypatch):
    import threading
    t0, root = _world(tmp_path)
    n = []
    orig = C._read_file
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: (n.append(1), orig(*a, **k))[1])
    rule = C.seal_rule(tmp_path)
    plan = C.price_plan({"config": {"instrument": "XBTUSD"}}, tmp_path, rule)
    out = []
    ths = [threading.Thread(target=lambda: out.append(C.get_store(plan, rule))) for _ in range(4)]
    [t.start() for t in ths]
    [t.join(30) for t in ths]
    assert len(out) == 4 and all(o is out[0] for o in out) and len(n) == len(plan.files)


def test_cache_write_failure_is_logged_and_the_store_stays_in_memory_without_rebuilding(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    rule = C.seal_rule(tmp_path)
    plan = C.price_plan({"config": {"instrument": "XBTUSD"}}, tmp_path, rule)
    n = []
    orig = C._read_file
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: (n.append(1), orig(*a, **k))[1])

    def locked(*a, **k):
        raise PermissionError("[WinError 32] file is being used by another process")
    monkeypatch.setattr(C.np, "save", locked)
    st = C.get_store(plan, rule)
    assert st.rows == 3000 and st.pinned and not st.from_cache
    log = (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")
    assert "cache_write_failed" in log and "WinError 32" in log
    assert not list((tmp_path / "cache").glob(".*.tmp"))  # no half-written directory is left
    # other stores come and go: the pinned one is not pushed out, so the next request does not parse again
    for i in range(3):
        C._STORES[f"x{i}"] = C.Store("x", st.frames, 0, 0, 0, None, 0, False)
        with C._LOCK:
            while len(C._STORES) > 2:
                v = next((k for k, o in C._STORES.items() if not o.pinned), None)
                C._STORES.pop(v)
    assert C.get_store(plan, rule) is st and len(n) == len(plan.files)


def test_warmup_builds_every_store_in_the_background_and_a_later_request_finds_it(tmp_path):
    t0, root = _world(tmp_path)
    C.start_store_warmup(tmp_path).join(60)  # no runs_dir: every instrument of MARKETS that has files
    d = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert not d["building"] and d["bars"]
    assert "warmup" in (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")


def test_tab_log_has_one_line_per_event_and_the_dashboard_logs_slow_and_failed_requests(tmp_path):
    dash = _dash()
    t0, root = _world(tmp_path)
    assert dash._backtest("/api/backtest/summary/" + "e" * 64, root, tmp_path)[0] == 404
    lines = (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    ts, action, sec, result = lines[0].split("\t")
    assert ts.endswith("Z") and action.startswith("GET /api/backtest/summary/") and sec.endswith("s") and result.startswith("HTTP 404")
    bat = (REPO / "deploy" / "share_logs.bat").read_text(encoding="utf-8")
    assert "copy /Y logs\\dashboard_bt.log paper_logs\\ >nul 2>&1" in bat


def test_page_script_never_leaves_a_black_screen_without_a_reason():
    dash = _dash()
    js = (Path(C.STATIC_DIR) / "backtest_tab.js").read_text(encoding="utf-8")
    for need in ("AbortController", "時間切れ", "サーバーに接続できない", "HTTP ${r.status}", 'addEventListener("error"', "unhandledrejection",
                 "価格のキャッシュを作っています(初回だけ)", "秒経過", "d.building"):
        assert need in js, need
    assert 'id="bt-banner"' in dash.PAGE and 'id="bt-chart-busy"' in dash.PAGE
    assert "start_store_warmup" in (REPO / "scripts" / "dashboard.py").read_text(encoding="utf-8")


# ---- the store is built by a separate process; only the instruments the tab uses are warmed -------------------------
def test_store_is_built_by_a_child_process_and_requests_stay_quick_meanwhile(tmp_path, monkeypatch):
    import threading
    import time
    t0, root = _world(tmp_path)
    monkeypatch.setattr(C, "BUILD_IN_CHILD", True)
    parent_reads = []
    orig = C._read_file
    monkeypatch.setattr(C, "_read_file", lambda *a, **k: (parent_reads.append(1), orig(*a, **k))[1])  # patched in THIS process only
    d = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert d["building"]  # the answer did not wait for the build
    slow = []
    deadline = time.time() + 120
    while time.time() < deadline:
        t = time.time()
        C.catalog(root)  # the list keeps answering while the child works
        slow.append(time.time() - t)
        d = C.run_chart(root, RID, root=tmp_path, wait=False)
        if not d["building"]:
            break
        time.sleep(0.3)
    assert not d["building"] and d["bars"], d["building"]
    assert max(slow) < 2.0, slow
    assert parent_reads == []  # this process never read the 1-minute files: the child did
    log = (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")
    pid = int(next(ln for ln in log.splitlines() if "\tstore_child\t" in ln).rsplit("pid=", 1)[1])
    assert pid != os.getpid() and "store_built" in log and "store_loaded" in log
    assert list((tmp_path / "cache").glob("XBTUSD-*/meta.json"))


def test_a_child_that_cannot_write_the_cache_leaves_the_build_to_this_process_in_memory(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    monkeypatch.setattr(C, "BUILD_IN_CHILD", True)
    # the cache directory is a plain file: the child cannot create it
    (tmp_path / "cache").write_text("not a directory")
    d = C.run_chart(root, RID, root=tmp_path, wait=False)
    import threading
    import time
    for _ in range(240):
        if not d["building"]:
            break
        time.sleep(0.5)
        d = C.run_chart(root, RID, root=tmp_path, wait=False)
    assert d["bars"] and not d["building"]
    log = (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")
    assert "cache_write_failed" in log and "store_child_no_cache" in log


def test_warmup_builds_only_the_instruments_the_runs_use_most_runs_first(tmp_path):
    t0, root = _world(tmp_path)  # one run on XBTUSD
    _run(tmp_path, "1" * 64, "g", {"instrument": "XBTUSD"}, first=t0 * NS, last=(t0 + 600) * NS, trades=[])
    _csv(tmp_path / FXDIR / "candles_1m_2022.csv.gz", _minute_rows(_ts("2022-01-01T00:00:00"), 100), header="ts,open,high,low,close,volume",
         iso="%Y-%m-%dT%H:%M:%S+00:00")
    _run(tmp_path, "3" * 64, "g", {"instrument": "FX_BTC_JPY"}, first=_ts("2022-01-01T00:01:00") * NS, last=_ts("2022-01-01T01:00:00") * NS, trades=[])
    assert C.used_markets(root) == ["XBTUSD", "FX_BTC_JPY"]
    C.start_store_warmup(tmp_path, root).join(60)
    built = {p.name.split("-")[0] for p in (tmp_path / "cache").glob("*-*") if (p / "meta.json").exists()}
    assert built == {"XBTUSD", "FX_BTC_JPY"}  # BTC_JPY and BTCUSDT: no run uses them, so nothing was made for them
    assert "instruments: XBTUSD, FX_BTC_JPY" in (tmp_path / "dashboard_bt.log").read_text(encoding="utf-8")
