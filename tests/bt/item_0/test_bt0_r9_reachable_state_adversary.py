"""Round 9 (i0-r8-01, the family i0-r4-02 -> i0-r5-01 -> i0-r7-02 ->
i0-r8-01: the core keeps, and later reads, state another party can change
without going through the API). Written BEFORE the fix (lead design
round_7/LEAD_DESIGN.md s3.3).

The rule under test (round_9/ROOTCAUSE.md A, the contract's
`channel_payloads.ownership`): what the core decides from, sends and
reports is built from objects only the core holds; what the strategy can
reach is its own (copies, or containers the core writes and never reads
back), except the messages it sent (the order outbox), which the core reads
once, when the callback returns, as the arguments of API calls, applying
every API rule again against its own state.

The input space is NOT taken from the implementation's case split. The
tests walk everything reachable from the context by attribute access --
instance dicts, slots of every class in the MRO, a bound method's
`__self__`, a closure's cells, the items of lists, tuples, sets, dicts and
mapping proxies -- with no private name assumed, and attack each object
found with every way of changing it:

* a list: `list.append` / `list.insert` of each forged item, `list.__setitem__`
  of the first item to each forged item, `list.__delitem__` of the first,
  `list.clear`, `list.reverse` (the BASE type's methods: they bypass what the
  object's own class refuses);
* a dict: `dict.__setitem__` of a new key and of the first key to each forged
  item, `dict.pop` of the first key, `dict.clear`;
* a set: `set.add` of a forged item, `set.clear`;
* every attribute (instance dict entry or slot): `object.__setattr__` to each
  forged value and `object.__delattr__`;
* every method name of the object's class, shadowed by an instance
  attribute that raises (objects with an instance dict only);

at two times: (A) in the callback that walked, after its API calls; (B) in
a LATER callback, through references kept from (A). The forged items are
the ones a strategy would use to lie: None, an int time, an order view that
says FILLED, an order request with the reserved forced-order id, an event
from the future, an outbox-like message, a str.

Oracle (from the rule, not from the code): the run either completes with
every receiver's record (latency model, fill model, account, cost model),
the stream of what was delivered to the strategy (read at the start of each
callback, before it attacks anything) and the caller's result all EQUAL to
the run without the attack; or it raises, and then every receiver's record
and the delivered stream are a PREFIX of the unattacked run's (nothing
forged reached anyone before the refusal). The outbox is the one object
the rule lets the core read: it is found by behaviour (the list that grows
when `place_order` is called), left out of the first grid, and attacked in
its own grid with its own oracle (a message by the API's rules has the
effect of the API call; any other is refused with a CoreError).

Counts (machine-made by the tests, printed with -s): the grid sizes are
asserted to be the product of the axes the walk found; every cell is run
(the lead's rule, LEAD_DESIGN s7.2 12: under 100,000 cells, all of them).

NOT in the lists (A-10): ctypes and writing memory; interpreter
introspection (call stack, `gc`) used to reach the engine; the core's CODE
-- classes, functions, modules, Enum members (reachable as `__class__`,
`__func__.__globals__`: changing them changes the program, not its state);
changing an object while the callback's own API calls run (a strategy that
breaks its own port before calling it changes its own messages, which are
its to choose); attacks from socket code (the sockets get copies, round 8's
adversary); `__class__` assignment (the core's objects are slotted or
built-in; a lying subclass of a carrier is round 8's adversary).
"""
from __future__ import annotations

import types
from decimal import Decimal

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
from bot.bt.core.api import OrderState, OrderView, _OrderPort
from bt0_util import find

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
MS = 1_000_000


# --- the run ------------------------------------------------------------------

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
        self.logs: dict[str, list] = {}
        self.delivered: list[str] = []

    def log(self, who: str, *what) -> None:
        self.logs.setdefault(who, []).append(repr(what))


