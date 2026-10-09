# リードが書いた。委任・批評家を通していない(数えるだけ)。scratchpad の gate_dist.py(PLAN.md §1.4 の門の値を出した台本)と同じ足の読み方で、
# 門の値以下(ボラ)・未満(幅)・超(幅の上)の足の割合を前半(〜2019-12-08)・後半(2019-12-09〜)で数える。
# 使い方(リポジトリの根から): PYTHONPATH=src python3 docs/RESEARCH/matilda_main/gate_dist_halves.py
import glob
from bot.bt.simple import read_bars
from bot.strategy.matilda_simple import MatildaSimple, BASE_PARAMS

F = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
F = [f for f in F if int(f[-11:-7]) <= 2023]
CUT = "2019-12-09"
VOLA = (0.00017, 0.000276, 0.000465)
LO = (0.001857, 0.003010, 0.005133)
HI = (0.008844, 0.014995)
st = MatildaSimple(dict(BASE_PARAMS))
cnt = {h: {"n": 0, **{("v", g): 0 for g in VOLA}, **{("lo", g): 0 for g in LO}, **{("hi", g): 0 for g in HI}} for h in ("前半", "後半")}
prev = None
for b in read_bars(F, "2023-12-17T15:00:00+00:00"):
    t, o, h, l, c, vol = b
    if o == c and (prev is None or o == prev):
        continue
    prev = c
    st.decide({"kind": "close", "ts": t, "price": c, "fills": [], "touched": [], "bar": b})
    ind = st.ind
    if ind is None or st._snap is None:
        continue
    half = "前半" if str(t) < CUT else "後半"
    d = cnt[half]
    d["n"] += 1
    w, v = ind["width"] / c, ind["vola"] / c
    for g in VOLA:
        d[("v", g)] += v <= g
    for g in LO:
        d[("lo", g)] += w < g
    for g in HI:
        d[("hi", g)] += w > g
print("| 区切り | 足 | ボラ ≤ 0.0170% | ≤ 0.0276% | ≤ 0.0465% | 幅 < 0.1857% | < 0.3010% | < 0.5133% | 幅 > 0.8844% | > 1.4995% |")
print("|---|---|---|---|---|---|---|---|---|---|")
for h, d in cnt.items():
    cells = [f"{d[('v', g)] / d['n']:.1%}" for g in VOLA] + [f"{d[('lo', g)] / d['n']:.1%}" for g in LO] + [f"{d[('hi', g)] / d['n']:.1%}" for g in HI]
    print(f"| {h} | {d['n']:,} | " + " | ".join(cells) + " |")
