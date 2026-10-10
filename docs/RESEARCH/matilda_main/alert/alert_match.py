#!/usr/bin/env python3
"""待ちを短くした 2 本(5 分・10 分、L-945)と基準(20 分)を、同じ合図の時刻の取引で突き合わせる(相方 03_D10 の指摘 1・3)。

読み口 `diag_tables.d7` の突き合わせ(合図の時刻の鍵。どの本も合図 1 つに取引 1 本)を、閉じ方の組で割る:
基準の閉じ方 × 短くした本の閉じ方 ごとの本数と、損益の差(短くした本 − 基準)の和(円、記述、【結果で決まる群】)。
あわせて、全部の取引の 1 取引あたり(円、記述。区間は付けない)を本ごとに出す。半分は合図の UTC の日で 2019-12-09 から後半。
【試験の無い台本の値】。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/alert/alert_match.py > docs/RESEARCH/matilda_main/alert/alert_match.out
"""
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"
NAME = {"close": "利確", "break": "ブレイク", "market": "時間切れの成行"}


def load(run):
    d = pd.read_csv(f"{T}/{run}/trades.csv.gz", usecols=["signal_t", "pnl_jpy", "exit_reason"])
    assert d.signal_t.is_unique, run
    d["half"] = (d.signal_t.str[:10] >= CUT).map({False: "前半", True: "後半"})
    return d


base = load("base")
print("## 1 取引あたり(円、記述。区間なし)\n")
print("| 本 | 半分 | 取引 | 損益の和 | 1 取引あたり |")
print("|---|---|---|---|---|")
runs = {"base": base, "alert_10": load("alert_10"), "alert_5": load("alert_5")}
for run, d in runs.items():
    for h in ("前半", "後半"):
        x = d[d.half == h]
        print(f"| {run} | {h} | {len(x)} | {x.pnl_jpy.sum():+.0f} | {x.pnl_jpy.mean():+.3f} |")

for run in ("alert_5", "alert_10"):
    m = base.merge(runs[run], on="signal_t", suffixes=("_b", "_a"))
    m["diff"] = m.pnl_jpy_a - m.pnl_jpy_b
    print(f"\n## {run} と基準の、同じ合図の取引(両方にある {len(m)} 本、差の和 {m['diff'].sum():+.0f} 円)\n")
    print("| 半分 | 基準の閉じ方 | " + run + " の閉じ方 | 本 | 差の和(円) | 1 本あたりの差(円) |")
    print("|---|---|---|---|---|---|")
    for h in ("前半", "後半"):
        x = m[m.half_b == h]
        g = x.groupby(["exit_reason_b", "exit_reason_a"])["diff"].agg(["size", "sum"]).reset_index()
        for _, r in g.iterrows():
            print(f"| {h} | {NAME[r.exit_reason_b]} | {NAME[r.exit_reason_a]} | {r['size']} | {r['sum']:+.0f} | {r['sum'] / r['size']:+.2f} |")
        print(f"| {h} | 計 | | {len(x)} | {x['diff'].sum():+.0f} | {x['diff'].mean():+.2f} |")
    oa = runs[run][~runs[run].signal_t.isin(base.signal_t)]
    ob = base[~base.signal_t.isin(runs[run].signal_t)]
    print(f"\n- {run} だけの取引 {len(oa)} 本(和 {oa.pnl_jpy.sum():+.0f} 円)/ 基準だけの取引 {len(ob)} 本(和 {ob.pnl_jpy.sum():+.0f} 円)")
