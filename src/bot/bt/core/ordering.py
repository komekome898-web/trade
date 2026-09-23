"""The deterministic order in which the engine processes things.

The engine is a discrete-event simulation over ONE priority queue. Every
queue entry has the key

    (time_ns, priority, seq)

and entries are processed in ascending key order. The three parts:

1. `time_ns` -- when the entry happens. Venue-side entries use the venue's
   clock (a market event's `exchange_time_ns`; an order's arrival time at
   the venue). Strategy deliveries use the time the strategy receives the
   event (`received_time_ns` plus the latency model's feed delay, or the
   venue time of a report plus the notice delay). Every queue time is
   checked to be an int64 of nanoseconds when it is pushed (engine.py
   `_push`), so a latency model cannot push a time out of range unnoticed.
2. `priority` -- `PRIORITY` below. At one instant the venue acts first:
   market data is applied to the venue in the event-type order of
   `TYPE_ORDER` (settled venue-side facts -- liquidation, funding -- before
   the evolving market state -- book snapshot -> book delta -> trade -> bar;
   a bar is derived from the trades that built it), then orders arriving
   at that instant, then cancels arriving at that instant. Then deliveries
   to the strategy happen in the same type order, followed by our own order
   notices (ack -> reject -> fill -> canceled -> state unknown; an order is
   acknowledged before it can fill), and the clock heartbeat last, so a
   timer sees everything else that happened at that instant.
3. `seq` -- a counter the engine increments on every push. Source events
   are pushed in merge order (next point), and entries created while
   processing an entry are pushed in the order they are created, so `seq`
   is unique and the key is a *total* order: two runs over the same input
   with the same models process exactly the same sequence. Nothing relies
   on sort stability or on hash/dict iteration order.

Several input streams (for example trades, board, bars and funding read
from separate files) are merged by `(exchange_time_ns, stream name)`: the
earliest event first; at equal times the stream whose name sorts first.
The name order is `sorted()` of the names, not the order the streams were
handed over, so the result does not depend on the order of the mapping.
Inside one stream the stream's own order is kept, and a stream that goes
backwards in `exchange_time_ns` is refused (`EventOrderError`) -- the core
merges streams, it does not re-sort a stream.

So for events that share a timestamp the rule is: type (`TYPE_ORDER`),
then stream name, then position inside the stream. Only the last one
depends on how the input was written, and it is the stream's own sequence
(for example the venue's print order of two trades in one nanosecond).

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

# Event-type order at one instant, shared by the venue side and the
# strategy side.
TYPE_ORDER: tuple[EventType, ...] = (
    EventType.LIQUIDATION,
    EventType.FUNDING,
    EventType.BOOK_SNAPSHOT,
    EventType.BOOK_DELTA,
    EventType.TRADE,
    EventType.BAR,
    EventType.ORDER_ACK,
    EventType.ORDER_REJECT,
    EventType.ORDER_FILL,
    EventType.ORDER_CANCELED,
    EventType.ORDER_STATE_UNKNOWN,
    EventType.CLOCK,
)

assert set(TYPE_ORDER) == set(EventType) and len(TYPE_ORDER) == len(EventType), (
    "every EventType needs exactly one place in TYPE_ORDER"
)

_VENUE_MARKET_BASE = 0
VENUE_MARKET_PRIORITY: dict[EventType, int] = {
    t: _VENUE_MARKET_BASE + i
    for i, t in enumerate(
        x for x in TYPE_ORDER
        if x in (EventType.LIQUIDATION, EventType.FUNDING, EventType.BOOK_SNAPSHOT,
                 EventType.BOOK_DELTA, EventType.TRADE, EventType.BAR)
    )
}
VENUE_ORDER = 10
VENUE_CANCEL = 11

_DELIVERY_BASE = 20
DELIVERY_PRIORITY: dict[EventType, int] = {t: _DELIVERY_BASE + i for i, t in enumerate(TYPE_ORDER)}

assert set(DELIVERY_PRIORITY) == set(EventType), "every EventType needs a delivery priority"
assert len(set(DELIVERY_PRIORITY.values())) == len(DELIVERY_PRIORITY), "priorities must be distinct"
assert max(VENUE_MARKET_PRIORITY.values()) < VENUE_ORDER < VENUE_CANCEL < min(DELIVERY_PRIORITY.values())

PRIORITY: dict[str, int] = {
    **{f"venue:market:{t.value}": p for t, p in VENUE_MARKET_PRIORITY.items()},
    "venue:order": VENUE_ORDER,
    "venue:cancel": VENUE_CANCEL,
    **{f"deliver:{t.value}": p for t, p in DELIVERY_PRIORITY.items()},
}

ORDERING_RULE: dict = {
    "key": ["time_ns", "priority", "seq"],
    "time_ns": {
        "venue": "exchange_time_ns of market data; arrival time of our order/cancel at the venue",
        "deliver": "received_time_ns + feed delay (market data); venue time + notice delay (notices); timer time",
        "checked": "every queue time is validated as int64 ns when pushed",
    },
    "priority_ascending": [name for name, _ in sorted(PRIORITY.items(), key=lambda kv: kv[1])],
    "type_order_at_one_instant": [t.value for t in TYPE_ORDER],
    "seq": "engine push counter: merged source order, then creation order; unique per entry",
    "source_merge": {
        "key": ["exchange_time_ns", "stream name (sorted())", "position inside the stream"],
        "backwards_inside_a_stream": "EventOrderError (never re-sorted)",
        "depends_on_mapping_order": False,
    },
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
