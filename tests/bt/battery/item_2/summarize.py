#!/usr/bin/env python3
"""Count a run_battery output per viewpoint:  python3 summarize.py OUT.tsv [OUT2.tsv ...] [--detail]"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict

CLASSES = ("正解と一致", "対応なし", "不一致", "結果なし")


def main() -> int:
    detail = "--detail" in sys.argv
    for path in [a for a in sys.argv[1:] if not a.startswith("--")]:
        rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))
        tot = Counter(r["class_1"] for r in rows)
        rep = Counter(r["repro"] == "2 回の実行で同じ" for r in rows)
        print(f"== {path.rsplit('/', 1)[-1]}: " + " ".join(f"{c} {tot[c]}" for c in CLASSES) + f" / 2 回で同じ {rep[True]}/{len(rows)}")
        by = defaultdict(Counter)
        for r in rows:
            by[r["viewpoint"]][r["class_1"]] += 1
        print("   " + " | ".join(f"{vp}:{by[vp]['正解と一致']}/{sum(by[vp].values())}" for vp in sorted(by, key=lambda v: int(v.split('-')[1]))))
        if detail:
            for r in rows:
                print(f"   {r['scene']:28s} {r['class_1']:6s} {r['repro'][:12]:12s} {r['detail_1'][:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
