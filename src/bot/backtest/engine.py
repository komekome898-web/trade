"""Backtest engine.

Anti-look-ahead design:
- The strategy at bar i sees candles[0..i] only (an expanding slice).
- A signal at bar i executes at bar i+1's OPEN (execution delay), with
  spread + slippage + taker fee applied.
Costs are explicit and conservative. Long-only (spot), all-in position sizing
bounded by risk limits is applied by the caller via `order_notional_jpy`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from bot.backtest.metrics import Metrics, compute_metrics
from bot.strategy.base import SignalType, Strategy


@dataclass
class CostModel:
    taker_fee_pct: float = 0.15
    slippage_pct: float = 0.05
    spread_pct: float = 0.10       # half applied per side around mid

    def buy_price(self, ref_price: float) -> float:
        return ref_price * (1 + (self.spread_pct / 2 + self.slippage_pct) / 100)

    def sell_price(self, ref_price: float) -> float:
        return ref_price * (1 - (self.spread_pct / 2 + self.slippage_pct) / 100)

    def fee(self, notional: float) -> float:
        return notional * self.taker_fee_pct / 100


@dataclass
class BacktestResult:
    metrics: Metrics
    equity_curve: pd.Series
    trade_pnls: list[float] = field(default_factory=list)
    trade_log: list[dict] = field(default_factory=list)


def run_backtest(
    strategy: Strategy,
    candles: pd.DataFrame,
    *,
    initial_equity_jpy: float = 6000.0,
    order_notional_jpy: float = 3000.0,
    costs: CostModel | None = None,
) -> BacktestResult:
    costs = costs or CostModel()
    cash = initial_equity_jpy
    position = 0.0
    entry_price = 0.0
    entry_cost = 0.0
    pending: SignalType | None = None
    equity = []
    trade_pnls: list[float] = []
    trade_log: list[dict] = []
    fees_total = 0.0

    start = strategy.min_history
    closes = candles["close"].to_numpy()
    opens = candles["open"].to_numpy()

    for i in range(len(candles)):
        # 1) execute the signal decided on the PREVIOUS bar at THIS bar's open
        if pending is not None and i > 0:
            ref = opens[i]
            if pending is SignalType.BUY and position == 0.0:
                price = costs.buy_price(ref)
                size = order_notional_jpy / price
                fee = costs.fee(size * price)
                if size * price + fee <= cash:
                    cash -= size * price + fee
                    fees_total += fee
                    position, entry_price = size, price
                    entry_cost = fee
                    trade_log.append({"bar": i, "side": "BUY", "price": price, "size": size})
            elif pending is SignalType.SELL and position > 0.0:
                price = costs.sell_price(ref)
                fee = costs.fee(position * price)
                cash += position * price - fee
                fees_total += fee
                pnl = (price - entry_price) * position - fee - entry_cost
                trade_pnls.append(pnl)
                trade_log.append({"bar": i, "side": "SELL", "price": price,
                                  "size": position, "pnl": pnl})
                position, entry_price, entry_cost = 0.0, 0.0, 0.0
            pending = None

        # 2) decide on this bar using only candles[0..i]
        if i >= start:
            signal = strategy.on_candles(candles.iloc[: i + 1])
            if signal.type in (SignalType.BUY, SignalType.SELL):
                pending = signal.type

        equity.append(cash + position * closes[i])

    equity_curve = pd.Series(equity, index=candles.index)
    metrics = compute_metrics(trade_pnls, equity_curve, fees_total)
    return BacktestResult(metrics, equity_curve, trade_pnls, trade_log)
