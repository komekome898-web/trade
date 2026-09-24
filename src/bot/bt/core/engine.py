"""The core event-driven engine.

One priority queue, ordered by ordering.py's total order, holds everything
that will happen: market data reaching the venue, market data reaching the
strategy, our orders and cancels reaching the venue, the venue's answers
reaching the strategy, and timers. `step()` processes one entry;
`run()` processes all of them.

Two clocks, one queue:

* Venue side (`exchange_time_ns`, order arrival times): the fill model sees
  market data and our requests here, and every fill is costed (cost model)
  and booked (account) here, at the time it happens.
* Strategy side (`received_time_ns`): the strategy is called here and sees
  only what has been delivered to it. With a latency model, an order placed
  at t reaches the venue at t + order delay, and its ACK reaches the
  strategy at venue time + notice delay.

Four paths are FIFO channels (ordering.py): input -> venue, strategy ->
venue requests (new orders and cancels on ONE channel), input -> strategy
(per stream, in reception order), venue -> strategy notices. Timers are
not a channel: each is delivered at the time the strategy asked for, so a
timer set later for an earlier time comes first (same time: set order).
The queue key is (time, phase, received time, position); the event type
is not in it, so nothing on a channel is re-sorted by type. What travels
on a path is a value made when it is sent (values.py): every field of every
carrier (an order or cancel request, a venue report, a fill notice, an
event) is the built-in type itself -- never an object or a subclass
instance of the sender's -- and the carrier classes are slotted. Each path
takes the core's own carrier classes themselves (a subclass is refused),
and the strategy's and the account's requests are rebuilt when they enter
(api.py `fresh_request`), so no sender holds what its receiver reads.
Neither side can change what the other receives, or learns, without
sending.

Input is one stream of events, or several named streams (a mapping of
name -> iterable, e.g. trades, board, bars and funding read from separate
files). Streams are merged by time (ordering.py: exchange time, then
stream name in `sorted()` order, then position inside the stream), so the
events are processed in time order whatever order the streams, or the
types, were handed over in; inside a stream, the stream's own order is
kept whatever the types. Each stream is consumed lazily: the engine
holds at most one not-yet-processed event per stream and pulls the next
one only when the queue has nothing earlier to process, so a stream can be
a generator over a file larger than memory. Nothing the strategy is handed
(its context and every object reachable from it by attribute access,
private attributes included) holds an event it has not received yet; see
api.py for what that guarantee does not cover (the strategy runs in the
engine's own process, so introspecting the interpreter -- the call stack,
`gc` -- reaches the engine). Each stream must be non-decreasing in
`exchange_time_ns`; a backwards step raises `EventOrderError` naming the
stream (the core merges streams, it never re-sorts one silently).

Lifecycle. A step changes state owned by several parties one after the
other (the strategy's order view and outbox, the FIFO channels, the queue,
the venue ledger, the fill list, and the plug-ins' own state), and code
outside the core (the strategy, every socket) can raise at any point of
it. The core cannot roll the strategy and the plug-ins back, so a step is
not made atomic; instead the engine has a lifecycle: any exception that
escapes `step()` -- whatever its type -- is re-raised unchanged and leaves
the engine FAILED, and a FAILED engine refuses every later `step()`,
`run()` and `result()` with `EngineFailedError` (the original exception is
its `__cause__` and `failure`). Nothing half-updated is ever run on or
returned as a result. Calling `step()` / `run()` / `result()` from inside
one of the engine's own steps is refused with `EngineReentryError`
(`CORE_CONTRACT["lifecycle"]`).

Nothing here is market-specific; fills, delays, fees and bookkeeping are
the sockets' job (interfaces.py).
"""
from __future__ import annotations

import dataclasses
import hashlib
import heapq
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Optional, Union

from .api import FORCED_ID_PREFIX, CancelRequest, OrderRequest, OrderView, StrategyContext, _OrderPort, fresh_request
from .errors import (
    AccountSocketError,
    CostModelError,
    EngineFailedError,
    EngineReentryError,
    EventOrderError,
    LatencyModelError,
    MissingCostModelError,
    SourceEventTypeError,
    TimestampUnitError,
    VenueProtocolError,
)
from .events import (
    LIQUIDITY,
    MARKET_EVENT_TYPES,
    NOTICE_EVENT_TYPES,
    SOURCE_EVENT_TYPES,
    EVENT_TYPE_TO_CLASS,
    ClockEvent,
    Event,
    EventType,
    OrderAckEvent,
    OrderCanceledEvent,
    OrderFillEvent,
    OrderRejectEvent,
    OrderStateUnknownEvent,
)
from .interfaces import (
    Account,
    Ack,
    Canceled,
    CostModel,
    Fill,
    FillModel,
    FillNotice,
    LatencyModel,
    NullAccount,
    NullFillModel,
    REPORT_CLASSES,
    Reject,
    StateUnknown,
    ZeroLatency,
)
from .ordering import (
    PHASE_DELIVER_INPUT,
    PHASE_DELIVER_NOTICE,
    PHASE_DELIVER_TIMER,
    PHASE_VENUE_MARKET,
    PHASE_VENUE_REQUEST,
    merge_key,
)
from .history import DeliveredHistory
from .strategy import Strategy
from .time import validate_nanos
from .values import as_float, as_int, as_text, is_a, type_name
from .window import EventWindow

