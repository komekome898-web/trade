"""Round 11 (family i0-r8-01 -> i0-r9-02: the core acts, outside a party's
own call, on an object that party made). Written BEFORE the fix (lead
design round_7/LEAD_DESIGN.md s3.3, s3.4, s8.3; round_11/ROOTCAUSE.md B).

The rule under test (round_11/ROOTCAUSE.md B, the contract's
`channel_payloads.ownership` and `lifecycle`): whatever code outside the
core (the strategy, a socket, an input stream) made, the core does not act
on it through its class outside that party's own call -- no method of it,
no attribute read through it, no metaclass descriptor of its class runs --
and the core decides, sends and reports nothing from what the strategy can
reach but the messages of its outbox.

Two grids, each over an input space NOT taken from the implementation:

1. failures (`test_a_failure_s_own_code_never_runs_and_every_later_call_is_refused`):
   every entry point where outside code runs inside a step -- the
   strategy's `on_event`, every method of every socket protocol (listed
   from `interfaces.SOCKETS` by `socket_methods`, not by hand), an input
   stream's `__next__` -- raises, at its first call, an exception of each
   kind of `EXCEPTION_KINDS` (code in `__str__` / `__repr__` / `__format__`
   / `__getattribute__` / `__eq__` + `__hash__` / an `args` property; code
   in what `args` holds; a metaclass whose `__name__` / `__qualname__` /
   `__module__` run code; a class body `__module__` that is an object with
   code; a BaseException that is not an Exception; a subclass of the
   core's own error; a plain exception). Oracle, from the contract's
   `lifecycle` rule: the escaping exception is the original; then every
   later `step()`, `run()` and `result()` raises `EngineFailedError` whose
   `__cause__` and `engine.failure` are the original and whose text names
   the exception's class; and NOTHING of the exception's code runs after it
   was raised. Also: sockets whose metaclass runs code when their class's
   names are read record nothing between the engine's construction and
   the end of `result()`, and `result().models` names them.
2. what the strategy reaches (`test_changing_anything_the_strategy_reaches_changes_nothing_the_core_decides`):
   R = every state object reachable from the context by `gc.get_referents`
   (closures' cells, functions' defaults / keyword defaults / dicts, bound
   methods' `__self__`, containers' items, instance dicts and slots). Every
   object of R is changed by EVERY way its real type offers: for list,
   dict, set, array (and bytearray) every method the type has and its
   immutable counterpart (tuple, mappingproxy, frozenset, bytes) lacks --
   the table is checked against that difference, so a method Python adds
   fails the test until it is classified; a cell's contents set and
   deleted; a function's `__defaults__`, `__kwdefaults__` and `__dict__`;
   every instance attribute and slot set (object.__setattr__) and deleted
   (object.__delattr__). Times (callback numbers of the run): in the
   callback that walked, after its API calls (A: 3/3); in a later callback,
   through kept references (B: walked at 3, changed at 24; D: 13/28, walked
   after history_limit dropped events); late in the run, when
   history_limit has dropped events of three types (C: 24/24). The outbox (found by
   behaviour, as in round 9) and the messages in it are left out: they are
   what the strategy SENDS, the grid of test_bt0_r9_reachable_state_adversary.py.
   Oracle (round 9's, from the rule): the run completes with every
   receiver's record, the delivered stream and the caller's result EQUAL to
   the unattacked run's, or it raises a CoreError (or the strategy's own call
   fails on what it broke) and every record and the delivered stream are a
   PREFIX of the unattacked run's.
   Also: the core's own lists of references to the event copies
   (history.py `HistoryLists._items` / `_overall_items`), which it slices
   when it drops events, are not in R.

NOT in the grids (A-10): ctypes and writing memory; interpreter
introspection (frames, `gc.get_referrers`) used to reach the engine; the
core's CODE (classes, functions' `__code__`, `__globals__`, modules, Enum
members); finalizers (`__del__`, weakref callbacks) of the strategy's
objects, which the interpreter runs whenever it frees them -- inside a step
too (the contract's `scope` states it; they reach only what the strategy
reaches, which grid 2 changes at two times); exceptions raised inside a
socket's call and caught there by the socket itself; an exception's
`__traceback__` / `__context__` (frames: introspection); the
`__class__` swap of what the strategy reaches (test_bt0_r10_strategy_side.py
grid 2); the outbox and its messages (round 9's grid and round 10's message
grid); `sort` with a key that is the strategy's code (the key runs inside
the strategy's own call).
"""
from __future__ import annotations

import array
import gc
import io
import sys
import types
from decimal import Decimal

import pytest

from bot.bt.core import (
    Ack,
    Canceled,
    CancelRequest,
    CoreEngine,
    CoreError,
    EngineFailedError,
    EventType,
    Fill,
    FundingEvent,
    LiquidationEvent,
    OrderRequest,
    TradeEvent,
)
from bot.bt.core.api import OrderState, OrderView
from bot.bt.core.errors import OrderApiError
from bot.bt.core.interfaces import SOCKETS, socket_methods

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
MS = 1_000_000


# --- the run (synthetic, recording every receiver) ----------------------------

