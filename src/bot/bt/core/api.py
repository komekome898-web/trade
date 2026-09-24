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
  order functions are bound methods of `_OrderPort`, an object that holds
  only the strategy's OWN copies of its order views and its outbox -- not
  the engine, not the core's order book, not the event source, not the
  pending queue. So nothing reachable from a context, even through private
  attributes, holds an event the strategy has not received yet. Scope of
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
    is_a,
    rebuild_carrier,
    renew,
    thaw,
    type_name,
)
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
        """`extra` as a fresh dict, lists / dicts / sets as they were given
        (values.py `thaw`); changing it changes nothing else."""
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
            pairs.append((key, freeze(value, f"extra[{key!r}]")))
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
        raise error(
            f"{who} takes a {cls.__name__} itself (not a subclass), got "
            f"{type(request).__module__}.{type(request).__qualname__}"
        )
    try:
        return rebuild_carrier(request)
    except error:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise error(f"{who}: the {cls.__name__} cannot be made again from its fields: {exc}") from None


def _require_positive(name: str, value: Any) -> float:
    f = _order_field(as_float, name, value)  # the one number rule (values.py), never a bool
    if not math.isfinite(f) or f <= 0:
        raise OrderApiError(f"{name} must be finite and > 0, got {value!r}")
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
    order views (`_registry`, written by the engine, never read by it) and
    its outbox (the messages it sent, read by the engine once per callback,
    engine.py `_drain`). It has no reference to the engine or to the core's
    book. Slotted: nothing can be put on it (an instance attribute cannot
    shadow a method)."""

    __slots__ = ("_registry", "_outbox", "_counter", "_now")

    def __init__(self, registry: Optional[dict] = None, outbox: Optional[list] = None) -> None:
        self._registry: dict[str, OrderView] = {} if registry is None else registry
        self._outbox: list[tuple] = [] if outbox is None else outbox
        self._counter = 0
        # the delivery time of the callback in progress; None before the
        # first callback ("no time yet" is not a time: every int64 is one)
        self._now: Optional[int] = None

    def _time(self) -> int:
        now = self._now
        if now is None:
            raise OrderApiError("the order port was used before the first callback")
        return now

    # -- strategy-facing (through StrategyContext) --------------------------
    def place(self, request: OrderRequest) -> str:
        # the view keeps its own copy; the outbox carries another (below):
        # nothing the strategy holds is what the venue receives
        request = fresh_request(request, OrderRequest, OrderApiError, "place_order")
        now = self._time()
        coid = request.client_order_id
        if coid:
            check_new_id(coid, self._registry.__contains__)
        else:
            while True:
                self._counter += 1
                coid = f"core-{self._counter}"
                if coid not in self._registry:
                    break
            request = dataclasses.replace(request, client_order_id=coid)
        self._registry[coid] = _new_view(request, now)
        self._outbox.append(("new", dataclasses.replace(request), now))
        return coid

    def cancel(self, request: Union[CancelRequest, str]) -> None:
        if is_a(request, str):  # the real type: an object claiming to be a str is not an id
            request = CancelRequest(request)
        request = fresh_request(request, CancelRequest, OrderApiError, "cancel_order (or an id)")
        view = self._registry.get(request.client_order_id)
        if view is None:
            raise OrderApiError(f"cancel for unknown client_order_id {request.client_order_id!r}")
        now = self._time()
        self._registry[request.client_order_id] = _view_after_cancel(view, now)
        self._outbox.append(("cancel", request, now))

    def knows(self, client_order_id: str) -> bool:
        return client_order_id in self._registry

    def set_timer(self, at_ns: int, tag: str) -> None:
        at, text = check_timer(at_ns, tag, self._time())
        self._outbox.append(("timer", at, text))

    def order(self, client_order_id: str) -> Optional[OrderView]:
        """The strategy's own copy of its view of one order (None if
        unknown): an object the core wrote for the strategy alone
        (engine.py `_show`, a new copy at every change) and never reads."""
        return self._registry.get(client_order_id)

    def open_orders(self) -> tuple[OrderView, ...]:
        """The strategy's own copies of its views of its open orders."""
        return tuple(v for v in self._registry.values() if v.is_open)


