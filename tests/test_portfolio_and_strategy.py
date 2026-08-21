"""Portfolio accounting, strategy behavior on insufficient/missing data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.portfolio.portfolio import Portfolio
from bot.strategy import STRATEGIES
from bot.strategy.base import SignalType


def test_portfolio_round_trip_pnl():
    p = Portfolio(6000.0, clock=lambda: 1000.0)
    p.on_fill(symbol="XRP_JPY", side="BUY", size=10.0, price=100.0, fee_jpy=1.5)
    assert p.position_size == 10.0
    assert p.avg_entry_price == 100.0
    realized = p.on_fill(symbol="XRP_JPY", side="SELL", size=10.0, price=110.0, fee_jpy=1.65)
    assert realized == pytest.approx(100.0 - 1.65)
    assert p.position_size == 0.0
    assert p.realized_pnl_jpy == pytest.approx(100.0 - 1.5 - 1.65)


def test_consecutive_losses_tracked():
    p = Portfolio(6000.0, clock=lambda: 1000.0)
    for _ in range(3):
        p.on_fill(symbol="X", side="BUY", size=1.0, price=100.0)
        p.on_fill(symbol="X", side="SELL", size=1.0, price=90.0)
    assert p.consecutive_losses == 3
    p.on_fill(symbol="X", side="BUY", size=1.0, price=100.0)
    p.on_fill(symbol="X", side="SELL", size=1.0, price=120.0)
    assert p.consecutive_losses == 0


def test_drawdown_from_peak():
    p = Portfolio(1000.0, clock=lambda: 1000.0)
    p.on_fill(symbol="X", side="BUY", size=10.0, price=10.0)
    assert p.drawdown_pct(12.0) == pytest.approx(0.0)   # equity 1020 = new peak
    dd = p.drawdown_pct(9.0)                            # equity 990 vs peak 1020
    assert dd == pytest.approx((1020 - 990) / 1020 * 100)


def test_daily_pnl_resets_on_new_day():
    now = [86400.0 * 10]
    p = Portfolio(6000.0, clock=lambda: now[0])
    p.on_fill(symbol="X", side="BUY", size=1.0, price=100.0)
    p.on_fill(symbol="X", side="SELL", size=1.0, price=90.0)
    assert p.daily_pnl_jpy(mark_price=90.0) == pytest.approx(-10.0)
    now[0] += 86400  # next day
    assert p.daily_pnl_jpy(mark_price=90.0) == pytest.approx(0.0)
    assert p.realized_pnl_jpy == pytest.approx(-10.0)  # cumulative unaffected


def test_daily_unrealized_is_measured_from_the_entry_of_a_position_opened_today():
    """Unchanged semantics for a same-day trade: the anchor IS the entry."""
    p = Portfolio(1000.0, clock=lambda: 86400.0 * 10)
    p.on_fill(symbol="X", side="BUY", size=10.0, price=100.0)
    assert p.daily_mark_price == pytest.approx(100.0)
    assert p.daily_pnl_jpy(mark_price=97.0) == pytest.approx(-30.0)


def test_daily_unrealized_re_anchors_at_the_utc_rollover():
    """A position held across midnight starts the new day flat: yesterday's
    open loss was charged to yesterday's MAX_DAILY_LOSS_JPY budget and must not
    be charged again to today's."""
    now = [86400.0 * 10]
    p = Portfolio(1000.0, clock=lambda: now[0])
    p.on_fill(symbol="X", side="BUY", size=10.0, price=100.0)
    assert p.daily_pnl_jpy(mark_price=90.0) == pytest.approx(-100.0)
    now[0] += 86400
    assert p.daily_pnl_jpy(mark_price=90.0) == pytest.approx(0.0)   # re-anchored
    assert p.daily_pnl_jpy(mark_price=85.0) == pytest.approx(-50.0)  # today's move
    assert p.unrealized_pnl_jpy(85.0) == pytest.approx(-150.0)      # total intact


def test_anchor_boot_equity_marks_a_restored_position_to_market():
    """The drawdown peak of a restored book is its MARK-TO-MARKET boot equity,
    so an inherited open loss is not an instant MAX_DRAWDOWN breach; what the
    check measures is deterioration since this boot."""
    p = Portfolio(1000.0, clock=lambda: 86400.0 * 10)
    p.realized_pnl_jpy = -100.0
    p.position_size, p.avg_entry_price = 10.0, 100.0
    p.anchor_boot_equity()

    assert p.drawdown_pct(90.0) == 0.0                  # boot equity 800 = peak
    assert p.equity_peak_jpy == pytest.approx(800.0)
    assert p.daily_pnl_jpy(mark_price=90.0) == pytest.approx(0.0)
    assert p.drawdown_pct(88.0) == pytest.approx((800 - 780) / 800 * 100)
    assert p.daily_pnl_jpy(mark_price=88.0) == pytest.approx(-20.0)


def test_seeding_the_daily_figure_is_refused_once_the_day_has_turned():
    now = [86400.0 * 10]
    p = Portfolio(1000.0, clock=lambda: now[0])
    day = p.daily_day_index
    now[0] += 86400                    # midnight, between the caller's read and
    p.seed_daily_realized(-500.0, day=day)             # the seed
    assert p.daily_pnl_jpy(mark_price=100.0) == 0.0
    p.seed_daily_realized(-500.0, day=p.daily_day_index)
    assert p.daily_pnl_jpy(mark_price=100.0) == pytest.approx(-500.0)


def make_candles(n=100, seed=1):
    rng = np.random.default_rng(seed)
    p = 100 + rng.normal(0, 0.5, n).cumsum()
    return pd.DataFrame({"open": p, "high": p * 1.001, "low": p * 0.999,
                         "close": p, "volume": np.ones(n)})


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategies_hold_on_insufficient_history(name):
    strat = STRATEGIES[name]({})
    signal = strat.on_candles(make_candles(3))
    assert signal.type is SignalType.HOLD


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategies_hold_on_missing_data(name):
    candles = make_candles(60)
    candles.loc[55:, ["close", "high", "low"]] = np.nan  # data gap at the end
    strat = STRATEGIES[name]({})
    signal = strat.on_candles(candles)
    assert signal.type is SignalType.HOLD  # never trade through a data gap


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_strategies_return_indicator_values(name):
    strat = STRATEGIES[name]({})
    candles = make_candles(200)
    candles["leader_close"] = candles["close"]  # for cross-exchange strategies
    candles["buy_vol"] = candles["volume"] / 2  # for order-flow strategies
    candles["sell_vol"] = candles["volume"] / 2
    signal = strat.on_candles(candles)
    assert isinstance(signal.indicators, dict) and signal.indicators
    assert signal.reason
