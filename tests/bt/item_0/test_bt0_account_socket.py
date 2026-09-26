"""P0-7, account socket: an account written outside the core can reject an
order at the venue (pre-trade check), mark positions on every market event,
and force orders (a close-out) -- without editing the core."""
import pytest

from bot.bt.core import (
    AccountSocketError,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderApiError,
    OrderRequest,
    OrderState,
)
from bot.bt.core.testing import FixedRateCost

from bt0_util import MS, T0, Recorder, clock, trade


class _Account:
    """Written here, not in the core: long-only book with a margin limit."""

    def __init__(self, max_size=1.0, close_below=None):
        self.position = 0.0
        self.max_size = max_size
        self.close_below = close_below
        self.marks = []
        self.fills = []
        self.checked = []
        self.closed = False

    def apply_fill(self, f):
        self.fills.append(f)
        self.position += f.size if f.side == "buy" else -f.size

    def apply_funding(self, e):
        pass

    def apply_liquidation(self, e):
        pass

    def check_order(self, order, t):
        self.checked.append((order.client_order_id, t))
        if order.side == "buy" and self.position + order.size > self.max_size:
            return "insufficient_margin"
        return None

    def on_market_event(self, e, t):
        if e.EVENT_TYPE is EventType.TRADE:
            self.marks.append((t, e.price))
            if self.close_below is not None and e.price < self.close_below and self.position > 0 and not self.closed:
                self.closed = True
                return (OrderRequest("sell", "market", self.position),)
        return ()


class _Venue:
    def __init__(self):
        self.orders = []
        self.last = None

    def on_market_event(self, e, t):
        if e.EVENT_TYPE is EventType.TRADE:
            self.last = e.price
        return ()

    def on_order(self, o, t):
        from bot.bt.core import Ack, Fill

        self.orders.append((o.client_order_id, t))
        return (Ack(o.client_order_id), Fill(o.client_order_id, self.last, o.size))

    def on_cancel(self, r, t):  # pragma: no cover
        from bot.bt.core import Canceled

        return (Canceled(r.client_order_id),)


class _Lat:
    def feed_delay_ns(self, e):
        return 0

    def order_delay_ns(self, o, t):
        return 2 * MS

    def cancel_delay_ns(self, r, t):
        return 2 * MS

    def notice_delay_ns(self, r, t):
        return 3 * MS


def test_pre_trade_reject_reaches_the_strategy_and_the_venue_never_sees_the_order():
    acct, venue = _Account(max_size=1.0), _Venue()
    seen = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE and ctx.order("big") is None:
            ctx.place_order(OrderRequest("buy", "market", 2.0, client_order_id="big"))
        seen.append((ev.EVENT_TYPE, getattr(ev, "reason", None)))

    res = CoreEngine(Recorder(act), [trade(T0, 100.0)], fill_model=venue, account=acct,
                     cost_model=NullCostModel(), latency_model=_Lat()).run()
    assert venue.orders == []
    assert acct.checked == [("big", T0 + 2 * MS)]  # at venue arrival, not at send time
    assert seen == [(EventType.TRADE, None), (EventType.ORDER_REJECT, "insufficient_margin")]
    assert res.orders["big"].state is OrderState.REJECTED
    assert res.venue_states["big"] == "REJECTED"


@pytest.mark.parametrize("bad", [False, "", 0, ["no"]])
def test_check_order_answer_must_be_none_or_a_reason(bad):
    class _Bad(_Account):
        def check_order(self, order, t):
            return bad

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE:
            ctx.place_order(OrderRequest("buy", "market", 0.5))

    with pytest.raises(AccountSocketError):
        CoreEngine(Recorder(act), [trade(T0, 100.0)], fill_model=_Venue(), account=_Bad(),
                   cost_model=NullCostModel()).run()


def test_mark_hook_sees_every_trade_at_venue_time_after_the_fill_model():
    acct = _Account()
    CoreEngine(Recorder(), [trade(T0, 100.0, exch=T0 - 5), trade(T0 + 10, 99.0)], account=acct).run()
    assert acct.marks == [(T0 - 5, 100.0), (T0 + 10, 99.0)]


def test_forced_close_goes_to_the_venue_now_and_the_strategy_learns_by_notice():
    acct, venue = _Account(max_size=1.0, close_below=95.0), _Venue()
    log = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE and ev.price == 100.0:
            ctx.place_order(OrderRequest("buy", "market", 1.0, client_order_id="entry"))
        log.append((int(ev.received_time_ns) - T0, ev.EVENT_TYPE, getattr(ev, "client_order_id", ""),
                    ctx.order("forced-1") is not None))

    events = [trade(T0, 100.0), trade(T0 + 10 * MS, 94.0), clock(T0 + 11 * MS), clock(T0 + 20 * MS)]
    res = CoreEngine(Recorder(act), events, fill_model=venue, account=acct,
                     cost_model=FixedRateCost(0.0), latency_model=_Lat()).run()
    # entry: sent at 0, at venue 2ms, notices at 5ms. Close-out: forced at the
    # 94.0 trade's venue time 10ms (no order latency), notices at 13ms.
    assert venue.orders == [("entry", T0 + 2 * MS), ("forced-1", T0 + 10 * MS)]
    assert [(t // MS, et, c, known) for t, et, c, known in log] == [
        (0, EventType.TRADE, "", False),
        (5, EventType.ORDER_ACK, "entry", False),
        (5, EventType.ORDER_FILL, "entry", False),
        (10, EventType.TRADE, "", False),
        (11, EventType.CLOCK, "", False),  # the venue has closed, the notice is not here yet
        (13, EventType.ORDER_ACK, "forced-1", True),
        (13, EventType.ORDER_FILL, "forced-1", True),
        (20, EventType.CLOCK, "", True),
    ]
    view = res.orders["forced-1"]
    assert view.origin == "forced" and view.state is OrderState.FILLED and view.avg_fill_price == 94.0
    assert res.orders["entry"].origin == "strategy"
    assert [o.client_order_id for o in res.forced_orders] == ["forced-1"]
    assert acct.position == 0.0


def test_strategy_cannot_use_the_forced_prefix():
    def act(ev, ctx):
        with pytest.raises(OrderApiError, match="reserved"):
            ctx.place_order(OrderRequest("buy", "market", 1.0, client_order_id="forced-1"))

    CoreEngine(Recorder(act), [trade(T0)]).run()


@pytest.mark.parametrize("forced", [
    ("not an order",),
    (OrderRequest("sell", "market", 1.0, client_order_id="mine"),),
    (OrderRequest("sell", "market", 1.0, client_order_id="forced-x"),
     OrderRequest("sell", "market", 1.0, client_order_id="forced-x")),
])
def test_bad_forced_orders_are_refused(forced):
    class _Forcer(_Account):
        def on_market_event(self, e, t):
            return forced

    with pytest.raises(AccountSocketError):
        CoreEngine(Recorder(), [trade(T0, 100.0)], fill_model=_Venue(), account=_Forcer(),
                   cost_model=NullCostModel()).run()
