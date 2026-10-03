"""参照と段階 G の突き合わせの読み方の決まり(`scripts/w4_measure/c2_ref_vs_g_match.py` の R1〜R4)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("c2_ref_vs_g_match", REPO / "scripts" / "w4_measure" / "c2_ref_vs_g_match.py")
mm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mm)


def test_identity_holds_and_counts():
    ref = [(100, 1, 200, 5.0), (300, -1, 400, -2.0), (500, 1, 600, 1.0)]
    g = [(100, 1, 250, 3.0), (300, -1, 400, -2.0), (700, -1, 800, 4.0)]
    m = mm.match_year(ref, g)
    assert (m["common_n"], m["r_only_n"], m["g_only_n"]) == (2, 1, 1)
    assert m["common_exit_differs_n"] == 1
    assert abs(m["diff_bp"] - (m["r_only_bp"] - m["g_only_bp"] + m["common_diff_bp"])) < 1e-9
    assert m["common_diff_bp"] == 2.0


def test_side_is_part_of_key_and_duplicates_pair_in_order():
    ref = [(100, 1, 200, 1.0), (100, 1, 300, 2.0)]
    g = [(100, -1, 200, 1.0), (100, 1, 200, 1.0)]
    m = mm.match_year(ref, g)
    assert (m["common_n"], m["r_only_n"], m["g_only_n"]) == (1, 1, 1)


def test_g_pnl_sign_and_year_of_bar_start():
    g = mm.g_trades([{"entry_t_ns": 1, "exit_t_ns": 2, "entry_px": 100.0, "exit_px": 101.0, "side": "sell"}])
    assert abs(g[0][3] + 100.0) < 1e-9
    # 2020-01-01T00:00Z ちょうどに建てた 5 分の取引は、建てた足の始まりが 2019 年
    assert mm.year_of(1577836800 * 10**9, 5) == 2019
