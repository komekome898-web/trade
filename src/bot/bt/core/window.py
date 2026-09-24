"""Read-only, revocable view of the strategy's history.

`EventWindow(history, end)` exposes `history[:end]` as a `Sequence` without
copying (O(1) to build). `history` is the engine's list of events already
DELIVERED to the strategy, appended to only between callbacks, so every
element of the backing list satisfies `received_time_ns <= now_ns` while
the callback runs: the future is not hidden behind a bound, it was never
put into the list.

When the callback returns (the engine's `alive()` turns false, or
`revoke()` is called) every further access raises `StaleContextError` and
the window's reading functions drop the backing list, so a window kept past
its callback shows nothing, rather than events delivered later. The window
holds the backing only inside those functions and its attributes cannot be
changed (round 9, LEAD_DESIGN s3.4).
"""
from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Any, Iterator, NamedTuple, Optional

from .errors import (
    BeforeFirstEventError,
    DroppedPositionError,
    FuturePositionError,
    OutsideAnswerError,
    StaleContextError,
)
from .events import Event


# The position rule of a history read, as ONE table of ranges (i0-r4-01,
# i0-r7-01). Every explicit bound -- an index, a slice start or stop, the
# start / stop of `index()` -- is first placed in the answer's own
# coordinate, c = b (b >= 0) or c = b + len (b < 0: Python's "count from
# the end"), and checked there against its role's range, BEFORE anything is
# cut; `tuple` slicing runs only on bounds already inside, so it never
# shortens an answer. The sign of a bound and the direction of the answer
# decide nothing on their own (i0-r7-01: negative slice bounds used to be
# cut by their sign, which on a newest-first answer skipped the future).
#
# Each role is (lowest c, highest c as an offset from len):
# * an index and a slice start name an ITEM: 0 <= c <= len-1;
# * a slice stop names a GAP: a forward stop c the gap between c-1 and c,
#   a backward stop c the gap between c and c+1; the len+1 gaps from
#   "before 0" to "after len-1" are inside: forward 0 <= c <= len, backward
#   -1 <= c <= len-1 (c = -1, written b = -(len+1), reads down to the
#   oldest). A gap outside names the one of its two neighbours nearer the
#   answer.
#
# WHICH error follows from the NAMED position (i0-r6-01), never from one
# fact about the answer as a whole: the answer knows its place in what
# the read reads (`AnswerPlace`), so the named position q is mapped back
# there (u = first + q * step) and the error says what is there -- an event
# not delivered yet (`FuturePositionError`, a `LookAheadError`), a
# delivered event outside the answer (`OutsideAnswerError`), a delivered
# event `history_limit` dropped (`DroppedPositionError`), or nothing
# (`BeforeFirstEventError`). Of two bounds outside, one naming an event
# not delivered yet is reported, else the start's.
POSITION_RULE: dict[str, tuple[int, int]] = {
    "index": (0, -1),
    "forward slice start": (0, -1),
    "forward slice stop": (0, 0),
    "backward slice start": (0, -1),
    "backward slice stop": (-1, -1),
}

POSITION_RULE_TEXT = (
    "every explicit bound (an index, a slice start or stop, index()'s start and stop) is placed in the "
    "answer's coordinate first (c = b, or b + len for b < 0) and checked there against its role's range, "
    "never cut before the check: an index and a slice start name an item (0 <= c <= len-1); a slice stop "
    "names a gap (forward 0 <= c <= len, backward -1 <= c <= len-1); a gap outside names its neighbour "
    "nearer the answer; the direction of the answer and the sign of a bound decide nothing on their own"
)


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


def _named(role: str, c: int, n: int) -> Optional[int]:
    """The answer position a bound of `role` at answer coordinate `c` names
    OUTSIDE the answer of `n`, or None when it is inside (POSITION_RULE)."""
    lowest, highest = POSITION_RULE[role]
    if lowest <= c <= n + highest:
        return None
    if role.endswith("stop"):  # a gap: its neighbour nearer the answer
        below, above = (c - 1, c) if role.startswith("forward") else (c, c + 1)
        return below if c > n + highest else above
    return c


