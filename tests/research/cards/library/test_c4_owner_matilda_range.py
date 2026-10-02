"""カード 4(c4_owner_matilda_range)の関数の試験: 手で作った小さな入力で、持ち高が意図どおりに出るか。

意図の地図(docs/RESEARCH/cards/c4_owner_matilda_range/INTENT_MAP.md)の ○ の各項に 1 つ以上。
各試験の名前と docstring に項の番号を書く。カードは run_card(bot.bt.core の事象の流れ)を通して呼ぶ。

入力の作り方: bitFlyer の 1 分足。値段は P = 1,000,000 円の近く。「往復の足」は偶数番目が P → P+200 の陽線、
奇数番目が P+200 → P の陰線(実体 200 円、ヒゲ無し)。窓 40 分なら、40 本目(番号 39)の足の終わりで
初めて窓が満ちる。数字は試験の入力で、データではない。
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent
from bot.research.cards import CardError, run_card
from bot.research.cards.library.c4_owner_matilda_range import (ENTRY_K, HOLD_MAX_MIN, VR_MAX,
                                                                C4OwnerMatildaRange)

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z。試験の時刻で、データではない
P = 1_000_000.0


def bar(i, o, c, h=None, lo=None, vol=1.0):
    h = max(o, c) if h is None else h
    lo = min(o, c) if lo is None else lo
    return BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M,
                    start_time_ns=T0 + i * M, open=o, high=h, low=lo, close=c, volume=vol)


def osc(i, amp=200.0):
    return bar(i, P, P + amp) if i % 2 == 0 else bar(i, P + amp, P)


def run(bars, card=None):
    r = run_card(card or C4OwnerMatildaRange(), bars, references={}, declarations={}, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return {int(e): float(x) for e, x in zip(r.end_ns, r.exposure)}


def ex(r, i):
    return r[T0 + (i + 1) * M]


def base(n=39, amp=200.0):
    return [osc(i, amp) for i in range(n)]


def test_constants_are_from_the_source():
    """水準は原典の値(INTENT_MAP §2 の I-5・I-9・I-12)。"""
    assert ENTRY_K == 2.0 and HOLD_MAX_MIN == 40 and VR_MAX == 10.0


def test_I5_short_above_and_long_below_center():
    """I-5: 中心から上に離れたら売り、下に離れたら買い(中心 ± 2 × 平均実体)。"""
    up = run(base() + [bar(39, P, P + 1000)])  # 中心 P+500、平均実体 220、門 P+940 < 終値 P+1000
    assert ex(up, 39) == -1.0
    down = run(base() + [bar(39, P + 200, P - 800)])  # 中心 P-300、門 P-740 > 終値 P-800
    assert ex(down, 39) == 1.0
    near = run(base() + [bar(39, P, P + 900)])  # 中心 P+450、平均実体 217.5、門 P+885 < P+900
    assert ex(near, 39) == -1.0
    inside = run(base() + [bar(39, P, P + 850)])  # 中心 P+425、平均実体 216.25、門 P+857.5 > P+850
    assert ex(inside, 39) == 0.0


def test_I6_I7_I3_take_profit_at_center_then_trade_again():
    """I-6: 中心に届いたら利確。I-7: 往復を重ねる。I-3: 中心は毎分動く(41 本目は新しい中心で判定)。"""
    bars = base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 450), bar(41, P + 450, P + 1200)]
    r = run(bars)
    assert ex(r, 39) == -1.0
    assert ex(r, 40) == 0.0  # 中心 P+500 に終値 P+450 が届いた
    assert ex(r, 41) == -1.0  # 窓が 1 分進み、上端 P+1200・中心 P+600・門 P+1085 < P+1200


def test_I6_no_take_profit_before_center():
    """I-6: 中心の手前では利確しない。"""
    r = run(base() + [bar(39, P, P + 1000), bar(40, P + 1000, P + 600)])
    assert ex(r, 40) == -1.0


def test_I18_opposite_signal_flips():
    """I-18: 持ち高があるときに反対側の入りの条件がそろえば、反対へ。"""
    r = run(base() + [bar(39, P, P + 1000), bar(40, P + 1000, P - 600)])
    assert ex(r, 39) == -1.0
    assert ex(r, 40) == 1.0  # 中心 P+200、平均実体 255、門 P-310 > 終値 P-600


def test_I12_time_exit_after_40_minutes():
    """I-12: 建ててから 40 分(原典 alert_count × 2)で決済。中心に届かなくても出る。"""
    card = C4OwnerMatildaRange(window_min=60, vr_max=None)
    bars = base(59) + [bar(59, P, P + 1000)] + [bar(i, P + 800, P + 800) for i in range(60, 101)]
    r = run(bars, card)
    assert ex(r, 59) == -1.0
    assert ex(r, 98) == -1.0  # 39 分
    assert ex(r, 99) == 0.0  # 40 分。中心 P+500 < 終値 P+800 なので利確ではない
    assert ex(r, 100) == -1.0  # 次の足で、まだ離れているので建て直す


def test_I8_too_small_range_is_not_traded():
    """I-8(△): レンジ幅が 150 円に満たなければ建てない。門を外すと建てる。"""
    bars = base(amp=10.0) + [bar(39, P, P + 100)]  # 幅 100 円、中心 P+50、門 P+74.5 < P+100
    assert ex(run(bars), 39) == 0.0
    assert ex(run(bars, C4OwnerMatildaRange(min_width_jpy=None)), 39) == -1.0


def trend_bars():
    """40 本続けて 100 円ずつ上がる足(番号 0〜39)。番号 39 で幅 4,000 円、平均実体 100 円、比 40。"""
    return [bar(i, P + 100 * i, P + 100 * (i + 1)) for i in range(40)]


def test_I9_I14_I15_I16_stand_aside_on_one_way_move():
    """I-9(△)・I-14・I-15・I-16: 比(幅 ÷ 平均実体)が 10 以上なら一方向の動きとみなし、建てない(静観)。
    門を外すと中心から離れているので売る。follow なら動きの向きに持つ(I-13)。"""
    assert ex(run(trend_bars()), 39) == 0.0
    assert ex(run(trend_bars(), C4OwnerMatildaRange(vr_max=None)), 39) == -1.0
    assert ex(run(trend_bars(), C4OwnerMatildaRange(on_trend="follow")), 39) == 1.0
    assert ex(run(trend_bars(), C4OwnerMatildaRange(vr_max=100.0)), 39) == -1.0  # 比 40 < 100


def test_I9_flat_closes_a_range_position():
    """I-9: 静観(flat)では、レンジで建てた持ち高も一方向の動きを見たら 0 にする。"""
    bars = base() + [bar(39, P, P + 1000)] + [bar(40 + j, P + 1000 + 2000 * j, P + 1000 + 2000 * (j + 1))
                                              for j in range(3)]
    r = run(bars)
    assert ex(r, 39) == -1.0
    assert ex(r, 40) == 0.0  # 上端 P+3000、比 3000 / 265 > 10、終値は中心 P+1500 より上 → 上向きの動き
    assert ex(r, 42) == 0.0


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
    I-13: follow(逆転順張り)は、その間ずっと動きの向き(+1)に持つ。"""
    r = run(resume_bars(), C4OwnerMatildaRange(on_trend="follow"))
    k13_ratio = (5000 - 1300) / ((27 * 100 + 13 * 1000) / 40)
    assert k13_ratio < 10
    for k in range(0, 30):
        assert ex(r, 39 + k) == 1.0, k
    assert ex(r, 39 + 30) == 0.0  # 中心 P+4000 に終値 P+4000 が戻った


