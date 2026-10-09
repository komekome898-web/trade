"""1 段目と同じ 1 分足の中で閉じた取引(出の時刻 ≦ 建ての時刻)の数・和を、本ごと・前半後半(境 2019-12-09)で数える。
これらの取引の損益は足の中の道筋の仮定(陽線 O→L→H→C・陰線 O→H→L→C)だけで決まる。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/count/same_bar.py base count_20 count_80 ...
"""
import csv, gzip, sys
CUT = "2019-12-09"
print("| 本 | 取引 | 同じ足で閉じた 本(割合) | その和 円 | うちブレイク 本 | 前半の和 円 | 後半の和 円 | 全体の和 円 |")
print("|---|---|---|---|---|---|---|---|")
for r in sys.argv[1:]:
    n = same = br = 0; s = tot = 0.0; h = [0.0, 0.0]
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        n += 1; v = float(t["pnl_jpy"]); tot += v
        if t["exit_t"] <= t["entry_t"]:
            same += 1; s += v; br += t["exit_reason"] == "break"; h[t["exit_t"][:10] >= CUT] += v
    print(f"| {r} | {n:,} | {same:,}({same/n:.1%}) | {s:+,.0f} | {br:,} | {h[0]:+,.0f} | {h[1]:+,.0f} | {tot:+,.0f} |")
