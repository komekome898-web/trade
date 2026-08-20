"""End-to-end paper-mode test on FX_BTC_JPY: leader drop opens a short,
leader recovery flattens it. No network, no real orders."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from bot.main import TradingApp
from bot.market_data.feed import Tick
from bot.monitoring.notifier import NullNotifier
from bot.settings import Mode, RiskLimits, Settings
from tests.conftest import FakeResponse, FakeSession

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(tmp_path, monkeypatch):
    shutil.copytree(REPO / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)

    config = {
        "product_code": "FX_BTC_JPY",
        "candle_interval_sec": 60,
        "paper_equity_jpy": 200000,
        "sfd_guard_pct": 4.5,
        "stop_loss_pct": 0.5,
        "strategy": {"name": "xborder_momentum",
                     "params": {"k": 2, "thr_pct": 0.15, "exit_pct": 0.03}},
        "leader": {"exchange": "binance", "symbol": "BTCUSDT"},
        "costs": {"slippage_pct": 0.0},
        "market_data": {"max_staleness_sec": 3600, "max_price_jump_pct": 50,
                        "max_spread_pct": 5.0},
    }
    limits = RiskLimits.from_dict({
        "MAX_ORDER_SIZE_JPY": 130000, "MAX_POSITION_SIZE_JPY": 130000,
        "MAX_DAILY_LOSS_JPY": 6000, "MAX_DRAWDOWN_PCT": 10.0,
        "MAX_OPEN_ORDERS": 1, "MAX_CONSECUTIVE_LOSSES": 5,
        "MAX_API_ERRORS_IN_ROW": 5,
    })
    settings = Settings(mode=Mode.PAPER, product_code="FX_BTC_JPY",
                        config=config, risk_limits=limits)

    session = FakeSession()
    # spot BTC ticker used by the SFD guard: divergence ~0
    session.set("GET", "/v1/ticker", FakeResponse(200, {
        "ltp": 10_000_000, "best_bid": 9_999_000, "best_ask": 10_001_000}))
    from bot.exchange.bitflyer_client import BitflyerClient
    client = BitflyerClient(session=session, sleep=lambda s: None)

    app = TradingApp(settings, client, NullNotifier())
    monkeypatch.setattr(app.leader_feed, "poll", lambda: None)
    return app


def drive(app, ticks, leader_by_start):
    """ticks: list of (t, price). leader_by_start: {interval_start: leader_close}."""
    app.leader_feed._closes.update(leader_by_start)
    for t, price in ticks:
        tick = Tick(timestamp=t, price=price, best_bid=price - 1000,
                    best_ask=price + 1000)
        app.feed.last_tick = tick
        app.feed.last_update = t

        def fake_poll(tick=tick):
            return tick
        app.feed.poll_ticker = fake_poll
        app.step()


def test_leader_drop_opens_short_then_recovery_closes(app):
    price = 10_000_000.0
    leader = {0: 100000.0, 60: 100000.0, 120: 100000.0, 180: 100000.0,
              240: 99600.0, 300: 99600.0, 360: 99610.0}
    ticks = [(30, price), (90, price), (150, price), (210, price),
             (270, price), (330, price)]
    drive(app, ticks, leader)
    # candle for start=240 completed at t=330: leader mom over k=2 =
    # log(99600/100000) = -0.40% < -0.15% -> SELL -> paper short 0.01 BTC
    assert app.portfolio.position_size == pytest.approx(-0.013)

    drive(app, [(390, price), (430, price), (490, price)], leader)
    # candle 360: mom = log(99610/99600) = +0.01% <= exit band -> CLOSE
    assert app.portfolio.position_size == 0.0
    assert len(app.portfolio.trades) == 2


def test_stop_loss_flattens_losing_short(app):
    price = 10_000_000.0
    leader = {0: 100000.0, 60: 100000.0, 120: 100000.0, 180: 100000.0,
              240: 99600.0, 300: 99500.0, 360: 99500.0, 420: 99500.0}
    drive(app, [(30, price), (90, price), (150, price), (210, price),
                (270, price), (330, price)], leader)
    assert app.portfolio.position_size == pytest.approx(-0.013)
    # price jumps +1% against the short -> protective stop (0.5%) must flatten
    drive(app, [(390, price * 1.01)], leader)
    assert app.portfolio.position_size == 0.0
    assert app.portfolio.realized_pnl_jpy < 0
