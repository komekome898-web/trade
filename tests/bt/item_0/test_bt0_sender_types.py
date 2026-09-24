"""i0-r6-03 and its root: every decision on the type of a value a sender
hands the core reads the value's REAL type, never what the object claims
through `__class__` (values.py `is_a`), and one rule (values.py `scalar`)
decides which foreign values become built-in values.

Each row below is one place a sender's value enters the core (a field of
a carrier, a read argument, an answer index, a plug-in's answer, a source,
a run setting). It is fed an object that CLAIMS the expected class and
records every method of its own that runs; the place must refuse it with
its own error type (never a bare TypeError / AttributeError from a later
read, never a silently empty answer), and none of the object's methods
may run -- the claim decides nothing.

A second table feeds numpy scalars (what numpy and pandas give): a number
field takes every number of the numeric tower, an int field every
integral one, a flag field a numpy bool; what is stored is the built-in
type itself, and the same value is treated the same at every place of
the same kind."""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from bot.bt.core import (
    Ack,
    AccountSocketError,
    CoreError,
    BarEvent,
    CancelRequest,
    ClockEvent,
    CoreEngine,
    CostModelError,
    EventType,
    EventValidationError,
    Fill,
    LatencyModelError,
    NullAccount,
    NullCostModel,
    NullFillModel,
    OrderApiError,
    OrderRequest,
    Reject,
    SourceEventTypeError,
    Strategy,
    TimestampUnitError,
    TradeEvent,
    VenueProtocolError,
    ZeroLatency,
    to_nanos,
    validate_nanos,
)
from bot.bt.core.values import as_flag, as_float, as_int, as_text, freeze, is_a, scalar, type_name

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000

RAN: list = []  # (claimed class, method) of every Liar method that ran


def liar(cls):
    """An object whose `__class__` claims `cls`; every other method it has
    records that it ran."""
    def rec(name):
        def method(self, *a, **k):
            RAN.append((cls.__name__, name))
            if name in ("__index__", "__int__", "__len__", "__hash__"):
                return 1
            if name == "__float__":
                return 1.0
            if name in ("__str__", "__repr__"):
                return "liar"
            if name == "__bool__":
                return True
            if name == "__iter__":
                return iter(())
            return NotImplemented
        return method

    names = ("__index__", "__int__", "__float__", "__str__", "__bool__", "__len__", "__iter__",
             "__getitem__", "__eq__", "__lt__", "__hash__")
    ns = {n: rec(n) for n in names}
    ns["__class__"] = property(lambda self: cls)
    ns["__repr__"] = lambda self: f"Liar({cls.__name__})"
    return type("Liar", (), ns)()


def bar(t, c=100.0):
    return BarEvent(received_time_ns=t, open=c, high=c, low=c, close=c, volume=1.0)


def req(**kw):
    base = dict(side="buy", order_type="limit", size=1.0, price=100.0)
    base.update(kw)
    return OrderRequest(**base)


class _Noop(Strategy):
    def on_event(self, event, ctx):
        pass


def _in_run(action, **engine_kw):
    got = {}

    class S(Strategy):
        def on_event(self, ev, ctx):
            if "done" in got:
                return
            got["done"] = True
            got["out"] = action(ctx)

    CoreEngine(S(), [bar(T0), bar(T0 + SEC)], **engine_kw).run()
    return got.get("out")


class _Lat(ZeroLatency):
    def __init__(self, v):
        self.v = v

    def order_delay_ns(self, order, sent):
        return self.v


class _FillAll(NullFillModel):
    def on_order(self, order, t):
        return (Ack(order.client_order_id), Fill(order.client_order_id, 100.0, 1.0))


class _Cost(NullCostModel):
    def __init__(self, v):
        self.v = v

    def cost(self, fill):
        return self.v


class _Acct(NullAccount):
    def __init__(self, reason=None, forced=()):
        self.reason, self.forced, self.calls = reason, forced, 0

    def check_order(self, order, t):
        return self.reason

    def on_market_event(self, ev, t):
        self.calls += 1
        return self.forced if self.calls == 1 else ()


def _place(ctx):
    return ctx.place_order(req())


