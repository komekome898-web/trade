"""カード 4 段 1(v37 を 1 分足で指値として再現する。src/bot/research/matilda_limit_sim.py)の試験。

仕様: docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/SPEC.md。手で作った小さな足の並びで、仕様の各節の規則を確かめる。
入力の作り方(カード 4 の試験と同じ): 値段は P = 1,000,000 円の近く。「往復の足」は偶数番目が P → P+200 の陽線、
奇数番目が P+200 → P の陰線(実体 200 円、ヒゲ無し)。40 本(番号 0〜39)で窓 40 分が満ち、番号 40 の足から
出来事が起きる。そのときの量は 中心 P+100・ボラ 200・幅 200・S1 = P+500・B1 = P−300(entry = 2)。
数字は試験の入力で、データではない。
"""
from __future__ import annotations

import math
import random

import pytest

from bot.bt.core import BarEvent
from bot.research.cards import run_card
from bot.research.cards.library.c4_owner_matilda_range import MIN_WIDTH_RATIO, C4OwnerMatildaRange
from bot.research.matilda_limit_sim import MatildaLimitSim

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z。試験の時刻で、データではない
P = 1_000_000.0


def bar(i, o, c, h=None, lo=None, vol=1.0, t0=T0):
    h = max(o, c) if h is None else h
    lo = min(o, c) if lo is None else lo
    return BarEvent(received_time_ns=t0 + (i + 1) * M, exchange_time_ns=t0 + (i + 1) * M,
                    start_time_ns=t0 + i * M, open=o, high=h, low=lo, close=c, volume=vol)


def osc(i, amp=200.0, p=P):
    return bar(i, p, p + amp) if i % 2 == 0 else bar(i, p + amp, p)


def base(n=40, amp=200.0, p=P):
    return [osc(i, amp, p) for i in range(n)]


def feed(sim, bars):
    rows = []
    for b in bars:
        rows += sim.feed(b)
    return rows


def sim(**kw):
    kw.setdefault("fill_side", "good")
    return MatildaLimitSim(**kw)


def pnl(side, fills, px, n=7):
    return math.fsum(side * (px / f - 1.0) * 1e4 / n for f in fills)


# ---------------------------------------------------------------- 1. 量(仕様 2)
def test_1_window_center_vola_width_by_hand():
    s = sim()
    feed(s, base(39))
    assert s._q is None  # 39 本では窓 40 分が満ちない(カードと同じ)
    feed(s, [osc(39)])
    q = s._q
    assert (q.center, q.vola, q.width, q.hi2, q.lo2) == (P + 100, 200.0, 200.0, P + 200, P)
    assert (q.s1, q.b1) == (P + 500, P - 300)
    assert q.bup is None and q.bdp is None  # hi == hi2・lo == lo2 なので判定値は未定のまま(v37 504〜509 行)


@pytest.mark.parametrize("range_from,bar_min", [("body", 1), ("wick", 1), ("body", 5), ("wick", 5)])
def test_1_quantities_match_card_4(range_from, bar_min):
    """同じ足をカード 4 に通したときの窓の中の端・中心・ボラと同じ値(出来高 0 の足を含む)。"""
    rnd = random.Random(7)
    px, bars = P, []
    for i in range(130):
        o = px
        c = o + rnd.choice([-1, 1]) * rnd.randint(0, 300)
        h, lo = max(o, c) + rnd.randint(0, 80), min(o, c) - rnd.randint(0, 80)
        bars.append(bar(i, o, c, h, lo, vol=0.0 if i % 17 == 5 else 1.0))
        px = c
    card = C4OwnerMatildaRange(range_from=range_from, bar_min=bar_min, trend_gate=False)
    run_card(card, bars, references={}, declarations={}, venue="bitflyer", symbol="FX_BTC_JPY")
    s = sim(range_from=range_from, bar_min=bar_min)
    feed(s, bars)
    hi, lo = card._maxq[0][1], card._minq[0][1]
    assert s._q.center == (hi + lo) / 2.0
    assert s._q.width == hi - lo
    assert s._q.vola == pytest.approx(card._body_sum / len(card._bars), rel=1e-12)


# ---------------------------------------------------------------- 2. 売りの 1 段目(仕様 3-2。等号なし)
def test_2_first_sell_fills_only_above_s1():
    s = sim()
    feed(s, base() + [bar(40, P + 450, P + 450, h=P + 500, lo=P + 450)])
    assert s._side == 0  # H == S1 は約定しない
    s = sim()
    feed(s, base() + [bar(40, P + 450, P + 450, h=P + 500.5, lo=P + 450)])
    assert s._side == -1 and s._fills == [P + 500]  # 約定の値段 = S1


def test_2_first_buy_fills_only_below_b1():
    s = sim()
    feed(s, base() + [bar(40, P - 250, P - 250, h=P - 250, lo=P - 300)])
    assert s._side == 0
    s = sim()
    feed(s, base() + [bar(40, P - 250, P - 250, h=P - 250, lo=P - 300.5)])
    assert s._side == 1 and s._fills == [P - 300]


# ---------------------------------------------------------------- 3. 1 本で複数段・上限 N
def test_3_all_levels_crossed_in_one_bar_fill_and_stop_at_n():
    s = sim()
    feed(s, base() + [bar(40, P + 900, P + 900, h=P + 900, lo=P + 900)])
    assert s._fills == [P + 500, P + 700]  # P+900 ちょうどは約定しない
    s = sim()  # 安値は利確(建値 P+1100 − 160 / 7)に届かない
    feed(s, base() + [bar(40, P + 1600, P + 1600, h=P + 5000, lo=P + 1600)])
    assert s._fills == [P + 500 + 200 * k for k in range(7)]  # 上限 7(v37 118 行)
    s = sim(n_levels=4)
    feed(s, base() + [bar(40, P + 1600, P + 1600, h=P + 5000, lo=P + 1600)])
    assert s._fills == [P + 500 + 200 * k for k in range(4)]


def test_3_next_level_counts_from_the_previous_fill_with_step():
    s = sim(step=2)
    feed(s, base() + [bar(40, P + 900, P + 900, h=P + 1300, lo=P + 900)])
    assert s._fills == [P + 500, P + 900]  # 次の段 = 前の段 + 2 × vola、P+1300 ちょうどは約定しない


