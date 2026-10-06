"""帳簿のツールの受け入れの場面 1・2・3・5・6(委任文 DELEGATION_one_road_step1.md)と、
直し 1 の批評家の場面(DELEGATION_one_road_step1_fix1.md 5.)。

損益・建玉・平均の建値は 10 進の文字列で、== で比べる(近似で比べない)。
"""
from __future__ import annotations

import re

import pytest

from bot.bt.costs import FxPoint, FxRates
from bot.bt.road import ledger as ledger_mod
from bot.bt.road.ledger import SUMMARY_KEYS, TRADE_KEYS, LedgerError, book, dec_str

M = 60_000_000_000  # 1 分(ns)
T0 = 1_700_000_040_000_000_000  # 分の区切り(0:00 とみなす)


def _f(minute, side, qty, px, ccy="JPY"):
    return {"t_ns": T0 + minute * M, "side": side, "qty": qty, "px": px, "ccy": ccy}


def _trade(first, last, levels, max_pos, hold, pnl, status):
    return {"first_t_ns": T0 + first * M, "last_t_ns": T0 + last * M, "levels": levels, "max_position": max_pos,
            "hold_ns": None if hold is None else hold * M, "pnl_jpy": pnl, "status": status}


def test_summary_shape():
    led = book([_f(0, "buy", 0.01, 10000)])
    assert tuple(led.summary) == SUMMARY_KEYS
    assert tuple(led.summary["trades"][0]) == TRADE_KEYS


def test_scene1_owner_example_L747():
    # 0.01 ずつ 10,200・10,100・10,000・9,900・9,800 で買い、0:10 に 0.05 を 10,100 で売る
    # 手計算: 平均の建値 = (102+101+100+99+98) ÷ 0.05 = 10,000、損益 = (10,100 − 10,000) × 0.05 = 5 円
    fills = [_f(k, "buy", 0.01, 10200 - 100 * k) for k in range(5)] + [_f(10, "sell", 0.05, 10100)]
    led = book(fills)
    assert [r["avg_px_after"] for r in led.fills] == ["10200", "10150", "10100", "10050", "10000", None]
    assert led.fills[4]["position_after"] == "0.05"
    assert led.fills[5]["position_after"] == "0"
    assert led.fills[5]["pnl_jpy"] == "5"
    assert led.summary == {"fill_count": 6, "closed_trades": 1, "pnl_jpy": "5", "open_trades": 0,
                           "trades": [_trade(0, 10, 5, "0.05", 10, "5", "closed")]}


def test_scene2_doten():
    # 手計算: 閉じる分 0.01 × (10,100 − 10,000) = 1 円。残り 売り 0.01 を 10,100 で建てる(途中)
    led = book([_f(0, "buy", 0.01, 10000), _f(5, "sell", 0.02, 10100)])
    assert led.summary == {"fill_count": 2, "closed_trades": 1, "pnl_jpy": "1", "open_trades": 1,
                           "trades": [_trade(0, 5, 1, "0.01", 5, "1", "closed"),
                                      _trade(5, 5, 1, "0.01", None, "0", "open")]}
    rest = led.trades[1]
    assert rest["direction"] == "short" and rest["position"] == "-0.01" and rest["avg_px"] == "10100"
    assert led.fills[1]["trade"] == 0 and led.fills[1]["opens_trade"] == 1


def test_scene3_partial_close():
    # 手計算: (10,200 − 10,000) × 0.01 = 2、(9,900 − 10,000) × 0.01 = −1、合計 1 円
    led = book([_f(0, "buy", 0.02, 10000), _f(3, "sell", 0.01, 10200), _f(6, "sell", 0.01, 9900)])
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "2", "-1"]
    assert [r["pnl_jpy_cum"] for r in led.fills] == ["0", "2", "1"]
    assert led.summary == {"fill_count": 3, "closed_trades": 1, "pnl_jpy": "1", "open_trades": 0,
                           "trades": [_trade(0, 6, 1, "0.02", 6, "1", "closed")]}


