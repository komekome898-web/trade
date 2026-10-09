"""リードが書いた。委任・批評家を通していない(数えるだけ)。本 × 保有の帯(0 分 = 1 段目と同じ足で閉じた / 0 分超)ごとの、取引の段の数(levels 列)の平均・上限段の割合・
1 取引あたりの損益(円)を前半・後半(境 2019-12-09、出の UTC の日)で数える。数えるだけ(区間は付けない)。
相方の entry_exit D9b の指摘 3。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/levels_band.py <本> [...]
"""
import csv, gzip, json, sys
CUT = "2019-12-09"
print("| 本 | 帯 | 区切り | 本数 | 段の数の平均 | 上限段の割合 | 1 取引あたり 円 |")
print("|---|---|---|---|---|---|---|")
for name in sys.argv[1:]:
    cap = json.load(open(f"backtest_runs_shared/matilda_main/{name}/run.json"))["params"]["levels"]
    acc = {}
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{name}/trades.csv.gz", "rt")):
        band = "0 分" if r["exit_t"] <= r["entry_t"] else "0 分超"
        half = "前半" if r["exit_t"][:10] < CUT else "後半"
        a = acc.setdefault((band, half), [0, 0, 0, 0.0])
        lv = int(r["levels"])
        a[0] += 1; a[1] += lv; a[2] += lv >= cap; a[3] += float(r["pnl_jpy"])
    for band in ("0 分", "0 分超"):
        for half in ("前半", "後半"):
            n, s, c, p = acc[(band, half)]
            print(f"| {name} | {band} | {half} | {n:,} | {s / n:.2f} | {c / n:.3f} | {p / n:+.1f} |")