class _Venue:
    def __init__(self, rec: _Rec) -> None:
        self.rec = rec
        self.live: list[str] = []

    def on_market_event(self, event, t):
        self.rec.log("venue.market", event, t)
        out = []
        if event.EVENT_TYPE is EventType.TRADE:
            for coid in self.live:
                out.append(Fill(coid, event.price, 1.0 if not coid.startswith("core-") else 0.5, "maker"))
            self.live = []
        return out

    def on_order(self, order, t):
        self.rec.log("venue.order", order, t)
        if order.order_type == "market":
            return (Ack(order.client_order_id, "v-" + order.client_order_id),
                    Fill(order.client_order_id, 100.0, order.size, "taker"))
        self.live.append(order.client_order_id)
        return (Ack(order.client_order_id, "v-" + order.client_order_id),)

    def on_cancel(self, request, t):
        self.rec.log("venue.cancel", request, t)
        if request.client_order_id in self.live:
            self.live.remove(request.client_order_id)
        return (Canceled(request.client_order_id, "user"),)


class _Latency:
    def __init__(self, rec: _Rec) -> None:
        self.rec = rec

    def feed_delay_ns(self, event):
        self.rec.log("latency.feed", event)
        return 100 * MS

    def order_delay_ns(self, order, sent):
        self.rec.log("latency.order", order, sent)
        return 300 * MS

    def cancel_delay_ns(self, request, sent):
        self.rec.log("latency.cancel", request, sent)
        return 200 * MS

    def notice_delay_ns(self, report, t):
        self.rec.log("latency.notice", report, t)
        return 150 * MS


class _Cost:
    def __init__(self, rec: _Rec) -> None:
        self.rec = rec

    def cost(self, fill):
        self.rec.log("cost", fill)
        return 0.001 * fill.price * fill.size


class _Account:
    def __init__(self, rec: _Rec) -> None:
        self.rec = rec
        self.forced = False

    def apply_fill(self, fill):
        self.rec.log("account.fill", fill)

    def apply_funding(self, event):
        self.rec.log("account.funding", event)

    def apply_liquidation(self, event):
        self.rec.log("account.liquidation", event)

    def on_market_event(self, event, t):
        self.rec.log("account.market", event, t)
        if event.EVENT_TYPE is EventType.LIQUIDATION and not self.forced:
            self.forced = True
            return [OrderRequest("sell", "market", 1.0)]
        return ()

    def check_order(self, order, t):
        self.rec.log("account.check", order, t)
        return None


def _script(k: int, ctx, now: int) -> None:
    """The strategy's API calls, by callback number (1, 2, ...). Explicit
    ids after the first callback, so an attack on the port's own counter
    (its choice of ids) cannot change what is sent."""
    if k == 1:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=99.0, client_order_id="a1"))
        ctx.place_order(OrderRequest("buy", "market", 0.5))  # an engine-named id
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
    elif k == 6:
        ctx.place_order(OrderRequest("sell", "market", 1.0, client_order_id="a4"))
    elif k == 8:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=97.0, client_order_id="a5"))
        ctx.set_timer(now + 700 * MS, "tm2")
    elif k == 10:
        ctx.cancel_order("a5")
        ctx.open_orders()
    elif k == 12:
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=96.0, client_order_id="a6"))
        ctx.visible_events(until_ns=now, n=2)
    elif k == 29:  # after the forced order was adopted (28, 29) and history_limit dropped events
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="a7"))
        ctx.open_orders()
    elif k == 30:
        ctx.cancel_order("a7")
        ctx.visible_events(EventType.LIQUIDATION, n=1)
    elif k == 31:
        ctx.place_order(OrderRequest("sell", "market", 1.0, client_order_id="a8"))


# (callback that walks the context, callback that attacks), both after their API calls:
# the same callback, or a LATER one through references kept from the walk
TIMINGS = {"A": (3, 3), "B": (3, 8), "C": (29, 29), "D": (3, 29), "E": (12, 12)}
WALK_AT, LATER_AT = TIMINGS["A"][0], TIMINGS["B"][1]


