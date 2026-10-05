"""カード 6: 週明けの行が NY 17 時(日 21・22 時 UTC)から外れた週の確かめ(アドバイザーの指摘、2026-10-05)。
(1) 月曜 0 時 UTC に見つけた 3 週と年末年始の 2 週について、USDJPY の置き場(fx_usdjpy_1m_20170801_20221231、封印の前)の
    日曜 20 時 〜 r + 5 分(UTC)の行を、前の週の最後の値と並べて出す(行が無いか・値が前の週と同じまま続いたか)。
(2) c6_weeks.csv から、外れた 5 週の btc の損益が、|g_btc| の上の帯・前半・後半の和に占める分。
台本の試験は無い。
    python3 docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/offhour_check.py
出力: このフォルダの OFFHOUR_CHECK.md
"""
import csv
import gzip
import os
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/trade"


def main():
    wk = list(csv.DictReader(open(os.path.join(HERE, "c6_weeks.csv"))))
    off = [w for w in wk if not (datetime.fromisoformat(w["r_utc"].replace("Z", "+00:00")).weekday() == 6
                                 and datetime.fromisoformat(w["r_utc"].replace("Z", "+00:00")).hour in (21, 22))]
    want = {}
    for w in off:
        r = datetime.fromisoformat(w["r_utc"].replace("Z", "+00:00"))
        sun = (r - timedelta(days=(r.weekday() + 1) % 7)).replace(hour=20, minute=0)  # その週の日曜 20 時 UTC
        want[w["r_utc"]] = (sun, r + timedelta(minutes=5))
    rows = {k: [] for k in want}
    last_prev = {k: None for k in want}
    with gzip.open(os.path.join(REPO, "backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz"), "rt") as fh:
        rd = csv.reader(fh)
        next(rd)
        for row in rd:
            t = datetime.fromisoformat(row[0])
            for k, (a, b) in want.items():
                if a - timedelta(days=3) <= t < a:
                    last_prev[k] = (row[0], row[4], row[5])
                if a <= t < b:
                    rows[k].append((row[0], row[4], row[5]))
    out = ["# カード 6: 外れた週の USDJPY の行(置き場の生の行。close・volume)", ""]
    for k in sorted(want):
        a, b = want[k]
        out += [f"## 週明けの行 r = {k}(見た範囲 {a.isoformat()} 〜 {b.isoformat()})", "",
                f"- 範囲より前の最後の行(3 日前まで): {last_prev[k]}",
                f"- 範囲の行の数: {len(rows[k])}"]
        if rows[k]:
            vals = [x[1] for x in rows[k]]
            chg = [i for i in range(1, len(vals)) if vals[i] != vals[i - 1]]
            out.append(f"- 範囲の最初の行 {rows[k][0]}、最後の行 {rows[k][-1]}")
            out.append(f"- 範囲の中で値が変わった最初の行: {rows[k][chg[0]] if chg else '無し'}")
            vol0 = sum(1 for x in rows[k] if float(x[2] or 0) == 0)
            out.append(f"- 量 0 の行: {vol0} / {len(rows[k])}")
        out.append("")
    # (2) 和に占める分
    gb = np.array([abs(float(w["g_btc_bp"])) for w in wk])
    q2 = float(np.quantile(gb, 2 / 3))
    days = sorted(l.split(",")[0] for l in open(os.path.join(HERE, "..", "measure", "btc", "daily.csv")).read().splitlines()[1:])
    edge = days[len(days) // 2]
    top = [w for w in wk if abs(float(w["g_btc_bp"])) >= q2]
    offk = {w["r_utc"] for w in off}
    f = lambda xs: sum(float(w["pnl_btc"]) for w in xs)  # noqa: E731
    first = [w for w in wk if w["jst_day"] < edge]
    second = [w for w in wk if w["jst_day"] >= edge]
    out += ["## 外れた 5 週の btc の損益が占める分", "",
            "| 集まり | 週 | btc の和 | うち外れた週 | その和 | 割合 |", "|---|---|---|---|---|---|"]
    for nm, xs in (("全部", wk), (f"|g_btc| の上の帯({q2:.1f} bp 以上)", top), (f"前半(日本時間の日 < {edge})", first), (f"後半(≥ {edge})", second)):
        o = [w for w in xs if w["r_utc"] in offk]
        out.append(f"| {nm} | {len(xs)} | {f(xs):+,.1f} | {len(o)} | {f(o):+,.1f} | {f(o) / f(xs):.1%} |")
    open(os.path.join(HERE, "OFFHOUR_CHECK.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
