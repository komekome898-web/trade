"""What each sender hands to a path reaches the other side as a value made
at send time (i0-r5-01): run through the engine, from each of the four
senders -- the strategy, the account socket (forced orders), the fill
model (reports) and the event source -- plus the strategy's timers.

Each case sends once and then changes only the sender's own state (or its
own object, even bypassing `frozen` with `object.__setattr__`); the other
side must see what was sent, and an object of the sender's own class
(a subclass of a carrier, or something that only answers `==`) is refused
when it is handed over. The round-6 probe (scratchpad
`bt/item0_r6_worker_probe_same_root.py`) found each of these open before
the change.
"""
from __future__ import annotations

import pytest

from bot.bt.core import (
    AccountSocketError,
    Ack,
    CoreEngine,
    CoreError,
    EventType,
    Fill,
    NullAccount,
    NullCostModel,
    OrderApiError,
    OrderRequest,
    Reject,
    SourceEventTypeError,
    Strategy,
    TradeEvent,
    VenueProtocolError,
)

from bt0_util import SEC, T0

STATE = {"v": "sent"}


class _AnyEq:
    def __eq__(self, other):
        return True

    __hash__ = object.__hash__

    def __repr__(self):
        return f"AnyEq({STATE['v']})"


class _LiveText(str):
    def __str__(self):
        return STATE["v"]

    def __eq__(self, other):
        return STATE["v"] == other

    __hash__ = str.__hash__


class _Slow:
    """Orders reach the venue 10 s after they are sent."""

    def feed_delay_ns(self, e):
        return 0

    def order_delay_ns(self, o, t):
        return 10 * SEC

    def cancel_delay_ns(self, r, t):
        return 0

    def notice_delay_ns(self, r, t):
        return 0


class _Venue:
    def __init__(self, answer=None):
        self.seen: list = []
        self.answer = answer

    def on_market_event(self, e, t):
        return ()

    def on_order(self, o, t):
        self.seen.append({"type": type(o), "side": o.side, "size": o.size, "post_only": o.post_only,
                          "order_type": o.order_type})
        return self.answer(o) if self.answer else (Ack(o.client_order_id),)

    def on_cancel(self, r, t):
        return ()


def _trades(n):
    return [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(n)]


def _strategy_sends(make, after=None, venue=None):
    """The strategy places `make()` at T0 and, at T0 + 1 s (the order is in
    flight until T0 + 10 s), changes its state and runs `after(request,
    ctx)` on what it kept."""
    STATE["v"] = "sent"
    venue = venue or _Venue()
    kept: dict = {}
    refused: list = []

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ctx.now_ns == T0:
                try:
                    kept["r"] = make()
                    kept["id"] = ctx.place_order(kept["r"])
                except CoreError as exc:
                    refused.append(exc)
            elif ctx.now_ns == T0 + SEC:
                STATE["v"] = "changed"
                if after is not None and "r" in kept:
                    after(kept, ctx)

    CoreEngine(_S(), _trades(12), fill_model=venue, latency_model=_Slow(), cost_model=NullCostModel()).run()
    return venue.seen, refused


def test_strategy_text_that_only_answers_equal_is_refused():
    seen, refused = _strategy_sends(lambda: OrderRequest(side=_AnyEq(), order_type="limit", size=1.0, price=90.0))
    assert seen == [] and isinstance(refused[0], OrderApiError)


def test_strategy_text_subclass_reaches_the_venue_as_the_text_sent():
    seen, refused = _strategy_sends(lambda: OrderRequest(side="buy", order_type=_LiveText("limit"), size=1.0,
                                                         price=90.0))
    assert refused == [] and seen[0]["order_type"] == "limit" and type(seen[0]["order_type"]) is str
    assert (seen[0]["order_type"] == "market") is False


def test_strategy_flag_that_decides_when_asked_is_refused():
    class _LiveBool:
        def __bool__(self):
            return STATE["v"] == "changed"

    seen, refused = _strategy_sends(lambda: OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                                         post_only=_LiveBool()))
    assert seen == [] and isinstance(refused[0], OrderApiError)


