#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反証者(research-protocol §11)の再計算 — O3C SIGNAL「続く / 止まるの単位」。

出力: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW6_2026-09-20.md` に貼る数値。
読むもの: backtest_data/o3c_signal_continue_20260920/(行データと q0〜q7)、
          backtest_data/o3c_signal_explore5_20260920/rows_prints.csv.gz(束の位置)。
paper_logs/ と data/jev/ は開かない。探索段なので判定語は書かない。
"""
from __future__ import annotations
import json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/trade")
OUT = ROOT / "backtest_data" / "o3c_signal_continue_20260920"
EX5 = ROOT / "backtest_data" / "o3c_signal_explore5_20260920" / "rows_prints.csv.gz"
NAN = float("nan")
N_BANDS = 10
MAT_VAR = {1:"same_side_count_60s_and_elapsed",2:"interval_ratio_last_two",
           3:"notional_and_ratio_to_previous",4:"move_since_cascade_start_and_bounce",
           5:"distance_to_liquidation_node",6:"time_of_day_band",
           8:"open_interest_mass_ahead",9:"taker_imbalance_5s",
           10:"oi_slope_and_funding",11:"notional_over_60s_range",
           12:"notional_over_max_recent_print",13:"taker_imbalance_trend",
           14:"trade_count_60s",15:"burst_ratio_10s_over_60s"}
MAT_NUMS = list(MAT_VAR)
MAT_CONT = [n for n in MAT_NUMS if n != 6]
COL = {n: f"mat{n}_{MAT_VAR[n]}" for n in MAT_NUMS}
LABELS = (30, 60, 120)
CELLS = [0]   # 反証者が新しく切ったセルの数

def cell(k=1):
    CELLS[0] += k

def say(*a):
    print(*a)

def hr(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# ---------------------------------------------------------------- 統計の道具
def mean_se_cluster(vals, days):
    ok = np.isfinite(vals); v = vals[ok]; d = np.asarray(days)[ok]
    n = int(v.size)
    if n == 0: return NAN, NAN, 0, 0
    m = float(v.mean()); acc = defaultdict(float)
    for x, dd in zip(v.tolist(), d.tolist()): acc[dd] += x - m
    g = len(acc)
    se = math.sqrt(sum(s*s for s in acc.values()))/n*math.sqrt(g/(g-1)) if g > 1 else NAN
    return m, se, n, g

def day_eq_mean(vals, days):
    ok = np.isfinite(vals); v, d = vals[ok], np.asarray(days)[ok]
    if v.size == 0: return NAN
    acc = defaultdict(list)
    for x, dd in zip(v.tolist(), d.tolist()): acc[dd].append(x)
    ms = [sum(xs)/len(xs) for xs in acc.values()]
    return float(sum(ms)/len(ms))

def qs(v, ps):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if v.size == 0: return [NAN]*len(ps)
    return [float(x) for x in np.percentile(v, ps)]

def band_of(v, cuts):
    v = np.asarray(v, float)
    k = np.searchsorted(cuts, v, side="right") + 1
    return np.where(np.isfinite(v), k, -1)

def branch_stats(pnl, days):
    p25, p50, p75 = qs(pnl, [25, 50, 75])
    m, se, n, g = mean_se_cluster(pnl, days)
    fin = np.isfinite(pnl)
    neg = float((pnl[fin] < 0).mean()) if fin.any() else NAN
    return dict(n=n, days=g, med=p50, p25=p25, p75=p75, neg=neg,
                deq=day_eq_mean(pnl, days), se=se, mean=m)

def fmt(d):
    return (f"n={d['n']} 日{d['days']} 中央値{d['med']:+.4f} p25{d['p25']:+.4f} "
            f"p75{d['p75']:+.4f} 負{d['neg']:.4f} 日等重み{d['deq']:+.4f} "
            f"SE{d['se']:.4f}")

def cmp2(name, mine, theirs, tol=5e-4):
    ok = (isinstance(mine,float) and isinstance(theirs,float)
          and (abs(mine-theirs) <= tol or (mine!=mine and theirs!=theirs)))
    if not isinstance(mine,float): ok = (mine == theirs)
    say(f"  {'一致' if ok else '★不一致'} {name}: 反証者={mine} / 委任先={theirs}")
    return ok

# ---------------------------------------------------------------- 読み込み
hr("0. 読み込み")
summ = json.loads((OUT/"summary.json").read_text())
df = pd.read_csv(OUT/"rows_continue.csv.gz",
                 dtype={c:str for c in ("kind","print_id","day","side","half",
                                        "bundle_id",COL[6],"q7_matched_print_id")})
for c in df.columns:
    if c not in ("kind","print_id","day","side","half","bundle_id",COL[6],
                 "q7_matched_print_id"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
say(f"rows_continue 全行 {len(df)}")
pr = df[df.kind=="print"].reset_index(drop=True)
q7 = df[df.kind=="q7_candidate"].reset_index(drop=True)
say(f"プリント {len(pr)} / Q7 候補 {len(q7)}")
fh = pr[pr.half=="前半"]; bh = pr[pr.half=="後半"].reset_index(drop=True)
say(f"前半 {len(fh)} / 後半 {len(bh)}")
q2t = pd.read_csv(OUT/"q2.csv"); q4t = pd.read_csv(OUT/"q4.csv")
q5t = pd.read_csv(OUT/"q5.csv"); q7t = pd.read_csv(OUT/"q7.csv")
q1t = pd.read_csv(OUT/"q1.csv"); q0t = pd.read_csv(OUT/"q0.csv")

# ---------------------------------------------------------------- §0-1 基準率
hr("§0-1 基準率(前半 / 後半 × 30/60/120 秒)")
base = {}
for h in ("前半","後半"):
    for L in LABELS:
        v = float(pr.loc[pr.half==h, f"label_{L}"].mean()); base[(h,L)] = v; cell()
        cmp2(f"基準率 {h} {L}s", round(v,6), round(summ["基準率(半期別)"][h][str(L)],6))
base_fh60 = base[("前半",60)]

# ---------------------------------------------------------------- §0-2 切り値
hr("§0-2 前半だけから切り値が作られているか(再計算)")
cuts = {}
for n in MAT_CONT:
    v = pd.to_numeric(fh[COL[n]], errors="coerce").to_numpy(float)
    v = v[np.isfinite(v)]
    cuts[n] = np.quantile(v, [i/N_BANDS for i in range(1,N_BANDS)])
ok_all = True
for n in MAT_CONT:
    theirs = np.array(summ["前半の材料の切り値(10分位、材料6を除く)"][str(n)])
    same = np.allclose(cuts[n], theirs, rtol=0, atol=1e-6)
    ok_all &= same
    if not same: say(f"  ★不一致 材料{n}: {cuts[n]} vs {theirs}")
say(f"  {'全 13 材料で一致(切り値は前半だけから出ている)' if ok_all else '★不一致あり'}")
cell(13)
cuts_all = {n: np.quantile(pd.to_numeric(pr[COL[n]],errors='coerce')
                           .to_numpy(float)[np.isfinite(pd.to_numeric(pr[COL[n]],
                            errors='coerce').to_numpy(float))],
                           [i/N_BANDS for i in range(1,N_BANDS)]) for n in MAT_CONT}
diff = [n for n in MAT_CONT if not np.allclose(cuts[n], cuts_all[n], rtol=0, atol=1e-9)]
say(f"  456 日全部で切った場合と切り値が違う材料: {len(diff)}/13 本 {diff}")
say("  → 前半だけから出ている(全部で切ったら別の値になる材料が {} 本ある)".format(len(diff)))

# 帯付け
def add_bands(d, cuts):
    d = d.copy()
    for n in MAT_CONT: d[f"band_{n}"] = band_of(d[COL[n]].to_numpy(float), cuts[n])
    TB = ["UTC 00–06","UTC 06–12","UTC 12–18","UTC 18–24"]
    cb = pd.Series(-1, index=d.index, dtype=int)
    for i, nm in enumerate(TB, start=1): cb[d[COL[6]]==nm] = i
    d["band_6"] = cb
    return d
pr = add_bands(pr, cuts)
fh = pr[pr.half=="前半"]; bh = pr[pr.half=="後半"].reset_index(drop=True)

# ---------------------------------------------------------------- 規則を再構成
hr("§0-3 規則の「続く」の帯が前半だけから作られているか(再計算)")
rule_bands, rule_set, spread = {}, {}, {}
for n in MAT_NUMS:
    r = {}
    for b, g in fh.groupby(f"band_{n}"):
        r[int(b)] = (float(g["label_60"].mean()), int(len(g)))
    rule_bands[n] = r
    rule_set[n] = {b:(rt>base_fh60) for b,(rt,c) in r.items() if b>=1 and c>0}
    rates = [rt for b,(rt,c) in r.items() if b>=1 and c>0]
    spread[n] = (max(rates)-min(rates)) if len(rates)>=2 else -1.0
top3 = sorted(MAT_NUMS, key=lambda n: spread[n], reverse=True)[:3]
say(f"  上位3材料(帯ごとの続く割合の広がり順)= {top3} / 委任先 {summ['上位3材料(組の規則)']['番号']}")
say("  広がり: " + ", ".join(f"{n}:{spread[n]:.4f}" for n in
    sorted(MAT_NUMS, key=lambda n: spread[n], reverse=True)))
cell(14)
for n in (1,14,5,4):
    say(f"  規則{n} の「続く」と言う帯 = {sorted(b for b,v in rule_set[n].items() if v)}")

def apply_rule(d, n):
    return d[f"band_{n}"].map(lambda b: rule_set[n].get(int(b)))
def apply_combo(d):
    def f(row):
        vs = []
        for n in top3:
            r = rule_bands[n].get(int(row[f"band_{n}"]))
            if r is None: return None
            vs.append(r[0])
        return (sum(vs)/len(vs)) > base_fh60
    return d.apply(f, axis=1)

judg = {f"rule_{n}": apply_rule(bh, n) for n in MAT_NUMS}
judg["rule_combo"] = apply_combo(bh)
judg["all_continue"] = pd.Series(True, index=bh.index)
judg["all_stop"] = pd.Series(False, index=bh.index)
judg["perfect"] = (bh["label_60"]==1)

# ---------------------------------------------------------------- §0-4 Q2
hr("§0-4 Q2 規則の的中率(後半、h=60。rule_1 / 14 / 5 / 4 / combo)")
def rule_metrics(pred, y):
    has = pred.notna(); p = pred[has].astype(bool); yy = y[has].astype(float)
    n = int(has.sum())
    tp = int(((p)&(yy==1)).sum()); fp = int(((p)&(yy==0)).sum())
    fn = int(((~p)&(yy==1)).sum()); tn = int(((~p)&(yy==0)).sum())
    return dict(n=n, acc=(tp+tn)/n if n else NAN,
                prec=tp/(tp+fp) if tp+fp else NAN,
                rec=tp/(tp+fn) if tp+fn else NAN,
                said=int(p.sum()), undrawn=int((~has).sum()),
                tp=tp, fp=fp, fn=fn, tn=tn)
q2_check = {}
for key in ("rule_1","rule_14","rule_5","rule_4","rule_combo","rule_12","rule_9","rule_15"):
    m = rule_metrics(judg[key], bh["label_60"]); q2_check[key] = m
    row = q2t[(q2t["規則"].str.startswith(key+"(")) & (q2t["h(秒)"]==60)]
    say(f"\n {key}")
    if len(row):
        r = row.iloc[0]
        cmp2("n", m["n"], int(r["n"])); cmp2("的中率", round(m["acc"],6), round(float(r["的中率"]),6))
        cmp2("適合率", round(m["prec"],6), round(float(r["適合率"]),6))
        cmp2("再現率", round(m["rec"],6), round(float(r["再現率"]),6))
        cmp2("「続く」と言った件数", m["said"], int(r["「続く」と言った件数"]))
    say(f"   内訳 TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} 引けず{m['undrawn']}")
    cell(5)

# ---------------------------------------------------------------- §0-5 Q4 主格子
hr("§0-5 Q4 主格子(t0+1s → 60s)の 2 枝(再計算)")
def pnl_for(d, pred, branch_bool, e=1, h=60):
    s = d["dir_sign"].astype(float)
    entry = d[f"p_entry_{e}"]; ex = d[f"p_exit_e{e}_h{h}"]
    dirn = s if branch_bool else -s
    v = (dirn*(ex-entry)/entry*1e4)
    return v.where(pred==branch_bool, NAN).to_numpy(float)
q4_check = {}
for key in ("all_continue","all_stop","perfect","rule_combo","rule_14"):
    for br, bb in (("続く",True),("止まる",False)):
        st = branch_stats(pnl_for(bh, judg[key], bb), bh["day"].to_numpy(object))
        q4_check[(key,br)] = st
        row = q4t[(q4t["判断"]==key)&(q4t["枝"]==br)&(q4t["entry_s"]==1)&(q4t["hold_s"]==60)]
        say(f"\n {key} / {br}: {fmt(st)}")
        if len(row) and st["n"]>0:
            r = row.iloc[0]
            cmp2("n", st["n"], int(r["n"]))
            cmp2("中央値", round(st["med"],5), round(float(r["中央値"]),5))
            cmp2("p25", round(st["p25"],5), round(float(r["p25"]),5))
            cmp2("p75", round(st["p75"],5), round(float(r["p75"]),5))
            cmp2("負の割合", round(st["neg"],5), round(float(r["負の割合"]),5))
            cmp2("日等重み平均", round(st["deq"],5), round(float(r["日等重み平均"]),5))
            cmp2("日クラスタSE", round(st["se"],5), round(float(r["日クラスタSE"]),5))
        cell(7)

# ---------------------------------------------------------------- §0-6 Q7 の 2 本
hr("§0-6 Q7 の 2 本(rule_9 / rule_15、対照側)")
for n in (9, 15):
    pred = q7[f"q7_band{n}"].map(lambda b: rule_set[n].get(int(b)) if pd.notna(b) else None)
    said = float((pred==True).sum())/max(int(pred.notna().sum()),1)
    for br, bb in (("続く",True),("止まる",False)):
        st = branch_stats(pnl_for(q7, pred, bb), q7["day"].to_numpy(object))
        row = q7t[(q7t["規則"]==f"rule_{n}")&(q7t["枝"]==br)]
        say(f"\n rule_{n} / {br}: {fmt(st)} 続くと言った割合 {said:.6f}")
        if len(row):
            r = row.iloc[0]
            cmp2("n", st["n"], int(r["n"]))
            cmp2("中央値", round(st["med"],5), round(float(r["中央値"]),5))
            cmp2("負の割合", round(st["neg"],5), round(float(r["負の割合"]),5))
            cmp2("日等重み平均", round(st["deq"],5), round(float(r["日等重み平均"]),5))
            cmp2("続くと言った割合", round(said,6), round(float(r["続くと言った割合"]),6))
        cell(6)

# ---------------------------------------------------------------- §0-7 Q1 の帯
hr("§0-7 Q1 の帯ごとの続く割合(材料 1・14・4・5、前半 / 後半)")
for n in (1,14,4,5):
    say(f"\n 材料 {n}({MAT_VAR[n]})")
    for b in sorted(set(pr[f"band_{n}"].unique())):
        if b < 1: continue
        f_ = fh[fh[f"band_{n}"]==b]; b_ = bh[bh[f"band_{n}"]==b]
        rf = float(f_["label_60"].mean()) if len(f_) else NAN
        rb = float(b_["label_60"].mean()) if len(b_) else NAN
        row = q1t[(q1t["材料"]==n)&(q1t["帯"]==b)]
        mark = ""
        if len(row):
            r = row.iloc[0]
            okf = abs(rf-float(r["前半 続く割合"]))<5e-5 and int(r["前半 n"])==len(f_)
            okb = abs(rb-float(r["後半 続く割合"]))<5e-5 and int(r["後半 n"])==len(b_)
            mark = "一致" if (okf and okb) else "★不一致"
        say(f"  帯{b}: 前半 n={len(f_)} {rf:.4f} / 後半 n={len(b_)} {rb:.4f}  {mark}"
            f"  {'続くと言う' if rule_set[n].get(b) else '止まると言う'}")
        cell(4)

# ---------------------------------------------------------------- 2. 分母と選択
hr("2. 欠測と分母(材料 8・10・12)")
metrics_missing = set(json.loads((OUT/"stage1_notes.json").read_text())["metrics_days_missing"])
say(f"metrics 欠測日 {len(metrics_missing)} 日")
for n in (8,10,12):
    miss = pr[COL[n]].isna()
    say(f"\n 材料{n}: 欠測 {int(miss.sum())}/{len(pr)} = {miss.mean():.4f}")
    inm = pr["day"].isin(metrics_missing)
    say(f"   metrics 欠測日にあるプリント {int(inm.sum())} 件、"
        f"そのうち材料{n} 欠測 {int((miss&inm).sum())} 件 "
        f"({(miss&inm).sum()/max(int(inm.sum()),1):.4f})")
    say(f"   metrics のある日でも欠測 {int((miss&~inm).sum())} 件 "
        f"({(miss&~inm).sum()/max(int((~inm).sum()),1):.4f})")
    say(f"   後半で引ける件数 {int((~bh[COL[n]].isna()).sum())} / {len(bh)}")
    say(f"   引ける行の基準率 {float(bh.loc[~bh[COL[n]].isna(),'label_60'].mean()):.4f} "
        f"vs 後半全体 {float(bh['label_60'].mean()):.4f}")
    cell(6)
say("\n rule_12 の正体(欠測の構造):")
m12_na = pr[COL[12]].isna(); m1_zero = (pr[COL[1]]==0)
say(f"   材料12 が欠測 ⟺ 材料1 == 0 か: 一致 {int((m12_na==m1_zero).sum())}/{len(pr)}")
say(f"   材料12 が引ける行数 {int((~m12_na).sum())}、材料1>=1 の行数 {int((~m1_zero).sum())}")
b12 = sorted(b for b,v in rule_set[12].items() if v)
say(f"   規則12 が「続く」と言う帯 = {b12}(全 {len([b for b in rule_set[12]])} 帯中)")
say(f"   → 規則12 は引ける行すべてに「続く」と言う(再現率 1.0 の出所)")
say(f"   rule_1 の「続く」集合 == rule_12 の引ける集合 か: "
    f"{int(((judg['rule_1']==True) == (~bh[COL[12]].isna())).sum())}/{len(bh)}")
say(f"   ラベル 1 の件数 {int((pr['label_60']==1).sum())} / 材料1>=1 の件数 {int((~m1_zero).sum())}"
    " (同じ側の前後の対応で構造的にほぼ一致する)")
cell(6)

# ---------------------------------------------------------------- 3. ラベルと損益のずれ
hr("3. ラベルと損益のずれ(束の位置の排他 4 群で分解)")
ex5 = pd.read_csv(EX5, usecols=["kind","print_id","bundle_pos","bundle_pos_single"],
                  dtype=str)
ex5 = ex5[ex5.kind=="print"][["print_id","bundle_pos","bundle_pos_single"]]
def grp(r):
    if r.bundle_pos == "束の外": return "束の外"
    if r.bundle_pos_single == "1": return "単発"
    return {"最初":"多件の最初","途中":"途中","最後":"多件の最後"}[r.bundle_pos]
ex5["群"] = ex5.apply(grp, axis=1)
say(ex5["群"].value_counts().to_string())
bh2 = bh.merge(ex5[["print_id","群"]], on="print_id", how="left")
assert bh2["群"].notna().all()
say(f"\n 後半の群の内訳:\n{bh2['群'].value_counts().to_string()}")
cell(5)
s = bh2["dir_sign"].astype(float)
raw = (s*(bh2["p_exit_e1_h60"]-bh2["p_entry_1"])/bh2["p_entry_1"]*1e4)
bh2["pnl_long"] = raw     # 清算の向きに乗ったときの 1 件あたり bp
say("\n 後半・t0+1s→60s・清算の向きに乗った損益(群ごと):")
for g, gg in bh2.groupby("群"):
    st = branch_stats(gg["pnl_long"].to_numpy(float), gg["day"].to_numpy(object))
    say(f"   {g:8s} {fmt(st)} 平均{st['mean']:+.4f}")
    cell(7)
say("\n 規則が「続く」と言った集合の中身(群 × ラベル)と、その群の損益:")
for key in ("rule_combo","rule_14","rule_1"):
    pred = judg[key]
    sub = bh2[pred.reindex(bh2.index)==True]
    say(f"\n  {key} の「続く」集合 n={len(sub)}")
    for g, gg in sub.groupby("群"):
        st = branch_stats(gg["pnl_long"].to_numpy(float), gg["day"].to_numpy(object))
        say(f"    {g:8s} n={len(gg)} ({len(gg)/len(sub):.3f}) ラベル1割合"
            f"{gg['label_60'].mean():.3f} 中央値{st['med']:+.3f} 平均{st['mean']:+.3f} "
            f"日等重み{st['deq']:+.3f}")
        cell(6)
    # 当たった件 / 外した件の損益
    for lab, name in ((1,"当たり(label=1)"),(0,"外れ(label=0)")):
        gg = sub[sub.label_60==lab]
        st = branch_stats(gg["pnl_long"].to_numpy(float), gg["day"].to_numpy(object))
        say(f"    {name} n={len(gg)} 中央値{st['med']:+.3f} 平均{st['mean']:+.3f}")
        cell(3)
say("\n 止まる枝も同じ分解(rule_combo):")
sub = bh2[judg["rule_combo"].reindex(bh2.index)==False]
for g, gg in sub.groupby("群"):
    st = branch_stats((-gg["pnl_long"]).to_numpy(float), gg["day"].to_numpy(object))
    say(f"    {g:8s} n={len(gg)} ({len(gg)/len(sub):.3f}) ラベル1割合"
        f"{gg['label_60'].mean():.3f} 中央値{st['med']:+.3f} 平均{st['mean']:+.3f}")
    cell(5)

hr("3b. 「値段の続き」(value_continuation_60)をラベルにしたとき")
vc = pr["value_continuation_60"]
say(f" value_continuation_60 の欠測 {int(vc.isna().sum())}")
for h in ("前半","後半"):
    say(f"  {h} の「値段の続き」割合 {float(pr.loc[pr.half==h,'value_continuation_60'].mean()):.4f}"
        f"(清算のラベル 60s は {base[(h,60)]:.4f})")
    cell(2)
say(f"  清算のラベル と 値段の続き の一致率(後半) "
    f"{float((bh['label_60']==bh['value_continuation_60']).mean()):.4f}")
cell()
# 前半で「値段の続き」から規則を作り直す
base_fh_vc = float(fh["value_continuation_60"].mean())
rs_vc, rb_vc, sp_vc = {}, {}, {}
for n in MAT_NUMS:
    r = {int(b):(float(g["value_continuation_60"].mean()), int(len(g)))
         for b,g in fh.groupby(f"band_{n}")}
    rb_vc[n] = r
    rs_vc[n] = {b:(rt>base_fh_vc) for b,(rt,c) in r.items() if b>=1 and c>0}
    rates = [rt for b,(rt,c) in r.items() if b>=1 and c>0]
    sp_vc[n] = (max(rates)-min(rates)) if len(rates)>=2 else -1.0
top3_vc = sorted(MAT_NUMS, key=lambda n: sp_vc[n], reverse=True)[:3]
say(f"  値段の続きを基準にした前半の基準率 {base_fh_vc:.4f}、上位3材料 {top3_vc}")
cell(2)
def apply_rule_vc(d, n): return d[f"band_{n}"].map(lambda b: rs_vc[n].get(int(b)))
say("\n  (a) 規則はそのまま(清算のラベルで作った規則)、当てる先だけ「値段の続き」に替える:")
for key in ("rule_1","rule_14","rule_4","rule_5","rule_combo"):
    m = rule_metrics(judg[key], bh["value_continuation_60"])
    say(f"    {key}: n={m['n']} 的中率{m['acc']:.4f} 適合率{m['prec']:.4f} "
        f"再現率{m['rec']:.4f}(後半の基準 {float(bh['value_continuation_60'].mean()):.4f})")
    cell(4)
say("\n  (b) 規則も「値段の続き」で作り直す(前半で作り後半で測る):")
for n in (1,14,4,5,15,9):
    pred = apply_rule_vc(bh, n)
    m = rule_metrics(pred, bh["value_continuation_60"])
    st_c = branch_stats(pnl_for(bh, pred, True), bh["day"].to_numpy(object))
    st_s = branch_stats(pnl_for(bh, pred, False), bh["day"].to_numpy(object))
    say(f"    rule_{n}: 的中率{m['acc']:.4f} 適合率{m['prec']:.4f} 再現率{m['rec']:.4f} "
        f"| 続く枝 {fmt(st_c)} | 止まる枝 {fmt(st_s)}")
    cell(10)
# perfect on value continuation
pv = (bh["value_continuation_60"]==1)
st_c = branch_stats(pnl_for(bh, pv, True), bh["day"].to_numpy(object))
st_s = branch_stats(pnl_for(bh, pv, False), bh["day"].to_numpy(object))
say(f"    perfect(値段の続きを事後に知る): 続く枝 {fmt(st_c)} | 止まる枝 {fmt(st_s)}")
cell(14)

# ---------------------------------------------------------------- 4. 上限との差
hr("4. 完全な判断(perfect)と規則の差はどこで失われるか")
say(" 後半・主格子。perfect は label_60 を事後に知る。")
for key in ("perfect","rule_combo","rule_14","rule_1"):
    pred = judg[key]
    for br, bb in (("続く",True),("止まる",False)):
        st = branch_stats(pnl_for(bh, pred, bb), bh["day"].to_numpy(object))
        if st["n"]: say(f"   {key:12s} {br}: {fmt(st)} 平均{st['mean']:+.4f}")
        cell(2)
say("\n 2x2(規則 rule_combo の判断 × 事後のラベル)ごとの 1 件あたり損益(清算の向きに乗った値):")
pc_ = judg["rule_combo"].reindex(bh2.index)
for p in (True, False):
    for l in (1, 0):
        gg = bh2[(pc_==p)&(bh2.label_60==l)]
        st = branch_stats(gg["pnl_long"].to_numpy(float), gg["day"].to_numpy(object))
        say(f"   予測{'続く' if p else '止まる'} × 実際{'続く' if l else '止まる'}: "
            f"n={len(gg)} 中央値{st['med']:+.4f} 平均{st['mean']:+.4f} "
            f"日等重み{st['deq']:+.4f}")
        cell(4)
say("\n perfect の 2 枝の中身(群の割合):")
for l, name in ((1,"perfect 続く枝(label=1)"),(0,"perfect 止まる枝(label=0)")):
    gg = bh2[bh2.label_60==l]
    say(f"   {name} n={len(gg)}: " + ", ".join(
        f"{g}{len(x)/len(gg):.3f}" for g,x in gg.groupby('群')))
    cell(5)

# ---------------------------------------------------------------- 5. 逆張りの枝
hr("5. 逆張りの枝(all_stop・規則の止まる枝・2 件目以降を逆張り)")
st_all = branch_stats(pnl_for(bh, judg["all_stop"], False), bh["day"].to_numpy(object))
say(f" all_stop(全部逆張り) {fmt(st_all)} 平均{st_all['mean']:+.4f}")
cell(7)
for key in ("rule_combo","rule_14","rule_1","rule_5","rule_4"):
    st = branch_stats(pnl_for(bh, judg[key], False), bh["day"].to_numpy(object))
    say(f"   {key} 止まる枝 {fmt(st)} 平均{st['mean']:+.4f}")
    cell(7)
# 2 件目以降を逆張り = mat1>=1 を全部逆張り
sec = (bh[COL[1]]>=1)
pnl_sec = (-(bh["dir_sign"].astype(float))*(bh["p_exit_e1_h60"]-bh["p_entry_1"])
           /bh["p_entry_1"]*1e4).where(sec, NAN).to_numpy(float)
st_sec = branch_stats(pnl_sec, bh["day"].to_numpy(object))
say(f"\n 2 件目以降(材料1>=1)を全部逆張り: {fmt(st_sec)} 平均{st_sec['mean']:+.4f}")
first = (bh[COL[1]]==0)
pnl_1st = (-(bh["dir_sign"].astype(float))*(bh["p_exit_e1_h60"]-bh["p_entry_1"])
           /bh["p_entry_1"]*1e4).where(first, NAN).to_numpy(float)
st_1st = branch_stats(pnl_1st, bh["day"].to_numpy(object))
say(f" 1 件目(材料1==0)を全部逆張り:     {fmt(st_1st)} 平均{st_1st['mean']:+.4f}")
cell(14)
say("\n 探索段 5 との突き合わせ(探索段 5 は 456 日・p0 起点・r(60)、ここは後半 228 日・"
    "t0+1s 入り→60 秒):")
for nm, msk in (("1 件目(材料1==0)", first), ("2 件目以降(材料1>=1)", sec)):
    gg = bh2[msk.reindex(bh2.index).fillna(False).to_numpy()]
    st = branch_stats(gg["pnl_long"].to_numpy(float), gg["day"].to_numpy(object))
    say(f"   {nm}: n={st['n']} 清算の向きの平均 {st['mean']:+.4f} ± {st['se']:.4f} "
        f"中央値 {st['med']:+.4f}")
    cell(4)
say("\n 日ごとの分布(後半 228 日、主格子):")
def daily(pnl, days):
    v = np.asarray(pnl,float); ok=np.isfinite(v)
    d = pd.Series(v[ok]).groupby(np.asarray(days)[ok]).sum()
    tot = float(d.sum()); top5 = float(d.sort_values(ascending=False).head(5).sum())
    return dict(days=int(d.size), neg=float((d<0).mean()),
                top5=top5/tot if tot else NAN, total=tot,
                med=float(d.median()))
for nm, v in (("all_stop", pnl_for(bh, judg["all_stop"], False)),
              ("rule_combo 止まる枝", pnl_for(bh, judg["rule_combo"], False)),
              ("2 件目以降を逆張り", pnl_sec),
              ("1 件目を逆張り", pnl_1st),
              ("all_continue", pnl_for(bh, judg["all_continue"], True))):
    d = daily(v, bh["day"].to_numpy(object))
    say(f"   {nm:22s} 日数{d['days']} 負の日{d['neg']:.4f} "
        f"上位5日/全体{d['top5']:+.4f} 合計{d['total']:+.1f}bp 日中央値{d['med']:+.4f}")
    cell(5)
# 上位 5 日の日付
v = pnl_sec; ok=np.isfinite(v)
dser = pd.Series(v[ok]).groupby(bh["day"].to_numpy(object)[ok]).sum().sort_values(ascending=False)
say(f"   2 件目以降を逆張り 上位5日: " + ", ".join(f"{d}:{x:+.0f}" for d,x in dser.head(5).items()))
say(f"   同 下位5日: " + ", ".join(f"{d}:{x:+.0f}" for d,x in dser.tail(5).items()))
cell(10)

# ---------------------------------------------------------------- 6. 保有と入る時点
hr("6. 保有期間(30/60/300)と入る時点(t0+1/3/5 秒)")
for key in ("all_continue","all_stop","perfect","rule_combo"):
    say(f"\n {key}")
    for e in (1,3,5):
        line = []
        for h in (30,60,300):
            for br, bb in (("続",True),("止",False)):
                st = branch_stats(pnl_for(bh, judg[key], bb, e, h), bh["day"].to_numpy(object))
                if st["n"]: line.append(f"h{h}{br} 中{st['med']:+.2f}/日等{st['deq']:+.2f}")
                cell(2)
        say(f"   e={e}s: " + " | ".join(line))
say("\n perfect の続く枝が h=300 で負になる中身(群ごと、後半):")
for h in (30,60,300):
    gg = bh2[bh2.label_60==1]
    v = (gg["dir_sign"].astype(float)*(gg[f"p_exit_e1_h{h}"]-gg["p_entry_1"])
         /gg["p_entry_1"]*1e4)
    say(f"   h={h}: 全体 中央値{float(v.median()):+.3f} 平均{float(v.mean()):+.3f}")
    for g, x in gg.groupby("群"):
        vv = (x["dir_sign"].astype(float)*(x[f"p_exit_e1_h{h}"]-x["p_entry_1"])
              /x["p_entry_1"]*1e4)
        say(f"      {g:8s} n={len(x)} 中央値{float(vv.median()):+.3f} 平均{float(vv.mean()):+.3f}")
        cell(3)

# ---------------------------------------------------------------- 7. Q7
hr("7. Q7 の対照(取れた割合・帯の偏り・プリント側との差)")
mb = json.loads((OUT/"stage2_notes.json").read_text())["miss_by_band"]
got = sum(v[0] for v in mb.values()); tot = sum(v[1] for v in mb.values())
say(f" 取れた合計 {got} / 対象合計 {tot} = {got/tot:.4f}")
say(f" 対象合計 {tot} と 後半プリント {len(bh)} の差 {len(bh)-tot} 件"
    f"(材料15 か 9 が引けない行)")
say(f" 52,000 を分母にすると {got/52000:.4f}(Q7 は後半だけで作るので分母が違う)")
cell(4)
say("\n 材料15 の帯ごと(委任先の q7 表と同じ数え方):")
agg = defaultdict(lambda: [0,0])
for k,(g,t) in mb.items():
    agg[int(k.split("_")[0])][0]+=g; agg[int(k.split("_")[0])][1]+=t
for b in range(1,11):
    g,t = agg[b]
    row = q7t[q7t["材料15の帯"]==b]
    ok = len(row) and abs(g/t - float(row.iloc[0]["取れた割合"]))<5e-5
    say(f"   帯{b}: 対象{t} 取れた{g} {g/t:.4f} {'一致' if ok else '★不一致'}")
    cell(3)
say("\n 材料9 の帯ごと(反証者が新しく切った):")
agg9 = defaultdict(lambda: [0,0])
for k,(g,t) in mb.items():
    agg9[int(k.split("_")[1])][0]+=g; agg9[int(k.split("_")[1])][1]+=t
for b in range(1,11):
    g,t = agg9[b]
    say(f"   帯{b}: 対象{t} 取れた{g} {g/t:.4f}")
    cell(3)
say("\n 取れた候補の帯の分布 vs 対象のプリントの帯の分布(材料15):")
for b in range(1,11):
    g,t = agg[b]
    say(f"   帯{b}: プリント側 {t/tot:.4f} → 対照側 {g/got:.4f} "
        f"(差 {g/got - t/tot:+.4f})")
    cell(3)
say("\n Q7 のラベル(値段の続き)とプリント側の比較:")
say(f"   対照側の「値段の続き」割合 {float(q7['value_continuation_60'].mean()):.4f} "
    f"(欠測 {int(q7['value_continuation_60'].isna().sum())})")
say(f"   後半プリント側の「値段の続き」割合 {float(bh['value_continuation_60'].mean()):.4f}")
cell(2)
for n in (9,15):
    pred = q7[f"q7_band{n}"].map(lambda b: rs_vc[n].get(int(b)) if pd.notna(b) else None)
    m = rule_metrics(pred, q7["value_continuation_60"])
    pred_p = apply_rule_vc(bh, n)
    mp = rule_metrics(pred_p, bh["value_continuation_60"])
    say(f"   rule_{n}(値段の続きで作り直した規則): 対照側 的中率{m['acc']:.4f} "
        f"(n={m['n']}) / プリント側 的中率{mp['acc']:.4f}(n={mp['n']})")
    cell(4)
say("\n Q7 候補が 1 プリントに 1 件取れているか(重複):")
say(f"   対照候補の時刻 {q7['ts_ms'].nunique()} 種 / {len(q7)} 件")
say(f"   対照候補の出口が引けなかった件数 {int(q7['p_exit_e1_h60'].isna().sum())}")
cell(2)

# ---------------------------------------------------------------- 8. データ妥当性
hr("8. データ妥当性")
say(" (a) p_entry_1 は t0+1 秒『以前』の最後の約定(at_or_before)。p0 と同じ値の割合:")
same = (pr["p_entry_1"]==pr["p0"])
say(f"   p_entry_1 == p0 : {int(same.sum())}/{len(pr)} = {same.mean():.4f}")
for e in (3,5):
    s2 = (pr[f"p_entry_{e}"]==pr["p0"])
    say(f"   p_entry_{e} == p0 : {int(s2.sum())}/{len(pr)} = {s2.mean():.4f}")
    cell(2)
say(f"   p_entry_1 == p_entry_3 : {(pr['p_entry_1']==pr['p_entry_3']).mean():.4f}")
cell(3)
say(" (b) 出口の欠測:")
for c in ["p_entry_1","p_entry_3","p_entry_5"]+[f"p_exit_e{e}_h{h}" for e in (1,3,5) for h in (30,60,300)]:
    say(f"   {c}: 欠測 {int(pr[c].isna().sum())}({pr[c].isna().mean():.5f})")
    cell()
say(" (c) 重なり(同じ 60 秒に入るプリント数、後半):")
ts = np.sort(bh["ts_ms"].to_numpy(np.int64))
lo = np.searchsorted(ts, ts-60_000, "left"); hi = np.searchsorted(ts, ts+60_000, "right")
ov = hi-lo
say(f"   自分を含む ±60 秒のプリント数: 中央値{np.median(ov):.0f} 平均{ov.mean():.2f} "
    f"p90 {np.percentile(ov,90):.0f} 最大{ov.max()}")
say(f"   ±60 秒に自分しかいない割合 {float((ov==1).mean()):.4f}")
blocks = len(np.unique(ts//60_000))
say(f"   60 秒の区切りに落とした独立な枠の数 {blocks}(n={len(ts)}、1 枠あたり "
    f"{len(ts)/blocks:.2f} 件)")
say(f"   後半の日数 {bh['day'].nunique()}、1 日あたり {len(bh)/bh['day'].nunique():.1f} 件")
cell(6)
say(" (d) 材料が p0 に依るか(試験が変えていない入力を反証者が変えて測る):")
sys.path.insert(0, str(ROOT/"scripts"))
import importlib.util as _iu
_sp = _iu.spec_from_file_location("sc", ROOT/"scripts"/"o3c_signal_continue.py")
sc = _iu.module_from_spec(_sp); _sp.loader.exec_module(sc)
def probe_p0(prev_gap_ms):
    day = "2024-01-02"; ts = sc.day_start_ms(day) + 3_600_000
    rows = [{"print_id":"cur","day":day,"side":"SELL","ts_ms":ts,"t0_ms":ts,
             "p0":30003.6,"notional":500_000.0,"dist_node_bp":-12.5,
             "oi_covered":0,"bundle_id":""}]
    if prev_gap_ms is not None:
        rows.append({"print_id":"prev","day":day,"side":"SELL","ts_ms":ts-prev_gap_ms,
                     "t0_ms":ts-prev_gap_ms,"p0":29990.0,"notional":200_000.0,
                     "dist_node_bp":0.0,"oi_covered":0,"bundle_id":""})
    out = []
    for p0v in (30003.6, 31003.6):
        rr = [dict(r) for r in rows]; rr[0]["p0"] = p0v
        pcx = None
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cols = ["kind","print_id","day","side","ts_ms","t0_ms","p0","notional",
                    "dist_node_bp","oi_covered","bundle_id"]
            d = pd.DataFrame([{c:r.get(c,"") for c in cols} for r in rr]); d["kind"]="print"
            p = Path(td)/"r.csv.gz"; d.to_csv(p, index=False, compression="gzip")
            pcx = sc.PrintsCSV(p)
        nbx = sc.same_side_neighbors(pcx)
        i = int(np.flatnonzero(pcx.print_id=="cur")[0])
        times = np.arange(ts-4_000_000, ts+400_001, 1000, dtype=np.int64)
        prices = 30000.0 + 0.001*(times-(ts-4_000_000))
        qv = np.ones(times.size); mk = (np.arange(times.size)%2==0)
        _row, mv = sc.compute_print_row(day, pcx, i, nbx, times, prices, qv, mk,
                                        {"t_all":np.zeros(0,dtype=np.int64)}, None,
                                        np.zeros(0,dtype=np.int64), np.zeros(0),
                                        np.zeros(0), np.zeros(0,dtype=np.int64),
                                        np.zeros(0), "前半")
        out.append(mv)
    ch = [n for n in sc.MAT_NUMS
          if not (out[0][n]==out[1][n] or (isinstance(out[0][n],float)
                  and out[0][n]!=out[0][n] and out[1][n]!=out[1][n]))]
    return ch, out
ch1, o1 = probe_p0(30_000)
say(f"   直前の同じ側が 30 秒前(材料1>=1)のとき、p0 を変えて値が変わる材料: {ch1}")
ch2, o2 = probe_p0(None)
say(f"   直前の同じ側が無い(材料1==0)のとき、p0 を変えて値が変わる材料: {ch2}")
if 4 in ch2:
    say(f"      材料4: p0=30003.6 -> {o2[0][4]} / p0=31003.6 -> {o2[1][4]}")
cell(4)
say("   行データでの裏取り(材料1==0 の行で 材料4 が −k(bp) と一致するか):")
k_bp = pr["k_ticks"]*0.1/pr["p0"]*1e4
m1z = (pr[COL[1]]==0)
# k_ticks は絶対値なので符号を戻す: 材料4 = s*(p_pre-p0)/p0*1e4
approx = (-np.sign(pr[COL[4]])*k_bp).abs()
close = (pr.loc[m1z, COL[4]].abs() - k_bp[m1z]).abs() < 1e-3
say(f"      |材料4| == k(bp) の行 {int(close.sum())}/{int(m1z.sum())} "
    f"= {close.mean():.4f}(材料1==0 の行のみ)")
say(f"      材料1>=1 の行では {int((( pr.loc[~m1z,COL[4]].abs()-k_bp[~m1z]).abs()<1e-3).sum())}"
    f"/{int((~m1z).sum())}")
say(f"      材料4 の帯 1〜4 に入る行のうち 材料1==0 の割合 "
    f"{float(m1z[pr['band_4'].isin([1,2,3,4])].mean()):.4f}、"
    f"帯 1〜4 の行数 {int(pr['band_4'].isin([1,2,3,4]).sum())}")
cell(4)

# ---------------------------------------------------------------- 9. 前半/後半
hr("9. 前半 / 後半の違いと切り値の安定性")
for h in ("前半","後半"):
    x = pr[pr.half==h]
    say(f" {h}: 日数{x['day'].nunique()} 清算{len(x)} 1日あたり{len(x)/x['day'].nunique():.1f} "
        f"p0 {x['p0'].min():.1f}〜{x['p0'].max():.1f} 中央値{x['p0'].median():.1f} "
        f"基準率60s {float(x['label_60'].mean()):.4f} "
        f"SELL割合{float((x.side=='SELL').mean()):.4f}")
    cell(7)
say(f" 後半 / 前半 の清算数の比 {len(bh)/len(fh):.3f}")
say("\n 後半だけで切り直したとき、後半の行の帯が変わる割合:")
tot_chg = []
for n in MAT_CONT:
    v = pd.to_numeric(bh[COL[n]],errors="coerce").to_numpy(float)
    vv = v[np.isfinite(v)]
    c2 = np.quantile(vv, [i/N_BANDS for i in range(1,N_BANDS)])
    b_old = band_of(v, cuts[n]); b_new = band_of(v, c2)
    m = np.isfinite(v)
    chg = float((b_old[m]!=b_new[m]).mean())
    tot_chg.append(chg)
    say(f"   材料{n:2d}: {chg:.4f}")
    cell(2)
say(f"   13 材料の中央値 {np.median(tot_chg):.4f}、最小 {min(tot_chg):.4f}、最大 {max(tot_chg):.4f}")
say("\n 後半だけで規則を作り直したら「続く」と言う帯は変わるか(前半の規則との比較):")
for n in (1,14,4,5,15,9):
    base_bh = float(bh["label_60"].mean())
    rs2 = {}
    for b, g in bh.groupby(f"band_{n}"):
        if int(b) >= 1: rs2[int(b)] = float(g["label_60"].mean()) > base_bh
    a = sorted(b for b,v in rule_set[n].items() if v)
    c = sorted(b for b,v in rs2.items() if v)
    say(f"   材料{n}: 前半 {a} / 後半 {c} {'同じ' if a==c else '★違う'}")
    cell(2)

# ---------------------------------------------------------------- 10. 多重性
hr("10. 多重性")
say(f" 委任先の行数 {summ['表の行数の合計(Q6 を除く)']}、セル数 {summ['tables.md の数値セル数']}")
say(f" 設計の見積もり 407 との差 {summ['設計の見積もり(407)との差']}")
say(f" 反証者が新しく切ったセルの数(この走りで数えた) {CELLS[0]}")

hr("完了")

# ===========================================================================
# 追補(反証者の 2 回目の走り)
# ===========================================================================
hr("11. 規則どうしの重なり(15 本は何本ぶんの別々の判断か)")
keys = ["rule_1","rule_2","rule_3","rule_4","rule_5","rule_6","rule_8","rule_9",
        "rule_10","rule_11","rule_12","rule_13","rule_14","rule_15","rule_combo"]
say("  一致率(後半、両方が引ける行だけ):")
say("        " + " ".join(f"{k.replace('rule_',''):>5s}" for k in keys))
for a in keys:
    line = []
    for b in keys:
        pa, pb = judg[a], judg[b]
        m = pa.notna() & pb.notna()
        line.append(f"{float((pa[m]==pb[m]).mean()):.3f}"[1:])
    say(f"  {a.replace('rule_',''):>5s} " + " ".join(f"{x:>5s}" for x in line))
    cell(15)
say("\n  「続く」と言った件数が rule_1 とそろう規則:")
for k in keys:
    m = judg[k].notna() & judg["rule_1"].notna()
    say(f"   {k}: 一致率 {float((judg[k][m]==judg['rule_1'][m]).mean()):.4f} "
        f"(n={int(m.sum())})")
    cell(2)

hr("12. 規則が『多件の最後』をどちらの枝に入れるか")
for k in ("rule_1","rule_4","rule_5","rule_14","rule_combo"):
    pred = judg[k].reindex(bh2.index)
    for g in ("多件の最後","単発","多件の最初","途中"):
        gg = bh2[bh2["群"]==g]
        pp = pred[bh2["群"]==g]
        n_c = int((pp==True).sum()); n_t = int(pp.notna().sum())
        say(f"   {k:11s} {g:6s}: 「続く」に入れた {n_c}/{n_t} = "
            f"{n_c/max(n_t,1):.4f}")
        cell(2)
    say("")

hr("13. 分岐点(何割当たれば取り分が 0 になるか)")
pc_ = judg["rule_combo"].reindex(bh2.index)
for k in ("rule_combo","rule_14","rule_1"):
    p_ = judg[k].reindex(bh2.index)
    a = bh2[(p_==True)&(bh2.label_60==1)]["pnl_long"]
    b = bh2[(p_==True)&(bh2.label_60==0)]["pnl_long"]
    pa, pb = float(a.mean()), float(b.mean())
    be = (-pb)/(pa-pb) if pa != pb else NAN
    prec = len(a)/(len(a)+len(b))
    say(f" {k} 続く枝: 当たりの平均 {pa:+.4f} / 外れの平均 {pb:+.4f} "
        f"→ 取り分 0 になる適合率 {be:.4f}(実際 {prec:.4f})")
    a2 = bh2[(p_==False)&(bh2.label_60==0)]["pnl_long"]*-1
    b2 = bh2[(p_==False)&(bh2.label_60==1)]["pnl_long"]*-1
    pa2, pb2 = float(a2.mean()), float(b2.mean())
    be2 = (-pb2)/(pa2-pb2) if pa2 != pb2 else NAN
    prec2 = len(a2)/(len(a2)+len(b2))
    say(f" {k} 止まる枝: 当たりの平均 {pa2:+.4f} / 外れの平均 {pb2:+.4f} "
        f"→ 取り分 0 になる的中割合 {be2:.4f}(実際 {prec2:.4f})")
    cell(8)

hr("14. Q7 の対照はプリントと同じ荒さの瞬間か")
s7 = q7["dir_sign"].astype(float)
pnl7 = (s7*(q7["p_exit_e1_h60"]-q7["p_entry_1"])/q7["p_entry_1"]*1e4).to_numpy(float)
pnlp = (bh["dir_sign"].astype(float)*(bh["p_exit_e1_h60"]-bh["p_entry_1"])
        /bh["p_entry_1"]*1e4).to_numpy(float)
for nm, v in (("後半のプリント", pnlp), ("Q7 の対照候補", pnl7)):
    p10,p25,p50,p75,p90 = qs(v,[10,25,50,75,90])
    say(f"  {nm:14s} n={np.isfinite(v).sum()} 60 秒の動き(向き付き bp) "
        f"p10{p10:+.2f} p25{p25:+.2f} 中央{p50:+.2f} p75{p75:+.2f} p90{p90:+.2f} "
        f"四分位幅 {p75-p25:.2f} |値|の中央 {np.median(np.abs(v[np.isfinite(v)])):.2f}")
    cell(7)
say(f"  四分位幅の比(プリント ÷ 対照) "
    f"{(qs(pnlp,[75])[0]-qs(pnlp,[25])[0])/(qs(pnl7,[75])[0]-qs(pnl7,[25])[0]):.3f}")
say(f"  「値段の続き」(5bp 以上進む)割合: プリント {float(bh['value_continuation_60'].mean()):.4f}"
    f" / 対照 {float(q7['value_continuation_60'].mean()):.4f}")
say("  合わせた 2 材料の分布(後半のプリント vs 対照候補):")
for n in (15, 9):
    a = pr.loc[pr.half=='後半', COL[n]].to_numpy(float)
    b = q7[COL[n]].to_numpy(float)
    say(f"   材料{n}: プリント p25{qs(a,[25])[0]:+.4f} 中央{qs(a,[50])[0]:+.4f} "
        f"p75{qs(a,[75])[0]:+.4f} / 対照 p25{qs(b,[25])[0]:+.4f} "
        f"中央{qs(b,[50])[0]:+.4f} p75{qs(b,[75])[0]:+.4f}")
    cell(6)

hr("15. 束の外(2,561 件)の影響と上位 5 日の寄与")
sub = bh2[bh2["群"]!="束の外"]
st = branch_stats((-sub["pnl_long"]).to_numpy(float), sub["day"].to_numpy(object))
say(f" all_stop から束の外を抜くと: {fmt(st)} 平均{st['mean']:+.4f}"
    f"(抜く前 中央値+1.0297 日等重み+1.0211)")
d = daily(-bh2["pnl_long"].to_numpy(float), bh2["day"].to_numpy(object))
say(f" all_stop 日ごと: 負の日{d['neg']:.4f} 上位5日/全体{d['top5']:+.4f} 合計{d['total']:+.1f}")
ds = pd.Series(-bh2["pnl_long"].to_numpy(float)).groupby(
    bh2["day"].to_numpy(object)).sum().sort_values(ascending=False)
say(f" all_stop 上位5日: " + ", ".join(f"{k}:{v:+.0f}" for k,v in ds.head(5).items()))
cell(10)

hr("16. 前半でも同じ向きか(反証者の追加の切り。規則を使わない層なので前半でも測れる)")
for nm, msk in (("1 件目(材料1==0)を逆張り", fh[COL[1]]==0),
                ("2 件目以降(材料1>=1)を逆張り", fh[COL[1]]>=1),
                ("全部逆張り", pd.Series(True, index=fh.index))):
    v = (-(fh["dir_sign"].astype(float))*(fh["p_exit_e1_h60"]-fh["p_entry_1"])
         /fh["p_entry_1"]*1e4).where(msk, NAN).to_numpy(float)
    st = branch_stats(v, fh["day"].to_numpy(object))
    dd = daily(v, fh["day"].to_numpy(object))
    say(f"  前半 {nm:26s} {fmt(st)} 平均{st['mean']:+.4f} 負の日{dd['neg']:.4f} "
        f"上位5日/全体{dd['top5']:+.4f}")
    cell(9)

hr("17. 多重性(追補ぶんを足した合計)")
say(f" 反証者が新しく切ったセルの数(追補まで含めた合計) {CELLS[0]}")

hr("18. 逆張りの取り分は前半にもあるか(半期ごとに分けて測る)")
ex5g = ex5[["print_id","群"]]
pr2 = pr.merge(ex5g, on="print_id", how="left")
for half in ("前半","後半"):
    x = pr2[pr2.half==half]
    v = (-(x["dir_sign"].astype(float))*(x["p_exit_e1_h60"]-x["p_entry_1"])
         /x["p_entry_1"]*1e4)
    st = branch_stats(v.to_numpy(float), x["day"].to_numpy(object))
    dd = daily(v.to_numpy(float), x["day"].to_numpy(object))
    say(f" {half} 全部逆張り: {fmt(st)} 平均{st['mean']:+.4f} 負の日{dd['neg']:.4f} "
        f"合計{dd['total']:+.1f}")
    y = x[x["群"]!="束の外"]
    v2 = (-(y["dir_sign"].astype(float))*(y["p_exit_e1_h60"]-y["p_entry_1"])
          /y["p_entry_1"]*1e4)
    st2 = branch_stats(v2.to_numpy(float), y["day"].to_numpy(object))
    say(f"   └ 束の外({len(x)-len(y)} 件)を抜くと: {fmt(st2)} 平均{st2['mean']:+.4f}")
    ds2 = pd.Series(v.to_numpy(float)).groupby(x["day"].to_numpy(object)).sum().sort_values()
    say(f"   下位5日: " + ", ".join(f"{k}:{val:+.0f}" for k,val in ds2.head(5).items()))
    say(f"   上位5日: " + ", ".join(f"{k}:{val:+.0f}" for k,val in ds2.tail(5).items()))
    cell(12)
say("\n 排他 4 群の 1 件あたり(清算の向き、t0+1s→60s)を半期ごとに:")
for half in ("前半","後半"):
    x = pr2[pr2.half==half]
    line = []
    for g in ("多件の最初","途中","単発","多件の最後","束の外"):
        gg = x[x["群"]==g]
        v = (gg["dir_sign"].astype(float)*(gg["p_exit_e1_h60"]-gg["p_entry_1"])
             /gg["p_entry_1"]*1e4)
        st = branch_stats(v.to_numpy(float), gg["day"].to_numpy(object))
        line.append(f"{g} n={st['n']} 中{st['med']:+.2f} 平均{st['mean']:+.2f}±{st['se']:.2f}")
        cell(4)
    say(f"  {half}: " + " | ".join(line))
say("\n 半期ごとの「2 件目以降を逆張り」:")
for half in ("前半","後半"):
    x = pr2[pr2.half==half]
    m = (x[COL[1]]>=1)
    v = (-(x["dir_sign"].astype(float))*(x["p_exit_e1_h60"]-x["p_entry_1"])
         /x["p_entry_1"]*1e4).where(m, NAN)
    st = branch_stats(v.to_numpy(float), x["day"].to_numpy(object))
    dd = daily(v.to_numpy(float), x["day"].to_numpy(object))
    say(f"  {half}: {fmt(st)} 平均{st['mean']:+.4f} 負の日{dd['neg']:.4f} "
        f"上位5日/全体{dd['top5']:+.4f} 合計{dd['total']:+.1f}")
    cell(9)

hr("19. 多重性(最終)")
say(f" 反証者が新しく切ったセルの数(合計) {CELLS[0]}")
