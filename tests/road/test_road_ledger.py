"""帳簿のツールの受け入れの場面 1・2・3・5・6(委任文 DELEGATION_one_road_step1.md)。"""
from __future__ import annotations

import pytest

from bot.bt.costs import FxPoint, FxRateMissingError, FxRates
from bot.bt.road.ledger import LedgerError, book

M = 60_000_000_000  # 1 分(ns)
T0 = 1_700_000_040_000_000_000  # 分の区切り(0:00 とみなす)


def _f(minute, side, qty, px, ccy="JPY"):
    return {"t_ns": T0 + minute * M, "side": side, "qty": qty, "px": px, "ccy": ccy}


def test_scene1_owner_example_L747():
    fills = [_f(k, "buy", 0.01, 10200 - 100 * k) for k in range(5)] + [_f(10, "sell", 0.05, 10100)]
    led = book(fills)
    assert led.fills[4]["avg_px_after"] == pytest.approx(10000, abs=1e-9)  # 平均の建値 10,000 円
    assert led.fills[4]["position_after"] == pytest.approx(0.05, abs=1e-12)
    assert led.fills[5]["position_after"] == 0.0
    assert led.fills[5]["pnl_jpy"] == pytest.approx(5, abs=1e-6)
    assert len(led.trades) == 1
    tr = led.trades[0]
    assert tr["status"] == "closed"
    assert tr["levels"] == 5
    assert tr["hold_ns"] == 10 * M  # 保有 10 分
    assert tr["max_position"] == pytest.approx(0.05, abs=1e-12)
    assert led.summary["closed_trades"] == 1
    assert led.summary["open_trades"] == 0
    assert led.summary["pnl_jpy"] == pytest.approx(5, abs=1e-6)


def test_scene2_doten():
    led = book([_f(0, "buy", 0.01, 10000), _f(5, "sell", 0.02, 10100)])
    assert led.summary == {"closed_trades": 1, "pnl_jpy": 1.0, "open_trades": 1}
    closed, rest = led.trades
    assert closed["status"] == "closed" and closed["pnl_jpy"] == 1.0 and closed["hold_ns"] == 5 * M
    assert closed["levels"] == 1
    assert rest["status"] == "open" and rest["direction"] == "short"
    assert rest["position"] == -0.01 and rest["avg_px"] == 10100.0  # 売り 0.01、建値 10,100
    assert rest["first_t_ns"] == T0 + 5 * M and rest["levels"] == 1 and rest["hold_ns"] is None
    assert led.fills[1]["trade"] == 0 and led.fills[1]["opens_trade"] == 1


def test_scene3_partial_close():
    led = book([_f(0, "buy", 0.02, 10000), _f(3, "sell", 0.01, 10200), _f(6, "sell", 0.01, 9900)])
    assert [r["pnl_jpy"] for r in led.fills] == [0.0, 2.0, -1.0]
    assert led.summary == {"closed_trades": 1, "pnl_jpy": 1.0, "open_trades": 0}
    assert led.trades[0]["hold_ns"] == 6 * M
    assert led.trades[0]["levels"] == 1


def test_scene5_open_at_end():
    led = book([_f(0, "buy", 0.01, 10000)])
    assert led.summary == {"closed_trades": 0, "pnl_jpy": 0.0, "open_trades": 1}
    assert led.trades[0]["status"] == "open" and led.trades[0]["hold_ns"] is None


def test_open_trade_partial_pnl_not_in_sum():
    # 閉じた取引の後に、一部だけ決済した途中の取引: 途中の分は合計に入らない
    led = book([_f(0, "buy", 0.01, 10000), _f(1, "sell", 0.01, 10100),
                _f(2, "buy", 0.02, 10000), _f(3, "sell", 0.01, 10300)])
    assert led.summary == {"closed_trades": 1, "pnl_jpy": 1.0, "open_trades": 1}
    assert led.trades[1]["pnl_jpy"] == 3.0 and led.trades[1]["status"] == "open"


@pytest.mark.parametrize("ccy", ["USD", "USDT"])
def test_scene6_usd_converted_at_close_time(ccy):
    fx = [FxPoint(time_ns=T0, pair="USDJPY", rate=150.0), FxPoint(time_ns=T0 + 5 * M, pair="USDJPY", rate=151.0)]
    led = book([_f(0, "buy", 0.01, 30000, ccy), _f(5, "sell", 0.01, 30100, ccy)], fx)
    assert led.fills[1]["pnl_jpy"] == 151.0  # +1 USD × 151
    assert led.summary == {"closed_trades": 1, "pnl_jpy": 151.0, "open_trades": 0}
    # {t_ns, pair, rate} の辞書の列・FxRates でも同じ
    as_rows = [{"t_ns": p.time_ns, "pair": p.pair, "rate": p.rate} for p in fx]
    assert book([_f(0, "buy", 0.01, 30000, ccy), _f(5, "sell", 0.01, 30100, ccy)], as_rows).summary == led.summary
    assert book([_f(0, "buy", 0.01, 30000, ccy), _f(5, "sell", 0.01, 30100, ccy)], FxRates(fx)).summary == led.summary


def test_usd_without_rate_stops():
    with pytest.raises(FxRateMissingError):
        book([_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.01, 30100, "USD")])
    # 確定時刻より後の相場しか無いときも止まる(1 とみなさない)
    late = [FxPoint(time_ns=T0 + 6 * M, pair="USDJPY", rate=151.0)]
    with pytest.raises(FxRateMissingError):
        book([_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.01, 30100, "USD")], late)


@pytest.mark.parametrize("fills", [
    [_f(1, "buy", 0.01, 1.0), _f(0, "sell", 0.01, 1.0)],  # 時刻が戻る
    [_f(0, "buy", 0.01, 1.0, "JPY"), _f(1, "sell", 0.01, 1.0, "USD")],  # 通貨が混ざる
    [_f(0, "hold", 0.01, 1.0)],
    [_f(0, "buy", 0.0, 1.0)],
    [_f(0, "buy", 0.01, -1.0)],
    [_f(0, "buy", 0.01, 1.0, "EUR")],
])
def test_refuses(fills):
    with pytest.raises(LedgerError):
        book(fills)