def _events():
    out = []
    for i in range(10):
        out.append(TradeEvent(received_time_ns=T0 + i * SEC, price=100.0 + i, size=1.0,
                              side="buy" if i % 2 else "sell"))
        if i == 2:
            out.append(FundingEvent(received_time_ns=T0 + i * SEC + 500 * MS, rate=0.0001, mark_price=101.0))
        if i == 7:
            out.append(LiquidationEvent(received_time_ns=T0 + i * SEC + 500 * MS, price=107.0, size=1.0,
                                        side="sell"))
    return out


class _Rec:
    def __init__(self) -> None:
        self.logs: dict = {}
        self.delivered: list = []

    def log(self, who, *what):
        self.logs.setdefault(who, []).append(repr(what))


class _Venue:
    def __init__(self, rec):
        self.rec, self.live = rec, []

    def on_market_event(self, event, t):
        self.rec.log("venue.market", event, t)
        out = []
        if event.EVENT_TYPE is EventType.TRADE:
            out = [Fill(c, event.price, 1.0, "maker") for c in self.live]
            self.live = []
        return out

    def on_order(self, order, t):
        self.rec.log("venue.order", order, t)
        if order.order_type == "market":
            return (Ack(order.client_order_id, "v"), Fill(order.client_order_id, 100.0, order.size, "taker"))
        self.live.append(order.client_order_id)
        return (Ack(order.client_order_id, "v"),)

    def on_cancel(self, request, t):
        self.rec.log("venue.cancel", request, t)
        if request.client_order_id in self.live:
            self.live.remove(request.client_order_id)
        return (Canceled(request.client_order_id, "user"),)


class _Latency:
    def __init__(self, rec):
        self.rec = rec

    def feed_delay_ns(self, event):
        return 100 * MS

    def order_delay_ns(self, order, sent):
        self.rec.log("latency.order", order, sent)
        return 300 * MS

    def cancel_delay_ns(self, request, sent):
        self.rec.log("latency.cancel", request, sent)
        return 200 * MS

    def notice_delay_ns(self, report, t):
        return 150 * MS


class _Cost:
    def __init__(self, rec):
        self.rec = rec

    def cost(self, fill):
        self.rec.log("cost", fill)
        return 0.001 * fill.price * fill.size


class _Account:
    def __init__(self, rec):
        self.rec, self.forced = rec, False

    def apply_fill(self, fill):
        self.rec.log("account.fill", fill)

    def apply_funding(self, event):
        self.rec.log("account.funding", event)

    def apply_liquidation(self, event):
        self.rec.log("account.liquidation", event)

    def on_market_event(self, event, t):
        if event.EVENT_TYPE is EventType.LIQUIDATION and not self.forced:
            self.forced = True
            return [OrderRequest("sell", "market", 1.0)]
        return ()

    def check_order(self, order, t):
        return None


_BASE_SOCKETS = {"fill_model": _Venue, "latency_model": _Latency, "cost_model": _Cost, "account": _Account}


def _script(k, ctx, now):
    if k == 1:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=99.0, client_order_id="a1"))
        ctx.place_order(OrderRequest("buy", "market", 0.5))
        ctx.set_timer(now + 1200 * MS, "tm")
    elif k == 2:
        ctx.place_order(OrderRequest("sell", "limit", 1.0, price=105.0, client_order_id="a2"))
    elif k == 3:
        ctx.cancel_order("a2")
        ctx.order("a1")
        ctx.open_orders()
        ctx.visible_events(n=3)
    elif k == 4:
        ctx.place_order(OrderRequest("buy", "limit", 2.0, price=98.0, client_order_id="a3"))
    elif k == 5:
        ctx.cancel_order(CancelRequest("a3"))
        ctx.visible_events(EventType.TRADE, n=2)
    elif k == 8:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=97.0, client_order_id="a5"))
        ctx.set_timer(now + 700 * MS, "tm2")
        ctx.visible_events(EventType.TRADE, since_ns=now - 5 * SEC)
    elif k == 10:
        ctx.cancel_order("a5")
        ctx.open_orders()
    elif k == 12:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=96.0, client_order_id="a6"))
        ctx.visible_events(until_ns=now, n=2)
    elif k >= 13:
        ctx.visible_events(EventType.TRADE, n=1)
        ctx.last(EventType.FUNDING)
        ctx.open_orders()


# === grid 1: failures ===========================================================

class _Watch:
    armed = False  # True from the moment the injected exception is raised
    after: list = []  # what of the exception's code ran while armed


def _mark(what):
    if _Watch.armed:
        _Watch.after.append(what)


def _hostile(name):
    """A method that records that it ran (after the raise) and raises."""
    def method(self, *a, **k):
        _mark(name)
        raise RuntimeError(f"the exception's own {name} ran")
    return method


class _StrSub(str):
    """A str subclass whose own methods record (what `args` can hold, and
    what a class body can set `__module__` to)."""
    def __str__(self):
        _mark("StrSub.__str__")
        return "decided by the sender"

    def __repr__(self):
        _mark("StrSub.__repr__")
        return "decided by the sender"

    def __format__(self, spec):
        _mark("StrSub.__format__")
        return "decided by the sender"

    def __eq__(self, other):
        _mark("StrSub.__eq__")
        return True

    def __hash__(self):
        _mark("StrSub.__hash__")
        return 0

    def __len__(self):
        _mark("StrSub.__len__")
        return 0