_K_VENUE_MARKET = 0
_K_VENUE_ORDER = 1
_K_VENUE_CANCEL = 2
_K_DELIVER = 3  # a notice or a timer
_K_DELIVER_INPUT = 4

_OVERFILL_TOL = 1e-9
_FILLED_EPS = 1e-12


@dataclass
class EngineResult:
    events_processed: int  # callbacks made to the strategy
    source_events: int  # events consumed from the source
    order_requests: list[OrderRequest] = field(default_factory=list)
    cancel_requests: list[CancelRequest] = field(default_factory=list)
    fills: list[FillNotice] = field(default_factory=list)
    orders: dict[str, OrderView] = field(default_factory=dict)
    venue_states: dict[str, str] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)
    # the sockets (fill_model, latency_model, cost_model, account) and run
    # settings (time_span) the caller did not give, so the core's default ran
    defaults_used: list[str] = field(default_factory=list)
    first_time_ns: Optional[int] = None
    last_time_ns: Optional[int] = None
    stopped_at_end_time: bool = False
    delivery_digest: str = ""  # sha256 over every delivered event, in order
    forced_orders: list[OrderRequest] = field(default_factory=list)  # from the account socket
    source_events_by_stream: dict[str, int] = field(default_factory=dict)
    time_span_ns: Optional[tuple[int, int]] = None  # the declared span, None if not given

    @property
    def open_orders(self) -> list[OrderView]:
        return [v for v in self.orders.values() if v.is_open]


@dataclass
class _VenueOrder:
    """The venue-side FACTS about one order. Its state name is derived from
    them, so an ambiguous answer never erases what is already known (that
    the order was acknowledged, how much of it filled)."""

    request: OrderRequest
    acked: bool = False
    filled: float = 0.0
    final: Optional[str] = None  # FILLED | CANCELED | REJECTED
    unknown_new: bool = False  # ambiguous answer to the new order, not settled
    unknown_cancel: bool = False  # ambiguous answer to a cancel, not settled

    def state_name(self) -> str:
        if self.final is not None:
            return self.final
        if self.unknown_new or self.unknown_cancel:
            return _VenueLedger.UNKNOWN
        return _VenueLedger.LIVE if self.acked else _VenueLedger.ARRIVED


class _VenueLedger:
    """The venue-side history of every order, used to reject impossible
    reports from a fill model. Each report is checked against the order's
    facts (`_VenueOrder`), not against a single state string."""

    ARRIVED = "ARRIVED"
    LIVE = "LIVE"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    UNKNOWN = "STATE_UNKNOWN"

    def __init__(self) -> None:
        self._orders: dict[str, _VenueOrder] = {}

    def arrive(self, order: OrderRequest) -> None:
        coid = order.client_order_id
        if coid in self._orders:  # pragma: no cover - the port refuses duplicates
            raise VenueProtocolError(f"order {coid!r} reached the venue twice")
        self._orders[coid] = _VenueOrder(order)

    def __contains__(self, coid: str) -> bool:
        return coid in self._orders

    def request(self, coid: str) -> OrderRequest:
        return self._orders[coid].request

    def state(self, coid: str) -> Optional[str]:
        o = self._orders.get(coid)
        return None if o is None else o.state_name()

    def states(self) -> dict[str, str]:
        return {coid: o.state_name() for coid, o in self._orders.items()}

    def is_live(self, coid: str) -> bool:
        """At the venue and not final: acknowledged, or with an ambiguous
        answer to its new order (it may exist)."""
        o = self._orders.get(coid)
        return o is not None and o.final is None and (o.acked or o.unknown_new)

    def apply(self, report: Any, where: str, subject: Optional[str]) -> None:
        name = type(report).__name__
        # A report becomes a notice that crosses the venue -> strategy path,
        # so it must be one of the core's own report classes ITSELF: those
        # make every field a value when the report is made (interfaces.py,
        # values.py) and are slotted; a subclass could decide a field when
        # it is read (i0-r4-02, i0-r5-01).
        if type(report) not in REPORT_CLASSES:
            raise VenueProtocolError(
                f"{where}: unknown report type {type(report).__module__}.{type(report).__qualname__} "
                f"(a fill model answers with Ack / Reject / Fill / Canceled / StateUnknown themselves, "
                f"not subclasses)"
            )
        coid = report.client_order_id
        kind = getattr(report, "request_kind", None)
        if isinstance(report, (Reject, StateUnknown)) and kind == "cancel":
            # An answer to a cancel request: valid only as the answer to that
            # cancel (inside on_cancel for that order).
            if where != "on_cancel" or subject != coid:
                raise VenueProtocolError(f"{where}: cancel {name} for {coid!r} outside its cancel")
            if isinstance(report, Reject):
                return  # a refused cancel changes nothing about the order
        if coid not in self._orders:
            raise VenueProtocolError(
                f"{where}: {name} for order {coid!r}, which has not "
                f"reached the venue -- a fill model may not act on an order before "
                f"its arrival time"
            )
        o = self._orders[coid]
        if o.final is not None:
            raise VenueProtocolError(f"{where}: {name} for order {coid!r} after terminal state {o.final}")
        if isinstance(report, Ack):
            if o.acked:
                raise VenueProtocolError(f"{where}: second Ack for order {coid!r}")
            o.acked, o.unknown_new = True, False
        elif isinstance(report, Reject):
            if kind != "new":
                raise VenueProtocolError(f"{where}: Reject.request_kind {kind!r}")
            if o.acked or o.filled > 0:
                raise VenueProtocolError(f"{where}: new-order Reject for acknowledged order {coid!r}")
            o.final = self.REJECTED
        elif isinstance(report, Fill):
            if not (o.acked or o.unknown_new):
                raise VenueProtocolError(f"{where}: Fill for order {coid!r} before its Ack (state {o.state_name()})")
            for fname in ("price", "size"):
                val = getattr(report, fname)
                # a float itself: Fill makes its fields by the one number rule (interfaces.py)
                if not math.isfinite(val) or val <= 0:
                    raise VenueProtocolError(f"{where}: Fill.{fname} must be finite > 0, got {val!r}")
            if report.liquidity not in LIQUIDITY:
                raise VenueProtocolError(f"{where}: Fill.liquidity must be one of {LIQUIDITY}")
            size = o.request.size
            new_filled = o.filled + float(report.size)
            if new_filled > size * (1 + _OVERFILL_TOL):
                raise VenueProtocolError(
                    f"{where}: overfill of {coid!r}: {new_filled} > order size {size}"
                )
            # a fill proves the order exists (settles an ambiguous new order)
            o.filled, o.acked, o.unknown_new = new_filled, True, False
            if new_filled >= size * (1 - _FILLED_EPS):
                o.final = self.FILLED
        elif isinstance(report, Canceled):
            if not (o.acked or o.unknown_new):
                raise VenueProtocolError(f"{where}: Canceled for order {coid!r} in state {o.state_name()}")
            o.final = self.CANCELED
        elif isinstance(report, StateUnknown):
            if kind == "cancel":
                o.unknown_cancel = True  # the order's own facts stay as they are
            elif kind == "new":
                if o.acked:
                    raise VenueProtocolError(
                        f"{where}: StateUnknown about the new order {coid!r}, which was acknowledged"
                    )
                o.unknown_new = True
            else:
                raise VenueProtocolError(f"{where}: StateUnknown.request_kind {kind!r}")
        else:
            raise VenueProtocolError(f"{where}: unknown report type {name}")


