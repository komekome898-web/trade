#!/usr/bin/env python3
"""Round 11 check: in every table, count the cells of each viewpoint section
("正しさ: 正解と一致" / "再現: 2 回の実行で同じ") per row and compare with the
table's own count rows."""
import re
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent
bad = 0
for p in sorted(OUT.glob("表_*.md")):
    t = p.read_text(encoding="utf-8")
    secs = re.split(r"^## ", t, flags=re.M)
    counts = {}
    for s in secs:
        m = re.match(r"(P0-\d) ", s)
        if not m:
            continue
        for l in s.splitlines():
            r = re.match(r"\| ([AB]) \|(.*)\|$", l)
            if r:
                cells = r.group(2).split(" | ")
                counts[(m.group(1), r.group(1))] = (sum("正しさ: 正解と一致" in c for c in cells),
                                                    sum("再現: 2 回の実行で同じ" in c for c in cells), len(cells))
    for sec, idx in (("観点ごとの「正解と一致」の数", 0), ("観点ごとの「2 回の実行で同じ」の数", 1)):
        body = next(s for s in secs if s.startswith(sec))
        hdr = [h.strip() for h in [l for l in body.splitlines() if l.startswith("| 対象")][0].strip("|").split("|")][1:-1]
        for l in body.splitlines():
            r = re.match(r"\| ([AB]) \|(.*)\|$", l)
            if r:
                vals = [c.strip() for c in r.group(2).split("|")][:-1]
                for vp, v in zip(hdr, vals):
                    h, n = (int(x) for x in v.split("/"))
                    got = counts[(vp, r.group(1))]
                    ok = (h, n) == (got[idx], got[2])
                    bad += not ok
                    if not ok:
                        print("MISMATCH", p.name, sec, r.group(1), vp, v, got)
    print(p.name, "checked", len(counts), "viewpoint rows")
print("mismatches:", bad)
