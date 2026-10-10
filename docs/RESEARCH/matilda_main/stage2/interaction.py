#!/usr/bin/env python3
"""段 2 の 1 本(幅の下の門 0.5133% × ブレイクの線を近づける 0.25)の読み。式は走らせる前に `STAGE2_MATERIALS.md` §7 に書いた。

相互作用(日ごと) = (組 − 基準) − [(門 − 基準) + (線 − 基準)] = 組 − 門 − 線 + 基準(円/日、取引の無い日は 0 円、4 本の日の和集合)。
前半・後半の境 2019-12-09。区間と MDE は読み口 `diag_tables.mean_ci`(日の塊 5 日・1,000 回・種 20261004)。【試験の無い台本の値】。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/stage2/interaction.py > docs/RESEARCH/matilda_main/stage2/interaction.out
"""
import os
import sys

sys.path.insert(0, "scripts/analysis")
sys.path.insert(0, "scripts/w4_measure")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades"
RUNS = {"基準": "base", "門": "range_lo_p50", "線": "break_dist_0.25", "組": "range_lo_p50_break_dist_0.25"}
CUT = "2019-12-09"

ser = {k: dt.daily_series(dt.load_run(os.path.join(T, v))) for k, v in RUNS.items()}
days = sorted(set().union(*[set(s) for s in ser.values()]))
g = lambda k, d: ser[k].get(d, 0.0)  # noqa: E731
rows = {
    "組 − 基準": [g("組", d) - g("基準", d) for d in days],
    "門 − 基準": [g("門", d) - g("基準", d) for d in days],
    "線 − 基準": [g("線", d) - g("基準", d) for d in days],
    "相互作用 = 組 − 門 − 線 + 基準": [g("組", d) - g("門", d) - g("線", d) + g("基準", d) for d in days],
}
print(f"日 {len(days)}({days[0]}〜{days[-1]})。円/日 [区間](MDE)\n")
print("| 量 | 全期間 | 前半 | 後半 |")
print("|---|---|---|---|")
fi = [i for i, d in enumerate(days) if d < CUT]
se = [i for i, d in enumerate(days) if d >= CUT]
for name, v in rows.items():
    cells = []
    for idx in (range(len(days)), fi, se):
        r = dt.mean_ci([v[i] for i in idx])
        cells.append(f"{r['mean']:+.1f} [{r['lo']:+.1f}, {r['hi']:+.1f}]({r['mde']:.1f})")
    print(f"| {name} | " + " | ".join(cells) + " |")
