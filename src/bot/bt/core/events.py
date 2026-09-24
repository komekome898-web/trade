"""Event types.

`EventType` enumerates everything that can reach a strategy in a run:

* market data -- TRADE (public execution print), BOOK_SNAPSHOT,
  BOOK_DELTA, BAR, FUNDING, LIQUIDATION;
* the heartbeat -- CLOCK (from the data source, or a timer the strategy
  set with `StrategyContext.set_timer`);
* order-flow notices about our own orders -- ORDER_ACK, ORDER_REJECT,
  ORDER_FILL, ORDER_CANCELED, ORDER_STATE_UNKNOWN. Notices are produced by
  the engine from the fill model's reports; an event source may not supply
  them (see `SOURCE_EVENT_TYPES`).

Two timestamps, both int64 UTC nanoseconds (time.py):

* `exchange_time_ns` -- when the thing happened at the venue. The venue
  side of the engine (the fill model) processes market data at this time.
* `received_time_ns` -- when our process could first have received it. A
  strategy is called for an event at its received time and can only ever
  see events whose received time is <= its current time (engine.py).
  `exchange_time_ns` defaults to `received_time_ns` and may never exceed
  it.

A BAR's timestamps are the time the bar became complete (its close), never
its open: delivering an open-labelled bar at its open time would let a
strategy see the bar's high/low/close before they happened. `start_time_ns`
optionally records the bar's open; if given it must be strictly before the
close (a bar covers [start, close) with a positive length), so an
open-stamped bar (start == close) is refused.

Every event is frozen and validated at construction; `to_dict()` returns a
JSON-friendly copy of every field (tuples become lists).
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar, Optional

from .errors import EventValidationError
from .time import Nanos, validate_nanos


class EventType(Enum):
    TRADE = "TRADE"
    BOOK_SNAPSHOT = "BOOK_SNAPSHOT"
    BOOK_DELTA = "BOOK_DELTA"
    BAR = "BAR"
    FUNDING = "FUNDING"
    LIQUIDATION = "LIQUIDATION"
    CLOCK = "CLOCK"
    ORDER_ACK = "ORDER_ACK"
    ORDER_REJECT = "ORDER_REJECT"
    ORDER_FILL = "ORDER_FILL"
    ORDER_CANCELED = "ORDER_CANCELED"
    ORDER_STATE_UNKNOWN = "ORDER_STATE_UNKNOWN"


MARKET_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.TRADE,
        EventType.BOOK_SNAPSHOT,
        EventType.BOOK_DELTA,
        EventType.BAR,
        EventType.FUNDING,
        EventType.LIQUIDATION,
    }
)
NOTICE_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.ORDER_ACK,
        EventType.ORDER_REJECT,
        EventType.ORDER_FILL,
        EventType.ORDER_CANCELED,
        EventType.ORDER_STATE_UNKNOWN,
    }
)
SOURCE_EVENT_TYPES: frozenset[EventType] = MARKET_EVENT_TYPES | {EventType.CLOCK}

ORDER_SIDES = ("buy", "sell")
TRADE_SIDES = ("buy", "sell", "")  # "" = aggressor unknown (e.g. an auction print)
BOOK_SIDES = ("bid", "ask")
LIQUIDITY = ("maker", "taker")
REQUEST_KINDS = ("new", "cancel")
# What an ORDER_CANCELED notice answers: "cancel" = one of our cancels (the
# venue's answer to it), "new" = part of the answer to the new order (an IOC
# remainder, say), "venue" = the venue acted on its own (expiry, say).
CANCELED_ANSWERS = ("cancel", "new", "venue")


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise EventValidationError(f"{name} must be a number, got bool")
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise EventValidationError(f"{name} must be a number, got {value!r}") from exc
    if not math.isfinite(f):
        raise EventValidationError(f"{name} must be finite, got {value!r}")
    return f


def _positive(name: str, value: Any) -> float:
    f = _finite(name, value)
    if f <= 0:
        raise EventValidationError(f"{name} must be > 0, got {value!r}")
    return f


def _non_negative(name: str, value: Any) -> float:
    f = _finite(name, value)
    if f < 0:
        raise EventValidationError(f"{name} must be >= 0, got {value!r}")
    return f


def _choice(name: str, value: Any, allowed: tuple) -> str:
    if value not in allowed:
        raise EventValidationError(f"{name} must be one of {allowed}, got {value!r}")
    return value


def _str(name: str, value: Any) -> str:
    """A text field of a notice. Text only: a notice crosses the venue ->
    strategy path, so it may not carry state the venue could still change
    after sending it (values.py, i0-r4-02)."""
    if not isinstance(value, str):
        raise EventValidationError(f"{name} must be a str, got {type(value).__name__}")
    return value


def _nonempty_str(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise EventValidationError(f"{name} must be a non-empty str, got {value!r}")
    return value


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base class. Only subclasses are instantiated."""

    received_time_ns: Nanos
    exchange_time_ns: Optional[Nanos] = None
    seq: int = 0  # set by the engine on delivery: the strategy's own delivery count (1, 2, 3, ...)

    EVENT_TYPE: ClassVar[EventType]

    def __post_init__(self) -> None:
        if type(self) is Event:
            raise TypeError("Event is abstract; instantiate a subclass")
        recv = validate_nanos(self.received_time_ns)
        object.__setattr__(self, "received_time_ns", recv)
        exch = recv if self.exchange_time_ns is None else validate_nanos(self.exchange_time_ns)
        if exch > recv:
            raise EventValidationError(
                f"exchange_time_ns {exch} is after received_time_ns {recv}: an "
                f"event cannot be received before it happened"
            )
        object.__setattr__(self, "exchange_time_ns", exch)
        if isinstance(self.seq, bool) or not isinstance(self.seq, int):
            raise EventValidationError(f"seq must be int, got {type(self.seq).__name__}")
        self._validate()

    def _validate(self) -> None:  # overridden per type
        return None

    @property
    def event_type(self) -> EventType:
        return self.EVENT_TYPE

    def to_dict(self) -> dict:
        out: dict = {"type": self.EVENT_TYPE.value}
        for f in dataclasses.fields(self):
            out[f.name] = _plain(getattr(self, f.name))
        return out


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    return value


