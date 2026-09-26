"""Backtest performance metrics — the full set required by the project rules.

Since item 4 of the backtest-environment work (finishing condition 3,
2026-09-26) the names are the compatibility mouth `bot.bt.compat.metrics`
(the same definitions, the old arithmetic bit for bit: tests/bt/compat/).
The old module is kept under docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/
round_3/materials/replace/old_engine_snapshot/metrics.py.

compute_metrics(trade_pnls, equity_curve, total_fees_jpy=0.0,
periods_per_year=365 * 24 * 60): trade_pnls is the realized PnL per closed
round-trip, equity_curve the per-bar equity; Sharpe from per-bar equity
returns, annualized for the bar frequency; avg_loss_jpy is negative.
"""
from __future__ import annotations

from bot.bt.compat.metrics import Metrics, compute_metrics  # noqa: F401

__all__ = ["Metrics", "compute_metrics"]
