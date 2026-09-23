import dataclasses
import math

import pytest

from bot.bt.core import (
    ALL_EVENT_CLASSES,
    EVENT_TYPE_TO_CLASS,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    Event,
    EventType,
    EventValidationError,
    FundingEvent,
    LiquidationEvent,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderStateUnknownEvent,
    TimestampUnitError,
    TradeEvent,
    event_from_dict,
)

from ._util import T0

SAMPLES = [
    TradeEvent(received_time_ns=T0 + 123456789, price=5012345.0, size=0.01, side="buy", trade_id="x"),
    BookSnapshotEvent(received_time_ns=T0, bids=[[5012000.0, 0.5], [5011000.0, 1.0]], asks=[[5012500.0, 0.4]]),
    BookDeltaEvent(received_time_ns=T0, side="bid", price=5012000.0, size=0.3),
    BarEvent(received_time_ns=T0, open=100.0, high=101.0, low=99.0, close=100.5, volume=12.0, start_time_ns=T0 - 60 * 10**9),
    FundingEvent(received_time_ns=T0, rate=-0.0001, mark_price=5000000.0),
    LiquidationEvent(received_time_ns=T0, price=4990000.0, size=0.2, side="sell"),
    ClockEvent(received_time_ns=T0, tag="t"),
    OrderAckEvent(received_time_ns=T0, client_order_id="c1", venue_order_id="v1"),
    OrderRejectEvent(received_time_ns=T0, client_order_id="c1", reason="r", request_kind="cancel"),
    OrderFillEvent(received_time_ns=T0, client_order_id="c1", price=1.0, size=2.0, side="sell", liquidity="maker", fee=-0.1),
    OrderCanceledEvent(received_time_ns=T0, client_order_id="c1"),
    OrderStateUnknownEvent(received_time_ns=T0, client_order_id="c1", detail="timeout"),
]


def test_one_class_per_event_type():
    assert {c.EVENT_TYPE for c in ALL_EVENT_CLASSES} == set(EventType)
    assert len(ALL_EVENT_CLASSES) == len(EventType)
    assert {type(s).EVENT_TYPE for s in SAMPLES} == set(EventType)
    assert EVENT_TYPE_TO_CLASS[EventType.BAR] is BarEvent


@pytest.mark.parametrize("event", SAMPLES, ids=lambda e: e.EVENT_TYPE.value)
def test_to_dict_roundtrip_is_lossless(event):
    d = event.to_dict()
    assert d["type"] == event.EVENT_TYPE.value
    assert event_from_dict(d) == event
    # JSON-friendly: no tuples left
    assert not any(isinstance(v, tuple) for v in d.values())


def test_book_levels_normalised_to_tuples_and_values_kept():
    e = SAMPLES[1]
    assert e.bids == ((5012000.0, 0.5), (5011000.0, 1.0))
    assert e.to_dict()["bids"] == [[5012000.0, 0.5], [5011000.0, 1.0]]


def test_events_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        SAMPLES[0].price = 1.0  # type: ignore[misc]


def test_base_event_is_abstract():
    with pytest.raises(TypeError):
        Event(received_time_ns=T0)


def test_exchange_time_defaults_to_received_and_may_not_exceed_it():
    assert SAMPLES[0].exchange_time_ns == SAMPLES[0].received_time_ns
    ok = TradeEvent(received_time_ns=T0 + 5, exchange_time_ns=T0, price=1.0, size=1.0, side="")
    assert ok.exchange_time_ns == T0
    with pytest.raises(EventValidationError):
        TradeEvent(received_time_ns=T0, exchange_time_ns=T0 + 1, price=1.0, size=1.0, side="buy")


def test_timestamps_must_be_int_ns():
    with pytest.raises(TimestampUnitError):
        ClockEvent(received_time_ns=1.7e18)
    with pytest.raises(TimestampUnitError):
        ClockEvent(received_time_ns=True)


@pytest.mark.parametrize(
    "build",
    [
        lambda: TradeEvent(received_time_ns=T0, price=math.nan, size=1.0, side="buy"),
        lambda: TradeEvent(received_time_ns=T0, price=1.0, size=0.0, side="buy"),
        lambda: TradeEvent(received_time_ns=T0, price=1.0, size=1.0, side="long"),
        lambda: BookSnapshotEvent(received_time_ns=T0, bids=[[1.0, 1.0], [2.0, 1.0]], asks=[]),
        lambda: BookSnapshotEvent(received_time_ns=T0, bids=[], asks=[[2.0, 1.0], [2.0, 1.0]]),
        lambda: BookSnapshotEvent(received_time_ns=T0, bids=[[1.0]], asks=[]),
        lambda: BookDeltaEvent(received_time_ns=T0, side="buy", price=1.0, size=1.0),
        lambda: BookDeltaEvent(received_time_ns=T0, side="bid", price=1.0, size=-1.0),
        lambda: BarEvent(received_time_ns=T0, open=1.0, high=0.5, low=0.4, close=1.0, volume=1.0),
        lambda: BarEvent(received_time_ns=T0, open=1.0, high=2.0, low=1.5, close=1.8, volume=1.0),
        lambda: BarEvent(received_time_ns=T0, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0, start_time_ns=T0 + 1),
        lambda: FundingEvent(received_time_ns=T0, rate=math.inf),
        lambda: LiquidationEvent(received_time_ns=T0, price=1.0, size=1.0, side="long"),
        lambda: OrderAckEvent(received_time_ns=T0, client_order_id=""),
        lambda: OrderRejectEvent(received_time_ns=T0, client_order_id="c", reason="r", request_kind="amend"),
        lambda: OrderFillEvent(received_time_ns=T0, client_order_id="c", price=1.0, size=1.0, liquidity="both"),
        lambda: ClockEvent(received_time_ns=T0, seq=1.5),
    ],
)
def test_invalid_fields_are_rejected(build):
    with pytest.raises(EventValidationError):
        build()
