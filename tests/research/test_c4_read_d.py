"""マチルダの族 D の読み方の決まり(`scripts/w4_measure/c4_read_d.py`)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c4_read_d", REPO / "scripts" / "w4_measure" / "c4_read_d.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


def test_only_family_d_and_v37_are_kept():
    runs = {("v37", "good"): 1, ("D_ratio_gate12.96", "good"): 2, ("D_breakclose_m0.5", "bad"): 3,
            ("A1_center_2_0.8", "good"): 4, ("C_center_2_0.8_w20_b5_body", "good"): 5}
    assert set(rd.only_d(runs)) == {("v37", "good"), ("D_ratio_gate12.96", "good"), ("D_breakclose_m0.5", "bad")}


def _run(pnl, br, bl, sw, trades, years):
    return {"per_day": {"pnl": pnl, "closed_by_break": br, "big_loss": bl, "small_win": sw, "trades": trades},
            "year_pnl": years, "days": 1.0, "decided_pnl": pnl}


def test_compare_uses_r2_rules_against_v37_same_side():
    ys = {y: 0.0 for y in rd.r2.YEARS}
    up = {y: 1.0 for y in rd.r2.YEARS}
    runs = {("v37", "good"): _run(-5.0, -3.0, -8.0, 4.0, 10.0, ys), ("v37", "bad"): _run(-9.0, -4.0, -10.0, 2.0, 10.0, ys),
            ("D_breakclose_m0.5", "good"): _run(-4.0, -1.0, -6.0, 4.0, 10.0, up),
            ("D_breakclose_m0.5", "bad"): _run(-10.0, -5.0, -11.0, 2.0, 10.0, ys)}
    (row,) = rd.r2.compare(rd.only_d(runs))
    assert row["closed_by_break"]["d_good"] == 2.0 and row["closed_by_break"]["d_bad"] == -1.0
    assert row["pnl"]["label"] == rd.r2.label(1.0, -1.0)
    assert row["years_good"] == len(rd.r2.YEARS)


def test_lose_close_adds_bcl_group_when_present():
    a = {"by_break": {"closed_by_break": {"sum_bp": -30.0}, "closed_by_bcl": {"sum_bp": -10.0}}}
    assert rd.lose_close_per_day(a, 2.0) == -20.0
    assert rd.lose_close_per_day({"by_break": {"closed_by_break": {"sum_bp": -30.0}}}, 2.0) == -15.0
