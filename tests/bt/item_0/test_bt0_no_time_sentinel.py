"""Every int64 is a valid time, 0 and times before 1970 included; "nothing
yet" is never written as a time (i0-r2-01). The FIFO channels start empty,
not at time 0; a FillNotice has no default time; the order port has no
time before its first callback."""
import dataclasses

import pytest

from bot.bt.core import (
    Ack,
    CoreEngine,
    EventType,
    FillNotice,
    NullCostModel,
    OrderApiError,
    OrderRequest,
    TimestampUnitError,
    TradeEvent,
    ZeroLatency,
)
from bot.bt.core.api import _OrderPort
from bot.bt.core.testing import ImmediateFillModel

from bt0_util import MS, SEC, Recorder

INT64_MIN = -(2**63)


class _Log(ZeroLatency):
    def __init__(self, order_ms=0, notice_ms=0):
        self.order_ms, self.notice_ms = order_ms, notice_ms

    def order_delay_ns(self, order, sent):
        return self.order_ms * MS

    def cancel_delay_ns(self, request, sent):
        return self.order_ms * MS

    def notice_delay_ns(self, report, venue_time):
        return self.notice_ms * MS


class _Venue:
    def __init__(self):
        self.arrivals = []

    def on_market_event(self, e, t):
        return ()

    def on_order(self, o, t):
        self.arrivals.append(t)
        return (Ack(o.client_order_id),)

    def on_cancel(self, c, t):  # pragma: no cover
        return ()


def _trades(start, n=3, step=MS):
    return [TradeEvent(received_time_ns=start + k * step, price=100.0, size=1.0, side="buy") for k in range(n)]


def _buy_each_trade(ev, ctx):
    if ev.EVENT_TYPE is EventType.TRADE:
        ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))


@pytest.mark.parametrize("start", [-10 * SEC, -1, 0, INT64_MIN + 10 * MS])
@pytest.mark.parametrize("order_ms,notice_ms", [(0, 0), (2, 3)])
def test_orders_and_notices_keep_their_times_at_and_before_the_epoch(start, order_ms, notice_ms):
    venue, rec = _Venue(), Recorder(_buy_each_trade)
    CoreEngine(rec, _trades(start), fill_model=venue, latency_model=_Log(order_ms, notice_ms),
               cost_model=NullCostModel()).run()
    sent = [start + k * MS for k in range(3)]
    assert venue.arrivals == [t + order_ms * MS for t in sent]
    acks = [int(e.received_time_ns) for e in rec.seen if e.EVENT_TYPE is EventType.ORDER_ACK]
    assert acks == [t + (order_ms + notice_ms) * MS for t in sent]


def test_fifo_still_holds_for_negative_times():
    """A later request with a shorter delay still waits for the earlier one."""

    class _Shrinking(_Log):
        def __init__(self):
            super().__init__()
            self.delays = iter([5, 1])

        def order_delay_ns(self, order, sent):
            return next(self.delays) * MS

    venue = _Venue()
    CoreEngine(Recorder(_buy_each_trade), _trades(-SEC, n=2), fill_model=venue,
               latency_model=_Shrinking(), cost_model=NullCostModel()).run()
    assert venue.arrivals == [-SEC + 5 * MS, -SEC + 5 * MS]


def test_fill_notice_has_no_default_time_and_checks_it():
    with pytest.raises(TypeError):
        FillNotice("o", 1.0, 1.0)  # venue_time_ns is required
    with pytest.raises(TimestampUnitError):
        FillNotice("o", 1.0, 1.0, venue_time_ns=1.5)
    n = FillNotice("o", 1.0, 1.0, venue_time_ns=-5)
    assert n.venue_time_ns == -5 and dataclasses.replace(n, fee=1.0).venue_time_ns == -5


def test_fills_before_1970_are_booked_at_their_time():
    rec = Recorder(lambda ev, ctx: ev.seq == 1 and ctx.place_order(
        OrderRequest(side="buy", order_type="market", size=1.0)))
    res = CoreEngine(rec, _trades(-SEC), fill_model=ImmediateFillModel(), cost_model=NullCostModel()).run()
    assert [f.venue_time_ns for f in res.fills] == [-SEC]


def test_order_port_has_no_time_before_the_first_callback():
    port = _OrderPort()
    with pytest.raises(OrderApiError):
        port.place(OrderRequest(side="buy", order_type="market", size=1.0))
    with pytest.raises(OrderApiError):
        port.set_timer(0, "t")
