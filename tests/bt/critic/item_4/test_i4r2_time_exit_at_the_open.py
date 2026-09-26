"""Item 4 critic, round 2 (i4-r2-02): on the time-exit bar the spec model must close at the OPEN.

Requirement I4-13: 「ポジションが max_hold_bars 本保持されたら、ちょうど bar entry_bar + max_hold_bars の始値で
taker 決済されるか」. The scene set's own principle R-O1: 「始値の出来事(①・②の時間切れ・③)は足の範囲の出来事
(④〜⑦)より先: 足 j の始値は足 j の範囲より前に起きる」. R-H3 (「同じ足 b + N で先に見るのは逆指値だけ」) puts a
range event (the fixed stop, reached somewhere inside bar b+N) BEFORE the time exit that happens at bar b+N's
open. When the open is above the stop level the stop cannot have triggered before the open, so the price the
spec model books (the stop level, below the open) is a price the time order does not allow: it uses bar b+N's
range, which happens after the open, to choose what happens at the open (pessimistic, systematic).

The same bar also shows the second shape: a CLOSE signal pending for bar b+N's open (③, at the open) loses to the
range stop.

Built by hand (no engine output used): bars with open 100 each; BUY at bar 0 -> filled at bar 1's open 100
(R-T1); stop 2 % -> 98; max_hold_bars = 2 -> the time exit is due at bar 3's open 100. Bar 3's low 97 reaches the
stop only after the open. Expected (spec): CLOSE at bar 3, price 100, reason time_exit, PnL 0.
The legacy rule set is not tested here (the old engine looks at the stop first; the compatibility mouth keeps it).
"""
from __future__ import annotations

import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
BARS = [(100, 101, 99.5, 100), (100, 101, 99.5, 100), (100, 101, 99.5, 100), (100, 101, 97, 99), (99, 100, 98, 99)]


def _run(signals):
    cfg = {"initial_equity": 10000.0, "order_notional": 3000.0,
           "costs": {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
           "execution": "taker", "maker_timeout_bars": 1, "allow_short": False, "swap_daily_pct": 0.0,
           "bar_seconds": 60.0, "stop_loss_pct": 2.0, "take_profit_pct": None, "max_hold_bars": 2,
           "exit_execution": "signal", "maker_tp_pct": None, "entry_mask": None, "entry_sides": "both",
           "stop_mode": "fixed", "stop_window_bars": None}
    rows = [{"open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0} for b in BARS]
    ev = bar_events(rows, [T0 + i * 60 * NS for i in range(len(rows))], 60 * NS)
    return run_bars(ev, lambda n: signals.get(n - 1), options_from_mapping(cfg), "spec", start=0)


@pytest.mark.parametrize("signals", [{0: "BUY"}, {0: "BUY", 2: "CLOSE"}], ids=["time_exit_only", "close_pending_too"])
def test_the_time_exit_bar_closes_at_its_open(signals):
    res = _run(signals)
    closes = [f for f in res.fills if f["side"].startswith("CLOSE_")]
    assert len(closes) == 1
    c = closes[0]
    assert (c["bar"], c["price"]) == (3, 100.0), c
    assert c["reason"] in ("time_exit", "signal"), c
    assert res.trade_pnls == [pytest.approx(0.0)]
