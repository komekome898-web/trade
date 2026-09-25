"""What a strategy can see and do.

A strategy is called once per delivered event with a `StrategyContext`.
The context is the strategy's only handle on the run:

* `now_ns`, `current_event`, `visible_events(...)`, `last(...)` -- read
  the history of events already delivered to it (all with
  `received_time_ns <= now_ns`); any time argument after `now_ns` (the
  start or the end of a window) raises `LookAheadError`, and naming a
  position outside an answer raises, by what that position is in what the
  read reads (window.py): `FuturePositionError` (a `LookAheadError`) for
  an event not delivered yet, `OutsideAnswerError` (or its
  `DroppedPositionError` / `BeforeFirstEventError`) for the past --
  rather than returning a silently empty or truncated answer;
* `place_order`, `cancel_order`, `set_timer` -- act;
* `order(id)`, `open_orders()` -- its own orders, as it knows them.

Structural guarantees (tested in tests/bt/item_0/test_bt0_lookahead.py and
tests/bt/item_0/test_bt0_api_surface.py):

* No path to the future. The history view is backed by the list of events
  already delivered; the engine appends to it only between callbacks. The
  context holds no mutable object (round 9, LEAD_DESIGN s3.4): values, the
  frozen current event, windows that hold none either (window.py), and
  functions -- the history lists are reached only inside the windows'
  reading functions, and the order functions close over the methods of
  `_OrderPort`, an object that holds only the strategy's OWN copies of its
  order views and its outbox -- not the engine, not the core's order book,
  not the event source, not the pending queue. So nothing reachable from a
  context, even through private attributes or functions' closures, holds an
  event the strategy has not received yet. Scope of
  this guarantee: the context and what is reachable from it by attribute
  access. It does NOT cover introspecting the interpreter: the strategy is
  called inside the engine's own process and call (`CoreEngine.step`), so
  `sys._getframe()` / `inspect.stack()` / `gc.get_objects()` reach the
  engine and its queue. The core does not sandbox strategy code; a
  strategy that does this is outside the contract
  (`CORE_CONTRACT["visibility"]["scope"]`).
* Nothing the strategy can reach decides anything of the core's (round 9,
  i0-r8-01; `CORE_CONTRACT["channel_payloads"]["ownership"]`). The facts
  of the strategy's orders live in the core's own `_OrderBook`, which no
  context reaches; the port's registry holds the strategy's own copies
  (what `order()` / `open_orders()` return), each a new object the core
  writes at every change and never reads back. The one thing the core reads from
  what the strategy can reach is the outbox -- the messages it sent --
  once, when the callback returns, as the arguments of API calls: the
  core applies every rule of `place_order` / `cancel_order` / `set_timer`
  again, against its own book and its own time (`check_new_id`,
  `check_timer`), so a message written into the outbox around the port
  has exactly the effect of the API call, or is refused.
* No acting later. The engine revokes the context when the callback
  returns; any later attempt to read history or act raises
  `StaleContextError`, and the history view drops its backing list.
  (`now_ns` / `current_event` stay readable: they describe the instant
  the context was built for and reveal nothing later.) What was sent
  cannot be changed afterwards either: an `OrderRequest` is a value down
  to every field (each made the built-in type itself when the request is
  made, `extra` immutable plain data, values.py), `place_order` takes the
  class itself (not a subclass), and the engine takes the request from the
  outbox when the callback returns, makes it again (`fresh_request`) and
  hands every receiver a copy of its own (engine.py), so nothing the
  strategy keeps -- or reaches through private attributes -- is shared
  with the venue.
* The strategy's view of its orders moves only when it acts or when a
  notice is delivered to it. It never sees the venue's state directly: an
  order it placed is PENDING_NEW until the ACK notice arrives, however long
  the latency model says that takes.
* The view is kept as FACTS (acknowledged? filled size? how many cancels
  of ours await their answers? an ambiguous answer about the new order or
  about a cancel? a final state?) and `state` is derived from them
  (`_derive_state`). Cancels are counted one by one: the venue answers each
  cancel exactly once (engine.py refuses a fill model that answers one with
  none or two), the channels are FIFO, and each answer (a cancel reject, an
  ambiguous cancel, or an ORDER_CANCELED with `answers == "cancel"`)
  takes one off `cancels_in_flight`; `cancel_pending` is "at least one". STATE_UNKNOWN is held until a notice that settles it
  arrives -- for an ambiguous new order: ACK, new-order reject, a fill or
  CANCELED; for an ambiguous cancel: CANCELED or the last fill. Nothing the
  strategy does (sending a cancel) and no cancel reject clears it.
"""
from __future__ import annotations

import bisect
import dataclasses
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Sequence, Union

