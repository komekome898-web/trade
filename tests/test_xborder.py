"""Cross-exchange strategy and leader feed."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot.market_data.external_feed import BinanceFeed
from bot.strategy.xborder_momentum import XborderMomentumStrategy
from bot.strategy.base import SignalType


def make_candles(n, leader=None):
    p = np.full(n, 100.0)
    df = pd.DataFrame({"open": p, "high": p, "low": p, "close": p,
                       "volume": np.ones(n)})
    if leader is not None:
        df["leader_close"] = pd.Series(leader, dtype="float64")
    return df


def test_buy_on_leader_surge():
    leader = [1.0] * 19 + [1.01]  # +1% over last 10 bars
    s = XborderMomentumStrategy({"k": 10, "thr_pct": 0.8})
    sig = s.on_candles(make_candles(20, leader))
    assert sig.type is SignalType.BUY
    assert sig.indicators["leader_mom_pct"] > 0.8


def test_sell_on_negative_leader_momentum():
    leader = [1.0] * 19 + [0.99]
    s = XborderMomentumStrategy({"k": 10, "thr_pct": 0.8})
    assert s.on_candles(make_candles(20, leader)).type is SignalType.SELL


def test_hold_without_leader_column():
    s = XborderMomentumStrategy({"k": 10, "thr_pct": 0.8})
    sig = s.on_candles(make_candles(20))
    assert sig.type is SignalType.HOLD
    assert "no leader" in sig.reason


def test_hold_on_leader_gap():
    leader = [1.0] * 19 + [np.nan]
    s = XborderMomentumStrategy({"k": 10, "thr_pct": 0.8})
    assert s.on_candles(make_candles(20, leader)).type is SignalType.HOLD


class FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, price="1.2345", status=200):
        self.price = price
        self.status = status
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return FakeResp(self.status, {"symbol": params["symbol"], "price": self.price})


def test_feed_records_interval_close():
    now = [1200.0]
    feed = BinanceFeed("XRPUSDT", interval_sec=60, session=FakeSession("2.0"),
                       clock=lambda: now[0])
    assert feed.poll() == 2.0
    assert feed.close_for(1200) == 2.0
    assert feed.close_for(1260) == 2.0   # falls back to previous interval
    assert feed.close_for(1500) is None  # too stale (beyond max_age)


def test_feed_error_returns_none():
    feed = BinanceFeed("XRPUSDT", session=FakeSession(status=500))
    assert feed.poll() is None
    assert feed.last_update is None
