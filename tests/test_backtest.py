"""General properties through the mouth `bot.backtest` (the new engine, item 4): costs reduce PnL, zero costs
break even (R-A3 with every rate 0), look-ahead prevention, split integrity (D-1 / D-2), the metric set (M-1 ..
M-12), indicator causality. The scene-set rules R-* themselves are held by tests/bt/battery/item_4 and
tests/bt/item_4 (engine vs the independent reference)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.backtest.metrics import compute_metrics
from bot.backtest.walk_forward import split_data
from bot.indicators.core import donchian, ema, rsi
from bot.strategy.base import Signal, SignalType, Strategy


def make_candles(prices: list[float]) -> pd.DataFrame:
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame({"open": p, "high": p * 1.001, "low": p * 0.999,
                         "close": p, "volume": np.ones_like(p)})


class BuyThenSellOnce(Strategy):
    """Deterministic: BUY at bar 3, SELL at bar 6."""
    @property
    def min_history(self):
        return 2

    def on_candles(self, candles):
        i = len(candles) - 1
        if i == 3:
            return Signal(SignalType.BUY, "scripted")
        if i == 6:
            return Signal(SignalType.SELL, "scripted")
        return Signal(SignalType.HOLD, "")


def test_costs_reduce_pnl_on_flat_market():
    candles = make_candles([100.0] * 10)
    res = run_backtest(BuyThenSellOnce({}), candles,
                       costs=CostModel(taker_fee_pct=0.15, slippage_pct=0.05, spread_pct=0.1))
    assert len(res.trade_pnls) == 1
    assert res.trade_pnls[0] < 0  # flat prices: round trip must lose exactly the costs
    assert res.metrics.total_fees_jpy > 0


def test_zero_cost_flat_market_is_breakeven():
    candles = make_candles([100.0] * 10)
    res = run_backtest(BuyThenSellOnce({}), candles,
                       costs=CostModel(taker_fee_pct=0, slippage_pct=0, spread_pct=0))
    assert res.trade_pnls[0] == pytest.approx(0.0)


class LookAheadProbe(Strategy):
    """Records the last close it can see at each decision bar."""
    def __init__(self, params=None):
        super().__init__(params)
        self.seen: list[float] = []

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        self.seen.append(float(candles["close"].iloc[-1]))
        return Signal(SignalType.HOLD, "")


def test_strategy_never_sees_future_bars():
    prices = [float(i) for i in range(1, 21)]
    strat = LookAheadProbe({})
    run_backtest(strat, make_candles(prices))
    assert strat.seen == prices[strat.min_history:]  # bar i sees close[i], nothing later


def test_split_is_chronological_and_disjoint():
    candles = make_candles([float(i) for i in range(100)])
    s = split_data(candles, 0.6, 0.2)
    # D-1: floor(100 * 0.6) = 60, floor(100 * (0.6 + 0.2)) = 80 on the written decimals -> 60 / 20 / 20
    assert len(s.training) == 60 and len(s.validation) == 20 and len(s.out_of_sample) == 20
    assert s.training["close"].iloc[-1] < s.validation["close"].iloc[0]
    assert s.validation["close"].iloc[-1] < s.out_of_sample["close"].iloc[0]


def test_metrics_full_set():
    equity = pd.Series([100, 110, 105, 120, 115], dtype=float)
    # the values follow from the definitions M-1 .. M-12 (bot.bt.compat.metrics): 2 wins of 4 (M-3), gross profit
    # 25 / gross loss 10 (M-4), one loss at a time (M-7), mean win 12.5 / mean loss -5 (M-8, M-9), 12.5 / 5 (M-10),
    # 15 / 4 (M-11); the equity falls from 110 to 105 and from 120 to 115 (M-6 > 0)
    m = compute_metrics([10.0, -5.0, 15.0, -5.0], equity)
    assert m.num_trades == 4
    assert m.win_rate_pct == 50.0
    assert m.profit_factor == pytest.approx(25.0 / 10.0)
    assert m.max_consecutive_losses == 1
    assert m.avg_win_jpy == pytest.approx(12.5)
    assert m.avg_loss_jpy == pytest.approx(-5.0)
    assert m.risk_reward_ratio == pytest.approx(2.5)
    assert m.expectancy_per_trade_jpy == pytest.approx(3.75)
    assert m.max_drawdown_pct > 0


# ---- indicator causality --------------------------------------------------
def test_ema_is_causal():
    a = pd.Series([float(i) for i in range(50)])
    b = a.copy()
    b.iloc[-1] = 1000.0  # change ONLY the last value
    ea, eb = ema(a, 10), ema(b, 10)
    assert (ea.iloc[:-1].fillna(0) == eb.iloc[:-1].fillna(0)).all()


def test_rsi_bounds_and_warmup():
    r = rsi(pd.Series(np.random.default_rng(0).normal(100, 1, 100).cumsum()), 14)
    assert r.iloc[:13].isna().all()
    valid = r.dropna()
    assert ((valid >= 0) & (valid <= 100)).all()


def test_donchian_excludes_current_bar():
    high = pd.Series([1.0] * 20 + [100.0])
    low = pd.Series([0.5] * 21)
    ch = donchian(high, low, 5)
    assert ch["upper"].iloc[-1] == 1.0  # current bar's 100 spike not in its own channel
