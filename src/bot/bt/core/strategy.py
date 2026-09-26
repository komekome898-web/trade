"""Strategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .api import StrategyContext
from .events import Event


class Strategy(ABC):
    @abstractmethod
    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        """Called once per delivered event, in the order ordering.py
        defines. `event is ctx.current_event`. `ctx` is revoked when this
        returns; do not keep it."""