def test_strategy_request_subclass_is_refused():
    class _Sub(OrderRequest):
        __slots__ = ()

    seen, refused = _strategy_sends(lambda: _Sub(side="buy", order_type="limit", size=1.0, price=90.0))
    assert seen == [] and isinstance(refused[0], OrderApiError) and "itself" in str(refused[0])


@pytest.mark.parametrize("coid", ["", "mine"])
def test_strategy_bypassing_frozen_after_sending_reaches_no_one(coid):
    """The strategy changes its own request object and the request in its
    view of the order with object.__setattr__ while the order is in
    flight; the venue receives what was sent (with or without its own id:
    round 5 shared the object when the id was given)."""
    def after(kept, ctx):
        object.__setattr__(kept["r"], "size", 500.0)
        object.__setattr__(ctx.order(kept["id"]).request, "size", 700.0)

    seen, refused = _strategy_sends(
        lambda: OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0, client_order_id=coid),
        after=after)
    assert refused == [] and seen[0]["size"] == 1.0


def test_timer_tag_reaches_the_strategy_as_the_text_set():
    got: list = []

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ev.EVENT_TYPE is EventType.CLOCK:
                got.append((type(ev.tag), ev.tag == "t1", str(ev.tag)))
            elif ctx.now_ns == T0:
                ctx.set_timer(T0 + 5 * SEC, _LiveText("t1"))
            elif ctx.now_ns == T0 + SEC:
                STATE["v"] = "changed"

    STATE["v"] = "t1"
    CoreEngine(_S(), _trades(8)).run()
    assert got == [(str, True, "t1")]


def test_fill_model_text_subclass_reaches_the_strategy_as_the_text_sent():
    """The critic's case (i0-r5-01 3.): a reject reason of a str subclass
    that reads the venue's state when printed."""
    reasons: list = []
    venue = _Venue(answer=lambda o: (Reject(o.client_order_id, _LiveText("rejected")),))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ctx.now_ns == T0 and ctx.order("o") is None:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="o"))
            elif ctx.order("o") is not None and ctx.order("o").reason:
                reasons.append((type(ctx.order("o").reason), str(ctx.order("o").reason)))
            if ctx.now_ns == T0 + 3 * SEC:
                STATE["v"] = "venue secret"

    STATE["v"] = "rejected"
    CoreEngine(_S(), _trades(8), fill_model=venue, cost_model=NullCostModel()).run()
    assert reasons and set(reasons) == {(str, "rejected")}


def test_fill_model_fields_that_only_answer_equal_are_refused():
    venue = _Venue(answer=lambda o: (Ack(o.client_order_id), Fill(o.client_order_id, 90.0, 1.0, _AnyEq())))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ctx.now_ns == T0 and ctx.order("o") is None:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="o"))

    with pytest.raises(VenueProtocolError, match="liquidity"):
        CoreEngine(_S(), _trades(3), fill_model=venue, cost_model=NullCostModel()).run()


def test_fill_model_report_subclass_is_refused():
    class _LateAck(Ack):
        __slots__ = ()

    venue = _Venue(answer=lambda o: (_LateAck(o.client_order_id),))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ctx.now_ns == T0 and ctx.order("o") is None:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="o"))

    with pytest.raises(VenueProtocolError, match="unknown report type"):
        CoreEngine(_S(), _trades(3), fill_model=venue, cost_model=NullCostModel()).run()


class _ForcingAccount(NullAccount):
    """Forces one order on the first market event and keeps it; later
    changes it with object.__setattr__."""

    def __init__(self, request):
        self.request = request
        self.done = False

    def on_market_event(self, event, venue_time_ns):
        if not self.done:
            self.done = True
            return (self.request,)
        object.__setattr__(self.request, "size", 900.0)
        return ()


