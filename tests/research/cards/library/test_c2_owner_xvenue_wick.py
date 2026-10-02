"""カード 2(c2_owner_xvenue_wick)の関数の試験: 手で作った小さな入力で、持ち高が意図どおりに出るか。

意図の地図(docs/RESEARCH/cards/c2_owner_xvenue_wick/INTENT_MAP.md)の ○ の各項に 1 つ以上。
各試験の docstring に項の番号を書く。カードは run_card(bot.bt.core の事象の流れ)を通して呼ぶ。

入力の作り方: bitFlyer の 1 分足は値段 100 の平らな足(ヒゲも実体も無い)。Binance の 1 分足は、
15 分足 1 本 = 1 分足 15 本で、1 本目に 4 本値を全部入れ、残り 14 本は終値で平ら(まとめると
指定した 4 本値になる)。行の時刻は 1 分足の始まり、遅れ 60 秒(カードの宣言どおり)。
"""
from __future__ import annotations

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import run_card
from bot.research.cards import CardError
from bot.research.cards.library.c2_owner_xvenue_wick import (FOOT_NS, FOOTS, ROW_LAG_NS, SERIES, SERIES_BITMEX,
                                                              SERIES_SPOT, SERIES_UM, C2OwnerXvenueWick, classify,
                                                              classify_detail)

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z(15 分の区切り)。試験の時刻で、データではない
DECL = {n: {"lag_ns": ROW_LAG_NS, "source": "試験の入力(行の時刻は分の始まり、分の終わりに使える)"}
        for n in SERIES_SPOT + SERIES_UM + SERIES_BITMEX}

P = 10_000.0  # Binance の 15 分足の始値。1 bp = 1.0
FLAT = (P, P, P, P)


def candle(color: int, body_bp: float, top_bp: float, under_bp: float, o: float = P):
    """4 本値(o, h, l, c)。color +1 陽線 / -1 陰線 / 0 同値足。長さは o に対する bp。"""
    bp = o * 1e-4
    c = o + color * body_bp * bp
    h = max(o, c) + top_bp * bp
    lo = min(o, c) - under_bp * bp
    return (o, h, lo, c)


def binance_rows(candles, start=T0, foot=15, names=SERIES, shape_last=False):
    """foot 分足の並びを 1 分足の行(4 系列、名前は names)にする。shape_last なら形を分に散らす(1 分目に高値、
    2 分目に安値、最後の 1 分に終値。ほかは始値で平ら)。足を最後まで待ち、全部の分をまとめないと形が分からない。"""
    out = {n: [] for n in names}
    for j, (o, h, lo, c) in enumerate(candles):
        for m in range(foot):
            ts = start + (j * foot + m) * M
            if shape_last and foot >= 3:
                vals = ((o, h, o, o) if m == 0 else (o, o, lo, o) if m == 1
                        else (o, max(o, c), min(o, c), c) if m == foot - 1 else (o, o, o, o))
            elif shape_last:
                vals = (o, h, lo, c)
            else:
                vals = (o, h, lo, c) if m == 0 else (c, c, c, c)
            for n, v in zip(names, vals):
                out[n].append((ts, float(v)))
    return out


def refs_from(rows):
    return {n: reference_series(n, rows[n], declarations=DECL) for n in rows}


def bf_bars(n_min, start=T0, empty=(), shapes=None):
    """bitFlyer の 1 分足 n_min 本(平ら)。empty の位置は出来高 0、shapes で形を上書き。"""
    out = []
    for i in range(n_min):
        o, h, lo, c = (shapes or {}).get(i, (100.0, 100.0, 100.0, 100.0))
        out.append(BarEvent(received_time_ns=start + (i + 1) * M, exchange_time_ns=start + (i + 1) * M,
                            start_time_ns=start + i * M, open=o, high=h, low=lo, close=c,
                            volume=0.0 if i in set(empty) else 1.0))
    return out


def run(candles, *, card=None, extra_min=1, empty=(), shapes=None, rows=None, foot=15):
    card = card or C2OwnerXvenueWick()
    rows = rows or binance_rows(candles, foot=foot)
    n_min = len(candles) * foot + extra_min
    r = run_card(card, bf_bars(n_min, empty=empty, shapes=shapes), references=refs_from(rows), declarations=DECL,
                 venue="bitflyer", symbol="FX_BTC_JPY")
    return r


def at_end(r, j):
    """j 本目の 15 分足が閉じた時刻(= bitFlyer の (j+1)*15 本目の足の終わり)の持ち高。"""
    i = (j + 1) * 15 - 1
    assert r.end_ns[i] == T0 + (j + 1) * FOOT_NS
    return r.exposure[i]


