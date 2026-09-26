"""Every carrier's every field is a built-in value (i0-r5-01, i0-r4-02).

Round 5 made `OrderRequest.extra` immutable, but the other fields -- and
every field of the reports and events -- were checked by type NAME
(`isinstance`, `in`), which lets a SUBCLASS through: an object of the
sender's own class whose methods run when the receiver uses the field, at
the arrival time, reading the sender's state then. `in` even lets through
an object that is not text at all but answers `==` as it likes.

Now every class that crosses a path (`PATH_CARRIERS`) makes every field
with a values.py function when it is made. These tests do not name
fields: for every carrier and every field they (1) put in a subclass
instance of the field's built-in type (a "live" value whose methods count
their calls and read a shared state) and check that the carrier holds the
built-in type itself, equal to the value given, without having called a
single method of the subclass; (2) put in an object that is not of the
field's type but answers `==` with True, and check that it is refused.
A carrier added without that treatment, or a field added without it,
fails here. A frozen dataclass of the core that is not in the list fails
`test_every_frozen_dataclass_of_the_core_is_a_listed_carrier`.
"""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import pkgutil

import pytest

import bot.bt.core as core
from bot.bt.core import (
    PATH_CARRIERS,
    Ack,
    CancelRequest,
    Canceled,
    CoreError,
    Fill,
    FillNotice,
    FrozenDict,
    FrozenList,
    FrozenSet,
    OrderRequest,
    Reject,
    StateUnknown,
)

from bt0_util import T0
from test_bt0_events import SAMPLES

CALLS = {"n": 0}


def _count(*_a, **_k):
    CALLS["n"] += 1


def _live_class(base: type) -> type:
    """A subclass of `base` whose every operator a receiver could use
    counts a call (and would answer from the sender's state)."""
    names = ["__eq__", "__ne__", "__hash__", "__str__", "__repr__", "__format__", "__len__", "__bool__",
             "__contains__", "__lt__", "__le__", "__gt__", "__ge__", "__add__", "__radd__", "__mul__",
             "__rmul__", "__sub__", "__rsub__", "__truediv__", "__float__", "__int__", "__index__",
             "__getitem__", "startswith", "lower", "encode"]
    body = {}
    for name in names:
        if hasattr(base, name):
            orig = getattr(base, name)

            def method(self, *a, _orig=orig, **k):
                _count()
                return _orig(self, *a, **k)

            body[name] = method
    return type(f"Live{base.__name__.title()}", (base,), body)


LIVE = {t: _live_class(t) for t in (str, float, int)}


class _AnyEq:
    """Not of any field's type; equal to everything."""

    def __eq__(self, other):
        return True

    __hash__ = object.__hash__


def _live(value):
    """The same value, rebuilt from live subclass instances all the way
    down (tuples as tuples of live values)."""
    t = type(value)
    if t is bool or value is None:
        return value
    if t in LIVE:
        return LIVE[t](value)
    if isinstance(value, tuple):
        return tuple(_live(v) for v in value)
    raise AssertionError(f"no live form for {t}")


_BUILTIN = (int, float, str, bool, type(None), tuple, FrozenList, FrozenDict, FrozenSet, frozenset)


def _assert_builtin(value, where: str) -> None:
    assert type(value) in _BUILTIN, f"{where} holds a {type(value).__module__}.{type(value).__qualname__}"
    if isinstance(value, tuple):
        for i, v in enumerate(value):
            _assert_builtin(v, f"{where}[{i}]")


def _samples() -> list:
    """One valid instance of every carrier, every optional field set."""
    return SAMPLES + [
        OrderRequest("buy", "limit", 1.5, price=2.5, client_order_id="c1", time_in_force="IOC",
                     post_only=True, reduce_only=True, trigger_price=3.5, extra=(("k", "v"), ("n", 2))),
        CancelRequest("c1"),
        Ack("c1", "v1"),
        Reject("c1", "no", "cancel"),
        Fill("c1", 100.0, 0.5, "maker"),
        Canceled("c1", "expired"),
        StateUnknown("c1", "timeout", "cancel"),
        FillNotice("c1", 100.0, 0.5, "buy", "maker", venue_time_ns=T0, fee=0.1),
    ]


def _fields(obj) -> dict:
    return {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj) if f.init}


def test_the_samples_cover_every_carrier():
    assert {type(s) for s in _samples()} == set(PATH_CARRIERS)
    assert [c.__name__ for c in PATH_CARRIERS] == core.CORE_CONTRACT["channel_payloads"]["carriers"]


_CASES = [(type(s).__name__, s, name) for s in _samples() for name in _fields(s)]


@pytest.mark.parametrize("cls_name, sample, field", _CASES, ids=[f"{c}.{f}" for c, _, f in _CASES])
def test_a_subclass_value_is_stored_as_the_builtin_value_it_holds(cls_name, sample, field):
    given = _fields(sample)
    if type(given[field]) is bool:
        pytest.skip("bool cannot be subclassed; see the refusal test")
    given[field] = _live(given[field])
    CALLS["n"] = 0
    made = type(sample)(**given)
    assert CALLS["n"] == 0, f"{cls_name}.{field}: a method of the sender's subclass ran while the carrier was made"
    for name, value in _fields(made).items():
        _assert_builtin(value, f"{cls_name}.{name}")
    assert _fields(made) == _fields(sample)
    assert made == sample and hash(made) == hash(sample)


@pytest.mark.parametrize("cls_name, sample, field", _CASES, ids=[f"{c}.{f}" for c, _, f in _CASES])
def test_an_object_that_only_answers_equal_is_refused(cls_name, sample, field):
    given = _fields(sample)
    given[field] = _AnyEq()
    with pytest.raises(CoreError):
        type(sample)(**given)


@pytest.mark.parametrize("sample", _samples(), ids=lambda s: type(s).__name__)
def test_nothing_can_be_attached_to_a_carrier(sample):
    assert not hasattr(sample, "__dict__")
    with pytest.raises(AttributeError):
        object.__setattr__(sample, "attached", "the sender's iterator")


def test_bool_fields_take_a_bool_itself():
    class _LiveBool:
        def __bool__(self):
            _count()
            return True

    for bad in (_LiveBool(), 1, "yes", None):
        for field in ("post_only", "reduce_only"):
            with pytest.raises(CoreError):
                OrderRequest("buy", "limit", 1.0, price=1.0, **{field: bad})


def test_every_frozen_dataclass_of_the_core_is_a_listed_carrier():
    """A new class that crosses a path must be listed (and pass the tests
    above). The one exemption is the strategy's own view of an order: the
    port builds it from carriers and it never crosses a path."""
    exempt = {"OrderView"}
    found = set()
    for info in pkgutil.iter_modules(core.__path__):
        mod = importlib.import_module(f"bot.bt.core.{info.name}")
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != mod.__name__ or not dataclasses.is_dataclass(obj):
                continue
            if obj.__dataclass_params__.frozen and not inspect.isabstract(obj) and name != "Event":
                found.add(name)
    assert found - exempt == {c.__name__ for c in PATH_CARRIERS}


@pytest.mark.parametrize("make", [
    lambda v: OrderRequest("buy", "limit", v, price=1.0),
    lambda v: Fill("c1", v, 1.0),
    lambda v: SAMPLES[0].__class__(received_time_ns=T0, price=v, size=1.0, side="buy"),
], ids=["OrderRequest.size", "Fill.price", "TradeEvent.price"])
def test_a_number_a_float_cannot_hold_is_refused_as_the_carriers_error(make):
    with pytest.raises(CoreError, match="a float can hold"):
        make(10**400)