def test_scene5_open_at_end():
    led = book([_f(0, "buy", 0.01, 10000)])
    assert led.summary == {"fill_count": 1, "closed_trades": 0, "pnl_jpy": "0", "open_trades": 1,
                           "trades": [_trade(0, 0, 1, "0.01", None, "0", "open")]}


def test_open_trade_partial_pnl_not_in_sum():
    # 閉じた取引(+1)の後に、一部だけ決済した途中の取引(+3): 途中の分は合計に入らない
    led = book([_f(0, "buy", 0.01, 10000), _f(1, "sell", 0.01, 10100),
                _f(2, "buy", 0.02, 10000), _f(3, "sell", 0.01, 10300)])
    assert led.summary["pnl_jpy"] == "1"
    assert led.summary["closed_trades"] == 1 and led.summary["open_trades"] == 1
    assert led.summary["trades"][1] == _trade(2, 3, 1, "0.02", None, "3", "open")


@pytest.mark.parametrize("ccy", ["USD", "USDT"])
def test_scene6_usd_converted_at_trade_start(ccy):
    # 手計算: (30,100 − 30,000) × 0.01 = 1 USD、取引の開始(0:00)の USDJPY 150 → 150 円(L-763・L-764)。
    # 確定時(0:05)の 151 は使わない。
    fx = [FxPoint(time_ns=T0, pair="USDJPY", rate=150.0), FxPoint(time_ns=T0 + 5 * M, pair="USDJPY", rate=151.0)]
    fills = [_f(0, "buy", 0.01, 30000, ccy), _f(5, "sell", 0.01, 30100, ccy)]
    led = book(fills, fx)
    assert led.fills[1]["pnl_jpy"] == "150"
    assert led.summary == {"fill_count": 2, "closed_trades": 1, "pnl_jpy": "150", "open_trades": 0,
                           "trades": [_trade(0, 5, 1, "0.01", 5, "150", "closed")]}
    # {t_ns, pair, rate} の辞書の列・FxRates でも同じ
    as_rows = [{"t_ns": p.time_ns, "pair": p.pair, "rate": p.rate} for p in fx]
    assert book(fills, as_rows).summary == led.summary
    assert book(fills, FxRates(fx)).summary == led.summary


def test_usd_rates_not_round_numbers_exact():
    # 手計算: 0.02 を 60,000.5 で買い(取引の開始、USDJPY 149.37)、0.01 を 60,100.25(その時 150.11)・
    #   0.01 を 59,950.75(その時 148.93)で売る。1 つの取引なので両方とも開始の 149.37 で円に:
    #   0.01 × 99.75 × 149.37 = 148.996575、0.01 × (−49.75) × 149.37 = −74.311575、合計 74.685 円
    fx = [FxPoint(time_ns=T0, pair="USDJPY", rate=149.37), FxPoint(time_ns=T0 + 2 * M, pair="USDJPY", rate=150.11),
          FxPoint(time_ns=T0 + 4 * M, pair="USDJPY", rate=148.93)]
    led = book([_f(0, "buy", 0.02, 60000.5, "USD"), _f(2, "sell", 0.01, 60100.25, "USD"),
                _f(4, "sell", 0.01, 59950.75, "USD")], fx)
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "148.996575", "-74.311575"]
    assert led.summary["pnl_jpy"] == "74.685"


def test_usd_doten_new_trade_uses_rate_at_doten():
    # 0:00 に 0.01 を 30,000 USD で買い(USDJPY 150)、0:05 に 0.02 を 30,100 で売る(その時 151、ドテン)、
    # 0:08 に 0.01 を 30,000 で買い戻す(その時 152)。
    # 手計算: 閉じた側 = 1 USD × 150(1 つ目の取引の開始)= 150 円。新しい売りの取引 = 1 USD × 151(ドテンの約定 = 開始)
    #   = 151 円。合計 301 円(確定時の相場なら 151 + 152 = 303 円)。
    fx = [FxPoint(time_ns=T0, pair="USDJPY", rate=150.0), FxPoint(time_ns=T0 + 5 * M, pair="USDJPY", rate=151.0),
          FxPoint(time_ns=T0 + 8 * M, pair="USDJPY", rate=152.0)]
    led = book([_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.02, 30100, "USD"),
                _f(8, "buy", 0.01, 30000, "USD")], fx)
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "150", "151"]
    assert led.summary["pnl_jpy"] == "301"
    assert led.summary["closed_trades"] == 2 and led.summary["open_trades"] == 0


