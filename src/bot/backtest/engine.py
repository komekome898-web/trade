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

Trade log: every CLOSE_* entry carries a "reason" in
{"signal", "stop_loss", "take_profit", "time_exit", "maker_tp", "wick_stop"} so
callers can break down how trades actually ended (exit-structure audits).
Additive field only — existing consumers keying off "bar"/"side"/"price"/"pnl"
are unaffected.

Additive options (all default to the historical behaviour; existing callers get
bit-identical results):

``exit_execution="maker_tp"`` + ``maker_tp_pct``
    Rests a maker take-profit limit at ``maker_tp_pct`` away from the entry
    price for the life of the position, while the strategy's own signal exit
    and the protective ``stop_loss_pct`` stay as taker fallbacks. The limit
    fills under the SAME conservative traded-through rule the maker entry
    path uses: the bar must trade strictly THROUGH the level
    (``high > level`` for a long TP, ``low < level`` for a short TP); merely
    touching it is not a fill. The fill is booked at the level itself with
    ``maker_fee`` and no spread/slippage, and is only ever checked on bars
    STRICTLY AFTER the entry bar, so there is no look-ahead.

    1m-bar approximation (optimistic, stated for the record): on a 1-minute
    bar we only know that the level traded through somewhere inside the
    minute, not that our specific resting order was reached in the queue, nor
    whether the stop level was touched EARLIER in the same minute. When the
    stop and the maker TP are both inside one bar's range the STOP is taken
    first (conservative), but within a single bar the true sequencing is
    unknown. Real fills also depend on queue position; this model grants the
    fill on any strict through-trade. Treat maker-TP results as an upper
    bound, not a promise.

