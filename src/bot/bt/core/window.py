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
from typing import Any, Iterator, NamedTuple

from .errors import (
    BeforeFirstEventError,
    DroppedPositionError,
    FuturePositionError,
    OutsideAnswerError,
    StaleContextError,
)
from .events import Event


# The position rule of a history read, as ONE table (i0-r4-01). A bound of
# an index or a slice has a role; each role says how far the position it
# names may go, as an offset from `len` (the count of events in the
# answer): an INCLUSIVE bound (an index, the first position a slice reads,
# and the exclusive old-side end of a backward slice, which names an event
# that must be there) may name at most `len - 1`; the exclusive end of a
# FORWARD slice may be `len` itself -- "up to the end of what was
# delivered" -- and no more (it names position `bound - 1`). An explicit
# non-negative bound past its limit, and a negative INDEX before the
# oldest (`< -len`), name a position outside the answer and raise. Negative
# SLICE bounds count back from the newest and are cut at the answer's ends,
# as for any tuple (a cut only ever shortens towards what the answer
# holds). `DeliveredEvents.__getitem__` only looks bounds up here.
#
# WHICH error follows from the NAMED position (i0-r6-01), never from one
# fact about the answer as a whole: the answer knows its place in what
# the read reads (`AnswerPlace`), so the named position is mapped back
# there and the error says what is there -- an event not delivered yet
# (`FuturePositionError`, a `LookAheadError`), a delivered event outside
# the answer (`OutsideAnswerError`), a delivered event `history_limit`
# dropped (`DroppedPositionError`), or nothing (`BeforeFirstEventError`).
POSITION_RULE: dict[str, int] = {
    "index": -1,
    "forward slice start": -1,
    "forward slice stop": 0,
    "backward slice start": -1,
    "backward slice stop": -1,
}


class AnswerPlace(NamedTuple):
    """Where an answer lies in what its read reads (the delivered events of
    the read's type, or all of them, in delivery order; the history's kept
    part when `history_limit` drops some): answer position `i` is position
    `first + i * step` there. `delivered` is how many events of it had
    been delivered when the answer was made (the read's `now_ns`; an
    answer kept past its callback still speaks of that instant).
    `dropped`: how many delivered events of it lie before its oldest kept
    one, which `history_limit` dropped (positions -dropped .. -1 there;
    before them nothing was ever delivered)."""

    first: int
    step: int
    delivered: int
    dropped: int


def _checked_place(first: Any, step: Any, delivered: Any, dropped: Any, n: int) -> AnswerPlace:
    for name, v in (("first", first), ("step", step), ("delivered", delivered), ("dropped", dropped)):
        if type(v) is not int:
            raise TypeError(f"AnswerPlace.{name} must be an int, got {type(v).__qualname__}")
    if step == 0 or delivered < 0 or dropped < 0:
        raise ValueError(
            f"AnswerPlace step {step} / delivered {delivered} / dropped {dropped}: step must be "
            f"non-zero, delivered and dropped >= 0"
        )
    if n and not (0 <= first < delivered and 0 <= first + (n - 1) * step < delivered):
        raise ValueError(
            f"an answer of {n} events at positions {first}, {first + step}, ... of what the read reads "
            f"must lie within the {delivered} delivered ones"
        )
    return AnswerPlace(first, step, delivered, dropped)