class _Talker:
    """An object with code in every way of turning it into text."""
    __str__ = _hostile("arg.__str__")
    __repr__ = _hostile("arg.__repr__")
    __format__ = _hostile("arg.__format__")


class _NamingMeta(type):
    """A metaclass whose classes run code when their names (`__name__`,
    `__qualname__`, `__module__`) are read the usual way. (A class body
    cannot hold a `__qualname__` descriptor: `type` refuses it; the
    metaclass's own attribute lookup is the way such code runs.)"""
    def __getattribute__(cls, name):
        if name in ("__name__", "__qualname__", "__module__"):
            _mark(f"meta {name}")
        return type.__getattribute__(cls, name)


def _exc_class(name, base=Exception, ns=None, meta=type):
    body = {"__module__": __name__, "__qualname__": name}
    body.update(ns or {})
    return meta(name, (base,), body)


def _getattribute(self, name):
    _mark(f"__getattribute__ {name}")
    return BaseException.__getattribute__(self, name)


def _eq(self, other):
    _mark("__eq__")
    return self is other


def _hash(self):
    _mark("__hash__")
    return id(self)


def _args_property():
    def get(self):
        _mark("args property")
        return ("decided by the sender",)
    return property(get)


# kind -> (a function making the exception, the class name its text must hold)
EXCEPTION_KINDS = {
    "plain": (lambda: _exc_class("PlainBoom")("plain message 7"), "PlainBoom"),
    "code in __str__": (lambda: _exc_class("StrBoom", ns={"__str__": _hostile("__str__")})("m"), "StrBoom"),
    "code in __repr__": (lambda: _exc_class("ReprBoom", ns={"__repr__": _hostile("__repr__")})("m"), "ReprBoom"),
    "code in __format__": (lambda: _exc_class("FormatBoom", ns={"__format__": _hostile("__format__")})("m"),
                           "FormatBoom"),
    "code in __getattribute__": (lambda: _exc_class("AttrBoom", ns={"__getattribute__": _getattribute})("m"),
                                 "AttrBoom"),
    "code in __eq__ and __hash__": (lambda: _exc_class("EqBoom", ns={"__eq__": _eq, "__hash__": _hash})("m"),
                                    "EqBoom"),
    "code in an args property": (lambda: _exc_class("ArgsBoom", ns={"args": _args_property()})("m"), "ArgsBoom"),
    "args holds an object with code": (lambda: _exc_class("ArgObjBoom")(_Talker()), "ArgObjBoom"),
    "args holds a str subclass": (lambda: _exc_class("ArgStrBoom")(_StrSub("x")), "ArgStrBoom"),
    "args holds several": (lambda: _exc_class("ManyBoom")(1, 2.5, True, "s", None, _Talker(), _StrSub("y")),
                           "ManyBoom"),
    "metaclass names run code": (lambda: _exc_class("MetaBoom", meta=_NamingMeta)("m"), "MetaBoom"),
    "__module__ is an object with code": (
        lambda: _exc_class("ModBoom", ns={"__module__": _StrSub("evil.module"), "__str__": _hostile("__str__")})("m"),
        "ModBoom"),
    "a BaseException, not an Exception": (
        lambda: _exc_class("BaseBoom", base=BaseException, ns={"__str__": _hostile("__str__")})("m"), "BaseBoom"),
    "a subclass of the core's error": (
        lambda: _exc_class("CoreBoom", base=CoreError, ns={"__str__": _hostile("__str__")})("m"), "CoreBoom"),
}


