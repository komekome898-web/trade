"""Backtest engine.

Anti-look-ahead design:
- The strategy at bar i sees candles[0..i] only (an expanding slice).
- Taker execution: a signal at bar i executes at bar i+1's OPEN with
  spread + slippage + taker fee applied.
- Maker execution: a signal at bar i places a limit at bar i's CLOSE; it fills
  only when a LATER bar trades strictly through the limit (low < limit for BUY,
  high > limit for SELL), paying the maker fee only. Unfilled orders cancel
  after `maker_timeout_bars` and are counted as missed fills. Touching the
  level is not enough — a conservative fill model.

Position model: one net position at a time. BUY closes a short or opens a
long; SELL closes a long or opens a short (shorts only when allow_short, for
margin products such as FX_BTC_JPY). Margin carry cost accrues per bar via
`swap_daily_pct` and is charged against the open trade's PnL.

Time exit: `max_hold_bars` caps how long a position may stay open. A position
filled at bar b is force-closed at the OPEN of bar b + max_hold_bars — i.e.
after exactly max_hold_bars bars of holding — with taker costs, whatever the
strategy says. The forced close overrides any pending signal on that bar. An
intrabar stop/take-profit on an EARLIER bar naturally fires first; on the same
bar the stop is checked first (conservative).
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
    allow_short: bool = False,
    swap_daily_pct: float = 0.0,
    bar_seconds: float = 60.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    max_hold_bars: int | None = None,
) -> BacktestResult:
    if execution not in ("taker", "maker"):
        raise ValueError(f"unknown execution model: {execution}")
    if max_hold_bars is not None and max_hold_bars < 1:
        raise ValueError("max_hold_bars must be >= 1")
    costs = costs or CostModel()
    cash = initial_equity_jpy
    position = 0.0                 # signed: >0 long, <0 short
    entry_price = 0.0
    entry_bar = -1                 # bar index the open position was filled on
    entry_cost = 0.0               # entry fee + accrued carry, charged at close
    pending_taker: SignalType | None = None
    pending_limit: _PendingLimit | None = None
    equity = []
    trade_pnls: list[float] = []
    trade_log: list[dict] = []
    fees_total = 0.0
    missed_fills = 0
    swap_per_bar = swap_daily_pct / 100 * (bar_seconds / 86400.0)

    start = strategy.min_history
    closes = candles["close"].to_numpy()
    opens = candles["open"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()

    def open_position(i: int, side: SignalType, price: float, fee_fn) -> None:
        nonlocal cash, position, entry_price, entry_bar, entry_cost, fees_total
        size = order_notional_jpy / price
        fee = fee_fn(size * price)
        fees_total += fee
        position = size if side is SignalType.BUY else -size
        entry_price = price
        entry_bar = i
        entry_cost = fee
        trade_log.append({"bar": i, "side": f"OPEN_{'LONG' if position > 0 else 'SHORT'}",
                          "price": price, "size": size})

    def close_position(i: int, price: float, fee_fn) -> None:
        nonlocal cash, position, entry_price, entry_bar, entry_cost, fees_total
        size = abs(position)
        fee = fee_fn(size * price)
        fees_total += fee
        direction = 1.0 if position > 0 else -1.0
        pnl = (price - entry_price) * size * direction - fee - entry_cost
        cash += pnl
        trade_pnls.append(pnl)
        trade_log.append({"bar": i, "side": f"CLOSE_{'LONG' if position > 0 else 'SHORT'}",
                          "price": price, "size": size, "pnl": pnl})
        position, entry_price, entry_cost = 0.0, 0.0, 0.0
        entry_bar = -1

    def execute(i: int, side: SignalType, price: float, fee_fn) -> None:
        if side is SignalType.BUY:
            if position < 0:
                close_position(i, price, fee_fn)
            elif position == 0:
                open_position(i, SignalType.BUY, price, fee_fn)
        else:
            if position > 0:
                close_position(i, price, fee_fn)
            elif position == 0 and allow_short:
                open_position(i, SignalType.SELL, price, fee_fn)

    def actionable(side: SignalType) -> bool:
        if side is SignalType.BUY:
            return position <= 0
        return position > 0 or (position == 0 and allow_short)

    for i in range(len(candles)):
        # 0) margin carry accrues on any open position, per bar
        if position != 0.0 and swap_per_bar > 0:
            carry = abs(position) * closes[i - 1 if i > 0 else 0] * swap_per_bar
            entry_cost += carry
            fees_total += carry

        # 0.5) protective stop / take-profit, checked intrabar. When both
        # levels are inside the bar's range the STOP is assumed to fill first
        # (conservative). Stops fill as market orders with taker costs; take
        # profits are resting limits filled at their level with maker fee.
        if position != 0.0 and i > 0 and (stop_loss_pct or take_profit_pct):
            long = position > 0
            sl_level = entry_price * (1 - stop_loss_pct / 100) if long and stop_loss_pct \
                else entry_price * (1 + stop_loss_pct / 100) if stop_loss_pct else None
            tp_level = entry_price * (1 + take_profit_pct / 100) if long and take_profit_pct \
                else entry_price * (1 - take_profit_pct / 100) if take_profit_pct else None
            sl_hit = sl_level is not None and (
                lows[i] <= sl_level if long else highs[i] >= sl_level)
            tp_hit = tp_level is not None and (
                highs[i] > tp_level if long else lows[i] < tp_level)
            if sl_hit:
                trigger = min(opens[i], sl_level) if long else max(opens[i], sl_level)
                price = costs.sell_price(trigger) if long else costs.buy_price(trigger)
                close_position(i, price, costs.fee)
                pending_taker = None
                pending_limit = None
            elif tp_hit:
                close_position(i, tp_level, costs.maker_fee)
                pending_taker = None
                pending_limit = None

        # 0.7) time exit: a position filled at bar b is force-closed at the OPEN
        # of bar b + max_hold_bars with taker costs. Any pending signal for this
        # bar is simply overridden.
        if max_hold_bars is not None and position != 0.0 \
                and i - entry_bar >= max_hold_bars:
            ref = opens[i]
            price = costs.sell_price(ref) if position > 0 else costs.buy_price(ref)
            close_position(i, price, costs.fee)
            pending_taker = None
            pending_limit = None

        # 1) execute prior decisions against THIS bar
        if execution == "taker":
            if pending_taker is not None and i > 0:
                ref = opens[i]
                side = pending_taker
                if side is SignalType.CLOSE:
                    side = SignalType.SELL if position > 0 else SignalType.BUY \
                        if position < 0 else None
                if side is not None:
                    price = costs.buy_price(ref) if side is SignalType.BUY \
                        else costs.sell_price(ref)
                    execute(i, side, price, costs.fee)
                pending_taker = None
        else:
            if pending_limit is not None and i > pending_limit.placed_bar:
                po = pending_limit
                traded_through = (lows[i] < po.limit) if po.side is SignalType.BUY \
                    else (highs[i] > po.limit)
                if traded_through and actionable(po.side):
                    execute(i, po.side, po.limit, costs.maker_fee)
                    pending_limit = None
                elif i - po.placed_bar >= maker_timeout_bars:
                    missed_fills += 1
                    trade_log.append({"bar": i, "side": f"CANCEL_{po.side.value}",
                                      "price": po.limit, "size": 0.0})
                    pending_limit = None

        # 2) decide on this bar using only candles[0..i]
        if i >= start:
            signal = strategy.on_candles(candles.iloc[: i + 1])
            sig_type = signal.type
            if sig_type is SignalType.CLOSE:
                # resolve CLOSE to the concrete closing side, or drop when flat
                sig_type = SignalType.SELL if position > 0 else SignalType.BUY \
                    if position < 0 else None
                if sig_type is None and execution == "taker":
                    pass
            if sig_type in (SignalType.BUY, SignalType.SELL):
                if execution == "taker":
                    if signal.type is SignalType.CLOSE:
                        pending_taker = SignalType.CLOSE
                    else:
                        pending_taker = sig_type
                elif actionable(sig_type) or signal.type is SignalType.CLOSE:
                    if pending_limit is not None and pending_limit.side is not sig_type:
                        missed_fills += 1
                    pending_limit = _PendingLimit(sig_type, closes[i], i)

        direction = 1.0 if position >= 0 else -1.0
        unrealized = (closes[i] - entry_price) * abs(position) * direction - entry_cost \
            if position != 0 else 0.0
        equity.append(cash + unrealized)

    equity_curve = pd.Series(equity, index=candles.index)
    metrics = compute_metrics(trade_pnls, equity_curve, fees_total)
    return BacktestResult(metrics, equity_curve, trade_pnls, trade_log, missed_fills)
