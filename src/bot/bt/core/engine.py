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
  strategy at venue time + notice delay; both channels are FIFO (a later
  request never overtakes an earlier one, a later notice never overtakes an
  earlier one), as on a single connection.

The event source is consumed lazily: the engine pulls the next source event
only when the queue has nothing earlier to process, so a source can be a
generator over a file larger than memory, and no future source event is
held anywhere a strategy could reach. The source must be non-decreasing in
`exchange_time_ns`; a backwards step raises `EventOrderError` (the core
never re-sorts data silently). Events sharing a timestamp may arrive in any
order; ordering.py decides.

Nothing here is market-specific; fills, delays, fees and bookkeeping are
the sockets' job (interfaces.py).
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import heapq
import math
import numbers
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional

from .api import CancelRequest, OrderRequest, OrderView, StrategyContext, _OrderPort
from .errors import (
    CostModelError,
    EventOrderError,
    LatencyModelError,
    MissingCostModelError,
    SourceEventTypeError,
    VenueProtocolError,
)
from .events import (
    LIQUIDITY,
    MARKET_EVENT_TYPES,
    NOTICE_EVENT_TYPES,
    SOURCE_EVENT_TYPES,
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
    Reject,
    StateUnknown,
    ZeroLatency,
)
from .ordering import DELIVERY_PRIORITY, VENUE_CANCEL, VENUE_MARKET, VENUE_ORDER
from .strategy import Strategy
from .window import EventWindow

_K_VENUE_MARKET = 0
_K_VENUE_ORDER = 1
_K_VENUE_CANCEL = 2
_K_DELIVER = 3

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
    defaults_used: list[str] = field(default_factory=list)
    first_time_ns: Optional[int] = None
    last_time_ns: Optional[int] = None
    stopped_at_end_time: bool = False
    delivery_digest: str = ""  # sha256 over every delivered event, in order

    @property
    def open_orders(self) -> list[OrderView]:
        return [v for v in self.orders.values() if v.is_open]


class _VenueLedger:
    """The venue-side history of every order, used to reject impossible
    reports from a fill model."""

    ARRIVED = "ARRIVED"
    LIVE = "LIVE"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    UNKNOWN = "STATE_UNKNOWN"
    TERMINAL = frozenset({FILLED, CANCELED, REJECTED})

    def __init__(self) -> None:
        self.state: dict[str, str] = {}
        self.orders: dict[str, OrderRequest] = {}
        self.filled: dict[str, float] = {}

    def arrive(self, order: OrderRequest) -> None:
        coid = order.client_order_id
        if coid in self.state:  # pragma: no cover - the port refuses duplicates
            raise VenueProtocolError(f"order {coid!r} reached the venue twice")
        self.state[coid] = self.ARRIVED
        self.orders[coid] = order
        self.filled[coid] = 0.0

    def is_live(self, coid: str) -> bool:
        return self.state.get(coid) in (self.LIVE, self.UNKNOWN)

    def apply(self, report: Any, where: str, subject: Optional[str]) -> None:
        coid = getattr(report, "client_order_id", None)
        if isinstance(report, Reject) and report.request_kind == "cancel":
            # A cancel reject speaks about the cancel, not the order: it is
            # valid in any order state, but only as the answer to that cancel.
            if where != "on_cancel" or subject != coid:
                raise VenueProtocolError(f"{where}: cancel Reject for {coid!r} outside its cancel")
            return
        if coid not in self.state:
            raise VenueProtocolError(
                f"{where}: {type(report).__name__} for order {coid!r}, which has not "
                f"reached the venue -- a fill model may not act on an order before "
                f"its arrival time"
            )
        st = self.state[coid]
        name = type(report).__name__
        if st in self.TERMINAL:
            raise VenueProtocolError(f"{where}: {name} for order {coid!r} after terminal state {st}")
        if isinstance(report, Ack):
            if st not in (self.ARRIVED, self.UNKNOWN):
                raise VenueProtocolError(f"{where}: second Ack for order {coid!r}")
            self.state[coid] = self.LIVE
        elif isinstance(report, Reject):
            if report.request_kind == "new":
                if st not in (self.ARRIVED, self.UNKNOWN):
                    raise VenueProtocolError(f"{where}: new-order Reject for acknowledged order {coid!r}")
                self.state[coid] = self.REJECTED
            else:
                raise VenueProtocolError(f"{where}: Reject.request_kind {report.request_kind!r}")
        elif isinstance(report, Fill):
            if st not in (self.LIVE, self.UNKNOWN):
                raise VenueProtocolError(f"{where}: Fill for order {coid!r} before its Ack (state {st})")
            for fname in ("price", "size"):
                val = getattr(report, fname)
                if isinstance(val, bool) or not isinstance(val, numbers.Real) or not math.isfinite(val) or val <= 0:
                    raise VenueProtocolError(f"{where}: Fill.{fname} must be finite > 0, got {val!r}")
            if report.liquidity not in LIQUIDITY:
                raise VenueProtocolError(f"{where}: Fill.liquidity must be one of {LIQUIDITY}")
            size = self.orders[coid].size
            new_filled = self.filled[coid] + float(report.size)
            if new_filled > size * (1 + _OVERFILL_TOL):
                raise VenueProtocolError(
                    f"{where}: overfill of {coid!r}: {new_filled} > order size {size}"
                )
            self.filled[coid] = new_filled
            self.state[coid] = self.FILLED if new_filled >= size * (1 - _FILLED_EPS) else self.LIVE
        elif isinstance(report, Canceled):
            if st not in (self.LIVE, self.UNKNOWN):
                raise VenueProtocolError(f"{where}: Canceled for order {coid!r} in state {st}")
            self.state[coid] = self.CANCELED
        elif isinstance(report, StateUnknown):
            self.state[coid] = self.UNKNOWN
        else:
            raise VenueProtocolError(f"{where}: unknown report type {name}")


