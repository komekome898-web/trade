"""Child program of test_bt0_r14_process_state.py (round 14, i0-r13-01).

It always runs in a FRESH interpreter: an ABC registration, a class with a
metaclass hook, a thread's decimal context, the int <-> str digit limit and
a renamed numpy attribute cannot be undone, and would change every later
test of the session.

Modes (argv[1:]):
  state <change>    the site battery; then a strategy makes <change> inside
                    its own on_event; then the same battery again. Prints
                    JSON {"before", "after", "hooks_in_core", "applied"}.
  bigint <limit>    every entry that takes an int, with ints just outside
                    int64 and ints too long to print (<limit>: "default" or
                    a digit limit set first). Prints JSON of outcomes.
  nesting <pre>     plain data nested 0..MAX_NESTING+3 containers deep at
                    every entry that takes plain data; the strategy uses
                    <pre> frames of its own before it calls the API.
  equivalence       in a clean process, the core's number and mapping
                    decisions against the ABCs' answers for every class.
"""
from __future__ import annotations

import abc
import collections
import collections.abc
import decimal
import json
import numbers
import os
import sys
import types
from decimal import Decimal
from fractions import Fraction

import numpy as np

import bot.bt.core as core_pkg
from bot.bt.core import BarEvent, CoreEngine, to_nanos, validate_nanos
from bot.bt.core import values as V
from bot.bt.core.api import CancelRequest, OrderRequest
from bot.bt.core.interfaces import Ack, Fill
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

CORE_DIR = os.path.dirname(os.path.abspath(core_pkg.__file__)) + os.sep
T0 = 1_700_000_000_000_000_000
INSIDE = [0]  # > 0 while the CHANGING strategy's own on_event runs
HOOKS_IN_CORE: list = []  # code of the changer that ran with a core frame on the stack, outside its call
KEEP: list = []


def _core_on_stack() -> bool:
    f = sys._getframe(2)
    while f is not None:
        if f.f_code.co_filename.startswith(CORE_DIR):
            return True
        f = f.f_back
    return False


def _note(what: str) -> None:
    if INSIDE[0] <= 0 and _core_on_stack():
        HOOKS_IN_CORE.append(what)


# ---- values ---------------------------------------------------------------------------

class Inherits(numbers.Real):
    """A Python class that IS a real number by its own MRO."""

    def __float__(self):
        return 0.75

    def __repr__(self):
        return "Inherits()"


Inherits.__abstractmethods__ = frozenset()


class RegOnly:
    """A Python class that converts like a number but is one only if someone registers it."""

    def __float__(self):
        return 0.75

    def __int__(self):
        return 3

    def __index__(self):
        return 3

    def __complex__(self):
        return 0.75 + 0j


class Foo:
    """What the changer puts in numpy's names; any code of it that runs is recorded."""

    def __bool__(self):
        _note("Foo.__bool__")
        return False

    def __int__(self):
        _note("Foo.__int__")
        return 0

    def __float__(self):
        _note("Foo.__float__")
        return 0.0

    def __index__(self):
        _note("Foo.__index__")
        return 0


def numpy_scalar_types() -> list:
    """Every numpy scalar type a number, a bool or a time can be (from numpy's own table)."""
    out = {t for t in np.sctypeDict.values()
           if issubclass(t, (np.number, np.bool_, np.datetime64))}
    return sorted(out, key=lambda t: t.__name__)


def _small(t):
    if issubclass(t, np.bool_):
        return t(True)
    if issubclass(t, np.timedelta64):
        return np.timedelta64(3, "ns")
    if issubclass(t, np.datetime64):
        return np.datetime64(3, "ns")
    if issubclass(t, np.integer):
        return t(3)
    return t(0.75)


def _big(t):
    if issubclass(t, np.bool_):
        return t(True)
    if issubclass(t, np.timedelta64):
        return np.timedelta64(T0 + 128, "ns")
    if issubclass(t, np.datetime64):
        return np.datetime64(T0 + 128, "ns")
    if issubclass(t, np.integer):
        try:
            return t(T0 + 128)
        except OverflowError:
            return t(3)
    return t(T0 + 128)