# ---------------------------------------------------------------- 4. exit_flg 1 の利確
def _two_level_short():
    """番号 40 の足で売り 2 段(P+500・P+700、建値 P+600)。足は十字(実体 0)で、その足では利確に届かない。"""
    s = sim()
    rows = feed(s, base() + [bar(40, P + 600, P + 600, h=P + 701, lo=P + 600)])
    assert rows == [] and s._fills == [P + 500, P + 700]
    return s


def test_4_exit_flg1_price_and_fill():
    s = _two_level_short()
    q = s._q
    tp = (P + 600) - 0.8 * q.vola / 2  # E − step_exit × vola / n
    tp_got, why = s._tp(s._state(), q, T0 + 41 * M)
    assert tp_got == pytest.approx(tp) and why == "利確1"
    rows = feed(s, [bar(41, tp + 10, tp + 10, h=tp + 10, lo=tp)])
    assert rows == [] and s._side == -1  # L == 利確の値段は約定しない
    q = s._q
    tp = (P + 600) - 0.8 * q.vola / 2
    rows = feed(s, [bar(42, tp + 10, tp + 10, h=tp + 10, lo=tp - 0.5)])
    assert len(rows) == 1
    r = rows[0]
    assert r["exit_price"] == pytest.approx(tp) and r["exit_reason"] == "利確1" and r["levels"] == 2
    assert r["entry_price"] == P + 600 and s._side == 0


# ---------------------------------------------------------------- 5. 20 分で flg 2、40 分で次の足の始値で成行
def _hold_bars(s, i0, i1, px=P + 650):
    rows = []
    for i in range(i0, i1):
        rows += s.feed(bar(i, px, px, h=px, lo=px))
    return rows


def test_5_exit_flg2_after_alert_minutes():
    """t0 = 1 段目が約定した足(番号 40)の終わり = T0 + 41 分。足の始まりが t0 + 20 分以上の足(番号 61〜)から flg 2。"""
    s = _two_level_short()
    assert _hold_bars(s, 41, 60) == []
    assert s._tp(s._state(), s._q, T0 + 60 * M)[1] == "利確1"
    assert s._tp(s._state(), s._q, T0 + 61 * M)[1] == "利確2"
    s2 = _two_level_short()
    _hold_bars(s2, 41, 61)
    tp, why = s2._tp(s2._state(), s2._q, T0 + 61 * M)
    assert why == "利確2" and tp == pytest.approx(max(s2._q.center, (P + 600) - 0.8 * s2._q.vola / 2))
    rows = s2.feed(bar(61, P + 650, P + 650, h=P + 650, lo=tp - 1))
    assert rows[0]["exit_reason"] == "利確2" and rows[0]["exit_price"] == pytest.approx(tp)


def test_5_exit_flg2_when_entry_is_on_the_losing_side_of_center():
    """売りで建値 < 中心なら 20 分を待たずに flg 2: 利確の値段 = max(中心, E − exit_vola)。"""
    s = _two_level_short()
    st = s._state()
    q = s._q
    q.center = P + 650  # 建値 P+600 < 中心(量を直に置いて規則だけ確かめる)
    tp, why = s._tp(st, q, T0 + 41 * M)
    assert why == "利確2" and tp == P + 650


def test_5_time_exit_at_the_open_of_the_next_bar():
    """足の終わり − t0 ≥ 40 分(番号 80 の足の終わり)で決め、番号 81 の足の始値で閉じる。"""
    s = _two_level_short()
    assert _hold_bars(s, 41, 81) == []
    assert s._side == -1 and s._pending_time
    rows = s.feed(bar(81, P + 640, P + 660))
    assert len(rows) == 1
    r = rows[0]
    assert r["exit_reason"] == "時間" and r["exit_price"] == P + 640 and r["exit_ns"] == T0 + 81 * M
    assert r["pnl_bp"] == pytest.approx(pnl(-1, [P + 500, P + 700], P + 640))


# ---------------------------------------------------------------- 6. 反対の入り
def test_6_opposite_entry_price_is_always_beyond_take_profit_so_take_profit_fills_first():
    """仕様 3-3 の利確の値段は、同じ量で作る反対の入りの値段より必ず手前にある(売り: 利確 ≥ 中心 − 0.8 vola > B1)。
    値段の順で通すので、両方を越えた足では利確が先に約定する。"""
    s = _two_level_short()
    q = s._q
    rows = s.feed(bar(41, P + 600, q.b1 - 50, h=P + 600, lo=q.b1 - 100))
    assert rows[0]["exit_reason"] == "利確1"


@pytest.mark.parametrize("fill_side,reenter", [("good", True), ("bad", False)])
def test_6_opposite_entry_closes_at_that_price_and_reentry_is_undecided(monkeypatch, fill_side, reenter):
    """反対の入りの値段を越えたらその値段で閉じる(利確を遠くへ置いて機構だけ確かめる)。閉じた後に同じ足でその向きに
    入るのは良い側だけ。その足は決まらない足。"""
    s = sim(fill_side=fill_side)
    feed(s, base() + [bar(40, P - 250, P - 250, h=P - 250, lo=P - 300.5)])  # 買い 1 段 P−300
    assert s._side == 1
    q = s._q
    monkeypatch.setattr(s, "_tp", lambda st, q, t: (P + 10 ** 6, "利確1"))
    rows = s.feed(bar(41, q.s1 - 10, q.s1 + 5, h=q.s1 + 5, lo=q.s1 - 10))
    assert len(rows) == 1
    r = rows[0]
    assert r["exit_reason"] == "反対の入り" and r["exit_price"] == q.s1 and r["undecided"] == 1
    assert (s._side == -1 and s._fills == [q.s1]) if reenter else s._side == 0


# ---------------------------------------------------------------- 7. ブレイク(仕様 3-1)
def two_phase(a1=400.0, a2=200.0, lo1=P):
    """番号 0〜39 は lo1 ↔ lo1 + a1 の往復、40〜79 は P ↔ P + a2 の往復。番号 79 の足の終わりで、窓(40 分)の上端は
    P + a2、2 倍の窓の上端は lo1 + a1。"""
    first = [bar(i, lo1, lo1 + a1) if i % 2 == 0 else bar(i, lo1 + a1, lo1) for i in range(40)]
    return first + [osc(i, a2) for i in range(40, 80)]