# 型: 陽線/陰線 × 上ヒゲ/下ヒゲ。ヒゲ 30 bp、実体 10 bp(ヒゲ > 実体、ヒゲ >= 19)
STRONG_BUY = candle(1, 10, 0, 30)    # 下ヒゲ陽線
WEAK_BUY = candle(-1, 10, 0, 30)     # 下ヒゲ陰線
STRONG_SELL = candle(-1, 10, 30, 0)  # 上ヒゲ陰線
WEAK_SELL = candle(1, 10, 30, 0)     # 上ヒゲ陽線
UP_NOSIG = candle(1, 10, 0, 0)       # 陽線、シグナル無し
DOWN_NOSIG = candle(-1, 10, 0, 0)    # 陰線、シグナル無し


# ---- classify(15 分足 1 本の判定) ----

def test_I1_wick_must_be_longer_than_body():
    """I-1 / I-5: 19 <= ヒゲ < 24 のとき、ヒゲが実体より長ければシグナル、短ければ無し。"""
    assert classify(*candle(1, 10, 0, 20))[1] == 1
    assert classify(*candle(1, 21, 0, 20))[1] == 0


def test_I5_length_gate_19():
    """I-5: ヒゲ > 実体でも 19 bp 未満はシグナルでない。19 bp ちょうどはシグナル(「19 以上」)。"""
    assert classify(*candle(-1, 5, 0, 18.9))[1] == 0
    assert classify(*candle(-1, 5, 0, 19.0))[1] == 1


def test_I6_big_wick_24_skips_the_body_condition():
    """I-6: 24 bp 以上のヒゲは、実体の方が長くてもシグナル。24 未満で実体の方が長ければ無し。"""
    assert classify(*candle(1, 40, 24.0, 0))[1] == -1
    assert classify(*candle(1, 40, 23.9, 0))[1] == 0


def test_I7_direction_from_the_longer_wick():
    """I-7: 向きは反対側のヒゲより長い方で決まる。両方同じ長さならシグナル無し。"""
    assert classify(*candle(1, 5, 30, 20)) == (1, -1, candle(1, 5, 30, 20)[1])
    assert classify(*candle(1, 5, 20, 30)) == (1, 1, candle(1, 5, 20, 30)[2])
    assert classify(*candle(1, 5, 30, 30))[1] == 0


def test_I19_doji_does_nothing():
    """I-19: 同値足(実体 0)は色 0・シグナル無し。持ち高も無効化も動かない。"""
    assert classify(*candle(0, 0, 0, 50)) == (0, 0, None)
    r = run([STRONG_BUY, candle(0, 0, 0, 0, o=STRONG_BUY[2] - 5.0)])  # 先端より下で終わる同値足
    assert at_end(r, 0) == 1.0 and at_end(r, 1) == 1.0


# ---- 強弱と、決済 / ドテン / 新規 ----

def test_I2_I3_strong_signal_flips_an_opposite_position():
    """I-2 / I-3: 強い(下ヒゲ陽線・上ヒゲ陰線)は反対の持ち高があってもドテンする。"""
    r = run([STRONG_SELL, STRONG_BUY, STRONG_SELL])
    assert [at_end(r, j) for j in range(3)] == [-1.0, 1.0, -1.0]


def test_I3_weak_signal_only_closes_an_opposite_position():
    """I-3: 弱い(上ヒゲ陽線・下ヒゲ陰線)は反対の持ち高を決済で止める(ドテンしない)。"""
    r = run([STRONG_SELL, WEAK_BUY, STRONG_BUY, WEAK_SELL])
    assert [at_end(r, j) for j in range(4)] == [-1.0, 0.0, 1.0, 0.0]


def test_I4_weak_signal_opens_when_flat():
    """I-4: 持ち高が無ければ、弱いシグナルでも新規に建てる。"""
    r = run([WEAK_BUY, WEAK_SELL])  # 1 本目で +1、2 本目は反対の持ち高なので決済 = 0
    assert [at_end(r, j) for j in range(2)] == [1.0, 0.0]
    r = run([WEAK_SELL])
    assert at_end(r, 0) == -1.0


