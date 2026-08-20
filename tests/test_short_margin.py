"""Short-selling and margin-carry behavior in the engine, portfolio and paper executor."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.portfolio.portfolio import Portfolio
from bot.products import load_products
from bot.strategy.base import Signal, SignalType, Strategy

NO_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0)


def make_candles(prices):
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame({"open": p, "high": p * 1.001, "low": p * 0.999,
                         "close": p, "volume": np.ones_like(p)})


class Scripted(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.script = params["script"]

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        sig = self.script.get(len(candles) - 1)
        return Signal(sig, "scripted") if sig else Signal(SignalType.HOLD, "")


def test_short_profits_when_price_falls():
    prices = [100.0] * 3 + [100.0, 100.0, 90.0, 90.0, 90.0]
    strat = Scripted({"script": {2: SignalType.SELL, 5: SignalType.BUY}})
    res = run_backtest(strat, make_candles(prices), costs=NO_COST,
                       allow_short=True, order_notional_jpy=3000)
    assert len(res.trade_pnls) == 1
    # short 30 units @100, cover @90 -> +300
    assert res.trade_pnls[0] == pytest.approx(3000 / 100 * 10, rel=1e-3)
    opens = [t for t in res.trade_log if t["side"] == "OPEN_SHORT"]
    assert len(opens) == 1


def test_sell_without_short_permission_is_noop():
    prices = [100.0] * 8
    strat = Scripted({"script": {2: SignalType.SELL}})
    res = run_backtest(strat, make_candles(prices), costs=NO_COST, allow_short=False)
    assert res.trade_pnls == []
    assert all(not t["side"].startswith("OPEN") for t in res.trade_log)


def test_swap_carry_reduces_pnl():
    prices = [100.0] * 20
    strat = Scripted({"script": {2: SignalType.BUY, 15: SignalType.SELL}})
    res = run_backtest(strat, make_candles(prices), costs=NO_COST,
                       allow_short=True, swap_daily_pct=0.04,
                       bar_seconds=86400 / 4, order_notional_jpy=3000)
    # held ~12 bars of 6h each = ~3 days of 0.04%/day on 3000 = ~3.6 JPY
    assert res.trade_pnls[0] < 0
    assert res.trade_pnls[0] == pytest.approx(-3000 * 0.0004 * 3, rel=0.35)


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


def test_close_signal_flattens_long_and_short():
    prices = [100.0] * 10
    strat = Scripted({"script": {2: SignalType.SELL, 5: SignalType.CLOSE}})
    res = run_backtest(strat, make_candles(prices), costs=NO_COST, allow_short=True)
    assert len(res.trade_pnls) == 1  # short opened then flattened by CLOSE
    assert [t["side"] for t in res.trade_log] == ["OPEN_SHORT", "CLOSE_SHORT"]


def test_close_signal_when_flat_is_noop():
    prices = [100.0] * 8
    strat = Scripted({"script": {2: SignalType.CLOSE}})
    res = run_backtest(strat, make_candles(prices), costs=NO_COST, allow_short=True)
    assert res.trade_log == [] and res.trade_pnls == []


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
    too_small = fx_checker.check(OrderRequest("FX_BTC_JPY", "BUY", 0.005, 10_000_000,
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
    assert fx.min_size == pytest.approx(0.01)
    assert fx.leverage == pytest.approx(2.0)
    spot = products["XRP_JPY"]
    assert not spot.shortable and not spot.is_margin