def value_table(kind: str) -> dict:
    vals = {}
    for t in numpy_scalar_types():
        vals[f"numpy.{t.__name__}"] = _small(t) if kind == "small" else _big(t)
    small = kind == "small"
    vals.update({
        "int": 3 if small else T0 + 128,
        "float": 0.75 if small else float(T0 + 128),
        "complex": 0.75 + 0j if small else complex(T0 + 128),
        "bool": True,
        "str": "0.75" if small else str(T0 + 128),
        "Fraction": Fraction(3, 4) if small else Fraction(T0 + 128),
        "Decimal": Decimal("0.75") if small else Decimal(T0 + 128),
        "Inherits": Inherits(),
        "RegOnly": RegOnly(),
        "Foo": Foo(),
        "object": object(),
    })
    return vals


with np.errstate(over="ignore"):  # numpy.float16 of T0 is inf: a value like any other here
    SMALL = value_table("small")
    BIG = value_table("big")


# ---- the sites: every place the core decides a value ----------------------------------

def bar(t, **kw):
    d = dict(received_time_ns=t, open=100.0, high=100.0, low=0.5, close=100.0, volume=1.0)
    d.update(kw)
    return BarEvent(**d)


def _plain(x):
    """What an outcome holds, as JSON (a float by its repr: no rounding in the comparison)."""
    t = type(x)
    if t is float:
        return ["float", float.__repr__(x)]
    if t in (int, str, bool) or x is None:
        return x
    if t in (list, tuple):
        return [_plain(v) for v in x]
    return ["?", t.__name__]


def outcome(fn):
    try:
        return ["ok", _plain(fn())]
    except BaseException as exc:  # noqa: BLE001 - the outcome is what is compared
        return ["raised", type(exc).__name__]


class Cost:
    def __init__(self, v):
        self.v = v

    def cost(self, fill):
        return self.v


class ZeroCost:
    def cost(self, fill):
        return 0.0


class Delay:
    def __init__(self, order=0, feed=0, cancel=0, notice=0):
        self.o, self.f, self.c, self.n = order, feed, cancel, notice

    def feed_delay_ns(self, event):
        return self.f

    def order_delay_ns(self, order, t):
        return self.o

    def cancel_delay_ns(self, req, t):
        return self.c

    def notice_delay_ns(self, report, t):
        return self.n


class PriceFill(ImmediateFillModel):
    def __init__(self, v):
        super().__init__()
        self.v = v

    def on_order(self, order, venue_time_ns):
        coid = order.client_order_id
        return (Ack(coid, "x"), Fill(coid, self.v, order.size, "taker"))


def outbox(ctx):
    return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]


class Placer:
    """Places one order (or does `act`) at its first event; records what it sees."""

    def __init__(self, act=None, **req):
        self.act, self.req, self.done, self.seen = act, req, False, []

    def on_event(self, ev, ctx):
        self.seen.append([ev.EVENT_TYPE.value, ev.received_time_ns, getattr(ev, "price", None)])
        if self.done:
            return
        self.done = True
        if self.act is not None:
            self.act(ctx)
            return
        req = dict(side="buy", order_type="market", size=1.0, client_order_id="o1")
        req.update(self.req)
        ctx.place_order(OrderRequest(**req))


def _run(strategy, events=None, **kw):
    kw.setdefault("fill_model", ImmediateFillModel(100.0))
    kw.setdefault("cost_model", ZeroCost())
    acct = kw.setdefault("account", RecordingAccount())
    CoreEngine(strategy, events if events is not None else [bar(T0), bar(T0 + 10)], **kw).run()
    orders = [[c[1].size, c[1].post_only, c[1].price] for c in acct.calls if c[0] == "check_order"]
    fees = [c[1].fee for c in acct.calls if c[0] == "fill"]
    return [strategy.seen, orders, fees]


def site_fee(v):
    return _run(Placer(), cost_model=Cost(v))


def site_delay(v):
    return _run(Placer(), latency_model=Delay(order=v))


def site_fill_price(v):
    return _run(Placer(), fill_model=PriceFill(v))


def site_size(v):
    return _run(Placer(size=v))


def site_post_only(v):
    return _run(Placer(order_type="limit", price=100.0, post_only=v))