def test_7_break_up_then_no_entry_while_flat_then_break_off():
    s = sim()
    assert feed(s, two_phase()) == [] and s._side == 0
    q = s._q
    assert q.bup == P + 300 and q.hi2 == P + 400 and q.bdp is None  # bup = hi + width / 2
    s.feed(bar(80, P + 200, P + 380, h=P + 400, lo=P + 200))
    assert s._brk == 0  # H == max(bup, hi2) はブレイクしない
    s = sim()
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 380, h=P + 400.5, lo=P + 200))
    assert s._brk == 1 and s._side == 0  # S1 = P+500 は越えていない
    rows = s.feed(bar(81, P + 380, P + 390, h=P + 5000, lo=P + 380))
    assert rows == [] and s._side == 0 and s._brk == 1  # brk 中は持ち高 0 から入らない
    center = s._q.center
    s.feed(bar(82, P + 390, center - 1, h=P + 390, lo=center - 1))
    assert s._brk == 0  # 終値 < 中心で解ける


def test_7_break_down():
    s = sim()
    feed(s, two_phase(a1=400.0, lo1=P - 200))
    q = s._q
    assert q.bdp == P - 100 and q.lo2 == P - 200 and q.bup is None
    s.feed(bar(80, P, P - 150, h=P, lo=P - 250))
    assert s._brk == -1 and s._side == 0  # 判定値 min(bdp, lo2) = P−200 を下に越えた。B1 = P−300 は越えていない


def test_7_opposite_position_is_closed_at_the_break_price():
    """entry = 1(S1 = P+300)。上りの脚で売りが P+300 で約定し、P+400 のブレイクでその値段で閉じる。"""
    s = sim(entry=1)
    feed(s, two_phase())
    rows = s.feed(bar(80, P + 200, P + 420, h=P + 450, lo=P + 200))
    assert len(rows) == 1
    r = rows[0]
    assert (r["side"], r["entry_price"], r["exit_price"], r["exit_reason"]) == (-1, P + 300, P + 400, "反対のブレイク")
    assert r["pnl_bp"] == pytest.approx(pnl(-1, [P + 300], P + 400)) and r["undecided"] == 0
    assert s._brk == 1 and s._side == 0


def test_7_follow_enters_one_level_at_the_break_price():
    s = sim(on_break="follow")
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 420, h=P + 450, lo=P + 200))
    assert s._side == 1 and s._fills == [P + 400]


@pytest.mark.parametrize("on_break,closed", [("close", True), ("hold", False)])
def test_7_close_variant_closes_a_same_direction_position(monkeypatch, on_break, closed):
    """on_break="close" はブレイクで同じ向きの持ち高も判定値の値段で閉じる。仕様 3-3 の利確の値段は建値と判定値の
    間にあるので、ふつうは利確が先に約定する。ここでは利確を遠くへ置いて機構だけ確かめる。"""
    s = sim(on_break=on_break)
    feed(s, two_phase())
    s.feed(bar(80, P - 250, P - 250, h=P - 250, lo=P - 300.5))  # 買い 1 段 P−300
    assert s._side == 1
    monkeypatch.setattr(s, "_tp", lambda st, q, t: (P + 10 ** 6, "利確1"))
    q = s._q
    q.gate = False  # 上りの脚で反対の入り(S1 < 判定値)が先に起きないように、量の門を閉じておく
    pb = max(q.bup, q.hi2)
    rows = s.feed(bar(81, P - 250, pb + 10, h=pb + 20, lo=P - 250))
    assert s._brk == 1
    if closed:
        assert (rows[0]["exit_reason"], rows[0]["exit_price"], s._side) == ("ブレイク", pb, 0)
    else:
        assert rows == [] and s._side == 1


def test_7_break_delay_0_never_breaks_and_3_uses_the_third_last_update():
    s = sim(break_delay=0)
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 380, h=P + 10 ** 5, lo=P + 200))
    assert s._brk == 0
    s = sim(break_delay=3)
    feed(s, two_phase())
    assert s._q.bup is None  # 更新は 1 回だけ。3 回前はまだ未定


# ---------------------------------------------------------------- 8. 決まらない足
def test_8_entry_and_take_profit_in_one_bar_good_and_bad():
    """持ち高 0 から、売り(S1 = P+500)と、その利確(P+500 − 160 = P+340)が同じ足に入る。"""
    b40 = bar(40, P + 400, P + 300, h=P + 501, lo=P + 300)
    g = sim(fill_side="good")
    rows = feed(g, base() + [b40])
    assert len(rows) == 1
    r = rows[0]
    assert (r["entry_price"], r["exit_price"], r["exit_reason"], r["undecided"]) == (P + 500, P + 340, "利確1", 1)
    assert g.undecided_bars == 1
    b = sim(fill_side="bad")
    assert feed(b, base() + [b40]) == [] and b._side == -1
    rows = b.finish()
    assert rows[0]["exit_reason"] == "期間の終わり" and rows[0]["undecided"] == 1 and rows[0]["exit_price"] == P + 300


def test_8_add_and_take_profit_in_one_bar():
    """売り 2 段を持つ足で、段の追加(上)と利確(下)が両方に入る。下が先の道は 2 段のまま利確、上が先の道は段を
    足した後の利確の値段(建値の方へ動く)でも利確する = 両方の道で利確(リードの決め)。決まらない足に数え、
    良い側 = 損益の良い方の道、悪い側 = 損益の悪い方の道(止めない)。"""
    g = _two_level_short()
    q = g._q
    tp = (P + 600) - 0.8 * q.vola / 2
    nxt = math.floor(max(q.s1, P + 700 + q.vola))  # 売りの段は 1 円に切り下げ(L-595)
    fills3 = [P + 500, P + 700, nxt]
    tp3 = math.ceil(math.fsum(fills3) / 3 - 0.8 * q.vola / 3)  # 売り持ちの利確は 1 円に切り上げ
    b41 = bar(41, P + 650, P + 650, h=nxt + 1, lo=tp - 1)
    assert tp3 > tp - 1
    rows = g.feed(b41)
    assert (rows[0]["exit_reason"], rows[0]["levels"], rows[0]["undecided"]) == ("利確1", 2, 1)
    assert rows[0]["exit_price"] == pytest.approx(tp)
    bd = MatildaLimitSim(fill_side="bad")
    feed(bd, base() + [bar(40, P + 600, P + 600, h=P + 701, lo=P + 600)])
    rb = bd.feed(b41)
    assert (rb[0]["exit_reason"], rb[0]["levels"], rb[0]["undecided"]) == ("利確1", 3, 1)
    assert rb[0]["exit_price"] == pytest.approx(tp3)
    assert rows[0]["pnl_bp"] > rb[0]["pnl_bp"] == pytest.approx(pnl(-1, fills3, tp3))


