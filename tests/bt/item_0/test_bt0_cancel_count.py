"""Cancels are counted one by one (i0-r2-02).

The venue answers each cancel exactly once; ORDER_CANCELED says what it
answers (`answers`: our cancel / the new order / the venue on its own); the
strategy's view keeps `cancels_in_flight` and shows PENDING_CANCEL while it
is >= 1, whatever the order in which the answers arrive."""
import random

import pytest

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderRequest,
    OrderState,
    Reject,
    StateUnknown,
    Strategy,
    ZeroLatency,
)

from bt0_util import MS, T0, trade


class _Venue:
    """Acks every order; each cancel pops its answer from `answers`;
    market events pop report lists from `later`."""

    def __init__(self, answers=(), on_order=None, later=()):
        self.answers = list(answers)
        self._on_order = on_order
        self.later = list(later)

    def on_market_event(self, e, t):
        return tuple(self.later.pop(0)) if self.later else ()

    def on_order(self, o, t):
        if self._on_order is not None:
            return tuple(self._on_order(o.client_order_id))
        return (Ack(o.client_order_id),)

    def on_cancel(self, c, t):
        return tuple(self.answers.pop(0)(c.client_order_id))


class _Latency(ZeroLatency):
    def __init__(self, cancel_ms=1, notice_ms=lambda r: 1):
        self.cancel_ms, self.notice_ms = cancel_ms, notice_ms

    def cancel_delay_ns(self, request, sent):
        return self.cancel_ms * MS

    def notice_delay_ns(self, report, venue_time):
        return self.notice_ms(report) * MS


class _Script(Strategy):
    """Trade call k runs script[k]: "place" or "cancel"; records
    (seq, state, cancels_in_flight, cancel_pending) after every call."""

    def __init__(self, script):
        self.script, self.k, self.coid, self.views = script, 0, None, []

    def on_event(self, ev, ctx):
        if ev.EVENT_TYPE is EventType.TRADE:
            self.k += 1
            act = self.script.get(self.k)
            if act == "place":
                self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
            elif act == "cancel":
                ctx.cancel_order(self.coid)
        if self.coid is not None:
            v = ctx.order(self.coid)
            self.views.append((ev.EVENT_TYPE.value, v.state, v.cancels_in_flight, v.cancel_pending))


def _trades(n=30):
    return [trade(T0 + k * MS // 2) for k in range(n)]


def test_critic_scene_first_cancel_refused_second_still_in_flight():
    venue = _Venue([lambda c: [Reject(c, "busy", "cancel")], lambda c: [Canceled(c)]])
    lat = _Latency(notice_ms=lambda r: 1 if isinstance(r, Reject) else 5)
    strat = _Script({1: "place", 2: "cancel", 3: "cancel"})
    res = CoreEngine(strat, _trades(), fill_model=venue, latency_model=lat, cost_model=NullCostModel()).run()
    after_reject = [v for v in strat.views if v[0] == "ORDER_REJECT"]
    assert after_reject == [("ORDER_REJECT", OrderState.PENDING_CANCEL, 1, True)]
    assert res.orders[strat.coid].state is OrderState.CANCELED
    assert res.orders[strat.coid].cancels_in_flight == 0
    # never OPEN with an unanswered cancel of ours
    assert not [v for v in strat.views if v[2] > 0 and v[1] is OrderState.OPEN]


def test_cancel_on_a_final_order_is_counted_until_the_engine_answers_it():
    venue = _Venue([lambda c: [Canceled(c)]])
    strat = _Script({1: "place", 2: "cancel", 3: "cancel"})
    lat = _Latency(cancel_ms=1, notice_ms=lambda r: 3)
    res = CoreEngine(strat, _trades(), fill_model=venue, latency_model=lat, cost_model=NullCostModel()).run()
    # the second cancel reaches a CANCELED order; the engine answers it itself
    rejects = [v for v in strat.views if v[0] == "ORDER_REJECT"]
    assert rejects and rejects[-1][1:] == (OrderState.CANCELED, 0, False)
    assert res.orders[strat.coid].cancel_pending is False


def test_canceled_notice_says_what_it_answers():
    seen = []

    class _Rec(Strategy):
        def on_event(self, ev, ctx):
            if ev.EVENT_TYPE is EventType.TRADE and ev.seq == 1:
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                             client_order_id="ioc"))
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                             client_order_id="expire"))
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                             client_order_id="ours"))
                ctx.cancel_order("ours")
            if ev.EVENT_TYPE is EventType.ORDER_CANCELED:
                seen.append((ev.client_order_id, ev.answers))

    def on_order(c):
        return [Ack(c), Canceled(c, "ioc_remainder")] if c == "ioc" else [Ack(c)]

    venue = _Venue([lambda c: [Canceled(c)]], on_order=on_order, later=[[], [Canceled("expire", "expired")]])
    CoreEngine(_Rec(), _trades(5), fill_model=venue, cost_model=NullCostModel()).run()
    assert sorted(seen) == [("expire", "venue"), ("ioc", "new"), ("ours", "cancel")]


