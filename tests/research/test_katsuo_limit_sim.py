"""カード 2 の指値の再現(katsuo_v03 を 1 分足で。src/bot/research/katsuo_limit_sim.py)の試験。

仕様: docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/SPEC.md。手で作った小さな足の並びで、仕様の各節の規則を確かめる。
入力の作り方: bitFlyer の 1 分足は値段 P = 1,000,000 円の近く、海外の 1 分足は Q = 10,000 ドルの近く(1 bp = 1 ドル)。
多くの試験は foot_min = 1(海外の 1 分足 1 本 = 合図の足 1 本)。分 i の海外の行(open_time = T0 + i 分)は
T0 + (i+1) 分に使えるので、その合図の注文は分 i+1 の bitFlyer の足から約定を見る。P1・X = 分 i の bitFlyer の終値。
数字は試験の入力で、データではない。
"""
from __future__ import annotations

import math
import random

import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import run_card
from bot.research.cards.library.c2_owner_xvenue_wick import ROW_LAG_NS, SERIES_SPOT, C2OwnerXvenueWick
from bot.research.katsuo_limit_sim import (EXIT_CLOSE, EXIT_DOTEN, EXIT_END, EXIT_LIMIT, EXIT_SL1, EXIT_SL2, EXIT_SM,
                                           STRONG, WEAK, XSIG_LINE, XSIG_WEAK, KatsuoLimitSim, action, k1_signal,
                                           tercile, tick_down, tick_up)

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z。試験の時刻で、データではない
P = 1_000_000.0
Q = 10_000.0

# 海外の足の形 (始値, 高値, 安値, 終値)
BUY = (Q, Q + 10, Q - 30, Q + 10)  # 陽線 × 下ヒゲ 30 bp(19・24 の両方の枝)→ 買い。先端 Q − 30
BUY_SMALL = (Q, Q + 10, Q - 20, Q + 10)  # 陽線 × 下ヒゲ 20 bp(19 の枝だけ)→ 買い
SELL = (Q, Q + 30, Q - 10, Q - 10)  # 陰線 × 上ヒゲ → 売り。先端 Q + 30
UPB = (Q, Q + 40, Q, Q + 10)  # 陽線 × 上ヒゲ → 買い持ちなら降りる、それ以外は売り
DNB = (Q, Q, Q - 40, Q - 10)  # 陰線 × 下ヒゲ → 売り持ちなら降りる、それ以外は買い
FLAT = (Q, Q, Q, Q)  # 同値足(何もしない)

R_BUY = 40 / (Q + 10)  # BUY の先端までの比 |終値 − 先端| / 終値
R_SELL = 40 / (Q - 10)


def bar(i, o=P, h=None, lo=None, c=None, vol=1.0, t0=T0):
    c = o if c is None else c
    h = max(o, c) if h is None else h
    lo = min(o, c) if lo is None else lo
    return BarEvent(received_time_ns=t0 + (i + 1) * M, exchange_time_ns=t0 + (i + 1) * M,
                    start_time_ns=t0 + i * M, open=o, high=h, low=lo, close=c, volume=vol)


def sim(**kw):
    kw.setdefault("fill_side", "good")
    kw.setdefault("at_max", "skip")
    kw.setdefault("foot_min", 1)
    return KatsuoLimitSim(**kw)


def step(s, i, o=P, h=None, lo=None, c=None, ref=None, vol=1.0):
    """分 i: 海外の行(あれば)を渡してから、bitFlyer の足 i を渡す。"""
    if ref is not None:
        s.add_refs([(T0 + i * M, *ref)])
    return s.feed(bar(i, o, h, lo, c, vol))


def orders(s):
    return [(o.kind, o.side, o.qty, o.price, o.trig, o.armed) for o in s._orders]


def long_half(s, ref=BUY):
    """分 0 に買いの合図、分 1 に注文、分 2 に 1 本目が P で約定 → 買い 0.5(建値 P)。次の分の番号を返す。"""
    step(s, 0, ref=ref)
    step(s, 1)
    step(s, 2, lo=P - 1)
    assert s._pos == 0.5 and s._trade["avg"] == P
    return 3


def short_half(s):
    step(s, 0, ref=SELL)
    step(s, 1)
    step(s, 2, h=P + 1)
    assert s._pos == -0.5 and s._trade["avg"] == P
    return 3


def exit_prices(x, c_ov, d):
    """降りる 4 本の値段(1 円刻み、自分に不利な側: 降りる注文は −d の向き。指値は売り切り下げ・買い切り上げ、
    引き金は売りのストップ切り上げ・買いのストップ切り下げ)。u は丸める前の 1 ドルの幅。"""
    u = x / c_ov
    lim = tick_down if d == 1 else tick_up
    trg = tick_up if d == 1 else tick_down
    return {"u": u, "x": x, "t1": trg(x - d * 1.5 * u), "l1": lim(x - d * 1.0 * u), "t2": trg(x - d * 3.5 * u),
            "l2": lim(x - d * 3.0 * u), "t3": trg(x - d * 5.0 * u)}


# ---------------------------------------------------------------- 仕様 3-1: 入り 2 本
def test_entry_buy_two_orders_prices_and_sizes():
    s = sim()
    step(s, 0, ref=BUY)
    assert s._orders == []  # 合図の行は分 1 の頭まで使えない
    step(s, 1)  # 分 1 の頭で注文。分 1 の足は安値 = P(等号なし)なので約定しない
    assert orders(s) == [("ent1", 1, 0.5, P, None, False), ("ent2", 1, 0.5, tick_up(P * (1 - R_BUY / 2)), None, False)]
    assert s._pos == 0.0


def test_entry_sell_two_orders_prices_and_sizes():
    s = sim()
    step(s, 0, ref=SELL)
    step(s, 1)
    assert orders(s) == [("ent1", -1, 0.5, P, None, False), ("ent2", -1, 0.5, tick_down(P * (1 + R_SELL / 2)), None, False)]


def test_p1_is_the_close_of_the_bar_just_before_t():
    s = sim()
    step(s, 0, o=P + 50, c=P + 70, ref=BUY)
    step(s, 1, o=P + 90, lo=P + 80)  # 分 1 の値段は P1 に使わない
    assert s._orders[0].price == P + 70


def test_fill_is_strict_and_at_the_order_price():
    s = sim()
    step(s, 0, ref=BUY)
    step(s, 1, lo=P)
    step(s, 2, o=P + 5, lo=P)  # 安値 = P1 は約定しない
    assert s._pos == 0.0
    step(s, 3, o=P + 5, lo=P - 0.01, c=P + 1)
    assert s._pos == 0.5 and s._trade["avg"] == P  # 安値ではなく注文の値段
    s = sim()
    step(s, 0, ref=SELL)
    step(s, 1, h=P)
    assert s._pos == 0.0
    step(s, 2, h=P + 0.01)
    assert s._pos == -0.5 and s._trade["avg"] == P


# ---------------------------------------------------------------- 仕様 3-1: 注文は次の注文まで残る・次の注文で取り消される
def test_orders_rest_until_the_next_order_and_are_cancelled_by_it():
    s = sim()
    i = long_half(s)
    p2 = tick_up(P * (1 - R_BUY / 2))
    for k in range(i, i + 5):  # 期限は無い。2 本目は残る
        step(s, k, lo=P - 1)
    assert orders(s) == [("ent2", 1, 0.5, p2, None, False)]
    step(s, i + 5, ref=FLAT)  # 同値足: 何もしない(取り消しもしない)
    step(s, i + 6)
    assert orders(s) == [("ent2", 1, 0.5, p2, None, False)]
    step(s, i + 7, ref=SELL)
    step(s, i + 8)  # 売りの合図: 全部取り消して売りの 2 本(ドテンの量)
    assert orders(s) == [("ent1", -1, 1.0, P, None, False), ("ent2", -1, 0.5, tick_down(P * (1 + R_SELL / 2)), None, False)]


# ---------------------------------------------------------------- 仕様 3-1: 増し玉と上限
def test_add_on_and_cap_at_max():
    s = sim()
    i = long_half(s)
    step(s, i, c=P + 100, ref=BUY)
    step(s, i + 1, o=P + 100)  # 持ち高 0.5 からの買い: 1 本目 0.5、2 本目は上限で切って出さない
    assert orders(s) == [("ent1", 1, 0.5, P + 100, None, False)]
    assert [x[:3] for x in s.order_log] == [["ent1", T0 + M, 0.5], ["ent2", T0 + M, 0.5], ["ent1", T0 + (i + 1) * M, 0.5]]
    step(s, i + 2, o=P + 100, lo=P + 99)
    assert s._pos == 1.0 and s._trade["avg"] == (P + P + 100) / 2 and s._trade["max_size"] == 1.0
    step(s, i + 3, ref=BUY)
    step(s, i + 4)  # 上限で同じ向きの合図: スルー(取り消しもしない)
    assert s._orders == [] and s.decisions["skip_at_max_same"] == 1