@dataclass(frozen=True, kw_only=True)
class TradeEvent(Event):
    price: float
    size: float
    side: str  # taker side: "buy" | "sell" | "" (unknown)
    trade_id: str = ""
    EVENT_TYPE: ClassVar[EventType] = EventType.TRADE

    def _validate(self) -> None:
        object.__setattr__(self, "price", _positive("price", self.price))
        object.__setattr__(self, "size", _positive("size", self.size))
        _choice("side", self.side, TRADE_SIDES)
        if not isinstance(self.trade_id, str):
            raise EventValidationError("trade_id must be str")


def _levels(name: str, raw: Any, descending: bool) -> tuple[tuple[float, float], ...]:
    try:
        items = list(raw)
    except TypeError as exc:
        raise EventValidationError(f"{name} must be a sequence of (price, size)") from exc
    out: list[tuple[float, float]] = []
    for i, level in enumerate(items):
        try:
            price, size = level
        except (TypeError, ValueError) as exc:
            raise EventValidationError(f"{name}[{i}] must be a (price, size) pair") from exc
        out.append((_positive(f"{name}[{i}].price", price), _non_negative(f"{name}[{i}].size", size)))
    for i in range(1, len(out)):
        prev, cur = out[i - 1][0], out[i][0]
        ok = cur < prev if descending else cur > prev
        if not ok:
            order = "strictly descending" if descending else "strictly ascending"
            raise EventValidationError(f"{name} prices must be {order} (best first); index {i}")
    return tuple(out)


@dataclass(frozen=True, kw_only=True)
class BookSnapshotEvent(Event):
    bids: tuple[tuple[float, float], ...]  # (price, size), best (highest) first
    asks: tuple[tuple[float, float], ...]  # (price, size), best (lowest) first
    EVENT_TYPE: ClassVar[EventType] = EventType.BOOK_SNAPSHOT

    def _validate(self) -> None:
        object.__setattr__(self, "bids", _levels("bids", self.bids, descending=True))
        object.__setattr__(self, "asks", _levels("asks", self.asks, descending=False))


@dataclass(frozen=True, kw_only=True)
class BookDeltaEvent(Event):
    side: str  # "bid" | "ask"
    price: float
    size: float  # new resting size at this price; 0 removes the level
    EVENT_TYPE: ClassVar[EventType] = EventType.BOOK_DELTA

    def _validate(self) -> None:
        _choice("side", self.side, BOOK_SIDES)
        object.__setattr__(self, "price", _positive("price", self.price))
        object.__setattr__(self, "size", _non_negative("size", self.size))


@dataclass(frozen=True, kw_only=True)
class BarEvent(Event):
    open: float
    high: float
    low: float
    close: float
    volume: float
    start_time_ns: Optional[Nanos] = None  # bar open; timestamps above are the close
    EVENT_TYPE: ClassVar[EventType] = EventType.BAR

    def _validate(self) -> None:
        o = _positive("open", self.open)
        h = _positive("high", self.high)
        lo = _positive("low", self.low)
        c = _positive("close", self.close)
        v = _non_negative("volume", self.volume)
        if h < max(o, c, lo) or lo > min(o, c, h):
            raise EventValidationError(
                f"bar invariant violated: open={o} high={h} low={lo} close={c}"
            )
        for name, val in (("open", o), ("high", h), ("low", lo), ("close", c), ("volume", v)):
            object.__setattr__(self, name, val)
        if self.start_time_ns is not None:
            start = validate_nanos(self.start_time_ns)
            if start >= self.exchange_time_ns:
                # A bar aggregates the interval [start_time_ns, exchange_time_ns)
                # and needs a positive length. start == close is the signature
                # of a bar stamped at its open (its high/low/close would reach
                # the strategy at the open); one print is a TradeEvent.
                raise EventValidationError(
                    f"start_time_ns {start} is not before the bar's completion time "
                    f"{self.exchange_time_ns}; a bar covers [start, close) with a "
                    f"positive length and is timestamped at its close, not its open"
                )
            object.__setattr__(self, "start_time_ns", start)


