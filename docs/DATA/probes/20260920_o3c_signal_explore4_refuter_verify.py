"""リードの再計算(反証者レビュー 4 の要所、2026-09-20)。rows_gap60.csv.gz から独立に出す。"""
import math
import numpy as np, pandas as pd
d = pd.read_csv("backtest_data/o3c_signal_explore4_20260920/rows_gap60.csv.gz")
def cl(v, days):
    m = np.isfinite(v); v = v[m]; days = days[m]; n = v.size; mu = v.mean()
    s = pd.Series(v - mu).groupby(days).sum(); G = s.size
    return mu, math.sqrt((s**2).sum()) / n * math.sqrt(G / (G - 1)), n
liq = d[d["kind"] == "liq"].copy(); days = liq["day"].to_numpy()
# 致命 1: 終端+60 → 終端+300 / +900(r_end は終端起点の bp。差分は同じ p_end 基準なので引き算でよい)
nx = liq["next_bundle_gap_s"].to_numpy(float)
print("致命 1: next_bundle_gap_s < 60 の件数", int((nx < 60).sum()), "p1", round(float(np.nanpercentile(nx, 1)), 1), "p50", round(float(np.nanpercentile(nx, 50)), 1))
for h in (300, 900):
    v = liq[f"r_end_{h}"].to_numpy(float) - liq["r_end_60"].to_numpy(float)
    mu, se, n = cl(v, days); print(f"  終端+60 → 終端+{h}: {mu:+.4f}±{se:.4f} n={n}")
mu, se, n = cl(liq["r_end_60"].to_numpy(float), days); print(f"  終端 → 終端+60: {mu:+.4f}±{se:.4f}")
# 致命 2: m の 10 分位で r_end/m と r_end/掃き
m = liq["m_60"].to_numpy(float); sw = liq["sweep_bp"].to_numpy(float); r = liq["r_end_60"].to_numpy(float)
q = np.quantile(m, np.arange(0.1, 1.0, 0.1)); edges = np.concatenate([[-np.inf], q, [np.inf]])
print("致命 2: 帯 / m平均 / 掃き平均 / r_end / r/m / r/掃き")
for k in (0, 1, 2, 4, 7, 9):
    sel = (m >= edges[k]) & (m < edges[k + 1])
    print(f"  帯{k+1} {m[sel].mean():.3f} {sw[sel].mean():.3f} {r[sel].mean():.3f} {r[sel].mean()/m[sel].mean():.3f} {r[sel].mean()/sw[sel].mean():.3f}")
X = np.column_stack([np.ones(len(liq)), m, sw]); beta = np.linalg.lstsq(X, r, rcond=None)[0]
print("  最小二乗 r_end = %.4f %+.4f·m %+.4f·掃き" % tuple(beta))
# 致命 5: 次の束 120 秒以内のうち同じ側の割合(掃きQ1×mQ1 と Q3×Q3)
liq_sorted = liq.sort_values(["day", "t_end_ms"])
side_next = liq_sorted.groupby("day")["side"].shift(-1)
liq_sorted = liq_sorted.assign(side_next=side_next)
mq = np.nanpercentile(m, [100/3, 200/3])
def cell(swlo, swhi, mlo, mhi):
    s = liq_sorted[(liq_sorted.sweep_bp > swlo) & (liq_sorted.sweep_bp <= swhi) & (liq_sorted.m_60 > mlo) & (liq_sorted.m_60 <= mhi)]
    s = s[np.isfinite(s.next_bundle_gap_s)]
    w = s[s.next_bundle_gap_s <= 120]
    return len(s), len(w) / len(s), float((w.side_next == w.side).mean())
for lab, args in (("掃きQ1×mQ1", (-np.inf, 0.200939, -np.inf, mq[0])), ("掃きQ3×mQ3", (8.076017, np.inf, mq[1], np.inf))):
    n, rate, same = cell(*args); print(f"致命 5: {lab} 母数 {n} 次≤120 {rate:.4f} うち同じ側 {same:.3f} 同じ側だけ {rate*same:.4f}")
# 直すべき 3: 前の束から 120 秒未満の束
pv = liq["prev_bundle_gap_s"].to_numpy(float); near = pv < 120
print("直すべき 3: 前の束から 120 秒未満", int(near.sum()), f"{near.mean():.4f}")
sel1 = (m >= edges[0]) & (m < edges[1])
for lab, mask in (("帯1 前が近い", sel1 & near), ("帯1 前が遠い", sel1 & (pv >= 120))):
    mu, se, n = cl(r[mask], days[mask]); print(f"  {lab}: {mu:+.3f}±{se:.3f} n={n}")
# 総括 3: m も掃きも小さい束(|m|<1 かつ |掃き|<0.2 相当は反証者の定義が不明なので、反証者の 1,364 に近い定義を試す)
for lab, mask in (("m<4 & |sweep|<0.2", (m < 4.0) & (np.abs(sw) < 0.2)), ("m<2 & |sweep|<0.2", (m < 2.0) & (np.abs(sw) < 0.2))):
    mu, se, n = cl(r[mask], days[mask]); print(f"小さい束 {lab}: {mu:+.3f}±{se:.3f} n={n}")
