"""P0-5: the same-instant rule, as values.

The rule (ordering.py): every path is a FIFO channel; at one instant the
phases run input->venue, requests->venue, input->strategy, notices->strategy,
timers. Different input streams at the same exchange time merge by the
head's type (TYPE_ORDER), then stream name; one stream keeps its own order.

The expected sequences below are written out by hand from that rule, not
computed by the engine or by `order_events`.
"""
import random

from bot.bt.core import (
    ORDERING_RULE,
    PHASES,
    TYPE_ORDER,
    Ack,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    CoreEngine,
    EventType,
    Fill,
    FundingEvent,
    LiquidationEvent,
    NullCostModel,
    OrderRequest,
    Strategy,
    order_events,
)

from bt0_util import T0, Recorder, bar, trade


def _one_per_stream():
    return {
        "a_trades": [trade(T0, 100.0)],
        "b_bars": [bar(T0, 100.0)],
        "c_clock": [ClockEvent(received_time_ns=T0, tag="d")],
        "d_delta": [BookDeltaEvent(received_time_ns=T0, side="ask", price=101.0, size=1.0)],
        "e_snap": [BookSnapshotEvent(received_time_ns=T0, bids=[[99.0, 1.0]], asks=[[101.0, 1.0]])],
        "f_funding": [FundingEvent(received_time_ns=T0, rate=0.0001)],
        "g_liq": [LiquidationEvent(received_time_ns=T0, price=100.0, size=1.0, side="sell")],
    }


# By hand: seven streams, one event each, all at T0 -> the heads are compared
# by TYPE_ORDER (liquidation, funding, snapshot, delta, trade, bar, clock).
EXPECTED_TYPES = [
    EventType.LIQUIDATION,
    EventType.FUNDING,
    EventType.BOOK_SNAPSHOT,
    EventType.BOOK_DELTA,
    EventType.TRADE,
    EventType.BAR,
    EventType.CLOCK,
]


def test_same_instant_types_across_streams_follow_the_declared_type_order_in_any_hand_over_order():
    base = _one_per_stream()
    for seed in range(20):
        names = list(base)
        random.Random(seed).shuffle(names)
        streams = {n: base[n] for n in names}  # mapping order shuffled
        rec = Recorder()
        CoreEngine(rec, streams).run()
        assert [e.EVENT_TYPE for e in rec.seen] == EXPECTED_TYPES


def test_one_stream_keeps_its_own_order_whatever_the_types():
    """The same seven events in ONE stream, in a given order: that order is
    kept (a stream is never re-sorted by type)."""
    evs = [e for evs in _one_per_stream().values() for e in evs]
    for seed in range(20):
        shuffled = evs[:]
        random.Random(seed).shuffle(shuffled)
        rec = Recorder()
        CoreEngine(rec, shuffled).run()
        assert [e.EVENT_TYPE for e in rec.seen] == [e.EVENT_TYPE for e in shuffled]


def test_same_type_same_instant_keeps_source_order():
    events = [trade(T0, 100.0 + i) for i in range(5)]
    rec = Recorder()
    CoreEngine(rec, events).run()
    assert [e.price for e in rec.seen] == [100.0, 101.0, 102.0, 103.0, 104.0]
    assert [e.seq for e in rec.seen] == [1, 2, 3, 4, 5]


class _Venue:
    def __init__(self):
        self.log = []

    def on_market_event(self, event, t):
        self.log.append(("market", event.EVENT_TYPE.value, t))
        return ()

    def on_order(self, order, t):
        self.log.append(("order", order.client_order_id, t))
        return (Ack(order.client_order_id), Fill(order.client_order_id, 100.0, order.size))

    def on_cancel(self, req, t):  # pragma: no cover - not used
        return ()


class _Script(Strategy):
    """At the first call (T0-1): place an order that arrives at T0 (zero
    latency is not used: the order is placed one ns before), set a timer at
    T0. Records everything."""

    def __init__(self):
        self.seen = []

    def on_event(self, e, ctx):
        self.seen.append((e.EVENT_TYPE.value, e.received_time_ns))
        if len(self.seen) == 1:
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o"))
            ctx.set_timer(T0, "t")


