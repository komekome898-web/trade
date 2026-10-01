"""D-1 (K1 stage A, 2026-09-27): K1 through the integrated door bot.bt.pipeline -- the "module" strategy
(bot.strategy.k1_wick:pipeline_strategy) and the venue rule market_ref = "last_bar_close" (gate rule I-6: the
order is not held; the venue prices it at the close of the last bar it has seen).

Expected fills are written from the rule text of docs/PHASE2/K1/RESULT.md 1.3-1.4 (the hand scene of
tests/test_k1_wick.py) and from the venue rule (a fill's price = the close of the bar the venue saw at the
fill's time). The origin evidence of the integrated run looks only at the files handed to the run (round 2 of the
env fixes), here a file under a temporary root outside the repository's market folders: the test reads no market
file of the repository (round 1 pointed MARKET_ROOTS at an empty folder; that setting no longer exists)."""
from __future__ import annotations

import os

import pytest

from bot.bt import pipeline as P
from bot.bt.core import CoreEngine, NullAccount, ZeroLatency
from bot.bt.repro.fixed import DeclaredFeeCost
from bot.strategy.k1_wick import PIPELINE_PRODUCT, PIPELINE_RULES, K1WickStrategy, bar_close_venue

NS = 10**9
IV_S = 900
ZERO = {"kind": "constant", "ns": 0}
SCENE_A = [  # tests/test_k1_wick.py SCENE_A (RESULT.md 1.3-1.4)
    (4000, 4001, 3999, 4000.5), (4000, 4002, 3990, 4001), (4001, 4003, 4000, 4002),
    (4002, 4003, 3985, 3989), (3989, 3999, 3988, 3990), (3990, 3991, 3989, 3990.5)]
# (id, side, px, bar index): tests/test_k1_wick.py::test_scene_a_both
SCENE_A_FILLS = [("e1", "buy", 4000.5, 0), ("x2", "sell", 3989.0, 3), ("e3", "sell", 3990.0, 4),
                 ("x4", "buy", 3990.5, 5), ("e5", "buy", 3990.5, 5)]
T0 = 1_483_228_800  # 2017-01-01T00:00:00Z
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "none", "kind": "bar", "symbol": "XBTUSD",
        "asset": "crypto", "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": IV_S, "label": "start", "session": "24x7"}, "key": "start"}  # session: G-4 (2026-10-01)


@pytest.fixture()
def root(tmp_path, monkeypatch):
    (tmp_path / "backtest_data" / "k1").mkdir(parents=True)
    (tmp_path / "prereg.md").write_text("# prereg (test)\n")
    return tmp_path


