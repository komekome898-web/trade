import random

from bot.bt.core import (
    DELIVERY_PRIORITY,
    ORDERING_RULE,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    LiquidationEvent,
    order_events,
)

from bt0_util import T0, Recorder, bar, trade


def _same_instant_market():
    return [
        trade(T0, 100.0),
        bar(T0, 100.0),
        ClockEvent(received_time_ns=T0, tag="d"),
        BookDeltaEvent(received_time_ns=T0, side="ask", price=101.0, size=1.0),
        BookSnapshotEvent(received_time_ns=T0, bids=[[99.0, 1.0]], asks=[[101.0, 1.0]]),
        FundingEvent(received_time_ns=T0, rate=0.0001),
        LiquidationEvent(received_time_ns=T0, price=100.0, size=1.0, side="sell"),
    ]


EXPECTED_TYPES = [
    EventType.LIQUIDATION,
    EventType.FUNDING,
    EventType.BOOK_SNAPSHOT,
    EventType.BOOK_DELTA,
    EventType.TRADE,
    EventType.BAR,
    EventType.CLOCK,
]


def test_same_instant_types_follow_the_declared_priority_regardless_of_input_order():
    base = _same_instant_market()
    for seed in range(20):
        shuffled = base[:]
        random.Random(seed).shuffle(shuffled)
        rec = Recorder()
        CoreEngine(rec, shuffled).run()
        assert [e.EVENT_TYPE for e in rec.seen] == EXPECTED_TYPES


def test_same_type_same_instant_keeps_source_order():
    events = [trade(T0, 100.0 + i) for i in range(5)]
    rec = Recorder()
    CoreEngine(rec, events).run()
    assert [e.price for e in rec.seen] == [100.0, 101.0, 102.0, 103.0, 104.0]
    assert [e.seq for e in rec.seen] == sorted(e.seq for e in rec.seen)


def test_two_runs_give_the_identical_sequence_and_digest():
    base = _same_instant_market() + [trade(T0 + 1, 1.0), bar(T0 + 2, 2.0)]
    runs = []
    for _ in range(2):
        rec = Recorder()
        res = CoreEngine(rec, list(base)).run()
        runs.append(([e.to_dict() for e in rec.seen], res.delivery_digest))
    assert runs[0] == runs[1]


def test_order_events_matches_engine_delivery_with_zero_latency():
    base = _same_instant_market() + [trade(T0 + 5, 1.0), clock_at(T0 + 5)]
    rec = Recorder()
    CoreEngine(rec, base).run()
    assert [e.EVENT_TYPE for e in order_events(base)] == [e.EVENT_TYPE for e in rec.seen]


def clock_at(t):
    return ClockEvent(received_time_ns=t)


def test_rule_is_declared_machine_readably_and_is_total():
    assert ORDERING_RULE["key"] == ["time_ns", "priority", "seq"]
    assert ORDERING_RULE["total_order"] is True
    assert set(DELIVERY_PRIORITY) == set(EventType)
    names = ORDERING_RULE["priority_ascending"]
    assert names[:8] == [
        "venue:market:LIQUIDATION", "venue:market:FUNDING", "venue:market:BOOK_SNAPSHOT",
        "venue:market:BOOK_DELTA", "venue:market:TRADE", "venue:market:BAR",
        "venue:order", "venue:cancel",
    ]
    assert names.index("deliver:ORDER_ACK") < names.index("deliver:ORDER_FILL")
    assert names[-1] == "deliver:CLOCK"
