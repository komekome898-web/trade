"""Item 4 (old item 14): the old bar backtest's behaviour as selectable models
of the new engine, and the old names and arguments on top of them.

  barmodel     the bar model on the core (venue + account + cost sockets, the
               signal strategy); rule sets "legacy" (the old engine, bit for
               bit) and "spec" (the stated rules); run_bars
  engine       run_backtest / CostModel / BacktestResult (old names, old
               arguments, the "legacy" rule set)
  metrics      Metrics / compute_metrics (old names)
  walk_forward Splits / split_data / evaluate_on_splits (old names) and the
               native split_rows (binary or decimal arithmetic)
  models       one strategy description through several rule sets

Tests: tests/bt/compat/ (with the golden files of the old engine).
"""
from .barmodel import (LEGACY, RULES, SPEC, BarCosts, BarModelError, BarOptions, BarRules, BarRunResult, bar_events,
                       options_from_mapping, rules_of, run_bars)
from .engine import BacktestResult, CostModel, run_backtest
from .metrics import Metrics, compute_metrics, compute_metrics_values
from .walk_forward import SplitError, Splits, evaluate_on_splits, split_bounds, split_data, split_rows

__all__ = ["BacktestResult", "BarCosts", "BarModelError", "BarOptions", "BarRules", "BarRunResult", "CostModel", "LEGACY",
           "Metrics", "RULES", "SPEC", "SplitError", "Splits", "bar_events", "compute_metrics", "compute_metrics_values",
           "evaluate_on_splits", "options_from_mapping", "rules_of", "run_backtest", "run_bars", "split_bounds",
           "split_data", "split_rows"]
