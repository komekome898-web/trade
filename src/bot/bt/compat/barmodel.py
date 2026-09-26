"""The bar backtest model of the new engine (item 4): the stated rules of
tests/bt/battery/item_4/DEFINITIONS.md 「足の模型の仕様」 (R-T, R-C, R-A, R-M,
R-P, R-X, R-W, R-H, R-E, R-S, R-O, R-V), running ON the core.

The bar model runs on the core (`bot.bt.core.CoreEngine`): the core drives
time, delivers the bars to the strategy (a bar is received at its close, so a
decision at bar i can only use bars 0..i), carries the strategy's orders to
the venue, prices every fill through the run's cost model and hands every fill
to the account. What this module adds is the bar venue's RULES, plugged into
the core's sockets:

  BarVenue     the fill-model socket AND the account socket (one object: the
               venue keeps the net position its rules need). It answers the
               strategy's signal orders, applies the protective exits
               (fixed % stop / take-profit, maker take-profit, structural
               wick stop, time exit) and the carry, and books every fill.
  BarCost      the cost-model socket: fee = size * price * pct / 100 with the
               taker or maker pct of the fill's liquidity.
  SignalStrategy  the strategy socket: at each bar's close it asks a decision
               function for BUY / SELL / CLOSE / nothing and sends it to the
               venue as a signal order.

The order flow (all zero latency; the core's ordering.py decides the order at
one instant: venue market data, then arriving requests, then deliveries,
then notices, then timers):

  * bar i reaches the venue at its close. The venue closes the books of bar
    i-1 (its equity), accrues the carry (R-S1), and decides the ONE thing bar
    i does to the position, in the time order inside the bar (R-O1: a bar's
    open comes before the rest of its range):
      AT THE OPEN -- the structural wick stop (R-W3), then the time exit
        (R-H1; both decided by information older than bar i; they drop the
        pending signal or limit, R-W3 / R-H2), else the pending taker signal
        (R-T1);
      THEN, only if the position lives on through the open (no signal, or a
        signal the same way as the position), bar i's RANGE -- the fixed stop
        (R-P3), the take-profit (R-P4), the maker take-profit (R-X1), then a
        pending maker limit (R-M1). Never on the entry bar (R-P2 / R-X2).
    The fill is a FORCED order the account socket returns (the venue acting
    on its own; core FORCED_ID_PREFIX), so every fill is a core fill with its
    fee from the cost model.
  * the strategy receives bar i, then the notices of bar i's fill, then its
    own timer set for the same instant: it decides in the timer, knowing its
    position after bar i. A signal order reaches the venue at bar i's close;
    the venue acknowledges it and keeps it pending (a signal order is an
    instruction: it is never filled itself; it ends as Canceled with the
    reason it ended: executed / no_action / entry_filtered / dropped_by_exit
    / timeout / replaced / kept_older).

Points of the rules stated here (each with its rule):
  * a maker entry signal whose bar's entry mask or entry sides block the entry
    places no limit and counts no missed fill (R-E4 / R-E5); a maker signal
    the same way as the pending limit keeps the old limit and its lifetime
    (R-M6 / R-M7);
  * the stop / take-profit levels are computed and compared on the written
    decimal values of the entry price and the percentage (R-X1 「水準は書かれた
    10 進の値どおりに比べる」);
  * the Sharpe ratio is annualised by the bar frequency (M-5: 365 * 86400 /
    bar seconds);
  * the carry is charged for any non-zero daily rate (R-S1: the formula, no
    sign condition);
  * "not used" is None; a rate or a bar count <= 0 is refused, never read as
    "off" (R-V2 / R-V4).

There is ONE rule set, named "spec" (`SPEC`; `RULES` lists it). `run_bars(bars,
decide, options, rules)` takes that name (a caller states the rule set it asks
for); `BarOptions` has no defaults (every option is stated by the caller).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from decimal import Decimal, localcontext
from typing import Any, Callable, Optional, Sequence

from ..core import (FORCED_ID_PREFIX, Ack, BarEvent, Canceled, ClockEvent, CoreEngine, EngineResult, Event, Fill,
                    OrderFillEvent, OrderRequest, Reject, Strategy, StrategyContext, ZeroLatency)
from .metrics import compute_metrics_values

EXECUTIONS = ("taker", "maker")
EXIT_EXECUTIONS = ("signal", "maker_tp")
ENTRY_SIDES = ("both", "long", "short")
STOP_MODES = ("fixed", "wick_invalidation")
SIGNALS = ("BUY", "SELL", "CLOSE")
# a signal order: at the next bar's open (taker) / a limit at the signal bar's close (maker; "_close" = from a
# CLOSE signal). Its side is the signal's (BUY -> buy, SELL -> sell); its size (1.0) is nominal: the venue sizes the
# fill (order_notional / price to open, the position to close).
SIGNAL_ORDER_TYPES = ("signal_market", "signal_limit", "signal_limit_close")
SECONDS_PER_YEAR = 365 * 86400  # M-5: periods per year = SECONDS_PER_YEAR / bar seconds


class BarModelError(ValueError):
    """The bar model refuses an option or an input (a ValueError, as the
    compatibility mouth's refusals are)."""


# --------------------------------------------------------------------------- the rule set
SPEC = "spec"  # the stated rules of the scene set: the one rule set of this model
RULES = (SPEC,)


def rules_of(name: Any) -> str:
    if name in RULES:
        return name
    raise BarModelError(f"rules must be one of {list(RULES)}, got {name!r}")


def periods_per_year(bar_seconds: float) -> float:
    """M-5: the Sharpe ratio is annualised by the bar frequency."""
    return SECONDS_PER_YEAR / bar_seconds


# --------------------------------------------------------------------------- options
@dataclass(frozen=True)
class BarCosts:
    taker_fee_pct: float
    maker_fee_pct: float
    slippage_pct: float
    spread_pct: float  # half applied per side around the reference price (taker only)

    def buy_price(self, ref: float) -> float:
        return ref * (1 + (self.spread_pct / 2 + self.slippage_pct) / 100)

    def sell_price(self, ref: float) -> float:
        return ref * (1 - (self.spread_pct / 2 + self.slippage_pct) / 100)


def _num(v: Any, name: str) -> float:
    if type(v) is bool or not isinstance(v, (int, float)):
        raise BarModelError(f"{name} must be a number, got {v!r}")
    f = float(v)
    if not math.isfinite(f):
        raise BarModelError(f"{name} must be finite, got {v!r}")
    return f


@dataclass(frozen=True)
class BarOptions:
    """Every option of the bar model; no defaults (the caller states each)."""
    initial_equity: float
    order_notional: float
    costs: BarCosts
    execution: str
    maker_timeout_bars: int
    allow_short: bool
    swap_daily_pct: float
    bar_seconds: float
    stop_loss_pct: Optional[float]
    take_profit_pct: Optional[float]
    max_hold_bars: Optional[int]
    exit_execution: str
    maker_tp_pct: Optional[float]
    entry_mask: Optional[tuple]
    entry_sides: str
    stop_mode: str
    stop_window_bars: Optional[int]

    def check(self, n_bars: int) -> None:
        """The option checks (R-V1 .. R-V4 and the option vocabulary)."""
        if self.execution not in EXECUTIONS:
            raise BarModelError(f"unknown execution model: {self.execution}")
        if self.max_hold_bars is not None and self.max_hold_bars < 1:
            raise BarModelError("max_hold_bars must be >= 1")
        if self.stop_mode not in STOP_MODES:
            raise BarModelError(f"unknown stop mode: {self.stop_mode}")
        if self.stop_mode == "wick_invalidation":
            if self.stop_window_bars is None or self.stop_window_bars < 1:
                raise BarModelError('stop_mode="wick_invalidation" requires stop_window_bars >= 1')
            if self.stop_loss_pct is not None:  # R-W4: the two protective stops never stack
                raise BarModelError('stop_mode="wick_invalidation" replaces stop_loss_pct; pass stop_loss_pct=None')
        elif self.stop_window_bars is not None:
            raise BarModelError('stop_window_bars requires stop_mode="wick_invalidation"')
        if self.exit_execution not in EXIT_EXECUTIONS:
            raise BarModelError(f"unknown exit execution model: {self.exit_execution}")
        if self.exit_execution == "maker_tp":
            if self.maker_tp_pct is None or self.maker_tp_pct <= 0:  # R-X3
                raise BarModelError('exit_execution="maker_tp" requires maker_tp_pct > 0')
        elif self.maker_tp_pct is not None:
            raise BarModelError('maker_tp_pct requires exit_execution="maker_tp"')
        if self.entry_sides not in ENTRY_SIDES:
            raise BarModelError(f"unknown entry_sides: {self.entry_sides}")
        if self.entry_mask is not None and len(self.entry_mask) != n_bars:
            raise BarModelError(f"entry_mask length ({len(self.entry_mask)},) != number of candles {n_bars}")
        # R-V2 / R-V4: "not used" is None; 0 or less is refused, never read as "off"
        for name in ("stop_loss_pct", "take_profit_pct", "maker_tp_pct", "max_hold_bars", "stop_window_bars"):
            v = getattr(self, name)
            if v is not None and v <= 0:
                raise BarModelError(f"{name} must be > 0 or None (None = not used; R-V2), got {v!r}")
        if self.maker_timeout_bars < 1:
            raise BarModelError(f"maker_timeout_bars must be >= 1 (R-V4), got {self.maker_timeout_bars!r}")


def options_from_mapping(m: dict) -> BarOptions:
    """A BarOptions from a plain mapping with EVERY key (no defaults): the keys
    of BarOptions; `costs` a mapping of the four cost keys."""
    names = [f.name for f in fields(BarOptions)]
    missing = [k for k in names if k not in m]
    extra = sorted(set(m) - set(names))
    if missing or extra:
        raise BarModelError(f"bar options: missing {missing}, unknown {extra} (every option is stated; no defaults)")
    c = m["costs"]
    ck = [f.name for f in fields(BarCosts)]
    if not isinstance(c, dict) or sorted(c) != sorted(ck):
        raise BarModelError(f"bar options: costs must have exactly {ck}, got {c!r}")
    costs = BarCosts(**{k: _num(c[k], f"costs.{k}") for k in ck})
    mask = m["entry_mask"]
    if mask is not None:
        mask = tuple(bool(x) for x in mask)
    vals = dict(m)
    vals.update(costs=costs, entry_mask=mask)
    return BarOptions(**vals)


# --------------------------------------------------------------------------- decimal levels
def _dec(x: float) -> Decimal:
    return Decimal(repr(float(x)))


class _Level:
    """A protective level (R-P1 / R-X1): its float value (for fill prices) and
    its comparison with a bar's price on the written decimal values."""
    __slots__ = ("value", "_d")

    def __init__(self, entry: float, pct: float, up: bool) -> None:
        with localcontext() as ctx:
            ctx.prec = 60
            d = _dec(entry) * ((Decimal(1) + _dec(pct) / 100) if up else (Decimal(1) - _dec(pct) / 100))
        self._d = d
        self.value = float(d)

    def lt(self, price: float) -> bool:  # level < price
        return self._d < _dec(price)

    def gt(self, price: float) -> bool:  # level > price
        return self._d > _dec(price)

    def le(self, price: float) -> bool:
        return not self.gt(price)

    def ge(self, price: float) -> bool:
        return not self.lt(price)


# --------------------------------------------------------------------------- the venue (+ account)
@dataclass
class _Plan:
    kind: str  # "open" | "close"
    side: str  # "buy" | "sell"
    price: float
    size: float
    liquidity: str
    reason: str  # close reason (signal / stop_loss / take_profit / maker_tp / time_exit / wick_stop); "" for open
    decision_bar: int = -1


@dataclass
class _Pending:
    coid: str
    side: str  # "BUY" | "SELL"
    decision_bar: int
    limit: Optional[float] = None  # maker only


class BarVenue:
    """The bar venue's rules: FillModel + Account sockets of the core."""

    def __init__(self, options: BarOptions) -> None:
        self.o = options
        self.costs = options.costs
        # market history the venue has seen (never ahead of the bar it handles)
        self.opens: list[float] = []
        self.highs: list[float] = []
        self.lows: list[float] = []
        self.closes: list[float] = []
        # the book
        self.cash = options.initial_equity
        self.position = 0.0
        self.entry_price = 0.0
        self.entry_bar = -1
        self.entry_cost = 0.0
        self.wick_level: Optional[float] = None
        self.fees_total = 0.0
        self.trade_pnls: list[float] = []
        self.trade_log: list[dict] = []
        self.fills: list[dict] = []
        self.equity: list[float] = []
        self.missed_fills = 0
        self.pending_taker: Optional[_Pending] = None
        self.pending_limit: Optional[_Pending] = None
        self._plan: Optional[_Plan] = None
        self._forced_plan: dict[str, _Plan] = {}
        self._n_forced = 0
        self._finished = False
        self._booking: Optional[_Plan] = None
        self.swap_per_bar = options.swap_daily_pct / 100 * (options.bar_seconds / 86400.0)  # R-S1

    # ------------------------------------------------------------ helpers
    @property
    def i(self) -> int:
        return len(self.closes) - 1

    def _entry_ok(self, decision_bar: int, side: str) -> bool:
        """R-E1 / R-E2: the entry sides and the mask of the DECISION bar; never consulted for a close (R-E3)."""
        if self.o.entry_sides == "long" and side == "SELL":
            return False
        if self.o.entry_sides == "short" and side == "BUY":
            return False
        if self.o.entry_mask is not None and not bool(self.o.entry_mask[decision_bar]):
            return False
        return True

    def _actionable(self, side: str) -> bool:
        if side == "BUY":
            return self.position <= 0
        return self.position > 0 or (self.position == 0 and self.o.allow_short)

    def _execute_plan(self, side: str, price: float, liquidity: str, decision_bar: int) -> Optional[_Plan]:
        """What executing `side` at `price` does now (R-T3 / R-T4): a BUY covers a short or opens a long; a SELL
        closes a long or opens a short when shorts are allowed; an opposite signal only closes (no re-entry)."""
        if side == "BUY":
            if self.position < 0:
                return _Plan("close", "buy", price, abs(self.position), liquidity, "signal")
            if self.position == 0 and self._entry_ok(decision_bar, side):
                return _Plan("open", "buy", price, self.o.order_notional / price, liquidity, "", decision_bar)
            return None
        if self.position > 0:
            return _Plan("close", "sell", price, abs(self.position), liquidity, "signal")
        if self.position == 0 and self.o.allow_short and self._entry_ok(decision_bar, side):
            return _Plan("open", "sell", price, self.o.order_notional / price, liquidity, "", decision_bar)
        return None

    def _equity_now(self) -> float:
        """R-A4: the equity at the close of the bar being handled."""
        i = self.i
        direction = 1.0 if self.position >= 0 else -1.0
        unrealized = (self.closes[i] - self.entry_price) * abs(self.position) * direction - self.entry_cost \
            if self.position != 0 else 0.0
        return self.cash + unrealized

    def finish(self) -> None:
        """Close the books of the last bar (its equity)."""
        if not self._finished and self.closes:
            self.equity.append(self._equity_now())
        self._finished = True

    # ------------------------------------------------------------ FillModel socket
    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence:
        if type(event) is not BarEvent:
            return ()
        if self.closes:
            self.equity.append(self._equity_now())  # the books of bar i-1 are closed
        self.opens.append(event.open)
        self.highs.append(event.high)
        self.lows.append(event.low)
        self.closes.append(event.close)
        i = self.i
        reports: list = []
        plan: Optional[_Plan] = None
        o, c = self.o, self.costs

        # 0) carry on any open position, per bar (R-S1: |size| x the previous close x the per-bar rate)
        if self.position != 0.0 and self.swap_per_bar != 0:
            carry = abs(self.position) * self.closes[i - 1 if i > 0 else 0] * self.swap_per_bar
            self.entry_cost += carry
            self.fees_total += carry

        # 1) AT THE OPEN, first: the structural wick stop (R-W2 / R-W3): a breach is bar i-1's close beyond the
        #    frozen level; the exit is bar i's open with taker costs
        if self.wick_level is not None and self.position != 0.0 and i > self.entry_bar:
            long = self.position > 0
            breached = self.closes[i - 1] < self.wick_level if long else self.closes[i - 1] > self.wick_level
            if breached:
                ref = self.opens[i]
                price = c.sell_price(ref) if long else c.buy_price(ref)
                plan = _Plan("close", "sell" if long else "buy", price, abs(self.position), "taker", "wick_stop")

        # 2) AT THE OPEN, second: the time exit (R-H1 / R-O1): the position filled at bar b is closed at the open
        #    of bar b + N, before anything of bar i's range; it drops the pending signal or limit (R-H2)
        time_due = (o.max_hold_bars is not None and self.position != 0.0 and i - self.entry_bar >= o.max_hold_bars)
        if plan is None and time_due:
            ref = self.opens[i]
            long = self.position > 0
            price = c.sell_price(ref) if long else c.buy_price(ref)
            plan = _Plan("close", "sell" if long else "buy", price, abs(self.position), "taker", "time_exit")
        mtp_pct = o.maker_tp_pct if o.exit_execution == "maker_tp" else None

        # 3) AT THE OPEN, third: the pending taker signal (R-T1) acts at bar i's open, before bar i's range. Not
        #    when an exit decided by older information took the open (above): those drop it.
        signal_done = False
        if plan is None and o.execution == "taker" and self.pending_taker is not None and i > 0:
            p = self.pending_taker
            ref = self.opens[i]
            price = c.buy_price(ref) if p.side == "BUY" else c.sell_price(ref)
            plan = self._execute_plan(p.side, price, "taker", p.decision_bar)
            reports.append(Canceled(p.coid, "executed" if plan is not None else "no_action"))
            self.pending_taker = None
            signal_done = True

        # 4) THE RANGE: the fixed stop (R-P3), the take-profit (R-P4), the maker take-profit (R-X1), the stop first
        #    (R-O1); never on the entry bar (R-P2 / R-X2), never after the open closed the position
        if plan is None and self.position != 0.0 and i > 0 and i > self.entry_bar \
                and (o.stop_loss_pct or o.take_profit_pct or mtp_pct):
            long = self.position > 0
            sl = _Level(self.entry_price, o.stop_loss_pct, not long) if o.stop_loss_pct else None
            tp = _Level(self.entry_price, o.take_profit_pct, long) if o.take_profit_pct else None
            mtp = _Level(self.entry_price, mtp_pct, long) if mtp_pct else None
            lo, hi, op = self.lows[i], self.highs[i], self.opens[i]
            sl_hit = sl is not None and (sl.ge(lo) if long else sl.le(hi))  # R-P3: the range reaches the level
            tp_hit = tp is not None and (tp.lt(hi) if long else tp.gt(lo))  # R-P4: strictly through
            mtp_hit = mtp is not None and (mtp.lt(hi) if long else mtp.gt(lo))  # R-X1: strictly through
            if sl_hit:
                # R-P3: the reference price is min(open, level) for a long, max(open, level) for a short
                if long:
                    price = c.sell_price(sl.value if sl.lt(op) else op)
                else:
                    price = c.buy_price(sl.value if sl.gt(op) else op)
                plan = _Plan("close", "sell" if long else "buy", price, abs(self.position), "taker", "stop_loss")
            elif tp_hit:
                plan = _Plan("close", "sell" if long else "buy", tp.value, abs(self.position), "maker", "take_profit")
            elif mtp_hit:
                plan = _Plan("close", "sell" if long else "buy", mtp.value, abs(self.position), "maker", "maker_tp")

        if signal_done:
            pass  # the taker signal was consumed at the open (executed or no_action); a range exit may follow
        elif plan is not None:
            # an exit drops whatever signal was pending for this bar (R-W3 / R-H2 / R-M5: not a missed fill)
            for p in (self.pending_taker, self.pending_limit):
                if p is not None:
                    reports.append(Canceled(p.coid, "dropped_by_exit"))
            self.pending_taker = self.pending_limit = None
        elif o.execution == "maker":
            # 5) THE RANGE, last: a pending maker limit (R-M1: strictly through, never on the bar it was placed;
            #    R-M2: its lifetime)
            p = self.pending_limit
            if p is not None and i > p.decision_bar:
                through = (self.lows[i] < p.limit) if p.side == "BUY" else (self.highs[i] > p.limit)
                if through and self._actionable(p.side):
                    plan = self._execute_plan(p.side, p.limit, "maker", p.decision_bar)
                    reports.append(Canceled(p.coid, "executed" if plan is not None else "entry_filtered"))
                    self.pending_limit = None
                elif i - p.decision_bar >= o.maker_timeout_bars:
                    self.missed_fills += 1
                    self.trade_log.append({"bar": i, "side": f"CANCEL_{p.side}", "price": p.limit, "size": 0.0})
                    reports.append(Canceled(p.coid, "timeout"))
                    self.pending_limit = None
        self._plan = plan
        return tuple(reports)

    def on_order(self, order: OrderRequest, venue_time_ns: int) -> Sequence:
        coid = order.client_order_id
        if coid.startswith(FORCED_ID_PREFIX):
            plan = self._forced_plan.pop(coid, None)
            if plan is None:
                return (Reject(coid, "unknown_forced_order"),)
            return (Ack(coid, f"bar-{coid}"), Fill(coid, plan.price, plan.size, plan.liquidity))
        if order.order_type not in SIGNAL_ORDER_TYPES:
            return (Reject(coid, f"the bar venue takes signal orders only (order_type one of {SIGNAL_ORDER_TYPES})"),)
        sig = "BUY" if order.side == "buy" else "SELL"
        i = self.i
        if order.order_type == "signal_market":
            if self.o.execution != "taker":
                return (Reject(coid, "execution is maker: send signal_limit"),)
            out = []
            if self.pending_taker is not None:  # cannot happen with one decision per bar; kept explicit
                out.append(Canceled(self.pending_taker.coid, "replaced"))
            self.pending_taker = _Pending(coid, sig, i)
            return (Ack(coid, f"bar-{coid}"), *out)
        if self.o.execution != "maker":
            return (Reject(coid, "execution is taker: send signal_market"),)
        if not (self._actionable(sig) or order.order_type == "signal_limit_close"):
            return (Reject(coid, "not_actionable"),)
        out = [Ack(coid, f"bar-{coid}")]
        old = self.pending_limit
        if order.order_type == "signal_limit" and self.position == 0.0 and not self._entry_ok(i, sig):
            # R-E4 / R-E5: an entry signal its bar's mask or the entry sides stop places no limit, replaces no
            # pending limit and counts no missed fill
            return (*out, Canceled(coid, "entry_filtered"))
        if old is not None and old.side == sig:
            # R-M7: the pending limit the same way stays (its price and its lifetime); no new limit
            return (*out, Canceled(coid, "kept_older"))
        if old is not None:  # R-M3: a limit the opposite way replaces the old one, which counts as missed
            self.missed_fills += 1
            out.append(Canceled(old.coid, "replaced"))
        self.pending_limit = _Pending(coid, sig, i, self.closes[i])
        return tuple(out)

    def on_cancel(self, request, venue_time_ns: int) -> Sequence:
        coid = request.client_order_id
        for name in ("pending_taker", "pending_limit"):
            p = getattr(self, name)
            if p is not None and p.coid == coid:
                setattr(self, name, None)
        return (Canceled(coid, "canceled"),)

    # ------------------------------------------------------------ Account socket
    def on_market_event_account(self, event: Event, venue_time_ns: int) -> Sequence:
        plan, self._plan = self._plan, None
        if plan is None:
            return ()
        self._n_forced += 1
        coid = f"{FORCED_ID_PREFIX}bar{self.i}-{self._n_forced}"
        self._forced_plan[coid] = plan
        self._booking = plan
        return (OrderRequest(side=plan.side, order_type="market" if plan.liquidity == "taker" else "limit",
                             size=plan.size, price=None if plan.liquidity == "taker" else plan.price,
                             client_order_id=coid, reduce_only=plan.kind == "close"),)

    def apply_fill(self, fill) -> None:
        plan = self._booking
        self._booking = None
        i = self.i
        fee = fill.fee
        price = fill.price
        self.fees_total += fee
        if plan.kind == "open":
            size = fill.size  # R-A1: order_notional / the fill price
            self.position = size if plan.side == "buy" else -size
            self.entry_price = price
            self.entry_bar = i
            self.entry_cost = fee
            if self.o.stop_mode == "wick_invalidation":
                # R-W1: the extreme of the N COMPLETED bars before the fill bar (the fill bar itself excluded)
                lo = max(0, i - self.o.stop_window_bars)
                self.wick_level = (min(self.lows[lo:i]) if self.position > 0 else max(self.highs[lo:i])) \
                    if lo < i else None
            side = f"OPEN_{'LONG' if self.position > 0 else 'SHORT'}"
            self.trade_log.append({"bar": i, "side": side, "price": price, "size": size})
            self.fills.append({"bar": i, "side": side, "price": price, "size": size, "fee": fee, "reason": "open",
                               "t_ns": fill.venue_time_ns})
        else:
            size = abs(self.position)
            direction = 1.0 if self.position > 0 else -1.0
            pnl = (price - self.entry_price) * size * direction - fee - self.entry_cost  # R-A3
            self.cash += pnl
            self.trade_pnls.append(pnl)
            side = f"CLOSE_{'LONG' if self.position > 0 else 'SHORT'}"
            self.trade_log.append({"bar": i, "side": side, "price": price, "size": size, "pnl": pnl,
                                   "reason": plan.reason})
            self.fills.append({"bar": i, "side": side, "price": price, "size": size, "fee": fee,
                               "reason": plan.reason, "t_ns": fill.venue_time_ns})
            self.position, self.entry_price, self.entry_cost = 0.0, 0.0, 0.0
            self.entry_bar = -1
            self.wick_level = None

    def apply_funding(self, event) -> None:
        return None

    def apply_liquidation(self, event) -> None:
        return None

    def check_order(self, order, venue_time_ns: int) -> Optional[str]:
        return None


class _AccountPort:
    """The account socket of a BarVenue (the core calls the account's
    on_market_event after the fill model's)."""

    def __init__(self, venue: BarVenue) -> None:
        self._v = venue

    def apply_fill(self, fill) -> None:
        self._v.apply_fill(fill)

    def apply_funding(self, event) -> None:
        return None

    def apply_liquidation(self, event) -> None:
        return None

    def on_market_event(self, event, venue_time_ns: int) -> Sequence:
        return self._v.on_market_event_account(event, venue_time_ns)

    def check_order(self, order, venue_time_ns: int) -> Optional[str]:
        return None


class BarCost:
    """Cost-model socket (R-A2): fee = size * price * pct / 100 (taker or maker
    pct by the fill's liquidity)."""

    def __init__(self, costs: BarCosts) -> None:
        self.c = costs

    def cost(self, fill) -> float:
        pct = self.c.taker_fee_pct if fill.liquidity == "taker" else self.c.maker_fee_pct
        return fill.size * fill.price * pct / 100


# --------------------------------------------------------------------------- the strategy socket
class SignalStrategy(Strategy):
    """At each bar's close (k bars delivered) with k - 1 >= start, asks
    `decide(k)` for "BUY" / "SELL" / "CLOSE" / None and sends it to the venue.
    It decides in a timer set for the bar's own instant, so it knows its
    position after the bar's fill (the notices come before the timer)."""

    def __init__(self, decide: Callable[[int], Optional[str]], *, start: int, execution: str) -> None:
        self._decide = decide
        self._start = start
        self._execution = execution
        self.bars_seen = 0
        self.position = 0.0
        self._n = 0
        self._last_close: Optional[float] = None

    def on_event(self, event: Event, ctx: StrategyContext) -> None:
        if type(event) is BarEvent:
            self.bars_seen += 1
            self._last_close = event.close
            if self.bars_seen - 1 >= self._start:
                ctx.set_timer(ctx.now_ns, "decide")
            return
        if type(event) is OrderFillEvent:
            self.position += event.size if event.side == "buy" else -event.size
            return
        if type(event) is ClockEvent and event.tag == "decide":
            sig = self._decide(self.bars_seen)
            if sig is None:
                return
            if sig not in SIGNALS:
                raise BarModelError(f"a decision must be one of {SIGNALS} or None, got {sig!r}")
            is_close = sig == "CLOSE"
            if is_close:
                sig = "SELL" if self.position > 0 else "BUY" if self.position < 0 else None
                if sig is None:
                    return
            self._n += 1
            if self._execution == "taker":
                ctx.place_order(OrderRequest(side=sig.lower(), order_type="signal_market", size=1.0,
                                             client_order_id=f"sig{self._n}"))
            else:
                ctx.place_order(OrderRequest(side=sig.lower(),
                                             order_type="signal_limit_close" if is_close else "signal_limit",
                                             size=1.0, price=self._last_close, client_order_id=f"sig{self._n}"))


# --------------------------------------------------------------------------- running
@dataclass
class BarRunResult:
    rules: str
    fills: list  # [{bar, side, price, size, fee, reason, t_ns}]
    trade_log: list
    trade_pnls: list
    equity: list
    missed_fills: int
    fees_total: float
    metrics: dict
    core: EngineResult = field(repr=False)


BAR_SPACING_NS = 60_000_000_000


def bar_events(rows: Sequence[dict], start_ns: Sequence[int], bar_ns: int) -> list[BarEvent]:
    """BarEvents from rows {open, high, low, close[, volume]}: bar i covers
    [start_ns[i], start_ns[i] + bar_ns) and is received at its end."""
    out = []
    for k, (r, s) in enumerate(zip(rows, start_ns)):
        try:
            out.append(BarEvent(received_time_ns=s + bar_ns, start_time_ns=s, open=r["open"], high=r["high"],
                                low=r["low"], close=r["close"], volume=r.get("volume", 0.0)))
        except Exception as exc:  # the core's own refusal of a row (NaN, high < max(open, close), ...)
            raise BarModelError(f"bar {k} cannot be a bar event: {exc}") from None
    for k in range(1, len(out)):
        if out[k].start_time_ns < out[k - 1].received_time_ns:
            raise BarModelError(f"bar {k} starts before bar {k - 1} ends (bars must not overlap)")
    return out


def run_bars(events: Sequence[BarEvent], decide: Callable[[int], Optional[str]], options: BarOptions,
             rules: Any, *, start: int = 0) -> BarRunResult:
    """One run of the bar model over `events` (from bar_events) under the rule
    set `rules` (the one rule set, "spec")."""
    r = rules_of(rules)
    if not isinstance(options, BarOptions):
        raise BarModelError("options must be a BarOptions (options_from_mapping builds one from a mapping)")
    n = len(events)
    options.check(n)
    venue = BarVenue(options)
    strat = SignalStrategy(decide, start=start, execution=options.execution)
    if n == 0:
        core = EngineResult(events_processed=0, source_events=0)
    else:
        span = (events[0].exchange_time_ns, events[-1].received_time_ns)
        core = CoreEngine(strat, {"bars": list(events)}, venue, ZeroLatency(), BarCost(options.costs),
                          _AccountPort(venue), time_span_ns=span).run()
    venue.finish()
    metrics = compute_metrics_values(venue.trade_pnls, venue.equity, venue.fees_total,
                                     periods_per_year(options.bar_seconds))
    return BarRunResult(r, venue.fills, venue.trade_log, venue.trade_pnls, venue.equity, venue.missed_fills,
                        venue.fees_total, metrics, core)
