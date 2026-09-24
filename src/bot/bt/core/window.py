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

from .errors import FuturePositionError, OutsideAnswerError, StaleContextError
from .events import Event


# The position rule of a history read, as ONE table (i0-r4-01). A bound of
# an index or a slice has a role; each role says how far the position it
# names may go, as an offset from `len` (the count of events in the
# answer): an INCLUSIVE bound (an index, the first position a slice reads,
# and the exclusive old-side end of a backward slice, which names an event
# that must be there) may name at most `len - 1`; the exclusive end of a
# FORWARD slice may be `len` itself -- "up to the end of what was
# delivered" -- and no more. An explicit non-negative bound past its limit
# names a position after the last event of the answer and raises:
# `FuturePositionError` if the answer ends at the newest delivered event of
# what it reads (what follows is not delivered yet), `OutsideAnswerError`
# if it ends in the delivered past (DeliveredEvents.next_is_undelivered). Negative bounds count back from the newest and can
# only name the past (a slice reaching before the oldest is cut at it, as
# for any tuple). `DeliveredEvents.__getitem__` only looks bounds up here.
POSITION_RULE: dict[str, int] = {
    "index": -1,
    "forward slice start": -1,
    "forward slice stop": 0,
    "backward slice start": -1,
    "backward slice stop": -1,
}


def _check_bound(role: str, bound, n: int, shown: str, next_is_undelivered: bool) -> None:
    if bound is None:
        return
    b = operator.index(bound)
    if b >= 0 and b > n + POSITION_RULE[role]:
        where = f"the {role} {b} names a position after the last event of this answer (it holds {n}, positions 0..{n - 1})"
        if next_is_undelivered:
            raise FuturePositionError(
                f"{shown}: {where}; this answer ends at the newest delivered event of what it reads, "
                f"so what comes after it has not been delivered yet"
            )
        raise OutsideAnswerError(
            f"{shown}: {where}; this answer ends before the newest delivered event of what it reads "
            f"(a time range, n or a slice ended it), so the events after it were delivered but are "
            f"outside this answer -- read a wider range instead"
        )


class DeliveredEvents(tuple):
    """What a history read (`StrategyContext.visible_events`) returns: a
    tuple of delivered events, oldest first (a backward slice of one is
    newest first). Every position `0 .. len-1` holds an event of the
    answer; naming a position after its last event -- by an index or by an
    explicit non-negative slice bound, whatever the bound's role
    (`POSITION_RULE`) -- raises instead of returning a silently shortened
    or empty tuple. WHICH error depends on a fact the answer carries,
    `next_is_undelivered` (i0-r5-05): is the position after its last event
    an event not delivered yet? True for an answer that ends at the newest
    delivered event of what it reads -> `FuturePositionError` (an
    `IndexError` and a `LookAheadError`); False for one that ends in the
    delivered past (cut by `until_ns`, a slice, or read backwards) ->
    `OutsideAnswerError` (an `IndexError`, not a `LookAheadError`: those
    events were delivered, they are only outside the answer). Negative
    positions count back from the newest and can only name the past.
    Otherwise it is a plain tuple (equality, hashing, iteration, `len`),
    and a slice of it is again a `DeliveredEvents` under the same rule,
    carrying the fact for ITS last event.

    The fact is the class (`_EndsAtNewest` / `_EndsInPast`), fixed when
    the answer is made: `DeliveredEvents(items, next_is_undelivered=...)`
    has no default -- the maker of an answer states what follows it."""

    __slots__ = ()
    next_is_undelivered: bool  # set by the two concrete classes below

    def __new__(cls, items=(), *, next_is_undelivered: bool):
        if type(next_is_undelivered) is not bool:
            raise TypeError("next_is_undelivered must be a bool")
        target = _EndsAtNewest if next_is_undelivered else _EndsInPast
        return tuple.__new__(target, items)

    def __reduce__(self):
        return (_rebuild, (tuple(self), self.next_is_undelivered))

    def __getitem__(self, index):
        n = len(self)
        after = self.next_is_undelivered
        if isinstance(index, slice):
            shown = f"[{index.start}:{index.stop}:{index.step}]"
            step = 1 if index.step is None else operator.index(index.step)
            way = "forward" if step > 0 else "backward"  # step 0 is refused by tuple below
            if step != 0:
                _check_bound(f"{way} slice start", index.start, n, shown, after)
                _check_bound(f"{way} slice stop", index.stop, n, shown, after)
            items = tuple.__getitem__(self, index)
            # What follows the slice's last event: the position after it in
            # this answer is start + len * step. Past this answer's end (a
            # forward slice that reaches it), it is what follows this
            # answer; inside it, or before its oldest (a backward slice),
            # it is a delivered event outside the slice.
            start, _stop, st = index.indices(n)
            nxt = start + len(items) * st
            return DeliveredEvents(items, next_is_undelivered=after and st > 0 and nxt >= n)
        i = operator.index(index)
        _check_bound("index", i, n, f"[{i}]", after)
        return tuple.__getitem__(self, i)


class _EndsAtNewest(DeliveredEvents):
    """An answer whose last event is the newest delivered one of what it
    reads: what follows it has not been delivered yet."""

    __slots__ = ()
    next_is_undelivered = True


class _EndsInPast(DeliveredEvents):
    """An answer that ends in the delivered past: what follows it was
    delivered but is outside the answer."""

    __slots__ = ()
    next_is_undelivered = False


def _rebuild(items: tuple, next_is_undelivered: bool) -> DeliveredEvents:
    return DeliveredEvents(items, next_is_undelivered=next_is_undelivered)


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
