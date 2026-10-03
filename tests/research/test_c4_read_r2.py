"""マチルダ段 1 の読みの決まり(`scripts/w4_measure/c4_read_r2.py` の R3〜R5)を、表を見る前に固める。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("c4_read_r2", REPO / "scripts" / "w4_measure" / "c4_read_r2.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


def _run(pnl_day: float, small: float, big: float, years: dict, decided: float, days: float = 100.0, brk: float = 0.0):
    return {"days": days, "trades": 1000, "wins": 900, "avg_win_bp": 1.0, "undecided_share": 0.5,
            "per_day": {"trades": 10.0, "small_win": small, "big_loss": big, "pnl": pnl_day, "closed_by_break": brk},
            "year_pnl": years, "decided_pnl": decided}


def test_label_rules():
    assert rd.label(1.0, 2.0) == "増える(両側)"
    assert rd.label(-1.0, -0.1) == "減る(両側)"
    assert rd.label(1.0, -1.0) == "側で割れる"
    assert rd.label(0.0, 0.0) == "同じ"
    assert rd.label(0.0, 1.0) == "側で割れる"  # 片側だけ動くのは両側で同じ向きとは言わない


def test_year_agreement_counts_only_2016_2023():
    base = _run(0, 0, 0, {y: 0.0 for y in range(2015, 2024)}, 0)
    var_years = {y: 1.0 for y in range(2016, 2024)}
    var_years[2015] = -100.0  # 2015 は数えない
    var_years[2019] = -1.0
    var = _run(0.06, 0, 0, var_years, 0)
    assert rd.year_agreement(var, base) == 7


def test_decided_same_direction():
    base = _run(0, 0, 0, {}, decided=10.0)
    var = _run(0.1, 0, 0, {}, decided=20.0)
    assert rd.decided_same(var, base) is True
    var2 = _run(0.1, 0, 0, {}, decided=5.0)
    assert rd.decided_same(var2, base) is False


def test_compare_uses_same_side_and_per_day():
    runs = {("v37", "good"): _run(1.0, 5.0, -4.0, {}, 0), ("v37", "bad"): _run(-1.0, 3.0, -4.0, {}, 0),
            ("A9_x", "good"): _run(2.0, 6.0, -4.0, {}, 0), ("A9_x", "bad"): _run(-2.0, 2.0, -4.0, {}, 0)}
    (row,) = rd.compare(runs)
    assert row["small_win"]["d_good"] == 1.0 and row["small_win"]["d_bad"] == -1.0
    assert row["small_win"]["label"] == "側で割れる"
    assert row["big_loss"]["label"] == "同じ"
    assert row["family"] == "A9"


def test_compare_skips_variant_missing_a_side():
    runs = {("v37", "good"): _run(0, 0, 0, {}, 0), ("v37", "bad"): _run(0, 0, 0, {}, 0),
            ("A9_x", "good"): _run(0, 0, 0, {}, 0)}
    assert rd.compare(runs) == []
