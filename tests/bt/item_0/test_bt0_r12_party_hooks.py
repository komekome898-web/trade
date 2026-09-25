"""Round 12 (i0-r11-01, i0-r11-03; family i0-r8-01 -> i0-r9-02: the core
acts, outside a party's own call, on something that party made or can
reach). Written BEFORE the fix (lead design round_7/LEAD_DESIGN.md s3.3;
round_12/ROOTCAUSE.md A).

The rule under test (round_12/ROOTCAUSE.md A; the contract's `scope`,
`lifecycle`, `channel_payloads.ownership` and `type_decisions`): outside a
party's own call (the strategy's `on_event`, a socket's method, an input
stream's `__next__`), what the core does with what that party handed over,
raised, or can reach is decided only by objects the core made and no one
else reaches, or by static (C) types -- so NO code that party wrote runs
there, and what it planted changes nothing the core decides. Round 11 stated
the rule as "only base-type C functions" and missed that such functions
consult state the party decides (the keys of a hash table, the hash and `==`
of a class, a buffer export, truth and iteration, a number's conversion).

The input space is built from what a party can plant, NOT from the core's
code paths:

Grid 1 (`test_nothing_a_party_planted_runs_outside_its_call`):
  * ENTRY: every place a party hands the core something inside a step --
    every method of every socket protocol (`interfaces.SOCKETS` /
    `socket_methods`), an input stream's `__next__`, the strategy's
    `on_event` (what it raises, returns, and writes in its outbox).
  * SHAPE, from the DECLARED type of what the entry hands over (the
    protocol's return annotation, `typing.get_type_hints`; `Event` for a
    stream; the outbox's message form for the strategy; any exception for
    every entry): a subclass of the declared type; the declared type
    holding, in one of its fields / items, a subclass of that field's own
    type (or a number class of the numeric tower written in Python); and an
    object unrelated to the declared type.
  * HOOK: every special method a class can define that an operation on an
    object or on a class may call -- listed from the built-in types
    themselves (`HOOKS`: the dunder methods of object, type, int, float,
    complex, str, bytes, tuple, list, dict, set, frozenset, BaseException,
    plus `EXTRA_HOOKS`), each recording when it runs while its party is not
    inside its own call, then answering exactly as the base type does.
  * LEVEL: where the hook sits -- on the planted object's class
    (`class`), on that class's metaclass (`meta`), or as a key in the
    class's own dict that hashes like a name the core could look up there
    (`dict`: one key per name of `LOOKUP_NAMES` -- every hook name, the
    class-attribute names and every field of the core's carriers -- all
    planted at once; each records independently).
  Cells: every (entry, shape) x {class, meta} x (all hooks at once, and
  each hook alone), plus (entry, shape) x dict. Every cell is run
  (LEAD_DESIGN s7.2 12: the count is printed and bounded below 100,000).
  Oracle (the contract's words): no hook ran outside its party's call; and
  the run is EQUAL to the unplanted run (for a shape that carries the
  declared value itself: a subclass of the declared container or scalar
  holding the same value, a field holding the same value in a subclass of
  its type, what an entry declared to answer None returns), or it completes,
  or it is refused with the entry's own error type (a CoreError), after
  which every later `step()` / `run()` / `result()` raises
  `EngineFailedError`; an exception a party raised escapes unchanged and the
  same three calls raise `EngineFailedError` caused by it.

Grid 2 (`test_what_the_strategy_plants_in_what_it_reaches_changes_nothing`):
  R = every object reachable from the context (gc referents; closures'
  cells, functions' defaults, bound methods' `__self__`). Without changing
  any content, the strategy constrains what an operation on R may do: it
  holds a `memoryview` of every object of R that exports a buffer (an
  exported buffer cannot be resized), and puts into every dict and set of R
  a key of its own that hashes like every order id the run uses (read from
  the unplanted run's result: the ids it placed, the forced ones, the ones
  the port names) and like every key already there, whose `__eq__`
  records. Times: the first callback, and late in the run after
  history_limit dropped events. Oracle: the run's result, every receiver's
  record and the delivered stream EQUAL the unplanted run's, and no planted
  key's code ran outside the strategy's own call.

NOT in the grids (A-10): construction hooks (`__new__`, `__init__`,
`__init_subclass__`, `__prepare__`, `__class_getitem__`, `__set_name__`) --
they run when the party builds the object, inside its own call;
`__subclasshook__`, ABC registrations and the metaclass hooks of ABC
subclasses (round 14: the core asks no ABC; grid 1 of
test_bt0_r14_process_state.py sets them for every ABC of numbers and
collections.abc, the contract's `process_state`); finalizers (`__del__`, weakref callbacks: the contract
leaves them out); `__class__` (not a method); ctypes, frames, gc referrers
(interpreter introspection); changing the CONTENT of what the strategy
reaches (round 11's grid 2 and round 9's outbox grid); hooks planted on the
core's own classes (changing the program); `__subclasscheck__` on the
metaclass of an exception a party RAISES -- the interpreter itself asks it
of the exception's class while the exception propagates through any frame
(the caller's, the core's), with no core code involved (shown without the
core: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/
scratchpad/bt/r12_worker/item0_r12_worker_dbg2_interpreter_subclasscheck.py), as it runs finalizers; the core re-raises the
party's exception unchanged (the contract's `lifecycle`). A hook that runs
INSIDE its own party's call (the party calling its own object) is allowed
and not recorded. Hooks on the party object ITSELF (the strategy, a socket,
a stream): the core's call of its method -- the method's lookup included --
is that party's own call (the contract's `scope`, round 10).
"""
from __future__ import annotations

