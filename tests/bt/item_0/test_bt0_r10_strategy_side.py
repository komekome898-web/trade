"""Round 10 (i0-r9-02, family i0-r8-01: the core keeps, and later touches,
state the strategy can change without the API). Written BEFORE the fix
(lead design round_7/LEAD_DESIGN.md s3.3, s3.4 and s7.4 20).

The rule under test (round_10/ROOTCAUSE.md B, the contract's
`channel_payloads.ownership`): everything the strategy can reach that
outlives a callback lives in ONE holder of the engine (`_StrategySide`);
the core's own state holds nothing of it; the core touches it only through
base-type C functions on containers it made and reads, of what the
strategy reaches, only the outbox's messages, once per callback, and only
values that need none of the sender's code to be read (it also slices its
own lists of references to the event copies, which the strategy cannot
reach: test_bt0_r11_foreign_objects.py). So, whatever the strategy does to what it
reaches -- including giving an object another class -- its code runs only
inside its own `on_event`, and the core decides, sends and reports the same
(or refuses with a CoreError).

Three grids, each over an input space NOT taken from the implementation:

1. reachability (`test_the_strategy_reaches_nothing_of_the_core_s_own_state`):
   at every callback, R = everything reachable from the context by
   `gc.get_referents` -- closures' cells, bound methods' `__self__`,
   defaults, instance dicts, slots, container items -- and C = everything
   reachable the same way from the engine without entering the
   `_StrategySide` holder or the strategy object (the core's state, found
   by walking, not by names). R and C share no state object; an object
   reached at two callbacks is reached from the holder; the outbox (found by
   behaviour) is in the holder and not in C.
2. class swap (`test_giving_a_reached_object_another_class_runs_no_strategy_code_outside_its_call`):
   every object in R whose `__class__` can be assigned gets a subclass of
   its own class that records every attribute read, write and delete
   (`__getattribute__`, `__setattr__`, `__delattr__`, a data descriptor per
   slot name, which `object.__getattribute__` / `object.__setattr__` also
   run), every method of the class and the implicit dunders (len, [],
   iteration, contains, eq, hash, repr, bool). Times: the callback that
   walked (A), a later one through kept references (B). Oracle: nothing
   recorded while the strategy's `on_event` is not running, and the run's
   result, receivers' records and delivered stream equal the unattacked
   run's (or it raised a CoreError after which they are a prefix).
3. message values (`test_a_message_value_is_read_without_the_sender_s_code`):
   every field of a new order, a cancel and a timer message in the outbox,
   set (after the API call put the message there, before the callback
   returned) to each kind of value: the built-in type itself, a subclass of
   it, a number of the numeric tower whose conversion records that it ran,
   an object that is not plain data, a subclass of it holding a value the
   API refuses; every subclass and tower number records when any of its
   own methods (repr, str, format, eq, hash, conversions) runs. Oracle:
   nothing recorded outside the strategy's `on_event`; the first two have
   exactly the effect of the API call with that value; the others are
   refused with a CoreError before anything is sent.

NOT in the grids (A-10): ctypes and writing memory; interpreter
introspection (frames, `gc.get_referrers`) used to reach the engine; the
core's CODE (classes, functions, modules, Enum members; a function's
`__code__`, `__globals__`); objects the strategy makes itself; objects of a
built-in type whose `__class__` cannot be assigned (dict, list, tuple,
array, int, str, function, cell, method: counted and printed by grid 2 --
their methods are C code, which runs no strategy code); a class change
made while the strategy's own API call runs (inside its call); subclasses
of `numbers` ABCs with a `__subclasshook__` (defining classes changes the
program); the bool fields' subclass kind (bool cannot be subclassed).
"""
from __future__ import annotations

import gc
import numbers
import sys
import types
from decimal import Decimal
from fractions import Fraction

import pytest

from bot.bt.core import (
    Ack,
    Canceled,
    CancelRequest,
    CoreEngine,
    CoreError,
    EventType,
    Fill,
    FundingEvent,
    LiquidationEvent,
    OrderRequest,
    TradeEvent,
)
from bot.bt.core import engine as engine_mod

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
        pass

    def apply_liquidation(self, event):
        pass

    def on_market_event(self, event, t):
        if event.EVENT_TYPE is EventType.LIQUIDATION and not self.forced:
            self.forced = True
            return [OrderRequest("sell", "market", 1.0)]
        return ()

    def check_order(self, order, t):
        return None


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


