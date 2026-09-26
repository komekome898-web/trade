#!/usr/bin/env python3
"""Count, per survey target and viewpoint, the scenes graded 正解と一致 in
survey_results/*.tsv (the runner's output, copied from the scene keeper's
runs); the catalogue number of each target comes from opponents/RUNNABILITY.tsv
(run candidates) and from the review table's 再現した rows (reproductions). Prints a Markdown table; CONSIDERED.md quotes it. Standard library only.

Usage: python3 survey_counts.py
"""
from __future__ import annotations

import csv
import collections
from pathlib import Path

HERE = Path(__file__).resolve().parent


def catalog_numbers() -> dict[str, int]:
    """target -> catalogue number, from the runnability ledger (one source of truth)."""
    with (HERE / "opponents" / "RUNNABILITY.tsv").open(encoding="utf-8") as f:
        return {r["target"]: int(r["cand"]) for r in csv.DictReader(f, delimiter="\t") if r["result"] == "走った"}


def repro_numbers() -> dict[str, int]:
    """repro_<name> -> catalogue number, from the review table's 再現した rows
    (round r6-3: a reproduction is counted with its candidate's number)."""
    import re
    text = (HERE / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\| (\d+) [^|]*\|[^|]*\|[^|]*\| 再現した \|([^\n]*)$", text, flags=re.M):
        for t in re.findall(r"opponents/(repro_\w+)\.py", m.group(2)):
            out[t] = int(m.group(1))
    return out


def main() -> None:
    no_of = {**catalog_numbers(), **repro_numbers()}
    rows, vps = [], set()
    for p in sorted((HERE / "survey_results").glob("*.tsv")):
        hit, tot, same = collections.Counter(), collections.Counter(), 0
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                tot[r["viewpoint"]] += 1
                hit[r["viewpoint"]] += r["correctness"] == "正解と一致"
                same += r["reproducibility"] == "2 回の実行で同じ"
        vps |= set(tot)
        rows.append((no_of.get(p.stem, 0), p.stem, hit, tot, same, sum(tot.values())))
    vps = sorted(vps)
    print("| 候補 | 対象 | " + " | ".join(f"{v}" for v in vps) + " | 2 回の実行で同じ |")
    print("|---" * (len(vps) + 3) + "|")
    for no, name, hit, tot, same, n in sorted(rows):
        print(f"| {no} | {name} | " + " | ".join(f"{hit[v]}/{tot[v]}" for v in vps) + f" | {same}/{n} |")


if __name__ == "__main__":
    main()
