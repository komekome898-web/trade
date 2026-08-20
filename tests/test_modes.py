"""PAPER MODE / LIVE MODE gating (items 18-19)."""
from __future__ import annotations

import pytest

from bot.execution.live import LiveExecutor, LiveModeNotArmed
from bot.execution.paper import PaperExecutor
from bot.settings import (
    LIVE_ACK_PHRASE, Mode, ModeConfigError, RiskLimits, Secret, Settings, resolve_mode,
)

LIMITS = RiskLimits(3000, 6000, 300, 10.0, 1, 4, 5)


def make_settings(mode: Mode) -> Settings:
    return Settings(mode=mode, product_code="XRP_JPY", config={}, risk_limits=LIMITS)


# ---- mode resolution ------------------------------------------------------
def test_default_is_paper():
    assert resolve_mode({}, {}) is Mode.PAPER


def test_live_requires_env_and_ack():
    env = {"PAPER_MODE": "false", "LIVE_MODE": "true"}
    assert resolve_mode(env, {"live_mode_ack": LIVE_ACK_PHRASE}) is Mode.LIVE


def test_live_env_without_ack_refused():
    env = {"PAPER_MODE": "false", "LIVE_MODE": "true"}
    with pytest.raises(ModeConfigError):
        resolve_mode(env, {})


def test_ack_without_live_env_refused():
    # Half-armed configuration must not silently fall back to paper.
    with pytest.raises(ModeConfigError):
        resolve_mode({"PAPER_MODE": "true"}, {"live_mode_ack": LIVE_ACK_PHRASE})


def test_both_modes_true_refused():
    env = {"PAPER_MODE": "true", "LIVE_MODE": "true"}
    with pytest.raises(ModeConfigError):
        resolve_mode(env, {"live_mode_ack": LIVE_ACK_PHRASE})


def test_wrong_ack_phrase_refused():
    env = {"PAPER_MODE": "false", "LIVE_MODE": "true"}
    with pytest.raises(ModeConfigError):
        resolve_mode(env, {"live_mode_ack": "yes please"})


# ---- executor gating ------------------------------------------------------
def test_live_executor_refuses_paper_mode(client):
    with pytest.raises(LiveModeNotArmed):
        LiveExecutor(make_settings(Mode.PAPER), client)


def test_paper_mode_sends_zero_real_orders(fake_session):
    """The core PAPER guarantee: a full buy/sell cycle produces no HTTP calls."""
    quotes = {"XRP_JPY": (99.9, 100.1)}
    ex = PaperExecutor(quote_fn=lambda s: quotes[s], balance_jpy=6000.0)
    ex.submit_order(symbol="XRP_JPY", side="BUY", size=10.0, order_type="MARKET", price=None)
    ex.submit_order(symbol="XRP_JPY", side="SELL", size=10.0, order_type="MARKET", price=None)
    assert fake_session.calls == []          # no network traffic at all
    assert fake_session.order_calls() == []


def test_paper_fill_model_and_balance():
    ex = PaperExecutor(quote_fn=lambda s: (99.9, 100.1), balance_jpy=6000.0,
                       taker_fee_pct=0.15, slippage_pct=0.05)
    result = ex.submit_order(symbol="XRP_JPY", side="BUY", size=10.0,
                             order_type="MARKET", price=None)
    fill = ex.fills[0]
    assert fill.price == pytest.approx(100.1 * 1.0005)
    assert ex.positions["XRP_JPY"] == 10.0
    assert ex.balance_jpy < 6000.0
    status = ex.fetch_order_status(symbol="XRP_JPY", acceptance_id=result.acceptance_id)
    assert status.state == "COMPLETED"


def test_paper_rejects_overdraft():
    ex = PaperExecutor(quote_fn=lambda s: (99.9, 100.1), balance_jpy=100.0)
    with pytest.raises(ValueError, match="insufficient"):
        ex.submit_order(symbol="XRP_JPY", side="BUY", size=50.0,
                        order_type="MARKET", price=None)


def test_paper_rejects_selling_more_than_held():
    ex = PaperExecutor(quote_fn=lambda s: (99.9, 100.1), balance_jpy=6000.0)
    with pytest.raises(ValueError, match="position insufficient"):
        ex.submit_order(symbol="XRP_JPY", side="SELL", size=1.0,
                        order_type="MARKET", price=None)
