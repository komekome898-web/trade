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
* what was dropped is recorded as a fact per type: the delivery number
  (`seq`) and the received time of the last dropped event of that type.
  The strategy context uses it to refuse any read whose answer would reach
  into the dropped part (`HistoryTruncatedError`), instead of returning a
  silently shorter answer.

Lists are replaced, never shortened in place, so a view built for an
earlier callback is not affected by a later drop.

The lists are `DeliveredList`s: the strategy reaches them through a
window's private attribute (window.py), so reading one by position
follows the same rule as an answer (round 8, i0-r7-01: nothing is cut,
a position outside raises by what is there), and changing one through its
own behaviour is refused at every entry (round 9, i0-r8-02: every
attribute assignment and deletion, `__init__` on a made list, and every
`list` method that changes the contents). The core writes them with
`list`'s own methods and NEVER reads them back (round 9, i0-r8-01): which
events a type keeps, what was dropped, how many each list holds and how
many were dropped before its oldest -- all of it comes from the core's own
records (per delivered event: its delivery number, received time, type,
and the event object the core put in the lists), which nothing outside
the core reaches.
What the strategy changes in a list it reaches (by calling `list`'s own
methods on it, outside the contract) changes only what it reads there.
"""
from __future__ import annotations

from typing import Optional

from .events import Event, EventType
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
    `DeliveredEvents`. Made by the core only (`_made`); every change through
    its own behaviour is refused; the core writes it with `list`'s methods
    and reads nothing back from it."""

    __slots__ = ("_dropped",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("a DeliveredList is made by the core only")

    @classmethod
    def _made(cls, items=(), dropped: int = 0) -> "DeliveredList":
        self = list.__new__(cls)
        list.__init__(self, items)
        object.__setattr__(self, "_dropped", int(dropped))
        return self

    def __init__(self, *args, **kwargs) -> None:
        _refused()

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


class DeliveredHistory:
    """The history's lists (what the strategy reaches) and the core's own
    records they are made from (what the core reads)."""

    __slots__ = ("_limit", "overall", "typed", "dropped", "dropped_count", "_kept", "_overall_kept",
                 "overall_dropped")

    def __init__(self, limit: Optional[int]) -> None:
        self._limit = limit
        self.overall: DeliveredList = DeliveredList._made()
        self.typed: dict[EventType, DeliveredList] = {t: DeliveredList._made() for t in EventType}
        # the core's own records, parallel to the lists: per type, and overall
        self._kept: dict[EventType, list] = {t: [] for t in EventType}
        self._overall_kept: list = []
        # type -> (seq, received_time_ns) of the last event of that type dropped
        self.dropped: dict[EventType, tuple[int, int]] = {}
        # type -> how many delivered events of that type were dropped (all
        # before its oldest kept one: a type drops its oldest)
        self.dropped_count: dict[EventType, int] = {}
        # delivered events before the overall list's oldest (all dropped)
        self.overall_dropped = 0

    def append(self, event: Event, seq: int, recv: int, etype: EventType) -> None:
        """Keep `event` (the strategy's copy, delivered as number `seq` at
        `recv`, of type `etype` -- the core's own values, not read from the
        event)."""
        kept = self._kept[etype]
        limit = self._limit
        if limit is not None and len(kept) >= 2 * limit:
            cut = len(kept) - (limit - 1)  # drop kept[:cut]
            dropped_seq, dropped_recv, _t, _e = kept[cut - 1]
            self.dropped[etype] = (dropped_seq, dropped_recv)
            self.dropped_count[etype] = self.dropped_count.get(etype, 0) + cut
            kept = kept[cut:]
            self._kept[etype] = kept
            self.typed[etype] = DeliveredList._made([r[3] for r in kept], self.dropped_count[etype])
            # the overall list = what the types keep; drop the same events
            overall = [r for r in self._overall_kept if not (r[2] is etype and r[0] <= dropped_seq)]
            self._overall_kept = overall
            # its place: every delivery before its oldest kept event was dropped
            self.overall_dropped = (overall[0][0] if overall else seq) - 1
            self.overall = DeliveredList._made([r[3] for r in overall], self.overall_dropped)
        rec = (seq, recv, etype, event)
        kept.append(rec)
        self._overall_kept.append(rec)
        list.append(self.typed[etype], event)
        list.append(self.overall, event)

    def count(self, etype: Optional[EventType] = None) -> int:
        """How many events the list holds (the core's own count)."""
        return len(self._overall_kept if etype is None else self._kept[etype])

    def dropped_before(self, etype: EventType) -> int:
        """How many delivered events of `etype` lie before its list's oldest."""
        return self.dropped_count.get(etype, 0)

    def dropped_facts(self) -> Optional[dict[EventType, tuple[int, int]]]:
        """A copy for one callback's context, or None when nothing was dropped."""
        return dict(self.dropped) if self.dropped else None

    def dropped_count_facts(self) -> Optional[dict[EventType, int]]:
        """A copy for one callback's context, or None when nothing was dropped."""
        return dict(self.dropped_count) if self.dropped_count else None