def test_same_side_signal_keeps_one_unit_and_moves_the_line():
    """I-20(✕ 増し玉)の扱いと I-9: 同じ向きのシグナルでは持ち高は 1 のまま。無効化ラインは新しいシグナル足の
    先端に替わる(原典の lcprice はシグナルごとに上書き)。"""
    first = candle(1, 10, 0, 30)  # 先端 = 10,000 - 30 = 9,970
    second = candle(1, 10, 0, 30, o=10_100.0)  # 先端 = 10,100 - 30.3 = 10,069.7
    stop = (10_100.0, 10_100.0, 10_050.0, 10_060.0)  # 陰線、シグナル無し、終値 10,060 は新しい先端より下
    r = run([first, second, stop])
    assert [at_end(r, j) for j in range(3)] == [1.0, 1.0, 0.0]


# ---- 無効化ライン(O-3b、I-9)と、終値で見る(I-8) ----

def test_I9_exit_when_the_close_crosses_the_wick_tip_on_an_opposite_colored_bar():
    """I-9: 買い持ち(下ヒゲで入った)で、シグナル無しの陰線が先端以下で終われば 0。先端より上で終われば保持。"""
    tip = STRONG_BUY[2]  # 9,970
    hold = (10_010.0, 10_010.0, 9_975.0, 9_980.0)  # 陰線、下ヒゲ 5 bp でシグナル無し、終値 9,980 > 先端
    cross = (9_980.0, 9_980.0, 9_960.0, tip)  # 陰線、終値 = 先端(以下なので抜けた)
    assert classify(*hold)[1] == 0 and classify(*cross)[1] == 0
    r = run([STRONG_BUY, hold, cross])
    assert [at_end(r, j) for j in range(3)] == [1.0, 1.0, 0.0]


def test_I9_short_side_mirror():
    """I-9(売り側): 売り持ちで、シグナル無しの陽線が先端以上で終われば 0。"""
    tip = STRONG_SELL[1]  # 10,030
    cross = (10_020.0, 10_040.0, 10_020.0, 10_035.0)  # 陽線、上ヒゲ 5 < 実体 15、終値 > 先端
    hold = (10_000.0, 10_025.0, 10_000.0, 10_020.0)  # 陽線、上ヒゲ 5 bp でシグナル無し、終値 10,020 < 先端
    assert classify(*cross)[1] == 0 and cross[3] >= tip
    assert classify(*hold)[:2] == (1, 0) and hold[3] < tip
    r = run([STRONG_SELL, hold, cross])
    assert [at_end(r, j) for j in range(3)] == [-1.0, -1.0, 0.0]


def test_I9_color_condition_same_colored_bar_does_not_check_the_line():
    """I-9 の色の条件(原典 502-511 / 524-533、KATSUO_INTENT_MAP §3-d): 買い持ちで、先端より下で終わっても
    陽線(持ち高と同じ向きの足)なら無効化を見ない。"""
    below = (9_900.0, 9_910.0, 9_900.0, 9_905.0)  # 陽線、シグナル無し、終値 9,905 < 先端 9,970
    assert classify(*below)[:2] == (1, 0)
    r = run([STRONG_BUY, below])
    assert [at_end(r, j) for j in range(2)] == [1.0, 1.0]


def test_I9_signal_bar_does_not_check_the_old_line():
    """I-9(原典どおり、KATSUO_INTENT_MAP §3-b): シグナルが出た足では古い先端を見ない。買い持ちで、古い先端
    9,970 より下で終わる下ヒゲ陰線(弱い買い)が来ても降りず、ラインがその足の安値に替わる。"""
    new = (9_960.0, 9_960.0, 9_920.0, 9_950.0)  # 陰線 実体 10、下ヒゲ 30 → 弱い買い。終値 9,950 < 9,970
    assert classify(*new) == (-1, 1, 9_920.0)
    after = (9_950.0, 9_950.0, 9_930.0, 9_935.0)  # 陰線、シグナル無し、終値 9,935 > 新しい先端 9,920
    assert classify(*after)[:2] == (-1, 0)
    r = run([STRONG_BUY, new, after])
    assert [at_end(r, j) for j in range(3)] == [1.0, 1.0, 1.0]


def test_I8_intrabar_touch_is_not_an_exit():
    """I-8: 足の途中で先端を割っても、終値が先端より上なら降りない(確定した足の形だけを見る)。"""
    tip = STRONG_BUY[2]
    dip = (10_000.0, 10_000.0, tip - 5.0, tip + 10.0)  # 陰線。安値 9,965 は先端を割るが終値 9,980 は上
    assert classify(*dip)[:2] == (-1, 0)  # 下ヒゲ 15 bp < 19 でシグナル無し → 無効化を見る足
    r = run([STRONG_BUY, dip])
    assert at_end(r, 1) == 1.0


