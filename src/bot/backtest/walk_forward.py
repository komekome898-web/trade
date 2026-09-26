"""Time-ordered Training / Validation / Out-of-Sample splitting and
walk-forward evaluation to guard against overfitting.

Since item 4 of the backtest-environment work (finishing condition 3,
2026-09-26) the names are the compatibility mouth `bot.bt.compat`:
split_data — chronological split, no shuffling, no overlap, OOS strictly
last, the old float arithmetic (int(n * train_frac), int(n * (train_frac +
val_frac))), fractions in (0, 1) summing to < 1 else ValueError;
evaluate_on_splits — the SAME parameter set on each split (parameters may be
chosen on training/validation only; out_of_sample is the final untouched
verdict), through the layer that gives the old numbers for every input the
old engine took. The old module is kept under docs/DISCUSSIONS/
2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/.
"""
from __future__ import annotations

from bot.backtest.engine import BacktestResult, CostModel, run_backtest  # noqa: F401  (the old module imported these)
from bot.bt.compat.engine import evaluate_on_splits_as_old as evaluate_on_splits  # noqa: F401
from bot.bt.compat.walk_forward import Splits, split_data  # noqa: F401
from bot.strategy.base import Strategy  # noqa: F401  (the old module imported this)

__all__ = ["Splits", "evaluate_on_splits", "split_data"]
