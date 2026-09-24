"""P0-4 / P0-5: the queue key (time, phase, received, position) and the
strategy-visible `seq`.

* `seq` on a delivered event is the strategy's own delivery count. A queue
  counter would also count entries for events the strategy has not received
  yet (an event that happened at the exchange but reaches us later), and
  its gaps would let the strategy count them.
* The processing order is a function of the input only: for input events
  it equals a global sort by (delivery time, received time, merge
  position), where the merge takes the streams' heads by (exchange time,
  TYPE_ORDER, stream name) and delivery never lets an event overtake an
  earlier-received event of its own stream, whatever the feed delays and
  whatever the lazy stream reading does; an input heartbeat and a strategy
  timer at the same instant are ordered input first.
"""
import random

from bot.bt.core import (
    TYPE_ORDER,
    BarEvent,
    ClockEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    Strategy,
    TradeEvent,
)

from bt0_util import Recorder

T0 = 1_700_006_400_000_000_000
D = 86_400 * 1_000_000_000


class _TimerAtFirstCall(Strategy):
    def __init__(self, at):
        self.at = at
        self.seen = []

    def on_event(self, e, ctx):
        self.seen.append(e)
        if len(self.seen) == 1:
            ctx.set_timer(self.at, "timer")


def _run(events_or_streams, strategy=None):
    rec = strategy or Recorder()
    CoreEngine(rec, events_or_streams).run()
    return rec.seen


def test_seq_is_the_delivery_count():
    evs = [TradeEvent(received_time_ns=T0 + i * D, price=100.0 + i, size=1.0, side="buy") for i in range(1, 6)]
    seen = _run(evs)
    assert [e.seq for e in seen] == [1, 2, 3, 4, 5]


def test_seq_does_not_reveal_an_event_not_received_yet():
    """Day 2: an event that happened at the exchange at day 1.5 but reaches
    us at day 9 must leave no trace in what the strategy sees at day 2."""
    visible = [TradeEvent(received_time_ns=T0 + D, price=100.0, size=1.0, side="buy"),
               TradeEvent(received_time_ns=T0 + 2 * D, price=101.0, size=1.0, side="buy")]
    hidden = TradeEvent(exchange_time_ns=T0 + 3 * D // 2, received_time_ns=T0 + 9 * D,
                        price=999.0, size=1.0, side="buy")

    def upto_day2(with_hidden):
        evs = [visible[0], hidden, visible[1]] if with_hidden else list(visible)
        seen = _run(evs)
        return [(e.EVENT_TYPE, e.received_time_ns, e.seq, e.price) for e in seen if e.received_time_ns <= T0 + 2 * D]

    assert upto_day2(True) == upto_day2(False) == [
        (EventType.TRADE, T0 + D, 1, 100.0), (EventType.TRADE, T0 + 2 * D, 2, 101.0)]


def _clock_tags(streams):
    seen = _run(streams, _TimerAtFirstCall(T0 + 3 * D))
    return [e.tag for e in seen if e.EVENT_TYPE is EventType.CLOCK]


