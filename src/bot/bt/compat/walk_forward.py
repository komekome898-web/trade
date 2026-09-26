"""Row-fraction splits: the compatibility mouth of `bot.backtest.walk_forward`
(item 4: `split_data`, `evaluate_on_splits`) and the native split (`split_rows`,
rules D-1 / D-2 of the item-4 scene set).

  split_rows(n, train_frac, val_frac, arithmetic)
      rows 0..n-1, never reordered, never overlapping: training = the first
      floor(n * train) rows, validation up to floor(n * (train + val)),
      out-of-sample = the rest (last). Fractions in (0, 1), sum < 1, else
      refused. arithmetic "decimal" (the one arithmetic, D-1): the fractions
      are the written decimal values (0.7 + 0.2 = 0.9 exactly, so 100 rows
      split at 90).
  split_data(candles, train_frac=0.6, val_frac=0.2)
      the same names and arguments as bot.backtest.walk_forward, on the
      decimal arithmetic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext

import pandas as pd

from bot.strategy.base import Strategy

from .engine import BacktestResult, CostModel, run_backtest

DECIMAL = "decimal"  # the one arithmetic of the split (D-1: the written decimal values)
ARITHMETICS = (DECIMAL,)


class SplitError(ValueError):
    pass


@dataclass
class Splits:
    training: pd.DataFrame
    validation: pd.DataFrame
    out_of_sample: pd.DataFrame


def _frac(x, name: str) -> float:
    if type(x) is bool or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise SplitError(f"{name} must be a finite number, got {x!r}")
    return float(x)


def split_bounds(n: int, train_frac: float, val_frac: float, arithmetic: str) -> tuple[int, int]:
    """(end of training, end of validation) as row counts."""
    if type(n) is not int or n < 0:
        raise SplitError(f"n must be an int >= 0, got {n!r}")
    if arithmetic not in ARITHMETICS:
        raise SplitError(f"arithmetic must be one of {list(ARITHMETICS)}, got {arithmetic!r}")
    t, v = _frac(train_frac, "train_frac"), _frac(val_frac, "val_frac")
    dt, dv = Decimal(repr(t)), Decimal(repr(v))
    if not 0 < dt < 1 or not 0 < dv < 1 or dt + dv >= 1:
        raise SplitError("fractions must be in (0,1) and sum to < 1")
    with localcontext() as ctx:
        ctx.prec = 60
        return int((n * dt).to_integral_value(rounding="ROUND_FLOOR")), \
            int((n * (dt + dv)).to_integral_value(rounding="ROUND_FLOOR"))


def split_rows(n: int, train_frac: float, val_frac: float, arithmetic: str) -> dict:
    """{"training": [row positions], "validation": [...], "out_of_sample": [...]}."""
    a, b = split_bounds(n, train_frac, val_frac, arithmetic)
    return {"training": list(range(0, a)), "validation": list(range(a, b)), "out_of_sample": list(range(b, n))}


def split_data(candles: pd.DataFrame, train_frac: float = 0.6,
               val_frac: float = 0.2) -> Splits:
    """Chronological split (D-2) — no shuffling, no overlap, OOS strictly last."""
    t_end, v_end = split_bounds(len(candles), train_frac, val_frac, DECIMAL)
    return Splits(training=candles.iloc[:t_end], validation=candles.iloc[t_end:v_end],
                  out_of_sample=candles.iloc[v_end:])


def evaluate_on_splits(strategy_cls: type[Strategy], params: dict,
                       candles: pd.DataFrame, *,
                       initial_equity_jpy: float = 6000.0,
                       order_notional_jpy: float = 3000.0,
                       costs: CostModel | None = None) -> dict[str, BacktestResult]:
    """Run the SAME parameter set on each split. Parameters may be chosen on
    training/validation only; out_of_sample is the final untouched verdict."""
    splits = split_data(candles)
    out: dict[str, BacktestResult] = {}
    for name, data in (("training", splits.training), ("validation", splits.validation),
                       ("out_of_sample", splits.out_of_sample)):
        out[name] = run_backtest(strategy_cls(params), data, initial_equity_jpy=initial_equity_jpy,
                                 order_notional_jpy=order_notional_jpy, costs=costs)
    return out
