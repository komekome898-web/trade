#!/usr/bin/env python3
"""Round 17 materials checks (pre-submission):
(1) pattern coverage: every target base name (runs/*.tsv, part before '@')
    is matched by some line of logs/grep_tool_names.pat;
(2) the per-target note lines of materials/not_entered.tsv equal the
    scene keeper's CLI `grid_c.py <runs/*.tsv>` output (logs/grid_c_cli.out),
    and every '行 A/B …' note in the six tables is one of those lines."""
import re
import sys
from pathlib import Path
MAT = Path(__file__).resolve().parent
OUT = MAT.parent
pats = [l for l in (MAT / "logs/grep_tool_names.pat").read_text(encoding="utf-8").splitlines() if l]
bases = sorted({p.stem.split("@", 1)[0] for p in (MAT / "runs").glob("*.tsv")})
miss = [b for b in bases if not any(re.search(p, b, re.I) for p in pats)]
print("(1) target base names:", len(bases), "not matched by the pattern file:", miss,
      "(new_impl/current_impl/mutant/survey are row names, not tool names)")
cli = (MAT / "logs/grid_c_cli.out").read_text(encoding="utf-8").splitlines()
ne = [l.split("\t", 1) for l in (MAT / "not_entered.tsv").read_text(encoding="utf-8").splitlines()[1:]]
cli_notes = set()
for line in cli:
    cli_notes.add(line.split("\t", 1)[1] if "\t" in line else line)
bad = [t for t, n in ne if not any(n in c for c in cli)]
print("(2a) not_entered.tsv rows:", len(ne), "cli lines:", len(cli), "rows not found in cli output:", bad)
notes = set(n for _, n in ne)
extra = 0
for p in sorted(OUT.glob("表_*.md")):
    for l in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"注記: 行 [AB] (?:の対象: |に寄せた設定つき対象 \d+ 件のうち \d+ 件: )(.*)$", l)
        if m and m.group(1) not in notes:
            extra += 1
            print("  note not in not_entered.tsv:", p.name, m.group(1)[:120])
print("(2b) table notes not in not_entered.tsv:", extra)
sys.exit(1 if (bad or extra) else 0)
