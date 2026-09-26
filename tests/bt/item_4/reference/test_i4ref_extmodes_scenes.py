"""Known-answer scenes for the bar reference (bot.bt.reference.bar_sim).

Expected values are worked out by hand in the comments from SPEC.md
section 3; none is read back from a run.
"""
from __future__ import annotations

from fractions import Fraction as F

import pytest

from ext_bar_modes import Signal, make_bar, run_bars

H = 3_600_000_000_000


def bars(*ohlc):
    return [make_bar(i * H, *b) for i, b in enumerate(ohlc)]


def P(**kw):
    p = dict(qty=1, initial_cash=0, taker_rate=0, maker_rate=0, limit_cross="strict",
             stop_trigger="touch", stop_fill="level", tp_fee="maker", exits_from_entry_bar=True,
             limit_valid_bars=1, mask=None, mask_applies_to="signal_bar", entry_sides="both",
             max_hold_bars=None, close_at_end=False)
    p.update(kw)
    return p


FLAT = (100, 101, 99, 100)


def test_next_open_taker_entry_and_max_hold_exit_at_open():
    # signal long at bar 0 -> entry at open of bar 1 = 102 (taker 0.001: 0.102).
    # max_hold 2 -> exit at open of bar 1+2 = 3 = 106 (fee 0.106).
    # pnl = 106 - 102 - 0.102 - 0.106 = 3.792
    b = bars(FLAT, (102, 103, 101, 102), (104, 105, 103, 104), (106, 107, 105, 106), (108, 109, 107, 108))
    s = [Signal("long"), None, None, None, None]
    r = run_bars(b, s, **P(taker_rate="0.001", max_hold_bars=2))
    (t,) = r.trades
    assert (t.entry_bar, t.entry_price, t.exit_bar, t.exit_price, t.reason) == (1, 102, 3, 106, "max_hold")
    assert t.pnl == F("3.792")
    # equity at bar 2 close: open trade marked at 104: 104-102-0.102 = 1.898
    assert r.equity[2] == F("1.898") and r.equity[3] == F("3.792")


def test_stop_priority_when_bar_reaches_both():
    # entry long @100 at bar 1 open; sl 95, tp 105. bar 2 h106 l94 -> stop @95.
    b = bars(FLAT, FLAT, (100, 106, 94, 100), FLAT)
    r = run_bars(b, [Signal("long", sl_dist=5, tp_dist=5), None, None, None], **P())
    (t,) = r.trades
    assert (t.exit_bar, t.exit_price, t.reason, t.pnl) == (2, 95, "stop", -5)


def test_short_take_profit_and_stop_levels_mirror():
    # short @100 at bar 1: sl 104, tp 97. bar 2 low 96 -> tp @97 (strict: 96 < 97).
    b = bars(FLAT, FLAT, (100, 101, 96, 98), FLAT)
    r = run_bars(b, [Signal("short", sl_dist=4, tp_dist=3), None, None, None], **P())
    (t,) = r.trades
    assert (t.sl, t.tp, t.exit_price, t.reason, t.pnl) == (104, 97, 97, "take_profit", 3)


@pytest.mark.parametrize("cross,filled", [("strict", False), ("touch", True)])
def test_limit_entry_strict_vs_touch_and_missed_fill(cross, filled):
    # long limit 99 decided at bar 0, live on bar 1 only; bar 1 low is exactly 99.
    b = bars(FLAT, (100, 101, 99, 100), FLAT)
    r = run_bars(b, [Signal("long", limit=99), None, None], **P(limit_cross=cross))
    if filled:
        assert r.open_trade.entry_price == 99 and r.open_trade.entry_liquidity == "maker"
        assert r.missed_fills == 0
    else:
        assert r.open_trade is None and r.missed_fills == 1


def test_limit_never_fills_at_a_better_price_than_its_own():
    # long limit 100; bar 1 opens at 95 (below the limit). Fill is at 100, not 95.
    b = bars(FLAT, (95, 96, 94, 95), FLAT)
    r = run_bars(b, [Signal("long", limit=100), None, None], **P())
    assert r.open_trade.entry_price == 100


def test_take_profit_never_fills_at_a_better_open():
    # long @100 (bar 1), tp 103. bar 2 opens at 110 -> exit at 103, not 110.
    b = bars(FLAT, FLAT, (110, 111, 109, 110))
    r = run_bars(b, [Signal("long", tp_dist=3), None, None], **P())
    assert r.trades[0].exit_price == 103


