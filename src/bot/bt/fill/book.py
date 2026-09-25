"""The venue's copy of the displayed (external) book: snapshots and deltas,
and what our own aggressive executions took from it since the last update.
Our own resting orders are never in it (the data does not contain them)."""
from __future__ import annotations

from typing import Optional

from bot.bt.core import BookDeltaEvent, BookSnapshotEvent

_EPS = 1e-12


class ExternalBook:
    def __init__(self) -> None:
        self.bids: list[list[float]] = []  # [price, size], best (highest) first
        self.asks: list[list[float]] = []  # best (lowest) first
        self.seen = False  # any snapshot or delta applied
        self.snapshot_time_ns: Optional[int] = None
        # since when the whole book is known from data: the last snapshot, or,
        # for a book kept by deltas only, the last delta
        self.fresh_since_ns: int = -(2 ** 63)

    def apply_snapshot(self, ev: BookSnapshotEvent, t: int) -> None:
        self.bids = [[float(p), float(s)] for p, s in ev.bids if s > 0]
        self.asks = [[float(p), float(s)] for p, s in ev.asks if s > 0]
        self.seen = True
        self.snapshot_time_ns = t
        self.fresh_since_ns = t

    def apply_delta(self, ev: BookDeltaEvent, t: int) -> None:
        levels = self.bids if ev.side == "bid" else self.asks
        desc = ev.side == "bid"
        for i, (p, _s) in enumerate(levels):
            if p == ev.price:
                if ev.size > 0:
                    levels[i][1] = float(ev.size)
                else:
                    del levels[i]
                break
            if (p < ev.price) if desc else (p > ev.price):
                if ev.size > 0:
                    levels.insert(i, [float(ev.price), float(ev.size)])
                break
        else:
            if ev.size > 0:
                levels.append([float(ev.price), float(ev.size)])
        self.seen = True
        if self.snapshot_time_ns is None:
            self.fresh_since_ns = t

    def side(self, name: str) -> list[list[float]]:
        """"bid" or "ask" levels."""
        return self.bids if name == "bid" else self.asks

    def best(self, name: str) -> Optional[float]:
        for p, s in self.side(name):
            if s > _EPS:
                return p
        return None

    def size_at(self, name: str, price: float) -> float:
        for p, s in self.side(name):
            if p == price:
                return s
        return 0.0

    def consume(self, name: str, price: float, qty: float) -> None:
        for lvl in self.side(name):
            if lvl[0] == price:
                lvl[1] = max(lvl[1] - qty, 0.0)
                return

    def mid(self) -> Optional[float]:
        b, a = self.best("bid"), self.best("ask")
        if b is None or a is None:
            return None
        return (b + a) / 2.0
