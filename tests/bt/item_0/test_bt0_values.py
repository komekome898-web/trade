"""What crosses a path is a value when it is made (i0-r4-02, i0-r4-07).

An order request travels strategy -> venue and arrives LATER; a notice
travels venue -> strategy. Round 4 carried references: a list the strategy
put in `OrderRequest.extra`, changed from a later callback while the order
was in flight, reached the venue changed; a list a fill model put in a
reject reason, changed later at the venue, showed in the strategy's view
without any notice. Now `OrderRequest` makes `extra` deeply immutable at
construction (values.py; `extra_dict()` reads back a fresh copy) and notice
text fields must be str, so nothing changeable is shared across a path.
"""
from __future__ import annotations

import enum
import random
from decimal import Decimal
from fractions import Fraction

import pytest

from bot.bt.core import (
    ALL_EVENT_CLASSES,
    Ack,
    CoreEngine,
    EngineFailedError,
    FrozenDict,
    FrozenList,
    NullCostModel,
    OrderApiError,
    OrderRequest,
    Reject,
    StateUnknown,
    Canceled,
    Strategy,
    TradeEvent,
    VenueProtocolError,
)
from bot.bt.core.values import PlainDecimal, PlainFraction, freeze, thaw

from test_bt0_events import SAMPLES

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


class _SlowOrders:
    """Orders reach the venue 10 s after they are sent; nothing else waits."""

    def feed_delay_ns(self, event) -> int:
        return 0

    def order_delay_ns(self, order, sent_time_ns) -> int:
        return 10 * SEC

    def cancel_delay_ns(self, request, sent_time_ns) -> int:
        return 0

    def notice_delay_ns(self, report, venue_time_ns) -> int:
        return 0


class _Venue:
    """Records what arrives; optionally changes what it received."""

    def __init__(self, change_received=None) -> None:
        self.received = []
        self.change_received = change_received

    def on_market_event(self, event, venue_time_ns):
        return ()

    def on_order(self, order, venue_time_ns):
        got = order.extra_dict()
        self.received.append((venue_time_ns, got))
        if self.change_received is not None:
            self.change_received(got)
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, venue_time_ns):
        return (Canceled(request.client_order_id),)


def _run_with(change_after_send, venue=None):
    venue = venue or _Venue()
    seen = {}

    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0:
                self.mine = {"legs": ["a"], "show": {"qty": 1.0}, "tags": {"x"}}
                self.req = OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0,
                                        extra=(("meta", self.mine),))
                self.coid = ctx.place_order(self.req)
            elif ctx.now_ns == T0 + SEC:  # a later callback; the order is still in flight
                change_after_send(self, ctx)
            elif ctx.now_ns == T0 + 11 * SEC:
                seen["view"] = ctx.order(self.coid).request.extra_dict()

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(12)]
    res = CoreEngine(_S(), events, fill_model=venue, latency_model=_SlowOrders(),
                     cost_model=NullCostModel()).run()
    return venue, seen, res


_SENT = {"meta": {"legs": ["a"], "show": {"qty": 1.0}, "tags": {"x"}}}


def _change_own_container(s, ctx):
    s.mine["legs"].append("changed later")
    s.mine["show"]["qty"] = 0.0
    s.mine["tags"].add("y")
    s.mine["new"] = 1


def _change_what_the_view_reads(s, ctx):
    got = ctx.order(s.coid).request.extra_dict()
    got["meta"]["legs"].append("changed later")
    got["meta"]["show"]["qty"] = 0.0


def _change_what_the_request_reads(s, ctx):
    got = s.req.extra_dict()
    got["meta"]["legs"].append("changed later")


@pytest.mark.parametrize("change", [_change_own_container, _change_what_the_view_reads,
                                    _change_what_the_request_reads])
def test_the_venue_receives_what_was_sent_whatever_the_strategy_changes_later(change):
    venue, seen, res = _run_with(change)
    assert venue.received == [(T0 + 10 * SEC, _SENT)]
    assert seen["view"] == _SENT
    assert res.order_requests[0].extra_dict() == _SENT


def test_what_the_venue_changes_in_what_it_received_reaches_nobody():
    def venue_changes(got):
        got["meta"]["legs"].append("venue wrote this")
        got["meta"]["show"]["qty"] = 99.0

    venue, seen, res = _run_with(lambda s, ctx: None, _Venue(change_received=venue_changes))
    assert seen["view"] == _SENT
    assert res.order_requests[0].extra_dict() == _SENT
    assert res.orders[next(iter(res.orders))].request.extra_dict() == _SENT


