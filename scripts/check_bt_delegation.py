"""Mechanical checks on the backtest-env delegation before it goes to the auditor (L-433 提出前の吟味).

Checks, all against primary records:
1. Every owner decision cited as L-NNN in the delegation has a row in docs/OWNER_LOG.md.
2. Every bold quote written as L-NNN「**…**」 in the delegation appears verbatim in that L-NNN row of OWNER_LOG.
3. The L numbers listed in the 「オーナーだけが変える」 sentence all appear in §0's table (right column).
4. The definition heading 「周回の数え方と止める条件」 occurs exactly once as a definition and every other
   mention points at it.
5. No auditor output in the VERDICTS file is abbreviated with 「(…)」 inside a 「監査役の出力」 section (O-4).

Usage: python3 scripts/check_bt_delegation.py [delegation.md] [OWNER_LOG.md] [VERDICTS.md]
Exit 1 on any error.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULTS = ("docs/DATA/delegations/20260923_backtest_env_prompt.md", "docs/OWNER_LOG.md",
            "docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_prompt.md")


def owner_rows(log: str) -> dict[str, str]:
    rows = {}
    for line in log.splitlines():
        m = re.match(r"\|\s*(L-\d{3})\s*\|", line)
        if m:
            rows[m.group(1)] = line
    return rows


def check(doc: str, log: str, verdicts: str) -> list[str]:
    errs: list[str] = []
    rows = owner_rows(log)
    cited = sorted(set(re.findall(r"L-\d{3}", doc)))
    for l in cited:
        if l not in rows:
            errs.append(f"{l}: 委任文が引いているが OWNER_LOG に行が無い")
    for m in re.finditer(r"(L-\d{3})「\*\*([^*]+?)\*\*」", doc):
        l, q = m.group(1), m.group(2)
        row = rows.get(l, "")
        if q not in row:
            errs.append(f"{l}: 太字の引用「{q[:40]}…」が OWNER_LOG の {l} の行に逐語で無い")
    sec0 = doc.split("## 1.", 1)[0]
    m = re.search(r"はオーナーだけが変える。", doc)
    if m:
        sent = doc[doc.rfind("**", 0, m.start()) : m.end()]
        for l in set(re.findall(r"L-\d{3}", sent)):
            if l not in sec0:
                errs.append(f"{l}: 「オーナーだけが変える」の一覧にあるが §0 の表に無い")
    else:
        errs.append("「はオーナーだけが変える。」の文が無い")
    defs = doc.count("**周回の数え方と止める条件(")
    if defs != 1:
        errs.append(f"「周回の数え方と止める条件」の定義が {defs} 回(1 回でなければならない)")
    in_audit = False
    for i, line in enumerate(verdicts.splitlines(), 1):
        if line.startswith("### "):
            in_audit = "監査役の出力" in line
        elif in_audit and re.search(r"(?<!「)\(…\)(?!」)", line):  # 「(…)」 quoted by the auditor itself is not a cut
            errs.append(f"VERDICTS:{i}: 監査役の出力の中に「(…)」= 切り詰めがある(O-4)")
    return errs


def main(argv: list[str]) -> int:
    paths = [Path(argv[i]) if i < len(argv) else Path(DEFAULTS[i]) for i in range(3)]
    errs = check(*(p.read_text(encoding="utf-8") for p in paths))
    for e in errs:
        print("NG", e)
    print(f"{'OK' if not errs else 'NG'} 誤り {len(errs)} 件")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