def test_ambiguous_cancel_answer_takes_one_off_and_keeps_state_unknown():
    venue = _Venue([lambda c: [StateUnknown(c, "timeout", "cancel")], lambda c: [Reject(c, "busy", "cancel")]])
    strat = _Script({1: "place", 2: "cancel", 3: "cancel"})
    res = CoreEngine(strat, _trades(), fill_model=venue, latency_model=_Latency(),
                     cost_model=NullCostModel()).run()
    v = res.orders[strat.coid]
    assert (v.state, v.cancels_in_flight, v.unknown_cancel) == (OrderState.STATE_UNKNOWN, 0, True)


def test_random_cancels_view_counts_match_the_requests_in_flight():
    """Random answers and delays: at every callback, cancels_in_flight equals
    cancels sent minus cancel answers delivered, and PENDING_CANCEL / OPEN
    follow it for an acknowledged, not-final order."""
    for seed in range(120):
        rng = random.Random(seed)

        def answer(c, rng=rng):
            r = rng.random()
            if r < 0.4:
                return [Reject(c, "busy", "cancel")]
            if r < 0.55:
                return [StateUnknown(c, "timeout", "cancel")]
            return [Canceled(c)]

        venue = _Venue([answer] * 50)
        lat = _Latency(cancel_ms=rng.choice([0, 1, 3]), notice_ms=lambda r, rng=rng: rng.choice([0, 1, 4, 9]))

        class _T(Strategy):
            def __init__(self):
                self.coid, self.sent, self.answered, self.bad = None, 0, 0, []

            def on_event(self, ev, ctx):
                name = ev.EVENT_TYPE.value
                if name == "ORDER_REJECT" and ev.request_kind == "cancel" or \
                        name == "ORDER_STATE_UNKNOWN" and ev.request_kind == "cancel" or \
                        name == "ORDER_CANCELED" and ev.answers == "cancel":
                    self.answered += 1
                if name == "TRADE":
                    if self.coid is None:
                        self.coid = ctx.place_order(OrderRequest(side="buy", order_type="limit", size=1.0,
                                                                 price=90.0))
                    elif rng.random() < 0.5:
                        ctx.cancel_order(self.coid)
                        self.sent += 1
                if self.coid is not None:
                    v = ctx.order(self.coid)
                    if v.cancels_in_flight != self.sent - self.answered:
                        self.bad.append((ev.seq, v.cancels_in_flight, self.sent - self.answered))
                    if v.acked and v.state not in (OrderState.FILLED, OrderState.CANCELED,
                                                   OrderState.REJECTED, OrderState.STATE_UNKNOWN):
                        want = OrderState.PENDING_CANCEL if v.cancels_in_flight else OrderState.OPEN
                        if v.state is not want:
                            self.bad.append((ev.seq, v.state, want))

        strat = _T()
        res = CoreEngine(strat, _trades(40), fill_model=venue, latency_model=lat,
                         cost_model=NullCostModel()).run()
        assert strat.bad == [], (seed, strat.bad[:3])
        assert res.orders[strat.coid].cancels_in_flight == 0
