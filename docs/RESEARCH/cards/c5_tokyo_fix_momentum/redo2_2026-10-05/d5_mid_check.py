"""カード 5 の D5 の確かめ(アドバイザーの止める 1、2026-10-05)。保存済みの run.npz だけ。台本の試験は無い。
(1) 向きが変わった決定(持ち高の符号が前の決定と違い、0 でない = 取引の建て)の P_t の和と、全体の和に占める割合。
    持ち続けた決定(符号が前と同じ)の和。日本時間の時刻の帯ごとの、向きが変わった決定の数・P_t の和と、持ち続けた決定の P_t の和。
(2) 約定の値段を使わない量: 足の (高値 + 安値) ÷ 2 を中ほどの値の代わりにして、決定 t の次の足 t+1 から次の次の足 t+2 までの
    中ほどの動き × 持ち高の符号(本体)。対照 = 24 時間後の同じ時刻の足どうし(t+1 の始まり + 24 時間 の足と、その次の空でない足)。
    向きが変わった決定・持ち続けた決定・全部 × 全期間・前半・後半。区間は日の塊(群の和 ÷ 群の数)。日 = 決定の日本時間の日。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_mid_check.py
出力: このフォルダの D5_MID_CHECK.md
"""
import collections
import os
import sys
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/trade"
sys.path.insert(0, os.path.join(REPO, "scripts/analysis"))
sys.path.insert(0, os.path.join(REPO, "src"))
import diag_tables as dt  # noqa: E402

NS, MIN = 10**9, 60 * 10**9


def main():
    z = np.load(os.path.join(HERE, "..", "measure", "default", "run.npz"))
    d = np.flatnonzero(z["decided"])
    m = len(d) - 2
    bar, fill, ex = d[:m], d[1:m + 1], d[2:m + 2]
    op, hi, lo, end_ns, start_ns = z["open"], z["high"], z["low"], z["end_ns"], z["start_ns"]
    e = z["exposure"][bar]
    p = e * (op[ex] / op[fill] - 1.0) * 1e4
    s = np.sign(e)
    prev = np.concatenate([[0.0], s[:-1]])
    flip = (s != 0) & (s != prev)
    hold = (s != 0) & (s == prev)
    total = p.sum()
    secs = end_ns[bar] // NS
    jday = (secs + 9 * 3600) // 86400
    hour = (((secs + 9 * 3600) % 86400) - 1) // 3600
    out = ["# カード 5: 向きが変わった決定と持ち続けた決定(run.npz から。bp、経費の前)", "",
           f"- 全体の P_t の和 {total:+,.1f}。向きが変わった決定 {flip.sum():,} 本・和 {p[flip].sum():+,.1f}({p[flip].sum() / total:.1%})、"
           f"持ち続けた決定 {hold.sum():,} 本・和 {p[hold].sum():+,.1f}({p[hold].sum() / total:.1%})", "",
           "## 時刻の帯ごと(決定の時刻 = 足の終わりの日本時間の時)", "",
           "| 帯 | 向きが変わった決定 | その和 | 持ち続けた決定 | その和 |", "|---|---|---|---|---|"]
    for h in range(10):
        a, b = flip & (hour == h), hold & (hour == h)
        out.append(f"| {h} 時台 | {a.sum():,} | {p[a].sum():+,.1f} | {b.sum():,} | {p[b].sum():+,.1f} |")
    # (2) 中ほどの値
    mid = (hi + lo) / 2.0
    s_dec = start_ns[d]
    mid_dec = mid[d]

    def at(ns):
        j = np.searchsorted(s_dec, ns, side="left")
        ok = (j + 1 < len(s_dec))
        j = np.minimum(j, len(s_dec) - 2)
        ok &= (s_dec[j] - ns) < 5 * MIN
        return j, ok
    body = s * (mid[ex] / mid[fill] - 1.0) * 1e4
    jc, okc = at(start_ns[fill] + 86400 * NS)
    ctrl = s * (mid_dec[jc + 1] / mid_dec[jc] - 1.0) * 1e4
    days = sorted({(date(1970, 1, 1) + timedelta(days=int(k))).isoformat() for k in np.unique(jday)})
    dayarr = np.array([(date(1970, 1, 1) + timedelta(days=int(k))).isoformat() for k in jday])
    half = len(days) // 2
    parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
    out += ["", f"## 中ほどの値((高値 + 安値) ÷ 2)で測った t+1 → t+2 の動き × 持ち高の符号(bp/決定)。前半・後半の境 {days[half]}", "",
            "比べのために、同じ決定の始値 → 始値(= P_t)も並べる。", "",
            "| 決定 | 期間 | 決定の数 | 始値 → 始値 [区間] | 中ほど 本体 [区間] | 中ほど 対照 [区間] | 中ほど 本体 − 対照 [区間] |",
            "|---|---|---|---|---|---|---|"]
    f = lambda q: "—" if q["per_trade"] is None else f"{q['per_trade']:+.3f} [{q['lo']:+.3f}, {q['hi']:+.3f}]"  # noqa: E731
    for nm, msk in (("向きが変わった", flip), ("持ち続けた", hold), ("全部(持ち高 ≠ 0)", s != 0)):
        mm = msk & okc
        for pn, pd in parts.items():
            pm = mm & np.isin(dayarr, pd)
            r = {}
            for k, v in (("p", p), ("b", body), ("c", ctrl), ("d", body - ctrl)):
                su, cn = collections.defaultdict(float), collections.defaultdict(int)
                for dd, x in zip(dayarr[pm], v[pm]):
                    su[dd] += float(x)
                    cn[dd] += 1
                r[k] = dt.group_ratio_ci(pd, su, cn)
            out.append(f"| {nm} | {pn} | {r['b']['trades']:,} | {f(r['p'])} | {f(r['b'])} | {f(r['c'])} | {f(r['d'])} |")
    open(os.path.join(HERE, "D5_MID_CHECK.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
