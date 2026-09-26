"""The event path: the same work done by a strategy on the core's engine,
one event at a time (the reference the vector path is fixed against).

run_event_bars(trades, interval_s)   -> bars (bars.py definition)
run_event_rule(bars, interval_s, rule) -> the rule's series (rules.py)

`trades`: the core's TradeEvent objects (e.g. from the data layer's
`LoadResult.events`) or mappings {t_ns, px, qty, side, id}. `bars`:
mappings {start_ns, open, high, low, close, volume}; each becomes a
BarEvent stamped at its close (start + interval), as the core requires.
The engine runs with no order sockets used (the strategies place no
orders) and the run's time span declared.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from ..core.engine import CoreEngine
from ..core.events import BarEvent, TradeEvent
from ..core.strategy import Strategy
from ..data.errors import VectorError
from .bars import interval_ns


def _trade_events(trades: Iterable[Any]) -> list[TradeEvent]:
    out = []
    for i, t in enumerate(trades):
        if type(t) is TradeEvent:
            out.append(t)
        elif isinstance(t, dict):
            try:
                out.append(TradeEvent(received_time_ns=t["t_ns"], price=t["px"], size=t["qty"],
                                      side=t.get("side", ""), trade_id=str(t.get("id", ""))))
            except (KeyError, ValueError) as exc:
                raise VectorError(f"trades[{i}]: {exc}") from None
        else:
            raise VectorError(f"trades[{i}] must be a TradeEvent or a mapping, got {type(t).__name__}")
    return out


def bar_events(bars: Iterable[Any], interval_s: int) -> list[BarEvent]:
    iv = interval_ns(interval_s)
    out, last = [], None
    for i, b in enumerate(bars):
        if not isinstance(b, dict):
            raise VectorError(f"bars[{i}] must be a mapping")
        try:
            st = b["start_ns"]
            if type(st) is not int:
                raise VectorError(f"bars[{i}].start_ns must be an int of ns")
            if last is not None and st <= last:
                raise VectorError(f"bars[{i}].start_ns {st} is not after the previous bar's {last}")
            last = st
            out.append(BarEvent(received_time_ns=st + iv, start_time_ns=st, open=b["open"], high=b["high"],
                                low=b["low"], close=b["close"], volume=b["volume"]))
        except KeyError as exc:
            raise VectorError(f"bars[{i}]: no field {exc}") from None
        except ValueError as exc:
            if isinstance(exc, VectorError):
                raise
            raise VectorError(f"bars[{i}]: {exc}") from None
    return out


def _run(strategy: Strategy, events: list) -> None:
    if not events:
        return
    lo = min(int(e.exchange_time_ns) for e in events)
    hi = max(int(e.received_time_ns) for e in events)
    CoreEngine(strategy, {"input": events}, time_span_ns=(lo, hi), history_limit=1).run()


class _BarBuilder(Strategy):
    def __init__(self, iv: int) -> None:
        self._iv = iv
        self._cur: Optional[dict] = None
        self.bars: list[dict] = []

    def on_event(self, event, ctx) -> None:
        if type(event) is not TradeEvent:
            return
        t, p, q = int(event.exchange_time_ns), float(event.price), float(event.size)
        start = t // self._iv * self._iv
        cur = self._cur
        if cur is None or cur["start_ns"] != start:
            if cur is not None:
                self.bars.append(cur)
            self._cur = {"start_ns": start, "open": p, "high": p, "low": p, "close": p, "volume": q}
            return
        cur["high"] = max(cur["high"], p)
        cur["low"] = min(cur["low"], p)
        cur["close"] = p
        cur["volume"] = cur["volume"] + q

    def finish(self) -> list[dict]:
        if self._cur is not None:
            self.bars.append(self._cur)
            self._cur = None
        return self.bars


def run_event_bars(trades: Iterable[Any], interval_s: int) -> list[dict]:
    iv = interval_ns(interval_s)
    evs = _trade_events(trades)
    for i in range(1, len(evs)):
        if evs[i].exchange_time_ns < evs[i - 1].exchange_time_ns:
            raise VectorError(f"trade times go backward at index {i}; sort or resolve them first (the data layer's anomalies)")
    s = _BarBuilder(iv)
    _run(s, evs)
    return s.finish()


def run_event_rule(bars: Iterable[Any], interval_s: int, rule: Any) -> dict:
    evs = bar_events(bars, interval_s)
    s = rule.event_strategy()
    _run(s, evs)
    return s.result()
