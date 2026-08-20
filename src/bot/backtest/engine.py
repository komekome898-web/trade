"""Backtest engine.

Anti-look-ahead design:
- The strategy at bar i sees candles[0..i] only (an expanding slice).
- Taker execution: a signal at bar i executes at bar i+1's OPEN with
  spread + slippage + taker fee applied.
- Maker execution: a signal at bar i places a limit at bar i's CLOSE; it fills
  only when a LATER bar trades strictly through the limit (low < limit for BUY,
  high > limit for SELL), paying the maker fee only. Unfilled orders cancel
  after `maker_timeout_bars` and are counted as missed fills. This is a
  conservative fill model: touching the level is not enough.
Long-only (spot). Position sizing is bounded by the caller via
`order_notional_jpy`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from bot.backtest.metrics import Metrics, compute_metrics
from bot.strategy.base import SignalType, Strategy


@dataclass
class CostModel:
    taker_fee_pct: float = 0.15
    maker_fee_pct: float = 0.15    # bitFlyer spot charges the same tier both sides
    slippage_pct: float = 0.05
    spread_pct: float = 0.10       # half applied per side around mid (taker only)

    def buy_price(self, ref_price: float) -> float:
        return ref_price * (1 + (self.spread_pct / 2 + self.slippage_pct) / 100)

    def sell_price(self, ref_price: float) -> float:
        return ref_price * (1 - (self.spread_pct / 2 + self.slippage_pct) / 100)

    def fee(self, notional: float) -> float:
        return notional * self.taker_fee_pct / 100

    def maker_fee(self, notional: float) -> float:
        return notional * self.maker_fee_pct / 100


@dataclass
class BacktestResult:
    metrics: Metrics
    equity_curve: pd.Series
    trade_pnls: list[float] = field(default_factory=list)
    trade_log: list[dict] = field(default_factory=list)
    missed_fills: int = 0


@dataclass
class _PendingLimit:
    side: SignalType
    limit: float
    placed_bar: int


def run_backtest(
    strategy: Strategy,
    candles: pd.DataFrame,
    *,
    initial_equity_jpy: float = 6000.0,
    order_notional_jpy: float = 3000.0,
    costs: CostModel | None = None,
    execution: str = "taker",
    maker_timeout_bars: int = 5,
) -> BacktestResult:
    if execution not in ("taker", "maker"):
        raise ValueError(f"unknown execution model: {execution}")
    costs = costs or CostModel()
    cash = initial_equity_jpy
    position = 0.0
    entry_price = 0.0
    entry_cost = 0.0
    pending_taker: SignalType | None = None
    pending_limit: _PendingLimit | None = None
    equity = []
    trade_pnls: list[float] = []
    trade_log: list[dict] = []
    fees_total = 0.0
    missed_fills = 0

    start = strategy.min_history
    closes = candles["close"].to_numpy()
    opens = candles["open"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()

    def book_buy(i: int, price: float, fee_fn) -> None:
        nonlocal cash, position, entry_price, entry_cost, fees_total
        size = order_notional_jpy / price
        fee = fee_fn(size * price)
        if size * price + fee <= cash:
            cash -= size * price + fee
            fees_total += fee
            position, entry_price = size, price
            entry_cost = fee
            trade_log.append({"bar": i, "side": "BUY", "price": price, "size": size})

    def book_sell(i: int, price: float, fee_fn) -> None:
        nonlocal cash, position, entry_price, entry_cost, fees_total
        fee = fee_fn(position * price)
        cash += position * price - fee
        fees_total += fee
        pnl = (price - entry_price) * position - fee - entry_cost
        trade_pnls.append(pnl)
        trade_log.append({"bar": i, "side": "SELL", "price": price,
                          "size": position, "pnl": pnl})
        position, entry_price, entry_cost = 0.0, 0.0, 0.0

    for i in range(len(candles)):
        # 1) execute prior decisions against THIS bar (open for taker,
        #    intrabar range for maker) — always before deciding on bar i.
        if execution == "taker":
            if pending_taker is not None and i > 0:
                if pending_taker is SignalType.BUY and position == 0.0:
                    book_buy(i, costs.buy_price(opens[i]), costs.fee)
                elif pending_taker is SignalType.SELL and position > 0.0:
                    book_sell(i, costs.sell_price(opens[i]), costs.fee)
                pending_taker = None
        else:
            if pending_limit is not None and i > pending_limit.placed_bar:
                po = pending_limit
                filled = (
                    (po.side is SignalType.BUY and position == 0.0 and lows[i] < po.limit)
                    or (po.side is SignalType.SELL and position > 0.0 and highs[i] > po.limit)
                )
                if filled:
                    if po.side is SignalType.BUY:
                        book_buy(i, po.limit, costs.maker_fee)
                    else:
                        book_sell(i, po.limit, costs.maker_fee)
                    pending_limit = None
                elif i - po.placed_bar >= maker_timeout_bars:
                    missed_fills += 1
                    trade_log.append({"bar": i, "side": f"CANCEL_{po.side.value}",
                                      "price": po.limit, "size": 0.0})
                    pending_limit = None

        # 2) decide on this bar using only candles[0..i]
        if i >= start:
            signal = strategy.on_candles(candles.iloc[: i + 1])
            if signal.type in (SignalType.BUY, SignalType.SELL):
                actionable = (signal.type is SignalType.BUY and position == 0.0) or \
                             (signal.type is SignalType.SELL and position > 0.0)
                if execution == "taker":
                    pending_taker = signal.type
                elif actionable:
                    # new signal replaces any resting order (cancel/replace)
                    if pending_limit is not None and pending_limit.side is not signal.type:
                        missed_fills += 1
                    pending_limit = _PendingLimit(signal.type, closes[i], i)

        equity.append(cash + position * closes[i])

    equity_curve = pd.Series(equity, index=candles.index)
    metrics = compute_metrics(trade_pnls, equity_curve, fees_total)
    return BacktestResult(metrics, equity_curve, trade_pnls, trade_log, missed_fills)
