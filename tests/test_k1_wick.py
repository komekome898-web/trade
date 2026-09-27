"""K1 as a strategy of the new environment (src/bot/strategy/k1_wick.py, stage A of
L-479): small hand-computed scenes from the rule text of docs/PHASE2/K1/RESULT.md
1.3 (signal) and 1.4 (position machine), run on the core with the bar-close fill
socket. Every expected fill is derived in the comments from the rule text, not
from the old script."""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, CoreEngine, NullAccount, ZeroLatency
from bot.bt.repro.fixed import DeclaredFeeCost
from bot.bt.report.trades import round_trips
from bot.strategy.k1_wick import (INVALIDATED, OPPOSITE_WEAK, REVERSED, BarCloseMarketFill, K1Error, K1WickStrategy,
                                  gate_label, gates, signal_of_bar)

NS = 10**9
IV = 900 * NS


def bars(rows):
    return [BarEvent(received_time_ns=(i + 1) * IV, start_time_ns=i * IV, open=o, high=h, low=l, close=c, volume=1.0)
            for i, (o, h, l, c) in enumerate(rows)]


def run(rows, s="-", b="-", strength="both"):
    ev = bars(rows)
    strat = K1WickStrategy(s, b, strength)
    res = CoreEngine(strat, {"bars": ev}, BarCloseMarketFill(), ZeroLatency(), DeclaredFeeCost({"taker": 0.0, "maker": 0.0}),
                     NullAccount(), time_span_ns=(ev[0].received_time_ns, ev[-1].received_time_ns)).run()
    fills = [(f.client_order_id, f.side, f.price, f.venue_time_ns // IV - 1) for f in res.fills]  # (id, side, px, bar index)
    trades = round_trips([{"order_id": f.client_order_id, "t_ns": f.venue_time_ns, "side": f.side, "px": f.price,
                           "qty": f.size, "fee": f.fee, "liquidity": f.liquidity} for f in res.fills], strat.exit_reasons)
    return fills, trades, strat


def test_thirteen_gates():
    assert [gate_label(s, b) for s, b in gates()] == [
        "soff/b24", "soff/b40", "s-/b-", "s-/b24", "s-/b40", "s10/b-", "s10/b24", "s10/b40",
        "s19/b-", "s19/b24", "s19/b40", "s30/b-", "s30/b40"]
    with pytest.raises(K1Error):
        K1WickStrategy("30", "24", "both")  # s > b: the same rule as (off, 24)
    with pytest.raises(K1Error):
        K1WickStrategy("off", "-", "both")  # empty condition


def test_signal_rule_text():
    # 1.3: bullish bar, top = h - c = 0.5, under = o - l = 1; int(0) < int(1) -> buy, w = 1, lc = l
    assert signal_of_bar(4000, 4001, 3999, 4000.5, "-", "-") == (1, 3999.0, 1, "strong")
    # equal after int(): no signal (bar colour kept)
    assert signal_of_bar(4001, 4003, 4000, 4002, "-", "-") == (0, 0.0, 1, "")
    # bearish bar: top = h - o = 1, under = c - l = 4 -> buy candidate, w = 4 < body 13 -> small branch fails; b=- -> none
    assert signal_of_bar(4002, 4003, 3985, 3989, "-", "-") == (0, 0.0, -1, "")
    # the same bar with b=24: wbp = 4 / 3989 * 1e4 = 10.03 < 24 -> still none; with s=off, b=- refused above
    assert signal_of_bar(4002, 4003, 3985, 3989, "-", "24") == (0, 0.0, -1, "")
    # big branch skips the body condition: bearish, top = 1, under = 30 (w = 30 >= body 20): wbp = 30/3970*1e4 = 75.6 >= 24
    assert signal_of_bar(4000, 4001, 3940, 3970, "off", "24") == (1, 3940.0, -1, "weak")
    # small branch with a minimum: w = 10, wbp = 10/4001*1e4 = 24.99 -> s=19 passes, s=30 fails
    assert signal_of_bar(4000, 4002, 3990, 4001, "19", "-") == (1, 3990.0, 1, "strong")
    assert signal_of_bar(4000, 4002, 3990, 4001, "30", "-") == (0, 0.0, 1, "")
    # doji: no signal
    assert signal_of_bar(4000, 4005, 3995, 4000, "-", "-") == (0, 0.0, 0, "")


SCENE_A = [
    (4000, 4001, 3999, 4000.5),  # 0: buy strong (see test_signal_rule_text) -> open long at 4000.5, lc 3999
    (4000, 4002, 3990, 4001),    # 1: buy strong, same direction -> lcline = 3990 only
    (4001, 4003, 4000, 4002),    # 2: no signal; bullish = same colour as the position -> invalidation not looked at
    (4002, 4003, 3985, 3989),    # 3: no signal; bearish = opposite colour; close 3989 <= 3990 -> invalidated at 3989
    (3989, 3999, 3988, 3990),    # 4: bullish, top 9 > under 1 -> sell weak; no position -> open short at 3990, lc 3999
    (3990, 3991, 3989, 3990.5),  # 5: bullish, top 0.5 / under 1 -> buy strong; opposite -> close (reversed) and re-open long
]


def test_scene_a_both():
    fills, trades, strat = run(SCENE_A)
    assert fills == [("e1", "buy", 4000.5, 0), ("x2", "sell", 3989.0, 3), ("e3", "sell", 3990.0, 4),
                     ("x4", "buy", 3990.5, 5), ("e5", "buy", 3990.5, 5)]
    assert [(t["side"], t["entry_px"], t["exit_px"], t["reason"]) for t in trades] == [
        ("buy", 4000.5, 3989.0, INVALIDATED), ("sell", 3990.0, 3990.5, REVERSED)]
    assert strat.pos == 1 and strat.lcline == 3989.0  # bar 5's low
    assert strat.exit_reasons == {"x2": INVALIDATED, "x4": REVERSED}


def test_scene_a_strong_only():
    # keep=strong: bar 4's weak sell is "no signal"; it is bullish = same colour as no position -> nothing;
    # bar 5's buy strong finds no position -> open long. Only one trade (the invalidation).
    fills, trades, _ = run(SCENE_A, strength="strong")
    assert fills == [("e1", "buy", 4000.5, 0), ("x2", "sell", 3989.0, 3), ("e3", "buy", 3990.5, 5)]
    assert [t["reason"] for t in trades] == [INVALIDATED]


def test_scene_a_weak_only():
    # keep=weak: bars 0, 1, 5 (strong) are "no signal"; bar 4's weak sell opens short at 3990 (lc 3999);
    # bar 5 (bullish = opposite colour of a short): close 3990.5 >= 3999? no -> stays short.
    fills, trades, strat = run(SCENE_A, strength="weak")
    assert fills == [("e1", "sell", 3990.0, 4)]
    assert trades == [] and strat.pos == -1


def test_opposite_weak_closes_without_reentry():
    rows = [
        (4000, 4001, 3999, 4000.5),  # buy strong -> long at 4000.5
        (4010, 4020, 4009, 4011),    # bullish, top 9 / under 1 -> sell WEAK; opposite -> close (opposite_weak), no re-entry
        (4011, 4012, 4010, 4011.5),  # buy strong (top .5 / under 1) -> open long again
    ]
    fills, trades, _ = run(rows)
    assert fills == [("e1", "buy", 4000.5, 0), ("x2", "sell", 4011.0, 1), ("e3", "buy", 4011.5, 2)]
    assert [t["reason"] for t in trades] == [OPPOSITE_WEAK]


def test_invalidation_uses_updated_line_and_only_on_opposite_colour():
    rows = [
        (4000, 4001, 3990, 4000.5),  # buy strong, lc = 3990 -> long at 4000.5
        (4000, 4002, 3995, 4001),    # buy strong (under 5 > top 1, w 5 > body 1): same direction -> lcline = 3995
        (4001, 4002, 3993, 4001.5),  # bullish: top .5 / under 8 -> buy strong again -> lcline = 3993 (close 4001.5 not below)
        (4001.5, 4002, 3993.5, 3994),  # bearish, top .5 / under .5 -> equal -> none; opposite colour, close 3994 > 3993 -> NOT invalidated
        (3994, 3994.5, 3992, 3992.5),  # bearish, top .5 / under .5 -> equal -> none; close 3992.5 <= 3993 -> invalidated
    ]
    fills, trades, _ = run(rows)
    assert fills == [("e1", "buy", 4000.5, 0), ("x2", "sell", 3992.5, 4)]
    assert [t["reason"] for t in trades] == [INVALIDATED]


def test_gate_branches_change_which_bars_signal():
    # bar with a long wick but a longer body: only the big branch (b) takes it
    row = (4000, 4001, 3940, 3970)  # bearish, top 1 / under 30, body 30: small branch needs w > body -> 30 > 30 false
    assert signal_of_bar(*row, "-", "-") == (0, 0.0, -1, "")
    assert signal_of_bar(*row, "-", "24")[0] == 1  # wbp = 30 / 3970 * 1e4 = 75.6 >= 24 -> buy (weak: bearish bar)
    assert signal_of_bar(*row, "off", "40")[0] == 1
    assert signal_of_bar(*row, "10", "-") == (0, 0.0, -1, "")