def site_timer_outbox(v):
    return _run(Placer(act=lambda ctx: list.append(outbox(ctx), ("timer", v, "tag"))))


def site_timer_api(v):
    return _run(Placer(act=lambda ctx: ctx.set_timer(v, "tag")))


def site_bar_open(v):
    return bar(T0, open=v).open


def site_bar_time(v):
    return bar(v).received_time_ns


def site_to_nanos(v):
    return to_nanos(v, "ns", plausible=(0, 2 ** 63 - 1))


def site_to_nanos_s(v):
    return to_nanos(v, "s", plausible=(0, 2 ** 63 - 1))


def site_validate(v):
    return validate_nanos(v)


def site_exception_args(v):
    class Raiser:
        def on_event(self, ev, ctx):
            raise RuntimeError(v)

    eng = CoreEngine(Raiser(), [bar(T0)])
    try:
        eng.run()
    except RuntimeError:
        pass
    try:
        eng.run()
    except BaseException as exc:  # noqa: BLE001
        return [type(exc).__name__, str(exc)]
    return "no refusal"


SITES = {
    "fee": (site_fee, SMALL), "delay": (site_delay, SMALL), "fill_price": (site_fill_price, SMALL),
    "size": (site_size, SMALL), "post_only": (site_post_only, SMALL),
    "timer_outbox": (site_timer_outbox, BIG), "timer_api": (site_timer_api, BIG),
    "bar_open": (site_bar_open, SMALL), "bar_time": (site_bar_time, BIG),
    "to_nanos": (site_to_nanos, BIG), "to_nanos_s": (site_to_nanos_s, SMALL),
    "validate": (site_validate, BIG), "exception_args": (site_exception_args, SMALL),
}

# keys whose hashes collide: the core's freeze / settle build dicts and sets of new keys, and a
# collision makes the stored key compare itself with the new one. A FrozenDict hashes as the
# frozenset of its items, so that frozenset collides with it in every process (both orders; in a
# dict and in a set). Made once, before any change (the sender's own dict literal compares too).
_FD = V.FrozenDict({"a": 1})
_TWIN = frozenset({("a", 1)})
assert hash(_FD) == hash(_TWIN)
COLLIDING = {"fd_then_set": {_FD: 1, _TWIN: 2}, "set_then_fd": {_TWIN: 2, _FD: 1},
             "in_a_frozenset": frozenset([_FD, _TWIN]), "in_a_list": [{_FD: 1, _TWIN: 2}]}

TEXT_TIMES = [Decimal("1700000000.123456789"), "1700000000.123456789", 1700000000.5, "abc", "1e30",
              Decimal("1.7e9"), "1700000000123456789", "-0", "NaN", "1e-999999"]


def _shapes():
    bars = [bar(T0), bar(T0 + 10)]
    return {
        "list": list(bars), "tuple": tuple(bars), "dict": {"a": list(bars)},
        "mappingproxy": types.MappingProxyType({"a": list(bars)}),
        "OrderedDict": collections.OrderedDict(a=list(bars)), "generator": (b for b in bars),
    }


def battery() -> dict:
    out = {}
    for name, (site, table) in SITES.items():
        out[name] = {label: outcome(lambda: site(v)) for label, v in table.items()}
    out["time_text"] = {}
    for i, v in enumerate(TEXT_TIMES):
        for unit in ("s", "ms", "us", "ns"):
            out["time_text"][f"{i}:{unit}"] = outcome(lambda: to_nanos(v, unit, plausible=(0, 2 ** 63 - 1)))
    out["events_shape"] = {}
    for label, events in _shapes().items():
        out["events_shape"][label] = outcome(lambda: _run(Placer(act=lambda ctx: None), events=events)[0])
    # a text the core makes anew by encoding and decoding it (values._new_str): a lone surrogate
    out["text"] = {
        "client_order_id": outcome(lambda: _run(Placer(client_order_id="o\ud800"))[1]),
        "timer_tag": outcome(lambda: _run(Placer(act=lambda ctx: ctx.set_timer(T0 + 5, "t\udfff")))[0]),
        "freeze": outcome(lambda: V.freeze(("\ud800x",))[0] == "\ud800x"),
    }
    out["collisions"] = {}
    for label, v in COLLIDING.items():
        out["collisions"][f"extra:{label}"] = outcome(lambda: _run(Placer(extra=(("k", v),)))[1])
        out["collisions"][f"settle:{label}"] = outcome(lambda: len(V.settle(v)))
        out["collisions"][f"freeze:{label}"] = outcome(lambda: len(V.freeze(v)))
        out["collisions"][f"outbox:{label}"] = outcome(
            lambda: _run(Placer(act=lambda ctx: list.append(outbox(ctx), ("timer", T0 + 100, v))))[0])
    return out


