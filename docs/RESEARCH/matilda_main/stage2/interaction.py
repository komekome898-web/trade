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

# 希釈の見込み(相方の D10 の指摘 1、走らせた後に足した): 線の効きが取引に一様に散らばるとき、門の後に残る取引に効く分は
# (門の走らせにもある基準の合図の割合)×(線 − 基準)。相互作用の見込み = −(門で建てない基準の合図の割合)×(線 − 基準)。
import diag_paths as dp  # noqa: E402

base_t = dp.read_trades_csv(os.path.join(T, RUNS["基準"]))
gate_sig = {t["signal_ns"] for t in dp.read_trades_csv(os.path.join(T, RUNS["門"])) if "signal_ns" in t}
print("\n希釈の見込み(相互作用 ≈ −(門で建てない基準の合図の割合)×(線 − 基準)の点):\n")
print("| 半分 | 基準の取引 | うち門の走らせに無い合図 | 割合 | 線 − 基準 の点 | 見込み | 観測の相互作用 [区間] |")
print("|---|---|---|---|---|---|---|")
for name, idx in (("前半", fi), ("後半", se)):
    tt = [t for t in base_t if (dt.utc_day(t["signal_ns"]) < CUT) == (name == "前半")]
    nb = sum(1 for t in tt if t["signal_ns"] not in gate_sig)
    frac = nb / len(tt)
    line = dt.mean_ci([rows["線 − 基準"][i] for i in idx])["mean"]
    obs = dt.mean_ci([rows["相互作用 = 組 − 門 − 線 + 基準"][i] for i in idx])
    print(f"| {name} | {len(tt)} | {nb} | {frac:.3f} | {line:+.1f} | {-frac*line:+.1f} | {obs['mean']:+.1f} [{obs['lo']:+.1f}, {obs['hi']:+.1f}] |")