def test_usd_rate_needed_at_trade_start():
    # 確定の時刻(0:05)には相場があっても、取引の開始(0:00)の時刻以前に相場が無ければ止まる(1 とみなさない)
    fills = [_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.01, 30100, "USD")]
    after_start = [FxPoint(time_ns=T0 + 1 * M, pair="USDJPY", rate=150.0)]
    with pytest.raises(LedgerError, match="約定 0.*始まる取引.*USDJPY の相場が無い"):
        book(fills, after_start)


def test_usd_without_rate_stops_in_japanese():
    fills = [_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.01, 30100, "USD")]
    with pytest.raises(LedgerError, match="USDJPY の相場が渡されていない"):
        book(fills)
    # 確定時刻より後の相場しか無いときも止まる(1 とみなさない。取引の開始の時刻にも相場が無い)
    late = [FxPoint(time_ns=T0 + 6 * M, pair="USDJPY", rate=151.0)]
    with pytest.raises(LedgerError, match="USDJPY の相場が無い"):
        book(fills, late)
    # 逆向きの組(JPYUSD)だけでは止まる(帳簿は USDJPY だけを使う)
    inv = [FxPoint(time_ns=T0, pair="JPYUSD", rate=1 / 150)]
    with pytest.raises(LedgerError, match="USDJPY の相場が無い"):
        book(fills, inv)


def test_bad_fx_rows_stop_in_japanese():
    fills = [_f(0, "buy", 0.01, 30000, "USD"), _f(5, "sell", 0.01, 30100, "USD")]
    with pytest.raises(LedgerError, match="為替の 0 行目が読めない"):
        book(fills, [{"t_ns": T0, "pair": "usdjpy", "rate": 150.0}])
    with pytest.raises(LedgerError, match="為替の 0 行目"):
        book(fills, [{"t_ns": T0, "rate": 150.0}])


# ---- 直し 1 の批評家の場面 ----

def test_critic_add_partial_add_close_total_4():
    # 0.01@10,000 + 0.01@10,200(平均 10,100)→ 0.01 を 10,300 で売る: (10,300 − 10,100) × 0.01 = 2
    # → 0.01@10,000 を足す(平均 (101 + 100) ÷ 0.02 = 10,050)→ 0.02 を 10,150 で売る: 100 × 0.02 = 2 → 合計 4 円
    led = book([_f(0, "buy", 0.01, 10000), _f(1, "buy", 0.01, 10200), _f(2, "sell", 0.01, 10300),
                _f(3, "buy", 0.01, 10000), _f(4, "sell", 0.02, 10150)])
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "0", "2", "0", "2"]
    assert [r["avg_px_after"] for r in led.fills] == ["10000", "10100", "10100", "10050", None]
    assert led.summary == {"fill_count": 5, "closed_trades": 1, "pnl_jpy": "4", "open_trades": 0,
                           "trades": [_trade(0, 4, 3, "0.02", 4, "4", "closed")]}


