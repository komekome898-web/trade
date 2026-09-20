#!/usr/bin/env python3
"""O3C SIGNAL 探索段 5 の反証者の再計算(2026-09-20)。

行データ `backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz` だけを入力に、
H0 の診断・H1〜H6 の全数値セルを独立に組み直し、出力の csv と突き合わせる。
SE・日等重み平均・分位は委任先の道具を import せず、委任文に書かれた式から書き直した。

使い方: PYTHONPATH= python3 docs/DATA/probes/20260920_o3c_signal_explore5_refuter.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("backtest_data/o3c_signal_explore5_20260920")
ROWS = OUT / "rows_prints.csv.gz"
TOL = 1e-6
H_ALL = [1, 5, 10, 30, 60, 300, 900]
H_MAIN = [60, 300, 900]
T_MAIN = [10, 60]
NEXT_SEC = [60, 120]
NAN = float("nan")

# ---------------------------------------------------------------- 統計の道具


def cluster_se(v: np.ndarray, days: np.ndarray):
    """平均・日クラスタ SE・naive SE・n・日数。委任文の式をそのまま書き直したもの:
    m = mean(v); s_d = Σ_{i∈d}(v_i − m); SE = sqrt(Σ_d s_d²)/n × sqrt(G/(G−1))
    naive = 母標準偏差 / √n"""
    ok = np.isfinite(v)
    v, d = v[ok], days[ok]
    n = v.size
    if n == 0:
        return NAN, NAN, NAN, 0, 0
    m = float(v.mean())
    s = pd.Series(v - m).groupby(pd.Series(d)).sum().to_numpy()
    g = s.size
    se = math.sqrt(float((s * s).sum())) / n * math.sqrt(g / (g - 1)) if g > 1 else NAN
    naive = float(v.std(ddof=0)) / math.sqrt(n)
    return m, se, naive, int(n), int(g)


def day_equal_mean(v: np.ndarray, days: np.ndarray) -> float:
    ok = np.isfinite(v)
    if ok.sum() == 0:
        return NAN
    s = pd.Series(v[ok]).groupby(pd.Series(days[ok])).mean()
    return float(s.mean())


def r_stats(v: np.ndarray, days: np.ndarray) -> dict:
    mean, se, naive, n, g = cluster_se(v, days)
    fin = v[np.isfinite(v)]
    q = np.percentile(fin, [25, 50, 75]) if fin.size else [NAN] * 3
    return {
        "n": n, "含む日数": g, "r 平均(bp)": mean,
        "r 日クラスタ SE": se, "r naive SE": naive,
        "日クラスタ/naive": (se / naive if (math.isfinite(se) and naive > 0) else NAN),
        "r 日等重み平均": day_equal_mean(v, days),
        "r 中央値": q[1], "r p25": q[0], "r p75": q[2],
        "r < 0 の割合": float((fin < 0).mean()) if fin.size else NAN,
        "r < 0 の母数": int(fin.size),
    }


def next_liq(gap: np.ndarray) -> dict:
    n = gap.size
    out = {}
    for sec in NEXT_SEC:
        hit = np.isfinite(gap) & (gap <= sec)
        out[f"同じ側の次の清算 {sec} 秒以内の割合"] = float(hit.sum() / n) if n else NAN
        out[f"同じ側の次の清算 {sec} 秒以内の母数"] = n
    out["同じ側の次の清算が無い(この期間の最後)"] = int((~np.isfinite(gap)).sum())
    return out


def mm(v: np.ndarray, label: str) -> dict:
    fin = v[np.isfinite(v)]
    return {f"{label} 平均": float(fin.mean()) if fin.size else NAN,
            f"{label} 中央値": float(np.median(fin)) if fin.size else NAN}


def band_of(v: np.ndarray, cuts) -> np.ndarray:
    """委任先の band_of_m と同じ: searchsorted(side='right') + 1。NaN は −1。"""
    k = np.searchsorted(np.asarray(cuts, float), v, side="right") + 1
    return np.where(np.isfinite(v), k, -1)


def tertile_cuts(v: np.ndarray):
    fin = v[np.isfinite(v)]
    lo, hi = np.nanpercentile(fin, [100.0 / 3.0, 200.0 / 3.0])
    return float(lo), float(hi)


def tertile_mask(v: np.ndarray, lo: float, hi: float, q: int) -> np.ndarray:
    sel = (v <= lo) if q == 1 else ((v > lo) & (v <= hi)) if q == 2 else (v > hi)
    return sel & np.isfinite(v)


TER_LAB = ((1, "Q1(下位 3 分位)"), (2, "Q2(中位 3 分位)"), (3, "Q3(上位 3 分位)"))

# ---------------------------------------------------------------- 突き合わせ

MISMATCH: list = []
CHECKED = {"cells": 0, "rows": 0}


def cmp_row(table: str, key: str, got: dict, want: pd.Series, cols: list) -> None:
    CHECKED["rows"] += 1
    for c in cols:
        if c not in got:
            continue
        a, b = got[c], want[c]
        CHECKED["cells"] += 1
        if isinstance(b, str):
            try:
                b = float(b)
            except ValueError:
                continue
        fa, fb = float(a), float(b)
        if not math.isfinite(fa) and not math.isfinite(fb):
            continue
        if not math.isfinite(fa) or not math.isfinite(fb):
            MISMATCH.append((table, key, c, fa, fb))
            continue
        # 出力の csv は 6 桁で丸めてあるので、丸め幅 + 相対 1e-6 を許容する
        # 出力は 6 桁で丸めてあるので丸め幅 5e-7 を許容する
        if abs(fa - fb) > max(5.001e-7, TOL * max(abs(fa), abs(fb))):
            MISMATCH.append((table, key, c, fa, fb))


def main() -> int:
    df = pd.read_csv(ROWS)
    pr = df[df["kind"] == "print"].reset_index(drop=True)
    cc = df[df["kind"] == "control_c"].reset_index(drop=True)
    bi = df[df["kind"] == "control_b_i"].reset_index(drop=True)
    day = pr["day"].to_numpy()
    R = {h: pr[f"r_t0_{h}"].to_numpy(float) for h in H_ALL}
    Rts = {h: pr[f"r_{h}"].to_numpy(float) for h in H_ALL}
    gap = pr["next_same_side_gap_s"].to_numpy(float)
    k = pr["k"].to_numpy(float)
    d = pr["d"].to_numpy(float)
    m = {T: pr[f"m_{T}"].to_numpy(float) for T in T_MAIN}

    print(f"[行データ] print={len(pr)} control_c={len(cc)} control_b_i={len(bi)} "
          f"日数={pd.unique(day).size}")

    # ---- 帯・3 分位の切り値を行データから切り直す
    cuts = {T: np.percentile(m[T][np.isfinite(m[T])], [10 * i for i in range(1, 10)])
            for T in T_MAIN}
    ter = {T: tertile_cuts(m[T]) for T in T_MAIN}
    kpos = k[np.isfinite(k) & (k > 0)]
    kcuts = tuple(np.nanpercentile(kpos, [100 / 3, 200 / 3]))
    print("[切り値] m10 =", np.round(cuts[10], 6).tolist())
    print("[切り値] m60 =", np.round(cuts[60], 6).tolist())
    print("[切り値] m60 3分位 =", np.round(ter[60], 6).tolist(),
          " k>0 3分位 =", np.round(kcuts, 6).tolist())

    # =============================== H1
    h1 = pd.read_csv(OUT / "h1_all_prints.csv")
    bi_day = {h: bi.groupby("day")[f"r_{h}"].mean().to_dict() for h in H_ALL}
    sign = np.where(pr["side"].to_numpy() == "SELL", -1.0, 1.0)
    cols1 = [c for c in h1.columns if c not in ("群", "h(秒)")]
    for _, w in h1.iterrows():
        h = int(w["h(秒)"])
        got = {"プリント数": len(pr)}
        got.update(r_stats(R[h], day))
        got.update(next_liq(gap))
        bv = np.array([bi_day[h].get(dd, NAN) for dd in day]) * sign
        fin = bv[np.isfinite(bv)]
        got["対照 (b) 日集約 平均(bp)"] = float(fin.mean())
        got["対照 (b) 日集約 中央値"] = float(np.median(fin))
        got["対照 (b) の母数"] = int(fin.size)
        cmp_row("H1", f"h={h}", got, w, cols1)

    # =============================== H2
    h2 = pd.read_csv(OUT / "h2_premove.csv")
    cols2 = [c for c in h2.columns if c not in ("T(秒)", "m の帯", "帯の下限(bp)",
                                                "帯の上限(bp)", "h(秒)")]
    bands = {T: band_of(m[T], cuts[T]) for T in T_MAIN}
    for _, w in h2.iterrows():
        T, b, h = int(w["T(秒)"]), int(w["m の帯"]), int(w["h(秒)"])
        msk = bands[T] == b
        got = {"帯のプリント数": int(msk.sum())}
        got.update(mm(m[T][msk], "m"))
        got.update(mm(k[msk], "k"))
        got.update(r_stats(R[h][msk], day[msk]))
        got.update(next_liq(gap[msk]))
        cmp_row("H2", f"T={T} 帯{b} h={h}", got, w, cols2)

    # =============================== H3
    h3 = pd.read_csv(OUT / "h3_impact_premove.csv")
    cols3 = [c for c in h3.columns if c not in ("k の群", "m の群", "T(秒)", "h(秒)")]
    kmasks = {"K0(k ≤ 0)": np.isfinite(k) & (k <= 0)}
    for q, lab in TER_LAB:
        kmasks[f"K+{q}({lab}、k > 0)"] = (np.isfinite(k) & (k > 0)
                                          & tertile_mask(k, kcuts[0], kcuts[1], q))
    mmasks = {lab: tertile_mask(m[60], ter[60][0], ter[60][1], q) for q, lab in TER_LAB}
    for _, w in h3.iterrows():
        h = int(w["h(秒)"])
        msk = kmasks[w["k の群"]] & mmasks[w["m の群"]]
        got = {"群のプリント数": int(msk.sum()),
               "うち k = 0 ちょうどの数": int((msk & (k == 0.0)).sum())}
        got.update(mm(k[msk], "k"))
        got.update(mm(m[60][msk], "m"))
        got.update(r_stats(R[h][msk], day[msk]))
        got.update(next_liq(gap[msk]))
        cmp_row("H3", f"{w['k の群']}/{w['m の群']} h={h}", got, w, cols3)

    # =============================== H4(対照 c')
    h4 = pd.read_csv(OUT / "h4_control.csv")
    cols4 = [c for c in h4.columns if c not in ("種", "T(秒)", "m の帯",
                                                "帯の下限(bp)", "帯の上限(bp)", "h(秒)")]
    cday = cc["day"].to_numpy()
    cT = cc["ctrl_T"].to_numpy(float)
    ct = cc["c_t"].to_numpy(float)
    cR = {h: cc[f"r_t0_{h}"].to_numpy(float) for h in H_MAIN}
    cm = {T: cc[f"m_{T}"].to_numpy(float) for T in T_MAIN}
    for _, w in h4.iterrows():
        T, b, h = int(w["T(秒)"]), int(w["m の帯"]), int(w["h(秒)"])
        msk = (cT == T) & (band_of(cm[T], cuts[T]) == b)
        got = {"帯の行数": int(msk.sum())}
        got.update(mm(ct[msk], "c_t"))
        got.update(r_stats(cR[h][msk], cday[msk]))
        cmp_row("H4", f"T={T} 帯{b} h={h}", got, w, cols4)

    # =============================== H5
    h5 = pd.read_csv(OUT / "h5_density.csv")
    cols5 = [c for c in h5.columns if c not in ("d の群", "m の群", "T(秒)", "h(秒)")]
    dmasks = {"d = 0": d == 0, "d = 1〜2": (d >= 1) & (d <= 2), "d ≥ 3": d >= 3}
    for _, w in h5.iterrows():
        h = int(w["h(秒)"])
        msk = dmasks[w["d の群"]] & mmasks[w["m の群"]]
        got = {"群のプリント数": int(msk.sum())}
        got.update(mm(d[msk], "d"))
        got.update(mm(m[60][msk], "m"))
        got.update(r_stats(R[h][msk], day[msk]))
        got.update(next_liq(gap[msk]))
        cmp_row("H5", f"{w['d の群']}/{w['m の群']} h={h}", got, w, cols5)

    # =============================== H6
    h6 = pd.read_csv(OUT / "h6_attributes.csv")
    cols6 = [c for c in h6.columns if c not in ("属性", "群", "下限", "上限",
                                                "m の群", "T(秒)", "h(秒)")]
    side = pr["side"].to_numpy()
    hour = pr["hour_band"].to_numpy()
    attrv = {"print_notional": pr["notional"].to_numpy(float),
             "bin_pct": pr["bin_pct"].to_numpy(float),
             "|dist_node_bp|": np.abs(pr["dist_node_bp"].to_numpy(float)),
             "implied_leverage": pr["implied_leverage"].to_numpy(float)}
    gmask: dict = {}
    gmiss: dict = {}
    for s in ("SELL", "BUY"):
        gmask[("side", s)] = side == s
        gmiss[("side", s)] = 0.0
    for name, v in attrv.items():
        lo, hi = tertile_cuts(v)
        for q, lab in TER_LAB:
            gmask[(name, lab)] = tertile_mask(v, lo, hi, q)
            gmiss[(name, lab)] = float((~np.isfinite(v)).mean())
    HOUR_ATTR = "time_of_day(UTC 時、6 時間の 4 帯)"
    for hb in ("UTC 00–06", "UTC 06–12", "UTC 12–18", "UTC 18–24"):
        gmask[(HOUR_ATTR, hb)] = hour == hb
        gmiss[(HOUR_ATTR, hb)] = 0.0
    for _, w in h6.iterrows():
        h = int(w["h(秒)"])
        key = (w["属性"], w["群"])
        if key not in gmask:
            MISMATCH.append(("H6", str(key), "群が作れない", NAN, NAN))
            continue
        msk = gmask[key] & mmasks[w["m の群"]]
        got = {"群のプリント数": int(msk.sum()),
               "属性が欠測で群に入らないプリントの割合": gmiss[key]}
        got.update(mm(m[60][msk], "m"))
        got.update(r_stats(R[h][msk], day[msk]))
        got.update(next_liq(gap[msk]))
        cmp_row("H6", f"{key}/{w['m の群']} h={h}", got, w, cols6)

    # =============================== H0 診断(束の位置)+ 起点の取り方
    h0 = pd.read_csv(OUT / "h0_selfcheck.csv")
    pos = pr["bundle_pos"].to_numpy()
    single = pr["bundle_pos_single"].to_numpy(float)
    posmask = {"最初": (pos == "最初") | (single == 1),
               "途中": pos == "途中",
               "最後": (pos == "最後") | (single == 1)}
    diag = h0[h0["区分"] == "診断(束の位置)"]
    for _, w in diag.iterrows():
        h = int(str(w["量"]).split("h=")[1])
        msk = posmask[w["群"]]
        got = {"n": int(msk.sum()), "母数": int(msk.sum()),
               "r(t₀ 基準・主)平均": float(np.nanmean(R[h][msk])),
               "r(ts 基準・併記)平均": float(np.nanmean(Rts[h][msk])),
               "2 つの起点で値が違う行": int((R[h][msk] != Rts[h][msk]).sum()),
               "中央値": float(np.nanmedian(R[h][msk]))}
        cmp_row("H0診断", f"{w['群']} h={h}", got, w,
                ["n", "母数", "r(t₀ 基準・主)平均", "r(ts 基準・併記)平均",
                 "2 つの起点で値が違う行", "中央値"])
    org = h0[h0["区分"] == "起点の取り方"]
    for _, w in org.iterrows():
        h = int(str(w["量"]).split("h=")[1])
        got = {"n": len(pr), "母数": len(pr),
               "r(t₀ 基準・主)平均": float(np.nanmean(R[h])),
               "r(ts 基準・併記)平均": float(np.nanmean(Rts[h])),
               "2 つの起点で値が違う行": int((R[h] != Rts[h]).sum())}
        cmp_row("H0起点", f"h={h}", got, w,
                ["n", "母数", "r(t₀ 基準・主)平均", "r(ts 基準・併記)平均",
                 "2 つの起点で値が違う行"])

    # =============================== H0 対照 (c') の要所
    ctrl = h0[h0["区分"] == "対照 (c')"]
    for _, w in ctrl.iterrows():
        q = str(w["量"])
        T = int(w["T(秒)"])
        tsel = cT == T
        taken = np.isfinite(m[T])  # プリント側で対照が取れたか
        mid = cc.loc[tsel, "matched_print_id"].to_numpy()
        taken = pr["print_id"].isin(set(mid.tolist())).to_numpy()
        if q.startswith("対照 (c') が取れなかったプリント"):
            grp = str(w["群"])
            sel = np.ones(len(pr), bool) if grp == "全体" else (side == grp)
            got = {"n": int((~taken & sel).sum()), "母数": int(sel.sum()),
                   "割合": float((~taken & sel).sum() / sel.sum())}
            cmp_row("H0対照", f"T={T} {q} {grp}", got, w, ["n", "母数", "割合"])
        elif q.startswith("m の 10 分位帯ごとに取れなかった割合"):
            b = int(str(w["群"]).split()[1])
            sel = bands[T] == b
            got = {"n": int((~taken & sel).sum()), "母数": int(sel.sum()),
                   "割合": float((~taken & sel).sum() / sel.sum())}
            cmp_row("H0対照", f"T={T} 帯{b}", got, w, ["n", "母数", "割合"])
        elif q.startswith("取れた / 取れなかった"):
            sel = taken if str(w["群"]).startswith("取れた") else ~taken
            got = {"n": int(sel.sum()),
                   "m の中央値": float(np.nanmedian(m[T][sel])),
                   "k の中央値": float(np.nanmedian(k[sel])),
                   "r(60) の中央値": float(np.nanmedian(R[60][sel]))}
            cmp_row("H0対照", f"T={T} {w['群']}", got, w,
                    ["n", "m の中央値", "k の中央値", "r(60) の中央値"])
        elif q.startswith("日のプリント数 と"):
            n_pr = pd.Series(np.ones(len(pr)), index=day).groupby(level=0).sum()
            n_ct = pd.Series(taken.astype(float), index=day).groupby(level=0).sum()
            per = (n_ct / n_pr)
            got = {"n": int(n_pr.size), "母数": int(n_pr.size),
                   "相関": float(np.corrcoef(n_pr.to_numpy(), per.to_numpy())[0, 1])}
            cmp_row("H0対照", f"T={T} 相関", got, w, ["n", "母数", "相関"])
        elif q.startswith("|c_t − m_p|"):
            mp_by_id = dict(zip(pr["print_id"].tolist(), m[T].tolist()))
            mp = np.array([mp_by_id[i] for i in
                           cc.loc[tsel, "matched_print_id"].tolist()], float)
            v = np.abs(ct[tsel] - mp)
            p = np.percentile(v, [10, 25, 50, 75, 90, 99, 100])
            got = {"n": int(tsel.sum()), "母数": len(pr),
                   "p10": p[0], "p25": p[1], "p50": p[2], "p75": p[3],
                   "p90": p[4], "p99": p[5], "最大": p[6]}
            cmp_row("H0対照", f"T={T} |c_t-m|", got, w,
                    ["n", "母数", "p10", "p25", "p50", "p75", "p90", "p99", "最大"])
        elif q.startswith("候補の区間の変位"):
            got = {"n": int(tsel.sum()), "平均": float(np.nanmean(ct[tsel])),
                   "中央値": float(np.nanmedian(ct[tsel]))}
            cmp_row("H0対照", f"T={T} c_t", got, w, ["n", "平均", "中央値"])
        elif q.startswith("対照の掃き相当"):
            kc = cc["k_ctrl"].to_numpy(float)[tsel]
            got = {"n": int(tsel.sum()), "平均": float(np.nanmean(kc)),
                   "中央値": float(np.nanmedian(kc))}
            cmp_row("H0対照", f"T={T} k_ctrl", got, w, ["n", "平均", "中央値"])

    # =============================== H0 の残り(遅れ・分布・欠測)
    QS = ["p10", "p25", "p50", "p75", "p90", "p99", "最大"]

    def qrow(v):
        p = np.percentile(v[np.isfinite(v)], [10, 25, 50, 75, 90, 99, 100])
        return dict(zip(QS, p))

    lagmap = {"起点の遅れ p₀ − ts(ms)": pr["p0_lag_ms"].to_numpy(float),
              "直前の遅れ(ts − 1)− 直前の約定(ms)": pr["pre_lag_ms"].to_numpy(float)}
    for T in T_MAIN:
        lagmap[(T, "m の窓の遅れ(ms)")] = pr[f"m_lag_ms_{T}"].to_numpy(float)
    for h in H_ALL:
        lagmap[f"h 後の遅れ(ms) h={h}"] = pr[f"h_lag_ms_{h}"].to_numpy(float)
    for _, w in h0[h0["区分"] == "遅れ"].iterrows():
        key = w["量"] if w["T(秒)"] == "—" else (int(w["T(秒)"]), w["量"])
        v = lagmap[key]
        got = {"n": int(np.isfinite(v).sum()), "母数": len(pr)}
        got.update(qrow(v))
        cmp_row("H0遅れ", str(key), got, w, ["n", "母数"] + QS)
    for _, w in h0[h0["区分"] == "m の分布"].iterrows():
        T = int(w["T(秒)"])
        v = m[T]
        if str(w["量"]).startswith("m が引けない"):
            got = {"n": int((~np.isfinite(v)).sum()), "母数": len(pr),
                   "割合": float((~np.isfinite(v)).mean())}
            cmp_row("H0分布", f"m{T} 欠測", got, w, ["n", "母数", "割合"])
        else:
            got = {"n": int(np.isfinite(v).sum()), "母数": len(pr),
                   "割合": float((v <= 0).mean()),
                   "平均": float(np.nanmean(v)), "中央値": float(np.nanmedian(v))}
            got.update(qrow(v))
            cmp_row("H0分布", f"m{T}", got, w,
                    ["n", "母数", "割合", "平均", "中央値"] + QS)
    for _, w in h0[h0["区分"] == "k の分布"].iterrows():
        q = str(w["量"])
        if q == "k(bp)":
            got = {"n": int(np.isfinite(k).sum()), "母数": len(pr),
                   "平均": float(np.nanmean(k)), "中央値": float(np.nanmedian(k))}
            got.update(qrow(k))
            cmp_row("H0分布", "k", got, w, ["n", "母数", "平均", "中央値"] + QS)
        else:
            sel = {"k = 0 ちょうどのプリント": k == 0.0,
                   "k < 0 のプリント": k < 0,
                   "k が引けないプリント": ~np.isfinite(k)}[q]
            got = {"n": int(sel.sum()), "母数": len(pr), "割合": float(sel.mean())}
            cmp_row("H0分布", q, got, w, ["n", "母数", "割合"])
    for _, w in h0[h0["区分"] == "d の分布"].iterrows():
        if str(w["量"]) == "d(件)":
            got = {"n": len(pr), "母数": len(pr), "平均": float(d.mean()),
                   "中央値": float(np.median(d))}
            got.update(qrow(d))
            cmp_row("H0分布", "d", got, w, ["n", "母数", "平均", "中央値"] + QS)
        else:
            sel = {"d = 0": d == 0, "d = 1〜2": (d >= 1) & (d <= 2),
                   "d ≥ 3": d >= 3}[str(w["群"])]
            got = {"n": int(sel.sum()), "母数": len(pr), "割合": float(sel.mean())}
            cmp_row("H0分布", f"d {w['群']}", got, w, ["n", "母数", "割合"])
    missmap = {"付け直した属性が作れないプリント(bin_pct)":
               ~np.isfinite(pr["bin_pct"].to_numpy(float)),
               "付け直した属性が作れないプリント(dist_node_bp)":
               ~np.isfinite(pr["dist_node_bp"].to_numpy(float)),
               "付け直した属性が作れないプリント(implied_leverage)":
               ~np.isfinite(pr["implied_leverage"].to_numpy(float)),
               "探索段 4 の束(gap 60)に入らないプリント":
               pr["bundle_id"].isna().to_numpy()}
    for h in H_ALL:
        missmap[f"r(h)(t₀ 基準・主)が引けないプリント h={h}"] = ~np.isfinite(R[h])
    for _, w in h0[h0["区分"] == "欠測"].iterrows():
        sel = missmap[str(w["量"])]
        got = {"n": int(sel.sum()), "母数": len(pr), "割合": float(sel.mean())}
        cmp_row("H0欠測", str(w["量"]), got, w, ["n", "母数", "割合"])

    # =============================== 突き合わせの結果
    print(f"\n[突き合わせ] 行 {CHECKED['rows']} / セル {CHECKED['cells']} / "
          f"一致しないセル {len(MISMATCH)}")
    for t, key, c, a, b in MISMATCH[:60]:
        print(f"  × {t} {key} 列「{c}」 再計算={a!r} 出力={b!r}")
    return 0


# ===========================================================================
# 追加の計算(反証者が新しく切ったセル)
# ===========================================================================
def extras() -> None:
    import collections
    import glob
    import zipfile

    df = pd.read_csv(ROWS)
    pr = df[df["kind"] == "print"].reset_index(drop=True)
    cc = df[df["kind"] == "control_c"].reset_index(drop=True)
    bi = df[df["kind"] == "control_b_i"].reset_index(drop=True)
    day = pr["day"].to_numpy()
    side = pr["side"].to_numpy()
    ts = pr["ts_ms"].to_numpy(np.int64)
    t0 = pr["t0_ms"].to_numpy(np.int64)
    R = {h: pr[f"r_t0_{h}"].to_numpy(float) for h in H_ALL}
    k = pr["k"].to_numpy(float)
    d = pr["d"].to_numpy(float)
    m60 = pr["m_60"].to_numpy(float)
    m10 = pr["m_10"].to_numpy(float)
    gap = pr["next_same_side_gap_s"].to_numpy(float)

    print("\n" + "=" * 70)
    print("E1 日ごとの寄与(h=60・h=900 の平均を日で分解する)")
    for h in (60, 300, 900):
        v = R[h]
        m = float(v.mean())
        contrib = pd.Series(v, index=day).groupby(level=0).sum() / v.size
        s = contrib.reindex(contrib.abs().sort_values(ascending=False).index)
        top5 = float(s.iloc[:5].sum())
        top10 = float(s.iloc[:10].sum())
        neg = s[s < 0]
        print(f"  h={h}: 全体平均={m:.4f} 上位 5 日の寄与={top5:.4f}"
              f"({top5/m*100:.1f}%) 上位 10 日={top10:.4f}({top10/m*100:.1f}%)"
              f" 日数={s.size}")
        print(f"        上位 5 日 = {[(i, round(x,4)) for i, x in s.iloc[:5].items()]}")
        # 日の平均の符号
        dm = pd.Series(v, index=day).groupby(level=0).mean()
        print(f"        日の平均が負の日 {int((dm < 0).sum())}/{dm.size}"
              f"({(dm < 0).mean()*100:.1f}%)、日の平均の中央値={dm.median():.4f}")

    print("\nE2 平均と中央値の食い違い(h=60)")
    v = R[60]
    pos, negv = v[v > 0], v[v < 0]
    print(f"  r>0: n={pos.size} 平均={pos.mean():.3f} 合計={pos.sum():.0f}")
    print(f"  r<0: n={negv.size} 平均={negv.mean():.3f} 合計={negv.sum():.0f}")
    print(f"  r=0: n={int((v == 0).sum())}")
    for q in (0.1, 0.5, 1.0, 5.0):
        n = max(1, int(v.size * q / 100))
        idx = np.argsort(v)
        low = v[idx[:n]].sum() / v.size
        high = v[idx[-n:]].sum() / v.size
        print(f"  下位 {q}%({n} 件)の寄与={low:.4f} / 上位 {q}% の寄与={high:.4f}"
              f" / 両端を落とした平均={(v.sum()-v[idx[:n]].sum()-v[idx[-n:]].sum())/(v.size-2*n):.4f}")

    print("\nE3 束の位置を t₀ で分かる量から当てられるか")
    # 直前の同じ側のプリントからの間隔(t₀ 以前で分かる)
    prev_gap = np.full(len(pr), np.inf)
    for s in ("SELL", "BUY"):
        idx = np.where(side == s)[0]
        order = idx[np.argsort(ts[idx], kind="stable")]
        tt = ts[order].astype(float)
        g = np.diff(tt, prepend=np.nan) / 1000.0
        prev_gap[order] = g
    is_last = ((pr["bundle_pos"].to_numpy() == "最後")
               | (pr["bundle_pos_single"].to_numpy(float) == 1))
    print(f"  「最後」の割合(束に入る 49,439 件の中)= "
          f"{is_last[pr['bundle_id'].notna().to_numpy()].mean():.4f}"
          f" / 全 52,000 件の中 = {is_last.mean():.4f}")
    for name, vv, cuts_ in (("d", d, [0.5, 2.5, 5.5, 11.5]),
                            ("k", k, list(np.nanpercentile(k, [25, 50, 75, 90]))),
                            ("m60", m60, list(np.nanpercentile(m60, [25, 50, 75, 90]))),
                            ("直前の同じ側との間隔 s", prev_gap,
                             [10, 60, 300, 3600])):
        lab = np.digitize(np.nan_to_num(vv, nan=-1e18, posinf=1e18), cuts_)
        rows = []
        for b in range(len(cuts_) + 1):
            msk = lab == b
            if msk.sum() == 0:
                continue
            rows.append((b, int(msk.sum()), float(is_last[msk].mean()),
                         float(np.nanmean(R[60][msk])),
                         float(np.nanmedian(R[60][msk]))))
        print(f"  {name}: 切り値={[round(float(c),4) for c in cuts_]}")
        for b, n, p_last, rm, rmed in rows:
            print(f"    群{b}: n={n} 「最後」の割合={p_last:.4f} "
                  f"r(60)平均={rm:.4f} 中央値={rmed:.4f}")
    # 「最後」であるかを当てる単純な規則の当たり具合
    base = is_last.mean()
    for thr in (0, 1, 3):
        msk = d <= thr
        print(f"  規則「d ≤ {thr}」: n={int(msk.sum())} 的中率(「最後」)"
              f"={is_last[msk].mean():.4f}(基準 {base:.4f})"
              f" r(60)平均={np.nanmean(R[60][msk]):.4f}")

    print("\nE4 執行の視点(p₀ で入れない場合)")
    for h in (60, 300, 900):
        for lag in (1, 5, 10):
            v = R[h] - R[lag]
            print(f"  h={h} を lag={lag} 秒遅れて入る: 平均={v.mean():.4f} "
                  f"中央値={np.median(v):.4f} r<0 の割合={(v < 0).mean():.4f}")
    print(f"  r(1) 平均={R[1].mean():.4f} 中央値={np.median(R[1]):.4f}"
          f" r>0 の割合={(R[1] > 0).mean():.4f}")

    print("\nE5 重なり(独立でない観測の数)")
    for h in (60, 300, 900):
        order = np.argsort(t0, kind="stable")
        tt = t0[order]
        end = -1
        cnt = 0
        for x in tt:
            if x >= end:
                cnt += 1
                end = x + h * 1000
        print(f"  h={h}: 重ならない窓の最大数={cnt} / 52,000"
              f"(= {cnt/52000*100:.1f}%)")
    print(f"  同じ側の次の清算が 60 秒以内 = {np.mean(np.isfinite(gap) & (gap <= 60)):.4f}")

    print("\nE6 対照 (c') の対応づけ(選択の偏り)")
    for T in (10, 60):
        mcol = m10 if T == 10 else m60
        sel = cc["ctrl_T"].to_numpy(float) == T
        mid = set(cc.loc[sel, "matched_print_id"].tolist())
        taken = pr["print_id"].isin(mid).to_numpy()
        print(f"  T={T}: 取れた {int(taken.sum())} / 52,000 = {taken.mean():.4f}")
        # 対になったプリントだけで H2 と H4 を並べる
        cid = cc.loc[sel, "matched_print_id"].to_numpy()
        cr = {h: cc.loc[sel, f"r_t0_{h}"].to_numpy(float) for h in H_MAIN}
        pos_by_id = {p: i for i, p in enumerate(pr["print_id"].tolist())}
        pidx = np.array([pos_by_id[i] for i in cid])
        for h in H_MAIN:
            pv = R[h][pidx]
            dv = pv - cr[h]
            mean, se, naive, n, g = cluster_se(dv, day[pidx])
            print(f"    h={h}: 対のプリント 平均={pv.mean():.4f} 中央値={np.median(pv):.4f}"
                  f" / 対照 平均={cr[h].mean():.4f} 中央値={np.median(cr[h]):.4f}"
                  f" / 差 平均={mean:.4f} 日クラスタSE={se:.4f} 中央値={np.median(dv):.4f}")
        # 取れた側と取れなかった側で全プリントの r を比べる
        for h in (60,):
            print(f"    取れた側の r({h}) 平均={np.nanmean(R[h][taken]):.4f} / "
                  f"取れなかった側={np.nanmean(R[h][~taken]):.4f}")

    print("\nE7 対照 (b)(control_b_i、日集約)の中身")
    print(f"  行 {len(bi)} / 日 {bi['day'].nunique()} = 1 日あたり "
          f"{len(bi)/bi['day'].nunique():.2f} 行、side 列は "
          f"{'空' if bi['side'].isna().all() else '有り'}")
    for h in (60, 300, 900):
        raw = bi[f"r_t0_{h}"].to_numpy(float)
        print(f"  h={h}: 生(符号なし)平均={np.nanmean(raw):.4f} "
              f"中央値={np.nanmedian(raw):.4f} 標準偏差={np.nanstd(raw):.4f}")
        dmean = bi.groupby("day")[f"r_t0_{h}"].mean()
        sgn = np.where(side == "SELL", -1.0, 1.0)
        bv = dmean.reindex(day).to_numpy() * sgn
        # 側で分けた対照 (b)
        for s in ("SELL", "BUY"):
            msk = side == s
            print(f"    側 {s}: 対照(b)平均={np.nanmean(bv[msk]):.4f} "
                  f"プリント r 平均={np.nanmean(R[h][msk]):.4f} n={int(msk.sum())}")
        print(f"    両側を混ぜた対照(b)平均={np.nanmean(bv):.4f}"
              f"(SELL {int((side=='SELL').sum())} / BUY {int((side=='BUY').sum())})")

    print("\nE8 「束の外」2,561 件")
    out = pr["bundle_id"].isna().to_numpy()
    print(f"  件数={int(out.sum())} 日数={pd.unique(day[out]).size} "
          f"側 SELL={int((side[out]=='SELL').sum())} BUY={int((side[out]=='BUY').sum())}")
    print(f"  r(60) 平均={np.nanmean(R[60][out]):.4f} 中央値={np.nanmedian(R[60][out]):.4f}"
          f" / 束に入る側 平均={np.nanmean(R[60][~out]):.4f}")
    cnt = pd.Series(out.astype(int), index=day).groupby(level=0).sum()
    print(f"  日ごとの「束の外」の数: 最大={int(cnt.max())}({cnt.idxmax()}) "
          f"上位 5 日の合計={int(cnt.sort_values(ascending=False)[:5].sum())}")
    print(f"  「最初」+「途中」+「最後」の合計="
          f"{21198+19072+21198} 単発の束={int((pr['bundle_pos_single'].to_numpy(float)==1).sum())}")

    print("\nE9 切り値の期間の偏り(事後の切り方)")
    half = day < "2024-02-01"
    for T, mv in ((10, m10), (60, m60)):
        c_all = np.percentile(mv, [10 * i for i in range(1, 10)])
        c_a = np.percentile(mv[half], [10 * i for i in range(1, 10)])
        c_b = np.percentile(mv[~half], [10 * i for i in range(1, 10)])
        ba = band_of(mv, c_all)
        bb = np.where(half, band_of(mv, c_a), band_of(mv, c_b))
        print(f"  T={T}: 全期間の切り値 q9={c_all[8]:.3f} / 前半 {c_a[8]:.3f} / "
              f"後半 {c_b[8]:.3f}、帯が変わるプリント={int((ba != bb).sum())}"
              f"({(ba != bb).mean()*100:.1f}%)")
    lev = pr["implied_leverage"].to_numpy(float)
    okl = np.isfinite(lev)
    print(f"  implied_leverage 欠測 {int((~okl).sum())}/52,000、"
          f"有る側の日数={pd.unique(day[okl]).size} / 全 456 日、"
          f"有る側の r(60) 平均={np.nanmean(R[60][okl]):.4f} / "
          f"無い側={np.nanmean(R[60][~okl]):.4f}")

    print("\nE10 H2 の h 依存(問い 9)")
    cuts10 = np.percentile(m10, [10 * i for i in range(1, 10)])
    b10 = band_of(m10, cuts10)
    for b in (1, 5, 9, 10):
        msk = b10 == b
        row = [f"帯{b}(n={int(msk.sum())})"]
        for h in H_ALL:
            mean, se, naive, n, g = cluster_se(R[h][msk], day[msk])
            row.append(f"h={h}: {mean:+.2f}±{se:.2f}(中央値 {np.median(R[h][msk]):+.2f})")
        print("  " + " | ".join(row))

    print("\nE11 重複除去(生の zip から数え直す)")
    files = sorted(glob.glob("backtest_data/binance_cm_o3c_20260913/"
                             "liquidationSnapshot/BTCUSD_PERP/*.zip"))
    raw = 0
    uniq = 0
    mult = collections.Counter()
    seen_all: dict = {}
    for p in files:
        with zipfile.ZipFile(p) as z:
            name = z.namelist()[0]
            txt = z.read(name).decode().splitlines()
        body = [l for l in txt[1:] if l.strip()]
        raw += len(body)
        c = collections.Counter(body)
        uniq += len(c)
        for key, n in c.items():
            mult[n] += 1
            seen_all[key] = seen_all.get(key, 0) + 1
    print(f"  zip={len(files)} 生の行={raw} 全列一致で 1 件={uniq}")
    print(f"  多重度の分布(件数)= {dict(sorted(mult.items()))}")
    cross = sum(1 for v in seen_all.values() if v > 1)
    print(f"  日を跨いで全列一致する組={cross}")


if __name__ == "__main__":
    main()
    extras()


def count_cells(path: str) -> tuple:
    """`|` で始まる表の行から区切り行と各表の見出し行を除き、float() に通るセルを数える
    (探索段 3 の反証者のセル数と同じ数え方)。"""
    rows = hdr = n = 0
    inhdr = True
    for line in Path(path).read_text().splitlines():
        if not line.startswith("|"):
            inhdr = True
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        if inhdr:
            inhdr = False
            hdr += 1
            continue
        rows += 1
        for c in line.strip().strip("|").split("|"):
            try:
                float(c.strip())
                n += 1
            except ValueError:
                pass
    return rows, hdr, n
