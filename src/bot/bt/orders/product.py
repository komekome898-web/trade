"""What is traded: one instrument's specification.

Every field is required (no default): a product is always stated in full for a
run. Grid checks (tick, quantity step) are made on the shortest decimal text of
the numbers (`repr` of a float) with `decimal.Decimal`, so 0.19 is a multiple
of 1e-08 and 150.103 is on a 0.001 tick, exactly, without a float tolerance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from .errors import ProductSpecError


def _dec(x: float) -> Decimal:
    return Decimal(repr(float(x)))


def _positive(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProductSpecError(f"{name} must be a number, got {type(value).__name__}")
    f = float(value)
    if not math.isfinite(f) or f <= 0:
        raise ProductSpecError(f"{name} must be finite and > 0, got {value!r}")
    return f


def _text(name: str, value) -> str:
    if type(value) is not str or not value:
        raise ProductSpecError(f"{name} must be a non-empty str, got {value!r}")
    return value


@dataclass(frozen=True)
class Product:
    """One instrument.

    symbol / venue: names (the venue name also selects the data-wait notes of
    `bot.bt.fill.data_wait`). tick: price grid. min_qty: smallest order size.
    qty_step: size grid. quote_ccy: currency the price is quoted in (JPY for
    FX_BTC_JPY and JPX stocks, USD for EURUSD). margin: True for a margin
    (derivative / leveraged) product, False for a cash product (a cash
    product cannot be sold short)."""

    symbol: str
    venue: str
    tick: float
    min_qty: float
    qty_step: float
    quote_ccy: str
    margin: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text("symbol", self.symbol))
        object.__setattr__(self, "venue", _text("venue", self.venue))
        object.__setattr__(self, "tick", _positive("tick", self.tick))
        object.__setattr__(self, "min_qty", _positive("min_qty", self.min_qty))
        object.__setattr__(self, "qty_step", _positive("qty_step", self.qty_step))
        object.__setattr__(self, "quote_ccy", _text("quote_ccy", self.quote_ccy))
        if type(self.margin) is not bool:
            raise ProductSpecError(f"margin must be a bool, got {self.margin!r}")

    # -- grids ---------------------------------------------------------------
    def on_tick(self, price: float) -> bool:
        return _dec(price) % _dec(self.tick) == 0

    def on_step(self, qty: float) -> bool:
        return _dec(qty) % _dec(self.qty_step) == 0

    def round_qty_down(self, qty: float) -> float:
        """Floor a size to the size grid."""
        step = _dec(self.qty_step)
        n = (_dec(qty) / step).to_integral_value(rounding=ROUND_FLOOR)
        return float(n * step)

    def round_price(self, price: float, direction: str) -> float:
        """Round to the tick grid: direction "down" (floor) or "up" (ceiling)."""
        tick = _dec(self.tick)
        n = (_dec(price) / tick).to_integral_value(rounding=ROUND_FLOOR if direction == "down" else ROUND_CEILING)
        return float(n * tick)