class _Injector:
    """Raises the exception made by `make` at the first call of `target`
    inside a step (`live` is set once the engine is built: a stream is
    read from when the engine is made, which is not a step)."""

    def __init__(self, target, make):
        self.target, self.make = target, make
        self.calls: dict = {}
        self.raised = None
        self.live = False

    def hit(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1
        if self.live and name == self.target and self.raised is None:
            exc = self.make()
            self.raised = exc
            _Watch.armed = True
            raise exc


def _injecting(socket_name, inj):
    """The socket `socket_name` of the run, every method of its protocol
    (listed by `socket_methods`) calling `inj.hit` first."""
    base = _BASE_SOCKETS[socket_name]
    ns = {}
    for m in socket_methods(SOCKETS[socket_name]):
        def make(m=m):
            def method(self, *a, **k):
                inj.hit(f"{socket_name}.{m}")
                return getattr(base, m)(self, *a, **k)
            return method
        ns[m] = make()
    return type(f"Inj{base.__name__}", (base,), ns)


def _entry_points():
    """Every place where code outside the core runs inside a step."""
    points = ["strategy.on_event", "stream.__next__"]
    for name in sorted(SOCKETS):
        points.extend(f"{name}.{m}" for m in socket_methods(SOCKETS[name]))
    return points


class _PlainStrategy:
    def __init__(self, inj):
        self.inj, self.k = inj, 0

    def on_event(self, event, ctx):
        self.k += 1
        _script(self.k, ctx, ctx.now_ns)
        self.inj.hit("strategy.on_event")


def _stream(inj):
    for ev in _events():
        inj.hit("stream.__next__")
        yield ev


def _failing_engine(inj):
    rec = _Rec()
    socks = {name: _injecting(name, inj)(rec) for name in _BASE_SOCKETS}
    eng = CoreEngine(_PlainStrategy(inj), _stream(inj), fill_model=socks["fill_model"],
                     latency_model=socks["latency_model"], cost_model=socks["cost_model"],
                     account=socks["account"], history_limit=2)
    inj.live = True
    return eng


def test_every_entry_point_is_reached_by_the_unfailing_run():
    """A guard on the grid: every entry point is called in the run, so a
    cell of grid 1 never passes because its failure was never raised."""
    inj = _Injector(target=None, make=None)
    _failing_engine(inj).run()
    missing = [p for p in _entry_points() if not inj.calls.get(p)]
    assert not missing, missing


def _cells_1():
    return [(p, k) for p in _entry_points() for k in EXCEPTION_KINDS]


@pytest.mark.parametrize("cell", _cells_1(), ids=lambda c: f"{c[0]}-{c[1]}")
def test_a_failure_s_own_code_never_runs_and_every_later_call_is_refused(cell):
    point, kind = cell
    make, class_name = EXCEPTION_KINDS[kind]
    _Watch.armed, _Watch.after = False, []
    inj = _Injector(point, make)
    eng = _failing_engine(inj)
    escaped = None
    try:
        eng.run()
    except BaseException as exc:  # noqa: BLE001 - the injected one must escape unchanged
        escaped = exc
    try:
        assert inj.raised is not None, "the entry point was not reached"
        assert escaped is inj.raised, "the escaping exception is not the original"
        texts = []
        for call in ("step", "run", "result", "step"):
            refused = None
            try:
                getattr(eng, call)()
            except BaseException as exc:  # noqa: BLE001 - judged below
                refused = exc
            assert type(refused) is EngineFailedError, (call, type(refused))
            assert refused.__cause__ is inj.raised and eng.failure is inj.raised
            texts.append(BaseException.__str__(refused))  # the core's own error: its text is the core's
        assert all(class_name in t for t in texts), texts[0]
        if kind == "plain":
            assert all("plain message 7" in t for t in texts), texts[0]
        assert not _Watch.after, f"the exception's own code ran after it was raised: {_Watch.after[:4]}"
    finally:
        _Watch.armed = False


def test_the_failure_grid_is_the_product_of_its_axes():
    n_sockets = sum(len(socket_methods(p)) for p in SOCKETS.values())
    assert len(_cells_1()) == (2 + n_sockets) * len(EXCEPTION_KINDS)
    assert n_sockets >= 11  # the protocols' methods are listed, not typed in


def test_a_socket_s_class_names_are_read_once_when_the_engine_is_built():
    """result().models names each socket; reading it runs nothing of the
    socket's class (a metaclass whose names run code) after construction."""
    rec = _Rec()
    socks = {}
    for name, base in _BASE_SOCKETS.items():
        cls = _NamingMeta(f"Named{base.__name__}", (base,), {"__module__": __name__,
                                                              "__qualname__": f"Named{base.__name__}"})
        socks[name] = cls(rec)
    _Watch.armed, _Watch.after = False, []
    eng = CoreEngine(_PlainStrategy(_Injector(None, None)), _events(), **socks, history_limit=2)
    _Watch.armed = True
    try:
        res = eng.run()
        again = eng.result()
    finally:
        _Watch.armed = False
    assert not _Watch.after, _Watch.after[:4]
    for name, base in _BASE_SOCKETS.items():
        assert res.models[name] == again.models[name] == f"{__name__}.Named{base.__name__}", res.models


# === grid 2: what the strategy reaches ================================================

_ATOMS = (int, float, complex, str, bytes, bool, type(None), Decimal, range, slice)
_CODE = (type, types.ModuleType, types.CodeType, types.BuiltinFunctionType, types.MethodDescriptorType,
         types.WrapperDescriptorType, types.MethodWrapperType, types.GetSetDescriptorType,
         types.MemberDescriptorType, types.FrameType)


def _module_dicts() -> set:
    return {id(m.__dict__) for m in list(sys.modules.values()) if m is not None and hasattr(m, "__dict__")}


def _walk(root):
    """[(id, object)] reachable from `root`, in a fixed order (depth first,
    referents in the order gc gives them): a function is entered through
    its closure's cells, defaults, keyword defaults and dict (its code,
    globals and annotations are the program); a bound method through its
    `__self__`; everything else through gc.get_referents. Classes, modules,
    code, Enum members and module namespaces are not entered."""
    import enum
    mods = _module_dicts()
    seen: dict = {}
    order = []
    todo = [root]
    while todo:
        obj = todo.pop()
        if id(obj) in seen:
            continue
        if isinstance(obj, _CODE) or isinstance(obj, enum.Enum):
            continue
        if type(obj) is dict and id(obj) in mods:
            continue
        seen[id(obj)] = obj
        order.append(obj)
        if isinstance(obj, types.FunctionType):
            kids = list(obj.__closure__ or ()) + list(obj.__defaults__ or ())
            kids += list((obj.__kwdefaults__ or {}).values()) + [obj.__dict__]
        elif isinstance(obj, types.MethodType):
            kids = [obj.__self__]
        else:
            kids = list(gc.get_referents(obj))
        todo.extend(reversed(kids))
    return order


def _is_state(obj) -> bool:
    if isinstance(obj, _ATOMS) or isinstance(obj, types.MethodType):
        return False
    if type(obj) in (tuple, frozenset):  # immutable containers: their items are walked
        return False
    return True


# every method a mutable built-in type has and its immutable counterpart
# lacks, classified: the ones that change the object, and the ones that only
# read or make a new object (checked against the types themselves below)
MUTABLE_TYPES = {
    list: (tuple, {"__delitem__", "__iadd__", "__imul__", "__setitem__", "append", "clear", "extend", "insert",
                   "pop", "remove", "reverse", "sort"}, {"__reversed__", "copy"}),
    dict: (types.MappingProxyType, {"__delitem__", "__setitem__", "clear", "pop", "popitem", "setdefault",
                                    "update"}, {"fromkeys"}),
    set: (frozenset, {"__iand__", "__ior__", "__isub__", "__ixor__", "add", "clear", "difference_update",
                      "discard", "intersection_update", "pop", "remove", "symmetric_difference_update",
                      "update"}, set()),
    array.array: (bytes, {"__delitem__", "__iadd__", "__imul__", "__setitem__", "append", "byteswap", "extend",
                          "frombytes", "fromfile", "fromlist", "fromunicode", "insert", "pop", "remove",
                          "reverse"},
                  {"__copy__", "__deepcopy__", "__module__", "buffer_info", "itemsize", "tobytes", "tofile",
                   "tolist", "tounicode", "typecode"}),
    bytearray: (bytes, {"__delitem__", "__iadd__", "__imul__", "__setitem__", "append", "clear", "extend",
                        "insert", "pop", "remove", "reverse"}, {"__alloc__", "copy"}),
}


def test_the_mutator_tables_cover_every_method_the_types_add():
    for t, (frozen, changers, readers) in MUTABLE_TYPES.items():
        added = set(dir(t)) - set(dir(frozen))
        assert changers | readers == added, (t.__name__, sorted(added - changers - readers),
                                             sorted((changers | readers) - added))
        assert not changers & readers


def _forged():
    ghost = OrderView(request=OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="ghost"),
                      state=OrderState.FILLED, sent_time_ns=T0, last_update_ns=T0, acked=True,
                      filled_size=1.0, avg_fill_price=1.0, fees=-50.0)
    future = TradeEvent(received_time_ns=T0 + 10_000 * SEC, price=1.0, size=1.0, side="buy")
    return [("None", None), ("future time", T0 + 10_000 * SEC), ("FILLED view", ghost), ("future event", future)]