def test_at_max_same_direction_skip_keeps_resting_exit_orders():
    s = sim()
    i = long_half(s)
    step(s, i, ref=BUY)
    step(s, i + 1)
    step(s, i + 2, lo=P - 1)
    assert s._pos == 1.0
    step(s, i + 3, ref=UPB)
    step(s, i + 4)  # 降りる 4 本
    before = orders(s)
    assert [x[0] for x in before] == ["x_lim", "x_sl1", "x_sl2", "x_sm"]
    step(s, i + 5, ref=BUY)
    step(s, i + 6)  # 上限で買いの合図: スルー。降りる注文は残る
    assert orders(s) == before


# ---------------------------------------------------------------- 仕様 3-1: ドテン
def test_doten_size_and_trade_boundary():
    s = sim()
    i = short_half(s)
    step(s, i, c=P - 200, ref=BUY)
    step(s, i + 1, o=P - 200)
    assert orders(s) == [("ent1", 1, 1.0, P - 200, None, False), ("ent2", 1, 0.5, tick_up((P - 200) * (1 - R_BUY / 2)), None, False)]
    rows = step(s, i + 2, o=P - 200, lo=P - 201)
    assert len(rows) == 1
    r = rows[0]
    assert (r["side"], r["exit_reason"], r["exit_price"], r["entry_price"], r["max_size"]) == (-1, EXIT_DOTEN, P - 200, P, 0.5)
    assert r["pnl_bp"] == pytest.approx(-1 * ((P - 200) / P - 1) * 1e4 * 0.5, rel=1e-12)
    assert r["exit_ns"] == T0 + (i + 3) * M
    assert s._pos == 0.5 and s._trade["side"] == 1 and s._trade["avg"] == P - 200
    assert s._trade["entry_ns"] == T0 + (i + 3) * M


# ---------------------------------------------------------------- 仕様 3-1: 上限での反対の合図(skip と flip)
@pytest.mark.parametrize("at_max", ["skip", "flip"])
def test_opposite_signal_at_max(at_max):
    s = sim(at_max=at_max)
    step(s, 0, ref=BUY)
    step(s, 1)
    step(s, 2, lo=tick_up(P * (1 - R_BUY / 2)) - 1, c=P)  # 2 本とも約定 → 買い 1
    assert s._pos == 1.0 and s._orders == []
    step(s, 3, ref=SELL)
    step(s, 4)
    if at_max == "skip":
        assert s._orders == [] and s.decisions["skip_at_max_opposite"] == 1
    else:
        assert orders(s) == [("ent1", -1, 1.5, P, None, False), ("ent2", -1, 0.5, tick_down(P * (1 + R_SELL / 2)), None, False)]
        rows = step(s, 5, h=tick_down(P * (1 + R_SELL / 2)) + 1)  # 2 本とも約定 → 売り 1
        assert s._pos == -1.0 and rows[0]["exit_reason"] == EXIT_DOTEN and rows[0]["max_size"] == 1.0


# ---------------------------------------------------------------- 仕様 3-2: 降りる 4 本
def test_exit_four_orders_long_and_short():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    assert orders(s) == [("x_lim", -1, 0.5, e["x"], None, False), ("x_sl1", -1, 0.5, e["l1"], e["t1"], False),
                         ("x_sl2", -1, 0.5, e["l2"], e["t2"], False), ("x_sm", -1, 0.5, None, e["t3"], False)]
    s = sim()
    i = short_half(s)
    step(s, i, ref=DNB)
    step(s, i + 1)
    e = exit_prices(P, Q - 10, -1)
    assert e["t1"] > e["l1"] > e["x"]
    assert orders(s) == [("x_lim", 1, 0.5, e["x"], None, False), ("x_sl1", 1, 0.5, e["l1"], e["t1"], False),
                         ("x_sl2", 1, 0.5, e["l2"], e["t2"], False), ("x_sm", 1, 0.5, None, e["t3"], False)]


def test_exit_on_line_cross_without_signal():
    """陰線 × 合図なし × 買い持ちで、終値が先端(Q − 30)以下 → 降りる。先端より上なら何もしない。"""
    s = sim()
    i = long_half(s)
    step(s, i, ref=(Q, Q + 1, Q - 29, Q - 29 + 0.5))  # 陰線、ヒゲ 1 bp 未満で合図なし、終値 > 先端
    step(s, i + 1)
    assert [x[0] for x in orders(s)] == ["ent2"]
    step(s, i + 2, ref=(Q, Q + 1, Q - 30.5, Q - 30))  # 終値 = 先端
    step(s, i + 3)
    assert [x[0] for x in orders(s)] == ["x_lim", "x_sl1", "x_sl2", "x_sm"]


def test_exit_limit_fill_strict():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    assert step(s, i + 2, h=P) == []  # 高値 = X は約定しない
    rows = step(s, i + 3, h=P + 1)
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_LIMIT, P, 0)]
    assert s._pos == 0.0 and s._orders == []  # 1 本約定したら残りは無くなる


def test_stop_limit_1_trigger_then_return():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    u = e["u"]
    assert step(s, i + 2, o=P - 1.2 * u, lo=P - 2 * u) == []  # 引き金だけ(戻りは指値まで届かない)
    assert [(x[0], x[5]) for x in orders(s)] == [("x_lim", False), ("x_sl1", True), ("x_sl2", False), ("x_sm", False)]
    rows = step(s, i + 3, o=P - 1.2 * u, h=P - 0.5 * u)
    assert [(r["exit_reason"], r["exit_price"]) for r in rows] == [(EXIT_SL1, e["l1"])]
    assert rows[0]["exit_ns"] == T0 + (i + 4) * M and s.undecided_bars == 0


def test_stop_limit_not_filled_without_trigger():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    u = e["u"]
    assert step(s, i + 2, o=P - 1.2 * u, h=P - 0.5 * u, lo=P - 1.4 * u) == []  # 引き金(P − 1.5u)の手前
    assert all(not x[5] for x in orders(s))


def test_stop_limit_2_and_stop_market():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    u = e["u"]
    step(s, i + 2, o=P - 1.2 * u, lo=P - 2 * u, c=P - 2 * u)  # 1 の引き金
    step(s, i + 3, o=P - 3.2 * u, lo=P - 4 * u, c=P - 4 * u)  # 2 の引き金(戻りの高値 = 始値 < 2 の指値)
    assert [x[5] for x in orders(s)] == [False, True, True, False]
    rows = step(s, i + 4, o=P - 3.8 * u, h=P - 2 * u, c=P - 2 * u)
    assert [(r["exit_reason"], r["exit_price"]) for r in rows] == [(EXIT_SL2, e["l2"])]
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    rows = step(s, i + 2, o=P - 1.2 * u, lo=P - 6 * u, c=P - 6 * u)
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_SM, e["t3"] - 1, 0)]


def test_short_exit_stop_limit_is_mirrored():
    s = sim()
    i = short_half(s)
    step(s, i, ref=DNB)
    step(s, i + 1)
    e = exit_prices(P, Q - 10, -1)
    u = e["u"]
    step(s, i + 2, o=P + 1.2 * u, h=P + 2 * u)
    rows = step(s, i + 3, o=P + 1.2 * u, lo=P + 0.5 * u)
    assert [(r["side"], r["exit_reason"], r["exit_price"]) for r in rows] == [(-1, EXIT_SL1, e["l1"])]
    assert rows[0]["pnl_bp"] == pytest.approx(-1 * (e["l1"] / P - 1) * 1e4 * 0.5, rel=1e-12)


# ---------------------------------------------------------------- 仕様 4: 足の頭
def test_head_exit_limit_fills_at_its_price_not_the_open():
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    rows = step(s, i + 2, o=P + 500, h=P + 600, lo=P + 400)
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_LIMIT, P, 0)]


def test_head_stop_market_fills_at_the_open_when_open_is_beyond():
    """足の頭で引き金を越えたストップ成行は始値で約定(直し 1)。足の中で越えたら引き金の値段(下の試験)。"""
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    rows = step(s, i + 2, o=P - 10 * e["u"], lo=P - 11 * e["u"])
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_SM, P - 10 * e["u"], 0)]


def test_in_bar_stop_market_fills_one_yen_beyond_the_trigger():
    """足の中で引き金を越えたストップ成行は、丸めた引き金の 1 円向こう(売りのストップ −1 円、買いのストップ +1 円)。
    足の値段は 1 円刻み・判定は等号なしなので、引き金を越えた最初の値段がそこ。"""
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    rows = step(s, i + 2, o=round(P - 1.2 * e["u"]), lo=round(P - 11 * e["u"]), c=round(P - 11 * e["u"]))
    assert [(r["exit_reason"], r["exit_price"]) for r in rows] == [(EXIT_SM, e["t3"] - 1)]
    s = sim()
    i = short_half(s)
    step(s, i, ref=DNB)
    step(s, i + 1)
    e = exit_prices(P, Q - 10, -1)
    rows = step(s, i + 2, o=round(P + 1.2 * e["u"]), h=round(P + 11 * e["u"]), c=round(P + 11 * e["u"]))
    assert [(r["side"], r["exit_reason"], r["exit_price"]) for r in rows] == [(-1, EXIT_SM, e["t3"] + 1)]