# The fields of each event class, for the delivery copy. Every event that
# reaches `_deliver` is one of the core's own classes itself (input events
# are checked in `_SourceMerger._pull`, notices and timers are made here).
_EVENT_FIELDS: dict[type, tuple[str, ...]] = {
    cls: tuple(f.name for f in dataclasses.fields(cls)) for cls in EVENT_TYPE_TO_CLASS.values()
}


def _delivered_copy(event: Event, time_ns: int, seq: int) -> Event:
    """A copy of `event` with its delivery time and the strategy's delivery
    number. Field by field (the classes are slotted, so there is nothing
    else to copy): `copy.copy` of a slotted frozen dataclass goes through
    `__getstate__` / `__setstate__` and costs about seven times as much.
    The fields are values already (values.py); `time_ns` was validated as
    an int64 in `_push`."""
    cls = type(event)
    out = object.__new__(cls)
    put = object.__setattr__
    for name in _EVENT_FIELDS[cls]:
        put(out, name, getattr(event, name))
    put(out, "received_time_ns", time_ns)
    put(out, "seq", seq)
    return out


def _is_cancel_answer(report: Any, coid: str) -> bool:
    """A report that answers a cancel of order `coid` (inside on_cancel)."""
    t = type(report)  # the real type: only the core's report classes themselves answer
    if t not in REPORT_CLASSES or report.client_order_id != coid:
        return False
    if t is Canceled:
        return True
    return t in (Reject, StateUnknown) and report.request_kind == "cancel"


def _check_delay(value: Any, what: str) -> int:
    try:
        ivalue = as_int(value, what)  # the one int rule (values.py): an int itself, read once now
    except ValueError as exc:
        raise LatencyModelError(f"{what} must return an int of ns: {exc}") from None
    if ivalue < 0:
        raise LatencyModelError(f"{what} returned a negative delay {ivalue}")
    return ivalue


def _qualname(obj: Any) -> str:
    cls = type(obj)
    return f"{cls.__module__}.{cls.__qualname__}"


def _require_protocol(obj: Any, protocol: type, name: str) -> None:
    missing = [
        m for m in vars(protocol)
        if not m.startswith("_") and callable(vars(protocol)[m]) and not callable(getattr(obj, m, None))
    ]
    if missing:
        raise TypeError(f"{name} {type(obj).__name__} lacks {missing} required by {protocol.__name__}")


class _FifoChannel:
    """One FIFO path (strategy -> venue requests, or venue -> strategy
    notices). An item sent on it arrives at `max(its own time, the previous
    arrival)`, so nothing overtakes an earlier item (equal times are then
    ordered by position in the queue key). "Nothing sent yet" is `None`,
    never a time: every int64 is a valid time, 0 and negatives included."""

    __slots__ = ("_last",)

    def __init__(self) -> None:
        self._last: Optional[int] = None

    def admit(self, time_ns: int) -> int:
        last = self._last
        at = time_ns if last is None or time_ns >= last else last
        self._last = at
        return at


SINGLE_STREAM_NAME = "events"
# the core's own event classes themselves (never a subclass) -> their type
_CLASS_TO_TYPE: dict[type, EventType] = {cls: etype for etype, cls in EVENT_TYPE_TO_CLASS.items()}


