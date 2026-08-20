"""Engine time exit (`max_hold_bars`)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.strategy.base import Signal, SignalType, Strategy

NO_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0)


def candles_from(rows):
    a = np.array(rows, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3], "volume": np.ones(len(a))})


class Scripted(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.script = params["script"]

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        sig = self.script.get(len(candles) - 1)
        return Signal(sig, "scripted") if sig else Signal(SignalType.HOLD, "")


# entry signal on bar 1 -> filled at bar 2's open (100); prices then walk up 1/bar
RAMP = [
    (100, 100.5, 99.5, 100),
    (100, 100.5, 99.5, 100),   # bar 1: entry signal
    (100, 100.5, 99.5, 100),   # bar 2: filled at open 100
    (101, 101.5, 100.5, 101),
    (102, 102.5, 101.5, 102),
    (103, 103.5, 102.5, 103),  # bar 5: 3 bars after entry
    (104, 104.5, 103.5, 104),
]


def closes(res):
    return [t for t in res.trade_log if t["side"].startswith("CLOSE")]


def test_long_force_closed_after_exactly_n_bars_at_next_open():
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles_from(RAMP),
                       costs=NO_COST, order_notional_jpy=1000, max_hold_bars=3)
    assert len(res.trade_pnls) == 1
    # entry at bar 2 open 100, exit at bar 5 open 103, size 1000/100 = 10
    assert closes(res)[0]["bar"] == 5
    assert closes(res)[0]["price"] == pytest.approx(103.0)
    assert res.trade_pnls[0] == pytest.approx(10 * 3.0, rel=1e-6)


def test_short_force_closed_symmetrically():
    res = run_backtest(Scripted({"script": {1: SignalType.SELL}}), candles_from(RAMP),
                       costs=NO_COST, order_notional_jpy=1000, allow_short=True,
                       max_hold_bars=3)
    assert len(res.trade_pnls) == 1
    assert closes(res)[0]["bar"] == 5
    assert res.trade_pnls[0] == pytest.approx(-10 * 3.0, rel=1e-6)


def test_no_effect_when_none():
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles_from(RAMP),
                       costs=NO_COST, order_notional_jpy=1000, max_hold_bars=None)
    assert res.trade_pnls == []          # position stays open to the end
    assert closes(res) == []


def test_stop_loss_fires_first_when_hit_earlier():
    rows = list(RAMP)
    rows[3] = (101, 101.5, 98.9, 101)    # bar 3: low 98.9 <= SL 99
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles_from(rows),
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_loss_pct=1.0, max_hold_bars=3)
    assert len(res.trade_pnls) == 1
    assert closes(res)[0]["bar"] == 3    # stopped before the time exit at bar 5
    assert res.trade_pnls[0] == pytest.approx(-1000 * 0.01, rel=1e-6)


def test_time_exit_still_applies_when_stop_never_hit():
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles_from(RAMP),
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_loss_pct=1.0, max_hold_bars=3)
    assert len(res.trade_pnls) == 1
    assert closes(res)[0]["bar"] == 5
    assert res.trade_pnls[0] == pytest.approx(10 * 3.0, rel=1e-6)


def test_force_close_overrides_pending_signal_on_that_bar():
    # short opened at bar 2; a BUY signal on bar 4 is pending for bar 5, the same
    # bar the time exit fires — the forced close must swallow it, not re-enter long.
    res = run_backtest(
        Scripted({"script": {1: SignalType.SELL, 4: SignalType.BUY}}),
        candles_from(RAMP), costs=NO_COST, order_notional_jpy=1000,
        allow_short=True, max_hold_bars=3)
    assert len(res.trade_pnls) == 1
    assert closes(res)[0]["bar"] == 5
    assert not [t for t in res.trade_log if t["side"] == "OPEN_LONG"]


def test_invalid_max_hold_bars_rejected():
    with pytest.raises(ValueError):
        run_backtest(Scripted({"script": {}}), candles_from(RAMP), max_hold_bars=0)
