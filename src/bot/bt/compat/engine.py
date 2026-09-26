"""The compatibility mouth of the old `bot.backtest.engine` (item 4, old item
14; L-408 案2: 「旧と同じ名前・同じ引数の呼び口(`run_backtest`・`CostModel`
...)を新エンジンの上に新しく書き」).

`run_backtest` takes the old arguments with the old defaults and runs the
new engine's bar model (`barmodel.run_bars` on the core) with the rule set
"legacy", so the result is the old engine's, bit for bit (proved by
tests/bt/compat/: the old tests' scenes and the golden files made with the
old engine before it is replaced).

The strategy is the old interface (`bot.strategy.base.Strategy`): at bar i
it gets `candles.iloc[: i + 1]` -- i + 1 is the number of bars the core has
delivered to the strategy socket, so the slice never reaches a bar the core
has not delivered. The bars are handed to the core on a synthetic clock
(bar i starts at BASE_NS + i * 60 s): the old engine's rules are by bar
index, not by time; `bar_seconds` is used for the carry only, as before.

This mouth refuses a row that the core cannot take as a bar (a NaN, a price
<= 0, high below max(open, close), low above min(open, close)) with a
ValueError instead of computing a number from it: the core's contract.

`run_backtest_as_old` is the layer in front of this mouth (L-407
「完全上位互換」, finishing condition 3: 「旧が計算していた不正な足…は、互換の口の
手前に「旧と同じ数を出す層」を置いて旧と同じ結果を返す(核の契約は変えない)」).
It has the old signature and is what `bot.backtest.engine.run_backtest` is.
Before anything runs it decides the route, without calling the strategy:

  core    every row is a bar the core takes (bar_events succeeds);
          `costs` is a CostModel whose buy_price / sell_price / fee /
          maker_fee are CostModel's own (the core's cost socket is a
          percentage model and cannot honour a subclass's method), whose
          four percentages are finite and whose taker prices stay > 0;
          order_notional_jpy is finite and > 0 (the core refuses any
          other order size); stop_loss_pct / take_profit_pct /
          maker_tp_pct are None or finite  ->  this mouth, on the core.
  old     anything else  ->  `_old_arithmetic`, the old engine's loop
          (src/bot/backtest/engine.py before the replacement, copied line
          for line; snapshot and sha256 under docs/DISCUSSIONS/
          2026-09-23_backtest_env/item_4/round_3/materials/replace/
          old_engine_snapshot/). The core never sees such a run.

tests/bt/compat/test_replace_layer_grid.py runs the layer against the
snapshot over (malformed-row shape x option cell) and over fresh seeded
valid cells, and proves that a valid run never takes the old route.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from bot.strategy.base import SignalType, Strategy

from .barmodel import LEGACY, BarCosts, BarModelError, BarOptions, bar_events, run_bars
from .metrics import Metrics, compute_metrics

BASE_NS = 946_684_800 * 1_000_000_000  # 2000-01-01T00:00:00Z, the synthetic clock's origin
SPACING_NS = 60 * 1_000_000_000


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


def _mask(entry_mask, n: int):
    if entry_mask is None:
        return None
    mask = np.asarray(entry_mask, dtype=bool)
    if mask.shape != (n,):
        raise BarModelError(f"entry_mask length {mask.shape} != number of candles {n}")
    return tuple(bool(x) for x in mask)


def _rows(candles: pd.DataFrame) -> list[dict]:
    cols = {k: candles[k].to_numpy() for k in ("open", "high", "low", "close")}
    vol = candles["volume"].to_numpy() if "volume" in candles.columns else None
    out = []
    for i in range(len(candles)):
        r = {k: float(cols[k][i]) for k in cols}
        r["volume"] = float(vol[i]) if vol is not None else 0.0
        out.append(r)
    return out


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
    return _on_core(strategy, candles, None, initial_equity_jpy=initial_equity_jpy,
                    order_notional_jpy=order_notional_jpy, costs=costs, execution=execution,
                    maker_timeout_bars=maker_timeout_bars, allow_short=allow_short, swap_daily_pct=swap_daily_pct,
                    bar_seconds=bar_seconds, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                    max_hold_bars=max_hold_bars, exit_execution=exit_execution, maker_tp_pct=maker_tp_pct,
                    entry_mask=entry_mask, entry_sides=entry_sides, stop_mode=stop_mode,
                    stop_window_bars=stop_window_bars)


def _events(candles: pd.DataFrame) -> list:
    n = len(candles)
    return bar_events(_rows(candles), [BASE_NS + i * SPACING_NS for i in range(n)], SPACING_NS)


def _on_core(strategy: Strategy, candles: pd.DataFrame, events, *, initial_equity_jpy, order_notional_jpy, costs,
             execution, maker_timeout_bars, allow_short, swap_daily_pct, bar_seconds, stop_loss_pct,
             take_profit_pct, max_hold_bars, exit_execution, maker_tp_pct, entry_mask, entry_sides, stop_mode,
             stop_window_bars) -> BacktestResult:
    costs = costs or CostModel()
    n = len(candles)
    opts = BarOptions(
        initial_equity=initial_equity_jpy, order_notional=order_notional_jpy,
        costs=BarCosts(costs.taker_fee_pct, costs.maker_fee_pct, costs.slippage_pct, costs.spread_pct),
        execution=execution, maker_timeout_bars=maker_timeout_bars, allow_short=allow_short,
        swap_daily_pct=swap_daily_pct, bar_seconds=bar_seconds, stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct, max_hold_bars=max_hold_bars, exit_execution=exit_execution,
        maker_tp_pct=maker_tp_pct, entry_mask=None, entry_sides=entry_sides, stop_mode=stop_mode,
        stop_window_bars=stop_window_bars)
    opts.check(n)  # the old engine's option checks come before the mask's
    opts = BarOptions(**{**opts.__dict__, "entry_mask": _mask(entry_mask, n)})
    if events is None:
        events = _events(candles)

    def decide(k: int):
        sig = strategy.on_candles(candles.iloc[:k])
        t = sig.type
        if t is SignalType.BUY:
            return "BUY"
        if t is SignalType.SELL:
            return "SELL"
        if t is SignalType.CLOSE:
            return "CLOSE"
        return None

    res = run_bars(events, decide, opts, LEGACY, start=strategy.min_history)
    equity_curve = pd.Series(res.equity, index=candles.index, dtype=float) if n else \
        pd.Series(res.equity, index=candles.index, dtype=float)
    metrics = compute_metrics(res.trade_pnls, equity_curve, res.fees_total)
    return BacktestResult(metrics, equity_curve, list(res.trade_pnls), list(res.trade_log), res.missed_fills)

# --------------------------------------------------------------------------- the layer in front of the mouth
_COST_METHODS = ("buy_price", "sell_price", "fee", "maker_fee")
_COST_FIELDS = ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")


def _real(v) -> bool:
    return type(v) is not bool and isinstance(v, numbers.Real) and math.isfinite(float(v))


def _core_takes_costs(costs) -> bool:
    """The core's cost socket is a percentage model and its venue refuses a
    fill price <= 0: it can carry `costs` only when `costs` is a CostModel
    whose price and fee methods are CostModel's own, whose four percentages
    are finite numbers, and whose taker prices stay > 0 for every price > 0
    (1 - (spread/2 + slippage)/100 > 0 and 1 + (spread/2 + slippage)/100 > 0)."""
    if costs is None:
        return True
    if not isinstance(costs, CostModel):
        return False
    if any(getattr(type(costs), m) is not getattr(CostModel, m) for m in _COST_METHODS):
        return False
    if not all(_real(getattr(costs, f, None)) for f in _COST_FIELDS):
        return False
    half = (float(costs.spread_pct) / 2 + float(costs.slippage_pct)) / 100
    return 1 - half > 0 and 1 + half > 0


def _core_takes_options(order_notional_jpy, stop_loss_pct, take_profit_pct, maker_tp_pct) -> bool:
    """The core's order socket refuses a size that is not finite and > 0 (the
    old engine opened a position of notional / price whatever its sign), and
    a level from a NaN percentage compares differently: those runs are the
    old arithmetic's."""
    if not _real(order_notional_jpy) or not float(order_notional_jpy) > 0:
        return False
    return all(v is None or _real(v) for v in (stop_loss_pct, take_profit_pct, maker_tp_pct))


