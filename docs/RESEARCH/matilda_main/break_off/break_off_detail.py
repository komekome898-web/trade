"""リードが書いた。委任・批評家を通していない(数えるだけ)。break_off と基準を合図の時刻で結び、(1) 足の後まで持った取引で基準ブレイク → 本で利確/成行 の群の、
本の側の保有の分 > 20 分の割合と、段の数の平均(基準 → 本)(2) 本の成行の取引を 3 群(基準でブレイク → 成行 / 基準でも成行 / こちらだけ・ほか)に分けた本数と 1 本の円
(3) 成行で閉じた取引の保有の分の分位(25・50・75%、本と基準)を、前半・後半(境 2019-12-09)で出す。相方の break_off D9b の指摘 1・2。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/break_off/break_off_detail.py
"""
import csv, gzip
from datetime import datetime
CUT = "2019-12-09"
def load(n):
    o = {}
    for r in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{n}/trades.csv.gz", "rt")):
        o.setdefault(r["signal_t"], []).append(r)
    return o
def mins(r):
    f = lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    return (f(r["exit_t"]) - f(r["entry_t"])) / 60
def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")
b, r = load("base"), load("break_off")
for h in ("前半", "後半"):
    sel = lambda k: (k[:10] < CUT) == (h == "前半")
    for to in ("close", "market"):
        n = over = lb = lr = 0
        for k, rs in r.items():
            if not sel(k) or k not in b or len(rs) != 1 or len(b[k]) != 1:
                continue
            x, y = b[k][0], rs[0]
            if x["exit_t"] > x["entry_t"] and y["exit_t"] > y["entry_t"] and x["exit_reason"] == "break" and y["exit_reason"] == to:
                n += 1; over += mins(y) > 20; lb += int(x["levels"]); lr += int(y["levels"])
        print(f"{h} 基準ブレイク → 本 {to}: {n:,} 本 / 本の保有 20 分超 {over / n:.1%} / 段の数 {lb / n:.2f} → {lr / n:.2f}")
    grp = {}
    for k, rs in r.items():
        if not sel(k):
            continue
        for y in rs:
            if y["exit_reason"] != "market":
                continue
            bx = b.get(k, [])
            g = "基準でブレイク" if len(bx) == 1 and bx[0]["exit_reason"] == "break" else ("基準でも成行" if len(bx) == 1 and bx[0]["exit_reason"] == "market" else ("こちらだけ" if not bx else "基準で利確ほか"))
            a = grp.setdefault(g, [0, 0.0]); a[0] += 1; a[1] += float(y["pnl_jpy"])
    print(h, "本の成行の群: " + "・".join(f"{g} {a[0]:,} 本 1 本 {a[1] / a[0]:+.1f} 円" for g, a in grp.items()))
    for name, d in (("本", r), ("基準", b)):
        hm = [mins(y) for k, rs in d.items() if sel(k) for y in rs if y["exit_reason"] == "market"]
        print(h, f"{name}の成行の保有の分 25・50・75%: {q(hm, .25):.0f}・{q(hm, .5):.0f}・{q(hm, .75):.0f}(n {len(hm):,})")
