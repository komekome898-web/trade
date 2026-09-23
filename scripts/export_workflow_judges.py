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
AUDIT_BATTERY = re.compile(r"^監査役\(場面\):(\d+)(?:#(\d+))?$")  # "#n" = audit before the worker (run 4 on)
AUDIT_TABLE = re.compile(r"^監査役\(表\):(\d+)$")
REPAIR = re.compile(r"^場面の直し:(\d+)#(\d+)$")
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
    out: dict = defaultdict(lambda: {"battery": [], "table": [], "report": [], "worker": []})
    for aid, lab in labels.items():
        res = results.get(aid)
        if res is None:
            continue
        if (m := AUDIT_BATTERY.match(lab)) and m.group(2) is None:
            out[(int(m.group(1)), 1)]["battery"].append((lab, aid, res.get("findings", [])))
        elif m := AUDIT_TABLE.match(lab):
            out[(int(m.group(1)), 1)]["table"].append((lab, aid, res.get("findings", [])))
        elif m := AUDIT_REPORT.match(lab):
            out[(int(m.group(1)), int(m.group(2)))]["report"].append((lab, aid, res.get("findings", [])))
        elif m := WORKER.match(lab):
            out[(int(m.group(1)), int(m.group(2)))]["worker"].append((lab, aid, res.get("questions_for_lead", [])))
    return out


def render_audit(item: int, rnd: int, sec: dict) -> str:
    lines = [f"# 監査役の出力と作業者の問い(項目 {item} 第 {rnd} 周、Workflow の記録から逐語で書き出し)", ""]
    titles = (("battery", "監査役(場面集と最初の表)の出力"), ("table", "監査役(最初の表)の出力"),
              ("report", "監査役(作業者の報告)の出力"),
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


def collect_battery(paths: list[str]) -> dict:
    """Audits of the battery before the worker and the 場面係's repairs, in order, per item."""
    labels, results = load(paths)
    out: dict = defaultdict(list)
    for aid, lab in labels.items():
        res = results.get(aid)
        if res is None:
            continue
        if (m := AUDIT_BATTERY.match(lab)) and m.group(2) is not None:
            out[int(m.group(1))].append((int(m.group(2)), 0, lab, aid, res))
        elif m := REPAIR.match(lab):
            out[int(m.group(1))].append((int(m.group(2)), 1, lab, aid, res))
    return out


def render_battery(item: int, rows: list) -> str:
    lines = [f"# 場面集の監査と直し(項目 {item}、作業者の前。Workflow の記録から逐語で書き出し)", "",
             "監査役(場面):N#k = k 回目の監査、場面の直し:N#k = k 回目の直し(その前の監査の指摘を受けたもの)。", ""]
    for _, _, lab, aid, res in sorted(rows, key=lambda r: (r[0], r[1])):
        lines += [f"## {lab}(agent {aid})", ""]
        if "findings" in res:
            lines += [f"- [{x['level']}] {x['text']}" for x in res["findings"]] or ["(指摘なし)"]
        else:
            lines += [f"- 根本原因の記録: {res.get('rootcause')}", f"- 検討表の道具の出力: {res.get('check_output')}",
                      f"- 動かせた: {res.get('survey_run')}", f"- 動かせなかった: {res.get('survey_not_run')}"]
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
    for item, rows in sorted(collect_battery(argv).items()):
        d = REC / f"item_{item}" / "battery"
        d.mkdir(parents=True, exist_ok=True)
        (d / "AUDIT.md").write_text(render_battery(item, rows), encoding="utf-8")
        print(d / "AUDIT.md", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
