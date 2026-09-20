"""反証者レビュー 5 の致命 1〜5 の数値をリードが行データから計算し直す(2026-09-20)。"""
import math, numpy as np, pandas as pd
D = "backtest_data/o3c_signal_explore5_20260920/"
r = pd.read_csv(D + "rows_prints.csv.gz"); p = r[r.kind == "print"].reset_index(drop=True)
def cl(v, d):
    f = np.isfinite(v); v = v[f]; d = d[f]; n = v.size; m = v.mean()
    s = pd.Series(v - m).groupby(d).sum(); G = s.size
    return m, math.sqrt((s**2).sum())/n*math.sqrt(G/(G-1)), n
def line(lbl, mask, h=60):
    m, se, n = cl(p.loc[mask, f"r_t0_{h}"].to_numpy(float), p.loc[mask, "day"].to_numpy())
    print(f"{lbl:<46} h={h:<4} n={n:<6} mean={m:+.4f} SE={se:.4f} med={np.nanmedian(p.loc[mask, f'r_t0_{h}']):+.4f}")
v = p.r_t0_60.to_numpy(float)
print("== 致命 1: 日の寄与の上位 5 日、束の外を除いた平均")
contrib = pd.Series(v).groupby(p.day.to_numpy()).sum() / len(p)
top5 = contrib.sort_values(ascending=False).head(5); print(top5.round(4).to_dict(), "sum", round(top5.sum(), 4))
out = (p.bundle_pos == "束の外").to_numpy()
print("束の外 n", out.sum(), "mean", round(v[out].mean(), 4), "寄与", round(v[out].sum()/len(p), 4))
print("全体", round(v.mean(), 4), "束の外を除く", round(v[~out].mean(), 4), "上位5日を除く", round(v[~p.day.isin(top5.index).to_numpy()].mean(), 4), "両方除く", round(v[~out & ~p.day.isin(top5.index).to_numpy()].mean(), 4))
print("== 致命 2: k のティック数(k×1e-4×p0/0.1)")
k = p.k.to_numpy(float); p0 = p.p0.to_numpy(float); tick = k * 1e-4 * p0 / 0.1
print("k 分位 p10/25/50/75/90:", np.round(np.nanpercentile(k, [10, 25, 50, 75, 90]), 4).tolist(), " ティック分位:", np.round(np.nanpercentile(tick, [10, 25, 50, 75, 90]), 2).tolist())
kpos = np.isfinite(k) & (k > 0); klo, khi = np.nanpercentile(k[kpos], [100/3, 200/3])
dt = np.abs(p0 - p.p_pre.to_numpy(float)) / 0.1   # 保存桁で丸めた k からではなく価格差そのものからティック数を出す
for lbl, msk in (("K+1", kpos & (k <= klo)), ("K+2", kpos & (k > klo) & (k <= khi)), ("K+3", kpos & (k > khi))):
    t = dt[msk]; print(lbl, "n", msk.sum(), "|p0−p_pre| = 1 ティックちょうどの割合", round(float((np.abs(t - 1) < 1e-6).mean()), 4), "p0 中央値", round(float(np.median(p0[msk])), 0))
print("注: k×1e-4×p0/0.1 に ±1e-6 の許容で当てると保存桁の丸めで 1 にならない(最初の試みは 0.033)。価格差から数えると上のとおり。")
print("== 致命 3: 対で引いた差(対照 c' が取れたプリントとその対照)")
c = r[r.kind == "control_c"]
for T in (10, 60):
    cc = c[c.ctrl_T == T]
    j = cc.merge(p[["print_id", "day", "r_t0_60", "r_t0_300", "r_t0_900"]], left_on="matched_print_id", right_on="print_id", suffixes=("_c", "_p"))
    for h in (60, 300, 900):
        d = j[f"r_t0_{h}_p"].to_numpy(float) - j[f"r_t0_{h}_c"].to_numpy(float)
        m, se, n = cl(d, j["day_p"].to_numpy()); print(f"T={T} h={h} n={n} プリント {np.nanmean(j[f'r_t0_{h}_p']):+.4f} 対照 {np.nanmean(j[f'r_t0_{h}_c']):+.4f} 差 {m:+.4f} SE {se:.4f} 差の中央値 {np.nanmedian(d):+.4f}")
print("== 致命 4: 束の位置を排他に分ける")
single = p.bundle_pos_single.to_numpy(float) == 1
print("bundle_pos 実数", p.bundle_pos.value_counts().to_dict(), " 単発", int(single.sum()))
for lbl, msk in (("多件の最初", (p.bundle_pos == "最初").to_numpy() & ~single), ("途中", (p.bundle_pos == "途中").to_numpy()), ("単発", single), ("多件の最後", (p.bundle_pos == "最後").to_numpy() & ~single), ("束の外", out)):
    line(lbl, msk); line(lbl, msk, 900)
print("表の「最初」= 多件の最初 + 単発 (n)", int(((p.bundle_pos == "最初").to_numpy() | single).sum()), end=" "); line("表の最初(単発込み)", (p.bundle_pos == "最初").to_numpy() | single)
print("== 致命 5: d = 0 の内訳、直前の同じ側からの間隔")
last = (p.bundle_pos == "最後").to_numpy()
d0 = p.d.to_numpy(float) == 0
print("d=0 n", d0.sum(), "最後の割合", round(float(last[d0].mean()), 4), "全体の最後の割合", round(float(last.mean()), 4)); line("d = 0", d0)
line("d=0 × 単発", d0 & single); line("d=0 × 多件の最初", d0 & (p.bundle_pos == "最初").to_numpy() & ~single); line("d=0 × 束の外", d0 & out)
ps = p.sort_values(["side", "ts_ms"]); gap = ps.groupby("side").ts_ms.diff().reindex(p.index) / 1000
for lbl, msk in (("直前の同じ側から 600 秒超", gap.to_numpy() > 600), ("直前の同じ側から 10 秒以内", gap.to_numpy() <= 10), ("3,600 秒超", gap.to_numpy() > 3600)):
    print(lbl, "n", int(np.nansum(msk)), "最後の割合", round(float(last[msk].mean()), 4), end=" "); line(lbl, msk)
