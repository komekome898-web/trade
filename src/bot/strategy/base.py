"""Strategy interface.

Strategies see candles and return a Signal. They know nothing about orders,
sizes, balances or the exchange API — that separation is a hard rule.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class SignalType(Enum):
    BUY = "BUY"      # open/extend long, or close a short
    SELL = "SELL"    # close a long, or open a short (shortable products only)
    CLOSE = "CLOSE"  # flatten any open position; never opens one
    HOLD = "HOLD"


@dataclass
class Signal:
    type: SignalType
    reason: str = ""
    indicators: dict[str, float] = field(default_factory=dict)


class Strategy(ABC):
    """Stateless decision function over completed candles.

    `candles` is a DataFrame with columns open/high/low/close/volume where the
    LAST row is the most recently COMPLETED candle. Implementations must only
    use rows 0..i to decide at i (backtest engine enforces this by slicing).
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}

    @property
    @abstractmethod
    def min_history(self) -> int:
        """Minimum number of candles required before signals are meaningful."""

    @abstractmethod
    def on_candles(self, candles: pd.DataFrame) -> Signal:
        ...