class DeliveredEvents(tuple):
    """What a history read (`StrategyContext.visible_events`) returns: a
    tuple of delivered events, oldest first (a backward slice of one is
    newest first). Every position `0 .. len-1` holds an event of the
    answer; naming a position outside it -- by an index `>= len` or
    `< -len`, or by an explicit non-negative slice bound past its limit
    (`POSITION_RULE`) -- raises instead of returning a silently shortened
    or empty tuple. WHICH error follows from what the NAMED position is in
    what the read reads (`place`, i0-r6-01): an event not delivered yet
    -> `FuturePositionError` (an `IndexError` and a `LookAheadError`); a
    delivered event outside the answer -> `OutsideAnswerError`; a
    delivered event `history_limit` dropped -> `DroppedPositionError`;
    nothing -> `BeforeFirstEventError` (the last three are
    `OutsideAnswerError`s, not `LookAheadError`s). When two slice bounds
    are outside, one naming an event not delivered yet is reported first.
    Otherwise it is a plain tuple (equality, hashing, iteration, `len`),
    and a slice of it is again a `DeliveredEvents` under the same rule,
    with its own place computed from this one.

    The place is fixed when the answer is made and cannot be changed:
    `DeliveredEvents(items, first=..., delivered=...)` has no default for
    them -- the maker of an answer states where it lies. (It is kept in the
    instance's dict, as a tuple subclass cannot have slots; a strategy
    that rewrites it there by bypassing `__setattr__` only misleads itself
    about its own answer and is outside the contract, like bypassing a
    frozen carrier with `object.__setattr__`.)"""

    def __new__(cls, items: Any = (), *, first: int, delivered: int, step: int = 1, dropped: int = 0):
        self = tuple.__new__(cls, items)
        place = _checked_place(first, step, delivered, dropped, tuple.__len__(self))
        object.__setattr__(self, "_place", place)
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("a history answer cannot be changed")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("a history answer cannot be changed")

    def __reduce__(self):
        return (_rebuild, (tuple(self), tuple(self._place)))

    @property
    def place(self) -> AnswerPlace:
        return self._place

    @property
    def next_is_undelivered(self) -> bool:
        """Is the position after the last event (in the answer's own
        direction) an event not delivered yet?"""
        p = self._place
        return p.first + tuple.__len__(self) * p.step >= p.delivered

    def __getitem__(self, index):
        n = tuple.__len__(self)
        if type(index) is slice:  # slice cannot be subclassed; an object claiming to be one is not
            # each bound read ONCE (its __index__), then the same ints are
            # checked, cut and placed
            key = slice(*(None if b is None else operator.index(b) for b in (index.start, index.stop, index.step)))
            step = 1 if key.step is None else key.step
            if step != 0:  # step 0 is refused by tuple below
                way = "forward" if step > 0 else "backward"
                self._check_bounds(((f"{way} slice start", key.start), (f"{way} slice stop", key.stop)),
                                   n, f"[{key.start}:{key.stop}:{key.step}]")
            items = tuple.__getitem__(self, key)
            start, _stop, st = key.indices(n)
            p = self._place
            return DeliveredEvents(items, first=p.first + start * p.step, step=p.step * st,
                                   delivered=p.delivered, dropped=p.dropped)
        i = operator.index(index)
        if i >= n or i < -n:
            raise self._outside("index", i, i if i >= 0 else i + n, n, f"[{i}]")
        return tuple.__getitem__(self, i)

    def _check_bounds(self, bounds: tuple, n: int, shown: str) -> None:
        errors = []
        for role, b in bounds:
            if b is not None and b >= 0 and b > n + POSITION_RULE[role]:
                errors.append(self._outside(role, b, b - 1 - POSITION_RULE[role], n, shown))
        if errors:
            future = [e for e in errors if isinstance(e, FuturePositionError)]
            raise (future or errors)[0]

    def _outside(self, role: str, bound: int, q: int, n: int, shown: str) -> IndexError:
        """The error for naming answer position `q` (outside the answer),
        from what that position is in what the read reads."""
        p = self._place
        u = p.first + q * p.step
        where = (
            f"{shown}: the {role} {bound} names position {q} of this answer (it holds {n}, positions "
            f"0..{n - 1}), which is position {u} of what the read reads"
        )
        if u >= p.delivered:
            cls, why = FuturePositionError, (
                f"; {p.delivered} of those events had been delivered when the answer was made "
                f"(positions 0..{p.delivered - 1}), so what position {u} names had not been delivered yet"
            )
        elif u >= 0:
            cls, why = OutsideAnswerError, (
                "; that event was delivered but is outside this answer (a time range, n or a slice "
                "ended it) -- read a wider range instead"
            )
        elif u >= -p.dropped:
            cls, why = DroppedPositionError, (
                f"; it lies before the oldest event the history keeps of what the read reads, among "
                f"the {p.dropped} delivered events history_limit dropped"
            )
        else:
            cls, why = BeforeFirstEventError, (
                f"; it lies before the first event ever delivered of what the read reads "
                f"({p.dropped} dropped ones included): nothing is there"
            )
        exc = cls(where + why)
        exc.answer_position, exc.read_position, exc.delivered = q, u, p.delivered
        return exc


def _rebuild(items: tuple, place: tuple) -> DeliveredEvents:
    first, step, delivered, dropped = place
    return DeliveredEvents(items, first=first, step=step, delivered=delivered, dropped=dropped)


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
