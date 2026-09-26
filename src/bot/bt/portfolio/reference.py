"""Dated reference data the account applies: FX rollovers (swap) and corporate
actions (splits / reverse splits).

The core's event types are fixed by item 0 and have neither, so they reach the
account as a dated schedule. The account applies every item with time <= t
before it handles anything at t (a fill, a funding event, a market event), and
the rest up to the run's end in `MarginAccount.finish(end_ns)`. The strategy
does not receive these items.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Union

from bot.bt.orders.errors import ExecutionModelError


@dataclass(frozen=True)
class Rollover:
    """One FX value-date roll: every open position pays / receives one day of
    swap (a triple roll is three items)."""

    time_ns: int

    def __post_init__(self) -> None:
        if type(self.time_ns) is not int:
            raise ExecutionModelError(f"Rollover.time_ns must be an int, got {self.time_ns!r}")


@dataclass(frozen=True)
class CorporateAction:
    """A split (ratio > 1: one share becomes `ratio` shares) or a reverse
    split / consolidation (ratio < 1). Position *= ratio, average price and the
    last price /= ratio."""

    time_ns: int
    ratio: float

    def __post_init__(self) -> None:
        if type(self.time_ns) is not int:
            raise ExecutionModelError(f"CorporateAction.time_ns must be an int, got {self.time_ns!r}")
        if isinstance(self.ratio, bool) or not isinstance(self.ratio, (int, float)) or not math.isfinite(self.ratio) \
                or self.ratio <= 0 or self.ratio == 1:
            raise ExecutionModelError(f"CorporateAction.ratio must be finite, > 0 and not 1, got {self.ratio!r}")
        object.__setattr__(self, "ratio", float(self.ratio))


ReferenceItem = Union[Rollover, CorporateAction]


class ReferenceSchedule:
    def __init__(self, items: Sequence[ReferenceItem]) -> None:
        rows = []
        for i, it in enumerate(items):
            if type(it) not in (Rollover, CorporateAction):
                raise ExecutionModelError(f"ReferenceSchedule holds Rollover / CorporateAction, got {type(it).__name__}")
            rows.append((it.time_ns, i, it))
        rows.sort(key=lambda r: (r[0], r[1]))
        self._items = [r[2] for r in rows]
        self._next = 0

    def due(self, t: int) -> list[ReferenceItem]:
        out = []
        while self._next < len(self._items) and self._items[self._next].time_ns <= t:
            out.append(self._items[self._next])
            self._next += 1
        return out
