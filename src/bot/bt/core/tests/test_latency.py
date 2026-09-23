"""The latency socket moves when things happen; the core honours it."""
import random

import pytest

from bot.bt.core import CoreEngine, EventType, LatencyModelError, NullCostModel, OrderRequest
from bot.bt.core.testing import ImmediateFillModel

from ._util import MS, T0, Recorder, clock, trade


class _Fixed:
    def __init__(self, feed=0, order=0, cancel=0, notice=0):
        self.feed, self.order, self.cancel, self.notice = feed, order, cancel, notice

    def feed_delay_ns(self, e):
        return self.feed

    def order_delay_ns(self, o, t):
        return self.order

    def cancel_delay_ns(self, r, t):
        return self.cancel

    def notice_delay_ns(self, r, t):
        return self.notice


def test_round_trip_times_are_send_plus_order_delay_plus_notice_delay():
    fm = ImmediateFillModel()
    times = {}

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE and "sent" not in times:
            times["sent"] = int(ctx.now_ns)
            ctx.place_order(OrderRequest("buy", "market", 1.0))
        if ev.EVENT_TYPE is EventType.ORDER_ACK:
            times["ack"] = int(ctx.now_ns)
            times["ack_venue"] = int(ev.exchange_time_ns)

    events = [trade(T0, 100.0), trade(T0 + 4 * MS, 101.0), trade(T0 + 6 * MS, 102.0)]
    res = CoreEngine(Recorder(act), events, fill_model=fm, cost_model=NullCostModel(),
                     latency_model=_Fixed(order=5 * MS, notice=2 * MS)).run()
    assert times == {"sent": T0, "ack_venue": T0 + 5 * MS, "ack": T0 + 7 * MS}
    # the venue filled at arrival (T0+5ms) against the last price IT had seen
    # (101.0 at T0+4ms), not the one the strategy had seen when sending.
    assert res.fills[0].price == 101.0 and res.fills[0].venue_time_ns == T0 + 5 * MS


def test_feed_delay_postpones_delivery_but_not_the_venue():
    fm = ImmediateFillModel()
    rec = Recorder(lambda ev, ctx: rec.now.append(int(ctx.now_ns)))
    rec.now = []
    CoreEngine(rec, [trade(T0)], fill_model=fm, cost_model=NullCostModel(),
               latency_model=_Fixed(feed=3 * MS)).run()
    assert rec.now == [T0 + 3 * MS]
    assert fm.market_events_seen[0][0] == T0
    assert rec.seen[0].exchange_time_ns == T0 and rec.seen[0].received_time_ns == T0 + 3 * MS


class _Random(_Fixed):
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def order_delay_ns(self, o, t):
        return self.rng.randrange(0, 20 * MS)

    def cancel_delay_ns(self, r, t):
        return self.rng.randrange(0, 20 * MS)

    def notice_delay_ns(self, r, t):
        return self.rng.randrange(0, 20 * MS)


@pytest.mark.parametrize("seed", range(5))
def test_channels_are_fifo_under_random_delays(seed):
    arrivals = []
    notices = []

    class _Watch(ImmediateFillModel):
        def on_order(self, o, t):
            arrivals.append((t, o.client_order_id))
            return super().on_order(o, t)

        def on_cancel(self, r, t):
            arrivals.append((t, "cancel:" + r.client_order_id))
            return super().on_cancel(r, t)

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK:
            a = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))
            ctx.cancel_order(a)
            ctx.place_order(OrderRequest("sell", "limit", 1.0, price=2.0))
        elif ev.EVENT_TYPE.value.startswith("ORDER_"):
            notices.append((int(ctx.now_ns), ev.EVENT_TYPE, ev.client_order_id))

    CoreEngine(Recorder(act), [clock(T0 + i * MS) for i in range(10)], fill_model=_Watch(),
               cost_model=NullCostModel(), latency_model=_Random(seed)).run()
    sent_order = [x for _, x in arrivals]
    # every cancel arrives after its own order; arrival times never decrease
    assert [t for t, _ in arrivals] == sorted(t for t, _ in arrivals)
    for i, name in enumerate(sent_order):
        if name.startswith("cancel:"):
            assert sent_order.index(name[len("cancel:"):]) < i
    assert [t for t, _, _ in notices] == sorted(t for t, _, _ in notices)
    for coid in {c for _, _, c in notices}:
        kinds = [k for _, k, c in notices if c == coid]
        assert kinds[0] is EventType.ORDER_ACK


@pytest.mark.parametrize("bad", [-1, 1.5, True, None])
def test_bad_delay_values_are_refused(bad):
    with pytest.raises(LatencyModelError):
        CoreEngine(Recorder(), [trade(T0)], latency_model=_Fixed(feed=bad)).run()
