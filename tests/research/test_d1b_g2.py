"""前提の直接の測り(D1b)担当 G2 の台本(scripts/d1b/g2/)の試験。作り物のデータで、各量が手計算・カードの関数と合うこと、
先読みが無いこと(時刻 t の判断に t より後の値を使っていない)、区間の種で結果が決まること。"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "d1b" / "g2"))
import g2lib as L  # noqa: E402
import g2_item4 as I4  # noqa: E402
import g2_item5 as I5  # noqa: E402
import g2_item6 as I6  # noqa: E402
import g2_item7 as I7  # noqa: E402
import g2_item8 as I8  # noqa: E402
import g2_item11 as I11  # noqa: E402

MIN = L.MIN_NS
T0 = L.iso_ns("2020-01-05T15:00:00Z")  # 日本時間 2020-01-06(月)0 時


def mk_grid(closes, t0=T0, opens=None, highs=None, lows=None, vols=None):
    c = np.asarray(closes, dtype=float)
    o = c.copy() if opens is None else np.asarray(opens, dtype=float)
    h = np.fmax(o, c) if highs is None else np.asarray(highs, dtype=float)
    lo = np.fmin(o, c) if lows is None else np.asarray(lows, dtype=float)
    v = np.where(np.isfinite(c), 1.0, 0.0) if vols is None else np.asarray(vols, dtype=float)
    return L.Grid(t0, o, h, lo, c, v)


def walk(n, seed=1, start=1_000_000.0, step=0.001):
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(0, step, n)))
    o = np.concatenate([[start], c[:-1]]) * np.exp(rng.normal(0, step / 3, n))
    h = np.fmax(o, c) * (1 + np.abs(rng.normal(0, step / 2, n)))
    lo = np.fmin(o, c) * (1 - np.abs(rng.normal(0, step / 2, n)))
    return o, h, lo, c


class FakeView:
    def __init__(self, bars, t, refs=None):
        self._bars, self.now_ns, self._refs = bars, t, refs or {}

    def bars(self, n):
        return self._bars[-n:]

    def ref(self, name):
        return self._refs[name]


def bar_objs(g):
    out = []
    for i in np.flatnonzero(g.ne):
        s = int(g.start(i))
        out.append(SimpleNamespace(start_time_ns=s, received_time_ns=s + MIN, exchange_time_ns=s + MIN, open=g.o[i],
                                   high=g.h[i], low=g.l[i], close=g.c[i], volume=g.v[i]))
    return out


# ---------------------------------------------------------------- 共通部

def test_days_halves_and_years():
    d = L.Days.of(L.iso_ns("2019-12-30T15:00:00Z"), L.iso_ns("2020-01-03T15:00:00Z"))
    assert [L.day_str(x) for x in d.nums] == ["2019-12-31", "2020-01-01", "2020-01-02", "2020-01-03"]
    p = d.parts()
    assert [L.day_str(x) for x in p["前半"]] == ["2019-12-31", "2020-01-01"]
    assert sorted(d.years()) == [2019, 2020]


def test_ratio_ci_hand_and_seed_fixed():
    num = np.array([1, 0, 2, 1, 0, 3, 1, 1, 0, 2.0] * 10)
    den = np.array([2, 1, 2, 2, 1, 4, 1, 2, 1, 2.0] * 10)
    num[::7] += 1
    den[::7] += 1
    a = L.ratio_ci(num, den)
    assert a["est"] == pytest.approx(num.sum() / den.sum())
    assert a["lo"] < a["est"] < a["hi"]
    b = L.ratio_ci(num, den)
    assert (a["lo"], a["hi"], a["se"]) == (b["lo"], b["hi"], b["se"])
    assert a["mde"] == pytest.approx(2.8 * a["se"])
    old = L.SEED
    try:
        L.SEED = old + 1
        c = L.ratio_ci(num, den)
    finally:
        L.SEED = old
    assert (c["lo"], c["hi"], c["se"]) != (a["lo"], a["hi"], a["se"])


def test_ratio_ci_zero_denominator_resample_is_reported_not_hidden():
    den = np.zeros(20)
    den[3] = 1
    r = L.ratio_ci(np.where(den > 0, 1.0, 0.0), den)
    assert r["est"] == 1.0 and r["lo"] is None and r["why"].startswith("区間なし")


def test_corr_ci_matches_numpy():
    rng = np.random.default_rng(3)
    x, y = rng.normal(size=50), rng.normal(size=50)
    acc = {"n": np.ones(50), "sx": x, "sy": y, "sxx": x * x, "syy": y * y, "sxy": x * y}
    assert L.corr_ci(acc, ci=False)["est"] == pytest.approx(np.corrcoef(x, y)[0, 1])


def test_grid_next_prev():
    g = mk_grid([1, np.nan, np.nan, 2, np.nan])
    assert list(g.next_ne(np.arange(5))) == [0, 3, 3, 3, 5]
    assert list(g.prev_ne(np.arange(5))) == [0, 0, 0, 3, 3]


def test_check_period_refuses_after_cut():
    with pytest.raises(SystemExit):
        L.check_period(L.iso_ns("2023-12-01T15:00:00Z"), L.iso_ns("2023-12-18T15:00:00Z"))


# ---------------------------------------------------------------- # 4

def test_item4_window_hand():
    # 40 本は平らな足(始値 = 終値 = 100、実体 0)+ 1 本だけ実体 4。窓 40 本の中心・平均実体・比
    n = 41
    o = np.full(n, 100.0)
    c = np.full(n, 100.0)
    o[20], c[20] = 100.0, 104.0
    g = mk_grid(c, opens=o)
    idx, sig, center, vola, ratio, warm = I4.signals(g)
    k = 40  # 窓 = 1〜40
    assert warm[k] and not warm[38]
    assert center[k] == pytest.approx(102.0)
    assert vola[k] == pytest.approx(4 / 40)
    assert ratio[k] == pytest.approx(4 / 0.1)
    assert sig[k] == 1  # 終値 100 < 中心 − 2 × 0.1 = 101.8 → 下に離れた(中心へは +1)


def test_item4_signal_matches_card_when_flat():
    from bot.research.cards.library.c4_owner_matilda_range import C4OwnerMatildaRange
    o, h, lo, c = walk(700, seed=5)
    g = mk_grid(c, opens=o, highs=h, lows=lo)
    idx, sig, center, vola, ratio, warm = I4.signals(g)
    card = C4OwnerMatildaRange(width_gate=False, trend_gate=False, levels=False)
    bars = bar_objs(g)
    prev, checked, opened = 0.0, 0, 0
    for k in range(len(bars)):
        e = card.exposure(FakeView(bars[:k + 1], bars[k].exchange_time_ns))
        if prev == 0.0:
            assert e == sig[k], k  # 持ち高 0 からは、合図があればその向きに 1 段(門なし)
            checked += 1
            opened += e != 0
        prev = e
    assert checked > 100 and opened > 5


def test_item4_episodes():
    assert list(I4.episodes(np.array([0, 1, 1, 0, -1, -1, 1], dtype=np.int8))) == [1, 4, 6]


def test_item4_outcomes_hand():
    n = 50
    o = np.full(n, np.nan)
    h, lw, c = o.copy(), o.copy(), o.copy()
    o[0] = h[0] = lw[0] = c[0] = 120.0
    o[1], h[1], lw[1], c[1] = 110.0, 113.0, 109.0, 112.0
    o[2], h[2], lw[2], c[2] = 112.0, 115.0, 105.5, 105.9  # (B) 終値 < 110 − 0.8 × 5 = 106 で戻る
    o[3], h[3], lw[3], c[3] = 105.9, 106.0, 104.0, 104.5  # (A) 終値 <= 中心 105 で戻る
    g = mk_grid(c, opens=o, highs=h, lows=lw)
    r = I4.outcomes(g, np.array([0]), np.array([-1]), np.array([105.0]), np.array([5.0]))
    assert r["ok"][0] and r["S"][0] == 110.0
    assert r["retA"][0] and r["minA"][0] == 3
    assert r["retB"][0] and r["minB"][0] == 2
    assert r["advA"][0] == pytest.approx(math.log(115 / 110) * 1e4)  # 戻った足(3)より前の足 1・2
    assert r["advB"][0] == pytest.approx(math.log(113 / 110) * 1e4)  # 足 1 だけ


def test_item4_not_returned_uses_whole_path_and_floor_zero():
    n = 50
    c = np.full(n, np.nan)
    o, h, lw = c.copy(), c.copy(), c.copy()
    o[0] = h[0] = lw[0] = c[0] = 90.0
    for j in range(1, 41):  # 40 分 ずっと中心(100)より下で、起点 90 より上にしか動かない
        o[j], c[j], h[j], lw[j] = 90.0, 91.0, 91.5, 90.0
    g = mk_grid(c, opens=o, highs=h, lows=lw)
    r = I4.outcomes(g, np.array([0]), np.array([1]), np.array([100.0]), np.array([2.0]))
    assert not r["retA"][0] and math.isnan(r["minA"][0])
    assert r["advA"][0] == 0.0  # 買いの向きの不利 = −ln(安値 ÷ 90) <= 0 → 0
    assert not r["retB"][0]  # 終値 91 は 90 + 0.8 × 2 = 91.6 を越えない


def test_item4_no_lookahead():
    o, h, lo, c = walk(400, seed=7)
    g1 = mk_grid(c, opens=o, highs=h, lows=lo)
    c2, o2 = c.copy(), o.copy()
    c2[250:] *= 1.05
    o2[250:] *= 0.95
    g2 = mk_grid(c2, opens=o2, highs=np.fmax(h, np.fmax(o2, c2)), lows=np.fmin(lo, np.fmin(o2, c2)))
    a, b = I4.signals(g1), I4.signals(g2)
    for x, y in zip(a, b):
        assert np.array_equal(np.asarray(x)[:250], np.asarray(y)[:250])


# ---------------------------------------------------------------- # 5

def test_item5_hand():
    n = 1440
    o = np.full(n, np.nan)
    c = o.copy()
    o[0], c[0] = 100.0, 101.0
    o[1], c[1] = 101.0, 99.0
    o[2], c[2] = 99.0, 103.0
    o[594], c[594] = 103.0, 102.0  # 9:54〜9:55 の足 = P_F。決定には入らない(終わり = 9:55)
    g = mk_grid(c, opens=o)
    days = L.Days.of(T0, T0 + L.DAY_NS)
    d, i0 = I5.window_slots(g, days, 0)
    assert list(d) == [L.jst_day(T0)] and list(i0) == [0]
    m1, m2, v = I5.pairs(g, i0)
    assert v.sum() == 3 and not v[0, 593]
    assert m1[0, 0] == pytest.approx(math.log(1.01) * 1e4)
    assert m2[0, 1] == pytest.approx(math.log(102 / 99) * 1e4)
    acc = L.DayAcc(days, I5.NAMES)
    I5.day_sums(g, days, 0, acc)
    assert acc.s["den"][0] == 3 and acc.s["agree"][0] == 1  # (+,+) だけ一致
    assert I5.window_slots(g, days, 15)[0].size == 0  # 窓が格子(期間)を越える日は数えない


def test_item5_m1_sign_matches_card_and_no_lookahead():
    from bot.research.cards.library.c5_tokyo_fix_momentum import TokyoFixMomentum
    n = 2 * 1440
    o, h, lo, c = walk(n, seed=11)
    c = np.round(c, -2)  # 0 の値動きも入れる
    g = mk_grid(c, opens=o, highs=np.fmax(h, c), lows=np.fmin(lo, c))
    days = L.Days.of(T0, T0 + 2 * L.DAY_NS)
    d, i0 = I5.window_slots(g, days, 0)
    m1, m2, v = I5.pairs(g, i0)
    card = TokyoFixMomentum()
    bars = bar_objs(g)
    checked = 0
    for k, b in enumerate(bars):
        e = card.exposure(FakeView(bars[:k + 1], b.exchange_time_ns))
        j = int(g.index(b.start_time_ns))
        row, col = divmod(j, 1440)
        if col < I5.WIN_MIN - 1:
            assert e == np.sign(m1[row, col]), (row, col)
            checked += 1
        else:
            assert e == 0.0
    assert checked == 2 * (I5.WIN_MIN - 1)
    c2 = c.copy()
    c2[300:] *= 1.1
    m1b, _, _ = I5.pairs(mk_grid(c2, opens=o), i0)
    assert np.array_equal(m1[0, :299], m1b[0, :299])  # 1 日目の 300 番目の足より前の分の m1 は変わらない


# ---------------------------------------------------------------- # 6

def _usdjpy_rows():
    """金曜(UTC)〜月曜(日本時間)の作り物の行。週の境 = 日本時間 月曜 0 時 = UTC 日曜 15 時。"""
    t_fri = L.iso_ns("2020-01-10T20:00:00Z")  # 金曜
    rows = []
    px = 110.0
    for k in range(60):  # 金曜の 1 時間: 値が動く
        px += 0.01 * (1 if k % 3 else -1)
        rows.append((t_fri + k * MIN, round(px, 3)))
    last = rows[-1][1]
    t_sun = L.iso_ns("2020-01-12T14:00:00Z")
    for k in range(120):  # 日曜 14:00〜16:00 UTC: 平らな行(週の境をまたぐ)
        rows.append((t_sun + k * MIN, last))
    t_open = L.iso_ns("2020-01-12T22:00:00Z")
    for k in range(120):  # 週明け: 最初の行から値が違う
        rows.append((t_open + k * MIN, round(last + 0.05 + 0.003 * ((k * 7) % 5 - 2), 3)))
    return rows


def test_item6_week_open_matches_card():
    from bot.research.cards.library.c6_weekend_gap_revert import FX, WeekendGapRevert
    rows = _usdjpy_rows()
    t0 = L.iso_ns("2020-01-10T15:00:00Z")
    n = 3 * 1440
    o, h, lo, c = walk(n, seed=13)
    g = mk_grid(c, t0=t0, opens=o, highs=h, lows=lo)
    u_t = np.array([r[0] for r in rows], dtype=np.int64)
    u_c = np.array([r[1] for r in rows])
    mine = I6.week_opens(u_t, u_c, I6.bf_asof_fn(g))
    assert len(mine) == 1 and mine[0][0] == L.iso_ns("2020-01-12T22:00:00Z")
    for gap, col in (("usdjpy", 1), ("btc", 2)):
        card = WeekendGapRevert(gap)
        bars = bar_objs(g)
        seen = set()
        for k, b in enumerate(bars):
            t = b.exchange_time_ns
            delivered = [(rt, rc) for rt, rc in rows if rt + I6.LAG_NS <= t]
            card.exposure(FakeView(bars[:k + 1], t, {FX: delivered}))
            if card._open_ns is not None:
                seen.add((card._open_ns, card._g))
        assert len(seen) == 1
        r, gg = seen.pop()
        assert r == mine[0][0] and gg == pytest.approx(mine[0][col], rel=0, abs=1e-15)


def test_item6_outcomes_hand():
    t0 = L.iso_ns("2020-01-11T15:00:00Z")  # 日本時間 日曜 0 時(前の週の中)
    r = L.iso_ns("2020-01-12T22:00:00Z")  # 日本時間 月曜 7 時
    n = 2 * 1440
    c = np.full(n, 1000.0)
    h, lw = c.copy(), c.copy()
    ir = (r - t0) // MIN
    c[ir] = 1010.0  # 足 [r, r + 1 分) の終値 = P0(r + 60 秒 時点)
    h[ir + 5] = 1030.0  # 経路の中で g の向き(上)に続いた点
    c[ir + 59], lw[ir + 59] = 990.0, 980.0  # 足 [r + 59 分, r + 60 分) の終値 = P1
    g = mk_grid(c, t0=t0, opens=c, highs=np.fmax(h, c), lows=np.fmin(lw, c))
    u_t = np.array([t0 + 60 * MIN, t0 + 6 * 60 * MIN, r, r + 30 * MIN, r + 59 * MIN], dtype=np.int64)
    u_c = np.array([99.9, 100.0, 100.5, 101.0, 100.2])
    u_h = u_c + np.array([0.0, 0.0, 0.0, 0.3, 0.0])  # 高値は終値より上(r + 30 分 の行の高値 101.3 が一番深い点)
    u_l = u_c - 0.1
    res = I6.run(g, L.Days.of(t0, t0 + 2 * L.DAY_NS), u_t, u_c, u_h=u_h, u_l=u_l)
    vb, vu = res["variants"]["btc"], res["variants"]["usdjpy"]
    assert list(res["r"]) == [r]
    assert vb["g"][0] == pytest.approx(math.log(1010 / 1000) * 1e4)
    assert vb["m"][0] == pytest.approx(math.log(990 / 1010) * 1e4)
    assert vb["adv"][0] == pytest.approx(math.log(1030 / 1010) * 1e4)
    assert vu["g"][0] == pytest.approx(math.log(100.5 / 100) * 1e4)
    assert vu["m"][0] == pytest.approx(math.log(100.2 / 100.5) * 1e4)
    assert vu["adv"][0] == pytest.approx(math.log(101.3 / 100.5) * 1e4)  # 行の高値で取る(終値の 101 ではない)


# ---------------------------------------------------------------- # 7

def test_item7_width_and_race_hand():
    n = 180
    x = np.zeros(n)
    x[1:60] = np.cumsum(np.where(np.arange(1, 60) % 2, 0.001, -0.001))  # 1 時間の窓の中は ±10 bp の往復
    c = 100.0 * np.exp(x)
    c[61:] = c[60]
    c[75] = c[60] * math.exp(0.02)  # 上に 200 bp
    c[76:] = c[75]
    g = mk_grid(c)
    e, xx, cs = I7.prep(g)
    T = np.array([T0 + 61 * MIN], dtype=np.int64)  # 最初の足の終わり T0 + 1 分 <= T − 1 時間 で温まりの後
    a, w, warm, k = I7.widths(e, xx, cs, T, L.HOUR_NS)
    r = np.diff(np.log(c[:61]))  # 終わりが (T − 1 時間, T] の足 1〜60 の r
    assert warm[0] and w[0] == pytest.approx(math.sqrt(np.sum(r ** 2)))
    assert k[0] == 60 and a[0] == pytest.approx(math.log(c[60]))
    side, hit = I7.race(xx, k, a, w)
    assert side[0] == 1 and hit[0] == 75


def test_item7_width_matches_card_at_race_start():
    from bot.research.cards.library.c7_barrier_race import BarrierRace
    o, h, lo, c = walk(600, seed=17, step=0.002)
    g = mk_grid(c, opens=o, highs=h, lows=lo)
    e, xx, cs = I7.prep(g)
    card = BarrierRace("1h")
    bars = bar_objs(g)
    checked = 0
    for k, b in enumerate(bars):
        before = card._anchor
        card.exposure(FakeView(bars[:k + 1], b.exchange_time_ns))
        if card._anchor is not None and (card._anchor != before or before is None) and card._anchor == math.log(b.close):
            a, w, warm, _ = I7.widths(e, xx, cs, np.array([b.exchange_time_ns]), L.HOUR_NS)
            assert w[0] == pytest.approx(card._width, rel=1e-12)
            checked += 1
    assert checked > 3


def test_item7_no_lookahead():
    o, h, lo, c = walk(400, seed=19)
    T = np.array([T0 + 200 * MIN], dtype=np.int64)
    g1 = mk_grid(c)
    c2 = c.copy()
    c2[200:] *= 1.3
    g2 = mk_grid(c2)
    r1 = I7.widths(*I7.prep(g1), T, L.HOUR_NS)
    r2 = I7.widths(*I7.prep(g2), T, L.HOUR_NS)
    assert r1[0][0] == r2[0][0] and r1[1][0] == r2[1][0]


# ---------------------------------------------------------------- # 8

@pytest.mark.parametrize("session,h", [("jst_day", 15), ("bf_maint", 19)])
def test_item8_dev_sign_matches_card(session, h):
    from bot.research.cards.library.c8_session_mean_revert import SessionMeanRevert
    n = 2 * 1440
    o, hh, lo, c = walk(n, seed=23)
    c = np.round(c, -2)
    g = mk_grid(c, opens=o, highs=np.fmax(hh, c), lows=np.fmin(lo, c))
    i, dev, sid, last = I8.session_dev(g, h)
    card = SessionMeanRevert(session)
    bars = bar_objs(g)
    for k, b in enumerate(bars):
        e = card.exposure(FakeView(bars[:k + 1], b.exchange_time_ns))
        if last[k]:
            assert e == 0.0
        else:
            assert e == -np.sign(dev[k]), k
    assert last.sum() >= 1


def test_item8_running_mean_hand():
    t0 = L.iso_ns("2020-01-05T14:57:00Z")  # 15:00 UTC(jst_day の境)の 3 分前から
    c = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 30.0])
    g = mk_grid(c, t0=t0)
    i, dev, sid, last = I8.session_dev(g, 15)
    # 足 0〜2 は前のセッション(平均 10・15・20)、足 3〜5 は新しいセッション(平均 40・45・40)
    assert dev == pytest.approx(np.log(np.array([10 / 10, 20 / 15, 30 / 20, 40 / 40, 50 / 45, 30 / 40])) * 1e4)
    assert list(last) == [False, False, True, False, False, False]
    mins = I8.crossing(g, i, dev, sid)
    assert np.isnan(mins[1]) and np.isnan(mins[2])  # セッションの終わりまでまたがない
    assert mins[4] == 1  # 足 4(上)→ 足 5(下)


def test_item8_forward_hand():
    o = np.array([100.0, 101.0, 103.0, 99.0, 98.0, 97.0, 96.0, 95.0])
    h = o + 1
    lo = o - 1
    g = mk_grid(o, opens=o, highs=h, lows=lo)
    i0 = np.array([0])
    assert I8.fwd(g, i0, 1, "約定", False)[0] == pytest.approx(math.log(103 / 101) * 1e4)
    assert I8.fwd(g, i0, 5, "約定", False)[0] == pytest.approx(math.log(96 / 101) * 1e4)
    assert I8.fwd(g, i0, 5, "約定", True)[0] == pytest.approx(math.log(96 / 103) * 1e4)
    assert I8.fwd(g, i0, 1, "中ほど", False)[0] == pytest.approx(math.log(103 / 101) * 1e4)
    assert np.isnan(I8.fwd(g, i0, 15, "約定", False)[0])


def test_item8_no_lookahead():
    o, h, lo, c = walk(600, seed=29)
    g1 = mk_grid(c)
    c2 = c.copy()
    c2[300:] *= 1.2
    a = I8.session_dev(g1, 15)
    b = I8.session_dev(mk_grid(c2), 15)
    assert np.array_equal(a[1][:300], b[1][:300])


# ---------------------------------------------------------------- # 11

def test_item11_form_rows_hand():
    days = L.Days.of(T0, T0 + 20 * L.DAY_NS)
    cls = {int(d): ("low" if k % 2 == 0 else "high") for k, d in enumerate(days.nums)}
    num = np.array([1.0 if k % 2 == 0 else 0.0 for k in range(20)])
    den = np.ones(20)
    r = I11.form_rows(days, cls, num, den, days.nums)
    assert r["low"]["est"] == 1.0 and r["high"]["est"] == 0.0 and r["mid"]["est"] is None
    assert r["low − high"]["est"] == 1.0


# ---------------------------------------------------------------- リードの決め(2026-10-06)の形

def test_item4_ratio_edges_from_first_half_only():
    days = L.Days.of(T0, T0 + 10 * L.DAY_NS)  # 前半 = 最初の 5 日
    d = np.repeat(days.nums, 3)
    ratio = np.where(d < days.half_start, np.tile([1.0, 2.0, 3.0], 10), 100.0)
    e = I4.ratio_edges(days, d, ratio)
    assert e == pytest.approx(tuple(np.quantile(np.tile([1.0, 2.0, 3.0], 5), [1 / 3, 2 / 3])))  # 後半の 100 は入らない


def test_item5_corr_per_t_across_days_hand():
    # 3 日 × 時刻 2 つの (m1, m2) の和から、時刻ごとの日をまたいだ相関と、その平均
    rng = np.random.default_rng(31)
    x, y = rng.normal(size=(3, 2)), rng.normal(size=(3, 2))
    M = np.stack([np.ones((3, 2)), x, y, x * x, y * y, x * y], axis=1)  # (日, 6, 時刻)
    r = I5.corr_t(M.sum(axis=0))
    assert r[0] == pytest.approx(np.corrcoef(x[:, 0], y[:, 0])[0, 1])
    assert r[1] == pytest.approx(np.corrcoef(x[:, 1], y[:, 1])[0, 1])
    assert I5.tmean_ci(M, np.arange(3), ci=False)["est"] == pytest.approx(r.mean())


def test_item5_within_day_identity_not_used():
    # 1 日の中では m1 + m2 が一定(機械的に −1)。時刻ごとの相関は日をまたいだ値なので、1 日だけなら出ない
    n = 1440
    o, h, lo, c = walk(n, seed=37)
    g = mk_grid(c, opens=o)
    days = L.Days.of(T0, T0 + L.DAY_NS)
    acc = L.DayAcc(days, I5.NAMES)
    M = I5.day_sums(g, days, 0, acc)
    assert np.isnan(I5.corr_t(M.sum(axis=0))).all()


def test_item6_control_times_weekdays_same_clock():
    r = np.array([L.iso_ns("2020-01-12T22:00:00Z")], dtype=np.int64)  # 日本時間 月曜 7 時
    wi, cs = I6.control_times(r, L.iso_ns("2020-01-20T00:00:00Z"))
    assert list(wi) == [0, 0, 0, 0]
    assert [L.ns_iso(int(t)) for t in cs] == ["2020-01-13T22:00:00Z", "2020-01-14T22:00:00Z", "2020-01-15T22:00:00Z",
                                              "2020-01-16T22:00:00Z"]  # 日本時間 火〜金 7 時
    assert [I6.c5_weekday(int(t)) for t in cs] == [1, 2, 3, 4]
    wi2, cs2 = I6.control_times(r, L.iso_ns("2020-01-15T00:00:00Z"))  # 期間の終わりで切る
    assert len(cs2) == 2  # 13 日・14 日の 22〜23 時(UTC)だけが終わり 15 日 0 時より前


def test_item6_control_values_hand():
    t0 = L.iso_ns("2020-01-11T15:00:00Z")
    r = L.iso_ns("2020-01-12T22:00:00Z")
    n = 7 * 1440
    c = np.full(n, 1000.0)
    ir = (r - t0) // MIN
    c[ir] = 1010.0
    for j, endpx in zip(range(1, 5), (1020.0, 1000.0, 1010.0, 990.0)):  # 対照 4 本の 1 時間の終わりの値(起点は 1000)
        c[ir + j * 1440 + 59] = endpx
    g = mk_grid(c, t0=t0)
    u_t = np.array([t0 + 60 * MIN, t0 + 6 * 60 * MIN, r] + [r + j * L.DAY_NS for j in range(1, 5)], dtype=np.int64)
    u_c = np.array([99.9, 100.0, 100.5, 100.5, 100.5, 100.5, 100.5])
    res = I6.run(g, L.Days.of(t0, t0 + 7 * L.DAY_NS), u_t, u_c, u_h=u_c, u_l=u_c)
    ct = res["variants"]["btc"]["ctrl"]
    gb = res["variants"]["btc"]["g"][0]
    assert ct["n"][0] == 4
    ms = np.log(np.array([1020.0, 1000.0, 1010.0, 990.0]) / 1000.0) * 1e4  # 起点は対照の始まり + 60 秒 時点の 1000
    assert ct["ratio"][0] == pytest.approx(np.mean(-ms / gb))
    assert ct["same"][0] == pytest.approx(np.mean([1.0, 1.0, 0.0]))  # m = 0 の 1 本は符号の一致に入れない(g > 0)


def test_item7_band_edges_first_half_only():
    days = L.Days.of(T0, T0 + 10 * L.DAY_NS)
    d = np.repeat(days.nums, 3)
    w = np.where(d < days.half_start, np.tile([10.0, 20.0, 30.0], 10), 999.0)
    assert I7.band_edges(days, d, w) == pytest.approx(tuple(np.quantile(np.tile([10.0, 20.0, 30.0], 5), [1 / 3, 2 / 3])))


def test_item11_c8_cell_is_lead_decision():
    assert I11.C8_CELL == (15, 15, "約定", True) and I8.offset_ns(15) == c8_jst_offset()


def c8_jst_offset():
    from bot.research.cards.library.c8_session_mean_revert import SESSIONS
    return SESSIONS["jst_day"]



# ---------------------------------------------------------------- 批評家 1 回目の m1・m2・m3 を捕まえる試験

def test_item6_weighted_ratio_hand():
    days = L.Days.of(T0, T0 + 10 * L.DAY_NS)
    d = days.nums[:3]
    res = {"day": d, "variants": {"btc": {"g": np.array([10.0, -40.0, 5.0]), "m": np.array([-5.0, 20.0, 5.0]),
                                          "adv": np.zeros(3),
                                          "ctrl": {k: np.full(3, np.nan) for k in ("same", "ratio", "adv", "wnum", "n", "n_same")}}}}
    s = I6._summ(days, res, "btc", days.nums, ci=False)
    assert s["ratio"]["est"] == pytest.approx(np.mean([0.5, 0.5, -1.0]))
    assert s["wratio"]["est"] == pytest.approx((5 + 20 - 5) / (10 + 40 + 5))


def test_item7_prior_window_move_sign_hand():
    # m1: 前の向き = 起点 T の前の 1 時間の値動きの符号。上げの道なら +1、下げの道なら −1
    n = 180
    for sign in (1, -1):
        c = 100.0 * np.exp(sign * 0.0001 * np.arange(n))
        g = mk_grid(c)
        lo, hi = T0, T0 + L.DAY_NS
        res = I7.run(g, L.Days.of(lo, hi), lo, hi)
        wv = res["windows"]["1h"]
        k = list(wv["T"]).index(T0 + 120 * MIN)
        assert wv["prior_window_move"][k] == sign
        # 前の向きと同じ側の線に先に当たれば「続き」
        r = I7._cont(L.Days.of(lo, hi), wv, L.Days.of(lo, hi).nums, np.arange(len(wv["T"])) == k, ci=False)
        assert r["cont"]["est"] == 1.0


def test_item11_c8_form_is_one_minus_agree():
    # m2: 平均からの離れの続き = 1 − 一致(値動きが平均から離れる向き)
    days = L.Days.of(T0, T0 + 6 * L.DAY_NS)
    cls = {int(dd): "low" for dd in days.nums}
    a8 = L.DayAcc(days, ("den", "agree"))
    a8.add(days.nums, den=4.0, agree=1.0)
    a5 = L.DayAcc(days, I5.NAMES)
    a5.add(days.nums, den=2.0, agree=2.0)
    res7 = {"windows": {"1h": {"day": days.nums, "side": np.ones(6, dtype=np.int8), "prior_window_move": np.ones(6, dtype=np.int8)}}}
    md, obj = I11.tables(days, cls, {"accs": {0: a5}}, res7, {"kept": {I11.C8_CELL: a8}})
    f8 = [k for k in obj["forms"] if k.startswith("平均からの離れ")][0]
    assert obj["forms"][f8]["全期間"]["low"]["est"] == pytest.approx(0.75)
    f5 = [k for k in obj["forms"] if k.startswith("朝の向き")][0]
    assert obj["forms"][f5]["全期間"]["low"]["est"] == pytest.approx(1.0)
    f7 = [k for k in obj["forms"] if k.startswith("一定幅の線")][0]
    assert obj["forms"][f7]["全期間"]["low"]["est"] == pytest.approx(1.0)


@pytest.mark.parametrize("side,close", [(-1, 105.0), (1, 105.0)])
def test_item4_close_equal_to_center_counts_as_return(side, close):
    # m3: 終値 = 中心 は「戻った」(向き −1 は 終値 <= 中心、+1 は 終値 >= 中心)
    n = 50
    c = np.full(n, np.nan)
    o, h, lw = c.copy(), c.copy(), c.copy()
    start = 110.0 if side == -1 else 100.0
    o[0] = h[0] = lw[0] = c[0] = start
    o[1], c[1] = start, start
    h[1], lw[1] = start + 0.5, start - 0.5
    o[2], c[2], h[2], lw[2] = start, close, max(start, close), min(start, close)
    g = mk_grid(c, opens=o, highs=h, lows=lw)
    r = I4.outcomes(g, np.array([0]), np.array([side]), np.array([105.0]), np.array([1.0]))
    assert r["retA"][0] and r["minA"][0] == 2


# ---------------------------------------------------------------- 批評家 2 回目の mA・mB・mC を捕まえる試験

def test_item6_usdjpy_g_negative_low_path_ends_and_control_hand():
    t0 = L.iso_ns("2020-01-11T15:00:00Z")
    r = L.iso_ns("2020-01-12T22:00:00Z")
    g = mk_grid(np.full(7 * 1440, 1000.0), t0=t0)
    rows = [  # (時刻, 終値, 高値, 安値)
        (t0 + 60 * MIN, 100.4, 100.45, 100.35),
        (t0 + 6 * 60 * MIN, 100.5, 100.55, 100.45),  # 前の週の最後の行
        (r, 100.0, 100.05, 97.0),  # 週明けの行(起点。g < 0)。安値 97 は経路に入れない
        (r + 1 * MIN, 100.2, 100.3, 99.5),  # 経路の最初の行(k0 + 1)
        (r + 59 * MIN, 100.1, 100.35, 99.0),  # 経路の最後の行(時刻 = r + HOLD − LAG)。安値 99.0 が一番深い点
        (r + 60 * MIN, 100.3, 100.4, 98.0),  # 経路の外
    ]
    ends = (100.2, 99.9, 100.0, 100.4)  # 対照 4 本(火〜金の同じ時刻)の 1 時間の終わりの終値(起点はどれも 100.0)
    for j, e in zip(range(1, 5), ends):
        c = r + j * L.DAY_NS
        rows += [(c, 100.0, 100.05, 99.95), (c + 59 * MIN, e, e + 0.05, e - 0.05)]
    rows.sort()
    u_t = np.array([x[0] for x in rows], dtype=np.int64)
    u_c, u_h, u_l = (np.array([x[i] for x in rows]) for i in (1, 2, 3))
    days = L.Days.of(t0, t0 + 7 * L.DAY_NS)
    res = I6.run(g, days, u_t, u_c, u_h=u_h, u_l=u_l)
    v = res["variants"]["usdjpy"]
    gg = math.log(100.0 / 100.5) * 1e4
    assert v["g"][0] == pytest.approx(gg) and gg < 0
    assert v["m"][0] == pytest.approx(math.log(100.1 / 100.0) * 1e4)
    assert v["adv"][0] == pytest.approx(-math.log(99.0 / 100.0) * 1e4)  # 安値の枝。起点の行(97)と経路の外(98)は入らない
    mc = np.log(np.array(ends) / 100.0) * 1e4
    ct = v["ctrl"]
    assert ct["n"][0] == 4
    assert ct["wnum"][0] == pytest.approx(np.mean(-mc * np.sign(gg)))
    assert ct["ratio"][0] == pytest.approx(np.mean(-mc / gg))
    assert ct["same"][0] == pytest.approx(1 / 3)  # m ≠ 0 の 3 本のうち g と同じ符号(下)は 99.9 の 1 本
    s = I6._summ(days, res, "usdjpy", days.nums, ci=False)
    assert s["ctrl"]["wratio"]["est"] == pytest.approx(np.mean(-mc * np.sign(gg)) / abs(gg))
    assert s["wratio"]["est"] == pytest.approx(-v["m"][0] * np.sign(gg) / abs(gg))


def test_item7_band_diff_is_low_minus_high():
    days = L.Days.of(T0, T0 + 10 * L.DAY_NS)
    d = np.repeat(days.nums, 4)
    w = np.tile([1.0, 2.0, 3.0, 3.0], 10)
    pr = np.ones(40, dtype=np.int8)
    side = np.ones(40, dtype=np.int8)  # 低い帯(w = 1)は全部続き
    side[(w == 2.0) & (np.arange(40) % 8 < 4)] = -1  # 中の帯は半分続き
    side[w == 3.0] = -1  # 高い帯は全部戻り
    wv = {"T": T0 + np.arange(40) * L.HOUR_NS, "day": d, "w": w, "side": side, "min": np.ones(40),
          "prior_window_move": pr, "n_warm": 40, "n_w0": 0}
    md, obj = I7.tables({"days": days, "windows": {"1h": wv}})
    dd = obj["windows"]["1h"]["diff_low_minus_high"]["全期間"]
    assert dd["est"] == pytest.approx(1.0 - 0.0)  # 中の帯を相手にすると 0.5 になる


def test_item5_diff_morning_minus_k_points():
    days = L.Days.of(T0, T0 + 10 * L.DAY_NS)
    a0, a1 = L.DayAcc(days, I5.NAMES), L.DayAcc(days, I5.NAMES)
    a0.add(days.nums, den=4.0, agree=3.0)
    a1.add(days.nums, den=4.0, agree=1.0)
    rng = np.random.default_rng(41)
    T = 3
    def mk():
        x, y = rng.normal(size=(10, T)), rng.normal(size=(10, T))
        return np.stack([np.ones((10, T)), x, y, x * x, y * y, x * y], axis=1)
    M0, M1 = mk(), mk()
    k_idx = np.arange(10)
    dr = I5.tmean_diff_ci(M0, M1, k_idx)
    rb = lambda M: float(np.nanmean(I5.corr_t(M.sum(axis=0))))  # noqa: E731
    assert dr["est"] == pytest.approx(rb(M0) - rb(M1))
    assert dr["se"] > 0 and dr["lo"] < dr["hi"]  # 抽き直しでも両方の窓を作り直している(片方だけなら差は 0 に潰れる)
    corr = {k: {"tmean": {p: {"est": None} for p in ("全期間", "前半", "後半")}, "t": {p: [{"est": None}] * (I5.WIN_MIN - 1) for p in ("全期間", "前半", "後半")},
                "years": {y: {"est": None} for y in days.years()}, "diff_morning_minus_k": {}} for k in (0, 1)}
    corr[1]["diff_morning_minus_k"]["全期間"] = dr
    md, obj = I5.tables({"accs": {0: a0, 1: a1}, "corr": corr, "days": days})
    assert obj["diff_morning_minus_k"][1]["全期間"]["agree"]["est"] == pytest.approx(0.75 - 0.25)
    assert obj["diff_morning_minus_k"][1]["全期間"]["corr_tmean"]["est"] == pytest.approx(rb(M0) - rb(M1))
