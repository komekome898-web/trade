"""カツオの入りと降りの分け方の読み方の決まり(`scripts/w4_measure/c2_read_ablation.py` の R1〜R3)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c2_read_ablation", REPO / "scripts" / "w4_measure" / "c2_read_ablation.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)


def test_names_for_entry_c_uses_close_b_and_ce_lx_b():
    nm = ra.names_for(15, "c", "bad")
    assert nm == {"ref": "weak_f15_close_b", "full": "weak_f15_limit_c_bad",
                  "entry_only": "weak_f15_le_cx_c_good", "exit_only": "weak_f15_ce_lx_b_bad"}
    assert ra.names_for(5, "a", "good")["exit_only"] == "weak_f5_ce_lx_a_good"


def test_split_sums_back_to_total():
    s = ra.split({"ref": 10.0, "full": 4.0, "entry_only": 7.0, "exit_only": 12.0})
    assert s == {"total": -6.0, "entry": -3.0, "exit": 2.0, "interaction": -5.0}
    assert s["entry"] + s["exit"] + s["interaction"] == s["total"]


def _r(pnl, trades=1.0):
    return {"per_day": {"pnl": pnl, "trades": trades}}


def test_decompose_skips_incomplete_and_labels_both_sides():
    runs = {"weak_f5_close_a": _r(10.0), "weak_f5_limit_a_good": _r(4.0), "weak_f5_limit_a_bad": _r(2.0),
            "weak_f5_le_cx_a_good": _r(7.0), "weak_f5_ce_lx_a_good": _r(12.0), "weak_f5_ce_lx_a_bad": _r(9.0)}
    rows = ra.decompose(runs)
    assert len(rows) == 1 and rows[0]["foot"] == 5 and rows[0]["entry"] == "a"
    assert rows[0]["labels"]["entry"] == "減る(両側)"         # 入りだけは両側に同じ値
    assert rows[0]["labels"]["exit"] == "側で割れる"           # +2 / −1
    assert rows[0]["bad_pnl"]["interaction"] == -8.0 - (-3.0) - (-1.0)
