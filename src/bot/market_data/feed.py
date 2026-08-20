"""Market data acquisition with anomaly and staleness detection.

bitFlyer has no official candle endpoint, so 1-minute candles are built from
the public executions stream. All anomalies surface as MarketDataAnomaly so
the caller can stop trading on the safe side (rule 8).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from bot.exchange.bitflyer_client import BitflyerClient


class MarketDataAnomaly(Exception):
    """Abnormal price / spread / staleness — trading must pause or stop."""


@dataclass
class Tick:
    timestamp: float
    price: float
    best_bid: float
    best_ask: float

    @property
    def spread_pct(self) -> float:
        mid = (self.best_bid + self.best_ask) / 2
        return (self.best_ask - self.best_bid) / mid * 100 if mid > 0 else float("inf")


@dataclass
class Candle:
    start: int  # unix seconds, aligned to interval
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class CandleBuilder:
    """Builds fixed-interval candles from (timestamp, price, size) trades.

    A candle is only emitted once a trade arrives in a *later* interval, so
    consumers never see a partially formed (look-ahead prone) candle.
    """

    interval_sec: int = 60
    _current: Candle | None = None
    completed: list[Candle] = field(default_factory=list)

    def add_trade(self, timestamp: float, price: float, size: float) -> Candle | None:
        start = int(timestamp // self.interval_sec) * self.interval_sec
        cur = self._current
        if cur is None:
            self._current = Candle(start, price, price, price, price, size)
            return None
        if start == cur.start:
            cur.high = max(cur.high, price)
            cur.low = min(cur.low, price)
            cur.close = price
            cur.volume += size
            return None
        if start < cur.start:
            return None  # late/out-of-order trade: ignore rather than rewrite history
        finished = cur
        self.completed.append(finished)
        self._current = Candle(start, price, price, price, price, size)
        return finished


class MarketDataFeed:
    def __init__(
        self,
        client: BitflyerClient,
        product_code: str,
        *,
        max_staleness_sec: float = 60,
        max_price_jump_pct: float = 5.0,
        max_spread_pct: float = 1.0,
        clock=time.time,
    ):
        self._client = client
        self.product_code = product_code
        self.max_staleness_sec = max_staleness_sec
        self.max_price_jump_pct = max_price_jump_pct
        self.max_spread_pct = max_spread_pct
        self._clock = clock
        self.last_tick: Tick | None = None
        self.last_update: float | None = None

    def poll_ticker(self) -> Tick:
        data = self._client.ticker(self.product_code)
        price = float(data["ltp"])
        tick = Tick(
            timestamp=self._clock(),
            price=price,
            best_bid=float(data["best_bid"]),
            best_ask=float(data["best_ask"]),
        )
        self._validate(tick)
        self.last_tick = tick
        self.last_update = tick.timestamp
        return tick

    def _validate(self, tick: Tick) -> None:
        if tick.price <= 0 or tick.best_bid <= 0 or tick.best_ask <= 0:
            raise MarketDataAnomaly(f"non-positive price data: {tick}")
        if tick.best_bid > tick.best_ask:
            raise MarketDataAnomaly(f"crossed book: bid {tick.best_bid} > ask {tick.best_ask}")
        if tick.spread_pct > self.max_spread_pct:
            raise MarketDataAnomaly(
                f"abnormal spread {tick.spread_pct:.3f}% > {self.max_spread_pct}%"
            )
        if self.last_tick is not None:
            jump = abs(tick.price - self.last_tick.price) / self.last_tick.price * 100
            if jump > self.max_price_jump_pct:
                raise MarketDataAnomaly(
                    f"abnormal price jump {jump:.2f}% (from {self.last_tick.price} to {tick.price})"
                )

    def check_freshness(self) -> None:
        if self.last_update is None:
            raise MarketDataAnomaly("no market data received yet")
        age = self._clock() - self.last_update
        if age > self.max_staleness_sec:
            raise MarketDataAnomaly(f"market data stale: {age:.0f}s > {self.max_staleness_sec}s")
