#!/usr/bin/env python3
"""Independent recount (round 7 materials person's pre-submission check):
per viewpoint, count 正解と一致 and 2 回の実行で同じ straight from
materials/runs/*.tsv (survey side = per-scene best in the battery-rule-5
order, recomputed here without make_tables.py), then parse the count rows of
each table file and compare. Prints OK / MISMATCH per table."""
import csv, glob, os, re, sys
from pathlib import Path
csv.field_size_limit(10**9)
MAT = Path(__file__).resolve().parent
OUT = MAT.parent
C = {"正解と一致": 0, "対応なし": 1, "不一致": 2, "結果なし": 3}
R = {"2 回の実行で同じ": 0, "2 回で違う": 1, "結果なし": 2}

def load(t):
    return list(csv.DictReader(open(MAT / "runs" / f"{t}.tsv", encoding="utf-8"), delimiter="\t"))

def counts(rows):
    vps = []
    for r in rows:
        if r["viewpoint"] not in vps:
            vps.append(r["viewpoint"])
    res = {}
    for field, good in (("correctness", "正解と一致"), ("reproducibility", "2 回の実行で同じ")):
        res[field] = [(vp, sum(r[field] == good for r in rows if r["viewpoint"] == vp),
                       sum(1 for r in rows if r["viewpoint"] == vp)) for vp in vps]
    return res

surv = {os.path.basename(p)[:-4]: {r["scene_id"]: r for r in load(os.path.basename(p)[:-4])}
        for p in sorted(glob.glob(str(MAT / "runs" / "opp_*.tsv")) + glob.glob(str(MAT / "runs" / "repro_*.tsv")))}
new = load("new_impl")
best = []
for r in new:
    sid = r["scene_id"]
    cand = sorted(((C[s[sid]["correctness"]], R[s[sid]["reproducibility"]]), s[sid]) for s in surv.values()
                  for _ in [0]) if False else None
    b = min((s[sid] for s in surv.values()), key=lambda x: (C[x["correctness"]], R[x["reproducibility"]]))
    best.append(b)
rows = {"new_impl": new, "current_impl": load("current_impl"), "mutant": load("mutant"), "survey_best": best}
want = {k: counts(v) for k, v in rows.items()}
for k, v in want.items():
    print(k, {f: [(vp, f"{h}/{n}") for vp, h, n in v[f]] for f in v})

def parse(path):
    txt = Path(path).read_text(encoding="utf-8")
    secs = re.split(r"^## ", txt, flags=re.M)
    got = {}
    for sec, field in (("観点ごとの「正解と一致」の数", "correctness"), ("観点ごとの「2 回の実行で同じ」の数", "reproducibility")):
        body = next(s for s in secs if s.startswith(sec))
        hdr = [l for l in body.splitlines() if l.startswith("| 対象")][0].strip("|").split("|")[1:-1]
        for l in body.splitlines():
            m = re.match(r"\| ([AB]) \|(.*)\|$", l)
            if m:
                cells = [c.strip() for c in m.group(2).split("|")][:-1]
                got.setdefault(m.group(1), {})[field] = [(vp.strip(), int(c.split("/")[0]), int(c.split("/")[1])) for vp, c in zip(hdr, cells)]
    return got

bad = 0
for line in list(open(MAT / "mapping.tsv", encoding="utf-8"))[1:]:
    tid, f, a, b = line.rstrip("\n").split("\t")
    got = parse(OUT / f)
    ok = got["A"] == want[a] and got["B"] == want[b]
    bad += not ok
    print(tid, f, "A=", a, "B=", b, "OK" if ok else f"MISMATCH got={got} want A={want[a]} B={want[b]}")
print("mismatches:", bad)
sys.exit(1 if bad else 0)
