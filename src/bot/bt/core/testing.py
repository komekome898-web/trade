"""Small, explicit test doubles for exercising the sockets.

These are NOT models of any venue and must not be used for research runs:
item 3 owns fill models, item 5 owns costs, item 6 owns accounts. They
exist so tests (this package's, the battery's, other items') can drive the
full order lifecycle through `CoreEngine` without writing a venue each
time.
"""
from __future__ import annotations

from typing import Optional, Sequence

from .api import CancelRequest, OrderRequest
from .events import BarEvent, Event, TradeEvent
from .interfaces import Ack, Canceled, Fill, FillNotice, Reject, VenueReport


class ImmediateFillModel:
    """Market orders fill in full, as taker, at `fixed_price` if given, else
    at the last trade price / bar close the VENUE has seen at arrival time
    (rejected with reason "no_price" if it has seen none). Any other order
    type is acknowledged and rests without ever filling; cancels succeed."""

    def __init__(self, fixed_price: Optional[float] = None) -> None:
        self._fixed = fixed_price
        self._last: Optional[float] = None
        self.market_events_seen: list[tuple[int, Event]] = []

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        self.market_events_seen.append((venue_time_ns, event))
        if isinstance(event, TradeEvent):
            self._last = event.price
        elif isinstance(event, BarEvent):
            self._last = event.close
        return ()

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        coid = order.client_order_id
        if order.order_type != "market":
            return (Ack(coid, f"imm-{coid}"),)
        price = self._fixed if self._fixed is not None else self._last
        if price is None:
            return (Reject(coid, "no_price"),)
        return (Ack(coid, f"imm-{coid}"), Fill(coid, price, order.size, "taker"))

    def on_cancel(self, request: CancelRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        return (Canceled(request.client_order_id),)


class FixedRateCost:
    """fee = |price * size| * rate."""

    def __init__(self, rate: float) -> None:
        self.rate = rate

    def cost(self, fill: FillNotice) -> float:
        return abs(fill.price * fill.size) * self.rate


class RecordingAccount:
    """Keeps every call it receives, in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def apply_fill(self, fill: FillNotice) -> None:
        self.calls.append(("fill", fill))

    def apply_funding(self, event: Event) -> None:
        self.calls.append(("funding", event))

    def apply_liquidation(self, event: Event) -> None:
        self.calls.append(("liquidation", event))

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[OrderRequest]:
        self.calls.append(("market", event))
        return ()

    def check_order(self, order: OrderRequest, venue_time_ns: int) -> Optional[str]:
        self.calls.append(("check_order", order))
        return None