def test_8_no_second_round_trip_after_take_profit():
    """利確の後、同じ足では入らない(L-581)。"""
    s = _two_level_short()
    q = s._q
    tp = (P + 600) - 0.8 * q.vola / 2
    rows = s.feed(bar(41, P + 650, P + 650, h=P + 650, lo=q.b1 - 1))  # 利確の後、B1 も越えた
    assert rows[0]["exit_reason"] == "利確1" and rows[0]["exit_price"] == pytest.approx(tp)
    assert s._side == 0


# ---------------------------------------------------------------- 9. 幅の門
def test_9_width_gate_blocks_entry():
    amp = 100.0  # 幅 100 円 < MIN_WIDTH_RATIO × 終値(約 130 円)
    assert amp / (P + amp) < MIN_WIDTH_RATIO
    b40 = bar(40, P + 4000, P + 4000, h=P + 5000, lo=P + 4000)  # S1 = P+50 + 2 × 100。安値は利確に届かない
    s = sim()
    feed(s, base(amp=amp) + [b40])
    assert s._side == 0
    s = sim(width_gate=False)
    feed(s, base(amp=amp) + [b40])
    assert s._side == -1 and s._fills[0] == P + 250


# ---------------------------------------------------------------- 10. 損益と取引の切れ目
def test_10_pnl_formula_and_trade_boundaries():
    s = sim()
    rows = feed(s, base() + [bar(40, P + 900, P + 900, h=P + 1300.5, lo=P + 900)])  # 売り 5 段
    assert rows == [] and s._fills == [P + 500, P + 700, P + 900, P + 1100, P + 1300]
    q = s._q
    tp = math.ceil((P + 900) - 0.8 * q.vola / 5)  # 売り持ちの利確は 1 円に切り上げ(L-595)
    assert tp != (P + 900) - 0.8 * q.vola / 5
    rows = s.feed(bar(41, P + 1000, tp - 1, h=P + 1000, lo=tp - 1))
    assert len(rows) == 1
    r = rows[0]
    assert r["pnl_bp"] == pytest.approx(pnl(-1, [P + 500, P + 700, P + 900, P + 1100, P + 1300], tp))
    assert r["entry_ns"] == T0 + 41 * M and r["exit_ns"] == T0 + 42 * M and s._side == 0
    assert r["width"] == 200.0 and r["vola"] == 200.0 and r["ratio"] == 1.0 and r["close_k"] == P and r["brk"] == 0
    # 次の取引は 0 から始まる(段・時計を引き継がない)
    q = s._q
    rows = s.feed(bar(42, q.b1 + 1, q.b1 + 1, h=q.b1 + 1, lo=q.b1 - 1))
    assert s._side == 1 and s._fills == [math.ceil(q.b1)] and s._info["entry_ns"] == T0 + 43 * M  # 買いは切り上げ


# ---------------------------------------------------------------- 11. 暦年の区切りでつないでも同じ
def _walk(n, seed, t0):
    rnd = random.Random(seed)
    px, out = P, []
    for i in range(n):
        o = px
        c = o + rnd.gauss(0, 150)
        out.append(bar(i, o, c, max(o, c) + abs(rnd.gauss(0, 60)), min(o, c) - abs(rnd.gauss(0, 60)),
                       vol=0.0 if i % 53 == 7 else 1.0, t0=t0))
        px = c
    return out


@pytest.mark.parametrize("fill_side", ["good", "bad"])
@pytest.mark.parametrize("bar_min", [1, 5])
def test_11_chunked_by_calendar_year_equals_one_pass(fill_side, bar_min):
    t0 = 1_546_300_800 * NS - 1500 * M  # 2019-01-01T00:00Z の 1500 分前から
    bars = _walk(3000, 3, t0)
    cut = next(i for i, b in enumerate(bars) if b.start_time_ns >= 1_546_300_800 * NS)
    one = sim(fill_side=fill_side, bar_min=bar_min)
    r1 = feed(one, bars) + one.finish()
    two = sim(fill_side=fill_side, bar_min=bar_min)
    r2 = feed(two, bars[:cut]) + feed(two, bars[cut:]) + two.finish()
    assert len(r1) > 20 and r1 == r2


# ---------------------------------------------------------------- 12. 先読みなし
def test_12_bar_k1_is_judged_with_quantities_made_before_it():
    """足 k+1 の実体が中心を大きく動かしても、足 k+1 の入りは足 k までの S1(P+500)で決まる。"""
    s = sim()
    feed(s, base() + [bar(40, P + 3000, P + 3000, h=P + 3000, lo=P + 3000)])
    assert s._side == -1 and s._fills[0] == P + 500


