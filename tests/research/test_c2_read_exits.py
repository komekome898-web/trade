"""カツオの長い保有の降り方の読み方の決まり(`scripts/w4_measure/c2_read_exits.py` の R1〜R4)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c2_read_exits", REPO / "scripts" / "w4_measure" / "c2_read_exits.py")
rx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rx)


def test_pairs_same_foot_base_only_when_both_exist():
    names = {"weak_f5_close_a", "weak_f5_close_a_stop1", "weak_f5_close_a_time24", "weak_f15_close_a_stop2",
             "weak_f5_gate_close_a", "weak_f15_close_b"}
    assert rx.pairs(names) == [("weak_f5_close_a_stop1", "weak_f5_close_a"), ("weak_f5_close_a_time24", "weak_f5_close_a")]


def test_new_exit_sums_only_the_two_new_reasons():
    a = {"by_exit_signal": {"値段で降りる": {"trades": 3, "sum_bp": -12.0}, "時間で降りる": {"trades": 2, "sum_bp": 5.0},
                            "弱い合図": {"trades": 9, "sum_bp": 40.0}}}
    assert rx.new_exit(a) == {"trades": 5, "sum_bp": -7.0}
    assert rx.new_exit({"by_exit_signal": {"弱い合図": {"trades": 1, "sum_bp": 1.0}}}) == {"trades": 0, "sum_bp": 0}


def _run(pnl_total, days, trades, years):
    return {"days": days, "per_day": {"pnl": pnl_total / days, "trades": trades / days},
            "per_trade": pnl_total / trades, "year_pnl": years, "hold": None}


def test_compare_differences_and_year_agreement():
    ys_b = {y: 10.0 for y in rx.rl.YEARS}
    ys_x = {y: (12.0 if y != 2019 else 5.0) for y in rx.rl.YEARS}
    runs = {"weak_f5_close_a": _run(60.0, 10.0, 6, ys_b), "weak_f5_close_a_stop1": _run(67.0, 10.0, 7, ys_x)}
    alls = {"weak_f5_close_a": {"sum_win_bp": 100.0, "sum_loss_bp": -40.0},
            "weak_f5_close_a_stop1": {"sum_win_bp": 90.0, "sum_loss_bp": -23.0,
                                      "by_exit_signal": {"値段で降りる": {"trades": 4, "sum_bp": -8.0}}}}
    (r,) = rx.compare(runs, alls)
    assert abs(r["d_pnl_day"] - 0.7) < 1e-12
    assert abs(r["d_win_day"] + 1.0) < 1e-12 and abs(r["d_loss_day"] - 1.7) < 1e-12
    assert r["new_exit"] == {"trades": 4, "sum_bp": -8.0}
    # 全期間の差は正。2019 だけ年の差が負なので、6 年中 5 年
    assert r["years_agree"] == len(rx.rl.YEARS) - 1


def test_hold_diff_by_band():
    x = [{"lo": 0, "hi": 5, "trades": 3, "sum_bp": 1.0}, {"lo": 480, "hi": None, "trades": 1, "sum_bp": -50.0}]
    b = [{"lo": 0, "hi": 5, "trades": 2, "sum_bp": 4.0}, {"lo": 480, "hi": None, "trades": 4, "sum_bp": -90.0}]
    assert rx.hold_diff(x, b) == [{"lo": 0, "hi": 5, "d_trades": 1, "d_sum_bp": -3.0},
                                  {"lo": 480, "hi": None, "d_trades": -3, "d_sum_bp": 40.0}]
    assert rx.hold_diff(None, b) is None
