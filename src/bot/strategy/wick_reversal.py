"""ヒゲ (wick) reversal strategy.

A completed candle with a wick much larger than its body marks a rejected
price probe; fade it (long after a large lower wick, short after a large
upper wick). Exits are TP/SL backstops supplied by the caller, mirroring the
original rule "stop when the wick price is broken again".

Designed for 15-minute candles (the caller resamples), but timeframe-agnostic.
"""
from __future__ import annotations

import pandas as pd

from bot.strategy.base import Signal, SignalType, Strategy


class WickReversalStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return 3

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        wick_body_mult = float(self.params.get("wick_body_mult", 2.0))
        min_wick_pct = float(self.params.get("min_wick_pct", 0.15))

        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")
        o = float(candles["open"].iloc[-1])
        h = float(candles["high"].iloc[-1])
        low = float(candles["low"].iloc[-1])
        c = float(candles["close"].iloc[-1])
        body = abs(c - o)
        upper = h - max(o, c)
        lower = min(o, c) - low
        min_wick = min_wick_pct / 100 * c
        ind = {"body": body, "upper_wick": upper, "lower_wick": lower, "close": c}

        if lower >= max(wick_body_mult * body, min_wick) and lower > upper:
            return Signal(SignalType.BUY, f"lower wick {lower / c * 100:.2f}% rejected", ind)
        if upper >= max(wick_body_mult * body, min_wick) and upper > lower:
            return Signal(SignalType.SELL, f"upper wick {upper / c * 100:.2f}% rejected", ind)
        return Signal(SignalType.HOLD, "no dominant wick", ind)
