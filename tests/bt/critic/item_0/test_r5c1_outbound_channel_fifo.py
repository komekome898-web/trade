"""Critic, item 0, round 1 of run 5 (i0-r1-05).

engine.py (module docstring, lines 14-19) and ordering.py
(`ORDERING_RULE["channels_fifo"]`) promise that the strategy -> venue channel
is FIFO: "a later request never overtakes an earlier one, ... as on a single
connection".

`_drain` (engine.py 532-548) keeps arrival TIMES monotone with
`max(sent + delay, self._last_outbound)`, but two requests that end up with
the same arrival time are then ordered by queue priority, and
`VENUE_ORDER = 10 < VENUE_CANCEL = 11` (ordering.py 110-111). So a cancel
sent BEFORE a new order, arriving at the same instant, reaches the venue
AFTER it. The venue (fill model, account.check_order) sees the new order
while the order the strategy already asked to cancel is still live -- e.g.
a margin check that rejects the new order although the strategy freed the
margin first. Nothing errors; the run is silently wrong.
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    NullCostModel,
    OrderRequest,
    Strategy,
    TradeEvent,
)

T0 = 1_700_006_400_000_000_000
DAY = 86_400 * 1_000_000_000


class _RecordingVenue:
    def __init__(self) -> None:
        self.seen: list[tuple[str, str]] = []

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        self.seen.append(("new", order.client_order_id))
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        self.seen.append(("cancel", request.client_order_id))
        return (Canceled(request.client_order_id),)


class _CancelThenPlace(Strategy):
    def __init__(self) -> None:
        self.n = 0

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE.value != "TRADE":
            return
        self.n += 1
        if self.n == 1:
            ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                         client_order_id="X"))
        elif self.n == 2:
            ctx.cancel_order("X")  # sent first
            ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=91.0,
                                         client_order_id="Y"))  # sent second


def test_cancel_sent_before_a_new_order_reaches_the_venue_first():
    trades = [TradeEvent(received_time_ns=T0 + k * DAY, price=100.0, size=100.0, side="buy")
              for k in (1, 2, 3)]
    venue = _RecordingVenue()
    CoreEngine(_CancelThenPlace(), trades, fill_model=venue, cost_model=NullCostModel()).run()
    assert venue.seen == [("new", "X"), ("cancel", "X"), ("new", "Y")], (
        f"the venue saw the requests in the order {venue.seen}; the strategy sent "
        f"cancel X before new Y on one FIFO channel"
    )
