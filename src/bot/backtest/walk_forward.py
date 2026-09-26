"""The names the research scripts import (`Splits`, `split_data`,
`evaluate_on_splits`), delegated to the new engine's mouth
`bot.bt.compat.walk_forward` (item 4). No arithmetic lives here.
"""
from __future__ import annotations

from bot.bt.compat.walk_forward import Splits, evaluate_on_splits, split_data

__all__ = ["Splits", "evaluate_on_splits", "split_data"]
