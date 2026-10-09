"""リードが書いた。委任・批評家を通していない(数えるだけ)。本と基準の取引を合図の時刻(signal_t)で結べなかった取引(こちらだけ・基準だけ)について、
相手側の最も近い合図の時刻までの距離(分)を数え、±1・±5・±40 分以内の割合と、その中で同じ向き(side)の割合を出す(前半・後半、境 2019-12-09)。
合図の時刻の厳密一致で結べない取引が「別の合図」か「同じ場面で時刻が数分ずれただけ」かを分ける。相方の beard D9b の指摘 1。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/nearest_signal.py <本>
"""
import bisect, csv, gzip, sys
from datetime import datetime
CUT = "2019-12-09"

def load(n):
    out = {}
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{n}/trades.csv.gz", "rt")):
        out.setdefault(r["signal_t"], []).append(r["side"])
    return out

def mins(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() / 60

b, r = load("base"), load(sys.argv[1])
for name, me, other in (("こちらだけ", r, b), ("基準だけ", b, r)):
    keys = sorted(other)
    ot = [mins(k) for k in keys]
    acc = {}
    for k, sides in me.items():
        if k in other:
            continue
        h = "前半" if k[:10] < CUT else "後半"
        t = mins(k)
        i = bisect.bisect_left(ot, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(ot):
                d = abs(ot[j] - t)
                if best is None or d < best[0]:
                    best = (d, other[keys[j]][0])
        a = acc.setdefault(h, [0, 0, 0, 0, 0])
        for s in sides:
            a[0] += 1
            if best:
                if best[0] <= 1: a[1] += 1
                if best[0] <= 5: a[2] += 1
                if best[0] <= 40: a[3] += 1
                if best[0] <= 5 and best[1] == s: a[4] += 1
    for h in ("前半", "後半"):
        n, w1, w5, w40, s5 = acc[h]
        print(f"{sys.argv[1]} {name} {h} 本 {n:,} / ±1 分 {w1 / n:.1%} / ±5 分 {w5 / n:.1%}(同じ向き {s5 / n:.1%})/ ±40 分 {w40 / n:.1%}")
