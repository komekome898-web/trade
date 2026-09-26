#!/usr/bin/env python3
"""Recount, WITHOUT make_tables.py: new_impl's 「正解と一致」 from runs/new_impl.tsv
(and runs_2/), per viewpoint, from the raw tsv columns."""
import csv
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
for d in ("runs", "runs_2"):
    for t in ("new_impl", "current_impl", "mutant"):
        rows = list(csv.DictReader(open(HERE / d / f"{t}.tsv", encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
        both = Counter(r["viewpoint"] for r in rows if r["class_1"] == r["class_2"] == "正解と一致")
        first = sum(r["class_1"] == "正解と一致" for r in rows)
        print(d, t, "scenes", len(rows), "correct_pass1", first, "correct_both_passes", sum(both.values()),
              "by_viewpoint", dict(sorted(both.items())))
