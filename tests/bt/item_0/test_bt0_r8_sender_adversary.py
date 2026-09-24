"""Round 8 (i0-r7-02, the family i0-r4-02 -> i0-r5-01 -> i0-r7-02): what
crosses a path is an object the core BUILT, and nothing a sender holds
reaches a receiver -- checked by an adversary, written BEFORE the fix
(lead design round_7/LEAD_DESIGN.md s3.1, s3.3).

Rounds 4, 5 and 7 each fixed one member of a list of "values that may be
passed on as they are" and the critic found the next hole in the list
(round 7: `Fraction` in the list, and its slots can be assigned). The
tests here do not read any list of the core. They take the space of what
a sender can hand over and attack everything reachable from it:

* unit grid: every carrier class (`PATH_CARRIERS`) x every field x every
  kind of value a sender can put there (the built-in type made fresh, a
  subclass of it, numpy's, Fraction / Decimal and their subclasses,
  numeric text, containers of every shape, the core's own frozen
  containers). A kind the field refuses is counted and skipped (nothing
  crossed). For each accepted one: (a) the carrier's object graph and
  the sender's share no object -- the graph is what the interpreter says
  each object references (`gc.get_referents`), classes left out, and an
  object the interpreter itself keeps one of per value (asked by building
  it twice: small ints, empty and one-character strings, None, True,
  False, the empty tuple) is not sharing; (b) every object of the
  carrier's graph is of a type the core builds; (c) after the sender
  changes everything reachable from what it handed over -- list / dict /
  set contents, every slot and instance attribute (`object.__setattr__`,
  frozen or not), `__class__` swapped to a subclass that lies -- the
  carrier reads what it read when it was made.
* engine run: every path and every receiver on it -- strategy -> latency
  model, account, fill model, the result; fill model -> latency model,
  cost model, account, strategy, the result; data source -> latency
  model, fill model, account, strategy; account (a forced order) -> fill
  model, strategy, the result; a timer tag -> strategy. Every sender
  attacks what it sent, later (before the receiver reads it); every
  receiver attacks what it received (a receiver is a sender to no one:
  another receiver of the same thing must not see it). Each receiver's
  graph is disjoint from the sender's and from every other receiver's,
  and reads what was sent.

NOT in the lists (A-10): ctypes and writing memory; interpreter
introspection used to reach the CORE's own state (call stack, gc of the
engine); classes, functions and Enum members (module constants: one
object each by design; changing one changes the program); a thread changing an object while the core builds from it (the
core is single-threaded and runs no sender code while it reads a
carrier's slots); an object that `gc.get_referents` does not show
(nothing of the core's own types is such).
"""
from __future__ import annotations

import dataclasses
import enum
import gc
import pickle
import types
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from bt0_util import find

from bot.bt.core.api import _OrderPort

from bot.bt.core import (
    PATH_CARRIERS,
    Ack,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    CancelRequest,
    Canceled,
    ClockEvent,
    CoreEngine,
    CoreError,
    EventType,
    Fill,
    FillNotice,
    FrozenDict,
    FrozenList,
    FrozenSet,
    FundingEvent,
    LiquidationEvent,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderRequest,
    OrderStateUnknownEvent,
    Reject,
    StateUnknown,
    TradeEvent,
)

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


# -- the sender's kinds of value ------------------------------------------------

class StrSub(str):
    pass


class FloatSub(float):
    pass


class IntSub(int):
    pass


class ComplexSub(complex):
    pass


class BytesSub(bytes):
    pass


class DecSub(Decimal):
    pass


class FracSub(Fraction):
    pass


def _fresh_str(v: str) -> str:
    return "".join([c for c in v])  # a new object (unless the interpreter keeps one per value)


def _fresh_int(v: int) -> int:
    return int(str(v))


def _fresh_float(v: float) -> float:
    return float(repr(v))