import dataclasses
import gc
import numbers
import types
import typing
from collections.abc import Sequence as AbcSequence

import pytest

from bot.bt.core import (
    Ack,
    AccountSocketError,
    Canceled,
    CancelRequest,
    CoreEngine,
    CoreError,
    CostModelError,
    EngineFailedError,
    EventType,
    EventValidationError,
    Fill,
    FundingEvent,
    LatencyModelError,
    LiquidationEvent,
    OrderApiError,
    OrderRequest,
    SourceEventTypeError,
    TradeEvent,
    VenueProtocolError,
)
from bot.bt.core.contract import PATH_CARRIERS
from bot.bt.core.events import Event
from bot.bt.core.interfaces import SOCKETS, socket_methods

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
MS = 1_000_000

# --- who is inside its own call ------------------------------------------------------

PARTIES = ("strategy", "stream", "fill_model", "latency_model", "cost_model", "account")
_IN = {p: 0 for p in PARTIES}
_ARMED = [False]
_OUTSIDE: list = []


def _hit(party: str, what: str) -> None:
    if _ARMED[0] and _IN[party] <= 0:
        _OUTSIDE.append((party, what))


class _Inside:
    __slots__ = ("party",)

    def __init__(self, party):
        self.party = party

    def __enter__(self):
        _IN[self.party] += 1

    def __exit__(self, *exc):
        _IN[self.party] -= 1
        return False


# --- the hooks, listed from the built-in types themselves ----------------------------

_SOURCES = (object, type, int, float, complex, str, bytes, tuple, list, dict, set, frozenset, BaseException)
NOT_HOOKS = {
    "__new__": "construction: runs inside the party's own call",
    "__init__": "construction",
    "__init_subclass__": "class construction",
    "__prepare__": "class construction",
    "__class_getitem__": "construction of a generic alias",
    "__set_name__": "class construction",
    "__subclasshook__": "ABC machinery, which the core never asks (round 14: test_bt0_r14_process_state.py)",
    "__del__": "finalizers (the contract's scope)",
    "__class__": "not a method",
    "__subclasses__": "a class's own list, never asked of a planted object",
    "__instancecheck__": "only on a metaclass (it is in META_HOOKS)",
    "__subclasscheck__": "only on a metaclass (it is in META_HOOKS)",
}
EXTRA_HOOKS = ("__next__", "__length_hint__", "__getattr__", "__missing__", "__get__", "__index__")


def _dunders() -> set:
    out = set()
    for t in _SOURCES:
        for n in dir(t):
            if n.startswith("__") and n.endswith("__") and callable(getattr(t, n, None)):
                out.add(n)
    return out


HOOKS: tuple = tuple(sorted((_dunders() | set(EXTRA_HOOKS)) - set(NOT_HOOKS)))
META_HOOKS: tuple = tuple(sorted(set(HOOKS) | {"__instancecheck__", "__subclasscheck__"}))
# the metaclass of a RAISED exception: the interpreter asks `__subclasscheck__`
# while the exception propagates (module docstring, "NOT in the grids")
RAISED_META_HOOKS: tuple = tuple(h for h in META_HOOKS if h != "__subclasscheck__")


def _carrier_fields() -> set:
    return {f.name for c in PATH_CARRIERS for f in dataclasses.fields(c)}


LOOKUP_NAMES: tuple = tuple(sorted(set(META_HOOKS) | set(NOT_HOOKS) | _carrier_fields() | {
    "__module__", "__qualname__", "__name__", "__dict__", "__doc__", "__slots__", "__weakref__", "__mro__",
    "__bases__", "__annotations__", "__dataclass_fields__", "__match_args__", "EVENT_TYPE", "args"}))


