"""The deterministic order in which the engine processes things.

Everything that happens travels on one of five CHANNELS, and every channel
is FIFO: nothing on a channel ever overtakes something sent on it earlier.

    phase  channel                       position on the channel
    -----  ----------------------------  ---------------------------------
    0      input  -> venue               merge position (below)
    1      strategy -> venue requests    send order (new orders AND cancels,
                                         one channel, as on one connection)
    2      input  -> strategy            per input stream: reception order =
                                         (recorded received_time_ns, merge
                                         position)
    3      venue  -> strategy notices    the order the venue emitted them
    4      strategy timers               the order they were set

The engine is a discrete-event simulation over ONE priority queue whose key
is

    (time_ns, phase, received_time_ns or the entry's own time, position)

and entries are processed in ascending key order. So at one instant the
venue acts first (market data, then the requests arriving at that instant,
in the order they were sent), then deliveries reach the strategy (input
events, then order notices in the order the venue emitted them, then the
strategy's own timers). The event TYPE is not part of the key: a channel's
sequence is never re-sorted by type (a trade and the book delta it caused,
printed in that order in one feed, stay in that order; an ACK / FILL /
STATE_UNKNOWN keep the order the venue sent them; a cancel sent before a
new order reaches the venue first).

Times on a channel never decrease: a request's arrival time is
`max(send time + delay, previous arrival)`, a notice's delivery time is
`max(venue time + delay, previous delivery)` (the first item on a channel
has no previous one: it keeps its own time -- "nothing sent yet" is not a
time, every int64 is, 0 and times before 1970 included), and an input event is not
delivered before an event of the same stream that was received earlier
(its delivery is postponed to that event's delivery time; engine.py
`_deliver_input`). With equal times the position decides, so the channel
stays FIFO. Every queue time is checked to be an int64 of nanoseconds when
it is pushed (engine.py `_push`).

Merging input streams (phase 0 positions)
-----------------------------------------
Several input streams (trades, board, bars and funding read from separate
files, say) are merged by comparing the streams' NEXT events:

    (exchange_time_ns, place of the event's type in TYPE_ORDER, stream name)

The smallest head is taken, then that stream's next event becomes its head.
So a stream's own order is always kept, and only between different streams
at the same exchange time does the type order decide (liquidation, funding,
book snapshot, book delta, trade, bar, clock -- settled venue-side facts
first, a bar after the trades it is built from, a heartbeat last), then the
stream name (`sorted()` order, not the order the mapping was handed over).
A stream that goes backwards in `exchange_time_ns` is refused
(`EventOrderError`); the core merges streams, it never re-sorts one.
The merge position is fixed by the input alone -- not by when the engine
pulls an event (streams are read lazily), not by sort stability, not by
dict order.

Delivery of input events (phase 2)
----------------------------------
An input event reaches the strategy at `received_time_ns + feed delay`.
Inside one stream the reception order -- (recorded received_time_ns, merge
position) -- is kept whatever the feed delays are: a jittered delay never
lets a later-received event of the same stream overtake an earlier one.
The recorded received_time_ns is data (when the recorder actually got the
event); if a stream records an event as received later than the next one
(a late print), the reception order is what the record says. Between
streams at one delivery time: recorded received time, then merge position.

The strategy sees `event.seq` = its own delivery count (1, 2, 3, ...), not
the queue key: the queue also holds entries for events the strategy has
not received yet, and a counter over the queue would let it count them.

Causality inside one instant: an entry created while processing time T at
time T (an order a strategy placed at T that reaches the venue with zero
latency, say) is processed after the entry that created it, then by key
among the entries still pending at T. The queue never goes back in time.

`ORDERING_RULE` is the machine-readable form of this docstring.
`merge_order` and `order_events` apply the rule to a finite input (what the
engine does when every latency is zero).
"""
from __future__ import annotations

import heapq
from typing import Iterable, Mapping, Union

from .events import SOURCE_EVENT_TYPES, Event, EventType

# Type order used to merge the heads of DIFFERENT input streams at one
# exchange time. Only input (source) types appear: notices are never merged
# with input, they travel on their own channel.
TYPE_ORDER: tuple[EventType, ...] = (
    EventType.LIQUIDATION,
    EventType.FUNDING,
    EventType.BOOK_SNAPSHOT,
    EventType.BOOK_DELTA,
    EventType.TRADE,
    EventType.BAR,
    EventType.CLOCK,
)

assert set(TYPE_ORDER) == set(SOURCE_EVENT_TYPES) and len(TYPE_ORDER) == len(SOURCE_EVENT_TYPES), (
    "every input event type needs exactly one place in TYPE_ORDER"
)

