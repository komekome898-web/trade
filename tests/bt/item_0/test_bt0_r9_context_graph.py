"""Round 9, the lead's design addendum (round_7/LEAD_DESIGN.md s3.4): the
graph of what a strategy reaches from its context and the graph of the
core's mutable state do not meet, and what the context reaches holds no
mutable object at all.

The walk is by reachability, not by a list of names: `gc.get_referents`
from the context, with no depth limit, not entering classes, functions
(what the context acts through: it reaches the core only by CALLING them)
and modules. A bound method is entered (its `__self__` is state).

Checked at every callback of a run that places, cancels and fills orders,
adopts a forced order, sets timers and drops history (`history_limit`):

1. no object the context reaches is (`is`) one of the core's mutable
   objects -- everything the engine holds, found by the same walk from the
   engine's own attributes (its order book, the port's registry and outbox,
   the history lists and records, the venue ledger, the queue, the source
   merger, the channels, the request / fill lists, the sockets' objects);
2. no object the context reaches is of a mutable kind: a dict, list, set or
   bytearray, an object with an instance dict, or an object one of whose
   slots can be assigned by plain `setattr` (the context itself included).

The adversary that changes everything the strategy reaches before the
result is taken, and compares the result, is
test_bt0_r9_reachable_state_adversary.py (it also enters functions'
closures, which this walk does not: the stricter of the two).

NOT walked (A-10): the interpreter's own objects reached only through a
function (code, globals, closure cells: the adversary file walks the cells);
objects the strategy makes itself.
"""
from __future__ import annotations

import gc
import types

from bot.bt.core import (
    Ack,
    Canceled,
    CoreEngine,
    EventType,
    Fill,
    FundingEvent,
    LiquidationEvent,
    NullCostModel,
    OrderRequest,
    TradeEvent,
)

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
MS = 1_000_000

_NOT_ENTERED = (type, types.FunctionType, types.ModuleType, types.CodeType, types.BuiltinFunctionType,
                types.MethodDescriptorType, types.WrapperDescriptorType, types.MethodWrapperType,
                types.GetSetDescriptorType, types.MemberDescriptorType)


def _enter(obj) -> bool:
    if isinstance(obj, types.BuiltinFunctionType):  # a C method bound to an object is state
        s = getattr(obj, "__self__", None)
        return s is not None and not isinstance(s, types.ModuleType)
    return not isinstance(obj, _NOT_ENTERED)


def _graph(*roots, stop=()) -> dict:
    """id -> object for everything reachable from `roots` by
    gc.get_referents, not entering what `_enter` refuses or `stop`."""
    stop_ids = {id(o) for o in stop}
    seen: dict = {}
    todo = [r for r in roots if _enter(r)]
    while todo:
        obj = todo.pop()
        if id(obj) in seen or id(obj) in stop_ids:
            continue
        seen[id(obj)] = obj
        for ref in gc.get_referents(obj):
            if id(ref) not in seen and _enter(ref):
                todo.append(ref)
    return seen


def _slot_names(obj):
    for cls in type(obj).__mro__:
        slots = cls.__dict__.get("__slots__", ())
        for s in ([slots] if isinstance(slots, str) else slots):
            if s in ("__dict__", "__weakref__"):
                continue
            yield f"_{cls.__name__.lstrip('_')}{s}" if s.startswith("__") and not s.endswith("__") else s


def _mutable(obj) -> str | None:
    """Why `obj` is of a mutable kind, or None."""
    if isinstance(obj, (dict, list, set, bytearray)):
        return type(obj).__name__
    if isinstance(getattr(obj, "__dict__", None), dict):
        return f"{type(obj).__name__} has an instance dict"
    for name in _slot_names(obj):
        try:
            value = object.__getattribute__(obj, name)
        except AttributeError:
            continue
        try:
            setattr(obj, name, value)  # the same value: harmless if it is accepted
        except Exception:  # noqa: BLE001 - refused: not assignable
            continue
        return f"{type(obj).__name__}.{name} can be assigned"
    return None


