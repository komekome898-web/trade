"""リードが書いた。委任・批評家を通していない(数えるだけ)。本と基準の取引を合図の時刻で結び、両方とも保有 0 分(1 段目と同じ足で閉じた)の取引(--held を付けると両方とも 0 分超 = 足の後まで持った取引)を、
出の理由の組(基準 → 本)× 前半・後半(境 2019-12-09)で数える。本数・1 本あたり(円)・差の和 ÷ 半分の日数(1,469・1,470)。区間なし。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/same_bar_reason.py <本> [--held]
"""
import csv, gzip, sys
from collections import defaultdict
CUT="2019-12-09"
def load(n):
    o=defaultdict(list)
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{n}/trades.csv.gz","rt")):
        o[r["signal_t"]].append(r)
    return o
HELD="--held" in sys.argv
b=load("base"); r=load(sys.argv[1])
band=lambda t:(t["exit_t"]>t["entry_t"])==HELD
acc=defaultdict(lambda:[0,0.0,0.0])
for k in set(b)&set(r):
    if len(b[k])==1 and len(r[k])==1:
        x,y=b[k][0],r[k][0]
        if band(x) and band(y):
            h="前半" if k[:10]<CUT else "後半"
            a=acc[(h,x["exit_reason"]+"→"+y["exit_reason"])]
            a[0]+=1;a[1]+=float(x["pnl_jpy"]);a[2]+=float(y["pnl_jpy"])
for key in sorted(acc):
    n,sb,sr=acc[key]; print(key, n, f"{sb/n:+.1f} -> {sr/n:+.1f}", f"diff/day {(sr-sb)/(1469 if key[0]=='前半' else 1470):+.1f}")
