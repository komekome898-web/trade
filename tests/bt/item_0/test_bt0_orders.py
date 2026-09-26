"""Order lifecycle through the API, the venue socket and the notices."""
import pytest

from bot.bt.core import (
    Ack,
    CancelRequest,
    Canceled,
    CoreEngine,
    EventType,
    Fill,
    MissingCostModelError,
    NullCostModel,
    OrderApiError,
    OrderRequest,
    OrderState,
    Reject,
    StateUnknown,
    VenueProtocolError,
)
from bot.bt.core.testing import FixedRateCost, ImmediateFillModel, RecordingAccount

from bt0_util import MS, T0, Recorder, clock, trade


def test_place_then_cancel_returns_open_orders_to_zero():
    log = {}

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK and "id" not in log:
            log["id"] = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=99.0))
            log["after_place"] = len(ctx.open_orders())
            ctx.cancel_order(CancelRequest(log["id"]))
        if ev.EVENT_TYPE is EventType.ORDER_CANCELED:
            log["after_cancel"] = len(ctx.open_orders())

    res = CoreEngine(Recorder(act), [clock(T0)]).run()
    assert log["after_place"] == 1
    assert log["after_cancel"] == 0
    assert res.open_orders == []
    assert res.orders[log["id"]].state is OrderState.CANCELED
    assert res.venue_states[log["id"]] == "CANCELED"


def test_ack_then_fill_updates_the_strategy_view_and_account():
    acct = RecordingAccount()
    seen = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE and not seen:
            oid = ctx.place_order(OrderRequest("sell", "market", 2.0, client_order_id="mine"))
            assert oid == "mine"
            assert ctx.order("mine").state is OrderState.PENDING_NEW
        seen.append(ev.EVENT_TYPE)

    res = CoreEngine(Recorder(act), [trade(T0, 100.0)], fill_model=ImmediateFillModel(),
                     cost_model=FixedRateCost(0.001), account=acct).run()
    assert seen == [EventType.TRADE, EventType.ORDER_ACK, EventType.ORDER_FILL]
    view = res.orders["mine"]
    assert view.state is OrderState.FILLED and view.filled_size == 2.0 and view.avg_fill_price == 100.0
    assert view.fees == pytest.approx(0.2)  # 100 * 2 * 0.001, closed form
    booked = [c for k, c in acct.calls if k == "fill"]
    assert len(booked) == 1
    assert booked[0].fee == pytest.approx(0.2) and booked[0].side == "sell"


def test_fill_without_cost_model_is_refused():
    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE:
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    with pytest.raises(MissingCostModelError):
        CoreEngine(Recorder(act), [trade(T0)], fill_model=ImmediateFillModel()).run()


def test_reject_is_delivered_and_closes_the_order():
    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK:
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    rec = Recorder(act)
    res = CoreEngine(rec, [clock(T0)], fill_model=ImmediateFillModel(), cost_model=NullCostModel()).run()
    assert rec.seen[-1].EVENT_TYPE is EventType.ORDER_REJECT and rec.seen[-1].reason == "no_price"
    assert res.orders["core-1"].state is OrderState.REJECTED and res.open_orders == []


class _Unknown:
    def on_market_event(self, e, t):
        return ()

    def on_order(self, o, t):
        return (StateUnknown(o.client_order_id, "timeout"),)

    def on_cancel(self, r, t):
        return (StateUnknown(r.client_order_id, "timeout", "cancel"),)


def test_state_unknown_is_held_open_and_never_resent():
    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK:
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    rec = Recorder(act)
    res = CoreEngine(rec, [clock(T0), clock(T0 + 1)], fill_model=_Unknown(), cost_model=NullCostModel()).run()
    # the strategy placed twice (one per clock); each went out exactly once
    assert len(res.order_requests) == 2
    assert [v.state for v in res.orders.values()] == [OrderState.STATE_UNKNOWN] * 2
    assert len(res.open_orders) == 2
    assert sum(1 for e in rec.seen if e.EVENT_TYPE is EventType.ORDER_STATE_UNKNOWN) == 2


def test_cancel_of_closed_order_is_rejected_by_the_engine_not_the_model():
    calls = []

    class _Imm(ImmediateFillModel):
        def on_cancel(self, r, t):
            calls.append(r)
            return super().on_cancel(r, t)

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE:
            ctx.place_order(OrderRequest("buy", "market", 1.0, client_order_id="a"))
        if ev.EVENT_TYPE is EventType.ORDER_FILL:
            ctx.cancel_order("a")

    rec = Recorder(act)
    CoreEngine(rec, [trade(T0)], fill_model=_Imm(), cost_model=NullCostModel()).run()
    last = rec.seen[-1]
    assert last.EVENT_TYPE is EventType.ORDER_REJECT and last.request_kind == "cancel"
    assert last.reason.startswith("order_not_open")
    assert calls == []