def _kinds(v):
    """Every kind of value a sender can hand over for a field whose
    baseline value is `v` (a fresh object each call)."""
    if isinstance(v, bool) or v is None:
        yield "same", lambda: v
        if isinstance(v, bool):
            yield "numpy.bool_", lambda: np.bool_(v)
        return
    if isinstance(v, str):
        yield "str", lambda: _fresh_str(v)
        yield "StrSub", lambda: StrSub(v)
        yield "numpy.str_", lambda: np.str_(v)
        return
    if isinstance(v, int):
        yield "int", lambda: _fresh_int(v)
        yield "IntSub", lambda: IntSub(v)
        yield "numpy.int64", lambda: np.int64(v)
        return
    if isinstance(v, float):
        yield "float", lambda: _fresh_float(v)
        yield "FloatSub", lambda: FloatSub(v)
        yield "Fraction", lambda: Fraction(v)
        yield "FracSub", lambda: FracSub(Fraction(v))
        yield "Decimal", lambda: Decimal(repr(v))
        yield "DecSub", lambda: DecSub(repr(v))
        yield "numpy.float64", lambda: np.float64(v)
        yield "numeric text", lambda: _fresh_str(repr(v))
        if v == int(v):
            yield "IntSub", lambda: IntSub(int(v))
        return
    if isinstance(v, tuple) and v and isinstance(v[0], tuple) and v[0] and isinstance(v[0][0], str):
        # OrderRequest.extra: (key, value) pairs; every value of the zoo
        for name, make in _ZOO:
            yield f"extra {name}", (lambda make=make: ((StrSub("k"), make()), ("k2", [make(), {"n": make()}])))
        return
    if isinstance(v, tuple):  # book levels: pairs of numbers, every container shape
        yield "list of lists", lambda: [[FracSub(Fraction(p)), FloatSub(s)] for p, s in v]
        yield "tuple of FrozenList", lambda: tuple(FrozenList((np.float64(p), Fraction(s))) for p, s in v)
        yield "list of tuples of Decimal", lambda: [(Decimal(repr(p)), DecSub(repr(s))) for p, s in v]
        return
    raise AssertionError(f"no kinds for {v!r}")  # pragma: no cover


_ZOO = (
    ("None", lambda: None),
    ("bool", lambda: True),
    ("big int", lambda: _fresh_int(10**40 + 7)),
    ("IntSub", lambda: IntSub(123456789)),
    ("float", lambda: _fresh_float(2.5)),
    ("FloatSub", lambda: FloatSub(-0.0)),
    ("complex", lambda: complex(1.5, -2.5)),
    ("ComplexSub", lambda: ComplexSub(3.0, 4.0)),
    ("str", lambda: _fresh_str("hello world")),
    ("StrSub", lambda: StrSub("sub text")),
    ("bytes", lambda: bytes(bytearray(b"raw bytes"))),
    ("BytesSub", lambda: BytesSub(b"sub bytes")),
    ("Decimal", lambda: Decimal("1.2500")),
    ("DecSub", lambda: DecSub("-3.75E+2")),
    ("Fraction", lambda: Fraction(1, 3)),
    ("FracSub", lambda: FracSub(7, 9)),
    ("numpy.float64", lambda: np.float64(1.25)),
    ("numpy.int64", lambda: np.int64(-42)),
    ("numpy.bool_", lambda: np.bool_(False)),
    ("numpy.str_", lambda: np.str_("np text")),
    ("numpy.complex128", lambda: np.complex128(1 + 2j)),
    ("tuple", lambda: (Fraction(1, 2), "ab", 1.5)),
    ("list", lambda: [Fraction(2, 3), [Decimal("1.5")], "xy"]),
    ("dict", lambda: {"a": Fraction(5, 7), "b": [1.5, {"c": FracSub(1, 4)}]}),
    ("set", lambda: {Fraction(1, 5), "s"}),
    ("frozenset", lambda: frozenset({Fraction(1, 6), 7.5})),
    ("FrozenList", lambda: FrozenList((Fraction(3, 5), 2.5))),
    ("FrozenDict", lambda: FrozenDict({"f": Fraction(4, 9), "l": FrozenList((1.5,))})),
    ("FrozenSet", lambda: FrozenSet({Fraction(2, 9)})),
)

