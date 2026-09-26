"""Critic, item 0, round 4 (i0-r4-02): an order already sent can still be
changed by the strategy while it travels to the venue.

`OrderRequest` is frozen, but `extra` (api.py, "anything else a venue model
needs") is only checked to be a tuple: its values may be mutable (a list, a
dict). The engine hands the SAME request object to the outbound channel
(api.py `_OrderPort.place` appends `request`; engine.py `_drain` pushes it;
`_venue_order` hands it to `account.check_order` / `fill_model.on_order` at
the arrival time). So a strategy that mutates a value it put in `extra`
AFTER the callback that sent the order returned -- in a later callback,
while the order is still in flight -- changes what the venue receives. On a
real connection the request is bytes on the wire at send time; changing it
later needs a new message (an amend or a cancel). api.py promises "No acting
later ... any later attempt to ... act raises StaleContextError", and the
strategy -> venue path is a FIFO channel carrying what was SENT.

The fill model here copies what it receives at arrival. A request that is
a snapshot at send time shows ["sent"]; this core shows ["sent", "changed
later"].
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    CoreEngine,
    NullCostModel,
    OrderRequest,
    Strategy,
    TradeEvent,
)

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


class _Latency:
    def feed_delay_ns(self, event) -> int:
        return 0

    def order_delay_ns(self, order, sent_time_ns) -> int:
        return 10 * SEC  # the order arrives at the venue 10 s after it was sent

    def cancel_delay_ns(self, request, sent_time_ns) -> int:
        return 0

    def notice_delay_ns(self, report, venue_time_ns) -> int:
        return 0


class _Venue:
    def __init__(self) -> None:
        self.received = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        meta = order.extra_dict()["meta"]
        self.received.append((venue_time_ns, list(meta) if isinstance(meta, list) else dict(meta)))
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        return ()


def _run(make_meta, change):
    venue = _Venue()

    class _S(Strategy):
        def __init__(self) -> None:
            self.meta = None

        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0:
                self.meta = make_meta()
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                             extra=(("meta", self.meta),)))
            elif ctx.now_ns == T0 + SEC:  # a later callback, the order still in flight
                change(self.meta)

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(12)]
    CoreEngine(_S(), events, fill_model=venue, latency_model=_Latency(), cost_model=NullCostModel()).run()
    return venue.received


def test_list_in_extra_changed_after_sending_does_not_reach_the_venue():
    got = _run(lambda: ["sent"], lambda m: m.append("changed later"))
    assert got and got[0][0] == T0 + 10 * SEC
    assert got[0][1] == ["sent"], (
        f"the venue received {got[0][1]!r} at arrival: the strategy changed an order in flight "
        f"from a later callback, without sending anything"
    )


def test_dict_in_extra_changed_after_sending_does_not_reach_the_venue():
    got = _run(lambda: {"iceberg_show": 1.0}, lambda m: m.update(iceberg_show=0.0))
    assert got[0][1] == {"iceberg_show": 1.0}, (
        f"the venue received {got[0][1]!r} at arrival: the strategy changed an order in flight"
    )
