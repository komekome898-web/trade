"""Export blind-judge outputs of the backtest-rebuild workflow to docs, verbatim.

The workflow script cannot write files, so judge verdicts only live in the
workflow journal (outside the repo). This copies every judge result into
docs/DISCUSSIONS/2026-09-23_backtest_env/item_<n>/round_<r>/JUDGES.md so the
record can be checked later (audit round 12, finding 4).

Usage: python3 scripts/export_workflow_judges.py <journal.jsonl> [<journal.jsonl> ...]
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REC = Path("docs/DISCUSSIONS/2026-09-23_backtest_env")
LABEL = re.compile(r"^盲検:(\d+)#(\d+):([a-z]+)(\d)$")


def collect(paths: list[str]) -> dict:
    labels: dict[str, str] = {}
    results: dict[str, object] = {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            aid = d.get("agentId")
            if not aid:
                continue
            if "label" in d:
                labels[aid] = d["label"]
            if "result" in d:
                results[aid] = d["result"]
    out: dict = defaultdict(list)
    for aid, lab in labels.items():
        m = LABEL.match(lab)
        if not m or aid not in results:
            continue
        item, rnd, key, k = m.groups()
        out[(int(item), int(rnd))].append((key, int(k), lab, aid, results[aid]))
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for (item, rnd), rows in sorted(collect(argv).items()):
        d = REC / f"item_{item}" / f"round_{rnd}"
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"# 盲検の審査員の出力(項目 {item} 第 {rnd} 周、Workflow の記録から逐語で書き出し)", ""]
        for key, k, lab, aid, res in sorted(rows):
            lines += [f"## {lab}(agent {aid})", "", "```json", json.dumps(res, ensure_ascii=False, indent=2), "```", ""]
        (d / "JUDGES.md").write_text("\n".join(lines), encoding="utf-8")
        print(d / "JUDGES.md", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
