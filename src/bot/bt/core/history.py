"""The strategy's history of delivered events, and its ONE retention rule.

Without a limit every delivered event is kept. With `history_limit = N`
the rule is per event type: each type keeps its latest N..2N delivered
events (amortised: when a type reaches 2N, its oldest events down to N - 1
are dropped, then the new one is appended). There is no second rule:

* the overall list is exactly the events that their type keeps, in
  delivery order -- it is rebuilt from the types whenever a type drops
  events, so `overall filtered by type == that type's list` holds by
  construction (finding i0-r2-03: two lists with two independent rules
  disagreed);
* what was dropped is recorded as facts, per type, for EVERY dropped event:
  its delivery number (`seq`) and received time, two int64 each (round 10,
  i0-r9-01; the event objects are let go: the limit bounds the events held,
  not these facts). The strategy context uses them to refuse exactly the
  reads whose unlimited answer holds a dropped event
  (`HistoryTruncatedError`), and to state the place of an empty answer,
  instead of returning a silently shorter answer or refusing a read the
  kept events answer in full.

Lists are replaced, never shortened in place, so a view built for an
earlier callback is not affected by a later drop.

Two owners (round 10, i0-r9-02): `DeliveredHistory` is the core's records
(delivery numbers, received times, types, counts) and decides everything;
`HistoryLists` is the strategy's side -- the lists, the event copies in
them and the dropped facts -- which the core writes through base-type C
functions and NEVER reads back. The lists are `DeliveredList`s: the
strategy reaches them through a window's reading functions (window.py), so
reading one by position follows the same rule as an answer (round 8,
i0-r7-01: nothing is cut, a position outside raises by what is there), and
changing one through its own behaviour is refused at every entry (round 9,
i0-r8-02: every attribute assignment and deletion, `__init__` on a made
list, and every `list` method that changes the contents). What the strategy
changes in what it reaches (by a base class's methods, outside the
contract) changes only what it reads there.
"""
from __future__ import annotations

import bisect
from array import array
from typing import Any, Optional

from .events import Event, EventType
from .values import renew
from .window import AnswerPlace, DeliveredEvents, resolve_key, resolve_search


# every method of `list` that changes the contents (the rest only read);
# listed from `list` itself by the test (tests/bt/item_0/test_bt0_r9_history_owner.py)
_LIST_CHANGERS = ("append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse",
                  "__setitem__", "__delitem__", "__iadd__", "__imul__")


def _refused(*_args, **_kwargs):
    raise TypeError("the delivered history is the core's: it cannot be changed from outside")


class DeliveredList(list):
    """The core's list of delivered events (the whole history or one
    type's), as the strategy reaches it. Its place is first 0, step 1,
    delivered = its length (it holds only delivered events), `dropped`
    delivered events before its oldest (history_limit). Read by position, it
    follows the answer's rule (window.py `resolve_key`); a slice is a
    `DeliveredEvents`. Once made (`DeliveredList(items, dropped)`, or the
    core's `_made`), every change through its own behaviour is refused --
    `__init__` again included; the core writes it with `list`'s methods and
    reads nothing back from it."""

    __slots__ = ("_dropped", "_sealed")

    def __new__(cls, items=(), dropped: int = 0):
        self = list.__new__(cls)
        list.__init__(self, items)
        object.__setattr__(self, "_dropped", int(dropped))
        object.__setattr__(self, "_sealed", False)  # sealed by the __init__ call that follows construction
        return self

    @classmethod
    def _made(cls, items=(), dropped: int = 0) -> "DeliveredList":
        """The core's maker: a list sealed at once."""
        self = cls.__new__(cls, items, dropped)
        object.__setattr__(self, "_sealed", True)
        return self

    def __init__(self, *args, **kwargs) -> None:
        # the call Python makes right after construction seals the list;
        # any later call (re-initialising a made list) is refused
        if self._sealed:
            _refused()
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value) -> None:
        _refused()

    def __delattr__(self, name) -> None:
        _refused()

    @property
    def dropped(self) -> int:
        return self._dropped

    def _place(self) -> AnswerPlace:
        return AnswerPlace(0, 1, list.__len__(self), self._dropped)

    def __getitem__(self, key):
        n = list.__len__(self)
        k = resolve_key(key, n, self._place())
        if type(k) is int:
            return list.__getitem__(self, k)
        start, stop, step = k.indices(n)
        get = list.__getitem__
        items = tuple([get(self, i) for i in range(start, stop, step)])
        return DeliveredEvents._placed(items, start, step, n, self._dropped)

    def index(self, value, *args):
        start, stop = resolve_search(args, list.__len__(self), self._place())
        return list.index(self, value, start, stop)

    def __reduce__(self):  # a copy is a plain list of what it holds
        return (list, (list.__getitem__(self, slice(None)),))