from .errors import HistoryTruncatedError, LookAheadError, OrderApiError, StaleContextError
from .events import (
    ORDER_SIDES,
    Event,
    EventType,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderStateUnknownEvent,
)
from .time import Nanos, validate_nanos
from .values import (
    as_choice,
    as_flag,
    as_float,
    as_int,
    as_text,
    copy_carrier,
    freeze,
    int_text,
    is_a,
    rebuild_carrier,
    renew,
    thaw,
    type_name,
    value_text,
)
from .history import dropped_before, dropped_in_range
from .window import DeliveredEvents, EventWindow


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """An order as the strategy (or the account socket) sends it. It crosses
    the strategy -> venue path and is read at the venue LATER, so it is a
    value down to every field (values.py): made at construction by the
    values.py functions -- `str`, `float`, `bool` themselves and immutable
    plain data in `extra` -- and slotted, so nothing can be attached."""

    side: str  # "buy" | "sell"
    order_type: str  # "market" | "limit" | ... -- the set is item 2's to define
    size: float
    price: Optional[float] = None
    client_order_id: str = ""
    time_in_force: str = "GTC"  # the set is item 2's to define; a non-empty str
    post_only: bool = False
    reduce_only: bool = False
    trigger_price: Optional[float] = None
    # anything else a venue model needs, as (key, value) pairs of plain data
    # (values.py). Made immutable here, when the request is made: what the
    # venue receives at the arrival time is what was sent (i0-r4-02).
    extra: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        put = lambda name, value: object.__setattr__(self, name, value)  # noqa: E731
        put("side", _order_field(as_choice, "side", self.side, ORDER_SIDES))
        order_type = _order_field(as_text, "order_type", self.order_type)
        if not order_type:
            raise OrderApiError("order_type must be a non-empty str")
        put("order_type", order_type)
        put("size", _require_positive("size", self.size))
        if self.price is not None:
            put("price", _require_positive("price", self.price))
        if self.trigger_price is not None:
            put("trigger_price", _require_positive("trigger_price", self.trigger_price))
        put("client_order_id", _order_field(as_text, "client_order_id", self.client_order_id))
        tif = _order_field(as_text, "time_in_force", self.time_in_force)
        if not tif:
            raise OrderApiError("time_in_force must be a non-empty str")
        put("time_in_force", tif)
        put("post_only", _order_field(as_flag, "post_only", self.post_only))
        put("reduce_only", _order_field(as_flag, "reduce_only", self.reduce_only))
        put("extra", _frozen_extra(self.extra))

    def extra_dict(self) -> dict:
        """`extra` as a fresh dict, lists / dicts / sets as they were given,
        a dict key or a set element as the core's immutable copy of what was
        given there (it has a hash; values.py `thaw`, round 17); changing it
        changes nothing else."""
        return {key: thaw(value) for key, value in self.extra}


def _order_field(make: Callable[..., Any], name: str, value: Any, *args: Any) -> Any:
    """One field of an order request made by a values.py function; its
    refusal is an OrderApiError."""
    try:
        return make(value, name, *args)
    except ValueError as exc:
        raise OrderApiError(str(exc)) from None


def _frozen_extra(extra: Any) -> tuple:
    """The one check of `OrderRequest.extra`, at construction: a tuple of
    (non-empty str key, plain data value) pairs with no key twice, made
    deeply immutable (values.py)."""
    # decided by the REAL type and read by tuple's own methods (values.py
    # `is_a`): an object claiming to be a tuple, or a tuple subclass with
    # its own iteration, does not decide what the pairs are
    if not is_a(extra, tuple):
        raise OrderApiError(f"extra must be a tuple of (key, value) pairs, got {type_name(extra)}")
    pairs = []
    seen: set = set()
    for i, pair in enumerate(tuple.__getitem__(extra, slice(None))):
        if not is_a(pair, tuple) or tuple.__len__(pair) != 2:
            raise OrderApiError(f"extra[{i}] must be a (key, value) pair, got a {type_name(pair)}")
        key, value = tuple.__getitem__(pair, 0), tuple.__getitem__(pair, 1)
        key = _order_field(as_text, f"extra[{i}] key", key)  # a str itself before anything reads it
        if not key:
            raise OrderApiError(f"extra[{i}]: key must be a non-empty str, got {key!r}")
        if key in seen:
            raise OrderApiError(f"extra: key {key!r} given twice")
        seen.add(key)
        try:
            # the pair's value sits in extra's tuple and its pair: 2 containers of the field
            pairs.append((key, freeze(value, f"extra[{key!r}]", outer=2)))
        except ValueError as exc:
            raise OrderApiError(str(exc)) from None
    return tuple(pairs)


@dataclass(frozen=True, slots=True)
class CancelRequest:
    client_order_id: str

    def __post_init__(self) -> None:
        coid = _order_field(as_text, "client_order_id", self.client_order_id)
        if not coid:
            raise OrderApiError("client_order_id must be a non-empty str")
        object.__setattr__(self, "client_order_id", coid)


def fresh_request(request: Any, cls: type, error: type, who: str) -> Any:
    """What the core hands on across the strategy -> venue path (and from
    the account socket to the strategy's view): an instance of the core's
    own request class, never a subclass (a subclass could decide a field
    when it is read), rebuilt from its fields, so the receiver holds an
    object the sender does not (it cannot be changed afterwards, even by
    bypassing `frozen`). A request whose slots were broken after it was made
    (a field deleted or set to what the class refuses) is refused as
    `error`, never a core crash."""
    if type(request) is not cls:
        # the real type named by values.type_name: no code of its class,
        # metaclass or dict keys runs (round 12)
        raise error(f"{who} takes a {cls.__name__} itself (not a subclass), got {type_name(request)}")
    try:
        return rebuild_carrier(request)
    except error:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise error(f"{who}: the {cls.__name__} cannot be made again from its fields: {exc}") from None


