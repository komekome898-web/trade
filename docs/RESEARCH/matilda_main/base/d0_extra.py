"""基準(base)の D0 の足し(相方の指摘 P-3・P-5・P-7・P-9)。取引の行(simple_trades.py の出力)と約定の列と 1 分足を読むだけ。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d0_extra.py
"""
import csv, glob, gzip, statistics
from collections import defaultdict
from bot.bt.simple import read_bars

T = "backtest_runs_shared/matilda_main_trades/base/trades.csv.gz"
F = "backtest_runs_shared/matilda_main/base/fills.csv.gz"
rows = list(csv.DictReader(gzip.open(T, "rt")))
# P-5: 年ごとの 1 段目の量と円の大きさ
by = defaultdict(list)
for r in rows:
    by[r["signal_t"][:4]].append((float(r["qty1"]), float(r["qty1"]) * float(r["entry_price"])))
print("年 | 取引 | 1 段目の量の中央値 BTC | 1 段目の円の中央値 | 円の 10%〜90%")
for y in sorted(by):
    q = sorted(x for x, _ in by[y]); j = sorted(v for _, v in by[y]); n = len(j)
    print(y, n, statistics.median(q), round(statistics.median(j)), round(j[n // 10]), round(j[n * 9 // 10]))
# P-3: 最初の約定から 20 分を越えて足した段
late = [r for r in rows if int(r["late_levels"]) > 0]
print("20 分を越えて段を足した取引", len(late), "/", len(rows), "その取引の損益の和(円)", round(sum(float(r["pnl_jpy"]) for r in late)),
      "越えて足した段の数", sum(int(r["late_levels"]) for r in late))
# 段の数ごと
lv = defaultdict(lambda: [0, 0.0])
for r in rows:
    lv[int(r["levels"])][0] += 1; lv[int(r["levels"])][1] += float(r["pnl_jpy"])
print("段の数 | 取引 | 損益の和(円) | 1 取引あたり(円)")
for k in sorted(lv):
    print(k, lv[k][0], round(lv[k][1]), round(lv[k][1] / lv[k][0], 2))
# P-7/P-9 の 3 つの時刻: 先頭 5 本の取引の 1 段目の約定を、その時刻の 1 分足と突き合わせる
want = {r["signal_t"]: r for r in rows[:5]}
fills = []
with gzip.open(F, "rt") as fh:
    for i, f in enumerate(csv.DictReader(fh)):
        if f["ts"] in want and f["kind"] == "entry":
            fills.append(f)
        if len(fills) >= 5 or i > 200:
            break
FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_201[5].csv.gz"))
need = {f["ts"] for f in fills}
prev = None
for b in read_bars(FILES, "2023-12-17T15:00:00+00:00"):
    t = b[0]
    if t in need:
        f = [x for x in fills if x["ts"] == t][0]
        print("1 段目", t, f["side"], f["px"], f["case"], "| 足 O H L C", b[1:5], "| 前の終値", prev)
    prev = b[4]
    if t > max(need):
        break