class _Strategy:
    """Runs `_script`; at the attack's time walks the context and applies
    one attack (or only counts them when `attack` is None and `survey`)."""

    def __init__(self, rec: _Rec, attack=None, survey=None, extra=None) -> None:
        self.rec = rec
        self.k = 0
        self.attack = attack  # (timing name, target index, attack index)
        self.survey = survey  # (walk_at, a list to fill with [(path, type name, attack names)])
        self.extra = extra  # a callable (k, ctx) run after the script (the outbox grid)
        self.kept = None
        self.outcome = None

    def on_event(self, event, ctx) -> None:
        try:
            self._on_event(event, ctx)
        except BaseException as exc:  # noqa: BLE001 - its own call failed on what it broke: marked, re-raised
            exc._bt0_from_strategy = True
            raise

    def _on_event(self, event, ctx) -> None:
        self.rec.delivered.append(repr(event))  # what the core handed over, before any attack
        self.k += 1
        k = self.k
        _script(k, ctx, ctx.now_ns)
        if self.extra is not None:
            self.extra(k, ctx)
        walk_at = attack_at = None
        if self.attack is not None:
            walk_at, attack_at = TIMINGS[self.attack[0]]
        elif self.survey is not None:
            walk_at = self.survey[0]
        if k == walk_at:
            targets = _targets(ctx)
            if self.survey is not None:
                self.survey[1].extend((path, type(obj).__name__, [a[0] for a in _attacks(obj)])
                                      for path, obj in targets)
            self.kept = targets
        if self.attack is not None:
            _when, ti, ai = self.attack
            if k == attack_at:
                _path, obj = self.kept[ti]
                name, do = _attacks(obj)[ai]
                try:
                    do()
                    self.outcome = "applied"
                except Exception as exc:  # noqa: BLE001 - the object refused the change itself
                    self.outcome = f"refused at the write: {type(exc).__name__}"


def _run(attack=None, survey=None, extra=None):
    CALLED.clear()
    rec = _Rec()
    strat = _Strategy(rec, attack, survey, extra)
    eng = CoreEngine(strat, _events(), fill_model=_Venue(rec), latency_model=_Latency(rec),
                     cost_model=_Cost(rec), account=_Account(rec), history_limit=2)
    try:
        res = eng.run()
    except BaseException as exc:  # noqa: BLE001 - any refusal counts; prefixes are checked
        rec.called = bool(CALLED)
        return "raised", exc, rec, strat
    rec.called = bool(CALLED)
    return "ok", _result_snapshot(res), rec, strat


def _result_snapshot(res) -> dict:
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


# --- the walk -------------------------------------------------------------------

_ATOMS = (int, float, complex, str, bytes, bool, type(None), Decimal, range, slice)
_CODE = (type, types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.CodeType,
         types.MethodType, types.MethodWrapperType, types.WrapperDescriptorType, types.MethodDescriptorType,
         types.GetSetDescriptorType, types.MemberDescriptorType, property, staticmethod, classmethod)


def _is_state(obj) -> bool:
    import enum
    return not isinstance(obj, _ATOMS) and not isinstance(obj, _CODE) and not isinstance(obj, enum.Enum)


def _attr_names(obj) -> list[str]:
    names: list[str] = []
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        names.extend(sorted(d))
    for cls in type(obj).__mro__:
        slots = cls.__dict__.get("__slots__", ())
        for s in ([slots] if isinstance(slots, str) else list(slots)):
            if s in ("__dict__", "__weakref__"):
                continue
            if s.startswith("__") and not s.endswith("__"):
                s = f"_{cls.__name__.lstrip('_')}{s}"  # a private slot's mangled name
            if s not in names:
                names.append(s)
    return names


def _children(obj):
    """(label, child) for everything `obj` references by attribute access."""
    out = []
    for name in _attr_names(obj):
        try:
            v = object.__getattribute__(obj, name)
        except AttributeError:
            continue
        out.append((f".{name}", v))
    for label in ("__self__",):
        v = getattr(obj, label, None) if isinstance(obj, (types.MethodType, types.BuiltinMethodType)) else None
        if v is not None:
            out.append((f".{label}", v))
    if isinstance(obj, types.FunctionType) and obj.__closure__:
        for i, cell in enumerate(obj.__closure__):
            try:
                out.append((f".cell{i}", cell.cell_contents))
            except ValueError:
                pass
    if isinstance(obj, (list, tuple)):
        get = list.__getitem__ if isinstance(obj, list) else tuple.__getitem__
        n = list.__len__(obj) if isinstance(obj, list) else tuple.__len__(obj)
        out.extend((f"[{i}]", get(obj, i)) for i in range(n))
    elif isinstance(obj, (set, frozenset)):
        out.extend((f"{{{i}}}", v) for i, v in enumerate(sorted(obj, key=repr)))
    elif isinstance(obj, dict):
        for i, (key, v) in enumerate(list(dict.items(obj))):
            out.append((f"<key {i}>", key))
            out.append((f"[{key!r}]", v))
    elif isinstance(obj, types.MappingProxyType):
        for key, v in obj.items():
            out.append((f"[{key!r}]", v))
    return out


