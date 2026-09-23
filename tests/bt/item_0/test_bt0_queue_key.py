"""P0-4 / P0-5: the queue key (time, priority, origin, ordinal) and the
strategy-visible `seq`.

* `seq` on a delivered event is the strategy's own delivery count. A queue
  counter would also count entries for events the strategy has not received
  yet (an event that happened at the exchange but reaches us later), and
  its gaps would let the strategy count them.
* The processing order is a function of the input only: for input events
  it equals a global sort by (delivery time, type priority, merge position),
  whatever the lazy stream reading does; an input heartbeat and a strategy
  timer at the same instant are ordered input first.
"""
import random

from bot.bt.core import (
    DELIVERY_PRIORITY,
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


def test_order_equals_the_stated_rule_as_a_global_sort():
    """Reference computed without the engine: merge position = rank by
    (exchange time, stream name, position); delivery order = sort by
    (received time, type priority, merge position)."""
    for seed in range(200):
        rng = random.Random(seed)
        streams = _random_streams(rng)
        tagged = [(e.exchange_time_ns, name, i, e) for name, evs in streams.items() for i, e in enumerate(evs)]
        merged = [x[3] for x in sorted(tagged, key=lambda x: x[:3])]
        expected = [
            e for _, e in sorted(enumerate(merged),
                                 key=lambda p: (p[1].received_time_ns, DELIVERY_PRIORITY[p[1].EVENT_TYPE], p[0]))
        ]
        got = _run(streams)
        assert [(e.EVENT_TYPE, e.received_time_ns, e.exchange_time_ns, getattr(e, "tag", None),
                 getattr(e, "price", None)) for e in got] == \
               [(e.EVENT_TYPE, e.received_time_ns, e.exchange_time_ns, getattr(e, "tag", None),
                 getattr(e, "price", None)) for e in expected], seed
