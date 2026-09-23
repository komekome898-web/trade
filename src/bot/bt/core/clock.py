"""Deterministic same-instant event ordering (requirement V4).

The tie-break rule, in order:

1. `received_time_ns`, ascending -- the primary clock.
2. Event-type priority (`TYPE_PRIORITY` below), ascending -- documented
   rationale: events that represent something already settled at the venue
   (LIQUIDATION, FUNDING) are applied before events that describe evolving
   market state (book snapshot -> book delta -> trade -> bar, in that
   order because a bar close is derived from the trades that built it),
   which are applied before our own order-flow feedback (ack -> reject ->
   fill -- an order cannot be filled before it is acknowledged), which is
   applied before the CLOCK heartbeat, so a strategy's periodic wake-up
   sees everything else that happened at this instant first.
3. `seq`, ascending -- a globally unique counter assigned once, in
   `assign_seq`, from the order events are handed to it (their "arrival
   order": file line order for a single source, or whatever order a caller
   merges multiple sources in). Because `seq` is unique per event, keys 1-3
   together form a *total* order: no two events can ever compare equal, so
   replaying the same input (same events, same arrival order) always
   produces the same output sequence. There is no reliance on Python's sort
   stability to fill in what the first two keys leave ambiguous.
"""
from __future__ import annotations

import dataclasses
from typing import Iterable

from .events import Event, EventType

TYPE_PRIORITY: dict[EventType, int] = {
    EventType.LIQUIDATION: 0,
    EventType.FUNDING: 1,
    EventType.BOOK_SNAPSHOT: 2,
    EventType.BOOK_DELTA: 3,
    EventType.TRADE: 4,
    EventType.BAR: 5,
    EventType.ORDER_ACK: 6,
    EventType.ORDER_REJECT: 7,
    EventType.ORDER_FILL: 8,
    EventType.CLOCK: 9,
}

assert set(TYPE_PRIORITY) == set(EventType), "every EventType must have a tie-break priority"


def sort_key(event: Event) -> tuple[int, int, int]:
    return (event.received_time_ns, TYPE_PRIORITY[event.EVENT_TYPE], event.seq)


def assign_seq(events_in_arrival_order: Iterable[Event]) -> list[Event]:
    """Return new Event instances (originals are frozen, so `dataclasses.replace`
    is used rather than mutation) carrying a fresh `seq` = their 0-based
    position in `events_in_arrival_order`. Arrival order is caller-controlled
    and is what makes the final tie-break reproducible for a given input.
    """
    return [dataclasses.replace(event, seq=i) for i, event in enumerate(events_in_arrival_order)]


def build_event_log(events_in_arrival_order: Iterable[Event]) -> list[Event]:
    """Assign seq by arrival order, then sort by the deterministic total
    order defined by `sort_key`. This is the only supported way to turn a
    set of events into the sequence `CoreEngine` replays."""
    assigned = assign_seq(events_in_arrival_order)
    return sorted(assigned, key=sort_key)
