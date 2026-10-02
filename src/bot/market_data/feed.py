"""Market data acquisition with anomaly and staleness detection.

bitFlyer has no official candle endpoint, so 1-minute candles are built from
the public executions stream. All anomalies surface as MarketDataAnomaly so
the caller can stop trading on the safe side (rule 8).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from bot.exchange.bitflyer_client import BitflyerClient

logger = logging.getLogger(__name__)


class MarketDataAnomaly(Exception):
    """Abnormal price / spread / staleness — trading must pause or stop."""


class MarketDataStale(MarketDataAnomaly):
    """No fresh data for longer than `max_staleness_sec` — the ONE anomaly a
    PAPER bot pauses on instead of tripping the kill switch (bot/main.py,
    `_pause_for_stale_data`, owner L-544). A subclass, so every existing
    `except MarketDataAnomaly` still catches it, and the pause is decided by
    the exception's type, never by its message text.

    `detail_ja` is the same fact for the owner's alert (O-1: owner-facing
    text is Japanese); the English message stays the log's."""

    def __init__(self, age_sec: float, limit_sec: float) -> None:
        super().__init__(f"market data stale: {age_sec:.0f}s > {limit_sec}s")
        self.age_sec, self.limit_sec = age_sec, limit_sec
        self.detail_ja = (f"最後に市場データを受け取ってから {age_sec:.0f} 秒"
                          f"(上限 {limit_sec:g} 秒)")


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
    buy_vol: float = 0.0    # taker-buy volume (order-flow strategies)
    sell_vol: float = 0.0


@dataclass
class CandleBuilder:
    """Builds fixed-interval candles from (timestamp, price, size) trades.

    A candle is only emitted once a trade arrives in a *later* interval, so
    consumers never see a partially formed (look-ahead prone) candle.
    """

    interval_sec: int = 60
    _current: Candle | None = None
    completed: list[Candle] = field(default_factory=list)

    def add_trade(self, timestamp: float, price: float, size: float,
                  side: str | None = None) -> Candle | None:
        start = int(timestamp // self.interval_sec) * self.interval_sec
        buy = size if side == "BUY" else 0.0
        sell = size if side == "SELL" else 0.0
        cur = self._current
        if cur is None:
            self._current = Candle(start, price, price, price, price, size, buy, sell)
            return None
        if start == cur.start:
            cur.high = max(cur.high, price)
            cur.low = min(cur.low, price)
            cur.close = price
            cur.volume += size
            cur.buy_vol += buy
            cur.sell_vol += sell
            return None
        if start < cur.start:
            return None  # late/out-of-order trade: ignore rather than rewrite history
        finished = cur
        self.completed.append(finished)
        self._current = Candle(start, price, price, price, price, size, buy, sell)
        return finished


class SpreadRecorder:
    """Appends every observed quote to a CSV — the dataset strategy ③
    (spread/market-making) needs, which cannot be reconstructed from trades."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("timestamp,best_bid,best_ask,ltp\n", encoding="utf-8")

    def record(self, tick: "Tick") -> None:
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(f"{tick.timestamp:.3f},{tick.best_bid},{tick.best_ask},{tick.price}\n")
        except OSError:
            pass  # recording must never break trading


class MarketDataFeed:
    def __init__(
        self,
        client: BitflyerClient,
        product_code: str,
        *,
        max_staleness_sec: float = 60,
        max_spread_pct: float = 1.0,
        clock=time.time,
    ):
        self._client = client
        self.product_code = product_code
        self.max_staleness_sec = max_staleness_sec
        self.max_spread_pct = max_spread_pct
        self._clock = clock
        self.last_tick: Tick | None = None
        self.last_update: float | None = None
        self._last_exec_id = 0

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
        # No check on the size of the move from the last tick (owner L-548
        # "外す"): the 5% limit had no recorded basis, never fired in paper,
        # and a real crash moves more than 5% within a minute — it would have
        # frozen the position with no stop-loss exactly then.

    def poll_executions(self, builder: CandleBuilder) -> list[Candle]:
        """Fetch new public executions and feed them into `builder`, returning
        any candles completed by this batch. Trade timestamps come from the
        exchange (exec_date), so candles carry real volume and taker sides."""
        from datetime import datetime, timezone

        trades = self._client.executions(self.product_code, count=100)
        new = [t for t in trades if int(t["id"]) > self._last_exec_id]
        completed: list[Candle] = []
        for t in sorted(new, key=lambda x: int(x["id"])):
            ts = datetime.fromisoformat(t["exec_date"]).replace(
                tzinfo=timezone.utc).timestamp()
            finished = builder.add_trade(ts, float(t["price"]), float(t["size"]),
                                         side=t.get("side") or None)
            if finished is not None:
                completed.append(finished)
            self._last_exec_id = max(self._last_exec_id, int(t["id"]))
        return completed

    def check_freshness(self) -> None:
        if self.last_update is None:
            raise MarketDataAnomaly("no market data received yet")
        age = self._clock() - self.last_update
        if age > self.max_staleness_sec:
            raise MarketDataStale(age, self.max_staleness_sec)
