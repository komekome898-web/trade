"""Timeline of a backtest-env session from primary records (no memory, no summaries).

Reads the lead's conversation transcripts and the Workflow journals and prints, in UTC:
- every launch/resume, auditor call and report, owner question and answer, scheduled notification;
- each owner question's wait time and how long delegates were running meanwhile;
- the merged spans in which at least one delegate was running, and their total.

Usage:
  python3 scripts/session_timeline.py --since 2026-09-23T07:50 \
      --transcript <lead .jsonl> [--transcript ...] --workflow <workflow dir> [--workflow ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json


def ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def events(transcripts: list[str], since: dt.datetime):
    ev, questions, answers = [], [], []
    for fn in transcripts:
        for line in open(fn, encoding="utf-8"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t, m = d.get("timestamp"), d.get("message")
            if not t or not isinstance(m, dict) or d.get("isSidechain"):
                continue
            t = ts(t)
            if t < since:
                continue
            c = m.get("content")
            if d.get("type") == "assistant" and isinstance(c, list):
                for x in c:
                    if x.get("type") != "tool_use":
                        continue
                    n, i = x["name"], x.get("input", {})
                    if n == "Workflow":
                        ev.append((t, "再開" if i.get("resumeFromRunId") else "起動", i.get("resumeFromRunId") or ""))
                    elif n == "Agent":
                        ev.append((t, "監査役を起こす", i.get("description", "")[:40]))
                    elif n == "AskUserQuestion":
                        q = i["questions"][0]["question"][:45]
                        ev.append((t, "オーナーに質問", q))
                        questions.append((t, q))
                    elif n.endswith("send_later"):
                        ev.append((t, "予約", i.get("name", "")))
            elif d.get("type") == "user":
                text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                if isinstance(c, list):
                    for x in c:
                        if x.get("type") == "tool_result" and "Your questions have been answered" in json.dumps(x.get("content"), ensure_ascii=False):
                            answers.append(t)
                if not text:
                    continue
                if "<task-notification>" in text:
                    if "Dynamic workflow" in text:
                        ev.append((t, "Workflow 終了の知らせ", ""))
                    elif "queued-remote" in text:
                        ev.append((t, "予約の知らせが届いた", ""))
                elif "Another Claude session sent" in text:
                    ev.append((t, "監査役の報告", ""))
                elif len(text) < 400 and not text.startswith(("<", "Stop hook", "[SYSTEM")):
                    ev.append((t, "オーナーの発言", text[:60].replace("\n", " ")))
    return sorted(ev), sorted(questions), sorted(answers)


def spans(workflow_dirs: list[str]):
    out = []
    for d in workflow_dirs:
        for f in glob.glob(d + "/agent-*.jsonl"):
            stamps = []
            for line in open(f, encoding="utf-8"):
                try:
                    s = json.loads(line).get("timestamp")
                except json.JSONDecodeError:
                    s = None
                if s:
                    stamps.append(ts(s))
            if stamps:
                out.append((min(stamps), max(stamps)))
    out.sort()
    merged: list[list[dt.datetime]] = []
    for s, e in out:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return out, merged


def overlap_minutes(raw, t0, t1):
    tot = 0.0
    for s, e in raw:
        lo, hi = max(s, t0), min(e, t1)
        if hi > lo:
            tot += (hi - lo).total_seconds()
    return tot / 60


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--transcript", action="append", required=True)
    ap.add_argument("--workflow", action="append", required=True)
    a = ap.parse_args()
    since = ts(a.since if "+" in a.since or a.since.endswith("Z") else a.since + "+00:00")
    ev, qs, ans = events(a.transcript, since)
    raw, merged = spans(a.workflow)
    print("## 出来事(UTC)")
    for t, k, x in ev:
        print(f"{t:%m-%d %H:%M} {k:<14} {x}")
    print("\n## オーナーへの質問 → 答え")
    for qt, q in qs:
        at = next((x for x in ans if x > qt), None)
        if at:
            w = (at - qt).total_seconds() / 60
            print(f"{qt:%m-%d %H:%M} → {at:%H:%M} 待ち {w:5.0f} 分(うち委任先が動いていた {overlap_minutes(raw, qt, at):4.0f} 分) {q}")
    now = dt.datetime.now(dt.timezone.utc)
    active = sum((e - s).total_seconds() for s, e in merged) / 3600
    print(f"\n## 経過 {(now - since).total_seconds() / 3600:.1f} h、委任先が 1 体でも動いていた時間 {active:.1f} h")
    for s, e in merged:
        print(f"  {s:%m-%d %H:%M}→{e:%H:%M} ({(e - s).total_seconds() / 60:.0f} 分)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