def _recorder(name: str, base: type, party: str):
    """A method that records (outside its party's call) and then answers as
    `base` answers (or as a type without it: TypeError)."""
    def method(self, *a, **k):
        _hit(party, name)
        f = getattr(base, name, None)
        if f is None:
            raise TypeError(f"{name} is not supported")
        return f(self, *a, **k)
    method.__name__ = name
    return method


def _ns(names, base, party) -> dict:
    ns = {n: _recorder(n, base, party) for n in names}
    if "__eq__" in names and "__hash__" not in names:
        ns["__hash__"] = getattr(base, "__hash__", None)  # defining __eq__ alone would drop hashing
    return ns


class _Key:
    """A key of the party's: hashes like `name`; its `__eq__` records."""
    __slots__ = ("name", "party")

    def __init__(self, name, party):
        self.name, self.party = name, party

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        _hit(self.party, f"key {self.name!r}.__eq__")
        return NotImplemented


_COUNTER = [0]


def hooked(base: type, level: str, hooks, party: str) -> type:
    """A class of the party's deriving from `base`, carrying `hooks` at
    `level` (class / meta / dict)."""
    _COUNTER[0] += 1
    name = f"P{_COUNTER[0]}{base.__name__}"
    body = {"__module__": "party_module", "__qualname__": name}
    if level == "class":
        body.update(_ns(hooks, base, party))
        return type(name, (base,), body)
    if level == "meta":
        mbase = type(base)
        meta = type(f"M{name}", (mbase,), {**_ns(hooks, mbase, party), "__module__": "party_module"})
        return meta(name, (base,), body)
    assert level == "dict"
    keys = {_Key(n, party): 1 for n in LOOKUP_NAMES}
    return type(name, (base,), {**keys, **body})


# --- the run --------------------------------------------------------------------------

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
    def __init__(self):
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
            return [Ack(order.client_order_id, "v"), Fill(order.client_order_id, 100.0, order.size, "taker")]
        self.live.append(order.client_order_id)
        return [Ack(order.client_order_id, "v")]

    def on_cancel(self, request, t):
        self.rec.log("venue.cancel", request, t)
        if request.client_order_id in self.live:
            self.live.remove(request.client_order_id)
        return [Canceled(request.client_order_id, "user")]


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
        return []

    def check_order(self, order, t):
        return None


BASE_SOCKETS = {"fill_model": _Venue, "latency_model": _Latency, "cost_model": _Cost, "account": _Account}


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
        ctx.visible_events(n=0, until_ns=now - 9 * SEC)
        ctx.last(EventType.FUNDING)
        ctx.open_orders()
        ctx.order("a1")


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
        "first_last": (res.first_time_ns, res.last_time_ns),
        "digest": res.delivery_digest,
        "by_stream": sorted(res.source_events_by_stream.items()),
    }


# --- entries and shapes -----------------------------------------------------------------

def _declared(socket: str, method: str):
    return typing.get_type_hints(getattr(SOCKETS[socket], method)).get("return")


def _kind_of(ret) -> str:
    """The declared form of an answer: 'sequence' (Sequence[X]), 'int',
    'float', 'text' (Optional[str]) or 'nothing' (None)."""
    if ret is None or ret is type(None):
        return "nothing"
    if ret in (int, float):
        return ret.__name__
    origin = typing.get_origin(ret)
    if origin is AbcSequence:
        return "sequence"
    if origin is typing.Union and set(typing.get_args(ret)) == {str, type(None)}:
        return "text"
    raise AssertionError(f"an answer form this grid does not list: {ret!r}")  # a new protocol fails here


SHAPES = {
    "sequence": ("list-sub", "tuple-sub", "item-sub", "item-field", "item-unrelated", "unrelated"),
    "int": ("sub", "tower", "unrelated"),
    "float": ("sub", "tower", "unrelated"),
    "text": ("sub", "unrelated"),
    "nothing": ("unrelated",),
    "event": ("sub", "field", "unrelated"),
    "outbox": ("msg-sub", "kind-sub", "payload-sub", "payload-field", "payload-unrelated", "timer-values",
               "unrelated"),
    "returned": ("unrelated",),
    "raised": ("exc", "exc-arg", "base-exc"),
}
# shapes that carry the declared value itself: the run must be EQUAL to the unplanted one
EQUAL = {("sequence", "list-sub"), ("sequence", "tuple-sub"), ("sequence", "item-field"), ("int", "sub"),
         ("float", "sub"), ("nothing", "unrelated"), ("event", "field"), ("returned", "unrelated")}
