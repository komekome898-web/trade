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
"""
from __future__ import annotations

from typing import Optional

from .events import Event, EventType


class DeliveredHistory:
    __slots__ = ("_limit", "overall", "typed", "dropped")

    def __init__(self, limit: Optional[int]) -> None:
        self._limit = limit
        self.overall: list[Event] = []
        self.typed: dict[EventType, list[Event]] = {t: [] for t in EventType}
        # type -> (seq, received_time_ns) of the last event of that type dropped
        self.dropped: dict[EventType, tuple[int, int]] = {}

    def append(self, event: Event) -> None:
        etype = event.EVENT_TYPE
        kept = self.typed[etype]
        limit = self._limit
        if limit is not None and len(kept) >= 2 * limit:
            cut = len(kept) - (limit - 1)  # drop kept[:cut]
            last_dropped = kept[cut - 1]
            dropped_seq = int(last_dropped.seq)
            self.dropped[etype] = (dropped_seq, int(last_dropped.received_time_ns))
            kept = kept[cut:]
            self.typed[etype] = kept
            # the overall list = what the types keep; drop the same events
            self.overall = [
                e for e in self.overall if not (e.EVENT_TYPE is etype and e.seq <= dropped_seq)
            ]
        kept.append(event)
        self.overall.append(event)

    def dropped_facts(self) -> Optional[dict[EventType, tuple[int, int]]]:
        """A copy for one callback's context, or None when nothing was dropped."""
        return dict(self.dropped) if self.dropped else None