def _outside(place: AnswerPlace, role: str, bound: int, q: int, n: int, shown: str) -> IndexError:
    """The error for naming answer position `q` (outside the answer), from
    what that position is in what the read reads."""
    u = place.first + q * place.step
    holds = f"it holds {n}, positions 0..{n - 1}" if n else "it holds no event"
    where = (
        f"{shown}: the {role} {bound} names position {q} of this answer ({holds}), which is "
        f"position {u} of what the read reads"
    )
    if u >= place.delivered:
        had = f"positions 0..{place.delivered - 1}" if place.delivered else "none"
        cls, why = FuturePositionError, (
            f"; {place.delivered} of those events had been delivered when the answer was made "
            f"({had}), so what position {u} names had not been delivered yet"
        )
    elif u >= 0:
        cls, why = OutsideAnswerError, (
            "; that event was delivered but is outside this answer (a time range, n or a slice "
            "ended it) -- read a wider range instead"
        )
    elif u >= -place.dropped:
        cls, why = DroppedPositionError, (
            f"; it lies before the oldest event the history keeps of what the read reads, among "
            f"the {place.dropped} delivered events history_limit dropped"
        )
    else:
        cls, why = BeforeFirstEventError, (
            "; it lies before the first event ever delivered of what the read reads"
            + (f" (the {place.dropped} history_limit dropped included)" if place.dropped else "")
            + ": nothing is there"
        )
    exc = cls(where + why)
    exc.answer_position, exc.read_position, exc.delivered = q, u, place.delivered
    return exc


def resolve_key(key: Any, n: int, place: AnswerPlace) -> Any:
    """THE rule (POSITION_RULE) for one key on an answer of `n` at `place`:
    an int index returns its answer coordinate (0 <= c < n); a slice returns
    a slice of plain ints, every bound read ONCE (its __index__) and
    checked BEFORE anything is cut, so slicing a sequence of `n` by it cuts
    nothing (a backward stop c = -1 is returned as None: "down to the
    oldest"). Raises the error of the named position otherwise. A step of
    0 is returned as it is (the sequence refuses it with ValueError)."""
    if type(key) is slice:  # slice cannot be subclassed; an object claiming to be one is not
        b0, b1, b2 = key.start, key.stop, key.step
        start = None if b0 is None else operator.index(b0)
        stop = None if b1 is None else operator.index(b1)
        step = None if b2 is None else operator.index(b2)
        st = 1 if step is None else step
        if st == 0:
            return slice(start, stop, step)
        way = "forward" if st > 0 else "backward"
        shown = f"[{start}:{stop}:{step}]"
        errors = []
        cs = ct = None
        if start is not None:
            cs = start if start >= 0 else start + n
            q = _named(f"{way} slice start", cs, n)
            if q is not None:
                errors.append(_outside(place, f"{way} slice start", start, q, n, shown))
        if stop is not None:
            ct = stop if stop >= 0 else stop + n
            q = _named(f"{way} slice stop", ct, n)
            if q is not None:
                errors.append(_outside(place, f"{way} slice stop", stop, q, n, shown))
        if errors:
            future = [e for e in errors if isinstance(e, FuturePositionError)]
            raise (future or errors)[0]
        return slice(cs, None if ct == -1 else ct, step)
    i = operator.index(key)
    c = i if i >= 0 else i + n
    if _named("index", c, n) is not None:
        raise _outside(place, "index", i, c, n, f"[{i}]")
    return c


