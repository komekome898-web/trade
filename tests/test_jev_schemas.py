"""`scripts/jev/schemas.py` の質問セットの形を検査する。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.jev.schemas import principle_screen, risk_route, trace_review


def test_principle_screen_has_16_items_ids_p1_to_p16():
    q = principle_screen()
    assert len(q) == 16
    assert set(q.keys()) == {f"P{n}" for n in range(1, 17)}
    for qid, spec in q.items():
        assert spec["type"] == "noul"
        assert "instructions" in spec and spec["instructions"]
        assert set(spec["criteria"].keys()) == {"true", "false"}


def test_trace_review_has_6_items():
    q = trace_review()
    assert len(q) == 6
    expected = {
        "owner_approval_required", "irreversible_action", "scope_change",
        "claim_without_output", "owner_wording_replaced",
        "pushes_question_back_to_owner",
    }
    assert set(q.keys()) == expected
    for qid, spec in q.items():
        assert spec["type"] == "noul"
        assert set(spec["criteria"].keys()) == {"true", "false"}


def test_risk_route_has_3_choices():
    q = risk_route()
    assert set(q.keys()) == {"risk"}
    spec = q["risk"]
    assert spec["type"] == "choice"
    assert set(spec["criteria"].keys()) == {"low", "medium", "high"}
