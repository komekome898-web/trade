"""族 count の D0 の確かめ。
(1) count_20・count_80 の引数で戦略に 2017 年の頭 2,000 本を close で渡し、足が閉じるたびに戦略のボラ(ind["vola"])が
    渡した足の直近 vola_count 本の |終値 − 始値| の平均と一致するかを数える(線を作る本数が引数どおりか)
(2) 各本の 2017 年の最初の取引の約定を 1 分足の高値・安値と突き合わせる
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/count/count_check.py
"""
import csv, glob, gzip, itertools
from bot.bt.simple import read_bars
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple
F = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz"))
for name, n in (("count_20", 20), ("count_80", 80)):
    p = dict(BASE_PARAMS); p.update({"levels": 5, "entry_setting": 4, "exit_setting": 3, "vola_count": n, "range_count": n, "alert_count": n * 0.5})
    st = MatildaSimple(p)
    prev = None; fed = []; ok = bad = 0; bars = {}
    for b in itertools.islice(read_bars(F, "2023-12-17T15:00:00+00:00"), 2000):
        bars[b[0]] = b
        if b[1] == b[4] and (prev is None or b[1] == prev):
            continue
        prev = b[4]; fed.append(abs(b[4] - b[1]))
        st.decide({"kind": "close", "ts": b[0], "price": b[4], "fills": [], "touched": [], "bar": b})
        if st.ind and len(fed) >= n:
            if abs(st.ind["vola"] - sum(fed[-n:]) / n) < 1e-6: ok += 1
            else: bad += 1
    print(name, "ボラが直近", n, "本の実体の平均と一致:", ok, "/ 不一致:", bad)
    fills = []; pos = 0.0
    for f in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main/{name}/fills.csv.gz", "rt")):
        if f["ts"] < "2017":
            continue
        fills.append(f); pos += float(f["qty"]) * (1 if f["side"] == "buy" else -1)
        if abs(pos) < 1e-9:
            break
    for f in fills:
        b = bars.get(f["ts"])
        print(" ", f["ts"], f["kind"], f["side"], f["qty"], f["px"], f["case"], "| 足 O H L C", b[1:5] if b else "(頭 2,000 本の外)", "| 高安の中", (b[3] <= float(f["px"]) <= b[2]) if b else None)
# (3) count_80 の最初の日(相方の D9b の指摘 5): 2015 年の足を戦略と同じ決まりで飛ばして数え、線に要る 160 本目の時刻と最初の約定を並べる
F15 = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2015.csv.gz"))
prev = None; fed = 0; at160 = None
for b in read_bars(F15, "2023-12-17T15:00:00+00:00"):
    if b[1] == b[4] and (prev is None or b[1] == prev):
        continue
    prev = b[4]; fed += 1
    if fed == 160:
        at160 = b[0]; break
first = next(csv.DictReader(gzip.open("backtest_runs_shared/matilda_main/count_80/fills.csv.gz", "rt")))["ts"]
print("count_80: 渡した足の 160 本目", at160, "/ 最初の約定", first)