# ---- the changes a strategy makes inside its own call ---------------------------------

def abcs() -> list:
    """Every ABC of `numbers` and `collections.abc` (read from the modules)."""
    out = []
    for mod in (numbers, collections.abc):
        for name in sorted(getattr(mod, "__all__", dir(mod))):
            obj = getattr(mod, name, None)
            if isinstance(obj, abc.ABCMeta):
                out.append(f"{mod.__name__}.{name}")
    return out


CHANGES = (
    [f"register:{a}" for a in abcs()] + [f"hook:{a}" for a in abcs()]
    + ["decimal:prec1", "decimal:floor3", "decimal:notraps", "decimal:capitals0", "decimal:emax",
       "digits:640"]
    + [f"numpy_name:{n}" for n in ("bool_", "integer", "floating", "inexact", "number", "generic",
                                   "float32", "int64", "float64", "complexfloating")]
    + ["sys_modules:numpy", "warnings:error", "numpy_seterr:raise", "codecs_error:surrogatepass",
       "codecs_error:strict"]
)


def _resolve(dotted: str):
    mod, _, name = dotted.rpartition(".")
    return getattr(sys.modules[mod], name)


def _every_type() -> list:
    ts = {type(v) for v in list(SMALL.values()) + list(BIG.values())}
    ts |= {list, tuple, dict, types.MappingProxyType, set, frozenset, str, bytes, collections.OrderedDict}
    return sorted(ts, key=lambda t: (t.__module__, t.__qualname__))


def apply(change: str) -> None:
    kind, _, arg = change.partition(":")
    if kind == "register":
        a = _resolve(arg)
        for t in _every_type():
            try:
                a.register(t)
            except (TypeError, RuntimeError):  # a cycle, or a class the ABC refuses
                pass
    elif kind == "hook":
        a = _resolve(arg)

        def sub(cls, other):
            _note(f"__subclasscheck__({arg})")
            return True

        def inst(cls, obj):
            _note(f"__instancecheck__({arg})")
            return True

        meta = type("M", (type(a),), {"__subclasscheck__": sub, "__instancecheck__": inst})
        KEEP.append(meta("Evil", (a,), {}))
        # one registration anywhere clears every ABC's negative cache (so earlier "no" answers
        # do not hide the hook). It is made with an ABC of the changer's own, outside every
        # hierarchy: registering with an ABC above `a` (Sized, for Mapping) would ask the hook
        # itself, which answers "already a subclass", and no registration would happen
        KEEP.append(abc.ABCMeta("Bump", (), {}))
        KEEP[-1].register(type("Fresh", (), {}))
    elif kind == "decimal":
        ctx = decimal.getcontext()
        if arg == "prec1":
            ctx.prec = 1
        elif arg == "floor3":
            ctx.prec, ctx.rounding = 3, decimal.ROUND_FLOOR
        elif arg == "notraps":
            for s in list(ctx.traps):
                ctx.traps[s] = False
        elif arg == "capitals0":
            ctx.capitals = 0
        elif arg == "emax":
            ctx.Emax, ctx.Emin = 5, -5
    elif kind == "digits":
        sys.set_int_max_str_digits(int(arg))
    elif kind == "numpy_name":
        setattr(np, arg, Foo)
    elif kind == "warnings":
        import warnings

        warnings.simplefilter(arg)
    elif kind == "numpy_seterr":
        np.seterr(all=arg)
    elif kind == "codecs_error":
        import codecs

        def handler(exc):
            _note(f"codecs error handler {arg}")
            return ("?", exc.end)

        codecs.register_error(arg, handler)
    elif kind == "sys_modules":
        fake = types.ModuleType("numpy")
        for n in ("bool_", "integer", "floating", "inexact", "number", "generic", "complexfloating"):
            setattr(fake, n, Foo)
        sys.modules["numpy"] = fake
    else:
        raise SystemExit(f"unknown change {change}")


