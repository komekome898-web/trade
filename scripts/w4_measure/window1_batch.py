#!/usr/bin/env python3
"""探索の窓 1 の走らせの一覧(PREREG §2・§7。走らせ 1 回: カツオ 3 本・マチルダ 4 本。追加禁止)。

引数は元の走らせ(window1_read.ORIG)と同じ形 + 窓の引数 --window1 だけ(--measure-from は窓の既定 2023-12-18T00:00Z)。
  カツオ: c2_limit_batch.py の _r2(+ K-B は _r2g)と同じ。K-A = 時間で降りる N = 6、K-B = 直前 365 日の門 × N = 9。
  マチルダ: c4_limit_batch.py の v37(引数なし)と R2_ratio_gate_rolling_center_4_3 と同じ、良い側・悪い側。
置き場は docs/RESEARCH/WINDOW1/runs/<名前>(window1_read.py が読む名前)。読みの台本は走らせの params を元の走らせと突き合わせる。

    W4_WINDOW1=P2-08-explore PYTHONPATH=src python3 scripts/w4_measure/window1_batch.py --card k|m [--only 名前] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "docs", "RESEARCH", "WINDOW1", "runs")

_K = ["--series", "a", "--design", "k1", "--foot-min", "15", "--entry", "a", "--fill", "close", "--fill-side", "good"]
_KG = ["--vol-gate", "--vol-gate-mode", "rolling"]
_MA = ["--ratio-gate-mode", "rolling", "--exit-form", "center", "--entry", "4", "--exit-setting", "3"]

JOBS = {
    "k": [("K-0", "c2_limit_run.py", _K),
          ("K-A", "c2_limit_run.py", _K + ["--k1-time-exit-bars", "6"]),
          ("K-B", "c2_limit_run.py", _K + _KG + ["--k1-time-exit-bars", "9"])],
    "m": [(f"{f}_{s}", "c4_limit_run.py", ["--fill-side", s] + extra)
          for f, extra in (("M-0", []), ("M-A", _MA)) for s in ("good", "bad")],
}


def commands(card: str) -> list[tuple[str, list[str]]]:
    return [(name, [sys.executable, os.path.join(HERE, script)] + args + ["--window1", "--out", os.path.join(OUT, name)])
            for name, script, args in JOBS[card]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, choices=sorted(JOBS))
    ap.add_argument("--only", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rc = 0
    for name, cmd in commands(a.card):
        if a.only and name != a.only:
            continue
        print(" ".join(cmd), flush=True)
        if a.dry_run:
            continue
        os.makedirs(os.path.join(OUT, name), exist_ok=True)
        with open(os.path.join(OUT, name, "run.log"), "w", encoding="utf-8") as fh:
            r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=REPO)
        print(f"{name}: exit {r.returncode}", flush=True)
        rc = rc or r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
