"""基準(base)の D8: 成行の約定の側(次の足の始値で全量)を、その足の (高値 + 安値) ÷ 2 に置き換えたときの損益の差(円)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d8_market.py
"""
import csv, glob, gzip
from collections import defaultdict
from bot.bt.simple import read_bars

F = "backtest_runs_shared/matilda_main/base/fills.csv.gz"
mk = {}
for f in csv.DictReader(gzip.open(F, "rt")):
    if f["kind"] == "market":
        mk.setdefault(f["ts"], []).append(f)
FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
FILES = [x for x in FILES if int(x[-11:-7]) <= 2023]
d = defaultdict(float); n = defaultdict(int); n_all = 0
for b in read_bars(FILES, "2023-12-17T15:00:00+00:00"):
    for f in mk.get(b[0], []):
        mid = (b[2] + b[3]) / 2
        px, q = float(f["px"]), float(f["qty"])
        diff = q * (mid - px) if f["side"] == "sell" else q * (px - mid)
        d[b[0][:4]] += diff; n[b[0][:4]] += 1; n_all += 1
print("成行の約定", sum(len(v) for v in mk.values()), "突き合わせた", n_all)
for y in sorted(d):
    print(y, n[y], round(d[y]))
print("合計(円)", round(sum(d.values())))
