"""カツオの門あり・なしの比べの読み方の決まり(`scripts/w4_measure/c2_read_gated.py` の R1〜R4)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c2_read_gated", REPO / "scripts" / "w4_measure" / "c2_read_gated.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)


def test_pairs_need_both_and_match_type():
    names = {"weak_f5_gate_limit_a_good", "weak_f5_limit_a_good", "weak_f5_gate_close_b", "weak_f5_close_b",
             "weak_f15_gate_limit_c_bad", "weak_f30_limit_a_good", "weak_f5_le_cx_a_good"}
    p = rg.pairs(names)
    assert ("weak_f5_gate_limit_a_good", "weak_f5_limit_a_good") in p
    assert ("weak_f5_gate_close_b", "weak_f5_close_b") in p
    assert len(p) == 2                       # 15 分の c 悪は門なしが無い。30 分・le_cx は対象外


def _run(year_pnl, per_day=0.0, trades=0.0, per_trade=0.0):
    return {"year_pnl": year_pnl, "per_day": {"pnl": per_day, "trades": trades}, "per_trade": per_trade}


def test_oos_uses_2020_to_2023_only():
    r = _run({2017: 1e6, 2018: 1e6, 2019: 1e6, 2020: 1447.0, 2021: 0.0, 2022: 0.0, 2023: 1447.0})
    assert rg.oos_per_day(r) == 2.0


def test_oos_year_agreement_counts_sign_matches():
    g = _run({2020: 10.0, 2021: 10.0, 2022: -10.0, 2023: 10.0})
    u = _run({2020: 0.0, 2021: 0.0, 2022: 0.0, 2023: 0.0})
    assert rg.oos_year_agreement(g, u) == 3


def test_side_labels_from_oos_diff():
    rows = [{"gated": "weak_f5_gate_limit_a_good", "d_oos_day": 1.0},
            {"gated": "weak_f5_gate_limit_a_bad", "d_oos_day": -1.0},
            {"gated": "weak_f15_gate_limit_b_good", "d_oos_day": 2.0},
            {"gated": "weak_f15_gate_limit_b_bad", "d_oos_day": 3.0}]
    lab = rg.side_labels(rows)
    assert lab == {"f5_limit_a": "側で割れる", "f15_limit_b": "増える(両側)"}
