"""The names the research scripts import (`run_backtest`, `CostModel`,
`BacktestResult`), delegated to the new engine's mouth `bot.bt.compat.engine`
(item 4, L-406 「2.案1」: the scripts are not touched; L-408 「案2」: the mouth
with the same names and arguments is written on the new engine). No
arithmetic lives here.
"""
from __future__ import annotations

from bot.bt.compat.engine import BacktestResult, CostModel, run_backtest

__all__ = ["BacktestResult", "CostModel", "run_backtest"]
