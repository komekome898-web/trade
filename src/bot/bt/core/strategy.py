"""Strategy interface for the new engine (item 0's half of V5; item 2/3/4/5/6
supply what a strategy's orders actually do once placed).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .api import StrategyContext
from .events import Event


class Strategy(ABC):
    @abstractmethod
    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        """Called once per event, in the deterministic order `clock.py`
        defines. `event` is also reachable as `ctx.current_event` -- both
        are passed for convenience, they are the same object. The strategy
        must not retain `ctx` past this call and use it later: `CoreEngine`
        builds a fresh `StrategyContext` for every event and never reuses
        one, so a stashed reference simply stops being updated -- it does
        not let the strategy see a `now` that has since moved forward."""
