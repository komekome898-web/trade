"""Event types (requirement V2).

`EventType` enumerates every kind of thing that can happen in a backtest run
in this project: market data (trade, book snapshot, book delta, bar,
funding, liquidation), the heartbeat (clock), and our own order-flow
feedback (ack, reject, fill). Each member has exactly one corresponding
frozen dataclass below; `ALL_EVENT_CLASSES` and the `test_events.py`
completeness test keep that 1:1 mapping honest.

All event classes share the same base (`Event`): a validated `Nanos`
timestamp (`received_time_ns`, see time.py) and a `seq` used for
tie-breaking (clock.py). No event class stores a time value in any other
unit or type -- that is what keeps V1 true at the type level, not just by
convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from .time import Nanos, validate_nanos


class EventType(Enum):
    TRADE = "TRADE"                  # a match/fill printed by the venue (public tape)
    BOOK_SNAPSHOT = "BOOK_SNAPSHOT"  # full order book snapshot
    BOOK_DELTA = "BOOK_DELTA"        # incremental order book update
    BAR = "BAR"                      # OHLCV candle close
    FUNDING = "FUNDING"              # perpetual/CFD funding rate settlement
    LIQUIDATION = "LIQUIDATION"      # forced liquidation print (ours or market-wide)
    CLOCK = "CLOCK"                  # wall-clock heartbeat tick, carries no market data
    ORDER_ACK = "ORDER_ACK"          # venue accepted an order we sent
    ORDER_REJECT = "ORDER_REJECT"    # venue rejected an order we sent
    ORDER_FILL = "ORDER_FILL"        # venue reported an execution against our order


@dataclass(frozen=True)
class Event:
    """Base class. Never instantiated directly -- use a subclass below."""

    received_time_ns: Nanos
    seq: int  # assigned/overwritten by clock.assign_seq; see clock.py docstring

    def __post_init__(self) -> None:
        object.__setattr__(self, "received_time_ns", validate_nanos(self.received_time_ns))
        if isinstance(self.seq, bool) or not isinstance(self.seq, int):
            raise TypeError(f"seq must be int, got {type(self.seq).__name__}")


@dataclass(frozen=True)
class TradeEvent(Event):
    price: float
    size: float
    side: str  # "buy" | "sell" -- taker side
    trade_id: str
    EVENT_TYPE: ClassVar[EventType] = EventType.TRADE


@dataclass(frozen=True)
class BookSnapshotEvent(Event):
    bids: tuple[tuple[float, float], ...]  # (price, size), best first
    asks: tuple[tuple[float, float], ...]  # (price, size), best first
    EVENT_TYPE: ClassVar[EventType] = EventType.BOOK_SNAPSHOT


@dataclass(frozen=True)
class BookDeltaEvent(Event):
    side: str  # "bid" | "ask"
    price: float
    size: float  # new resting size at this price; 0 means the level is gone
    EVENT_TYPE: ClassVar[EventType] = EventType.BOOK_DELTA


@dataclass(frozen=True)
class BarEvent(Event):
    open: float
    high: float
    low: float
    close: float
    volume: float
    EVENT_TYPE: ClassVar[EventType] = EventType.BAR


@dataclass(frozen=True)
class FundingEvent(Event):
    rate: float  # funding rate for this settlement, as a fraction (e.g. 0.0001)
    EVENT_TYPE: ClassVar[EventType] = EventType.FUNDING


@dataclass(frozen=True)
class LiquidationEvent(Event):
    price: float
    size: float
    side: str  # side of the liquidated position ("long" | "short")
    EVENT_TYPE: ClassVar[EventType] = EventType.LIQUIDATION


@dataclass(frozen=True)
class ClockEvent(Event):
    EVENT_TYPE: ClassVar[EventType] = EventType.CLOCK


@dataclass(frozen=True)
class OrderAckEvent(Event):
    client_order_id: str
    venue_order_id: str
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_ACK


@dataclass(frozen=True)
class OrderRejectEvent(Event):
    client_order_id: str
    reason: str
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_REJECT


@dataclass(frozen=True)
class OrderFillEvent(Event):
    client_order_id: str
    price: float
    size: float
    fee: float = 0.0
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_FILL


ALL_EVENT_CLASSES: tuple[type[Event], ...] = (
    TradeEvent,
    BookSnapshotEvent,
    BookDeltaEvent,
    BarEvent,
    FundingEvent,
    LiquidationEvent,
    ClockEvent,
    OrderAckEvent,
    OrderRejectEvent,
    OrderFillEvent,
)

EVENT_TYPE_TO_CLASS: dict[EventType, type[Event]] = {
    cls.EVENT_TYPE: cls for cls in ALL_EVENT_CLASSES
}