class _Pairs(Mapping):
    """A mapping of (key, value) pairs that never hashes or compares its
    keys (so only the core can run a key's methods)."""

    def __init__(self, pairs):
        self._pairs = list(pairs)

    def __getitem__(self, key):
        for k, v in self._pairs:
            if k is key:
                return v
        raise KeyError(key)

    def __iter__(self):
        return (k for k, _ in self._pairs)

    def __len__(self):
        return len(self._pairs)

    def items(self):
        return list(self._pairs)


# (place, how the claimed value is handed over, the place's error type)
LIAR_ROWS = [
    ("OrderRequest.size", lambda v: req(size=v), float, OrderApiError),
    ("OrderRequest.price", lambda v: req(price=v), float, OrderApiError),
    ("OrderRequest.trigger_price", lambda v: req(trigger_price=v), float, OrderApiError),
    ("OrderRequest.side", lambda v: req(side=v), str, OrderApiError),
    ("OrderRequest.order_type", lambda v: req(order_type=v), str, OrderApiError),
    ("OrderRequest.client_order_id", lambda v: req(client_order_id=v), str, OrderApiError),
    ("OrderRequest.time_in_force", lambda v: req(time_in_force=v), str, OrderApiError),
    ("OrderRequest.post_only", lambda v: req(post_only=v), bool, OrderApiError),
    ("OrderRequest.reduce_only", lambda v: req(reduce_only=v), bool, OrderApiError),
    ("OrderRequest.extra", lambda v: req(extra=v), tuple, OrderApiError),
    ("OrderRequest.extra pair", lambda v: req(extra=(v,)), tuple, OrderApiError),
    ("OrderRequest.extra key", lambda v: req(extra=((v, 1),)), str, OrderApiError),
    ("OrderRequest.extra value", lambda v: req(extra=(("k", v),)), str, OrderApiError),
    ("CancelRequest.client_order_id", lambda v: CancelRequest(v), str, OrderApiError),
    ("Ack.client_order_id", lambda v: Ack(v), str, VenueProtocolError),
    ("Fill.price", lambda v: Fill("a", v, 1.0), float, VenueProtocolError),
    ("Fill.liquidity", lambda v: Fill("a", 1.0, 1.0, v), str, VenueProtocolError),
    ("Reject.reason", lambda v: Reject("a", v), str, VenueProtocolError),
    ("TradeEvent.price", lambda v: TradeEvent(received_time_ns=T0, price=v, size=1.0, side="buy"),
     float, EventValidationError),
    ("TradeEvent.trade_id", lambda v: TradeEvent(received_time_ns=T0, price=1.0, size=1.0, side="buy",
                                                 trade_id=v), str, EventValidationError),
    ("TradeEvent.received_time_ns", lambda v: TradeEvent(received_time_ns=v, price=1.0, size=1.0, side="buy"),
     int, TimestampUnitError),
    ("ClockEvent.tag", lambda v: ClockEvent(received_time_ns=T0, tag=v), str, EventValidationError),
    ("validate_nanos", lambda v: validate_nanos(v), int, TimestampUnitError),
    ("to_nanos ms", lambda v: to_nanos(v, "ms"), int, TimestampUnitError),
    ("to_nanos s", lambda v: to_nanos(v, "s"), float, TimestampUnitError),
    ("to_nanos iso", lambda v: to_nanos(v, "iso"), str, TimestampUnitError),
    ("ctx.cancel_order", lambda v: _in_run(lambda c: c.cancel_order(v)), str, OrderApiError),
    ("ctx.order", lambda v: _in_run(lambda c: c.order(v)), str, OrderApiError),
    ("ctx.set_timer at", lambda v: _in_run(lambda c: c.set_timer(v, "t")), int, TimestampUnitError),
    ("ctx.set_timer tag", lambda v: _in_run(lambda c: c.set_timer(T0 + 1, v)), str, OrderApiError),
    ("ctx.visible_events event_type", lambda v: _in_run(lambda c: c.visible_events(v)), EventType, OrderApiError),
    ("ctx.visible_events n", lambda v: _in_run(lambda c: c.visible_events(n=v)), int, OrderApiError),
    ("ctx.visible_events since_ns", lambda v: _in_run(lambda c: c.visible_events(since_ns=v)), int,
     TimestampUnitError),
    ("ctx.visible_events until_ns", lambda v: _in_run(lambda c: c.visible_events(until_ns=v)), int,
     TimestampUnitError),
    ("latency order_delay_ns", lambda v: _in_run(_place, latency_model=_Lat(v), cost_model=NullCostModel()),
     int, LatencyModelError),
    ("cost model", lambda v: _in_run(_place, fill_model=_FillAll(), cost_model=_Cost(v)), float, CostModelError),
    ("account check_order", lambda v: _in_run(_place, account=_Acct(reason=v), cost_model=NullCostModel()),
     str, AccountSocketError),
    ("account forced order", lambda v: _in_run(lambda c: None, account=_Acct(forced=(v,))), OrderRequest,
     AccountSocketError),
    ("source event", lambda v: CoreEngine(_Noop(), [v]).run(), TradeEvent, SourceEventTypeError),
    ("stream name", lambda v: CoreEngine(_Noop(), _Pairs([(v, [bar(T0)])])), str, TypeError),
    ("time_span_ns", lambda v: CoreEngine(_Noop(), [bar(T0)], time_span_ns=v), tuple, TimestampUnitError),
    ("time_span_ns item", lambda v: CoreEngine(_Noop(), [bar(T0)], time_span_ns=(v, T0)), int, TimestampUnitError),
    ("end_time_ns", lambda v: CoreEngine(_Noop(), [bar(T0)], end_time_ns=v), int, TimestampUnitError),
    ("history_limit", lambda v: CoreEngine(_Noop(), [bar(T0)], history_limit=v), int, ValueError),
]


