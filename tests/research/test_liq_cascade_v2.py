"""`bot.research.liq_cascade_v2` の試験。どれも合成の小さな入力で、答えを手で書ける形にしてある。"""
from __future__ import annotations

import io
import math
import random
import zipfile
from datetime import date

import numpy as np
import pytest

from bot.research import liq_cascade_v2 as v2

D0 = v2.day_start_ms("2023-07-01")


def _prints(rows):
    """rows = (ts_ms, side, qty)。orig_qty = qty + 1、price = 30000。"""
    return v2.Prints.from_rows([(t, s, q, q + 1, 30000.0) for t, s, q in rows])


def _trades(times, prices, qtys=None, maker=None):
    times = np.asarray(times, dtype=np.int64)
    n = times.size
    return v2.Trades(times, np.asarray(prices, dtype=float),
                     np.ones(n) if qtys is None else np.asarray(qtys, dtype=float),
                     np.zeros(n, bool) if maker is None else np.asarray(maker, dtype=bool))


def _ramp(t_lo_s, t_hi_s, base=100.0):
    """毎秒 1 件、価格 = base + 秒。"""
    ks = np.arange(t_lo_s, t_hi_s + 1)
    return _trades(D0 + ks * 1000, base + ks)


# --------------------------------------------------------------------------- #
# 一意化と列
# --------------------------------------------------------------------------- #
def test_dedup_keeps_original_quantity(tmp_path):
    root = tmp_path / "liquidationSnapshot" / v2.SYMBOL
    root.mkdir(parents=True)
    hdr = ("time,side,order_type,time_in_force,original_quantity,price,average_price,"
           "order_status,last_fill_quantity,accumulated_fill_quantity\n")
    r1 = f"{D0 + 5},SELL,LIMIT,IOC,10,29000,29100.5,FILLED,3,7\n"
    r2 = f"{D0 + 9},BUY,LIMIT,IOC,4,31000,30900,FILLED,4,4\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", hdr + r1 + r1 + r2)       # r1 が全列一致で 2 回
    (root / f"{v2.SYMBOL}-liquidationSnapshot-2023-07-01.zip").write_bytes(buf.getvalue())
    pr = v2.load_prints(tmp_path, date(2023, 7, 1), date(2023, 7, 1))
    assert (pr.stats.n_in, pr.stats.n_out) == (3, 2)
    assert pr.stats.multiplicity == {1: 1, 2: 1}
    assert pr.side.tolist() == ["SELL", "BUY"]
    assert pr.qty.tolist() == [7.0, 4.0]             # accumulated_fill_quantity
    assert pr.orig_qty.tolist() == [10.0, 4.0]       # original_quantity(並べて持つ)
    assert pr.price.tolist() == [29100.5, 30900.0]   # average_price
    assert pr.sign.tolist() == [-1.0, 1.0]


# --------------------------------------------------------------------------- #
# 束ね方(同じ側だけ、gap ちょうどは同じ束)
# --------------------------------------------------------------------------- #
def test_same_side_bundles_gap_boundary_and_sides():
    pr = _prints([(D0, "SELL", 1), (D0 + 30_000, "BUY", 5), (D0 + 60_000, "SELL", 2),
                  (D0 + 120_001, "SELL", 4)])
    b = v2.same_side_bundles(pr, 60)
    ids = b["bundle_id"].tolist()
    # SELL 0 と 60000 は差 = 60 秒ちょうど → 同じ束。120001 は 60.001 秒 → 別。BUY は混ざらない
    assert ids[0] == ids[2] and ids[3] != ids[0] and ids[1] not in (ids[0], ids[3])
    assert b["pos_label"].tolist() == ["最初", "単発", "最後", "単発"]
    assert b["k_in_bundle"].tolist() == [0, 0, 1, 0]
    assert b["qty_so_far"].tolist() == [1.0, 5.0, 3.0, 4.0]
    assert sorted(x["n_prints"] for x in b["bundles"]) == [1, 1, 2]