@pytest.mark.parametrize("k", [60, 200, 777, 1500])
def test_12_changing_bar_k1_high_low_does_not_change_what_was_decided_through_bar_k(k, monkeypatch):
    """足 k+1 の高値・安値を変えた 2 通りで: 足 k までの行・持ち高・量が同じ。足 k+1 の出来事(_leg)に渡る量は
    足 k までで作った量そのもの。足 k+1 を窓に入れた後の量は 2 通りで違う(ヒゲの端で窓を作るので、変えた効きが
    次の量には出る = 足 k+1 の中では使っていない)。"""
    bars = _walk(1600, 11, T0)
    snaps, used, after = [], [], []
    for dh in (0.0, 5000.0):
        b = bars[k + 1]
        alt = bar(k + 1, b.open, b.close, b.high + dh, b.low - dh)
        s = sim(range_from="wick")
        rows = feed(s, bars[:k + 1])
        snap = (rows, s._side, list(s._fills), s._brk, vars_q(s._q), s.undecided_bars)
        seen = []
        orig = s._leg
        monkeypatch.setattr(s, "_leg", lambda st, up, ext, q, *a, _o=orig, _s=seen: (_s.append(vars_q(q)),
                                                                                     _o(st, up, ext, q, *a))[1])
        s.feed(alt)
        snaps.append(snap)
        used.append(seen)
        after.append(vars_q(s._q))
    assert snaps[0] == snaps[1]
    assert used[1] and all(u == snaps[0][4] for u in used[0] + used[1])
    assert after[0] != after[1]


def vars_q(q):
    return None if q is None else tuple(getattr(q, k) for k in type(q).__slots__)


# ---------------------------------------------------------------- 引数の表(仕様 5)
@pytest.mark.parametrize("kw", [{"window_min": 60}, {"entry": 6}, {"step": 3}, {"n_levels": 3}, {"alert_min": 10},
                                {"break_delay": 2}, {"on_break": "flat"}, {"exit_form": "center", "entry": 2,
                                                                           "exit_setting": 0.5},
                                {"exit_setting": 0.8}, {"step_exit": 0.0}, {"width_gate": 1}, {"bar_min": 15}])
def test_values_outside_the_table_are_refused(kw):
    with pytest.raises(ValueError):
        sim(**kw)


def test_center_form_takes_profit_at_center_plus_exit_setting_vola():
    s = sim(exit_form="center", entry=3, exit_setting=2)
    feed(s, base() + [bar(40, P + 650, P + 650, h=P + 700.5, lo=P + 650)])  # S1 = P+100 + 3 × 200
    assert s._fills == [P + 700]
    tp, why = s._tp(s._state(), s._q, T0 + 41 * M)
    assert why == "中心型の利確" and tp == s._q.center + 2 * s._q.vola


# ---------------------------------------------------------------- 足の頭(リードの決め。仕様 3-5 の補足)
@pytest.mark.parametrize("fill_side", ["good", "bad"])
def test_head_entry_at_s1_when_open_is_above_then_take_profit_is_decided(fill_side):
    """持ち高 0 で O > S1(P+500): 入りは足の頭で S1 の値段。続く下りで利確(P+500 − 160 = P+340)まで行けば、
    良い側・悪い側とも同じで、決まらない足に数えない。"""
    s = sim(fill_side=fill_side)
    rows = feed(s, base() + [bar(40, P + 600, P + 300, h=P + 600, lo=P + 300)])
    assert len(rows) == 1
    r = rows[0]
    assert (r["entry_price"], r["levels"], r["exit_price"], r["exit_reason"], r["undecided"]) == (
        P + 500, 1, P + 340, "利確1", 0)
    assert s.undecided_bars == 0 and s._side == 0


@pytest.mark.parametrize("fill_side", ["good", "bad"])
def test_head_take_profit_when_open_is_beyond_it(fill_side):
    """売り 2 段を持ち、O が利確の値段より下: 足の頭で利確(利確の値段で約定)。その後の上りで段の値段を越えても
    足さない(利確の後は入らない)。2 通りの道で同じなので決まらない足にならない。"""
    s = MatildaLimitSim(fill_side=fill_side)
    feed(s, base() + [bar(40, P + 600, P + 600, h=P + 701, lo=P + 600)])
    q = s._q
    tp = (P + 600) - 0.8 * q.vola / 2
    nxt = max(q.s1, P + 700 + q.vola)
    rows = s.feed(bar(41, tp - 5, tp - 5, h=nxt + 1, lo=tp - 5))
    assert len(rows) == 1
    r = rows[0]
    assert (r["exit_reason"], r["levels"], r["undecided"]) == ("利確1", 2, 0)
    assert r["exit_price"] == pytest.approx(tp) and s._side == 0 and s.undecided_bars == 0


def test_head_levels_below_open_fill_at_their_own_prices_and_the_rest_in_the_up_leg():
    """O = P+800: 段 P+500・P+700 は頭で、P+900 は上りの脚で(H = P+900.5)。約定の値段は段の値段。"""
    s = sim()
    feed(s, base() + [bar(40, P + 800, P + 850, h=P + 900.5, lo=P + 800)])
    assert s._fills == [P + 500, P + 700, P + 900]


# ---------------------------------------------------------------- 批評家【3】の壊し方を捕まえる試験と、直し 1〜3・5 の試験
def _inject(s, side, fills, t0):
    """持ち高を直に置く(規則の組み合わせを短い並びで作るため)。"""
    q = s._q
    s._side, s._fills, s._t0 = side, list(fills), t0
    s._info = {"entry_ns": t0, "side": side, "width": q.width, "vola": q.vola, "ratio": q.width / q.vola,
               "brk": s._brk, "close_k": q.close}


def test_no_take_profit_in_either_path_uses_the_path_to_the_nearer_extreme(monkeypatch):
    """(M03)両方の道で利確が起きず結果が違う足は、始値に近い方の端へ先に行く道。利確を遠くへ置き、持ち高 0 から
    S1(P+500)と B1(P−300)の両方を越える足を作る。始値 P+400 は高値に近い → 上が先: 売りが先に入り、下りで
    反対の入り(B1)で閉じ、良い側は買いで入り直す。"""
    s = sim()
    feed(s, base())
    monkeypatch.setattr(s, "_tp", lambda st, q, t: (P + st.side * 10 ** 6, "利確1"))
    rows = s.feed(bar(40, P + 400, P + 400, h=P + 501, lo=P - 301))
    assert [(r["side"], r["entry_price"], r["exit_price"], r["exit_reason"], r["undecided"]) for r in rows] == [
        (-1, P + 500, P - 300, "反対の入り", 1)]
    assert s._side == 1 and s._fills == [P - 300]


