"""Donchian channel breakout (prior-N-bar channel, no same-bar look-ahead)."""
from __future__ import annotations

import math

import pandas as pd

from bot.indicators.core import donchian
from bot.strategy.base import Signal, SignalType, Strategy


class BreakoutStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return int(self.params.get("channel_period", 20)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        period = int(self.params.get("channel_period", 20))
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        ch = donchian(candles["high"], candles["low"], period)
        close = float(candles["close"].iloc[-1])
        upper = float(ch["upper"].iloc[-1])
        lower = float(ch["lower"].iloc[-1])
        ind = {"close": close, "donchian_upper": upper, "donchian_lower": lower}
        if math.isnan(upper) or math.isnan(lower):
            return Signal(SignalType.HOLD, "indicators warming up", ind)

        if close > upper:
            return Signal(SignalType.BUY, f"close {close} broke above {period}-bar high {upper}", ind)
        if close < lower:
            return Signal(SignalType.SELL, f"close {close} broke below {period}-bar low {lower}", ind)
        return Signal(SignalType.HOLD, "inside channel", ind)