class _OneNsOrderDelay:
    def feed_delay_ns(self, e):
        return 0

    def order_delay_ns(self, o, t):
        return 1

    def cancel_delay_ns(self, c, t):
        return 0

    def notice_delay_ns(self, r, t):
        return 0


def test_every_phase_at_one_instant_by_hand():
    """Hand-computed P0-5 value: at T0 there are, at once, a trade and a bar
    (two streams), a funding print (third stream), our order arriving (sent
    at T0-1 with 1 ns delay), its ACK+FILL (zero notice delay), a timer, and
    an input heartbeat. Rule: venue input (funding < trade < bar by type) ->
    our order at the venue -> input deliveries (funding, trade, bar, then
    the heartbeat stream: its head type CLOCK sorts last) -> notices in the
    order the venue emitted (ACK, FILL) -> the timer."""
    streams = {
        "first": [trade(T0 - 1, 1.0)],
        "trades": [trade(T0, 100.0)],
        "bars": [bar(T0, 100.0)],
        "funding": [FundingEvent(received_time_ns=T0, rate=0.0001)],
        "hb": [ClockEvent(received_time_ns=T0, tag="hb")],
    }
    venue, strat = _Venue(), _Script()
    CoreEngine(strat, streams, fill_model=venue, latency_model=_OneNsOrderDelay(),
               cost_model=NullCostModel()).run()
    assert venue.log == [
        ("market", "TRADE", T0 - 1),
        ("market", "FUNDING", T0),
        ("market", "TRADE", T0),
        ("market", "BAR", T0),
        ("order", "o", T0),
    ]
    assert strat.seen == [
        ("TRADE", T0 - 1),
        ("FUNDING", T0),
        ("TRADE", T0),
        ("BAR", T0),
        ("CLOCK", T0),  # input heartbeat (input deliveries come before notices)
        ("ORDER_ACK", T0),
        ("ORDER_FILL", T0),
        ("CLOCK", T0),  # the strategy's timer, last
    ]


def test_two_runs_give_the_identical_sequence_and_digest():
    base = _one_per_stream()
    base["a_trades"] = base["a_trades"] + [trade(T0 + 1, 1.0)]
    base["b_bars"] = base["b_bars"] + [bar(T0 + 2, 2.0)]
    runs = []
    for _ in range(2):
        rec = Recorder()
        res = CoreEngine(rec, {k: list(v) for k, v in base.items()}).run()
        runs.append(([e.to_dict() for e in rec.seen], res.delivery_digest))
    assert runs[0] == runs[1]


def test_order_events_matches_engine_delivery_with_zero_latency():
    base = _one_per_stream()
    base["a_trades"] = base["a_trades"] + [trade(T0 + 5, 1.0)]
    base["c_clock"] = base["c_clock"] + [ClockEvent(received_time_ns=T0 + 5)]
    rec = Recorder()
    CoreEngine(rec, base).run()
    assert [e.EVENT_TYPE for e in order_events(base)] == [e.EVENT_TYPE for e in rec.seen]


def test_rule_is_declared_machine_readably_and_is_total():
    assert ORDERING_RULE["key"][:2] == ["time_ns", "phase"]
    assert ORDERING_RULE["type_in_key"] is False
    assert ORDERING_RULE["depends_on_pull_timing"] is False
    assert ORDERING_RULE["total_order"] is True
    assert ORDERING_RULE["phases_ascending"] == [
        "venue:input", "venue:request", "deliver:input", "deliver:notice", "deliver:timer"]
    assert set(PHASES.values()) == set(range(5))
    assert [t.value for t in TYPE_ORDER] == ORDERING_RULE["source_merge"]["type_order"] == [
        "LIQUIDATION", "FUNDING", "BOOK_SNAPSHOT", "BOOK_DELTA", "TRADE", "BAR", "CLOCK"]