def _require_positive(name: str, value: Any) -> float:
    f = _order_field(as_float, name, value)  # the one number rule (values.py), never a bool
    if not math.isfinite(f) or f <= 0:
        raise OrderApiError(f"{name} must be finite and > 0, got {float.__repr__(f)}")
    return f


class OrderState(Enum):
    PENDING_NEW = "PENDING_NEW"  # sent, no answer received yet
    OPEN = "OPEN"  # acknowledged, not fully filled
    PENDING_CANCEL = "PENDING_CANCEL"  # cancel sent, no answer received yet
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    STATE_UNKNOWN = "STATE_UNKNOWN"  # ambiguous answer; held, never resent


FORCED_ID_PREFIX = "forced-"  # client_order_id prefix reserved for the account socket's forced orders

OPEN_STATES = frozenset(
    {OrderState.PENDING_NEW, OrderState.OPEN, OrderState.PENDING_CANCEL, OrderState.STATE_UNKNOWN}
)

_FILL_EPS = 1e-12

FINAL_STATES = frozenset({OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED})


def _derive_state(view: "OrderView") -> OrderState:
    """The state shown to the strategy, from the view's facts. A final
    state is kept; otherwise an unsettled ambiguous answer wins over
    everything (CLAUDE.md section 1: STATE_UNKNOWN is held until
    resolved), then a cancel awaiting its answer, then acknowledged."""
    if view.state in FINAL_STATES:
        return view.state
    if view.unknown_new or view.unknown_cancel:
        return OrderState.STATE_UNKNOWN
    if view.cancels_in_flight > 0:
        return OrderState.PENDING_CANCEL
    return OrderState.OPEN if view.acked else OrderState.PENDING_NEW


@dataclass(frozen=True)
class OrderView:
    """The strategy's knowledge of one of its orders."""

    request: OrderRequest
    state: OrderState
    sent_time_ns: int
    last_update_ns: int
    acked: bool = False
    filled_size: float = 0.0
    avg_fill_price: Optional[float] = None
    fees: float = 0.0
    venue_order_id: str = ""
    reason: str = ""
    origin: str = "strategy"  # "strategy" = placed by the strategy; "forced" = by the account socket
    # cancels of ours sent and not answered yet (one fact per cancel, not one
    # per order: with two in flight, the answer to the first leaves one)
    cancels_in_flight: int = 0
    unknown_new: bool = False  # an ambiguous answer about the new order, not settled yet
    unknown_cancel: bool = False  # an ambiguous answer about a cancel, not settled yet

    @property
    def cancel_pending(self) -> bool:
        """A cancel of ours was sent and has no answer yet."""
        return self.cancels_in_flight > 0

    @property
    def client_order_id(self) -> str:
        return self.request.client_order_id

    @property
    def remaining_size(self) -> float:
        return max(self.request.size - self.filled_size, 0.0)

    @property
    def is_open(self) -> bool:
        return self.state in OPEN_STATES


def copy_view(view: OrderView) -> OrderView:
    """A new copy of an order view for one receiver (the strategy, on every
    `order()` / `open_orders()`; the caller's result): the request copied
    (values.py `copy_carrier`), every other field built anew (the state is
    an Enum member: one object). What a receiver does to it reaches no one."""
    fields = {f.name: getattr(view, f.name) for f in dataclasses.fields(view)}
    fields["request"] = copy_carrier(fields["request"])
    for name, v in fields.items():
        if name not in ("request", "state"):
            fields[name] = renew(v)
    return OrderView(**fields)


def _fresh_view(view: OrderView) -> OrderView:
    """A new OrderView object with the same fields, for one answer of
    `order()` / `open_orders()`: what the strategy does to it (bypassing
    `frozen`) reaches no other answer. The fields are values; the request is
    the strategy's own copy (frozen and slotted, made by `copy_view` when the
    core wrote the view)."""
    out = object.__new__(OrderView)
    out.__dict__.update(view.__dict__)
    return out


def _new_view(request: OrderRequest, now: int, origin: str = "strategy") -> OrderView:
    return OrderView(request=request, state=OrderState.PENDING_NEW, sent_time_ns=now, last_update_ns=now,
                     origin=origin)


def _view_after_cancel(view: OrderView, now: int) -> OrderView:
    """Every cancel is answered by the venue exactly once (the engine
    answers one for an order that is not live there), so it is counted
    even for an order already final in this view."""
    view = dataclasses.replace(view, cancels_in_flight=view.cancels_in_flight + 1, last_update_ns=now)
    return dataclasses.replace(view, state=_derive_state(view))


