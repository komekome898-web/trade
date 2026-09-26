"""Item 3 (old item 9): metrics that keep the distribution, and their exports.

Fixed requirements: docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/REQUIREMENTS.md
(C3-11 .. C3-15). Tests: tests/bt/item_3/.

  metrics  per-trade bp, quantiles, share negative, trade hours and bp per
           hour, fill rate and missed orders, markout, cost breakdown, exit
           reasons, drawdown (every definition written once in its docstring)
  trades   round trips from fills (FIFO lots), each with its exit reason
  exports  the one writer of metric files; every file carries its purpose
"""
from .errors import ReportError
from .exports import PURPOSES, RESEARCH, SMOKE, SMOKE_WARNING, check_purpose, read_export, write_export
from .metrics import (bp_per_hour, cost_breakdown, drawdown, exit_reasons, exposure, fill_metrics, markout,
                      neg_frac, per_trade_bp, quantiles, trade_distribution)
from .trades import open_lots, round_trips

__all__ = ["PURPOSES", "RESEARCH", "ReportError", "SMOKE", "SMOKE_WARNING", "bp_per_hour", "check_purpose",
           "cost_breakdown", "drawdown", "exit_reasons", "exposure", "fill_metrics", "markout", "neg_frac",
           "open_lots", "per_trade_bp", "quantiles", "read_export", "round_trips", "trade_distribution",
           "write_export"]
