"""Parsing/scoring correctness of scripts/qa/score_audit.py.

Uses small hand-built "sealed answers" and fake auditor reports (never a
real auditor run — the QA plan forbids running an auditor from this task)
to check that verdict extraction, sensitivity/specificity, trap detection
and MDE sanity behave as specified.
"""
from __future__ import annotations

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


def test_trap_keywords_only_count_inside_assumption_section(answers):
    report = (
        "## QA-1\n判定: 再現\n交差板の話がここに出てくる(本来のセクション外)\n"
        "## 前提の誤り\nnone found.\n"
    )
    result = sa.score(report, answers)
    assert result["trap_detection"]["per_trap"]["crossed_book_rows"] is False


def test_mde_sanity_flags_implausible_value(answers):
    report = GOOD_REPORT.replace("about 0.6bps", "about 50bps")
    result = sa.score(report, answers)
    assert result["mde_sanity"]["plausible"] is False


def test_mde_sanity_none_when_not_reported(answers):
    report = GOOD_REPORT.split("## 前提の誤り")[0] + "## 前提の誤り\nnone found.\n"
    result = sa.score(report, answers)
    assert result["mde_sanity"]["reported_mde_bps"] == []
    assert result["mde_sanity"]["plausible"] is None