class _State:
    inside = False  # True while the strategy's on_event runs
    outside_calls: list = []


class _Strategy:
    def __init__(self, rec, extra=None):
        self.rec, self.k, self.extra = rec, 0, extra

    def on_event(self, event, ctx):
        _State.inside = True
        try:
            self.rec.delivered.append(repr(event))
            self.k += 1
            _script(self.k, ctx, ctx.now_ns)
            if self.extra is not None:
                self.extra(self.k, ctx)
        except BaseException as exc:  # noqa: BLE001 - its own call failed: marked, re-raised
            exc._bt0_from_strategy = True
            raise
        finally:
            _State.inside = False


def _run(extra=None, keep_engine=None):
    _State.outside_calls = []
    rec = _Rec()
    eng = CoreEngine(_Strategy(rec, extra), _events(), fill_model=_Venue(rec), latency_model=_Latency(rec),
                     cost_model=_Cost(rec), account=_Account(rec), history_limit=2)
    if keep_engine is not None:
        keep_engine.append(eng)
    try:
        res = eng.run()
    except BaseException as exc:  # noqa: BLE001 - judged by _judge
        return "raised", exc, rec
    return "ok", _snapshot(res), rec


def _snapshot(res):
    return {
        "order_requests": [repr(r) for r in res.order_requests],
        "cancel_requests": [repr(r) for r in res.cancel_requests],
        "fills": [repr(f) for f in res.fills],
        "orders": sorted((k, repr(v)) for k, v in res.orders.items()),
        "venue_states": sorted(res.venue_states.items()),
        "forced": [repr(r) for r in res.forced_orders],
        "digest": res.delivery_digest,
        "events": res.events_processed,
    }


def _prefix(short, long):
    return len(short) <= len(long) and long[:len(short)] == short


def _judge(base, got):
    kind, payload, rec = got
    _bk, bres, brec = base
    if kind == "ok":
        if payload != bres:
            return f"result differs in {[k for k in bres if payload.get(k) != bres[k]]}"
        if rec.logs != brec.logs or rec.delivered != brec.delivered:
            return "receivers or delivered stream differ"
        return None
    if not (isinstance(payload, CoreError) or getattr(payload, "_bt0_from_strategy", False)):
        return f"the core failed on what the strategy changed: {type(payload).__name__}: {payload}"
    for who, lst in rec.logs.items():
        if not _prefix(lst, brec.logs.get(who, [])):
            return f"raised {type(payload).__name__}, but {who} saw what the unattacked run did not"
    if not _prefix(rec.delivered, brec.delivered):
        return "raised, but the delivered stream is not a prefix"
    return None


# --- the walk -----------------------------------------------------------------

_MODULE_DICTS: set = set()


def _module_dicts() -> set:
    return {id(m.__dict__) for m in list(sys.modules.values()) if m is not None and hasattr(m, "__dict__")}


_CODE = (type, types.ModuleType, types.CodeType, types.BuiltinFunctionType, types.MethodDescriptorType,
         types.WrapperDescriptorType, types.MethodWrapperType, types.GetSetDescriptorType,
         types.MemberDescriptorType, types.FrameType)
_ATOMS = (int, float, complex, str, bytes, bool, type(None), Decimal, range, slice)


def _enter(obj) -> bool:
    import enum
    if isinstance(obj, _CODE) or isinstance(obj, enum.Enum):
        return False
    if type(obj) is dict and id(obj) in _MODULE_DICTS:
        return False  # a module's namespace = the program
    return True