def test_bup_is_updated_during_a_break_even_when_hi_equals_hi2():
    """(M05)v37 504 行 `range_max != range_max2 or break_flg != 0`: ブレイク中は hi == hi2 でも bup を作り直す。"""
    s = sim()
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 450, h=P + 460, lo=P + 200))
    q = s._q
    assert s._brk == 1 and q.hi2 == P + 450 and q.width == 450.0
    assert q.bup == P + 450 + 225  # 更新しなければ P+300 のまま


def test_up_break_is_checked_before_down_break():
    """(M06)上と下の判定値を同じ足で両方越えたら上(v37 934・942 行の if / elif)。"""
    s = sim()
    feed(s, two_phase(a1=600.0, lo1=P - 200))
    q = s._q
    assert (max(q.bup, q.hi2), min(q.bdp, q.lo2)) == (P + 400, P - 200)
    s.feed(bar(80, P + 100, P + 150, h=P + 450, lo=P - 250))
    assert s._brk == 1


def test_head_up_side_is_processed_before_down_side():
    """(M07)足の頭で上りの側(上のブレイクの判定値 P+400 < 始値)と下りの側(売りの利確 P+840 > 始値)の両方に
    当たったら、上りの側 → 下りの側【置いた形】: 売りは判定値の値段で閉じる。"""
    s = sim()
    feed(s, two_phase())
    _inject(s, -1, [P + 1000], T0 + 80 * M)
    assert s._tp(s._state(), s._q, T0 + 80 * M) == (P + 840, "利確1")
    rows = s.feed(bar(80, P + 600, P + 600, h=P + 600, lo=P + 600))
    assert (rows[0]["exit_reason"], rows[0]["exit_price"]) == ("反対のブレイク", P + 400)


def test_relax_after_20_minutes_is_judged_at_the_start_of_the_bar():
    """(M08)番号 60 の足は始まりが t0 + 19 分(終わりは + 20 分)なので exit_flg 1 のまま利確する。"""
    s = _two_level_short()
    _hold_bars(s, 41, 60)
    tp, why = s._tp(s._state(), s._q, T0 + 60 * M)
    assert why == "利確1"
    rows = s.feed(bar(60, P + 650, P + 650, h=P + 650, lo=tp - 1))
    assert (rows[0]["exit_reason"], rows[0]["exit_price"]) == ("利確1", pytest.approx(tp))


def test_no_time_exit_during_a_break():
    """(M09)ブレイク中は 40 分の成行を判定しない(v37 1027〜1036 行に時間の条件が無い)。follow で判定値の値段
    P+400 に買い 1 段、その後 45 本、中心より上・利確より下の P+390 で止まる。"""
    s = sim(on_break="follow")
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 420, h=P + 450, lo=P + 200))
    assert s._side == 1 and s._fills == [P + 400] and s._brk == 1
    rows = _hold_bars(s, 81, 126, px=P + 390)
    assert rows == [] and s._side == 1 and s._brk == 1 and not s._pending_time


def test_follow_does_not_enter_after_take_profit_in_the_same_bar():
    """(M11)利確の後、同じ足のブレイクで follow は入らない(利確の後は入らない)。"""
    s = sim(on_break="follow")
    feed(s, two_phase())
    s.feed(bar(80, P - 250, P - 250, h=P - 250, lo=P - 300.5))  # 買い 1 段 P−300
    q = s._q
    pb = max(q.bup, q.hi2)
    tp, _ = s._tp(s._state(), q, T0 + 81 * M)
    assert tp < pb == P + 425
    rows = s.feed(bar(81, P - 250, pb + 5, h=pb + 15, lo=P - 250))
    assert rows[0]["exit_reason"] == "利確1" and s._brk == 1 and s._side == 0
    # brk = 1 の間は上のブレイクが起き直さない(st.brk != 1)ので、次の足で判定値を越えても follow は入らない
    q = s._q
    assert max(q.bup, q.hi2) < P + 5000
    assert s.feed(bar(82, pb + 5, pb + 5, h=P + 5000, lo=pb + 5)) == []
    assert s._brk == 1 and s._side == 0


def test_same_price_break_comes_before_take_profit():
    """(M01)同じ値段ならブレイク → 利確の順(_PRIO)。"""
    s = sim()
    feed(s, two_phase())
    _inject(s, 1, [P], T0 + 80 * M)
    q = s._q
    st = s._run_path(s._state(), True, (P + 100, P + 300, P + 100, T0 + 80 * M, T0 + 81 * M), q, 1, P + 160, False)
    assert st.events == [("brk", P + 160), ("tp", P + 160)]


def test_break_off_uses_the_center_made_before_the_bar():
    """(M20)解けたかは足 k の中心で判定する。足 81 の実体が新しい上端を作っても(新しい中心は上がる)、終値が
    足 80 までの中心より上なら解けない。"""
    s = sim()
    feed(s, two_phase())
    s.feed(bar(80, P + 200, P + 380, h=P + 400.5, lo=P + 200))
    center = s._q.center
    assert s._brk == 1 and center == P + 190
    s.feed(bar(81, P + 2000, center + 1, h=P + 2000, lo=center + 1))
    assert s._brk == 1


def test_bad_path_stopped_at_take_profit_still_crosses_the_break_price_later_on_the_leg():
    """(直し 2)利確の手前で止めた後も、その脚の先のブレイクの判定値は値段の順に越え、brk だけ変える。"""
    s = sim()
    feed(s, two_phase())
    _inject(s, 1, [P], T0 + 80 * M)
    q = s._q
    st = s._run_path(s._state(), True, (P + 100, P + 500, P + 100, T0 + 80 * M, T0 + 81 * M), q, 1, P + 400, True)
    assert st.events == [("stop", P + 160), ("brk", P + 400)]
    assert st.brk == 1 and st.side == 1 and st.closed == []


def test_width_gate_upper_limit():
    """(直し 3)幅 / 終値 > 100000 / 1,152,502(v37 135 行 over_range_setting)なら入らない。width_gate=False なら入る。"""
    from bot.research.matilda_limit_sim import MAX_WIDTH_RATIO
    assert MAX_WIDTH_RATIO == 100000.0 / 1152502.0
    b40 = bar(40, P + 295000, P + 295000, h=P + 300000, lo=P + 290000)
    for amp, gate, side in ((100000.0, True, 0), (100000.0, False, -1), (80000.0, True, -1)):
        s = sim(width_gate=gate)
        feed(s, base(amp=amp) + [b40])
        assert s._side == side, (amp, gate)


