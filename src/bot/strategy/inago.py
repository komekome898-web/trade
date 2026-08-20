"""いなご (volume-surge) strategy.

Follows aggressive order-flow surges: when taker volume spikes far above its
rolling baseline with a strong directional imbalance and price confirming,
enter in that direction. Exit when an opposite surge appears (the engine's
symmetric handling closes-and/or-reverses) — the classic いなごフライヤー
pattern, computed from our own executions data instead of the website.

Requires flow candles with `buy_vol` and `sell_vol` columns (taker sides).
TP/SL backstops are applied by the caller (engine params / live bot stop).
"""
from __future__ import annotations

import pandas as pd

from bot.strategy.base import Signal, SignalType, Strategy


class InagoStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return int(self.params.get("baseline_window", 60)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        window = int(self.params.get("baseline_window", 60))
        spike_mult = float(self.params.get("spike_mult", 5.0))
        dir_ratio = float(self.params.get("dir_ratio", 0.7))

        if "buy_vol" not in candles.columns or "sell_vol" not in candles.columns:
            return Signal(SignalType.HOLD, "no order-flow columns")
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        vol = candles["volume"]
        baseline = float(vol.iloc[-1 - window:-1].mean())
        v = float(vol.iloc[-1])
        buy = float(candles["buy_vol"].iloc[-1])
        sell = float(candles["sell_vol"].iloc[-1])
        close = float(candles["close"].iloc[-1])
        open_ = float(candles["open"].iloc[-1])
        ratio = buy / v if v > 0 else 0.5
        ind = {"volume": v, "baseline": baseline, "buy_ratio": ratio, "close": close}

        if baseline <= 0 or v < spike_mult * baseline:
            return Signal(SignalType.HOLD, "no volume surge", ind)
        if ratio >= dir_ratio and close > open_:
            return Signal(SignalType.BUY, f"buy surge x{v / baseline:.1f}", ind)
        if ratio <= 1 - dir_ratio and close < open_:
            return Signal(SignalType.SELL, f"sell surge x{v / baseline:.1f}", ind)
        return Signal(SignalType.HOLD, "surge without direction", ind)
