"""反証者レビュー 6 の致命 1〜6 をリードが行データから計算し直す(2026-09-20)。"""
import math, numpy as np, pandas as pd
D = "backtest_data/o3c_signal_continue_20260920/"
r = pd.read_csv(D + "rows_continue.csv.gz"); p = r[r.kind == "print"].reset_index(drop=True)
e5 = pd.read_csv("backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz"); e5 = e5[e5.kind == "print"][["print_id", "bundle_pos", "bundle_pos_single", "k"]]
p = p.merge(e5, on="print_id", how="left")
single = p.bundle_pos_single.to_numpy(float) == 1; pos = p.bundle_pos.astype(str).to_numpy()
grp = np.where(pos == "束の外", "束の外", np.where(single, "単発", np.where(pos == "最初", "多件の最初", np.where(pos == "途中", "途中", "多件の最後"))))
p["grp"] = grp
def cl(v, d):
    f = np.isfinite(v); v = v[f]; d = d[f]; n = v.size; m = v.mean(); s = pd.Series(v - m).groupby(d).sum(); G = s.size
    return n, m, math.sqrt((s**2).sum())/n*math.sqrt(G/(G-1)) if G > 1 else float("nan"), float(np.median(v))
def mv(df, entry=1, hold=60):
    pe = df[f"p_entry_{entry}"].to_numpy(float); px = df[f"p_exit_e{entry}_h{hold}"].to_numpy(float)
    return df.dir_sign.to_numpy(float) * (px - pe) / pe * 1e4
sh = p[p.half == "後半"].reset_index(drop=True); fh = p[p.half == "前半"].reset_index(drop=True)
print("== 致命 1: rule_1(前 60 秒に同じ側の清算あり = 材料 1 ≥ 1)の「続く」枝に入る群(後半)")
say = sh.mat1_same_side_count_60s_and_elapsed.to_numpy(float) >= 1
for g in ("多件の最初", "途中", "単発", "多件の最後", "束の外"):
    m = sh.grp.to_numpy() == g; v = mv(sh); n, mean, se, med = cl(v[m], sh.day.to_numpy()[m])
    print(f"{g:<6} n={int(m.sum()):<6} 続くと言われた={int((m & say).sum()):<6} 乗った損益 平均={mean:+.3f} SE={se:.3f} 中央値={med:+.3f}")
print("\n== 致命 2: 予測 × 実際(rule_1、後半、乗った損益)")
lab = sh.label_60.to_numpy() == 1; v = mv(sh); d = sh.day.to_numpy()
for lbl, m in (("予測続く×実際続く", say & lab), ("予測続く×実際止まる", say & ~lab), ("予測止まる×実際続く", ~say & lab), ("予測止まる×実際止まる", ~say & ~lab)):
    n, mean, se, med = cl(v[m], d[m]); print(f"{lbl:<14} n={n:<6} 乗った損益 平均={mean:+.3f} 中央値={med:+.3f}")
a = v[say & lab].mean(); b = v[say & ~lab].mean(); print("続く枝の取り分が 0 になる適合率 =", round(-b / (a - b), 4), " 実際の適合率 =", round(float(lab[say].mean()), 4))
print("\n== 致命 4: 全部逆張り(all_stop)の前半と後半")
for lbl, df in (("前半", fh), ("後半", sh)):
    v = -mv(df); n, mean, se, med = cl(v, df.day.to_numpy()); print(f"{lbl} n={n} 平均={mean:+.4f} SE={se:.3f} 中央値={med:+.4f}")
    out = df.grp.to_numpy() == "束の外"; n2, mean2, se2, med2 = cl(v[~out], df.day.to_numpy()[~out]); print(f"   束の外 {int(out.sum())} 件を除く: 平均={mean2:+.4f} SE={se2:.3f}")
    contrib = pd.Series(v).groupby(df.day.to_numpy()).sum(); print("   日ごとの合計の最小:", contrib.idxmin(), round(contrib.min(), 1))
print("\n== 致命 5: 材料 1 = 0 の行で |材料 4| == |k(bp)|(k は探索段 5 の列)か")
m0 = p.mat1_same_side_count_60s_and_elapsed.to_numpy(float) == 0
d4 = np.abs(np.abs(p.mat4_move_since_cascade_start_and_bounce.to_numpy(float)) - np.abs(p.k.to_numpy(float)))
print("材料 1 = 0 の行", int(m0.sum()), " そのうち |材料4| と |k| の差 < 1e-6:", int((d4[m0] < 1e-6).sum()))
print("\n== 致命 6: rule_12 の集合 = 材料 12 が引ける行 = 材料 1 ≥ 1 か")
m12 = np.isfinite(p.mat12_notional_over_max_recent_print.to_numpy(float)); m1 = p.mat1_same_side_count_60s_and_elapsed.to_numpy(float) >= 1
print("材料 12 有限 ⟺ 材料 1 ≥ 1 の一致行:", int((m12 == m1).sum()), "/", len(p))
print("\n== 直すべき: Q7 の取れた割合(後半で材料 15・9 が引ける行が分母)")
ok = np.isfinite(sh.mat15_burst_ratio_10s_over_60s.to_numpy(float)) & np.isfinite(sh.mat9_taker_imbalance_5s.to_numpy(float))
got = sh.q7_matched_print_id.notna().to_numpy() if sh.q7_matched_print_id.notna().any() else None
cand = r[r.kind == "q7_candidate"]; print("候補の行", len(cand), " 後半で引ける行", int(ok.sum()), " 取れた割合 =", round(len(cand) / int(ok.sum()), 4))
print("== Q7 の対照の荒さ: 60 秒の動きの四分位幅 プリント(後半) 対 候補")
def iqr(df):
    pe = df.p_entry_1.to_numpy(float); px = df.p_exit_e1_h60.to_numpy(float); x = (px - pe) / pe * 1e4; x = x[np.isfinite(x)]; return np.percentile(x, 75) - np.percentile(x, 25)
print("プリント IQR", round(iqr(sh), 2), " 候補 IQR", round(iqr(cand), 2), " 比", round(iqr(sh) / iqr(cand), 2))
print("値段の続きの割合 プリント(後半)", round(float(sh.value_continuation_60.mean()), 4), " 候補", round(float(cand.value_continuation_60.mean()), 4))
