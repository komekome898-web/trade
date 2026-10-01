"""G-1 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-1): before the fix a core
event carried no stream name (Event had received_time_ns / exchange_time_ns / seq only), so a strategy reading two
markets could tell their bars apart only by the merge order of one instant (ordering.py: stream names in sorted()
order). Rule after the fix (events.py, engine.py `_SourceMerger._pull`): every source event carries the name of the
stream it was pulled from (`Event.stream`), set by the engine on intake; a source event naming another stream is
refused; notices and the strategy's timers carry "".
"""
from __future__ import annotations

import pytest

from bot.bt.core import (Ack, BarEvent, ClockEvent, CoreEngine, NullAccount, OrderRequest, Strategy, TradeEvent,
                         ZeroLatency, event_from_dict)
from bot.bt.core.errors import EventValidationError
from bot.bt.core.testing import FixedRateCost, ImmediateFillModel

NS = 1_000_000_000
T0 = 1_700_000_000 * NS


def bar(i: int, px: float, stream: str = "") -> BarEvent:
    return BarEvent(received_time_ns=T0 + (i + 1) * 60 * NS, start_time_ns=T0 + i * 60 * NS,
                    open=px, high=px + 1, low=px - 1, close=px, volume=1.0, stream=stream)


class Recorder(Strategy):
    def __init__(self, order_at: int = -1) -> None:
        self.seen: list[tuple[str, str, float]] = []
        self.order_at = order_at
        self.n = 0

    def on_event(self, event, ctx) -> None:
        self.seen.append((event.EVENT_TYPE.value, event.stream, getattr(event, "close", 0.0)))
        if type(event) is BarEvent:
            self.n += 1
            if self.n == self.order_at:
                ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1"))
                ctx.set_timer(int(event.received_time_ns) + NS, "t")


def _run(strategy, streams):
    return CoreEngine(strategy, streams, ImmediateFillModel(), ZeroLatency(), FixedRateCost(0.0), NullAccount()).run()


@pytest.mark.parametrize("names", [("a", "b"), ("b", "a"), ("signal", "price"), ("price", "signal")])
def test_every_delivered_source_event_carries_its_streams_name(names):
    first, second = names
    s = Recorder()
    _run(s, {first: [bar(i, 100.0 + i) for i in range(3)], second: [bar(i, 200.0 + i) for i in range(3)]})
    got = {(st, c) for _t, st, c in s.seen}
    assert got == {(first, 100.0 + i) for i in range(3)} | {(second, 200.0 + i) for i in range(3)}


def test_one_unnamed_stream_is_named_events_and_notices_and_timers_carry_no_stream():
    s = Recorder(order_at=1)
    _run(s, [bar(0, 100.0), bar(1, 101.0)])
    by_type = {}
    for t, st, _c in s.seen:
        by_type.setdefault(t, set()).add(st)
    assert by_type["BAR"] == {"events"}
    assert by_type["ORDER_ACK"] == {""} and by_type["ORDER_FILL"] == {""}
    assert by_type["CLOCK"] == {""}


def test_a_source_event_naming_another_stream_is_refused_and_its_own_name_is_accepted():
    with pytest.raises(EventValidationError, match="names the stream 'x'"):
        _run(Recorder(), {"a": [bar(0, 100.0, stream="x")]})
    s = Recorder()
    _run(s, {"a": [bar(0, 100.0, stream="a")], "b": [TradeEvent(received_time_ns=T0, price=1.0, size=1.0, side="")]})
    assert sorted(st for _t, st, _c in s.seen) == ["a", "b"]


def test_a_source_clock_event_carries_its_stream():
    s = Recorder()
    _run(s, {"hb": [ClockEvent(received_time_ns=T0)]})
    assert s.seen == [("CLOCK", "hb", 0.0)]


def test_stream_is_a_text_field_and_survives_to_dict():
    e = bar(0, 100.0, stream="d1")
    assert e.to_dict()["stream"] == "d1"
    assert event_from_dict(e.to_dict()) == e
    with pytest.raises(EventValidationError):
        bar(0, 100.0, stream=1)  # type: ignore[arg-type]