def _view_after_notice(view: OrderView, event: Event, t: int) -> OrderView:
    """The facts of one order after a delivered notice (delivered at `t`),
    then its derived state. Nothing here guesses a previous state."""
    coid = view.client_order_id
    final: Optional[OrderState] = None
    if _answers_cancel(event):
        # channels are FIFO, so the k-th answer answers the k-th cancel
        if view.cancels_in_flight < 1:  # pragma: no cover - engine invariant
            raise RuntimeError(f"an answer to a cancel of {coid!r} with no cancel in flight")
        view = dataclasses.replace(view, cancels_in_flight=view.cancels_in_flight - 1)
    if isinstance(event, OrderAckEvent):
        view = dataclasses.replace(view, acked=True, unknown_new=False, venue_order_id=event.venue_order_id)
    elif isinstance(event, OrderRejectEvent):
        if event.request_kind == "new":
            final = OrderState.REJECTED
        # a cancel reject answers our cancel; it says nothing that settles
        # an ambiguous answer about the order
        view = dataclasses.replace(view, reason=event.reason)
    elif isinstance(event, OrderFillEvent):
        filled = view.filled_size + event.size
        prev_notional = (view.avg_fill_price or 0.0) * view.filled_size
        avg = (prev_notional + event.price * event.size) / filled
        # a fill proves the order exists at the venue (settles an
        # ambiguous new order), not whether a cancel took effect
        view = dataclasses.replace(
            view, acked=True, unknown_new=False, filled_size=filled, avg_fill_price=avg,
            fees=view.fees + event.fee,
        )
        if filled >= view.request.size * (1 - _FILL_EPS):
            final = OrderState.FILLED
    elif isinstance(event, OrderCanceledEvent):
        final = OrderState.CANCELED
        view = dataclasses.replace(view, reason=event.reason)
    elif isinstance(event, OrderStateUnknownEvent):
        if event.request_kind == "cancel":
            view = dataclasses.replace(view, unknown_cancel=True, reason=event.detail)
        else:
            view = dataclasses.replace(view, unknown_new=True, reason=event.detail)
    else:  # pragma: no cover - engine only routes notices here
        raise TypeError(type(event).__name__)
    if final is not None and view.state not in FINAL_STATES:
        # a final state settles every ambiguity; cancels still in flight
        # stay counted until their answers arrive
        view = dataclasses.replace(view, state=final, unknown_new=False, unknown_cancel=False)
    view = dataclasses.replace(view, last_update_ns=t)
    return dataclasses.replace(view, state=_derive_state(view))


def check_new_id(coid: str, known: Callable[[str], bool]) -> None:
    """THE rule for the id of a new order, applied by `place_order` (against
    the strategy's copies, to answer at once) and again by the core when it
    takes the order from the outbox (against its own book, engine.py): not
    the prefix reserved for forced orders, not an id already used."""
    if coid.startswith(FORCED_ID_PREFIX):
        raise OrderApiError(
            f"client_order_id {coid!r}: the prefix {FORCED_ID_PREFIX!r} is reserved "
            f"for forced orders from the account socket"
        )
    if known(coid):
        raise OrderApiError(f"duplicate client_order_id {coid!r}")


def check_timer(at_ns: Any, tag: Any, now: int) -> tuple[int, str]:
    """THE rule for a timer, applied by `set_timer` and again by the core
    when it takes the timer from the outbox (against the callback's time):
    an int64 of ns not before now, and a tag that is a str (it reaches the
    strategy later, in a ClockEvent)."""
    at = int(validate_nanos(at_ns))
    if at < now:
        raise OrderApiError(f"timer at {at} is before now {now}")
    return at, _order_field(as_text, "timer tag", tag)


class _OrderBook:
    """The core's OWN record of the strategy's orders: the facts of every
    order the core took from the outbox and of every forced order the
    strategy was told of. Held by the engine only -- no context, port or
    receiver reaches it -- so what the strategy changes in what it can
    reach changes nothing here (round 9, i0-r8-01). The engine derives
    from it the strategy's copies (the port's registry) and the caller's
    result."""

    __slots__ = ("_views",)

    def __init__(self) -> None:
        self._views: dict[str, OrderView] = {}

    def knows(self, client_order_id: str) -> bool:
        return client_order_id in self._views

    def view(self, client_order_id: str) -> OrderView:
        return self._views[client_order_id]

    def items(self):
        return self._views.items()

    def add(self, request: OrderRequest, now: int, origin: str = "strategy") -> None:
        coid = request.client_order_id
        if coid in self._views:  # pragma: no cover - the engine checks ids first (check_new_id)
            raise OrderApiError(f"duplicate client_order_id {coid!r}")
        self._views[coid] = _new_view(request, now, origin)

    def cancel(self, client_order_id: str, now: int) -> None:
        self._views[client_order_id] = _view_after_cancel(self._views[client_order_id], now)

    def apply_notice(self, event: Event, t: int) -> None:
        coid = event.client_order_id  # type: ignore[attr-defined]
        self._views[coid] = _view_after_notice(self._views[coid], event, t)


