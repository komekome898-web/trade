"""リードが書いた。委任・批評家を通していない(数えるだけ)。本と基準の取引を合図の時刻(signal_t)で結び、基準の帯(0 分 = 1 段目と同じ足で閉じた / 0 分超)× 本の帯 の 2 × 2 と、
片方だけの取引を、前半・後半(境 2019-12-09、合図の UTC の日)で数える。各升目の本数・基準の和・本の和(円)と、
差の和 ÷ その半分の日数(円/日。日の数は基準の期間の 1,469・1,470 日)。区間は付けない(数えるだけ)。
帯の差(D7 の帯による分解)が「同じ取引の損益が変わった分」か「取引が帯を移った分」かを分ける。相方の break_dist D9b の指摘 1。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/band_migration.py <本> [...]
"""
import csv, gzip, sys
from collections import defaultdict
CUT, DAYS = "2019-12-09", {"前半": 1469, "後半": 1470}

def load(name):
    out = defaultdict(list)
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{name}/trades.csv.gz", "rt")):
        band = "0 分" if r["exit_t"] <= r["entry_t"] else "0 分超"
        out[r["signal_t"]].append((band, float(r["pnl_jpy"])))
    return out

base = load("base")
print("| 本 | 区切り | 基準の帯 → 本の帯 | 本数 | 基準の和 円 | 本の和 円 | 差 円/日 |")
print("|---|---|---|---|---|---|---|")
for name in sys.argv[1:]:
    run = load(name)
    acc = defaultdict(lambda: [0, 0.0, 0.0])
    for k in set(base) | set(run):
        half = "前半" if k[:10] < CUT else "後半"
        b, r = base.get(k, []), run.get(k, [])
        if len(b) == 1 and len(r) == 1:
            a = acc[(half, f"{b[0][0]} → {r[0][0]}")]
            a[0] += 1; a[1] += b[0][1]; a[2] += r[0][1]
        else:  # 片方だけ(同じ合図の時刻に 2 本以上ある取引もここに入れる)
            for band, p in b:
                a = acc[(half, f"{band} → (無し)")]; a[0] += 1; a[1] += p
            for band, p in r:
                a = acc[(half, f"(無し) → {band}")]; a[0] += 1; a[2] += p
    for half in ("前半", "後半"):
        for key in sorted(k for k in acc if k[0] == half):
            n, sb, sr = acc[key]
            print(f"| {name} | {half} | {key[1]} | {n:,} | {sb:+,.0f} | {sr:+,.0f} | {(sr - sb) / DAYS[half]:+.0f} |")
