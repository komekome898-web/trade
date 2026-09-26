#!/usr/bin/env python3
"""Recount from the table cells themselves (not from make_tables.py's counts):
per table and row A/B, per viewpoint, cells whose correctness is 正解と一致 and
whose reproducibility is 2 回の実行で同じ; compare with the table's own summary rows."""
import re
from pathlib import Path
ROUND = Path(__file__).resolve().parent.parent
bad = 0
for p in sorted(ROUND.glob("表_*.md")):
    lines = p.read_text(encoding="utf-8").splitlines()
    cnt = {"A": {}, "B": {}}
    vp = None
    summary = {}
    sec = None
    for ln in lines:
        m = re.match(r"## (V\d) ", ln)
        if m:
            vp = m.group(1); sec = "vp"; continue
        if ln.startswith("## 観点ごとの「正解と一致」"):
            sec = "sum_c"; continue
        if ln.startswith("## 観点ごとの「2 回の実行で同じ」"):
            sec = "sum_s"; continue
        m = re.match(r"\| ([AB]) \| (.*) \|$", ln)
        if not m:
            continue
        row, cells = m.group(1), m.group(2).split(" | ")
        if sec == "vp":
            c = sum(x.startswith("正しさ: 正解と一致<br>") for x in cells)
            s = sum(x.endswith("再現: 2 回の実行で同じ") for x in cells)
            cnt[row][vp] = (c, s, len(cells))
        elif sec in ("sum_c", "sum_s"):
            summary[(sec, row)] = [tuple(map(int, x.split(" / "))) for x in cells]
    out = {}
    for row in "AB":
        vps = sorted(cnt[row])
        c = [(cnt[row][v][0], cnt[row][v][2]) for v in vps]
        s = [(cnt[row][v][1], cnt[row][v][2]) for v in vps]
        tc = (sum(x[0] for x in c), sum(x[1] for x in c))
        ts = (sum(x[0] for x in s), sum(x[1] for x in s))
        ok = summary[("sum_c", row)] == c + [tc] and summary[("sum_s", row)] == s + [ts]
        bad += not ok
        out[row] = f"correct {dict(zip(vps, [x[0] for x in c]))} total {tc[0]}/{tc[1]} same {ts[0]}/{ts[1]} summary_matches={ok}"
    print(p.name, out)
print("mismatches:", bad)
