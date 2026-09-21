"""リードの再計算(探索段 4、2026-09-20)。委任先の g1_reversal.csv / g2_continuation.csv の gap 60・T = 60・h = 60 を rows_gap60.csv.gz から独立に出す。"""
import math
import numpy as np, pandas as pd
D = "backtest_data/o3c_signal_explore4_20260920/"
d = pd.read_csv(D + "rows_gap60.csv.gz")
print("rows", len(d), d["kind"].value_counts().to_dict())
def cl(v, days):
    m = np.isfinite(v); v = v[m]; days = days[m]; n = v.size; mu = v.mean()
    s = pd.Series(v - mu).groupby(days).sum(); G = s.size
    return mu, math.sqrt((s**2).sum()) / n * math.sqrt(G / (G - 1)), n
liq = d[d["kind"] == "liq"].copy()
m = liq["m_60"].to_numpy(float)
q = np.quantile(m[np.isfinite(m)], np.arange(0.1, 1.0, 0.1))
edges = np.concatenate([[-np.inf], q, [np.inf]])
print("m_60 deciles cuts", np.round(q, 3).tolist(), "m<=0 share", round(float((m <= 0).mean()), 4))
g1 = pd.read_csv(D + "g1_reversal.csv")
sub = g1[(g1["gap(秒)"] == 60) & (g1["T(秒)"] == 60) & (g1["h(秒)"] == 60)]
print("--- G1 gap60 T60 h60: 委任先 vs リード ---")
for k in range(10):
    sel = (m >= edges[k]) & (m < edges[k + 1])
    mu, se, n = cl(liq.loc[sel, "r_end_60"].to_numpy(float), liq.loc[sel, "day"].to_numpy())
    gv = liq.loc[sel, "g_60_60"].to_numpy(float); den = liq.loc[sel, "den_bp_60"].to_numpy(float)
    ok = np.isfinite(gv) & (den > 0)
    row = sub.iloc[k]
    print(f"帯{k+1} n={n} m平均 {m[sel].mean():+.3f} r_end {mu:+.3f}±{se:.3f} | 委任先 {row['r_end 平均(bp)']:+.3f}±{row['r_end 日クラスタ SE']:.3f} n={row['n']} | g>1 {np.mean(gv[ok]>1):.4f} vs {row['g > 1 の割合(分母>0)']:.4f}")
# G2: 掃き 3 分位 × m 3 分位, T=60, h=60
g2 = pd.read_csv(D + "g2_continuation.csv")
print("--- G2 gap60 T60 h60 ---")
print(g2.columns.tolist()[:14])
s2 = g2[(g2["T(秒)"] == 60) & (g2["h(秒)"] == 60)]
print(s2[["掃きの群","m の群","n","r_end 平均(bp)","r_end 日クラスタ SE"] + [c for c in g2.columns if "120" in c][:2]].to_string(index=False))
# 独立: 掃き tertile (0.200939/8.076017) × m tertile
sw = liq["sweep_bp"].to_numpy(float)
mq = np.nanpercentile(m, [100/3, 200/3])
print("m_60 tertile cuts", np.round(mq, 3).tolist())
for si, (lo, hi) in enumerate([(-np.inf, 0.200939), (0.200939, 8.076017), (8.076017, np.inf)]):
    for mi, (mlo, mhi) in enumerate([(-np.inf, mq[0]), (mq[0], mq[1]), (mq[1], np.inf)]):
        sel = (sw > lo) & (sw <= hi) & (m > mlo) & (m <= mhi)
        mu, se, n = cl(liq.loc[sel, "r_end_60"].to_numpy(float), liq.loc[sel, "day"].to_numpy())
        nxt = liq.loc[sel, "next_bundle_gap_s"].to_numpy(float)
        cont = np.mean(nxt[np.isfinite(nxt)] <= 120)
        print(f"sweep Q{si+1} m Q{mi+1} n={n} r_end60 {mu:+.3f}±{se:.3f} next<=120 {cont:.4f} (母数 {int(np.isfinite(nxt).sum())})")
