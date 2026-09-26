#!/usr/bin/env python3
"""Recount each table from its cell text (the 'I4-n' section rows) and compare
with the table's own two count sections (正解と一致 / 2 回の実行で同じ)."""
import csv, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ok = True
for m in csv.DictReader(open(HERE / "mapping.tsv", encoding="utf-8"), delimiter="\t"):
    text = (HERE.parent / m["file"]).read_text(encoding="utf-8")
    secs = re.split(r"^## ", text, flags=re.M)
    counted = {"A": {}, "B": {}}
    stated = {}
    for s in secs[1:]:
        head, body = s.split("\n", 1)
        rows = [l for l in body.splitlines() if l.startswith("| A |") or l.startswith("| B |")]
        if head.startswith("観点ごと"):
            key = 0 if "正解と一致" in head else 1
            hdr = [l for l in body.splitlines() if l.startswith("| 対象")][0].strip("|").split("|")[1:-1]
            for l in rows:
                cells = l.strip("|").split("|")
                lab = cells[0].strip()
                for vp, c in zip([h.strip() for h in hdr], cells[1:-1]):
                    stated[(lab, vp, key)] = int(c.split("/")[0])
                stated[(lab, "計", key)] = int(cells[-1].split("/")[0])
        elif re.match(r"I4-\d+ ", head):
            vp = head.split()[0]
            for l in rows:
                cells = l.strip("|").split("|")
                lab = cells[0].strip()
                c = sum("正しさ: 正解と一致" in x for x in cells[1:])
                r = sum("再現: 2 回の実行で同じ" in x for x in cells[1:])
                counted[lab][vp] = (c, r)
    for lab in "AB":
        for key in (0, 1):
            tot = 0
            for vp, cr in counted[lab].items():
                tot += cr[key]
                if stated[(lab, vp, key)] != cr[key]:
                    ok = False; print("MISMATCH", m["table_id"], lab, vp, key, stated[(lab, vp, key)], cr[key])
            if stated[(lab, "計", key)] != tot:
                ok = False; print("MISMATCH total", m["table_id"], lab, key)
        print(m["table_id"], m["file"], lab, m[lab], "正解と一致",
              sum(v[0] for v in counted[lab].values()), "同じ", sum(v[1] for v in counted[lab].values()),
              "場面", sum(1 for _ in counted[lab]), "観点")
print("all counts match the cells:", ok)
