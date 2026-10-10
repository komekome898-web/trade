"""族 alert の D0 の確かめ(待ち 5・10 分の 2 本、L-947)。alert_check.py (1)(2) と同じ計算: 時間切れの成行で閉じた取引の保有の分
(signal_t から exit_t まで)の最小・中央値・最大と、2 × alert_count 分以下の成行の本数。【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/alert/alert_check_short.py > docs/RESEARCH/matilda_main/alert/alert_check_short.out
"""
import csv, gzip, statistics
from datetime import datetime
for r, ac in (("alert_10", 10), ("alert_5", 5)):
    h = []
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        if t["exit_reason"] == "market":
            h.append((datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60)
    early = sum(1 for x in h if x <= 2 * ac)
    print(r, "alert_count", ac, "分 / 2 倍", 2 * ac, "分 | 成行", len(h), "本 | 保有の分 最小", min(h), "中央値", statistics.median(h), "最大", max(h), "| 2 倍以下の成行", early)
# (3)(3b) alert_check.py と同じ: 出の理由ごとの本数と、20 分(基準の alert_count)を超えて持った取引の本数・和、その出の理由別
from collections import Counter
for r in ("base", "alert_10", "alert_5"):
    c = Counter(); c20 = Counter(); s20 = Counter(); n = 0
    for t in csv.DictReader(gzip.open(f"backtest_runs_shared/matilda_main_trades/{r}/trades.csv.gz", "rt")):
        n += 1; c[t["exit_reason"]] += 1
        if (datetime.fromisoformat(t["exit_t"]) - datetime.fromisoformat(t["signal_t"])).total_seconds() / 60 > 20:
            c20[t["exit_reason"]] += 1; s20[t["exit_reason"]] += float(t["pnl_jpy"])
    n20 = sum(c20.values())
    print(r, "取引", n, "出の理由", dict(c), "| 20 分超", n20, f"({n20/n:.1%})", "和", round(sum(s20.values())), "| 出の理由別", {k: (c20[k], round(s20[k])) for k in sorted(c20)})
