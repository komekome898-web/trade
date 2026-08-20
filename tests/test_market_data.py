"""Market data: fetch, abnormal price/spread, data staleness (items 4, 11, 12)."""
from __future__ import annotations

import pytest

from bot.market_data.feed import CandleBuilder, MarketDataAnomaly, MarketDataFeed
from tests.conftest import make_ticker


def make_feed(client, **kw):
    return MarketDataFeed(client, "XRP_JPY", max_price_jump_pct=5.0,
                          max_spread_pct=1.0, max_staleness_sec=60, **kw)


def test_poll_ticker_ok(client, fake_session):
    fake_session.set("GET", "/v1/ticker", make_ticker(100.0, 99.9, 100.1))
    tick = make_feed(client).poll_ticker()
    assert tick.price == 100.0


def test_abnormal_price_jump_detected(client, fake_session):
    feed = make_feed(client)
    fake_session.set("GET", "/v1/ticker", make_ticker(100.0, 99.9, 100.1))
    feed.poll_ticker()
    fake_session.set("GET", "/v1/ticker", make_ticker(110.0, 109.9, 110.1))  # +10%
    with pytest.raises(MarketDataAnomaly, match="price jump"):
        feed.poll_ticker()


def test_abnormal_spread_detected(client, fake_session):
    fake_session.set("GET", "/v1/ticker", make_ticker(100.0, 98.0, 102.0))  # 4% spread
    with pytest.raises(MarketDataAnomaly, match="spread"):
        make_feed(client).poll_ticker()


def test_non_positive_price_detected(client, fake_session):
    fake_session.set("GET", "/v1/ticker", make_ticker(0.0, 99.9, 100.1))
    with pytest.raises(MarketDataAnomaly):
        make_feed(client).poll_ticker()


def test_staleness_detected(client, fake_session):
    now = [1000.0]
    feed = MarketDataFeed(client, "XRP_JPY", max_staleness_sec=60, clock=lambda: now[0])
    fake_session.set("GET", "/v1/ticker", make_ticker())
    feed.poll_ticker()
    now[0] += 61
    with pytest.raises(MarketDataAnomaly, match="stale"):
        feed.check_freshness()


def test_no_data_yet_is_stale(client):
    with pytest.raises(MarketDataAnomaly):
        make_feed(client).check_freshness()


def test_candle_builder_completes_on_interval_boundary():
    cb = CandleBuilder(60)
    assert cb.add_trade(0, 100, 1) is None
    assert cb.add_trade(30, 105, 1) is None
    finished = cb.add_trade(65, 90, 2)   # next interval -> emits candle for [0,60)
    assert finished is not None
    assert (finished.open, finished.high, finished.low, finished.close) == (100, 105, 100, 105)
    assert finished.volume == 2


def test_candle_builder_ignores_out_of_order_trades():
    cb = CandleBuilder(60)
    cb.add_trade(65, 100, 1)
    assert cb.add_trade(10, 999, 1) is None  # late trade must not rewrite history
    assert cb.completed == []