ENTRY_ERRORS = {
    "fill_model": (VenueProtocolError,),
    "account": (AccountSocketError,),
    "latency_model": (LatencyModelError,),
    "cost_model": (CostModelError,),
    "stream": (SourceEventTypeError, EventValidationError),
    "strategy": (OrderApiError,),
}


def entries() -> list:
    """(party, entry name, form) for every entry, listed from the protocols."""
    out = [("strategy", "strategy.on_event", "outbox"), ("strategy", "strategy.on_event", "returned"),
           ("stream", "stream.__next__", "event")]
    for s in sorted(SOCKETS):
        for m in socket_methods(SOCKETS[s]):
            out.append((s, f"{s}.{m}", _kind_of(_declared(s, m))))
    points = sorted({(p, e) for p, e, _f in out})
    out.extend((p, e, "raised") for p, e in points)
    return out


def _twin(obj, cls):
    """An instance of `cls` (a subclass of type(obj), one of the core's
    slotted dataclasses) with obj's field values."""
    return cls(**{f.name: getattr(obj, f.name) for f in dataclasses.fields(type(obj)) if f.init})


def _field_value(value, level, hooks, party):
    """`value` (a built-in value) as an instance of a party's subclass of
    its type holding the same value; None if the type cannot be
    subclassed (bool, None)."""
    t = type(value)
    if t in (bool, type(None)):
        return None
    return hooked(t, level, hooks, party)(value)


def _tower(value, level, hooks, party, integral):
    """A number class of the numeric tower written in Python (a subclass of
    numbers.Integral / numbers.Real, not registered: registering would stay
    in the ABC for the rest of the session), holding `value`. Its
    conversions answer `value` unless a hook of the cell replaced them (the
    hook then answers as `object` does: TypeError)."""
    cls = hooked(numbers.Integral if integral else numbers.Real, level, hooks, party)

    def as_int(self):
        return int(value)

    def as_float(self):
        return float(value)

    for n, f in (("__index__", as_int), ("__int__", as_int), ("__float__", as_float), ("__trunc__", as_int)):
        if n not in cls.__dict__:
            setattr(cls, n, f)
    cls.__abstractmethods__ = frozenset()
    return cls()


def _unrelated(level, hooks, party):
    return hooked(object, level, hooks, party)()


def _poke_first_field(obj, level, hooks, party):
    """obj (a core carrier) with its first field that a subclass can hold
    replaced -- behind the class's back -- by the same value in a party's
    subclass of the value's type. False if no field can be."""
    for f in dataclasses.fields(type(obj)):
        v = getattr(obj, f.name)
        planted = _field_value(v, level, hooks, party)
        if planted is not None:
            object.__setattr__(obj, f.name, planted)
            return True
    return False


def shape_answer(form, shape, answer, level, hooks, party):
    """The planted answer, or None if this answer cannot carry the shape
    (then a later call is tried)."""
    if form == "sequence":
        items = list(answer)
        if shape == "list-sub":
            return hooked(list, level, hooks, party)(items)
        if shape == "tuple-sub":
            return hooked(tuple, level, hooks, party)(items)
        if shape == "unrelated":
            return _unrelated(level, hooks, party)
        if not items:
            return None
        first = items[0]
        if shape == "item-sub":
            items[0] = _twin(first, hooked(type(first), level, hooks, party))
        elif shape == "item-field":
            if not _poke_first_field(first, level, hooks, party):
                return None
        else:  # item-unrelated
            items[0] = _unrelated(level, hooks, party)
        return items
    if form in ("int", "float"):
        if shape == "sub":
            return hooked(type(answer), level, hooks, party)(answer)
        if shape == "tower":
            return _tower(answer, level, hooks, party, integral=form == "int")
        return _unrelated(level, hooks, party)
    if form == "text":
        if shape == "sub":
            return hooked(str, level, hooks, party)("refused by the party")
        return _unrelated(level, hooks, party)
    if form in ("nothing", "returned"):
        return _unrelated(level, hooks, party)
    raise AssertionError(form)


def shape_event(shape, event, level, hooks, party):
    if shape == "sub":
        return _twin(event, hooked(type(event), level, hooks, party))
    if shape == "field":
        _poke_first_field(event, level, hooks, party)
        return event
    return _unrelated(level, hooks, party)


def shape_exception(shape, level, hooks, party):
    if shape == "exc":
        return hooked(Exception, level, hooks, party)("planted")
    if shape == "base-exc":
        return hooked(BaseException, level, hooks, party)("planted")
    return Exception(_unrelated(level, hooks, party), "text")


