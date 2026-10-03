"""The バックテスト tab's ledger, family axes, price stores and chart API (src/bot/monitoring/backtest_themes.py,
backtest_chart.py). The seal tests are written so that each layer of the cut fails on its own when removed (see the
mutation list in the comments)."""
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
from bot.monitoring import backtest_themes as T

REPO = Path(__file__).resolve().parents[1]
BOUNDARY = int(datetime(2023, 12, 18, tzinfo=timezone.utc).timestamp())
NS = 10**9
XBT = "backtest_data/k1_newenv_a_20260927/xbtusd_1m_2017_2019.csv.gz"
FXDIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("BT_CHART_CACHE_DIR", str(tmp_path / "cache"))
    for d in (C._STORES, C._TRADES, C._REC, C._RULES):
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


def _run(root: Path, rid: str, group="g", cfg=None, data=None, first=None, last=None, trades=None, git="a" * 40, diff="b" * 64):
    d = root / "backtest_runs_shared" / group / rid
    d.mkdir(parents=True)
    rec = {"config": cfg or {"instrument": "XBTUSD"}, "data": data if data is not None else [], "engine": {"first_time_ns": first, "last_time_ns": last},
           "git_sha": git, "diff_hash": diff, "purpose": "研究", "setup": {"name": "x"}}
    (d / "record.json").write_text(json.dumps(rec))
    (d / "repro.json").write_text("{}")
    with gzip.open(d / "trades.json.gz", "wt") as fh:
        json.dump(trades if isinstance(trades, dict) else {"data": trades or []}, fh)
    return str(root / "backtest_runs_shared")


def _trade(i, et, xt, ep, xp, side="buy"):
    sgn = 1 if side == "buy" else -1
    return {"id": f"t{i}", "entry_t_ns": et * NS, "exit_t_ns": xt * NS, "entry_px": ep, "exit_px": xp, "qty": 1.0,
            "side": side, "pnl": (xp - ep) * sgn, "fees": 0.0, "reason": "r"}


def _world(tmp_path, n_min=3000, start="2023-01-01T00:00:00", trades=None, data_kind="bar", rid="2" * 64, first=None, last=None):
    """A root with the seal ledger, an XBTUSD 1-minute store file and one run on it (its own file is a 15 m one)."""
    _seal(tmp_path)
    t0 = _ts(start)
    _csv(tmp_path / XBT, _minute_rows(t0, n_min))
    trades = trades if trades is not None else [_trade(1, t0 + 600, t0 + 1200, 110, 120), _trade(2, t0 + 3000, t0 + 3600, 130, 120, "sell"),
                                                _trade(3, t0 + 90000, t0 + 90600, 200, 190)]
    root = _run(tmp_path, rid, data=[_spec("backtest_data/k1_newenv_a_20260927/xbtusd_15m_2017_2019.csv.gz", interval=900, kind=data_kind)],
                first=(first if first is not None else t0 + 900) * NS, last=(last if last is not None else t0 + n_min * 60) * NS, trades=trades)
    return t0, root


# ---- the ledger ---------------------------------------------------------------------------------------------
def test_every_ledger_group_exists_and_every_shared_run_is_placed():
    cat = C.catalog(str(REPO / "backtest_runs_shared"))
    assert cat["missing_groups"] == []
    assert [t["id"] for t in cat["themes"] if t["id"] == T.UNLISTED_THEME] == []
    assert sum(s["n_runs"] for t in cat["themes"] for s in t["strategies"]) == cat["n_runs"]
    T.strategy_groups()
    for th in T.THEMES:
        for st in th["strategies"]:
            assert 3 <= len(st["description"]) <= 6 and st["sources"] and set(st["axes"]) <= set(T.AXES)
    env = [t for t in cat["themes"] if t["id"] == "env_check"][0]
    assert "k1_newenv_g_close" in [g for s in env["strategies"] for g in s["groups"]]


def test_ledger_strategy_axes_make_each_run_reachable_and_unique():
    cat = C.catalog(str(REPO / "backtest_runs_shared"))
    for t in cat["themes"]:
        for s in t["strategies"]:
            keys = [a["key"] for a in s["axes"]]
            combos = [tuple(r["axes"][k] for k in keys) for r in s["runs"]]
            assert len(set(combos)) == len(combos), s["id"]
            for a in s["axes"]:
                assert {v["value"] for v in a["values"]} >= {r["axes"][a["key"]] for r in s["runs"]}


