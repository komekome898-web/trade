"""The four sockets other items plug into: fill model (venue), latency
model, cost model, account.

Each is a `typing.Protocol`: an implementation anywhere (`src/bot/bt/fill/`,
`latency/`, `costs/`, `portfolio/`, a test file) that has the methods
below is accepted by `CoreEngine` without editing this package.

Venue reports
-------------
A fill model answers with `VenueReport`s (`Ack`, `Reject`, `Fill`,
`Canceled`, `StateUnknown`). The engine checks every report against the
order's venue-side history (engine.py `_VenueLedger`) and raises
`VenueProtocolError` on a contradiction, so a buggy fill model fails loudly
instead of producing fills that could never happen: a report about an order
that has not reached the venue yet, a fill before the ack, an overfill, a
report after a terminal state, or no answer to an order or a cancel.

Time
----
The fill model is called on the venue's clock: `on_market_event` at the
event's `exchange_time_ns`, `on_order` / `on_cancel` at the request's
arrival time at the venue (strategy send time + latency). It is never
handed an event the venue could not have seen yet.

Account
-------
The account socket is also called on the venue's clock. Per instant and
per market event the engine calls, in this order: `apply_funding` /
`apply_liquidation` (for those event types), the fill model's
`on_market_event` (its fills reach `apply_fill`), then
`account.on_market_event`, which may mark positions and return forced
orders (a margin close-out, say). A forced order goes straight to the fill
model at that venue time (it does not travel the strategy's order
channel), and its notices reach the strategy like any other, with
`OrderView.origin == "forced"`. When one of the strategy's orders reaches
the venue, `account.check_order` is asked first; a non-None answer is
the reject reason (insufficient margin, say) and the fill model never sees
the order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence, Union, runtime_checkable

from .api import CancelRequest, OrderRequest
from .errors import VenueProtocolError
from .events import Event
from .time import validate_nanos
from .values import as_float, as_text


# --- venue reports -----------------------------------------------------------
# A report crosses the venue -> strategy path (the engine turns it into a
# notice), so it is a value (values.py): every field is made when the report
# is made, as the built-in type itself, and the classes are slotted. A
# field of the wrong type is the fill model's error: VenueProtocolError.
# Whether a value is allowed (a request kind, a liquidity, a finite
# positive price) is the engine's check against the order's history
# (engine.py `_VenueLedger`).

def _report_field(make, cls: str, name: str, value: Any) -> Any:
    try:
        return make(value, f"{cls}.{name}")
    except ValueError as exc:
        raise VenueProtocolError(str(exc)) from None


def _make_fields(obj: Any, **makers: Any) -> None:
    cls = type(obj).__name__
    for name, make in makers.items():
        object.__setattr__(obj, name, _report_field(make, cls, name, getattr(obj, name)))


@dataclass(frozen=True, slots=True)
class Ack:
    client_order_id: str
    venue_order_id: str = ""

    def __post_init__(self) -> None:
        _make_fields(self, client_order_id=as_text, venue_order_id=as_text)


@dataclass(frozen=True, slots=True)
class Reject:
    client_order_id: str
    reason: str
    request_kind: str = "new"  # "new" | "cancel"

    def __post_init__(self) -> None:
        _make_fields(self, client_order_id=as_text, reason=as_text, request_kind=as_text)


@dataclass(frozen=True, slots=True)
class Fill:
    client_order_id: str
    price: float
    size: float
    liquidity: str = "taker"  # "maker" | "taker"

    def __post_init__(self) -> None:
        _make_fields(self, client_order_id=as_text, price=as_float, size=as_float, liquidity=as_text)


@dataclass(frozen=True, slots=True)
class Canceled:
    client_order_id: str
    reason: str = "canceled"  # "canceled" | "expired" | "ioc_remainder" | ...

    def __post_init__(self) -> None:
        _make_fields(self, client_order_id=as_text, reason=as_text)


@dataclass(frozen=True, slots=True)
class StateUnknown:
    client_order_id: str
    detail: str = ""
    request_kind: str = "new"

    def __post_init__(self) -> None:
        _make_fields(self, client_order_id=as_text, detail=as_text, request_kind=as_text)


VenueReport = Union[Ack, Reject, Fill, Canceled, StateUnknown]
REPORT_CLASSES: tuple[type, ...] = (Ack, Reject, Fill, Canceled, StateUnknown)


@dataclass(frozen=True, slots=True)
class FillNotice:
    """What the cost model and the account see for one fill. `fee` is 0.0
    when handed to the cost model and carries the cost model's answer when
    handed to the account. Made by the engine from a report; a value like
    the report (values.py)."""

    client_order_id: str
    price: float
    size: float
    side: str = ""
    liquidity: str = "taker"
    # required (no default): a default time would be a real instant (0 =
    # 1970-01-01), so a notice built without one would carry a wrong time
    venue_time_ns: int = field(kw_only=True)
    fee: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "venue_time_ns", int(validate_nanos(self.venue_time_ns)))
        _make_fields(self, client_order_id=as_text, price=as_float, size=as_float, side=as_text,
                     liquidity=as_text, fee=as_float)


# --- sockets -----------------------------------------------------------------

@runtime_checkable
class FillModel(Protocol):
    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        """Market data reaches the venue (at `event.exchange_time_ns`).
        Return fills/cancels (e.g. expiry) for resting orders, or nothing."""
        ...

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        """A new order reaches the venue. Must answer it: `Ack` (optionally
        followed by `Fill`s / `Canceled`), `Reject`, or `StateUnknown`."""
        ...

    def on_cancel(self, request: CancelRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        """A cancel reaches the venue for a live order. Must answer it:
        `Canceled`, `Reject(request_kind="cancel")`, or `StateUnknown`.
        (Cancels for orders that are not live at the venue are answered by
        the engine itself and never reach this method.)"""
        ...


@runtime_checkable
class LatencyModel(Protocol):
    def feed_delay_ns(self, event: Event) -> int:
        """Extra delay, on top of the event's recorded `received_time_ns`,
        before the strategy receives a market-data event."""
        ...

    def order_delay_ns(self, order: OrderRequest, sent_time_ns: int) -> int:
        """Strategy send -> arrival at the venue, for a new order."""
        ...

    def cancel_delay_ns(self, request: CancelRequest, sent_time_ns: int) -> int:
        """Strategy send -> arrival at the venue, for a cancel."""
        ...

    def notice_delay_ns(self, report: VenueReport, venue_time_ns: int) -> int:
        """Venue report -> the strategy receiving the notice."""
        ...


@runtime_checkable
class CostModel(Protocol):
    def cost(self, fill: FillNotice) -> float:
        """Fee for this fill, in the account currency (negative = rebate)."""
        ...


@runtime_checkable
class Account(Protocol):
    def apply_fill(self, fill: FillNotice) -> None:
        """Called at the fill's venue time, with `fill.fee` set."""
        ...

    def apply_funding(self, event: Event) -> None:
        """Called at the funding event's venue time."""
        ...

    def apply_liquidation(self, event: Event) -> None:
        """Called at the liquidation print's venue time."""
        ...

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[OrderRequest]:
        """Called for every market event at its venue time, after the fill
        model has handled it. Mark positions here. Return forced orders
        (e.g. a margin close-out) or nothing."""
        ...

    def check_order(self, order: OrderRequest, venue_time_ns: int) -> Optional[str]:
        """Called when one of the strategy's orders reaches the venue,
        before the fill model. Return None to let it through, or a
        non-empty reject reason."""
        ...