@pytest.mark.parametrize("place, hand, claimed, error", LIAR_ROWS, ids=[r[0] for r in LIAR_ROWS])
def test_an_object_claiming_a_class_is_refused_by_the_places_error_and_runs_nothing(place, hand, claimed, error):
    RAN.clear()
    value = liar(claimed)
    assert isinstance(value, claimed) and not is_a(value, claimed)  # the claim fools isinstance only
    with pytest.raises(Exception) as info:
        hand(value)
    exc = info.value
    assert isinstance(exc, error), f"{place}: {type(exc).__module__}.{type(exc).__qualname__}: {exc}"
    if issubclass(error, CoreError):  # (a stream name and history_limit are TypeError / ValueError by contract)
        assert isinstance(exc, CoreError), f"{place}: a bare {type(exc).__name__}: {exc}"
    assert "Liar" in str(exc) or place in ("OrderRequest.extra pair",), f"{place}: the real type is not named: {exc}"
    assert RAN == [], f"{place}: the object's own methods ran: {RAN}"


def test_an_object_claiming_to_be_a_slice_is_an_index_by_its_real_type():
    """A history answer tells a slice from an index by the real type
    (`slice` cannot be subclassed): an object that only claims to be a
    slice is read as an index, through its `__index__`, once."""
    from bot.bt.core import DeliveredEvents

    RAN.clear()
    got = DeliveredEvents(("a", "b"), first=0, delivered=2)[liar(slice)]  # its __index__ says 1
    assert got == "b" and RAN == [("slice", "__index__")]


def test_the_liar_is_named_by_its_real_type():
    with pytest.raises(OrderApiError, match="Liar"):
        req(size=liar(float))
    with pytest.raises(OrderApiError, match=r"post_only must be a bool, got numpy\.int64"):
        req(post_only=np.int64(1))


# -- numpy scalars: one rule for every place of a kind ------------------------

NUMBER_PLACES = [
    ("OrderRequest.size", lambda v: req(size=v).size),
    ("Fill.price", lambda v: Fill("a", v, 1.0).price),
    ("TradeEvent.price", lambda v: TradeEvent(received_time_ns=T0, price=v, size=1.0, side="buy").price),
    ("as_float", lambda v: as_float(v, "x")),
]
INT_PLACES = [
    ("validate_nanos", lambda v: validate_nanos(v)),
    ("TradeEvent.received_time_ns", lambda v: TradeEvent(received_time_ns=v, price=1.0, size=1.0,
                                                          side="buy").received_time_ns),
    ("history_limit", lambda v: CoreEngine(_Noop(), [bar(T0)], history_limit=v)._history_limit),
    ("as_int", lambda v: as_int(v, "x")),
]
FLAG_PLACES = [
    ("OrderRequest.post_only", lambda v: req(post_only=v).post_only),
    ("OrderRequest.reduce_only", lambda v: req(reduce_only=v).reduce_only),
    ("as_flag", lambda v: as_flag(v, "x")),
]