@pytest.mark.parametrize("mode,px", [("level", 95), ("worse_of_level_and_open", 90)])
def test_gap_through_stop(mode, px):
    # long @100 at bar 1, sl 95. bar 2 opens at 90 (gap below the stop).
    b = bars(FLAT, FLAT, (90, 91, 89, 90))
    r = run_bars(b, [Signal("long", sl_dist=5), None, None], **P(stop_fill=mode))
    assert r.trades[0].exit_price == px


@pytest.mark.parametrize("flag,exit_bar", [(True, 1), (False, 2)])
def test_exits_from_entry_bar(flag, exit_bar):
    # long @100 at bar 1 open; bar 1 low 94 reaches sl 95; bar 2 low 94 too.
    b = bars(FLAT, (100, 101, 94, 100), (100, 101, 94, 100))
    r = run_bars(b, [Signal("long", sl_dist=5), None, None], **P(exits_from_entry_bar=flag))
    assert r.trades[0].exit_bar == exit_bar


def test_entry_sides_and_mask():
    b = bars(FLAT, FLAT, FLAT, FLAT)
    sigs = [Signal("short"), None, Signal("long"), None]
    r = run_bars(b, sigs, **P(entry_sides="long", close_at_end=True))
    assert r.ignored_signals == [(0, "side_filtered")]
    assert [t.signal_bar for t in r.trades] == [2]
    m = [True, True, False, True]
    r2 = run_bars(b, [None, None, Signal("long"), None], **P(mask=m))
    assert r2.ignored_signals == [(2, "mask_at_signal_bar")] and r2.open_trade is None
    r3 = run_bars(b, [None, Signal("long"), None, None], **P(mask=m, mask_applies_to="fill_bar"))
    assert r3.ignored_signals == [(1, "mask_at_fill_bar")] and r3.open_trade is None


def test_signals_ignored_while_in_position_or_pending_and_at_last_bar():
    b = bars(FLAT, FLAT, FLAT, FLAT)
    sigs = [Signal("long", limit=50), Signal("long"), Signal("long"), Signal("long")]
    r = run_bars(b, sigs, **P(limit_valid_bars=1))
    # bar0 limit 50 pending (never fills, missed at bar 1); bar1 signal is
    # decided after the missed limit clears at bar 1 -> accepted, fills bar 2;
    # bar2 in_position; bar3 last bar (also in_position, checked first)
    assert r.missed_fills == 1
    assert r.ignored_signals == [(2, "in_position"), (3, "in_position")]
    r2 = run_bars(b, [None, None, None, Signal("long")], **P())
    assert r2.ignored_signals == [(3, "no_next_bar")]


def test_limit_window_cut_by_end_is_not_counted_missed():
    b = bars(FLAT, FLAT)
    r = run_bars(b, [Signal("long", limit=50), None], **P(limit_valid_bars=3))
    assert r.missed_fills == 0 and r.ignored_signals == [(0, "window_cut_by_end")]


def test_close_at_end_and_equity_identity():
    # long @100 bar1, bar 2 close 104 -> close_at_end exit 104, pnl 4 (no fees)
    b = bars(FLAT, FLAT, (100, 105, 99, 104))
    r = run_bars(b, [Signal("long"), None, None], **P(close_at_end=True, initial_cash=1000))
    assert r.trades[0].reason == "end" and r.equity[-1] == 1004


def test_required_parameters_have_no_defaults():
    b = bars(FLAT)
    p = P()
    for k in list(p):
        q = dict(p)
        del q[k]
        with pytest.raises(TypeError):
            run_bars(b, [None], **q)


@pytest.mark.parametrize("tp_fee,fee", [("maker", "-0.0206"), ("taker", "0.103")])
def test_take_profit_fee_side(tp_fee, fee):
    # long @100 at bar 1 (taker 0.001 -> 0.1), tp 103 hit on bar 2.
    # exit fee: maker -0.0002*103 = -0.0206 or taker 0.001*103 = 0.103.
    b = bars(FLAT, FLAT, (100, 104, 99, 100))
    r = run_bars(b, [Signal("long", tp_dist=3), None, None],
                 **P(taker_rate="0.001", maker_rate="-0.0002", tp_fee=tp_fee))
    t = r.trades[0]
    assert t.exit_fee == F(fee) and t.pnl == 3 - F("0.1") - F(fee)
