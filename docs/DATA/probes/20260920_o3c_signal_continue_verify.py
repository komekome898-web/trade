"""続く / 止まるの単位: リードが行データから独立に再計算する(2026-09-20)。道具の表の関数は使わない。"""
import hashlib, math, numpy as np, pandas as pd
D = "backtest_data/o3c_signal_continue_20260920/"
print("MD5 rows_continue.csv.gz:", hashlib.md5(open(D + "rows_continue.csv.gz", "rb").read()).hexdigest())
r = pd.read_csv(D + "rows_continue.csv.gz")
print("rows:", len(r), "columns:", len(r.columns)); print([c for c in r.columns][:80])
p = r[r.kind == "print"].reset_index(drop=True) if "print" in set(r.kind) else r[r.print_id.notna()].reset_index(drop=True)
print("kind counts:", r.kind.value_counts().to_dict())
fh = p[p.half == p.half.min()]; sh = p[p.half != p.half.min()]
print("half values:", p.half.unique().tolist(), "前半 n", len(fh), "日", fh.day.nunique(), "後半 n", len(sh), "日", sh.day.nunique())
print("基準率(前半 60 秒)", round(fh.label_60.mean(), 4), " 後半", round(sh.label_60.mean(), 4), " 30 秒後半", round(sh.label_30.mean(), 4), " 120 秒後半", round(sh.label_120.mean(), 4))
def cl(v, d):
    f = np.isfinite(v); v = v[f]; d = d[f]; n = v.size; m = v.mean(); s = pd.Series(v - m).groupby(d).sum(); G = s.size
    return n, G, np.median(v), float((v < 0).mean()), pd.Series(v).groupby(d).mean().mean(), math.sqrt((s**2).sum())/n*math.sqrt(G/(G-1))
def payoff(df, say_continue, entry=1, hold=60):
    pe = df[f"p_entry_{entry}"].to_numpy(float); px = df[f"p_exit_e{entry}_h{hold}"].to_numpy(float)
    mv = df.dir_sign.to_numpy(float) * (px - pe) / pe * 1e4
    return np.where(say_continue, mv, -mv)
print("\n== Q4 再計算(後半、入る t₀+1 秒、60 秒保有)")
for lbl, say in (("all_continue", np.ones(len(sh), bool)), ("all_stop", np.zeros(len(sh), bool)), ("perfect", sh.label_60.to_numpy() == 1)):
    v = payoff(sh, say); d = sh.day.to_numpy()
    for br, msk in (("続く", say), ("止まる", ~say)):
        if msk.sum() == 0: continue
        n, G, med, neg, dew, se = cl(v[msk], d[msk]); print(f"{lbl:<13} {br:<4} n={n:<6} 日={G:<4} 中央値={med:+.4f} 負={neg:.4f} 日等重み={dew:+.4f} SE={se:.4f}")
print("\n== Q2 再計算: 前半で 10 分位帯を切り、帯の続く割合 > 前半の基準率 の帯を「続く」と言う規則を後半に当てる")
base = fh.label_60.mean()
for m in ("mat1_same_side_count_60s_and_elapsed", "mat14_trade_count_60s", "mat5_distance_to_liquidation_node", "mat4_move_since_cascade_start_and_bounce", "mat9_taker_imbalance_5s"):
    x = fh[m].to_numpy(float); ok = np.isfinite(x); cuts = np.quantile(x[ok], [i/10 for i in range(1, 10)])
    band_f = np.searchsorted(cuts, x, side="right"); rate = pd.Series(fh.label_60.to_numpy()[ok]).groupby(band_f[ok]).mean()
    cont_bands = set(rate[rate > base].index)
    xs = sh[m].to_numpy(float); oks = np.isfinite(xs); bs = np.searchsorted(cuts, xs, side="right")
    say = np.isin(bs, list(cont_bands)) & oks; lab = sh.label_60.to_numpy() == 1
    hit = float((say == lab)[oks].mean()); prec = float(lab[say].mean()) if say.sum() else float("nan"); rec = float(say[lab & oks].mean())
    v = payoff(sh, say); d = sh.day.to_numpy()
    n1, G1, med1, neg1, dew1, se1 = cl(v[say], d[say]); n0, G0, med0, neg0, dew0, se0 = cl(v[~say & oks], d[~say & oks])
    print(f"{m:<44} 続く帯={sorted(cont_bands)} n={int(oks.sum())} 的中={hit:.4f} 適合={prec:.4f} 再現={rec:.4f} 続く件={int(say.sum())} | 続く枝 中央値={med1:+.4f} 負={neg1:.4f} SE={se1:.4f} | 止まる枝 中央値={med0:+.4f} 負={neg0:.4f} SE={se0:.4f}")
print("\n== 位置(前 60 秒に同じ側の清算が有るか)ごとの続く割合(後半)と、その群の損益(all_stop 側)")
m1 = sh["mat1_same_side_count_60s_and_elapsed"].to_numpy(float)
for lbl, msk in (("1 件目(前 60 秒に無し)", m1 == 0), ("2 件目以降", m1 > 0)):
    v = payoff(sh, np.zeros(len(sh), bool)); n, G, med, neg, dew, se = cl(v[msk], sh.day.to_numpy()[msk])
    print(f"{lbl:<20} n={int(msk.sum())} 続く割合={sh.label_60.to_numpy()[msk].mean():.4f} 逆張りの中央値={med:+.4f} 負={neg:.4f} 日等重み={dew:+.4f} SE={se:.4f}")