def test_same_side_context_past_and_next():
    pr = _prints([(D0, "SELL", 2), (D0 + 5_000, "BUY", 9), (D0 + 10_000, "SELL", 4),
                  (D0 + 10_000, "SELL", 1), (D0 + 75_000, "SELL", 8)])
    c = v2.same_side_context(pr)
    # 並びは (ts, side, qty) 順: [0 SELL 2], [5000 BUY 9], [10000 SELL 1], [10000 SELL 4], [75000 SELL 8]
    assert pr.qty.tolist() == [2, 9, 1, 4, 8]
    assert c["n_prev60"].tolist() == [0, 0, 1, 1, 0]          # 同じ ms は前に数えない
    assert c["elapsed_prev_s"][2] == 10.0 and c["elapsed_prev_s"][3] == 10.0
    assert c["qty_ratio_prev"][2] == 0.5 and c["qty_ratio_prev"][3] == 2.0
    assert c["qty_ratio_max60"][3] == 2.0
    assert math.isnan(c["qty_ratio_max60"][4])                # [15000, 75000) に SELL 無し
    assert c["elapsed_prev_s"][4] == 65.0
    assert c["gap_next_ms"].tolist() == [10_000, np.inf, 65_000, 65_000, np.inf]


# --------------------------------------------------------------------------- #
# 状態機械(9 通り × 型 A/B。期待値は手で書いた表、前の道具の表は使わない)
# --------------------------------------------------------------------------- #
EXPECTED = {
    ("わからない", "止まる"): {"A": "新規_逆張り", "B": "新規_逆張り"},
    ("わからない", "続く"): {"A": "新規_順張り", "B": "新規_順張り"},
    ("わからない", "わからない"): {"A": "何もしない", "B": "何もしない"},
    ("続く", "止まる"): {"A": "決済", "B": "ドテン_逆張り"},
    ("続く", "続く"): {"A": "ホールド", "B": "ホールド"},
    ("続く", "わからない"): {"A": "ホールド", "B": "ホールド"},
    ("止まる", "止まる"): {"A": "ホールド", "B": "ホールド"},
    ("止まる", "続く"): {"A": "決済", "B": "ドテン_順張り"},
    ("止まる", "わからない"): {"A": "ホールド", "B": "ホールド"},
}


def _bundle(pr, gap_s=60):
    return v2.same_side_bundles(pr, gap_s)["bundles"][0]


@pytest.mark.parametrize("j1,j2", list(EXPECTED))
@pytest.mark.parametrize("typ", ["A", "B"])
def test_state_machine_cells(j1, j2, typ):
    # SELL(下へ押す、向き −1)。価格は毎秒 +1 で上がる → 順張り(売り)は負、逆張り(買い)は正
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    tr = _ramp(0, 200)
    res = v2.simulate_bundle(pr, _bundle(pr), [j1, j2], typ, 1, v2.make_price_fn(tr))
    acts = [p["行動"] for p in res["path"] if p["print_id"] is not None]
    assert acts[1] == EXPECTED[(j1, j2)][typ]
    # 損益を手で: 入る = ts + 1 秒、決済/ドテン = 10 秒 + 1、終わり = 10 + 60 + 1 = 71 秒
    px = lambda s: 100.0 + s  # noqa: E731
    bp = lambda d, a, b: d * (px(b) - px(a)) / px(a) * 1e4  # noqa: E731
    dir1 = {"続く": -1.0, "止まる": 1.0, "わからない": 0.0}[j1]
    a2 = EXPECTED[(j1, j2)][typ]
    if dir1 == 0.0:
        exp = {"新規_逆張り": bp(1.0, 11, 71), "新規_順張り": bp(-1.0, 11, 71),
               "何もしない": 0.0}[a2]
    elif a2 == "ホールド":
        exp = bp(dir1, 1, 71)
    elif a2 == "決済":
        exp = bp(dir1, 1, 11)
    else:  # ドテン
        exp = bp(dir1, 1, 11) + bp(-dir1, 11, 71)
    assert res["pnl_pct"] == pytest.approx(exp / 100)     # 連鎖の損益はレグの和 → %(L-920)
    assert sum(l["レグ損益_bp"] for l in res["legs"]) == pytest.approx(exp)
    assert res["entered"] == (not (dir1 == 0.0 and a2 == "何もしない"))


