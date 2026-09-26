"""Run one golden scene through an engine module that has the old names
(`run_backtest`, `CostModel`) and record its whole output as plain JSON
(floats kept exact: json writes a float's repr, which reads back to the same
bits)."""
from __future__ import annotations

import pandas as pd

from bot.strategy.base import Signal, SignalType, Strategy

_SIG = {".": SignalType.HOLD, "B": SignalType.BUY, "S": SignalType.SELL, "C": SignalType.CLOSE}


class Script(Strategy):
    def __init__(self, signals: str, min_history: int):
        super().__init__({})
        self._s = signals
        self._m = min_history

    @property
    def min_history(self) -> int:
        return self._m

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        return Signal(_SIG[self._s[len(candles) - 1]])


def frame(bars):
    idx = pd.date_range("2026-01-05", periods=len(bars), freq="min", tz="UTC")
    return pd.DataFrame({"open": [b[0] for b in bars], "high": [b[1] for b in bars], "low": [b[2] for b in bars],
                         "close": [b[3] for b in bars], "volume": [1.0] * len(bars)}, index=idx)


def run(engine, scene: dict) -> dict:
    opts = dict(scene["options"])
    if "costs" in opts:
        opts["costs"] = engine.CostModel(**opts["costs"])
    res = engine.run_backtest(Script(scene["signals"], scene["min_history"]), frame(scene["bars"]), **opts)
    return {"trade_log": [dict(e) for e in res.trade_log], "trade_pnls": [float(p) for p in res.trade_pnls],
            "equity": [float(x) for x in res.equity_curve.tolist()],
            "metrics": dict(res.metrics.as_dict()), "missed_fills": int(res.missed_fills)}