def write_bars(root, rows) -> str:
    from datetime import datetime, timezone
    lines = ["start_ts,o,h,l,c,vol"]
    for i, (o, h, l, c) in enumerate(rows):
        ts = datetime.fromtimestamp(T0 + i * IV_S, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        lines.append(f"{ts},{o},{h},{l},{c},1.0")
    rel = "backtest_data/k1/bars.csv"
    (root / rel).write_text("\n".join(lines) + "\n")
    return rel


def args(root, datasets, price, strength="both", rules=None, kind="bar", module="bot.strategy.k1_wick"):
    return dict(root=str(root), datasets=datasets,
                instruments=[{"name": "XBTUSD", "price": price, "with": [], "product": dict(PIPELINE_PRODUCT),
                              "rules": dict(PIPELINE_RULES if rules is None else rules)}],
                strategy={"kind": "module", "module": module, "factory": "pipeline_strategy",
                          "params": {"s": "-", "b": "-", "strength": strength}},
                fill={"optimistic": {"tier": 2}, "pessimistic": {"tier": 2}},
                latency={"feed": ZERO, "order": ZERO, "cancel": ZERO, "notice": ZERO},
                costs={"maker_rate": 0, "taker_rate": 0, "spread": 0, "source": "test: 0"},
                account={"currency": "USD", "cash": 1e9, "leverage": 1, "mark": "last_trade", "liquidation": None,
                         "margin_check": "position_only"},
                purpose="研究", prereg="prereg.md")


def fills_by_side(root, plan):
    out = root / "out"
    out.mkdir(exist_ok=True)
    res = P.execute_once(plan, str(out))
    return {side: [(f["order_id"], f["side"], f["px"], (f["t_ns"] // NS - T0) // IV_S - 1, f["liquidity"])
                   for r in res["range"][side].values() for f in r.fills] for side in P.SIDES}, res


def test_scene_a_through_the_integrated_door(root):
    rel = write_bars(root, SCENE_A)
    plan = P.plan_pipeline(**args(root, [{"name": "b", "paths": [rel], "spec": SPEC, "origin": "real"}], "b"))
    got, res = fills_by_side(root, plan)
    want = [(i, s, px, k, "taker") for i, s, px, k in SCENE_A_FILLS]
    assert got == {"optimistic": want, "pessimistic": want}
    trades = res["range"]["pessimistic"]["XBTUSD"].trades
    assert [(t["side"], t["entry_px"], t["exit_px"], t["reason"]) for t in trades] == [
        ("buy", 4000.5, 3989.0, "invalidated"), ("sell", 3990.0, 3990.5, "reversed")]
    assert plan.identity["strategy"]["module_source_sha256"]


def test_without_the_rule_the_fills_move_to_the_next_bar(root):
    # the same scene with market_ref next_bar_open (the gate's rule I-4): the entry of bar 0 is priced at the
    # open of bar 1 (4000), not at bar 0's close (4000.5) -- the test above depends on the new rule
    rel = write_bars(root, SCENE_A)
    plan = P.plan_pipeline(**args(root, [{"name": "b", "paths": [rel], "spec": SPEC, "origin": "real"}], "b",
                                  rules={"market_ref": "next_bar_open"}))
    got, _ = fills_by_side(root, plan)
    assert got["pessimistic"][0][:3] == ("e1", "buy", 4000.0)


def test_random_bars_every_fill_is_the_close_of_the_bar_seen_and_matches_the_core_path(root):
    gen = {"name": "random_walk", "seed": 7, "params": {"kind": "bar", "start_ns": T0 * NS, "step_ns": IV_S * NS,
                                                        "n": 600, "price0": 4000.0, "step_pct": 0.8, "qty": 1.0}}
    a = args(root, [{"name": "g", "generator": gen}], "g")
    a.update(purpose="動作確認", prereg=None)
    plan = P.plan_pipeline(**a)
    out = root / "out"
    out.mkdir()
    res = P.execute_once(plan, str(out))
    events = list(P._generate(gen)[2])
    close_at = {e.received_time_ns: e.close for e in events}
    for side in P.SIDES:
        fills = res["range"][side]["XBTUSD"].fills
        assert len(fills) > 20
        assert all(f["px"] == close_at[f["t_ns"]] for f in fills)  # the rule: the close of the bar seen then
    # the same strategy on the core with the venue model directly (the runner's path): the same fills
    strat = K1WickStrategy("-", "-", "both")
    core = CoreEngine(strat, {"g": events}, bar_close_venue(), ZeroLatency(), DeclaredFeeCost({"taker": 0.0, "maker": 0.0}),
                      NullAccount(), time_span_ns=(events[0].received_time_ns, events[-1].received_time_ns)).run()
    want = [(f.client_order_id, f.side, f.price, f.venue_time_ns) for f in core.fills]
    got = [(f["order_id"], f["side"], f["px"], f["t_ns"]) for f in res["range"]["pessimistic"]["XBTUSD"].fills]
    assert got == want


def test_last_bar_close_only_for_a_bar_instrument(root):
    gen = {"name": "random_walk", "seed": 1, "params": {"kind": "trade", "start_ns": T0 * NS, "step_ns": NS, "n": 20,
                                                        "price0": 100.0, "step_pct": 0.5, "qty": 1.0}}
    a = args(root, [{"name": "g", "generator": gen}], "g")
    a.update(purpose="動作確認", prereg=None)
    with pytest.raises(P.PipelineError, match="I-6"):
        P.plan_pipeline(**a)


def test_module_strategy_is_a_repository_strategy(root):
    rel = write_bars(root, SCENE_A)
    ds = [{"name": "b", "paths": [rel], "spec": SPEC, "origin": "real"}]
    with pytest.raises(P.PipelineError, match="bot.strategy"):
        P.plan_pipeline(**args(root, ds, "b", module="os"))
    a = args(root, ds, "b")
    a["strategy"]["factory"] = "no_such_factory"
    with pytest.raises(P.PipelineError, match="factory"):
        P.plan_pipeline(**a)
    a = args(root, ds, "b")
    a["strategy"]["params"] = {"s": "-", "b": "-", "strength": "sideways"}
    plan = P.plan_pipeline(**a)
    with pytest.raises(P.PipelineError, match="strength"):
        P.execute_once(plan, str(root))


def test_real_data_smoke_run_refuses_a_module_strategy(root):
    rel = write_bars(root, SCENE_A)
    a = args(root, [{"name": "b", "paths": [rel], "spec": SPEC, "origin": "real"}], "b")
    a.update(purpose="動作確認", prereg=None)
    with pytest.raises(P.PipelineError, match="time-only"):
        P.plan_pipeline(**a)


def test_the_integrated_run_names_its_money_by_the_account_currency(root):
    """Round 2 of the env fixes, (d)5 (the root cause of D-4): the integrated run's metrics named the amount
    "pnl_jpy" and the equity "realized_jpy" whatever the account's currency. Now "pnl" / "realized" with the
    currency of the account (USD here)."""
    from bot.bt.report.exports import read_export
    rel = write_bars(root, SCENE_A)
    plan = P.plan_pipeline(**args(root, [{"name": "b", "paths": [rel], "spec": SPEC, "origin": "real"}], "b"))
    out = root / "out"
    out.mkdir()
    P.execute_once(plan, str(out))
    m = read_export(str(out / "metrics.json"))["data"]
    assert "pnl_jpy" not in m and m["pnl"]["currency"] == "USD" and set(m["pnl"]) >= {"realized", "fees"}
    assert "realized_jpy" not in m["equity"] and m["equity"]["currency"] == "USD" and "realized" in m["equity"]


def test_the_stage_a_name_of_the_fill_socket_is_gone():
    """Round 2, (d)4: BarCloseMarketFill (stage A's name, kept in round 1 as an alias of bar_close_venue) was removed;
    tests/test_k1_wick*.py build the fill socket by bar_close_venue."""
    import bot.strategy.k1_wick as K
    assert not hasattr(K, "BarCloseMarketFill") and callable(K.bar_close_venue)
