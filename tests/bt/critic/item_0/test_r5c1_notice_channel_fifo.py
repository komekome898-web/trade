"""Critic, item 0, round 1 of run 5 (i0-r1-06).

The venue -> strategy notice channel is promised FIFO ("a later notice never
overtakes an earlier one", engine.py 14-19; ORDERING_RULE["channels_fifo"]).
`_handle_reports` (engine.py 676-680) clamps delivery TIMES with
`max(venue_time + delay, self._last_notice)`, which makes notices with a
shorter delay land on the SAME delivery time as an earlier, slower one.
The queue then orders them by type priority (ORDER_ACK 26 < ORDER_FILL 28 <
ORDER_STATE_UNKNOWN 30, ordering.py 82-95), not by the order the venue sent
them.

Scenario (a latency model whose notice delay depends on the report, the
normal case for item 4): the venue answers the order ambiguously at t
(StateUnknown, 10 ms to reach us), then resolves it 1 ms later with Ack +
Fill (0 ms). All three are clamped to t + 10 ms and delivered as
ACK, FILL, STATE_UNKNOWN. The strategy's final view of a FILLED order is
STATE_UNKNOWN -- silently wrong, and it is exactly the state CLAUDE.md
section 1 says must block any further action on the order.
"""
from __future__ import annotations

from bot.bt.core import (
    Ack,
    CoreEngine,
    Fill,
    NullCostModel,
    OrderRequest,
    OrderState,
    StateUnknown,
    Strategy,
    TradeEvent,
    ZeroLatency,
)

T0 = 1_700_006_400_000_000_000
MS = 1_000_000


class _AmbiguousThenResolved:
    def __init__(self) -> None:
        self.pending = None

    def on_market_event(self, event, venue_time_ns):
        if self.pending is not None:
            coid, size = self.pending
            self.pending = None
            return (Ack(coid), Fill(coid, 100.0, size))
        return ()

    def on_order(self, order, venue_time_ns):
        self.pending = (order.client_order_id, order.size)
        return (StateUnknown(order.client_order_id, "timeout"),)

    def on_cancel(self, request, venue_time_ns):  # pragma: no cover - not used
        return ()


class _SlowUnknownNotice(ZeroLatency):
    def notice_delay_ns(self, report, venue_time_ns):
        return 10 * MS if isinstance(report, StateUnknown) else 0


class _Buyer(Strategy):
    def __init__(self) -> None:
        self.coid = None
        self.notices: list[str] = []

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE.value.startswith("ORDER_"):
            self.notices.append(event.EVENT_TYPE.value)
        if self.coid is None and event.EVENT_TYPE.value == "TRADE":
            self.coid = ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0))


def test_notices_reach_the_strategy_in_the_order_the_venue_sent_them():
    trades = [TradeEvent(received_time_ns=T0 + k * MS, price=100.0, size=100.0, side="buy")
              for k in range(0, 30)]
    strat = _Buyer()
    res = CoreEngine(strat, trades, fill_model=_AmbiguousThenResolved(),
                     latency_model=_SlowUnknownNotice(), cost_model=NullCostModel()).run()
    assert res.venue_states[strat.coid] == "FILLED"
    assert strat.notices == ["ORDER_STATE_UNKNOWN", "ORDER_ACK", "ORDER_FILL"], strat.notices
    assert res.orders[strat.coid].state is OrderState.FILLED, (
        f"venue says FILLED, the strategy's view says {res.orders[strat.coid].state}"
    )