def _validate_time_span(time_span: Any) -> Optional[tuple[int, int]]:
    """The run's declared time span (`CoreEngine(time_span_ns=...)`): two
    int64 ns times, first <= last, both included."""
    if time_span is None:
        return None
    if not is_a(time_span, tuple) or tuple.__len__(time_span) != 2:
        raise TimestampUnitError(
            f"time_span_ns must be a (first_ns, last_ns) tuple, got a {type_name(time_span)}"
            + (f" of {tuple.__len__(time_span)}" if is_a(time_span, tuple) else "")
        )
    try:
        lo = int(validate_nanos(tuple.__getitem__(time_span, 0)))
        hi = int(validate_nanos(tuple.__getitem__(time_span, 1)))
    except TimestampUnitError as exc:
        raise TimestampUnitError(f"time_span_ns: {exc}") from exc
    if lo > hi:
        raise TimestampUnitError(f"time_span_ns ({lo}, {hi}): the first time is after the last")
    return lo, hi


def _check_in_span(event: Event, exch: int, span: tuple[int, int], stream: str, number: int) -> None:
    """Both times of an input event must lie in the run's declared span; a
    bare int carries no unit, and this is where its magnitude meets one
    (i0-r4-06: seconds or milliseconds handed over as ns land near 1970)."""
    lo, hi = span
    for label, t in (("exchange_time_ns", exch), ("received_time_ns", int(event.received_time_ns))):
        if not lo <= t <= hi:
            raise TimestampUnitError(
                f"stream {stream!r} event #{number} ({event.EVENT_TYPE.value}) has {label} {t}, "
                f"outside the run's time_span_ns [{lo}, {hi}] -- is it in another unit (s, ms, us) "
                f"handed over as ns?"
            )


class _SourceMerger:
    """Merges named streams by comparing their next events (ordering.py
    `merge_key`: exchange time, type rank, stream name), holding at most one
    pending event per stream. A stream's own order is always kept."""

    def __init__(self, streams: Mapping[str, Iterable[Event]],
                 time_span: Optional[tuple[int, int]] = None) -> None:
        self._span = time_span
        by_name: dict[str, Iterable[Event]] = {}
        for key, stream in streams.items():
            # a str itself (values.py): the names decide the merge order, so
            # no name may compare or sort by methods of its own
            try:
                name = as_text(key, "stream name")  # by its real type (values.py)
            except ValueError:
                raise TypeError(f"stream names must be non-empty str, got a {type_name(key)}") from None
            if not name:
                raise TypeError(f"stream names must be non-empty str, got {key!r}")
            if name in by_name:
                raise TypeError(f"stream name {name!r} given twice")
            by_name[name] = stream
        self._names = sorted(by_name)  # rank = position in sorted(); independent of mapping order
        self._iters: list[Iterator[Event]] = [iter(by_name[n]) for n in self._names]
        self._last: list[Optional[int]] = [None] * len(self._names)
        self.counts: list[int] = [0] * len(self._names)
        self._heads: list[tuple[tuple[int, int, int], Event]] = []  # (merge_key, event)
        for rank in range(len(self._names)):
            self._pull(rank)

    def _pull(self, rank: int) -> None:
        try:
            event = next(self._iters[rank])
        except StopIteration:
            return
        name = self._names[rank]
        if not is_a(event, Event):  # the real type, not what the object claims
            raise SourceEventTypeError(
                f"stream {name!r} yielded a {type_name(event)}, not an Event"
            )
        etype = _CLASS_TO_TYPE.get(type(event))  # the core's own event classes themselves
        if etype is None:
            # an event crosses the source -> venue / strategy paths: one of
            # the core's own classes itself (every field a value, slotted),
            # never a subclass that could decide a field when it is read
            raise SourceEventTypeError(
                f"stream {name!r} yielded a {type_name(event)}, a subclass of the core's Event; the "
                f"core takes its own event classes themselves"
            )
        if etype not in SOURCE_EVENT_TYPES:
            raise SourceEventTypeError(
                f"stream {name!r} yielded {etype.value}; order notices are produced by "
                f"the engine from the fill model's reports (place an order to get one)"
            )
        exch = int(event.exchange_time_ns)
        if self._span is not None:
            _check_in_span(event, exch, self._span, name, self.counts[rank] + 1)
        last = self._last[rank]
        if last is not None and exch < last:
            raise EventOrderError(
                f"stream {name!r} event #{self.counts[rank]} ({etype.value}) has "
                f"exchange_time_ns {exch} < previous {last} in the same stream"
            )
        self._last[rank] = exch
        self.counts[rank] += 1
        heapq.heappush(self._heads, (merge_key(event, rank), event))

    @property
    def n_streams(self) -> int:
        return len(self._names)

    def peek_time(self) -> Optional[int]:
        return self._heads[0][0][0] if self._heads else None

    def pop(self) -> tuple[int, Event]:
        key, event = heapq.heappop(self._heads)
        rank = key[2]
        self._pull(rank)
        return rank, event

    def counts_by_name(self) -> dict[str, int]:
        return dict(zip(self._names, self.counts))


