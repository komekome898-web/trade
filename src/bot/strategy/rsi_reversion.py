"""RSI mean-reversion with long-EMA trend filter."""
from __future__ import annotations

import math

import pandas as pd

from bot.indicators.core import ema, rsi
from bot.strategy.base import Signal, SignalType, Strategy


class RsiReversionStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return max(int(self.params.get("rsi_period", 14)),
                   int(self.params.get("trend_period", 50))) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        rsi_p = int(self.params.get("rsi_period", 14))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))
        trend_p = int(self.params.get("trend_period", 50))

        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        close = candles["close"]
        r = rsi(close, rsi_p)
        trend = ema(close, trend_p)
        ind = {
            "rsi": float(r.iloc[-1]),
            "trend_ema": float(trend.iloc[-1]),
            "trend_ema_prev": float(trend.iloc[-2]),
            "close": float(close.iloc[-1]),
        }
        if any(math.isnan(v) for v in ind.values()):
            return Signal(SignalType.HOLD, "indicators warming up", ind)

        trend_up = ind["trend_ema"] >= ind["trend_ema_prev"]
        if ind["rsi"] <= oversold and trend_up:
            return Signal(SignalType.BUY, f"RSI oversold ({ind['rsi']:.1f}) in non-down trend", ind)
        if ind["rsi"] >= overbought:
            return Signal(SignalType.SELL, f"RSI overbought ({ind['rsi']:.1f})", ind)
        return Signal(SignalType.HOLD, "RSI neutral", ind)
