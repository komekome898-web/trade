"""Parsing/scoring correctness of scripts/qa/score_audit.py.

Uses small hand-built "sealed answers" and fake auditor reports (never a
real auditor run — the QA plan forbids running an auditor from this task)
to check that verdict extraction, sensitivity/specificity, trap detection
and MDE sanity behave as specified.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "qa"))

import score_audit as sa  # noqa: E402


@pytest.fixture
def answers():
    return {
        "daily_overnight_premium": {
            "QA_BRAVO": {"realized_overnight_mean_bps": 2.1, "realized_overnight_t_stat": 7.0},
        },
        "claims": [
            {"id": "QA-1", "category": "premium", "truth_class": "true_effect", "claim_correct": True},
            {"id": "QA-2", "category": "premium", "truth_class": "zero_effect", "claim_correct": False},
            {"id": "QA-3", "category": "momentum", "truth_class": "true_effect", "claim_correct": True},
            {"id": "QA-4", "category": "momentum", "truth_class": "zero_effect", "claim_correct": False},
            {"id": "QA-5", "category": "cost_floor", "truth_class": "cost_trap", "claim_correct": True},
            {"id": "QA-6", "category": "cost_floor", "truth_class": "cost_trap", "claim_correct": False},
        ],
    }


GOOD_REPORT = """# Audit report

## QA-1
判定: 再現
recomputed +2.1bps/day, t=7.0

## QA-2
判定: 結論変更
recomputed -0.2bps/day, not significant.

## QA-3
判定: 再現
lag-1 autocorr +0.05

## QA-4
判定: 判定不能
no significant autocorrelation found.

## QA-5
判定: 再現
floor recomputed 3.6bps

## QA-6
判定: 結論変更
naive average was contaminated by crossed rows.

## 前提の誤り
- 交差板が存在する(0.1%)。
- メンテナンス窓(19:00-19:10 UTC)がフラットバーとして混入。
- 実行ファイルの t 列は収集時刻、ts 列が真の約定時刻。
- QA_ALPHA で価格が1000倍になっている日が2日ある(scale glitch)。
MDE at n~4000 daily obs is about 0.6bps.
"""

BAD_REPORT = """# Audit report

## QA-1
判定: 結論変更

## QA-2
判定: 再現

## QA-3
判定: 判定不能

## QA-4
判定: 再現

## QA-5
判定: 数値差異

## QA-6
判定: 再現