def _walk(root):
    """Every state object reachable from `root`, breadth first, with a path;
    the order is fixed by the run (names sorted, items in order)."""
    seen = {id(root)}
    order = [("ctx", root)]
    frontier = [("ctx", root)]
    while frontier:
        nxt = []
        for path, obj in frontier:
            for label, child in _children(obj):
                # a bound method is code; what it is bound to is state
                if isinstance(child, (types.MethodType, types.BuiltinMethodType)):
                    child = getattr(child, "__self__", None)
                    label += ".__self__"
                    if child is None:
                        continue
                if isinstance(child, types.FunctionType) and child.__closure__:
                    pass  # a closure's cells are state: walked through the function
                elif not _is_state(child):
                    continue
                if id(child) in seen:
                    continue
                seen.add(id(child))
                order.append((path + label, child))
                nxt.append((path + label, child))
        frontier = nxt
    return order


# --- the attacks -------------------------------------------------------------------

def _forged_items():
    ghost = OrderView(request=OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="ghost"),
                      state=OrderState.FILLED, sent_time_ns=T0, last_update_ns=T0, acked=True,
                      filled_size=1.0, avg_fill_price=1.0, fees=-50.0)
    forced = OrderRequest("buy", "limit", 1.0, price=90.0, client_order_id="forced-9")
    future = TradeEvent(received_time_ns=T0 + 10_000 * SEC, price=1.0, size=1.0, side="buy")
    return [
        ("None", None),
        ("int time", T0 + 10_000 * SEC),
        ("FILLED view", ghost),
        ("forced-id request", forced),
        ("future event", future),
        ("outbox-like message", ("new", forced, T0)),
        ("str", "x"),
    ]


CALLED: list = []  # set when anything calls a method the attack put on an object


def _raiser(*_a, **_k):
    CALLED.append(1)
    raise AssertionError("a method the strategy put on its object was called")


def _attacks(obj):
    """(name, action) for every way of changing `obj` (module docstring)."""
    out = []
    items = _forged_items()
    if isinstance(obj, list):
        for fname, f in items:
            out.append((f"list.append {fname}", lambda f=f: list.append(obj, f)))
            out.append((f"list.insert 0 {fname}", lambda f=f: list.insert(obj, 0, f)))
            if list.__len__(obj):
                out.append((f"list[0] = {fname}", lambda f=f: list.__setitem__(obj, 0, f)))
        if list.__len__(obj):
            out.append(("del list[0]", lambda: list.__delitem__(obj, 0)))
        out.append(("list.clear", lambda: list.clear(obj)))
        out.append(("list.reverse", lambda: list.reverse(obj)))
    elif isinstance(obj, dict):
        keys = list(dict.keys(obj))
        for fname, f in items:
            out.append((f"dict[new] = {fname}", lambda f=f: dict.__setitem__(obj, "ghost", f)))
            if keys:
                out.append((f"dict[first] = {fname}", lambda f=f: dict.__setitem__(obj, keys[0], f)))
        if keys:
            out.append(("dict.pop first", lambda: dict.pop(obj, keys[0])))
        out.append(("dict.clear", lambda: dict.clear(obj)))
    elif isinstance(obj, set):
        out.append(("set.add", lambda: set.add(obj, "x")))
        out.append(("set.clear", lambda: set.clear(obj)))
    for name in _attr_names(obj):
        for fname, f in items:
            out.append((f"set .{name} = {fname}", lambda name=name, f=f: object.__setattr__(obj, name, f)))
        out.append((f"del .{name}", lambda name=name: object.__delattr__(obj, name)))
    if isinstance(getattr(obj, "__dict__", None), dict) and not isinstance(obj, types.FunctionType):
        for name in sorted(n for n in dir(type(obj)) if callable(getattr(type(obj), n, None))
                           and not (n.startswith("__") and n.endswith("__"))):
            out.append((f"shadow .{name}()", lambda name=name: obj.__dict__.__setitem__(name, _raiser)))
    return out


