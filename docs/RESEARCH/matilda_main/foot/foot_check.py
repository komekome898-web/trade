"""族 foot の D0 の 3 つの時刻の確かめ(相方の D9b の指摘 1)。
(1) foot_5 の引数で戦略に 2017 年の頭 2,000 本の足を close で渡し、線(_snap)が作り直される足の時刻の「分 mod 5」を数える
(2) foot_5 の 2017 年の最初の取引の約定を 1 分足の高値・安値と突き合わせる
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/foot/foot_check.py
"""
import csv, glob, gzip, itertools
from collections import Counter
from bot.bt.simple import read_bars
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple
p = dict(BASE_PARAMS); p.update({"levels": 5, "entry_setting": 4, "exit_setting": 3, "foot": 5, "alert_count": 100.0})
st = MatildaSimple(p)
F = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz"))
prev = None; last = None; c = Counter(); bars = {}
for b in itertools.islice(read_bars(F, "2023-12-17T15:00:00+00:00"), 2000):
    bars[b[0]] = b
    if b[1] == b[4] and (prev is None or b[1] == prev):
        continue
    prev = b[4]
    st.decide({"kind": "close", "ts": b[0], "price": b[4], "fills": [], "touched": [], "bar": b})
    if st._snap is not None and st._snap is not last:
        c[int(b[0][14:16]) % 5] += 1
        last = st._snap
print("線が作り直された足の 分 mod 5:", dict(sorted(c.items())))
fills = []; pos = 0.0
for f in csv.DictReader(gzip.open("backtest_runs_shared/matilda_main/foot_5/fills.csv.gz", "rt")):
    if f["ts"] < "2017":
        continue
    fills.append(f); pos += float(f["qty"]) * (1 if f["side"] == "buy" else -1)
    if abs(pos) < 1e-9:
        break
for f in fills:
    b = bars.get(f["ts"])
    print(f["ts"], f["kind"], f["side"], f["qty"], f["px"], f["case"], "| 足 O H L C", b[1:5] if b else "(頭 2,000 本の外)", "| 高安の中", (b[3] <= float(f["px"]) <= b[2]) if b else None)
