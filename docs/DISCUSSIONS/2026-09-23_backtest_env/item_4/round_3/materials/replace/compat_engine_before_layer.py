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

One difference from the old engine, on purpose: a row that the core cannot
take as a bar (a NaN, a price <= 0, high below max(open, close), low above
min(open, close)) is refused with a ValueError instead of computing a
number from it.
"""
from __future__ import annotations

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
    events = bar_events(_rows(candles), [BASE_NS + i * SPACING_NS for i in range(n)], SPACING_NS)

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