def test_axes_are_collected_from_records_and_version_only_when_needed(tmp_path):
    root = None
    for i, (foot, gate) in enumerate([(1, "s19/b24"), (1, "s10/b-"), (5, "s19/b24")]):
        s, b = gate[1:].split("/b")
        root = _run(tmp_path, f"{i:064x}", "k1_newenv_a", {"instrument": "XBTUSD", "foot_min": foot, "gate": {"s": s, "b": b},
                                                         "strength": "both"}, first=NS, last=2 * NS)
    st = [s for t in C.catalog(root)["themes"] for s in t["strategies"] if s["id"] == "k1_wick_xbtusd"][0]
    axes = {a["key"]: [v["value"] for v in a["values"]] for a in st["axes"]}
    assert axes["foot_min"] == ["1", "5"] and axes["gate"] == ["s10/b-", "s19/b24"] and "version" not in axes
    _run(tmp_path, "f" * 64, "k1_newenv_a", {"instrument": "XBTUSD", "foot_min": 1, "gate": {"s": "19", "b": "24"}, "strength": "both"},
         first=NS, last=2 * NS, git="c" * 40)
    C._REC.clear()
    st = [s for t in C.catalog(root)["themes"] for s in t["strategies"] if s["id"] == "k1_wick_xbtusd"][0]
    ver = [a for a in st["axes"] if a["key"] == "version"][0]
    assert ver["secondary"] and len(ver["values"]) == 2


def test_period_label_names_the_last_day_it_contains():
    rec = {"engine": {"first_time_ns": BOUNDARY * NS - 86400 * NS, "last_time_ns": BOUNDARY * NS}}
    assert T._period(rec) == "2023-12-17〜2023-12-17"


def test_run_outside_the_ledger_is_listed_not_hidden(tmp_path):
    root = _run(tmp_path, "1" * 64, "unknown_group", first=NS, last=2 * NS)
    loose = [t for t in C.catalog(root)["themes"] if t["id"] == T.UNLISTED_THEME][0]
    assert loose["strategies"][0]["runs"][0]["run_id"] == "1" * 64


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
    assert "blocked" in s and "stats" not in s
    with pytest.raises(C.SealBlocked):
        C.run_chart(root, "2" * 64, root=tmp_path)
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
    assert max(C.get_store(C.price_plan(C._record(str(Path(root) / "g" / ("3" * 64))), tmp_path, C.seal_rule(tmp_path)), C.seal_rule(tmp_path)).frames[60][0]) < BOUNDARY


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


def test_boundary_trade_is_shown_for_a_bars_only_run_and_not_for_other_runs(tmp_path):
    start, root = _edge_world(tmp_path, kind="bar")
    s = C.run_summary(root, "3" * 64, tmp_path)
    assert s["stats"]["n"] == 2  # exits at start+240 and AT the boundary; the one after it is not part of the run
    d = C.run_chart(root, "3" * 64, root=tmp_path, from_s=start, to_s=BOUNDARY + 100)
    assert [t["xt"] for t in d["trades"]] == [start + 240, BOUNDARY] and d["trades_total"] == 2
    assert all(p[0] <= BOUNDARY for p in d["pnl"])
    C._REC.clear(); C._TRADES.clear()
    tmp2 = tmp_path / "other"
    tmp2.mkdir()
    start, root2 = _edge_world(tmp2, kind="trade")  # a data entry that is not a bar: a row AT the boundary is sealed
    s2 = C.run_summary(root2, "3" * 64, tmp2)
    assert s2["stats"]["n"] == 1
    assert [t["xt"] for t in C.run_chart(root2, "3" * 64, root=tmp2, from_s=start, to_s=BOUNDARY + 100)["trades"]] == [start + 240]


