#!/usr/bin/env python3
"""Compare, per target and scene, the absolute-`--out` run (runs/, tables source)
with the relative-`--out` run (logs/relative_out_all_targets/runs/): class and
digest of both passes. Prints every difference and a total."""
import csv
from pathlib import Path
HERE = Path(__file__).resolve().parent
REL = HERE / "logs" / "relative_out_all_targets"


def rd(p):
    with open(p, encoding="utf-8") as fh:
        return {r["scene"]: r for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}


n = diff = 0
for d_abs, d_rel in (("runs", "runs"), ("runs_2", "runs_2")):
    for p in sorted((HERE / d_abs).glob("*.tsv")):
        a, b = rd(p), rd(REL / d_rel / p.name)
        for sid, r in a.items():
            n += 1
            q = b[sid]
            k = lambda x: (x["class_1"], x["digest_1"], x["class_2"], x["digest_2"])  # noqa: E731
            if k(r) != k(q):
                diff += 1
                print(d_abs, p.stem, sid, "abs:", r["class_1"], "| rel:", q["class_1"], "|", q["detail_1"][:200])
print({"rows": n, "differ": diff})