def test_I17_range_from_bodies_ignores_wicks():
    """I-17: 既定はヒゲを除いた実体の端でレンジを測る(原典 beard_ignore)。ヒゲで測る変種と分かれる。"""
    bars = base() + [bar(39, P, P + 1000)]
    bars[20] = bar(20, P, P + 200, h=P + 5000)
    assert ex(run(bars, C4OwnerMatildaRange(vr_max=None)), 39) == -1.0
    assert ex(run(bars, C4OwnerMatildaRange(vr_max=None, range_from="wick")), 39) == 1.0  # 中心 P+2500


def test_I2_window_is_cut_by_time_not_by_bar_count():
    """I-2: 窓は 40 分(時刻で切る)。抜けた分(番号 10〜14)があっても、41 分前の足は窓から出る。"""
    bars = [bar(0, P - 5000, P)] + [osc(i) for i in range(1, 40) if not 10 <= i <= 14] + [bar(40, P + 200, P + 100)]
    r = run(bars, C4OwnerMatildaRange(vr_max=None))
    assert ex(r, 39) == -1.0  # 番号 0 の足が窓の中: 中心 P-2400、終値 P は上に離れている
    assert ex(r, 40) == 0.0  # 番号 0 が窓から出た: 中心 P+100 に終値 P+100 が届き利確(本数で切れば売りのまま)


def test_I2_waits_until_the_window_is_full():
    """I-2: 窓が満ちるまで(最初の 40 分)は建てない。"""
    r = run(base(38) + [bar(38, P, P + 1000)])
    assert ex(r, 38) == 0.0


def test_volume_zero_bars_do_not_enter_the_window():
    """＋(INTENT_MAP §3 の P-4): 出来高 0 の足は窓に入れない。"""
    bars = base() + [bar(39, P + 200, P)]
    bars[20] = bar(20, P + 9000, P + 9000, vol=0.0)
    assert ex(run(bars, C4OwnerMatildaRange(vr_max=None)), 39) == 0.0  # 入れると上端 P+9000 で買いになる


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


@pytest.mark.parametrize("kw", [dict(window_min=45), dict(vr_max=5.0), dict(min_width_jpy=100.0),
                                dict(range_from="x"), dict(on_trend="x")])
def test_levels_outside_the_source_are_refused(kw):
    """A-12: 原文・原典・W1 C4 に無い水準は拒む。"""
    with pytest.raises(CardError):
        C4OwnerMatildaRange(**kw)