def shape_message(shape, now, level, hooks, party):
    if shape == "msg-sub":
        return hooked(tuple, level, hooks, party)(("timer", now + 50 * MS, "planted"))
    if shape == "kind-sub":
        return (hooked(str, level, hooks, party)("timer"), now + 50 * MS, "planted")
    if shape == "payload-sub":
        req = OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="planted-1")
        return ("new", _twin(req, hooked(OrderRequest, level, hooks, party)), now)
    if shape == "payload-field":
        req = OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="planted-2")
        _poke_first_field(req, level, hooks, party)
        return ("new", req, now)
    if shape == "payload-unrelated":
        return ("new", _unrelated(level, hooks, party), now)
    if shape == "timer-values":
        return ("timer", hooked(int, level, hooks, party)(now + 50 * MS), hooked(str, level, hooks, party)("x"))
    return _unrelated(level, hooks, party)


class Plan:
    """One cell: plant `shape` at `level` with `hooks` at the first live
    call of `entry` that can carry it."""

    def __init__(self, party, entry, form, shape, level, hooks):
        self.party, self.entry, self.form, self.shape = party, entry, form, shape
        self.level, self.hooks = level, tuple(hooks)
        self.done = False
        self.raised = None

    def planted_answer(self, name, answer):
        if self.done or name != self.entry or self.form in ("raised", "outbox", "event"):
            return answer
        got = shape_answer(self.form, self.shape, answer, self.level, self.hooks, self.party)
        if got is None:
            return answer
        self.done = True
        return got

    def maybe_raise(self, name):
        if not self.done and name == self.entry and self.form == "raised":
            self.done = True
            self.raised = shape_exception(self.shape, self.level, self.hooks, self.party)
            raise self.raised


def _party_socket(socket, rec, plan, live):
    base = BASE_SOCKETS[socket]
    ns = {}
    for m in socket_methods(SOCKETS[socket]):
        def make(m=m):
            name = f"{socket}.{m}"

            def method(self, *a, **k):
                with _Inside(socket):
                    answer = getattr(base, m)(self, *a, **k)
                    if plan is not None and live[0]:
                        plan.maybe_raise(name)
                        answer = plan.planted_answer(name, answer)
                    return answer
            return method
        ns[m] = make()
    return type(f"Party{base.__name__}", (base,), ns)(rec)


class _Stream:
    def __init__(self, plan, live):
        self.it = iter(_events())
        self.plan, self.live = plan, live

    def __iter__(self):
        return self

    def __next__(self):
        with _Inside("stream"):
            ev = next(self.it)
            plan = self.plan
            if plan is not None and self.live[0] and plan.entry == "stream.__next__" and not plan.done:
                plan.maybe_raise("stream.__next__")
                if plan.form == "event":
                    plan.done = True
                    ev = shape_event(plan.shape, ev, plan.level, plan.hooks, "stream")
            return ev


def _outbox(ctx):
    """The strategy's outbox, found by behaviour (the list that grows by one
    when an order is placed), as round 9 and round 11 find it."""
    def lists(root):
        seen, todo, out = set(), [root], []
        while todo:
            o = todo.pop()
            if id(o) in seen or isinstance(o, (type, types.ModuleType)):
                continue
            seen.add(id(o))
            if type(o) is list:
                out.append(o)
            if isinstance(o, types.FunctionType):
                todo.extend(o.__closure__ or ())
                todo.extend(o.__defaults__ or ())
            elif isinstance(o, types.CellType):
                try:
                    todo.append(o.cell_contents)
                except ValueError:
                    pass
            elif isinstance(o, types.MethodType):
                todo.append(o.__self__)
            else:
                todo.extend(gc.get_referents(o))
        return out

    before = {id(o): (o, list.__len__(o)) for o in lists(ctx)}
    ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="probe-r12"))
    grown = [o for o, n in before.values() if list.__len__(o) == n + 1]
    assert len(grown) == 1, len(grown)
    list.pop(grown[0])  # taking the probe back is not sending it
    return grown[0]


class _Strategy:
    def __init__(self, rec, plan):
        self.rec, self.plan, self.k = rec, plan, 0

    def on_event(self, event, ctx):
        with _Inside("strategy"):
            self.rec.delivered.append(repr(event))
            self.k += 1
            _script(self.k, ctx, ctx.now_ns)
            plan = self.plan
            if plan is None or plan.done or plan.entry != "strategy.on_event" or self.k < 2:
                return None
            plan.maybe_raise("strategy.on_event")
            if plan.form == "outbox":
                plan.done = True
                list.append(_outbox(ctx), shape_message(plan.shape, ctx.now_ns, plan.level, plan.hooks, "strategy"))
                return None
            if plan.form == "returned":
                plan.done = True
                return _unrelated(plan.level, plan.hooks, "strategy")
            return None