class _OrderPort:
    """The strategy's side of the order channel: its OWN copies of its
    order views (`_registry`, written by the engine, never read by it), its
    outbox (the messages it sent, read by the engine once per callback,
    engine.py `_drain`) and its counter of engine-named ids. It has no
    reference to the engine or to the core's book, and holds no time (round
    10, i0-r9-02: the engine wrote the callback's time on it through its
    class, which ran the strategy's code when the strategy had replaced
    that class; the time now comes with each call). Slotted: nothing can be
    put on it. The context's calls do not go through its attributes: they
    are bound to the engine's own references to the same registry and
    outbox (engine.py `_context_calls`), so replacing an attribute here
    changes nothing that is sent."""

    __slots__ = ("_registry", "_outbox", "_shown", "_counter")

    def __init__(self, registry: Optional[dict] = None, outbox: Optional[list] = None,
                 shown: Optional[list] = None) -> None:
        self._registry: dict[str, OrderView] = {} if registry is None else registry
        self._outbox: list[tuple] = [] if outbox is None else outbox
        self._shown: list[tuple] = [] if shown is None else shown
        self._counter = 0

    # -- strategy-facing (through StrategyContext) --------------------------
    def place(self, request: OrderRequest, now: Optional[int] = None) -> str:
        return port_place(self, self._registry, self._shown, self._outbox, request, now)

    def cancel(self, request: Union[CancelRequest, str], now: Optional[int] = None) -> None:
        port_cancel(self._registry, self._shown, self._outbox, request, now)

    def knows(self, client_order_id: str) -> bool:
        _bring_up(self._registry, self._shown)
        return client_order_id in self._registry

    def set_timer(self, at_ns: int, tag: str, now: Optional[int] = None) -> None:
        port_timer(self._outbox, at_ns, tag, now)

    def order(self, client_order_id: str) -> Optional[OrderView]:
        return port_order(self._registry, self._shown, client_order_id)

    def open_orders(self) -> tuple[OrderView, ...]:
        return port_open_orders(self._registry, self._shown)


def _bring_up(registry: dict, shown: list) -> None:
    """Bring the strategy's registry up to date with the views the core
    showed it since the last call (engine.py `_show` only APPENDS to
    `shown`: round 12, i0-r11-01). Runs inside the strategy's own call --
    every port function starts with it -- so whatever the strategy put in
    its registry (a key of its own that compares as it likes) runs, if at
    all, inside its own call, and changes only what it reads."""
    if list.__len__(shown):
        views = list.__getitem__(shown, slice(None))
        list.clear(shown)
        for coid, view in views:
            dict.__setitem__(registry, coid, view)


def _callback_time(now: Optional[int]) -> int:
    if now is None:
        raise OrderApiError("the order port was used without a callback's time (before the first callback)")
    return now


def port_place(port: _OrderPort, registry: dict, shown: list, outbox: list, request: Any,
               now: Optional[int]) -> str:
    """`place_order`: the request made again (the view keeps its own copy;
    the outbox carries another: nothing the strategy holds is what the
    venue receives), its id checked against the strategy's copies (to
    answer at once; the core checks again against its book), its view
    written and its message put in the outbox. `registry`, `shown` and
    `outbox` are the strategy's side (plain dict and lists the engine made),
    written by their base type's methods, inside the strategy's call."""
    _bring_up(registry, shown)
    request = fresh_request(request, OrderRequest, OrderApiError, "place_order")
    now = _callback_time(now)
    coid = request.client_order_id
    known = registry.__contains__
    if coid:
        check_new_id(coid, known)
    else:
        while True:
            port._counter += 1
            coid = f"core-{port._counter}"
            if not known(coid):
                break
        request = dataclasses.replace(request, client_order_id=coid)
    dict.__setitem__(registry, coid, _new_view(request, now))
    list.append(outbox, ("new", dataclasses.replace(request), now))
    return coid


def port_cancel(registry: dict, shown: list, outbox: list, request: Any, now: Optional[int]) -> None:
    _bring_up(registry, shown)
    if is_a(request, str):  # the real type: an object claiming to be a str is not an id
        request = CancelRequest(request)
    request = fresh_request(request, CancelRequest, OrderApiError, "cancel_order (or an id)")
    view = dict.get(registry, request.client_order_id)
    if view is None:
        raise OrderApiError(f"cancel for unknown client_order_id {request.client_order_id!r}")
    now = _callback_time(now)
    dict.__setitem__(registry, request.client_order_id, _view_after_cancel(view, now))
    list.append(outbox, ("cancel", request, now))


def port_timer(outbox: list, at_ns: Any, tag: Any, now: Optional[int]) -> None:
    at, text = check_timer(at_ns, tag, _callback_time(now))
    list.append(outbox, ("timer", at, text))


def port_order(registry: dict, shown: list, client_order_id: str) -> Optional[OrderView]:
    """A new view object of one of the strategy's orders at every call
    (None if unknown), made from the strategy's own copy (which the core
    hands over at every change, engine.py `_show`, and never reads)."""
    _bring_up(registry, shown)
    view = dict.get(registry, client_order_id)
    return None if view is None else _fresh_view(view)


def port_open_orders(registry: dict, shown: list) -> tuple[OrderView, ...]:
    """New view objects of the strategy's open orders, at every call."""
    _bring_up(registry, shown)
    return tuple(_fresh_view(v) for v in dict.values(registry) if v.is_open)


_TYPES: tuple = tuple(EventType)  # position -> event type (a context holds positions, never Enum members)
_TYPE_POS: dict = {t: i for i, t in enumerate(_TYPES)}


