"""リードの再計算(反証者レビュー 3 の要所、2026-09-20)。rows_gap60.csv.gz から独立に出す。"""
import math
import numpy as np, pandas as pd
d = pd.read_csv("backtest_data/o3c_signal_explore3_20260920/rows_gap60.csv.gz")
def cl(v, days):
    m = np.isfinite(v); v = v[m]; days = days[m]; n = v.size; mu = v.mean()
    s = pd.Series(v - mu).groupby(days).sum(); G = s.size
    return mu, math.sqrt((s**2).sum()) / n * math.sqrt(G / (G - 1)), n
def show(tag, sub, cols=("r_pre_60","r_pre_300","r_end_60")):
    out = [f"{tag} n={len(sub)}"]
    for c in cols:
        mu, se, n = cl(sub[c].to_numpy(float), sub["day"].to_numpy()); out.append(f"{c} {mu:+.3f}±{se:.3f}")
    f = sub["f_60"].to_numpy(float); f = f[np.isfinite(f)]
    if f.size: out.append(f"f60 med {np.median(f):.3f} f>1 {np.mean(f>1):.4f}")
    print("  ".join(out))
liq = d[d["kind"]=="liq"]; S = liq["sweep_bp"]
print("致命 1/3: sweep=0", int((S==0).sum()), "sweep<0", int((S<0).sum()), "1 tick", int(((liq.p_end-liq.p_pre).abs().round(4)==0.1).sum() if False else 0))
show("sweep>0", liq[S>0]); show("sweep<=0", liq[S<=0]); show("sweep=0", liq[S==0]); show("sweep<0", liq[S<0])
show("sweep>20", liq[S>20]); show("sweep>5", liq[S>5])
q3 = 8.076017
show("sweep Q3(>8.076)", liq[S>q3], cols=("r_pre_60","r_pre_300","r_pre_900"))
f = liq[S>q3]["f_300"]; print("  Q3 f300 med", round(float(f.median()),3), "f900 med", round(float(liq[S>q3]["f_900"].median()),3))
# 致命 5
A = liq["next_bundle_gap_s"]>=180; B = liq["prev_bundle_gap_s"]>=180
print("致命 5: A", int(A.sum()), "B", int(B.sum()), "A&B", int((A&B).sum()), "Aonly", int((A&~B).sum()), "Bonly", int((B&~A).sum()))
show("A only", liq[A&~B]); show("B only", liq[B&~A])
# 致命 4
ca = d[d["kind"]=="control_a"]; matched = set(ca["matched_liq_id"])
pos = liq[S>0]; got = pos[pos["cascade_id"].isin(matched)]; miss = pos[~pos["cascade_id"].isin(matched)]
print("致命 4: got", len(got), "miss", len(miss), "miss sweep med", round(float(miss.sweep_bp.median()),3), "got sweep med", round(float(got.sweep_bp.median()),3))
show("liq matched", got); show("ctrl_a", ca)
print("  ctrl_a W_b=0 share", round(float(((ca.t_end_ms - ca.ctrl_t_ms)>=0).mean()),3) if "ctrl_t_ms" in ca else "")
# 致命 6
for h in (60,300,900):
    mu, se, n = cl(liq[f"bf_r_pre_{h}"].to_numpy(float), liq["day"].to_numpy()); print(f"致命 6: bf_r_pre_{h} {mu:+.3f}±{se:.3f} n={n}")
print("  bf baseline offset mean s", round(float((liq.t_pre_ms % 60000).mean()/1000),1))

# 追記(2026-09-20、報告の監査 3 回目・指摘 3): §3 の表に r_end(60 秒)の列を足すための値
print("--- r_end_60 by sweep tertile (F5 cuts: 0.200939 / 8.076017) ---")
lo, hi = 0.200939, 8.076017
for tag, m in (("Q1", (S>0)&(S<=lo)), ("Q2", (S>lo)&(S<=hi)), ("Q3", S>hi)):
    mu, se, n = cl(liq[m]["r_end_60"].to_numpy(float), liq[m]["day"].to_numpy()); print(f"sweep {tag} n={n} r_end_60 {mu:+.3f}±{se:.3f}")
