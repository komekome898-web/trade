"""The deterministic order in which the engine processes things.

The engine is a discrete-event simulation over ONE priority queue. Every
queue entry has the key

    (time_ns, priority, seq)

and entries are processed in ascending key order. The three parts:

1. `time_ns` -- when the entry happens. Venue-side entries use the venue's
   clock (a market event's `exchange_time_ns`; an order's arrival time at
   the venue). Strategy deliveries use the time the strategy receives the
   event (`received_time_ns` plus the latency model's feed delay, or the
   venue time of a report plus the notice delay).
2. `priority` -- `PRIORITY` below. At one instant the venue acts first
   (market data is applied to the venue, then orders arriving at that
   instant, then cancels arriving at that instant), then deliveries to the
   strategy happen in the event-type order in `DELIVERY_PRIORITY`: settled
   venue-side facts (liquidation, funding) before the evolving market state
   (book snapshot -> book delta -> trade -> bar; a bar is derived from the
   trades that built it), then our own order notices (ack -> reject ->
   fill -> canceled -> state unknown; an order is acknowledged before it can
   fill), and the clock heartbeat last, so a timer sees everything else that
   happened at that instant.
3. `seq` -- a counter the engine increments on every push. Source events
   are pushed in the order the source yields them, and entries created
   while processing an entry are pushed in the order they are created, so
   `seq` is unique and the key is a *total* order: two runs over the same
   input with the same models process exactly the same sequence. Nothing
   relies on sort stability or on hash/dict iteration order.

Causality inside one instant: an entry created while processing time T at
time T (for example an order a strategy placed at T that reaches the venue
with zero latency) is processed after the entry that created it, and then
by priority among the entries still pending at T. The queue never goes back
in time: an entry for a time earlier than the current time is an engine
error.

`ORDERING_RULE` is the machine-readable form of this docstring.
`order_events` applies the delivery part of the rule to a finite batch
(what the engine does when every latency is zero).
"""
from __future__ import annotations

from typing import Iterable

from .events import Event, EventType

VENUE_MARKET = 0
VENUE_ORDER = 1
VENUE_CANCEL = 2

DELIVERY_PRIORITY: dict[EventType, int] = {
    EventType.LIQUIDATION: 10,
    EventType.FUNDING: 11,
    EventType.BOOK_SNAPSHOT: 12,
    EventType.BOOK_DELTA: 13,
    EventType.TRADE: 14,
    EventType.BAR: 15,
    EventType.ORDER_ACK: 16,
    EventType.ORDER_REJECT: 17,
    EventType.ORDER_FILL: 18,
    EventType.ORDER_CANCELED: 19,
    EventType.ORDER_STATE_UNKNOWN: 20,
    EventType.CLOCK: 21,
}

assert set(DELIVERY_PRIORITY) == set(EventType), "every EventType needs a delivery priority"
assert len(set(DELIVERY_PRIORITY.values())) == len(DELIVERY_PRIORITY), "priorities must be distinct"

PRIORITY: dict[str, int] = {
    "venue:market": VENUE_MARKET,
    "venue:order": VENUE_ORDER,
    "venue:cancel": VENUE_CANCEL,
    **{f"deliver:{t.value}": p for t, p in DELIVERY_PRIORITY.items()},
}

ORDERING_RULE: dict = {
    "key": ["time_ns", "priority", "seq"],
    "time_ns": {
        "venue": "exchange_time_ns of market data; arrival time of our order/cancel at the venue",
        "deliver": "received_time_ns + feed delay (market data); venue time + notice delay (notices); timer time",
    },
    "priority_ascending": [name for name, _ in sorted(PRIORITY.items(), key=lambda kv: kv[1])],
    "seq": "engine push counter: source yield order, then creation order; unique per entry",
    "total_order": True,
    "same_instant_causality": "an entry created while processing time T at time T runs after its creator",
    "channels_fifo": ["strategy->venue orders/cancels", "venue->strategy notices"],
}


def delivery_key(event: Event, arrival_index: int) -> tuple[int, int, int]:
    return (int(event.received_time_ns), DELIVERY_PRIORITY[event.EVENT_TYPE], arrival_index)


def order_events(events_in_arrival_order: Iterable[Event]) -> list[Event]:
    """Sort a finite batch by the delivery rule (received time, type
    priority, arrival order). Pure function; the input is not modified."""
    indexed = list(enumerate(events_in_arrival_order))
    indexed.sort(key=lambda pair: delivery_key(pair[1], pair[0]))
    return [e for _, e in indexed]
