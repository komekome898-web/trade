"""場面(前の日のボラの三分位)× 前半・後半 の日に絞った、本 − 基準 の同じ日どうしの日ごとの差(円)と 95% 区間。
場面の分け方・日・区間の取り方は scenes.py と同じ(class_mean_ci、5 日の塊)。相方の count D9b の指摘 3。
    PYTHONPATH=src:scripts/w4_measure python3 docs/RESEARCH/matilda_main/scene_diff.py <本の名前> [...]
"""
import csv, gzip, sys
from collections import defaultdict
import numpy as np
sys.argv, names = sys.argv[:1], sys.argv[1:]
import importlib.util
spec = importlib.util.spec_from_file_location("scenes", "docs/RESEARCH/matilda_main/scenes.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)  # 引数なしで読むので本は回らない

def pnl_of(name):
    p = defaultdict(float)
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{name}/trades.csv.gz", "rt")):
        p[sc.jday(r["exit_t"])] += float(r["pnl_jpy"])
    return p

base = pnl_of("base")
for name in names:
    pn = pnl_of(name)
    print(f"\n{name} − base\n場面 | 区切り | 日数 | 差 1 日あたり 円 [区間]")
    for k in ("low", "mid", "high"):
        for hn, sel in (("前半(〜2019-12-08)", lambda d: d < sc.CUT), ("後半(2019-12-09〜)", lambda d: d >= sc.CUT)):
            x = np.array([pn.get(d, 0.0) - base.get(d, 0.0) for d in sc.days if sc.cls[d] == k and sel(d)])
            m, lo, hi = sc.class_mean_ci(x)
            print(k, hn, len(x), f"{m:+.0f} [{lo:+.0f}, {hi:+.0f}]")