def test_M2_the_chart_cuts_trades_even_if_the_loaded_set_holds_later_ones(tmp_path, monkeypatch):
    start, root = _edge_world(tmp_path, kind="trade")
    orig = C.load_trades
    monkeypatch.setattr(C, "load_trades", lambda d, r=None, limit_ns=None: orig(d, r, None))
    d = C.run_chart(root, "3" * 64, root=tmp_path, from_s=start, to_s=BOUNDARY + 100)
    assert [t["xt"] for t in d["trades"]] == [start + 240] and d["trades_in_range"] == 1
    assert all(p[0] < BOUNDARY for p in d["pnl"])


def test_numbers_of_the_headline_follow_the_same_cut(tmp_path):
    start, root = _edge_world(tmp_path, kind="trade")
    s = C.run_summary(root, "3" * 64, tmp_path)
    assert s["stats"]["n"] == 1 and s["stats"]["total"] == 1.0  # the trades at and after the boundary are not counted


def test_a_run_wholly_after_the_boundary_shows_no_number(tmp_path):
    _seal(tmp_path)
    t0 = BOUNDARY + 86400
    _csv(tmp_path / XBT, _minute_rows(BOUNDARY - 120, 5))
    root = _run(tmp_path, "7" * 64, data=[_spec("backtest_data/x.csv.gz")], first=t0 * NS, last=(t0 + 600) * NS,
                trades=[_trade(1, t0 + 60, t0 + 120, 1, 2)])
    s = C.run_summary(root, "7" * 64, tmp_path)
    assert s["after_seal"] and "封印の境" in s["blocked"] and "より後" in s["blocked"] and "stats" not in s
    with pytest.raises(C.AfterSeal):
        C.run_chart(root, "7" * 64, root=tmp_path)


