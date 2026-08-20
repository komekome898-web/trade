"""EMA cross trend-following with ATR volatility filter."""
from __future__ import annotations

import math

import pandas as pd

from bot.indicators.core import atr, ema
from bot.strategy.base import Signal, SignalType, Strategy


class EmaCrossStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return max(int(self.params.get("slow_period", 26)),
                   int(self.params.get("atr_period", 14))) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        fast_p = int(self.params.get("fast_period", 9))
        slow_p = int(self.params.get("slow_period", 26))
        atr_p = int(self.params.get("atr_period", 14))
        min_vol_pct = float(self.params.get("atr_min_volatility_pct", 0.0))

        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        close = candles["close"]
        fast = ema(close, fast_p)
        slow = ema(close, slow_p)
        a = atr(candles["high"], candles["low"], close, atr_p)

        ind = {
            "ema_fast": float(fast.iloc[-1]), "ema_slow": float(slow.iloc[-1]),
            "ema_fast_prev": float(fast.iloc[-2]), "ema_slow_prev": float(slow.iloc[-2]),
            "atr": float(a.iloc[-1]), "close": float(close.iloc[-1]),
        }
        if any(math.isnan(v) for v in ind.values()):
            return Signal(SignalType.HOLD, "indicators warming up", ind)

        atr_pct = ind["atr"] / ind["close"] * 100
        ind["atr_pct"] = atr_pct
        if atr_pct < min_vol_pct:
            return Signal(SignalType.HOLD, f"volatility too low ({atr_pct:.3f}%)", ind)

        crossed_up = ind["ema_fast_prev"] <= ind["ema_slow_prev"] and ind["ema_fast"] > ind["ema_slow"]
        crossed_down = ind["ema_fast_prev"] >= ind["ema_slow_prev"] and ind["ema_fast"] < ind["ema_slow"]
        if crossed_up:
            return Signal(SignalType.BUY, "EMA fast crossed above slow", ind)
        if crossed_down:
            return Signal(SignalType.SELL, "EMA fast crossed below slow", ind)
        return Signal(SignalType.HOLD, "no cross", ind)
