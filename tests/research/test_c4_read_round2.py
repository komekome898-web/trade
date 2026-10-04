"""マチルダの改良の周 2 の読み方の決まり(`scripts/w4_measure/c4_read_round2.py` の R1〜R7)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c4_read_round2", REPO / "scripts" / "w4_measure" / "c4_read_round2.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def _run(pnl, trades=10.0, years=None):
    ys = years or {y: pnl for y in range(2016, 2024)}
    pd = {"pnl": pnl, "small_win": pnl + 1, "big_loss": -1.0, "closed_by_break": -0.5, "trades": trades}
    return {"per_day": pd, "year_pnl": ys, "days": 1.0}


def test_wanted_names():
    w = rr.wanted()
    assert len(w) == 2 * 6  # 2 側 × (v37・利確・固定の門・固定×利確・過去だけ・過去だけ×利確)
    assert "R2_ratio_gate_rolling_center_4_3_bad" in w and "D_ratio_gate12.96_good" in w


def test_decompose_interaction_and_rolling_minus_fixed():
    runs = {}
    for s in rr.SIDES:
        runs[f"v37_{s}"] = _run(0.0)
        runs[f"A1_center_4_3_{s}"] = _run(5.0)
        runs[f"D_ratio_gate12.96_{s}"] = _run(3.0, trades=9.0)
        runs[f"R2_ratio_gate12.96_center_4_3_{s}"] = _run(6.0, trades=9.0)
        runs[f"R2_ratio_gate_rolling_{s}"] = _run(2.0)
        runs[f"R2_ratio_gate_rolling_center_4_3_{s}"] = _run(7.0)
    dec = rr.decompose(runs)
    g = dec["fixed"]["good"]["pnl"]
    assert g == {"tp": 5.0, "ruler": 3.0, "both": 6.0, "interaction": 6.0 - 5.0 - 3.0}
    assert dec["fixed"]["good"]["trades"]["ruler"] == -1.0
    rf = rr.rolling_minus_fixed(dec)
    assert rf["good"]["pnl"] == {"gate": 2.0 - 3.0, "both": 7.0 - 6.0}
    del runs["R2_ratio_gate_rolling_bad"]
    assert rr.decompose(runs)["rolling"] is None


def test_big_loss_overlap_groups():
    base = [("t1", "x", -30.0), ("t2", "x", -12.0), ("t3", "x", -15.0), ("t4", "x", -50.0), ("t5", "x", 3.0)]
    gate = [("t2", "x", -12.0), ("t3", "x", -15.0), ("t5", "x", 3.0)]  # t1・t4 が門で外れた
    tp = [("t1", "x", -5.0), ("t2", "x", 2.0), ("t3", "x", -15.0), ("t4", "x", -40.0), ("t5", "x", 1.0)]
    o = rr.big_loss_overlap(base, gate, tp)
    assert o["both"] == {"trades": 1, "sum_bp": -30.0}
    assert o["gate_only"] == {"trades": 1, "sum_bp": -50.0}
    assert o["tp_only"] == {"trades": 1, "sum_bp": -12.0}
    assert o["neither"] == {"trades": 1, "sum_bp": -15.0}  # t5 は大負けでないので数えない


def test_daily_and_ci():
    rows = [("e", "2020-01-01T10:00:00Z", 4.0), ("e", "2020-01-03T00:00:00Z", -1.0), ("e", "2021-01-01T00:00:00Z", 9.0)]
    assert rr.daily(rows, date(2020, 1, 1), date(2020, 1, 3)) == [4.0, 0.0, -1.0]
    c = rr.paired_ci([2.0, 4.0, 6.0, 8.0, 10.0, 12.0], [0.0] * 6)
    assert c["days"] == 6 and abs(c["mean"] - 7.0) < 1e-12 and c["lo"] <= 7.0 <= c["hi"] and c["mde"] > 0
