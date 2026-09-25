"""Costs of a run, declared in full, with no default value anywhere.

`CostSchedule` is the declaration. Two kinds of component:

* **Always met** -- every fill is a maker or a taker fill, so `maker_rate`
  and `taker_rate` (and the `source` of the numbers) are required keyword
  arguments with no default: a schedule cannot be built without them (a
  missing one is a `TypeError` from Python itself, an empty source a
  `CostNotDeclaredError`). This is the structural guard against the
  "disabled by default" failure (tool catalogue section 2.4, form 2).
* **Met when the run meets them** -- `spread` (a market order with no book to
  price it), `funding` (a FUNDING event while the account runs), `swap` (an FX
  rollover), `fee_table` (a per-order fee on top of the rates). Each is
  `NOT_DECLARED` unless given. When the run meets one that is not declared,
  the model that needs it raises `CostNotDeclaredError`; nothing is charged
  as zero in its place. A run that should charge nothing states 0 (a rate of
  0.0, a spread of 0.0).

`ScheduleCostModel` is the core's cost socket built from a schedule: the fee
of one fill, in the account currency (negative = rebate).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

from bot.bt.core import FillNotice
from bot.bt.orders.errors import ExecutionModelError
from bot.bt.orders.product import Product

from .fx import FxRates, FxRateMissingError


class CostNotDeclaredError(ExecutionModelError):
    """A cost component the run meets was not declared."""


class _NotDeclared:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NOT_DECLARED"

    def __bool__(self) -> bool:
        return False


NOT_DECLARED: Any = _NotDeclared()


def _rate(name: str, v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) >= 1:
        raise CostNotDeclaredError(f"{name} must be a finite fraction of the notional (|rate| < 1), got {v!r}")
    return float(v)


@dataclass(frozen=True)
class FeeTable:
    """A tiered fee per ORDER by its executed notional (a broker's table of
    "約定代金"): `tiers` = ((upper, fee), ..., (None, fee)), upper bounds
    included and increasing, the last tier open. Charged incrementally: a fill
    pays table(order's notional after it) - table(before it), so an order
    filled in several parts pays exactly the table's fee for its total."""

    tiers: tuple[tuple[Optional[float], float], ...]

    def __post_init__(self) -> None:
        rows = tuple((None if u is None else float(u), float(f)) for u, f in self.tiers)
        if not rows or rows[-1][0] is not None:
            raise CostNotDeclaredError("a fee table ends with an open tier (upper = None)")
        uppers = [u for u, _ in rows[:-1]]
        if any(u is None or not math.isfinite(u) or u <= 0 for u in uppers) or uppers != sorted(set(uppers)):
            raise CostNotDeclaredError(f"fee table upper bounds must be finite, > 0 and increasing: {self.tiers!r}")
        if any(not math.isfinite(f) or f < 0 for _, f in rows):
            raise CostNotDeclaredError(f"fee table fees must be finite and >= 0: {self.tiers!r}")
        object.__setattr__(self, "tiers", rows)

    def fee(self, notional: float) -> float:
        if notional <= 0:
            return 0.0
        for upper, fee in self.tiers:
            if upper is None or notional <= upper:
                return fee
        raise AssertionError("unreachable")  # pragma: no cover


@dataclass(frozen=True)
class SwapRule:
    """FX swap per unit of position per rollover, in the quote currency.
    Credits: positive = the holder receives. Paid = -credit * |position|."""

    long_credit_per_unit_per_day: float
    short_credit_per_unit_per_day: float

    def __post_init__(self) -> None:
        for n in ("long_credit_per_unit_per_day", "short_credit_per_unit_per_day"):
            v = getattr(self, n)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise CostNotDeclaredError(f"{n} must be a finite number, got {v!r}")
            object.__setattr__(self, n, float(v))

    def paid(self, position: float) -> float:
        if position > 0:
            return -self.long_credit_per_unit_per_day * position
        if position < 0:
            return -self.short_credit_per_unit_per_day * (-position)
        return 0.0


FUNDING_PRICES = ("event_mark",)


@dataclass(frozen=True)
class FundingRule:
    """How a FUNDING event is charged: position * price * rate is paid by the
    long side when the rate is positive. `price`: "event_mark" = the event's
    own mark price (a funding event without one is refused)."""

    price: str

    def __post_init__(self) -> None:
        if self.price not in FUNDING_PRICES:
            raise CostNotDeclaredError(f"funding price {self.price!r}: one of {FUNDING_PRICES}")


class CostSchedule:
    def __init__(self, *, maker_rate: float, taker_rate: float, source: str, spread: Any = NOT_DECLARED,
                 funding: Any = NOT_DECLARED, swap: Any = NOT_DECLARED, fee_table: Any = NOT_DECLARED) -> None:
        self.maker_rate = _rate("maker_rate", maker_rate)
        self.taker_rate = _rate("taker_rate", taker_rate)
        if type(source) is not str or not source.strip():
            raise CostNotDeclaredError(f"costs need a non-empty source (where the numbers come from), got {source!r}")
        self.source = source
        if spread is not NOT_DECLARED:
            if isinstance(spread, bool) or not isinstance(spread, (int, float)) or not math.isfinite(spread) \
                    or spread < 0:
                raise CostNotDeclaredError(f"spread must be a finite price distance >= 0, got {spread!r}")
            spread = float(spread)
        if funding is not NOT_DECLARED and type(funding) is not FundingRule:
            raise CostNotDeclaredError(f"funding must be a FundingRule, got {type(funding).__name__}")
        if swap is not NOT_DECLARED and type(swap) is not SwapRule:
            raise CostNotDeclaredError(f"swap must be a SwapRule, got {type(swap).__name__}")
        if fee_table is not NOT_DECLARED and type(fee_table) is not FeeTable:
            raise CostNotDeclaredError(f"fee_table must be a FeeTable, got {type(fee_table).__name__}")
        self.spread = spread
        self.funding = funding
        self.swap = swap
        self.fee_table = fee_table

    def need(self, name: str) -> Any:
        """A met component; CostNotDeclaredError if the run did not declare it."""
        if name not in ("spread", "funding", "swap", "fee_table"):
            raise KeyError(name)
        v = getattr(self, name)
        if v is NOT_DECLARED:
            raise CostNotDeclaredError(
                f"the run meets the cost component {name!r} and did not declare it "
                f"(declare it, as 0 if it costs nothing; no default is used)"
            )
        return v

    def declared(self) -> dict[str, Any]:
        """Every component with its value (NOT_DECLARED shown as None), for a
        run record."""
        return {"maker_rate": self.maker_rate, "taker_rate": self.taker_rate, "source": self.source,
                **{k: (None if getattr(self, k) is NOT_DECLARED else getattr(self, k))
                   for k in ("spread", "funding", "swap", "fee_table")}}


class ScheduleCostModel:
    """The core cost socket from a schedule: fee of one fill in the account
    currency = (rate of its liquidity * price * size + the fee table's
    increment for its order) converted from the quote currency at the fill's
    venue time."""

    def __init__(self, schedule: CostSchedule, *, product: Product, account_currency: str,
                 fx: Optional[FxRates]) -> None:
        if type(schedule) is not CostSchedule:
            raise CostNotDeclaredError("ScheduleCostModel needs a CostSchedule")
        self.schedule = schedule
        self.product = product
        self.account_currency = account_currency
        self.fx = fx
        self._notional: dict[str, float] = {}
        self.fees_by_order: dict[str, float] = {}

    def cost(self, fill: FillNotice) -> float:
        s = self.schedule
        rate = s.maker_rate if fill.liquidity == "maker" else s.taker_rate
        notional = fill.price * fill.size
        fee_q = rate * notional
        if s.fee_table is not NOT_DECLARED:
            before = self._notional.get(fill.client_order_id, 0.0)
            after = before + notional
            self._notional[fill.client_order_id] = after
            fee_q += s.fee_table.fee(after) - s.fee_table.fee(before)
        fee = self._to_account(fee_q, fill.venue_time_ns)
        self.fees_by_order[fill.client_order_id] = self.fees_by_order.get(fill.client_order_id, 0.0) + fee
        return fee

    def _to_account(self, amount: float, t: int) -> float:
        if self.product.quote_ccy == self.account_currency:
            return amount
        if self.fx is None:
            raise FxRateMissingError(f"fees are in {self.product.quote_ccy} and the account in "
                                     f"{self.account_currency}; no FX rates were given")
        return self.fx.convert(amount, self.product.quote_ccy, self.account_currency, t)
