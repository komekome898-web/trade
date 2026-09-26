"""A per-order (L3) feed for the venue: which external orders joined and left
each price level, and when.

The core has no event type for per-order book data (its event types are fixed
by item 0), so the feed is handed to the venue model as dated reference data
and applied in time order: every item with time <= t is applied before the
venue handles anything at t (a market event, an order or a cancel arriving at
t). The strategy does not receive these items. The two cancel stances that
read it (`l3_advance`, `l3_mark`) need it; the other stances do not use it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Union

from .spec import FillSpecError


@dataclass(frozen=True)
class L3Add:
    time_ns: int
    order_id: str
    side: str  # "bid" | "ask"
    price: float
    size: float

    def __post_init__(self) -> None:
        if type(self.time_ns) is not int or type(self.order_id) is not str or not self.order_id:
            raise FillSpecError(f"L3Add needs an int time and a non-empty order id: {self!r}")
        if self.side not in ("bid", "ask"):
            raise FillSpecError(f"L3Add.side must be 'bid' or 'ask', got {self.side!r}")
        if not (float(self.price) > 0 and float(self.size) > 0):
            raise FillSpecError(f"L3Add price and size must be > 0: {self!r}")


@dataclass(frozen=True)
class L3Cancel:
    time_ns: int
    order_id: str

    def __post_init__(self) -> None:
        if type(self.time_ns) is not int or type(self.order_id) is not str or not self.order_id:
            raise FillSpecError(f"L3Cancel needs an int time and a non-empty order id: {self!r}")


L3Item = Union[L3Add, L3Cancel]


class L3Feed:
    def __init__(self, items: Sequence[L3Item]) -> None:
        rows = []
        for i, it in enumerate(items):
            if type(it) not in (L3Add, L3Cancel):
                raise FillSpecError(f"L3Feed holds L3Add / L3Cancel, got {type(it).__name__}")
            rows.append((it.time_ns, i, it))
        rows.sort(key=lambda r: (r[0], r[1]))
        self._items = [r[2] for r in rows]
        self._next = 0

    def due(self, t: int) -> list[L3Item]:
        """Items with time <= t not handed out yet, in time order."""
        out = []
        while self._next < len(self._items) and self._items[self._next].time_ns <= t:
            out.append(self._items[self._next])
            self._next += 1
        return out