class StrategyContext:
    """Built by the engine for one callback and revoked when it returns."""

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
        typed_events: Optional[Mapping[EventType, Sequence[Event]]] = None,
        dropped: Optional[Mapping[EventType, tuple[int, int]]] = None,
        dropped_counts: Optional[Mapping[EventType, int]] = None,
        now_ns: Optional[int] = None,
        dropped_overall: Optional[int] = None,
    ) -> None:
        """`typed_events`, if given, maps an event type to the delivered
        events of that type (same objects, same order as `visible_events`);
        it only makes `visible_events(event_type)` faster.

        `dropped`, if given, maps an event type to (seq, received_time_ns)
        of the last event of that type the history no longer holds
        (`history_limit`, history.py); reads reaching into that part raise
        `HistoryTruncatedError`. `dropped_counts` maps a type to how many
        of its delivered events the history no longer holds (for the place
        of an answer, window.py). `now_ns`: the delivery time, from the
        engine (not read back from `current`, which is the strategy's own
        copy and could be changed by it); default `current`'s received
        time. `dropped_overall`: how many delivered events the whole history
        no longer holds, from the engine's own count (not read back from the
        events, which are the strategy's copies); default: counted from the
        oldest held event's delivery number."""
        self.__visible_events = visible_events
        self.__typed_events = typed_events
        self.__dropped = dict(dropped) if dropped else {}
        self.__dropped_counts = dict(dropped_counts) if dropped_counts else {}
        self.__current = current
        self.__now = int(current.received_time_ns) if now_ns is None else int(now_ns)
        self.__place_order_cb = place_order_cb
        self.__cancel_order_cb = cancel_order_cb
        self.__order_lookup_cb = order_lookup_cb
        self.__open_orders_cb = open_orders_cb
        self.__set_timer_cb = set_timer_cb
        self.__dropped_overall = None if dropped_overall is None else int(dropped_overall)
        self.__revoked = False

    def _revoke(self) -> None:
        """Called by the engine through the class (`StrategyContext._revoke(
        ctx)`), never looked up on the instance, and it only WRITES: it reads
        nothing the strategy could have changed on its context. The engine
        revokes the history windows it built itself, through its own
        references to them (engine.py `_deliver`)."""
        self.__revoked = True
        self.__typed_events = None

    def __check(self) -> None:
        if self.__revoked:
            raise StaleContextError("StrategyContext used after its callback returned")

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
        return self.__revoked

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

        With `history_limit`, a read whose answer would reach into the
        dropped part of a type it covers raises `HistoryTruncatedError`
        (history.py); an answer that is returned is the same as without the
        limit."""
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
        elif self.__typed_events is not None:
            events = self.__typed_events.get(event_type, ())
        else:
            events = tuple(e for e in self.__visible_events if e.EVENT_TYPE is event_type)

        # Delivered events are in non-decreasing received_time_ns (the
        # engine's queue never goes back in time), so a range is a slice.
        lo, hi = 0, len(events)
        if since is not None:
            lo = bisect.bisect_left(events, since, key=_recv)
        if until is not None:
            hi = bisect.bisect_right(events, until, key=_recv)
        # Where the answer lies in what the read reads (window.py
        # `AnswerPlace`, i0-r6-01): its first event is events[lo] (an empty
        # answer lies where the range was cut, events[hi]); every event of
        # `events` was delivered by now; `dropped` delivered events of it
        # lie before its oldest kept one, all dropped by history_limit: for
        # one type, the count the history recorded; for the whole history,
        # every delivery before its oldest kept event (deliveries are
        # numbered 1, 2, 3, ... without gaps and everything not dropped is
        # kept).
        if event_type is not None:
            dropped = self.__dropped_counts.get(event_type, 0)
        elif self.__dropped_overall is not None:
            dropped = self.__dropped_overall  # the engine's own count
        elif self.__dropped and len(events):
            dropped = max(0, int(events[0].seq) - 1)
        else:
            dropped = 0  # nothing dropped: the oldest held event is the first delivered
        delivered = len(events)
        if count is not None:
            if count == 0:
                return self.__empty_answer(event_type, until, hi, delivered, dropped)
            lo = max(lo, hi - count)
        if self.__dropped:
            self.__refuse_truncated(event_type, since, count, events, lo, hi)
        if hi <= lo:
            return self.__empty_answer(event_type, until, hi, delivered, dropped)
        # the core's own read of the kept events lo..hi-1 (inside by construction)
        chunk = events._range(lo, hi) if type(events) is EventWindow else tuple(events)[lo:hi]
        return DeliveredEvents._placed(chunk, lo, 1, delivered, dropped)

    def __empty_answer(self, event_type: Optional[EventType], until: Optional[int], hi: int,
                       delivered: int, dropped: int) -> DeliveredEvents:
        """An empty answer lies where its range was cut (events[hi]). If
        `until_ns` cut it before the oldest kept event and before the newest
        event history_limit dropped, the cut lies somewhere among the
        dropped events and the history cannot say where: the answer could
        not state its place, so the read is refused (i0-r6-01), as any read
        reaching into the dropped part is."""
        if hi == 0 and dropped and until is not None:
            newest_dropped = max(
                (recv for etype, (_seq, recv) in self.__dropped.items()
                 if event_type is None or etype is event_type),
                default=None,
            )
            if newest_dropped is not None and until < newest_dropped:
                raise HistoryTruncatedError(
                    f"visible_events(event_type={None if event_type is None else event_type.value}, "
                    f"until_ns={until}) ends inside the history dropped by history_limit (newest dropped "
                    f"received at {newest_dropped}); its (empty) answer cannot be placed -- read with "
                    f"until_ns >= {newest_dropped}"
                )
        return DeliveredEvents._placed((), hi, 1, delivered, dropped)

    def __refuse_truncated(self, event_type: Optional[EventType], since: Optional[int],
                           count: Optional[int], events: Sequence[Event], lo: int, hi: int) -> None:
        """Raise if the answer events[lo:hi] may lack events the history
        dropped. For each type the read covers that has a dropped part: the
        window reaches into it when it has no start or starts at or before
        the last dropped event's received time; it is still complete when
        `n` confines it to `count` kept events that all come after that
        type's last dropped event (by delivery number)."""
        for etype, (dropped_seq, dropped_recv) in self.__dropped.items():
            if event_type is not None and etype is not event_type:
                continue
            if since is not None and since > dropped_recv:
                continue  # the window starts after everything dropped of this type
            if count is not None and hi - lo == count and int(events[lo].seq) > dropped_seq:
                continue  # the last `count` events are all after the dropped part
            raise HistoryTruncatedError(
                f"visible_events(event_type={None if event_type is None else event_type.value}, "
                f"since_ns={since}, n={count}) reaches into the {etype.value} history dropped by "
                f"history_limit (last dropped: delivery #{dropped_seq} received at {dropped_recv}); "
                f"narrow the read with since_ns > {dropped_recv} or a smaller n"
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
        raise OrderApiError(f"n is a count of events and must be >= 0, got {n}")
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
