"""探索段 5 の主な数値をリードが行データから独立に再計算する(2026-09-20)。
道具 scripts/o3c_signal_explore5.py の表の関数は使わない。行データ rows_prints.csv.gz だけを読む。
"""
import hashlib, json, math, sys
import numpy as np, pandas as pd

D = "backtest_data/o3c_signal_explore5_20260920/"
print("MD5 rows_prints.csv.gz:", hashlib.md5(open(D + "rows_prints.csv.gz", "rb").read()).hexdigest())
r = pd.read_csv(D + "rows_prints.csv.gz")
print("kind counts:", r["kind"].value_counts().to_dict())
p = r[r["kind"] == "print"].reset_index(drop=True)
print("prints:", len(p), "days:", p["day"].nunique())

def cl(v, days):
    fin = np.isfinite(v); v = v[fin]; days = days[fin]
    n = v.size; m = v.mean()
    s = pd.Series(v - m).groupby(days).sum()
    G = s.size
    se = math.sqrt((s ** 2).sum()) / n * math.sqrt(G / (G - 1))
    naive = v.std(ddof=1) / math.sqrt(n)
    dew = pd.Series(v).groupby(days).mean().mean()
    return n, G, m, se, naive, dew, np.median(v), (v < 0).mean()

def show(label, mask, h, col="r_t0"):
    v = p.loc[mask, f"{col}_{h}"].to_numpy(float); d = p.loc[mask, "day"].to_numpy()
    n, G, m, se, naive, dew, med, neg = cl(v, d)
    print(f"{label:<44} h={h:<4} n={n:<6} G={G:<4} mean={m:+.6f} clSE={se:.6f} naive={naive:.6f} dew={dew:+.6f} med={med:+.6f} r<0={neg:.6f}")

print("\n== H1 全プリント(t₀ 基準)")
for h in (1, 5, 10, 30, 60, 300, 900): show("全プリント", np.ones(len(p), bool), h)
print("== H1 全プリント(ts 基準・併記)")
for h in (60, 300): show("全プリント ts", np.ones(len(p), bool), h, "r")

print("\n== H0 診断: 束の位置(t₀ 基準)。探索段 4 の r_end(60) = −6.800366 との突き合わせ")
print("bundle_pos values:", p["bundle_pos"].value_counts().to_dict(), " single:", p["bundle_pos_single"].value_counts().to_dict())
for pos in sorted(p["bundle_pos"].dropna().unique()):
    for h in (60, 300):
        show(f"位置={pos}", (p["bundle_pos"] == pos).to_numpy(), h)

print("\n== H2 m(T) の 10 分位帯(456 日の全プリントで切る)")
for T in (10, 60):
    m = p[f"m_{T}"].to_numpy(float)
    cuts = np.quantile(m[np.isfinite(m)], [i / 10 for i in range(1, 10)])
    print(f"T={T} cuts:", np.round(cuts, 6).tolist())
    band = np.where(np.isfinite(m), np.searchsorted(cuts, m, side="right") + 1, 0)
    for k in (1, 5, 10):
        for h in (60, 300):
            show(f"T={T} 帯{k} (m 平均 {np.nanmean(m[band==k]):+.4f})", band == k, h)

print("\n== H3 k 4 群 × m(60) 3 分位(h = 60/300/900)")
k = p["k"].to_numpy(float); m60 = p["m_60"].to_numpy(float)
lo, hi = np.nanpercentile(m60[np.isfinite(m60)], [100 / 3, 200 / 3])
kpos = k[np.isfinite(k) & (k > 0)]
klo, khi = np.nanpercentile(kpos, [100 / 3, 200 / 3])
print(f"m tertile cuts: {lo:.6f} {hi:.6f}; k>0 tertile cuts: {klo:.6f} {khi:.6f}; k<=0 count: {int((k<=0).sum())}; k==0: {int((k==0).sum())}")
def ter(v, lo, hi, q):
    return (np.isfinite(v)) & ((v <= lo) if q == 1 else ((v > lo) & (v <= hi)) if q == 2 else (v > hi))
kg = [("K0", np.isfinite(k) & (k <= 0))] + [(f"K+{q}", np.isfinite(k) & (k > 0) & ter(k, klo, khi, q)) for q in (1, 2, 3)]
for kl, km in kg:
    for q in (1, 2, 3):
        mm = km & ter(m60, lo, hi, q)
        for h in (60, 300, 900):
            show(f"{kl} × Q{q}", mm, h)

print("\n== 探索段 4 のファイルから r_end(60) の全体平均を読み直す(束、gap 60)")
try:
    b = pd.read_csv("backtest_data/o3c_signal_explore4_20260920/rows_gap60.csv.gz")
    bb = b[b["kind"] == "bundle"] if "kind" in b.columns else b
    col = [c for c in bb.columns if c.startswith("r_end_60")][0]
    v = bb[col].to_numpy(float); print("explore4 bundles:", len(bb), col, "mean:", f"{np.nanmean(v):+.6f}", "n fin:", int(np.isfinite(v).sum()))
except Exception as e:
    print("explore4 read failed:", e)
