"""Critic, item 0, round 5 (i0-r5-01, same cause as i0-r4-02): what crosses a
path is still not a value, outside `OrderRequest.extra`.

Round 5 made `extra` immutable plain data (values.py `freeze`) and checks a
notice's text fields with `isinstance(value, str)`. The rule the worker wrote
(values.py module doc, api.py "No acting later") is "nothing that crosses a
path may be shared, changeable state ... a function (it can read the
sender's state when it is called, later), an arbitrary object ... is
refused". But:

* the other fields of `OrderRequest` are kept as the objects given: `size`,
  `price`, `trigger_price` pass `_require_positive` (any `numbers.Real`,
  subclasses included) and `side` / `order_type` / `client_order_id` /
  `time_in_force` pass an `in` / `isinstance(str)` test, so a float or str
  SUBCLASS whose methods read the strategy's state rides to the venue;
* `freeze` accepts any `Enum` member whose `.value` is a scalar, and the
  member's class is the strategy's own class with its own methods;
* the venue -> strategy text check is `isinstance(value, str)`
  (engine.py `_VenueLedger.apply`, events.py `_str`), so a str subclass from
  the fill model rides to the strategy.

Each test sends once, changes nothing through the API afterwards, and checks
that the other side sees what was sent. Any fix that makes these fields
values at construction (exact float / str, or refusing subclasses and
behaviour-carrying Enum members) passes them.
"""
from __future__ import annotations

import enum

import pytest

from bot.bt.core import (
    Ack,
    CoreEngine,
    NullCostModel,
    OrderRequest,
    Reject,
    Strategy,
    TradeEvent,
)
from bot.bt.core.errors import CoreError

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
STATE = {"size": 1.0, "type": "limit", "tag": "sent"}


class _LiveSize(float):
    """A float subclass whose arithmetic reads the strategy's state when the
    venue does the arithmetic (at arrival), not when the order was sent."""

    def __mul__(self, other):
        return STATE["size"] * other

    __rmul__ = __mul__

    def __float__(self):
        return STATE["size"]


class _LiveType(str):
    def __eq__(self, other):
        return STATE["type"] == other

    __hash__ = str.__hash__


class _LiveTag(enum.Enum):
    A = 1

    def __eq__(self, other):
        return STATE["tag"] == other

    __hash__ = enum.Enum.__hash__


class _Latency:
    def feed_delay_ns(self, event) -> int:
        return 0

    def order_delay_ns(self, order, sent_time_ns) -> int:
        return 10 * SEC  # arrives 10 s after it was sent

    def cancel_delay_ns(self, request, sent_time_ns) -> int:
        return 0

    def notice_delay_ns(self, report, venue_time_ns) -> int:
        return 0


class _Venue:
    def __init__(self) -> None:
        self.seen: list[dict] = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        self.seen.append({
            "t": venue_time_ns,
            "notional": order.size * 100.0,
            "float_size": float(order.size),
            "is_market": order.order_type == "market",
            "tag_changed": order.extra_dict().get("tag") == "changed",
        })
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        return ()


def _send_then_change(make_request) -> dict:
    STATE.update(size=1.0, type="limit", tag="sent")
    venue = _Venue()

    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0:
                try:
                    ctx.place_order(make_request())
                except CoreError:
                    pass  # refused when made: nothing was sent, nothing can change later
            elif ctx.now_ns == T0 + SEC:  # a later callback; the order is still in flight
                STATE.update(size=500.0, type="market", tag="changed")

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(12)]
    CoreEngine(_S(), events, fill_model=venue, latency_model=_Latency(), cost_model=NullCostModel()).run()
    return venue.seen[0] if venue.seen else {}


def test_size_the_venue_uses_at_arrival_is_the_size_sent():
    got = _send_then_change(lambda: OrderRequest(side="buy", order_type="limit", size=_LiveSize(1.0), price=90.0))
    if got:
        assert got["notional"] == 100.0 and got["float_size"] == 1.0, (
            f"the venue computed size * 100 = {got['notional']} and float(size) = {got['float_size']} at arrival "
            f"for an order sent with size 1: the strategy changed it from a later callback without sending anything"
        )


def test_order_type_the_venue_reads_at_arrival_is_the_type_sent():
    got = _send_then_change(lambda: OrderRequest(side="buy", order_type=_LiveType("limit"), size=1.0, price=90.0))
    if got:
        assert got["is_market"] is False, (
            "an order sent as 'limit' compares equal to 'market' at the venue at arrival: the strategy "
            "changed it from a later callback without sending anything"
        )


def test_enum_member_in_extra_is_what_was_sent():
    got = _send_then_change(lambda: OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                                 extra=(("tag", _LiveTag.A),)))
    if got:
        assert got["tag_changed"] is False, (
            "an Enum member of the strategy's own class in `extra` compares equal to 'changed' at the venue "
            "at arrival: freeze() accepted a member whose methods read the sender's state later"
        )


class _LiveText(str):
    SECRET = {"text": "none"}

    def __str__(self):
        return _LiveText.SECRET["text"]

    def __contains__(self, item):
        return item in _LiveText.SECRET["text"]

    __hash__ = str.__hash__


def test_notice_text_does_not_change_after_it_was_delivered():
    _LiveText.SECRET["text"] = "none"

    class _RejectingVenue:
        def on_market_event(self, event, venue_time_ns):
            if venue_time_ns == T0 + 5 * SEC:
                _LiveText.SECRET["text"] = "venue secret at T0+5s"
            return ()

        def on_order(self, order, venue_time_ns):
            return (Reject(order.client_order_id, _LiveText("rejected")),)

        def on_cancel(self, request, venue_time_ns):
            return ()

    seen: list = []

    class _S(Strategy):
        def __init__(self) -> None:
            self.coid = None

        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0 and self.coid is None:
                self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
            elif self.coid is not None:
                reason = ctx.order(self.coid).reason
                seen.append((ctx.now_ns, type(event).__name__, str(reason), "secret" in reason))

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(7)]
    try:
        CoreEngine(_S(), events, fill_model=_RejectingVenue(), cost_model=NullCostModel()).run()
    except CoreError:
        return  # the core refused the report: the venue's live object never reached the strategy
    texts = {(s, c) for _, _, s, c in seen}
    assert len(texts) == 1, (
        f"the reject's reason read by the strategy changed with no notice delivered: {seen}"
    )