class Changer:
    def __init__(self, change):
        self.change, self.applied = change, False

    def on_event(self, ev, ctx):
        INSIDE[0] += 1
        try:
            if not self.applied:
                apply(self.change)
                self.applied = True
        finally:
            INSIDE[0] -= 1


def mode_state(change: str) -> dict:
    before = battery()
    changer = Changer(change)
    CoreEngine(changer, [bar(T0)]).run()
    after = battery()
    return {"before": before, "after": after, "hooks_in_core": HOOKS_IN_CORE, "applied": changer.applied}


# ---- big ints ---------------------------------------------------------------------------

HUGE = 10 ** 5000
BIGINTS = {"+huge": HUGE, "-huge": -HUGE, "+2**2000": 2 ** 2000, "+2**2001": 2 ** 2001,
           "-2**2001": -(2 ** 2001), "+ref": 2 ** 63, "-ref": -(2 ** 63) - 1}


def _err(fn):
    try:
        fn()
        return ["ok"]
    except BaseException as exc:  # noqa: BLE001
        try:
            text = BaseException.__str__(exc)
        except ValueError as e2:  # the exception's own argument cannot be printed
            text = BaseException.__str__(e2)
        return ["raised", type(exc).__name__, "digit limit" if "Exceeds the limit" in text or "int_max_str_digits" in text else ""]


class Idle:
    def on_event(self, ev, ctx):
        pass


def _inside(call):
    """`call(ctx)` inside the strategy's own call; its refusal is caught there."""
    got = []

    def act(ctx):
        got.append(_err(lambda: call(ctx)))

    _run(Placer(act=act))
    return got[0]


def _latency(which):
    def make(v):
        def act(ctx):
            ctx.place_order(OrderRequest(side="buy", order_type="limit", price=100.0, size=1.0,
                                         client_order_id="o1"))
            ctx.set_timer(T0 + 5, "t")

        class Canceller(Placer):
            def on_event(self, ev, ctx):
                super().on_event(ev, ctx)
                if ev.EVENT_TYPE.value == "clock":
                    ctx.cancel_order("o1")

        return _err(lambda: _run(Canceller(act=act), latency_model=Delay(**{which: v})))
    return make


INT_ENTRIES = {
    "validate_nanos": lambda v: _err(lambda: validate_nanos(v)),
    **{f"to_nanos_{u}": (lambda u: lambda v: _err(lambda: to_nanos(v, u)))(u) for u in ("s", "ms", "us", "ns")},
    "event_received": lambda v: _err(lambda: bar(v)),
    "event_exchange": lambda v: _err(lambda: bar(T0, exchange_time_ns=v)),
    "history_limit": lambda v: _err(lambda: CoreEngine(Idle(), [bar(T0)], history_limit=v)),
    "end_time_ns": lambda v: _err(lambda: CoreEngine(Idle(), [bar(T0)], end_time_ns=v)),
    "time_span_ns": lambda v: _err(lambda: CoreEngine(Idle(), [bar(T0)], time_span_ns=(v, v))),
    "set_timer": lambda v: _inside(lambda ctx: ctx.set_timer(v, "t")),
    "read_n": lambda v: _inside(lambda ctx: ctx.visible_events(n=v)),
    "read_since": lambda v: _inside(lambda ctx: ctx.visible_events(since_ns=v)),
    "read_until": lambda v: _inside(lambda ctx: ctx.visible_events(until_ns=v)),
    "outbox_timer": lambda v: _err(lambda: _run(Placer(act=lambda ctx: list.append(outbox(ctx), ("timer", v, "t"))))),
    "feed_delay": _latency("feed"), "order_delay": _latency("order"),
    "cancel_delay": _latency("cancel"), "notice_delay": _latency("notice"),
    "exception_args": lambda v: ["raised", *site_exception_args(v)[:1], ""],
}


