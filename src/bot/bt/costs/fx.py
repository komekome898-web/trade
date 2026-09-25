"""Currency conversion from dated rates (reference data given to the run).

The core has no event type for an FX rate, so rates are handed to the cost
model and the account as a dated table. `rate(pair, t)` is the last rate of
`pair` with time <= t (a rate stamped exactly at t is in force at t). A
conversion with no rate in force is refused (`FxRateMissingError`), never
assumed to be 1.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Sequence

from bot.bt.orders.errors import ExecutionModelError


class FxRateMissingError(ExecutionModelError):
    """No rate in force for a conversion the run needs."""


@dataclass(frozen=True)
class FxPoint:
    time_ns: int
    pair: str  # six letters, base then quote: "USDJPY" = JPY per USD
    rate: float

    def __post_init__(self) -> None:
        if type(self.time_ns) is not int:
            raise ExecutionModelError(f"fx time must be an int of ns, got {self.time_ns!r}")
        if type(self.pair) is not str or len(self.pair) != 6 or not self.pair.isalpha() or not self.pair.isupper():
            raise ExecutionModelError(f"fx pair must be six upper-case letters (base+quote), got {self.pair!r}")
        if isinstance(self.rate, bool) or not isinstance(self.rate, (int, float)) or not math.isfinite(self.rate) \
                or self.rate <= 0:
            raise ExecutionModelError(f"fx rate must be finite > 0, got {self.rate!r}")
        object.__setattr__(self, "rate", float(self.rate))


class FxRates:
    def __init__(self, points: Sequence[FxPoint]) -> None:
        by_pair: dict[str, list[tuple[int, int, float]]] = {}
        for i, p in enumerate(points):
            if type(p) is not FxPoint:
                raise ExecutionModelError(f"FxRates holds FxPoint objects, got {type(p).__name__}")
            by_pair.setdefault(p.pair, []).append((p.time_ns, i, p.rate))
        self._times: dict[str, list[int]] = {}
        self._rates: dict[str, list[float]] = {}
        for pair, rows in by_pair.items():
            rows.sort()
            self._times[pair] = [r[0] for r in rows]
            self._rates[pair] = [r[2] for r in rows]

    def rate(self, pair: str, t: int) -> float:
        times = self._times.get(pair)
        if times:
            i = bisect.bisect_right(times, t) - 1
            if i >= 0:
                return self._rates[pair][i]
        raise FxRateMissingError(f"no {pair} rate in force at {t}")

    def convert(self, amount: float, from_ccy: str, to_ccy: str, t: int) -> float:
        """`amount` in `from_ccy` expressed in `to_ccy` at time t."""
        if from_ccy == to_ccy:
            return amount
        direct, inverse = from_ccy + to_ccy, to_ccy + from_ccy
        if direct in self._times:
            return amount * self.rate(direct, t)
        if inverse in self._times:
            return amount / self.rate(inverse, t)
        raise FxRateMissingError(f"no {direct} (or {inverse}) rate given; cannot express {from_ccy} in {to_ccy}")