class _Venue:
    def __init__(self) -> None:
        self.live: list[str] = []

    def on_market_event(self, event, t):
        out = []
        if event.EVENT_TYPE is EventType.TRADE:
            out = [Fill(c, event.price, 1.0, "maker") for c in self.live]
            self.live = []
        return out

    def on_order(self, order, t):
        if order.order_type == "market":
            return (Ack(order.client_order_id), Fill(order.client_order_id, 100.0, order.size, "taker"))
        self.live.append(order.client_order_id)
        return (Ack(order.client_order_id),)

    def on_cancel(self, request, t):
        if request.client_order_id in self.live:
            self.live.remove(request.client_order_id)
        return (Canceled(request.client_order_id, "user"),)


class _Account:
    def __init__(self) -> None:
        self.done = False

    def apply_fill(self, fill):
        pass

    def apply_funding(self, event):
        pass

    def apply_liquidation(self, event):
        pass

    def on_market_event(self, event, t):
        if event.EVENT_TYPE is EventType.LIQUIDATION and not self.done:
            self.done = True
            return [OrderRequest("sell", "market", 1.0)]
        return ()

    def check_order(self, order, t):
        return None


def _events():
    out = []
    for i in range(12):
        out.append(TradeEvent(received_time_ns=T0 + i * SEC, price=100.0 + i, size=1.0, side="buy"))
        if i == 3:
            out.append(FundingEvent(received_time_ns=T0 + i * SEC + 5 * MS, rate=0.0001))
        if i == 6:
            out.append(LiquidationEvent(received_time_ns=T0 + i * SEC + 5 * MS, price=106.0, size=1.0,
                                        side="sell"))
    return out


def test_the_context_graph_meets_no_mutable_state_of_the_core_and_holds_none():
    engines = []
    problems = []
    counts = {"callbacks": 0, "reached": 0}

    class S:
        def __init__(self) -> None:
            self.k = 0

        def on_event(self, event, ctx):
            self.k += 1
            k = self.k
            if k % 3 == 1:
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0 + k, client_order_id=f"o{k}"))
            if k % 3 == 2 and ctx.open_orders():
                ctx.cancel_order(ctx.open_orders()[0].client_order_id)
            if k % 5 == 0:
                ctx.set_timer(ctx.now_ns + SEC, "t")
            ctx.visible_events(n=2)
            ctx.visible_events(EventType.TRADE, n=1)
            eng = engines[0]
            reached = _graph(ctx)
            core = _graph(eng, stop=(eng._strategy,))
            core_mutable = {i for i, o in core.items() if _mutable(o)}
            shared = sorted({type(reached[i]).__name__ for i in set(reached) & core_mutable})
            if shared:
                problems.append((k, "meets the core's mutable state", shared))
            mutable = sorted({why for o in reached.values() for why in [_mutable(o)] if why})
            if mutable:
                problems.append((k, "reaches mutable objects", mutable))
            counts["callbacks"] += 1
            counts["reached"] += len(reached)

    eng = CoreEngine(S(), _events(), fill_model=_Venue(), cost_model=NullCostModel(), account=_Account(),
                     history_limit=2)
    engines.append(eng)
    res = eng.run()
    assert res.fills and res.forced_orders and any(v.cancels_in_flight == 0 for v in res.orders.values())
    assert counts["callbacks"] == res.events_processed > 20 and counts["reached"] > 0
    assert not problems, problems[:5]


def test_the_walk_finds_what_it_should():
    """The walk itself: a bound method's owner and a list are reached and
    judged mutable (a guard on the test, not on the core)."""
    class Holder:
        def m(self):
            return None

    h = Holder()
    got = _graph((h.m, [1]))
    assert any(o is h for o in got.values())
    assert _mutable(h) and _mutable([1]) and _mutable({}) and not _mutable((1, 2)) and not _mutable("x")
