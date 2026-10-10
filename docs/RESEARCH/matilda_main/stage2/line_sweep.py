"""L-975: I5(利確 2 ボラ)に I6 の門(line_setting 4・5・6・7・8 ボラ。7・8 は L-976)を足した本を、I5・I5 + I1 0.49 と並べる(gate_sweep.py を写して本の一覧と差の相手を変えた)。本そのものの 1 日あたり(前半・後半・年ごと)と区間。
日 = 出の時刻の UTC の日(読み口 diag_tables と同じ)。取引の無い日は 0 円。前半 2015-12-01〜2019-12-08・後半 2019-12-09〜2023-12-17。
区間 95%・日の塊(循環 5 日・1,000 回・種 20261004)。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/line_sweep.py > docs/RESEARCH/matilda_main/stage2/line_sweep.out
"""
import numpy as np
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades/"
RUNS = [("base", "基準(利確 3 ボラ)"), ("exit_2", "I5(利確 2 ボラ)"), ("exit_2_dev_0.49", "I5 + I1 0.49"),
        ("exit_2_line_4", "I5 + I6 4"), ("exit_2_line_5", "I5 + I6 5"), ("exit_2_line_6", "I5 + I6 6"), ("exit_2_line_7", "I5 + I6 7"), ("exit_2_line_8", "I5 + I6 8")]
ALL = pd.date_range("2015-12-01", "2023-12-17").strftime("%Y-%m-%d")
PER = [("前半", "2015-12-01", "2019-12-08"), ("後半", "2019-12-09", "2023-12-17")] + \
      [(str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2016, 2024)]
rng = np.random.default_rng(20261004)


def ci(v):
    n = len(v)
    st = rng.integers(0, n, size=(1000, int(np.ceil(n / 5))))
    idx = (st[:, :, None] + np.arange(5)).reshape(1000, -1)[:, :n] % n
    m = v[idx].mean(axis=1)
    return f"{v.mean():+.0f} [{np.percentile(m, 2.5):+.0f}, {np.percentile(m, 97.5):+.0f}]"


daily = {}
print("| 本 | 取引 | 全期間の和(円) | 前半 本 | 後半 本 |")
print("|---|---|---|---|---|")
for r, lab in RUNS:
    d = pd.read_csv(T + r + "/trades.csv.gz", usecols=["exit_t", "pnl_jpy"])
    d["day"] = d.exit_t.str[:10]
    daily[r] = d.groupby("day").pnl_jpy.sum().reindex(ALL, fill_value=0)
    print(f"| {lab} | {len(d):,} | {d.pnl_jpy.sum():+,.0f} | {(d.day < '2019-12-09').sum():,} | {(d.day >= '2019-12-09').sum():,} |")
print("\n## 本そのものの 1 日あたり(円/日)[区間]\n")
print("| 期間 | " + " | ".join(l for _, l in RUNS) + " |")
print("|---|" + "---|" * len(RUNS))
for p, a, b in PER:
    print(f"| {p} | " + " | ".join(ci(daily[r][(daily[r].index >= a) & (daily[r].index <= b)].to_numpy()) for r, _ in RUNS) + " |")
print("\n## I5 + I6 の各本 − I5 の同じ日どうしの差(円/日)[区間]\n")
print("| 期間 | I6 4 − I5 | I6 5 − I5 | I6 6 − I5 | I6 7 − I5 | I6 8 − I5 | I1 0.49 − I5 |")
print("|---|---|---|---|---|---|---|")
for p, a, b in PER:
    m = (daily["exit_2"].index >= a) & (daily["exit_2"].index <= b)
    print(f"| {p} | " + " | ".join(ci((daily[r] - daily["exit_2"])[m].to_numpy()) for r in ("exit_2_line_4", "exit_2_line_5", "exit_2_line_6", "exit_2_line_7", "exit_2_line_8", "exit_2_dev_0.49")) + " |")
