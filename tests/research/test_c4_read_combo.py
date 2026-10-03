"""マチルダの組み合わせ C の読み方の決まり(`scripts/w4_measure/c4_read_combo.py` の R1〜R4)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c4_read_combo", REPO / "scripts" / "w4_measure" / "c4_read_combo.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)


def test_names_match_existing_run_names():
    nm = rc.names_for(2, 0.8, 20, 5, "body", "good")
    assert nm == {"base": "v37_good", "tp": "A1_center_2_0.8_good", "ruler": "A3_w20_b5_body_good",
                  "both": "C_center_2_0.8_w20_b5_body_good"}


def test_split_interaction():
    s = rc.split({"base": -10.0, "tp": -4.0, "ruler": -7.0, "both": 0.0})
    assert s == {"tp": 6.0, "ruler": 3.0, "both": 10.0, "interaction": 1.0}


def _run(pnl, years):
    return {"per_day": {"pnl": pnl}, "year_pnl": years, "days": 1.0}


def test_year_agreement_against_best_single():
    ys = {y: 0.0 for y in rc.YEARS}
    runs = {"tp": _run(5.0, dict(ys)), "ruler": _run(1.0, dict(ys)),
            "both": _run(6.0, {y: (1.0 if y < 2022 else -1.0) for y in rc.YEARS})}
    nm = {"tp": "tp", "ruler": "ruler", "both": "both"}
    # 良い方の単独 = tp。両方 − tp の年の差は 2016〜2021 が正(6 年)、2022・2023 が負。全期間の差(1 日あたり 6 − 5)の符号は正
    assert rc.year_agree_vs_best_single(runs, nm) == 6