def test_baseline_enters_first_and_exits_at_end_plus_gap():
    pr = _prints([(D0, "BUY", 1), (D0 + 20_000, "BUY", 1)])
    tr = _ramp(0, 300)
    res = v2.simulate_bundle(pr, _bundle(pr, 30), None, "-", 3, v2.make_price_fn(tr),
                             baseline="順張り")
    # 入る 3 秒(103)、出る 20 + 30 + 3 = 53 秒(153)、BUY の順張り = 買い
    assert res["pnl_pct"] == pytest.approx((153 - 103) / 103 * 100)   # %(L-920)


def test_rule_and_perfect_judgments():
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1), (D0 + 100_000, "SELL", 1)])
    ctx = v2.same_side_context(pr)
    b = v2.same_side_bundles(pr, 180)["bundles"][0]
    assert v2.judgments_for("規則_材料1", b["members"], ctx) == ["止まる", "続く", "止まる"]
    assert v2.judgments_for("完全な判断", b["members"], ctx) == ["続く", "続く", "止まる"]


# --------------------------------------------------------------------------- #
# s 秒の曲線
# --------------------------------------------------------------------------- #
def test_s_curve_points_counts():
    pr = _prints([(D0, "SELL", 1), (D0 + 5_000, "BUY", 1), (D0 + 10_000, "SELL", 1)])
    c = v2.same_side_context(pr)
    rows, ss = v2.s_curve_points(pr.ts, c["gap_next_ms"], D0 + 60_500)
    cnt = np.bincount(rows, minlength=3).tolist()
    # SELL@0: 次の SELL まで 10 秒 → s = 1..9。BUY@5: 次が無い → 範囲の終わり 55.5 秒まで → 1..55。
    # SELL@10: 50.5 秒まで → 1..50。間に入った反対側のプリントは数えない
    assert cnt == [9, 55, 50]
    assert ss[rows == 0].tolist() == list(range(1, 10))
    rows2, _ = v2.s_curve_points(pr.ts, c["gap_next_ms"], D0 + 10 ** 7)
    assert np.bincount(rows2).tolist() == [9, 180, 180]       # 上限 S_MAX


def test_s_curve_values_hand():
    tr = _ramp(0, 100)
    ts = np.array([D0], dtype=np.int64)
    vals = v2.s_curve_values(tr, ts, np.array([-1.0]), np.array([0]), np.array([2]), 1, (5,))
    # 判断 2 秒、入る at_or_after(3 秒) = 103、出る 3 + 5 = 8 秒 = 108。SELL の fade = 買い
    assert vals[5][0] == pytest.approx((108 - 103) / 103 * 1e4)


