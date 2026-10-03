"""カード 4(c4_owner_matilda_range)の関数の試験: 手で作った小さな入力で、持ち高が意図どおりに出るか。

意図の地図(docs/RESEARCH/cards/c4_owner_matilda_range/INTENT_MAP.md)の ○ と △ の各項に 1 つ以上。
各試験の名前と docstring に項の番号を書く。カードは run_card(bot.bt.core の事象の流れ)を通して呼ぶ。
オーナーの答え(INTENT_MAP §8、L-564)で変えた点: 幅の門 = 値段に対する割合 / 比の門 = 10 に固定 / 段(1 段 = 1/7)込み。
L-565 のリードの指示: 水準を引数で受ける(表は原典の値だけ、表の外は拒む)、足の長さ bar_min、部品ごとの切り替え
(width_gate・trend_gate・time_exit・levels)。第 3 稿(リードの決め、原典 v37 の動きに合わせる。L-564・L-566):
段は前に段を積んだ判定の終値から step × 平均実体 を越えたら 1 本の足で 1 段ずつ足す(v37 843・867 行)/ 一方向の動きの
間も follow なら同じ規則で段を足す / 利確の既定 = 形 2(建値からの値幅)+ 按分 + 0.8 + 20 分の緩め(v37 881・
897〜898・911〜912 行)/ 建値の守りは値段に対する割合。利確の線の形 1(中心 ∓ 0.8 × 平均実体)を確かめる試験は
exit_mode=1 を明示する。
第 4 稿(リードの決め、v37 の動きにそろえる): 一方向の動きの間は持ち高 0 からは入らない(flat。follow は入る)、
持ち高は動きと反対なら閉じ、同じ向きなら形 2 の利確と段の規則(時間成行なし)/ 動きの始まり・解けた足で閉じない
(trend_close・trend_end_close 既定 False)/ 足 1 本 = v37 の巡回 1 回(入り → 決済の判定)で、反対の合図の足は
閉じるだけ / 買いだけの起点の戻りは buy_ref_reset(既定 False)。

入力の作り方: bitFlyer の 1 分足。値段は P = 1,000,000 円の近く。「往復の足」は偶数番目が P → P+200 の陽線、
奇数番目が P+200 → P の陰線(実体 200 円、ヒゲ無し)。窓 40 分なら、40 本目(番号 39)の足の終わりで
初めて窓が満ちる。数字は試験の入力で、データではない。
持ち高は「段の数 ÷ 7」。L = 1/7 を 1 段とする。
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent
from bot.research.cards import CardError, run_card
import bot.research.cards.library.c4_owner_matilda_range as c4
from bot.research.cards.library.c4_owner_matilda_range import (BAR_MIN, ENTRY_K, EXIT_K, HOLD_MAX_MIN, MIN_WIDTH_RATIO, N_LEVELS, ON_TRENDS,
                                                                RANGE_FROMS, STEP_K, VR_MAX, WINDOWS,
                                                                C4OwnerMatildaRange)

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z。試験の時刻で、データではない
P = 1_000_000.0
L = 1.0 / 7.0  # 1 段


def bar(i, o, c, h=None, lo=None, vol=1.0):
    h = max(o, c) if h is None else h
    lo = min(o, c) if lo is None else lo
    return BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M,
                    start_time_ns=T0 + i * M, open=o, high=h, low=lo, close=c, volume=vol)


def osc(i, amp=200.0, p=P):
    return bar(i, p, p + amp) if i % 2 == 0 else bar(i, p + amp, p)


def run(bars, card=None):
    r = run_card(card or C4OwnerMatildaRange(), bars, references={}, declarations={}, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return {int(e): float(x) for e, x in zip(r.end_ns, r.exposure)}


def ex(r, i):
    return r[T0 + (i + 1) * M]


def base(n=39, amp=200.0, p=P):
    return [osc(i, amp, p) for i in range(n)]


def test_constants_are_from_the_source():
    """水準は原典の値と、オーナーの答え(L-564)の値(INTENT_MAP §2 の I-5・I-6・I-8・I-9・I-12・I-19)。"""
    assert ENTRY_K == 2.0 and EXIT_K == 0.8 and STEP_K == 1.0 and N_LEVELS == 7
    assert HOLD_MAX_MIN == 40 and VR_MAX == 10.0 and BAR_MIN == 1 and c4.ALERT_MIN == 20
    assert c4.EXIT_MODE == 2 and c4.EXIT_STEP == 0.8  # v37 のコードの実際の利確(881 行)が既定
    assert c4.EXIT_GUARD_RATIO == 100.0 / 1152502.0  # v52 の 100 円 ÷ 2019-09-04 の値段(幅の門と同じ)
    assert c4.EXIT_SETTINGS == (0.0, 0.8, 2.0) and c4.EXIT_STEPS == (0.8, 0.0) and c4.EXIT_MODES == (0, 1, 2)
    assert MIN_WIDTH_RATIO == 150.0 / 1152502.0  # 150 円 ÷ 2019-09-04(日本時間)の終値の中央値


def test_I5_short_above_and_long_below_center():
    """I-5: 中心から上に離れたら売り、下に離れたら買い(中心 ± 2 × 平均実体)。離れが 2〜3 倍なら 1 段。"""
    up = run(base() + [bar(39, P, P + 1000)])  # 中心 P+500、平均実体 220、門 P+940 < 終値 P+1000(3 倍の P+1160 未満)
    assert ex(up, 39) == pytest.approx(-L)
    down = run(base() + [bar(39, P + 200, P - 800)])  # 中心 P-300、門 P-740 > 終値 P-800
    assert ex(down, 39) == pytest.approx(L)
    near = run(base() + [bar(39, P, P + 900)])  # 中心 P+450、平均実体 217.5、門 P+885 < P+900
    assert ex(near, 39) == pytest.approx(-L)
    inside = run(base() + [bar(39, P, P + 850)])  # 中心 P+425、平均実体 216.25、門 P+857.5 > P+850
    assert ex(inside, 39) == 0.0


def test_I19_one_level_per_bar_from_flat():
    """I-19: 何も持たない所から建てるのは 1 段だけ(原典 v37 843・844 行: 1 回の巡回で order_limit(sizemin) を 1 つ。
    最初の指値は buy_status / sell_status の値段が 9999999 / 0(231・232 行)なので必ず置かれる)。
    中心から 3 倍・4 倍離れていても 1 本の足では 1 段。"""
    two = run(base() + [bar(39, P, P + 1600)])  # 中心 P+800、平均実体 235、離れ 800/235 = 3.40
    assert ex(two, 39) == pytest.approx(-L)
    three = run(base() + [bar(39, P, P + 2000)])  # 中心 P+1000、平均実体 245、離れ 4.08。比 8.2
    assert ex(three, 39) == pytest.approx(-L)


def test_I19_next_level_counts_from_the_close_of_the_previous_level():
    """I-19: 次の段は、前に段を積んだ判定の足の終値から step_setting × 平均実体 を越えて離れたとき(原典 v37 843 行
    price < buy_status['price'] − step、867 行 price > sell_status['price'] + step。比べは等号なし)。
    中心からの離れ(3.4 倍)ではなく、前の段の値段からの離れで決まる。"""
    head = base() + [bar(39, P, P + 1600)]  # 1 段売り。前の段の値段 P+1600
    near = run(head + [bar(40, P + 1600, P + 1700)], C4OwnerMatildaRange(exit_mode=1))
    # 40: 平均実体 (38 × 200 + 1600 + 100) / 40 = 232.5、中心 P+850、合図あり(P+1700 > P+1315)。
    # 前の段から 100 円 < 232.5 → 足さない
    assert ex(near, 40) == pytest.approx(-L)
    far = run(base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 1300)])
    # 40: 平均実体 222.5、中心 P+650、合図あり(P+1300 > P+1095)。前の段 P+1000 から 300 > 222.5 → 2 段
    assert ex(far, 40) == pytest.approx(-2 * L)


def climb_bars():
    """番号 39 で P → P+1000(1 段売り)、40〜44 は 300 円ずつ上がる陽線(P+1000 → … → P+2500)。"""
    return base() + [bar(39, P, P + 1000)] + [bar(40 + j, P + 1000 + 300 * j, P + 1300 + 300 * j) for j in range(5)]


def window_ratio(bars, i):
    """番号 i の足の終わりの窓(番号 i−39〜i の 40 本。どれも出来高あり)の 比 = 実体の端の幅 ÷ 平均実体。"""
    w = bars[i - 39:i + 1]
    hi = max(max(b.open, b.close) for b in w)
    lo = min(min(b.open, b.close) for b in w)
    return (hi - lo) / (sum(abs(b.close - b.open) for b in w) / 40)


def test_I19_levels_can_pass_three_while_the_ratio_gate_is_below_10():
    """I-19・I-9: 第 2 稿は段を中心から数えたので、比 < 10 の間は |終値 − 中心| < 5 × 平均実体 で 3 段(3/7)までだった。
    前の段から数える形では、比 < 10 のまま 5 段まで積める(上限 3 が無くなる)。比が 10 を越えた足では、上向きの動きと反対の売りなので閉じて 0(v37 1027〜1028 行)。
    40: 平均実体 222.5 / 41: 225 / 42: 227.5 / 43: 230。どの足も 前の段 + 平均実体 < 終値、中心 + 2 × 平均実体 < 終値。
    売りで値段が上がり続けるので、既定の利確(形 2: 終値 < 建値 − 値幅)には届かない。"""
    bars = climb_bars()
    r = run(bars)
    for i in range(39, 44):
        assert window_ratio(bars, i) < VR_MAX, i
    assert window_ratio(bars, 43) == pytest.approx(2200 / 230)
    assert [ex(r, i) for i in range(39, 44)] == pytest.approx([-L, -2 * L, -3 * L, -4 * L, -5 * L])
    assert window_ratio(bars, 44) == pytest.approx(2500 / 232.5)  # 10.75 >= 10
    assert ex(r, 44) == 0.0


def stack_bars():
    """番号 39 で 1 段売り(P+1000)、40 で 2 段に積み(P+1600 > P+1000 + 230)、41 で合図が消えても 2 段のまま。"""
    return base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 1600), bar(41, P + 1600, P + 1200)]


def m1():
    """利確の形 1(中心 ∓ exit_setting × 平均実体)を確かめる試験の関数(既定は形 2)。"""
    return C4OwnerMatildaRange(exit_mode=1)


def test_I19_levels_are_added_and_never_reduced_until_flat():
    """I-19: 同じ向きにさらに離れたら段を足す。段は利確・時間・一方向の動きで 0 になるまで減らさない
    (原典 v37 881 行 order_exit の量 = mybtc 全部、703〜714 行 reflesh = mybtc 全部の成行)。
    利確の形 1 で見る(既定の形 2 では 41 で按分の値幅に届いて閉じる。test_exit_prorate_…)。"""
    r = run(stack_bars(), m1())
    assert ex(r, 39) == pytest.approx(-L)
    assert ex(r, 40) == pytest.approx(-2 * L)  # 平均実体 230、前の段 P+1000 から 600 > 230
    assert ex(r, 41) == pytest.approx(-2 * L)  # 平均実体 235、中心 P+800、合図(P+1270)は消えたが減らさない


def test_I6_take_profit_at_center_plus_exit_k_vola_closes_all_levels():
    """I-6: 売りは 終値 <= 中心 + 0.8 × 平均実体 で、積んだ段を全部 0 にする(中心ちょうどまで待たない)。"""
    r = run(stack_bars() + [bar(42, P + 1200, P + 900)], m1())  # 中心 P+800、平均実体 237.5、利確の線 P+990 >= P+900
    assert ex(r, 41) == pytest.approx(-2 * L)
    assert ex(r, 42) == 0.0


def test_I6_no_take_profit_above_the_line():
    """I-6: 売りは 終値 > 中心 + 0.8 × 平均実体 の間は利確しない。"""
    r = run(stack_bars() + [bar(42, P + 1200, P + 1000)], m1())  # 平均実体 235、利確の線 P+988 < P+1000
    assert ex(r, 42) == pytest.approx(-2 * L)


def test_I6_buy_side_take_profit_line_is_below_center():
    """I-6: 買いは 終値 >= 中心 − 0.8 × 平均実体 で 0。線の手前では持ったまま。"""
    head = base() + [bar(39, P + 200, P - 800)]  # 中心 P-300、平均実体 220 → 1 段買い
    hold = run(head + [bar(40, P - 800, P - 500)], m1())  # 平均実体 222.5、利確の線 P-478 > 終値 P-500
    assert ex(hold, 39) == pytest.approx(L) and ex(hold, 40) == pytest.approx(L)
    take = run(head + [bar(40, P - 800, P - 450)], m1())  # 平均実体 223.75、利確の線 P-479 <= 終値 P-450
    assert ex(take, 40) == 0.0


def test_I6_I7_I3_take_profit_then_trade_again():
    """I-6: 利確。I-7: 往復を重ねる。I-3: 中心は毎分動く(41 本目は新しい中心で判定)。"""
    bars = base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 450), bar(41, P + 450, P + 1200)]
    r = run(bars, m1())
    assert ex(r, 39) == pytest.approx(-L)
    assert ex(r, 40) == 0.0  # 中心 P+500、利確の線 P+682 >= 終値 P+450
    assert ex(r, 41) == pytest.approx(-L)  # 窓が 1 分進み、上端 P+1200・中心 P+600・平均実体 242.5・門 P+1085


def test_I18_opposite_signal_closes_this_bar_and_enters_the_next_bar():
    """I-18・第 4 稿(v37 の巡回 1 回 = 足 1 本): 反対側の入りの条件がそろった足では全部閉じるだけ(1083〜1096 行:
    入りの指値を置いたあと exit_judge が 1010・1018 行で exit_flg = 3 → reflesh が指値ごと取り消して成行で閉じる)。
    次の足でも合図が続いていれば、反対の 1 段目を建てる。
    40: 中心 P+200、平均実体 255、終値 P-600 < P-310 → 閉じて 0。
    41: 平均実体 252.5、上端 P+1000・下端 P-700・中心 P+150、終値 P-700 < P-355 → 1 段の買い。"""
    r = run(base() + [bar(39, P, P + 1000), bar(40, P + 1000, P - 600), bar(41, P - 600, P - 700)])
    assert ex(r, 39) == pytest.approx(-L)
    assert ex(r, 40) == 0.0
    assert ex(r, 41) == pytest.approx(L)


def clock_bars():
    """窓 60 分。番号 59 で 1 段売り(P+1000)、70 で 2 段に積む(P+1600)、71〜99 は合図が出ても前の段 P+1600 から
    離れないので 2 段のまま、99 で 40 分。"""
    out = base(59) + [bar(59, P, P + 1000)]
    out += [bar(i, P + 700, P + 900) if i % 2 == 0 else bar(i, P + 900, P + 700) for i in range(60, 70)]
    out.append(bar(70, P + 900, P + 1600))
    out += [bar(i, P + 1100, P + 1300) if i % 2 else bar(i, P + 1300, P + 1100) for i in range(71, 102)]
    return out


def test_I12_time_exit_counts_from_the_first_level_and_adding_levels_does_not_reset_it():
    """I-12: 建ててから 40 分(原典 alert_count × 2)で全部決済。段を足しても時計は戻さない
    (原典 v37 1050・1066 行: poschangetime は売り買いの向きが変わったときだけ更新)。中心に届かなくても出る。"""
    r = run(clock_bars(), C4OwnerMatildaRange(window_min=60, exit_mode=1))
    assert ex(r, 59) == pytest.approx(-L)  # 中心 P+500、平均実体 213.3、離れ 2.34
    assert ex(r, 69) == pytest.approx(-L)  # 利確の線 P+670.7 < 終値 P+700
    assert ex(r, 70) == pytest.approx(-2 * L)  # 平均実体 221.7、前の段 P+1000 から 600。中心 P+800、離れ 3.61
    assert ex(r, 98) == pytest.approx(-2 * L)  # 39 分。利確の線 P+977 < 終値 P+1100
    assert ex(r, 99) == 0.0  # 59 本目から 40 分(70 本目からは 29 分)
    assert ex(r, 100) == 0.0  # 終値 P+1100 は入りの線 P+1243 の内側
    assert ex(r, 101) == pytest.approx(-L)  # 終値 P+1300 > P+1243 で、1 段から建て直す(段は 0 に戻った)


def test_I8_width_gate_is_a_ratio_of_the_price():
    """I-8(△): 幅 ÷ 終値 が 150 / 1,152,502(= 0.0130%)に満たなければ建てない。
    円の固定値ではないので、140 円の幅は 100 万円なら建て、200 万円なら建てない。"""
    assert ex(run(base(amp=20.0) + [bar(39, P, P + 140)]), 39) == pytest.approx(-L)  # 140/1000140 = 0.01400%
    assert ex(run(base(amp=20.0) + [bar(39, P, P + 120)]), 39) == 0.0  # 120/1000120 = 0.01200%
    p2 = 2 * P
    assert ex(run(base(amp=20.0, p=p2) + [bar(39, p2, p2 + 140)]), 39) == 0.0  # 140/2000140 = 0.00700%


def gate_bars(z):
    """番号 0 は P+130 → P-50 の陰線(実体 180)。1〜38 は P と P+18 の往復(実体 18)。39 は P → P+100、
    40 は P+100 → P+z。39 では番号 0 が窓の中で幅 180、40 では番号 0 が窓から出て幅 z。"""
    return ([bar(0, P + 130, P - 50)] + [osc(i, 18.0) for i in range(1, 39)]
            + [bar(39, P, P + 100), bar(40, P + 100, P + z)])


def test_I8_gate_also_stops_adding_levels():
    """I-8・I-19: 幅の門を割っている間は、段も足さない(原典 v37 976・993 行で entry_flg = 0 → order_sell を
    呼ばない)。持っている段は利確・時間で閉じるまで持つ。"""
    # 39: 中心 P+40、平均実体 24.1、離れ 2.49 → 1 段。幅 180 / P+100 は門を越える。比 7.5
    # 40: 幅 125、125 / 1,000,125 = 0.01250% < 0.01302%(門を割る)。中心 P+62.5、平均実体 20.2、離れ 3.09、
    #     前の段 P+100 から 25 > 20.2
    shut = run(gate_bars(125.0))
    assert ex(shut, 39) == pytest.approx(-L)
    assert ex(shut, 40) == pytest.approx(-L)  # 門が開いていれば 2 段
    # 対照: 40 の幅 135(0.01350% >= 門)。平均実体 20.5、前の段 P+100 から 35 > 20.5 → 2 段に足す
    open_ = run(gate_bars(135.0))
    assert ex(open_, 40) == pytest.approx(-2 * L)


def trend_bars():
    """40 本続けて 100 円ずつ上がる足(番号 0〜39)。番号 39 で幅 4,000 円、平均実体 100 円、比 40。"""
    return [bar(i, P + 100 * i, P + 100 * (i + 1)) for i in range(40)]


def test_I9_I14_I15_I16_stand_aside_on_one_way_move():
    """I-9(△)・I-14・I-15・I-16: 比(幅 ÷ 平均実体)が 10 以上なら一方向の動きとみなし、建てない(静観)。
    follow なら動きの向きに 1 段から持つ(I-13。原典 v37 1002〜1005 行 entry_flg = break_flg → 1083〜1090 行の
    order_buy / order_sell で 1 段目)。"""
    assert ex(run(trend_bars()), 39) == 0.0
    assert ex(run(trend_bars(), C4OwnerMatildaRange(on_trend="follow")), 39) == pytest.approx(L)


def test_I9_opposite_position_is_closed_by_the_move():
    """I-9・第 4 稿: 一方向の動きと反対の向きの持ち高は、その足で閉じる(v37 1002〜1005 行: 持ち高があれば
    entry_flg = break_flg、1027〜1028 行: 反対の entry_flg で exit_flg = 3)。flat は持ち高 0 からは入らない
    (1002 行 b_signal == 0 and posside == 'None' → entry_flg = 0。b_signal は使わない)。"""
    bars = base() + [bar(39, P, P + 1000)] + [bar(40 + j, P + 1000 + 2000 * j, P + 1000 + 2000 * (j + 1))
                                              for j in range(3)]
    r = run(bars)
    assert ex(r, 39) == pytest.approx(-L)
    assert ex(r, 40) == 0.0  # 上端 P+3000、比 3000 / 265 > 10、終値は中心 P+1500 より上 → 上向きの動き
    assert ex(r, 42) == 0.0
    # follow: 40 で閉じ(exit_flg = 3)、41 で動きの向きに 1 段(窓 2〜41、平均実体 310、比 16、終値 P+5000 > 中心)。
    # 42: 建値 P+5000(42 の始値)、終値 P+7000 > 建値 + 値幅 → 一方向の動きの間も形 2 の利確で 0(1029〜1030 行)
    fol = run(bars, C4OwnerMatildaRange(on_trend="follow"))
    assert ex(fol, 40) == 0.0 and ex(fol, 41) == pytest.approx(L) and ex(fol, 42) == 0.0


def test_I13_follow_adds_levels_during_the_move_with_the_same_step_rule():
    """I-13・I-19: follow は一方向の動きの間も、前に段を積んだ判定の終値から step_setting × 平均実体 を越えて
    有利な側(買いなら下)へ離れたら 1 段足す(原典 v37 1002〜1005 行で break_flg の間も entry_flg = break_flg、
    order_buy 843 行は break の間も同じ間隔の規則。量は sizemin、844 行)。段は減らさない。
    40: 窓 1〜40、平均実体 (39 × 100 + 200) / 40 = 102.5、上端 P+4000・下端 P+100・中心 P+2050、比 38 → 上向きのまま。
        前の段 P+4000 から 200 円下 > 102.5 → 2 段。
    41: 平均実体 101.25、前の段 P+3800 から 50 円下 < 101.25 → 2 段のまま(第 2 稿は 1 段に戻していた)。"""
    bars = trend_bars() + [bar(40, P + 4000, P + 3800), bar(41, P + 3800, P + 3750)]
    r = run(bars, C4OwnerMatildaRange(on_trend="follow"))
    assert ex(r, 39) == pytest.approx(L)
    assert ex(r, 40) == pytest.approx(2 * L)
    assert ex(r, 41) == pytest.approx(2 * L)
    flat = run(bars)
    assert ex(flat, 40) == 0.0 and ex(flat, 41) == 0.0


def resume_bars():
    """番号 0〜39 は上げ続け。そのあと k = 1, 2, … で P+4000 と P+5000 の間を実体 1,000 円で往復する
    (k が奇数で P+5000 に、偶数で P+4000 に終わる)。k = 13 で比が 10 を下回り、k = 30 で中心が P+4000 に
    なって偶数の足の終値が中心に届く。"""
    out = trend_bars()
    for k in range(1, 33):
        i = 39 + k
        out.append(bar(i, P + 4000, P + 5000) if k % 2 else bar(i, P + 5000, P + 4000))
    return out


def test_I10_I13_resume_only_when_price_returns_to_center():
    """I-10: 一方向の動きの後は、比が下がっただけでは再開せず、価格が新しい中心へ戻ったときに再開する。
    I-13: follow(逆転順張り)は、その間ずっと動きの向きに持つ(この足の並びでは、前の段 P+4000 より下に
    平均実体以上離れる終値が無いので 1 段 = +1/7 のまま)。
    第 4 稿: 形 0(利確の線なし)で、状態が続く間 follow の 1 段が持たれ続けることを見る。状態が解けるのは
    k = 30 の足の終わり(v37 952〜965 行 break_off_judge は巡回の最後)で、既定ではその足で持ち高を 0 にしない。
    trend_end_close=True(第 3 稿までの動き)なら k = 30 で 0。flat は持ち高 0 からは入らないので 0 のまま。"""
    r = run(resume_bars(), C4OwnerMatildaRange(on_trend="follow", exit_mode=0))
    k13_ratio = (5000 - 1300) / ((27 * 100 + 13 * 1000) / 40)
    assert k13_ratio < 10
    for k in range(0, 31):
        assert ex(r, 39 + k) == pytest.approx(L), k
    end = run(resume_bars(), C4OwnerMatildaRange(on_trend="follow", exit_mode=0, trend_end_close=True))
    assert ex(end, 39 + 29) == pytest.approx(L)
    assert ex(end, 39 + 30) == 0.0  # 中心 P+4000 に終値 P+4000 が戻った
    flat = run(resume_bars())
    assert all(ex(flat, 39 + k) == 0.0 for k in range(0, 31))


def test_I17_range_from_bodies_ignores_wicks():
    """I-17: 既定はヒゲを除いた実体の端でレンジを測る(原典 beard_ignore)。ヒゲで測る変種と分かれる。"""
    bars = base() + [bar(39, P, P + 1000)]
    bars[20] = bar(20, P, P + 200, h=P + 1800)
    assert ex(run(bars), 39) == pytest.approx(-L)  # 実体: 上端 P+1000、中心 P+500
    assert ex(run(bars, C4OwnerMatildaRange(range_from="wick")), 39) == 0.0  # ヒゲ: 上端 P+1800、中心 P+900、比 8.2


def test_I2_window_is_cut_by_time_not_by_bar_count():
    """I-2: 窓は 40 分(時刻で切る)。抜けた分(番号 10〜14)があっても、41 分前の足は窓から出る。"""
    bars = [bar(0, P - 1300, P)] + [osc(i) for i in range(1, 40) if not 10 <= i <= 14] + [bar(40, P + 200, P + 100)]
    r = run(bars, m1())
    assert ex(r, 39) == pytest.approx(-L)  # 番号 0 の足が窓の中: 中心 P-550、平均実体 231.4、比 6.5
    assert ex(r, 40) == 0.0  # 番号 0 が窓から出た: 中心 P+100 に終値 P+100 が届き利確(本数で切れば売りのまま)


def test_I2_waits_until_the_window_is_full():
    """I-2: 窓が満ちるまで(最初の 40 分)は建てない。"""
    r = run(base(38) + [bar(38, P, P + 1000)])
    assert ex(r, 38) == 0.0


def test_volume_zero_bars_do_not_enter_the_window():
    """＋(INTENT_MAP §3 の P-3): 出来高 0 の足は窓に入れない。"""
    bars = base() + [bar(39, P + 200, P)]
    bars[20] = bar(20, P + 1300, P + 1300, vol=0.0)
    # 入れると上端 P+1300・中心 P+650・平均実体 195・離れ 3.33 で 1 段の買いになる
    assert ex(run(bars), 39) == 0.0


def test_I1_no_lookahead_prefix_is_unchanged_by_later_bars():
    """未来を読まない: 同じ前半に違う後半を付けても、前半の持ち高は同じ。後半の無い走りとも同じ。"""
    head = base() + [bar(39, P, P + 1000)]
    a = run(head + [bar(40, P + 1000, P + 450), bar(41, P + 450, P + 1200)])
    b = run(head + [bar(40, P + 1000, P + 90000), bar(41, P + 90000, P - 50000)])
    c = run(head)
    for i in range(40):
        assert ex(a, i) == ex(b, i) == ex(c, i), i


def test_same_input_same_output():
    """同じ入力なら同じ出力(乱数を使わない)。"""
    bars = resume_bars()
    assert run(bars) == run(bars)


def test_window_range_and_trend_variants_are_accepted():
    """窓 8(地図 L-565)× flat/follow × body/wick は全部受け入れる。どれを測るかはリードが決める(L-565)。"""
    made = {(c.window_min, c.on_trend, c.range_from) for c in
            (C4OwnerMatildaRange(window_min=w, on_trend=o, range_from=f)
             for w in WINDOWS for o in ON_TRENDS for f in RANGE_FROMS)}
    assert WINDOWS == (10, 20, 40, 60, 80, 160, 1440, 10080) and len(made) == 32
    assert c4.BAR_MINS == (1, 5) and c4.ENTRY_SETTINGS == (1.0, 2.0, 3.0)  # 地図(L-565)


@pytest.mark.parametrize("kw", [dict(window_min=45), dict(window_min=40.0), dict(range_from="x"),
                                dict(on_trend="x"), dict(bar_min=3), dict(bar_min=1.0), dict(entry_setting=4.0),
                                dict(exit_setting=0.5), dict(step_setting=2.0), dict(n_levels=5),
                                dict(hold_max_min=20), dict(entry_setting=True), dict(width_gate=1),
                                dict(trend_gate=None), dict(time_exit="no"), dict(levels=0),
                                dict(on_trend="follow", trend_gate=False), dict(exit_mode=3),
                                dict(exit_mode=True), dict(exit_step=0.5), dict(exit_prorate=1),
                                dict(exit_guard=True, exit_mode=2), dict(exit_guard=True, exit_mode=0),
                                dict(exit_guard=True), dict(exit_relax=1), dict(exit_relax=None)])
def test_levels_outside_the_source_are_refused(kw):
    """A-12: 原文・原典・W1 C4・オーナーの答えに無い水準は拒む。follow は静観の門が無いと意味が無いので拒む。"""
    with pytest.raises(CardError):
        C4OwnerMatildaRange(**kw)


@pytest.mark.parametrize("kw", [dict(vr_max=None), dict(vr_max=100.0), dict(min_width_jpy=None),
                                dict(min_width_jpy=150.0)])
def test_removed_variants_are_not_accepted(kw):
    """L-564: 比の門は 10 に固定(変種 None・100 は外した)、幅の門は割合に固定(円の 150・None は外した)。"""
    with pytest.raises(TypeError):
        C4OwnerMatildaRange(**kw)


def test_exit_must_not_exceed_entry(monkeypatch):
    """原典 v37 139 行「必ず entry_setting > exit_setting」/ v52 128・130 行は両方 2。等しいまでは受け、越えたら拒む。"""
    C4OwnerMatildaRange(exit_setting=2.0)
    monkeypatch.setattr(c4, "EXIT_SETTINGS", (0.8, 2.0, 3.0))
    with pytest.raises(CardError):
        C4OwnerMatildaRange(exit_setting=3.0)


# 部品の切り替え(L-565: 部品ごとの効果を分けて測るため)

def test_switch_width_gate_off_trades_small_ranges():
    """width_gate=False: 幅 120 円(門を割る)でも建てる。"""
    bars = base(amp=20.0) + [bar(39, P, P + 120)]  # 平均実体 22.5、離れ 2.67 → 1 段
    assert ex(run(bars), 39) == 0.0
    assert ex(run(bars, C4OwnerMatildaRange(width_gate=False)), 39) == pytest.approx(-L)


def test_switch_trend_gate_off_keeps_trading_one_way_moves():
    """trend_gate=False: 比 40 でも静観せず、レンジの入りの規則で建てる(離れ 20 でも 1 本の足では 1 段)。"""
    assert ex(run(trend_bars(), C4OwnerMatildaRange(trend_gate=False)), 39) == pytest.approx(-L)


def test_switch_time_exit_off_holds_past_40_minutes():
    """time_exit=False: 40 分たっても出ない。"""
    r = run(clock_bars(), C4OwnerMatildaRange(window_min=60, exit_mode=1, time_exit=False))
    assert ex(r, 99) == pytest.approx(-2 * L)


def test_switch_levels_off_holds_one_unit():
    """levels=False: 段は 1 つだけ。持ち高は −1 / 0 / +1(量 ÷ 最大の量 = 1 ÷ 1)。"""
    card = lambda: C4OwnerMatildaRange(levels=False)  # noqa: E731
    r = run(stack_bars(), card())
    assert ex(r, 39) == -1.0 and ex(r, 40) == -1.0 and ex(r, 41) == -1.0  # 41: 建値 P+1000 − 0.8 × 235 = P+812 < P+1200
    assert ex(run(base() + [bar(39, P, P + 2000)], card()), 39) == -1.0
    assert ex(run(trend_bars(), C4OwnerMatildaRange(levels=False, on_trend="follow")), 39) == 1.0


# 足の長さ(L-565: 1 分足を k 分にまとめて判定する)。表は原典の 1 だけなので、表に 2 を足した形で確かめる。

def two_minute_bars(skip_41=False):
    """1 分足 2 本で 2 分足 1 本。2 分足の番号 j = 0〜19 は P → P+200 / P+200 → P の往復(1 分足は 100 円ずつ)、
    j = 20 は 1 分足 40(P → P+500)と 41(P+500 → P+1000)= 2 分足 P → P+1000。"""
    out = []
    for i in range(40):
        j, half = divmod(i, 2)
        a, b = (P + 100 * half, P + 100 * (half + 1)) if j % 2 == 0 else (P + 200 - 100 * half, P + 100 - 100 * half)
        out.append(bar(i, a, b))
    if skip_41:
        return out + [bar(40, P, P + 1000), bar(42, P + 1000, P + 1000)]
    return out + [bar(40, P, P + 500), bar(41, P + 500, P + 1000)]


def test_bar_min_aggregates_and_decides_only_at_the_end_of_each_bar(monkeypatch):
    """bar_min=2: 2 分の区切りの終わりでだけ判定する。窓 40 分 = 2 分足 20 本。
    区切りの途中(1 分足 40 の終わり)では持ち高を変えない。"""
    monkeypatch.setattr(c4, "BAR_MINS", (1, 2))
    r = run(two_minute_bars(), C4OwnerMatildaRange(bar_min=2))
    assert ex(r, 39) == 0.0
    assert ex(r, 40) == 0.0  # 区切りの途中
    assert ex(r, 41) == pytest.approx(-L)  # 2 分足 1〜20: 中心 P+500、平均実体 240、離れ 2.08 → 1 段


def test_bar_min_closes_a_bar_whose_last_minute_is_missing(monkeypatch):
    """bar_min=2: 区切りの最後の 1 分足が無い(約定 0)とき、次に呼ばれた時にその区切りを判定する。"""
    monkeypatch.setattr(c4, "BAR_MINS", (1, 2))
    r = run(two_minute_bars(skip_41=True), C4OwnerMatildaRange(bar_min=2))
    assert ex(r, 40) == 0.0
    assert ex(r, 42) == pytest.approx(-L)  # 2 分足 20 = 1 分足 40 だけ(P → P+1000)。区切り 21 はまだ途中


# 利確の形(L-566: 原典の利確の設定を全部引数に)。建値 = 段を足した判定の次の足の始値(W1 の仕様 C2)の平均。

def test_exit_mode_0_has_no_take_profit_line_and_closes_on_the_opposite_signal():
    """exit_mode=0(v52 162 行「ドテン」、942-943 行 exit_flg = 0): 利確の線では閉じず、反対の入りの条件で反対へ。"""
    card = lambda: C4OwnerMatildaRange(exit_mode=0)  # noqa: E731
    r = run(stack_bars() + [bar(42, P + 1200, P + 900)], card())  # exit_mode=1 なら 42 で利確(上の試験)
    assert ex(r, 42) == pytest.approx(-2 * L)
    flip = run(base() + [bar(39, P, P + 1000), bar(40, P + 1000, P - 600), bar(41, P - 600, P - 700)], card())
    assert ex(flip, 40) == 0.0 and ex(flip, 41) == pytest.approx(L)


def test_exit_mode_2_takes_profit_at_a_distance_from_the_entry_price():
    """exit_mode=2(既定。v37 881 行・v52「値幅」817・828-836 行): 売りは 終値 < 建値 − exit_step × vola(× 1/段の数)
    で 0。建値は 39 の判定の次の足 40 の始値 P+1000。中心からの線(exit_mode=1)とは別の所で閉じる。"""
    m2 = lambda: C4OwnerMatildaRange(exit_mode=2)  # noqa: E731
    head = base() + [bar(39, P, P + 1000)]
    take = head + [bar(40, P + 1000, P + 800)]  # 平均実体 220、線 P+1000 − 176 = P+824 > P+800
    assert ex(run(take, m2()), 40) == 0.0
    assert ex(run(take), 40) == 0.0  # 既定が形 2
    assert ex(run(take, m1()), 40) == pytest.approx(-L)  # exit_mode=1: 線 P+500 + 176 = P+676 < P+800 で持つ
    hold = head + [bar(40, P + 1000, P + 850)]  # 平均実体 218.75、線 P+825 < P+850
    assert ex(run(hold, m2()), 40) == pytest.approx(-L)


def test_exit_step_0_takes_any_profit_from_the_entry_price():
    """exit_step=0(v52 163 行「0だとvolaに関係なく利益になる」): 終値が建値より下なら売りを閉じる。"""
    bars = base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 990)]
    assert ex(run(bars, C4OwnerMatildaRange(exit_mode=2, exit_step=0.0)), 40) == 0.0
    assert ex(run(bars, C4OwnerMatildaRange(exit_mode=2)), 40) == pytest.approx(-L)  # 線 P+1000 − 172.2


def test_exit_prorate_divides_the_distance_by_the_levels_held():
    """exit_prorate(v37 881 行 exit_vola = vola × step_exit × (sizemin / mybtc)、v52 817 行): 2 段なら幅は半分。
    建値 = (40 の始値 P+1000 + 41 の始値 P+1600) / 2 = P+1300。41 の平均実体 235。"""
    on = run(stack_bars(), C4OwnerMatildaRange(exit_mode=2))  # 線 P+1300 − 0.8 × 235 / 2 = P+1206 > P+1200
    assert ex(on, 40) == pytest.approx(-2 * L)
    assert ex(on, 41) == 0.0
    off = run(stack_bars(), C4OwnerMatildaRange(exit_mode=2, exit_prorate=False))  # 線 P+1112 < P+1200
    assert ex(off, 41) == pytest.approx(-2 * L)


def test_exit_guard_moves_a_losing_center_line_to_entry_minus_a_ratio_of_the_price():
    """exit_guard(v52 840-843 行: sep > entry_price なら entry_price − 100): 中心からの線が建値より損の側なら、
    線を 建値 − 終値 × 100 / 1,152,502 にする(100 円を幅の門と同じく 2019-09-04 の値段に対する割合にした)。
    exit_mode=1、exit_setting = 2(v52 の値)。建値 P+1000(40 の始値)。
    41(終値 P+1050): 上端 P+1300、中心 P+650、平均実体 218.75、線 P+1087.5 > 建値 → 守りの線 P+1000 − 86.86 = P+913.14。
    41(終値 P+910): 平均実体 222.25、線 P+1094.5 > 建値 → 守りの線 P+1000 − 86.85 = P+913.15 >= P+910 で閉じる
    (100 円の固定なら P+900 < P+910 で持ったまま)。"""
    def bars(c41):
        return base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 1100), bar(41, P + 1300, c41)]
    guard = lambda: C4OwnerMatildaRange(exit_mode=1, exit_setting=2.0, exit_guard=True)  # noqa: E731
    plain = run(bars(P + 1050), C4OwnerMatildaRange(exit_mode=1, exit_setting=2.0))
    assert ex(plain, 40) == pytest.approx(-L)  # 線 P+985 < P+1100。前の段から 100 < 217.5 で 1 段のまま
    assert ex(plain, 41) == 0.0  # P+1050 <= P+1087.5(損の側で閉じる)
    assert ex(run(bars(P + 1050), guard()), 41) == pytest.approx(-L)  # P+1050 > P+913.14
    assert (P + 1000) - (P + 910) * c4.EXIT_GUARD_RATIO > P + 910 > P + 900
    assert ex(run(bars(P + 910), guard()), 41) == 0.0


def test_exit_guard_buy_side_is_entry_plus_a_ratio_of_the_price():
    """exit_guard の買い(v52 873-874 行: lep < entry_price なら entry_price + 100)。上の試験を P+100 を軸に
    上下を裏返した足: 建値 P-800、線 P-887.5 < 建値 → 守りの線 P-800 + 999,150 × 100 / 1,152,502 = P-713.31。"""
    m = lambda x: 2 * P + 200 - x  # noqa: E731
    bars = base() + [bar(39, m(P), m(P + 1000)), bar(40, m(P + 1000), m(P + 1100)), bar(41, m(P + 1300), m(P + 1050))]
    plain = run(bars, C4OwnerMatildaRange(exit_mode=1, exit_setting=2.0))
    assert ex(plain, 40) == pytest.approx(L) and ex(plain, 41) == 0.0
    guard = run(bars, C4OwnerMatildaRange(exit_mode=1, exit_setting=2.0, exit_guard=True))
    assert ex(guard, 41) == pytest.approx(L)  # 終値 P-850 < P-713.31


# 利確の緩め(v37 1012〜1014・1020〜1022 行 exit_flg = 2 → 897〜898・911〜912 行。リードの決め 4、INTENT_MAP X-4)

def losing_side_bars(c41):
    """39 で 1 段売り(建値 = 40 の始値 P+1000)。40 で P+2200 まで上がり、中心が P+1100 > 建値(売りの損の側)。"""
    return base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 2200), bar(41, P + 2200, c41)]


def test_exit_relax_when_the_entry_price_is_on_the_losing_side_of_the_center():
    """建値が中心より損の側(売りなら 建値 < 中心)なら、利確の線を 中心 と 建値 − 値幅 の高い方(損な方)へ緩める。
    段は 1 つ(levels=False)にして按分を外す。
    40: 平均実体 245、中心 P+1100、比 8.98。緩めた線 max(P+1100, P+1000 − 196) = P+1100 > 終値 P+2200 → 持つ。
    41: 平均実体 268.75、中心 P+1100、比 8.19。緩めた線 P+1100 > 終値 P+1050 → 閉じる。
        緩めなければ線 P+1000 − 215 = P+785 < P+1050 → 持つ。"""
    bars = losing_side_bars(P + 1050)
    on = run(bars, C4OwnerMatildaRange(levels=False))
    assert [ex(on, i) for i in (39, 40, 41)] == [-1.0, -1.0, 0.0]
    off = run(bars, C4OwnerMatildaRange(levels=False, exit_relax=False))
    assert ex(off, 41) == -1.0
    # 買い(上下を裏返した足): 建値 P-800 > 中心 P-900 で損の側。線 min(中心, 建値 + 値幅) = P-900 < 終値 P-850 → 閉じる
    m = lambda x: 2 * P + 200 - x  # noqa: E731
    mirror = [bar(i, m(b.open), m(b.close)) for i, b in enumerate(bars)]
    assert ex(run(mirror, C4OwnerMatildaRange(levels=False)), 41) == 0.0
    assert ex(run(mirror, C4OwnerMatildaRange(levels=False, exit_relax=False)), 41) == 1.0


def twenty_minute_bars():
    """39 で 1 段売り(建値 = 40 の始値 P+1000)。40 は P+1000 → P+1900。41 からは P+900 と P+1100 の往復
    (奇数番号が P+1100 → P+900)。40 以降の窓: 上端 P+1900、下端 P、中心 P+950(建値より下 = 売りの得の側)、
    平均実体 (38 × 200 + 1000 + 900) / 40 = 237.5、比 8.0。利確の線 P+1000 − 190 = P+810。"""
    out = base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 1900)]
    out += [bar(i, P + 1100, P + 900) if i % 2 else bar(i, P + 900, P + 1100) for i in range(41, 61)]
    return out


def test_exit_relax_after_20_minutes():
    """建ててから 20 分(v37 126 行 alert_count。40 分の時間成行は alert_count × 2)たったら、利確の線を
    中心 と 建値 − 値幅 の高い方へ緩める。建てた判定は 39 の終わり。57(18 分)の終値 P+900 は P+810 より上で持つ。
    59(20 分)の終値 P+900 は緩めた線 max(P+950, P+810) = P+950 より下で閉じる。"""
    on = run(twenty_minute_bars(), C4OwnerMatildaRange(levels=False))
    assert ex(on, 57) == -1.0 and ex(on, 58) == -1.0
    assert ex(on, 59) == 0.0
    off = run(twenty_minute_bars(), C4OwnerMatildaRange(levels=False, exit_relax=False))
    assert ex(off, 59) == -1.0


def test_exit_relax_only_acts_on_the_take_profit_by_distance():
    """緩めは形 2 の線にだけ効く(按分と同じ。v37 の緩めは 建値 ∓ exit_vola と中心の比べ)。形 1 では有無で同じ。"""
    bars = twenty_minute_bars()
    a = run(bars, C4OwnerMatildaRange(levels=False, exit_mode=1))
    b = run(bars, C4OwnerMatildaRange(levels=False, exit_mode=1, exit_relax=False))
    assert a == b


def test_default_take_profit_is_v37_code():
    """既定の利確 = v37 のコードの実際の動き: 形 2(建値から値幅)+ 按分 + step_exit 0.8 + 20 分の緩め。"""
    card = C4OwnerMatildaRange()
    assert (card.exit_mode, card.exit_prorate, card.exit_step, card.exit_relax) == (2, True, 0.8, True)


# 第 4 稿(リードの決め: 一方向の動きの間と、足 1 本の中の順番を v37 にそろえる)

def up_move_bars():
    """39 で 1 段買い(P+200 → P-800。中心 P-300、平均実体 220、P-800 < P-740)。40 は P-800 → P+2500 の大陽線
    (窓 1〜40: 平均実体 (38 × 200 + 1000 + 3300) / 40 = 297.5、幅 3,300、比 11.09、終値 > 中心 P+850 → 上向き)。
    41〜85 は 100 円ずつ上がる陽線(比は 10 を越えたまま)。"""
    out = base() + [bar(39, P + 200, P - 800), bar(40, P - 800, P + 2500)]
    out += [bar(41 + j, P + 2500 + 100 * j, P + 2600 + 100 * j) for j in range(45)]
    return out


def test_with_trend_position_is_kept_when_the_move_starts():
    """v37 937〜948 行: break の始まりで閉じる処理は文字列に入れて消されている。動きと同じ向きの持ち高(上向きの
    動きの買い)は閉じない(既定 trend_close=False)。trend_close=True(第 3 稿までの flat の動き)なら閉じ、
    flat なのでそのあとも入らない。利確の線の無い形 0 で見る。"""
    keep = run(up_move_bars(), C4OwnerMatildaRange(exit_mode=0))
    assert ex(keep, 39) == pytest.approx(L) and ex(keep, 40) == pytest.approx(L) and ex(keep, 41) == pytest.approx(L)
    close = run(up_move_bars(), C4OwnerMatildaRange(exit_mode=0, trend_close=True))
    assert ex(close, 40) == 0.0 and ex(close, 41) == 0.0


def test_no_time_exit_during_the_move():
    """v37 1027〜1036 行: break の間の exit_judge には alert_count × 2 の時間成行が無い。39 で建てて 41 分後の
    80(窓 41〜80: 幅 4,000、平均実体 100、比 40)でも持ったまま。"""
    r = run(up_move_bars(), C4OwnerMatildaRange(exit_mode=0))
    assert ex(r, 80) == pytest.approx(L)


def test_take_profit_by_distance_works_during_the_move():
    """v37 1029〜1030 行: break の間も b_signal == 0 なら exit_flg = 1(形 2 の利確の指値)。既定の形 2 なら、
    40 で 建値 P-800(40 の始値)+ 0.8 × 297.5 = P-562 < 終値 P+2500 → 0。"""
    assert ex(run(up_move_bars()), 40) == 0.0


def buy_lapse_bars():
    """39 で 1 段買い(終値 P-800)。40 は P-500 で始まる(1 段目の約定 = 建値 P-500)P-500 → P-400 で合図が切れる
    (中心 P-300、平均実体 217.5、P-400 > P-735)。41 は P-400 → P-760(平均実体 221.5、中心 P-300、P-760 < P-743 で合図)。"""
    return base() + [bar(39, P + 200, P - 800), bar(40, P - 500, P - 400), bar(41, P - 400, P - 760)]


def test_buy_reference_resets_to_the_entry_price_only_when_asked():
    """迷った点 20: v37 1092 行の or と and の順で、買いは合図の切れた巡回で指値が全部取り消され、次の合図で起点が
    建値の平均 entry_price になる(836〜839 行)。既定(buy_ref_reset=False)は売り買い同じ = 前の段の終値 P-800 から
    数え、41 の P-760 は P-800 − 221.5 より上なので足さない。True なら起点 P-500 から数え、P-760 < P-721.5 で 2 段。
    売り(上下を裏返した足)は True でも戻らない(1 段のまま)。"""
    assert ex(run(buy_lapse_bars()), 41) == pytest.approx(L)
    assert ex(run(buy_lapse_bars(), C4OwnerMatildaRange(buy_ref_reset=True)), 41) == pytest.approx(2 * L)
    m = lambda x: 2 * P + 200 - x  # noqa: E731
    mirror = [bar(i, m(b.open), m(b.close)) for i, b in enumerate(buy_lapse_bars())]
    assert ex(run(mirror, C4OwnerMatildaRange(buy_ref_reset=True)), 41) == pytest.approx(-L)


@pytest.mark.parametrize("kw", [dict(trend_close=1), dict(trend_end_close=None), dict(buy_ref_reset="yes")])
def test_new_switches_take_only_bools(kw):
    with pytest.raises(CardError):
        C4OwnerMatildaRange(**kw)


def test_new_switch_defaults_follow_v37():
    card = C4OwnerMatildaRange()
    assert (card.on_trend, card.trend_close, card.trend_end_close, card.buy_ref_reset) == ("flat", False, False, False)