def _container_calls(obj):
    """(name, zero-argument action) for every changing method of the real
    type of `obj` (MUTABLE_TYPES), with arguments that fit it."""
    t = next((c for c in MUTABLE_TYPES if isinstance(obj, c)), None)
    if t is None:
        return []
    out = []
    changers = sorted(MUTABLE_TYPES[t][1])
    forged = _forged()
    if t is array.array:
        numbers = [T0 + 10_000 * SEC, -1, 0]
        n = array.array.__len__(obj)
        args = {
            "__delitem__": [(0,)] if n else [], "__iadd__": [(array.array(obj.typecode, numbers),)],
            "__imul__": [(0,), (2,)], "__setitem__": [(0, v) for v in numbers] if n else [],
            "append": [(v,) for v in numbers], "byteswap": [()], "extend": [(numbers,)],
            "frombytes": [(array.array(obj.typecode, numbers).tobytes(),)],
            "fromfile": [(io.BytesIO(array.array(obj.typecode, numbers).tobytes()), len(numbers))],
            "fromlist": [(numbers,)], "fromunicode": [("x",)], "insert": [(0, v) for v in numbers],
            "pop": [()] if n else [], "remove": [(array.array.__getitem__(obj, 0),)] if n else [],
            "reverse": [()],
        }
    elif t is list:
        n = list.__len__(obj)
        args = {
            "__delitem__": [(0,)] if n else [], "__iadd__": [([f],) for _k, f in forged], "__imul__": [(0,), (2,)],
            "__setitem__": [(0, f) for _k, f in forged] if n else [], "append": [(f,) for _k, f in forged],
            "clear": [()], "extend": [([f],) for _k, f in forged], "insert": [(0, f) for _k, f in forged],
            "pop": [()] if n else [], "remove": [(list.__getitem__(obj, 0),)] if n else [],
            "reverse": [()], "sort": [()],
        }
    elif t is dict:
        keys = list(dict.keys(obj))
        first = keys[:1]
        args = {
            "__delitem__": [(k,) for k in first], "__setitem__": [(k, f) for k in first + ["ghost"] for _n, f in forged],
            "clear": [()], "pop": [(k,) for k in first], "popitem": [()] if keys else [],
            "setdefault": [("ghost", f) for _n, f in forged],
            "update": [({k: f},) for k in first + ["ghost"] for _n, f in forged],
        }
    elif t is set:
        items = sorted(set.__iter__(obj), key=repr)[:1] if set.__len__(obj) else []
        args = {
            "__iand__": [(set(),)], "__ior__": [({"x"},)], "__isub__": [(set(items),)], "__ixor__": [({"x"},)],
            "add": [("x",)], "clear": [()], "difference_update": [(items,)], "discard": [(i,) for i in items],
            "intersection_update": [((),)], "pop": [()] if items else [], "remove": [(i,) for i in items],
            "symmetric_difference_update": [(["x"],)], "update": [(["x"],)],
        }
    else:  # bytearray
        n = bytearray.__len__(obj)
        args = {m: [((0,) if m in ("__delitem__",) else ())] if n or m in ("clear", "reverse") else []
                for m in changers}
        args.update({"__iadd__": [(b"x",)], "__imul__": [(2,)], "append": [(1,)], "extend": [(b"x",)],
                     "insert": [(0, 1)], "__setitem__": [(0, 1)] if n else []})
    assert set(args) == set(changers), (t.__name__, set(changers) ^ set(args))
    for name in changers:
        for i, a in enumerate(args[name]):
            out.append((f"{t.__name__}.{name}#{i}", lambda name=name, a=a: getattr(t, name)(obj, *a)))
    return out


