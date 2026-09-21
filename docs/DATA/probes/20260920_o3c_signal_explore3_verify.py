"""リードの再計算(探索段 3、2026-09-20)。委任先の f2_retrace.csv の gap 60 の要所を rows_gap60.csv.gz から独立に出す。"""
import gzip, math, sys
import numpy as np, pandas as pd
d = pd.read_csv("backtest_data/o3c_signal_explore3_20260920/rows_gap60.csv.gz")
print("rows", len(d), d["kind"].value_counts().to_dict())
def cl(v, days):
    m = np.isfinite(v); v = v[m]; days = days[m]
    n = v.size; mu = v.mean()
    s = pd.Series(v - mu).groupby(days).sum()
    G = s.size
    se = math.sqrt((s**2).sum()) / n * math.sqrt(G / (G - 1))
    return mu, se, n, G
liq = d[d["kind"] == "liq"]
print("liq n", len(liq), "sweep<=0", int((liq["sweep_bp"] <= 0).sum()), "sweep NaN", int(liq["sweep_bp"].isna().sum()))
for kind, sub in (("liq", liq), ("ctrl_a", d[d["kind"].str.contains("a", regex=False) & ~d["kind"].isin(["liq"])])):
    print("kind", kind, "n", len(sub), sub["kind"].unique()[:3])
    for h in (60, 300, 900):
        mu, se, n, G = cl(sub[f"r_pre_{h}"].to_numpy(float), sub["day"].to_numpy())
        mu2, se2, _, _ = cl(sub[f"r_end_{h}"].to_numpy(float), sub["day"].to_numpy())
        f = sub[f"f_{h}"].to_numpy(float); f = f[np.isfinite(f)]
        print(f"  h={h} r_pre {mu:+.4f}±{se:.4f} (n={n},G={G}) r_end {mu2:+.4f}±{se2:.4f} "
              f"f>1 {np.mean(f>1):.4f} 0..1 {np.mean((f>=0)&(f<=1)):.4f} f<0 {np.mean(f<0):.4f} nf={f.size} fmed {np.median(f):.4f}")
# 次の束まで 180 秒以上(gap 60 清算)
sub = liq[liq["next_bundle_gap_s"] >= 180]
mu, se, n, G = cl(sub["r_pre_300"].to_numpy(float), sub["day"].to_numpy())
print(f"next>=180 n={n} r_pre_300 {mu:+.4f}±{se:.4f}")
# 基準の自己点検
print("baseline_lag_ms quantiles", liq["baseline_lag_ms"].quantile([.5,.9,.99]).to_dict(), "max", liq["baseline_lag_ms"].max())
print("baseline_in_prev_bundle", int(liq["baseline_in_prev_bundle"].sum()))
