"""Item 4: the bar backtest model of the new engine under the stated rules of
the scene set (tests/bt/battery/item_4/DEFINITIONS.md), and the mouth with the
research scripts' names and arguments on top of it (L-408 案2).

  barmodel     the bar model on the core (venue + account + cost sockets, the
               signal strategy); the one rule set "spec" (SPEC); run_bars
  engine       run_backtest / CostModel / BacktestResult (the mouth's names
               and arguments; bot.backtest.engine delegates here)
  metrics      Metrics / compute_metrics (bot.backtest.metrics delegates here)
  walk_forward Splits / split_data / evaluate_on_splits (bot.backtest.walk_forward
               delegates here) and the native split_rows (decimal arithmetic)

Tests: tests/bt/item_4/ (against the independent reference bot.bt.reference.bar_sim
and the scene set tests/bt/battery/item_4/).
"""
from .barmodel import (RULES, SPEC, BarCosts, BarModelError, BarOptions, BarRunResult, bar_events,
                       options_from_mapping, periods_per_year, rules_of, run_bars)
from .engine import BacktestResult, CostModel, run_backtest
from .metrics import Metrics, compute_metrics, compute_metrics_values
from .walk_forward import ARITHMETICS, DECIMAL, SplitError, Splits, evaluate_on_splits, split_bounds, split_data, \
    split_rows

__all__ = ["ARITHMETICS", "BacktestResult", "BarCosts", "BarModelError", "BarOptions", "BarRunResult", "CostModel",
           "DECIMAL", "Metrics", "RULES", "SPEC", "SplitError", "Splits", "bar_events", "compute_metrics",
           "compute_metrics_values", "evaluate_on_splits", "options_from_mapping", "periods_per_year", "rules_of",
           "run_backtest", "run_bars", "split_bounds", "split_data", "split_rows"]