def _load_w4(name):
    """scripts/w4_measure の台本を読み込む。台本は `from common import ...` で同じ置き場の common を読むが、
    全部の試験を続けて回すと別の試験が別の `common`(tests/bt/battery/item_0/adapters/common.py など)を
    sys.modules に先に入れていて取り違える。読み込む間だけ別の置き場の common・post・run_v2 を外し、後で戻す。"""
    import importlib
    import os
    import sys
    d = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "w4_measure"))
    if d not in sys.path:
        sys.path.insert(0, d)
    if name in sys.modules:
        return sys.modules[name]
    foreign = {k: sys.modules.pop(k) for k in ("common", "post", "run_v2") if k in sys.modules
               and os.path.dirname(os.path.abspath(getattr(sys.modules[k], "__file__", None) or "")) != d}
    try:
        return importlib.import_module(name)
    finally:
        for k, m in foreign.items():
            sys.modules[k] = m


def _runner():
    return _load_w4("c4_limit_run")


def test_year_stats():
    r = _runner()
    rows = [{"pnl_bp": x, "undecided": u} for x, u in ((1.0, 0), (-2.0, 2), (0.0, 0), (3.0, 1))]
    st = r.year_stats(rows, 2.0)
    assert (st["trades"], st["wins"], st["losses"]) == (4, 2, 1)
    assert (st["avg_win_bp"], st["avg_loss_bp"], st["sum_win_bp"], st["sum_loss_bp"], st["sum_bp"]) == (
        2.0, -2.0, 4.0, -2.0, 2.0)
    assert st["per_day"] == {"trades": 2.0, "wins": 1.0, "pnl_bp": 1.0}
    assert (st["undecided_bars_in_trades"], st["trades_with_undecided"]) == (3, 2)
    empty = r.year_stats([], 0.0)
    assert empty["avg_win_bp"] is None and empty["per_day"]["trades"] is None


def test_by_year_uses_exit_year_and_keeps_the_finish_row():
    """(直し 5)年 = 出の時刻の暦年。終わりが 1 月 1 日 00:00 で、期間の終わりの行の出の時刻が翌年でも落とさない。"""
    r = _runner()
    y18, y19 = 1_514_764_800 * NS, 1_546_300_800 * NS  # 2018-01-01・2019-01-01(UTC)
    lo, hi = y19 - 2 * 86_400 * NS, y19
    rows = [{"exit_ns": y19 - 3600 * NS, "pnl_bp": 1.0, "undecided": 0},
            {"exit_ns": y19, "pnl_bp": -1.0, "undecided": 1}]
    out = r.by_year(rows, lo, hi)
    assert sorted(out) == ["2018", "2019"] and y18 < lo
    assert (out["2018"]["trades"], out["2018"]["days"]) == (1, 2.0)
    assert (out["2019"]["trades"], out["2019"]["days"], out["2019"]["per_day"]["trades"]) == (1, 0.0, None)
    assert sum(v["trades"] for v in out.values()) == len(rows)


# ---------------------------------------------------------------- 1 円刻み(オーナー L-595)
def test_order_prices_are_rounded_to_one_yen_against_us():
    """売りの注文は切り下げ、買いの注文は切り上げ。窓を 40 本の往復 P ↔ P+201(実体 201、中心 P+100.5、
    vola 201)にすると S1 = P+502.5 → 売りの入り P+502、B1 = P−301.5 → 買いの入り P−301。"""
    from bot.research.matilda_limit_sim import _dn, _up
    assert (_dn(10.7), _up(10.2), _dn(10.0), _up(10.0)) == (10.0, 11.0, 10.0, 10.0)
    assert (_dn(1000502.9999999999), _up(1000502.0000000001)) == (1000503.0, 1000502.0)  # 浮動小数の誤差は吸う
    assert (_dn(10.9995), _up(10.0005)) == (10.0, 11.0)  # 遊びは誤差の大きさ(1e-6)だけ。0.0005 円は吸わない
    s = sim()
    feed(s, base(amp=201.0))
    assert (s._q.s1, s._q.b1) == (P + 502.5, P - 301.5)
    feed(s, [bar(40, P + 450, P + 450, h=P + 503, lo=P + 450)])
    assert s._fills == [P + 502]
    b = sim()
    feed(b, base(amp=201.0) + [bar(40, P - 250, P - 250, h=P - 250, lo=P - 302)])
    assert b._fills == [P - 301]
    # 利確: 買い持ちは売りの注文 = 切り下げ、売り持ちは買いの注文 = 切り上げ
    st = b._state()
    tp, _ = b._tp(st, b._q, T0 + 41 * M)
    raw = (P - 301) + 0.8 * b._q.vola
    assert raw != int(raw) and tp == math.floor(raw)
    st2 = s._state()
    tp2, _ = s._tp(st2, s._q, T0 + 41 * M)
    raw2 = (P + 502) - 0.8 * s._q.vola
    assert raw2 != int(raw2) and tp2 == math.ceil(raw2)


def test_fills_are_judged_against_the_rounded_price():
    """S1 = P+502.5 の売りの注文は P+502。高値 P+502.5(> 丸めた値段)なら約定、P+502 ちょうどなら約定しない。"""
    s = sim()
    feed(s, base(amp=201.0) + [bar(40, P + 450, P + 450, h=P + 502, lo=P + 450)])
    assert s._side == 0
    s = sim()
    feed(s, base(amp=201.0) + [bar(40, P + 450, P + 450, h=P + 502.5, lo=P + 450)])
    assert s._fills == [P + 502]  # 丸める前の S1(P+502.5)は越えていないが、丸めた P+502 は越えた


def test_break_close_price_is_rounded_but_the_break_threshold_is_not():
    """entry = 1。判定値 pb は丸めずに越えたかを見て、売り持ちを閉じる値段(買い)は _up(pb)。"""
    s = sim(entry=1)
    feed(s, two_phase(a1=401.0))
    q = s._q
    pb = max(q.bup, q.hi2)
    assert pb == P + 401
    rows = s.feed(bar(80, P + 200, P + 401, h=P + 401.5, lo=P + 200))
    assert s._brk == 1 and rows[0]["exit_reason"] == "反対のブレイク" and rows[0]["exit_price"] == P + 401