def run(plan=None):
    """(outcome, payload, rec, engine): outcome 'ok' (payload = snapshot),
    'raised' (payload = the exception)."""
    rec = _Rec()
    live = [False]
    socks = {s: _party_socket(s, rec, plan, live) for s in BASE_SOCKETS}
    eng = CoreEngine(_Strategy(rec, plan), _Stream(plan, live), **socks, history_limit=2)
    live[0] = True
    _OUTSIDE.clear()
    _ARMED[0] = True
    try:
        try:
            res = eng.run()
            got = ("ok", _snapshot(res), rec, eng)
        except BaseException as exc:  # noqa: BLE001 - judged by the caller
            got = ("raised", exc, rec, eng)
        if got[0] == "raised":
            later = []
            for call in ("step", "run", "result"):
                try:
                    getattr(eng, call)()
                    later.append(None)
                except BaseException as exc:  # noqa: BLE001
                    later.append(exc)
            got = got + (later,)
    finally:
        _ARMED[0] = False
    return got


_BASE: dict = {}


def base_run():
    if "run" not in _BASE:
        got = run(None)
        assert got[0] == "ok", got[1]
        _BASE["run"] = got
    return _BASE["run"]


def judge(plan, got) -> "str | None":
    if _OUTSIDE:
        return f"party code ran outside its call: {sorted(set(_OUTSIDE))[:6]}"
    if plan.form != "returned" and not plan.done:
        return "the entry never carried the shape (the cell tested nothing)"
    base = base_run()
    if (plan.form, plan.shape) in EQUAL:
        if got[0] != "ok":
            return f"refused ({type(got[1]).__name__}: {BaseException.__str__(got[1])[:120]}) where the run must be equal"
        if got[1] != base[1]:
            return f"result differs in {[k for k in base[1] if got[1].get(k) != base[1][k]]}"
        if got[2].logs != base[2].logs or got[2].delivered != base[2].delivered:
            return "a receiver's record or the delivered stream differs"
        return None
    if got[0] == "ok":
        return None
    exc, later = got[1], got[4]
    if plan.form == "raised":
        if exc is not plan.raised:
            return f"the escaping exception is not the planted one: {type(exc).__name__}"
        cause_ok = all(type(x) is EngineFailedError and x.__cause__ is plan.raised for x in later)
        return None if cause_ok else f"later calls: {[type(x).__name__ for x in later]}"
    allowed = ENTRY_ERRORS[plan.party]
    if not isinstance(exc, allowed):
        return f"refused with {type(exc).__name__}, not the entry's error {[a.__name__ for a in allowed]}"
    if not all(type(x) is EngineFailedError for x in later):
        return f"later calls: {[type(x).__name__ for x in later]}"
    return None


def cells() -> list:
    out = []
    for party, entry, form in entries():
        for shape in SHAPES[form]:
            out.append((party, entry, form, shape))
    return out


def test_every_entry_is_reached_and_every_shape_is_carried_by_the_all_hooks_cell():
    """Guard: every cell's entry is called in the unplanted run, and the
    all-hooks cell of every (entry, shape) plants what it says (so no cell
    passes because it planted nothing)."""
    base_run()
    missing = []
    for party, entry, form, shape in cells():
        plan = Plan(party, entry, form, shape, "class", HOOKS)
        run(plan)
        if form != "returned" and not plan.done:
            missing.append((entry, shape))
    assert not missing, missing


def test_the_hook_lists_are_listed_from_the_types():
    assert set(HOOKS) >= {"__eq__", "__hash__", "__bool__", "__len__", "__iter__", "__index__", "__float__",
                          "__str__", "__repr__", "__format__", "__getattribute__", "__setattr__"}
    assert not set(HOOKS) & set(NOT_HOOKS)
    assert len(HOOKS) >= 80, len(HOOKS)


@pytest.mark.parametrize("cell", cells(), ids=lambda c: f"{c[1]}-{c[3]}")
def test_nothing_a_party_planted_runs_outside_its_call(cell):
    party, entry, form, shape = cell
    bad, ran = [], 0
    meta_hooks = RAISED_META_HOOKS if form == "raised" else META_HOOKS
    for level in ("class", "meta", "dict"):
        hooks_of_level = HOOKS if level == "class" else meta_hooks
        subsets = [("all", hooks_of_level)]
        if level != "dict":
            subsets += [(h, (h,)) for h in hooks_of_level]
        for label, hooks in subsets:
            plan = Plan(party, entry, form, shape, level, hooks)
            got = run(plan)
            ran += 1
            why = judge(plan, got)
            if why is not None:
                bad.append((level, label, why))
    assert ran == 3 + len(HOOKS) + len(meta_hooks)
    assert not bad, "\n".join(map(str, bad[:10])) + f"\n... {len(bad)} of {ran}"