@pytest.mark.parametrize("d", [1, -1])
@pytest.mark.parametrize("c_ov", [Q + 10, Q + 3.7, Q + 17.3, 2 * Q, 4321.0])
def test_in_bar_stop_market_fill_is_on_the_unfavorable_side_of_the_unrounded_trigger(d, c_ov):
    """約定の値段は、丸める前の引き金(X − d × 5 ドルの幅)より自分に不利な側(買い持ちなら下、売り持ちなら上)。
    1 円の幅の 1 円未満の端数をいくつか変えて見る。"""
    s = sim()
    i = long_half(s) if d == 1 else short_half(s)
    shape = (Q, Q + 40, Q, Q + 10) if d == 1 else (Q, Q, Q - 40, Q - 10)
    k = c_ov / shape[3]  # 終値が c_ov になるように海外の足を拡大する
    step(s, i, ref=tuple(x * k for x in shape))
    step(s, i + 1)
    raw = P - d * 5.0 * P / c_ov
    far = round(P - d * 20.0 * P / c_ov)
    rows = step(s, i + 2, o=round(P - d * 1.2 * P / c_ov), h=None if d == 1 else far, lo=far if d == 1 else None,
                c=far)
    assert len(rows) == 1 and rows[0]["exit_reason"] == EXIT_SM
    px = rows[0]["exit_price"]
    assert float(px).is_integer() and d * (raw - px) > 0


@pytest.mark.parametrize("fill_side", ["good", "bad"])
def test_head_limit_above_open_is_decided_before_both_legs(fill_side):
    """始値が X より上で、安値はストップ成行の引き金より下の足: 足の頭で X が約定するので、2 通りの道で同じ(決まる)。
    頭を通さないと、下が先の道でストップ成行になり、悪い側が変わる(壊し方 M09 を捕まえる)。"""
    s = sim(fill_side=fill_side)
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    rows = step(s, i + 2, o=P + 500, h=P + 500, lo=P - 11 * e["u"], c=P)
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_LIMIT, P, 0)]
    assert s.undecided_bars == 0


def test_head_entry_both_orders_below_open_fill_at_their_prices():
    s = sim()
    step(s, 0, ref=BUY)
    step(s, 1)
    p2 = tick_up(P * (1 - R_BUY / 2))
    step(s, 2, o=p2 - 100, lo=p2 - 110)
    assert s._pos == 1.0 and s._trade["avg"] == (P + p2) / 2
    assert [x[3] for x in s.order_log] == [T0 + 3 * M, T0 + 3 * M]


# ---------------------------------------------------------------- 仕様 4: 決まらない足(良い側・悪い側)
@pytest.mark.parametrize("fill_side,reason,px_key", [("good", EXIT_LIMIT, "x"), ("bad", EXIT_SL1, "l1")])
def test_undecided_bar_limit_above_and_stop_below(fill_side, reason, px_key):
    """上が先: 指値 X で約定。下が先: 1 の引き金 → 戻りで 1 の指値 X − u で約定。良い側 = X、悪い側 = X − u。"""
    s = sim(fill_side=fill_side)
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    rows = step(s, i + 2, o=P - 0.2 * e["u"], h=P + 0.5 * e["u"], lo=P - 2 * e["u"], c=P)
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(reason, e[px_key], 1)]
    assert s.undecided_bars == 1


@pytest.mark.parametrize("fill_side", ["good", "bad"])
def test_undecided_bar_one_path_still_open(fill_side):
    """上が先: 高値(X と 1 の指値の間)→ 安値で 1 の引き金(足の中では戻らない)。下が先: 引き金 → 高値で 1 の指値。
    終値は 1 の指値より下なので、閉じた方(下が先)が良い側。悪い側は引き金を引いたまま次の足へ。"""
    s = sim(fill_side=fill_side)
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    u = e["u"]
    rows = step(s, i + 2, o=P - 1.2 * u, h=P - 0.5 * u, lo=P - 2 * u, c=P - 1.8 * u)
    if fill_side == "good":
        assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_SL1, e["l1"], 1)]
    else:
        assert rows == [] and s._pos == 0.5 and s._trade["und"] == 1
        assert [(x[0], x[5]) for x in orders(s)] == [("x_lim", False), ("x_sl1", True), ("x_sl2", False),
                                                     ("x_sm", False)]
        rows = step(s, i + 3, o=P - 0.8 * u, lo=P - 0.9 * u)  # 次の足の頭で 1 の指値
        assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [(EXIT_SL1, e["l1"], 1)]


@pytest.mark.parametrize("near_up", [True, False])
def test_equal_value_paths_use_the_path_to_the_nearer_extreme_first(monkeypatch, near_up):
    """2 通りの道の損益の和が同じとき、始値に近い方の端へ先に行く道を使う(壊し方 M22 を捕まえる)。和を同じにする
    ために _value を 0 に置き換える。上が先 = X で約定、下が先 = 1 の引き金 → 1 の指値で約定。"""
    monkeypatch.setattr(KatsuoLimitSim, "_value", staticmethod(lambda st, c: 0.0))
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    e = exit_prices(P, Q + 10, 1)
    u = e["u"]
    if near_up:
        rows = step(s, i + 2, o=P - 0.2 * u, h=P + 0.5 * u, lo=P - 2 * u, c=P)  # 高値の方が近い
        want = (EXIT_LIMIT, e["x"])
    else:
        rows = step(s, i + 2, o=P - 0.2 * u, h=P + 5 * u, lo=P - 2 * u, c=P)  # 安値の方が近い
        want = (EXIT_SL1, e["l1"])
    assert [(r["exit_reason"], r["exit_price"], r["undecided"]) for r in rows] == [want + (1,)]


def test_entry_bars_are_never_undecided():
    s = sim(fill_side="bad")
    step(s, 0, ref=BUY)
    step(s, 1)
    p2 = tick_up(P * (1 - R_BUY / 2))
    step(s, 2, o=P + 10, h=P + 3000, lo=p2 - 1, c=P)
    assert s._pos == 1.0 and s.undecided_bars == 0


# ---------------------------------------------------------------- 仕様 5: 損益と取引の切れ目
def test_pnl_weighted_entry_and_signal_columns():
    s = sim()
    step(s, 0, ref=BUY_SMALL)
    step(s, 1)
    p2 = tick_up(P * (1 - 30 / (Q + 10) / 2))  # r = |終値 − 先端| / 終値 = (Q + 10 − (Q − 20)) / (Q + 10)
    step(s, 2, lo=P - 1)
    step(s, 3, lo=p2 - 1, c=P)
    assert s._pos == 1.0
    step(s, 4, c=P + 300, ref=UPB)
    step(s, 5, o=P + 300)
    rows = step(s, 6, o=P + 300, h=P + 301)
    assert len(rows) == 1
    r = rows[0]
    avg = (P * 0.5 + p2 * 0.5) / 1.0
    assert r["entry_price"] == pytest.approx(avg, rel=1e-15) and r["max_size"] == 1.0
    assert r["pnl_bp"] == pytest.approx(((P + 300) / avg - 1) * 1e4 * 1.0, rel=1e-12)
    assert (r["small"], r["big"]) == (True, False) and r["r"] == pytest.approx(30 / (Q + 10), rel=1e-15)
    assert (r["entry_ns"], r["exit_ns"], r["signal_ns"]) == (T0 + 3 * M, T0 + 7 * M, T0 + M)


def test_finish_closes_at_last_close():
    s = sim()
    long_half(s)
    step(s, 3, c=P + 40)
    rows = s.finish()
    assert [(r["exit_reason"], r["exit_price"], r["exit_ns"]) for r in rows] == [(EXIT_END, P + 40, T0 + 4 * M)]
    assert rows[0]["pnl_bp"] == pytest.approx((40 / P) * 1e4 * 0.5, rel=1e-12)


# ---------------------------------------------------------------- 仕様 2: 合図と分岐はカード 2 と同じ
def _walk(n, seed, t0, vol0=53):
    rnd = random.Random(seed)
    refs, bars, q, p = [], [], Q, P
    for i in range(n):
        o = q
        c = o + rnd.choice([-1, 1]) * rnd.uniform(0, 15)
        h = max(o, c) + (rnd.uniform(0, 40) if rnd.random() < 0.4 else rnd.uniform(0, 3))
        lo = min(o, c) - (rnd.uniform(0, 40) if rnd.random() < 0.4 else rnd.uniform(0, 3))
        refs.append((t0 + i * M, o, h, lo, c))
        q = c
        o = p  # bitFlyer の値段は 1 円刻み(L-595)
        c = o + round(rnd.uniform(-1500, 1500))
        bars.append(bar(i, o, max(o, c) + round(rnd.uniform(0, 1500)), min(o, c) - round(rnd.uniform(0, 1500)), c,
                        vol=0.0 if i % vol0 == 7 else 1.0, t0=t0))
        p = c
    return refs, bars