def _attr_names(obj) -> list[str]:
    names: list[str] = []
    try:
        d = object.__getattribute__(obj, "__dict__")
    except AttributeError:
        d = None
    if type(d) is dict:
        names.extend(sorted(dict.keys(d)))
    for cls in type(obj).__mro__:
        slots = cls.__dict__.get("__slots__", ())
        for s in ([slots] if isinstance(slots, str) else list(slots)):
            if s in ("__dict__", "__weakref__"):
                continue
            if s.startswith("__") and not s.endswith("__"):
                s = f"_{cls.__name__.lstrip('_')}{s}"
            if s not in names:
                names.append(s)
    return names


def _attacks(obj):
    """(name, action) for every way of changing `obj` (module docstring)."""
    out = _container_calls(obj)
    forged = _forged()[:2]  # None and a future time: every attribute set to each, and deleted
    if type(obj) is types.CellType:
        for fname, f in forged:
            out.append((f"cell = {fname}", lambda f=f: setattr(obj, "cell_contents", f)))
        out.append(("del cell", lambda: delattr(obj, "cell_contents")))
        return out
    if isinstance(obj, types.FunctionType):
        out.append(("__defaults__ = None", lambda: setattr(obj, "__defaults__", None)))
        for fname, f in forged:
            out.append((f"__defaults__ = ({fname},)", lambda f=f: setattr(obj, "__defaults__", (f,))))
        out.append(("__kwdefaults__ = {}", lambda: setattr(obj, "__kwdefaults__", {"x": None})))
        out.append(("__dict__[x] = None", lambda: obj.__dict__.__setitem__("x", None)))
        return out
    if isinstance(obj, (list, dict, set, array.array, bytearray)) and type(obj) in MUTABLE_TYPES:
        return out  # a built-in container itself has no attribute to set
    for name in _attr_names(obj):
        for fname, f in forged:
            out.append((f"set .{name} = {fname}", lambda name=name, f=f: object.__setattr__(obj, name, f)))
        out.append((f"del .{name}", lambda name=name: object.__delattr__(obj, name)))
    return out


def _box_ids(ctx) -> set:
    """The outbox (the list that grows by one on place_order, round 9) and
    everything reachable from its messages: what the strategy SENDS."""
    before = {id(o): list.__len__(o) for o in _walk(ctx) if type(o) is list}
    ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="probe-r11"))
    after = {id(o): o for o in _walk(ctx) if type(o) is list}
    grown = [after[i] for i, n in before.items() if i in after and list.__len__(after[i]) == n + 1]
    assert len(grown) == 1, len(grown)
    box = grown[0]
    list.pop(box)  # taking the probe back is not sending it
    return {id(box)} | {id(o) for m in list.__iter__(box) for o in _walk(m)}


TIMINGS = {"A": (3, 3), "B": (3, 24), "C": (24, 24), "D": (13, 28)}


