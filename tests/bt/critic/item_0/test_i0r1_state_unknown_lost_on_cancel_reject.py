"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-09.

CLAUDE.md section 1: an ambiguous answer is held as STATE_UNKNOWN until it is
resolved; events.py 355-360 and api.py 113 promise the same for the
strategy's view ("held, never resent").

The strategy's view drops STATE_UNKNOWN without any venue answer about the
order: `_OrderPort.cancel` moves STATE_UNKNOWN to PENDING_CANCEL (api.py
203-206), and a cancel Reject then moves it to OPEN if the order was ever
acked, else PENDING_NEW (api.py 250-252). Nothing the venue said resolved the
order -- the venue ledger still says STATE_UNKNOWN -- but the strategy is
told the order is OPEN (or PENDING_NEW, i.e. "an answer is still coming").
Silently wrong, on exactly the state CLAUDE.md section 1 protects.
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    CoreEngine,
    NullCostModel,
    OrderRequest,
    OrderState,
    Reject,
    StateUnknown,
    Strategy,
    TradeEvent,
)

T0 = 1_700_006_400_000_000_000
DAY = 86_400 * 1_000_000_000


class _Venue:
    def __init__(self) -> None:
        self.cancels = 0

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        self.cancels += 1
        if self.cancels == 1:  # first cancel: the answer is lost
            return (StateUnknown(request.client_order_id, "cancel timed out", "cancel"),)
        # second cancel: the venue refuses the cancel request itself
        return (Reject(request.client_order_id, "busy", "cancel"),)


class _Strat(Strategy):
    def __init__(self) -> None:
        self.n = 0
        self.coid = None

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE.value != "TRADE":
            return
        self.n += 1
        if self.n == 1:
            self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
        elif self.n in (2, 3):
            ctx.cancel_order(self.coid)


def test_state_unknown_is_not_turned_into_open_by_a_cancel_reject():
    trades = [TradeEvent(received_time_ns=T0 + k * DAY, price=100.0, size=100.0, side="buy")
              for k in (1, 2, 3, 4)]
    strat = _Strat()
    res = CoreEngine(strat, trades, fill_model=_Venue(), cost_model=NullCostModel()).run()
    assert res.venue_states[strat.coid] == "STATE_UNKNOWN"
    assert res.orders[strat.coid].state is OrderState.STATE_UNKNOWN, (
        f"the venue never resolved the order (ledger: STATE_UNKNOWN), but the strategy's view "
        f"says {res.orders[strat.coid].state}"
    )
