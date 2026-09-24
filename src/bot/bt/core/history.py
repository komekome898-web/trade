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
a position outside raises by what is there), and changing one is refused
(the core changes them with `list`'s own methods).
"""
from __future__ import annotations

from typing import Optional

from .events import Event, EventType
from .window import AnswerPlace, DeliveredEvents, resolve_key, resolve_search


class DeliveredList(list):
    """The core's list of delivered events (the whole history or one
    type's). Its place is first 0, step 1, delivered = its length (it holds
    only delivered events), `dropped` delivered events before its oldest
    (history_limit). Read by position, it follows the answer's rule
    (window.py `resolve_key`); a slice is a `DeliveredEvents`. Changing it
    through its own methods is refused: only the core changes it, with
    `list`'s methods."""

    __slots__ = ("dropped",)

    def __init__(self, items=(), dropped: int = 0) -> None:
        list.__init__(self, items)
        self.dropped = dropped

    def _place(self) -> AnswerPlace:
        return AnswerPlace(0, 1, list.__len__(self), self.dropped)

    def __getitem__(self, key):
        n = list.__len__(self)
        k = resolve_key(key, n, self._place())
        if type(k) is int:
            return list.__getitem__(self, k)
        start, stop, step = k.indices(n)
        get = list.__getitem__
        items = tuple([get(self, i) for i in range(start, stop, step)])
        return DeliveredEvents._placed(items, start, step, n, self.dropped)

    def index(self, value, *args):
        start, stop = resolve_search(args, list.__len__(self), self._place())
        return list.index(self, value, start, stop)

    def _refuse(self, *args, **kwargs):
        raise TypeError("the delivered history is the core's: it cannot be changed from outside")

    append = extend = insert = pop = remove = clear = sort = reverse = _refuse
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _refuse

    def __reduce__(self):  # a copy is a plain list of what it holds
        return (list, (list(self),))


class DeliveredHistory:
    __slots__ = ("_limit", "overall", "typed", "dropped", "dropped_count")

    def __init__(self, limit: Optional[int]) -> None:
        self._limit = limit
        self.overall: DeliveredList = DeliveredList()
        self.typed: dict[EventType, DeliveredList] = {t: DeliveredList() for t in EventType}
        # type -> (seq, received_time_ns) of the last event of that type dropped
        self.dropped: dict[EventType, tuple[int, int]] = {}
        # type -> how many delivered events of that type were dropped (all
        # before its oldest kept one: a type drops its oldest)
        self.dropped_count: dict[EventType, int] = {}

    def append(self, event: Event) -> None:
        etype = event.EVENT_TYPE
        kept = self.typed[etype]
        limit = self._limit
        if limit is not None and len(kept) >= 2 * limit:
            cut = len(kept) - (limit - 1)  # drop kept[:cut]
            last_dropped = list.__getitem__(kept, cut - 1)
            dropped_seq = int(last_dropped.seq)
            self.dropped[etype] = (dropped_seq, int(last_dropped.received_time_ns))
            self.dropped_count[etype] = self.dropped_count.get(etype, 0) + cut
            kept = DeliveredList(list.__getitem__(kept, slice(cut, None)), self.dropped_count[etype])
            self.typed[etype] = kept
            # the overall list = what the types keep; drop the same events
            overall = [e for e in list.__iter__(self.overall)
                       if not (e.EVENT_TYPE is etype and e.seq <= dropped_seq)]
            # its place: every delivery before its oldest kept event was dropped
            first_seq = int(overall[0].seq) if overall else int(event.seq)
            self.overall = DeliveredList(overall, first_seq - 1)
        list.append(kept, event)
        list.append(self.overall, event)

    def dropped_facts(self) -> Optional[dict[EventType, tuple[int, int]]]:
        """A copy for one callback's context, or None when nothing was dropped."""
        return dict(self.dropped) if self.dropped else None

    def dropped_count_facts(self) -> Optional[dict[EventType, int]]:
        """A copy for one callback's context, or None when nothing was dropped."""
        return dict(self.dropped_count) if self.dropped_count else None
