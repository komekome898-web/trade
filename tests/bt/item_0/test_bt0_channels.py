"""Every path is a FIFO channel (ordering.py; i0-r1-05, 06, 10, 12).

The expected sequences are the send / emit / reception orders themselves,
written out by hand."""
import random

from bot.bt.core import (
    Ack,
    BookDeltaEvent,
    Canceled,
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

from bt0_util import MS, T0, Recorder, trade


class _LogVenue:
    def __init__(self):
        self.log = []

    def on_market_event(self, e, t):
        self.log.append(("market", e.EVENT_TYPE.value, t))
        return ()

    def on_order(self, o, t):
        self.log.append(("new", o.client_order_id, t))
        return (Ack(o.client_order_id),)

    def on_cancel(self, c, t):
        self.log.append(("cancel", c.client_order_id, t))
        return (Canceled(c.client_order_id),)


class _Delays(ZeroLatency):
    def __init__(self, order=0, cancel=0):
        self.o, self.c = order, cancel

    def order_delay_ns(self, o, t):
        return self.o

    def cancel_delay_ns(self, c, t):
        return self.c


class _Sender(Strategy):
    """First call: place X. Second call: send the scripted requests."""

    def __init__(self, script):
        self.script = script
        self.n = 0

    def on_event(self, e, ctx):
        if e.EVENT_TYPE.value != "TRADE":
            return
        self.n += 1
        if self.n == 1:
            ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id="X"))
        elif self.n == 2:
            for kind, coid in self.script:
                if kind == "cancel":
                    ctx.cancel_order(coid)
                else:
                    ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=91.0,
                                                 client_order_id=coid))


def _requests(script, latency):
    venue = _LogVenue()
    trades = [trade(T0 + k * MS, 100.0) for k in range(1, 20)]
    CoreEngine(_Sender(script), trades, fill_model=venue, latency_model=latency,
               cost_model=NullCostModel()).run()
    return [(k, c) for k, c, _ in venue.log if k != "market"], [t for k, _, t in venue.log if k != "market"]


def test_requests_reach_the_venue_in_send_order_with_equal_delays():
    got, _ = _requests([("cancel", "X"), ("new", "Y"), ("new", "Z")], ZeroLatency())
    assert got == [("new", "X"), ("cancel", "X"), ("new", "Y"), ("new", "Z")]


def test_a_slower_cancel_is_not_overtaken_by_a_faster_new_order():
    # cancel delay 5 ms, order delay 0: the new order Y is sent after the
    # cancel, so it arrives no earlier and after it (one connection)
    got, times = _requests([("cancel", "X"), ("new", "Y")], _Delays(order=0, cancel=5 * MS))
    assert got == [("new", "X"), ("cancel", "X"), ("new", "Y")]
    assert times[1] == times[2] == T0 + 2 * MS + 5 * MS


class _ScriptedVenue:
    """Answers each order with a scripted list of reports; records what it
    emitted, in order."""

    def __init__(self, reports_for):
        self.reports_for = reports_for
        self.emitted = []
        self.later = []

    def on_market_event(self, e, t):
        out, self.later = self.later, []
        self.emitted.extend(out)
        return tuple(out)

    def on_order(self, o, t):
        now, later = self.reports_for(o)
        self.later = later
        self.emitted.extend(now)
        return tuple(now)

    def on_cancel(self, c, t):  # pragma: no cover - not used
        return ()


class _RandomNoticeDelay(ZeroLatency):
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def notice_delay_ns(self, r, t):
        return self.rng.choice([0, 1, 3 * MS, 10 * MS])


def test_notices_reach_the_strategy_in_emit_order_under_random_notice_delays():
    for seed in range(50):
        def reports_for(o):
            c = o.client_order_id
            return [StateUnknown(c, "timeout")], [Ack(c), Fill(c, 100.0, 0.25), Fill(c, 100.0, 0.75)]

        venue = _ScriptedVenue(reports_for)
        strat = Recorder(lambda e, ctx: (
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0))
            if e.EVENT_TYPE.value == "TRADE" and not ctx.open_orders() and ctx.order("core-1") is None else None))
        res = CoreEngine(strat, [trade(T0 + k * MS) for k in range(30)], fill_model=venue,
                         latency_model=_RandomNoticeDelay(seed), cost_model=NullCostModel()).run()
        got = [e.EVENT_TYPE.value for e in strat.seen if e.EVENT_TYPE.value.startswith("ORDER_")]
        assert got == ["ORDER_STATE_UNKNOWN", "ORDER_ACK", "ORDER_FILL", "ORDER_FILL"], seed
        assert res.venue_states["core-1"] == "FILLED"
        assert res.orders["core-1"].state is OrderState.FILLED, seed


def test_one_stream_same_instant_trade_then_delta_reaches_venue_and_strategy_in_that_order():
    stream = [TradeEvent(received_time_ns=T0, price=100.0, size=1.0, side="sell"),
              BookDeltaEvent(received_time_ns=T0, side="bid", price=100.0, size=0.0),
              TradeEvent(received_time_ns=T0, price=100.0, size=1.0, side="sell")]
    venue, rec = _LogVenue(), Recorder()
    CoreEngine(rec, stream, fill_model=venue, cost_model=NullCostModel()).run()
    assert [x[1] for x in venue.log] == ["TRADE", "BOOK_DELTA", "TRADE"]
    assert [e.EVENT_TYPE.value for e in rec.seen] == ["TRADE", "BOOK_DELTA", "TRADE"]


class _FeedDelay(ZeroLatency):
    def __init__(self, by_price):
        self.by_price = by_price

    def feed_delay_ns(self, e):
        return self.by_price.get(getattr(e, "price", None), 0)


def test_feed_jitter_postpones_a_later_event_behind_an_earlier_one_of_its_stream():
    # 100 received at T0 with 5 ms delay; 101 received at T0+1ms with 0 delay.
    # Reception order 100, 101 is kept: 101 waits until 100 is delivered.
    stream = [trade(T0, 100.0), trade(T0 + MS, 101.0)]
    rec = Recorder()
    CoreEngine(rec, stream, latency_model=_FeedDelay({100.0: 5 * MS})).run()
    assert [(e.price, e.received_time_ns) for e in rec.seen] == [(100.0, T0 + 5 * MS), (101.0, T0 + 5 * MS)]


def test_feed_jitter_does_not_hold_back_other_streams():
    streams = {"a": [trade(T0, 100.0), trade(T0 + MS, 101.0)], "b": [trade(T0 + MS, 200.0)]}
    rec = Recorder()
    CoreEngine(rec, streams, latency_model=_FeedDelay({100.0: 5 * MS})).run()
    assert [(e.price, e.received_time_ns) for e in rec.seen] == [
        (200.0, T0 + MS), (100.0, T0 + 5 * MS), (101.0, T0 + 5 * MS)]


def test_a_recorded_late_reception_is_delivered_in_recorded_reception_order():
    """The recorded received_time_ns is data: an event of a stream recorded as
    received after the next one (a late print) is delivered after it."""
    late = TradeEvent(exchange_time_ns=T0, received_time_ns=T0 + 3 * MS, price=101.0, size=1.0, side="buy")
    stream = [late, trade(T0 + MS, 100.0), trade(T0 + 4 * MS, 102.0)]
    rec = Recorder()
    CoreEngine(rec, stream).run()
    assert [(e.price, e.received_time_ns) for e in rec.seen] == [
        (100.0, T0 + MS), (101.0, T0 + 3 * MS), (102.0, T0 + 4 * MS)]