def resolve_search(args: tuple, n: int, place: AnswerPlace) -> tuple[int, int]:
    """The start and stop of `index(value, start, stop)` (a forward range of
    the answer), by the same rule: (start, stop) as answer coordinates."""
    if len(args) > 2:
        raise TypeError(f"index expected at most 3 arguments, got {len(args) + 1}")
    key = resolve_key(slice(args[0] if args else None, args[1] if len(args) > 1 else None), n, place)
    return (0 if key.start is None else key.start), (n if key.stop is None else key.stop)


class DeliveredEvents(tuple):
    """What a history read (`StrategyContext.visible_events`) returns: a
    tuple of delivered events, oldest first (a backward slice of one is
    newest first). Every position `0 .. len-1` holds an event of the
    answer; naming a position outside it -- by an index, a slice bound or
    `index()`'s start / stop, of either sign, on an answer of either
    direction (`POSITION_RULE`) -- raises instead of returning a silently
    shortened or empty tuple. WHICH error follows from what the NAMED
    position is in what the read reads (`place`, i0-r6-01): an event not
    delivered yet -> `FuturePositionError` (an `IndexError` and a
    `LookAheadError`); a delivered event outside the answer ->
    `OutsideAnswerError`; a delivered event `history_limit` dropped ->
    `DroppedPositionError`; nothing -> `BeforeFirstEventError` (the last
    three are `OutsideAnswerError`s, not `LookAheadError`s). When two slice
    bounds are outside, one naming an event not delivered yet is reported
    first. Otherwise it is a plain tuple (equality, hashing, iteration,
    `len`), and a slice of it is again a `DeliveredEvents` under the same
    rule, with its own place computed from this one.

    The place is fixed when the answer is made and cannot be changed:
    `DeliveredEvents(items, first=..., delivered=...)` has no default for
    them -- the maker of an answer states where it lies. (It is kept in the
    instance's dict, as a tuple subclass cannot have slots; a strategy
    that rewrites it there by bypassing `__setattr__` only misleads itself
    about its own answer and is outside the contract, like bypassing a
    frozen carrier with `object.__setattr__` or calling
    `tuple.__getitem__` on the answer.)"""

    def __new__(cls, items: Any = (), *, first: int, delivered: int, step: int = 1, dropped: int = 0):
        self = tuple.__new__(cls, items)
        place = _checked_place(first, step, delivered, dropped, tuple.__len__(self))
        object.__setattr__(self, "_place", place)
        return self

    @classmethod
    def _placed(cls, items: Any, first: int, step: int, delivered: int, dropped: int) -> "DeliveredEvents":
        """The core's own maker (`visible_events`, a slice of an answer):
        the place is right by construction, so it is not checked again."""
        self = tuple.__new__(cls, items)
        object.__setattr__(self, "_place", AnswerPlace(first, step, delivered, dropped))
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
        p = self._place
        key = resolve_key(index, n, p)
        if type(key) is int:
            return tuple.__getitem__(self, key)
        items = tuple.__getitem__(self, key)  # every bound is inside: nothing is cut
        start, _stop, st = key.indices(n)
        return DeliveredEvents._placed(items, p.first + start * p.step, p.step * st, p.delivered, p.dropped)

    def index(self, value: Any, *args: Any) -> int:
        """`tuple.index`, with `start` and `stop` naming positions by the
        same rule as a forward slice `[start:stop]`."""
        start, stop = resolve_search(args, tuple.__len__(self), self._place)
        return tuple.index(self, value, start, stop)


def _rebuild(items: tuple, place: tuple) -> DeliveredEvents:
    first, step, delivered, dropped = place
    return DeliveredEvents(items, first=first, step=step, delivered=delivered, dropped=dropped)


def _getter(history: Any) -> Any:
    """The core's own read of a backing sequence: the base type's method (a
    `DeliveredList`'s own position rule is for the strategy's reads)."""
    if isinstance(history, list):
        return list.__getitem__
    if isinstance(history, tuple):
        return tuple.__getitem__
    return type(history).__getitem__