def _walk(*roots, stop_types=(), stop=()):
    """id -> object reachable from `roots` by gc.get_referents (a bound
    method's `__self__` included; for a function: its closure's cells,
    defaults, keyword defaults and dict -- not its `__code__`,
    `__globals__` or annotations; not classes or modules), not entering
    objects of `stop_types` or `stop`."""
    global _MODULE_DICTS
    _MODULE_DICTS = _module_dicts()
    stop_ids = {id(o) for o in stop}
    seen: dict = {}
    todo = [r for r in roots]
    while todo:
        obj = todo.pop()
        if id(obj) in seen or id(obj) in stop_ids or not _enter(obj):
            continue
        if stop_types and type(obj) in stop_types:
            continue
        seen[id(obj)] = obj
        if isinstance(obj, types.FunctionType):
            # the state a function holds: its closure's cells, its defaults
            # and its dict (its code, globals and annotations are the program)
            todo.extend(obj.__closure__ or ())
            todo.extend(obj.__defaults__ or ())
            todo.extend((obj.__kwdefaults__ or {}).values())
            todo.append(obj.__dict__)
        elif isinstance(obj, types.MethodType):
            todo.append(obj.__self__)  # what it is bound to is state; its function is the program
        else:
            todo.extend(gc.get_referents(obj))
    return seen


def _is_state(obj) -> bool:
    """Not an atom (a value the interpreter may share), not code (a
    function or method is the program; the state it closes over is in its
    cells, which are walked), not the one object per value (the empty
    tuple)."""
    if isinstance(obj, _ATOMS) or isinstance(obj, (types.FunctionType, types.MethodType)):
        return False
    if type(obj) in (tuple, frozenset) and type(obj)(list(obj)) is obj:
        return False
    return True


def test_the_strategy_reaches_nothing_of_the_core_s_own_state():
    engines: list = []
    problems: list = []
    kept: list = []  # (callback, {id: obj} reached, {id} of the holder's walk) -- refs kept: ids stay unique
    found = {}

    def check(k, ctx):
        eng = engines[0]
        side = eng._side
        assert type(side) is engine_mod._StrategySide
        reached = _walk(ctx)
        core = _walk(eng, stop_types=(engine_mod._StrategySide,), stop=(eng._strategy,))
        holder = _walk(side)
        shared = sorted({type(reached[i]).__name__ for i in set(reached) & set(core) if _is_state(reached[i])})
        if shared:
            problems.append((k, "the context reaches the core's own state", shared))
        if k == 3:
            before = {i: list.__len__(o) for i, o in reached.items() if type(o) is list}
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="probe"))
            after = _walk(ctx)
            grew = [i for i, n in before.items() if list.__len__(after[i]) == n + 1]
            found["outbox"] = grew
            found["outbox_in_holder"] = all(i in holder for i in grew)
            found["outbox_in_core"] = any(i in core for i in grew)
        kept.append((k, reached, set(holder)))
        found["core_has_book"] = any(o is eng._book for o in core.values())

    _run(extra=check, keep_engine=engines)
    assert found["core_has_book"]  # the walk from the engine does find the core's state
    assert len(found["outbox"]) == 1 and found["outbox_in_holder"] and not found["outbox_in_core"], found
    # an object reached at two callbacks outlives a callback: it must be the holder's
    for (k1, r1, _h1), (k2, r2, h2) in zip(kept, kept[1:]):
        lasting = [r2[i] for i in set(r1) & set(r2) if _is_state(r2[i]) and r1[i] is r2[i]]
        outside = sorted({type(o).__name__ for o in lasting if id(o) not in h2})
        if outside:
            problems.append((k2, "reached at two callbacks but not in the holder", outside))
    print(f"\ncallbacks {len(kept)}, reached per callback {min(len(r) for _k, r, _h in kept)}.."
          f"{max(len(r) for _k, r, _h in kept)}")
    assert not problems, problems[:6]


# --- grid 2: class swap -----------------------------------------------------------

def _record(what):
    if not _State.inside:
        _State.outside_calls.append(what)


def _slot_names(cls):
    for c in cls.__mro__:
        slots = c.__dict__.get("__slots__", ())
        for s in ([slots] if isinstance(slots, str) else slots):
            if s in ("__dict__", "__weakref__"):
                continue
            yield f"_{c.__name__.lstrip('_')}{s}" if s.startswith("__") and not s.endswith("__") else s


_DUNDERS = ("__len__", "__getitem__", "__iter__", "__contains__", "__eq__", "__hash__", "__repr__",
            "__bool__", "__lt__", "__index__", "__int__", "__float__", "__str__", "__format__")


