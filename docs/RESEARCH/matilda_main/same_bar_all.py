"""本ごとに、取引を「1 段目と同じ 1 分足の中で閉じた(出の時刻 ≦ 建ての時刻)」と「1 段目の足の後まで持った」に分け、
本数・和(円)を全期間・前半・後半(境 2019-12-09、出の日。compare_family.py と同じ)で直接数える(引き算で出さない)。
同じ足の中の取引の損益は、足の中の道筋の仮定(陽線 O→L→H→C・陰線 O→H→L→C)だけで決まる。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/same_bar_all.py [<本> ...](無ければ全部)
"""
import csv, gzip, os, sys
CUT = "2019-12-09"
T = "backtest_runs_shared/matilda_main_trades"
runs = sys.argv[1:] or sorted(os.listdir(T))
print("| 本 | 同じ足 本 | 同じ足 和 | 同じ足 前半 | 同じ足 後半 | 後まで 本 | 後まで 和 | 後まで 前半 | 後まで 後半 | 全体 和 |")
print("|---|---|---|---|---|---|---|---|---|---|")
for r in runs:
    c = {k: [0, 0.0, 0.0, 0.0] for k in ("same", "after")}
    for t in csv.DictReader(gzip.open(f"{T}/{r}/trades.csv.gz", "rt")):
        k = "same" if t["exit_t"] <= t["entry_t"] else "after"
        v = float(t["pnl_jpy"]); x = c[k]
        x[0] += 1; x[1] += v; x[2 if t["exit_t"][:10] < CUT else 3] += v
    s, a = c["same"], c["after"]
    print(f"| {r} | {s[0]:,} | {s[1]:+,.0f} | {s[2]:+,.0f} | {s[3]:+,.0f} | {a[0]:,} | {a[1]:+,.0f} | {a[2]:+,.0f} | {a[3]:+,.0f} | {s[1]+a[1]:+,.0f} |")
