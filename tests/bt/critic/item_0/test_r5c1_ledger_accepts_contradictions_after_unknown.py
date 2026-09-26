"""Critic, item 0, round 1 of run 5 (i0-r1-07).

interfaces.py 8-16 promises that the engine checks every fill-model report
against the order's venue-side history and raises `VenueProtocolError` on a
contradiction ("a fill before the ack, an overfill, a report after a
terminal state ..."), and `_VenueLedger.apply` refuses a "new-order Reject
for acknowledged order" (engine.py 184-186).

But STATE_UNKNOWN erases the history: `apply` sets the state to UNKNOWN for
ANY StateUnknown (also `request_kind="cancel"`, engine.py 211-212), and from
UNKNOWN it accepts a second Ack (180-182) and a new-order Reject (185-187)
even when the order was already acknowledged and partly FILLED. An order
that has fills ends as REJECTED, both in the venue ledger and in the
strategy's view -- the account kept the fill, the strategy is told the
order never existed. A buggy fill model is not caught.
"""
from __future__ import annotations

import pytest

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    Fill,
    NullCostModel,
    OrderRequest,
    Reject,
    StateUnknown,
    Strategy,
    TradeEvent,
    VenueProtocolError,
)

T0 = 1_700_006_400_000_000_000
DAY = 86_400 * 1_000_000_000


class _Contradicting:
    """Ack + half fill; the cancel is answered ambiguously; then the venue
    'rejects' the (already acknowledged, half filled) order as a new order."""

    def __init__(self, second_report) -> None:
        self.coid = None
        self.after_unknown = False
        self.second_report = second_report

    def on_market_event(self, event, venue_time_ns):
        if self.after_unknown:
            self.after_unknown = False
            return (self.second_report(self.coid),)
        return ()

    def on_order(self, order, venue_time_ns):
        self.coid = order.client_order_id
        return (Ack(self.coid), Fill(self.coid, 100.0, order.size / 2))

    def on_cancel(self, request, venue_time_ns):
        self.after_unknown = True
        return (StateUnknown(request.client_order_id, "cancel timed out", "cancel"),)


class _PlaceThenCancel(Strategy):
    def __init__(self) -> None:
        self.n = 0
        self.coid = None

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE.value != "TRADE":
            return
        self.n += 1
        if self.n == 1:
            self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=2.0, price=100.0))
        elif self.n == 2:
            ctx.cancel_order(self.coid)


def _run(second_report):
    trades = [TradeEvent(received_time_ns=T0 + k * DAY, price=100.0, size=100.0, side="buy")
              for k in (1, 2, 3, 4)]
    return CoreEngine(_PlaceThenCancel(), trades, fill_model=_Contradicting(second_report),
                      cost_model=NullCostModel()).run()


def test_new_order_reject_after_ack_and_fill_is_refused():
    with pytest.raises(VenueProtocolError):
        _run(lambda coid: Reject(coid, "rejected as new", "new"))


def test_second_ack_after_ack_and_fill_is_refused():
    with pytest.raises(VenueProtocolError):
        _run(lambda coid: Ack(coid, "again"))


def test_canceled_after_unknown_is_still_accepted():
    # Control: resolving the ambiguous cancel with Canceled is legitimate.
    res = _run(lambda coid: Canceled(coid))
    assert list(res.venue_states.values()) == ["CANCELED"]