def mode_bigint(limit: str) -> dict:
    if limit != "default":
        sys.set_int_max_str_digits(int(limit))
    return {entry: {label: fn(v) for label, v in BIGINTS.items()} for entry, fn in INT_ENTRIES.items()}


# ---- nesting ----------------------------------------------------------------------------

KINDS = ("tuple", "list", "dict", "frozenset", "set")


def nested(kind: str, depth: int):
    v = 1
    for i in range(depth):
        outer = i == depth - 1
        if kind == "tuple":
            v = (v,)
        elif kind == "list":
            v = [v]
        elif kind == "dict":
            v = {"k": v}
        elif kind == "frozenset" or (kind == "set" and not outer):
            v = frozenset([v])
        else:
            v = {v}
    return v


def _burn(pre: int, fn):
    """Call fn with `pre` frames of the caller's own below it."""
    if pre <= 0:
        return fn()
    return _burn(pre - 1, fn)


def mode_nesting(pre: int) -> dict:
    limit = V.MAX_NESTING
    out = {"MAX_NESTING": limit, "cells": {}}
    for kind in KINDS:
        for depth in range(limit + 4):
            v = nested(kind, depth)
            cell = {}
            cell["freeze"] = _burn(pre, lambda: _err(lambda: V.freeze(v)))
            cell["settle"] = _burn(pre, lambda: _err(lambda: V.settle(v)))
            got = []

            def act(ctx):
                got.append(_burn(pre, lambda: _err(lambda: ctx.place_order(OrderRequest(
                    side="buy", order_type="market", size=1.0, client_order_id="o1", extra=(("k", v),))))))

            cell["extra_run"] = _err(lambda: _run(Placer(act=act)))
            cell["extra"] = got[0] if got else ["not called"]

            def put_request(ctx):
                req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o2")
                object.__setattr__(req, "extra", (("k", v),))
                list.append(outbox(ctx), ("new", req, 0))

            cell["outbox_extra"] = _err(lambda: _run(Placer(act=put_request)))
            cell["timer_tag"] = _err(lambda: _run(Placer(act=lambda ctx: list.append(outbox(ctx), ("timer", T0 + 100, v)))))
            out["cells"][f"{kind}:{depth}"] = cell
    return out


# ---- the clean process: the core's decisions against the ABCs' --------------------------

def _all_classes():
    seen, stack = set(), [object]
    while stack:
        c = stack.pop()
        if id(c) in seen:
            continue
        seen.add(id(c))
        yield c
        try:
            stack.extend(type.__subclasses__(c))
        except TypeError:
            pass


def mode_equivalence() -> dict:
    import pandas  # noqa: F401 - a declared dependency: its classes are in the process too

    numbers_diff, mapping_diff, counted = [], [], [0, 0]
    for c in list(_all_classes()):
        try:
            by_abc = next((conv.__name__ for a, conv in ((numbers.Integral, int), (numbers.Real, float),
                                                          (numbers.Complex, complex)) if issubclass(c, a)), None)
            is_map = issubclass(c, collections.abc.Mapping)
        except Exception:  # noqa: BLE001 - a class whose hooks fail: not a number / mapping here
            continue
        kind = V.number_kind(c)
        mine = None if kind is None else kind.__name__
        if V.is_static(c):
            counted[0] += 1
            if mine != by_abc and not any(m is b for m in V._MRO(c) for b in (int, float, complex)):
                numbers_diff.append([f"{c.__module__}.{c.__qualname__}", by_abc, mine])
        counted[1] += 1
        if V.is_mapping(c) != is_map:
            mapping_diff.append([f"{c.__module__}.{c.__qualname__}", is_map])
    return {"numbers_diff": numbers_diff, "mapping_diff": mapping_diff, "static": counted[0],
            "classes": counted[1]}


if __name__ == "__main__":
    mode, *rest = sys.argv[1:]
    if mode == "state":
        result = mode_state(rest[0])
    elif mode == "bigint":
        result = mode_bigint(rest[0])
    elif mode == "nesting":
        result = mode_nesting(int(rest[0]))
    elif mode == "equivalence":
        result = mode_equivalence()
    elif mode == "changes":
        result = CHANGES
    else:
        raise SystemExit(f"unknown mode {mode}")
    sys.stdout.write(json.dumps(result))
