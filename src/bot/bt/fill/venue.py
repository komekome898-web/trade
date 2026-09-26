"""`SimVenue`: the core's fill-model socket for item 2 -- order types and the
venue's rules (old item 2) and the fill / queue models (old item 3).

What happens when a request reaches the venue (`on_order`, at its arrival
time):

1. the fault plan (`bot.bt.orders.faults`) may answer instead of the venue;
2. the request's own shape is checked (type, time in force, which prices it
   carries); a malformed request is Rejected with the reason;
3. the venue's rules (`bot.bt.orders.rules`): size (min_qty, qty_step), price
   (tick, price limit), trading hours. A policy the situation needs and the
   run did not declare raises `RuleNotDeclaredError` -- the run stops;
4. reduce-only (against the venue's own net position, built from every fill
   it reported) and post-only (against the displayed book and our own resting
   orders);
5. Ack, then the order acts: a market order executes, a limit order executes
   what is marketable and rests (GTC), cancels the rest (IOC) or fills all or
   nothing (FOK), a stop waits for its trigger, an order outside trading hours
   waits for the open (rule outside_session = queue_to_next_open).

A rejection before the Ack is a Reject; anything after it (an IOC remainder,
a failed FOK, a post-only that would cross at the open, OCO) is Canceled with
the reason.

Aggressive executions walk the displayed book (`book.ExternalBook`), best
level first, each level up to its displayed size; what we took stays taken
until the next book update. Our own resting orders on the other side are in
the way: reaching one is a self-match, decided by rule `self_trade`. Tier 6
prices aggressive executions by the impact function instead. With no book at
all (a trade-only run), rule `market_ref` decides: `last_trade` = the last
print +/- half the declared spread (cost component `spread`), filling the
whole size; `next_bar_open` = the open of the next bar that starts after the
order arrived.

Resting orders fill by the selected tier (`spec.py`), as the maker, at their
limit price. OCO: a fill of one cancels the other (Canceled "oco"); a cancel
of one by the strategy cancels the other ("oco_partner_canceled").
Reduce-only is enforced at every fill: a fill that would grow or flip the
position is cut to what reduces it, and the rest is cancelled.

What does not fill: a book update alone never fills a resting order (only
trades, or bars in tier 2, do; a snapshot showing the other side through our
price is not taken as a trade with us), and a stop fires on a trade (or, in
tier 2, a bar) reaching its trigger, not on a quote.

Same-instant order: everything with time <= t in the L3 feed is applied
first; then the market event (or the request); orders held for the open are
released after a book snapshot at or after the open is applied (in a run with
no book at all, after the first market event at or after the open).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from bot.bt.core import (
    FORCED_ID_PREFIX,
    Ack,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    CancelRequest,
    Canceled,
    Event,
    Fill,
    OrderRequest,
    Reject,
    StateUnknown,
    TradeEvent,
    VenueReport,
)
from bot.bt.costs.schedule import CostSchedule
from bot.bt.orders.client import (
    AMEND,
    AMEND_APPLIED,
    AMENDED_SIZE_FILLED,
    AMENDS_KEY,
    LIQUIDATION,
    ROUNDED_SIZE_FILLED,
    OCO_KEY,
    ORDER_TYPES,
    TIME_IN_FORCE,
)
from bot.bt.orders.errors import ExecutionModelError
from bot.bt.orders.faults import FaultPlan
from bot.bt.orders.product import Product
from bot.bt.orders.rules import VenueRules

from .book import ExternalBook
from .data_wait import DataUnavailableError
from .l3 import L3Add, L3Feed
from .spec import TIER_MECHANISM, FillSpec, FillSpecError

_EPS = 1e-12


def _opp(side_name: str) -> str:
    return "ask" if side_name == "bid" else "bid"


@dataclass(eq=False)
class _L3Entry:
    order_id: str
    side: str
    price: float
    size: float
    canceled: bool = False


@dataclass(eq=False)
class _Queue:
    ahead: float = 0.0
    prev_level: float = 0.0
    entries: Optional[list] = None  # l3 stances: shared _L3Entry objects ahead of us


@dataclass(eq=False)
class _VOrder:
    request: OrderRequest
    coid: str
    side: str  # "buy" | "sell"
    kind: str
    price: Optional[float]
    trigger: Optional[float]
    size: float  # size in force (amend / reduce-only cap may lower it)
    tif: str
    post_only: bool
    reduce_only: bool
    oco: Optional[str]
    arrival_ns: int
    seq: int
    filled: float = 0.0
    state: str = "new"  # held | resting | stop | bar_open | done
    rest_since: Optional[int] = None
    hold_until: Optional[int] = None
    queue: Optional[_Queue] = None
    size_cut_reason: str = ""

    @property
    def sign(self) -> int:
        return 1 if self.side == "buy" else -1

    @property
    def book_side(self) -> str:
        return "bid" if self.side == "buy" else "ask"

    @property
    def remaining(self) -> float:
        return max(self.size - self.filled, 0.0)

    def reaches(self, price: float) -> bool:
        """A trade / level at `price` reaches our limit (touches or crosses)."""
        return price <= self.price if self.side == "buy" else price >= self.price  # type: ignore[operator]

    def through(self, price: float) -> bool:
        return price < self.price if self.side == "buy" else price > self.price  # type: ignore[operator]


@dataclass
class FillRecord:
    time_ns: int
    client_order_id: str
    price: float
    size: float
    liquidity: str


class SimVenue:
    """The fill-model socket. Every argument is required (keyword-only):
    `faults=FaultPlan(())` for none, `l3=None` for a run without a per-order
    feed."""

    def __init__(self, *, product: Product, rules: VenueRules, fill: FillSpec, costs: CostSchedule,
                 faults: FaultPlan, l3: Optional[L3Feed]) -> None:
        for name, obj, cls in (("product", product, Product), ("rules", rules, VenueRules),
                               ("fill", fill, FillSpec), ("costs", costs, CostSchedule),
                               ("faults", faults, FaultPlan)):
            if type(obj) is not cls:
                raise ExecutionModelError(f"SimVenue {name} must be a {cls.__name__}, got {type(obj).__name__}")
        if l3 is not None and type(l3) is not L3Feed:
            raise ExecutionModelError("SimVenue l3 must be an L3Feed or None")
        if fill.cancel_stance in ("l3_advance", "l3_mark") and l3 is None:
            raise FillSpecError(f"cancel_stance {fill.cancel_stance!r} reads a per-order feed; l3 is None")
        self.product, self.rules, self.fill, self.costs, self.faults, self.l3 = product, rules, fill, costs, faults, l3
        self.tier = fill.tier
        self.book = ExternalBook()
        self.last_trade: Optional[float] = None
        self.position = 0.0
        self.impact_shift = 0.0
        self.arrivals: dict[str, int] = {}
        self.fills: list[FillRecord] = []
        self._live: dict[str, _VOrder] = {}
        self._filled_any: set[str] = set()  # orders that had a fill (for OCO partners arriving later)
        self._oco_done: dict[str, str] = {}  # partner id -> why it must not live
        self._seq = 0
        self._l3_orders: dict[str, _L3Entry] = {}
        self._l3_levels: dict[tuple[str, float], list[_L3Entry]] = {}
        # how often each met cost component was used (a declared one that is
        # never used shows 0 here, e.g. a spread in a run that always has a book)
        self.used: dict[str, int] = {"spread": 0}

    # ------------------------------------------------------------------ feed
    def _advance(self, t: int) -> None:
        if self.l3 is None:
            return
        for item in self.l3.due(t):
            if type(item) is L3Add:
                if item.order_id in self._l3_orders:
                    raise ExecutionModelError(f"L3 order {item.order_id!r} added twice")
                e = _L3Entry(item.order_id, item.side, float(item.price), float(item.size))
                self._l3_orders[item.order_id] = e
                self._l3_levels.setdefault((item.side, e.price), []).append(e)
            else:
                e = self._l3_orders.pop(item.order_id, None)
                if e is None:
                    continue  # a cancel of an order the feed never added: nothing in the queue moves
                e.canceled = True
                level = self._l3_levels.get((e.side, e.price), [])
                if e in level:
                    level.remove(e)
                if self.fill.cancel_stance == "l3_advance":
                    for o in self._live.values():
                        if o.queue is not None and o.queue.entries is not None and e in o.queue.entries:
                            o.queue.entries.remove(e)
                # l3_mark: the entry stays in each queue, marked; skipped when reached

    # ------------------------------------------------------------- reporting
    def _fill(self, o: _VOrder, price: float, qty: float, liquidity: str, t: int, out: list) -> float:
        """Report a fill of up to `qty`; returns what was filled."""
        qty = min(qty, o.remaining)
        if o.reduce_only:
            if self.position == 0 or (self.position > 0) == (o.side == "buy"):
                self._close(o, "reduce_only", out)
                return 0.0
            qty = min(qty, abs(self.position))
        if qty <= _EPS:
            return 0.0
        out.append(Fill(o.coid, price, qty, liquidity))
        o.filled += qty
        self.position += o.sign * qty
        if abs(self.position) < 1e-12:
            self.position = 0.0
        self.fills.append(FillRecord(t, o.coid, price, qty, liquidity))
        self._filled_any.add(o.coid)
        if o.remaining <= _EPS * max(1.0, o.size):
            o.state = "done"
            self._live.pop(o.coid, None)
            if o.size < float(o.request.size) * (1 - 1e-12):
                out.append(Canceled(o.coid, o.size_cut_reason or AMENDED_SIZE_FILLED))
        if o.oco is not None:
            self._oco_partner_off(o.oco, "oco", out)
        return qty

    def _close(self, o: _VOrder, reason: str, out: list) -> None:
        if o.state == "done":
            return
        o.state = "done"
        self._live.pop(o.coid, None)
        out.append(Canceled(o.coid, reason))

    def _oco_partner_off(self, partner: str, reason: str, out: list) -> None:
        p = self._live.get(partner)
        if p is not None:
            self._close(p, reason, out)
        elif partner not in self._filled_any:
            # the partner has not reached the venue yet: refuse it when it does
            self._oco_done.setdefault(partner, "oco_partner_filled" if reason == "oco" else reason)

    # --------------------------------------------------------------- sockets
    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[VenueReport]:
        t = int(venue_time_ns)
        self._advance(t)
        out: list = []
        if type(event) is BookSnapshotEvent:
            self.book.apply_snapshot(event, t)
            self._book_changed(None)
        elif type(event) is BookDeltaEvent:
            self.book.apply_delta(event, t)
            self._book_changed((event.side, float(event.price)))
        elif type(event) is TradeEvent:
            self.last_trade = float(event.price)
            self._on_trade(event, t, out)
        elif type(event) is BarEvent:
            self._on_bar(event, t, out)
        self._release_held(t, out)
        return out

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        t = int(venue_time_ns)
        self._advance(t)
        coid = order.client_order_id
        self.arrivals[coid] = self.arrivals.get(coid, 0) + 1
        fault = self.faults.new_order_fault(coid)
        if fault == "reject":
            return [Reject(coid, "injected_reject")]
        if fault == "timeout":
            return [StateUnknown(coid, "injected timeout: no answer; the request did not reach the book")]
        if fault == "unknown":
            return [StateUnknown(coid, "injected ambiguous error answer; the request did not reach the book")]
        ack = (StateUnknown(coid, "injected: the answer was lost; the order lives")
               if fault == "ack_lost" else Ack(coid, f"sim-{coid}"))
        out: list = []
        if order.order_type == AMEND:
            return self._amend(order, t, ack)
        if order.order_type == LIQUIDATION:
            return self._liquidation(order, t, ack)
        o, reason = self._new_order(order, t)
        if o is None:
            return [Reject(coid, reason)]
        if o.coid in self._oco_done:
            return [Reject(coid, self._oco_done[o.coid])]
        if self.rules.has_hours and not self.rules.is_open(t):
            if self.rules.need("outside_session") == "reject":
                return [Reject(coid, "outside_session")]
            o.state, o.hold_until = "held", self.rules.next_open(t)
            out.append(ack)
            self._live[coid] = o
            return out
        refuse = self._activation_refusal(o)
        if refuse is not None:
            if refuse[0] == "reject":
                return [Reject(coid, refuse[1])]
            out.append(ack)
            out.append(Canceled(coid, refuse[1]))
            return out
        if o.tif in ("IOC", "FOK") and not self.book.seen:
            return [Reject(coid, "ioc_fok_need_a_book")]
        out.append(ack)
        self._live[coid] = o
        self._activate(o, t, out)
        return out

    def on_cancel(self, request: CancelRequest, venue_time_ns: int) -> Sequence[VenueReport]:
        t = int(venue_time_ns)
        self._advance(t)
        coid = request.client_order_id
        fault = self.faults.cancel_fault(coid)
        if fault == "cancel_reject":
            return [Reject(coid, "injected_cancel_reject", "cancel")]
        if fault == "cancel_timeout":
            return [StateUnknown(coid, "injected cancel timeout: no answer", "cancel")]
        o = self._live.get(coid)
        if o is None:
            # the core thinks it may live (an ambiguous answer), the venue has no such order
            return [Reject(coid, "order_not_found", "cancel")]
        out: list = []
        self._close(o, "canceled", out)
        if o.oco is not None:
            self._oco_partner_off(o.oco, "oco_partner_canceled", out)
        return out

    # ----------------------------------------------------------- new orders
    def _new_order(self, order: OrderRequest, t: int) -> tuple[Optional[_VOrder], str]:
        kind = order.order_type
        if kind not in ORDER_TYPES:
            return None, f"unknown_order_type:{kind}"
        if order.time_in_force not in TIME_IN_FORCE:
            return None, f"unknown_time_in_force:{order.time_in_force}"
        needs_price = kind in ("limit", "stop_limit")
        needs_trigger = kind in ("stop", "stop_limit")
        if needs_price != (order.price is not None):
            return None, "price_required" if needs_price else "price_not_allowed"
        if needs_trigger != (order.trigger_price is not None):
            return None, "trigger_required" if needs_trigger else "trigger_not_allowed"
        if order.post_only and kind != "limit":
            return None, "post_only_needs_limit"
        if needs_trigger and order.time_in_force != "GTC":
            return None, "stop_needs_gtc"
        extra = order.extra_dict()
        unknown = set(extra) - {OCO_KEY}
        if unknown:
            return None, f"unknown_extra:{sorted(unknown)}"
        oco = extra.get(OCO_KEY)
        if oco is not None and (type(oco) is not str or not oco or oco == order.client_order_id):
            return None, "bad_oco_partner"
        size = float(order.size)
        p = self.product
        rules = self.rules
        if size < p.min_qty * (1 - 1e-12):
            if rules.need("below_min_qty") == "reject":
                return None, "below_min_qty"
        size_cut = ""
        if not p.on_step(size):
            if rules.need("off_step") == "reject":
                return None, "off_step"
            size = p.round_qty_down(size)
            size_cut = ROUNDED_SIZE_FILLED
            if size < p.min_qty * (1 - 1e-12):
                return None, "below_min_qty_after_rounding"
        price = None if order.price is None else float(order.price)
        trigger = None if order.trigger_price is None else float(order.trigger_price)
        if price is not None and not p.on_tick(price):
            if rules.need("off_tick") == "reject":
                return None, "off_tick"
            price = p.round_price(price, "down" if order.side == "buy" else "up")
        if trigger is not None and not p.on_tick(trigger):
            if rules.need("off_tick") == "reject":
                return None, "off_tick_trigger"
            # a stop is passive the other way: it waits until the price gets worse
            trigger = p.round_price(trigger, "up" if order.side == "buy" else "down")
        lim = rules.price_limit
        if lim is not None:
            if price is not None and not lim.allows(price):
                return None, "outside_price_limit"
            if trigger is not None and not lim.allows(trigger):
                return None, "trigger_outside_price_limit"
        self._seq += 1
        o = _VOrder(request=order, coid=order.client_order_id, side=order.side, kind=kind, price=price,
                    trigger=trigger, size=size, tif=order.time_in_force, post_only=bool(order.post_only),
                    reduce_only=bool(order.reduce_only), oco=oco, arrival_ns=t, seq=self._seq,
                    size_cut_reason=size_cut)
        return o, ""

    def _crosses(self, o: _VOrder) -> bool:
        """Would a limit order at o.price take liquidity now (displayed book
        or our own resting orders on the other side)?"""
        best = self.book.best(_opp(o.book_side))
        if best is not None and o.reaches(best):
            return True
        return any(x.state == "resting" and x.side != o.side and o.reaches(x.price)  # type: ignore[arg-type]
                   for x in self._live.values())

    def _activation_refusal(self, o: _VOrder) -> Optional[tuple[str, str]]:
        """("reject" | "cancel", reason) when the order may not act now."""
        if o.reduce_only:
            if self.position == 0 or (self.position > 0) == (o.side == "buy"):
                return ("reject", "reduce_only_would_increase")
            if o.size > abs(self.position):
                o.size = abs(self.position)
                o.size_cut_reason = "reduce_only_size_cut_filled"
        if o.post_only:
            if not self.book.seen:
                return ("reject", "post_only_needs_a_book")
            if self._crosses(o):
                policy = self.rules.need("post_only")
                return ("reject" if policy == "reject_if_crossing" else "cancel", "post_only_would_take")
        return None

    def _activate(self, o: _VOrder, t: int, out: list) -> None:
        if o.kind == "market":
            self._aggress(o, t, out, limit=None)
            self._market_remainder(o, out)
        elif o.kind == "limit":
            self._activate_limit(o, t, out)
        else:  # stop / stop_limit wait for their trigger
            o.state = "stop"
            o.rest_since = t

    def _market_remainder(self, o: _VOrder, out: list) -> None:
        """What a market (or fired stop) order could not fill now: cancelled by
        rule market_remainder (an order waiting for the next bar's open
        stays)."""
        if o.state in ("done", "bar_open") or o.remaining <= _EPS:
            return
        self.rules.need("market_remainder")  # "cancel" is the one policy the model knows
        self._close(o, "market_remainder", out)

    def _activate_limit(self, o: _VOrder, t: int, out: list) -> None:
        if o.tif == "FOK":
            if self._available(o) < o.remaining - _EPS:
                self._close(o, "fok_not_filled", out)
                return
        if self.book.seen or self._own_opposite(o):
            self._aggress(o, t, out, limit=o.price)
        if o.state == "done":
            return
        if o.tif in ("IOC", "FOK"):
            if o.remaining > _EPS:
                self._close(o, "ioc_remainder" if o.tif == "IOC" else "fok_not_filled", out)
            return
        o.state, o.rest_since = "resting", t
        if self.tier == 0:
            self._fill(o, o.price, o.remaining, "maker", t, out)  # type: ignore[arg-type]
            return
        if self.tier >= 5:
            self._init_queue(o)

    def _own_opposite(self, o: _VOrder) -> list[_VOrder]:
        own = [x for x in self._live.values()
               if x is not o and x.state == "resting" and x.side != o.side]
        own.sort(key=lambda x: ((x.price if o.side == "buy" else -x.price), x.seq))  # type: ignore[operator]
        return own

    def _available(self, o: _VOrder) -> float:
        total = 0.0
        for p, s in self.book.side(_opp(o.book_side)):
            if o.reaches(p):
                total += s
        return total

    # --------------------------------------------------- aggressive executions
    def _aggress(self, o: _VOrder, t: int, out: list, limit: Optional[float]) -> None:
        if self.tier == 6:
            self._aggress_impact(o, t, out, limit)
            return
        if not self.book.seen and o.kind in ("market", "stop"):
            self._aggress_no_book(o, t, out, limit)
            return
        opp = _opp(o.book_side)
        levels = self.book.side(opp)
        own = self._own_opposite(o)
        while o.state != "done" and o.remaining > _EPS:
            ext = next((lv for lv in levels if lv[1] > _EPS), None)
            mine = own[0] if own else None
            if mine is not None and (limit is None or o.reaches(mine.price)) and \
                    (ext is None or (mine.price <= ext[0] if o.side == "buy" else mine.price >= ext[0])):
                policy = self.rules.need("self_trade")
                if policy in ("cancel_maker", "cancel_both"):
                    self._close(mine, "self_trade", out)
                    own.pop(0)
                if policy in ("cancel_taker", "cancel_both"):
                    self._close(o, "self_trade", out)
                    return
                continue
            if ext is None or (limit is not None and not o.reaches(ext[0])):
                return
            got = self._fill(o, ext[0], min(o.remaining, ext[1]), "taker", t, out)
            if got <= _EPS:
                return
            self.book.consume(opp, ext[0], got)

    def _aggress_impact(self, o: _VOrder, t: int, out: list, limit: Optional[float]) -> None:
        spec = self.fill.impact
        basis_name = spec.basis  # type: ignore[union-attr]
        if basis_name == "opposite_best":
            basis_name = "best_ask" if o.side == "buy" else "best_bid"
        if not self.book.seen:
            raise DataUnavailableError(self.product.venue, "book",
                                       f"the impact function's basis {spec.basis!r} needs a displayed book")  # type: ignore[union-attr]
        basis = self.book.mid() if basis_name == "mid" else self.book.best("ask" if basis_name == "best_ask" else "bid")
        if basis is None:
            # the book is known and that side is empty now: nothing to price from
            if limit is None:
                self._close(o, "impact_basis_empty", out)
            return
        own = self._own_opposite(o)
        q = o.remaining
        price = spec.price(o.sign, q, basis + self.impact_shift)  # type: ignore[union-attr]
        if own and (limit is None or o.reaches(own[0].price)) and \
                (own[0].price <= price if o.side == "buy" else own[0].price >= price):
            policy = self.rules.need("self_trade")
            if policy in ("cancel_maker", "cancel_both"):
                for x in own:
                    if o.side == "buy" and x.price <= price or o.side == "sell" and x.price >= price:  # type: ignore[operator]
                        self._close(x, "self_trade", out)
            if policy in ("cancel_taker", "cancel_both"):
                self._close(o, "self_trade", out)
                return
        if limit is not None and not o.reaches(price):
            return
        got = self._fill(o, price, q, "taker", t, out)
        self.impact_shift += spec.permanent_shift(o.sign, got)  # type: ignore[union-attr]

    def _aggress_no_book(self, o: _VOrder, t: int, out: list, limit: Optional[float]) -> None:
        ref = self.rules.need("market_ref")
        if ref == "next_bar_open":
            if o.kind in ("market", "stop"):
                o.state = "bar_open"
            return
        if self.last_trade is None:
            if o.kind in ("market", "stop"):
                self._close(o, "no_price_yet", out)
            return
        half = float(self.costs.need("spread")) / 2.0
        self.used["spread"] = self.used.get("spread", 0) + 1
        price = self.last_trade + o.sign * half
        if limit is not None and not o.reaches(price):
            return
        self._fill(o, price, o.remaining, "taker", t, out)

    # -------------------------------------------------------------- queues
    def _init_queue(self, o: _VOrder) -> None:
        stance = self.fill.cancel_stance
        if stance is None:
            raise FillSpecError(f"a resting order under tier {self.tier} needs a cancel_stance (none declared)")
        q = _Queue()
        if stance in ("l3_advance", "l3_mark"):
            q.entries = [e for e in self._l3_levels.get((o.book_side, o.price), []) if not e.canceled]  # type: ignore[arg-type]
        else:
            if not self.book.seen:
                raise DataUnavailableError(self.product.venue, "book",
                                           f"tier {self.tier} (queue position) needs the displayed size at the "
                                           f"order's price when it rests")
            level = self.book.size_at(o.book_side, o.price)  # type: ignore[arg-type]
            q.ahead = level * (1.0 - self.fill.cancel_rate) if stance == "discount_at_entry" else level  # type: ignore[operator]
            q.prev_level = level
        o.queue = q

    def _book_changed(self, level: Optional[tuple[str, float]]) -> None:
        stance = self.fill.cancel_stance
        if self.tier < 5 or stance in (None, "none", "discount_at_entry", "l3_advance", "l3_mark"):
            for o in self._live.values():
                if o.queue is not None and o.queue.entries is None:
                    o.queue.prev_level = self.book.size_at(o.book_side, o.price)  # type: ignore[arg-type]
            return
        for o in self._resting_by_priority():
            if o.queue is None or o.queue.entries is not None:
                continue
            if level is not None and (o.book_side, o.price) != level:
                continue
            new = self.book.size_at(o.book_side, o.price)  # type: ignore[arg-type]
            q = o.queue
            if stance == "snapshot_cap":
                q.ahead = min(q.ahead, new)
            elif stance == "prob":
                d = q.prev_level - new
                if d > 0:
                    front, back = q.ahead, max(q.prev_level - q.ahead, 0.0)
                    wf, wb = self.fill.prob_weight(front), self.fill.prob_weight(back)
                    p_back = wb / (wb + wf) if wb + wf > 0 else 0.0
                    q.ahead = min(front - (1.0 - p_back) * d + min(back - p_back * d, 0.0), new)
                    q.ahead = max(q.ahead, 0.0)
            q.prev_level = new

    def _resting_by_priority(self) -> list[_VOrder]:
        rest = [o for o in self._live.values() if o.state == "resting"]
        # better prices first on each side, then arrival
        rest.sort(key=lambda o: (0 if o.side == "buy" else 1, (-o.price if o.side == "buy" else o.price), o.seq))  # type: ignore[operator]
        return rest

    # --------------------------------------------------------------- trades
    def _on_trade(self, ev: TradeEvent, t: int, out: list) -> None:
        px, budget_all = float(ev.price), float(ev.size)
        tier = self.tier
        if tier in (1, 3, 4):
            budget = budget_all
            for o in self._resting_by_priority():
                if o.state != "resting":
                    continue
                if tier == 1 and o.through(px) or tier == 3 and o.reaches(px):
                    self._fill(o, o.price, o.remaining, "maker", t, out)  # type: ignore[arg-type]
                elif tier == 4 and o.reaches(px) and budget > _EPS:
                    budget -= self._fill(o, o.price, min(o.remaining, budget), "maker", t, out)  # type: ignore[arg-type]
        elif tier >= 5:
            self._queue_trade(ev, px, budget_all, t, out)
        self._trigger_stops_on_trade(px, t, out)

    def _queue_trade(self, ev: TradeEvent, px: float, qty: float, t: int, out: list) -> None:
        levels: dict[tuple[str, float], list[_VOrder]] = {}
        for o in self._resting_by_priority():
            if o.through(px):
                self._fill(o, o.price, o.remaining, "maker", t, out)  # type: ignore[arg-type]
            elif o.price == px:
                levels.setdefault((o.side, px), []).append(o)
        for (side, _p), orders in levels.items():
            hits_us = ev.side in ("", "sell" if side == "buy" else "buy")
            if not hits_us:
                continue
            orders.sort(key=lambda o: o.seq)
            budget, ext_used = qty, 0.0
            for o in orders:
                if o.state != "resting":
                    continue
                q = o.queue
                if q.entries is not None:  # type: ignore[union-attr]
                    while budget > _EPS and q.entries:  # type: ignore[union-attr]
                        e = q.entries[0]  # type: ignore[union-attr]
                        if e.canceled or e.size <= _EPS:
                            q.entries.pop(0)  # type: ignore[union-attr]
                            continue
                        use = min(e.size, budget)
                        e.size -= use
                        budget -= use
                        ext_used += use
                        if e.size <= _EPS:
                            q.entries.pop(0)  # type: ignore[union-attr]
                else:
                    q.ahead = max(q.ahead - ext_used, 0.0)  # type: ignore[union-attr]
                    use = min(q.ahead, budget)  # type: ignore[union-attr]
                    q.ahead -= use  # type: ignore[union-attr]
                    budget -= use
                    ext_used += use
                if budget > _EPS and self._ahead(o) <= _EPS:
                    budget -= self._fill(o, o.price, min(o.remaining, budget), "maker", t, out)  # type: ignore[arg-type]
            if ext_used > 0:
                self.book.consume("bid" if side == "buy" else "ask", px, ext_used)
                for o in orders:
                    if o.queue is not None and o.queue.entries is None:
                        o.queue.prev_level = max(o.queue.prev_level - ext_used, 0.0)

    @staticmethod
    def _ahead(o: _VOrder) -> float:
        q = o.queue
        if q is None:
            return 0.0
        if q.entries is not None:
            return sum(e.size for e in q.entries if not e.canceled)
        return q.ahead

    def tier_numbers(self) -> dict[str, int]:
        """C2-5 as numbers: `mechanism` = the highest tier this model can
        select (6), `selected` = the tier this run declared (the model has no
        default tier, so what it runs at "as is" is always the declared one)."""
        return {"mechanism": TIER_MECHANISM, "selected": self.tier}

    def open_orders(self) -> list[tuple[str, float]]:
        """(side, remaining size) of every order live at the venue (resting,
        waiting for a trigger, for the open or for a bar): what could still
        fill. For the account's margin check."""
        return [(o.side, o.remaining) for o in sorted(self._live.values(), key=lambda x: x.seq)
                if o.state != "done" and o.kind != "liquidation"]

    def queue_ahead(self, client_order_id: str) -> Optional[dict]:
        """What is ahead of a resting order in its queue: `size` (live size
        ahead) and `entries` (per-order entries still in front, marked ones
        included for l3_mark). None for an order without a queue."""
        o = self._live.get(client_order_id)
        if o is None or o.queue is None:
            return None
        if o.queue.entries is not None:
            return {"size": self._ahead(o), "entries": len(o.queue.entries)}
        return {"size": o.queue.ahead, "entries": None}

    def _trigger_stops_on_trade(self, px: float, t: int, out: list) -> None:
        stops = [o for o in self._live.values() if o.state == "stop"]
        stops.sort(key=lambda o: o.seq)
        for o in stops:
            if o.state != "stop":
                continue
            hit = px >= o.trigger if o.side == "buy" else px <= o.trigger  # type: ignore[operator]
            if hit:
                self._fire_stop(o, t, out)

    def _fire_stop(self, o: _VOrder, t: int, out: list) -> None:
        if o.kind == "stop":
            self._aggress(o, t, out, limit=None)
            self._market_remainder(o, out)
        else:  # stop_limit becomes a limit order now
            o.kind = "limit"
            o.state = "new"
            self._activate_limit(o, t, out)

    # ----------------------------------------------------------------- bars
    def _on_bar(self, ev: BarEvent, t: int, out: list) -> None:
        start = ev.start_time_ns
        if start is None and self.fill.bar_ns is not None:
            start = t - self.fill.bar_ns
        needs_start = self.tier == 2 or any(o.state == "bar_open" for o in self._live.values())
        if start is None:
            if needs_start:
                raise FillSpecError("a bar without start_time_ns and no bar_ns: which orders it may fill is unknown")
            return
        for o in sorted(self._live.values(), key=lambda x: x.seq):
            # a bar that starts after the order arrived (an order arriving at a
            # bar's start came after that instant's prints)
            if o.state == "bar_open" and start > o.arrival_ns:
                half = float(self.costs.need("spread")) / 2.0
                self.used["spread"] = self.used.get("spread", 0) + 1
                self._fill(o, float(ev.open) + o.sign * half, o.remaining, "taker", t, out)
        if self.tier != 2:
            return
        for o in sorted(self._live.values(), key=lambda x: x.seq):
            if o.rest_since is None or start <= o.rest_since:
                continue  # the bar began before (or as) the order rested: its low/high may predate it
            if o.state == "resting":
                hit = ev.low <= o.price if o.side == "buy" else ev.high >= o.price  # type: ignore[operator]
                if hit:
                    self._fill(o, o.price, o.remaining, "maker", t, out)  # type: ignore[arg-type]
            elif o.state == "stop" and o.kind == "stop":
                hit = ev.high >= o.trigger if o.side == "buy" else ev.low <= o.trigger  # type: ignore[operator]
                if hit:
                    px = max(o.trigger, ev.open) if o.side == "buy" else min(o.trigger, ev.open)  # type: ignore[type-var]
                    self._fill(o, px, o.remaining, "taker", t, out)

    # ----------------------------------------------------------- held orders
    def _release_held(self, t: int, out: list) -> None:
        held = [o for o in self._live.values() if o.state == "held"]
        if not held:
            return
        held.sort(key=lambda o: o.seq)
        for o in held:
            if t < o.hold_until:  # type: ignore[operator]
                continue
            if not self.rules.is_open(t):
                o.hold_until = self.rules.next_open(t)
                continue
            if self.book.seen and self.book.fresh_since_ns < o.hold_until:  # type: ignore[operator]
                continue  # wait for a book taken at or after the open (the one before it is stale)
            o.state = "new"
            refuse = self._activation_refusal(o)
            if refuse is not None:
                self._close(o, refuse[1], out)
                continue
            self._activate(o, t, out)

    # ------------------------------------------------------------ amend / forced
    def _amend(self, order: OrderRequest, t: int, ack: VenueReport) -> list:
        coid = order.client_order_id
        extra = order.extra_dict()
        target_id = extra.get(AMENDS_KEY)
        if set(extra) != {AMENDS_KEY} or type(target_id) is not str:
            return [Reject(coid, "amend_needs_its_target")]
        o = self._live.get(target_id)
        if o is None or o.state != "resting" or o.side != order.side or o.price is None:
            return [Reject(coid, "amend_target_not_resting")]
        if order.price is None:
            return [Reject(coid, "amend_needs_a_price")]
        new_size, new_price = float(order.size), float(order.price)
        p, rules = self.product, self.rules
        if new_size > float(o.request.size) * (1 + 1e-12):
            # the core's ledger holds the first size; a larger one could not be reported as filled
            return [Reject(coid, "amend_above_first_size")]
        if new_size <= o.filled + _EPS:
            return [Reject(coid, "amend_size_not_above_filled")]
        if new_size < p.min_qty * (1 - 1e-12) and rules.need("below_min_qty") == "reject":
            return [Reject(coid, "below_min_qty")]
        if not p.on_step(new_size):
            if rules.need("off_step") == "reject":
                return [Reject(coid, "off_step")]
            new_size = p.round_qty_down(new_size)
            if new_size <= o.filled + _EPS:
                return [Reject(coid, "amend_size_not_above_filled")]
        if not p.on_tick(new_price):
            if rules.need("off_tick") == "reject":
                return [Reject(coid, "off_tick")]
            new_price = p.round_price(new_price, "down" if o.side == "buy" else "up")
        if rules.price_limit is not None and not rules.price_limit.allows(new_price):
            return [Reject(coid, "outside_price_limit")]
        price_changed = new_price != o.price
        if o.post_only and price_changed:
            old = o.price
            o.price = new_price
            crosses = self._crosses(o)
            o.price = old
            if crosses:
                return [Reject(coid, "post_only_would_take")]
        out: list = [ack]
        size_up, size_down = new_size > o.size, new_size < o.size
        lose = price_changed or size_up
        if size_down and not lose and self.tier >= 5:
            lose = rules.need("amend_qty_down") == "lose_priority"
        o.price, o.size = new_price, new_size
        if new_size < float(o.request.size) * (1 - 1e-12):
            o.size_cut_reason = AMENDED_SIZE_FILLED
        out.append(Canceled(coid, AMEND_APPLIED))
        if lose:
            o.rest_since = t
            if price_changed and (self.book.seen or self._own_opposite(o)) and self._crosses(o):
                self._aggress(o, t, out, limit=o.price)
                if o.state == "done":
                    return out
            if self.tier >= 5:
                self._init_queue(o)
        return out

    def _liquidation(self, order: OrderRequest, t: int, ack: VenueReport) -> list:
        coid = order.client_order_id
        if not coid.startswith(FORCED_ID_PREFIX):
            return [Reject(coid, "liquidation_is_venue_only")]
        if order.price is None:
            return [Reject(coid, "liquidation_needs_its_price")]
        self._seq += 1
        o = _VOrder(request=order, coid=coid, side=order.side, kind=LIQUIDATION, price=float(order.price),
                    trigger=None, size=float(order.size), tif="GTC", post_only=False, reduce_only=True, oco=None,
                    arrival_ns=t, seq=self._seq)
        out: list = [ack]
        self._live[coid] = o
        self._fill(o, float(order.price), o.remaining, "taker", t, out)
        if o.state != "done":
            self._close(o, "liquidation_size_above_position", out)
        return out