for _name in _LIST_CHANGERS:
    setattr(DeliveredList, _name, _refused)
del _name


class HistoryLists:
    """The STRATEGY'S side of the history (round 10, i0-r9-02): what the
    strategy reaches -- the lists (`overall`, `typed`), the event copies in
    them, and the facts of the dropped events (per type, two `array('q')`:
    delivery numbers and received times, in drop order) -- plus the plain
    lists of the same event objects the core rebuilds lists from. Held by
    the engine only inside its strategy-side holder (engine.py
    `_StrategySide`); the core's own records (`DeliveredHistory`) hold no
    reference to it. The core WRITES it through base-type C functions only
    (`list.append`, `array.array.extend`, new lists) and never reads it back
    to decide anything: which events are kept, what was dropped and every
    count come from `DeliveredHistory`, which tells this object what to
    move (`add`, `drop`)."""

    __slots__ = ("overall", "typed", "_items", "_overall_items", "dropped_seqs", "dropped_recvs")

    def __init__(self) -> None:
        self.overall: DeliveredList = DeliveredList._made()
        self.typed: dict[EventType, DeliveredList] = {t: DeliveredList._made() for t in EventType}
        self._items: dict[EventType, list[Event]] = {t: [] for t in EventType}
        self._overall_items: list[Event] = []
        self.dropped_seqs: dict[EventType, array] = {t: array("q") for t in EventType}
        self.dropped_recvs: dict[EventType, array] = {t: array("q") for t in EventType}

    def add(self, event: Event, etype: EventType) -> None:
        list.append(self._items[etype], event)
        list.append(self._overall_items, event)
        list.append(self.typed[etype], event)
        list.append(self.overall, event)

    def drop(self, etype: EventType, cut: int, keep: list, gone: list, count: int, overall_dropped: int) -> None:
        """The core decided (from its records) to drop the oldest `cut`
        events of `etype`: `gone` are their (seq, recv), `keep` the indices
        of the overall events that stay, `count` / `overall_dropped` the new
        counts of dropped events before the type's / the overall list's
        oldest. New lists are made (a list handed out earlier keeps what it
        held)."""
        items = self._items[etype] = self._items[etype][cut:]
        self.typed[etype] = DeliveredList._made(items, count)
        old = self._overall_items
        self._overall_items = [old[i] for i in keep]
        self.overall = DeliveredList._made(self._overall_items, overall_dropped)
        array.extend(self.dropped_seqs[etype], [s for s, _r in gone])
        array.extend(self.dropped_recvs[etype], [r for _s, r in gone])

    def dropped_arrays(self) -> tuple:
        """Per type position (`tuple(EventType)` order): (its dropped
        delivery numbers, their received times) -- the arrays themselves,
        in a new tuple, for one callback's context."""
        return tuple((self.dropped_seqs[t], self.dropped_recvs[t]) for t in EventType)