BASE = {
    OrderRequest: dict(side="buy", order_type="limit", size=1.5, price=101.25, client_order_id="c-1",
                       time_in_force="GTC", post_only=False, reduce_only=False, trigger_price=99.5,
                       extra=(("k", 1.5),)),
    CancelRequest: dict(client_order_id="c-1"),
    Ack: dict(client_order_id="c-1", venue_order_id="v-1"),
    Reject: dict(client_order_id="c-1", reason="no margin", request_kind="new"),
    Fill: dict(client_order_id="c-1", price=101.25, size=0.5, liquidity="maker"),
    Canceled: dict(client_order_id="c-1", reason="canceled"),
    StateUnknown: dict(client_order_id="c-1", detail="timeout", request_kind="new"),
    FillNotice: dict(client_order_id="c-1", price=101.25, size=0.5, side="buy", liquidity="maker",
                     venue_time_ns=T0, fee=0.25),
    TradeEvent: dict(received_time_ns=T0 + 5, exchange_time_ns=T0, seq=3, price=101.25, size=0.5, side="buy",
                     trade_id="t-1"),
    BookSnapshotEvent: dict(received_time_ns=T0, bids=((101.0, 1.5), (100.5, 2.0)),
                            asks=((101.5, 1.0), (102.0, 3.0))),
    BookDeltaEvent: dict(received_time_ns=T0, side="bid", price=101.0, size=1.5),
    BarEvent: dict(received_time_ns=T0, open=100.5, high=102.25, low=99.75, close=101.25, volume=12.5,
                   start_time_ns=T0 - 60 * SEC),
    FundingEvent: dict(received_time_ns=T0, rate=0.0001, mark_price=101.25),
    LiquidationEvent: dict(received_time_ns=T0, price=101.25, size=2.5, side="sell"),
    ClockEvent: dict(received_time_ns=T0, tag="tick"),
    OrderAckEvent: dict(received_time_ns=T0, client_order_id="c-1", venue_order_id="v-1"),
    OrderRejectEvent: dict(received_time_ns=T0, client_order_id="c-1", reason="no margin", request_kind="new"),
    OrderFillEvent: dict(received_time_ns=T0, client_order_id="c-1", price=101.25, size=0.5, side="buy",
                         liquidity="maker", fee=0.25),
    OrderCanceledEvent: dict(received_time_ns=T0, client_order_id="c-1", reason="canceled", answers="cancel"),
    OrderStateUnknownEvent: dict(received_time_ns=T0, client_order_id="c-1", detail="timeout",
                                 request_kind="new"),
}


# -- graphs, snapshots, attacks -------------------------------------------------

# classes, code and module constants (an Enum member is one object per
# member, like a class): shared by design, and changing them changes the
# program, not a value -- left out of the graphs and the attacks
_SKIP_TYPES = (type, types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.MethodType,
               types.CodeType, types.GetSetDescriptorType, types.MemberDescriptorType, enum.Enum)


def _graph(*roots) -> list:
    """Every object reachable from the roots, as the interpreter says
    (`gc.get_referents`), classes and code left out. Kept alive by the
    list (ids are compared)."""
    out, seen, stack = [], set(), list(roots)
    while stack:
        o = stack.pop()
        if isinstance(o, _SKIP_TYPES) or id(o) in seen:
            continue
        seen.add(id(o))
        out.append(o)
        stack.extend(gc.get_referents(o))
    return out


def _kept_once_per_value(o) -> bool:
    """Does the interpreter itself keep one object per value of this one?
    Asked by building it twice from its bytes."""
    if o is None or o is True or o is False:
        return True
    if type(o) not in (int, str, bytes, tuple, frozenset, float, complex):
        return False
    try:
        a, b = pickle.loads(pickle.dumps(o)), pickle.loads(pickle.dumps(o))
    except Exception:  # pragma: no cover
        return False
    return a is b


def _shared(g1: list, g2: list) -> list:
    ids = {id(o) for o in g2}
    return [o for o in g1 if id(o) in ids and not _kept_once_per_value(o)]


_CORE_BUILT = (type(None), bool, int, float, complex, str, bytes, Decimal, Fraction, tuple, frozenset,
               FrozenList, FrozenSet, FrozenDict, types.MappingProxyType, dict, *PATH_CARRIERS)


def _foreign(graph: list) -> list:
    return [type(o).__qualname__ for o in graph if type(o) not in _CORE_BUILT]


