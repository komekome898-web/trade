"""`MarginAccount`: the core's account socket for item 2 (old item 6).

The account is kept in its `currency` (JPY for this project: "円建て"); a
product quoted in another currency is converted with the dated FX table at
the time of each amount (a realised P&L at the fill's time, a fee at the
fill's time, a funding / swap payment at its time).

* Position and average price: average-cost accounting. A fill that reduces
  the position realises (price - average) * closed size * direction; a fill
  that flips it realises the whole old position and opens the rest at the
  fill price.
* Realised P&L (`realized`, quote currency; `realized_account`, account
  currency) is price P&L only. Fees, funding and swap are kept apart
  (`fees`, `funding_paid`, `swap_paid`, all "paid", a receipt negative), and
  per order (`fees_by_order` = the cost of each leg).
* Mark: `mark="last_trade"` (the last trade at the venue -- a print of the
  data, one of our own fills, or the last bar's close, whichever came last)
  or `"mid"` (the displayed book's mid). Unrealised P&L = (mark - average) *
  position.
* Margin (margin products): the worst position the account could reach if
  every order that can still fill did fill is
  max(|position + all buys|, |position - all sells|) ("all" = the orders live
  at the venue, from `open_orders`, plus the new one). An order that raises
  it is refused when worst * price / leverage > equity (price: the new
  order's limit price, its stop trigger, or for a market order the best
  opposite quote, else the last print -- the other orders are valued at the
  same price). Equity = cash + realised - fees - funding - swap +
  unrealised. `open_orders` is a required argument: the venue's
  `SimVenue.open_orders` (the account socket is not told of cancels, so it
  asks the venue what still stands), or None for a run that states the
  margin check counts the position and the new order only.
* Cash products (`product.margin` False): no short position (a sell above
  the position less the other live sells is refused), a buy needs its
  notional plus the other live buys' notional in cash, leverage 1.
* Liquidation (`liquidation=LiquidationRule(...)`, or None for a run
  without it -- the argument is required): at each market event, when
  equity / (|position| * mark / leverage) < maint_ratio, the account returns a
  forced order of type "liquidation" at the mark for the whole position (the
  venue fills it at that price) and records `liquidated_t`.
* Exposure clock: the time with a non-zero position, summed, from fill times;
  `finish(end_ns)` closes it at the run's end.
* Funding (FUNDING events) and swap (`Rollover` items) are charged by the
  cost schedule's `funding` / `swap` components, which must be declared when
  the run meets them. Corporate actions adjust position and average price.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from bot.bt.core import (
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    Event,
    FillNotice,
    FundingEvent,
    OrderRequest,
    TradeEvent,
)
from bot.bt.costs.fx import FxRateMissingError, FxRates
from bot.bt.costs.schedule import CostSchedule
from bot.bt.fill.book import ExternalBook
from bot.bt.orders.client import AMEND, AMENDS_KEY, LIQUIDATION
from bot.bt.orders.errors import ExecutionModelError
from bot.bt.orders.product import Product

from .reference import CorporateAction, ReferenceSchedule, Rollover

MARK_RULES = ("last_trade", "mid")
_EPS = 1e-12


@dataclass(frozen=True)
class LiquidationRule:
    maint_ratio: float
    source: str
    price: str = "mark"  # the one price the model knows: the account's mark

    def __post_init__(self) -> None:
        if isinstance(self.maint_ratio, bool) or not isinstance(self.maint_ratio, (int, float)) \
                or not math.isfinite(self.maint_ratio) or self.maint_ratio <= 0:
            raise ExecutionModelError(f"maint_ratio must be finite > 0, got {self.maint_ratio!r}")
        object.__setattr__(self, "maint_ratio", float(self.maint_ratio))
        if type(self.source) is not str or not self.source.strip():
            raise ExecutionModelError("a liquidation rule needs its source (where the rule comes from)")
        if self.price != "mark":
            raise ExecutionModelError(f"liquidation price {self.price!r}: the model knows 'mark'")


@dataclass(frozen=True)
class AccountSnapshot:
    currency: str
    position: float
    avg_px: Optional[float]
    realized: float
    realized_account: float
    unrealized: Optional[float]
    unrealized_account: Optional[float]
    fees: float
    funding_paid: float
    swap_paid: float
    exposure_ns: int
    liquidated_t: Optional[int]
    equity: Optional[float]
    fees_by_order: dict = field(default_factory=dict)


class MarginAccount:
    def __init__(self, *, product: Product, currency: str, cash: float, leverage: float,
                 liquidation: Optional[LiquidationRule], mark: str, costs: CostSchedule, fx: Optional[FxRates],
                 reference: Optional[ReferenceSchedule],
                 open_orders: Optional[Callable[[], Sequence[tuple[str, float]]]]) -> None:
        if type(product) is not Product:
            raise ExecutionModelError("MarginAccount needs a Product")
        if type(currency) is not str or len(currency) != 3 or not currency.isupper():
            raise ExecutionModelError(f"currency must be a 3-letter code, got {currency!r}")
        for name, v in (("cash", cash), ("leverage", leverage)):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ExecutionModelError(f"{name} must be finite > 0, got {v!r}")
        if not product.margin and float(leverage) != 1.0:
            raise ExecutionModelError("a cash product (margin False) has leverage 1")
        if liquidation is not None and type(liquidation) is not LiquidationRule:
            raise ExecutionModelError("liquidation must be a LiquidationRule or None")
        if mark not in MARK_RULES:
            raise ExecutionModelError(f"mark {mark!r}: one of {MARK_RULES}")
        if type(costs) is not CostSchedule:
            raise ExecutionModelError("MarginAccount needs the run's CostSchedule")
        if fx is not None and type(fx) is not FxRates:
            raise ExecutionModelError("fx must be an FxRates or None")
        if reference is not None and type(reference) is not ReferenceSchedule:
            raise ExecutionModelError("reference must be a ReferenceSchedule or None")
        if open_orders is not None and not callable(open_orders):
            raise ExecutionModelError("open_orders must be a callable (e.g. SimVenue.open_orders) or None")
        self.open_orders = open_orders
        self.product, self.currency = product, currency
        self.cash, self.leverage = float(cash), float(leverage)
        self.liquidation, self.mark_rule, self.costs, self.fx, self.reference = liquidation, mark, costs, fx, reference
        self.position = 0.0
        self.avg_px: Optional[float] = None
        self.realized = 0.0
        self.realized_account = 0.0
        self.fees = 0.0
        self.funding_paid = 0.0
        self.swap_paid = 0.0
        self.cash_flow = 0.0  # cash products: notional paid (+) / received (-), account currency
        self.exposure_ns = 0
        self.liquidated_t: Optional[int] = None
        self.fees_by_order: dict[str, float] = {}
        self._clock: Optional[int] = None
        self._book = ExternalBook()
        self._last_price: Optional[float] = None
        self._forced_pending = False
        self._order_sizes: dict[str, float] = {}
        self.liquidation_prints = 0
        # how often each met cost component was charged
        self.used: dict[str, int] = {"funding": 0, "swap": 0}

    # ---------------------------------------------------------------- time
    def _to(self, t: int) -> None:
        """Bring the account to time t: reference items <= t, then the clock."""
        if self.reference is not None:
            for item in self.reference.due(t):
                self._tick(item.time_ns)
                if type(item) is Rollover:
                    rule = self.costs.need("swap")
                    self.used["swap"] += 1
                    self.swap_paid += self._acct(rule.paid(self.position), item.time_ns)
                elif type(item) is CorporateAction:
                    self._corporate(item.ratio)
        self._tick(t)

    def _tick(self, t: int) -> None:
        if self._clock is not None and t > self._clock and self.position != 0:
            self.exposure_ns += t - self._clock
        if self._clock is None or t > self._clock:
            self._clock = t

    def _corporate(self, ratio: float) -> None:
        self.position *= ratio
        if self.avg_px is not None:
            self.avg_px /= ratio
        if self._last_price is not None:
            self._last_price /= ratio
        for side in (self._book.bids, self._book.asks):
            for lvl in side:
                lvl[0] /= ratio
                lvl[1] *= ratio

    def _acct(self, amount: float, t: int) -> float:
        if self.product.quote_ccy == self.currency:
            return amount
        if self.fx is None:
            raise FxRateMissingError(f"the product is quoted in {self.product.quote_ccy} and the account is in "
                                     f"{self.currency}; no FX rates were given")
        return self.fx.convert(amount, self.product.quote_ccy, self.currency, t)

    # -------------------------------------------------------------- sockets
    def apply_fill(self, fill: FillNotice) -> None:
        t = int(fill.venue_time_ns)
        self._to(t)
        s = 1 if fill.side == "buy" else -1
        q, px = float(fill.size), float(fill.price)
        fee = float(fill.fee)
        self._last_price = px  # our fill is a trade at the venue too
        self.fees += fee
        self.fees_by_order[fill.client_order_id] = self.fees_by_order.get(fill.client_order_id, 0.0) + fee
        if not self.product.margin:
            self.cash_flow += self._acct(s * q * px, t)
        pos = self.position
        if pos == 0 or (pos > 0) == (s > 0):
            new = pos + s * q
            self.avg_px = ((self.avg_px or 0.0) * abs(pos) + px * q) / abs(new)
            self.position = new
        else:
            closed = min(q, abs(pos))
            pnl = (px - self.avg_px) * closed * (1 if pos > 0 else -1)  # type: ignore[operator]
            self.realized += pnl
            self.realized_account += self._acct(pnl, t)
            rest = q - closed
            if rest > _EPS * max(1.0, q):
                self.position, self.avg_px = s * rest, px
            else:
                self.position = pos + s * closed
                if abs(self.position) <= _EPS * max(1.0, abs(pos)):
                    self.position, self.avg_px = 0.0, None
        if self.position == 0:
            self._forced_pending = False

    def apply_funding(self, event: Event) -> None:
        t = int(event.exchange_time_ns)
        self._to(t)
        rule = self.costs.need("funding")
        self.used["funding"] += 1
        if type(event) is not FundingEvent:
            raise ExecutionModelError(f"apply_funding got a {type(event).__name__}")
        if rule.price == "event_mark":
            if event.mark_price is None:
                raise ExecutionModelError("funding rule 'event_mark' and the funding event has no mark_price")
            price = float(event.mark_price)
        self.funding_paid += self._acct(self.position * price * float(event.rate), t)

    def apply_liquidation(self, event: Event) -> None:
        self._to(int(event.exchange_time_ns))
        self.liquidation_prints += 1  # someone else's liquidation print: nothing to book

    def on_market_event(self, event: Event, venue_time_ns: int) -> Sequence[OrderRequest]:
        t = int(venue_time_ns)
        self._to(t)
        et = type(event)
        if et is TradeEvent:
            self._last_price = float(event.price)
        elif et is BarEvent:
            self._last_price = float(event.close)
        elif et is BookSnapshotEvent:
            self._book.apply_snapshot(event, t)
        elif et is BookDeltaEvent:
            self._book.apply_delta(event, t)
        return self._maybe_liquidate(t)

    def check_order(self, order: OrderRequest, venue_time_ns: int) -> Optional[str]:
        t = int(venue_time_ns)
        self._to(t)
        size = float(order.size)
        if order.order_type == AMEND:
            target = order.extra_dict().get(AMENDS_KEY)
            before = self._order_sizes.get(target) if type(target) is str else None
            if before is None:
                return None  # the venue answers an amend of an unknown order
            self._order_sizes[target] = max(before, size)
            size = size - before
            if size <= _EPS:
                return None
        else:
            self._order_sizes[order.client_order_id] = size
        if order.order_type == LIQUIDATION:
            return None
        s = 1 if order.side == "buy" else -1
        buys = sells = 0.0
        if self.open_orders is not None:
            for side, remaining in self.open_orders():
                if side == "buy":
                    buys += float(remaining)
                else:
                    sells += float(remaining)
        pos = self.position
        without = max(abs(pos + buys), abs(pos - sells))
        with_new = max(abs(pos + buys + (size if s > 0 else 0.0)), abs(pos - sells - (size if s < 0 else 0.0)))
        if not self.product.margin and s < 0 and sells + size > pos * (1 + 1e-12) + _EPS:
            return "no_short_in_cash_account"
        if with_new <= without * (1 + 1e-12):
            return None  # it cannot make the worst position larger
        price = self._order_price(order, s)
        if price is None:
            return "no_price_for_margin_check"
        if not self.product.margin:
            need = self._acct((buys + size) * price, t) if s > 0 else 0.0
            if need > self.cash - self.cash_flow - self.fees - self.funding_paid - self.swap_paid + _EPS:
                return "insufficient_cash"
            return None
        equity = self.equity()
        if equity is None:
            return "no_mark_for_equity"  # the position cannot be valued, so its margin cannot be checked
        required = self._acct(with_new * price, t) / self.leverage
        if required > equity + _EPS:
            return "insufficient_margin"
        return None

    # ------------------------------------------------------------- helpers
    def _order_price(self, order: OrderRequest, s: int) -> Optional[float]:
        if order.order_type in ("limit", "stop_limit", AMEND) and order.price is not None:
            return float(order.price)
        if order.order_type == "stop" and order.trigger_price is not None:
            return float(order.trigger_price)
        quote = self._book.best("ask" if s > 0 else "bid")
        return quote if quote is not None else self._last_price

    def mark(self) -> Optional[float]:
        if self.mark_rule == "mid":
            return self._book.mid()
        return self._last_price

    def unrealized(self) -> Optional[float]:
        if self.position == 0:
            return 0.0
        m = self.mark()
        if m is None:
            return None
        return (m - self.avg_px) * self.position  # type: ignore[operator]

    def equity(self) -> Optional[float]:
        u = self.unrealized()
        if u is None:
            return None
        t = self._clock if self._clock is not None else 0
        return self.cash + self.realized_account - self.fees - self.funding_paid - self.swap_paid + self._acct(u, t)

    def _maybe_liquidate(self, t: int) -> list:
        rule = self.liquidation
        if rule is None or self.position == 0 or self._forced_pending or not self.product.margin:
            return []
        m = self.mark()
        eq = self.equity()
        if m is None or eq is None:
            return []
        need = self._acct(abs(self.position) * m, t) / self.leverage
        if need <= 0 or eq / need >= rule.maint_ratio:
            return []
        self._forced_pending = True
        self.liquidated_t = t
        side = "sell" if self.position > 0 else "buy"
        return [OrderRequest(side=side, order_type=LIQUIDATION, size=abs(self.position), price=m,
                             reduce_only=True)]

    # --------------------------------------------------------------- results
    def finish(self, end_ns: int) -> AccountSnapshot:
        """Apply what is due up to the run's end and close the exposure clock."""
        if type(end_ns) is not int:
            raise ExecutionModelError(f"end_ns must be an int of ns, got {end_ns!r}")
        self._to(end_ns)
        return self.snapshot()

    def snapshot(self) -> AccountSnapshot:
        u = self.unrealized()
        t = self._clock if self._clock is not None else 0
        return AccountSnapshot(
            currency=self.currency, position=self.position, avg_px=self.avg_px, realized=self.realized,
            realized_account=self.realized_account, unrealized=u,
            unrealized_account=None if u is None else self._acct(u, t), fees=self.fees,
            funding_paid=self.funding_paid, swap_paid=self.swap_paid, exposure_ns=self.exposure_ns,
            liquidated_t=self.liquidated_t, equity=self.equity(), fees_by_order=dict(self.fees_by_order))
