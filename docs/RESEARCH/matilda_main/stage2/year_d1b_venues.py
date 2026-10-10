"""L-973 次の手 1: K-378 の測り(中心から 4 ボラ外れた起点の後 40 分)を、bitFlyer FX_BTC_JPY と Binance BTCUSDT 現物で年ごとに並べる。
起点の記録: bitFlyer `data/d1b/records.pkl`(run_d1b.py)、Binance `<binance の置き場>/records.pkl`(d1b_binance.py)。
2 つの起点の集め方: (A) 門が開き・ブレイク中でない起点の全部(K-378 の表と同じ)(B) そのうち外れた最初の足(entry。戦略が建てる足に近い)。
区間は日の塊(循環 5 日・1,000 回・種 20261004)の割合の作り直し。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/year_d1b_venues.py <binance の置き場> > docs/RESEARCH/matilda_main/stage2/year_d1b_venues.out
"""
import pickle
import sys

import numpy as np
import pandas as pd

rng = np.random.default_rng(20261004)


def load(p):
    d = pd.DataFrame(pickle.load(open(p, "rb"))["records"])
    d = d[d.gate & (d.brk == 0)]
    d["y"] = d.day.str[:4].astype(int)
    return d


def ci(x, out):
    g = x.groupby("day").outcome.agg([lambda s: (s == out).sum(), "size"]).to_numpy()
    num, den = g[:, 0].astype(float), g[:, 1].astype(float)
    n = len(den)
    st = rng.integers(0, n, size=(1000, int(np.ceil(n / 5))))
    idx = (st[:, :, None] + np.arange(5)).reshape(1000, -1)[:, :n] % n
    rr = num[idx].sum(axis=1) / den[idx].sum(axis=1)
    return f"{num.sum() / den.sum():.1%} [{np.percentile(rr, 2.5):.1%}, {np.percentile(rr, 97.5):.1%}]"


V = {"bitFlyer": load("data/d1b/records.pkl"), "Binance": load(sys.argv[1] + "/records.pkl")}
for lab, sel in (("(A) 門が開き・ブレイク中でない起点の全部", lambda d: d), ("(B) そのうち外れた最初の足(entry)", lambda d: d[d.entry])):
    for out, nm in (("i", "20 分以内に利確の線(中心 ± 3 ボラ)に届く割合"), ("iii", "ブレイクの線に先に届く割合"), ("ii", "21〜40 分に起点の値段に戻る割合")):
        print(f"\n## {lab}: {nm}\n")
        print("| 年 | bitFlyer 起点 | bitFlyer | Binance 起点 | Binance |")
        print("|---|---|---|---|---|")
        for y in range(2016, 2024):
            cells = []
            for v, d in V.items():
                x = sel(d[d.y == y])
                cells += [f"{len(x):,}", ci(x, out) if len(x) else "—"]
            print(f"| {y} | " + " | ".join(cells) + " |")
