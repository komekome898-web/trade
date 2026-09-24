"""P0-1 / P0-5: typed events handed over as several streams are processed in
time order, not in the order they were handed over; ties follow the
declared rule, independent of the order of the mapping."""
import itertools
import random

import pytest

from bot.bt.core import (
    ORDERING_RULE,
    BookSnapshotEvent,
    ClockEvent,
    CoreEngine,
    EventOrderError,
    EventType,
    FundingEvent,
    SourceEventTypeError,
    OrderAckEvent,
)

from bt0_util import SEC, T0, Recorder, bar, trade


def _streams():
    # bars at 60s, 120s; trades at 30s, 90s; funding at 45s -- every stream
    # is later-first relative to another one when read in handing order.
    return {
        "bars": [bar(T0 + 60 * SEC, 101.0), bar(T0 + 120 * SEC, 102.0)],
        "trades": [trade(T0 + 30 * SEC, 100.0), trade(T0 + 90 * SEC, 100.5)],
        "funding": [FundingEvent(received_time_ns=T0 + 45 * SEC, rate=0.0001)],
    }


def test_streams_are_processed_in_time_order_not_handing_order():
    rec = Recorder()
    res = CoreEngine(rec, _streams()).run()
    got = [(int(e.received_time_ns) - T0) // SEC for e in rec.seen]
    assert got == [30, 45, 60, 90, 120]  # closed form: the union sorted by time
    assert [e.EVENT_TYPE for e in rec.seen] == [
        EventType.TRADE, EventType.FUNDING, EventType.BAR, EventType.TRADE, EventType.BAR,
    ]
    assert res.source_events_by_stream == {"bars": 2, "funding": 1, "trades": 2}
    assert res.source_events == 5


def test_mapping_order_does_not_change_anything():
    base = _streams()
    digests = set()
    for perm in itertools.permutations(base):
        rec = Recorder()
        res = CoreEngine(rec, {k: list(base[k]) for k in perm}).run()
        digests.add(res.delivery_digest)
    assert len(digests) == 1


def test_same_time_same_type_across_streams_is_ordered_by_stream_name():
    a = [trade(T0, 1.0, side="buy")]
    b = [trade(T0, 2.0, side="sell")]
    for mapping in ({"b": b, "a": a}, {"a": a, "b": b}):
        rec = Recorder()
        CoreEngine(rec, mapping).run()
        assert [e.price for e in rec.seen] == [1.0, 2.0]  # "a" < "b"


def test_same_instant_different_types_across_streams_follow_type_order():
    rec = Recorder()
    CoreEngine(rec, {
        "a_clock": [ClockEvent(received_time_ns=T0)],
        "b_bars": [bar(T0, 1.0)],
        "c_trades": [trade(T0, 1.0)],
        "d_book": [BookSnapshotEvent(received_time_ns=T0, bids=[[1.0, 1.0]], asks=[[2.0, 1.0]])],
    }).run()
    assert [e.EVENT_TYPE for e in rec.seen] == [
        EventType.BOOK_SNAPSHOT, EventType.TRADE, EventType.BAR, EventType.CLOCK,
    ]


def test_backwards_step_inside_one_stream_is_refused_and_named():
    streams = {"trades": [trade(T0 + 2, 1.0), trade(T0 + 1, 1.0)], "bars": [bar(T0, 1.0)]}
    with pytest.raises(EventOrderError, match="'trades'"):
        CoreEngine(Recorder(), streams).run()


def test_single_stream_backwards_is_refused_not_resorted():
    with pytest.raises(EventOrderError):
        CoreEngine(Recorder(), [trade(T0 + 2, 1.0), trade(T0 + 1, 1.0)]).run()


def test_notice_in_a_stream_is_refused():
    with pytest.raises(SourceEventTypeError, match="'x'"):
        CoreEngine(Recorder(), {"x": [OrderAckEvent(received_time_ns=T0, client_order_id="a")]}).run()


def test_bad_stream_name_is_refused():
    with pytest.raises(TypeError):
        CoreEngine(Recorder(), {"": [trade(T0)]})


def test_each_stream_is_pulled_lazily_one_ahead_at_most():
    pulled = {"a": 0, "b": 0}

    def gen(name, times):
        for t in times:
            pulled[name] += 1
            yield trade(t, 1.0)

    observed = []

    def act(ev, ctx):
        observed.append((int(ev.received_time_ns) - T0, dict(pulled)))

    a_times = [T0 + i * 10 for i in range(5)]
    b_times = [T0 + 5 + i * 10 for i in range(5)]
    CoreEngine(Recorder(act), {"a": gen("a", a_times), "b": gen("b", b_times)}).run()
    for now, counts in observed:
        # events pulled from a stream but not yet delivered: at most one per stream
        delivered_a = sum(1 for t in a_times if t - T0 <= now)
        delivered_b = sum(1 for t in b_times if t - T0 <= now)
        assert counts["a"] - delivered_a <= 1 and counts["b"] - delivered_b <= 1


def test_random_streams_two_runs_identical_and_time_ordered():
    rng = random.Random(7)
    streams = {}
    for name in ("s1", "s2", "s3"):
        t = T0
        evs = []
        for _ in range(200):
            t += rng.choice([0, 0, 1, 5, 1000])
            evs.append(trade(t, 100.0 + rng.random(), side=rng.choice(["buy", "sell"])))
        streams[name] = evs
    digests = []
    for _ in range(2):
        rec = Recorder()
        res = CoreEngine(rec, {k: list(v) for k, v in streams.items()}).run()
        times = [int(e.received_time_ns) for e in rec.seen]
        assert times == sorted(times) and len(times) == 600
        digests.append(res.delivery_digest)
    assert digests[0] == digests[1]


def test_merge_rule_is_declared():
    merge = ORDERING_RULE["source_merge"]
    assert merge["compare_heads_by"] == ["exchange_time_ns", "TYPE_ORDER", "stream name (sorted())"]
    assert merge["inside_one_stream"] == "the stream's own order, whatever the types"
    assert merge["depends_on_mapping_order"] is False