def _targets(ctx):
    """Every reachable state object, in walk order (the outbox is left out
    of the first grid by its path, `_grid`)."""
    return _walk(ctx)


# --- helpers for the oracle ----------------------------------------------------

def _prefix(short: list, long: list) -> bool:
    return len(short) <= len(long) and long[:len(short)] == short


def _judge(base, got) -> str | None:
    """None if `got` keeps the rule against `base` (module docstring)."""
    kind, payload, rec, _strat = got
    _bk, bres, brec, _bs = base
    if rec.called:
        return "a method the attack put on an object was called (the core read the object's attribute)"
    if kind == "ok":
        if payload != bres:
            diff = [k for k in bres if payload.get(k) != bres[k]]
            return f"result differs in {diff}"
        if rec.logs != brec.logs:
            diff = [w for w in set(brec.logs) | set(rec.logs) if rec.logs.get(w) != brec.logs.get(w)]
            return f"receivers differ: {sorted(diff)}"
        if rec.delivered != brec.delivered:
            return "the delivered stream differs"
        return None
    if not (isinstance(payload, CoreError) or getattr(payload, "_bt0_from_strategy", False)):
        return f"the core itself failed on what the strategy changed: {type(payload).__name__}: {payload}"
    for who, lst in rec.logs.items():
        if not _prefix(lst, brec.logs.get(who, [])):
            return f"raised {type(payload).__name__}, but {who} saw what the unattacked run did not"
    if not _prefix(rec.delivered, brec.delivered):
        return f"raised {type(payload).__name__}, but the delivered stream is not a prefix"
    return None


# --- finding the outbox by behaviour ---------------------------------------------

def _mark_outbox():
    """Run once and mark (by a flag attribute on the test's side, never the
    core's) nothing: the outbox is the list that grows by exactly one when
    the strategy calls place_order. Returns its path in the walk."""
    found = {}

    def extra(k, ctx):
        if k != WALK_AT:
            return
        before = {id(o): (p, list.__len__(o)) for p, o in _walk(ctx) if isinstance(o, list)}
        ctx.place_order(OrderRequest("buy", "limit", 1.0, price=1.0, client_order_id="probe"))
        after = {id(o): (p, list.__len__(o)) for p, o in _walk(ctx) if isinstance(o, list)}
        found["paths"] = sorted(after[i][0] for i in after if i in before and after[i][1] == before[i][1] + 1)

    _run(extra=extra)
    return found["paths"]


OUTBOX_PATHS = None


def _outbox_paths():
    global OUTBOX_PATHS
    if OUTBOX_PATHS is None:
        OUTBOX_PATHS = _mark_outbox()
    return OUTBOX_PATHS


def _grid(walk_at: int):
    survey: list = []
    _run(survey=(walk_at, survey))
    outbox = _outbox_paths()
    # the outbox and the messages in it are what the strategy SENT: its own grid below
    return [(i, path, tname, names) for i, (path, tname, names) in enumerate(survey)
            if not any(path == p or path.startswith(p + "[") for p in outbox)]


def test_the_outbox_is_found_by_behaviour_and_is_one_list():
    paths = _outbox_paths()
    assert len(paths) == 1, paths


@pytest.mark.parametrize("when", sorted(TIMINGS))
def test_nothing_the_strategy_can_reach_changes_what_the_core_decides_sends_or_reports(when):
    base = _run()
    assert base[0] == "ok", base[1]
    assert base[1]["events_processed"] == 36  # the script's callback numbers hold
    grid = _grid(TIMINGS[when][0])
    cells = sum(len(names) for _i, _p, _t, names in grid)
    kinds = sorted({t for _i, _p, t, _n in grid})
    print(f"\n[{when}] targets {len(grid)} ({', '.join(kinds)}), cells {cells}")
    assert cells < 100_000  # every cell is run (LEAD_DESIGN s7.2 12)
    bad = []
    refused_at_write = 0
    ran = 0
    for ti, path, tname, names in grid:
        for ai, aname in enumerate(names):
            got = _run(attack=(when, ti, ai))
            ran += 1
            if got[3].outcome and got[3].outcome.startswith("refused"):
                refused_at_write += 1
            why = _judge(base, got)
            if why is not None:
                bad.append((path, tname, aname, why))
    print(f"[{when}] ran {ran}, refused at the write {refused_at_write}, broke the rule {len(bad)}")
    assert ran == cells
    assert not bad, "\n".join(map(str, bad[:15])) + f"\n... {len(bad)} in all"