# --------------------------------------------------------------------------- #
# 値動き・最大順行・最大逆行・山からの戻り
# --------------------------------------------------------------------------- #
def test_reactions_mfe_mae_giveback_hand():
    tr = _trades(D0 + np.array([0, 1000, 2000, 3000, 4000]), [100, 101, 99, 102, 100])
    up = v2.reactions_from_anchor(tr, np.array([D0]), np.array([1.0]), (1, 2, 3, 4))
    assert up["p0"][0] == 100
    assert [up[f"react_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([100, -100, 200, 0])
    assert [up[f"mfe_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([100, 100, 200, 200])
    assert [up[f"mae_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([0, -100, -100, -100])
    assert [up[f"giveback_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([0, 200, 200, 200])
    assert [up[f"mfe_minus_react_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([0, 200, 0, 200])
    dn = v2.reactions_from_anchor(tr, np.array([D0]), np.array([-1.0]), (1, 2, 3, 4))
    assert [dn[f"react_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([-100, 100, -200, 0])
    assert [dn[f"mfe_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([0, 100, 100, 100])
    # 山は p₀(0)から始まる: 1 秒で −100 → 戻り 100、3 秒で 100 → −200 → 300
    assert [dn[f"giveback_{h}"][0] for h in (1, 2, 3, 4)] == pytest.approx([100, 100, 300, 300])


def test_reactions_hole_is_nan():
    tr = _trades(D0 + np.array([0, 1000]), [100, 101])
    r = v2.reactions_from_anchor(tr, np.array([D0]), np.array([1.0]), (1, 400))
    assert r["react_1"][0] == pytest.approx(100)
    assert math.isnan(r["react_400"][0]) and math.isnan(r["mfe_400"][0])   # 穴 > 300 秒


# --------------------------------------------------------------------------- #
# 先読みしないこと
# --------------------------------------------------------------------------- #
def _world(seed=7):
    rng = np.random.default_rng(seed)
    t = np.sort(D0 + rng.integers(0, 600_000, 4000))
    px = 30000 + np.cumsum(rng.normal(0, 2, t.size))
    tr = _trades(t, px, rng.uniform(1, 50, t.size), rng.random(t.size) < 0.5)
    lt = np.sort(D0 + rng.integers(100_000, 500_000, 40))
    pr = _prints([(int(x), "SELL" if rng.random() < 0.6 else "BUY", float(rng.integers(1, 99)))
                  for x in lt])
    return tr, pr


def _subset_prints(pr, keep):
    return v2.Prints(pr.ts[keep], pr.side[keep], pr.qty[keep], pr.orig_qty[keep],
                     pr.price[keep], pr.print_id[keep])


def _side_data(t_lo_ms, t_hi_ms, seed=5):
    rng = np.random.default_rng(seed)
    t_oi = np.arange(t_lo_ms, t_hi_ms, 300_000, dtype=np.int64)
    oi = 1e6 + np.cumsum(rng.normal(0, 1e3, t_oi.size))
    tls = rng.uniform(0.5, 1.5, t_oi.size)
    t_f = np.arange(t_lo_ms, t_hi_ms, 8 * 3_600_000, dtype=np.int64)
    r_f = rng.normal(1e-4, 5e-5, t_f.size)
    buckets = {"t_ms": t_oi[1:], "delta": rng.uniform(1, 100, t_oi.size - 1),
               "vwap": 30000 + rng.normal(0, 20, t_oi.size - 1),
               "buy_share": rng.uniform(0, 1, t_oi.size - 1), "t_all": t_oi[1:]}
    return v2.SideData(t_oi, oi, tls, t_f, r_f, buckets)


def _cut_side(sd, ts):
    k = sd.t_oi <= ts
    kf = sd.t_fund <= ts
    b = sd.oi_buckets
    kb = b["t_ms"] <= ts
    return v2.SideData(sd.t_oi[k], sd.oi[k], sd.tls[k], sd.t_fund[kf], sd.r_fund[kf],
                       {"t_ms": b["t_ms"][kb], "delta": b["delta"][kb], "vwap": b["vwap"][kb],
                        "buy_share": b["buy_share"][kb], "t_all": b["t_all"][b["t_all"] <= ts]})


def _world_long(seed=7):
    """約定 10 時間(材料 5 の 8 時間の窓のため)、清算は最後の 1 時間。"""
    rng = np.random.default_rng(seed)
    t = np.sort(D0 + rng.integers(0, 36_000_000, 20_000))
    px = 30000 + np.cumsum(rng.normal(0, 2, t.size))
    tr = _trades(t, px, rng.uniform(1, 50, t.size), rng.random(t.size) < 0.5)
    lt = np.sort(D0 + rng.integers(32_400_000, 35_900_000, 30))
    pr = v2.Prints.from_rows([(int(x), "SELL" if rng.random() < 0.6 else "BUY",
                               float(rng.integers(1, 99)), 100.0,
                               float(30000 + rng.normal(0, 30))) for x in lt])
    return tr, pr, _side_data(D0 - 3_600_000, D0 + 36_000_000)


def _assert_same(a, b):
    if isinstance(a, str) or isinstance(b, str):
        assert a == b
    else:
        np.testing.assert_equal(float(a), float(b))


def test_no_lookahead_truncate_and_perturb():
    tr, pr, sd = _world_long()
    ctx = v2.same_side_context(pr)
    b60 = v2.same_side_bundles(pr, 60)
    sel = np.arange(len(pr))
    mats = v2.print_materials(pr, sel, tr, ctx, b60, sd)
    pre = v2.pre_state_arrays(tr, pr.ts)
    past_ctx = ("n_prev60", "elapsed_prev_s", "qty_ratio_prev", "qty_ratio_max60")
    n_fin8 = 0
    for i in range(len(pr)):
        ts = int(pr.ts[i])
        # (1) ts 以後の約定・ts より後の清算・ts より後の metrics/資金調達率/建玉の桶を消す
        tr_cut = tr.slice_time(0, ts)
        pr_cut = _subset_prints(pr, np.arange(len(pr)) <= i)
        ctx_c = v2.same_side_context(pr_cut)
        b_c = v2.same_side_bundles(pr_cut, 60)
        sd_c = _cut_side(sd, ts)
        m_c = v2.print_materials(pr_cut, np.array([i]), tr_cut, ctx_c, b_c, sd_c)
        for k in mats:
            _assert_same(m_c[k][0], mats[k][i])
        n_fin8 += int(np.isfinite(mats[v2.MAT_COL[8]][i]))
        for k in past_ctx:
            np.testing.assert_equal(ctx_c[k][i], ctx[k][i])
        pre_c = v2.pre_state_arrays(tr_cut, pr_cut.ts)
        for k in pre:
            np.testing.assert_equal(pre_c[k][i], pre[k][i])
        assert b_c["k_in_bundle"][i] == b60["k_in_bundle"][i]
        assert b_c["qty_so_far"][i] == b60["qty_so_far"][i]
        row = {k: mats[k][i] for k in mats}
        row_c = {k: m_c[k][0] for k in m_c}
        assert v2.jev_state_raw(i, pr, row, b60) == v2.jev_state_raw(i, pr_cut, row_c, b_c)
        assert v2.judge_rule_mat1(ctx_c["n_prev60"][i]) == v2.judge_rule_mat1(ctx["n_prev60"][i])
        # (2) ts 以後の約定の価格(p₀ を含む)を書き換えても変わらない
        tr_pert = v2.Trades(tr.times, np.where(tr.times >= ts, tr.prices + 500.0, tr.prices),
                            tr.qtys, tr.maker)
        m_p = v2.print_materials(pr, np.array([i]), tr_pert, ctx, b60, sd)
        for k in mats:
            _assert_same(m_p[k][0], mats[k][i])
    # 試験が空振りしていないこと: 材料 5・8・10 が実際に値を持つ行がある
    assert n_fin8 > 0
    assert np.isfinite(mats[v2.MAT_COL[5]]).any() and np.isfinite(mats[v2.MAT_COL[10]]).any()


def test_materials_hand():
    ks = np.arange(-100, 201)
    tr = _trades(D0 + ks * 1000, 200.0 + ks)                  # 毎秒、価格 = 200 + 秒、全部 買い taker
    pr = v2.Prints.from_rows([(D0, "SELL", 1, 1, 100.0), (D0 + 10_000, "SELL", 2, 2, 100.0),
                              (D0 + 30_000, "SELL", 3, 3, 100.0)])
    sd = v2.SideData(np.array([D0 - 3_600_000, D0, D0 + 25_000]), np.array([100.0, 110, 999]),
                     np.array([1.0, 2, 3]), np.array([D0 - 28_800_000, D0 + 20_000]),
                     np.array([1e-4, 2e-4]), None)
    ctx = v2.same_side_context(pr)
    m = v2.print_materials(pr, np.arange(3), tr, ctx, v2.same_side_bundles(pr, 60), sd)
    C = v2.MAT_COL
    assert m[C[1]].tolist() == [0, 1, 2]
    assert m["mat1_elapsed_since_burst_s"].tolist() == [0, 10, 30]
    assert math.isnan(m[C[2]][1]) and m[C[2]][2] == pytest.approx(0.5)        # 10 ÷ 20
    assert m[C[3]][2] == pytest.approx(1.5) and m[C[12]][2] == pytest.approx(1.5)
    # 材料 4: 連鎖の最初 = 0 秒のプリント、p₀ = 200。p_pre = 29 秒の 229。SELL なので −
    assert math.isnan(m[C[4]][0])                    # 最初が自分 → p₀ は ts 以後 → 使わない
    assert m[C[4]][2] == pytest.approx(-(229 - 200) / 200 * 1e4)
    assert m["mat4_bounce_bp"][2] == pytest.approx(-(229 - 210) / 210 * 1e4)
    assert m[C[14]][2] == 60                          # [−30 秒, 30 秒) の約定
    assert m[C[11]][2] == pytest.approx(300 / ((229 - 170) / 229 * 1e4))
    assert m[C[9]][2] == -1.0 and m[C[13]][2] == 0.0  # 偏り 5 秒 = 30 秒 = +1、SELL
    assert m[C[10]][2] == pytest.approx((999 - 100) / 100 * 1e4)
    assert m[C[10]][1] == pytest.approx((110 - 100) / 100 * 1e4)               # 25 秒の行はまだ無い
    assert m["mat10_funding_rate"].tolist() == [1e-4, 1e-4, 2e-4]
    assert m["mat10_taker_ls_ratio"].tolist() == [2.0, 2.0, 3.0]
    assert m[C[6]].tolist() == ["UTC 00–06"] * 3
    assert np.isnan(m[C[8]]).all()                    # 建玉の桶を渡していない


# --------------------------------------------------------------------------- #
# 対照
# --------------------------------------------------------------------------- #
def test_control_random_margin_same_day_no_duplicates():
    liq = np.array([D0 + 43_200_000, D0 + 43_500_000], dtype=np.int64)
    t = v2.control_random("2023-07-01", 5000, liq, random.Random(1))
    assert t.size == 5000 and np.unique(t).size == 5000
    assert t.min() >= D0 and t.max() < D0 + v2.MS_DAY
    d = np.min(np.abs(t[:, None] - liq[None, :]), axis=1)
    assert d.min() > v2.CTRL_MARGIN_MS
    # 求めた数より候補が少なければ、取れた分だけ
    dense = D0 + np.arange(-600_000, v2.MS_DAY + 600_001, 600_000, dtype=np.int64)
    assert v2.control_random("2023-07-01", 10, dense, random.Random(1)).size == 0


def test_control_matched_nearest_in_band_without_replacement():
    cuts15, cuts9 = np.array([0.0]), np.array([0.0])          # 帯 0 = 負、帯 1 = 0 以上
    tgt15, tgt9 = np.array([0.5, 0.6, -0.5, 0.7]), np.array([0.5, 0.5, 0.5, -0.1])
    cand_t = np.arange(4)
    c15, c9 = np.array([0.55, 0.9, -0.4, 2.0]), np.array([0.5, 0.5, 0.4, 0.3])
    pick = v2.control_matched(tgt15, tgt9, cand_t, c15, c9, cuts15, cuts9)
    # 1 件目: 帯 (1,1) の候補 0,1,3 → 最も近い 0。2 件目: 0 は使用済み → 1 と 3 のうち近い 1。
    # 3 件目: 帯 (0,1) → 候補 2。4 件目: 帯 (1,0) → 候補無し
    assert pick.tolist() == [0, 1, 2, -1]


def test_match_across_days_order_and_used():
    cuts = np.array([0.0])
    mk = lambda a15, a9: {"t": np.arange(len(a15)), "mat15": np.array(a15, float),  # noqa: E731
                          "mat9": np.array(a9, float), "dir": np.ones(len(a15)),
                          "used": np.zeros(len(a15), bool)}
    cands = {0: mk([0.55], [0.5]), -1: mk([0.9], [0.9]), 1: mk([0.61], [0.6])}
    off, pick = v2.match_across_days(np.array([0.5, 0.6, 0.7, -0.5]),
                                     np.array([0.5, 0.6, 0.7, 0.5]), cands, cuts, cuts)
    # 1 件目は同じ日。2 件目は同じ日が使用済み → −1 日を +1 日より先に探す。
    # 3 件目は −1 日も使用済み → +1 日。4 件目は帯 (0,1) の候補がどの日にも無い
    assert off.tolist() == [0, -1, 1, 99] and pick.tolist() == [0, 0, 0, -1]
    assert cands[-1]["used"].tolist() == [True] and cands[1]["used"].tolist() == [True]


def test_control_placebo_volume_tolerance_and_margin():
    day = "2023-07-01"
    liq = np.array([D0 + 43_200_000], dtype=np.int64)
    times = [D0 + 3_605_000, D0 + 7_205_000, D0 + 10_805_000, D0 + 43_200_000]
    qtys = [12.0, 20.0, 7.0, 10.0]     # 束の窓の量 10。12 は ±25% の中、20・7 は外
    prices = [101.0, 102.0, 103.0, 100.0]
    tr = _trades(times, prices, qtys)
    bundles = [{"bundle_id": "b", "start_ms": D0 + 43_200_000, "end_ms": D0 + 43_200_000}]
    pl = v2.control_placebo(day, tr, bundles, liq, random.Random(0))
    assert len(pl) == 1
    assert pl[0]["vol_bundle"] == 10.0 and pl[0]["vol_placebo"] == 12.0
    assert pl[0]["start_ms"] == D0 + 3_600_000 and pl[0]["end_ms"] == D0 + 3_610_000


def test_controls_use_same_pre_state_as_prints():
    tr, _pr = _world(3)
    t = np.array([D0 + 200_000, D0 + 300_000], dtype=np.int64)
    a = v2.pre_state_arrays(tr, t)
    for k in a:
        for j in range(2):
            np.testing.assert_equal(v2.pre_state_arrays(tr, t[j:j + 1])[k][0], a[k][j])
    assert set(np.unique(a["dir10"][np.isfinite(a["dir10"])])) <= {-1.0, 1.0}


# --------------------------------------------------------------------------- #
# 分布の集計
# --------------------------------------------------------------------------- #
def test_dist_stats_hand():
    s = v2.dist_stats([1.0, -1.0, 2.0, 0.0, float("nan")], ["a", "a", "b", "b", "b"])
    assert s["n"] == 4 and s["n_nan"] == 1
    assert (s["share_pos"], s["share_neg"], s["share_zero"]) == (0.5, 0.25, 0.25)
    assert s["day_eq_mean"] == pytest.approx(0.5)          # a: 0、b: 1
    assert s["daysum_mean"] == pytest.approx(1.0)          # a: 0、b: 2
    assert s["daysum_se"] == pytest.approx(1.0)            # sd(0,2)=√2、÷√2
    assert s["q50"] == pytest.approx(0.5)


def test_cluster_se_matches_prior_tool():
    ex2 = v2._load_script("o3c_signal_explore2")
    rng = np.random.default_rng(0)
    vals = rng.normal(size=200)
    days = np.array([f"d{k % 7}" for k in range(200)], dtype=object)
    m, se, _naive, n, g = ex2.mean_se_cluster(vals, days)
    se2, g2 = v2.cluster_se(vals, days)
    assert se2 == pytest.approx(se) and g2 == g


# --------------------------------------------------------------------------- #
# 規則(3 択): 期間の分け方・帯の決め方・入らないの分岐
# --------------------------------------------------------------------------- #
def test_split_days_make_before_measure():
    make, meas = v2.split_days(["2023-07-03", "2023-07-01", "2023-07-05", "2023-07-02",
                                "2023-07-04"])
    assert make == ["2023-07-01", "2023-07-02", "2023-07-03"]
    assert meas == ["2023-07-04", "2023-07-05"]
    assert max(make) < min(meas)


def _calib_data():
    """帯ごとに件数 1000、続く割合 0.2 / 0.5 / 0.52 / 0.8(基準率 0.505、2SE ≈ 0.03)。"""
    probs, ys = [], []
    for p, rate in ((0.31, 0.2), (0.51, 0.5), (0.53, 0.52), (0.71, 0.8)):
        k = int(round(rate * 1000))
        probs += [p] * 1000
        ys += [1.0] * k + [0.0] * (1000 - k)
    return np.array(probs), np.array(ys)


def test_band_rule_l277_and_judge():
    cal = v2.value_module().calibration_table(*_calib_data())
    # 0.50〜0.52 と 0.52〜0.54 は基準率と 2SE で区別できず、基準率を跨ぐ位置(0.52 の帯)を含む
    assert cal["帯"] == (0.5, 0.54)
    band, cross = cal["帯"], cal["跨ぐ位置の帯"]
    assert v2.judge_three_way(0.49, band, cross) == "止まる"
    assert v2.judge_three_way(0.51, band, cross) == "わからない"
    assert v2.judge_three_way(0.54, band, cross) == "続く"
    assert v2.judge_three_way(float("nan"), band, cross) == "わからない"
    # 区別できない帯が無いときは、基準率を跨ぐ帯の下端で側に寄せる
    assert v2.judge_three_way(0.49, None, (0.5, 0.52)) == "止まる"
    assert v2.judge_three_way(0.50, None, (0.5, 0.52)) == "続く"


def test_three_way_unknown_means_no_entry():
    pr = _prints([(D0, "SELL", 1), (D0 + 10_000, "SELL", 1)])
    ctx = v2.same_side_context(pr)
    b = _bundle(pr)
    model = {v2.SCENE_FIRST: {"band": (0.4, 0.6), "cross": None},
             v2.SCENE_CHAIN: {"band": (0.4, 0.6), "cross": None}}
    tr = _ramp(0, 200)
    jd = v2.judgments_for(v2.POLICY_3WAY, b["members"], ctx, np.array([0.5, 0.7]), model)
    assert jd == ["わからない", "続く"]
    res = v2.simulate_bundle(pr, b, jd, "A", 1, v2.make_price_fn(tr))
    assert [p["行動"] for p in res["path"] if p["print_id"]] == ["何もしない", "新規_順張り"]
    jd2 = v2.judgments_for(v2.POLICY_3WAY, b["members"], ctx, np.array([0.5, 0.45]), model)
    res2 = v2.simulate_bundle(pr, b, jd2, "B", 1, v2.make_price_fn(tr))
    assert not res2["entered"] and res2["pnl_pct"] == 0.0 and res2["n_entries"] == 0


def _logit_df(seed=0):
    import pandas as pd
    rng = np.random.default_rng(seed)
    days = np.repeat([f"2023-07-0{k}" for k in range(1, 7)], 80)
    d = {"day": days, "cont_60": (rng.random(days.size) < 0.6).astype(float)}
    for f in v2.LOGIT_FEATURES:
        d[f] = rng.normal(size=days.size)
    d[v2.MAT_COL[1]] = rng.integers(0, 3, days.size).astype(float)
    return pd.DataFrame(d)


def test_fit_three_way_reads_only_make_period():
    df = _logit_df()
    make, meas = v2.split_days(sorted(set(df["day"])))
    m1 = v2.fit_three_way(df, make)
    df2 = df.copy()
    late = df2["day"].isin(meas)
    for f in v2.LOGIT_FEATURES:
        df2.loc[late, f] = 1e6                       # 後半の材料とラベルを壊す
    df2.loc[late, "cont_60"] = 1.0 - df2.loc[late, "cont_60"]
    m2 = v2.fit_three_way(df2, make)
    for sc in (v2.SCENE_FIRST, v2.SCENE_CHAIN):
        np.testing.assert_array_equal(m1[sc]["beta"], m2[sc]["beta"])
        assert m1[sc]["band"] == m2[sc]["band"] and m1[sc]["n"] == m2[sc]["n"]
        for f in v2.LOGIT_FEATURES:
            np.testing.assert_array_equal(m1[sc]["ecdf"][f], m2[sc]["ecdf"][f])
    p1 = v2.predict_three_way(m1, df[~late])
    p2 = v2.predict_three_way(m2, df2[~late])
    np.testing.assert_array_equal(p1, p2)
    assert np.isfinite(p1).all()
