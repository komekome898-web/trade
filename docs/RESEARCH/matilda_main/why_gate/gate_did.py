#!/usr/bin/env python3
"""持ち越しの 4(L-941): 門の候補(K-359 幅の下の門・K-363/K-364 ボラの門)の予言を、前提の直接の測り(D1b)の記録で確かめる。

予言は台帳の行に、この台本を走らせる前に書いて押し出した(K-359 は e4bbbac6)。【試験の無い台本の値】。
入力: `data/d1b/records.pkl`(`docs/RESEARCH/matilda_main/d1b/run_d1b.py` で作る。git に入れていない)。新しい走らせはしない。
見方: 入りごと・門が開いていてブレイク中でない(D1B_SPEC §5 の主に読む見方)。狭い = 物差し < 閾値、広い = それ以上。
差の差 = (後半 − 前半)狭い − (後半 − 前半)広い。区間は日の塊(循環 5 日・1,000 回・種 20261004)で、半分ごとに日を選び直し、
同じ選び直しの日で狭い・広いを数える(2 つの群は同じ日の上で相関する)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/why_gate/gate_did.py --measure width --thr 0.005133
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/why_gate/gate_did.py --measure vola --thr 0.000465
"""
import argparse
import math
import pickle
from collections import defaultdict

import numpy as np

CUT, BLOCK, NBOOT, SEED = "2019-12-09", 5, 1000, 20261004


def blocks(n, rng):
    nb = math.ceil(n / BLOCK)
    s = rng.integers(0, n, size=nb)
    return (s[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", choices=["width", "vola"], required=True)
    ap.add_argument("--thr", type=float, required=True)
    a = ap.parse_args()
    d = pickle.load(open("data/d1b/records.pkl", "rb"))
    recs = [r for r in d["records"] if r["entry"] and r["gate"] and r["brk"] == 0]
    days = sorted(d["days"])
    halves = {"前半": [x for x in days if x < CUT], "後半": [x for x in days if x >= CUT]}
    # 日ごとの数: 群 g(0 狭い / 1 広い)× 結果の数、と 幅 ÷ ボラ の値の並び
    cnt = defaultdict(lambda: np.zeros((2, 4)))  # 列: n, i, iii, both
    wv = defaultdict(lambda: ([], []))
    for r in recs:
        x = (r["width"] if a.measure == "width" else r["vola"]) / r["c0"]
        g = 0 if x < a.thr else 1
        c = cnt[r["day"]]
        c[g, 0] += 1
        c[g, 1] += r["outcome"] == "i"
        c[g, 2] += r["outcome"] == "iii"
        c[g, 3] += r["outcome"] == "both"
        if r["vola"] > 0:
            wv[r["day"]][g].append(r["width"] / r["vola"])
    print(f"物差し {a.measure} ÷ 終値、閾値 {a.thr}、起点 {len(recs)}(入りごと・門が開いていてブレイク中でない)\n")
    arr = {h: np.array([cnt[x] if x in cnt else np.zeros((2, 4)) for x in ds]) for h, ds in halves.items()}
    wva = {h: [(np.array(wv[x][0]), np.array(wv[x][1])) for x in ds] for h, ds in halves.items()}

    def stat(h, idx):
        s = arr[h][idx].sum(axis=0)  # (2, 4)
        share = s[:, 1:] / s[:, :1]
        narrow_frac = s[0, 0] / s[:, 0].sum()
        med = [float(np.median(np.concatenate([wva[h][k][g] for k in idx]))) for g in (0, 1)]
        return share, narrow_frac, med

    pt = {h: stat(h, np.arange(len(halves[h]))) for h in halves}
    rng = np.random.default_rng(SEED)
    bs = {h: [] for h in halves}
    for _ in range(NBOOT):
        for h in halves:
            bs[h].append(stat(h, blocks(len(halves[h]), rng)))

    def ci(v):
        lo, hi = np.percentile(v, [2.5, 97.5])
        return f"[{lo:+.4f}, {hi:+.4f}]"

    print("| 半分 | 狭い 起点 | 広い 起点 | 狭い i | 広い i | 狭い iii | 広い iii | 狭い 同じ足で両方 | 広い 同じ足で両方 | 狭い 幅÷ボラ 中央値 | 広い 幅÷ボラ 中央値 | 狭い起点の割合 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for h in halves:
        s = arr[h].sum(axis=0)
        sh, nf, med = pt[h]
        print(f"| {h} | {int(s[0,0])} | {int(s[1,0])} | {sh[0,0]:.4f} | {sh[1,0]:.4f} | {sh[0,1]:.4f} | {sh[1,1]:.4f} | {sh[0,2]:.4f} | {sh[1,2]:.4f} | {med[0]:.3f} | {med[1]:.3f} | {nf:.4f} |")
    print()
    names = [("i(20 分以内に利確の線)", 0), ("iii(ブレイクの線に先に届く)", 1), ("同じ足で両方", 2)]
    print("| 量 | 差の差 点 | 差の差 区間 | 狭い 後半−前半 | 広い 後半−前半 |")
    print("|---|---|---|---|---|")
    for nm, k in names:
        p = (pt["後半"][0][0, k] - pt["前半"][0][0, k]) - (pt["後半"][0][1, k] - pt["前半"][0][1, k])
        v = [(b2[0][0, k] - b1[0][0, k]) - (b2[0][1, k] - b1[0][1, k]) for b1, b2 in zip(bs["前半"], bs["後半"])]
        print(f"| {nm} | {p:+.4f} | {ci(v)} | {pt['後半'][0][0,k]-pt['前半'][0][0,k]:+.4f} | {pt['後半'][0][1,k]-pt['前半'][0][1,k]:+.4f} |")
    p = (pt["後半"][2][0] - pt["前半"][2][0]) - (pt["後半"][2][1] - pt["前半"][2][1])
    v = [(b2[2][0] - b1[2][0]) - (b2[2][1] - b1[2][1]) for b1, b2 in zip(bs["前半"], bs["後半"])]
    print(f"| 幅 ÷ ボラ の中央値 | {p:+.4f} | {ci(v)} | {pt['後半'][2][0]-pt['前半'][2][0]:+.4f} | {pt['後半'][2][1]-pt['前半'][2][1]:+.4f} |")
    print()
    print("| 量 | 点 | 区間 |")
    print("|---|---|---|")
    v = [b1[0][0, 2] - b1[0][1, 2] for b1 in bs["前半"]]
    print(f"| 前半の 同じ足で両方 狭い − 広い | {pt['前半'][0][0,2]-pt['前半'][0][1,2]:+.4f} | {ci(v)} |")
    v = [b2[1] - b1[1] for b1, b2 in zip(bs["前半"], bs["後半"])]
    print(f"| 狭い起点の割合 後半 − 前半 | {pt['後半'][1]-pt['前半'][1]:+.4f} | {ci(v)} |")


if __name__ == "__main__":
    main()
