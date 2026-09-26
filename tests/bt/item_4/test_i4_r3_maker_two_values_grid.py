"""Adversarial grid (finishing stage, i4-r2-08, the spec side): the two maker values the lead decided
(finishing delegation §1 i4-r2-08, verbatim): 「マスク False の合図は指値を置かない(取り逃しに数えない)」
「同じ向きの合図は指値を置き直さない(古い指値を残す)」, with R-M1 (limit at the signal bar's close, strict
pass-through, not on the bar it was placed), R-M2 (lifetime: cancelled on bar p + L, one missed fill), R-M3 (an
opposite signal that PLACES a new limit ends the old one: one missed fill) and R-E2 (the mask of the signal bar).

Grid: the mask of the tested signal's bar {True, False} x what is pending when it comes {nothing, a limit the same
way, a limit the opposite way} x bar 2 {strictly through 100 both ways, flat} x lifetime {1, 3} = 24 cells, flat
account, maker execution, shorts allowed. Bar 0 places the pending limit (mask True), bar 1 is flat at 100 (no limit
can pass through it: a buy and a sell limit at 100 both need a strict pass), the tested BUY comes at bar 1's close.
`expected()` walks the rule text above bar by bar (it never calls the engine).
Not in the grid: signals that close a position (R-E3: the mask never stops an exit), the long / short entry filter
(R-E1: the lead's text names the mask only -- a question to the lead), limits at other prices.
The legacy rule set is not tested here (it keeps the old computation; tests/bt/compat).
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
FLAT = (100.0, 100.0, 100.0, 100.0)
THROUGH = (100.0, 100.5, 99.5, 100.0)


def expected(bars, signals, mask, life):
    """The rule text, bar by bar: (fills [(bar, side, price)], missed)."""
    pend = None  # (side, price, placed bar)
    pos = 0
    fills, missed = [], 0
    for j, (o, h, l, c) in enumerate(bars):
        if pend is not None and j > pend[2]:
            side, px, p = pend
            through = l < px if side == "BUY" else h > px
            if through:
                fills.append((j, "OPEN_LONG" if side == "BUY" else "OPEN_SHORT", px))
                pos = 1 if side == "BUY" else -1
                pend = None
            elif j - p >= life:
                missed += 1
                pend = None
        sig = signals.get(j)
        if sig is None or pos != 0:
            continue
        if not mask[j]:
            continue  # the lead's value 1: no limit, no missed fill
        if pend is not None and pend[0] == sig:
            continue  # the lead's value 2: the old limit stays
        if pend is not None:
            missed += 1  # R-M3
        pend = (sig, c, j)
    return fills, missed


CELLS = list(itertools.product((True, False), ("nothing", "same", "opposite"), ("through", "flat"), (1, 3)))


@pytest.mark.parametrize("m,pending,bar2,life", CELLS)
def test_maker_signal_mask_and_same_way(m, pending, bar2, life):
    bars = [FLAT, FLAT, THROUGH if bar2 == "through" else FLAT, FLAT, FLAT, FLAT, FLAT]
    signals = {1: "BUY"}
    if pending == "same":
        signals[0] = "BUY"
    elif pending == "opposite":
        signals[0] = "SELL"
    mask = [True, m, True, True, True, True, True]
    cfg = {"initial_equity": 10000.0, "order_notional": 3000.0,
           "costs": {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
           "execution": "maker", "maker_timeout_bars": life, "allow_short": True, "swap_daily_pct": 0.0,
           "bar_seconds": 60.0, "stop_loss_pct": None, "take_profit_pct": None, "max_hold_bars": None,
           "exit_execution": "signal", "maker_tp_pct": None, "entry_mask": mask, "entry_sides": "both",
           "stop_mode": "fixed", "stop_window_bars": None}
    rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in bars]
    ev = bar_events(rows, [T0 + i * 60 * NS for i in range(len(rows))], 60 * NS)
    res = run_bars(ev, lambda n: signals.get(n - 1), options_from_mapping(cfg), "spec", start=0)
    want_fills, want_missed = expected(bars, signals, mask, life)
    assert [(f["bar"], f["side"], f["price"]) for f in res.fills] == want_fills
    assert res.missed_fills == want_missed
