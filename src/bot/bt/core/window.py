"""Read-only, revocable view of the strategy's history.

`EventWindow(history, end)` exposes `history[:end]` as a `Sequence` without
copying (O(1) to build). `history` is the engine's list of events already
DELIVERED to the strategy, appended to only between callbacks, so every
element of the backing list satisfies `received_time_ns <= now_ns` while
the callback runs: the future is not hidden behind a bound, it was never
put into the list.

`revoke()` is called by the engine when the callback returns: the window
drops its reference to the history (the backing becomes an empty tuple) and
every further access raises `StaleContextError`, so a window kept past its
callback shows nothing, rather than events delivered later.
"""
from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Iterator

from .errors import FuturePositionError, StaleContextError
from .events import Event


# The position rule of a history read, as ONE table (i0-r4-01). A bound of
# an index or a slice has a role; each role says how far the position it
# names may go, as an offset from `len` (the count of events in the
# answer): an INCLUSIVE bound (an index, the first position a slice reads,
# and the exclusive old-side end of a backward slice, which names an event
# that must be there) may name at most `len - 1`; the exclusive end of a
# FORWARD slice may be `len` itself -- "up to the end of what was
# delivered" -- and no more. An explicit non-negative bound past its limit
# names a position after the newest event of the answer and raises
# `FuturePositionError`. Negative bounds count back from the newest and can
# only name the past (a slice reaching before the oldest is cut at it, as
# for any tuple). `DeliveredEvents.__getitem__` only looks bounds up here.
POSITION_RULE: dict[str, int] = {
    "index": -1,
    "forward slice start": -1,
    "forward slice stop": 0,
    "backward slice start": -1,
    "backward slice stop": -1,
}


def _check_bound(role: str, bound, n: int, shown: str) -> None:
    if bound is None:
        return
    b = operator.index(bound)
    if b >= 0 and b > n + POSITION_RULE[role]:
        raise FuturePositionError(
            f"{shown}: the {role} {b} names a position after the last event of this answer "
            f"(it holds {n}, positions 0..{n - 1}); an answer that ends at the newest delivered "
            f"event has nothing after it but events not delivered yet"
        )


class DeliveredEvents(tuple):
    """What a history read (`StrategyContext.visible_events`) returns: a
    tuple of delivered events, oldest first. Every position `0 .. len-1`
    holds an event of the answer; naming a position after its last event
    -- by an index or by an explicit non-negative slice bound, whatever
    the bound's role (`POSITION_RULE`) -- raises `FuturePositionError` (an
    `IndexError` and a `LookAheadError`) instead of returning a silently
    shortened or empty tuple. Negative positions count back from the newest
    and can only name the past. Otherwise it is a plain tuple (equality,
    hashing, iteration, `len`), and a slice of it is again a
    `DeliveredEvents` under the same rule."""

    __slots__ = ()

    def __getitem__(self, index):
        n = len(self)
        if isinstance(index, slice):
            shown = f"[{index.start}:{index.stop}:{index.step}]"
            step = 1 if index.step is None else operator.index(index.step)
            way = "forward" if step > 0 else "backward"  # step 0 is refused by tuple below
            if step != 0:
                _check_bound(f"{way} slice start", index.start, n, shown)
                _check_bound(f"{way} slice stop", index.stop, n, shown)
            return DeliveredEvents(tuple.__getitem__(self, index))
        i = operator.index(index)
        _check_bound("index", i, n, f"[{i}]")
        return tuple.__getitem__(self, i)


class EventWindow(Sequence):
    __slots__ = ("_log", "_end", "_revoked")

    def __init__(self, history: Sequence[Event], end: int) -> None:
        self._log = history
        self._end = end
        self._revoked = False

    def revoke(self) -> None:
        self._log = ()
        self._end = 0
        self._revoked = True

    def _check(self) -> None:
        if self._revoked:
            raise StaleContextError("this history view belonged to a callback that has returned")

    def __len__(self) -> int:
        self._check()
        return self._end

    def __getitem__(self, index):
        self._check()
        if isinstance(index, slice):
            start, stop, step = index.indices(self._end)
            return tuple(self._log[start:stop:step])
        if index < 0:
            index += self._end
        if not 0 <= index < self._end:
            raise IndexError(index)
        return self._log[index]

    def __iter__(self) -> Iterator[Event]:
        self._check()
        log, end = self._log, self._end
        for i in range(end):
            yield log[i]

    def __reversed__(self) -> Iterator[Event]:
        self._check()
        log = self._log
        for i in range(self._end - 1, -1, -1):
            yield log[i]

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventWindow(len={self._end}, revoked={self._revoked})"