@dataclass(frozen=True, kw_only=True)
class FundingEvent(Event):
    rate: float  # fraction for this settlement (may be negative)
    mark_price: Optional[float] = None
    EVENT_TYPE: ClassVar[EventType] = EventType.FUNDING

    def _validate(self) -> None:
        object.__setattr__(self, "rate", _finite("rate", self.rate))
        if self.mark_price is not None:
            object.__setattr__(self, "mark_price", _positive("mark_price", self.mark_price))


@dataclass(frozen=True, kw_only=True)
class LiquidationEvent(Event):
    """A forced-liquidation order printed by the venue. `side` is the side of
    the liquidation ORDER ("sell" = a long position was liquidated), matching
    how venues publish it; position-side words ("long"/"short") are rejected
    rather than guessed."""

    price: float
    size: float
    side: str  # "buy" | "sell"
    EVENT_TYPE: ClassVar[EventType] = EventType.LIQUIDATION

    def _validate(self) -> None:
        object.__setattr__(self, "price", _positive("price", self.price))
        object.__setattr__(self, "size", _positive("size", self.size))
        _choice("side", self.side, ORDER_SIDES)


@dataclass(frozen=True, kw_only=True)
class ClockEvent(Event):
    tag: str = ""  # set by StrategyContext.set_timer; "" for source heartbeats
    EVENT_TYPE: ClassVar[EventType] = EventType.CLOCK

    def _validate(self) -> None:
        if not isinstance(self.tag, str):
            raise EventValidationError("tag must be str")


@dataclass(frozen=True, kw_only=True)
class OrderAckEvent(Event):
    client_order_id: str
    venue_order_id: str = ""
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_ACK

    def _validate(self) -> None:
        _nonempty_str("client_order_id", self.client_order_id)
        _str("venue_order_id", self.venue_order_id)


@dataclass(frozen=True, kw_only=True)
class OrderRejectEvent(Event):
    client_order_id: str
    reason: str
    request_kind: str = "new"  # "new" = order rejected, "cancel" = cancel rejected
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_REJECT

    def _validate(self) -> None:
        _nonempty_str("client_order_id", self.client_order_id)
        _str("reason", self.reason)
        _choice("request_kind", self.request_kind, REQUEST_KINDS)


@dataclass(frozen=True, kw_only=True)
class OrderFillEvent(Event):
    client_order_id: str
    price: float
    size: float
    side: str = ""  # filled for the order's side; "" only when built by hand
    liquidity: str = "taker"
    fee: float = 0.0  # from the run's cost model, account currency
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_FILL

    def _validate(self) -> None:
        _nonempty_str("client_order_id", self.client_order_id)
        object.__setattr__(self, "price", _positive("price", self.price))
        object.__setattr__(self, "size", _positive("size", self.size))
        _choice("side", self.side, ORDER_SIDES + ("",))
        _choice("liquidity", self.liquidity, LIQUIDITY)
        object.__setattr__(self, "fee", _finite("fee", self.fee))


@dataclass(frozen=True, kw_only=True)
class OrderCanceledEvent(Event):
    client_order_id: str
    reason: str = "canceled"
    # what this cancellation answers (one of CANCELED_ANSWERS), set by the
    # engine from where the venue reported it. Not `request_kind`: a reject
    # names the request refused, this names the request (if any) answered.
    answers: str = "venue"
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_CANCELED

    def _validate(self) -> None:
        _nonempty_str("client_order_id", self.client_order_id)
        _str("reason", self.reason)
        _choice("answers", self.answers, CANCELED_ANSWERS)


@dataclass(frozen=True, kw_only=True)
class OrderStateUnknownEvent(Event):
    """The venue's answer to a request was ambiguous (timeout, dropped
    connection). The order is held as STATE_UNKNOWN in the strategy's view
    and counted as open. The engine never resends anything on its own
    (CLAUDE.md section 1); only a later report from the venue resolves it."""

    client_order_id: str
    detail: str = ""
    request_kind: str = "new"
    EVENT_TYPE: ClassVar[EventType] = EventType.ORDER_STATE_UNKNOWN

    def _validate(self) -> None:
        _nonempty_str("client_order_id", self.client_order_id)
        _str("detail", self.detail)
        _choice("request_kind", self.request_kind, REQUEST_KINDS)


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
    OrderCanceledEvent,
    OrderStateUnknownEvent,
)

EVENT_TYPE_TO_CLASS: dict[EventType, type[Event]] = {cls.EVENT_TYPE: cls for cls in ALL_EVENT_CLASSES}

assert set(EVENT_TYPE_TO_CLASS) == set(EventType), "every EventType needs exactly one class"


def event_from_dict(data: dict) -> Event:
    """Inverse of `Event.to_dict()`."""
    payload = dict(data)
    try:
        etype = EventType(payload.pop("type"))
    except (KeyError, ValueError) as exc:
        raise EventValidationError(f"unknown or missing event type in {data!r}") from exc
    return EVENT_TYPE_TO_CLASS[etype](**payload)
