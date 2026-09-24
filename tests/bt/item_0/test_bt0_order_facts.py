"""Order state is kept as facts, on both sides (i0-r1-07, i0-r1-09).

Venue ledger: an ambiguous answer never erases what is known (acked,
filled), so contradictions after it still raise VenueProtocolError.
Strategy view: STATE_UNKNOWN is held until a notice that settles it; the
strategy's own cancel and a cancel reject do not clear it (CLAUDE.md
section 1)."""
import pytest

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    Fill,
    NullCostModel,
    OrderRequest,
    OrderState,
    Reject,
    StateUnknown,
    Strategy,
    VenueProtocolError,
)

from bt0_util import SEC, T0, trade


class _Venue:
    """on_order answers with `on_order`; each cancel pops the next answer
    from `cancels`; each market event pops the next list from `later`."""

    def __init__(self, on_order, cancels=(), later=()):
        self._on_order = on_order
        self.cancels = list(cancels)
        self.later = list(later)

    def on_market_event(self, e, t):
        return tuple(self.later.pop(0)) if self.later else ()

    def on_order(self, o, t):
        return tuple(self._on_order(o.client_order_id, o.size))

    def on_cancel(self, c, t):
        return tuple(self.cancels.pop(0)(c.client_order_id))


class _Script(Strategy):
    """Call n (1-based, trades only) runs script[n] if present; records the
    order view after every call."""

    def __init__(self, script):
        self.script = script
        self.n = 0
        self.views = []

    def on_event(self, e, ctx):
        if e.EVENT_TYPE.value == "TRADE":
            self.n += 1
            act = self.script.get(self.n)
            if act == "place":
                ctx.place_order(OrderRequest(side="buy", order_type="limit", size=2.0, price=90.0,
                                             client_order_id="o"))
            elif act == "cancel":
                ctx.cancel_order("o")
        v = ctx.order("o")
        if v is not None:
            self.views.append((e.EVENT_TYPE.value, v.state, v.cancel_pending, v.unknown_new, v.unknown_cancel))


def _run(venue, script, n=6):
    strat = _Script(script)
    res = CoreEngine(strat, [trade(T0 + k * SEC) for k in range(1, n + 1)], fill_model=venue,
                     cost_model=NullCostModel()).run()
    return strat, res


# -- venue ledger ---------------------------------------------------------------

def test_state_unknown_about_the_new_order_after_its_ack_is_a_contradiction():
    venue = _Venue(lambda c, s: [Ack(c)], later=[[], [StateUnknown("o", "late", "new")]])
    with pytest.raises(VenueProtocolError, match="acknowledged"):
        _run(venue, {1: "place"})


def test_cancel_state_unknown_outside_its_cancel_is_a_contradiction():
    venue = _Venue(lambda c, s: [Ack(c)], later=[[], [StateUnknown("o", "x", "cancel")]])
    with pytest.raises(VenueProtocolError, match="outside its cancel"):
        _run(venue, {1: "place"})


def test_fill_after_ambiguous_cancel_is_accepted_and_the_order_stays_unknown():
    venue = _Venue(lambda c, s: [Ack(c)],
                   cancels=[lambda c: [StateUnknown(c, "cancel timed out", "cancel")]],
                   later=[[], [], [Fill("o", 90.0, 1.0)]])
    strat, res = _run(venue, {1: "place", 2: "cancel"})
    assert res.venue_states["o"] == "STATE_UNKNOWN"
    assert res.orders["o"].state is OrderState.STATE_UNKNOWN
    assert res.orders["o"].filled_size == 1.0


def test_last_fill_after_ambiguous_cancel_settles_it_as_filled():
    venue = _Venue(lambda c, s: [Ack(c)],
                   cancels=[lambda c: [StateUnknown(c, "cancel timed out", "cancel")]],
                   later=[[], [], [Fill("o", 90.0, 2.0)]])
    _, res = _run(venue, {1: "place", 2: "cancel"})
    assert res.venue_states["o"] == "FILLED"
    assert res.orders["o"].state is OrderState.FILLED


def test_fill_settles_an_ambiguous_new_order():
    venue = _Venue(lambda c, s: [StateUnknown(c, "timeout")], later=[[], [Fill("o", 90.0, 1.0)]])
    _, res = _run(venue, {1: "place"})
    assert res.venue_states["o"] == "LIVE"
    assert res.orders["o"].state is OrderState.OPEN
    assert res.orders["o"].unknown_new is False


# -- strategy view --------------------------------------------------------------

def test_cancel_sent_on_an_unknown_order_keeps_state_unknown_and_marks_the_cancel():
    venue = _Venue(lambda c, s: [StateUnknown(c, "timeout")],
                   cancels=[lambda c: [Reject(c, "busy", "cancel")]])
    strat, res = _run(venue, {1: "place", 2: "cancel"})
    # after call 2 (the cancel was sent): still STATE_UNKNOWN, cancel pending
    assert ("TRADE", OrderState.STATE_UNKNOWN, True, True, False) in strat.views
    # the cancel reject answers the cancel only
    assert res.orders["o"].state is OrderState.STATE_UNKNOWN
    assert res.orders["o"].cancel_pending is False
    assert res.venue_states["o"] == "STATE_UNKNOWN"


def test_ack_settles_an_unknown_new_order_even_with_a_cancel_in_flight():
    venue = _Venue(lambda c, s: [StateUnknown(c, "timeout")],
                   cancels=[lambda c: [Canceled(c)]], later=[[], [Ack("o")]])
    strat, res = _run(venue, {1: "place", 3: "cancel"})
    assert ("ORDER_ACK", OrderState.OPEN, False, False, False) in strat.views
    assert res.orders["o"].state is OrderState.CANCELED


def test_pending_cancel_then_cancel_reject_returns_to_open_from_facts():
    venue = _Venue(lambda c, s: [Ack(c)], cancels=[lambda c: [Reject(c, "too late", "cancel")]])
    strat, res = _run(venue, {1: "place", 2: "cancel"})
    assert ("TRADE", OrderState.PENDING_CANCEL, True, False, False) in strat.views
    assert res.orders["o"].state is OrderState.OPEN
