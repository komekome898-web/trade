"""L-973 次の手 2: 中心から 4 ボラ外れた起点(K-378 の測りの起点。bitFlyer、`data/d1b/records.pkl` = run_d1b.py の書き出し)のうち、
20 分以内に利確の線へ戻る起点(結果 i)と戻らない起点を、起点の時点で分かる量で見分けられるかを数える。
起点は基準が建てる側(entry = 外れた最初の足・門が開き・ブレイク中でない)。年は 2016〜2023。
量(どれも起点の足が閉じた時点で分かる):
  深さ = 向き × (中心 − 終値) ÷ ボラ(4 より大きい。どこまで外れて閉じたか)
  幅 ÷ ボラ
  ボラ ÷ 値段(bp)
  ブレイクの線まで = 向き × (終値 − ブレイクの線) ÷ ボラ
  直前の動き = 向き × (終値 ÷ 5 分前の終値 − 1)(bp。正 = 外れる向きと逆 = すでに戻り始め、負 = 外れる向きに勢いがある)
  時刻(日本時間 4 時間ごと)
帯の境は前半(2016〜2019 年)の起点の五分位で決め、後半(2020〜2023 年)にも同じ境を当てる(前半で決めて後半に当てた形)。
出すもの: 量ごとに 帯 × 前半・後半 の i の割合・iii(ブレイクの線に先に)の割合・起点の数。あわせて、年ごとの i の割合を、量の帯の混ざり方を 2017〜2018 年にそろえた値と並べる。
区間は付けていない(起点の数が帯ごとに 5 万〜10 万。記述)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/fast_return_features.py > docs/RESEARCH/matilda_main/stage2/fast_return_features.out
"""
import glob
import pickle

import numpy as np
import pandas as pd

r = pickle.load(open("data/d1b/records.pkl", "rb"))
d = pd.DataFrame(r["records"])
d = d[d.entry & d.gate & (d.brk == 0)].copy()
d["y"] = d.day.str[:4].astype(int)
d = d[d.y.between(2016, 2023)]
F = sorted(f for f in glob.glob("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_20[12][0-9].csv.gz") if int(f[-11:-7]) <= 2023)
b = pd.concat(pd.read_csv(f, usecols=["ts", "close"]) for f in F).dropna()
b["t"] = pd.to_datetime(b.ts, utc=True)
c = b.set_index("t").close
t0 = pd.to_datetime(d.ts, utc=True)
prev5 = c.reindex(t0 - pd.Timedelta("5min")).to_numpy()
d["depth"] = d.side * (d.center - d.c0) / d.vola
d["w_v"] = d.width / d.vola
d["v_bp"] = d.vola / d.c0 * 1e4
d["line"] = d.side * (d.c0 - d.break_line) / d.vola
d["mom"] = d.side * (d.c0.to_numpy() / prev5 - 1) * 1e4
d["hour"] = ((t0.dt.hour + 9) % 24 // 4 * 4).to_numpy()
d["i"] = d.outcome == "i"
d["iii"] = d.outcome == "iii"
d["half"] = np.where(d.y <= 2019, "前半", "後半")
print(f"起点 {len(d):,}(前半 {(d.half == '前半').sum():,}・後半 {(d.half == '後半').sum():,})。直前の動きが取れない起点 {np.isnan(d.mom).sum():,}\n")
NAMES = {"depth": "深さ(ボラの何倍外れて閉じたか)", "w_v": "幅 ÷ ボラ", "v_bp": "ボラ ÷ 値段(bp)", "line": "ブレイクの線まで(ボラの何倍)", "mom": "直前 5 分の動き(bp、正 = 戻り始め)"}
early = d[d.half == "前半"]
for k, nm in NAMES.items():
    e = early[k].dropna().quantile([0.2, 0.4, 0.6, 0.8]).to_list()
    edges = [-np.inf] + e + [np.inf]
    lab = [f"〜{e[0]:.2f}"] + [f"{e[i]:.2f}〜{e[i + 1]:.2f}" for i in range(3)] + [f"{e[3]:.2f}〜"]
    d[k + "_b"] = pd.cut(d[k], edges, labels=lab)
    print(f"## {nm}(境 = 前半の五分位)\n")
    print("| 帯 | 前半 i | 後半 i | 前半 iii | 後半 iii | 後半の起点 |")
    print("|---|---|---|---|---|---|")
    for g in lab:
        x, y_ = d[(d[k + "_b"] == g) & (d.half == "前半")], d[(d[k + "_b"] == g) & (d.half == "後半")]
        print(f"| {g} | {x.i.mean():.1%} | {y_.i.mean():.1%} | {x.iii.mean():.1%} | {y_.iii.mean():.1%} | {len(y_):,} |")
    print()
print("## 時刻(日本時間)\n")
print("| 時刻 | 前半 i | 後半 i | 前半 iii | 後半 iii |")
print("|---|---|---|---|---|")
for h in sorted(d.hour.unique()):
    x, y_ = d[(d.hour == h) & (d.half == "前半")], d[(d.hour == h) & (d.half == "後半")]
    print(f"| {h:02d}〜{h + 4:02d} 時 | {x.i.mean():.1%} | {y_.i.mean():.1%} | {x.iii.mean():.1%} | {y_.iii.mean():.1%} |")
print("\n## 年ごとの i の割合と、量の帯の混ざり方を 2017〜2018 年にそろえた値(直接の標準化)\n")
ref = d[d.y.between(2017, 2018)]
print("| 年 | i(実際) | " + " | ".join(f"{NAMES[k].split('(')[0]}でそろえた" for k in NAMES) + " | 各量の中央値: 深さ・幅÷ボラ・ボラ bp・線まで・直前の動き |")
print("|---|---|" + "---|" * len(NAMES) + "---|")
for yy in range(2016, 2024):
    x = d[d.y == yy]
    cells = []
    for k in NAMES:
        w = ref[k + "_b"].value_counts(normalize=True)
        m = x.groupby(k + "_b", observed=False).i.mean()
        cells.append(f"{(m * w).sum():.1%}")
    med = " / ".join(f"{x[k].median():.2f}" for k in NAMES)
    print(f"| {yy} | {x.i.mean():.1%} | " + " | ".join(cells) + f" | {med} |")