def _hook_class(cls):
    ns: dict = {"__slots__": ()}
    for name in set(_slot_names(cls)):
        base = None
        for c in cls.__mro__:
            if name in c.__dict__:
                base = c.__dict__[name]
                break
        if base is None or not hasattr(base, "__get__"):
            continue

        def make(name=name, base=base):
            def fget(self):
                _record(("get", cls.__name__, name))
                return base.__get__(self, cls)

            def fset(self, value):
                _record(("set", cls.__name__, name))
                base.__set__(self, value)

            def fdel(self):
                _record(("del", cls.__name__, name))
                base.__delete__(self)
            return property(fget, fset, fdel)
        ns[name] = make()

    def __getattribute__(self, name):
        _record(("getattr", cls.__name__, name))
        return super(hook, self).__getattribute__(name)

    def __setattr__(self, name, value):
        _record(("setattr", cls.__name__, name))
        return super(hook, self).__setattr__(name, value)

    def __delattr__(self, name):
        _record(("delattr", cls.__name__, name))
        return super(hook, self).__delattr__(name)

    ns.update(__getattribute__=__getattribute__, __setattr__=__setattr__, __delattr__=__delattr__)
    for name in _DUNDERS:
        if any(name in c.__dict__ for c in cls.__mro__ if c is not object):
            def make_d(name=name):
                def dunder(self, *a, **k):
                    _record(("dunder", cls.__name__, name))
                    return getattr(super(hook, self), name)(*a, **k)
                return dunder
            ns[name] = make_d()
    for name, v in [(n, v) for c in reversed(cls.__mro__) if c is not object for n, v in c.__dict__.items()]:
        if isinstance(v, types.FunctionType) and not (name.startswith("__") and name.endswith("__")):
            def make_m(name=name):
                def method(self, *a, **k):
                    _record(("method", cls.__name__, name))
                    return getattr(super(hook, self), name)(*a, **k)
                return method
            ns[name] = make_m()
    hook = type(cls)(f"Hook{cls.__name__}", (cls,), ns)
    return hook


def _swap(obj) -> str:
    cls = type(obj)
    try:
        hook = _hook_class(cls)
        object.__setattr__(obj, "__class__", hook)
    except (TypeError, AttributeError) as exc:
        return f"not assignable ({type(exc).__name__})"
    return "swapped"


TIMINGS = {"A": (3, 3), "B": (3, 8), "C": (12, 12), "D": (3, 12)}


def _survey(walk_at):
    got = {}

    def extra(k, ctx):
        if k == walk_at:
            got["targets"] = [(type(o).__name__, o) for o in _walk(ctx).values() if _is_state(o)]
    _run(extra=extra)
    return [name for name, _o in got["targets"]]


@pytest.mark.parametrize("when", sorted(TIMINGS))
def test_giving_a_reached_object_another_class_runs_no_strategy_code_outside_its_call(when):
    base = _run()
    assert base[0] == "ok", base[1]
    walk_at, at = TIMINGS[when]
    names = _survey(walk_at)
    bad = []
    tried = {"swapped": 0, "not assignable": {}, "swapped types": set()}
    for i in range(len(names)):
        kept = {}

        def extra(k, ctx, i=i):
            if k == walk_at:
                kept["targets"] = [o for o in _walk(ctx).values() if _is_state(o)]
            if k == at:
                obj = kept["targets"][i]
                kept["outcome"] = _swap(obj)
                kept["type"] = type(obj).__name__
        got = _run(extra=extra)
        outcome = kept.get("outcome", "not reached")
        if outcome == "swapped":
            tried["swapped"] += 1
            tried["swapped types"].add(names[i])
        else:
            tried["not assignable"][names[i]] = tried["not assignable"].get(names[i], 0) + 1
        if _State.outside_calls:
            bad.append((names[i], "strategy code ran outside on_event", _State.outside_calls[:3]))
            continue
        why = _judge(base, got)
        if why is not None:
            bad.append((names[i], why))
    print(f"\n[{when}] targets {len(names)}, swapped {tried['swapped']} "
          f"({', '.join(sorted(tried['swapped types']))}), "
          f"not assignable {sorted(tried['not assignable'].items())}")
    # the strategy's side objects of every kind were among them
    assert {"StrategyContext", "EventWindow", "_OrderPort", "DeliveredList", "OrderView"} <= tried["swapped types"]
    assert not bad, "\n".join(map(str, bad[:12])) + f"\n... {len(bad)} in all"