def test_extra_is_immutable_and_the_request_is_hashable():
    req = OrderRequest("buy", "limit", 1.0, price=1.0, extra=(("a", [1, [2, 3]]), ("b", {"k": {1, 2}})))
    assert isinstance(req.extra[0][1], FrozenList) and isinstance(req.extra[1][1], FrozenDict)
    with pytest.raises((TypeError, AttributeError)):
        req.extra[1][1]["k"] = 0  # type: ignore[index]
    with pytest.raises(AttributeError):
        req.extra[0][1].append(4)  # type: ignore[attr-defined]
    hash(req)
    assert req.extra_dict() == {"a": [1, [2, 3]], "b": {"k": {1, 2}}}
    assert type(req.extra_dict()["a"]) is list and type(req.extra_dict()["b"]["k"]) is set


class _Size(enum.IntEnum):
    ONE = 1


class _Word(enum.StrEnum):
    RED = "red"


class _Ratio(float):
    pass


def _random_plain(rng: random.Random, depth: int = 0):
    # IntEnum / StrEnum members and a float subclass are stored as the
    # built-in value they hold (values.py `scalar`); they compare equal
    scalars = [None, True, rng.randrange(-10**20, 10**20), rng.random() * 1e6, "s" * rng.randrange(0, 4),
               b"b", Decimal("1.25"), Fraction(1, 3), complex(1, 2), _Size.ONE, _Word.RED, _Ratio(0.5)]
    if depth >= 3 or rng.random() < 0.35:
        return rng.choice(scalars)
    kind = rng.choice(["list", "tuple", "dict", "set", "frozenset"])
    n = rng.randrange(0, 4)
    if kind == "list":
        return [_random_plain(rng, depth + 1) for _ in range(n)]
    if kind == "tuple":
        return tuple(_random_plain(rng, depth + 1) for _ in range(n))
    if kind == "dict":
        return {f"k{i}": _random_plain(rng, depth + 1) for i in range(n)}
    leaves = [rng.randrange(0, 100) for _ in range(n)]
    return set(leaves) if kind == "set" else frozenset(leaves)


def _mutate_somewhere(value, rng) -> bool:
    """Change the first changeable container found; True if one was changed."""
    if isinstance(value, list):
        value.append("mutated")
        return True
    if isinstance(value, dict):
        value["mutated"] = 1
        return True
    if isinstance(value, set):
        value.add(-1)
        return True
    if isinstance(value, tuple):
        return any(_mutate_somewhere(v, rng) for v in value)
    return False


def _builtin_only(value) -> bool:
    if isinstance(value, (list, tuple, set, frozenset)):
        return all(_builtin_only(v) for v in value)
    if isinstance(value, dict):
        return all(_builtin_only(k) and _builtin_only(v) for k, v in value.items())
    # round 15 (i0-r14-01): a Fraction / Decimal comes back as the core's own PlainFraction / PlainDecimal
    return type(value) in (type(None), bool, int, float, complex, str, bytes, PlainDecimal, PlainFraction)


def test_plain_data_round_trips_and_later_changes_do_not_reach_the_request_seeded():
    rng = random.Random(20260924)
    changed = 0
    for i in range(2000):
        data = _random_plain(rng)
        req = OrderRequest("sell", "limit", 1.0, price=2.0, extra=(("v", data),))
        assert req.extra_dict() == {"v": data}
        assert _builtin_only(req.extra_dict())  # no object of the sender's class is kept
        hash(req)
        import copy
        before = copy.deepcopy(data)
        if _mutate_somewhere(data, rng):
            changed += 1
            assert req.extra_dict() == {"v": before}
        assert thaw(freeze(before)) == before
    assert changed > 300


class _Color(enum.Enum):
    RED = "red"


@pytest.mark.parametrize("value", [
    lambda: 1,                      # code: runs later with the sender's state
    object(),                       # an arbitrary object
    (x for x in range(3)),          # a generator
    bytearray(b"x"),                # a changeable scalar
    [1, object()],                  # nested
    _Color.RED,                     # a plain Enum member: an object of the sender's class (i0-r5-01)
    {"k": [_Color.RED]},            # ... nested
])
def test_values_that_are_not_plain_data_are_refused_when_the_request_is_made(value):
    with pytest.raises(OrderApiError, match="not plain data"):
        OrderRequest("buy", "limit", 1.0, price=1.0, extra=(("x", value),))


