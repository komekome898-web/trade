#!/usr/bin/env python3
"""カード 1(今の paper bot)の日ごとの損益を、期間(2018 年まで / 2019 年から)と年で分けて並べる(2026-10-04、L-639・L-640)。

知見台帳の書き直しの出所。新しい走らせはしない: 既にある日ごとの系列(`overlap_daily.SERIES`、経費前・持ち高 1 単位・
日本時間の日、2017-08-18〜2023-12-17)を読むだけ。封印の窓は読まない。

表 1: 今の paper bot の 1 日あたりの損益(bp/日)と 95% 区間(循環の塊 5 日・1,000 回・種 20261004)。
表 2: 3 本(今の paper bot・カツオ原典 1 分・円の上乗せ 1h)の組ごとの、日ごとの損益の相関と「良い 5% の日の重なり」
      (片方の損益が上位 5% の日のうち、もう片方でも上位 5% だった日の割合。2 本に関係が無ければ約 0.05)。
      2 本に共通の日だけ。期間で分けたときは、その期間の中で上位 5% を決め直す。

    PYTHONPATH=src python3 scripts/w4_measure/c1_period_split.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overlap_daily as ov  # noqa: E402

OUT = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "c1_xborder_mom", "PERIOD_SPLIT.md")
C1 = "今の paper bot"
TRIO = (C1, "カツオ原典 1分", "円の上乗せ 1h")
PERIODS = (("全期間", lambda d: True), ("2018 年まで", lambda d: d < "2019-01-01"), ("2019 年から", lambda d: d >= "2019-01-01"))


def mean_ci(x: list[float]) -> tuple[float, float, float]:
    from bot.bt.validation import block_bootstrap_ci
    c = block_bootstrap_ci([float(v) for v in x], block_len=5, n_resamples=1000, seed=20261004, alpha=0.05,
                           method="circular", statistic="mean")
    return c.estimate, c.lo, c.hi


def top_overlap(a: dict, b: dict, days: list[str], q: float = 0.95) -> float:
    def top(s):
        v = np.array([s[d] for d in days])
        thr = np.quantile(v, q)
        return {d for d in days if s[d] >= thr}
    ta, tb = top(a), top(b)
    return len(ta & tb) / len(ta)


def main() -> int:
    src = {n: (k, d) for n, k, d in ov.SERIES}
    ser = {n: ov.load_series(*src[n]) for n in TRIO}
    a = ser[C1]
    L = ["# カード 1(今の paper bot)の期間と年で分けた損益と、3 本の重なり", "",
         "`scripts/w4_measure/c1_period_split.py` が出した(手で書いていない)。経費前・持ち高 1 単位・日本時間の日。", "",
         "## 表 1 今の paper bot の 1 日あたりの損益(bp/日)", "",
         "| 期間 | 日数 | 1 日あたり | 95% 区間 |", "|---|---|---|---|"]
    rows = [(lab, f) for lab, f in PERIODS] + [(y, (lambda y: lambda d: d[:4] == y)(y)) for y in map(str, range(2017, 2024))]
    for lab, f in rows:
        x = [a[d] for d in sorted(a) if f(d)]
        m, lo, hi = mean_ci(x)
        L.append(f"| {lab} | {len(x)} | {m:+.1f} | [{lo:+.1f}, {hi:+.1f}] |")
    L += ["", "## 表 2 3 本の組ごとの相関と良い 5% の日の重なり(割合。関係が無ければ約 0.05)", "",
          "| 組 | 期間 | 共通の日数 | 相関 | 良い 5% の日の重なり |", "|---|---|---|---|---|"]
    for i in range(3):
        for j in range(i + 1, 3):
            x, y = ser[TRIO[i]], ser[TRIO[j]]
            common = sorted(set(x) & set(y))
            for lab, f in PERIODS:
                days = [d for d in common if f(d)]
                r = float(np.corrcoef([x[d] for d in days], [y[d] for d in days])[0, 1])
                L.append(f"| {TRIO[i]} × {TRIO[j]} | {lab} | {len(days)} | {r:.2f} | {top_overlap(x, y, days):.2f} |")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