# --- grid 3: message values ------------------------------------------------------------

CONVERTED: list = []


class _TowerReal(numbers.Real):
    """A number of the numeric tower whose conversion records that it ran."""

    def __init__(self, v):
        self.v = v

    def __float__(self):
        CONVERTED.append(("float", _State.inside))
        return float(self.v)

    def __int__(self):
        CONVERTED.append(("int", _State.inside))
        return int(self.v)

    __index__ = __int__

    def __trunc__(self):
        return int(self.v)

    def __floor__(self):
        return int(self.v)

    def __ceil__(self):
        return int(self.v)

    def __round__(self, n=None):
        return round(self.v, n)

    def __floordiv__(self, o):
        return NotImplemented

    __rfloordiv__ = __mod__ = __rmod__ = __lt__ = __le__ = __floordiv__

    def __add__(self, o):
        return NotImplemented

    __radd__ = __neg__ = __pos__ = __abs__ = __mul__ = __rmul__ = __truediv__ = __rtruediv__ = __add__
    __pow__ = __rpow__ = __eq__ = __add__
    __hash__ = object.__hash__


class _TowerIntegral(_TowerReal, numbers.Integral):
    def __and__(self, o):
        return NotImplemented

    __rand__ = __or__ = __ror__ = __xor__ = __rxor__ = __lshift__ = __rlshift__ = __and__
    __rshift__ = __rrshift__ = __invert__ = __and__


def _recording(base):
    """A subclass of a built-in type whose own methods (repr, str, format,
    eq, hash, and the conversions) record that they ran, then answer as the
    base type."""
    ns = {}
    for name in ("__repr__", "__str__", "__format__", "__eq__", "__ne__", "__hash__", "__int__", "__float__",
                 "__index__", "__bool__", "__len__", "__iter__", "__getitem__", "__lt__"):
        if hasattr(base, name):
            def make(name=name):
                def method(self, *a):
                    CONVERTED.append((f"{base.__name__}.{name}", _State.inside))
                    return getattr(base, name)(self, *a)
                return method
            ns[name] = make()
    return type(f"Rec{base.__name__}", (base,), ns)


_Str, _Float, _Int, _Tuple = _recording(str), _recording(float), _recording(int), _recording(tuple)


# field -> (a valid built-in value, its subclass form or None, a tower
# number, a subclass form of a value the API refuses or None); every
# subclass records when one of its own methods runs
NEW_FIELDS = {
    "side": ("sell", _Str("sell"), _TowerReal(1), _Str("up")),
    "order_type": ("market", _Str("market"), _TowerReal(1), _Str("")),
    "size": (2.0, _Float(2.0), _TowerReal(2.0), _Float(-1.0)),
    "price": (95.5, _Float(95.5), _TowerReal(95.5), _Float(0.0)),
    "client_order_id": ("m9", _Str("m9"), _TowerReal(9), _Str("forced-9")),
    "time_in_force": ("IOC", _Str("IOC"), _TowerReal(1), _Str("")),
    "post_only": (True, None, _TowerIntegral(1), None),
    "reduce_only": (True, None, _TowerIntegral(1), None),
    "trigger_price": (90.0, _Float(90.0), _TowerReal(90.0), _Float(-1.0)),
    "extra": ((("k", 1),), _Tuple((("k", 1),)), (("k", _TowerReal(1)),), _Tuple(((_Str(""), 1),))),
}
KINDS = ("builtin", "subclass", "tower", "not plain", "subclass refused")
TIMES = (3, 12)


def _box_of(ctx):
    """The outbox, found by behaviour: the list that grows by one when
    place_order is called (walking the context's closures)."""
    before = {i: list.__len__(o) for i, o in _walk(ctx).items() if type(o) is list}
    ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="probe-box"))
    after = _walk(ctx)
    [box] = [after[i] for i, n in before.items() if list.__len__(after[i]) == n + 1]
    list.pop(box)  # taking a message back is not sending it (round 9's rule)
    return box


