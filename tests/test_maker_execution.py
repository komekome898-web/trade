"""Maker (limit) execution model: fill conditions, timeout, no look-ahead."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.strategy.base import Signal, SignalType, Strategy

NO_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0)


def candles_from(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows: (open, high, low, close)"""
    a = np.array(rows, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3], "volume": np.ones(len(a))})


class ScriptedSignals(Strategy):
    """Emit fixed signals at fixed bar indices."""
    def __init__(self, params=None):
        super().__init__(params)
        self.script: dict[int, SignalType] = params["script"]

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        sig = self.script.get(len(candles) - 1)
        return Signal(sig, "scripted") if sig else Signal(SignalType.HOLD, "")


def test_maker_buy_fills_only_when_traded_through():
    # signal at bar 1 -> limit at close 100. Bar 2 low=100 (touch, no fill),
    # bar 3 low=99.5 (traded through -> fill at 100).
    candles = candles_from([
        (100, 101, 99, 100),
        (100, 101, 100, 100),   # bar 1: signal, limit=100
        (100, 101, 100, 100),   # touch only -> NO fill
        (100, 101, 99.5, 100),  # traded through -> fill
        (100, 101, 100, 100),
    ])
    res = run_backtest(ScriptedSignals({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, execution="maker")
    buys = [t for t in res.trade_log if t["side"] == "BUY"]
    assert len(buys) == 1
    assert buys[0]["bar"] == 3
    assert buys[0]["price"] == 100.0


def test_maker_timeout_cancels_and_counts_missed_fill():
    candles = candles_from([(100, 101, 100, 100)] * 10)  # never trades below 100
    res = run_backtest(ScriptedSignals({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, execution="maker", maker_timeout_bars=3)
    assert [t for t in res.trade_log if t["side"] == "BUY"] == []
    assert res.missed_fills == 1


def test_maker_sell_fill_and_fee_only_cost():
    costs = CostModel(taker_fee_pct=0.15, maker_fee_pct=0.10, slippage_pct=0.05,
                      spread_pct=0.10)
    candles = candles_from([
        (100, 101, 99, 100),
        (100, 101, 100, 100),    # bar 1: BUY signal, limit=100
        (100, 101, 98, 100),     # fill BUY at 100
        (100, 101, 100, 100),    # bar 3: SELL signal, limit=100
        (100, 102, 100, 100),    # high 102 > 100 -> fill SELL at 100
    ])
    res = run_backtest(
        ScriptedSignals({"script": {1: SignalType.BUY, 3: SignalType.SELL}}),
        candles, costs=costs, execution="maker", order_notional_jpy=3000)
    assert len(res.trade_pnls) == 1
    # flat round trip at same price: loss == maker fee both ways (0.10% x 2 of 3000)
    assert res.trade_pnls[0] == pytest.approx(-3000 * 0.001 * 2, rel=1e-6)


def test_maker_no_same_bar_fill():
    """A limit placed on bar i must never fill against bar i's own range."""
    candles = candles_from([
        (100, 101, 99, 100),
        (100, 101, 90, 100),   # bar 1: signal; its own low would "fill" -> must not
        (100, 101, 100, 100),
        (100, 101, 100, 100),
        (100, 101, 100, 100),
        (100, 101, 100, 100),
        (100, 101, 100, 100),
        (100, 101, 100, 100),
    ])
    res = run_backtest(ScriptedSignals({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, execution="maker", maker_timeout_bars=5)
    assert [t for t in res.trade_log if t["side"] == "BUY"] == []
    assert res.missed_fills == 1


def test_taker_path_unchanged_by_maker_addition():
    candles = candles_from([(100, 101, 99, 100)] * 6)
    res = run_backtest(ScriptedSignals({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, execution="taker")
    buys = [t for t in res.trade_log if t["side"] == "BUY"]
    assert buys and buys[0]["bar"] == 3 and buys[0]["price"] == 100.0