def test_input_heartbeat_before_timer_at_the_same_instant_in_every_arrangement():
    first = TradeEvent(received_time_ns=T0 + D, price=100.0, size=1.0, side="buy")
    # 1) heartbeat stamped at the instant itself
    assert _clock_tags({"a": [first, ClockEvent(received_time_ns=T0 + 3 * D, tag="input")]}) == ["input", "timer"]
    # 2) heartbeat that happened earlier but is received at that instant
    #    (it is read from its stream before the timer is set)
    assert _clock_tags({"a": [first, ClockEvent(exchange_time_ns=T0 + D + 1, received_time_ns=T0 + 3 * D,
                                                tag="input")]}) == ["input", "timer"]
    # 3) same as 1 with an unrelated delayed event in another stream
    assert _clock_tags({
        "a": [first, ClockEvent(received_time_ns=T0 + 3 * D, tag="input")],
        "b": [TradeEvent(exchange_time_ns=T0 + D // 2, received_time_ns=T0 + 5 * D, price=1.0, size=1.0, side="buy")],
    }) == ["input", "timer"]


def _random_streams(rng):
    streams = {}
    for name in rng.sample(["bars", "funding", "trades", "clock", "z"], k=rng.randint(1, 5)):
        t = T0
        evs = []
        for _ in range(rng.randint(0, 12)):
            t += rng.choice([0, 0, 1, 5, 1000])
            recv = t + rng.choice([0, 0, 0, 3, 7, 5000])
            kind = rng.choice(["trade", "bar", "funding", "clock"])
            if kind == "trade":
                e = TradeEvent(exchange_time_ns=t, received_time_ns=recv, price=float(rng.randint(1, 9)), size=1.0, side="buy")
            elif kind == "bar":
                e = BarEvent(exchange_time_ns=t, received_time_ns=recv, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
            elif kind == "funding":
                e = FundingEvent(exchange_time_ns=t, received_time_ns=recv, rate=0.0001)
            else:
                e = ClockEvent(exchange_time_ns=t, received_time_ns=recv, tag=f"{name}-{len(evs)}")
            evs.append(e)
        streams[name] = evs
    return streams


_RANK = {t: i for i, t in enumerate(TYPE_ORDER)}


def _reference_merge(streams):
    """Greedy merge written independently of the engine: repeatedly take
    the stream whose next event has the smallest (exchange time, type rank,
    stream name)."""
    pos = {n: 0 for n in streams}
    out = []
    while True:
        heads = [(evs[pos[n]].exchange_time_ns, _RANK[evs[pos[n]].EVENT_TYPE], n)
                 for n, evs in streams.items() if pos[n] < len(evs)]
        if not heads:
            return out
        _, _, n = min(heads)
        out.append((n, streams[n][pos[n]]))
        pos[n] += 1


def _reference_delivery(streams, delay_of):
    merged = _reference_merge(streams)
    mpos = {id(e): i for i, (_, e) in enumerate(merged)}
    deliver = {}
    for name, evs in streams.items():
        last = None
        for e in sorted(evs, key=lambda e: (e.received_time_ns, mpos[id(e)])):  # reception order
            t = e.received_time_ns + delay_of(e)
            if last is not None and t < last:
                t = last
            deliver[id(e)] = t
            last = t
    return sorted((e for _, e in merged), key=lambda e: (deliver[id(e)], e.received_time_ns, mpos[id(e)])), deliver


def _sig(e):
    return (e.EVENT_TYPE, e.exchange_time_ns, getattr(e, "tag", None), getattr(e, "price", None))


def test_order_equals_the_stated_rule_as_a_global_sort():
    for seed in range(200):
        rng = random.Random(seed)
        streams = _random_streams(rng)
        expected, deliver = _reference_delivery(streams, lambda e: 0)
        got = _run(streams)
        assert [_sig(e) for e in got] == [_sig(e) for e in expected], seed
        assert [e.received_time_ns for e in got] == [deliver[id(e)] for e in expected], seed


class _JitterFeed:
    def __init__(self, delays):
        self.delays = delays

    def feed_delay_ns(self, e):
        return self.delays[id(e)]

    def order_delay_ns(self, o, t):
        return 0

    def cancel_delay_ns(self, c, t):
        return 0

    def notice_delay_ns(self, r, t):
        return 0


def test_jittered_feed_delay_keeps_each_stream_in_reception_order():
    """i0-r1-12: with a random feed delay per event, the delivery order is
    the rule's: per stream, reception order is kept (delivery time = running
    max over the stream in reception order)."""
    from bot.bt.core import MARKET_EVENT_TYPES
    for seed in range(200):
        rng = random.Random(1000 + seed)
        streams = _random_streams(rng)
        delays = {id(e): (rng.choice([0, 0, 1, 2, 9, 4000]) if e.EVENT_TYPE in MARKET_EVENT_TYPES else 0)
                  for evs in streams.values() for e in evs}
        expected, deliver = _reference_delivery(streams, lambda e: delays[id(e)])
        rec = Recorder()
        CoreEngine(rec, streams, latency_model=_JitterFeed(delays)).run()
        assert [_sig(e) for e in rec.seen] == [_sig(e) for e in expected], seed
        assert [e.received_time_ns for e in rec.seen] == [deliver[id(e)] for e in expected], seed
