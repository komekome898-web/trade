"""Critic, item 0, round 11 (i0-r11-01): the core runs code of a class the
strategy, a socket or a stream wrote while it names that class's type, after
the owner's call returned -- with NO metaclass of theirs.

Round 11 reads a foreign class's names by `type`'s own descriptors
(values.py `class_parts`: "no code of the class, its metaclass or what its
body set __module__ to runs") and describes a failure from its facts
(`exception_text`), and the contract states it (lifecycle: "no code of the
failure ... runs and the refusal is always EngineFailedError";
type_decisions: "no code of the class or its metaclass runs ... a refusal is
the error type of the place it enters"). But `type`'s `__module__`
descriptor LOOKS '__module__' UP in the class's own dict. A class made by
`type()` itself from a plain dict whose first key is an object of the
sender's that hashes like '__module__' has that object's `__eq__` called by
the lookup: the sender's code runs there, and whatever it raises replaces
the refusal.

Grid (every place where the core names a foreign object's type after the
owner's call returned): the strategy's exception (then step / run / result),
an argument of that exception, an outbox message, an outbox request object,
a fill model's report, a stream's event, the account's forced order; and the
same lookup in a dict on the strategy's side: the core's `dict.__setitem__`
into the order registry (engine.py `_show`) with a key of the strategy's that
hashes like the id of its order. Oracle
(the contract's words): the refusal is the entry's error type and the
sender's code ran 0 times outside its own call.

Not in the grid: metaclass __hash__ / __eq__ of a foreign class used as a
dict or tuple lookup key (contract scope carves metaclasses out); the lookup
at construction of the engine (inside the caller's own call).
"""
from __future__ import annotations

import pytest

from bot.bt.core import (AccountSocketError, BarEvent, CoreEngine, EngineFailedError, OrderApiError,
                         SourceEventTypeError, VenueProtocolError)
from bot.bt.core.api import OrderRequest
from bot.bt.core.testing import FixedRateCost, RecordingAccount

T0 = 1_700_000_000_000_000_000
INSIDE = [0]    # > 0 while the owner's own call runs
OUTSIDE: list = []


class _Key:
    """A dict key of the sender's: hashes like '__module__', records every
    comparison made outside the owner's call and raises there."""

    def __hash__(self):
        return hash("__module__")

    def __eq__(self, other):
        if INSIDE[0] <= 0:
            OUTSIDE.append(other)
            raise RuntimeError("the sender's code ran outside its own call")
        return NotImplemented


def _cls(name: str, base: type = object) -> type:
    INSIDE[0] += 1
    try:
        return type(name, (base,), {_Key(): 1, "__module__": "sender_mod"})
    finally:
        INSIDE[0] -= 1


Boom = _cls("Boom", Exception)
Plain = _cls("Plain")


class _Own:
    """Marks a sender's own call."""

    def __enter__(self):
        INSIDE[0] += 1

    def __exit__(self, *exc):
        INSIDE[0] -= 1
        return False


def _bar():
    return BarEvent(received_time_ns=T0, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)


def _outbox(ctx):
    return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]


def _strategy(act):
    class S:
        def on_event(self, ev, ctx):
            with _Own():
                act(ev, ctx)
    return S()


def _raise_boom(ev, ctx):
    raise Boom("x")


def _raise_with_arg(ev, ctx):
    with _Own():
        arg = Plain()
    raise ValueError(arg)


@pytest.fixture(autouse=True)
def _clear():
    OUTSIDE.clear()
    INSIDE[0] = 0
    yield


@pytest.mark.parametrize("act", [_raise_boom, _raise_with_arg], ids=["exception-class", "exception-argument"])
@pytest.mark.parametrize("later", ["step", "run", "result"])
def test_a_failed_engine_describes_the_strategy_s_exception_without_running_its_code(act, later):
    eng = CoreEngine(_strategy(act), [_bar()])
    with pytest.raises((Boom, ValueError)):
        while eng.step():
            pass
    OUTSIDE.clear()
    try:
        getattr(eng, later)()
        got = None
    except BaseException as exc:  # noqa: BLE001 - judged below
        got = exc
    assert OUTSIDE == [], "the strategy's code ran outside on_event"
    assert isinstance(got, EngineFailedError), type(got)


@pytest.mark.parametrize("message", ["message", "request"])
def test_an_outbox_message_of_a_class_of_the_strategy_s_is_refused_without_running_its_code(message):
    def act(ev, ctx):
        box = _outbox(ctx)
        list.append(box, Plain() if message == "message" else ("new", Plain(), 0))
    eng = CoreEngine(_strategy(act), [_bar()])
    with pytest.raises(BaseException) as info:
        eng.run()
    assert OUTSIDE == [], "the strategy's code ran after on_event returned"
    assert isinstance(info.value, OrderApiError), type(info.value)


class _Venue:
    def on_market_event(self, event, t):
        with _Own():
            return (Plain(),)

    def on_order(self, order, t):
        return ()

    def on_cancel(self, request, t):
        return ()


class _ForcingAccount(RecordingAccount):
    def on_market_event(self, event, t):
        with _Own():
            return (Plain(),)


def _stream():
    yield _bar()
    with _Own():
        obj = Plain()
    yield obj


@pytest.mark.parametrize("where", ["fill_model", "account", "stream"])
def test_a_socket_s_or_stream_s_object_of_its_own_class_is_refused_without_running_its_code(where):
    kw = {}
    events = [_bar()]
    if where == "fill_model":
        kw = {"fill_model": _Venue(), "cost_model": FixedRateCost(0.0)}
        want = VenueProtocolError
    elif where == "account":
        kw = {"account": _ForcingAccount()}
        want = AccountSocketError
    else:
        events = _stream()
        want = SourceEventTypeError
    with pytest.raises(BaseException) as info:
        CoreEngine(_strategy(lambda ev, ctx: None), events, **kw).run()
    assert OUTSIDE == [], "the sender's code ran outside its own call"
    assert isinstance(info.value, want), type(info.value)


# ---- the same lookup on the strategy's side: its order registry (a plain dict it reaches) -------------
# The core writes every new view into the registry with dict.__setitem__ after the callback returned
# (engine.py `_show`, "base-type C functions ... never through the objects' own classes"). A key of the
# strategy's that hashes like the id of its next order has its __eq__ run by that write.

class _IdKey:
    def __hash__(self):
        return hash("mine-1")

    def __eq__(self, other):
        if INSIDE[0] <= 0:
            OUTSIDE.append(other)
        return False


def test_the_core_s_write_into_the_order_registry_runs_no_code_of_the_strategy_s():
    from bot.bt.core.testing import ImmediateFillModel

    def act(ev, ctx):
        if ev.seq == 1:
            registry = object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[1]
            dict.__setitem__(registry, _IdKey(), None)
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="mine-1"))
    evs = [BarEvent(received_time_ns=T0 + i, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0) for i in range(3)]
    CoreEngine(_strategy(act), evs, fill_model=ImmediateFillModel(), cost_model=FixedRateCost(0.0)).run()
    assert OUTSIDE == [], "the strategy's code ran outside on_event"