def route_of(candles: pd.DataFrame, costs=None, *, order_notional_jpy=3000.0, stop_loss_pct=None,
             take_profit_pct=None, maker_tp_pct=None):
    """("core", events) when the core can run this input as the old engine
    would, else ("old", None). Never calls a strategy; never raises."""
    try:
        if not _core_takes_costs(costs) or not _core_takes_options(order_notional_jpy, stop_loss_pct,
                                                                     take_profit_pct, maker_tp_pct):
            return "old", None
        return "core", _events(candles)
    except Exception:  # a row the core refuses, a missing column, a non-number: the old engine's own handling
        return "old", None


def run_backtest_as_old(
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
    """The old `run_backtest`, whole: the core when it can take the input,
    the old arithmetic when it cannot (module docstring)."""
    kw = dict(initial_equity_jpy=initial_equity_jpy, order_notional_jpy=order_notional_jpy, costs=costs,
              execution=execution, maker_timeout_bars=maker_timeout_bars, allow_short=allow_short,
              swap_daily_pct=swap_daily_pct, bar_seconds=bar_seconds, stop_loss_pct=stop_loss_pct,
              take_profit_pct=take_profit_pct, max_hold_bars=max_hold_bars, exit_execution=exit_execution,
              maker_tp_pct=maker_tp_pct, entry_mask=entry_mask, entry_sides=entry_sides, stop_mode=stop_mode,
              stop_window_bars=stop_window_bars)
    route, events = route_of(candles, costs, order_notional_jpy=order_notional_jpy, stop_loss_pct=stop_loss_pct,
                             take_profit_pct=take_profit_pct, maker_tp_pct=maker_tp_pct)
    if route == "core":
        return _on_core(strategy, candles, events, **kw)
    return _old_arithmetic(strategy, candles, **kw)




def evaluate_on_splits_as_old(strategy_cls: type[Strategy], params: dict,
                              candles: pd.DataFrame, *,
                              initial_equity_jpy: float = 6000.0,
                              order_notional_jpy: float = 3000.0,
                              costs: CostModel | None = None) -> dict[str, BacktestResult]:
    """Run the SAME parameter set on each split. Parameters may be chosen on
    training/validation only; out_of_sample is the final untouched verdict.

    The old `bot.backtest.walk_forward.evaluate_on_splits`, through the layer
    (`run_backtest_as_old`), so a split with a row the core refuses gives the
    old numbers, as the old function did."""
    from .walk_forward import split_data  # walk_forward imports this module
    splits = split_data(candles)
    out: dict[str, BacktestResult] = {}
    for name, data in (("training", splits.training), ("validation", splits.validation),
                       ("out_of_sample", splits.out_of_sample)):
        out[name] = run_backtest_as_old(strategy_cls(params), data, initial_equity_jpy=initial_equity_jpy,
                                        order_notional_jpy=order_notional_jpy, costs=costs)
    return out

# --------------------------------------------------------------------------- the old arithmetic (copied line for line)
# Everything below is src/bot/backtest/engine.py before the replacement
# (sha256 3c2fc35d...), from `class _PendingLimit` to the end of
# `run_backtest` (renamed `_old_arithmetic`), unchanged. It runs only for
# the inputs the core does not take (route_of). CostModel, BacktestResult and
# compute_metrics are this package's, which are the old ones bit for bit
# (tests/bt/compat/test_compat_golden.py).


@dataclass
class _PendingLimit:
    side: SignalType
    limit: float
    placed_bar: int




def _old_arithmetic(
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
