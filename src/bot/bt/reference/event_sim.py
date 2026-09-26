"""Slow reference simulator for tick / order-book / funding events.

Written from the item-4 requirement text only (see SPEC.md). Every quantity is
an exact Fraction. All behaviour-changing choices that the requirement text
does not fix are required keyword arguments of `simulate` with no default.

Time model (two clocks, both UTC int64 nanoseconds):
  * t_exch - when the event happens at the exchange (matching uses this);
  * t_recv - when the strategy can receive it (t_recv >= t_exch).
The strategy is called once per delivered item and is handed only items whose
t_recv is <= the current time, so it structurally cannot look ahead.

Happenings are processed in the order of the key
    (time, rank, tie)
with rank 0 = exchange-side market event (at t_exch, tie = input seq),
     rank 1 = order / cancel arrival at the exchange (tie = submission counter),
     rank 2 = delivery to the strategy (at t_recv; market events before
              notifications, market events by seq, notifications by creation).
So an order arriving at time t sees the exchange state after every market
event with t_exch <= t, and never interacts with those events.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Optional

from bot.bt.reference.num import choice, nonneg_int, ns, on_grid, q, q_str

MARKET_KINDS = ("trade", "book", "funding", "bar", "clock")
NOTE_KINDS = ("ack", "reject", "fill", "cancel_ack", "cancel_reject", "expired")
SIDES = ("buy", "sell")

_R_EXCH, _R_ARRIVE, _R_DELIVER = 0, 1, 2


# ---------------------------------------------------------------- input data
@dataclass(frozen=True)
class Event:
    """One market-data event. Build with `make_event` to get validation."""
    kind: str
    t_exch: int
    t_recv: int
    seq: int
    price: Optional[Fraction] = None
    qty: Optional[Fraction] = None
    bids: tuple = ()
    asks: tuple = ()
    rate: Optional[Fraction] = None
    open: Optional[Fraction] = None
    high: Optional[Fraction] = None
    low: Optional[Fraction] = None
    close: Optional[Fraction] = None


def _levels(raw, name: str, descending: bool) -> tuple:
    out = []
    for i, lv in enumerate(raw or ()):
        p, s = lv
        p, s = q(p, f"{name}[{i}].price"), q(s, f"{name}[{i}].qty")
        if p <= 0 or s <= 0:
            raise ValueError(f"{name}[{i}]: price and qty must be > 0")
        out.append((p, s))
    for a, b in zip(out, out[1:]):
        if (descending and not a[0] > b[0]) or (not descending and not a[0] < b[0]):
            raise ValueError(f"{name}: prices must be strictly {'descending' if descending else 'ascending'}")
    return tuple(out)


def make_event(kind: str, t_exch: int, t_recv: int, seq: int, **kw) -> Event:
    """Validated constructor. Refuses unknown kinds, float/bool times,
    t_recv < t_exch, and inconsistent payloads (crossed book, bad bar)."""
    choice(kind, MARKET_KINDS, "kind")
    t_exch, t_recv = ns(t_exch, "t_exch"), ns(t_recv, "t_recv")
    if t_recv < t_exch:
        raise ValueError(f"t_recv {t_recv} < t_exch {t_exch}")
    if isinstance(seq, bool) or not isinstance(seq, int):
        raise TypeError("seq must be int")
    allowed = {
        "trade": {"price", "qty"},
        "book": {"bids", "asks"},
        "funding": {"rate", "price"},
        "bar": {"open", "high", "low", "close"},
        "clock": set(),
    }[kind]
    extra = set(kw) - allowed
    if extra:
        raise ValueError(f"{kind}: unexpected fields {sorted(extra)}")
    if kind == "trade":
        p, s = q(kw["price"], "price"), q(kw["qty"], "qty")
        if p <= 0 or s <= 0:
            raise ValueError("trade price and qty must be > 0")
        return Event(kind, t_exch, t_recv, seq, price=p, qty=s)
    if kind == "book":
        bids = _levels(kw.get("bids"), "bids", descending=True)
        asks = _levels(kw.get("asks"), "asks", descending=False)
        if bids and asks and not bids[0][0] < asks[0][0]:
            raise ValueError("crossed or locked book (best bid >= best ask)")
        return Event(kind, t_exch, t_recv, seq, bids=bids, asks=asks)
    if kind == "funding":
        r = q(kw["rate"], "rate")
        p = q(kw["price"], "price") if kw.get("price") is not None else None
        if p is not None and p <= 0:
            raise ValueError("funding mark price must be > 0")
        return Event(kind, t_exch, t_recv, seq, rate=r, price=p)
    if kind == "bar":
        o, h, l, c = (q(kw[k], k) for k in ("open", "high", "low", "close"))
        if not (l <= min(o, c) and h >= max(o, c) and l > 0):
            raise ValueError("bar must satisfy 0 < low <= min(open,close), high >= max(open,close)")
        return Event(kind, t_exch, t_recv, seq, open=o, high=h, low=l, close=c)
    return Event(kind, t_exch, t_recv, seq)


# --------------------------------------------------------- strategy actions
@dataclass(frozen=True)
class Market:
    cid: str
    side: str
    qty: object


@dataclass(frozen=True)
class Limit:
    cid: str
    side: str
    qty: object
    price: object
    post_only: bool


@dataclass(frozen=True)
class Cancel:
    cid: str


@dataclass(frozen=True)
class Note:
    """Notification from the exchange to the strategy."""
    kind: str
    t_exch: int
    t_recv: int
    cid: str
    side: Optional[str] = None
    price: Optional[Fraction] = None
    qty: Optional[Fraction] = None
    fee: Optional[Fraction] = None
    liquidity: Optional[str] = None  # "maker" | "taker" for fills
    reason: Optional[str] = None


@dataclass(frozen=True)
class Context:
    """What the strategy sees: the current time and every delivered item
    (market events and notifications) in delivery order."""
    now: int
    visible: tuple


def known_position(visible: tuple) -> Fraction:
    """Position implied by the fills the strategy has been told about."""
    pos = Fraction(0)
    for it in visible:
        if isinstance(it, Note) and it.kind == "fill":
            pos += it.qty if it.side == "buy" else -it.qty
    return pos


# ------------------------------------------------------------------- result
@dataclass
class Result:
    fills: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    deliveries: list = field(default_factory=list)  # (t_recv, "event"/"note", seq-or-cid, kind)
    equity_curve: list = field(default_factory=list)  # (t_exch, mark, equity) after each trade
    funding_payments: list = field(default_factory=list)  # (t_exch, mark, rate, payment)
    funding_skipped: list = field(default_factory=list)  # (t_exch, reason)
    open_orders_at_end: list = field(default_factory=list)
    position: Fraction = Fraction(0)
    cash: Fraction = Fraction(0)
    initial_cash: Fraction = Fraction(0)
    avg_cost: Optional[Fraction] = None
    realized: Fraction = Fraction(0)
    fees: Fraction = Fraction(0)
    funding: Fraction = Fraction(0)
    last_mark: Optional[Fraction] = None

    @property
    def unrealized(self) -> Fraction:
        if self.position == 0 or self.last_mark is None:
            return Fraction(0)
        return (self.last_mark - self.avg_cost) * self.position

    @property
    def equity(self) -> Optional[Fraction]:
        if self.position != 0 and self.last_mark is None:
            return None
        mark = self.last_mark if self.last_mark is not None else Fraction(0)
        return self.cash + self.position * mark

    def to_dict(self) -> dict:
        def note(n: Note) -> dict:
            d = {"kind": n.kind, "t_exch": n.t_exch, "t_recv": n.t_recv, "cid": n.cid}
            for k in ("side", "liquidity", "reason"):
                if getattr(n, k) is not None:
                    d[k] = getattr(n, k)
            for k in ("price", "qty", "fee"):
                if getattr(n, k) is not None:
                    d[k] = q_str(getattr(n, k))
            return d
        eq = self.equity
        return {
            "fills": [note(n) for n in self.fills],
            "notes": [note(n) for n in self.notes],
            "equity_curve": [[t, q_str(m), q_str(e)] for t, m, e in self.equity_curve],
            "funding_payments": [[t, q_str(m), q_str(r), q_str(p)] for t, m, r, p in self.funding_payments],
            "funding_skipped": [list(x) for x in self.funding_skipped],
            "open_orders_at_end": list(self.open_orders_at_end),
            "position": q_str(self.position),
            "cash": q_str(self.cash),
            "realized": q_str(self.realized),
            "unrealized": q_str(self.unrealized),
            "fees": q_str(self.fees),
            "funding": q_str(self.funding),
            "equity": None if eq is None else q_str(eq),
        }


# --------------------------------------------------------------- simulation
@dataclass
class _Order:
    cid: str
    kind: str  # "market" | "limit"
    side: str
    qty: Fraction
    remaining: Fraction
    price: Optional[Fraction]
    post_only: bool
    arrive_no: int


def simulate(
    events,
    strategy: Callable[[Context], object],
    *,
    initial_cash,
    maker_rate,
    taker_rate,
    order_latency_ns: int,
    cancel_latency_ns: int,
    notify_latency_ns: int,
    tick_size,
    lot_size,
    min_qty,
    liquidity: str,
    limit_cross: str,
    limit_fill_qty: str,
) -> Result:
    """Run the events through the strategy. See SPEC.md section 2.

    liquidity:      "book"   - market orders walk the latest book snapshot;
                               limits that cross the book execute on arrival
                               as taker (walk up to the limit), rest remains.
                    "trades" - no book: market orders fill at the price of the
                               next trade after arrival; limits never execute
                               on arrival (post_only has no effect).
    limit_cross:    "strict" - a resting buy limit fills only when a trade
                               prints strictly below it (sell: strictly above);
                    "touch"  - also when the trade prints at the limit.
    limit_fill_qty: "full"      - every qualifying resting order fills its full
                                  remaining quantity;
                    "trade_qty" - the trade's quantity is shared out by price
                                  then arrival priority.
    Resting limits always fill at their own limit price (never at a better
    price) and pay maker_rate; everything else pays taker_rate.
    """
    initial_cash = q(initial_cash, "initial_cash")
    maker_rate, taker_rate = q(maker_rate, "maker_rate"), q(taker_rate, "taker_rate")
    lat_o = nonneg_int(order_latency_ns, "order_latency_ns")
    lat_c = nonneg_int(cancel_latency_ns, "cancel_latency_ns")
    lat_n = nonneg_int(notify_latency_ns, "notify_latency_ns")
    tick, lot, minq = q(tick_size, "tick_size"), q(lot_size, "lot_size"), q(min_qty, "min_qty")
    if tick <= 0 or lot <= 0 or minq <= 0:
        raise ValueError("tick_size, lot_size and min_qty must be > 0")
    choice(liquidity, ("book", "trades"), "liquidity")
    choice(limit_cross, ("strict", "touch"), "limit_cross")
    choice(limit_fill_qty, ("full", "trade_qty"), "limit_fill_qty")

    events = list(events)
    seqs = set()
    for e in events:
        if not isinstance(e, Event):
            raise TypeError("events must be Event (use make_event)")
        if e.seq in seqs:
            raise ValueError(f"duplicate seq {e.seq}")
        seqs.add(e.seq)

    res = Result(cash=initial_cash, initial_cash=initial_cash)
    heap: list = []
    counter = [0]

    def push(t: int, rank: int, tie: tuple, payload) -> None:
        counter[0] += 1
        heapq.heappush(heap, (t, rank, tie, counter[0], payload))

    for e in events:
        if e.kind in ("trade", "book", "funding"):
            push(e.t_exch, _R_EXCH, (e.seq,), ("exch", e))
        push(e.t_recv, _R_DELIVER, (0, e.seq), ("deliver_event", e))

    visible: list = []
    note_no = [0]
    arrive_no = [0]
    seen_cids: set = set()
    open_orders: dict = {}  # cid -> _Order (resting limits and waiting market orders)
    state = {"book": None, "consumed": {}, "last_trade": None}

    def note(kind, t_exch, cid, **kw) -> Note:
        n = Note(kind=kind, t_exch=t_exch, t_recv=t_exch + lat_n, cid=cid, **kw)
        res.notes.append(n)
        if kind == "fill":
            res.fills.append(n)
        note_no[0] += 1
        push(n.t_recv, _R_DELIVER, (1, note_no[0]), ("deliver_note", n))
        return n

    def apply_fill(t: int, o: _Order, price: Fraction, qty: Fraction, liq: str) -> None:
        rate = maker_rate if liq == "maker" else taker_rate
        fee = price * qty * rate
        signed = qty if o.side == "buy" else -qty
        pos = res.position
        res.cash -= signed * price + fee
        res.fees += fee
        if pos != 0 and (pos > 0) != (signed > 0):
            closing = min(abs(signed), abs(pos))
            res.realized += closing * (price - res.avg_cost) * (1 if pos > 0 else -1)
            new = pos + signed
            if new == 0:
                res.avg_cost = None
            elif (new > 0) != (pos > 0):
                res.avg_cost = price
            res.position = new
        else:
            new = pos + signed
            res.avg_cost = price if pos == 0 else (res.avg_cost * abs(pos) + price * abs(signed)) / abs(new)
            res.position = new
        o.remaining -= qty
        note("fill", t, o.cid, side=o.side, price=price, qty=qty, fee=fee, liquidity=liq)

    def book_side(side: str):
        """Opposite levels with already-consumed quantity removed."""
        b = state["book"]
        if b is None:
            return None
        lv = b.asks if side == "buy" else b.bids
        out = []
        for p, s in lv:
            left = s - state["consumed"].get((side, p), Fraction(0))
            if left > 0:
                out.append((p, left))
        return out

    def walk(t: int, o: _Order, limit: Optional[Fraction]) -> None:
        for p, avail in book_side(o.side) or ():
            if o.remaining == 0:
                break
            if limit is not None and ((o.side == "buy" and p > limit) or (o.side == "sell" and p < limit)):
                break
            take = min(avail, o.remaining)
            state["consumed"][(o.side, p)] = state["consumed"].get((o.side, p), Fraction(0)) + take
            apply_fill(t, o, p, take, "taker")

    def valid_qty(x: Fraction) -> Optional[str]:
        if x <= 0:
            return "qty_not_positive"
        if not on_grid(x, lot):
            return "qty_off_lot"
        if x < minq:
            return "qty_below_min"
        return None

    def arrive(t: int, act) -> None:
        cid = act.cid
        if isinstance(act, Cancel):
            o = open_orders.pop(cid, None)
            if o is None:
                note("cancel_reject", t, cid, reason="not_open")
            else:
                note("cancel_ack", t, cid, side=o.side, qty=o.remaining)
            return
        if cid in seen_cids:
            note("reject", t, cid, reason="duplicate_cid")
            return
        seen_cids.add(cid)
        side = act.side
        qty = q(act.qty, "qty")
        why = valid_qty(qty)
        price = None
        if why is None and isinstance(act, Limit):
            price = q(act.price, "price")
            if price <= 0:
                why = "price_not_positive"
            elif not on_grid(price, tick):
                why = "price_off_tick"
        if why is not None:
            note("reject", t, cid, side=side, reason=why)
            return
        arrive_no[0] += 1
        o = _Order(cid, "market" if isinstance(act, Market) else "limit", side, qty, qty,
                   price, bool(getattr(act, "post_only", False)), arrive_no[0])
        if o.kind == "market":
            if liquidity == "book":
                if state["book"] is None:
                    note("reject", t, cid, side=side, reason="no_book")
                    return
                note("ack", t, cid, side=side, qty=qty)
                walk(t, o, None)
                if o.remaining > 0:
                    note("expired", t, cid, side=side, qty=o.remaining, reason="insufficient_depth")
            else:
                note("ack", t, cid, side=side, qty=qty)
                open_orders[cid] = o  # waits for the next trade
            return
        # limit order
        if liquidity == "book":
            levels = book_side(side) or []
            crosses = bool(levels) and ((side == "buy" and levels[0][0] <= price) or
                                        (side == "sell" and levels[0][0] >= price))
            if crosses and o.post_only:
                note("reject", t, cid, side=side, reason="post_only_would_cross")
                return
            note("ack", t, cid, side=side, qty=qty, price=price)
            if crosses:
                walk(t, o, price)
        else:
            note("ack", t, cid, side=side, qty=qty, price=price)
        if o.remaining > 0:
            open_orders[cid] = o

    def on_trade(e: Event) -> None:
        t, px = e.t_exch, e.price
        state["last_trade"] = px
        waiting = sorted((o for o in open_orders.values() if o.kind == "market"), key=lambda o: o.arrive_no)
        for o in waiting:
            apply_fill(t, o, px, o.remaining, "taker")
            del open_orders[o.cid]

        def qualifies(o: _Order) -> bool:
            if o.side == "buy":
                return px < o.price or (limit_cross == "touch" and px == o.price)
            return px > o.price or (limit_cross == "touch" and px == o.price)

        lims = [o for o in open_orders.values() if o.kind == "limit" and qualifies(o)]
        lims.sort(key=lambda o: ((-o.price if o.side == "buy" else o.price), o.arrive_no))
        budget = {"buy": e.qty, "sell": e.qty}
        for o in lims:
            if limit_fill_qty == "full":
                take = o.remaining
            else:
                take = min(o.remaining, budget[o.side])
                budget[o.side] -= take
            if take > 0:
                apply_fill(t, o, o.price, take, "maker")
            if o.remaining == 0:
                del open_orders[o.cid]
        res.last_mark = px
        res.equity_curve.append((t, px, res.cash + res.position * px))

    def on_exch(e: Event) -> None:
        if e.kind == "trade":
            on_trade(e)
        elif e.kind == "book":
            state["book"] = e
            state["consumed"] = {}
        elif e.kind == "funding":
            mark = e.price if e.price is not None else state["last_trade"]
            if mark is None:
                res.funding_skipped.append((e.t_exch, "no_mark"))
                return
            pay = -res.position * mark * e.rate
            res.cash += pay
            res.funding += pay
            res.funding_payments.append((e.t_exch, mark, e.rate, pay))

    def call_strategy(now: int) -> None:
        ctx = Context(now=now, visible=tuple(visible))
        acts = strategy(ctx)
        if acts is None:
            return
        for a in acts:
            if isinstance(a, Cancel):
                if not isinstance(a.cid, str):
                    raise TypeError("cid must be str")
                push(now + lat_c, _R_ARRIVE, (), ("arrive", a))
                continue
            if not isinstance(a, (Market, Limit)):
                raise TypeError(f"unknown action {a!r}")
            if not isinstance(a.cid, str):
                raise TypeError("cid must be str")
            choice(a.side, SIDES, "side")
            if isinstance(a, Limit) and not isinstance(a.post_only, bool):
                raise TypeError("post_only must be bool")
            push(now + lat_o, _R_ARRIVE, (), ("arrive", a))

    while heap:
        t, rank, _tie, _c, (what, obj) = heapq.heappop(heap)
        if what == "exch":
            on_exch(obj)
        elif what == "arrive":
            arrive(t, obj)
        elif what == "deliver_event":
            visible.append(obj)
            res.deliveries.append((t, "event", obj.seq, obj.kind))
            call_strategy(t)
        elif what == "deliver_note":
            visible.append(obj)
            res.deliveries.append((t, "note", obj.cid, obj.kind))
            call_strategy(t)

    res.open_orders_at_end = sorted(
        [{"cid": o.cid, "kind": o.kind, "side": o.side, "remaining": q_str(o.remaining),
          "price": None if o.price is None else q_str(o.price)} for o in open_orders.values()],
        key=lambda d: d["cid"])
    return res
