#!/usr/bin/env python3
"""Recount without make_tables.py: from runs/<target>.tsv only (csv + the
runner's class_1 / repro columns), per viewpoint and in total, for new_impl,
current_impl, mutant, and the survey fold (best by the order
正解と一致 > 対応なし > 不一致 > 結果なし, then 「2 回の実行で同じ」)."""
import csv
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ORDER = {"正解と一致": 0, "対応なし": 1, "不一致": 2, "結果なし": 3}
SAME = "2 回の実行で同じ"

def rd(name):
    with open(HERE / "runs" / f"{name}.tsv", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))

def show(label, rows):
    by = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        v = by[r["viewpoint"]]
        v[0] += r["class_1"] == "正解と一致"; v[1] += r["repro"] == SAME; v[2] += 1
    tot = [sum(v[i] for v in by.values()) for i in range(3)]
    vps = sorted(by, key=lambda x: int(x.split("-")[1]))
    print(f"{label}: 正解と一致 {tot[0]}/{tot[2]}  2 回の実行で同じ {tot[1]}/{tot[2]}")
    print("   " + " ".join(f"{vp}={by[vp][0]}/{by[vp][2]}(同じ {by[vp][1]})" for vp in vps))
    return tot

new = rd("new_impl")
t = show("new_impl", new)
show("current_impl", rd("current_impl"))
show("mutant", rd("mutant"))
survey = [p.stem for p in sorted((HERE / "runs").glob("opp_*.tsv"))]
tabs = {n: {r["scene"]: r for r in rd(n)} for n in survey}
fold = []
for r in new:
    sid = r["scene"]
    best = min((tabs[n][sid] for n in survey), key=lambda x: (ORDER[x["class_1"]], x["repro"] != SAME))
    fold.append({"viewpoint": r["viewpoint"], "class_1": best["class_1"], "repro": best["repro"]})
show(f"survey fold of {len(survey)} targets", fold)
print(f"new_impl_correct = {t[0]}/{t[2]}  all_correct = {t[0] == t[2]}")
