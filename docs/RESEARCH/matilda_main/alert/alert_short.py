#!/usr/bin/env python3
"""待ちの長さ(alert_count)の族に足した 10 分・5 分の 2 本(L-945)を、延ばした 40・80 分と並べて基準と比べる。

予言は走らせる前に `docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE2_MATERIALS.md` §7.2 に書いた。
同じ日どうしの差(2 本の日の和集合、取引の無い日は 0 円、円/日)。区間と MDE は読み口 `diag_tables.mean_ci`(日の塊 5 日・1,000 回・種 20261004)。
あわせて、閉じ方ごとの本数と和を半分ごとに出す(記述、【結果で決まる群】)。【試験の無い台本の値】。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/alert/alert_short.py > docs/RESEARCH/matilda_main/alert/alert_short.out
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, "scripts/analysis")
sys.path.insert(0, "scripts/w4_measure")
import diag_paths as dp  # noqa: E402
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"
RUNS = [("alert 5 分", "alert_5"), ("alert 10 分", "alert_10"), ("alert 20 分(基準)", "base"), ("alert 40 分", "alert_x1"), ("alert 80 分", "alert_x2")]

base = dt.daily_series(dt.load_run(os.path.join(T, "base")))
print("## 基準との同じ日どうしの差(円/日 [区間](MDE))\n")
print("| 本 | 全期間 | 前半 | 後半 |")
print("|---|---|---|---|")
for label, run in RUNS:
    if run == "base":
        continue
    s = dt.daily_series(dt.load_run(os.path.join(T, run)))
    days = sorted(set(s) | set(base))
    d = [s.get(x, 0.0) - base.get(x, 0.0) for x in days]
    cells = []
    for keep in (lambda x: True, lambda x: x < CUT, lambda x: x >= CUT):
        r = dt.mean_ci([v for x, v in zip(days, d) if keep(x)])
        cells.append(f"{r['mean']:+.1f} [{r['lo']:+.1f}, {r['hi']:+.1f}]({r['mde']:.1f})")
    print(f"| {label} | " + " | ".join(cells) + " |")
print("\n## 閉じ方ごとの本数と和(円、記述、【結果で決まる群】。半分は合図の UTC の日)\n")
print("| 本 | 半分 | 利確 本・和 | ブレイク 本・和 | 時間切れの成行 本・和 | 計 本・和 |")
print("|---|---|---|---|---|---|")
for label, run in RUNS:
    agg = defaultdict(lambda: [0, 0.0])
    for t in dp.read_trades_csv(os.path.join(T, run)):
        pass
    import csv, gzip  # noqa: E401,E402
    with gzip.open(os.path.join(T, run, "trades.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            h = "前半" if r["signal_t"][:10] < CUT else "後半"
            for k in (r["exit_reason"], "計"):
                agg[(h, k)][0] += 1
                agg[(h, k)][1] += float(r["pnl_jpy"])
    for h in ("前半", "後半"):
        c = [f"{agg[(h, k)][0]}・{agg[(h, k)][1]:+.0f}" for k in ("close", "break", "market", "計")]
        print(f"| {label} | {h} | " + " | ".join(c) + " |")
