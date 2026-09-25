#!/usr/bin/env python3
"""Round 13 materials check: for every target, compare pass 1 (runs/) and
pass 2 (runs_2/) of run_all.sh scene by scene on the graded fields
(correctness, reproducibility, output_1, output_2). Prints the differing
cells; the tables use pass 1."""
import csv
import sys
from pathlib import Path

csv.field_size_limit(10**9)
MAT = Path(__file__).resolve().parent
FIELDS = ("correctness", "reproducibility", "output_1", "output_2")


def load(p):
    with p.open(encoding="utf-8") as f:
        return {r["scene_id"]: r for r in csv.DictReader(f, delimiter="\t")}


total = 0
one = sorted(p.name for p in (MAT / "runs").glob("*.tsv"))
two = sorted(p.name for p in (MAT / "runs_2").glob("*.tsv"))
print("targets in pass 1:", len(one), "pass 2:", len(two), "only in one pass:", sorted(set(one) ^ set(two)))
for name in one:
    q = MAT / "runs_2" / name
    if not q.exists():
        continue
    a, b = load(MAT / "runs" / name), load(q)
    diff = [(s, f) for s in a for f in FIELDS if a[s].get(f) != b.get(s, {}).get(f)]
    total += len(diff)
    if diff:
        print(f"{name[:-4]}: {len(diff)} differing fields {diff}")
print("total differing fields:", total)
sys.exit(1 if total else 0)
