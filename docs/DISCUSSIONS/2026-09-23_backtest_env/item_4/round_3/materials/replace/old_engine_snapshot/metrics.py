"""Backtest performance metrics — the full set required by the project rules."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class Metrics:
    total_pnl_jpy: float
    num_trades: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    avg_win_jpy: float
    avg_loss_jpy: float
    risk_reward_ratio: float
    expectancy_per_trade_jpy: float
    total_fees_jpy: float

    def as_dict(self) -> dict:
        return asdict(self)


def compute_metrics(trade_pnls: list[float], equity_curve: pd.Series,
                    total_fees_jpy: float = 0.0,
                    periods_per_year: float = 365 * 24 * 60) -> Metrics:
    """trade_pnls: realized PnL per closed round-trip. equity_curve: per-bar equity."""
    pnls = np.asarray(trade_pnls, dtype=float)
    n = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0)

    # Sharpe from per-bar equity returns, annualized for the bar frequency
    rets = equity_curve.pct_change().dropna()
    sharpe = 0.0
    if len(rets) > 1 and rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(periods_per_year))

    peak = equity_curve.cummax()
    dd = ((peak - equity_curve) / peak * 100).max() if len(equity_curve) else 0.0

    max_consec = consec = 0
    for p in pnls:
        consec = consec + 1 if p < 0 else 0
        max_consec = max(max_consec, consec)

    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0  # negative
    rr = avg_win / abs(avg_loss) if avg_loss != 0 else 0.0

    return Metrics(
        total_pnl_jpy=float(pnls.sum()),
        num_trades=n,
        win_rate_pct=len(wins) / n * 100 if n else 0.0,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe,
        max_drawdown_pct=float(dd),
        max_consecutive_losses=max_consec,
        avg_win_jpy=avg_win,
        avg_loss_jpy=avg_loss,
        risk_reward_ratio=rr,
        expectancy_per_trade_jpy=float(pnls.mean()) if n else 0.0,
        total_fees_jpy=total_fees_jpy,
    )
