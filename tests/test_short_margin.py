"""Short-selling behaviour of the portfolio, the paper executor, the risk checker and the product registry
(the bar engine's short / carry rules R-T3 / R-T4 / R-S1 are held by tests/bt/battery/item_4 and tests/bt/item_4)."""
from __future__ import annotations

import pytest

from bot.portfolio.portfolio import Portfolio
from bot.products import load_products

def test_portfolio_short_round_trip():
    p = Portfolio(100000.0, clock=lambda: 1000.0)
    p.on_fill(symbol="FX_BTC_JPY", side="SELL", size=0.01, price=10_000_000, fee_jpy=0.0)
    assert p.position_size == pytest.approx(-0.01)
    assert p.unrealized_pnl_jpy(9_900_000) == pytest.approx(1000.0)  # short gains on drop
    realized = p.on_fill(symbol="FX_BTC_JPY", side="BUY", size=0.01, price=9_900_000)
    assert realized == pytest.approx(1000.0)
    assert p.position_size == 0.0
    assert p.consecutive_losses == 0


def test_portfolio_short_loss_counts_consecutive():
    p = Portfolio(100000.0, clock=lambda: 1000.0)
    p.on_fill(symbol="X", side="SELL", size=1.0, price=100.0)
    p.on_fill(symbol="X", side="BUY", size=1.0, price=110.0)  # short loses on rise
    assert p.realized_pnl_jpy == pytest.approx(-10.0)
    assert p.consecutive_losses == 1


def test_paper_margin_short_round_trip():
    from bot.execution.paper import PaperExecutor
    quotes = {"FX_BTC_JPY": (9_999_000.0, 10_001_000.0)}
    ex = PaperExecutor(quote_fn=lambda s: quotes[s], balance_jpy=200000.0,
                       taker_fee_pct=0.0, slippage_pct=0.0,
                       allow_short=True, leverage=2.0)
    ex.submit_order(symbol="FX_BTC_JPY", side="SELL", size=0.01,
                    order_type="MARKET", price=None)
    assert ex.positions["FX_BTC_JPY"] == pytest.approx(-0.01)
    quotes["FX_BTC_JPY"] = (9_899_000.0, 9_901_000.0)   # price fell 100k
    ex.submit_order(symbol="FX_BTC_JPY", side="BUY", size=0.01,
                    order_type="MARKET", price=None)
    assert ex.positions["FX_BTC_JPY"] == 0.0
    # short @ bid 9,999,000, cover @ ask 9,901,000 -> +980 JPY on 0.01 BTC
    assert ex.balance_jpy == pytest.approx(200000.0 + 980.0)


def test_paper_margin_leverage_cap():
    from bot.execution.paper import PaperExecutor
    ex = PaperExecutor(quote_fn=lambda s: (9_999_000.0, 10_001_000.0),
                       balance_jpy=50000.0, taker_fee_pct=0.0,
                       allow_short=True, leverage=2.0)
    with pytest.raises(ValueError, match="margin insufficient"):
        ex.submit_order(symbol="FX_BTC_JPY", side="BUY", size=0.02,  # ~200k > 50k x2
                        order_type="MARKET", price=None)


def test_risk_checker_product_rules(tmp_path):
    from bot.risk.kill_switch import KillSwitch
    from bot.risk.pre_trade_checks import AccountState, OrderRequest, PreTradeChecker
    from bot.settings import RiskLimits
    limits = RiskLimits(130000, 130000, 6000, 10.0, 1, 5, 5)
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    products = load_products("/home/user/trade")

    fx_checker = PreTradeChecker(limits, ks, product=products["FX_BTC_JPY"])
    account = AccountState(balance_jpy=200000, position_notional_jpy=0, open_orders=0,
                           daily_pnl_jpy=0, drawdown_pct=0, consecutive_losses=0)
    ok = fx_checker.check(OrderRequest("FX_BTC_JPY", "SELL", 0.01, 10_000_000,
                                       stop_price=10_050_000), account)
    assert ok.approved  # short entry allowed on FX
    too_small = fx_checker.check(OrderRequest("FX_BTC_JPY", "BUY", 0.0005, 10_000_000,
                                              stop_price=9_950_000), account)
    assert not too_small.approved and any("below product minimum" in r for r in too_small.reasons)

    spot_checker = PreTradeChecker(limits, ks, product=products["XRP_JPY"])
    short_spot = spot_checker.check(OrderRequest("XRP_JPY", "SELL", 10, 100,
                                                 stop_price=101), account)
    assert not short_spot.approved and any("not shortable" in r for r in short_spot.reasons)


def test_products_registry():
    products = load_products("/home/user/trade")
    fx = products["FX_BTC_JPY"]
    assert fx.shortable and fx.is_margin
    assert fx.taker_fee_pct == 0.0
    assert fx.min_size == pytest.approx(0.001)
    assert fx.leverage == pytest.approx(2.0)
    spot = products["XRP_JPY"]
    assert not spot.shortable and not spot.is_margin
