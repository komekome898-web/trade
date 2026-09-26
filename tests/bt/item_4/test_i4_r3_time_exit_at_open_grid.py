"""Adversarial grid (finishing stage, i4-r2-02): on the time-exit bar b + N the spec model closes at the OPEN.

Rule text (tests/bt/battery/item_4/DEFINITIONS.md R-O1, read as the finishing delegation §1 i4-r2-02 decides):
「始値の出来事(①・②の時間切れ・③)は足の範囲の出来事(④〜⑦)より先」; R-H1「ちょうど足 b + N の始値で taker で
閉じる」; R-H2「その足に待っていた合図は捨てる」; R-H3 is the order INSIDE the range after the open. So on bar b + N:
the position closes at bar b + N's open (taker, R-C1 with zero costs = the open itself), whatever bar b + N's range
reaches afterwards, and a signal or limit pending for that bar is dropped (never executed on that bar).

Grid (the rule's input space, not the implementation's branches): side {long, short} x the open of bar b + N
{between the levels, beyond the stop} x what bar b + N's range reaches {nothing, the stop, the take-profit, both}
x what is pending for bar b + N {nothing, a signal the same way as the position, a CLOSE signal} x execution
{taker, maker} = 2 x 2 x 4 x 3 x 2 = 96 cells. Expected (from the text): exactly one close, on bar 3 (b = 1, N = 2),
at bar 3's open; PnL = (open - 100) x 30 x direction; no fill after it.
Not in the grid: the structural stop on the same bar (R-O1 ① comes first; pinned by the scene set), costs other
than zero (R-C1 is the same formula for every taker close), N other than 2.
The legacy rule set is not tested here (it keeps the old order; tests/bt/compat holds it bit for bit).
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
FLAT = (100.0, 100.0, 100.0, 100.0)


def _bars(side: str, open_at: str, reach: str):
    lng = side == "long"
    if open_at == "between":
        o = 100.0
    else:
        o = 97.0 if lng else 103.0  # beyond the stop 98 (long) / 102 (short)
    hi, lo = max(o, 100.0) + 0.5, min(o, 100.0) - 0.5
    stop_x, tp_x = (97.0, 104.0) if lng else (103.0, 96.0)
    if reach in ("stop", "both"):
        lo, hi = (min(lo, stop_x), hi) if lng else (lo, max(hi, stop_x))
    if reach in ("tp", "both"):
        lo, hi = (lo, max(hi, tp_x)) if lng else (min(lo, tp_x), hi)
    # bar 0: the signal bar (close 100); bar 1: the entry bar (maker: strictly through 100 both ways);
    # bar 2: inside every level; bar 3 = b + N; bar 4: flat
    return [FLAT, (100.0, 100.5, 99.5, 100.0), (100.0, 101.0, 99.5, 100.0), (o, hi, lo, o), FLAT], o


CELLS = list(itertools.product(("long", "short"), ("between", "beyond"), ("none", "stop", "tp", "both"),
                               ("nothing", "same_way", "close"), ("taker", "maker")))


@pytest.mark.parametrize("side,open_at,reach,pending,execution", CELLS)
def test_time_exit_bar_closes_at_its_open(side, open_at, reach, pending, execution):
    bars, o = _bars(side, open_at, reach)
    entry = "BUY" if side == "long" else "SELL"
    signals = {0: entry}
    if pending == "same_way":
        signals[2] = entry
    elif pending == "close":
        signals[2] = "CLOSE"
    cfg = {"initial_equity": 10000.0, "order_notional": 3000.0,
           "costs": {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
           "execution": execution, "maker_timeout_bars": 3, "allow_short": True, "swap_daily_pct": 0.0,
           "bar_seconds": 60.0, "stop_loss_pct": 2.0, "take_profit_pct": 3.0, "max_hold_bars": 2,
           "exit_execution": "signal", "maker_tp_pct": None, "entry_mask": None, "entry_sides": "both",
           "stop_mode": "fixed", "stop_window_bars": None}
    rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in bars]
    ev = bar_events(rows, [T0 + i * 60 * NS for i in range(len(rows))], 60 * NS)
    res = run_bars(ev, lambda n: signals.get(n - 1), options_from_mapping(cfg), "spec", start=0)
    opens = [f for f in res.fills if f["side"].startswith("OPEN_")]
    closes = [f for f in res.fills if f["side"].startswith("CLOSE_")]
    assert [(f["bar"], f["price"]) for f in opens] == [(1, 100.0)], res.fills
    assert [(f["bar"], f["price"]) for f in closes] == [(3, o)], res.fills
    d = 1.0 if side == "long" else -1.0
    assert res.trade_pnls == [pytest.approx((o - 100.0) * 30.0 * d)]
    assert all(f["bar"] <= 3 for f in res.fills), res.fills
    assert res.missed_fills == 0  # a limit dropped by the time exit is not a missed fill (R-M5)
