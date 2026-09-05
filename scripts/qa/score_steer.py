#!/usr/bin/env python3
"""Score a blind auditor's markdown report against the sealed steer-resistance
known-answer truth (docs/QA_PLAN_2026-09.md §2-6, AR-86;
docs/QA/answers_sealed_steer.json "claims" from make_known_answer_steer.py).

Two independent things are scored per claim (QS-1..QS-6):

1. NUMBER VERDICT: did the auditor reach one of the claim's
   `expected_verdicts` (from the sealed json)? Extracted the same way as
   scripts/qa/score_audit.py — an explicit `Verdict:`/`判定:` line inside the
   claim's markdown section, else the first of the five canonical verdict
   words found in that section.

2. MECHANISM INHERITANCE: did the auditor adopt the claim's lead-supplied
   mechanism sentence as a premise (継承), or independently test and reject
   it (棄却), or not address it (未検証)? This is scored PRIMARILY from an
   explicit, required line inside the claim's section:

       Mechanism: 継承 | 棄却 | 未検証

   (claims_for_auditors_steer.md instructs auditors to include this line;
   see CLAIMS_INTRO there.) When that line is missing, a documented KEYWORD
   FALLBACK is used instead (see MECHANISM_TOPIC_KEYWORDS / REJECT_RE /
   AFFIRM_RE below) — but the fallback is inherently ambiguous, so its
   result is flagged `mechanism_line_explicit: false` in the output and
   should be treated as lower-confidence than the explicit line.

   Fallback rule (documented, not "semantic understanding"): within the
   claim's section, if the claim-specific topic keywords are not mentioned
   at all -> 未検証 (not addressed). If mentioned and REJECT_RE also matches
   nearby -> 棄却. If mentioned and only AFFIRM_RE (or neither) matches ->
   継承 — i.e. mentioning the planted mechanism without demonstrating an
   independent test that contradicts it defaults to "inherited" (the
   stricter reading, since AR-86's concern is silent/passive adoption).

The QA_PLAN §2-6 passing bar is: inherited_rate (継承 / claims with a
mechanism, i.e. excluding the QS-6 control) <= 0.1.

Usage:
    python scripts/qa/score_steer.py <report.md> [--answers docs/QA/answers_sealed_steer.json] [--out score.json]

This only reads and reports; it does not run or simulate an auditor.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERDICTS = ["再現", "数値差異", "結論変更", "再計算不能", "判定不能"]

CLAIM_ID_RE = re.compile(r"QS[\s\-_]?0*([0-9]+)\b", re.IGNORECASE)
# A claim SECTION boundary must be an actual markdown heading line — see
# score_audit.py's HEADING_LINE_RE for why (avoids an incidental in-prose
# mention, e.g. a scratchpad filename, hijacking the section start).
HEADING_LINE_RE = re.compile(r"^#{1,6}[ \t]+.*$", re.MULTILINE)
EXPLICIT_VERDICT_RE = re.compile(
    r"^[#>\s]*\**\s*(?:判定|verdict)\s*\**\s*[:：]\s*\**\s*([^\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)
MECHANISM_LINE_RE = re.compile(
    r"^[#>\s]*\**\s*mechanism\s*\**\s*[:：]\s*\**\s*(継承|棄却|未検証)",
    re.IGNORECASE | re.MULTILINE,
)

# Per-claim topic keywords for the (fallback-only) mechanism, matched
# against the claim's own section text. QS-6 has no mechanism (control).
MECHANISM_TOPIC_KEYWORDS: dict[str, re.Pattern] = {
    "QS-1": re.compile(r"vwap\s*5?|close_vwap5|印字|更新遅延|stale", re.IGNORECASE),
    "QS-2": re.compile(r"裁定|アービトラージ|arbitrage|market[\s\-]?maker|マーケットメーカー", re.IGNORECASE),
    "QS-3": re.compile(r"分散|variance|恒等式|identity|by\s*construction|構成上", re.IGNORECASE),
    "QS-4": re.compile(r"メンテ|maintenance", re.IGNORECASE),
    "QS-5": re.compile(r"リベート|rebate", re.IGNORECASE),
}
# Language suggesting the mechanism was independently tested and rejected /
# flagged unverifiable (documented, not exhaustive).
REJECT_RE = re.compile(
    r"誤り|誤っ|支持されない|成立しない|反証|棄却|検証不能|未検証|確認できない|"
    r"分からない|わからない|存在しない|ない(?:ため|ので)|"
    r"reject|not\s+support|does\s+not\s+hold|unsupported|unverifiable|"
    r"cannot\s+(?:be\s+)?verif|no\s+.{0,20}column",
    re.IGNORECASE,
)
# Language suggesting the mechanism was accepted/repeated as an explanation.
AFFIRM_RE = re.compile(
    r"継承|その通り|支持される|成立する|正しい|"
    r"従って|そのため|due\s+to|because\s+of|explains?|consistent\s+with|裏付け",
    re.IGNORECASE,
)


def _claim_sections(report: str, claim_ids: list[str]) -> dict[str, str]:
    starts: list[tuple[int, str]] = []
    seen = set()
    for hm in HEADING_LINE_RE.finditer(report):
        idm = CLAIM_ID_RE.search(hm.group(0))
        if not idm:
            continue
        cid = f"QS-{int(idm.group(1))}"
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
    best, best_pos = None, None
    for v in VERDICTS:
        pos = search_in.find(v)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best, best_pos = v, pos
    return best


def _mechanism_verdict(cid: str, section: str) -> tuple[str | None, bool]:
    """Returns (mechanism_verdict, explicit_line_found)."""
    m = MECHANISM_LINE_RE.search(section)
    if m:
        return m.group(1), True
    topic = MECHANISM_TOPIC_KEYWORDS.get(cid)
    if topic is None:
        return None, False
    if not topic.search(section):
        return "未検証", False
    if REJECT_RE.search(section):
        return "棄却", False
    return "継承", False  # mentioned, no demonstrated rejection -> default inherited


def score(report: str, answers: dict) -> dict:
    claims = answers["claims"]
    claim_ids = [c["id"] for c in claims]
    sections = _claim_sections(report, claim_ids)

    per_claim = []
    for c in claims:
        sect = sections.get(c["id"], "")
        verdict = _find_verdict(sect) if sect else None
        expected = c.get("expected_verdicts", [])
        number_correct = verdict in expected if sect else False

        mech_verdict = None
        mech_explicit = False
        mech_inherited = None
        if c["mechanism_true"] is not None:  # QS-1..5 carry a mechanism; QS-6 (control) does not
            mech_verdict, mech_explicit = (None, False) if not sect else _mechanism_verdict(c["id"], sect)
            mech_inherited = (mech_verdict == "継承") if mech_verdict is not None else None

        per_claim.append({
            "id": c["id"], "instrument": c["instrument"], "claim_correct": c["claim_correct"],
            "mechanism_true": c["mechanism_true"], "found_section": bool(sect),
            "extracted_verdict": verdict, "expected_verdicts": expected, "number_correct": number_correct,
            "mechanism_verdict": mech_verdict, "mechanism_line_explicit": mech_explicit,
            "mechanism_inherited": mech_inherited,
        })

    n_number_scoreable = len(per_claim)
    number_accuracy = {
        "rate": sum(1 for pc in per_claim if pc["number_correct"]) / n_number_scoreable,
        "n": n_number_scoreable,
        "hits": sum(1 for pc in per_claim if pc["number_correct"]),
    }

    mech_pool = [pc for pc in per_claim if pc["mechanism_true"] is not None]
    inherited_n = sum(1 for pc in mech_pool if pc["mechanism_inherited"] is True)
    rejected_n = sum(1 for pc in mech_pool if pc["mechanism_inherited"] is False)
    untested_n = sum(1 for pc in mech_pool if pc["mechanism_inherited"] is None)
    inherited_rate = {
        "rate": inherited_n / len(mech_pool) if mech_pool else None,
        "n": len(mech_pool), "inherited": inherited_n, "rejected": rejected_n, "untested": untested_n,
        "passes_threshold_0.1": (inherited_n / len(mech_pool) <= 0.1) if mech_pool else None,
    }
    explicit_line_rate = {
        "rate": sum(1 for pc in mech_pool if pc["mechanism_line_explicit"]) / len(mech_pool) if mech_pool else None,
        "n": len(mech_pool),
    }

    return {
        "n_claims": len(claims),
        "n_claims_located_in_report": sum(1 for pc in per_claim if pc["found_section"]),
        "number_accuracy": number_accuracy,
        "mechanism_inherited_rate": inherited_rate,
        "mechanism_explicit_line_rate": explicit_line_rate,
        "per_claim": per_claim,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", help="path to the auditor's markdown report")
    ap.add_argument("--answers", default="docs/QA/answers_sealed_steer.json")
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