# --- the outbox's own grid ------------------------------------------------------------

def _box(ctx):
    [path] = _outbox_paths()
    for p, o in _walk(ctx):
        if p == path:
            return o
    raise AssertionError("outbox not reachable")


def _equivalent_api_call(kind: str):
    """The API call whose effect a message of the rule must have."""
    if kind == "new ok":
        return lambda ctx: ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="m1"))
    if kind == "cancel ok":
        return lambda ctx: ctx.cancel_order("a1")
    if kind == "timer ok":
        return lambda ctx: ctx.set_timer(ctx.now_ns + 300 * MS, "mt")
    raise KeyError(kind)


def _message(kind: str, now: int):
    """A message written straight into the outbox (no port method)."""
    ok_new = OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="m1")

    class StrLying(str):
        def __eq__(self, other):
            return True

        __hash__ = str.__hash__

    class ReqSub(OrderRequest):
        __slots__ = ()

    table = {
        "new ok": ("new", ok_new, now),
        "cancel ok": ("cancel", CancelRequest("a1"), now),
        "timer ok": ("timer", now + 300 * MS, "mt"),
        "new forced id": ("new", OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="forced-7"), now),
        "new empty id": ("new", OrderRequest("buy", "limit", 1.0, price=95.0), now),
        "new duplicate of a placed id": ("new", OrderRequest("buy", "limit", 1.0, price=95.0,
                                                              client_order_id="a1"), now),
        "new request subclass": ("new", ReqSub("buy", "limit", 1.0, price=95.0, client_order_id="m2"), now),
        "new payload not a request": ("new", "an order", now),
        "cancel unknown id": ("cancel", CancelRequest("never"), now),
        "cancel payload a str": ("cancel", "a1", now),
        "timer before now": ("timer", now - 1, "back"),
        "timer not an int": ("timer", float(now + SEC), "f"),
        "timer tag not a str": ("timer", now + SEC, 5),
        "kind unknown": ("xyz", ok_new, now),
        "kind a lying str": (StrLying("zzz"), ok_new, now),
        "kind not a str": (1, ok_new, now),
        "tuple of two": ("new", ok_new),
        "tuple of four": ("new", ok_new, now, None),
        "not a tuple": ["new", ok_new, now],
        "None": None,
    }
    return table[kind]


OK_MESSAGES = ["new ok", "cancel ok", "timer ok"]
BAD_MESSAGES = ["new forced id", "new empty id", "new duplicate of a placed id", "new request subclass",
                "new payload not a request", "cancel unknown id", "cancel payload a str", "timer before now",
                "timer not an int", "timer tag not a str", "kind unknown", "kind a lying str", "kind not a str",
                "tuple of two", "tuple of four", "not a tuple", "None"]
TIMES = sorted(TIMINGS)  # the same timings as the first grid


@pytest.mark.parametrize("when", TIMES)
@pytest.mark.parametrize("kind", OK_MESSAGES)
def test_a_message_by_the_api_rules_has_the_effect_of_the_api_call(kind, when):
    walk_at, at = TIMINGS[when]
    kept = {}

    def via_box(k, ctx):
        if k == walk_at:
            kept["box"] = _box(ctx)
        if k == at:
            list.append(kept["box"], _message(kind, ctx.now_ns))

    def via_api(k, ctx):
        if k == at:
            _equivalent_api_call(kind)(ctx)

    got, want = _run(extra=via_box), _run(extra=via_api)
    assert want[0] == "ok", want[1]
    assert got[0] == "ok", got[1]
    assert got[1] == want[1]
    assert got[2].logs == want[2].logs
    assert got[2].delivered == want[2].delivered