TYPE_RANK: dict[EventType, int] = {t: i for i, t in enumerate(TYPE_ORDER)}

PHASE_VENUE_MARKET = 0
PHASE_VENUE_REQUEST = 1
PHASE_DELIVER_INPUT = 2
PHASE_DELIVER_NOTICE = 3
PHASE_DELIVER_TIMER = 4

PHASES: dict[str, int] = {
    "venue:input": PHASE_VENUE_MARKET,
    "venue:request": PHASE_VENUE_REQUEST,
    "deliver:input": PHASE_DELIVER_INPUT,
    "deliver:notice": PHASE_DELIVER_NOTICE,
    "deliver:timer": PHASE_DELIVER_TIMER,
}

assert sorted(PHASES.values()) == list(range(len(PHASES))), "phases must be 0..n-1"

ORDERING_RULE: dict = {
    "key": ["time_ns", "phase", "received_time_ns (input deliveries; the entry's time otherwise)", "position"],
    "phases_ascending": [name for name, _ in sorted(PHASES.items(), key=lambda kv: kv[1])],
    "channels": {
        "venue:input": {"time": "exchange_time_ns", "position": "merge position"},
        "venue:request": {"time": "max(send time + order/cancel delay, previous arrival); "
                                  "the first request keeps its own time",
                          "position": "send order; new orders and cancels share the channel"},
        "deliver:input": {"time": "received_time_ns + feed delay, never before an earlier-received "
                                  "event of the same stream",
                          "position": "(received_time_ns, merge position)"},
        "deliver:notice": {"time": "max(venue time + notice delay, previous delivery); "
                                   "the first notice keeps its own time",
                           "position": "the order the venue emitted the reports"},
        "deliver:timer": {"time": "the requested time", "position": "the order the timers were set"},
    },
    "channels_fifo": ["venue:input", "venue:request", "deliver:input (per stream, reception order)",
                      "deliver:notice", "deliver:timer"],
    "type_in_key": False,
    "source_merge": {
        "compare_heads_by": ["exchange_time_ns", "TYPE_ORDER", "stream name (sorted())"],
        "type_order": [t.value for t in TYPE_ORDER],
        "inside_one_stream": "the stream's own order, whatever the types",
        "backwards_inside_a_stream": "EventOrderError (never re-sorted)",
        "depends_on_mapping_order": False,
    },
    "depends_on_pull_timing": False,
    "strategy_visible_seq": "the strategy's own delivery count 1, 2, 3, ... (not the queue key)",
    "total_order": True,
    "same_instant_causality": "an entry created while processing time T at time T runs after its creator",
}


def merge_key(event: Event, stream_rank: int) -> tuple[int, int, int]:
    """Key of a stream's head in the merge: (exchange time, type rank,
    stream rank). One head per stream, so the key is unique."""
    return (int(event.exchange_time_ns), TYPE_RANK[event.EVENT_TYPE], stream_rank)


def _as_streams(events: Union[Iterable[Event], Mapping[str, Iterable[Event]]]) -> dict[str, list[Event]]:
    if isinstance(events, Mapping):
        return {name: list(evs) for name, evs in events.items()}
    return {"events": list(events)}


def merge_order(events: Union[Iterable[Event], Mapping[str, Iterable[Event]]]) -> list[Event]:
    """The merge positions of a finite input: one stream (an iterable) or
    several named streams (a mapping). Pure function."""
    streams = _as_streams(events)
    names = sorted(streams)
    heads: list[tuple[tuple[int, int, int], int]] = []
    pos = [0] * len(names)
    for rank, name in enumerate(names):
        if streams[name]:
            heapq.heappush(heads, (merge_key(streams[name][0], rank), rank))
    out: list[Event] = []
    while heads:
        _key, rank = heapq.heappop(heads)
        evs = streams[names[rank]]
        out.append(evs[pos[rank]])
        pos[rank] += 1
        if pos[rank] < len(evs):
            heapq.heappush(heads, (merge_key(evs[pos[rank]], rank), rank))
    return out


def order_events(events: Union[Iterable[Event], Mapping[str, Iterable[Event]]]) -> list[Event]:
    """The order in which a finite input reaches the strategy when every
    latency is zero: merge, then sort by (received time, merge position).
    Pure function; the input is not modified."""
    merged = merge_order(events)
    indexed = sorted(enumerate(merged), key=lambda p: (int(p[1].received_time_ns), p[0]))
    return [e for _, e in indexed]