def test_no_fractional_prices_in_trade_rows():
    """約定の値段(各段と出の値段)は全部 1 円刻み。建値(平均)は小数が残ってよい。"""
    for fill_side in ("good", "bad"):
        s = sim(fill_side=fill_side)
        rows = []
        orig = s._close
        fills_seen = []
        s._close = lambda st, price, reason, t, _o=orig: (fills_seen.extend(st.fills), _o(st, price, reason, t))[1]
        for b in _walk(3000, 5, T0):  # bitFlyer の足と同じく 4 本値を 1 円刻みにする
            o, c = round(b.open), round(b.close)
            rows += s.feed(bar(int((b.start_time_ns - T0) // M), o, c, max(o, c, round(b.high)),
                               min(o, c, round(b.low)), vol=b.volume))
        rows += s.finish()
        assert len(rows) > 20 and fills_seen
        assert all(r["exit_price"] == int(r["exit_price"]) for r in rows)
        assert all(f == int(f) for f in fills_seen)
        assert any(r["entry_price"] != int(r["entry_price"]) for r in rows)


# ---------------------------------------------------------------- 1 円刻みの向き(批評家の指摘、リードの決め)
def _half_up():
    """上のブレイクの判定値が半端(P+301.5)になる並び: 前半 P ↔ P+300、後半 P ↔ P+201。
    番号 79 の足の終わりで hi = P+201・幅 201 → bup = P+301.5、hi2 = P+300 → pb = P+301.5。"""
    return two_phase(a1=300.0, a2=201.0)


def _half_down():
    """下のブレイクの判定値が半端(P−100.5)になる並び: 前半 P−100 ↔ P+201、後半 P ↔ P+201。
    lo = P・幅 201 → bdp = P−100.5、lo2 = P−100 → pb = P−100.5。hi == hi2 なので上は未定。"""
    return two_phase(a1=301.0, a2=201.0, lo1=P - 100)


def test_half_break_price_closes_short_at_ceil_and_long_at_floor():
    s = sim()
    feed(s, _half_up())
    assert max(s._q.bup, s._q.hi2) == P + 301.5
    _inject(s, -1, [P + 250], T0 + 80 * M)
    rows = s.feed(bar(80, P + 200, P + 200, h=P + 302, lo=P + 200))
    assert (rows[0]["exit_reason"], rows[0]["exit_price"]) == ("反対のブレイク", P + 302)  # 買い = 切り上げ
    s = sim()
    feed(s, _half_down())
    assert s._q.bup is None and min(s._q.bdp, s._q.lo2) == P - 100.5
    _inject(s, 1, [P + 50], T0 + 80 * M)
    rows = s.feed(bar(80, P + 50, P + 50, h=P + 50, lo=P - 101))
    assert (rows[0]["exit_reason"], rows[0]["exit_price"]) == ("反対のブレイク", P - 101)  # 売り = 切り下げ


def test_follow_enters_up_break_at_ceil_and_down_break_at_floor():
    s = sim(on_break="follow")
    feed(s, _half_up())
    s.feed(bar(80, P + 200, P + 200, h=P + 302, lo=P + 200))
    assert (s._side, s._fills) == (1, [P + 302])
    s = sim(on_break="follow")
    feed(s, _half_down())
    s.feed(bar(80, P + 50, P + 50, h=P + 50, lo=P - 101))
    assert (s._side, s._fills) == (-1, [P - 101])


def test_center_form_half_take_profit_is_floor_for_long_and_ceil_for_short():
    """中心 P+100.5・vola 201、exit_setting 2: 売り持ちの利確 P+502.5 → P+503、買い持ちの利確 P−301.5 → P−302。"""
    s = sim(exit_form="center", entry=3, exit_setting=2)
    feed(s, base(amp=201.0))
    _inject(s, -1, [P + 700], T0 + 40 * M)
    assert s._tp(s._state(), s._q, T0 + 40 * M) == (P + 503, "中心型の利確")
    _inject(s, 1, [P - 500], T0 + 40 * M)
    assert s._tp(s._state(), s._q, T0 + 40 * M) == (P - 302, "中心型の利確")


def test_opposite_entry_close_price_is_dn_s1_for_long_and_up_b1_for_short(monkeypatch):
    """反対の入りは feed からは起きない(利確が先)ので _leg を直に呼ぶ。S1 = P+502.5 → 買い持ちは P+502 で閉じる、
    B1 = P−301.5 → 売り持ちは P−301 で閉じる。"""
    s = sim()
    feed(s, base(amp=201.0))
    q = s._q
    monkeypatch.setattr(s, "_tp", lambda st, q, t: (P + st.side * 10 ** 6, "利確1"))
    _inject(s, 1, [P - 400], T0 + 40 * M)
    st = s._state()
    s._leg(st, True, P + 503, q, 0, None, False, T0 + 40 * M, T0 + 41 * M)
    assert st.events[0] == ("opp", P + 502) and st.closed[0][2] == P + 502
    _inject(s, -1, [P + 600], T0 + 40 * M)
    st = s._state()
    s._leg(st, False, P - 302, q, 0, None, False, T0 + 40 * M, T0 + 41 * M)
    assert st.events[0] == ("opp", P - 301) and st.closed[0][2] == P - 301


def test_break_is_ordered_at_its_tick_before_a_level_at_the_same_tick():
    """entry = 1: 売りの次の段 = _dn(S1 = P+301.5) = P+301。ブレイクの判定値 P+301.5 は上りの脚では P+301 の刻みに
    並び、同じ刻みの段の追加より先に起きる → 段を足さずに 1 段のまま P+302 で閉じる。"""
    s = sim(entry=1)
    feed(s, _half_up())
    assert s._q.s1 == P + 301.5
    _inject(s, -1, [P + 100], T0 + 80 * M)
    rows = s.feed(bar(80, P + 200, P + 200, h=P + 302, lo=P + 200))
    assert (rows[0]["exit_reason"], rows[0]["levels"], rows[0]["exit_price"]) == ("反対のブレイク", 1, P + 302)
