#!/usr/bin/env python3
"""Compare, per target and scene: (1) the two passes inside runs/<t>.tsv,
(2) runs/ against runs_2/ (class and digest of both passes), (3) runs/ against
the scene keeper's tests/bt/battery/item_3/survey_results/<t>.tsv (class and digest)."""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SURVEY = Path("/home/user/trade/tests/bt/battery/item_3/survey_results")


def rd(p):
    with open(p, encoding="utf-8") as fh:
        return {r["scene"]: r for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}


tot = {"in_run_diff": 0, "run12_diff": 0, "vs_survey_diff": 0, "rows": 0}
for p in sorted((HERE / "runs").glob("*.tsv")):
    t = p.stem
    a, b = rd(p), rd(HERE / "runs_2" / p.name)
    s = rd(SURVEY / p.name) if (SURVEY / p.name).exists() else None
    for sid, r in a.items():
        tot["rows"] += 1
        if r["repro"] != "2 回の実行で同じ" and r["repro"] != "結果なし":
            tot["in_run_diff"] += 1
            print("IN_RUN", t, sid, r["repro"])
        q = b[sid]
        if (r["class_1"], r["digest_1"], r["class_2"], r["digest_2"]) != (q["class_1"], q["digest_1"], q["class_2"], q["digest_2"]):
            tot["run12_diff"] += 1
            print("RUN1_vs_RUN2", t, sid, r["class_1"], r["digest_1"], "|", q["class_1"], q["digest_1"])
        if s is not None:
            z = s.get(sid)
            if z is None or (r["class_1"], r["digest_1"]) != (z["class_1"], z["digest_1"]):
                tot["vs_survey_diff"] += 1
                print("VS_SURVEY", t, sid, r["class_1"], r["digest_1"], "|", z and z["class_1"], z and z["digest_1"])
print(tot)
