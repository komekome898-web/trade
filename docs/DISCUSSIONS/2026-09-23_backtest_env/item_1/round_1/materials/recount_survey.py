#!/usr/bin/env python3
"""Rebuild the survey side's folded row WITHOUT make_tables.py: per scene, the
best of the 14 survey targets (正解と一致 > 対応なし > 不一致 > 結果なし, then
「2 回の実行で同じ」 first), from runs/<target>.tsv; count per viewpoint.
Also counts, per viewpoint, how many survey targets had at least one
「正解と一致」 (to answer whether a 0 comes from no target reaching the
scene or from targets disagreeing with the answer)."""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/home/user/trade/tests/bt/battery/item_1")
import i1_targets as TG  # noqa: E402
ORDER = ["正解と一致", "対応なし", "不一致", "結果なし"]
runs = {n: {r["scene"]: r for r in csv.DictReader(open(HERE / "runs" / f"{n}.tsv", encoding="utf-8"),
                                                   delimiter="\t", quoting=csv.QUOTE_NONE)} for n in TG.SURVEY}
scenes = list(next(iter(runs.values())).values())
corr, same, tot = Counter(), Counter(), Counter()
classes = defaultdict(Counter)
for s in scenes:
    sid, vp = s["scene"], s["viewpoint"]
    best = min((ORDER.index(runs[n][sid]["class_1"]), runs[n][sid]["repro"] != "2 回の実行で同じ") for n in runs)
    tot[vp] += 1
    corr[vp] += best[0] == 0
    same[vp] += not best[1]
    for n in runs:
        classes[vp][runs[n][sid]["class_1"]] += 1
print("survey targets", len(runs))
for vp in sorted(tot):
    print(vp, "best_correct", corr[vp], "best_same", same[vp], "scenes", tot[vp],
          "all target x scene classes", dict(classes[vp]))
print("total correct", sum(corr.values()), "same", sum(same.values()), "of", sum(tot.values()))
