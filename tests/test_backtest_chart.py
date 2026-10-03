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

from bot.monitoring import backtest_cards as K
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
    for d in (C._STORES, C._TRADES, C._REC, C._RULES, K._MAN, K._OK, K._PROV):
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


# ---- the research cards (backtest_cards.py, the CARD_THEMES ledger) ------------------------------------------------
CARD_MANIFEST = REPO / "backtest_runs_shared" / "cards" / "manifest.json"
FXCOLS = "ts,open,high,low,close,vol"


def _write_card(root: Path, card: str, variant: str, t0: int, trades: list, period=None, prov_extra=None):
    """One card variant's output as scripts/dashboard_cards writes it: trades.json.gz (column form, bp only), daily.csv,
    provenance.json. `trades` = [(entry_t, exit_t, entry_px, exit_px, side, pnl_bp)] in UTC seconds."""
    d = root / "backtest_runs_shared" / "cards" / card / variant
    d.mkdir(parents=True, exist_ok=True)
    cols = {"version": 1, "t_unit": "ns", "entry_t_ns": [t[0] * NS for t in trades], "entry_px": [t[2] for t in trades],
            "exit_t_ns": [t[1] * NS for t in trades], "exit_px": [t[3] for t in trades], "side": [t[4] for t in trades],
            "qty": [1] * len(trades), "pnl_bp": [t[5] for t in trades]}
    with gzip.open(d / "trades.json.gz", "wb") as fh:
        fh.write(json.dumps(cols).encode())
    (d / "daily.csv").write_text("day,pnl_bp,n\n2023-01-01,%s,%d\n" % (sum(t[5] for t in trades), len(trades)))
    prov = {"card": card, "variant": variant, "display_ok": True, "trade_definition": "def", "seal": "s", "data_dirs_read": [FXDIR],
            "script": {"export": "e", "research_cmd": ["c"]}, "verified_items": ["daily_csv_sha256"], "not_verified": ["取引数は照合していない"]}
    prov.update(prov_extra or {})
    (d / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")
    return d


def _row(card, variant, d=None, ok=True, period=("2023-01-01T00:00:00Z", "2023-01-03T00:00:00Z"), **kw):
    row = {"card": card, "variant": variant, "status": "exported" if ok else "not_exported", "display_ok": ok, "period": list(period)}
    if ok:
        row.update(verified_items=["daily_csv_sha256"], not_verified=["取引数は照合していない"], n_trades=kw.pop("n_trades", 0))
        if d is not None:
            row["file_bytes"] = {f: (d / f).stat().st_size for f in K.FILES if (d / f).exists()}
    else:
        row["reason"] = "未実行または失敗"
    row.update(kw)
    return row


def _manifest(root: Path, rows, excluded=()):
    p = root / "backtest_runs_shared" / "cards" / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": 1, "git_sha": "g", "total_bytes": 1, "variants": list(rows), "excluded": list(excluded)}), encoding="utf-8")
    return p


def _cards_world(tmp_path, n_min=3000, start="2023-01-01T00:00:00"):
    """Seal ledger, a FX_BTC_JPY store (1-minute files) and the card c7_barrier_race with variants: 1h (ready), 1d (display_ok
    false), 1w (display_ok but its trades file is missing: being written)."""
    _seal(tmp_path)
    t0 = _ts(start)
    _csv(tmp_path / FXDIR / "candles_1m_2023.csv.gz", [(t0 + i * 60, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(n_min)], header=FXCOLS)
    trades = [(t0 + 600, t0 + 1200, 110, 120, 1, 90.9), (t0 + 3000, t0 + 3600, 130, 120, -1, 76.9)]
    d = _write_card(tmp_path, "c7_barrier_race", "1h", t0, trades)
    d_w = _write_card(tmp_path, "c7_barrier_race", "1w", t0, trades)
    (d_w / "trades.json.gz").unlink()
    _manifest(tmp_path, [_row("c7_barrier_race", "1h", d, n_trades=2), _row("c7_barrier_race", "1d", ok=False),
                         _row("c7_barrier_race", "1w", d_w, n_trades=2)],
              [{"card": "c9_liquidation_cascade", "variant": "-", "status": "excluded", "reason": "対象外: 測定が無い(文書のみ)"}])
    return t0, str(tmp_path / "backtest_runs_shared")


def _card_themes(root):
    return {t["id"]: t for t in C.catalog(root)["themes"] if t.get("is_card")}


def test_card_ledger_is_complete_and_every_card_has_title_description_and_sources():
    ids = [ct["card"] for ct in T.CARD_THEMES]
    assert len(ids) == len(set(ids)) and ids == sorted(ids, key=lambda c: int(c[1:].split("_")[0]))
    for ct in T.CARD_THEMES:
        assert ct["title"] and ct["summary"] and ct["sources"] and "docs/RESEARCH/cards/" in ct["sources"][0]
        assert (ct["card"] in ("c9_liquidation_cascade",)) == (ct["instrument"] is None)
        if ct["card"] in ("c2_owner_xvenue_wick", "c4_owner_matilda_range"):  # owner-derived: the verbatim section is a source
            assert ct["owner_origin"] and "原文(逐語)" in ct["sources"][0]
        for fam in T.card_families(ct):
            assert 3 <= len(fam["description"]) <= 6 and fam["sources"] and fam["id"]
            import re
            names = set(re.compile(fam["pattern"]).groupindex)
            assert names == set(fam["axes"]) and names <= set(T.CARD_AXES), fam["id"]
    assert [f["id"] for f in T.card_families(T.card_theme("c4_owner_matilda_range"))] == ["parts", "map", "limit"]


def test_axis_values_of_the_ledger_equal_the_names_the_measuring_scripts_make():
    """The axis tokens of the ledger are checked against the scripts that make the variants (read as text, not imported)."""
    import re
    b2 = (REPO / "scripts/w4_measure/run_b2.py").read_text(encoding="utf-8")
    v2 = (REPO / "scripts/w4_measure/run_v2.py").read_text(encoding="utf-8")
    kw = set(re.findall(r'^C4_KW = \{(.*?)\n\}?$', b2, re.S | re.M)[0:1] and re.findall(r'"(\w+)": \{', b2[b2.index("C4_KW"):b2.index("def make_card")]))
    assert kw == {t for t in T.CARD_AXES["c4_part"]["values"] if t != "follow"} | {"follow"} - set() and "follow" in kw
    tp = set(re.findall(r'"(\w+)": \{', b2[b2.index("C4_TP"):b2.index("C4_MAP")]))
    assert tp == set(T.CARD_AXES["c4_tp"]["values"])
    assert set(re.findall(r'^    "([abc])": \(', v2[v2.index("C2_VARIANTS"):], re.M)) == set(T.CARD_AXES["c2_series"]["values"])
    for card, key in (("c6", "c6_gap"), ("c7", "c7_window"), ("c8", "c8_session")):
        m = re.search(rf'"{card}": \("[a-z0-9_]+", \(([^)]*)\)', b2)
        assert set(re.findall(r'"(\w+)"', m.group(1))) == set(T.CARD_AXES[key]["values"]), card
    assert re.search(r'"c3".*window|--window', v2) and set(T.CARD_AXES["c3_window"]["values"]) == {"1h", "1d", "1w"}
    assert [v for v in re.findall(r'"c4_owner_matilda_range", tuple\(f"\{k\}_\{r\}" for k in \(([^)]*)\)', b2)[0].replace('"', "").split(", ")] == \
        [t for t in T.CARD_AXES["c4_part"]["values"] if t not in ("follow", "core")][:5] + ["follow", "core"]


def test_variant_names_split_into_axes_by_machine_rule():
    ct2, ct4 = T.card_theme("c2_owner_xvenue_wick"), T.card_theme("c4_owner_matilda_range")
    assert T.card_family_of(ct2, "b_30m")[1] == {"c2_series": "b", "c2_foot": "30"}
    f, tok = T.card_family_of(ct4, "no_width_wick")
    assert f["id"] == "parts" and tok == {"c4_part": "no_width", "c4_range": "wick"}
    f, tok = T.card_family_of(ct4, "m_b5_w160_e3_c08")
    assert f["id"] == "map" and tok == {"c4_bar": "5", "c4_win": "160", "c4_entry": "3", "c4_tp": "c08"}
    assert T.card_family_of(ct4, "m_b1_w10_e1_c0")[1]["c4_tp"] == "c0"
    f, tok = T.card_family_of(ct4, "limit_v37_bad")
    assert f["id"] == "limit" and tok == {"c4_fill": "bad"}
    assert T.card_family_of(ct4, "something_new") == (None, {})
    assert T.card_axis_label("c2_foot", "15") == ("15 分足", "") and T.card_axis_label("c4_entry", "2")[0] == "2 × 平均実体"
    assert T.card_axis_label("c4_tp", "dote")[0] == "利確の線なし(ドテン)"
    assert T.card_axis_label("c4_part", "brand_new")[1]  # no Japanese label: shown as it is, and the note says so
    assert sorted(["60", "5", "15"], key=lambda v: T.card_axis_order("c2_foot", v)) == ["5", "15", "60"]


@pytest.mark.skipif(not CARD_MANIFEST.is_file(), reason="no cards manifest in this checkout")
def test_the_real_manifest_agrees_with_the_ledger():
    man = K.load_manifest(CARD_MANIFEST.parent)
    assert man is not None and man.error is None and man.rows
    for (card, variant), row in man.rows.items():
        ct = T.card_theme(card)
        assert ct is not None, f"card {card} of the manifest is not in the ledger"
        fam, tok = T.card_family_of(ct, variant)
        assert fam is not None, f"variant {card}/{variant} is split by no family pattern"
        for k, v in tok.items():
            assert T.card_axis_label(k, v)[1] != "台帳にこの値の日本語の説明が無い", f"{card}/{variant}: {k}={v} has no Japanese label"
    for e in man.excluded:
        assert T.card_theme(e["card"]) is not None
    themes = {t["id"]: t for t in C.catalog(str(REPO / "backtest_runs_shared"))["themes"] if t.get("is_card")}
    for (card, variant), row in man.rows.items():
        strat = [s for s in themes[f"card:{card}"]["strategies"]]
        ready = {r["variant"] for s in strat for r in s["runs"]}
        other = {u["variant"]: u for s in strat for u in s["unavailable"]}
        assert (variant in ready) != (variant in other)
        if row["display_ok"] is not True:
            assert variant in other and (other[variant]["reason"] or other[variant]["state"] == "not_exported"), (card, variant)


def test_card_catalog_lists_ready_blocked_preparing_and_excluded_with_reasons(tmp_path):
    t0, root = _cards_world(tmp_path)
    th = _card_themes(root)
    c7 = th["card:c7_barrier_race"]["strategies"][0]
    assert [r["variant"] for r in c7["runs"]] == ["1h"] and c7["runs"][0]["run_id"] == "cards/c7_barrier_race/1h"
    un = {u["variant"]: u for u in c7["unavailable"]}
    assert un["1d"]["state"] == "not_exported" and "測定待ち" in un["1d"]["state_label"]
    assert un["1w"]["state"] == "preparing" and "trades.json.gz" in un["1w"]["reason"]
    assert [a["key"] for a in c7["axes"]] == ["c7_window"] and c7["axes"][0]["values"][0]["label"] == "1 時間"
    c9 = th["card:c9_liquidation_cascade"]["strategies"][0]
    assert c9["runs"] == [] and c9["excluded"][0]["reason"].startswith("対象外") and 3 <= len(c9["description"]) <= 6
    cat = C.catalog(root)
    assert cat["n_card_runs"] == 1 and cat["n_runs"] == 1 and cat["themes"][-1]["id"] == T.UNLISTED_THEME or cat["themes"][-1].get("is_card")


def test_card_with_display_ok_false_is_never_served(tmp_path):
    dash = _dash()
    t0, root = _cards_world(tmp_path)
    d = _write_card(tmp_path, "c7_barrier_race", "1d", t0, [(t0 + 600, t0 + 1200, 110, 120, 1, 1.0)])  # files exist, the manifest says no
    for route in ("summary", "chart", "run"):
        st, _, body = dash._backtest(f"/api/backtest/{route}/cards/c7_barrier_race/1d", root, tmp_path)
        assert st == 404 and (route == "run" or "not displayable" in json.loads(body)["error"]), route
    assert {u["variant"] for u in _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["unavailable"]} >= {"1d"}
    assert [r["variant"] for r in _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["runs"]] == ["1h"]


def test_card_ids_outside_the_manifest_or_with_path_tricks_are_404(tmp_path):
    dash = _dash()
    t0, root = _cards_world(tmp_path)
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "trades.json.gz").write_bytes(b"x")
    for rid in ("cards/c7_barrier_race/nope", "cards/c1_xborder_mom/default", "cards/../secret", "cards/c7_barrier_race/../1h",
                "cards%2F..%2F..%2Fsecret%2Fx", "cards/c7_barrier_race", "cards/c7_barrier_race/1h/extra", "cards//1h", "cards/c7_barrier_race/",
                "cards/c7_barrier_race/1h%00", "cards\\c7_barrier_race\\1h", "cards/c9_liquidation_cascade/-", "cards/./1h", "Cards/c7_barrier_race/1h"):
        for route in ("summary", "chart", "run"):
            st = dash._backtest(f"/api/backtest/{route}/{rid}", root, tmp_path)[0]
            assert st == 404, (rid, route, st)
    for ok in ("cards/c7_barrier_race/1h", "cards%2Fc7_barrier_race%2F1h"):
        assert dash._backtest(f"/api/backtest/summary/{ok}", root, tmp_path)[0] == 200
    # the 64-hex run id form is untouched
    assert dash._backtest("/api/backtest/summary/" + "9" * 64, root, tmp_path)[0] == 404


def test_symlink_that_leaves_the_cards_directory_is_refused(tmp_path):
    t0, root = _cards_world(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "trades.json.gz").write_bytes(b"x")
    d = tmp_path / "backtest_runs_shared" / "cards" / "c7_barrier_race" / "1h"
    for f in d.iterdir():
        f.unlink()
    d.rmdir()
    os.symlink(outside, d)
    with pytest.raises(Exception) as ei:
        K.resolve(root, "cards/c7_barrier_race/1h")
    assert "not a run id" in str(ei.value)


def test_half_written_variants_are_shown_as_preparing_not_as_errors(tmp_path):
    dash = _dash()
    t0, root = _cards_world(tmp_path)
    st, _, body = dash._backtest("/api/backtest/summary/cards/c7_barrier_race/1w", root, tmp_path)
    j = json.loads(body)
    assert st == 200 and "準備中" in j["preparing"] and "stats" not in j
    st, _, body = dash._backtest("/api/backtest/chart/cards/c7_barrier_race/1w", root, tmp_path)
    assert st == 400 and "準備中" in json.loads(body)["error"]
    # a gzip cut in the middle (the writer is still writing): preparing, and the catalog does not fail
    p = tmp_path / "backtest_runs_shared" / "cards" / "c7_barrier_race" / "1h" / "trades.json.gz"
    raw = p.read_bytes()
    p.write_bytes(raw[: len(raw) // 2])
    j = json.loads(dash._backtest("/api/backtest/summary/cards/c7_barrier_race/1h", root, tmp_path)[2])
    assert "準備中" in j["preparing"] and ("gzip" in j["preparing"] or "大きさ" in j["preparing"])
    c7 = _card_themes(root)["card:c7_barrier_race"]["strategies"][0]
    assert c7["runs"] == [] and {u["variant"]: u["state"] for u in c7["unavailable"]}["1h"] == "preparing"
    # the same size as the manifest says but the stream is cut (the manifest was written from a longer file): still preparing
    row = _row("c7_barrier_race", "1h", None, n_trades=2)
    row["file_bytes"] = {}
    _manifest(tmp_path, [row])
    K._MAN.clear()
    assert "gzip" in K.variant_state(K.manifests(root)[0], K.manifests(root)[0].rows[("c7_barrier_race", "1h")])[1]
    # writing finishes: it shows up again
    p.write_bytes(raw)
    _manifest(tmp_path, [_row("c7_barrier_race", "1h", p.parent, n_trades=2)])
    assert _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["runs"][0]["variant"] == "1h"
    assert json.loads(dash._backtest("/api/backtest/summary/cards/c7_barrier_race/1h", root, tmp_path)[2])["stats"]["n"] == 2


def test_manifest_is_read_again_when_it_changes_and_a_half_written_one_keeps_the_last(tmp_path):
    t0, root = _cards_world(tmp_path)
    assert len(_card_themes(root)["card:c7_barrier_race"]["strategies"][0]["runs"]) == 1
    d = _write_card(tmp_path, "c7_barrier_race", "1d", t0, [(t0 + 600, t0 + 1200, 110, 120, 1, 1.0)])
    rows = [_row("c7_barrier_race", "1h", tmp_path / "backtest_runs_shared/cards/c7_barrier_race/1h", n_trades=2), _row("c7_barrier_race", "1d", d, n_trades=1)]
    p = _manifest(tmp_path, rows)
    assert [r["variant"] for r in _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["runs"]] == ["1d", "1h"] or \
        {r["variant"] for r in _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["runs"]} == {"1h", "1d"}  # a new variant appears without a restart
    p.write_text('{"version": 1, "variants": [{"card": "c7_bar', encoding="utf-8")  # cut in the middle
    cat = C.catalog(root)
    assert cat["card_notes"] and cat["n_card_runs"] == 2  # the last good read is used and the page is told
    p.write_text("not json at all", encoding="utf-8")
    assert C.catalog(root)["n_card_runs"] == 2


def test_card_trades_are_cut_at_the_seal_boundary_like_a_run(tmp_path):
    dash = _dash()
    _seal(tmp_path)
    start = BOUNDARY - 3600
    _csv(tmp_path / FXDIR / "candles_1m_2023.csv.gz", [(start + i * 60, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(180)], header=FXCOLS)
    trades = [(start + 60, start + 600, 100, 110, 1, 10.0), (start + 700, BOUNDARY - 60, 110, 105, -1, 5.0),
              (BOUNDARY - 30, BOUNDARY, 105, 120, 1, 7.0), (BOUNDARY + 60, BOUNDARY + 600, 120, 130, 1, 100.0)]
    d = _write_card(tmp_path, "c8_session_mean_revert", "jst_day", start, trades)
    # the card's own period reaches past the boundary (as a bug in the exporter or a later export would make it)
    _manifest(tmp_path, [_row("c8_session_mean_revert", "jst_day", d, period=(_iso_z(start), _iso_z(BOUNDARY + 3600)), n_trades=4)])
    root = str(tmp_path / "backtest_runs_shared")
    s = C.run_summary(root, "cards/c8_session_mean_revert/jst_day", tmp_path)
    assert s["stats"]["n"] == 2 and s["stats"]["total_bp"] == 15.0  # the trade that exits AT the boundary and the one after it are not shown
    ch = C.run_chart(root, "cards/c8_session_mean_revert/jst_day", root=tmp_path, from_s=start, to_s=BOUNDARY + 7200)
    assert [t["xt"] for t in ch["trades"]] == [start + 600, BOUNDARY - 60] and ch["trades_total"] == 2
    assert all(p[0] < BOUNDARY for p in ch["pnl"]) and all(b[0] < BOUNDARY for b in ch["bars"])
    # a card variant wholly after the boundary shows no number
    d2 = _write_card(tmp_path, "c8_session_mean_revert", "bf_maint", start, [(BOUNDARY + 60, BOUNDARY + 600, 1, 2, 1, 1.0)])
    _manifest(tmp_path, [_row("c8_session_mean_revert", "bf_maint", d2, period=(_iso_z(BOUNDARY + 60), _iso_z(BOUNDARY + 3600)), n_trades=1)])
    j = json.loads(dash._backtest("/api/backtest/summary/cards/c8_session_mean_revert/bf_maint", root, tmp_path)[2])
    assert j["after_seal"] and "stats" not in j
    assert dash._backtest("/api/backtest/chart/cards/c8_session_mean_revert/bf_maint", root, tmp_path)[0] == 400


def _iso_z(s):
    return datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_card_summary_holds_bp_only_the_checks_and_the_price_of_the_ledgers_instrument(tmp_path):
    t0, root = _cards_world(tmp_path)
    s = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    assert s["pnl_derived"] is True and s["currency"] is None and s["stats"]["total"] is None and s["stats"]["total_bp"] == pytest.approx(167.8)
    assert s["instrument"] == "FX_BTC_JPY" and s["price"]["available"] and s["price"]["same_source"] and s["price"]["label"] == "bitFlyer FX_BTC_JPY"
    c = s["card"]
    assert c["verified_items"] == ["daily_csv_sha256"] and c["not_verified"] == ["取引数は照合していない"] and c["n_trades_manifest"] == 2
    assert c["card_title"] == T.card_theme("c7_barrier_race")["title"] and "FX_BTC_JPY" in c["instrument_source"] + c["instrument"]
    ch = C.run_chart(root, "cards/c7_barrier_race/1h", root=tmp_path)
    assert ch["pnl_derived"] and len(ch["trades"]) == 2 and ch["trades"][0]["pnl"] is None and ch["trades"][0]["bp"] == 90.9
    assert [p[2] for p in ch["pnl"]][-1] == pytest.approx(167.8)
    # the price directory the card read is not the store's: say so instead of claiming the same source
    d = _write_card(tmp_path, "c7_barrier_race", "1h", t0, [(t0 + 600, t0 + 1200, 110, 120, 1, 90.9)], prov_extra={"data_dirs_read": ["backtest_data/other"]})
    _manifest(tmp_path, [_row("c7_barrier_race", "1h", d, n_trades=1)])
    K._PROV.clear(); C._TRADES.clear()
    s2 = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    assert s2["price"]["same_source"] is False and "data_dirs_read" in s2["price"]["note"]


def test_card_with_an_instrument_the_ledger_has_no_store_for_shows_the_cumulative_profit_only(tmp_path, monkeypatch):
    t0, root = _cards_world(tmp_path)
    monkeypatch.setitem(T.card_theme("c7_barrier_race"), "instrument", "USDJPY")
    s = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    assert not s["price"]["available"] and "MARKETS" in s["price"]["reason"] and s["stats"]["n"] == 2
    ch = C.run_chart(root, "cards/c7_barrier_race/1h", root=tmp_path)
    assert ch["bars"] == [] and len(ch["pnl"]) >= 2


def test_daily_csv_and_the_trades_of_every_exported_variant_agree_on_the_total():
    """sum(daily.csv pnl_bp) = sum(trades pnl_bp). The trades' pnl_bp are rounded to 4 decimals when written (compact(x, 4) in
    export_card_trades.py), so the two sums can differ by at most n * 0.00005 bp; the per-day split differs by construction (daily.csv
    books a decision's profit on the decision's day, a trade books its whole profit at its exit)."""
    if not CARD_MANIFEST.is_file():
        pytest.skip("no cards manifest in this checkout")
    rd = str(REPO / "backtest_runs_shared")
    n_checked = 0
    for th in C.catalog(rd)["themes"]:
        for st in th["strategies"] if th.get("is_card") else []:
            for r in st["runs"]:
                ref = K.resolve(rd, r["run_id"])
                ts = C.load_trades(str(ref.dir))
                assert ts.n == ref.row["n_trades"], r["run_id"]
                assert abs(float(ts.cum_bp[-1]) - K.daily_sum_bp(ref)) <= ts.n * 0.00005 + 1e-6, r["run_id"]
                n_checked += 1
    assert n_checked >= 1


def test_card_page_and_script_carry_the_card_pieces():
    dash = _dash()
    assert 'id="bt-card-note"' in dash.PAGE
    js = (Path(C.STATIC_DIR) / "backtest_tab.js").read_text(encoding="utf-8")
    assert "選べない変種" in js and "対象外" in js and "照合の範囲" in js and "isCard" in js


# ---- critic fixes: bp note, headline source, waiting state, provenance display_ok, zlib, wording -----------------
@pytest.mark.skipif(not CARD_MANIFEST.is_file(), reason="no cards manifest in this checkout")
@pytest.mark.parametrize("cid,pid", [("c4_owner_matilda_range", "core_body"), ("c5_tokyo_fix_momentum", "default")])
def test_card_headline_equals_the_researchs_numbers(cid, pid):
    rd = str(REPO / "backtest_runs_shared")
    ref = K.resolve(rd, f"cards/{cid}/{pid}")
    git = ref and K.provenance(ref)["checks"]
    s = C.run_summary(rd, f"cards/{cid}/{pid}", REPO)
    st, hl = s["stats"], s["card"]["headline"]
    assert st["n"] == git["extra.trades"]["git"]["n"] and st["win_rate"] == git["extra.trades"]["git"]["win_rate"]
    assert st["max_dd_bp"] == pytest.approx(git["extra.drawdown"]["git"]["max_bp"], rel=1e-9)
    assert "研究の値" in hl["win_rate"] and "daily.csv" in hl["max_dd"] and "研究と同じ定義" in hl["max_dd"]
    assert s["card"]["bp_note"].startswith("bp = 持っていた間の 1 決定ごとの値動きの和") and "建値と決済値の比ではない" in s["card"]["bp_note"]


def test_headline_without_the_researchs_values_is_computed_and_says_so(tmp_path):
    t0, root = _cards_world(tmp_path)  # provenance has no checks
    s = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    hl = s["card"]["headline"]
    assert "丸め" in hl["win_rate"] and "daily.csv" in hl["max_dd"]
    assert s["stats"]["max_dd_bp"] == 0.0 and s["stats"]["win_rate"] == 1.0
    d = tmp_path / "backtest_runs_shared/cards/c7_barrier_race/1h"
    prov = json.loads((d / "provenance.json").read_text())
    prov["checks"] = {"extra.trades": {"git": {"n": 2, "win_rate": 0.5}}, "extra.drawdown": {"git": {"max_bp": 1.0}}}
    (d / "provenance.json").write_text(json.dumps(prov))
    _manifest(tmp_path, [_row("c7_barrier_race", "1h", d, n_trades=2)])
    s = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    assert s["stats"]["win_rate"] == 0.5 and "研究の値" in s["card"]["headline"]["win_rate"] and s["stats"]["wins"] == 1


def test_limit_variant_bp_note_differs_and_every_card_trade_explains_bp(tmp_path):
    t0, root = _cards_world(tmp_path)
    ref = K.resolve(root, "cards/c7_barrier_race/1h")
    assert K.info(ref)["bp_note"] == T.BP_NOTE
    ref.variant = "limit_v37_good"
    assert K.info(ref)["bp_note"] == T.BP_NOTE_LIMIT and "段の約定の平均" in T.BP_NOTE_LIMIT
    js = (Path(C.STATIC_DIR) / "backtest_tab.js").read_text(encoding="utf-8")
    assert js.count("bp_note") >= 4 and "bt-bpnote" in js and "bt-card-bpnote" in js  # legend, tooltip, card note


def test_waiting_variants_are_apart_from_failures_and_provenance_display_ok_false_blocks(tmp_path):
    dash = _dash()
    t0, root = _cards_world(tmp_path)
    c7 = _card_themes(root)["card:c7_barrier_race"]["strategies"][0]
    un = {u["variant"]: u for u in c7["unavailable"]}
    assert un["1d"]["state_label"] == K.WAITING == "測定待ち(書き出し・照合がまだ)" and un["1d"]["reason"] == ""
    d = tmp_path / "backtest_runs_shared/cards/c7_barrier_race/1d"
    _write_card(tmp_path, "c7_barrier_race", "1d", t0, [(t0 + 600, t0 + 1200, 110, 120, 1, 1.0)])
    _manifest(tmp_path, [_row("c7_barrier_race", "1h", tmp_path / "backtest_runs_shared/cards/c7_barrier_race/1h", n_trades=2),
                         _row("c7_barrier_race", "1d", d, n_trades=1, ok=True), _row("c7_barrier_race", "1w", ok=False, reason="照合が一致しない: daily_csv_sha256", status="exported")])
    c7 = _card_themes(root)["card:c7_barrier_race"]["strategies"][0]
    un = {u["variant"]: u for u in c7["unavailable"]}
    assert un["1w"]["state"] == "blocked" and "照合が一致しない" in un["1w"]["reason"] and un["1w"]["state_label"] != K.WAITING
    assert {r["variant"] for r in c7["runs"]} == {"1h", "1d"}
    pj = d / "provenance.json"
    prov = json.loads(pj.read_text())
    prov["display_ok"] = False
    pj.write_text(json.dumps(prov))
    _manifest(tmp_path, [_row("c7_barrier_race", "1d", d, n_trades=1)])
    st = _card_themes(root)["card:c7_barrier_race"]["strategies"][0]["unavailable"][0]
    assert st["state"] == "blocked" and "display_ok" in st["reason"]
    assert dash._backtest("/api/backtest/summary/cards/c7_barrier_race/1d", root, tmp_path)[0] == 404


def test_card_loads_its_gz_even_when_a_plain_trades_json_sits_beside_it(tmp_path):
    t0, root = _cards_world(tmp_path)
    d = tmp_path / "backtest_runs_shared/cards/c7_barrier_race/1h"
    (d / "trades.json").write_text(json.dumps({"version": 1, "t_unit": "ns", "entry_t_ns": [t0 * NS], "entry_px": [1], "exit_t_ns": [(t0 + 60) * NS],
                                               "exit_px": [1], "side": [1], "qty": [1], "pnl_bp": [999.0]}))
    s = C.run_summary(root, "cards/c7_barrier_race/1h", tmp_path)
    assert s["stats"]["n"] == 2 and s["stats"]["total_bp"] == pytest.approx(167.8)


def test_zlib_error_while_reading_trades_is_preparing_not_a_500(tmp_path, monkeypatch):
    import zlib
    dash = _dash()
    t0, root = _cards_world(tmp_path)

    def boom(*a, **k):
        raise zlib.error("incomplete")
    monkeypatch.setattr(C, "load_trades", boom)
    assert "準備中" in json.loads(dash._backtest("/api/backtest/summary/cards/c7_barrier_race/1h", root, tmp_path)[2])["preparing"]
    assert dash._backtest("/api/backtest/chart/cards/c7_barrier_race/1h", root, tmp_path)[0] == 400


def test_card_descriptions_follow_the_sources_wording():
    assert "比" in T.card_theme("c3_yen_premium_revert")["summary"] and "差" not in T.card_theme("c3_yen_premium_revert")["summary"]
    c = T.CARD_AXES["c2_series"]
    assert "measure/README.md" in c["source"] and "run_v2.py" in c["source"] and "CARD.md" not in c["source"]
    note = c["values"]["c"][1]
    assert "L-570" in note and "以後は測らない" in note and "参考として残す" in note and "食い違う" in note
    lim = T.card_families(T.card_theme("c4_owner_matilda_range"))[2]
    assert any("段の約定の平均" in x and "1 段目" in x and "範囲の外" in x for x in lim["description"]) and len(lim["description"]) <= 6