def test_a_container_that_holds_itself_is_refused():
    loop: list = [1]
    loop.append(loop)
    with pytest.raises(OrderApiError, match="cycle"):
        OrderRequest("buy", "limit", 1.0, price=1.0, extra=(("x", loop),))


@pytest.mark.parametrize("extra, match", [
    ([("a", 1)], "tuple"),
    ((("a",),), "pair"),
    ((("a", 1, 2),), "pair"),
    (((1, 1),), "key"),
    ((("", 1),), "key"),
    ((("a", 1), ("a", 2)), "twice"),
])
def test_the_shape_of_extra_is_checked_when_the_request_is_made(extra, match):
    # i0-r4-07: a malformed pair used to fail only at the venue, at the arrival time
    with pytest.raises(OrderApiError, match=match):
        OrderRequest("buy", "limit", 1.0, price=1.0, extra=extra)


class _BadTextVenue:
    def __init__(self, report) -> None:
        self.report = report

    def on_market_event(self, event, t):
        return ()

    def on_order(self, order, t):
        return (self.report(order.client_order_id),)

    def on_cancel(self, request, t):
        return ()


@pytest.mark.parametrize("field, report", [
    ("reason", lambda coid: Reject(coid, ["a list"])),
    ("detail", lambda coid: StateUnknown(coid, {"a": 1})),
    ("venue_order_id", lambda coid: Ack(coid, ["v1"])),
])
def test_a_report_whose_text_is_not_text_is_refused_at_the_venue(field, report):
    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0))

    eng = CoreEngine(_S(), [TradeEvent(received_time_ns=T0, price=1.0, size=1.0, side="buy")],
                     fill_model=_BadTextVenue(report), cost_model=NullCostModel())
    with pytest.raises(VenueProtocolError, match=field):
        eng.run()
    with pytest.raises(EngineFailedError):
        eng.result()


def test_the_venue_cannot_reach_the_strategy_through_a_notice_it_keeps():
    """The hole found in round 5: a fill model rejected with a list as the
    reason and appended to it at T0 + 5 s; the strategy's view showed the
    append at T0 + 5 s without any notice. Now the reject is refused."""
    shared = ["rejected"]

    class _V:
        def on_market_event(self, e, t):
            if t == T0 + 5 * SEC:
                shared.append("venue state at T0 + 5 s")
            return ()

        def on_order(self, o, t):
            return (Reject(o.client_order_id, shared),)

        def on_cancel(self, r, t):
            return ()

    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if ctx.now_ns == T0 and ctx.order("core-1") is None:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0))

    events = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy") for i in range(8)]
    with pytest.raises(VenueProtocolError, match="reason must be a str"):
        CoreEngine(_S(), events, fill_model=_V(), cost_model=NullCostModel()).run()


@pytest.mark.parametrize("event", SAMPLES, ids=lambda e: e.EVENT_TYPE.value)
def test_every_event_type_is_a_value(event):
    """Every field of every event type is immutable, so the event hashes;
    a new event type with a changeable field fails here."""
    hash(event)
    assert {type(s) for s in SAMPLES} == set(ALL_EVENT_CLASSES)


@pytest.mark.parametrize("cls, field", [
    ("OrderAckEvent", "venue_order_id"),
    ("OrderRejectEvent", "reason"),
    ("OrderCanceledEvent", "reason"),
    ("OrderStateUnknownEvent", "detail"),
])
def test_notice_text_fields_must_be_str(cls, field):
    import bot.bt.core as core
    from bot.bt.core import EventValidationError
    kwargs = {"received_time_ns": T0, "client_order_id": "c1", field: ["not", "text"]}
    if cls == "OrderRejectEvent" and field != "reason":
        kwargs["reason"] = "r"
    with pytest.raises(EventValidationError, match=field):
        getattr(core, cls)(**kwargs)


def test_a_request_survives_copy_deepcopy_and_pickle_as_the_same_value():
    """Item 8 (repro) keeps results; the frozen containers rebuild through
    their constructors, never by setting fields."""
    import copy
    import pickle
    req = OrderRequest("buy", "limit", 1.0, price=1.0, extra=(("a", [1, {"b": {2}}]), ("c", {"d": (1, [2])})))
    for clone in (copy.copy(req), copy.deepcopy(req), pickle.loads(pickle.dumps(req))):
        assert clone == req and hash(clone) == hash(req)
        assert clone.extra_dict() == {"a": [1, {"b": {2}}], "c": {"d": (1, [2])}}
