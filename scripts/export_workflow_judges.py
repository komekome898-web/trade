"""Export judge, auditor and worker-question records of the backtest-rebuild workflow to docs, verbatim.

The workflow script cannot write files, so these records only live in the
workflow journal (outside the repo). This copies them into
docs/DISCUSSIONS/2026-09-23_backtest_env/item_<n>/round_<r>/:

- JUDGES.md : every blind-judge result (audit round 12, finding 4)
- AUDIT.md  : auditor findings and worker questions, each in its own section
              (audit round 20, finding 4: the first hand-made record mixed them
              because it followed journal order)

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
AUDIT_BATTERY = re.compile(r"^監査役\(場面\):(\d+)$")
AUDIT_REPORT = re.compile(r"^監査役:(\d+)#(\d+)$")
WORKER = re.compile(r"^作る:(\d+)#(\d+)$")


def load(paths: list[str]) -> tuple[dict, dict]:
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
    return labels, results


def collect(paths: list[str]) -> dict:
    labels, results = load(paths)
    out: dict = defaultdict(list)
    for aid, lab in labels.items():
        m = LABEL.match(lab)
        if not m or aid not in results:
            continue
        item, rnd, key, k = m.groups()
        out[(int(item), int(rnd))].append((key, int(k), lab, aid, results[aid]))
    return out


def collect_audit(paths: list[str]) -> dict:
    """Group auditor findings and worker questions by (item, round), one section per source."""
    labels, results = load(paths)
    out: dict = defaultdict(lambda: {"battery": [], "report": [], "worker": []})
    for aid, lab in labels.items():
        res = results.get(aid)
        if res is None:
            continue
        if m := AUDIT_BATTERY.match(lab):
            out[(int(m.group(1)), 1)]["battery"].append((lab, aid, res.get("findings", [])))
        elif m := AUDIT_REPORT.match(lab):
            out[(int(m.group(1)), int(m.group(2)))]["report"].append((lab, aid, res.get("findings", [])))
        elif m := WORKER.match(lab):
            out[(int(m.group(1)), int(m.group(2)))]["worker"].append((lab, aid, res.get("questions_for_lead", [])))
    return out


def render_audit(item: int, rnd: int, sec: dict) -> str:
    lines = [f"# 監査役の出力と作業者の問い(項目 {item} 第 {rnd} 周、Workflow の記録から逐語で書き出し)", ""]
    titles = (("battery", "監査役(場面集と最初の表)の出力"), ("report", "監査役(作業者の報告)の出力"),
              ("worker", "作業者の「リードに聞くこと」"))
    for key, title in titles:
        lines += [f"## {title}", ""]
        rows = sec[key]
        if not rows:
            lines += ["(この周には無い)", ""]
            continue
        for lab, aid, items in rows:
            lines += [f"### {lab}(agent {aid})", ""]
            for x in items:
                lines.append(f"- [{x['level']}] {x['text']}" if isinstance(x, dict) else f"- {x}")
            lines.append("")
    return "\n".join(lines)


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
    for (item, rnd), sec in sorted(collect_audit(argv).items()):
        d = REC / f"item_{item}" / f"round_{rnd}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "AUDIT.md").write_text(render_audit(item, rnd, sec), encoding="utf-8")
        print(d / "AUDIT.md", {k: len(v) for k, v in sec.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