def test_I8_decides_only_after_the_15_minute_bar_closes():
    """I-8 / 未来を読まない: 15 分足が閉じる 1 分前までは持ち高 0、閉じた足の終わりで +1。
    途中の 1 分足が下ヒゲの形をしていても、閉じる前には動かない。"""
    rows = binance_rows([STRONG_BUY])
    r = run([STRONG_BUY], rows=rows)
    assert np.all(r.exposure[:14] == 0.0)
    assert at_end(r, 0) == 1.0


def test_I17_signal_is_read_on_the_15_minute_aggregate():
    """I-17: 1 分足 1 本ずつはシグナルの形でなくても、15 分にまとめた足が下ヒゲ陽線ならシグナル。"""
    o = P
    path = [(o, o, o - 15, o - 15)] + [(o - 15 - k, o - 15 - k, o - 16 - k, o - 16 - k) for k in range(14)]
    path[-1] = (o - 29, o + 10, o - 30, o + 10)  # 最後の 1 分で戻して陽線で終える
    rows = {n: [] for n in SERIES}
    for m, vals in enumerate(path):
        for n, v in zip(SERIES, vals):
            rows[n].append((T0 + m * M, float(v)))
    agg = (o, max(p[1] for p in path), min(p[2] for p in path), path[-1][3])
    assert classify(*agg)[1] == 1  # まとめると 下ヒゲ 30 bp > 実体 10 bp の陽線
    assert all(classify(*p)[1] == 0 for p in path)  # 1 分足 1 本ずつではどれもシグナル無し
    r = run([agg], rows=rows)
    assert at_end(r, 0) == 1.0


# ---- 執行は bitFlyer、シグナルは外(I-13 / I-16)----

def test_I13_I16_exposure_is_on_bitflyer_bars_and_bitflyer_wicks_are_not_read():
    """I-13: 持ち高は bitFlyer の 1 分足ごとに出る。I-16: bitFlyer の足に長いヒゲがあっても、外の足が平らなら 0。"""
    shapes = {i: (100.0, 100.5, 90.0, 100.5) for i in range(15)}  # 下ヒゲの長い陽線を毎分
    r = run([FLAT], shapes=shapes)
    assert r.venue == "bitflyer" and len(r.exposure) == 16
    assert np.all(r.exposure == 0.0)


# ---- データの扱い(＋)----

def test_catch_up_when_the_bitflyer_bar_at_the_boundary_is_empty():
    """＋ 追いつき: 15 分足が閉じる時刻の bitFlyer の足が空(出来高 0)なら、次の空でない足で判定が入る。"""
    r = run([STRONG_BUY], extra_min=2, empty=(14,))
    assert not r.decided[14] and r.decided[15]
    assert r.exposure[15] == 1.0


def test_catch_up_processes_every_closed_bar_in_order():
    """＋ 追いつき: 2 本の 15 分足が呼ばれない間に閉じても、古い順に両方判定する(買い → 弱い売りで決済 = 0)。"""
    empty = tuple(range(14, 30))
    r = run([STRONG_BUY, WEAK_SELL], extra_min=2, empty=empty)
    assert r.exposure[30] == 0.0
    r2 = run([STRONG_BUY, UP_NOSIG], extra_min=2, empty=empty)
    assert r2.exposure[30] == 1.0


def test_exposure_values_and_repeatability():
    """持ち高は −1 / 0 / +1 だけ。同じ入力で 2 回走らせると一致する。"""
    seq = [STRONG_SELL, WEAK_BUY, STRONG_BUY, DOWN_NOSIG, WEAK_SELL, UP_NOSIG, FLAT, STRONG_SELL]
    a, b = run(seq), run(seq)
    assert set(np.unique(a.exposure)) <= {-1.0, 0.0, 1.0}
    assert np.array_equal(a.exposure, b.exposure)


def test_mismatched_series_are_refused():
    """4 本値の行の時刻が揃わなければ止める(黙ってずれた足を作らない)。"""
    rows = binance_rows([STRONG_BUY])
    rows["binance_low"] = [(t + NS, v) for t, v in rows["binance_low"]]
    with pytest.raises(Exception):
        run([STRONG_BUY], rows=rows)


# ---- 変種(差し戻し 1 回目のリードの決定)----

