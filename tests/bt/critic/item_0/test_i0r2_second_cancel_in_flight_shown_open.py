"""Critic, item 0, round 2, finding i0-r2-02.

`OrderState.PENDING_CANCEL` is "cancel sent, no answer received yet"
(api.py 116), and the view keeps it as the fact `cancel_pending` (api.py
163: "a cancel of ours was sent and has no answer yet"). That fact is ONE
bool per order, not one per cancel request: `cancel` sets it (api.py 230) and
the first answer to ANY cancel clears it (a cancel reject, api.py 280; a
cancel StateUnknown, api.py 298).

With two cancels in flight, the answer to the first one (a cancel reject)
makes the strategy see OPEN / cancel_pending=False while the second cancel
has not been answered -- and will in fact cancel the order. A strategy that
re-quotes or re-cancels on "OPEN and nothing pending" acts on a state that is
silently wrong for as long as the second answer takes.
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderRequest,
    OrderState,
    Reject,
    Strategy,
    TradeEvent,
    ZeroLatency,
)

T0 = 1_700_006_400_000_000_000
MS = 1_000_000


class _Venue:
    """Acks every order; refuses the first cancel, accepts the second."""

    def __init__(self) -> None:
        self.cancels = 0

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        self.cancels += 1
        if self.cancels == 1:
            return (Reject(request.client_order_id, "busy", "cancel"),)
        return (Canceled(request.client_order_id),)


class _Latency(ZeroLatency):
    def cancel_delay_ns(self, request, sent_time_ns):
        return 1 * MS

    def notice_delay_ns(self, report, venue_time_ns):
        return 1 * MS if isinstance(report, Reject) else 5 * MS


class _TwoCancels(Strategy):
    def __init__(self) -> None:
        self.n = 0
        self.coid = None
        self.cancels_sent = 0
        self.cancel_answers = 0
        self.wrong: list[tuple[int, str, bool]] = []

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE in (EventType.ORDER_CANCELED, EventType.ORDER_REJECT):
            self.cancel_answers += 1  # every notice here answers one of our cancels
        if self.coid is not None:
            view = ctx.order(self.coid)
            outstanding = self.cancels_sent - self.cancel_answers
            if view.state not in (OrderState.CANCELED,) and outstanding > 0 and (
                view.state is not OrderState.PENDING_CANCEL or not view.cancel_pending
            ):
                self.wrong.append((ctx.now_ns - T0, view.state.value, view.cancel_pending))
        if event.EVENT_TYPE is EventType.TRADE:
            self.n += 1
            if self.n == 1:
                self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
            elif self.n in (2, 3):
                ctx.cancel_order(self.coid)
                self.cancels_sent += 1


def test_a_second_cancel_still_in_flight_keeps_the_order_pending_cancel():
    trades = [TradeEvent(received_time_ns=T0 + k * MS // 2, price=100.0, size=1.0, side="buy") for k in range(40)]
    strat = _TwoCancels()
    res = CoreEngine(strat, trades, fill_model=_Venue(), latency_model=_Latency(),
                     cost_model=NullCostModel()).run()
    assert res.orders[strat.coid].state is OrderState.CANCELED  # the second cancel did take effect
    assert strat.wrong == [], (
        "with a cancel of ours still unanswered, the strategy was shown "
        f"(t - T0 ns, state, cancel_pending) = {strat.wrong[:3]}"
    )
