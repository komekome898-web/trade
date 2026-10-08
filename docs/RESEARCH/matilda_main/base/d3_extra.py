"""基準(base)の D3 の足し: 出の理由 × 年、段の数 × 前半/後半 の 取引の数・損益の和(円)・1 取引あたり(円)。記述だけ(結果で決まる群)。
年 = 出の時刻の UTC の年。前半/後半の境は D1 と同じ 2019-12-09(UTC)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d3_extra.py
"""
import csv, gzip
from collections import defaultdict
rows = list(csv.DictReader(gzip.open("backtest_runs_shared/matilda_main_trades/base/trades.csv.gz", "rt")))
CUT = "2019-12-09"
t = defaultdict(lambda: [0, 0.0])
for r in rows:
    y = r["exit_t"][:4]; k = r["exit_reason"]
    t[(y, k)][0] += 1; t[(y, k)][1] += float(r["pnl_jpy"])
ys = sorted({y for y, _ in t})
print("年 | 利確 close 本・和 | ブレイク break 本・和 | 成行 market 本・和 | ブレイクの割合")
for y in ys:
    c, b, m = t[(y, "close")], t[(y, "break")], t[(y, "market")]
    n = c[0] + b[0] + m[0]
    print(y, c[0], round(c[1]), "|", b[0], round(b[1]), "|", m[0], round(m[1]), "|", f"{b[0]/n:.3f}",
          "| 利確 1 本あたり", round(c[1] / max(c[0], 1), 1), "ブレイク 1 本あたり", round(b[1] / max(b[0], 1), 1))
h = defaultdict(lambda: [0, 0.0])
for r in rows:
    half = "前半" if r["exit_t"][:10] < CUT else "後半"
    h[(half, int(r["levels"]), r["exit_reason"])][0] += 1
    h[(half, int(r["levels"]), r["exit_reason"])][1] += float(r["pnl_jpy"])
print("区切り | 段 | 出の理由 | 本 | 和 | 1 本あたり")
for k in sorted(h):
    print(*k, h[k][0], round(h[k][1]), round(h[k][1] / h[k][0], 1))
