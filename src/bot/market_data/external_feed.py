"""External (leader) market price feed for cross-exchange signals.

Read-only public endpoints, no auth. The feed builds per-interval closes that
main.py merges into the candles frame as a `leader_close` column. On any error
the feed reports no data and the strategy holds — never trades on a stale or
missing leader price.
"""
from __future__ import annotations

import time

import requests

BINANCE_PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"


class BinanceFeed:
    def __init__(self, symbol: str = "XRPUSDT", interval_sec: int = 60,
                 session: requests.Session | None = None, timeout: float = 10.0,
                 clock=time.time):
        self.symbol = symbol
        self.interval_sec = interval_sec
        self._session = session or requests.Session()
        self._timeout = timeout
        self._clock = clock
        # closed per-interval prices: {interval_start_unix: last price seen}
        self._closes: dict[int, float] = {}
        self.last_update: float | None = None

    def poll(self) -> float | None:
        try:
            resp = self._session.get(BINANCE_PRICE_URL,
                                     params={"symbol": self.symbol},
                                     timeout=self._timeout)
            if resp.status_code != 200:
                return None
            price = float(resp.json()["price"])
        except (requests.exceptions.RequestException, KeyError, ValueError):
            return None
        now = self._clock()
        start = int(now // self.interval_sec) * self.interval_sec
        self._closes[start] = price
        self.last_update = now
        # bound memory: keep the most recent ~3000 intervals
        if len(self._closes) > 3000:
            for key in sorted(self._closes)[:-3000]:
                del self._closes[key]
        return price

    def close_for(self, interval_start: int, max_age_intervals: int = 2) -> float | None:
        """Close of the given interval, falling back to at most
        `max_age_intervals` earlier intervals; None when data is too stale."""
        for back in range(max_age_intervals + 1):
            price = self._closes.get(interval_start - back * self.interval_sec)
            if price is not None:
                return price
        return None