def _value(field, kind):
    ok, sub, tower, bad = NEW_FIELDS[field]
    return {"builtin": ok, "subclass": sub, "tower": tower, "not plain": object(), "subclass refused": bad}[kind]


def _cells():
    out = []
    for at in TIMES:
        for field in NEW_FIELDS:
            for kind in KINDS:
                if (kind == "subclass" and NEW_FIELDS[field][1] is None
                        or kind == "subclass refused" and NEW_FIELDS[field][3] is None):
                    continue
                out.append(("new", field, kind, at))
        for kind in KINDS:
            out.append(("cancel", "client_order_id", kind, at))
        for field in ("at_ns", "tag"):
            for kind in KINDS:
                if not (field == "tag" and kind == "subclass refused"):  # every str is a tag
                    out.append(("timer", field, kind, at))
    return out


def _cancel_value(kind):
    return {"builtin": "a1", "subclass": _Str("a1"), "tower": _TowerReal(1), "not plain": object(),
            "subclass refused": _Str("")}[kind]


def _timer_value(field, kind, now):
    if field == "at_ns":
        v = now + 300 * MS
        return {"builtin": v, "subclass": _Int(v), "tower": _TowerIntegral(v), "not plain": object(),
                "subclass refused": _Int(now - 1)}[kind]
    return {"builtin": "mt", "subclass": _Str("mt"), "tower": _TowerReal(1), "not plain": object(),
            "subclass refused": None}[kind]


@pytest.mark.parametrize("cell", _cells(), ids=lambda c: "-".join(map(str, c)))
def test_a_message_value_is_read_without_the_sender_s_code(cell):
    what, field, kind, at = cell
    CONVERTED.clear()

    def changed(k, ctx):
        if k != at:
            return
        box = _box_of(ctx)
        if what == "new":
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="m1"))
            msg = list.__getitem__(box, -1)
            object.__setattr__(msg[1], field, _value(field, kind))
        elif what == "cancel":
            ctx.cancel_order("a1")
            msg = list.__getitem__(box, -1)
            object.__setattr__(msg[1], "client_order_id", _cancel_value(kind))
        else:
            ctx.set_timer(ctx.now_ns + 300 * MS, "mt")
            at_ns, tag = ctx.now_ns + 300 * MS, "mt"
            if field == "at_ns":
                at_ns = _timer_value(field, kind, ctx.now_ns)
            else:
                tag = _timer_value(field, kind, ctx.now_ns)
            list.__setitem__(box, -1, ("timer", at_ns, tag))

    def via_api(k, ctx):
        if k != at:
            return
        if what == "new":
            fields = dict(side="buy", order_type="limit", size=1.0, price=95.0, client_order_id="m1")
            fields[field] = _value(field, kind)
            ctx.place_order(OrderRequest(**fields))
        elif what == "cancel":
            ctx.cancel_order(_cancel_value(kind))
        else:
            if field == "at_ns":
                ctx.set_timer(_timer_value(field, kind, ctx.now_ns), "mt")
            else:
                ctx.set_timer(ctx.now_ns + 300 * MS, _timer_value(field, kind, ctx.now_ns))

    got = _run(extra=changed)
    outside = [c for c in CONVERTED if not c[1]]
    assert not outside, f"the sender's conversion ran outside its call: {outside}"
    if kind in ("builtin", "subclass"):
        want = _run(extra=via_api)
        if want[0] != "ok":  # the value is refused by the API itself: the message must be refused too
            assert got[0] == "raised" and isinstance(got[1], CoreError), got[:2]
            return
        assert got[0] == "ok", got[1]
        assert got[1] == want[1] and got[2].logs == want[2].logs and got[2].delivered == want[2].delivered
    else:  # a tower number, not plain data, or a value the API refuses: refused before anything is sent
        base = _run()
        assert got[0] == "raised" and isinstance(got[1], CoreError), got[:2]
        assert _judge(base, got) is None


def test_the_message_grid_is_the_product_of_its_axes():
    n_new = sum(3 + (NEW_FIELDS[f][1] is not None) + (NEW_FIELDS[f][3] is not None) for f in NEW_FIELDS)
    assert len(_cells()) == len(TIMES) * (n_new + len(KINDS) + 2 * len(KINDS) - 1)
