"""P0-2: every time the queue holds is an int64 of ns -- including times a
latency model or a timer computes. An out-of-range time fails loudly on
every channel."""
import pytest

from bot.bt.core import (
    ClockEvent,
    CoreEngine,
    NullCostModel,
    OrderRequest,
    TimestampUnitError,
)
from bot.bt.core.testing import ImmediateFillModel
from bot.bt.core.time import INT64_MAX

from bt0_util import T0, Recorder, trade

HUGE = 10**30


class _Lat:
    def __init__(self, which):
        self.which = which

    def feed_delay_ns(self, e):
        return HUGE if self.which == "feed" else 0

    def order_delay_ns(self, o, t):
        return HUGE if self.which == "order" else 0

    def cancel_delay_ns(self, r, t):
        return HUGE if self.which == "cancel" else 0

    def notice_delay_ns(self, r, t):
        return HUGE if self.which == "notice" else 0


def _act(ev, ctx):
    if ev.EVENT_TYPE.value == "TRADE":
        oid = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))
        ctx.cancel_order(oid)


@pytest.mark.parametrize("which", ["feed", "order", "cancel", "notice"])
def test_every_channel_refuses_a_time_past_int64(which):
    with pytest.raises(TimestampUnitError, match="int64"):
        CoreEngine(Recorder(_act), [trade(T0)], fill_model=ImmediateFillModel(fixed_price=1.0),
                   cost_model=NullCostModel(), latency_model=_Lat(which)).run()


def test_timer_past_int64_is_refused():
    def act(ev, ctx):
        ctx.set_timer(INT64_MAX + 1)

    with pytest.raises(TimestampUnitError):
        CoreEngine(Recorder(act), [ClockEvent(received_time_ns=T0)]).run()


def test_all_delivered_times_are_python_ints():
    rec = Recorder()
    CoreEngine(rec, [trade(T0), trade(T0 + 1)]).run()
    assert all(type(e.received_time_ns) is int and type(e.exchange_time_ns) is int for e in rec.seen)