def test_critic_doten_add_close_two_trades_total_5():
    # 0.01@10,000 買い → 0.03 を 10,100 で売る(ドテン: 閉じる 0.01 で +1、売り 0.02 を 10,100 で建てる)
    # → 0.01 を 10,200 で売り足す(売り 0.03、原価 202 + 102 = 304)→ 0.03 を 10,000 で買い戻す: 304 − 300 = 4
    # 閉じた取引 2、合計 5 円
    led = book([_f(0, "buy", 0.01, 10000), _f(5, "sell", 0.03, 10100), _f(7, "sell", 0.01, 10200),
                _f(9, "buy", 0.03, 10000)])
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "1", "0", "4"]
    assert led.fills[2]["avg_px_after"] == "10133.333333333333"  # 304 ÷ 0.03(割り切れないので 1e-12 の位で丸めた表示)
    assert led.summary == {"fill_count": 4, "closed_trades": 2, "pnl_jpy": "5", "open_trades": 0,
                           "trades": [_trade(0, 5, 1, "0.01", 5, "1", "closed"),
                                      _trade(5, 9, 2, "0.03", 4, "4", "closed")]}


def test_critic_two_adds_same_ns_close_at_10020_is_exactly_zero():
    # 0.01@10,000 と 0.02@10,030 を同じ ns に(平均 (100 + 200.6) ÷ 0.03 = 10,020)→ 0.03 を 10,020 で売る: ちょうど 0
    led = book([_f(0, "buy", 0.01, 10000), _f(0, "buy", 0.02, 10030), _f(1, "sell", 0.03, 10020)])
    assert led.fills[1]["avg_px_after"] == "10020"
    assert led.fills[2]["pnl_jpy"] == "0"
    assert led.summary == {"fill_count": 3, "closed_trades": 1, "pnl_jpy": "0", "open_trades": 0,
                           "trades": [_trade(0, 1, 2, "0.03", 1, "0", "closed")]}


def test_critic_three_partial_closes_exactly_3():
    # 0.03@10,000 を 0.01 ずつ 3 回 10,100 で決済: 1 + 1 + 1 = ちょうど 3 円
    led = book([_f(0, "buy", 0.03, 10000)] + [_f(1 + k, "sell", 0.01, 10100) for k in range(3)])
    assert [r["pnl_jpy"] for r in led.fills] == ["0", "1", "1", "1"]
    assert [r["position_after"] for r in led.fills] == ["0.03", "0.02", "0.01", "0"]
    assert led.summary == {"fill_count": 4, "closed_trades": 1, "pnl_jpy": "3", "open_trades": 0,
                           "trades": [_trade(0, 3, 1, "0.03", 3, "3", "closed")]}


def test_critic_three_buys_of_0_1_sell_0_3_exactly_15():
    # 0.1@10,000 を 3 回 → 0.3 を 10,050 で売る: 50 × 0.3 = ちょうど 15 円(浮動小数の 0.1 × 3 の誤差を持ち込まない)
    led = book([_f(k, "buy", 0.1, 10000) for k in range(3)] + [_f(3, "sell", 0.3, 10050)])
    assert [r["position_after"] for r in led.fills] == ["0.1", "0.2", "0.3", "0"]
    assert led.summary == {"fill_count": 4, "closed_trades": 1, "pnl_jpy": "15", "open_trades": 0,
                           "trades": [_trade(0, 3, 3, "0.3", 3, "15", "closed")]}


def test_repeating_average_two_partial_closes_exactly_zero():
    # 0.01@10,000 + 0.02@10,001(平均 300.02 ÷ 0.03 = 10,000.666…、割り切れない)
    # → 0.01 を 10,000 で売る(−0.00666…)→ 0.02 を 10,001 で売る(+0.00666…): 取引の合計はちょうど 0
    # (Decimal を桁で丸めて計算すると合計が 0 にならない形。分数で計算しているので 0)
    led = book([_f(0, "buy", 0.01, 10000), _f(1, "buy", 0.02, 10001), _f(2, "sell", 0.01, 10000),
                _f(3, "sell", 0.02, 10001)])
    assert led.fills[2]["pnl_jpy"] == "-0.006666666667" and led.fills[3]["pnl_jpy"] == "0.006666666667"
    assert led.fills[3]["pnl_jpy_cum"] == "0"
    assert led.summary["pnl_jpy"] == "0" and led.summary["trades"][0]["pnl_jpy"] == "0"


