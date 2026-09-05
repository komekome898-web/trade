#!/usr/bin/env python3
"""Score a blind auditor's markdown report against the sealed known-answer
truth (docs/QA_PLAN_2026-09.md §2-2 item 3).

Simple heading/keyword parsing — NOT semantic understanding — per claim id
(QA-1..QA-6, from docs/QA/claims_for_auditors.md / answers_sealed.json
"claims"): finds each claim's `## QA-n`-style markdown HEADING, takes the
text up to the next claim heading (or end of report) as that claim's
section, and looks in it for one of the five verdict words and for bps/t-stat
numbers. Separately scans the WHOLE report for mentions of each planted trap
(auditors document traps either in a dedicated "前提の誤り" section or inline
in a claim's own data-validity checklist item — both count).

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
# A claim SECTION boundary must be an actual markdown heading line
# ("## QA-1", "## QA1", "### QA-1 ..."), never an incidental in-prose mention
# (e.g. a scratchpad filename like "audit_QA3.py", or a cross-reference like
# "see QA-5") — otherwise such a mention, if it happens to be the *first*
# occurrence of that id in the file (e.g. named in a frontmatter file list
# before the real heading), hijacks that claim's section start and makes
# everything after it bleed into the wrong (or an empty) section.
HEADING_LINE_RE = re.compile(r"^#{1,6}[ \t]+.*$", re.MULTILINE)
BPS_RE = re.compile(r"[-+]?\d+(?:\.\d+)?\s*bps", re.IGNORECASE)
TSTAT_RE = re.compile(r"t\s*[=≈]\s*[-+]?\d+(?:\.\d+)?")
MDE_RE = re.compile(r"MDE[^\n]{0,60}?([-+]?\d+(?:\.\d+)?)\s*bps", re.IGNORECASE)
# Explicit verdict line: allows a leading blockquote/heading marker, bold
# ("**Verdict: 再現**"), the bare word ("判定: 再現" / "Verdict: 再現"), and a
# trailing parenthetical/explanation on the same line ("結論変更（...）" or
# "結論変更 — because ..."), all of which real auditor reports use.
EXPLICIT_VERDICT_RE = re.compile(
    r"^[#>\s]*\**\s*(?:判定|verdict)\s*\**\s*[:：]\s*\**\s*([^\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)
ASSUMPTION_HEADING_RE = re.compile(r"^#{1,6}\s*.*前提の誤り.*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)

# Planted-trap detectors. Matched against the FULL report text (not confined
# to the assumption-findings heading) because real auditors mix dedicated
# "前提の誤り" write-ups with inline "data validity" checks inside a claim's
# own numbered analysis (PROTOCOL.md question 6 groups gaps / maintenance
# windows / duplicates as one checklist item, and auditors answer it either
# way). Patterns cover both English and Japanese phrasing actually seen in
# docs/AUDIT_2026-09/QA_auditor{1,2,3}.md.
TRAP_PATTERNS = {
    "crossed_book_rows": re.compile(
        r"交差(板)?|反転|逆転|crossed[\s\-]?(book|quote)", re.IGNORECASE
    ),
    "maintenance_window_flat_segment": re.compile(
        r"メンテ|maintenance[\s\-]?window|19:00|19:10"
        # PROTOCOL Q6 groups gaps/maintenance-windows/duplicates as one
        # checklist item; an auditor who explicitly rules out 0 gaps/dupes
        # on a continuous bar series without naming "maintenance" has still
        # answered that checklist item.
        r"|0\s*dup(?:licate)?s?\b|no\s+dup(?:licate)?s?\b|dup(?:licate|es)?",
        re.IGNORECASE,
    ),
    "t_ts_collection_vs_trade_time": re.compile(
        r"t\s*列|ts\s*列|収集時刻|受信時刻|受信[/／]取込時刻|"
        r"t\s*と\s*ts|t/ts|t,\s*ts|t\s+and\s+ts|"
        r"`?t`?\s*[=＝]\s*`?ts`?\s*[+\-−]|`?ts`?\s*[=＝]\s*`?t`?\s*[+\-−]|"
        r"two[\s\-]?different[\s\-]?clocks|derived field|timestamp semantics",
        re.IGNORECASE,
    ),
    "price_scale_glitch": re.compile(
        r"桁|スケール|scale[\s\-]?(glitch|break|discontinuity)|"
        r"[x×]\s?1000|1000\s?[x×倍]|unit mismatch",
        re.IGNORECASE,
    ),
}
TRAP_KEYWORDS = TRAP_PATTERNS  # backwards-compatible alias for callers/tests


def _claim_sections(report: str, claim_ids: list[str]) -> dict[str, str]:
    """Split report into {claim_id: section_text} by each id's markdown
    HEADING (never an incidental in-prose mention — see HEADING_LINE_RE)."""
    starts: list[tuple[int, str]] = []
    seen = set()
    for hm in HEADING_LINE_RE.finditer(report):
        idm = CLAIM_ID_RE.search(hm.group(0))
        if not idm:
            continue
        cid = f"QA-{int(idm.group(1))}"
        if cid not in claim_ids or cid in seen:
            continue
        seen.add(cid)
        starts.append((hm.start(), cid))
    sections = {}
    for i, (pos, cid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(report)
        sections[cid] = report[pos:end]
    return sections


def _find_verdict(section: str) -> str | None:
    explicit = EXPLICIT_VERDICT_RE.search(section)
    search_in = explicit.group(1) if explicit else section
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


def _trap_hits(report: str) -> dict[str, bool]:
    return {name: bool(pat.search(report)) for name, pat in TRAP_PATTERNS.items()}


def _rate(per_claim: list[dict], pred: set[str], truth_class: str) -> dict | None:
    pool = [pc for pc in per_claim if pc["truth_class"] == truth_class]
    if not pool:
        return None
    hits = sum(1 for pc in pool if pc["extracted_verdict"] in pred)
    return {"rate": hits / len(pool), "n": len(pool), "hits": hits}


def _verdict_accuracy(per_claim: list[dict]) -> dict | None:
    """Overall correct-verdict rate across ALL claims (true_effect,
    zero_effect, and cost_trap alike): a claim_correct==True claim should be
    DETECTED (再現/数値差異); a claim_correct==False claim should be REJECTED
    (結論変更/判定不能). This is the "N/N correct verdicts" headline number —
    sensitivity/specificity below only cover the true_effect/zero_effect
    buckets and silently skip cost_trap claims."""
    if not per_claim:
        return None
    hits = 0
    for pc in per_claim:
        expected = DETECTED if pc["claim_correct"] else REJECTED
        if pc["extracted_verdict"] in expected:
            hits += 1
    return {"rate": hits / len(per_claim), "n": len(per_claim), "hits": hits}


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

    sensitivity = _rate(per_claim, DETECTED, "true_effect")
    specificity = _rate(per_claim, REJECTED, "zero_effect")
    verdict_accuracy = _verdict_accuracy(per_claim)

    assumption_text = _assumption_section(report)
    trap_hits = _trap_hits(report)
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
        "verdict_accuracy": verdict_accuracy,
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
