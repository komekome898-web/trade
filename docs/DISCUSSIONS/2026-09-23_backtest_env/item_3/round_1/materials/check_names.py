#!/usr/bin/env python3
"""Grep the six tables for anything that names a tool or a clock time:
target keys, adapter module stems, catalogue names (RUNNABILITY.tsv 'name'
column, each word of 4+ letters), venv dirs, commit-like hex, hh:mm times, dates."""
import csv, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
B = Path("/home/user/trade/tests/bt/battery/item_3")
sys.path.insert(0, str(B))
import i3_targets as T
pats = set()
for k, v in T.TARGETS.items():
    if k in ("new_impl", "current_impl", "mutant"):
        continue
    pats.add(k); pats.add(k.replace("opp_", ""))
    pats.add(Path(v["module"]).stem.replace("_adapter", ""))
    if v.get("venv"):
        pats.add(v["venv"].split("/")[1])
for r in csv.DictReader(open(B / "opponents/RUNNABILITY.tsv", encoding="utf-8"), delimiter="\t"):
    for w in re.split(r"[^A-Za-z0-9]+", r["name"]):
        if len(w) >= 4:
            pats.add(w)
stop = {"order", "book", "simulator", "backtest", "backtesting", "engine", "trading", "system", "market", "impact",
        "execution", "optimal", "simulation", "event", "driven", "matching", "fill", "model", "slippage", "research", "limit"}
pats = sorted(p for p in pats if p.lower() not in stop and len(p) >= 3)
bad = 0
for t in sorted(HERE.parent.glob("表_*.md")):
    text = t.read_text(encoding="utf-8")
    low = text.lower()
    hits = [p for p in pats if re.search(r"(?<![a-z0-9])" + re.escape(p.lower()) + r"(?![a-z0-9])", low)]
    times = re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text) + re.findall(r"20\d\d-\d\d-\d\d", text)
    hexes = [h for h in re.findall(r"\b[0-9a-f]{7,40}\b", text) if re.search(r"[a-f]", h)]
    print(t.name, "names:", hits, "times:", times[:5], "hex:", hexes[:5])
    bad += len(hits) + len(times) + len(hexes)
print("patterns:", len(pats), "hits total:", bad)
