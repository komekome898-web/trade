"""What a strategy can see and do.

A strategy is called once per delivered event with a `StrategyContext`.
The context is the strategy's only handle on the run:

* `now_ns`, `current_event`, `visible_events(...)`, `last(...)` -- read
  the history of events already delivered to it (all with
  `received_time_ns <= now_ns`); any time argument after `now_ns` (the
  start or the end of a window) raises `LookAheadError`, and naming a
  position after the newest delivered event (an index or slice bound past
  the end of the answer) raises `FuturePositionError`, rather than
  returning a silently empty or truncated answer;
* `place_order`, `cancel_order`, `set_timer` -- act;
* `order(id)`, `open_orders()` -- its own orders, as it knows them.

Structural guarantees (tested in tests/bt/item_0/test_bt0_lookahead.py and
tests/bt/item_0/test_bt0_api_surface.py):

* No path to the future. The history view is backed by the list of events
  already delivered; the engine appends to it only between callbacks. The
  order functions are bound methods of `_OrderPort`, an object that holds
  only the strategy's own order registry and an outbox -- not the engine,
  not the event source, not the pending queue. So nothing reachable from a
  context, even through private attributes, holds an event the strategy has
  not received yet. Scope of this guarantee: the context and what is
  reachable from it by attribute access. It does NOT cover introspecting
  the interpreter: the strategy is called inside the engine's own process
  and call (`CoreEngine.step`), so `sys._getframe()` / `inspect.stack()` /
  `gc.get_objects()` reach the engine and its queue. The core does not
  sandbox strategy code; a strategy that does this is outside the contract
  (`CORE_CONTRACT["visibility"]["scope"]`).
* No acting later. The engine revokes the context when the callback
  returns; any later attempt to read history or act raises
  `StaleContextError`, and the history view drops its backing list.
  (`now_ns` / `current_event` stay readable: they describe the instant
  the context was built for and reveal nothing later.) What was sent
  cannot be changed afterwards either: an `OrderRequest` is a value down
  to the contents of `extra` (made immutable when the request is made,
  values.py), so nothing the strategy keeps is shared with the venue.
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
import numbers
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
from .values import freeze, thaw
from .window import DeliveredEvents


@dataclass(frozen=True)
class OrderRequest:
    side: str  # "buy" | "sell"
    order_type: str  # "market" | "limit" | ... -- the set is item 2's to define
    size: float
    price: Optional[float] = None
    client_order_id: str = ""
    time_in_force: str = "GTC"
    post_only: bool = False
    reduce_only: bool = False
    trigger_price: Optional[float] = None
    # anything else a venue model needs, as (key, value) pairs of plain data
    # (values.py). Made immutable here, when the request is made: what the
    # venue receives at the arrival time is what was sent (i0-r4-02).
    extra: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.side not in ORDER_SIDES:
            raise OrderApiError(f"side must be one of {ORDER_SIDES}, got {self.side!r}")
        if not isinstance(self.order_type, str) or not self.order_type:
            raise OrderApiError("order_type must be a non-empty str")
        _require_positive("size", self.size)
        if self.price is not None:
            _require_positive("price", self.price)
        if self.trigger_price is not None:
            _require_positive("trigger_price", self.trigger_price)
        if not isinstance(self.client_order_id, str):
            raise OrderApiError("client_order_id must be str")
        object.__setattr__(self, "extra", _frozen_extra(self.extra))

    def extra_dict(self) -> dict:
        """`extra` as a fresh dict, lists / dicts / sets as they were given
        (values.py `thaw`); changing it changes nothing else."""
        return {key: thaw(value) for key, value in self.extra}


def _frozen_extra(extra: Any) -> tuple:
    """The one check of `OrderRequest.extra`, at construction: a tuple of
    (non-empty str key, plain data value) pairs with no key twice, made
    deeply immutable (values.py)."""
    if not isinstance(extra, tuple):
        raise OrderApiError(f"extra must be a tuple of (key, value) pairs, got {type(extra).__name__}")
    pairs = []
    seen: set = set()
    for i, pair in enumerate(extra):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise OrderApiError(f"extra[{i}] must be a (key, value) pair, got {pair!r}")
        key, value = pair
        if not isinstance(key, str) or not key:
            raise OrderApiError(f"extra[{i}]: key must be a non-empty str, got {key!r}")
        if key in seen:
            raise OrderApiError(f"extra: key {key!r} given twice")
        seen.add(key)
        try:
            pairs.append((key, freeze(value, f"extra[{key!r}]")))
        except ValueError as exc:
            raise OrderApiError(str(exc)) from None
    return tuple(pairs)


@dataclass(frozen=True)
class CancelRequest:
    client_order_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.client_order_id, str) or not self.client_order_id:
            raise OrderApiError("client_order_id must be a non-empty str")


def _require_positive(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise OrderApiError(f"{name} must be a number, got {value!r}")
    if not math.isfinite(value) or value <= 0:
        raise OrderApiError(f"{name} must be finite and > 0, got {value!r}")


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


class _OrderPort:
    """The strategy's side of the order channel. Holds the strategy's order
    registry and an outbox; the engine drains the outbox after each callback
    and feeds delivered notices back through `_apply_notice`. It has no
    reference to the engine."""

    def __init__(self) -> None:
        self._registry: dict[str, OrderView] = {}
        self._outbox: list[tuple] = []
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
        if not isinstance(request, OrderRequest):
            raise OrderApiError(f"place_order takes an OrderRequest, got {type(request).__name__}")
        now = self._time()
        coid = request.client_order_id
        if coid:
            if coid.startswith(FORCED_ID_PREFIX):
                raise OrderApiError(
                    f"client_order_id {coid!r}: the prefix {FORCED_ID_PREFIX!r} is reserved "
                    f"for forced orders from the account socket"
                )
            if coid in self._registry:
                raise OrderApiError(f"duplicate client_order_id {coid!r}")
        else:
            while True:
                self._counter += 1
                coid = f"core-{self._counter}"
                if coid not in self._registry:
                    break
            request = dataclasses.replace(request, client_order_id=coid)
        self._registry[coid] = OrderView(
            request=request,
            state=OrderState.PENDING_NEW,
            sent_time_ns=now,
            last_update_ns=now,
        )
        self._outbox.append(("new", request, now))
        return coid

    def cancel(self, request: Union[CancelRequest, str]) -> None:
        if isinstance(request, str):
            request = CancelRequest(request)
        if not isinstance(request, CancelRequest):
            raise OrderApiError(f"cancel_order takes a CancelRequest or id, got {type(request).__name__}")
        view = self._registry.get(request.client_order_id)
        if view is None:
            raise OrderApiError(f"cancel for unknown client_order_id {request.client_order_id!r}")
        now = self._time()
        # Every cancel is answered by the venue exactly once (the engine
        # answers one for an order that is not live there), so it is counted
        # even for an order already final in this view.
        view = dataclasses.replace(view, cancels_in_flight=view.cancels_in_flight + 1, last_update_ns=now)
        self._registry[request.client_order_id] = dataclasses.replace(view, state=_derive_state(view))
        self._outbox.append(("cancel", request, now))

    def knows(self, client_order_id: str) -> bool:
        return client_order_id in self._registry

    def set_timer(self, at_ns: int, tag: str) -> None:
        now = self._time()
        at = int(validate_nanos(at_ns))
        if at < now:
            raise OrderApiError(f"timer at {at} is before now {now}")
        if not isinstance(tag, str):
            raise OrderApiError("timer tag must be str")
        self._outbox.append(("timer", at, tag))

    def order(self, client_order_id: str) -> Optional[OrderView]:
        return self._registry.get(client_order_id)

    def open_orders(self) -> tuple[OrderView, ...]:
        return tuple(v for v in self._registry.values() if v.is_open)

    # -- engine-facing ------------------------------------------------------
    def _adopt(self, request: OrderRequest, time_ns: int, origin: str) -> None:
        """Register an order the strategy did not place (a forced order from
        the account socket). Called by the engine when the first notice
        about it is delivered, never earlier, so the strategy learns of it
        only through a notice."""
        coid = request.client_order_id
        if coid in self._registry:  # pragma: no cover - the engine checks ids first
            raise OrderApiError(f"duplicate client_order_id {coid!r}")
        self._registry[coid] = OrderView(
            request=request, state=OrderState.PENDING_NEW, sent_time_ns=time_ns,
            last_update_ns=time_ns, origin=origin,
        )

    def _apply_notice(self, event: Event) -> None:
        """Update the facts of one order from a delivered notice, then
        derive its state. Nothing here guesses a previous state."""
        coid = event.client_order_id  # type: ignore[attr-defined]
        view = self._registry[coid]
        t = int(event.received_time_ns)
        final: Optional[OrderState] = None
        if _answers_cancel(event):
            # channels are FIFO, so the k-th answer answers the k-th cancel
            if view.cancels_in_flight < 1:  # pragma: no cover - engine invariant
                raise RuntimeError(f"an answer to a cancel of {coid!r} with no cancel in flight")
            view = dataclasses.replace(view, cancels_in_flight=view.cancels_in_flight - 1)
        if isinstance(event, OrderAckEvent):
            view = dataclasses.replace(view, acked=True, unknown_new=False,
                                       venue_order_id=event.venue_order_id)
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
        self._registry[coid] = dataclasses.replace(view, state=_derive_state(view))


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
    ) -> None:
        """`typed_events`, if given, maps an event type to the delivered
        events of that type (same objects, same order as `visible_events`);
        it only makes `visible_events(event_type)` faster.

        `dropped`, if given, maps an event type to (seq, received_time_ns)
        of the last event of that type the history no longer holds
        (`history_limit`, history.py); reads reaching into that part raise
        `HistoryTruncatedError`."""
        self.__visible_events = visible_events
        self.__typed_events = typed_events
        self.__dropped = dict(dropped) if dropped else {}
        self.__current = current
        self.__place_order_cb = place_order_cb
        self.__cancel_order_cb = cancel_order_cb
        self.__order_lookup_cb = order_lookup_cb
        self.__open_orders_cb = open_orders_cb
        self.__set_timer_cb = set_timer_cb
        self.__revoked = False

    def _revoke(self) -> None:
        self.__revoked = True
        views = [self.__visible_events]
        if self.__typed_events is not None:
            views.extend(self.__typed_events.values())
        for view in views:
            revoke = getattr(view, "revoke", None)
            if revoke is not None:
                revoke()
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
        return self.__current.received_time_ns

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
        first, as a `DeliveredEvents` tuple: naming a position after the
        newest (an index `>= len`, or a slice bound past the end) raises
        `FuturePositionError` instead of a shortened answer (window.py).
        Filters, all optional: only `event_type`; only those with
        `since_ns <= received_time_ns <= until_ns`; then only the last `n`
        (`n` is a count >= 0: `n=0` returns nothing, a negative `n` raises
        `OrderApiError`).

        Any time argument after `now_ns` (`since_ns` or `until_ns`) raises
        `LookAheadError`: the history holds nothing after now, and a request
        for the future is a strategy bug that must not be answered with a
        silently empty or shortened result.

        With `history_limit`, a read whose answer would reach into the
        dropped part of a type it covers raises `HistoryTruncatedError`
        (history.py); an answer that is returned is the same as without the
        limit."""
        self.__check()
        now = int(self.__current.received_time_ns)
        since = _time_arg("since_ns", since_ns, now)
        until = _time_arg("until_ns", until_ns, now)
        count = _count_arg(n)
        if event_type is not None and not isinstance(event_type, EventType):
            raise OrderApiError(f"event_type must be an EventType, got {event_type!r}")

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
        if count is not None:
            if count == 0:
                return DeliveredEvents()
            lo = max(lo, hi - count)
        if self.__dropped:
            self.__refuse_truncated(event_type, since, count, events, lo, hi)
        if hi <= lo:
            return DeliveredEvents()
        return DeliveredEvents(events[lo:hi])

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
        self.__check()
        if self.__order_lookup_cb is None:
            raise OrderApiError("this context was built without an order registry")
        return self.__order_lookup_cb(client_order_id)

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
    if isinstance(n, bool) or not isinstance(n, int):
        raise OrderApiError(f"n must be an int, got {n!r}")
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