def _snap(v):
    """A plain, type-tagged picture of a value, read through its own
    methods (so a lying object shows)."""
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return (type(v).__qualname__, tuple((f.name, _snap(getattr(v, f.name))) for f in dataclasses.fields(v)))
    if isinstance(v, FrozenDict):
        return ("FrozenDict", tuple((_snap(k), _snap(x)) for k, x in v.items()))
    if isinstance(v, (tuple, frozenset, list, set)):
        items = [_snap(x) for x in v]
        if isinstance(v, (frozenset, set)):
            items = sorted(items, key=repr)
        return (type(v).__qualname__, tuple(items))
    return (type(v).__qualname__, repr(v))


def _liar(cls):
    """A subclass of `cls` with the same layout that answers everything
    with junk (for a `__class__` swap)."""
    ns = {"__slots__": (), "__repr__": lambda self: "LIED", "__eq__": lambda self, o: True,
          "__hash__": lambda self: 0}
    if dataclasses.is_dataclass(cls):
        for f in dataclasses.fields(cls):
            ns[f.name] = property(lambda self: "LIED")
    try:
        return type(f"Liar{cls.__name__}", (cls,), ns)
    except TypeError:
        return None


_LIARS: dict = {}

JUNK = 999


def _attack(*roots) -> int:
    """Change everything reachable from the roots by every means the
    interpreter allows short of writing memory. Returns how many objects
    were changed."""
    changed = 0
    for o in _graph(*roots):
        t = type(o)
        if t is list:
            o[:] = [JUNK]
            changed += 1
            continue
        if t is dict:
            o.clear()
            o["junk"] = JUNK
            changed += 1
            continue
        if t is set:
            o.clear()
            o.add(JUNK)
            changed += 1
            continue
        names = []
        for k in t.__mro__:
            slots = k.__dict__.get("__slots__", ())
            names.extend([slots] if isinstance(slots, str) else list(slots))
        if hasattr(o, "__dict__") and not isinstance(o, type):
            try:
                names.extend(list(vars(o)))
            except TypeError:  # pragma: no cover
                pass
        for name in names:
            if name in ("__dict__", "__weakref__"):
                continue
            try:
                object.__setattr__(o, name, JUNK)
                changed += 1
            except (AttributeError, TypeError):
                pass
        if t not in _LIARS:
            _LIARS[t] = _liar(t) if t.__module__ != "builtins" else None
        liar = _LIARS[t]
        if liar is not None:
            try:
                object.__setattr__(o, "__class__", liar)
                changed += 1
            except TypeError:
                pass
    return changed


# -- unit grid -----------------------------------------------------------------

def test_every_carrier_is_in_the_grid():
    assert set(BASE) == set(PATH_CARRIERS)
    for cls, kw in BASE.items():
        cls(**kw)  # the baseline is valid


def _grid():
    for cls, base in BASE.items():
        for name, v in base.items():
            for kind, make in _kinds(v):
                yield cls, name, kind, make


@pytest.mark.parametrize("cls", list(BASE), ids=lambda c: c.__name__)
def test_a_carrier_shares_nothing_with_its_sender_and_ignores_later_changes(cls):
    accepted, refused, problems = 0, [], []
    fields_accepting = set()
    for c, name, kind, make in _grid():
        if c is not cls:
            continue
        value = make()
        kw = dict(BASE[cls])
        kw[name] = value
        try:
            obj = cls(**kw)
        except (CoreError, ValueError, TypeError):
            refused.append((name, kind))
            continue
        accepted += 1
        fields_accepting.add(name)
        before = _snap(obj)
        carrier_graph = _graph(obj)
        sender_graph = _graph(value, kw)
        shared = _shared(carrier_graph, sender_graph)
        if shared:
            problems.append(("shared", name, kind, [type(o).__qualname__ for o in shared]))
        foreign = _foreign(carrier_graph)
        if foreign:
            problems.append(("foreign type", name, kind, foreign))
        _attack(value, kw)
        after = _snap(obj)
        if after != before:
            problems.append(("changed", name, kind, before, after))
    assert not problems, problems[:6]
    assert accepted > 0
    assert fields_accepting == set(BASE[cls]), set(BASE[cls]) - fields_accepting


