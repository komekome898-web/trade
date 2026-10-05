"""カード 8 の足し(アドバイザーの指摘、2026-10-05)。保存済みの measure/<変種>/run.npz と daily.csv だけ。台本の試験は無い。
(1) 決定ごと(持ち高 ≠ 0)の 1 分を、持ち高の向き(買い = 平均より下、売り = 平均より上)で分け、本体(始値 → 始値)・
    24 時間後の対照・24 時間前の対照(同じ時刻の足どうし・同じ向き)を並べる。全期間・前半・後半。bp/決定、区間は日の塊。
(2) セッションの始まりからの経過時間の帯(決定の足の始まり − セッションの始まり、分: 0〜60・60〜180・180〜600・600〜)ごとの、
    1 日あたりの損益(その帯の P_t の日ごとの和を、全部の日で平均)。区間は日の塊(diag_tables.mean_ci)。全期間・前半・後半。
    セッションの始まり: jst_day = 日本時間 0 時、bf_maint = UTC 19 時(足の始まりの時刻で決める。カードと同じ)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c8_session_mean_revert/redo2_2026-10-05/c8_more.py
出力: このフォルダの C8_MORE.md
"""
import os
import sys
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/trade/scripts/analysis")
sys.path.insert(0, "/home/user/trade/src")
import diag_tables as dt  # noqa: E402

NS, MIN, DAY = 10**9, 60 * 10**9, 86400 * 10**9
M = os.path.join(HERE, "..", "measure")


def dnum(s):
    return (date.fromisoformat(s) - date(1970, 1, 1)).days


def ratio(dk, vals, pd):
    nums = np.array([dnum(x) for x in pd])
    lo, hi = nums.min(), nums.max()
    q = (dk >= lo) & (dk <= hi)
    su = np.bincount(dk[q] - lo, weights=vals[q], minlength=hi - lo + 1)
    cn = np.bincount(dk[q] - lo, minlength=hi - lo + 1)
    return dt.group_ratio_ci(pd, {x: float(su[n - lo]) for x, n in zip(pd, nums)}, {x: int(cn[n - lo]) for x, n in zip(pd, nums)})


def main():
    f = lambda q: "—" if q["per_trade"] is None else f"{q['per_trade']:+.3f} [{q['lo']:+.3f}, {q['hi']:+.3f}]"  # noqa: E731
    t1 = ["## (1) 決定ごとの 1 分を持ち高の向きで分ける(bp/決定)", "",
          "| 変種 | 向き | 期間 | 決定 | 本体(始値 → 始値)[区間] | 24 時間後の対照 [区間] | 24 時間前の対照 [区間] |", "|---|---|---|---|---|---|---|"]
    t2 = ["## (2) セッションの始まりからの経過時間の帯ごとの 1 日あたり(bp/日、その帯の損益の日ごとの和の平均)", "",
          "| 変種 | 帯(分) | 全期間 [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    for v, start_utc_sec in (("jst_day", 15 * 3600), ("bf_maint", 19 * 3600)):
        _z = np.load(os.path.join(M, v, "run.npz"))
        z = {k: _z[k] for k in _z.files}
        d = np.flatnonzero(z["decided"])
        m = len(d) - 2
        bar, fill, ex = d[:m], d[1:m + 1], d[2:m + 2]
        op = z["open"]
        e = z["exposure"][bar]
        p = e * (op[ex] / op[fill] - 1) * 1e4
        s_dec, o_dec = z["start_ns"][d], op[d]
        dk = ((z["end_ns"][bar] // NS + 9 * 3600) // 86400).astype(np.int64)
        days = sorted(l.split(",")[0] for l in open(os.path.join(M, v, "daily.csv")).read().splitlines()[1:])
        half = len(days) // 2
        parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
        pnum = {k: np.array([dnum(x) for x in pd]) for k, pd in parts.items()}

        def ctrl(shift):
            j = np.searchsorted(s_dec, z["start_ns"][fill] + shift, side="left")
            ok = (j >= 0) & (j + 1 < len(s_dec))
            j = np.clip(j, 0, len(s_dec) - 2)
            ok &= np.abs(s_dec[j] - (z["start_ns"][fill] + shift)) < 5 * MIN
            return e * (o_dec[j + 1] / o_dec[j] - 1) * 1e4, ok
        cp, okp = ctrl(DAY)
        cm, okm = ctrl(-DAY)
        for sn, msk in (("買い(平均より下)", e > 0), ("売り(平均より上)", e < 0)):
            for pn, pd in parts.items():
                q = msk & okp & okm & np.isin(dk, pnum[pn])
                t1.append(f"| {v} | {sn} | {pn} | {int(q.sum()):,} | {f(ratio(dk[q], p[q], pd))} | {f(ratio(dk[q], cp[q], pd))} | {f(ratio(dk[q], cm[q], pd))} |")
        # 経過時間: 決定の足の始まり(= end − 60 秒)とセッションの始まりの差
        st = z["end_ns"][bar] // NS - 60
        el = ((st - start_utc_sec) % 86400) // 60
        for lo, hi in ((0, 60), (60, 180), (180, 600), (600, 1440)):
            msk = (el >= lo) & (el < hi)
            u = np.bincount(dk[msk] - dk.min(), weights=p[msk], minlength=dk.max() - dk.min() + 1)
            cells = []
            for pn, pd in parts.items():
                x = [float(u[dnum(y) - dk.min()]) if 0 <= dnum(y) - dk.min() < len(u) else 0.0 for y in pd]
                r = dt.mean_ci(x)
                cells.append(f"{r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]")
            t2.append(f"| {v} | {lo}〜{hi} | {cells[0]} | {cells[1]} | {cells[2]} |")
    out = ["# カード 8 の足し: 対照を向きで分ける・セッションの経過時間の帯", ""] + t1 + [""] + t2
    open(os.path.join(HERE, "C8_MORE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