class _Strategy:
    def __init__(self, rec, attack=None, survey=None):
        self.rec, self.k = rec, 0
        self.attack = attack  # (timing, target index, attack index)
        self.survey = survey  # a list to fill with (type name, attack names)
        self.kept = None
        self.outcome = None

    def on_event(self, event, ctx):
        try:
            self._on_event(event, ctx)
        except BaseException as exc:  # noqa: BLE001 - its own call failed on what it broke: marked
            exc._bt0_from_strategy = True
            raise

    def _on_event(self, event, ctx):
        self.rec.delivered.append(repr(event))  # what the core handed over, before any attack
        self.k += 1
        k = self.k
        _script(k, ctx, ctx.now_ns)
        timing = self.attack[0] if self.attack is not None else (self.survey[0] if self.survey else None)
        if timing is None:
            return
        walk_at, attack_at = TIMINGS[timing]
        if k == walk_at:
            box = _box_ids(ctx)
            self.kept = [o for o in _walk(ctx) if _is_state(o) and id(o) not in box]
            if self.survey is not None:
                self.survey[1].extend((type(o).__name__, [a[0] for a in _attacks(o)]) for o in self.kept)
        if self.attack is not None and k == attack_at and self.attack[1] is not None:
            _t, ti, ai = self.attack
            obj = self.kept[ti]
            _name, do = _attacks(obj)[ai]
            try:
                do()
                self.outcome = "applied"
            except Exception as exc:  # noqa: BLE001 - the object refused the change itself
                self.outcome = f"refused at the write: {type(exc).__name__}"


def _run(attack=None, survey=None):
    rec = _Rec()
    strat = _Strategy(rec, attack, survey)
    eng = CoreEngine(strat, _events(), fill_model=_Venue(rec), latency_model=_Latency(rec),
                     cost_model=_Cost(rec), account=_Account(rec), history_limit=2)
    try:
        res = eng.run()
    except BaseException as exc:  # noqa: BLE001 - judged by _judge
        return "raised", exc, rec, strat
    return "ok", _snapshot(res), rec, strat


def _snapshot(res) -> dict:
    return {
        "events_processed": res.events_processed,
        "source_events": res.source_events,
        "order_requests": [repr(r) for r in res.order_requests],
        "cancel_requests": [repr(r) for r in res.cancel_requests],
        "fills": [repr(f) for f in res.fills],
        "orders": sorted((k, repr(v)) for k, v in res.orders.items()),
        "venue_states": sorted(res.venue_states.items()),
        "forced_orders": [repr(r) for r in res.forced_orders],
        "defaults_used": list(res.defaults_used),
        "first_last": (res.first_time_ns, res.last_time_ns),
        "digest": res.delivery_digest,
        "by_stream": sorted(res.source_events_by_stream.items()),
    }


def _prefix(short, long):
    return len(short) <= len(long) and long[:len(short)] == short


def _judge(base, got):
    kind, payload, rec, _s = got
    _bk, bres, brec, _bs = base
    if kind == "ok":
        if payload != bres:
            return f"result differs in {[k for k in bres if payload.get(k) != bres[k]]}"
        if rec.logs != brec.logs:
            return f"receivers differ: {sorted(w for w in set(brec.logs) | set(rec.logs) if rec.logs.get(w) != brec.logs.get(w))}"
        if rec.delivered != brec.delivered:
            return "the delivered stream differs"
        return None
    if not (isinstance(payload, CoreError) or getattr(payload, "_bt0_from_strategy", False)):
        return f"the core itself failed on what the strategy changed: {type(payload).__name__}"
    for who, lst in rec.logs.items():
        if not _prefix(lst, brec.logs.get(who, [])):
            return f"raised {type(payload).__name__}, but {who} saw what the unattacked run did not"
    if not _prefix(rec.delivered, brec.delivered):
        return f"raised {type(payload).__name__}, but the delivered stream is not a prefix"
    return None


def _grid(timing):
    survey: list = []
    _run(survey=(timing, survey))
    return survey


@pytest.mark.parametrize("when", sorted(TIMINGS))
def test_changing_anything_the_strategy_reaches_changes_nothing_the_core_decides(when):
    # the unattacked run walks and finds the outbox the same way (its probe
    # order is taken back), so an attacked run differs from it only by the attack
    base = _run(attack=(when, None, None))
    assert base[0] == "ok", base[1]
    assert base[1] == _run()[1]  # and the walk itself changes nothing
    grid = _grid(when)
    cells = sum(len(names) for _t, names in grid)
    kinds = sorted({t for t, _n in grid})
    print(f"\n[{when}] targets {len(grid)} ({', '.join(kinds)}), cells {cells}")
    assert cells < 100_000  # every cell is run (LEAD_DESIGN s7.2 12)
    bad, ran, refused = [], 0, 0
    for ti, (tname, names) in enumerate(grid):
        for ai, aname in enumerate(names):
            got = _run(attack=(when, ti, ai))
            ran += 1
            if (got[3].outcome or "").startswith("refused"):
                refused += 1
            why = _judge(base, got)
            if why is not None:
                bad.append((tname, aname, why))
    print(f"[{when}] ran {ran}, refused at the write {refused}, broke the rule {len(bad)}")
    assert ran == cells
    assert not bad, "\n".join(map(str, bad[:15])) + f"\n... {len(bad)} in all"


def test_the_grid_reaches_every_kind_it_must():
    """A guard on grid 2: at the late timing the walk reaches the arrays of
    the dropped facts (through a function's defaults), cells, functions,
    the registry (a dict), the history lists and the order views; every
    reached object has at least one attack."""
    grid = _grid("C")
    kinds = {t for t, _n in grid}
    assert {"array", "cell", "function", "dict", "DeliveredList", "OrderView", "_OrderPort"} <= kinds, kinds
    assert all(names for _t, names in grid), [t for t, names in grid if not names]


