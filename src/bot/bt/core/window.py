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


class DeliveredEvents(tuple):
    """What a history read (`StrategyContext.visible_events`) returns: a
    tuple of delivered events, oldest first. Every position `0 .. len-1`
    holds an event already delivered; a position after the newest is the
    future. Naming one -- an index `>= len`, or a slice with an explicit
    non-negative start or stop past the end (for a backward slice: a start
    at or past the end) -- raises `FuturePositionError` (an `IndexError`
    and a `LookAheadError`) instead of returning a silently shortened or
    empty tuple. Negative positions count back from the newest and can
    only name the past; a slice reaching before the oldest is cut at it (as
    for any tuple). Otherwise it is a plain tuple (equality, hashing,
    iteration, `len`)."""

    __slots__ = ()

    def __getitem__(self, index):
        n = len(self)
        if isinstance(index, slice):
            step = 1 if index.step is None else operator.index(index.step)
            start = None if index.start is None else operator.index(index.start)
            stop = None if index.stop is None else operator.index(index.stop)
            ahead = (
                (start is not None and start >= 0 and (start > n if step > 0 else start >= n))
                or (step > 0 and stop is not None and stop > n)
            )
            if ahead:
                raise FuturePositionError(
                    f"slice [{index.start}:{index.stop}:{index.step}] names positions after the newest "
                    f"delivered event (there are {n}); those events have not been delivered"
                )
            return DeliveredEvents(tuple.__getitem__(self, index))
        i = operator.index(index)
        if i >= n:
            raise FuturePositionError(
                f"index {i} is after the newest delivered event (there are {n}); "
                f"that event has not been delivered"
            )
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