``stop_mode="wick_invalidation"`` + ``stop_window_bars``
    Replaces the fixed-percentage protective stop with a STRUCTURAL one: the
    invalidation level is the extreme of the trailing ``stop_window_bars``
    COMPLETED bars' wicks as of the fill — ``min(low)`` over bars
    ``[b - N, b - 1]`` for a long, ``max(high)`` over the same bars for a
    short, where ``b`` is the fill bar. Bar ``b`` itself is excluded (its own
    range is not yet known when the position fills at its open), so under the
    taker path the window ends exactly on the SIGNAL bar — the bar whose wick
    the legacy bot froze.

    The level is FROZEN at entry and never trails. It is breached only by a
    CLOSE beyond it (``close < level`` long, ``close > level`` short); a wick
    poking through is explicitly not an exit, which is the whole point of the
    construction. A breach detected at bar ``i``'s close is executed at bar
    ``i + 1``'s OPEN with taker costs — the same next-bar-open causality the
    signal path uses — and is logged with ``reason="wick_stop"``. It overrides
    any pending signal for that bar and is checked BEFORE the intrabar
    stop/take-profit block, because it rests on strictly older information
    (the previous bar's close) than that bar's high/low.

    Requires ``stop_loss_pct=None``: the two protective stops are alternatives,
    never a stack.

``entry_mask`` / ``entry_sides``
    Restrict which decisions may OPEN a position; closes are never blocked.
    ``entry_mask`` is a per-bar boolean aligned to ``candles`` and is
    evaluated at the DECISION bar (the bar whose information produced the
    signal), not at the fill bar. ``entry_sides`` is one of
    ``"both"`` / ``"long"`` / ``"short"``. Both are entry-side filters only:
    an open position still exits by signal, stop, take-profit, maker TP and
    time exit exactly as before.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
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
    exit_execution: str = "signal",
    maker_tp_pct: float | None = None,
    entry_mask=None,
    entry_sides: str = "both",
    stop_mode: str = "fixed",
    stop_window_bars: int | None = None,
) -> BacktestResult:
    if execution not in ("taker", "maker"):
        raise ValueError(f"unknown execution model: {execution}")
    if max_hold_bars is not None and max_hold_bars < 1:
        raise ValueError("max_hold_bars must be >= 1")
    if stop_mode not in ("fixed", "wick_invalidation"):
        raise ValueError(f"unknown stop mode: {stop_mode}")
    if stop_mode == "wick_invalidation":
        if stop_window_bars is None or stop_window_bars < 1:
            raise ValueError('stop_mode="wick_invalidation" requires stop_window_bars >= 1')
        if stop_loss_pct is not None:
            raise ValueError('stop_mode="wick_invalidation" replaces stop_loss_pct; '
                             "pass stop_loss_pct=None")
    elif stop_window_bars is not None:
        raise ValueError('stop_window_bars requires stop_mode="wick_invalidation"')
    if exit_execution not in ("signal", "maker_tp"):
        raise ValueError(f"unknown exit execution model: {exit_execution}")
    if exit_execution == "maker_tp":
        if maker_tp_pct is None or maker_tp_pct <= 0:
            raise ValueError('exit_execution="maker_tp" requires maker_tp_pct > 0')
    elif maker_tp_pct is not None:
        raise ValueError('maker_tp_pct requires exit_execution="maker_tp"')
    if entry_sides not in ("both", "long", "short"):
        raise ValueError(f"unknown entry_sides: {entry_sides}")
    mtp_pct = maker_tp_pct if exit_execution == "maker_tp" else None
    mask = None
    if entry_mask is not None:
        mask = np.asarray(entry_mask, dtype=bool)
        if mask.shape != (len(candles),):
            raise ValueError(
                f"entry_mask length {mask.shape} != number of candles {len(candles)}")
    costs = costs or CostModel()
    cash = initial_equity_jpy
    position = 0.0                 # signed: >0 long, <0 short
    entry_price = 0.0
    entry_bar = -1                 # bar index the open position was filled on
    entry_cost = 0.0               # entry fee + accrued carry, charged at close
    wick_level: float | None = None  # frozen structural stop, wick_invalidation mode
    pending_taker: SignalType | None = None
    pending_taker_bar: int = -1    # decision bar behind pending_taker
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
        nonlocal wick_level
        size = order_notional_jpy / price
        fee = fee_fn(size * price)
        fees_total += fee
        position = size if side is SignalType.BUY else -size
        entry_price = price
        entry_bar = i
        entry_cost = fee
        if stop_mode == "wick_invalidation":
            lo = max(0, i - stop_window_bars)
            # bars [lo, i) are the COMPLETED bars behind the fill; bar i's own
            # range is unknown at its open, so it is excluded.
            wick_level = (float(lows[lo:i].min()) if position > 0
                          else float(highs[lo:i].max())) if lo < i else None
        trade_log.append({"bar": i, "side": f"OPEN_{'LONG' if position > 0 else 'SHORT'}",
                          "price": price, "size": size})

    def close_position(i: int, price: float, fee_fn, reason: str = "signal") -> None:
        nonlocal cash, position, entry_price, entry_bar, entry_cost, fees_total
        nonlocal wick_level
        size = abs(position)
        fee = fee_fn(size * price)
        fees_total += fee
        direction = 1.0 if position > 0 else -1.0
        pnl = (price - entry_price) * size * direction - fee - entry_cost
        cash += pnl
        trade_pnls.append(pnl)
        trade_log.append({"bar": i, "side": f"CLOSE_{'LONG' if position > 0 else 'SHORT'}",
                          "price": price, "size": size, "pnl": pnl, "reason": reason})
        position, entry_price, entry_cost = 0.0, 0.0, 0.0
        entry_bar = -1
        wick_level = None

    def entry_ok(decision_bar: int, side: SignalType) -> bool:
        """Entry-side filters. Evaluated at the DECISION bar, never at the fill
        bar, and never consulted when the action would close a position."""
        if entry_sides == "long" and side is SignalType.SELL:
            return False
        if entry_sides == "short" and side is SignalType.BUY:
            return False
        if mask is not None and not bool(mask[decision_bar]):
            return False
        return True

    def execute(i: int, side: SignalType, price: float, fee_fn,
                decision_bar: int) -> None:
        if side is SignalType.BUY:
            if position < 0:
                close_position(i, price, fee_fn, reason="signal")
            elif position == 0 and entry_ok(decision_bar, side):
                open_position(i, SignalType.BUY, price, fee_fn)
        else:
            if position > 0:
                close_position(i, price, fee_fn, reason="signal")
            elif position == 0 and allow_short and entry_ok(decision_bar, side):
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

        # 0.4) structural wick-invalidation stop. The level was frozen at entry;
        # a breach is a CLOSE beyond it, so the trigger is bar i-1's close and
        # the fill is bar i's open with taker costs. Checked before the intrabar
        # block because it rests on strictly older information.
        if wick_level is not None and position != 0.0 and i > entry_bar:
            long = position > 0
            breached = closes[i - 1] < wick_level if long else closes[i - 1] > wick_level
            if breached:
                ref = opens[i]
                price = costs.sell_price(ref) if long else costs.buy_price(ref)
                close_position(i, price, costs.fee, reason="wick_stop")
                pending_taker = None
                pending_limit = None

        # 0.5) protective stop / take-profit, checked intrabar. When both
        # levels are inside the bar's range the STOP is assumed to fill first
        # (conservative). Stops fill as market orders with taker costs; take
        # profits are resting limits filled at their level with maker fee.
        if position != 0.0 and i > 0 and i > entry_bar \
                and (stop_loss_pct or take_profit_pct or mtp_pct):
            long = position > 0
            sl_level = entry_price * (1 - stop_loss_pct / 100) if long and stop_loss_pct \
                else entry_price * (1 + stop_loss_pct / 100) if stop_loss_pct else None
            tp_level = entry_price * (1 + take_profit_pct / 100) if long and take_profit_pct \
                else entry_price * (1 - take_profit_pct / 100) if take_profit_pct else None
            # resting maker take-profit (exit_execution="maker_tp"); same
            # traded-through rule as the maker ENTRY path, checked only on bars
            # strictly after entry_bar (guaranteed by the guard above).
            mtp_level = entry_price * (1 + mtp_pct / 100) if long and mtp_pct \
                else entry_price * (1 - mtp_pct / 100) if mtp_pct else None
            sl_hit = sl_level is not None and (
                lows[i] <= sl_level if long else highs[i] >= sl_level)
            tp_hit = tp_level is not None and (
                highs[i] > tp_level if long else lows[i] < tp_level)
            mtp_hit = mtp_level is not None and (
                highs[i] > mtp_level if long else lows[i] < mtp_level)
            if sl_hit:
                trigger = min(opens[i], sl_level) if long else max(opens[i], sl_level)
                price = costs.sell_price(trigger) if long else costs.buy_price(trigger)
                close_position(i, price, costs.fee, reason="stop_loss")
                pending_taker = None
                pending_limit = None
            elif tp_hit:
                close_position(i, tp_level, costs.maker_fee, reason="take_profit")
                pending_taker = None
                pending_limit = None
            elif mtp_hit:
                close_position(i, mtp_level, costs.maker_fee, reason="maker_tp")
                pending_taker = None
                pending_limit = None

        # 0.7) time exit: a position filled at bar b is force-closed at the OPEN
        # of bar b + max_hold_bars with taker costs. Any pending signal for this
        # bar is simply overridden.
        if max_hold_bars is not None and position != 0.0 \
                and i - entry_bar >= max_hold_bars:
            ref = opens[i]
            price = costs.sell_price(ref) if position > 0 else costs.buy_price(ref)
            close_position(i, price, costs.fee, reason="time_exit")
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
                    execute(i, side, price, costs.fee, pending_taker_bar)
                pending_taker = None
        else:
            if pending_limit is not None and i > pending_limit.placed_bar:
                po = pending_limit
                traded_through = (lows[i] < po.limit) if po.side is SignalType.BUY \
                    else (highs[i] > po.limit)
                if traded_through and actionable(po.side):
                    execute(i, po.side, po.limit, costs.maker_fee, po.placed_bar)
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
                    pending_taker_bar = i
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