class StrategyContext:
    """Built by the engine for one callback and revoked when it returns.

    Holds no mutable object (round 9, LEAD_DESIGN s3.4): its slots cannot be
    assigned or deleted, and what it holds is values (ints, tuples, the
    frozen current event), windows that hold no mutable object themselves
    (window.py `EventWindow`), and functions. Everything of the core's it
    acts on -- the order port, the history lists -- is reached only by
    CALLING those functions, never as an attribute value."""

    __slots__ = ("__visible_events", "__typed", "__dropped_of", "__dropped_counts", "__current", "__now",
                 "__place_order_cb", "__cancel_order_cb", "__order_lookup_cb", "__open_orders_cb",
                 "__set_timer_cb", "__dropped_overall", "__alive", "__revoked")

    def __init__(
        self,
        visible_events: Sequence[Event],
        current: Event,
        place_order_cb: Callable[[OrderRequest], str],
        cancel_order_cb: Callable[[CancelRequest], None],
        *,
        order_lookup_cb: Optional[Callable[[str], Optional[OrderView]]] = None,
        open_orders_cb: Optional[Callable[[], tuple]] = None,
        set_timer_cb: Optional[Callable[[int, str], None]] = None,
        typed_events: Optional[Union[Mapping[EventType, Sequence[Event]], Callable]] = None,
        dropped_of: Optional[Callable[[int], tuple]] = None,
        dropped_counts: Optional[Mapping[EventType, int]] = None,
        now_ns: Optional[int] = None,
        dropped_overall: Optional[int] = None,
        alive: Optional[Callable[[], bool]] = None,
    ) -> None:
        """`typed_events`, if given, maps an event type to the delivered
        events of that type (same objects, same order as `visible_events`)
        -- a mapping, or a function of the type (the engine's: it makes the
        type's window when it is first read); it only makes
        `visible_events(event_type)` faster.

        `dropped_counts` maps an event type to how many of its delivered
        events the history no longer holds (`history_limit`, history.py),
        and `dropped_of`, given with it, maps a type's position in
        `tuple(EventType)` to (the delivery numbers, the received times) of
        those events, in drop order (the engine's: the strategy's side of
        the history, history.py `HistoryLists`); with them a read is refused
        (`HistoryTruncatedError`) exactly when its answer without the limit
        holds a dropped event, and an empty answer's place is stated (for
        the placeof an answer, window.py). `now_ns`: the delivery time, from the
        engine (not read back from `current`, which is the strategy's own
        copy and could be changed by it); default `current`'s received
        time. `dropped_overall`: how many delivered events the whole history
        no longer holds, from the engine's own count (not read back from the
        events, which are the strategy's copies); default: counted from the
        oldest held event's delivery number. `alive`: the engine's function
        that turns false when the callback returns (the context is then
        revoked, like after `_revoke`)."""
        if typed_events is not None and not callable(typed_events):
            table = dict(typed_events)

            def typed(etype: EventType, _table=table) -> Sequence[Event]:
                return _table.get(etype, ())
        else:
            typed = typed_events
        put = object.__setattr__
        put(self, "_StrategyContext__visible_events", visible_events)
        put(self, "_StrategyContext__typed", typed)
        put(self, "_StrategyContext__dropped_of", dropped_of)
        put(self, "_StrategyContext__dropped_counts", tuple(
            (_TYPE_POS[t], int(n)) for t, n in dict(dropped_counts).items()) if dropped_counts else ())
        put(self, "_StrategyContext__current", current)
        put(self, "_StrategyContext__now", int(current.received_time_ns) if now_ns is None else int(now_ns))
        put(self, "_StrategyContext__place_order_cb", place_order_cb)
        put(self, "_StrategyContext__cancel_order_cb", cancel_order_cb)
        put(self, "_StrategyContext__order_lookup_cb", order_lookup_cb)
        put(self, "_StrategyContext__open_orders_cb", open_orders_cb)
        put(self, "_StrategyContext__set_timer_cb", set_timer_cb)
        put(self, "_StrategyContext__dropped_overall", None if dropped_overall is None else int(dropped_overall))
        put(self, "_StrategyContext__alive", alive)
        put(self, "_StrategyContext__revoked", False)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("a StrategyContext cannot be changed")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("a StrategyContext cannot be changed")

    def _revoke(self) -> None:
        """Revokes a context built without `alive` (a direct construction).
        The engine does not call it (round 10, i0-r9-02: writing the
        context's slots after the callback ran the class the strategy may
        have given its context); it revokes through `alive`, a cell only it
        flips."""
        object.__setattr__(self, "_StrategyContext__revoked", True)
        object.__setattr__(self, "_StrategyContext__typed", None)

    def __check(self) -> None:
        alive = self.__alive
        if self.__revoked or (alive is not None and not alive()):
            raise StaleContextError("StrategyContext used after its callback returned")

    def __dropped_count(self, event_type: EventType) -> int:
        pos = _TYPE_POS[event_type]
        for p, n in self.__dropped_counts:
            if p == pos:
                return n
        return 0

    # -- read ---------------------------------------------------------------
    # `now_ns` and `current_event` stay readable after revocation: they are
    # fixed facts about the instant this context was built for and cannot
    # reveal anything later. Everything that reads history or acts is
    # refused after revocation.
    @property
    def now_ns(self) -> Nanos:
        return self.__now

    @property
    def current_event(self) -> Event:
        return self.__current

    @property
    def revoked(self) -> bool:
        alive = self.__alive
        return self.__revoked or (alive is not None and not alive())

    def visible_events(
        self,
        event_type: Optional[EventType] = None,
        n: Optional[int] = None,
        *,
        since_ns: Optional[int] = None,
        until_ns: Optional[int] = None,
    ) -> DeliveredEvents:
        """Delivered events (all with `received_time_ns <= now_ns`), oldest
        first, as a `DeliveredEvents` tuple that knows where it lies in what
        the read reads: naming a position outside it (an index `>= len` or
        `< -len`, or a slice bound past the end) raises instead of a
        shortened answer, with the error chosen by what the NAMED position
        is (window.py): `FuturePositionError` (a `LookAheadError`) for an
        event not delivered yet, `OutsideAnswerError` for a delivered event
        outside the answer, `DroppedPositionError` / `BeforeFirstEventError`
        before the oldest.
        Filters, all optional: only `event_type`; only those with
        `since_ns <= received_time_ns <= until_ns`; then only the last `n`
        (`n` is a count >= 0: `n=0` returns nothing, a negative `n` raises
        `OrderApiError`).

        "The last k events, or all of them if fewer were delivered" is
        `visible_events(n=k)`, not `visible_events()[-k:]`: a slice bound
        naming a position before the answer's oldest event raises
        (`BeforeFirstEventError` / `DroppedPositionError`) instead of
        shortening the answer (round 8; `position_rule.last_k`).

        Any time argument after `now_ns` (`since_ns` or `until_ns`) raises
        `LookAheadError`: the history holds nothing after now, and a request
        for the future is a strategy bug that must not be answered with a
        silently empty or shortened result.

        With `history_limit`, a read raises `HistoryTruncatedError` exactly
        when its answer WITHOUT the limit holds an event the limit dropped
        (the error names the newest such event and how to read kept events
        only); every answer returned, empty or not, is the answer without
        the limit, at its place (round 10, i0-r9-01)."""
        self.__check()
        now = self.__now
        since = _time_arg("since_ns", since_ns, now)
        until = _time_arg("until_ns", until_ns, now)
        count = _count_arg(n)
        # a member of EventType itself (EventType has members, so it has no
        # subclasses): an object claiming to be one would match no type and
        # give a silently empty answer
        if event_type is not None and type(event_type) is not EventType:
            raise OrderApiError(f"event_type must be an EventType member, got a {type_name(event_type)}")

        if event_type is None:
            events: Sequence[Event] = self.__visible_events
        elif self.__typed is not None:
            events = self.__typed(event_type)
        else:
            events = tuple(e for e in self.__visible_events if e.EVENT_TYPE is event_type)

        # Delivered events are in non-decreasing received_time_ns (the
        # engine's queue never goes back in time), so a range is a slice.
        lo, hi = 0, len(events)
        if since is not None:
            lo = bisect.bisect_left(events, since, key=_recv)
        if until is not None:
            hi = bisect.bisect_right(events, until, key=_recv)
        delivered = len(events)
        # the types the read covers that history_limit dropped events of
        # (position, how many); and where the answer lies in what the read
        # reads (window.py `AnswerPlace`, i0-r6-01): the kept events of its
        # scope, with the `dropped` deliveries of it before its oldest kept
        # one at -dropped..-1 (for one type, the count the history keeps;
        # for the whole history, every delivery before its oldest kept one:
        # deliveries are numbered 1, 2, 3, ... and everything not dropped
        # is kept)
        counts = self.__dropped_counts if self.__dropped_of is not None else ()
        if event_type is not None:
            pos = _TYPE_POS[event_type]
            scope = tuple((p, k) for p, k in counts if p == pos)
            dropped = scope[0][1] if scope else 0
            before_seq = None  # a type drops its oldest: all its dropped events lie before its kept ones
        else:
            scope = counts
            dropped = self.__dropped_overall or 0  # the engine's own count
            before_seq = dropped + 1  # the oldest kept delivery
        if count == 0:
            return self.__empty_answer(scope, until, before_seq, hi, delivered, dropped)
        if scope:
            self.__refuse_truncated(event_type, since, until, count, scope, events, lo, hi)
        if count is not None:
            lo = max(lo, hi - count)
        if hi <= lo:
            return self.__empty_answer(scope, until, before_seq, hi, delivered, dropped)
        # the core's own read of the kept events lo..hi-1 (inside by construction)
        chunk = events._range(lo, hi) if type(events) is EventWindow else tuple(events)[lo:hi]
        return DeliveredEvents._placed(chunk, lo, 1, delivered, dropped)

    def __empty_answer(self, scope: tuple, until: Optional[int], before_seq: Optional[int], hi: int,
                       delivered: int, dropped: int) -> DeliveredEvents:
        """An empty answer lies where its range was cut: on the line of what
        the read reads (the `dropped` deliveries before the oldest kept one,
        then the kept ones), after every event received at or before
        `until_ns` (after all of them without `until_ns`). Among the kept
        ones that is `hi`; the dropped deliveries before the oldest kept one
        that were received after `until_ns` lie after the cut too, so the
        cut is that many positions before `hi` (round 10, i0-r9-01: it was
        refused as unplaceable)."""
        after = 0
        if until is not None:
            for p, k in scope:
                seqs, recvs = self.__dropped_of(p)
                after += dropped_before(seqs, recvs, k, before_seq, until)
        return DeliveredEvents._placed((), hi - after, 1, delivered, dropped)

    def __refuse_truncated(self, event_type: Optional[EventType], since: Optional[int], until: Optional[int],
                           count: Optional[int], scope: tuple, events: Sequence[Event], lo: int, hi: int) -> None:
        """Raise iff the answer this read gives WITHOUT history_limit holds
        a dropped event (round 10, i0-r9-01: the definition itself, decided
        from the facts of every dropped event, not from a list of cases).
        That answer is the last `count` (or all) of the delivered events of
        the scope with since <= received <= until. The kept ones of them are
        events[lo:hi]. With `count` and at least `count` kept ones, the
        answer starts at the kept event events[hi - count] and holds no
        dropped event iff no dropped event in the range comes after it;
        otherwise the answer needs every event in the range, and holds no
        dropped event iff there is none in the range. (An answer with no
        dropped event is a run of the delivered events all kept, so it is
        events[max(lo, hi - count):hi], the answer returned.)"""
        after_seq = None
        if count is not None and hi - lo >= count:
            after_seq = int(events[hi - count].seq)
        newest = None
        total = 0
        for p, k in scope:
            seqs, recvs = self.__dropped_of(p)
            a, b = dropped_in_range(seqs, recvs, k, since, until, after_seq)
            if b > a:
                total += b - a
                cand = (int(seqs[b - 1]), int(recvs[b - 1]), p)
                if newest is None or cand > newest:
                    newest = cand
        if newest is None:
            return
        seq, recv, p = newest
        # the events the read asks for after that one are all kept: how many
        kept_after = hi - bisect.bisect_right(events, seq, lo, hi, key=_seq)
        remedy = f"a since_ns after {recv}"
        if kept_after:
            remedy += f", or n <= {kept_after} (its newest {kept_after} events are kept)"
        raise HistoryTruncatedError(
            f"visible_events(event_type={None if event_type is None else event_type.value}, "
            f"since_ns={since}, until_ns={until}, n={None if count is None else int_text(count)}) "
            f"asks for delivery #{seq} "
            f"({_TYPES[p].value} received at {recv}), which history_limit dropped "
            f"({total} dropped event{'s' if total > 1 else ''} in its answer); to read kept events "
            f"only: {remedy}"
        )

    def last(self, event_type: EventType) -> Optional[Event]:
        """Most recent delivered event of `event_type`, or None."""
        got = self.visible_events(event_type, n=1)
        return got[0] if got else None

    def order(self, client_order_id: str) -> Optional[OrderView]:
        """The strategy's own view of one of its orders, or None for an id
        it never placed. The id is a str by its real type (values.py): an
        object that only claims to be one is refused, not answered None."""
        self.__check()
        if self.__order_lookup_cb is None:
            raise OrderApiError("this context was built without an order registry")
        return self.__order_lookup_cb(_order_field(as_text, "client_order_id", client_order_id))

    def open_orders(self) -> tuple[OrderView, ...]:
        self.__check()
        if self.__open_orders_cb is None:
            raise OrderApiError("this context was built without an order registry")
        return self.__open_orders_cb()

    # -- act ----------------------------------------------------------------
    def place_order(self, request: OrderRequest) -> str:
        """Send a new order; returns its client_order_id (the strategy's own
        if it set one, else an engine-assigned `core-N`)."""
        self.__check()
        return self.__place_order_cb(request)

    def cancel_order(self, request: Union[CancelRequest, str]) -> None:
        self.__check()
        self.__cancel_order_cb(request)

    def set_timer(self, at_ns: int, tag: str = "") -> None:
        """Deliver a `ClockEvent(tag=tag)` to this strategy at `at_ns`
        (>= now_ns)."""
        self.__check()
        if self.__set_timer_cb is None:
            raise OrderApiError("this context was built without timers")
        self.__set_timer_cb(at_ns, tag)