@pytest.mark.parametrize("foot", FOOTS)
def test_foot_variants_aggregate_on_the_utc_clock(foot):
    """足の長さの変種 {1, 3, 5, 15, 30, 60} 分: 区切りは UTC の時計(T0 = 毎時 0 分)。足が閉じる 1 分前までは 0、
    閉じた足の終わりで判定が入る。2 本目(弱い売り)で決済して 0。形は各足の最後の 1 分にだけ置く。"""
    rows = binance_rows([STRONG_BUY, WEAK_SELL], foot=foot, shape_last=True)
    r = run([STRONG_BUY, WEAK_SELL], card=C2OwnerXvenueWick(foot_min=foot), foot=foot, rows=rows)
    assert np.all(r.exposure[:foot - 1] == 0.0)
    assert r.end_ns[foot - 1] == T0 + foot * M and r.exposure[foot - 1] == 1.0
    assert r.end_ns[2 * foot - 1] == T0 + 2 * foot * M and r.exposure[2 * foot - 1] == 0.0


def test_foot_default_is_15_and_other_lengths_are_refused():
    """既定は原典の 15 分。{1, 3, 5, 15, 30, 60} 以外(根拠の無い長さ)は拒む。"""
    assert C2OwnerXvenueWick().foot_min == 15
    for bad in (10, 0, 15.0, 120):
        with pytest.raises(CardError):
            C2OwnerXvenueWick(foot_min=bad)


def test_30_minute_bar_differs_from_two_15_minute_bars():
    """30 分足は 15 分足 2 本と別の足になる: 15 分ずつでは平らな足と下げの足でも、まとめると下ヒゲ陽線。"""
    first = (P, P, P - 30.0, P - 30.0)  # 15 分: 陰線(ヒゲ無し)
    second = (P - 30.0, P + 10.0, P - 30.0, P + 10.0)  # 15 分: 陽線(ヒゲ無し)
    assert classify(*first)[1] == 0 and classify(*second)[1] == 0
    rows = {n: [] for n in SERIES}
    for j, (o, h, lo, c) in enumerate([first, second]):
        for m in range(15):
            vals = (o, h, lo, c) if m == 0 else (c, c, c, c)
            for n, v in zip(SERIES, vals):
                rows[n].append((T0 + (j * 15 + m) * M, float(v)))
    r15 = run([first, second], rows=rows)
    assert np.all(r15.exposure == 0.0)
    r30 = run([(P, P + 10.0, P - 30.0, P + 10.0)], rows=rows, card=C2OwnerXvenueWick(foot_min=30), foot=30)
    assert r30.exposure[29] == 1.0  # まとめた 30 分足 = 下ヒゲ 30 bp・実体 10 bp の陽線


@pytest.mark.parametrize("names", [SERIES_SPOT, SERIES_UM, SERIES_BITMEX])
def test_signal_source_variants_read_only_their_own_series(names):
    """I-11a の変種 (a) 現物 (b) USD-M (c) BitMEX: 指定した名前の 4 系列だけを読む。ほかの名前の系列に
    シグナルの形があっても動かない。"""
    other = SERIES_UM if names != SERIES_UM else SERIES_SPOT
    rows = {**binance_rows([STRONG_BUY], names=names), **binance_rows([STRONG_SELL], names=other)}
    r = run([STRONG_BUY], rows=rows, card=C2OwnerXvenueWick(series=names))
    assert at_end(r, 0) == 1.0
    assert [s.name for s in C2OwnerXvenueWick(series=names).requires] == list(names)


def test_signal_source_must_be_four_distinct_names():
    for bad in (SERIES_SPOT[:3], ("a", "a", "b", "c")):
        with pytest.raises(CardError):
            C2OwnerXvenueWick(series=bad)


def test_diagnostic_log_separates_the_19_and_24_branches():
    """診断(検定の数に入れない、L-053): シグナルごとに 19 の枝・24 の枝のどちらに当たったかを残す。"""
    only19 = candle(1, 10, 0, 20)  # ヒゲ 20 > 実体 10、24 未満
    only24 = candle(1, 40, 0, 25)  # ヒゲ 25 < 実体 40、24 以上
    both = candle(1, 10, 0, 30)
    assert classify_detail(*only19)[3:] == (True, False)
    assert classify_detail(*only24)[3:] == (False, True)
    assert classify_detail(*both)[3:] == (True, True)
    card = C2OwnerXvenueWick()
    run([only19, FLAT, only24, both], card=card)
    assert [(e, sig, a, b) for e, sig, a, b in card.signal_log] == [
        (T0 + 15 * M, 1, True, False), (T0 + 45 * M, 1, False, True), (T0 + 60 * M, 1, True, True)]
