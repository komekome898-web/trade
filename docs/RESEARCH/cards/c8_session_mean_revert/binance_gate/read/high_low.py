"""カード 8 の Binance の門の読み(事後の比べ。事前登録の主の量ではない): 区分 高 − 低 の 1 日あたりの差を、
bitFlyer の台帳 K-032 の「高 − 低 +69.88」と同じ量で出す。読み口 `scripts/analysis/diag_tables.py` の mean_ci・diff_ci を呼ぶだけ。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/read/high_low.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../../../.."))
sys.path.insert(0, os.path.join(ROOT, "scripts/analysis"))
import diag_tables as dt  # noqa: E402

BG = os.path.dirname(HERE)


def daily(name: str) -> dict[str, float]:
    with open(os.path.join(BG, "measure/jst_day", name), encoding="utf-8") as fh:
        return {r["day"]: float(r["pnl_bp"]) for r in csv.DictReader(fh)}


def main() -> int:
    with open(os.path.join(BG, "split/classes.json"), encoding="utf-8") as fh:
        cj = json.load(fh)
    cls, hb = cj["classes"], cj["half_boundary_day"]
    lines = ["# 区分 高 − 低(事後の比べ。事前登録の主の量ではない)", "",
             "`high_low.py` が出した。bp/日、経費の前。区間は 2 つの区分の日をそれぞれ日の塊(5 日・1,000 回・種 20261004)で選び直した差(`diag_tables.diff_ci`)。",
             f"前半・後半の境(後半の最初の日)= {hb}(区分の事前登録と同じ)。", ""]
    for fill, name in (("始値 → 始値", "daily.csv"), ("中ほど", "daily_mid.csv")):
        d = daily(name)
        lines += [f"## 約定 = {fill}", "", "| 期間 | 低 [区間](日数) | 高 [区間](日数) | 高 − 低 [区間] |", "|---|---|---|---|"]
        for lab, sel in (("全期間", lambda x: True), ("前半", lambda x: x < hb), ("後半", lambda x: x >= hb)):
            days = sorted(x for x in cls if sel(x))
            lo = [d.get(x, 0.0) for x in days if cls[x] == "low"]
            hi = [d.get(x, 0.0) for x in days if cls[x] == "high"]
            rl, rh = dt.mean_ci(lo), dt.mean_ci(hi)
            diff = dt.diff_ci(lo, hi)
            lines.append(f"| {lab} | {dt._ci(rl)}({len(lo)}) | {dt._ci(rh)}({len(hi)}) | {dt._ci(diff)} |")
        lines.append("")
    out = os.path.join(HERE, "high_low.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
