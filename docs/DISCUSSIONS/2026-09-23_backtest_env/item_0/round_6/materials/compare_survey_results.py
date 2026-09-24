#!/usr/bin/env python3
"""Check: per survey target, does this round's run (materials/runs/<t>.tsv)
grade every scene the same as the scene keeper's run
(tests/bt/battery/item_0/survey_results/<t>.tsv)? Prints the differing cells.
Only a consistency check; the tables use this round's runs."""
import csv
from pathlib import Path

MAT = Path(__file__).resolve().parent
REPO = MAT.parents[5]
SR = REPO / "tests/bt/battery/item_0/survey_results"


def load(p):
    with p.open(encoding="utf-8") as f:
        return {r["scene_id"]: r for r in csv.DictReader(f, delimiter="\t")}


total = 0
for p in sorted(SR.glob("*.tsv")):
    mine = MAT / "runs" / p.name
    if not mine.exists():
        print(f"{p.stem}: not run this round (scene keeper's file only)")
        continue
    a, b = load(p), load(mine)
    diff = [(s, a[s]["correctness"], b.get(s, {}).get("correctness"), a[s]["reproducibility"],
             b.get(s, {}).get("reproducibility")) for s in a
            if (a[s]["correctness"], a[s]["reproducibility"]) != (b.get(s, {}).get("correctness"), b.get(s, {}).get("reproducibility"))]
    total += len(diff)
    print(f"{p.stem}: {len(diff)} differing cells {diff}")
print("total differing cells:", total)