def test_a_value_the_sender_changes_through_its_slots_does_not_cross():
    """The critic's case (i0-r7-02) and its family, on the carrier alone:
    Fraction, a Fraction subclass, a Decimal subclass and the core's own
    FrozenDict handed in `extra`, changed through their slots afterwards."""
    held = [Fraction(1, 3), FracSub(2, 5), Decimal("1.5"), FrozenDict({"a": Fraction(1, 7)})]
    req = OrderRequest("buy", "limit", 1.0, price=90.0, extra=tuple((f"k{i}", v) for i, v in enumerate(held)))
    before = req.extra_dict()
    held[0]._numerator = 999
    object.__setattr__(held[1], "_denominator", 11)
    object.__setattr__(held[3], "_items", (("a", 5),))
    _attack(held)
    assert req.extra_dict() == before
    assert req.extra_dict()["k0"] == Fraction(1, 3) and type(req.extra_dict()["k0"]) is Fraction
    assert req.extra_dict()["k1"] == Fraction(2, 5) and type(req.extra_dict()["k2"]) is Decimal
    assert not _shared(_graph(req), _graph(held))


def test_a_value_the_sender_broke_before_sending_is_refused_or_read_as_it_is_now():
    """What a sender broke BEFORE handing it over is read as it is at that
    moment and checked like anything else: a FrozenDict whose pairs slot
    holds no pairs, a Fraction with a zero or non-int part, are refused
    with the API's error (not a TypeError from inside the core); a
    FrozenDict whose pairs now hold a list is frozen as a list."""
    broken = []
    fd = FrozenDict({"a": 1})
    object.__setattr__(fd, "_items", JUNK)
    broken.append(fd)
    fr = Fraction(1, 3)
    fr._denominator = 0
    broken.append(fr)
    fr2 = Fraction(1, 3)
    fr2._numerator = "x"
    broken.append(fr2)
    for value in broken:
        with pytest.raises(CoreError):
            OrderRequest("buy", "limit", 1.0, extra=(("k", value),))
    fd2 = FrozenDict({"a": 1})
    object.__setattr__(fd2, "_items", (("a", [1, 2]),))
    req = OrderRequest("buy", "limit", 1.0, extra=(("k", fd2),))
    assert req.extra_dict() == {"k": {"a": [1, 2]}}


def test_what_a_receiver_reads_back_is_its_own():
    """`extra_dict()` (and every read of a carrier) gives the reader
    objects no other reader holds: changing them changes nothing else."""
    req = OrderRequest("buy", "limit", 1.0, price=90.0, extra=(("f", Fraction(1, 3)), ("d", {"x": [1.5]})))
    a, b = req.extra_dict(), req.extra_dict()
    assert not _shared(_graph(a), _graph(b)) and not _shared(_graph(a), _graph(req))
    _attack(a)
    assert b == req.extra_dict() == {"f": Fraction(1, 3), "d": {"x": [1.5]}}


# -- engine run: every path, every receiver --------------------------------------

class _Log:
    def __init__(self) -> None:
        self.got: list = []  # (who, obj, snap at receipt, graph at receipt)
        self.foreign: list = []  # (who, type name) of objects not built by the core, at receipt

    def receive(self, who: str, obj, attack: bool = True, t=None):
        graph = _graph(obj) + ([t] if t is not None else [])  # the time argument is the receiver's too
        self.got.append((who, obj, _snap(obj), graph))
        self.foreign.extend((who, t) for t in _foreign(graph))  # at receipt, before it attacks
        if attack:
            _attack(obj)


LOG = _Log()


class _Latency:
    def __init__(self) -> None:
        self.kept: list = []

    def feed_delay_ns(self, event):
        LOG.receive("latency.feed", event)
        return IntAnswer(0)

    def order_delay_ns(self, order, sent):
        LOG.receive("latency.order", order, t=sent)
        return 10 * SEC

    def cancel_delay_ns(self, request, sent):
        LOG.receive("latency.cancel", request, t=sent)
        return 10 * SEC

    def notice_delay_ns(self, report, venue_time):
        LOG.receive("latency.notice", report, attack=False, t=venue_time)
        self.kept.append((report, _snap(report)))  # read again later
        return SEC


class IntAnswer(int):
    pass


