"""Shared builders for the core tests (synthetic inputs only)."""
from __future__ import annotations

from bot.bt.core import (
    BarEvent,
    ClockEvent,
    Strategy,
    TradeEvent,
)

T0 = 1_700_000_000_000_000_000  # 2023-11-14T22:13:20Z in ns
SEC = 1_000_000_000
MS = 1_000_000


def trade(t: int, price: float = 100.0, size: float = 1.0, side: str = "buy", exch: int | None = None) -> TradeEvent:
    return TradeEvent(received_time_ns=t, exchange_time_ns=exch, price=price, size=size, side=side)


def bar(t: int, close: float, exch: int | None = None) -> BarEvent:
    return BarEvent(received_time_ns=t, exchange_time_ns=exch, open=close, high=close, low=close, close=close, volume=1.0)


def clock(t: int) -> ClockEvent:
    return ClockEvent(received_time_ns=t)


class Recorder(Strategy):
    """Records every delivered event; optional `act(event, ctx)` hook."""

    def __init__(self, act=None) -> None:
        self.seen = []
        self.act = act

    def on_event(self, event, ctx) -> None:
        self.seen.append(event)
        if self.act is not None:
            self.act(event, ctx)
