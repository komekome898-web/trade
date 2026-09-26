"""The metric set of the bar model, and the compatibility mouth of
`bot.backtest.metrics` (item 4: 「`compute_metrics` の全指標」).

The same names and arguments as that module (`Metrics`, `compute_metrics`).
Definitions (M-1 .. M-12 of the item-4 scene set), for per-trade PnLs p (n of
them) and a per-bar equity e:

  total_pnl_jpy            sum p
  num_trades               n
  win_rate_pct             (#p > 0) / n * 100, 0 when n = 0
  profit_factor            sum(p > 0) / |sum(p < 0)|; with no loss: inf when
                           some gain, else 0
  sharpe_ratio             mean(r) / std(r, ddof=1) * sqrt(periods_per_year),
                           r = e's per-bar pct change; 0 unless len(r) > 1
                           and std > 0. periods_per_year = 365 * 86400 / bar
                           seconds (M-5); the mouth's default is the value for
                           its default bar_seconds = 60
  max_drawdown_pct         max((running max of e - e) / running max * 100)
  max_consecutive_losses   longest run of p < 0 (a 0 breaks the run)
  avg_win_jpy / avg_loss_jpy   mean of p > 0 / of p < 0 (negative), 0 if none
  risk_reward_ratio        avg_win / |avg_loss|, 0 when avg_loss = 0
  expectancy_per_trade_jpy sum p / n, 0 when n = 0
  total_fees_jpy           as given

The arithmetic is pandas / numpy's (tests/bt/battery/item_4: the I4-17 scenes
hold the values against the definitions).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

PERIODS_PER_YEAR_60S = 365 * 24 * 60  # M-5 for 60-second bars: 365 * 86400 / 60


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
                    periods_per_year: float = PERIODS_PER_YEAR_60S) -> Metrics:
    """trade_pnls: realized PnL per closed round-trip. equity_curve: per-bar equity."""
    pnls = np.asarray(trade_pnls, dtype=float)
    n = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0
    rets = equity_curve.pct_change().dropna()
    sharpe = 0.0
    if len(rets) > 1 and rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(periods_per_year))
    peak = equity_curve.cummax()
    dd = ((peak - equity_curve) / peak * 100).max() if len(equity_curve) else 0.0
    longest = run = 0
    for p in pnls:
        run = run + 1 if p < 0 else 0
        longest = max(longest, run)
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    rr = avg_win / abs(avg_loss) if avg_loss != 0 else 0.0
    return Metrics(
        total_pnl_jpy=float(pnls.sum()),
        num_trades=n,
        win_rate_pct=len(wins) / n * 100 if n else 0.0,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe,
        max_drawdown_pct=float(dd),
        max_consecutive_losses=longest,
        avg_win_jpy=avg_win,
        avg_loss_jpy=avg_loss,
        risk_reward_ratio=rr,
        expectancy_per_trade_jpy=float(pnls.mean()) if n else 0.0,
        total_fees_jpy=total_fees_jpy,
    )


def compute_metrics_values(trade_pnls, equity, total_fees: float, periods_per_year: float) -> dict:
    """The metric set as a plain dict, from a plain equity list."""
    return compute_metrics(list(trade_pnls), pd.Series(list(equity), dtype=float), total_fees,
                           periods_per_year=periods_per_year).as_dict()