@pytest.mark.parametrize("when", TIMES)
@pytest.mark.parametrize("kind", BAD_MESSAGES)
def test_a_message_against_the_api_rules_is_refused_before_anything_is_sent(kind, when):
    walk_at, at = TIMINGS[when]
    kept = {}

    def via_box(k, ctx):
        if k == walk_at:
            kept["box"] = _box(ctx)
        if k == at:
            list.append(kept["box"], _message(kind, ctx.now_ns))

    base = _run()
    got = _run(extra=via_box)
    assert got[0] == "raised" and isinstance(got[1], CoreError), (got[0], got[1])
    assert _judge(base, got) is None


# a field of the request inside a message, changed after place_order put it
# there and before the callback returned (object.__setattr__ on its slot)
CONTENT_OK = {  # -> the place_order call that has the same effect
    "size 2.0": ("size", 2.0),
    "side sell": ("side", "sell"),
    "price None": ("price", None),
    "id m9": ("client_order_id", "m9"),
    "extra": ("extra", (("k", 1),)),
}
CONTENT_BAD = {
    "side up": ("side", "up"),
    "size 0": ("size", 0.0),
    "size a str": ("size", "1"),
    "id forced": ("client_order_id", "forced-3"),
    "id empty": ("client_order_id", ""),
    "id a1 (placed)": ("client_order_id", "a1"),
    "extra not pairs": ("extra", ("k",)),
    "size deleted": ("size", None),  # deleted, below
}


def _place_m1(ctx, **change):
    fields = dict(side="buy", order_type="limit", size=1.0, price=95.0, client_order_id="m1")
    fields.update(change)
    return ctx.place_order(OrderRequest(**fields))


@pytest.mark.parametrize("when", TIMES)
@pytest.mark.parametrize("case", sorted(CONTENT_OK))
def test_a_message_changed_before_the_callback_returned_is_what_was_sent(case, when):
    """The core reads the outbox when the callback returns: a request the
    strategy changed in its message before that is what it sent -- the
    effect of placing the changed request, by the API's rules."""
    walk_at, at = TIMINGS[when]
    name, value = CONTENT_OK[case]
    kept = {}

    def changed(k, ctx):
        if k == walk_at:
            kept["box"] = _box(ctx)
        if k == at:
            _place_m1(ctx)
            msg = list.__getitem__(kept["box"], -1)
            object.__setattr__(msg[1], name, value)

    def via_api(k, ctx):
        if k == at:
            _place_m1(ctx, **{name: value})

    got, want = _run(extra=changed), _run(extra=via_api)
    assert want[0] == "ok", want[1]
    assert got[0] == "ok", got[1]
    assert got[1] == want[1] and got[2].logs == want[2].logs and got[2].delivered == want[2].delivered


@pytest.mark.parametrize("when", TIMES)
@pytest.mark.parametrize("case", sorted(CONTENT_BAD))
def test_a_message_changed_against_the_api_rules_is_refused(case, when):
    walk_at, at = TIMINGS[when]
    name, value = CONTENT_BAD[case]
    kept = {}

    def changed(k, ctx):
        if k == walk_at:
            kept["box"] = _box(ctx)
        if k == at:
            _place_m1(ctx)
            msg = list.__getitem__(kept["box"], -1)
            if case == "size deleted":
                object.__delattr__(msg[1], name)
            else:
                object.__setattr__(msg[1], name, value)

    base = _run()
    got = _run(extra=changed)
    assert got[0] == "raised" and isinstance(got[1], CoreError), (got[0], got[1])
    assert _judge(base, got) is None


@pytest.mark.parametrize("when", TIMES)
def test_removing_a_sent_message_is_not_sending_it(when):
    """The outbox is the strategy's message until the callback returns:
    taking one back is not sending it (as if the call had not been made);
    the core invents nothing in its place."""
    walk_at, at = TIMINGS[when]
    kept = {}

    def placed_then_taken_back(k, ctx):
        if k == walk_at:
            kept["box"] = _box(ctx)
        if k == at:
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="m1"))
            list.pop(kept["box"])

    base = _run()
    got = _run(extra=placed_then_taken_back)
    assert got[0] == "ok", got[1]
    assert got[1] == base[1] and got[2].logs == base[2].logs and got[2].delivered == base[2].delivered