@pytest.mark.parametrize("value", [np.float64(1.5), np.float32(1.5), np.int64(2), np.int32(2), 2, 1.5])
@pytest.mark.parametrize("place, make", NUMBER_PLACES, ids=[p[0] for p in NUMBER_PLACES])
def test_every_number_place_takes_every_real_number_as_a_float(place, make, value):
    got = make(value)
    assert type(got) is float and got == float(value)


@pytest.mark.parametrize("value", [np.int64(3), np.int32(3), np.uint8(3), 3])
@pytest.mark.parametrize("place, make", INT_PLACES, ids=[p[0] for p in INT_PLACES])
def test_every_int_place_takes_every_integral_number_as_an_int(place, make, value):
    got = make(value)
    assert type(got) is int and got == 3


@pytest.mark.parametrize("value", [np.True_, np.False_, True, False])
@pytest.mark.parametrize("place, make", FLAG_PLACES, ids=[p[0] for p in FLAG_PLACES])
def test_every_flag_place_takes_a_numpy_bool_as_a_bool(place, make, value):
    got = make(value)
    assert type(got) is bool and got is bool(value)


@pytest.mark.parametrize("value", [np.True_, True, "1", None, 1.0 + 0j])
def test_a_number_place_refuses_a_bool_and_non_numbers_with_the_real_type(value):
    with pytest.raises(OrderApiError, match=type_name(value).replace(".", r"\.")):
        req(size=value)


@pytest.mark.parametrize("value", [np.int64(1), 1, 1.0, "True", np.float64(1.0)])
def test_a_flag_place_refuses_numbers_and_text(value):
    with pytest.raises(OrderApiError, match="must be a bool"):
        req(post_only=value)


def test_plain_data_takes_the_same_foreign_scalars_as_the_fields():
    extra = req(extra=(("i", np.int64(3)), ("f", np.float32(0.5)), ("b", np.True_), ("s", np.str_("x")))).extra
    assert [(k, type(v)) for k, v in extra] == [("i", int), ("f", float), ("b", bool), ("s", str)]
    assert scalar(np.bool_(False)) is False
    frozen = freeze([np.int64(1)])
    assert list(frozen) == [1] and type(frozen[0]) is int


def test_a_numpy_bool_subclass_is_read_by_numpy_not_by_itself():
    class Late(np.bool_):
        def __bool__(self):  # would decide its truth when asked
            RAN.append(("Late", "__bool__"))
            return True

    RAN.clear()
    got = req(post_only=Late(False)).post_only
    assert got is False and RAN == []


def test_a_senders_failing_conversion_is_the_places_error():
    class Bad(float):
        pass

    import numbers

    class NotConvertible:
        def __float__(self):
            raise RuntimeError("the sender's code")

    numbers.Real.register(NotConvertible)
    with pytest.raises(OrderApiError, match="RuntimeError"):
        req(size=NotConvertible())
    assert req(size=Bad(2.0)).size == 2.0 and type(req(size=Bad(2.0)).size) is float


def test_a_decimal_is_a_number_only_where_text_numbers_are():
    from decimal import Decimal

    assert TradeEvent(received_time_ns=T0, price=Decimal("1.5"), size=1.0, side="buy").price == 1.5
    with pytest.raises(OrderApiError):
        req(size=Decimal("1.5"))


def test_as_text_and_type_name_read_the_real_type():
    assert as_text(np.str_("ab"), "x") == "ab" and type(as_text(np.str_("ab"), "x")) is str
    assert type_name(np.True_) == "numpy.bool" and type_name(1) == "int"


def test_a_source_event_of_a_class_the_core_does_not_own_is_refused_as_a_source_error():
    """An Event subclass with no event type of its own (or a subclass of a
    core class) is refused by the source check, not by a bare
    AttributeError."""
    from dataclasses import dataclass

    from bot.bt.core import Event

    @dataclass(frozen=True, kw_only=True)
    class Homemade(Event):
        pass

    class Sub(TradeEvent):
        pass

    for ev in (Homemade(received_time_ns=T0), Sub(received_time_ns=T0, price=1.0, size=1.0, side="buy")):
        with pytest.raises(SourceEventTypeError, match="subclass"):
            CoreEngine(_Noop(), [ev]).run()
