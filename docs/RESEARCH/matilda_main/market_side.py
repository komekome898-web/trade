"""マチルダ本測定の本ごとの D8(基準の d8_market.py を本の名前で回せるようにしたもの): 成行の約定の側(次の足の始値で全量)を、その足の (高値 + 安値) ÷ 2 に置き換えたときの損益の差(円)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/market_side.py <本の名前> [...]
"""
import csv, glob, gzip, sys
from collections import defaultdict
from bot.bt.simple import read_bars

FILES = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
FILES = [x for x in FILES if int(x[-11:-7]) <= 2023]
mk = {}
for name in sys.argv[1:]:
    for f in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main/{name}/fills.csv.gz", "rt")):
        if f["kind"] == "market":
            mk.setdefault(f["ts"], []).append((name, f))
d = defaultdict(float); n = defaultdict(int)
for b in read_bars(FILES, "2023-12-17T15:00:00+00:00"):
    for name, f in mk.get(b[0], []):
        mid = (b[2] + b[3]) / 2
        px, q = float(f["px"]), float(f["qty"])
        d[name] += q * (mid - px) if f["side"] == "sell" else q * (px - mid)
        n[name] += 1
for name in sys.argv[1:]:
    print(name, "成行の約定", n[name], "中ほどの値段に置き換えた差(円)", round(d[name]))
