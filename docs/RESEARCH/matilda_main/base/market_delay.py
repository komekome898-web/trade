"""基準(base)の監査 1 回目の指摘 2: 時間切れの成行の約定の遅れ。成行が約定した足の時刻と、その直前の足(成行を出した足が閉じた足)の時刻の差(分)を年ごとに。
最初の約定から成行の約定までの分(保有)も年ごとに。足は道と同じ読み方(read_bars)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/market_delay.py
"""
import csv, glob, gzip
from collections import defaultdict
from datetime import datetime
from bot.bt.simple import read_bars
F = "backtest_runs_shared/matilda_main/base/fills.csv.gz"
mk = set(); first = {}; pos = 0.0; t0 = None; hold = {}
for f in csv.DictReader(gzip.open(F, "rt")):
    q = float(f["qty"]) * (1 if f["side"] == "buy" else -1)
    if abs(pos) < 1e-12:
        t0 = f["ts"]
    pos += q
    if f["kind"] == "market":
        mk.add(f["ts"]); hold[f["ts"]] = (datetime.fromisoformat(f["ts"]) - datetime.fromisoformat(t0)).total_seconds() / 60
FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
FILES = [x for x in FILES if int(x[-11:-7]) <= 2023]
gap = defaultdict(list); prev = None
for b in read_bars(FILES, "2023-12-17T15:00:00+00:00"):
    if b[0] in mk and prev is not None:
        gap[b[0][:4]].append(((datetime.fromisoformat(b[0]) - datetime.fromisoformat(prev)).total_seconds() / 60, hold[b[0]]))
    prev = b[0]
print("年 | 成行 | 直前の足との差 1 分 | 2〜5 分 | 5 分超 | 保有 41〜45 分 | 保有 45 分超")
for y in sorted(gap):
    g = gap[y]
    print(y, len(g), sum(1 for d, h in g if d <= 1), sum(1 for d, h in g if 1 < d <= 5), sum(1 for d, h in g if d > 5),
          sum(1 for d, h in g if 40 < h <= 45), sum(1 for d, h in g if h > 45))
