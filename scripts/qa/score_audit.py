#!/usr/bin/env python3
"""Score a blind auditor's markdown report against the sealed known-answer
truth (docs/QA_PLAN_2026-09.md §2-2 item 3).

Simple heading/keyword parsing — NOT semantic understanding — per claim id
(QA-1..QA-6, from docs/QA/claims_for_auditors.md / answers_sealed.json
"claims"): finds the claim id in the report, takes the text up to the next
claim id (or heading) as that claim's section, and looks in it for one of
the five verdict words and for bps/t-stat numbers. Separately scans the
"前提の誤り" (assumption findings) section for mentions of each planted trap.

Usage:
    python scripts/qa/score_audit.py <report.md> [--answers docs/QA/answers_sealed.json] [--out score.json]

This only reads and reports; it does not run or simulate an auditor.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERDICTS = ["再現", "数値差異", "結論変更", "再計算不能", "判定不能"]
# verdicts that count as "a real effect was detected" for sensitivity
DETECTED = {"再現", "数値差異"}
# verdicts that count as "a null effect was correctly rejected" for specificity
REJECTED = {"結論変更", "判定不能"}

CLAIM_ID_RE = re.compile(r"QA[\s\-_]?0*([0-9]+)\b", re.IGNORECASE)
BPS_RE = re.compile(r"[-+]?\d+(?:\.\d+)?\s*bps", re.IGNORECASE)
TSTAT_RE = re.compile(r"t\s*[=≈]\s*[-+]?\d+(?:\.\d+)?")
MDE_RE = re.compile(r"MDE[^\n]{0,60}?([-+]?\d+(?:\.\d+)?)\s*bps", re.IGNORECASE)
ASSUMPTION_HEADING_RE = re.compile(r"^#{1,6}\s*.*前提の誤り.*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)

TRAP_KEYWORDS = {
    "crossed_book_rows": ["交差板", "crossed book", "crossed-book", "crossed quote"],
    "maintenance_window_flat_segment": ["メンテ", "maintenance window", "19:00", "19:10"],
    "t_ts_collection_vs_trade_time": [
        "t列", "ts列", "収集時刻", "受信時刻", "collection time", "t と ts",
        "t/ts", "t,ts", "t and ts",
    ],
    "price_scale_glitch": ["桁", "スケール", "scale glitch", "×1000", "x1000", "1000倍", "unit mismatch"],
}


def _claim_sections(report: str, claim_ids: list[str]) -> dict[str, str]:
    """Split report into {claim_id: section_text} by first occurrence of each id."""
    hits = []
    for m in CLAIM_ID_RE.finditer(report):
        cid = f"QA-{int(m.group(1))}"
        if cid in claim_ids:
            hits.append((m.start(), cid))
    hits.sort()
    # keep only the FIRST occurrence per claim id as the section start
    seen = set()
    starts = []
    for pos, cid in hits:
        if cid in seen:
            continue
        seen.add(cid)
        starts.append((pos, cid))
    sections = {}
    for i, (pos, cid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(report)
        sections[cid] = report[pos:end]
    return sections


def _find_verdict(section: str) -> str | None:
    explicit = re.search(r"(判定|verdict)\s*[:：]\s*([^\n]+)", section, re.IGNORECASE)
    search_in = explicit.group(2) if explicit else section
    best = None
    best_pos = None
    for v in VERDICTS:
        pos = search_in.find(v)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best, best_pos = v, pos
    return best


def _find_numbers(section: str) -> dict:
    bps = [float(x.replace("bps", "").strip()) for x in BPS_RE.findall(section)]
    t = TSTAT_RE.findall(section)
    return {"bps_values": bps, "t_stat_mentions": t}


def _assumption_section(report: str) -> str:
    m = ASSUMPTION_HEADING_RE.search(report)
    if not m:
        return ""
    rest = report[m.end():]
    nxt = NEXT_HEADING_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


def score(report: str, answers: dict) -> dict:
    claims = answers["claims"]
    claim_ids = [c["id"] for c in claims]
    sections = _claim_sections(report, claim_ids)

    per_claim = []
    for c in claims:
        sect = sections.get(c["id"], "")
        verdict = _find_verdict(sect) if sect else None
        nums = _find_numbers(sect) if sect else {"bps_values": [], "t_stat_mentions": []}
        per_claim.append({
            "id": c["id"], "category": c["category"], "truth_class": c["truth_class"],
            "claim_correct": c["claim_correct"], "found_section": bool(sect),
            "extracted_verdict": verdict, **nums,
        })

    def rate(pred, truth_class):
        pool = [pc for pc in per_claim if pc["truth_class"] == truth_class]
        if not pool:
            return None
        hits = sum(1 for pc in pool if pc["extracted_verdict"] in pred)
        return {"rate": hits / len(pool), "n": len(pool), "hits": hits}

    sensitivity = rate(DETECTED, "true_effect")
    specificity = rate(REJECTED, "zero_effect")

    assumption_text = _assumption_section(report)
    trap_hits = {}
    for trap, kws in TRAP_KEYWORDS.items():
        trap_hits[trap] = any(kw.lower() in assumption_text.lower() for kw in kws)
    trap_detection_rate = sum(trap_hits.values()) / len(trap_hits)

    # MDE sanity: compare any reported MDE (bps) against an MDE implied by
    # the sealed daily-premium standard error (2*SE rule of thumb), using
    # the clean instrument (QA_BRAVO) as the reference.
    bravo = answers["daily_overnight_premium"]["QA_BRAVO"]
    se_bps = abs(bravo["realized_overnight_mean_bps"] / bravo["realized_overnight_t_stat"])
    expected_mde_bps = round(2 * se_bps, 4)
    mde_matches = MDE_RE.findall(report)
    mde_values = [float(x) for x in mde_matches]
    mde_plausible = None
    if mde_values:
        mde_plausible = any(expected_mde_bps / 3 <= v <= expected_mde_bps * 3 for v in mde_values)

    return {
        "n_claims": len(claims),
        "n_claims_located_in_report": sum(1 for pc in per_claim if pc["found_section"]),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "trap_detection": {"per_trap": trap_hits, "rate": trap_detection_rate,
                            "assumption_section_found": bool(assumption_text)},
        "mde_sanity": {"expected_mde_bps_from_seal": expected_mde_bps,
                       "reported_mde_bps": mde_values, "plausible": mde_plausible},
        "per_claim": per_claim,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", help="path to the auditor's markdown report")
    ap.add_argument("--answers", default="docs/QA/answers_sealed.json")
    ap.add_argument("--out", default=None, help="write JSON score here (default: stdout)")
    args = ap.parse_args()

    report_text = Path(args.report).read_text(encoding="utf-8")
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    result = score(report_text, answers)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
