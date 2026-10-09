"""基準(base)の D10 の足し(相方の D10 の指摘 2): 戦略を使わず(指標の計算だけ)、足が閉じた時点の 幅 ÷ ボラ の年ごとの分布。
幅・ボラは戦略の指標(`MatildaSimple.ind`、直近 40 本、ヒゲの切り落とし 1 円)。足は道と同じ決まりで向きの決まらない足を飛ばす。
1 段のとんとんの割合 ≈ (幅 − 4 × ボラ) ÷ (幅 − 3 × ボラ)(上の線で売るとき: ブレイクの線 ≈ 中心 + 幅、建て = 中心 + 4 ボラ、利確 = 中心 + 3 ボラ)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/width_vola.py
"""
import glob
from collections import defaultdict
import numpy as np
from bot.bt.simple import read_bars
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple

F = sorted(glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz"))
F = [f for f in F if int(f[-11:-7]) <= 2023]
p = dict(BASE_PARAMS); p.update({"levels": 5, "entry_setting": 4, "exit_setting": 3})
st = MatildaSimple(p)
r = defaultdict(list)
prev = None
for b in read_bars(F, "2023-12-17T15:00:00+00:00"):
    t, o, h, l, c, v = b
    if o == c and (prev is None or o == prev):
        continue
    prev = c
    st.decide({"kind": "close", "ts": t, "price": c, "fills": [], "touched": [], "bar": b})
    ind = st.ind
    if ind is not None and st._snap is not None and ind["vola"] > 0:
        r[t[:4]].append(ind["width"] / ind["vola"])
print("年 | 足 | 幅÷ボラ 25% | 50% | 75% | 1 段のとんとん(中央値の幅÷ボラで)")
allv = []
for y in sorted(r):
    a = np.array(r[y]); allv.append((y, a))
    q = np.percentile(a, [25, 50, 75]); m = q[1]
    print(y, len(a), f"{q[0]:.2f}", f"{m:.2f}", f"{q[2]:.2f}", f"{(m-4)/(m-3):.4f}" if m > 4 else "幅<4ボラ")
for name, ys in (("前半(2015〜2019)", "2015 2016 2017 2018 2019"), ("後半(2020〜2023)", "2020 2021 2022 2023")):
    a = np.concatenate([x for y, x in allv if y in ys.split()])
    q = np.percentile(a, [25, 50, 75])
    print(name, len(a), f"{q[0]:.2f}", f"{q[1]:.2f}", f"{q[2]:.2f}")
