#!/usr/bin/env python3
"""Check: would the merged survey row change if the scene keeper's earlier
run of the one tool that could not be installed this round
(tests/bt/battery/item_0/survey_results/opp_finmarketpy.tsv) were added?
Compares, per scene, the merged best (correctness, reproducibility) with and
without it. That TSV is not this round's run and is not used in the tables."""
import csv
import sys
from pathlib import Path

MAT = Path(__file__).resolve().parent
sys.path.insert(0, str(MAT))
import make_tables as T  # noqa: E402

runs = {p.stem: T.load(p.stem) for p in sorted(T.RUNS.glob("*.tsv")) if p.stem.startswith(T.SURVEY_PREFIXES)}
base, _ = T.best(runs)
extra = T.REPO / "tests/bt/battery/item_0/survey_results/opp_finmarketpy.tsv"
with extra.open(encoding="utf-8") as f:
    fin = {r["scene_id"]: r for r in csv.DictReader(f, delimiter="\t")}
missing = [s.id for s in T.SCENES if s.id not in fin]
print("scenes missing from the earlier run:", missing)
exp_diff = [s.id for s in T.SCENES if s.id in fin and fin[s.id]["expected"] != base[s.id]["expected"]]
print("scenes whose expected differs from this round's scenes:", exp_diff)
with_fin, who = T.best({**runs, "opp_finmarketpy": fin})
changed = [(s.id, T.rank(base[s.id]), T.rank(with_fin[s.id])) for s in T.SCENES
           if (base[s.id]["correctness"], base[s.id]["reproducibility"]) !=
              (with_fin[s.id]["correctness"], with_fin[s.id]["reproducibility"])]
print("cells of the merged survey row that would change:", len(changed), changed)
