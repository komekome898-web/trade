#!/usr/bin/env python3
"""カツオの改良の周 2: 組んだ形 C_N と時間だけ T_N の差(dC − dT)に区間を付ける(K-048 の関門 ② 2 回目の直す 2、
READ_R2/RESULTS.md の次の手 (2'))。

読み方の決まり(表を見る前に、この台本と `tests/research/test_c2_read_r2_ct.py` で固めた):

CT1 系列: N = 6〜12 の C_N = weak_f15_rgate_close_a_time<N> と T_N = weak_f15_close_a_time<N>。日ごとの損益は
    c2_read_r2.read_daily(出の時刻の UTC の日、取引の無い日は 0、日の範囲は基準 weak_f15_close_a の summary の period)。
CT2 出すもの: C_N − T_N の日ごとの差の平均・95% 区間・MDE(c2_read_r2.paired_ci と同じ: 塊 5 日・1,000 回・
    種 20261004・5% 両側・80%)を、全期間と 2019-01-01〜2023-12-17(門の履歴が 1 年に満たない期間を外す)の 2 つで。
CT3 区間の両端と MDE を並べるだけ。「どちらが良い」の境は置かない(A-12)。7 通りの中のどれかを選ぶ読みにしない。
    経費なし。探索の読み。

出力: runs/READ_R2/CT_TABLES.md と ct.json。

    PYTHONPATH=src python3 scripts/w4_measure/c2_read_r2_ct.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_r2 as r2  # noqa: E402

LATE_FROM = date(2019, 1, 1)


def slice_from(x: list[float], lo: date, start: date) -> list[float]:
    """CT2。lo から始まる日ごとの列のうち start 以降。"""
    k = max(0, (start - lo).days)
    return x[k:]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r2.rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    with open(os.path.join(a.root, r2.B, "summary.json"), encoding="utf-8") as fh:
        p0, p1 = json.load(fh)["period"]
    lo = datetime.fromisoformat(p0.replace("Z", "+00:00")).date()
    hi = (datetime.fromisoformat(p1.replace("Z", "+00:00")) - timedelta(microseconds=1)).date()
    rows = []
    for n in r2.NS:
        c = r2.read_daily(os.path.join(a.root, r2.C(n)), lo, hi)
        t = r2.read_daily(os.path.join(a.root, r2.T(n)), lo, hi)
        if c is None or t is None:
            rows.append({"n": n, "all": None, "late": None})
            continue
        rows.append({"n": n, "all": r2.paired_ci(c, t),
                     "late": r2.paired_ci(slice_from(c, lo, LATE_FROM), slice_from(t, lo, LATE_FROM))})
    L = ["# カツオ 改良の周 2: 組んだ形 − 時間だけ(dC − dT)の区間", "",
         "`scripts/w4_measure/c2_read_r2_ct.py` が出した。読み方の決まり CT1〜CT3 はその台本の docstring。bp/日、経費の前。", "",
         "| N | 全期間 平均 [区間] | MDE | 2019〜2023 平均 [区間] | MDE |", "|---|---|---|---|---|"]
    for r in rows:
        f = lambda c: "— | —" if not c else f"{c['mean']:+.2f} [{c['lo']:+.2f}, {c['hi']:+.2f}] | {c['mde']:.2f}"
        L.append(f"| {r['n']} | {f(r['all'])} | {f(r['late'])} |")
    out = os.path.join(a.root, "READ_R2")
    with open(os.path.join(out, "CT_TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(out, "ct.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"rows {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
