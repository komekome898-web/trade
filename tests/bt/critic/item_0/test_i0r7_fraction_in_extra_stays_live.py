"""Critic, item 0, round 7 (same cause as i0-r5-01 / i0-r4-02): a value in
`OrderRequest.extra` that is still changeable state of the sender's.

values.py keeps "an instance of an exact built-in scalar type (None, bool,
int, float, complex, str, bytes, Decimal, Fraction)" as the SAME object
(`_SCALARS`, `_plain_scalar`: `if t in _SCALARS: return value`). The rule
it serves (values.py module doc): "nothing that crosses a path may be
shared, changeable state ... of the sender's". `fractions.Fraction` is not
immutable: it is a pure-Python class with `__slots__ = ('_numerator',
'_denominator')`, and slot attributes can be assigned. So the strategy that
sent a Fraction in `extra` keeps a reference to the very object the venue
reads at the arrival time and can change it from a later callback without
sending anything -- a path that skips the order latency.

The test sends once, changes the kept object from a later callback (not
through the API), and checks that the venue at arrival sees what was sent.
Any fix that makes the value a value when the request is made (store an
immutable copy, convert, or refuse) passes it.
"""
from __future__ import annotations

from fractions import Fraction

from bot.bt.core import Ack, CoreEngine, NullCostModel, OrderRequest, Strategy, TradeEvent
from bot.bt.core.errors import CoreError

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


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
        self.seen: list = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        self.seen.append((venue_time_ns, order.extra_dict().get("ratio")))
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        return ()


def test_fraction_in_extra_is_what_was_sent():
    venue = _Venue()
    kept = Fraction(1, 3)
    refused = []

    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0:
                try:
                    ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                                 extra=(("ratio", kept),)))
                except CoreError:
                    refused.append(True)  # refused when made: nothing crosses, nothing can change later
            elif ctx.now_ns == T0 + SEC:  # a later callback; the order is still in flight
                kept._numerator = 999  # the sender's object, changed without sending anything

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(12)]
    CoreEngine(_S(), events, fill_model=venue, latency_model=_Latency(), cost_model=NullCostModel()).run()
    if refused:
        return
    assert venue.seen, "the order never reached the venue"
    t, got = venue.seen[0]
    assert got == Fraction(1, 3), (
        f"the venue read extra['ratio'] = {got!r} at {t} for an order sent with Fraction(1, 3): the strategy "
        f"changed the kept Fraction from a later callback without sending anything (values.py keeps a "
        f"Fraction as the same object, and a Fraction's slots can be assigned)"
    )
