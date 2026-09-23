#!/usr/bin/env python3
"""Count, per survey target and viewpoint, the scenes graded 正解と一致 in
survey_results/*.tsv (the runner's output, copied from the scene keeper's
runs). Prints a Markdown table; CONSIDERED.md quotes it. Standard library only.

Usage: python3 survey_counts.py
"""
from __future__ import annotations

import csv
import collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_NO = {"opp_basana": 1, "opp_backtrader": 2, "opp_lib_pybroker": 4, "opp_ziplime": 6, "opp_fast_trade": 10,
              "opp_pybotters": 12, "opp_zipline_reloaded": 18, "opp_vnpy": 20, "opp_hftbacktest": 23, "opp_quantcore": 34,
              "opp_rqalpha": 53, "opp_finmarketpy": 54, "opp_backtesting": 55, "opp_qf_lib": 62, "opp_quanttrader": 68,
              "opp_freqtrade": 75, "opp_qstrader": 121, "opp_pyalgotrade": 122, "repro_33_execution_simulator": 33}


def main() -> None:
    rows, vps = [], set()
    for p in sorted((HERE / "survey_results").glob("*.tsv")):
        hit, tot, same = collections.Counter(), collections.Counter(), 0
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                tot[r["viewpoint"]] += 1
                hit[r["viewpoint"]] += r["correctness"] == "正解と一致"
                same += r["reproducibility"] == "2 回の実行で同じ"
        vps |= set(tot)
        rows.append((CATALOG_NO.get(p.stem, 0), p.stem, hit, tot, same, sum(tot.values())))
    vps = sorted(vps)
    print("| 候補 | 対象 | " + " | ".join(f"{v}" for v in vps) + " | 2 回の実行で同じ |")
    print("|---" * (len(vps) + 3) + "|")
    for no, name, hit, tot, same, n in sorted(rows):
        print(f"| {no} | {name} | " + " | ".join(f"{hit[v]}/{tot[v]}" for v in vps) + f" | {same}/{n} |")


if __name__ == "__main__":
    main()