def _check_delay(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise LatencyModelError(f"{what} must return an int of ns, got {value!r}")
    ivalue = int(value)
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


class CoreEngine:
    def __init__(
        self,
        strategy: Strategy,
        events: Iterable[Event],
        fill_model: Optional[FillModel] = None,
        latency_model: Optional[LatencyModel] = None,
        cost_model: Optional[CostModel] = None,
        account: Optional[Account] = None,
        *,
        end_time_ns: Optional[int] = None,
        history_limit: Optional[int] = None,
    ) -> None:
        """`history_limit`: if set, the strategy's history keeps at least
        the last `history_limit` and at most `2 * history_limit` delivered
        events (bounded memory for long tick runs). None keeps everything."""
        self._strategy = strategy
        self._source: Iterator[Event] = iter(events)
        self._head: Optional[Event] = None
        self._source_done = False
        self._last_source_exchange: Optional[int] = None
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
        self._fill_model = fill_model
        self._latency = latency_model
        self._cost_model = cost_model
        self._account = account
        self._defaults = defaults

        self._end_time_ns = end_time_ns
        if history_limit is not None and (isinstance(history_limit, bool) or history_limit < 1):
            raise ValueError("history_limit must be a positive int or None")
        self._history_limit = history_limit

        self._heap: list[tuple] = []
        self._seq = 0
        self._now: Optional[int] = None
        self._first: Optional[int] = None
        self._stopped_at_end = False

        self._port = _OrderPort()
        self._ledger = _VenueLedger()
        self._history: list[Event] = []
        self._deliveries = 0
        self._last_outbound = 0
        self._last_notice = 0
        self._order_requests: list[OrderRequest] = []
        self._cancel_requests: list[CancelRequest] = []
        self._fills: list[FillNotice] = []
        self._digest = hashlib.sha256()

    # -- queue -------------------------------------------------------------
    def _push(self, time_ns: int, priority: int, kind: int, payload: Any) -> None:
        self._seq += 1
        heapq.heappush(self._heap, (int(time_ns), priority, self._seq, kind, payload))

    def _next_source(self) -> Optional[Event]:
        if self._head is None and not self._source_done:
            try:
                self._head = next(self._source)
            except StopIteration:
                self._source_done = True
        return self._head

    def _refill(self) -> None:
        while True:
            head = self._next_source()
            if head is None:
                return
            if self._heap and int(head.exchange_time_ns) > self._heap[0][0]:
                return
            self._head = None
            self._ingest(head)

    def _ingest(self, event: Event) -> None:
        if not isinstance(event, Event):
            raise SourceEventTypeError(f"source yielded {type(event).__name__}, not an Event")
        etype = event.EVENT_TYPE
        if etype not in SOURCE_EVENT_TYPES:
            raise SourceEventTypeError(
                f"source yielded {etype.value}; order notices are produced by the "
                f"engine from the fill model's reports (place an order to get one)"
            )
        exch = int(event.exchange_time_ns)
        if self._last_source_exchange is not None and exch < self._last_source_exchange:
            raise EventOrderError(
                f"source event #{self._source_count} ({etype.value}) has exchange_time_ns "
                f"{exch} < previous {self._last_source_exchange}"
            )
        self._last_source_exchange = exch
        self._source_count += 1
        if etype in MARKET_EVENT_TYPES:
            self._push(exch, VENUE_MARKET, _K_VENUE_MARKET, event)
            delay = _check_delay(self._latency.feed_delay_ns(event), "feed_delay_ns")
        else:
            delay = 0
        self._push(int(event.received_time_ns) + delay, DELIVERY_PRIORITY[etype], _K_DELIVER, event)

    # -- public ------------------------------------------------------------
    @property
    def now_ns(self) -> Optional[int]:
        return self._now

    def step(self) -> bool:
        """Process one queue entry. Returns False when nothing is left (or
        the next entry is past `end_time_ns`)."""
        self._refill()
        if not self._heap:
            return False
        if self._end_time_ns is not None and self._heap[0][0] > self._end_time_ns:
            self._stopped_at_end = True
            return False
        time_ns, _prio, seq, kind, payload = heapq.heappop(self._heap)
        if self._now is not None and time_ns < self._now:  # pragma: no cover - invariant
            raise RuntimeError(f"queue went back in time: {time_ns} < {self._now}")
        self._now = time_ns
        if self._first is None:
            self._first = time_ns
        if kind == _K_DELIVER:
            self._deliver(time_ns, seq, payload)
        elif kind == _K_VENUE_MARKET:
            self._venue_market(time_ns, payload)
        elif kind == _K_VENUE_ORDER:
            self._venue_order(time_ns, payload)
        else:
            self._venue_cancel(time_ns, payload)
        return True

    def run(self) -> EngineResult:
        while self.step():
            pass
        return self.result()

    def result(self) -> EngineResult:
        return EngineResult(
            events_processed=self._deliveries,
            source_events=self._source_count,
            order_requests=list(self._order_requests),
            cancel_requests=list(self._cancel_requests),
            fills=list(self._fills),
            orders=dict(self._port._registry),
            venue_states=dict(self._ledger.state),
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
            delivery_digest=self._digest.hexdigest(),
        )

    # -- strategy side -----------------------------------------------------
    def _deliver(self, time_ns: int, seq: int, event: Event) -> None:
        # A shallow copy with the delivery time and sequence set. The event
        # was validated at construction and time_ns >= its received time >=
        # its exchange time, so re-running validation would only cost time.
        delivered = copy.copy(event)
        object.__setattr__(delivered, "received_time_ns", time_ns)
        object.__setattr__(delivered, "seq", seq)
        if delivered.EVENT_TYPE in NOTICE_EVENT_TYPES:
            self._port._apply_notice(delivered)
        limit = self._history_limit
        if limit is not None and len(self._history) >= 2 * limit:
            # amortised O(1): a new list, so no live view is affected
            self._history = self._history[-(limit - 1):] if limit > 1 else []
        self._history.append(delivered)
        self._deliveries += 1
        self._digest.update(repr(delivered).encode())
        self._digest.update(b"\n")
        port = self._port
        port._now = time_ns
        window = EventWindow(self._history, len(self._history))
        ctx = StrategyContext(
            visible_events=window,
            current=delivered,
            place_order_cb=port.place,
            cancel_order_cb=port.cancel,
            order_lookup_cb=port.order,
            open_orders_cb=port.open_orders,
            set_timer_cb=port.set_timer,
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
                arrive = max(sent + delay, self._last_outbound)
                self._last_outbound = arrive
                self._order_requests.append(req)
                self._push(arrive, VENUE_ORDER, _K_VENUE_ORDER, req)
            elif kind == "cancel":
                _, req, sent = item
                delay = _check_delay(self._latency.cancel_delay_ns(req, sent), "cancel_delay_ns")
                arrive = max(sent + delay, self._last_outbound)
                self._last_outbound = arrive
                self._cancel_requests.append(req)
                self._push(arrive, VENUE_CANCEL, _K_VENUE_CANCEL, req)
            else:
                _, at, tag = item
                self._push(at, DELIVERY_PRIORITY[EventType.CLOCK], _K_DELIVER, ClockEvent(received_time_ns=at, tag=tag))

    # -- venue side --------------------------------------------------------
    def _venue_market(self, time_ns: int, event: Event) -> None:
        if event.EVENT_TYPE is EventType.FUNDING:
            self._account.apply_funding(event)
        elif event.EVENT_TYPE is EventType.LIQUIDATION:
            self._account.apply_liquidation(event)
        reports = self._fill_model.on_market_event(event, time_ns)
        self._handle_reports(time_ns, reports or (), "on_market_event", None)

    def _venue_order(self, time_ns: int, order: OrderRequest) -> None:
        self._ledger.arrive(order)
        reports = self._fill_model.on_order(order, time_ns) or ()
        self._handle_reports(time_ns, reports, "on_order", order.client_order_id)
        if self._ledger.state[order.client_order_id] == _VenueLedger.ARRIVED:
            raise VenueProtocolError(
                f"on_order: fill model gave no Ack/Reject/StateUnknown for order "
                f"{order.client_order_id!r}"
            )

    def _venue_cancel(self, time_ns: int, request: CancelRequest) -> None:
        coid = request.client_order_id
        if not self._ledger.is_live(coid):
            state = self._ledger.state.get(coid, "not at venue")
            self._handle_reports(
                time_ns, (Reject(coid, f"order_not_open:{state}", "cancel"),), "on_cancel", coid
            )
            return
        reports = tuple(self._fill_model.on_cancel(request, time_ns) or ())
        answered = any(
            getattr(r, "client_order_id", None) == coid
            and (
                isinstance(r, Canceled)
                or (isinstance(r, (Reject, StateUnknown)) and r.request_kind == "cancel")
            )
            for r in reports
        )
        if not answered:
            raise VenueProtocolError(
                f"on_cancel: fill model gave no Canceled / cancel Reject / cancel "
                f"StateUnknown for order {coid!r}"
            )
        self._handle_reports(time_ns, reports, "on_cancel", coid)

    def _handle_reports(self, venue_time: int, reports: Iterable[Any], where: str, subject: Optional[str]) -> None:
        for report in reports:
            self._ledger.apply(report, where, subject)
            coid = report.client_order_id
            if isinstance(report, Fill):
                order = self._ledger.orders[coid]
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
                if isinstance(fee, bool) or not isinstance(fee, numbers.Real) or not math.isfinite(fee):
                    raise CostModelError(f"cost model returned {fee!r}")
                notice = dataclasses.replace(notice, fee=float(fee))
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
                event = OrderCanceledEvent(received_time_ns=venue_time, client_order_id=coid,
                                           reason=report.reason)
            else:
                event = OrderStateUnknownEvent(received_time_ns=venue_time, client_order_id=coid,
                                               detail=report.detail, request_kind=report.request_kind)
            delay = _check_delay(self._latency.notice_delay_ns(report, venue_time), "notice_delay_ns")
            deliver_at = max(venue_time + delay, self._last_notice)
            self._last_notice = deliver_at
            event = dataclasses.replace(event, received_time_ns=deliver_at, exchange_time_ns=venue_time)
            self._push(deliver_at, DELIVERY_PRIORITY[event.EVENT_TYPE], _K_DELIVER, event)
