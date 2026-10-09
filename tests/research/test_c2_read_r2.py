"""カツオの改良の周 2 の読み方の決まり(`scripts/w4_measure/c2_read_r2.py` の R1〜R9)を、走らせる前に固める。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
_spec = importlib.util.spec_from_file_location("c2_read_r2", REPO / "scripts" / "w4_measure" / "c2_read_r2.py")
r2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r2)


def _run(total, days, trades, years=None):
    ys = years or {y: total / len(r2.rl.YEARS) for y in r2.rl.YEARS}
    return {"days": days, "per_day": {"pnl": total / days, "trades": trades / days},
            "per_trade": total / trades, "year_pnl": ys, "hold": None}


def _all(win, loss):
    return {"sum_win_pct": win, "sum_loss_pct": loss}


def test_names_and_wanted_set():
    assert r2.T(6) == "weak_f15_close_a_time6" and r2.C(12) == "weak_f15_rgate_close_a_time12"
    assert r2.T(6, True) == "weak_f15_close_a_refjoin_time6"
    assert r2.C(6, True) == "weak_f15_rgate_close_a_refjoin_time6"
    w = r2.wanted()
    # 基準・門・内部結合 4 本 + 時間だけ 7 本 + 組んだ形 7 本 + 内部結合の時間だけ 1 本
    assert len(w) == 4 + 7 + 7 + 3
    # 走らせの一覧(c2_limit_batch.JOBS_R2)の 16 本は、読みが求める名前のうち、まだ無いもの全部
    spec = importlib.util.spec_from_file_location("c2_limit_batch", REPO / "scripts" / "w4_measure" / "c2_limit_batch.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    jobs = {n for n, _ in bt.JOBS_R2}
    assert len(jobs) == 16 and jobs <= w
    assert w - jobs == {r2.B, r2.G, r2.BJ, r2.T(6), r2.T(12)}


def test_additivity_and_vs_best_single():
    runs = {r2.B: _run(100.0, 10.0, 50), r2.G: _run(130.0, 10.0, 30),
            r2.T(6): _run(150.0, 10.0, 50), r2.C(6): _run(170.0, 10.0, 30)}
    alls = {k: _all(200.0, -100.0) for k in runs}
    out = r2.build(runs, alls)
    row = next(x for x in out["rows"] if x["n"] == 6)
    assert abs(row["dT"]["pnl"] - 5.0) < 1e-12 and abs(out["dG"]["pnl"] - 3.0) < 1e-12
    assert abs(row["dC"]["pnl"] - 7.0) < 1e-12
    assert abs(row["add"]["overlap"] - (7.0 - 5.0 - 3.0)) < 1e-12
    assert abs(row["add"]["vs_best_single"] - (7.0 - 5.0)) < 1e-12
    assert abs(row["dC"]["trades"] + 2.0) < 1e-12
    # ほかの N は走らせが無いので None
    assert next(x for x in out["rows"] if x["n"] == 7)["dC"] is None


def test_best_n_reports_candidates_and_neighbours():
    rows = [{"n": n, "dC": ({"pnl": p} if p is not None else None)}
            for n, p in ((6, 1.0), (7, 4.0), (8, 2.0), (9, None), (10, 0.5), (11, 0.1), (12, 0.0))]
    b = r2.best_n(rows)
    assert b == {"n": 7, "dC": 4.0, "candidates": 6, "left": 1.0, "right": 2.0}
    assert r2.best_n([{"n": 6, "dC": None}]) is None


def test_trade_overlap_groups():
    b = [("t1", "x", -50.0), ("t2", "x", 10.0), ("t3", "x", -20.0), ("t4", "x", 5.0)]
    g = [("t2", "x", 10.0), ("t3", "x", -20.0)]  # t1・t4 が門で外れた
    t = [("t1", "時間で降りる", -5.0), ("t2", "時間で降りる", 8.0), ("t3", "反対の弱い合図", -20.0), ("t4", "x", 5.0)]
    o = r2.trade_overlap(b, g, t)
    assert o["both"] == {"trades": 1, "sum_pct": -50.0}
    assert o["gate_only"] == {"trades": 1, "sum_pct": 5.0}
    assert o["time_only"] == {"trades": 1, "sum_pct": 10.0}
    assert o["neither"] == {"trades": 1, "sum_pct": -20.0}


def test_year_agreement_and_2019on_sum():
    ys_b = {y: 10.0 for y in r2.rl.YEARS}
    ys_c = {y: (20.0 if y != 2018 else 0.0) for y in r2.rl.YEARS}
    runs = {r2.B: _run(60.0, 10.0, 6, ys_b), r2.C(8): _run(100.0, 10.0, 6, ys_c)}
    alls = {k: _all(1.0, -1.0) for k in runs}
    row = next(x for x in r2.build(runs, alls)["rows"] if x["n"] == 8)
    assert row["years_agree"] == len(r2.rl.YEARS) - 1  # 2018 だけ逆
    assert row["dC_2019on"] == 50.0  # 2019〜2023 の 5 年 × 10


def test_join_difference_against_unjoined():
    runs = {r2.B: _run(100.0, 10.0, 10), r2.C(6): _run(160.0, 10.0, 10),
            r2.BJ: _run(80.0, 10.0, 10), r2.C(6, True): _run(110.0, 10.0, 10)}
    alls = {k: _all(1.0, -1.0) for k in runs}
    j = next(x for x in r2.build(runs, alls)["join"] if x["n"] == 6)
    assert abs(j["dCj"]["pnl"] - 3.0) < 1e-12
    assert abs(j["dCj_minus_dC"] - (3.0 - 6.0)) < 1e-12
    assert j["add_j"] is None  # 時間だけ・門だけの結合の走らせが無い


def test_read_daily_and_paired_ci(tmp_path):
    import csv
    import gzip
    from datetime import date
    d = tmp_path / "run"
    d.mkdir()
    with gzip.open(d / "trades.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["exit_t", "pnl_bp"])
        w.writerow(["2020-01-01T23:59:00Z", "5"])
        w.writerow(["2020-01-03T00:00:00Z", "-2"])
        w.writerow(["2020-01-03T10:00:00Z", "1"])
        w.writerow(["2020-02-01T00:00:00Z", "100"])  # 範囲の外
    x = r2.read_daily(str(d), date(2020, 1, 1), date(2020, 1, 4))
    assert x == pytest.approx([0.05, 0.0, -0.01, 0.0], abs=1e-15)  # 前の出力の pnl_bp は / 100 して %
    assert r2.read_daily(str(tmp_path / "none"), date(2020, 1, 1), date(2020, 1, 2)) is None
    c = r2.paired_ci([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], [0.0] * 6)
    assert c["days"] == 6 and abs(c["mean"] - 3.5) < 1e-12 and c["lo"] <= 3.5 <= c["hi"] and c["mde"] > 0