def test_signals_match_card_2():
    refs, bars = _walk(1500, 11, T0)
    decl = {n: {"lag_ns": ROW_LAG_NS, "source": "試験の入力"} for n in SERIES_SPOT}
    rs = {n: reference_series(n, [(r[0], r[k + 1]) for r in refs], declarations=decl) for k, n in enumerate(SERIES_SPOT)}
    card = C2OwnerXvenueWick(foot_min=15)
    run_card(card, bars, references=rs, declarations=decl, venue="bitflyer", symbol="FX_BTC_JPY")
    s = sim(foot_min=15)
    s.add_refs(refs)
    for b in bars + [bar(1500)]:  # カードは足の終わり T で、再現は始まりが T 以上の足で判定する(仕様 2)ので 1 本多く渡す
        s.feed(b)
    assert len(card.signal_log) > 10 and s.signal_log == card.signal_log


def _candle(color, top, under, body=10.0):
    c = Q + color * body
    return (Q, max(Q, c) + top, min(Q, c) - under, c)


@pytest.mark.parametrize("pos", [-1, 0, 1])
@pytest.mark.parametrize("shape", [(1, 0, 30), (1, 30, 0), (-1, 0, 30), (-1, 30, 0), (1, 1, 1.5), (-1, 1.5, 1),
                                   (1, 1, 2), (-1, 2, 1)])
@pytest.mark.parametrize("line_off", [-5.0, 0.0, 5.0])
def test_action_is_the_card_apply_branching(pos, shape, line_off):
    color, top, under = shape
    o, h, lo, c = _candle(color, top, under)
    card = C2OwnerXvenueWick()
    card._pos, card._line = pos, c + line_off
    card._apply(0, o, h, lo, c)
    new = card._pos
    sig = card.signal_log[-1][1] if card.signal_log else 0
    want = "exit" if (new == 0 and pos != 0) else ("buy" if new == 1 else "sell") if sig != 0 else None
    assert action(color, sig, pos * 0.5, c, card._line) == want


# ---------------------------------------------------------------- 暦年で分けて渡しても通しと同じ
@pytest.mark.parametrize("fill_side", ["good", "bad"])
@pytest.mark.parametrize("at_max", ["skip", "flip"])
@pytest.mark.parametrize("foot_min", [1, 15])
def test_chunked_by_calendar_year_equals_one_pass(fill_side, at_max, foot_min):
    cut = 1_546_300_800 * NS  # 2019-01-01T00:00Z
    t0 = cut - 1500 * M
    refs, bars = _walk(3000, 3, t0)
    kw = {"fill_side": fill_side, "at_max": at_max, "foot_min": foot_min}
    one = KatsuoLimitSim(**kw)
    one.add_refs(refs)
    r1 = [r for b in bars for r in one.feed(b)] + one.finish()
    two = KatsuoLimitSim(**kw)
    r2 = []
    for lo_, hi_ in ((t0, cut), (cut, t0 + 3000 * M)):
        two.add_refs([r for r in refs if lo_ <= r[0] < hi_])
        r2 += [r for b in bars if lo_ <= b.start_time_ns < hi_ for r in two.feed(b)]
    r2 += two.finish()
    assert len(r1) > 20 and r1 == r2
    assert one.order_log == two.order_log and one.undecided_bars == two.undecided_bars
    if fill_side == "good":
        assert one.undecided_bars > 0


# ---------------------------------------------------------------- 先読みなし
def test_no_fill_on_bitflyer_bars_before_t():
    s = sim()
    step(s, 0, lo=P - 50000, c=P, ref=BUY)  # 合図の分の足が大きく下げても、注文はまだ無い
    assert s._orders == [] and s._pos == 0.0
    step(s, 1)
    assert len(s._orders) == 2 and s._pos == 0.0


def _state(s):
    return (orders(s), s._pos, None if s._trade is None else dict(s._trade), list(s.signal_log), s._line,
            [list(x) for x in s.order_log])


def test_foot_closing_at_t_is_not_used_before_t():
    """15 分足 [T0+15分, T0+30分) の最後の 1 分の行(open_time T0+29分、使えるのは T = T0+30分)だけを変えた 2 通り:
    始まりが T より前の足まで状態が同じ。始まりが T の足で初めて違う。"""
    def rows(last):
        out = [(T0, *BUY)] + [(T0 + k * M, Q + 10, Q + 10, Q + 10, Q + 10) for k in range(1, 15)]
        out += [(T0 + k * M, Q, Q, Q, Q) for k in range(15, 29)] + [(T0 + 29 * M, *last)]
        return out
    a, b = sim(foot_min=15), sim(foot_min=15)
    a.add_refs(rows((Q, Q + 30, Q - 10, Q - 10)))  # まとめると SELL の形
    b.add_refs(rows(FLAT))  # まとめると同値足
    for i in range(30):
        x = bar(i, P, lo=P - 1 if i == 16 else P)
        a.feed(x)
        b.feed(x)
        assert _state(a) == _state(b)
    assert a._pos == 0.5  # 分 15 の頭で買いの注文、分 16 で 1 本目が約定
    x = bar(30, P)
    a.feed(x)
    b.feed(x)
    assert [o[0:3] for o in orders(a)] == [("ent1", -1, 1.0), ("ent2", -1, 0.5)]
    assert [o[0] for o in orders(b)] == ["ent2"]


def test_rows_given_after_the_bars_that_needed_them_are_refused():
    s = sim()
    s.feed(bar(5))
    with pytest.raises(ValueError):
        s.add_refs([(T0 + 4 * M, *FLAT)])  # 使えるのは T0+5分 = 既に通した足の始まり
    s.add_refs([(T0 + 5 * M, *FLAT)])


# ---------------------------------------------------------------- 仕様 6: 表の外は拒む
@pytest.mark.parametrize("kw", [{"fill_side": "mid"}, {"at_max": "hold"}, {"foot_min": 2}, {"foot_min": 15.0},
                                {"foot_min": True}])
def test_values_outside_the_table_are_refused(kw):
    with pytest.raises(ValueError):
        sim(**kw)


# ---------------------------------------------------------------- 仕様 8-2: 強い / 弱い と 降りる注文を出した理由
@pytest.mark.parametrize("ref,side,strength", [(BUY, 1, STRONG), (SELL, -1, STRONG), (UPB, -1, WEAK), (DNB, 1, WEAK)])
def test_entry_strength_column(ref, side, strength):
    """強い = 陽線 × 下ヒゲ → 買い・陰線 × 上ヒゲ → 売り。弱い = 陽線 × 上ヒゲ → 売り・陰線 × 下ヒゲ → 買い(持ち高 0 から)。"""
    s = sim()
    step(s, 0, ref=ref)
    step(s, 1)
    step(s, 2, h=P + 1, lo=P - 1)
    assert s._trade["side"] == side
    rows = s.finish()
    assert [(r["side"], r["strength"], r["exit_signal"], r["exit_signal_ns"]) for r in rows] == [(side, strength, None,
                                                                                                    None)]


def test_exit_signal_column_weak_opposite_and_line_cross():
    s = sim()
    i = long_half(s)  # BUY(強い)で買い
    step(s, i, ref=UPB)  # 陽線 × 上ヒゲ × 買い持ち → 降りる(反対の弱い合図)
    step(s, i + 1)
    rows = step(s, i + 2, h=P + 1)
    assert [(r["strength"], r["exit_signal"], r["exit_signal_ns"]) for r in rows] == [(STRONG, XSIG_WEAK, T0 + (i + 1) * M)]
    s = sim()
    i = long_half(s)
    step(s, i, ref=(Q, Q + 1, Q - 30.5, Q - 30))  # 陰線 × 合図なし × 買い持ち、終値 = 先端 → 降りる(先端を越えた)
    step(s, i + 1)
    rows = step(s, i + 2, h=P + 1)
    assert [(r["exit_reason"], r["exit_signal"], r["exit_signal_ns"]) for r in rows] == [(EXIT_LIMIT, XSIG_LINE,
                                                                                         T0 + (i + 1) * M)]
    s = sim()
    i = short_half(s)
    step(s, i, ref=DNB)  # 陰線 × 下ヒゲ × 売り持ち → 降りる(反対の弱い合図)
    step(s, i + 1)
    rows = step(s, i + 2, lo=P - 1)
    assert [(r["side"], r["exit_signal"]) for r in rows] == [(-1, XSIG_WEAK)]


def test_exit_signal_is_empty_for_doten():
    s = sim()
    i = short_half(s)
    step(s, i, ref=BUY)
    step(s, i + 1)
    rows = step(s, i + 2, lo=P - 1)
    assert [(r["exit_reason"], r["strength"], r["exit_signal"]) for r in rows] == [(EXIT_DOTEN, STRONG, None)]
    assert s._trade["strength"] == STRONG


