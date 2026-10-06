"""前提の直接の測り(D1b)担当 G1(# 1・# 2・# 3・# 9)の台本 `scripts/d1b/g1/` の試験。

作り物のデータだけを使う(時刻は試験の時刻で、実データのファイルは開かない)。確かめること(委任文の「試験」):
各量が手計算と合う / 先読みが無い(時刻 t の判断に t より後の値を使わない)/ 区間の種で結果が決まる。
加えて、カードの物(XborderMom・C2OwnerXvenueWick・YenPremiumRevert)を run_card で走らせた結果と、台本の合図・上乗せ・端が
一致すること。
"""
from __future__ import annotations

import gzip
import importlib.util
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import run_card
from bot.research.cards.pnl import pnl

D = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "d1b", "g1"))


def _load(name):
    key = "d1b_g1_" + name
    if key in sys.modules:
        return sys.modules[key]
    if D not in sys.path:
        sys.path.insert(0, D)
    spec = importlib.util.spec_from_file_location(key, os.path.join(D, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[key] = m
    spec.loader.exec_module(m)
    return m


G = _load("g1common")
C1 = _load("c1_venue")
C2 = _load("c2_wick")
C3 = _load("c3_premium")
C9 = _load("c9_liq1m")

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS - 9 * 3600 * NS  # 2023-12-31T15:00:00Z = 日本時間 2024-01-01 0 時。試験の時刻で、データではない


def bars_of(n, start=T0, price=100.0, prices=None, empty=()):
    out = []
    for i in range(n):
        p = float(prices[i]) if prices is not None else price
        out.append(BarEvent(received_time_ns=start + (i + 1) * M, exchange_time_ns=start + (i + 1) * M,
                            start_time_ns=start + i * M, open=p, high=p, low=p, close=p,
                            volume=0.0 if i in empty else 1.0))
    return out


# ============================================================================ g1common
def test_summarize_ratio_and_day_mean_by_hand():
    """1 件あたり = Σ値 ÷ Σ件数、1 日あたり = 日の和の平均。全部の日が同じなら区間は点に縮む。"""
    s = np.array([3.0, 0.0, 6.0, 1.0])
    c = np.array([1.0, 0.0, 2.0, 1.0])
    r = G.summarize(s, c, "event")
    assert r["estimate"] == pytest.approx(10.0 / 4.0) and r["n"] == 4 and r["n_days"] == 4
    assert G.summarize(s, c, "day")["estimate"] == pytest.approx(10.0 / 4.0)
    flat = G.summarize(np.full(20, 2.0), np.ones(20), "event")
    assert flat["ci"] == pytest.approx([2.0, 2.0]) and flat["se"] == pytest.approx(0.0)


def test_interval_is_fixed_by_seed_and_uses_day_blocks():
    """同じ入力・同じ種なら同じ区間。区間は日の塊の再標本の分位(種 20261006・1,000 回・塊 5 日)。"""
    rng = np.random.default_rng(1)
    vals = rng.normal(0, 1, 300)
    days = np.repeat(np.arange(100, 160), 5)
    alld = np.arange(100, 160)
    a = G.table(vals, days, alld, per="event", with_years=False)
    b = G.table(vals, days, alld, per="event", with_years=False)
    assert a == b
    assert G.SEED == 20261006 and G.N_RES == 1000 and G.BLOCK_DAYS == 5
    # 手で同じ再標本を作る: block_bootstrap_ci(循環、塊 5)に、日の番号から比を出す関数を渡す
    from bot.bt.validation import block_bootstrap_ci
    sm, ct = G.by_day(vals, days, alld)
    reps = []

    def stat(x):
        i = x.astype(int)
        reps.append(sm[i].sum() / ct[i].sum())
        return reps[-1]
    block_bootstrap_ci([float(i) for i in range(60)], block_len=5, n_resamples=1000, seed=20261006, alpha=0.05,
                       method="circular", statistic=stat)
    lo, hi = np.quantile(np.array(reps[:1000]), [0.025, 0.975])
    assert a["全期間"]["ci"] == pytest.approx([lo, hi])
    assert a["全期間"]["mde"] == pytest.approx(2.8 * np.std(np.array(reps[:1000]), ddof=1))


def test_halves_split_days_in_two_and_counts():
    alld = np.arange(10)
    days = np.array([0, 0, 4, 5, 9])
    ct = G.count_table(days + 19723, alld + 19723)
    assert ct["前半"]["n"] == 3 and ct["前半"]["n_days"] == 5 and ct["後半"]["n"] == 2 and ct["後半"]["n_days"] == 5
    t = G.table(np.array([1.0, 3.0, 5.0, 7.0, 9.0]), days + 19723, alld + 19723, per="event")
    assert t["前半"]["estimate"] == pytest.approx(3.0) and t["後半"]["estimate"] == pytest.approx(8.0)
    assert "後半 − 前半" not in t


def test_path_extremes_match_brute_force():
    rng = np.random.default_rng(3)
    ends = np.sort(rng.choice(np.arange(1, 500), 200, replace=False)).astype(np.int64)
    hi = rng.normal(0, 1, 200)
    lo = hi - 1
    t0 = rng.integers(0, 480, 50)
    t1 = t0 + rng.integers(0, 40, 50)
    mx, mn, n = G.path_extremes(ends, hi, lo, t0, t1)
    for k in range(50):
        m = (ends > t0[k]) & (ends <= t1[k])
        assert n[k] == m.sum()
        if m.any():
            assert mx[k] == hi[m].max() and mn[k] == lo[m].min()
        else:
            assert np.isnan(mx[k]) and np.isnan(mn[k])


def test_asof_and_exact_idx():
    t = np.array([10, 20, 30], dtype=np.int64)
    assert list(G.asof_idx(t, [5, 10, 25, 99])) == [-1, 0, 1, 2]
    assert list(G.exact_idx(t, [5, 10, 25, 30])) == [-1, 0, -1, 2]


# ============================================================================ # 1 カード 1
def test_c1_signals_are_entries_to_plus_minus_one():
    run = {"exposure": np.array([0, 1, 1, 0, -1, 1, 1, np.nan, 0.0]),
           "decided": np.array([True] * 7 + [False, True])}
    assert list(C1.signals(run)) == [1, 4, 5]


def _c1_run(prices_bf, bin_open):
    n = len(prices_bf)
    start = T0 + np.arange(n, dtype=np.int64) * M
    return {"start": start, "end": start + M, "open": np.asarray(prices_bf, float), "close": np.asarray(prices_bf, float),
            "volume": np.ones(n), "decided": np.ones(n, bool), "exposure": np.array([0, 1, 1, -1, 0, 0, 0, 0.0])[:n]}


def test_c1_pnl_two_venues_by_hand_and_control_shift():
    """P_bf = e_t × (始値_{t+2} / 始値_{t+1} − 1)、P_b = 同じ e_t を同じ時刻の Binance の始値で。ずらしは時刻を足した始値。"""
    bf = [100, 101, 102, 104, 103, 103, 103, 103]
    run = _c1_run(bf, None)
    bt = T0 + np.arange(-5, 12, dtype=np.int64) * M
    bo = 200.0 + np.arange(len(bt))  # 時刻 T0 + k 分の始値 = 205 + k
    r = C1.pnl_two_venues(run, bt, bo)
    # 決定 1(e = +1): 約定 = 足 2 の始値、出 = 足 3 の始値
    assert r["P_bf"][1] == pytest.approx((104 / 102 - 1) * 1e4)
    assert r["P_b"][1] == pytest.approx((208 / 207 - 1) * 1e4)
    assert r["P_b"][3] == pytest.approx(-1 * (210 / 209 - 1) * 1e4)
    assert np.array_equal(r["P_bf"], r["pnl_card"])
    sh = C1.pnl_two_venues(run, bt, bo, shift_ns=2 * M)
    assert sh["P_b"][1] == pytest.approx((210 / 209 - 1) * 1e4)  # 時刻 +2 分の Binance
    assert sh["P_bf"][1] == pytest.approx((103 / 103 - 1) * 1e4)  # 時刻 +2 分の bitFlyer(足 4 → 足 5)
    assert sh["P_bf"][0] == 0.0  # 持ち高 0 は 0
    far = C1.pnl_two_venues(run, bt, bo, shift_ns=100 * M)
    assert np.isnan(far["P_b"][1]) and np.isnan(far["P_bf"][1])  # 行が無ければ NaN


def test_c1_return_minutes_by_hand():
    """D(τ) = s × (X(τ) − X(t − 30 分))。D ≤ 0 になる最初の τ ≥ t までの分。戻らなければ NaN。"""
    tau = T0 + np.arange(1, 101, dtype=np.int64) * M
    X = np.zeros(100)
    X[40:47] = 0.01  # 分の終わり T0 + 41 分 〜 T0 + 47 分で開き、T0 + 48 分に 0 へ戻る
    t = np.array([T0 + 45 * M, T0 + 45 * M, T0 + 99 * M], dtype=np.int64)
    s = np.array([1.0, -1.0, 1.0])
    m, d0, st = C1.return_minutes(tau, X, t, s)
    assert list(st) == [0, 0, 0]
    assert m[0] == 3.0 and d0[0] == pytest.approx(0.01)  # 45 → 48 分
    assert m[1] == 0.0  # 売りの向きでは最初から D ≤ 0
    X2 = X.copy()
    X2[40:] = 0.01
    m2, _, st2 = C1.return_minutes(tau, X2, t[:1], s[:1])
    assert np.isnan(m2[0]) and st2[0] == 1  # データの終わりまで戻らない
    m3, _, st3 = C1.return_minutes(tau, X, np.array([T0 + 10 * M]), s[:1])
    assert np.isnan(m3[0]) and st3[0] == 2  # 基準(30 分前)が格子に無い
    mc, _, _ = C1.return_minutes(tau, X, t[:1], s[:1], shift_ns=-5 * M)  # 対照: 40 分(基準 10 分)→ 40 分の X = 0 → 0
    assert mc[0] == 0.0


def _c1_card_run(bin_close):
    from bot.research.cards.library.c1_xborder_mom import LEADER, XborderMom
    decl = {LEADER: {"lag_ns": M, "source": "試験の入力"}}
    n = len(bin_close)
    rows = [(T0 + i * M, float(v)) for i, v in enumerate(bin_close)]
    ref = reference_series(LEADER, rows, declarations=decl)
    return run_card(XborderMom(), bars_of(n), references={LEADER: ref}, declarations=decl, venue="bitflyer",
                    symbol="FX_BTC_JPY")


def test_c1_card_signal_and_pnl_match_card_and_no_lookahead():
    """カードを run_card で走らせ: Binance が 1% 上げた分(行の時刻 40 分)の終わり(T0 + 41 分)で買い = 合図。
    その後の Binance の値を変えても、合図までの持ち高は変わらない(先読みが無い)。"""
    bc = np.where(np.arange(120) < 40, 100.0, 101.0)
    r = _c1_card_run(bc)
    run = {"start": r.start_ns, "end": r.end_ns, "open": r.open, "close": r.close, "volume": r.volume,
           "decided": r.decided, "exposure": r.exposure}
    sig = C1.signals(run)
    assert list(r.end_ns[sig]) == [T0 + 41 * M] and r.exposure[sig[0]] == 1.0
    p = C1.pnl_two_venues(run, r.start_ns, r.open)
    assert np.array_equal(p["P_bf"], pnl(SimpleNamespace(decided=r.decided, volume=r.volume, exposure=r.exposure,
                                                         open=r.open, end_ns=r.end_ns, start_ns=r.start_ns)).pnl_bp)
    bc2 = bc.copy()
    bc2[41:] = 50.0
    r2 = _c1_card_run(bc2)
    k = int(np.searchsorted(r.end_ns, T0 + 41 * M)) + 1
    assert np.array_equal(r.exposure[:k], r2.exposure[:k])


# ============================================================================ # 2 カード 2
P = 10_000.0


def candle(color, body_bp, top_bp, under_bp, o=P):
    bp = o * 1e-4
    c = o + color * body_bp * bp
    return (o, max(o, c) + top_bp * bp, min(o, c) - under_bp * bp, c)


CANDLES = [candle(1, 5, 30, 1), candle(-1, 5, 1, 30), candle(1, 5, 1, 30), candle(-1, 5, 30, 1), candle(1, 1, 1, 1),
           candle(1, 30, 25, 1)]


def _ov_rows(candles, foot=15):
    t, o, h, lo, c = [], [], [], [], []
    for j, (oo, hh, ll, cc) in enumerate(candles):
        for m in range(foot):
            vals = (oo, hh, ll, cc) if m == 0 else (cc, cc, cc, cc)
            t.append(T0 + (j * foot + m) * M)
            for arr, v in zip((o, h, lo, c), vals):
                arr.append(float(v))
    return {"t": np.array(t, dtype=np.int64), "open": np.array(o), "high": np.array(h), "low": np.array(lo),
            "close": np.array(c)}


def test_c2_signals_match_card_run_and_strength():
    """台本の合図(カードに行を渡して signal_log を読む)は、run_card で走らせたカードの signal_log と同じ。区切りで分けても同じ。
    強い = 陽線 × 買い・陰線 × 売り。"""
    from bot.research.cards.library.c2_owner_xvenue_wick import ROW_LAG_NS, SERIES_SPOT, C2OwnerXvenueWick
    ov = _ov_rows(CANDLES)
    decl = {n: {"lag_ns": ROW_LAG_NS, "source": "試験の入力"} for n in SERIES_SPOT}
    refs = {n: reference_series(n, list(zip(ov["t"].tolist(), ov[c].tolist())), declarations=decl)
            for n, c in zip(SERIES_SPOT, ("open", "high", "low", "close"))}
    card = C2OwnerXvenueWick(series=SERIES_SPOT, foot_min=15)
    run_card(card, bars_of(len(CANDLES) * 15 + 2), references=refs, declarations=decl, venue="bitflyer",
             symbol="FX_BTC_JPY")
    ref_log = np.array(card.signal_log, dtype=np.int64).reshape(-1, 4)
    end = T0 + len(CANDLES) * 15 * M
    one = C2.wick_signals(ov, SERIES_SPOT, [(T0, end)])
    two = C2.wick_signals(ov, SERIES_SPOT, [(T0, T0 + 45 * M), (T0 + 45 * M, end)])
    for sg in (one, two):
        assert np.array_equal(sg["T"], ref_log[:, 0]) and np.array_equal(sg["s"], ref_log[:, 1])
    # 足 0: 陽線・上ヒゲ = 弱い売り / 足 1: 陰線・下ヒゲ = 弱い買い / 足 2: 陽線・下ヒゲ = 強い買い / 足 3: 陰線・上ヒゲ = 強い売り
    # 足 5: 陽線・上ヒゲ 25 bp(24 の枝)= 弱い売り
    assert list(one["s"]) == [-1, 1, 1, -1, -1]
    assert list(one["strong"]) == [False, False, True, True, False]
    assert list(one["T"]) == [T0 + 15 * M, T0 + 30 * M, T0 + 45 * M, T0 + 60 * M, T0 + 90 * M]


def test_c2_signals_no_lookahead():
    """足の終わり T までの合図は、T より後の行を変えても変わらない。"""
    from bot.research.cards.library.c2_owner_xvenue_wick import SERIES_SPOT
    ov = _ov_rows(CANDLES)
    end = T0 + len(CANDLES) * 15 * M
    a = C2.wick_signals(ov, SERIES_SPOT, [(T0, end)])
    ov2 = {k: v.copy() for k, v in ov.items()}
    cut = np.searchsorted(ov2["t"], T0 + 45 * M)
    for k in ("open", "high", "low", "close"):
        ov2[k][cut:] = ov2[k][cut:] * 1.3
    b = C2.wick_signals(ov2, SERIES_SPOT, [(T0, end)])
    m = a["T"] <= T0 + 45 * M
    assert np.array_equal(a["T"][m], b["T"][b["T"] <= T0 + 45 * M]) and np.array_equal(a["s"][m], b["s"][:m.sum()])


def test_c2_moves_by_hand():
    """終点 = s × (終値_{T+h} / 終値_T − 1)。取引の向きの一番深い点 = 合図の向きへ、不利の一番深い点 = 逆の向きへ。
    T・T+h のちょうどの足が無ければ NaN(値動き 0 にしない)で、as-of が古かった件として数える。"""
    end = T0 + np.arange(1, 8, dtype=np.int64) * M
    close = np.array([100, 100, 101, 99, 102, 100, 100.0])
    high = close + 0.5
    low = close - 0.5
    T = np.array([T0 + 2 * M, T0 + 2 * M], dtype=np.int64)
    s = np.array([1, -1])
    mv = C2.moves(T, s, end, close, high, low, 3, T0 + 100 * M)  # (T, T + 3 分] = 足 3・4・5
    assert mv["終点"][0] == pytest.approx((102 / 100 - 1) * 1e4)
    assert mv["終点"][1] == pytest.approx(-(102 / 100 - 1) * 1e4)
    assert mv[C2.FAV][0] == pytest.approx((102.5 / 100 - 1) * 1e4)
    assert mv[C2.ADV][0] == pytest.approx((98.5 / 100 - 1) * 1e4)
    assert mv[C2.FAV][1] == pytest.approx((1 - 98.5 / 100) * 1e4)
    assert mv[C2.ADV][1] == pytest.approx((1 - 102.5 / 100) * 1e4)
    assert not mv["_stale"].any()
    late = C2.moves(T, s, end, close, high, low, 3, T0 + 4 * M)
    assert np.isnan(late["終点"]).all() and late["_late"].all()  # T + h が終わりを越える
    # 足 5(終わり T0 + 5 分)が無い: T + 3 分のちょうどの足が無い → NaN、as-of が古かった件
    k = end != T0 + 5 * M
    gap = C2.moves(T, s, end[k], close[k], high[k], low[k], 3, T0 + 100 * M)
    assert np.isnan(gap["終点"]).all() and np.isnan(gap[C2.FAV]).all() and gap["_stale"].all()
    # 合図の足(終わり T0 + 2 分)が無い: 始点が無い → NaN
    k = end != T0 + 2 * M
    gap0 = C2.moves(T, s, end[k], close[k], high[k], low[k], 3, T0 + 100 * M)
    assert np.isnan(gap0["終点"]).all() and gap0["_stale"].all()


# ============================================================================ # 3 カード 3
def _c3_inputs(n=260, seed=5):
    rng = np.random.default_rng(seed)
    bf = 5_000_000 * np.exp(np.cumsum(rng.normal(0, 4e-4, n)))
    bc = 30_000 * np.exp(np.cumsum(rng.normal(0, 4e-4, n)))
    fx = 150 * np.exp(np.cumsum(rng.normal(0, 1e-4, n // 5 + 1)))
    b_t = T0 + np.arange(n, dtype=np.int64) * M
    keep = np.ones(n, bool)
    keep[[50, 51, 120]] = False  # Binance の行の抜け
    fx_t = T0 + np.arange(n // 5 + 1, dtype=np.int64) * 5 * M  # USDJPY は 5 分ごと(as-of で読む)
    return bf, b_t[keep], bc[keep], fx_t, fx


def _c3_card_run(window="1h", n=260, seed=5):
    from bot.research.cards.library import c3_yen_premium_revert as Y
    bf, b_t, bc, fx_t, fx = _c3_inputs(n, seed)
    decl = {Y.OVERSEAS: {"lag_ns": M, "source": "試験の入力"}, Y.FX: {"lag_ns": M, "source": "試験の入力"}}
    refs = {Y.OVERSEAS: reference_series(Y.OVERSEAS, list(zip(b_t.tolist(), bc.tolist())), declarations=decl),
            Y.FX: reference_series(Y.FX, list(zip(fx_t.tolist(), fx.tolist())), declarations=decl)}
    logged = []

    class Log(Y.YenPremiumRevert):
        def premium(self, view):
            p = super().premium(view)
            if p is not None:
                logged.append((view.now_ns, p))
            return p
    r = run_card(Log(window), bars_of(n, prices=bf), references=refs, declarations=decl, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return r, logged, (bf, b_t, bc, fx_t, fx)


def test_c3_premiums_and_outside_edge_match_card():
    """台本の上乗せ = カードの premium。台本の上・下の端 = カードの持ち高 −1・+1(窓の全部の値の外)。"""
    r, logged, (bf, b_t, bc, fx_t, fx) = _c3_card_run("1h")
    end = T0 + np.arange(1, len(bf) + 1, dtype=np.int64) * M
    pr = C3.premiums(end, bf, b_t, bc, fx_t, fx)
    lt = np.array([x[0] for x in logged])
    lp = np.array([x[1] for x in logged])
    assert np.array_equal(pr["t"], lt) and np.allclose(pr["p"], lp, rtol=0, atol=1e-15)
    hf, lf, warm = C3.edge_flags(pr["t"], pr["p"], 3600 * NS)
    e = r.exposure[np.searchsorted(r.end_ns, pr["t"])]
    assert np.array_equal(hf, e == -1.0) and np.array_equal(lf, e == 1.0)
    assert hf.sum() + lf.sum() > 0 and not (hf | lf)[~warm].any()


def test_c3_edge_no_lookahead_and_onset():
    _r, _l, (bf, b_t, bc, fx_t, fx) = _c3_card_run("1h")
    end = T0 + np.arange(1, len(bf) + 1, dtype=np.int64) * M
    pr = C3.premiums(end, bf, b_t, bc, fx_t, fx)
    hf, lf, _ = C3.edge_flags(pr["t"], pr["p"], 3600 * NS)
    k = 150
    p2 = pr["p"].copy()
    p2[k + 1:] = p2[k + 1:] + np.linspace(-0.01, 0.01, len(p2) - k - 1)
    hf2, lf2, _ = C3.edge_flags(pr["t"], p2, 3600 * NS)
    assert np.array_equal(hf[:k + 1], hf2[:k + 1]) and np.array_equal(lf[:k + 1], lf2[:k + 1])
    t = np.arange(8)
    h = np.array([0, 1, 1, 0, 1, 0, 0, 0], bool)
    lo = np.array([0, 0, 0, 0, 0, 1, 1, 0], bool)
    idx, s = C3.edge_events(t, h, lo, "onset")
    assert list(idx) == [1, 4, 5] and list(s) == [1, 1, -1]
    idx, s = C3.edge_events(t, h, lo, "every")
    assert list(idx) == [1, 2, 4, 5, 6]


def test_c3_cause_and_legs_by_hand():
    """原因 = 直前 1 分の脚の動きのうち、上乗せを端の向きへ一番動かした脚。脚の和 = −s × Δ上乗せ。"""
    pr = {"t": np.array([0, M, 2 * M, 4 * M, 5 * M], dtype=np.int64),
          "lbf": np.log([100, 101, 101, 102.0, 102.0]), "lb": np.log([10, 10, 9.8, 9.8, 9.8]),
          "lfx": np.log([1, 1, 1, 1.0, 0.99])}
    cz = C3.cause(pr, np.array([1, 2, 3, 4]), np.array([1, 1, 1, 1]))
    # 1: bitFlyer が上げた / 2: Binance が下げた / 3: 直前の分が 2 分前 → 不明 / 4: USDJPY が下げた(上乗せを上へ)
    assert list(cz) == [0, 1, -1, 2]
    # 下の端(s = −1)で USDJPY が上げた分が一番 → 原因 USDJPY。符号を逆にした写しは bitFlyer・Binance(0 の動き)と並ぶか外れる
    pr2 = {"t": np.array([0, M], dtype=np.int64), "lbf": np.log([100, 100.01]), "lb": np.log([10, 10.0]),
           "lfx": np.log([1, 1.01])}
    assert list(C3.cause(pr2, np.array([1]), np.array([-1]))) == [2]
    assert list(C3.cause(pr2, np.array([1]), np.array([1]))) == [0]
    bf = {"end": T0 + np.array([1, 2, 3], dtype=np.int64) * M, "close": np.array([100, 102, 101.0])}
    b_t = T0 + np.array([0, 1, 2], dtype=np.int64) * M
    b_c = np.array([10, 10.1, 10.0])
    fx_t = T0 + np.array([0, 2], dtype=np.int64) * M
    fx_c = np.array([1.0, 1.02])
    lg = C3.legs(np.array([T0 + M]), np.array([1]), 2, T0 + 100 * M, bf, b_t, b_c, fx_t, fx_c)
    assert lg["bitFlyer"][0] == pytest.approx(-np.log(101 / 100) * 1e4)
    assert lg["Binance"][0] == pytest.approx(np.log(10.0 / 10) * 1e4)
    assert lg["USDJPY"][0] == pytest.approx(np.log(1.02 / 1.0) * 1e4)  # 上の端で USDJPY が上げた = 上乗せを下げた = 戻り +
    p0 = np.log(100) - np.log(10) - np.log(1.0)
    p1 = np.log(101) - np.log(10.0) - np.log(1.02)
    assert lg["合計(上乗せの戻り)"][0] == pytest.approx(-(p1 - p0) * 1e4)
    assert not lg["_stale"].any()
    # T + h の bitFlyer の足が無い → NaN、古い値の件として数える(# 2 とそろえる)
    k = bf["end"] != T0 + 3 * M
    lg2 = C3.legs(np.array([T0 + M]), np.array([1]), 2, T0 + 100 * M, {kk: v[k] for kk, v in bf.items()},
                  b_t, b_c, fx_t, fx_c)
    assert np.isnan(lg2["合計(上乗せの戻り)"][0]) and np.isnan(lg2["bitFlyer"][0]) and lg2["_stale"][0]
    lg3 = C3.legs(np.array([T0 + M]), np.array([1]), 2, T0 + 2 * M, bf, b_t, b_c, fx_t, fx_c)
    assert np.isnan(lg3["USDJPY"][0]) and lg3["_late"][0] and not lg3["_stale"][0]


def test_c3_legs_binance_exact_and_usdjpy_minute_ending_at_t():
    """Binance の脚は行の時刻ちょうど T + h − 60 秒の行(無ければ NaN、as-of にしない)。USDJPY の脚は行の時刻 ≤ T + h − 60 秒の
    as-of(T + h に始まる分 = 先読みを使わない)。USDJPY の古さが 1 分を越えた件を数える。"""
    bf = {"end": T0 + np.arange(1, 8, dtype=np.int64) * M, "close": np.full(7, 100.0)}
    b_t = T0 + np.arange(0, 7, dtype=np.int64) * M
    b_c = np.full(7, 10.0)
    fx_t = T0 + np.arange(0, 7, dtype=np.int64) * M  # 毎分・別々の値
    fx_c = 1.0 + 0.01 * np.arange(7)
    T = np.array([T0 + 2 * M])
    lg = C3.legs(T, np.array([1]), 2, T0 + 100 * M, bf, b_t, b_c, fx_t, fx_c)
    assert lg["USDJPY"][0] == pytest.approx(np.log(fx_c[3] / fx_c[1]) * 1e4)  # 行の時刻 T + h − 60 秒 = 3 分 / T − 60 秒 = 1 分
    assert not lg["_fx_old"][0]
    k = b_t != T0 + 3 * M  # T + h − 60 秒の Binance の行が無い
    lgb = C3.legs(T, np.array([1]), 2, T0 + 100 * M, bf, b_t[k], b_c[k], fx_t, fx_c)
    assert np.isnan(lgb["Binance"][0]) and np.isnan(lgb["合計(上乗せの戻り)"][0]) and lgb["_stale"][0]
    k = (fx_t != T0 + 3 * M) & (fx_t != T0 + 2 * M)  # USDJPY の行が 2 分前まで無い → as-of の値(1 分)を使い、古さを数える
    lgf = C3.legs(T, np.array([1]), 2, T0 + 100 * M, bf, b_t, b_c, fx_t[k], fx_c[k])
    assert lgf["USDJPY"][0] == pytest.approx(0.0) and lgf["_fx_old"][0] and np.isfinite(lgf["合計(上乗せの戻り)"][0])


# ============================================================================ # 9 カード 9
def test_c9_minute_moves_by_hand_and_missing_bar():
    """t₀ を含む分の次の分の始値 → h 分後に終わる分の終値。足が無ければ NaN(埋めない)。"""
    start = T0 + np.array([0, 1, 2, 3, 5], dtype=np.int64) * M
    o = np.array([100, 101, 102, 103, 105.0])
    c = np.array([100.5, 101.5, 102.5, 103.5, 105.5])
    t0 = np.array([T0 + 30 * NS, T0 + 30 * NS, T0 + 2 * M + 1])
    s = np.array([-1.0, 1.0, 1.0])
    v1 = C9.minute_moves(t0, s, start, o, c, 1, T0 + 100 * M)
    assert v1[0] == pytest.approx(-(101.5 / 101 - 1) * 1e4)
    v2 = C9.minute_moves(t0, s, start, o, c, 2, T0 + 100 * M)
    assert v2[1] == pytest.approx((102.5 / 101 - 1) * 1e4)
    assert np.isnan(v2[2])  # 次の分 3 の始値 → 分 4 の終値: 分 4 の足が無い


def test_c9_xcorr_finds_the_lag():
    """bitFlyer のリターンが Binance の 2 分後に同じなら、相関が一番大きい遅れは +2 分。"""
    rng = np.random.default_rng(9)
    n = 200
    r = rng.normal(0, 1e-3, n)
    st = T0 + np.arange(n, dtype=np.int64) * M
    bc = 100 * np.exp(np.cumsum(r))
    fc = 100 * np.exp(np.cumsum(np.concatenate([rng.normal(0, 1e-3, 2), r[:-2]])))
    C, best = C9.xcorr(np.array([T0 + 100 * M + 5 * NS, T0 + 150 * M]), {"start": st, "close": bc},
                       {"start": st, "close": fc}, T0 + n * M)
    assert list(best) == [2.0, 2.0]
    assert C[0, C9.LAGS.index(2)] == pytest.approx(1.0)


C_PERIOD = ["2023-06-25", "2023-12-17"]  # 担当 C の走らせの run_meta.json の「期間」(c9_run_a.py の [args.start, args.end])
C_MISSING = ["2023-12-17", "2023-12-18"]  # 境で切った読み口で走らせたときの「約定の欠けた日(窓の中)」の例


def _ctrl_file(d, rows, period=C_PERIOD, missing=C_MISSING, metas=None):
    """担当 C の走らせの出力の形(scripts/c9_run_a.py が書く run_meta.json・chunks/meta/<日>.json・controls.csv.gz)の作り物。"""
    import json
    os.makedirs(os.path.join(d, "chunks", "meta"), exist_ok=True)
    with open(os.path.join(d, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"期間": period, "約定の欠けた日(窓の中)": missing}, fh, ensure_ascii=False)
    for day, n in (metas or {}).items():
        with open(os.path.join(d, "chunks", "meta", f"{day}.json"), "w", encoding="utf-8") as fh:
            json.dump({"day": day, "prints": n}, fh)
    p = os.path.join(d, "controls.csv.gz")
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        fh.write("kind,day,anchor_ms,dir,ref_id\n")
        fh.write("".join(rows))
    return p


def test_c9_controls_reader_uses_kind_ii_and_ref_id(tmp_path):
    """担当 C の本当の形(期間 ["2023-06-25", "2023-12-17"]、欠けた日に 2023-12-17)を受ける。ref_id で絞る。"""
    rows = ["(i)無作為,d,1000,1,\n", "(ii)合わせた時刻,d,2000,-1,2023-07-01_00001\n",
            "(ii)合わせた時刻,d,1500,1,2023-07-01_00000\n", "(ii)合わせた時刻,d,3000,1,2023-07-01_00009\n"]
    p = _ctrl_file(str(tmp_path / "a"), rows)
    ct = C9.load_controls(p, 1000 * 1_000_000, 5000 * 1_000_000)
    assert list(ct["t"]) == [1500 * 1_000_000, 2000 * 1_000_000, 3000 * 1_000_000] and list(ct["s"]) == [1.0, -1.0, 1.0]
    ct = C9.load_controls(p, 1000 * 1_000_000, 5000 * 1_000_000, ["2023-07-01_00000", "2023-07-01_00001"])
    assert list(ct["t"]) == [1500 * 1_000_000, 2000 * 1_000_000] and ct["ref_filter"] == {"入った": 2, "入らなかった": 1}


def test_c9_controls_refused_before_opening_when_run_goes_past_the_cut(tmp_path, monkeypatch):
    """期間の終わりが 2023-12-17 より後・「約定の欠けた日」に 2023-12-17 が無い(元の置き場で走らせた)・run_meta.json が無い
    のどれでも、controls.csv.gz を開かずに拒む。境 2023-12-17T15:00Z 以降の起点の行があれば、落とさずに拒む。"""
    rows = ["(ii)合わせた時刻,d,2000,-1,\n"]
    opened = []
    real_open = gzip.open
    monkeypatch.setattr(C9.gzip, "open", lambda *a, **k: opened.append(a) or real_open(*a, **k))
    for i, (per, miss) in enumerate(((["2023-06-25", "2024-10-14"], C_MISSING), (C_PERIOD, ["2023-09-09"]),
                                     (C_PERIOD, []))):
        p = _ctrl_file(str(tmp_path / f"b{i}"), rows, per, miss)
        opened.clear()
        with pytest.raises(SystemExit):
            C9.load_controls(p, 1000 * 1_000_000, 5000 * 1_000_000)
        assert opened == []
    os.remove(os.path.join(str(tmp_path / "b0"), "run_meta.json"))
    with pytest.raises(SystemExit):
        C9.load_controls(os.path.join(str(tmp_path / "b0"), "controls.csv.gz"), 1000 * 1_000_000, 5000 * 1_000_000)
    assert opened == []
    hi = G.iso_ns("2023-12-17T00:00:00Z")
    lo = hi - 10 * G.DAY_NS
    late = (G.HI_MAX // 1_000_000)
    q = _ctrl_file(str(tmp_path / "c"), [f"(ii)合わせた時刻,d,{lo // 1_000_000},-1,\n", f"(ii)合わせた時刻,d,{late},1,\n"])
    with pytest.raises(SystemExit):
        C9.load_controls(q, lo, hi)


def test_c9_controls_between_cut_end_and_boundary_are_kept_and_nan(tmp_path):
    """読み口の終わり(2023-12-17T00:00Z)以降・境(15:00Z)より前の起点は拒まずに残し、値動き・相関は NaN になる(足が無い)。"""
    hi = G.iso_ns("2023-12-17T00:00:00Z")
    lo = hi - 2 * G.DAY_NS
    t_in, t_mid = hi - 3 * 3600 * NS, hi + 5 * 3600 * NS
    q = _ctrl_file(str(tmp_path / "d"), [f"(ii)合わせた時刻,d,{t_in // 1_000_000},1,\n",
                                         f"(ii)合わせた時刻,d,{t_mid // 1_000_000},-1,\n"])
    ct = C9.load_controls(q, lo, hi)
    assert list(ct["t"]) == [t_in, t_mid] and ct["読み口の終わり以降(境の前)の起点"] == 1
    st = np.arange(lo, hi, M, dtype=np.int64)
    px = 100 + np.arange(len(st)) * 0.01
    mv = C9.minute_moves(ct["t"], ct["s"], st, px, px, 5, hi)
    assert np.isfinite(mv[0]) and np.isnan(mv[1])
    C, best = C9.xcorr(ct["t"], {"start": st, "close": px}, {"start": st, "close": px}, hi)
    assert np.isnan(C[1]).all() and np.isnan(best[1])


def test_c9_prints_checked_day_by_day_against_c_run(tmp_path):
    """C の chunks/meta/<日>.json の prints と、台本の UTC の日ごとの清算の数を照らす。1 日でも違えば止める。"""
    d0 = G.iso_ns("2023-07-01T00:00:00Z")
    t = np.array([d0 + 10 * NS, d0 + 20 * NS, d0 + G.DAY_NS + 5 * NS], dtype=np.int64)
    ok = _ctrl_file(str(tmp_path / "e"), [], metas={"2023-07-01": 2, "2023-07-02": 1, "2023-07-03": 0})
    assert C9.check_prints_vs_run(ok, t, d0) == {"照らした日": 3, "清算": 3}
    for i, metas in enumerate(({"2023-07-01": 2, "2023-07-02": 2}, {"2023-07-01": 2}, {"2023-07-01": 2, "2023-07-02": 1,
                                                                                   "2023-07-03": 4})):
        bad = _ctrl_file(str(tmp_path / f"f{i}"), [], metas=metas)
        with pytest.raises(SystemExit):
            C9.check_prints_vs_run(bad, t, d0)


def test_c9_prints_and_trades_refused_before_reading_past_the_cut(monkeypatch):
    """清算・約定は、終わりが読み口の最後の日の終わり(2023-12-17T00:00Z)を越えれば、読み口を呼ぶ前に拒む。
    読み口が終わり以後の清算を返したら、落とさずに拒む。読み口は境で切った置き場。"""
    from bot.research import liq_cascade_v2 as V
    calls = []
    monkeypatch.setattr(V, "load_prints", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(V, "TradeStore", lambda *a, **k: calls.append(a))
    lo = G.iso_ns("2023-12-10T00:00:00Z")
    for hi in (G.iso_ns("2023-12-17T15:00:00Z"), G.iso_ns("2023-12-17T00:00:01Z")):
        with pytest.raises(SystemExit):
            C9.load_prints(lo, hi)
        with pytest.raises(SystemExit):
            C9.coinm_bars(lo, hi)
    assert calls == []
    assert C9.CM_ROOT == "data/c9_run_a/cut_root_20231216" and C9.HI_DEFAULT == "2023-12-17T00:00:00Z"
    hi = G.iso_ns("2023-12-17T00:00:00Z")
    late = SimpleNamespace(ts=np.array([lo // 1_000_000, hi // 1_000_000], dtype=np.int64), sign=np.array([1.0, -1.0]),
                           print_id=np.array(["a", "b"], dtype=object), stats=None)
    monkeypatch.setattr(V, "load_prints", lambda root, d0, d1: (calls.append((str(root), d1)), late)[1])
    with pytest.raises(SystemExit):
        C9.load_prints(lo, hi)
    assert calls[-1][0].endswith("data/c9_run_a/cut_root_20231216") and str(calls[-1][1]) == "2023-12-16"
    ok = SimpleNamespace(ts=late.ts[:1], sign=late.sign[:1], print_id=late.print_id[:1], stats=None)
    monkeypatch.setattr(V, "load_prints", lambda root, d0, d1: ok)
    assert list(C9.load_prints(lo, hi)["t"]) == [lo]


# ============================================================================ # 1 の X の時刻(先読みが無い)
def test_c1_x_grid_uses_rows_of_the_minute_ending_at_tau():
    """X(τ) = ln(Binance × USDJPY) − ln bitFlyer。Binance・USDJPY は行の時刻 ≤ τ − 60 秒(τ で終わる分まで)、bitFlyer は終わり ≤ τ。
    行の時刻 τ の Binance(τ に始まる分、τ の後に決まる値)を使う写しはここで落ちる。"""
    lo = T0
    bin_t = T0 + np.arange(0, 5, dtype=np.int64) * M
    bin_c = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    fx_t = T0 + np.array([0, 2], dtype=np.int64) * M
    fx_c = np.array([100.0, 110.0])
    bf_end = T0 + np.arange(1, 6, dtype=np.int64) * M
    bf_c = np.array([1000.0, 1100.0, 1200.0, 1300.0, 1400.0])
    tau, X = C1.x_grid(lo, T0 + 4 * M, bf_end, bf_c, bin_t, bin_c, fx_t, fx_c)
    assert list(tau) == [T0 + k * M for k in (1, 2, 3, 4)]
    want = [np.log(10 * 100) - np.log(1000), np.log(11 * 100) - np.log(1100), np.log(12 * 110) - np.log(1200),
            np.log(13 * 110) - np.log(1300)]
    assert np.allclose(X, want)