@pytest.mark.parametrize(
    "bad_order_reports,bad_cancel_reports,match",
    [
        (lambda o: (Fill(o.client_order_id, 1.0, 1.0),), None, "before its Ack"),
        (lambda o: (Ack(o.client_order_id), Fill(o.client_order_id, 1.0, 2.0)), None, "overfill"),
        (lambda o: (Ack(o.client_order_id), Ack(o.client_order_id)), None, "second Ack"),
        (lambda o: (), None, "no Ack/Reject"),
        (lambda o: (Ack("ghost"),), None, "has not reached the venue"),
        (lambda o: (Ack(o.client_order_id), Fill(o.client_order_id, float("nan"), 1.0)), None, "finite"),
        (lambda o: (Ack(o.client_order_id),), lambda r: (), "gave 0 answers"),
        # one cancel, one answer (i0-r2-02): two answers to one cancel are refused
        (lambda o: (Ack(o.client_order_id),),
         lambda r: (Reject(r.client_order_id, "busy", "cancel"), Canceled(r.client_order_id)), "gave 2 answers"),
        (lambda o: (Ack(o.client_order_id),),
         lambda r: (Reject(r.client_order_id, "a", "cancel"), Reject(r.client_order_id, "b", "cancel")),
         "gave 2 answers"),
        (lambda o: (Ack(o.client_order_id), Canceled(o.client_order_id), Fill(o.client_order_id, 1.0, 1.0)), None, "terminal"),
        (lambda o: (Ack(o.client_order_id), Reject(o.client_order_id, "x", "cancel")), None, "outside its cancel"),
    ],
)
def test_impossible_venue_reports_raise(bad_order_reports, bad_cancel_reports, match):
    class _Bad:
        def on_market_event(self, e, t):
            return ()

        def on_order(self, o, t):
            return bad_order_reports(o)

        def on_cancel(self, r, t):
            return bad_cancel_reports(r) if bad_cancel_reports else (Canceled(r.client_order_id),)

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK:
            oid = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))
            ctx.cancel_order(oid)

    with pytest.raises(VenueProtocolError, match=match):
        CoreEngine(Recorder(act), [clock(T0)], fill_model=_Bad(), cost_model=NullCostModel()).run()


def test_fill_model_cannot_fill_an_order_before_it_arrives():
    class _Eager:
        def on_market_event(self, e, t):
            return (Fill("core-1", 1.0, 1.0),)  # the order is still in flight

        def on_order(self, o, t):
            return (Ack(o.client_order_id),)

        def on_cancel(self, r, t):
            return (Canceled(r.client_order_id),)

    class _Lat:
        def feed_delay_ns(self, e):
            return 0

        def order_delay_ns(self, o, t):
            return 10 * MS

        def cancel_delay_ns(self, r, t):
            return 0

        def notice_delay_ns(self, r, t):
            return 0

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK:
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    with pytest.raises(VenueProtocolError, match="has not reached the venue"):
        CoreEngine(Recorder(act), [clock(T0), trade(T0 + 1 * MS)], fill_model=_Eager(),
                   latency_model=_Lat(), cost_model=NullCostModel()).run()


def test_order_api_misuse_raises():
    errors = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is not EventType.CLOCK:
            return
        for call in (
            lambda: ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="x")),
            lambda: ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="x")),
            lambda: ctx.cancel_order("never-placed"),
            lambda: ctx.set_timer(int(ctx.now_ns) - 1),
            lambda: ctx.place_order("buy 1"),
        ):
            try:
                call()
                errors.append(None)
            except OrderApiError as exc:
                errors.append(type(exc).__name__)

    CoreEngine(Recorder(act), [clock(T0)]).run()
    assert errors == [None, "OrderApiError", "OrderApiError", "OrderApiError", "OrderApiError"]
    for bad in (
        lambda: OrderRequest("hold", "market", 1.0),
        lambda: OrderRequest("buy", "market", 0.0),
        lambda: OrderRequest("buy", "limit", 1.0, price=float("inf")),
        lambda: OrderRequest("buy", "", 1.0),
    ):
        with pytest.raises(OrderApiError):
            bad()


def test_engine_assigned_ids_are_what_is_recorded_and_skip_taken_ids():
    ids = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is not EventType.CLOCK:
            return
        ids.append(ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="core-1")))
        ids.append(ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0)))

    res = CoreEngine(Recorder(act), [clock(T0)]).run()
    assert ids == ["core-1", "core-2"]
    assert [r.client_order_id for r in res.order_requests] == ids


def test_timer_delivers_a_tagged_clock_event_at_the_requested_time():
    got = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE:
            ctx.set_timer(int(ctx.now_ns) + 300 * 10**9, "exit")
        if ev.EVENT_TYPE is EventType.CLOCK:
            got.append((int(ctx.now_ns), ev.tag))

    CoreEngine(Recorder(act), [trade(T0)]).run()
    assert got == [(T0 + 300 * 10**9, "exit")]


def test_funding_and_liquidation_reach_the_account_at_venue_time():
    from bot.bt.core import FundingEvent, LiquidationEvent

    acct = RecordingAccount()
    ev = [
        FundingEvent(received_time_ns=T0 + 5, exchange_time_ns=T0, rate=0.0001),
        LiquidationEvent(received_time_ns=T0 + 9, exchange_time_ns=T0 + 1, price=1.0, size=1.0, side="sell"),
    ]
    CoreEngine(Recorder(), ev, account=acct).run()
    assert [(k, int(e.exchange_time_ns)) for k, e in acct.calls if k != "market"] == [
        ("funding", T0), ("liquidation", T0 + 1),
    ]
    # the mark hook sees both, each after its settlement hook
    assert [k for k, _ in acct.calls] == ["funding", "market", "liquidation", "market"]