SOCKETS: dict[str, type] = {
    "fill_model": FillModel,
    "latency_model": LatencyModel,
    "cost_model": CostModel,
    "account": Account,
}


def socket_methods(protocol: type) -> list[str]:
    return sorted(
        name
        for name, value in vars(protocol).items()
        if callable(value) and not name.startswith("_")
    )


# --- explicit stand-ins ------------------------------------------------------

class NullFillModel:
    """Accepts every order and never fills it; acknowledges every cancel.
    It is a stand-in so the order lifecycle can run before a real fill model
    (item 3) is plugged in -- not a model of any venue."""

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        return ()

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        return (Ack(order.client_order_id, f"null-{order.client_order_id}"),)

    def on_cancel(self, request: CancelRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        return (Canceled(request.client_order_id),)


class ZeroLatency:
    """Every delay is 0 ns."""

    def feed_delay_ns(self, event: Event) -> int:
        return 0

    def order_delay_ns(self, order: OrderRequest, sent_time_ns: int) -> int:
        return 0

    def cancel_delay_ns(self, request: CancelRequest, sent_time_ns: int) -> int:
        return 0

    def notice_delay_ns(self, report: VenueReport, venue_time_ns: int) -> int:
        return 0


NullLatencyModel = ZeroLatency


class NullCostModel:
    """Zero cost, stated explicitly. The engine has no implicit cost model:
    a fill with no cost model supplied raises `MissingCostModelError`."""

    def cost(self, fill: FillNotice) -> float:
        return 0.0


class NullAccount:
    """Discards fills, funding and liquidations; never rejects an order and
    never forces one. A stand-in until item 6's account is plugged in."""

    def apply_fill(self, fill: FillNotice) -> None:
        return None

    def apply_funding(self, event: Event) -> None:
        return None

    def apply_liquidation(self, event: Event) -> None:
        return None

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[OrderRequest]:
        return ()

    def check_order(self, order: OrderRequest, venue_time_ns: int) -> Optional[str]:
        return None
