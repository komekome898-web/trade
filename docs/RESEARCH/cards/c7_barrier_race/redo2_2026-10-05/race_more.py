"""カード 7 の足し(アドバイザーの指摘、2026-10-05)。保存済みの races_<窓>.csv.gz と trades_1h/trades.csv.gz だけ。台本の試験は無い。
(1) 流れを抜いた反転の割合 = (上で当たった後の反転の割合 + 下で当たった後の反転の割合) ÷ 2 に、日の塊の区間を付ける
    (diag_tables と同じ循環 5 日・1,000 回・種 20261004 で日を選び直し、2 つの割合をそれぞれ作り直して平均する)。
(2) レースの始めの幅 w の三分位 × 前の当たりの側(上・下)の反転の割合と、その平均。
(3) 1h の取引で保有(出 − 建て)が 24 時間を超えた本数。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_more.py
出力: このフォルダの RACE_MORE.md
"""
import csv
import gzip
import math
import os
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/trade/scripts/analysis")
import diag_tables as dt  # noqa: E402


def avg_ci(days, recs):
    """recs = [(日, 前の側, 反転 0/1)]。日の塊で選び直した (上の割合 + 下の割合) ÷ 2 の点と 95% 区間。"""
    idx = {d: i for i, d in enumerate(days)}
    n = len(days)
    su = np.zeros((2, n))
    cn = np.zeros((2, n))
    for d, ps, x in recs:
        if d in idx:
            k = 0 if ps > 0 else 1
            su[k, idx[d]] += x
            cn[k, idx[d]] += 1

    def stat(ii):
        a = su[:, ii].sum(axis=1)
        b = cn[:, ii].sum(axis=1)
        if (b == 0).any():
            return None
        return float((a / b).mean())
    point = stat(np.arange(n))
    rng = np.random.default_rng(dt.SEED)
    nb = math.ceil(n / dt.BLOCK)
    reps = []
    for _ in range(dt.N_RES):
        st = rng.integers(0, n, size=nb)
        ii = (st[:, None] + np.arange(dt.BLOCK)[None, :]).ravel()[:n] % n
        v = stat(ii)
        if v is not None:
            reps.append(v)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return point, float(lo), float(hi), int(cn.sum())


def main():
    out = ["# カード 7: 流れを抜いた反転の割合の区間・幅の帯 × 側・1h の 24 時間を超えた取引", "",
           "## (1)(2) 流れを抜いた反転の割合 = (上の後 + 下の後) ÷ 2 [日の塊の区間]。幅の帯は全期間の三分位(標本の中)", "",
           "| 窓 | 幅の帯(bp) | 期間 | 当たり | 上の後の反転の割合 | 下の後の反転の割合 | 平均 [日の塊の区間] |", "|---|---|---|---|---|---|---|"]
    for v in ("1h", "1d", "1w"):
        rows = list(csv.DictReader(gzip.open(os.path.join(HERE, f"races_{v}.csv.gz"), "rt")))
        days = sorted(l.split(",")[0] for l in open(os.path.join(HERE, "..", "measure", v, "daily.csv")).read().splitlines()[1:])
        half = len(days) // 2
        parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
        recs, prev = [], None
        for r in rows:
            s = int(r["side"])
            if prev is not None:
                recs.append((r["jst_day"], prev, 1.0 if s != prev else 0.0, float(r["w_start"])))
            prev = s
        ws = np.array([x[3] for x in recs])
        q1, q2 = np.quantile(ws, [1 / 3, 2 / 3])
        bands = [("全部", 0, 1e9)] + [(f"〜{q1 * 1e4:.1f}", 0, q1), (f"{q1 * 1e4:.1f}〜{q2 * 1e4:.1f}", q1, q2), (f"{q2 * 1e4:.1f}〜", q2, 1e9)]
        for bn, lo_, hi_ in bands:
            for pn, pd in parts.items():
                ps_ = set(pd)
                sel = [(d, p_, x) for d, p_, x, w in recs if lo_ <= w < hi_ and d in ps_]
                up = [x for _, p_, x in sel if p_ > 0]
                dn = [x for _, p_, x in sel if p_ < 0]
                pt, lo, hi, nn = avg_ci(pd, sel)
                out.append(f"| {v} | {bn} | {pn} | {nn:,} | {np.mean(up):.3f}({len(up)}) | {np.mean(dn):.3f}({len(dn)}) | {pt:.3f} [{lo:.3f}, {hi:.3f}] |")
    tr = list(csv.DictReader(gzip.open(os.path.join(HERE, "trades_1h", "trades.csv.gz"), "rt")))
    hold = [(datetime.fromisoformat(t["exit_t"].replace("Z", "+00:00")) - datetime.fromisoformat(t["entry_t"].replace("Z", "+00:00"))).total_seconds() / 60 for t in tr]
    over = sum(1 for h in hold if h > 1440)
    out += ["", "## (3) 1h の取引の保有", "", f"- 取引 {len(tr):,}、保有が 24 時間(1,440 分)を超えた取引 {over:,}({over / len(tr):.1%})、保有の最大 {max(hold):,.0f} 分"]
    open(os.path.join(HERE, "RACE_MORE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
