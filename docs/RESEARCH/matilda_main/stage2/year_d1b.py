"""L-972 の D1b: 前提の直接の測り(戦略を使わない。`docs/RESEARCH/matilda_main/d1b/day_counts.csv`、K-373 の測り)を年で切る。
起点 = 足が閉じた時点で終値が 中心 ± 4 ボラ の外。結果 i 20 分以内に利確の線(中心 ± 3 ボラ)/ ii 21〜40 分に起点の値段 / iii ブレイクの線に先に / iv どれも無し。
ここでは門で閉じた起点・ブレイク中の起点も含めた全部(gate・brk を問わない)と、基準が建てる側(gate 1・brk 0)の 2 つ。区間は日の塊(5 日・1,000 回)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/year_d1b.py > docs/RESEARCH/matilda_main/stage2/year_d1b.out
"""
import numpy as np
import pandas as pd

d = pd.read_csv("docs/RESEARCH/matilda_main/d1b/day_counts.csv")
d["y"] = d.day.str[:4].astype(int)
rng = np.random.default_rng(20261004)


def share_ci(x, out):
    g = x.groupby(["day", "outcome"]).n.sum().unstack(fill_value=0)
    num, den = g.get(out, pd.Series(0, index=g.index)).to_numpy(), g.sum(axis=1).to_numpy()
    n = len(den)
    st = rng.integers(0, n, size=(1000, int(np.ceil(n / 5))))
    idx = (st[:, :, None] + np.arange(5)).reshape(1000, -1)[:, :n] % n
    r = num[idx].sum(axis=1) / den[idx].sum(axis=1)
    return f"{num.sum() / den.sum():.1%} [{np.percentile(r, 2.5):.1%}, {np.percentile(r, 97.5):.1%}]"


for lab, x0 in (("全部の起点", d), ("基準が建てる側の起点(門が開き・ブレイク中でない)", d[(d.gate == 1) & (d.brk == 0)])):
    print(f"\n## {lab}\n")
    print("| 年 | 起点の数 | i 20 分以内に利確の線 | iii ブレイクの線に先に | ii 21〜40 分に起点の値段 |")
    print("|---|---|---|---|---|")
    for y in range(2016, 2024):
        x = x0[x0.y == y]
        print(f"| {y} | {x.n.sum():,} | {share_ci(x, 'i')} | {share_ci(x, 'iii')} | {share_ci(x, 'ii')} |")