class EventWindow(Sequence):
    """The window a context holds over the history (the whole history or
    one type's): its first `end` events. Naming a position follows the same
    rule as an answer (`resolve_key`), with the window's own place: first
    0, step 1, delivered `end`, `dropped` delivered events before its oldest
    (history_limit); a slice of it is a `DeliveredEvents`.

    It holds no mutable object (round 9, LEAD_DESIGN s3.4): the backing list
    (the core's, which the core appends to) is held only inside the
    window's reading functions, never as an attribute, and the window's
    attributes cannot be assigned or deleted. It stops working when the
    engine's `alive()` (given) turns false at the end of its callback, or
    when `revoke()` is called; every access then raises `StaleContextError`
    and the functions drop the backing list, so a window kept past its
    callback shows nothing, rather than events delivered later. `_log` is a
    new tuple of the events it covers (empty once revoked)."""

    __slots__ = ("_read", "_range_of", "_ok", "_kill", "_end", "_dropped")

    def __init__(self, history: Sequence[Event], end: int, dropped: int = 0,
                 alive: Optional[Any] = None) -> None:
        get = _getter(history)
        backing: Any = history  # closure variables (not a container): only these functions see them
        live = True

        def ok() -> bool:
            return live and (alive is None or alive())

        def check() -> None:
            nonlocal backing
            if not ok():
                backing = ()
                raise StaleContextError("this history view belonged to a callback that has returned")

        def read(i: int) -> Event:
            check()
            return get(backing, i)

        def range_of(lo: int, hi: int) -> tuple:
            check()
            return tuple(get(backing, slice(lo, hi)))

        def kill() -> None:
            nonlocal backing, live
            backing, live = (), False

        put = object.__setattr__
        put(self, "_read", read)
        put(self, "_range_of", range_of)
        put(self, "_ok", ok)
        put(self, "_kill", kill)
        put(self, "_end", int(end))
        put(self, "_dropped", int(dropped))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("a history window cannot be changed")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("a history window cannot be changed")

    def revoke(self) -> None:
        self._kill()

    def _check(self) -> None:
        if not self._ok():
            self._kill()
            raise StaleContextError("this history view belonged to a callback that has returned")

    @property
    def _log(self) -> tuple:
        """The events this window covers, as a new tuple; () once revoked."""
        if not self._ok():
            return ()
        return self._range_of(0, self._end)

    def _place(self) -> AnswerPlace:
        return AnswerPlace(0, 1, self._end, self._dropped)

    def __len__(self) -> int:
        self._check()
        return self._end

    def __getitem__(self, index):
        self._check()
        end = self._end
        key = resolve_key(index, end, self._place())
        read = self._read
        if type(key) is int:
            return read(key)
        start, stop, step = key.indices(end)  # inside by the rule: nothing is cut
        # read the positions themselves: a negative start or stop of the
        # window's coordinate (an empty backward read, -1) is not a
        # position counted from the end of the backing list
        items = tuple([read(i) for i in range(start, stop, step)])
        return DeliveredEvents._placed(items, start, step, end, self._dropped)

    def _range(self, lo: int, hi: int) -> tuple:
        """The core's own read of events lo..hi-1 (0 <= lo <= hi <= end)."""
        return self._range_of(lo, hi)

    def index(self, value: Any, *args: Any) -> int:
        self._check()
        start, stop = resolve_search(args, self._end, self._place())
        read = self._read
        for i in range(start, stop):
            v = read(i)
            if v is value or v == value:
                return i
        raise ValueError(f"{value!r} is not in the window")

    def __iter__(self) -> Iterator[Event]:
        self._check()
        read = self._read
        for i in range(self._end):
            yield read(i)

    def __reversed__(self) -> Iterator[Event]:
        self._check()
        read = self._read
        for i in range(self._end - 1, -1, -1):
            yield read(i)

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventWindow(len={self._end}, revoked={not self._ok()})"
