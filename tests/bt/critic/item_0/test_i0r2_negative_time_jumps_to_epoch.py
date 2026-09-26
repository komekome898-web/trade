"""Critic, item 0, round 2, finding i0-r2-01.

P0-2 (REQUIREMENTS.md line 18): every time in the core is an int64 of UTC
nanoseconds. `validate_nanos` accepts the whole int64 range, negative values
(before 1970-01-01T00:00:00Z) included, and events built with such times are
accepted by `CoreEngine`.

But the FIFO clamps of the request and notice channels start from 0, not from
"no previous entry": `self._last_outbound = 0` / `self._last_notice = 0`
(engine.py 439-440), and `_drain` / `_handle_reports` take
`max(send time + delay, self._last_outbound)` (engine.py 644, 651) and
`max(venue time + delay, self._last_notice)` (engine.py 783). An order sent
at t < 0 therefore reaches the venue at t = 0, and its ACK reaches the
strategy at 0: the run silently moves our orders and notices forward to
1970-01-01, however far before it the data lie. No error, plausible values.
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderRequest,
    Strategy,
    TradeEvent,
)

S = 1_000_000_000
MS = 1_000_000
T = -10 * S  # 1969-12-31T23:59:50Z, a valid int64 of ns


class _Venue:
    def __init__(self) -> None:
        self.order_arrivals: list[int] = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        self.order_arrivals.append(venue_time_ns)
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):  # pragma: no cover
        return (Canceled(request.client_order_id),)


class _BuyOnce(Strategy):
    def __init__(self) -> None:
        self.placed_at = None
        self.ack_at = None

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE is EventType.TRADE and self.placed_at is None:
            self.placed_at = ctx.now_ns
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0))
        elif event.EVENT_TYPE is EventType.ORDER_ACK:
            self.ack_at = ctx.now_ns


def test_order_and_ack_before_1970_keep_their_times():
    trades = [TradeEvent(received_time_ns=T + k * MS, price=100.0, size=1.0, side="buy") for k in range(3)]
    venue, strat = _Venue(), _BuyOnce()
    CoreEngine(strat, trades, fill_model=venue, cost_model=NullCostModel()).run()
    assert strat.placed_at == T
    # zero latency everywhere: the order reaches the venue when it is sent,
    # and the ACK reaches the strategy at that same instant
    assert venue.order_arrivals == [T], f"order sent at {T} reached the venue at {venue.order_arrivals}"
    assert strat.ack_at == T, f"ACK for an order acknowledged at {T} delivered at {strat.ack_at}"