# ================================================================ 仕様 9: design="k1"
import sys  # noqa: E402

sys.path.insert(0, "/home/user/trade/scripts")
sys.path.insert(0, "/home/user/trade/scripts/w4_measure")
import measure_katsuo_dispersion as k1_base  # noqa: E402
import measure_katsuo_effect as k1_eff  # noqa: E402
import measure_katsuo_robustness as k1_rb  # noqa: E402

WIDE = 50_000.0  # bitFlyer の足の幅(どの注文も次の足で約定する)


def k1sim(**kw):
    kw.setdefault("fill_side", "good")
    kw.setdefault("design", "k1")
    kw.setdefault("foot_min", 15)
    kw.setdefault("entry", "a")
    return KatsuoLimitSim(**kw)


def foot_rows(j, ohlc, foot=15, t0=T0):
    """foot 分足 j を 1 分足の行に: 1 本目に 4 本値、残りは終値で平ら(まとめると ohlc)。"""
    o, h, lo, c = ohlc
    return [(t0 + (j * foot + m) * M, o, h, lo, c) if m == 0 else (t0 + (j * foot + m) * M, c, c, c, c)
            for m in range(foot)]


def _k1_walk(n_min, seed, t0=T0):
    rnd = random.Random(seed)
    rows, q = [], Q
    for i in range(n_min):
        o = q
        c = round(o + rnd.choice([-1, 1]) * rnd.uniform(0, 12), 2)
        h = round(max(o, c) + (rnd.uniform(0, 35) if rnd.random() < 0.3 else rnd.uniform(0, 3)), 2)
        lo = round(min(o, c) - (rnd.uniform(0, 35) if rnd.random() < 0.3 else rnd.uniform(0, 3)), 2)
        rows.append((t0 + i * M, o, h, lo, c))
        q = c
    return rows