class _Venue:
    def __init__(self) -> None:
        self.sent: list = []  # reports it handed over, attacked at its next call

    def _later(self) -> None:
        for r, _ in self.sent:
            _attack(r)

    def on_market_event(self, event, t):
        self._later()
        LOG.receive("venue.market", event, t=t)
        return ()

    def on_order(self, order, t):
        self._later()
        coid = order.client_order_id  # read before the attack: its own copy
        LOG.receive("venue.order", order, t=t)
        out = (Ack(StrSub(coid), StrSub(f"v-{coid}")), Fill(StrSub(coid), FracSub(203, 2), Fraction(1, 4),
                                                             liquidity=StrSub("maker")))
        self.sent.extend((r, _snap(r)) for r in out)
        return out

    def on_cancel(self, request, t):
        self._later()
        coid = request.client_order_id
        LOG.receive("venue.cancel", request, t=t)
        out = (Canceled(StrSub(coid), StrSub("user asked")),)
        self.sent.extend((r, _snap(r)) for r in out)
        return out


class _Cost:
    def cost(self, fill):
        LOG.receive("cost", fill)
        return FloatSub(0.5)


class _Account:
    def __init__(self) -> None:
        self.forced = None

    def apply_fill(self, fill):
        LOG.receive("account.fill", fill)

    def apply_funding(self, event):
        LOG.receive("account.funding", event)

    def apply_liquidation(self, event):
        LOG.receive("account.liquidation", event)

    def on_market_event(self, event, t):
        if self.forced is not None:
            _attack(self.forced[0])  # the account changes what it returned, later
        LOG.receive("account.market", event, t=t)
        if event.EVENT_TYPE is EventType.LIQUIDATION and self.forced is None:
            req = OrderRequest(StrSub("sell"), "market", FracSub(3, 2), client_order_id=StrSub("forced-1"),
                               extra=(("why", {"margin": [Fraction(1, 9)]}),))
            self.forced = (req, _snap(req))
            return [req]
        return ()

    def check_order(self, order, t):
        LOG.receive("account.check", order, t=t)
        return None


def _source(sent: list):
    """A data source that attacks every event it yielded when asked for
    the next one (the venue and the strategy read it later)."""
    evs = [
        TradeEvent(received_time_ns=T0, price=FracSub(201, 2), size=FloatSub(0.5), side=StrSub("buy"),
                   trade_id=StrSub("t-1")),
        BookSnapshotEvent(received_time_ns=T0 + SEC, bids=[[Fraction(201, 2), 1.5]], asks=[(101.0, Decimal("2"))]),
        BookDeltaEvent(received_time_ns=T0 + 2 * SEC, side=StrSub("bid"), price=np.float64(100.5), size=0.0),
        BarEvent(received_time_ns=T0 + 3 * SEC, open=100.0, high=101.0, low=99.0, close=100.5, volume=3.0),
        FundingEvent(received_time_ns=T0 + 4 * SEC, rate=Fraction(1, 10000), mark_price=100.5),
        LiquidationEvent(received_time_ns=T0 + 5 * SEC, price=100.0, size=IntSub(2), side="sell"),
        ClockEvent(received_time_ns=T0 + 6 * SEC, tag=StrSub("hb")),
    ] + [ClockEvent(received_time_ns=T0 + (7 + i) * SEC, tag=f"hb{i}") for i in range(30)]
    for ev in evs:
        for prev, _ in sent:
            _attack(prev)
        sent.append((ev, _snap(ev)))
        yield ev


class _Strategy:
    def __init__(self) -> None:
        self.sent: list = []  # (kind, obj, snap, extra graph roots)
        self.placed = False

    def on_event(self, event, ctx):
        now = ctx.now_ns  # read before it attacks its own copy (that only misleads itself)
        LOG.receive("strategy", event)  # the strategy attacks what it received too
        for _kind, obj, _snap_, roots in self.sent:
            _attack(obj, *roots)  # later, while in flight
        if not self.placed:
            self.placed = True
            held = [Fraction(1, 3), {"deep": [FracSub(1, 8)]}, FrozenDict({"x": Fraction(2, 7)})]
            req = OrderRequest(StrSub("buy"), StrSub("limit"), FracSub(5, 4), price=np.float64(99.5),
                               client_order_id=StrSub("s-1"), post_only=np.bool_(False),
                               extra=tuple((f"k{i}", v) for i, v in enumerate(held)))
            self.sent.append(("order", req, _snap(req), held))
            ctx.place_order(req)
            cancel = CancelRequest(StrSub("s-1"))
            self.sent.append(("cancel", cancel, _snap(cancel), []))
            ctx.cancel_order(cancel)
            tag = StrSub("my timer")
            self.sent.append(("tag", tag, _snap(tag), []))
            ctx.set_timer(now + 20 * SEC, tag)