def test_critic_qty_off_the_0_001_step_is_refused():
    with pytest.raises(LedgerError, match="0.001 BTC の刻みでない"):
        book([_f(0, "buy", 0.0105, 10000)])
    with pytest.raises(LedgerError, match="0.001 BTC の刻みでない"):
        book([_f(0, "buy", 0.01, 10000), _f(1, "sell", 0.0105, 10000)])


def test_cross_check_with_account_stops_on_disagreement(monkeypatch):
    # 口座の計算と 1e-6 円より離れたら止まる(突き合わせが効いている印: 口座の確定損益を 1e-5 円ずらす)
    real = ledger_mod.MarginAccount.apply_fill

    def shifted(self, fill):
        real(self, fill)
        if fill.side == "sell":
            self.realized_account += 1e-5

    monkeypatch.setattr(ledger_mod.MarginAccount, "apply_fill", shifted)
    with pytest.raises(LedgerError, match="2 つの計算が合わない"):
        book([_f(0, "buy", 0.01, 10000), _f(1, "sell", 0.01, 10100)])


def test_dec_str():
    from fractions import Fraction
    assert dec_str(Fraction(0)) == "0" and dec_str(Fraction(-0)) == "0"
    assert dec_str(Fraction(500)) == "500" and dec_str(Fraction(-1)) == "-1"
    assert dec_str(Fraction(1, 20)) == "0.05" and dec_str(Fraction(1, 3)) == "0.333333333333"
    assert dec_str(Fraction(-1, 3)) == "-0.333333333333" and dec_str(Fraction(1, 10 ** 13)) == "0.0000000000001"
    assert dec_str(Fraction(1, 3 * 10 ** 13)) == "0"  # 表せない値を 1e-12 の位で丸めて 0
    # 桁の多い値も丸めない(Decimal の文脈の 28 桁で丸めない)
    assert dec_str(Fraction(10 ** 30 + 1, 10 ** 5)) == "10000000000000000000000000.00001"
    assert dec_str(None) is None


@pytest.mark.parametrize("fills", [
    [_f(1, "buy", 0.01, 1.0), _f(0, "sell", 0.01, 1.0)],  # 時刻が戻る
    [_f(0, "buy", 0.01, 1.0, "JPY"), _f(1, "sell", 0.01, 1.0, "USD")],  # 通貨が混ざる
    [_f(0, "hold", 0.01, 1.0)],
    [_f(0, "buy", 0.0, 1.0)],
    [_f(0, "buy", 0.01, -1.0)],
    [_f(0, "buy", 0.01, 1.0, "EUR")],
])
def test_refuses(fills):
    with pytest.raises(LedgerError) as ei:
        book(fills)
    assert re.search(r"[぀-ヿ一-鿿]", str(ei.value))  # 文は日本語


# 批評家 2 回目の指摘 4: 口座との突き合わせが、大きな累計の後の正しい入力を拒まない
def test_cross_check_tolerates_float_error_after_large_cumulative():
    from bot.bt.road.ledger import book
    M = 60_000_000_000
    T = 1_700_000_040_000_000_000
    fills = []
    t = T
    for _ in range(20):  # 100 BTC を 1,000 万円で建てて 6,000 万円で閉じるのを繰り返し、累計を 1e11 円にする
        fills.append({"t_ns": t, "side": "buy", "qty": 100.0, "px": 10_000_000, "ccy": "JPY"}); t += M
        fills.append({"t_ns": t, "side": "sell", "qty": 100.0, "px": 60_000_000, "ccy": "JPY"}); t += M
    fills.append({"t_ns": t, "side": "buy", "qty": 0.003, "px": 10_000_001, "ccy": "JPY"}); t += M
    fills.append({"t_ns": t, "side": "sell", "qty": 0.003, "px": 10_000_002, "ccy": "JPY"})
    out = book(fills)
    assert out.summary["trades"][-1]["pnl_jpy"] == "0.003"