class DeliveredHistory:
    """The CORE'S records of the history: per kept event its delivery
    number and received time (per type) and its type (overall), how many
    events of each type were dropped and how many deliveries lie before the
    overall list's oldest kept one. Everything the core decides about the
    history is decided from these (round 9, i0-r8-01); they hold no
    reference to anything the strategy reaches (round 10, i0-r9-02): the
    lists and the event copies are the strategy's side (`HistoryLists`),
    which `append` is given to write."""

    __slots__ = ("_limit", "_facts", "_overall_facts", "dropped_count", "overall_dropped")

    def __init__(self, limit: Optional[int]) -> None:
        self._limit = limit
        self._facts: dict[EventType, list[tuple[int, int]]] = {t: [] for t in EventType}
        self._overall_facts: list[tuple[int, EventType]] = []
        # type -> how many delivered events of that type were dropped (all
        # before its oldest kept one: a type drops its oldest)
        self.dropped_count: dict[EventType, int] = {}
        # delivered events before the overall list's oldest (all dropped)
        self.overall_dropped = 0

    def append(self, event: Event, seq: int, recv: int, etype: EventType, lists: HistoryLists) -> None:
        """Record delivery number `seq` at `recv` of type `etype` (the
        core's own values, not read from the event) and have `lists` (the
        strategy's side) keep `event`, the strategy's copy."""
        facts = self._facts[etype]
        limit = self._limit
        if limit is not None and len(facts) >= 2 * limit:
            cut = len(facts) - (limit - 1)  # drop the oldest `cut`
            gone = facts[:cut]
            dropped_seq = gone[-1][0]
            count = self.dropped_count[etype] = self.dropped_count.get(etype, 0) + cut
            facts = self._facts[etype] = facts[cut:]
            # the overall list = what the types keep; drop the same events
            keep = [i for i, (s, t) in enumerate(self._overall_facts) if not (t is etype and s <= dropped_seq)]
            self._overall_facts = [self._overall_facts[i] for i in keep]
            # its place: every delivery before its oldest kept event was dropped
            self.overall_dropped = (self._overall_facts[0][0] if keep else seq) - 1
            lists.drop(etype, cut, keep, gone, count, self.overall_dropped)
        facts.append((seq, recv))
        self._overall_facts.append((seq, etype))
        lists.add(event, etype)

    def count(self, etype: Optional[EventType] = None) -> int:
        """How many events the list holds (the core's own count)."""
        return len(self._overall_facts if etype is None else self._facts[etype])

    def typed_places(self) -> list:
        """(type, how many its list holds, how many were dropped before its
        oldest) for every type with events -- the core's own counts."""
        dropped = self.dropped_count
        return [(t, len(f), dropped.get(t, 0)) for t, f in self._facts.items() if f]

    def dropped_count_facts(self) -> Optional[dict[EventType, int]]:
        """A new copy for one callback's context, or None when nothing was dropped."""
        return {t: renew(n) for t, n in self.dropped_count.items()} if self.dropped_count else None


def dropped_in_range(seqs: Any, recvs: Any, n: int, since: Optional[int], until: Optional[int],
                     after_seq: Optional[int]) -> tuple[int, int]:
    """Of the first `n` dropped events of one type (`seqs` / `recvs`: their
    delivery numbers and received times in drop order; both non-decreasing
    together, as deliveries are), the ones with `since <= recv <= until`
    and `seq > after_seq` form one run: (its start, its end) as indices,
    empty when start == end."""
    lo = 0 if after_seq is None else bisect.bisect_right(seqs, after_seq, 0, n)
    if since is not None:
        lo = max(lo, bisect.bisect_left(recvs, since, 0, n))
    hi = n if until is None else bisect.bisect_right(recvs, until, 0, n)
    return lo, max(lo, hi)


def dropped_before(seqs: Any, recvs: Any, n: int, before_seq: Optional[int], after_recv: int) -> int:
    """How many of the first `n` dropped events of one type have
    `seq < before_seq` (every one when `before_seq` is None) and
    `recv > after_recv`."""
    end = n if before_seq is None else bisect.bisect_left(seqs, before_seq, 0, n)
    return end - min(end, bisect.bisect_right(recvs, after_recv, 0, end))
