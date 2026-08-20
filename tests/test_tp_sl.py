"""Engine intrabar stop-loss / take-profit."""
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


def test_long_stop_loss_fires_intrabar():
    candles = candles_from([
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),   # bar 1: BUY signal
        (100, 100.5, 99.5, 100),   # bar 2: fill at open 100
        (100, 100.5, 98.9, 100),   # low 98.9 <= SL 99 -> stop out at 99
        (100, 100.5, 99.5, 100),
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, stop_loss_pct=1.0, order_notional_jpy=1000)
    assert len(res.trade_pnls) == 1
    assert res.trade_pnls[0] == pytest.approx(-1000 * 0.01, rel=1e-6)


def test_long_take_profit_fires_intrabar():
    candles = candles_from([
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),   # bar 1: BUY signal
        (100, 100.5, 99.5, 100),   # bar 2: fill at open 100
        (100, 101.2, 99.9, 100),   # high 101.2 > TP 101 -> exit at 101
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, take_profit_pct=1.0, order_notional_jpy=1000)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)


def test_stop_takes_priority_when_both_hit():
    candles = candles_from([
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),   # fill at 100
        (100, 102.0, 98.0, 100),   # both SL 99 and TP 101 inside range -> SL first
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, stop_loss_pct=1.0, take_profit_pct=1.0,
                       order_notional_jpy=1000)
    assert res.trade_pnls[0] == pytest.approx(-1000 * 0.01, rel=1e-6)


def test_short_stop_and_tp_sides():
    candles = candles_from([
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),   # SELL signal (short)
        (100, 100.5, 99.5, 100),   # short filled at open 100
        (100, 100.5, 98.8, 100),   # low 98.8 < TP level 99 -> cover at 99
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.SELL}}), candles,
                       costs=NO_COST, allow_short=True, take_profit_pct=1.0,
                       order_notional_jpy=1000)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)


def test_gap_open_beyond_stop_fills_at_open():
    candles = candles_from([
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),
        (100, 100.5, 99.5, 100),   # long filled at 100
        (97, 97.5, 96.5, 97),      # gaps far below SL 99 -> fill at open 97
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, stop_loss_pct=1.0, order_notional_jpy=1000)
    assert res.trade_pnls[0] == pytest.approx(-1000 * 0.03, rel=1e-6)