def test_the_grid_size_is_the_product_of_its_axes():
    n = sum(3 + len(HOOKS) + len(RAISED_META_HOOKS if c[2] == "raised" else META_HOOKS) for c in cells())
    print(f"\ngrid 1: {len(cells())} (entry, shape) cells, {n} runs")
    assert n < 100_000
    n_sockets = sum(len(socket_methods(p)) for p in SOCKETS.values())
    assert n_sockets >= 11


# === grid 2: plants in what the strategy reaches (no content changed) =====================

def _walk(root) -> list:
    import enum
    seen, order, todo = set(), [], [root]
    while todo:
        o = todo.pop()
        if id(o) in seen or isinstance(o, (type, types.ModuleType, types.CodeType, types.BuiltinFunctionType,
                                           types.MethodDescriptorType, types.WrapperDescriptorType,
                                           types.MethodWrapperType, types.GetSetDescriptorType,
                                           types.MemberDescriptorType, enum.Enum)):
            continue
        seen.add(id(o))
        order.append(o)
        if isinstance(o, types.FunctionType):
            todo.extend(o.__closure__ or ())
            todo.extend(o.__defaults__ or ())
            todo.extend((o.__kwdefaults__ or {}).values())
        elif isinstance(o, types.CellType):
            try:
                todo.append(o.cell_contents)
            except ValueError:
                pass
        elif isinstance(o, types.MethodType):
            todo.append(o.__self__)
        else:
            todo.extend(gc.get_referents(o))
    return order


PLANT_TIMES = {"first": 1, "late": 24}


class _Planter:
    def __init__(self, rec, when, ids):
        self.rec, self.when, self.ids, self.k = rec, when, ids, 0
        self.views: list = []
        self.keys_put = 0

    def on_event(self, event, ctx):
        with _Inside("strategy"):
            self.rec.delivered.append(repr(event))
            self.k += 1
            _script(self.k, ctx, ctx.now_ns)
            if self.when is not None and self.k == PLANT_TIMES[self.when]:
                for o in _walk(ctx):
                    try:
                        self.views.append(memoryview(o))
                    except TypeError:
                        pass
                    t = type(o)
                    if t is dict or t is set:
                        names = set(self.ids) | {k for k in (dict.keys(o) if t is dict else set.__iter__(o))
                                                 if type(k) is str}
                        # the value: one the dict already holds, so the strategy's own reads
                        # of it see nothing of a new kind (no content of a new kind is planted)
                        value = next(iter(dict.values(o)), None) if t is dict else None
                        for n in sorted(names):
                            key = _Key(n, "strategy")
                            if t is dict:
                                dict.__setitem__(o, key, value)
                            else:
                                set.add(o, key)
                            self.keys_put += 1


def _plant_run(when, ids):
    rec = _Rec()
    strat = _Planter(rec, when, ids)
    eng = CoreEngine(strat, _events(), **{s: c(rec) for s, c in BASE_SOCKETS.items()}, history_limit=2)
    _OUTSIDE.clear()
    _ARMED[0] = True
    try:
        res = eng.run()
    finally:
        _ARMED[0] = False
    return _snapshot(res), rec, strat


@pytest.mark.parametrize("when", sorted(PLANT_TIMES))
def test_what_the_strategy_plants_in_what_it_reaches_changes_nothing(when):
    base, brec, _s = _plant_run(None, ())
    ids = set(dict(base["orders"])) | {f"forced-{i}" for i in range(1, 4)} | {f"core-{i}" for i in range(1, 4)}
    got, rec, strat = _plant_run(when, sorted(ids))
    outside = list(_OUTSIDE)
    assert strat.views or strat.keys_put, "the strategy planted nothing"
    print(f"\n[{when}] views held {len(strat.views)}, keys put {strat.keys_put}")
    assert not outside, sorted(set(outside))[:6]
    assert got == base, [k for k in base if got.get(k) != base[k]]
    assert rec.logs == brec.logs and rec.delivered == brec.delivered


