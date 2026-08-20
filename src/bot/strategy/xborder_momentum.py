"""Cross-exchange momentum: follow strong moves on a leader market (Binance)
in the local (bitFlyer) market.

Research basis (docs/RESEARCH_REPORT): Binance XRPUSDT leads bitFlyer XRP_JPY
by 1-3 minutes (lag-1 corr +0.18). Average drift after ordinary moves is below
cost; only large leader moves (>= ~0.8% over 10-30 min) showed material
follow-through, on a statistically insufficient sample. This strategy exists
to VALIDATE that signal in paper trading; it is not proven.

The candles frame must carry a `leader_close` column; missing/stale leader
data yields HOLD.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from bot.strategy.base import Signal, SignalType, Strategy


class XborderMomentumStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return int(self.params.get("k", 10)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        k = int(self.params.get("k", 10))
        thr = float(self.params.get("thr_pct", 0.8)) / 100
        exit_band = float(self.params.get("exit_pct", 0.1)) / 100

        if "leader_close" not in candles.columns:
            return Signal(SignalType.HOLD, "no leader data column")
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        leader_now = float(candles["leader_close"].iloc[-1])
        leader_past = float(candles["leader_close"].iloc[-1 - k])
        if math.isnan(leader_now) or math.isnan(leader_past) or leader_past <= 0:
            return Signal(SignalType.HOLD, "leader data gap")

        mom = float(np.log(leader_now / leader_past))
        ind = {"leader_mom_pct": mom * 100, "leader_close": leader_now,
               "close": float(candles["close"].iloc[-1])}
        if mom > thr:
            return Signal(SignalType.BUY, f"leader +{mom*100:.2f}% over {k} bars", ind)
        if mom < -thr:
            return Signal(SignalType.SELL, f"leader {mom*100:.2f}% over {k} bars", ind)
        if abs(mom) <= exit_band:
            return Signal(SignalType.CLOSE, f"leader momentum faded ({mom*100:.2f}%)", ind)
        return Signal(SignalType.HOLD, "between exit band and threshold", ind)