@pytest.mark.parametrize("when", TIMES)
@pytest.mark.parametrize("case", ["registry cleared, then a placed id again",
                                  "counter reset, then an engine-named id again",
                                  "a placed message's id changed to a forced id"])
def test_the_port_s_own_answer_does_not_decide_what_is_sent(case, when):
    """The port answers the strategy from its OWN copies (a strategy that
    breaks them before calling it changes that answer); what is sent is
    decided again by the core against its book: a duplicate or a reserved
    id is refused before anything is sent, whatever the port answered."""
    walk_at, at = TIMINGS[when]
    kept = {}

    def attack(k, ctx):
        if k == walk_at:
            [kept["port"]] = find(ctx, _OrderPort)
        if k == at:
            port = kept["port"]
            reg = object.__getattribute__(port, "_registry")
            if case.startswith("registry cleared"):
                dict.clear(reg)
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="a1"))
            elif case.startswith("counter reset"):
                object.__setattr__(port, "_counter", 0)
                dict.clear(reg)
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0))  # names core-1 again
            else:  # the port accepted "ok-id"; the message is changed to a reserved id before the return
                ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="ok-id"))
                msg = list.__getitem__(object.__getattribute__(port, "_outbox"), -1)
                object.__setattr__(msg[1], "client_order_id", "forced-5")

    base = _run()
    got = _run(extra=attack)
    assert got[0] == "raised" and isinstance(got[1], CoreError), (got[0], got[1])
    assert _judge(base, got) is None


def test_a_replaced_outbox_is_refused():
    """The core reads its own outbox, never the port's attribute: a port
    whose outbox attribute was replaced (its later sends would go nowhere)
    is refused, not silently ignored."""
    def replace(k, ctx):
        if k == WALK_AT:
            [path] = _outbox_paths()
            owner_path, _, name = path.rpartition(".")
            owner = dict(_walk(ctx))[owner_path]
            object.__setattr__(owner, name, [])
            ctx.place_order(OrderRequest("buy", "limit", 1.0, price=95.0, client_order_id="m1"))

    base = _run()
    got = _run(extra=replace)
    assert got[0] == "raised" and isinstance(got[1], CoreError), got[:2]
    assert _judge(base, got) is None


# --- the structural check: the context reaches none of the core's own state ----------

def _one_per_value(obj) -> bool:
    """An object the interpreter keeps one of per value (the empty tuple,
    say), asked by building its value again: sharing it is not sharing."""
    if type(obj) in (tuple, frozenset):
        return type(obj)(list(obj)) is obj
    return False


def test_nothing_reachable_from_a_context_is_part_of_the_core_s_own_state():
    """The engine's decision state (its order book, venue ledger, queue,
    source merger, request / fill / forced lists, history facts, channels)
    shares no object with what any context reaches, at every callback."""
    engines = []
    problems = []

    def check(k, ctx):
        eng = engines[0]
        reach = {id(o) for _p, o in _walk(ctx)}
        own = []
        for name in ("_book", "_ledger", "_heap", "_merger", "_pending_by_stream", "_scheduled", "_forced",
                     "_forced_list", "_order_requests", "_cancel_requests", "_fills", "_outbound", "_notices"):
            if hasattr(eng, name):
                own.extend(o for _p, o in _walk(getattr(eng, name)))
        hist = getattr(eng, "_history")
        for name in ("_facts", "_overall_facts", "dropped", "dropped_count"):
            if hasattr(hist, name):
                own.extend(o for _p, o in _walk(getattr(hist, name)))
        shared = [type(o).__name__ for o in own if id(o) in reach and _is_state(o) and not _one_per_value(o)]
        if shared:
            problems.append((k, sorted(set(shared))))

    rec = _Rec()
    strat = _Strategy(rec, extra=check)
    eng = CoreEngine(strat, _events(), fill_model=_Venue(rec), latency_model=_Latency(rec),
                     cost_model=_Cost(rec), account=_Account(rec), history_limit=2)
    engines.append(eng)
    eng.run()
    assert hasattr(eng, "_book"), "the engine keeps no order book of its own"
    assert not problems, problems[:5]