def _k1_events(rows, foot, keep, delay):
    """K1 の関数(signals → delay_signals → simulate)の行動の列 (種類, 時刻 ns, 合図の向き)。"""
    bars = k1_base.fold([(r[0] // NS, *r[1:]) for r in rows], foot)
    sg = k1_eff.signals(bars, 19.0, 24.0, flip_body=(keep == "weak"))
    if delay:
        sg = k1_eff.delay_signals(sg)
    tr = k1_eff.simulate(bars, sg, keep, use_invalid=False)
    t = [(b[0] + foot * 60) * NS for b in bars]  # 足の終わり = 行動の時刻
    ev = []
    for k, (i, _r, hold, why) in enumerate(tr):
        d = sg[i][0]
        if not (ev and ev[-1][0] == "doten" and ev[-1][1] == t[i]):
            ev.append(("open", t[i], d))
        ev.append(("doten", t[i + hold], -d) if why == "reversed" else ("exit", t[i + hold], -d))
    return ev, bars, tr, sg


def _run_k1(rows, n_min, **kw):
    s = k1sim(**kw)
    s.add_refs(rows)
    out = []
    for i in range(n_min + 2):
        out += s.feed(bar(i, P, h=P + WIDE, lo=P - WIDE, c=P))
    return s, out


def _ref_events(sg, t, keep, entry):
    """行動の時刻の規則(再現のモジュールの説明。リードの直し 3)を、K1 の合図の列 sg(H3 なし)に当てた行動の列。
    約定は行動の時刻にすぐ(参照の形)。入り方 a では K1 の delay_signals → simulate と同じになる(下の試験で確かめる)。"""
    pos, pend, ev = 0, None, []

    def act(sig, T):
        nonlocal pos
        if pos == sig:
            return
        if pos == -sig:
            ev.append(("doten", T, sig) if keep == "strong" else ("exit", T, sig))
            pos = sig if keep == "strong" else 0
            return
        ev.append(("open", T, sig))
        pos = sig

    for j, (sig, _lc, _cs, st) in enumerate(sg):
        p, pend = pend, None
        if p is not None:
            act(p, t[j])
        if sig != 0 and st == keep:
            if entry != "a" and pos == 0:
                act(sig, t[j])
            else:
                pend = sig
    return ev


@pytest.mark.parametrize("keep,foot", [("weak", 15), ("weak", 5), ("strong", 1)])
@pytest.mark.parametrize("fill", ["limit", "close"])
def test_k1_entry_a_action_sequence_matches_k1_functions(keep, foot, fill):
    """手で作った海外の足の並びを K1 の関数(signals → delay_signals → simulate)と再現の両方に通し、行動の列(種類・
    向き・時刻)が一致する。入り方 a は入りも降りるも H3。limit は bitFlyer の足の幅を広くして、どの注文も次の 1 分で
    約定させる(約定した持ち高 = K1 の持ち高)。"""
    n_min = 3000 if foot > 1 else 600
    rows = _k1_walk(n_min, 5 + foot)
    ev, bars, tr, _sg = _k1_events(rows, foot, keep, delay=True)
    s, _out = _run_k1(rows, n_min, foot_min=foot, side_keep=keep, entry="a", fill=fill)
    got = s.action_log
    assert len(tr) > 5
    assert got[:len(ev)] == ev
    assert len(got) - len(ev) <= 1 and all(x[0] == "open" for x in got[len(ev):])  # K1 は最後の建玉を閉じない
    sg0 = k1_eff.signals(bars, 19.0, 24.0, flip_body=(keep == "weak"))
    assert _ref_events(sg0, [(b[0] + foot * 60) * NS for b in bars], keep, "a") == got  # 下の試験の物差しも K1 と同じ


@pytest.mark.parametrize("keep,foot", [("weak", 15), ("weak", 5), ("strong", 1)])
@pytest.mark.parametrize("entry", ["b", "c"])
def test_k1_entry_b_c_enter_at_the_signal_and_exit_one_foot_later(keep, foot, entry):
    """入り方 b・c: 持ち高 0 の入りは合図の時点、降りる・ドテンは H3 で 1 本遅れ(直し 3)。参照の形(すぐ約定)で
    行動の列を物差し _ref_events と比べる。"""
    n_min = 3000 if foot > 1 else 600
    rows = _k1_walk(n_min, 5 + foot)
    bars = k1_base.fold([(r[0] // NS, *r[1:]) for r in rows], foot)
    sg0 = k1_eff.signals(bars, 19.0, 24.0, flip_body=(keep == "weak"))
    want = _ref_events(sg0, [(b[0] + foot * 60) * NS for b in bars], keep, entry)
    s, _out = _run_k1(rows, n_min, foot_min=foot, side_keep=keep, entry=entry, fill="close")
    assert len(want) > 10 and s.action_log == want
    opens = [x for x in want if x[0] == "open"]
    sig_t = {(b[0] + foot * 60) * NS for b, g in zip(bars, sg0) if g[0] != 0}
    assert all(x[1] in sig_t for x in opens[:3])  # 入りは合図の足の区切りそのもの


def test_k1_close_entry_a_pnl_matches_k1_close_fills():
    """参照の形・入り方 a の取引ごとの損益 = K1 の simulate(prices = 行動の足の終わりの直前の bitFlyer の終値)。"""
    rows = _k1_walk(3000, 33)
    rnd = random.Random(9)
    closes = [P + rnd.uniform(-20000, 20000) for _ in range(3002)]
    s = k1sim(entry="a", fill="close")
    s.add_refs(rows)
    out = []
    for i in range(3002):
        c = closes[i]
        out += s.feed(bar(i, c, h=c + 10, lo=c - 10, c=c))
    bars = k1_base.fold([(r[0] // NS, *r[1:]) for r in rows], 15)
    prices = [closes[(b[0] // 60) + 15 - 1 - T0 // M] for b in bars]  # 足の終わりの直前の 1 分の終値
    sg = k1_eff.delay_signals(k1_eff.signals(bars, 19.0, 24.0, flip_body=True))
    tr = k1_eff.simulate(bars, sg, "weak", use_invalid=False, prices=prices)
    got = [r["pnl_bp"] for r in out if r["exit_reason"] == EXIT_CLOSE]
    assert len(tr) > 20
    assert got == pytest.approx([x[1] for x in tr], rel=1e-9, abs=1e-9)


def test_k1_vol_prev_matches_footdata():
    """取引ごとの vol_prev = K1 の FootData.vol_prev[行動の足](H3 の entry="a"、行動の足 = 合図の足 + 1)。"""
    rows = _k1_walk(3000, 20)
    _ev, bars, tr, _sg = _k1_events(rows, 15, "weak", delay=True)
    fd = k1_rb.FootData(bars)
    s, out = _run_k1(rows, 3000, foot_min=15, side_keep="weak", entry="a")
    out += s.finish()
    t = [(b[0] + 15 * 60) * NS for b in bars]
    k1_vol = {t[i - 1]: fd.vol_prev[i] for i, _r, _h, _w in tr}  # 合図の足の終わり → vol_prev[行動の足]
    checked = 0
    for r in out:
        v = k1_vol.get(r["signal_ns"])
        if v is None:
            continue
        if math.isnan(v):
            assert r["vol_prev"] is None
        else:
            assert r["vol_prev"] == pytest.approx(float(v), rel=1e-9)
            checked += 1
    assert checked > 5


WEAK_SELL = (Q, Q + 40, Q, Q + 10)  # 陽線 × 上ヒゲ → 売り(弱い)
WEAK_BUY = (Q, Q, Q - 40, Q - 10)  # 陰線 × 下ヒゲ → 買い(弱い)


@pytest.mark.parametrize("entry", ["a", "b", "c"])
def test_k1_entry_forms(entry):
    s = k1sim(entry=entry)
    s.add_refs(foot_rows(0, WEAK_SELL) + foot_rows(1, FLAT))
    for i in range(16):
        s.feed(bar(i))
    r = 30 / (Q + 10)  # |終値 Q + 10 − 先端 Q + 40| / 終値
    p2 = tick_down(P * (1 + r / 2))
    if entry == "a":
        assert s._orders == []  # H3: 次の足の区切り(T0+30分)まで待つ
        for i in range(16, 31):
            s.feed(bar(i))
        assert orders(s) == [("ent1", -1, 1.0, P, None, False)]
        assert s.order_log[0][1] == T0 + 30 * M
    elif entry == "b":
        assert orders(s) == [("ent2", -1, 1.0, p2, None, False)] and s.order_log[0][1] == T0 + 15 * M
    else:
        assert orders(s) == [("ent1", -1, 0.5, P, None, False), ("ent2", -1, 0.5, p2, None, False)]


def test_k1_weak_opposite_exits_one_foot_later_without_doten_and_same_side_does_nothing():
    s = k1sim(entry="b")
    s.add_refs(foot_rows(0, WEAK_SELL) + foot_rows(1, WEAK_SELL) + foot_rows(2, WEAK_BUY) + foot_rows(3, FLAT)
               + foot_rows(4, FLAT))
    for i in range(16):
        s.feed(bar(i))
    s.feed(bar(16, P, h=P + WIDE))  # 売り 1 が約定
    assert s._pos == -1.0
    for i in range(17, 46):
        s.feed(bar(i))
    assert s._orders == [] and s.decisions["k1_same_side"] == 1  # 同じ向き: 何もしない(T0+45分の区切りで)
    for i in range(46, 60):
        s.feed(bar(i))
    assert s._orders == []  # 足 2(T0+45分)の反対の合図の降りる注文は、次の区切り T0+60分 まで出さない(H3)
    s.feed(bar(60))
    assert [x[0] for x in orders(s)] == ["x_lim", "x_sl1", "x_sl2", "x_sm"]  # 反対の弱い合図: 降りる 4 本だけ
    rows = s.feed(bar(61, P, lo=P - 1))
    assert [(r["exit_reason"], r["exit_signal"], r["exit_signal_ns"], r["strength"], r["h1"]) for r in rows] == [
        (EXIT_LIMIT, XSIG_WEAK, T0 + 60 * M, WEAK, False)]
    assert s._pos == 0.0 and s._orders == []


def test_k1_h1_flips_a_body_dominant_foot_and_marks_it_weak():
    """実体 30 ≥ ヒゲ 25(24 の枝だけが通す)の陽線: ヒゲは上なので原典は売り。H1 は実体を逆張り = 売り(陽線の逆)。
    陰線で実体 ≥ 下ヒゲなら買い。どちらも弱い・h1 = True。"""
    bull = (Q, Q + 55, Q, Q + 30)  # 陽線、上ヒゲ 25、実体 30
    sig, lc, cs, st, small, big, fl = k1_signal(*bull, True)
    assert (sig, lc, cs, st, small, big, fl) == (-1, Q + 55, 1, "weak", False, True, True)
    bear_under = (Q, Q, Q - 55, Q - 30)  # 陰線、下ヒゲ 25 → 原典は買い。H1: 陰線の逆 = 買い
    assert k1_signal(*bear_under, True)[:4] == (1, Q - 55, -1, "weak")
    bear_top = (Q, Q + 25, Q - 30, Q - 30)  # 陰線、上ヒゲ 25 → 原典は売り(強い)。H1: 買い(弱い)
    assert k1_signal(*bear_top, True)[:4] == (1, Q - 30, -1, "weak")
    assert k1_signal(*bear_top, False)[:4] == (-1, Q + 25, -1, "strong")  # 強いだけの組は H1 を当てない


@pytest.mark.parametrize("edges,enters", [((0.0, 1e-9), True), ((1e8, 2e8), False)])
def test_k1_vol_gate_enters_only_in_the_high_tercile_and_never_blocks_exits(edges, enters):
    s = k1sim(entry="b", foot_min=5, vol_gate=True, vol_edges=edges)
    rows = []
    for j in range(102):
        rows += foot_rows(j, (Q + j % 2, Q + j % 2, Q + j % 2, Q + (j + 1) % 2), foot=5)  # 実体 1 の足(合図なし)
    rows += foot_rows(102, WEAK_SELL, foot=5) + foot_rows(103, FLAT, foot=5)
    s.add_refs(rows)
    for i in range(103 * 5 + 1):
        s.feed(bar(i))
    if enters:
        assert [x[0] for x in orders(s)] == ["ent2"]
    else:
        assert s._orders == [] and s.decisions["k1_vol_gate_skip"] == 1


def test_k1_vol_gate_blocks_until_101_feet_but_exit_is_not_gated():
    s = k1sim(entry="b", foot_min=5, vol_gate=True, vol_edges=(0.0, 1e-9))
    s.add_refs(foot_rows(0, WEAK_SELL, foot=5) + foot_rows(1, FLAT, foot=5))
    for i in range(6):
        s.feed(bar(i))
    assert s._orders == [] and s.decisions["k1_vol_gate_skip"] == 1  # vol_prev が無い = 三分位なし
    s._pos, s._trade = -1.0, {"side": -1, "size": 1.0, "avg": P}  # 売り持ちを置いて、反対の弱い合図
    s.add_refs(foot_rows(2, WEAK_BUY, foot=5) + foot_rows(3, FLAT, foot=5) + foot_rows(4, FLAT, foot=5))
    for i in range(6, 21):
        s.feed(bar(i))
    assert [x[0] for x in orders(s)] == ["x_lim", "x_sl1", "x_sl2", "x_sm"]  # 門に関係なく出す(T0+20分)
    assert s.decisions["k1_vol_gate_skip"] == 1


def test_k1_strong_one_minute_doten():
    s = k1sim(foot_min=1, side_keep="strong", entry="a")
    step(s, 0, ref=BUY)  # 強い買い(分 0 の足)
    step(s, 1, ref=FLAT)  # H3: 次の海外の足(分 1)が閉じた区切り(分 2 の頭)で出す
    assert s._orders == []
    step(s, 2)
    assert orders(s) == [("ent1", 1, 1.0, P, None, False)] and s.order_log[0][1] == T0 + 2 * M
    step(s, 3, lo=P - 1, ref=SELL)
    assert s._pos == 1.0
    step(s, 4, ref=FLAT)
    step(s, 5)
    assert orders(s) == [("ent1", -1, 2.0, P, None, False)] and s.decisions["k1_doten"] == 1
    rows = step(s, 6, h=P + 1)
    assert [(r["exit_reason"], r["side"], r["strength"]) for r in rows] == [(EXIT_DOTEN, 1, STRONG)]
    assert s._pos == -1.0


def _gate_rows(n_feet, foot=5):
    rows = []
    for j in range(n_feet):
        rows += foot_rows(j, (Q + j % 2, Q + j % 2, Q + j % 2, Q + (j + 1) % 2), foot=foot)  # 実体 1 の足(合図なし)
    return rows


def test_k1_gate_rejection_cancels_the_opposite_entry_order():
    """門で入りを弾いても、反対向きの入りの注文は取り消す(直し 4)。"""
    s = k1sim(entry="b", foot_min=5, vol_gate=True, vol_edges=(0.0, 1e-9))
    s.add_refs(_gate_rows(102) + foot_rows(102, WEAK_SELL, foot=5))
    for i in range(103 * 5 + 1):
        s.feed(bar(i))
    assert [x[:2] for x in orders(s)] == [("ent2", -1)]  # 売りの半値(届かない)
    s.vol_edges = (1e8, 2e8)  # 次の合図は低い三分位(門で弾く)
    s.add_refs(foot_rows(103, WEAK_BUY, foot=5) + foot_rows(104, FLAT, foot=5))
    for i in range(103 * 5 + 1, 104 * 5 + 1):
        s.feed(bar(i))
    assert s.decisions["k1_vol_gate_skip"] == 1 and s._orders == []
    s.feed(bar(104 * 5 + 1, P, h=P + WIDE))
    assert s._pos == 0.0  # 古い売りの指値は残っていないので約定しない


def test_k1_same_direction_signal_while_entry_order_rests_does_nothing():
    """同じ向きの入りの注文が残っている間に同じ向きの合図: 何もしない(注文は出し直さない。直し 5)。"""
    s = k1sim(entry="b")
    s.add_refs(foot_rows(0, WEAK_SELL) + foot_rows(1, (Q, Q + 60, Q, Q + 10)) + foot_rows(2, FLAT))
    for i in range(16):
        s.feed(bar(i))
    before = orders(s)
    for i in range(16, 31):
        s.feed(bar(i, P + 100, c=P + 100))  # 届かない(半値 > P + 100)
    assert orders(s) == before and s.decisions["k1_same_side_resting"] == 1
    assert len(s.order_log) == 1


def test_k1_close_fill_enters_and_exits_at_the_last_close_at_the_action_time():
    """参照の形: 入り方 b でも半値ではなく、行動の時刻の直前の bitFlyer の終値で全量を約定。降りるのは H3 の区切り。"""
    s = k1sim(entry="b", fill="close")
    s.add_refs(foot_rows(0, WEAK_SELL) + foot_rows(1, WEAK_BUY) + foot_rows(2, FLAT) + foot_rows(3, FLAT))
    for i in range(15):
        s.feed(bar(i, P, c=P + 7 if i == 14 else P))
    s.feed(bar(15))
    assert s._pos == -1.0 and s._trade["avg"] == P + 7 and s._trade["entry_ns"] == T0 + 15 * M and s._orders == []
    out = []
    for i in range(16, 46):
        out += s.feed(bar(i, P - 300, c=P - 300))
    assert [(r["exit_reason"], r["exit_price"], r["exit_ns"], r["signal_ns"]) for r in out] == [
        (EXIT_CLOSE, P - 300, T0 + 45 * M, T0 + 15 * M)]
    assert out[0]["pnl_bp"] == pytest.approx(-1 * ((P - 300) / (P + 7) - 1) * 1e4, rel=1e-12)
    assert s.order_log[0][3] == T0 + 15 * M


def _run_pair(refs, bars, **kw):
    lim, clo = k1sim(**kw), k1sim(**dict(kw, fill="close"))
    lim.add_refs(refs)
    clo.add_refs(refs)
    rl, rc = [], []
    for b in bars:
        rl += lim.feed(b)
        rc += clo.feed(b)
    return lim, rl + lim.finish(), rc + clo.finish()


def test_k1_missed_is_a_close_trade_without_a_limit_trade_for_the_same_signal():
    """取り逃し = 参照の形で建った取引のうち、指値の形に同じ合図の時刻の取引が無いもの(直し 5)。"""
    import c2_limit_run as R
    refs = foot_rows(0, WEAK_SELL) + foot_rows(1, WEAK_BUY) + foot_rows(2, FLAT) + foot_rows(3, FLAT)
    bars = [bar(i, P, c=P) for i in range(30)] + [bar(i, P - 1000, c=P - 1000) for i in range(30, 50)]
    lim, rl, rc = _run_pair(refs, bars, entry="b")
    ms = R.find_missed(rl, rc, lim.order_log)
    # 参照の形: 足 0 の売りを T0+15分 に P で建て、足 1 の反対の買いで T0+45分(H3)に P − 1000 で降りる(1 取引)。
    # 指値の形: 売りの半値にも、足 1 の買いの半値にも届かない(取引 0)。足 1 の買いは参照の形では降りる行動なので
    # 取引を作らず、取り逃しにも入らない。
    assert [(m["signal_ns"], m["side"], m["limit_order_placed"], m["exit_ns"]) for m in ms] == [
        (T0 + 15 * M, -1, True, T0 + 45 * M)]
    assert rl == [] and ms[0]["pnl_bp"] == pytest.approx(-1 * ((P - 1000) / P - 1) * 1e4, rel=1e-12)
    st = R.missed_stats(ms)
    assert (st["trades"], st["limit_order_placed"]["trades"], st["limit_order_not_placed"]["trades"]) == (1, 1, 0)
    # 指値の形が約定した合図は取り逃しに入らない
    bars2 = [bar(i, P, c=P) for i in range(15)] + [bar(15, P, h=P + WIDE)] + [bar(i, P, c=P) for i in range(16, 50)]
    lim, rl, rc = _run_pair(refs, bars2, entry="b")
    assert [r["signal_ns"] for r in rl][:1] == [T0 + 15 * M]
    assert T0 + 15 * M not in [m["signal_ns"] for m in R.find_missed(rl, rc, lim.order_log)]


def test_find_missed_marks_signals_without_a_limit_order():
    import c2_limit_run as R
    rc = [{"signal_ns": 1, "pnl_bp": 5.0}, {"signal_ns": 2, "pnl_bp": -3.0}, {"signal_ns": 3, "pnl_bp": 1.0}]
    rl = [{"signal_ns": 3, "pnl_bp": 0.5}]
    log = [["ent2", 10, 1.0, None, 0, 1]]
    ms = R.find_missed(rl, rc, log)
    assert [(m["signal_ns"], m["limit_order_placed"]) for m in ms] == [(1, True), (2, False)]
    st = R.missed_stats(ms)
    assert (st["trades"], st["sum_bp"], st["limit_order_placed"]["sum_bp"], st["limit_order_not_placed"]["sum_bp"]) == (
        2, 2.0, 5.0, -3.0)


# ---------------------------------------------------------------- K1 の合図の門・三分位(壊し方 M06・M08・M11)
import measure_katsuo_xvenue as k1_xv  # noqa: E402


@pytest.mark.parametrize("ohlc,want", [
    ((Q, Q + 25, Q - 25, Q - 25), (1, Q - 25, -1, "weak", False, True, True)),  # 陰線・上ヒゲ 25 = 実体 25: H1 で買い
    ((Q, Q + 40, Q, Q + 20), (0, 0.0, 1, "", False, False, False)),  # 陽線・上ヒゲ 20 = 実体 20、24 bp 未満: 小門も通らない
    ((Q, Q + 41, Q, Q + 20), (-1, Q + 41, 1, "weak", True, False, False)),  # 上ヒゲ 21 > 実体 20: 小門の枝
])
def test_k1_signal_edges_match_k1_function(ohlc, want):
    """H1 は 実体 >= ヒゲ(M06)、小門は ヒゲ > 実体(M08)。K1 の signals() と同じ値。"""
    got = k1_signal(*ohlc, True)
    assert got == want
    k = k1_eff.signals([(0, *ohlc)], 19.0, 24.0, flip_body=True)[0]
    assert (got[0], got[1], got[2], got[3]) == (k[0], k[1] if k[0] else 0.0, k[2], k[3])


@pytest.mark.parametrize("v", [None, float("nan"), 0.5, 1.0, 1.5, 2.0, 2.5])
def test_tercile_matches_k1_bucket_of(v):
    """境目ちょうどは上の三分位(v < q1 低、v < q2 中、それ以外 高。M11)。"""
    edges = (1.0, 2.0)
    want = None if v is None else k1_xv.bucket_of(v, edges)
    assert tercile(v, edges) == want
    assert tercile(2.0, edges) == "high" and tercile(1.0, edges) == "mid"


# ---------------------------------------------------------------- 走らせの集計(c2_limit_run.build_summary)
def test_run_summary_by_year_flags_and_2018on():
    import c2_limit_run as R
    y17, y18 = 1_483_228_800 * NS, 1_514_764_800 * NS  # 2017-01-01・2018-01-01
    lo, hi = y17 + 300 * 86_400 * NS, y18 + 31 * 86_400 * NS
    edges = [lo, y18, hi]

    def row(t, pnl, terc, st=WEAK, why=XSIG_WEAK, reason=EXIT_LIMIT, und=0):
        return {"exit_ns": t, "entry_ns": t - M, "pnl_bp": pnl, "vol_tercile": terc, "strength": st, "exit_signal": why,
                "exit_reason": reason, "undecided": und, "signal_ns": t - 2 * M}
    rows = [row(y17 + 301 * 86_400 * NS, 10.0, "high"), row(y17 + 302 * 86_400 * NS, -4.0, "low", und=2),
            row(y18 + NS, 6.0, "high", st=STRONG, why=None, reason=EXIT_DOTEN), row(y18 + 2 * NS, 0.0, None)]
    log = [["ent1", y17 + 301 * 86_400 * NS - 10 * M, 1.0, y17 + 301 * 86_400 * NS - 9 * M, 0, 0],
           ["ent2", y18 + 5 * M, 1.0, None, 1, 0]]
    missed = [{"signal_ns": y17 + 330 * 86_400 * NS, "pnl_bp": 3.0, "limit_order_placed": True},
              {"signal_ns": y18 + 3 * M, "pnl_bp": -1.0, "limit_order_placed": False}]
    for gate in (False, True):
        sm = R.build_summary(rows, log, missed, lo, hi, edges, gate)
        a17, a18 = sm["years"]["2017"], sm["years"]["2018"]
        assert (a17["trades"], a17["wins"], a17["losses"], a17["sum_bp"], a17["undecided_bars_in_trades"]) == (2, 1, 1,
                                                                                                                6.0, 2)
        assert (a18["trades"], a18["wins"], a18["losses"], a18["sum_bp"]) == (2, 1, 0, 6.0)
        assert a17["days"] == 65.0 and a18["days"] == 31.0 and a17["per_day"]["pnl_bp"] == 6.0 / 65.0
        assert a17["by_vol_tercile"]["high"]["sum_bp"] == 10.0 and a18["by_vol_tercile"]["値なし"]["trades"] == 1
        assert a17["vol_tercile_lookahead"] is True and a18["vol_tercile_lookahead"] is False  # 門の有無に関係なく
        assert a17["vol_gate_lookahead"] is gate and a18["vol_gate_in_sample"] is gate
        assert a17["entry_orders"]["ent1"] == {"placed": 1, "filled": 1, "fill_ratio": 1.0, "wait_min_mean": 1.0,
                                               "wait_min_median": 1.0}
        assert a18["entry_orders"]["ent2"]["fill_ratio"] == 0.0
        assert a17["missed"]["trades"] == 1 and a18["missed"]["limit_order_not_placed"]["sum_bp"] == -1.0
        assert a18["by_strength"][STRONG]["trades"] == 1 and a18["exit_reasons"] == {EXIT_DOTEN: 1, EXIT_LIMIT: 1}
        on = sm["all_2018on"]
        assert (on["trades"], on["sum_bp"], on["days"], on["missed"]["trades"]) == (2, 6.0, 31.0, 1)
        assert on["vol_tercile_lookahead"] is False
        al = sm["all"]
        assert (al["trades"], al["sum_bp"], al["days"]) == (4, 12.0, 96.0) and al["vol_tercile_lookahead"] is True


@pytest.mark.parametrize("kw", [{"at_max": "skip"}, {"side_keep": "strong"}, {"foot_min": 1}, {"foot_min": 3},
                                {"vol_gate": True}, {"vol_edges": (2.0, 1.0)}, {"entry": "d"},
                                {"foot_min": 1, "side_keep": "strong", "vol_gate": True, "vol_edges": (1.0, 2.0)},
                                {"fill": "market"}])
def test_k1_values_outside_the_table_are_refused(kw):
    with pytest.raises(ValueError):
        k1sim(**kw)


def test_v03_refuses_k1_only_values():
    for kw in ({"entry": "a"}, {"vol_gate": True, "vol_edges": (1.0, 2.0)}, {"fill": "close"}):
        with pytest.raises(ValueError):
            sim(**kw)


@pytest.mark.parametrize("entry", ["a", "b", "c"])
@pytest.mark.parametrize("fill,gate", [("limit", False), ("limit", True), ("close", False)])
def test_k1_chunked_by_calendar_year_equals_one_pass(entry, fill, gate):
    cut = 1_546_300_800 * NS  # 2019-01-01T00:00Z
    t0 = cut - 3000 * M
    refs = _k1_walk(6000, 41, t0=t0)
    _r, bars = _walk(6000, 42, t0)
    kw = {"fill_side": "bad", "design": "k1", "foot_min": 15, "entry": entry, "fill": fill, "vol_gate": gate,
          "vol_edges": (3.0, 6.0)}
    one = KatsuoLimitSim(**kw)
    one.add_refs(refs)
    r1 = [r for b in bars for r in one.feed(b)] + one.finish()
    two = KatsuoLimitSim(**kw)
    r2 = []
    for lo_, hi_ in ((t0, cut), (cut, t0 + 6000 * M)):
        two.add_refs([r for r in refs if lo_ <= r[0] < hi_])
        r2 += [r for b in bars if lo_ <= b.start_time_ns < hi_ for r in two.feed(b)]
    r2 += two.finish()
    assert len(r1) > 10 and r1 == r2 and one.order_log == two.order_log and one.action_log == two.action_log


# ---------------------------------------------------------------- 値段の刻み(L-595: bitFlyer は 1 円刻み)
def test_tick_rounding_helpers_and_float_error():
    assert tick_up(998001.2) == 998002.0 and tick_down(998001.8) == 998001.0
    assert tick_up(1_000_000.0000000001) == 1_000_000.0 and tick_down(999_999.9999999999) == 1_000_000.0  # 誤差は整数
    assert tick_up(-0.5) == 0.0 and tick_down(7.0) == 7.0


def test_order_prices_are_rounded_to_the_unfavorable_side():
    """買いの指値は切り上げ・売りの指値は切り下げ。売りのストップの引き金は切り上げ・買いのストップは切り下げ。"""
    s = sim()
    step(s, 0, ref=BUY)
    step(s, 1)
    assert s._orders[1].price == math.ceil(P * (1 - R_BUY / 2)) and s._orders[1].price != P * (1 - R_BUY / 2)
    s = sim()
    step(s, 0, ref=SELL)
    step(s, 1)
    assert s._orders[1].price == math.floor(P * (1 + R_SELL / 2)) and s._orders[1].price != P * (1 + R_SELL / 2)
    s = sim()
    i = long_half(s)
    step(s, i, ref=UPB)
    step(s, i + 1)
    u = P / (Q + 10)
    lim = {o.kind: (o.side, o.price, o.trig) for o in s._orders}
    assert lim["x_lim"] == (-1, P, None)
    assert lim["x_sl1"] == (-1, math.floor(P - 1.0 * u), math.ceil(P - 1.5 * u))  # 売り: 指値 ↓、引き金 ↑
    assert lim["x_sl2"] == (-1, math.floor(P - 3.0 * u), math.ceil(P - 3.5 * u))
    assert lim["x_sm"] == (-1, None, math.ceil(P - 5.0 * u))
    s = sim()
    i = short_half(s)
    step(s, i, ref=DNB)
    step(s, i + 1)
    u = P / (Q - 10)
    lim = {o.kind: (o.side, o.price, o.trig) for o in s._orders}
    assert lim["x_sl1"] == (1, math.ceil(P + 1.0 * u), math.floor(P + 1.5 * u))  # 買い: 指値 ↑、引き金 ↓
    assert lim["x_sl2"] == (1, math.ceil(P + 3.0 * u), math.floor(P + 3.5 * u))
    assert lim["x_sm"] == (1, None, math.floor(P + 5.0 * u))


def test_fill_is_judged_on_the_rounded_price():
    """買いの半値: 丸める前 P2、丸めた後 ceil(P2)。安値が P2 と ceil(P2) の間なら、丸めた値段で約定を判定するので約定し、
    約定の値段は ceil(P2)。(bitFlyer の 4 本値は整数なので、実データでは約定するかどうかは丸めで変わらず、約定の
    値段だけが自分に不利な側へ 1 円未満動く。ここでは判定に丸めた値段を使うことを見るために端数の安値を置く)"""
    raw = P * (1 - R_BUY / 2)
    s = sim()
    step(s, 0, ref=BUY)
    step(s, 1)
    step(s, 2, o=P + 5, lo=(raw + math.ceil(raw)) / 2, c=P + 1)  # 1 本目(P)も約定する
    assert s._pos == 1.0 and s.order_log[1][3] == T0 + 3 * M
    assert s._trade["avg"] == (P + math.ceil(raw)) / 2  # 建値は平均(端数が残りうる)
    s = sim()
    step(s, 0, ref=BUY)
    step(s, 1)
    step(s, 2, o=P + 5, lo=math.ceil(raw), c=P + 1)  # 安値 = 丸めた値段: 等号なしで約定しない
    assert s._pos == 0.5


@pytest.mark.parametrize("kw", [{"design": "v03", "at_max": "flip"}, {"design": "k1", "entry": "a"},
                                {"design": "k1", "entry": "b"}, {"design": "k1", "entry": "c"}])
def test_no_fractional_prices_in_orders_or_fills(kw):
    """1 円刻みの bitFlyer の足を通すと、置いた注文の値段・引き金と、取引の行の出の値段に端数が無い。建値は 1 本の
    約定なら整数、2 本の平均なら 0.5 円刻み。"""
    t0 = 1_546_300_800 * NS
    refs = _k1_walk(6000, 51, t0=t0) if kw["design"] == "k1" else _walk(6000, 52, t0)[0]
    _r, bars = _walk(6000, 53, t0)
    s = KatsuoLimitSim(fill_side="bad", foot_min=15 if kw["design"] == "k1" else 1, **kw)
    s.add_refs(refs)
    rows, seen = [], 0
    for b in bars:
        rows += s.feed(b)
        for o in s._orders:
            for v in (o.price, o.trig):
                if v is not None:
                    assert float(v).is_integer(), (o.kind, v)
                    seen += 1
    rows += s.finish()
    assert len(rows) > 10 and seen > 0
    assert all(float(r["exit_price"]).is_integer() for r in rows)
    assert all(float(r["entry_price"] * 2).is_integer() for r in rows)