def test_the_core_s_own_reference_lists_are_not_reached():
    """history.py `HistoryLists` keeps, for the core, lists of references to
    the event copies, which it slices when it drops events, and (round 12)
    its own dicts of the dropped facts' holders and of their pending lists:
    the strategy reaches neither them nor the holder that keeps them.
    (Round 12 rewrote this list: the two dicts of arrays `dropped_seqs` /
    `dropped_recvs` became the dicts `dropped` / `_pending`.)"""
    engines: list = []
    problems: list = []

    class S:
        def on_event(self, event, ctx):
            eng = engines[0]
            lists = eng._side.lists
            own = [lists, lists._overall_items, lists.typed, lists.dropped, lists._pending, eng._side,
                   *lists._items.values(), lists._items]
            reached = {id(o) for o in _walk(ctx)}
            hit = [type(o).__name__ for o in own if id(o) in reached]
            if hit:
                problems.append((event.seq, hit))
            ctx.visible_events(EventType.TRADE, n=1)

    eng = CoreEngine(S(), _events(), history_limit=1)
    engines.append(eng)
    eng.run()
    assert any(eng._history.dropped_count.values())
    assert not problems, problems[:4]


# === grid 3: a plug-in's number whose conversion fails =================================
# (found while fixing grid 1: values.py `_now` described the sender's failed
# conversion with the failure's own __str__; ROOTCAUSE round 11 E)

import numbers  # noqa: E402
import typing  # noqa: E402

from bot.bt.core import CostModelError, LatencyModelError  # noqa: E402

_ERROR_OF_SOCKET = {"latency_model": LatencyModelError, "cost_model": CostModelError}


def _number_points():
    """Every socket method whose answer is a number (read from the
    protocol's return annotation, not typed in): (socket, method, int/float)."""
    out = []
    for name in sorted(SOCKETS):
        for m in socket_methods(SOCKETS[name]):
            ret = typing.get_type_hints(getattr(SOCKETS[name], m)).get("return")
            if ret in (int, float):
                out.append((name, m, ret))
    return out


def _failing_number(kind, want):
    """A number of the numeric tower (registered, so `issubclass` says so)
    whose conversion raises an exception of `kind` (EXCEPTION_KINDS)."""
    make, _name = EXCEPTION_KINDS[kind]

    def convert(self, *a):
        exc = make()
        _Watch.armed = True
        raise exc

    cls = type("FailingNumber", (), {"__int__": convert, "__index__": convert, "__float__": convert,
                                     "__trunc__": convert})
    (numbers.Integral if want is int else numbers.Real).register(cls)
    return cls()


def _cells_3():
    return [(s, m, r, k) for s, m, r in _number_points() for k in EXCEPTION_KINDS]


@pytest.mark.parametrize("cell", _cells_3(), ids=lambda c: f"{c[0]}.{c[1]}-{c[3]}")
def test_a_plug_in_number_whose_conversion_fails_is_refused_by_the_entry_s_error(cell):
    socket_name, method, want, kind = cell
    _Watch.armed, _Watch.after = False, []
    rec = _Rec()
    base = _BASE_SOCKETS[socket_name]
    state = {"given": False}

    def answer(self, *a, **k):
        if not state["given"]:
            state["given"] = True
            return _failing_number(kind, want)
        return getattr(base, method)(self, *a, **k)

    socks = {n: c(rec) for n, c in _BASE_SOCKETS.items()}
    socks[socket_name] = type(f"Bad{base.__name__}", (base,), {method: answer})(rec)
    eng = CoreEngine(_PlainStrategy(_Injector(None, None)), _events(), **socks, history_limit=2)
    raised = None
    try:
        eng.run()
    except BaseException as exc:  # noqa: BLE001 - judged below
        raised = exc
    try:
        assert state["given"], "the socket method was not called"
        if issubclass(type(raised), Exception) or type(raised) is _ERROR_OF_SOCKET[socket_name]:
            # an error of the sender's conversion is the entry's error
            assert type(raised) is _ERROR_OF_SOCKET[socket_name], type(raised)
        else:
            # a BaseException that is not an Exception (an interrupt, an exit)
            # is never turned into a model error: it escapes unchanged
            # (the contract's lifecycle rule) and the engine is FAILED
            assert eng.failure is raised and not issubclass(type(raised), Exception)
            with pytest.raises(EngineFailedError):
                eng.result()
        assert not _Watch.after, f"the failure's own code ran: {_Watch.after[:4]}"
    finally:
        _Watch.armed = False


def test_the_number_grid_is_the_product_of_its_axes():
    points = _number_points()
    assert {(s, m) for s, m, _r in points} == {
        ("latency_model", "feed_delay_ns"), ("latency_model", "order_delay_ns"),
        ("latency_model", "cancel_delay_ns"), ("latency_model", "notice_delay_ns"), ("cost_model", "cost")}
    assert len(_cells_3()) == len(points) * len(EXCEPTION_KINDS)
