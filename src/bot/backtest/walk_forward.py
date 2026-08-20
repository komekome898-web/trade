"""Time-ordered Training / Validation / Out-of-Sample splitting and
walk-forward evaluation to guard against overfitting."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bot.backtest.engine import BacktestResult, CostModel, run_backtest
from bot.strategy.base import Strategy


@dataclass
class Splits:
    training: pd.DataFrame
    validation: pd.DataFrame
    out_of_sample: pd.DataFrame


def split_data(candles: pd.DataFrame, train_frac: float = 0.6,
               val_frac: float = 0.2) -> Splits:
    """Chronological split — no shuffling, no overlap, OOS strictly last."""
    if not 0 < train_frac < 1 or not 0 < val_frac < 1 or train_frac + val_frac >= 1:
        raise ValueError("fractions must be in (0,1) and sum to < 1")
    n = len(candles)
    t_end = int(n * train_frac)
    v_end = int(n * (train_frac + val_frac))
    return Splits(
        training=candles.iloc[:t_end],
        validation=candles.iloc[t_end:v_end],
        out_of_sample=candles.iloc[v_end:],
    )


def evaluate_on_splits(strategy_cls: type[Strategy], params: dict,
                       candles: pd.DataFrame, *,
                       initial_equity_jpy: float = 6000.0,
                       order_notional_jpy: float = 3000.0,
                       costs: CostModel | None = None) -> dict[str, BacktestResult]:
    """Run the SAME parameter set on each split. Parameters may be chosen on
    training/validation only; out_of_sample is the final untouched verdict."""
    splits = split_data(candles)
    out: dict[str, BacktestResult] = {}
    for name, data in (("training", splits.training),
                       ("validation", splits.validation),
                       ("out_of_sample", splits.out_of_sample)):
        out[name] = run_backtest(
            strategy_cls(params), data,
            initial_equity_jpy=initial_equity_jpy,
            order_notional_jpy=order_notional_jpy,
            costs=costs,
        )
    return out
