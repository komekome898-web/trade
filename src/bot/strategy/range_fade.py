"""レンジ (range fade) strategy.

In a calm regime (narrow rolling range, no volume expansion) fade the range
edges: buy near the bottom, short near the top, flatten in the middle. The
moment volatility or volume expands, stand aside (CLOSE) — the original
rule's 「増えてきたら取引をやめて静観」.
"""
from __future__ import annotations

import pandas as pd

from bot.strategy.base import Signal, SignalType, Strategy


class RangeFadeStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return int(self.params.get("window", 120)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        window = int(self.params.get("window", 120))
        max_width_pct = float(self.params.get("max_width_pct", 0.6))
        edge_frac = float(self.params.get("edge_frac", 0.15))
        mid_band = float(self.params.get("mid_band", 0.10))
        vol_expand_mult = float(self.params.get("vol_expand_mult", 3.0))

        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")
        hist = candles.iloc[-1 - window:-1]          # prior bars only
        hi = float(hist["high"].max())
        lo = float(hist["low"].min())
        close = float(candles["close"].iloc[-1])
        width_pct = (hi - lo) / close * 100 if close > 0 else float("inf")
        vol_base = float(hist["volume"].mean())
        v = float(candles["volume"].iloc[-1])
        ind = {"range_hi": hi, "range_lo": lo, "width_pct": width_pct,
               "close": close, "vol_ratio": v / vol_base if vol_base > 0 else 0.0}

        regime_calm = width_pct <= max_width_pct and (
            vol_base <= 0 or v <= vol_expand_mult * vol_base)
        if not regime_calm:
            return Signal(SignalType.CLOSE, "regime not calm — stand aside", ind)
        if hi <= lo:
            return Signal(SignalType.HOLD, "degenerate range", ind)

        pos_in_range = (close - lo) / (hi - lo)
        ind["pos_in_range"] = pos_in_range
        if pos_in_range <= edge_frac:
            return Signal(SignalType.BUY, f"at range bottom ({pos_in_range:.2f})", ind)
        if pos_in_range >= 1 - edge_frac:
            return Signal(SignalType.SELL, f"at range top ({pos_in_range:.2f})", ind)
        if abs(pos_in_range - 0.5) <= mid_band:
            return Signal(SignalType.CLOSE, "back at range middle", ind)
        return Signal(SignalType.HOLD, "inside range", ind)