def _fields(snap):
    return dict(snap[1]) if isinstance(snap[1], tuple) and snap[1] and isinstance(snap[1][0], tuple) else snap


def test_every_receiver_on_every_path_reads_what_was_sent_and_holds_its_own():
    LOG.got.clear()
    LOG.foreign.clear()
    source_sent: list = []
    strategy, venue, account, latency = _Strategy(), _Venue(), _Account(), _Latency()
    result = CoreEngine(strategy, _source(source_sent), fill_model=venue, latency_model=latency,
                        cost_model=_Cost(), account=account).run()
    problems = []

    # what each sender handed over, at the time it did
    order_snap = _fields(strategy.sent[0][2])
    cancel_snap = _fields(strategy.sent[1][2])
    forced_snap = _fields(account.forced[1])
    source_snaps = [(_fields(s), ev) for ev, s in source_sent]
    reports = {s[0]: _fields(s) for _r, s in venue.sent}  # by the class it had when sent

    def market_snap_for(obj_snap):
        f = dict(obj_snap)
        for want, _ev in source_snaps:
            keys = [k for k in want if k not in ("seq", "received_time_ns")]
            if all(f.get(k) == want[k] for k in keys) and f.get("received_time_ns") is not None:
                return want
        return None

    seen_whos = set()
    for who, obj, snap, graph in LOG.got:
        seen_whos.add(who)
        f = _fields(snap)
        if who in ("latency.feed", "venue.market", "account.market", "account.funding", "account.liquidation",
                   "strategy"):
            if snap[0].startswith("Order") and who == "strategy":  # the class at receipt
                continue  # notices, checked below
            if snap[0] == "ClockEvent" and who == "strategy" and f.get("tag") == ("str", repr("my timer")):
                continue  # the timer, checked below
            if market_snap_for(snap[1]) is None:
                problems.append(("market value", who, snap))
        elif who in ("latency.order", "account.check"):
            if f != order_snap:
                problems.append(("order value", who, f, order_snap))
        elif who == "venue.order":
            if f != order_snap and f != forced_snap:
                problems.append(("venue order value", f))
        elif who in ("latency.cancel", "venue.cancel"):
            if f != cancel_snap:
                problems.append(("cancel value", who, f))
        # graphs: disjoint from every sender's, and from every other receiver's
        for kind, sobj, _s, roots in strategy.sent:
            if _shared(graph, _graph(sobj, *roots)):
                problems.append(("shares with the strategy's", who, kind))
        for ev, _s in source_sent:
            if _shared(graph, _graph(ev)):
                problems.append(("shares with the source's", who))
        for r, _s in venue.sent:
            if _shared(graph, _graph(r)):
                problems.append(("shares with the venue's", who))
        if _shared(graph, _graph(account.forced[0])):
            problems.append(("shares with the account's", who))
    for i, (w1, _o1, _s1, g1) in enumerate(LOG.got):
        for w2, _o2, _s2, g2 in LOG.got[i + 1:]:
            if _shared(g1, g2):
                problems.append(("two receivers share", w1, w2))

    # the reports the latency model kept and read again later
    for r, s in latency.kept:
        if _snap(r) != s:
            problems.append(("the latency model's report changed", s, _snap(r)))
    fill = reports["Fill"]
    sent_reports = [_fields(s) for _r, s in venue.sent]
    for r, s in latency.kept:
        if _fields(s) not in sent_reports:
            problems.append(("notice report not as sent", s))

    # the strategy's notices and timer: what the venue and the strategy sent
    notices = [(who, s[0], _fields(s)) for who, _o, s, _g in LOG.got if who == "strategy"]  # class at receipt
    acks = [f for _w, c, f in notices if c == "OrderAckEvent" and f["client_order_id"] == ("str", "'s-1'")]
    fills = [f for _w, c, f in notices if c == "OrderFillEvent" and f["client_order_id"] == ("str", "'s-1'")]
    timers = [f for _w, c, f in notices if c == "ClockEvent" and f["tag"] == ("str", repr("my timer"))]
    if not (acks and acks[0]["venue_order_id"] == ("str", "'v-s-1'")):
        problems.append(("ack notice", acks))
    if not (fills and fills[0]["price"] == ("float", "101.5") and fills[0]["size"] == ("float", "0.25")):
        problems.append(("fill notice", fills))
    if not timers:
        problems.append(("timer", "no timer with the tag sent"))
    costs = [_fields(s) for who, _o, s, _g in LOG.got if who == "cost"]
    booked = [_fields(s) for who, _o, s, _g in LOG.got if who == "account.fill"]
    if not costs or costs[0]["price"] != ("float", "101.5") or costs[0]["fee"] != ("float", "0.0"):
        problems.append(("cost notice", costs))
    booked = [f for f in booked if f["client_order_id"] == ("str", "'s-1'")]
    if not booked or booked[0]["fee"] != ("float", "0.5") or booked[0]["side"] != ("str", "'buy'"):
        problems.append(("account notice", booked))
    assert fill["price"] == ("float", "101.5")

    # the result: what was sent, and none of it held by a sender or a receiver
    res_graph = _graph(result.order_requests, result.cancel_requests, result.fills, result.forced_orders)
    if _fields(_snap(result.order_requests[0])) != order_snap:
        problems.append(("result order", _snap(result.order_requests[0])))
    if _fields(_snap(result.forced_orders[0])) != forced_snap:
        problems.append(("result forced", _snap(result.forced_orders[0]), forced_snap))
    if _fields(_snap(result.cancel_requests[0])) != cancel_snap:
        problems.append(("result cancel",))
    for who, _o, _s, g in LOG.got:
        if _shared(res_graph, g):
            problems.append(("the result shares with", who))
    forced_view = result.orders["forced-1"].request
    if _fields(_snap(forced_view)) != forced_snap:
        problems.append(("forced view", _snap(forced_view)))

    if LOG.foreign:
        problems.append(("foreign types at receipt", LOG.foreign[:5]))
    need = {"latency.feed", "latency.order", "latency.cancel", "latency.notice", "venue.market", "venue.order",
            "venue.cancel", "cost", "account.fill", "account.funding", "account.liquidation", "account.market",
            "account.check", "strategy"}
    assert need <= seen_whos, need - seen_whos
    assert not problems, problems[:8]