def _count_arg(n: Optional[int]) -> Optional[int]:
    """The one check of the count argument of a history read: an int >= 0."""
    if n is None:
        return None
    n = _order_field(as_int, "n", n)  # the one int rule (values.py): never a bool
    if n < 0:
        raise OrderApiError(f"n is a count of events and must be >= 0, got {int_text(n)}")
    return n


def _time_arg(name: str, value: Optional[int], now: int) -> Optional[int]:
    """The one check every time argument of a history read passes: an int64
    of ns, and not after now."""
    if value is None:
        return None
    t = int(validate_nanos(value))
    if t > now:
        raise LookAheadError(f"visible_events({name}={t}) asks for events after now_ns={now}")
    return t


def _answers_cancel(event: Event) -> bool:
    """Is this notice the venue's answer to one of our cancels?"""
    if isinstance(event, OrderCanceledEvent):
        return event.answers == "cancel"
    if isinstance(event, (OrderRejectEvent, OrderStateUnknownEvent)):
        return event.request_kind == "cancel"
    return False


def _recv(event: Event) -> int:
    return int(event.received_time_ns)


def _seq(event: Event) -> int:
    return int(event.seq)


STRATEGY_API: tuple[str, ...] = (
    "now_ns",
    "current_event",
    "revoked",
    "visible_events",
    "last",
    "order",
    "open_orders",
    "place_order",
    "cancel_order",
    "set_timer",
)