def test_year_file_after_the_boundary_year_is_never_opened_and_sealed_dir_is_refused(tmp_path, monkeypatch):
    _seal(tmp_path)
    for y in (2023, 2024):
        _csv(tmp_path / FXDIR / f"candles_1m_{y}.csv.gz", _minute_rows(_ts(f"{y}-12-17T23:50:00"), 30), header="ts,open,high,low,close,volume",
             iso="%Y-%m-%dT%H:%M:%S+00:00")
    root = _run(tmp_path, "4" * 64, cfg={"instrument": "FX_BTC_JPY"}, data=[_spec("backtest_data/k1_newenv_g_20261001/x.csv.gz", "FX_BTC_JPY", 900)],
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


def test_range_and_pnl_slices(tmp_path, monkeypatch):
    t0, root = _world(tmp_path)
    full = C.run_chart(root, "2" * 64, root=tmp_path, max_bars=100)
    assert full["trades_in_range"] >= 2 and full["pnl"][-1][1] == pytest.approx(10 + 10 - 10) or full["trades_in_range"] == 3
    zoom = C.run_chart(root, "2" * 64, from_s=t0 + 500, to_s=t0 + 1500, interval_s=60, root=tmp_path)
    assert [t["i"] for t in zoom["trades"]] == [0] and zoom["trades"][0]["pnl"] == 10 and zoom["pnl"][0][1] == 0
    later = C.run_chart(root, "2" * 64, from_s=t0 + 3500, to_s=t0 + 3700, root=tmp_path)
    assert later["pnl"][0][1] == 10 and [t["i"] for t in later["trades"]] == [1]
    monkeypatch.setattr(C, "MAX_TRADES", 2)
    d = C.run_chart(root, "2" * 64, from_s=t0, to_s=t0 + 99999, root=tmp_path)
    assert d["too_many"] and d["trades"] == [] and d["trades_in_range"] == 3 and d["pnl"]


def test_no_price_still_gives_the_cumulative_profit(tmp_path):
    _seal(tmp_path)
    root = _run(tmp_path, "6" * 64, cfg={"instrument": "NOSUCH"}, data=[_spec("backtest_data/none/x.csv.gz", "NOSUCH")],
                first=100 * NS, last=900 * NS, trades=[_trade(1, 100, 200, 10, 15), _trade(2, 300, 400, 10, 5)])
    s = C.run_summary(root, "6" * 64, tmp_path)
    assert not s["price"]["available"] and "台帳" in s["price"]["reason"]
    d = C.run_chart(root, "6" * 64, root=tmp_path)
    assert d["bars"] == [] and d["pnl"][-1][1] == 0 and d["trades_in_range"] == 2
    st = s["stats"]
    assert st["n"] == 2 and st["wins"] == 1 and st["win_rate"] == 0.5 and st["total"] == 0 and st["max_dd"] == 5
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


# ---- trades: both shapes, money only when the record holds it ---------------------------------------------------------
def test_column_form_trades_read_like_the_row_form_and_hold_no_money():
    rows = [_trade(1, 10, 20, 100, 110), _trade(2, 30, 40, 100, 90, "sell"), _trade(3, 50, 60, 100, 95)]
    a = C.read_trades({"data": rows})
    doc = {"version": 1, "t_unit": "ns", "entry_t_ns": [r["entry_t_ns"] for r in rows], "entry_px": [100] * 3,
           "exit_t_ns": [r["exit_t_ns"] for r in rows], "exit_px": [r["exit_px"] for r in rows],
           "side": [1, -1, 1], "qty": [1, 1, 1], "pnl_bp": [float(x) for x in a.bp]}
    b = C.read_trades(doc)
    assert b.pnl_derived and np.allclose(b.bp, a.bp) and np.array_equal(b.xt, a.xt) and np.array_equal(b.side, a.side)
    st = C.trade_stats(b)
    assert st["total"] is None and st["max_dd"] is None and st["wins"] == 2 and st["total_bp"] == pytest.approx(C.trade_stats(a)["total_bp"])


def test_range_cut_on_many_column_trades_is_a_binary_search():
    n = 800_000
    et = (np.arange(n, dtype=np.int64) * 60 + 10**9) * NS
    ts = C.read_trades({"version": 1, "t_unit": "ns", "entry_t_ns": et, "entry_px": np.full(n, 100.0), "exit_t_ns": et + 30 * NS,
                        "exit_px": np.full(n, 101.0), "side": np.ones(n, dtype=np.int64), "qty": np.ones(n), "pnl_bp": np.ones(n)})
    assert ts.n == n and ts.entry_sorted and int(np.searchsorted(ts.xt, (10**9 + 6000) * NS)) == 100 and ts.cum_bp[-1] == n
    assert C.truncate(ts, int(et[1000])).n == 1000


def test_pipeline_ranges_follow_the_range_switch(tmp_path):
    _seal(tmp_path)
    rows = [dict(_trade(1, 100, 200, 10, 15), range="optimistic"), dict(_trade(1, 100, 200, 10, 12), range="pessimistic")]
    root = _run(tmp_path, "a" * 64, data=[], first=50 * NS, last=900 * NS, trades=rows)
    a = C.run_summary(root, "a" * 64, tmp_path, range_name="optimistic")
    b = C.run_summary(root, "a" * 64, tmp_path, range_name="pessimistic")
    assert a["ranges"] == ["optimistic", "pessimistic"] and a["ranges_identical"] is False
    assert a["stats"]["total"] == 5 and b["stats"]["total"] == 2 and b["range"] == "pessimistic"


# ---- the dashboard routes -------------------------------------------------------------------------------------
def _dash():
    spec = importlib.util.spec_from_file_location("dashboard_for_bt_chart", REPO / "scripts" / "dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dashboard_routes_serve_catalog_summary_chart_and_only_listed_static_files(tmp_path):
    dash = _dash()
    t0, root = _world(tmp_path)
    st, ct, body = dash._backtest("/api/backtest/catalog", root, tmp_path)
    cat = json.loads(body)
    assert st == 200 and cat["n_runs"] == 1 and cat["themes"][-1]["id"] == T.UNLISTED_THEME
    st, _, body = dash._backtest(f"/api/backtest/chart/{'2' * 64}?from={t0 + 500}&to={t0 + 1500}&interval=60", root, tmp_path)
    assert st == 200 and json.loads(body)["interval_s"] == 60
    st, _, body = dash._backtest(f"/api/backtest/summary/{'2' * 64}", root, tmp_path)
    assert st == 200 and json.loads(body)["price"]["available"]
    assert dash._backtest("/api/backtest/chart/" + "9" * 64, root, tmp_path)[0] == 404
    assert dash._backtest(f"/api/backtest/chart/{'2' * 64}?from=abc", root, tmp_path)[0] == 400
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
    assert json.loads(dash._backtest(f"/api/backtest/summary/{'7' * 64}", root, tmp_path)[2])["after_seal"] is True