def test_the_result_order_views_share_nothing_with_the_strategys():
    held = {}

    class S:
        def on_event(self, ev, ctx):
            if "coid" not in held:
                held["coid"] = ctx.place_order(OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="a-1",
                                                            extra=(("f", Fraction(1, 3)),)))
            held["view"] = ctx.order(held["coid"])

    result = CoreEngine(S(), [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0, size=1.0, side="buy")
                              for i in range(3)]).run()
    view = result.orders["a-1"]
    before = _snap(view.request)
    assert not _shared(_graph(view), _graph(held["view"]))
    _attack(held["view"])  # the strategy changes its own view afterwards
    assert _snap(view.request) == before and view.state.value == "OPEN"


@pytest.mark.parametrize("forged", [
    ("new", "not a request", 0),
    ("xyz", None, None),
    ["new"],
    ("cancel", CancelRequest("never-placed"), 0),
    ("timer", T0 - 1, "back in time"),
])
def test_an_outbox_item_written_around_the_order_port_is_refused(forged):
    """The outbox is reachable through the context's private attributes;
    an item that is not a message by the API's rules is refused
    (OrderApiError), not guessed at or sent at a time the item names.
    (Rewritten in round 9: the round-8 case of a well-formed new order for
    an id the port never registered is no longer refused -- the core reads a
    message by the API's rules against its OWN book, so such a message has
    exactly the effect of place_order; test_bt0_r9_reachable_state_adversary.py
    checks that equivalence.)"""
    class S:
        def on_event(self, ev, ctx):
            [port] = find(ctx, _OrderPort)  # reached through the context's call functions (round 9)
            port._outbox.append(forged)

    with pytest.raises(CoreError):
        CoreEngine(S(), [TradeEvent(received_time_ns=T0, price=100.0, size=1.0, side="buy")]).run()