@pytest.mark.parametrize("coid", ["", "forced-a"])
def test_account_forced_order_reaches_venue_and_strategy_as_sent(coid):
    """With or without its own id (round 5 shared the account's object
    with the strategy's view when the id was given)."""
    venue = _Venue()
    views: list = []
    account = _ForcingAccount(OrderRequest("sell", "market", 2.0, client_order_id=coid))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            for v in ctx.open_orders():
                views.append(v.request.size)

    CoreEngine(_S(), _trades(5), fill_model=venue, account=account, cost_model=NullCostModel()).run()
    assert venue.seen[0]["size"] == 2.0
    assert views and set(views) == {2.0}


def test_account_forced_order_subclass_is_refused():
    class _Sub(OrderRequest):
        __slots__ = ()

    account = _ForcingAccount(_Sub("sell", "market", 2.0))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            pass

    with pytest.raises(AccountSocketError, match="itself"):
        CoreEngine(_S(), _trades(3), account=account, cost_model=NullCostModel()).run()


def test_source_event_subclass_is_refused():
    class _LeakyTrade(TradeEvent):
        __slots__ = ()

        @property
        def later(self):
            return "the source's state"

    class _S(Strategy):
        def on_event(self, ev, ctx):
            pass

    with pytest.raises(SourceEventTypeError, match="subclass"):
        CoreEngine(_S(), [_LeakyTrade(received_time_ns=T0, price=1.0, size=1.0, side="buy")]).run()


def test_source_text_subclass_reaches_venue_and_strategy_as_the_text_sent():
    got: list = []
    venue_got: list = []

    class _V(_Venue):
        def on_market_event(self, e, t):
            venue_got.append((type(e.side), type(e.trade_id)))
            return ()

    class _S(Strategy):
        def on_event(self, ev, ctx):
            got.append((type(ev.side), type(ev.trade_id), ev.trade_id))

    STATE["v"] = "x"
    ev = TradeEvent(received_time_ns=T0, price=1.0, size=1.0, side=_LiveText("buy"), trade_id=_LiveText("t-1"))
    CoreEngine(_S(), [ev], fill_model=_V()).run()
    assert got == [(str, str, "t-1")] and venue_got == [(str, str)]


def test_plug_in_answers_and_stream_names_are_taken_as_builtin_values():
    """What the engine takes from a latency model (a delay), a cost model
    (a fee) and the caller (stream names) is read once, as the built-in
    value, never through the plug-in's own methods later."""
    calls = {"n": 0}

    class _LiveInt(int):
        def __int__(self):
            calls["n"] += 1
            return 999

        __index__ = __int__

    class _LiveFloat(float):
        def __float__(self):
            calls["n"] += 1
            return 999.0

    class _LiveName(str):
        def __lt__(self, other):
            calls["n"] += 1
            return True

        __hash__ = str.__hash__

    class _Lat:
        def feed_delay_ns(self, e):
            return _LiveInt(0)

        def order_delay_ns(self, o, t):
            return _LiveInt(SEC)

        def cancel_delay_ns(self, r, t):
            return _LiveInt(0)

        def notice_delay_ns(self, r, t):
            return _LiveInt(0)

    class _Cost:
        def cost(self, fill):
            return _LiveFloat(0.25)

    venue = _Venue(answer=lambda o: (Ack(o.client_order_id), Fill(o.client_order_id, 90.0, 1.0)))

    class _S(Strategy):
        def on_event(self, ev, ctx):
            if ctx.now_ns == T0 and ctx.order("o") is None:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="o"))

    streams = {_LiveName("b"): _trades(3), "a": [TradeEvent(received_time_ns=T0 + 1, price=1.0, size=1.0, side="buy")]}
    res = CoreEngine(_S(), streams, fill_model=venue, latency_model=_Lat(), cost_model=_Cost()).run()
    assert calls["n"] == 0
    assert [(type(f.fee), f.fee, f.venue_time_ns) for f in res.fills] == [(float, 0.25, T0 + SEC)]
    assert list(res.source_events_by_stream) == ["a", "b"]
    assert all(type(k) is str for k in res.source_events_by_stream)