def test_the_planter_reaches_the_arrays_and_the_registry():
    """Guard on grid 2: late in the run the walk reaches at least one
    buffer exporter (the dropped facts) and a dict holding order ids."""
    rec = _Rec()
    found: dict = {}

    class S:
        k = 0

        def on_event(self, event, ctx):
            S.k += 1
            _script(S.k, ctx, ctx.now_ns)
            if S.k == PLANT_TIMES["late"]:
                objs = _walk(ctx)
                found["buffers"] = sum(1 for o in objs if _exports(o))
                found["id dicts"] = sum(1 for o in objs if type(o) is dict and "a1" in dict.keys(o))

    CoreEngine(S(), _events(), **{s: c(rec) for s, c in BASE_SOCKETS.items()}, history_limit=2).run()
    assert found["buffers"] >= 1 and found["id dicts"] >= 1, found


def _exports(o) -> bool:
    try:
        memoryview(o).release()
        return True
    except TypeError:
        return False


# === the answer-taking rule, value by value (round 12) ===================================

def _one_run(latency=None, fee=None, forced=None):
    rec = _Rec()
    socks = {s: c(rec) for s, c in BASE_SOCKETS.items()}
    if latency is not None:
        socks["latency_model"].feed_delay_ns = lambda event: latency
    if fee is not None:
        socks["cost_model"].cost = lambda fill: fee
    if forced is not None:
        socks["account"].on_market_event = lambda event, t: forced
    return CoreEngine(_Strategy(rec, None), _events(), **socks, history_limit=2)


def test_a_c_number_class_s_answer_is_taken_and_a_python_number_class_s_is_refused():
    """A number of a static (C) class (numpy's) is converted by its C code
    and taken as the built-in value; a number whose class was written in
    Python is refused with the entry's error and its conversion never
    runs (round 12: its conversion is the plug-in's code, after its call)."""
    np = pytest.importorskip("numpy")
    base = _snapshot(_one_run(latency=100 * MS, fee=0.25).run())
    assert _snapshot(_one_run(latency=np.int64(100 * MS), fee=np.float32(0.25)).run()) == base
    ran = []

    class Py(numbers.Integral):
        def __index__(self):
            ran.append("index")
            return 100 * MS
        __int__ = __index__

    Py.__abstractmethods__ = frozenset()
    with pytest.raises(LatencyModelError, match="convert it"):
        _one_run(latency=Py()).run()

    class PyReal(numbers.Real):
        def __float__(self):
            ran.append("float")
            return 0.25

    PyReal.__abstractmethods__ = frozenset()
    with pytest.raises(CostModelError):
        _one_run(fee=PyReal()).run()
    assert ran == []


@pytest.mark.parametrize("answer", ["generator", "deque", "dict", "str"])
def test_a_sequence_answer_that_is_not_a_list_or_tuple_is_refused(answer):
    """The protocols declare `Sequence[...]`; the core reads a list or a
    tuple by the base type's iterator and asks nothing else of an answer."""
    import collections
    req = OrderRequest("sell", "market", 1.0)
    made = {"generator": lambda: (r for r in [req]), "deque": lambda: collections.deque([req]),
            "dict": lambda: {0: req}, "str": lambda: "x"}[answer]
    eng = _one_run()
    eng._account.on_market_event = lambda event, t: made() if event.EVENT_TYPE is EventType.LIQUIDATION else []
    with pytest.raises(AccountSocketError, match="list or tuple"):
        eng.run()


@pytest.mark.parametrize("entry", sorted({e for _p, e, f in entries() if f == "raised"}))
def test_after_a_raised_exception_escaped_the_later_calls_ask_nothing_of_its_class(entry):
    """The one hook left out of grid 1 for a raised exception -- its
    metaclass's `__subclasscheck__`, which the interpreter asks while the
    exception propagates -- is not asked by the core's later `step()`,
    `run()` and `result()` (they describe the failure from its facts and
    raise EngineFailedError): every hook of META_HOOKS is planted on the
    exception's metaclass and recorded only from the moment the exception
    has escaped `run()`."""
    party = entry.split(".")[0]
    plan = Plan(party, entry, "raised", "exc", "meta", META_HOOKS)
    rec = _Rec()
    live = [False]
    socks = {s: _party_socket(s, rec, plan, live) for s in BASE_SOCKETS}
    eng = CoreEngine(_Strategy(rec, plan), _Stream(plan, live), **socks, history_limit=2)
    live[0] = True
    with pytest.raises(BaseException) as info:
        eng.run()
    assert info.value is plan.raised
    _OUTSIDE.clear()
    _ARMED[0] = True
    try:
        later = []
        for call in ("step", "run", "result"):
            try:
                getattr(eng, call)()
            except EngineFailedError as exc:
                later.append(exc.__cause__ is plan.raised)
    finally:
        _ARMED[0] = False
    assert later == [True, True, True]
    assert _OUTSIDE == [], _OUTSIDE[:6]