class CoreEngine:
    def __init__(
        self,
        strategy: Strategy,
        events: Union[Iterable[Event], Mapping[str, Iterable[Event]]],
        fill_model: Optional[FillModel] = None,
        latency_model: Optional[LatencyModel] = None,
        cost_model: Optional[CostModel] = None,
        account: Optional[Account] = None,
        *,
        end_time_ns: Optional[int] = None,
        history_limit: Optional[int] = None,
        time_span_ns: Optional[tuple[int, int]] = None,
    ) -> None:
        """`events`: one iterable of source events, or a mapping of stream
        name -> iterable (merged by time, see ordering.py).

        `history_limit`: if set, the strategy's history keeps, per event
        type, at least the last `history_limit` and at most
        `2 * history_limit` delivered events (bounded memory for long tick
        runs); the overall history is exactly what the types keep
        (history.py). A read that would reach into a dropped part raises
        `HistoryTruncatedError`. None keeps everything.

        `time_span_ns`: the run's time span `(first_ns, last_ns)`, both
        included. Given, every input event whose exchange or received time
        lies outside it is refused with `TimestampUnitError` when it is read
        from its stream (a bare int carries no unit; a time in seconds or
        milliseconds handed over as ns lands near 1970). Not given, nothing
        is checked -- every int64 is a time -- and `defaults_used` records
        "time_span" so the result shows the run did not state it. It checks
        the unit of INPUT events only; it does not bound the run: a timer
        the strategy sets, a notice or a request arrival may lie after
        `last_ns` (`end_time_ns` ends a run)."""
        self._strategy = strategy
        time_span = _validate_time_span(time_span_ns)
        self._time_span = time_span
        if is_a(events, Mapping):  # the real type, not what the object claims
            streams = events
        else:
            streams = {SINGLE_STREAM_NAME: events}
        self._merger = _SourceMerger(streams, time_span)
        self._source_count = 0

        defaults: list[str] = []
        if fill_model is None:
            fill_model, _ = NullFillModel(), defaults.append("fill_model")
        if latency_model is None:
            latency_model, _ = ZeroLatency(), defaults.append("latency_model")
        if account is None:
            account, _ = NullAccount(), defaults.append("account")
        _require_protocol(fill_model, FillModel, "fill_model")
        _require_protocol(latency_model, LatencyModel, "latency_model")
        _require_protocol(account, Account, "account")
        if cost_model is not None:
            _require_protocol(cost_model, CostModel, "cost_model")
        else:
            defaults.append("cost_model")
        if time_span is None:
            defaults.append("time_span")
        self._fill_model = fill_model
        self._latency = latency_model
        self._cost_model = cost_model
        self._account = account
        self._defaults = defaults

        # Run settings pass the same checks as event times: an int64 of ns
        # (floats, bools and out-of-range values are refused here, before
        # anything runs). A value in the wrong unit that still fits int64
        # (seconds, say) ends the run before its first entry; `step` refuses
        # that window instead of processing nothing.
        if end_time_ns is not None:
            try:
                end_time_ns = int(validate_nanos(end_time_ns))
            except TimestampUnitError as exc:
                raise TimestampUnitError(f"end_time_ns: {exc}") from exc
        self._end_time_ns = end_time_ns
        if history_limit is not None:
            try:
                history_limit = as_int(history_limit, "history_limit")  # the one int rule (values.py)
            except ValueError as exc:
                raise ValueError(f"history_limit must be a positive int or None: {exc}") from None
            if history_limit < 1:
                raise ValueError(f"history_limit must be a positive int or None, got {history_limit}")
        self._history_limit = history_limit

        self._heap: list[tuple] = []
        self._created = 0  # position of engine-created entries (requests, notices, timers)
        # input -> strategy channel, per stream: the not-yet-delivered events
        # in reception order (received_time_ns, merge position), and each
        # one's scheduled delivery time
        self._pending_by_stream: list[list[tuple[int, int]]] = [[] for _ in range(self._merger.n_streams)]
        self._scheduled: dict[int, int] = {}
        self._now: Optional[int] = None
        self._first: Optional[int] = None
        self._stopped_at_end = False
        # lifecycle (module docstring): the exception that escaped a step,
        # if any (the engine is then FAILED for good), and whether a step is
        # in progress (a call from inside it is a re-entry)
        self._failure: Optional[BaseException] = None
        self._in_step = False

        self._port = _OrderPort()
        self._ledger = _VenueLedger()
        self._forced: dict[str, OrderRequest] = {}
        self._forced_list: list[OrderRequest] = []
        self._history = DeliveredHistory(self._history_limit)
        self._deliveries = 0
        self._outbound = _FifoChannel()  # strategy -> venue: new orders and cancels
        self._notices = _FifoChannel()  # venue -> strategy
        self._order_requests: list[OrderRequest] = []
        self._cancel_requests: list[CancelRequest] = []
        self._fills: list[FillNotice] = []
        self._digest = hashlib.sha256()

    # -- queue -------------------------------------------------------------
    def _push(self, time_ns: int, phase: int, kind: int, payload: Any,
              position: Optional[int] = None, received: Optional[int] = None) -> None:
        """Queue key = (time_ns, phase, received, position) -- ordering.py.
        `position` given: the entry comes from the input (its merge
        position; `received` is its recorded received time for a delivery).
        Otherwise the engine created it and its position is the creation
        count, which is the send / emit / set order on its channel.
        `received` not given: the entry's own time (no in-range sentinel).
        The key is unique, so the payload is never compared, and it does not
        depend on WHEN an input event was pulled from its stream."""
        # The one place every queue time passes: a delay that pushes a time
        # out of int64 fails here, loudly, whichever channel it came from.
        try:
            t = int(validate_nanos(time_ns))
        except TimestampUnitError as exc:
            raise TimestampUnitError(
                f"queue time {time_ns!r} for {type(payload).__name__} is not an int64 of ns "
                f"(a latency model or timer produced an out-of-range time): {exc}"
            ) from exc
        if position is None:
            self._created += 1
            position = self._created
        if received is None:
            received = t
        heapq.heappush(self._heap, (t, phase, received, position, kind, payload))

    def _refill(self) -> None:
        merger = self._merger
        while True:
            head_time = merger.peek_time()
            if head_time is None:
                return
            if self._heap and head_time > self._heap[0][0]:
                return
            self._ingest(*merger.pop())

    def _ingest(self, rank: int, event: Event) -> None:
        etype = event.EVENT_TYPE
        exch = int(event.exchange_time_ns)
        recv = int(event.received_time_ns)
        self._source_count += 1
        position = self._source_count  # merge position (ordering.py)
        if etype in MARKET_EVENT_TYPES:
            self._push(exch, PHASE_VENUE_MARKET, _K_VENUE_MARKET, event, position)
            delay = _check_delay(self._latency.feed_delay_ns(event), "feed_delay_ns")
        else:
            delay = 0
        at = recv + delay
        self._push(at, PHASE_DELIVER_INPUT, _K_DELIVER_INPUT, (rank, event), position, recv)
        heapq.heappush(self._pending_by_stream[rank], (recv, position))
        self._scheduled[position] = at

    # -- public ------------------------------------------------------------
    @property
    def now_ns(self) -> Optional[int]:
        return self._now

    @property
    def failure(self) -> Optional[BaseException]:
        """The exception that escaped a step and left this engine FAILED;
        None while it is usable. For diagnosis only: it is not a result."""
        return self._failure

    def _usable(self, what: str) -> None:
        if self._in_step:
            raise EngineReentryError(
                f"{what}() called from inside a step of the same engine; refused (nothing changed)"
            )
        failure = self._failure
        if failure is not None:
            text = str(failure)
            if len(text) > 300:
                text = text[:300] + "..."
            raise EngineFailedError(
                f"{what}() refused: an exception escaped an earlier step of this engine "
                f"({type(failure).__name__}: {text}); its state may be half-updated, so the run "
                f"is over and no result is produced from it"
            ) from failure

    def step(self) -> bool:
        """Process one queue entry. Returns False when nothing is left (or
        the next entry is past `end_time_ns`). Any exception that escapes
        is re-raised unchanged and leaves the engine FAILED (module
        docstring, "Lifecycle")."""
        self._usable("step")
        self._in_step = True
        try:
            return self._step()
        except BaseException as exc:
            self._failure = exc
            raise
        finally:
            self._in_step = False

    def _step(self) -> bool:
        self._refill()
        if not self._heap:
            return False
        if self._end_time_ns is not None and self._heap[0][0] > self._end_time_ns:
            if self._now is None:
                raise TimestampUnitError(
                    f"end_time_ns {self._end_time_ns} is before the first entry of the run "
                    f"({self._heap[0][0]} ns): the run would process nothing -- is end_time_ns "
                    f"in another unit (s, ms, us)?"
                )
            self._stopped_at_end = True
            return False
        time_ns, _phase, received, position, kind, payload = heapq.heappop(self._heap)
        if self._now is not None and time_ns < self._now:  # pragma: no cover - invariant
            raise RuntimeError(f"queue went back in time: {time_ns} < {self._now}")
        self._now = time_ns
        if self._first is None:
            self._first = time_ns
        if kind == _K_DELIVER_INPUT:
            self._deliver_input(time_ns, received, position, *payload)
        elif kind == _K_DELIVER:
            self._deliver(time_ns, payload)
        elif kind == _K_VENUE_MARKET:
            self._venue_market(time_ns, payload)
        elif kind == _K_VENUE_ORDER:
            self._venue_order(time_ns, payload)
        else:
            self._venue_cancel(time_ns, payload)
        return True

    def run(self) -> EngineResult:
        self._usable("run")
        while self.step():
            pass
        return self.result()

    def result(self) -> EngineResult:
        """The run's result so far. Refused on a FAILED engine and from
        inside a step (a half-processed step is never reported)."""
        self._usable("result")
        return EngineResult(
            events_processed=self._deliveries,
            source_events=self._source_count,
            order_requests=list(self._order_requests),
            cancel_requests=list(self._cancel_requests),
            fills=list(self._fills),
            orders=dict(self._port._registry),
            venue_states=self._ledger.states(),
            models={
                "fill_model": _qualname(self._fill_model),
                "latency_model": _qualname(self._latency),
                "cost_model": _qualname(self._cost_model) if self._cost_model is not None else "none",
                "account": _qualname(self._account),
            },
            defaults_used=list(self._defaults),
            first_time_ns=self._first,
            last_time_ns=self._now,
            stopped_at_end_time=self._stopped_at_end,
            time_span_ns=self._time_span,
            delivery_digest=self._digest.hexdigest(),
            forced_orders=list(self._forced_list),
            source_events_by_stream=self._merger.counts_by_name(),
        )

    # -- strategy side -----------------------------------------------------
    def _deliver_input(self, time_ns: int, received: int, position: int, rank: int, event: Event) -> None:
        """Input -> strategy channel of one stream, in reception order. If
        an event of the same stream that was received earlier has not been
        delivered yet (its feed delay was longer), this one waits for it:
        it is re-queued at that event's delivery time, where the key
        (received, position) puts it after that event. The earlier event is
        always already read from its stream here: it happened at the venue
        no later than it was received, i.e. no later than now."""
        pending = self._pending_by_stream[rank]
        head_recv, head_pos = pending[0]
        if head_pos != position:
            wait_until = self._scheduled[head_pos]
            if wait_until <= time_ns:  # pragma: no cover - invariant of the queue key
                raise RuntimeError("an earlier-received event of the stream is overdue")
            self._scheduled[position] = wait_until
            self._push(wait_until, PHASE_DELIVER_INPUT, _K_DELIVER_INPUT, (rank, event), position, received)
            return
        heapq.heappop(pending)
        del self._scheduled[position]
        self._deliver(time_ns, event)

    def _deliver(self, time_ns: int, event: Event) -> None:
        # A shallow copy with the delivery time and sequence set. The event
        # was validated at construction, and time_ns was validated as int64
        # in `_push` and is >= its received time >= its exchange time.
        # `seq` is the strategy's own delivery count (1, 2, 3, ...), never a
        # queue counter: a queue counter also counts entries for events the
        # strategy has not received yet (e.g. one that happened at the
        # exchange but reaches us later), and its gaps would let a strategy
        # count them -- a side channel to the future.
        delivered = _delivered_copy(event, time_ns, self._deliveries + 1)
        port = self._port
        if delivered.EVENT_TYPE in NOTICE_EVENT_TYPES:
            coid = delivered.client_order_id  # type: ignore[attr-defined]
            if not port.knows(coid):
                # first notice about a forced order: the strategy learns of it now
                port._adopt(dataclasses.replace(self._forced[coid]), time_ns, "forced")
            port._apply_notice(delivered)
        history = self._history
        history.append(delivered)
        self._deliveries += 1
        self._digest.update(repr(delivered).encode())
        self._digest.update(b"\n")
        port._now = time_ns
        window = EventWindow(history.overall, len(history.overall))
        typed_windows = {t: EventWindow(lst, len(lst)) for t, lst in history.typed.items() if lst}
        ctx = StrategyContext(
            visible_events=window,
            current=delivered,
            place_order_cb=port.place,
            cancel_order_cb=port.cancel,
            order_lookup_cb=port.order,
            open_orders_cb=port.open_orders,
            set_timer_cb=port.set_timer,
            typed_events=typed_windows,
            dropped=history.dropped_facts(),
            dropped_counts=history.dropped_count_facts(),
        )
        try:
            self._strategy.on_event(delivered, ctx)
        finally:
            ctx._revoke()
            outbox, port._outbox = port._outbox, []
        self._drain(outbox)

    def _drain(self, outbox: list[tuple]) -> None:
        for item in outbox:
            kind = item[0]
            if kind == "new":
                _, req, sent = item
                delay = _check_delay(self._latency.order_delay_ns(req, sent), "order_delay_ns")
                arrive = self._outbound.admit(sent + delay)
                self._order_requests.append(req)
                self._push(arrive, PHASE_VENUE_REQUEST, _K_VENUE_ORDER, req)
            elif kind == "cancel":
                _, req, sent = item
                delay = _check_delay(self._latency.cancel_delay_ns(req, sent), "cancel_delay_ns")
                arrive = self._outbound.admit(sent + delay)
                self._cancel_requests.append(req)
                self._push(arrive, PHASE_VENUE_REQUEST, _K_VENUE_CANCEL, req)
            else:
                _, at, tag = item
                self._push(at, PHASE_DELIVER_TIMER, _K_DELIVER, ClockEvent(received_time_ns=at, tag=tag))

    # -- venue side --------------------------------------------------------
    def _venue_market(self, time_ns: int, event: Event) -> None:
        if event.EVENT_TYPE is EventType.FUNDING:
            self._account.apply_funding(event)
        elif event.EVENT_TYPE is EventType.LIQUIDATION:
            self._account.apply_liquidation(event)
        reports = self._fill_model.on_market_event(event, time_ns)
        self._handle_reports(time_ns, reports or (), "on_market_event", None)
        forced = self._account.on_market_event(event, time_ns) or ()
        for request in forced:
            self._force(time_ns, request)

    def _force(self, time_ns: int, request: Any) -> None:
        if not is_a(request, OrderRequest):  # the real type, not what the object claims
            raise AccountSocketError(
                f"account.on_market_event returned a {type_name(request)}, not an OrderRequest"
            )
        # the account keeps what it returned; the venue and (later) the
        # strategy's view get objects of their own (api.py fresh_request)
        request = fresh_request(request, OrderRequest, AccountSocketError, "account.on_market_event")
        coid = request.client_order_id
        if not coid:
            coid = f"{FORCED_ID_PREFIX}{len(self._forced_list) + 1}"
            request = dataclasses.replace(request, client_order_id=coid)
        elif not coid.startswith(FORCED_ID_PREFIX):
            raise AccountSocketError(
                f"forced order id {coid!r} must be empty or start with {FORCED_ID_PREFIX!r}"
            )
        if coid in self._forced or coid in self._ledger:
            raise AccountSocketError(f"forced order id {coid!r} is already in use")
        self._forced[coid] = request
        self._forced_list.append(request)
        # A forced order is the venue acting on its own: it reaches the
        # fill model now, without the strategy's order latency and without
        # the account's pre-trade check.
        self._submit_to_venue(time_ns, request)

    def _venue_order(self, time_ns: int, order: OrderRequest) -> None:
        reason = self._account.check_order(order, time_ns)
        if reason is not None:
            # the reason reaches the strategy in a notice: a str itself
            # (values.py), made before anything reads it
            try:
                text = as_text(reason, "reason")  # a str itself (values.py), by its real type
            except ValueError:
                raise AccountSocketError(
                    f"account.check_order must return None or a non-empty str, got a {type_name(reason)}"
                ) from None
            if not text:
                raise AccountSocketError("account.check_order must return None or a non-empty str, got ''")
            reason = text
            self._ledger.arrive(order)
            self._handle_reports(
                time_ns, (Reject(order.client_order_id, reason),), "check_order", order.client_order_id
            )
            return
        self._submit_to_venue(time_ns, order)

    def _submit_to_venue(self, time_ns: int, order: OrderRequest) -> None:
        self._ledger.arrive(order)
        reports = self._fill_model.on_order(order, time_ns) or ()
        self._handle_reports(time_ns, reports, "on_order", order.client_order_id)
        if self._ledger.state(order.client_order_id) == _VenueLedger.ARRIVED:
            raise VenueProtocolError(
                f"on_order: fill model gave no Ack/Reject/StateUnknown for order "
                f"{order.client_order_id!r}"
            )

    def _venue_cancel(self, time_ns: int, request: CancelRequest) -> None:
        coid = request.client_order_id
        if not self._ledger.is_live(coid):
            state = self._ledger.state(coid) or "not at venue"
            self._handle_reports(
                time_ns, (Reject(coid, f"order_not_open:{state}", "cancel"),), "on_cancel", coid
            )
            return
        reports = tuple(self._fill_model.on_cancel(request, time_ns) or ())
        answers = sum(1 for r in reports if _is_cancel_answer(r, coid))
        if answers != 1:
            # one cancel, one answer: the strategy counts its cancels in
            # flight by their answers (api.py `cancels_in_flight`)
            raise VenueProtocolError(
                f"on_cancel: fill model gave {answers} answers (Canceled / cancel Reject / "
                f"cancel StateUnknown) to one cancel of order {coid!r}; exactly one is required"
            )
        self._handle_reports(time_ns, reports, "on_cancel", coid)

    def _handle_reports(self, venue_time: int, reports: Iterable[Any], where: str, subject: Optional[str]) -> None:
        for report in reports:
            self._ledger.apply(report, where, subject)
            coid = report.client_order_id
            if isinstance(report, Fill):
                order = self._ledger.request(coid)
                notice = FillNotice(
                    client_order_id=coid,
                    price=float(report.price),
                    size=float(report.size),
                    side=order.side,
                    liquidity=report.liquidity,
                    venue_time_ns=venue_time,
                )
                if self._cost_model is None:
                    raise MissingCostModelError(
                        "a fill happened but no cost_model was given; pass "
                        "NullCostModel() to state zero cost explicitly"
                    )
                fee = self._cost_model.cost(notice)
                try:
                    fee = as_float(fee, "fee")  # the one number rule (values.py): a float itself, read once now
                except ValueError as exc:
                    raise CostModelError(f"cost model returned a value that is not a number: {exc}") from None
                if not math.isfinite(fee):
                    raise CostModelError(f"cost model returned {fee!r}")
                notice = dataclasses.replace(notice, fee=fee)
                self._account.apply_fill(notice)
                self._fills.append(notice)
                event: Event = OrderFillEvent(
                    received_time_ns=venue_time, client_order_id=coid, price=notice.price,
                    size=notice.size, side=order.side, liquidity=notice.liquidity, fee=notice.fee,
                )
            elif isinstance(report, Ack):
                event = OrderAckEvent(received_time_ns=venue_time, client_order_id=coid,
                                      venue_order_id=report.venue_order_id)
            elif isinstance(report, Reject):
                event = OrderRejectEvent(received_time_ns=venue_time, client_order_id=coid,
                                         reason=report.reason, request_kind=report.request_kind)
            elif isinstance(report, Canceled):
                if coid == subject and where == "on_cancel":
                    answers = "cancel"  # the answer to our cancel
                elif coid == subject and where == "on_order":
                    answers = "new"  # part of the answer to the new order
                else:
                    answers = "venue"  # the venue on its own (expiry, say)
                event = OrderCanceledEvent(received_time_ns=venue_time, client_order_id=coid,
                                           reason=report.reason, answers=answers)
            else:
                event = OrderStateUnknownEvent(received_time_ns=venue_time, client_order_id=coid,
                                               detail=report.detail, request_kind=report.request_kind)
            delay = _check_delay(self._latency.notice_delay_ns(report, venue_time), "notice_delay_ns")
            deliver_at = self._notices.admit(venue_time + delay)
            event = dataclasses.replace(event, received_time_ns=deliver_at, exchange_time_ns=venue_time)
            self._push(deliver_at, PHASE_DELIVER_NOTICE, _K_DELIVER, event)