## 前提の誤り
none found.
"""


def test_good_report_scores_high(answers):
    result = sa.score(GOOD_REPORT, answers)
    assert result["sensitivity"]["rate"] == 1.0
    assert result["specificity"]["rate"] == 1.0
    assert result["trap_detection"]["rate"] == 1.0
    assert result["mde_sanity"]["plausible"] is True
    assert result["n_claims_located_in_report"] == 6


def test_bad_report_scores_low(answers):
    result = sa.score(BAD_REPORT, answers)
    assert result["sensitivity"]["rate"] == 0.0
    assert result["specificity"]["rate"] == 0.0
    assert result["trap_detection"]["rate"] == 0.0


def test_claim_id_without_hyphen_is_matched(answers):
    report = "## QA1\n判定: 再現\n## QA2\n判定: 結論変更\n"
    sections = sa._claim_sections(report, [c["id"] for c in answers["claims"]])
    assert "QA-1" in sections and "QA-2" in sections
    assert sa._find_verdict(sections["QA-1"]) == "再現"
    assert sa._find_verdict(sections["QA-2"]) == "結論変更"


def test_explicit_verdict_line_wins_over_incidental_mention(answers):
    # "再現性" style incidental text should not be picked over an explicit line
    section = "判定: 結論変更\n(この文言は再現性の議論であり判定ではない)"
    assert sa._find_verdict(section) == "結論変更"


def test_missing_claim_section_is_reported_as_not_found(answers):
    report = "## QA-1\n判定: 再現\n"  # only one of six claims present
    result = sa.score(report, answers)
    assert result["n_claims_located_in_report"] == 1
    missing = [pc for pc in result["per_claim"] if not pc["found_section"]]
    assert len(missing) == 5
    assert all(pc["extracted_verdict"] is None for pc in missing)


def test_trap_keywords_count_inline_in_a_claim_section_too(answers):
    # Real auditors document data-validity checks (PROTOCOL.md Q6) either in
    # the dedicated "前提の誤り" section or inline inside a claim's own
    # numbered checklist — both must count, not just the dedicated section.
    report = (
        "## QA-1\n判定: 再現\n交差板の話がここに出てくる(claim 本文中)\n"
        "## 前提の誤り\nnone found.\n"
    )
    result = sa.score(report, answers)
    assert result["trap_detection"]["per_trap"]["crossed_book_rows"] is True


def test_bold_verdict_line_is_parsed(answers):
    section = "recomputed the claim.\n\n**Verdict: 再現**\n\n## QA-2"
    assert sa._find_verdict(section) == "再現"


def test_verdict_followed_by_parenthetical_explanation(answers):
    section = "判定: 結論変更(オーバーナイト・プレミアムは存在しない。スケール断裂の産物)"
    assert sa._find_verdict(section) == "結論変更"

    section2 = "Verdict: 結論変更 — claimed premium does not survive a scale-break screen"
    assert sa._find_verdict(section2) == "結論変更"


def test_claim_sections_do_not_bleed_across_qa_n_headings(answers):
    # A claim id mentioned in prose BEFORE its real heading (e.g. a
    # scratchpad filename like "audit_QA3.py" in a frontmatter file list)
    # must not hijack that claim's section start.
    report = (
        "# report\n\nscripts used: audit_QA3.py, audit_QA2.py\n\n"
        "## QA-1\n判定: 再現\nnumbers: 1.0bps\n\n"
        "## QA-2\n判定: 結論変更\nnumbers: 2.0bps\n\n"
        "## QA-3\n判定: 再現\nnumbers: 3.0bps\n"
    )
    sections = sa._claim_sections(report, ["QA-1", "QA-2", "QA-3"])
    assert sa._find_verdict(sections["QA-1"]) == "再現"
    assert sa._find_verdict(sections["QA-2"]) == "結論変更"
    assert sa._find_verdict(sections["QA-3"]) == "再現"
    # QA-1's section must not swallow QA-2/QA-3's content
    assert "3.0bps" not in sections["QA-1"]
    assert "2.0bps" not in sections["QA-1"]


def test_verdict_accuracy_covers_cost_trap_claims_too(answers):
    # sensitivity/specificity only pool true_effect/zero_effect claims;
    # verdict_accuracy is the "N/N correct verdicts" headline across ALL
    # claims, cost_trap (QA-5/QA-6) included.
    result = sa.score(GOOD_REPORT, answers)
    assert result["verdict_accuracy"] == {"rate": 1.0, "n": 6, "hits": 6}


def test_mde_sanity_flags_implausible_value(answers):
    report = GOOD_REPORT.replace("about 0.6bps", "about 50bps")
    result = sa.score(report, answers)
    assert result["mde_sanity"]["plausible"] is False


def test_mde_sanity_none_when_not_reported(answers):
    report = GOOD_REPORT.split("## 前提の誤り")[0] + "## 前提の誤り\nnone found.\n"
    result = sa.score(report, answers)
    assert result["mde_sanity"]["reported_mde_bps"] == []
    assert result["mde_sanity"]["plausible"] is None


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("n", [1, 2, 3])
def test_real_auditor_reports_score_6_of_6_and_4_of_4(n):
    """Regression check on the three real blind-audit reports
    (docs/AUDIT_2026-09/QA_auditor{1,2,3}.md) against the real sealed
    answers: all three should score 6/6 correct verdicts and 4/4 planted
    traps (auditor 3 writes traps in Japanese: 交差/反転, メンテ, 収集時刻,
    スケール)."""
    report_path = REPO_ROOT / "docs" / "AUDIT_2026-09" / f"QA_auditor{n}.md"
    answers_path = REPO_ROOT / "docs" / "QA" / "answers_sealed.json"
    report = report_path.read_text(encoding="utf-8")
    real_answers = json.loads(answers_path.read_text(encoding="utf-8"))
    result = sa.score(report, real_answers)
    assert result["verdict_accuracy"]["rate"] == 1.0, result["per_claim"]
    assert result["trap_detection"]["rate"] == 1.0, result["trap_detection"]
