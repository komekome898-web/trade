"""分析のスキルの読み口(`scripts/analysis/diag_tables.py`)の決まりを固める試験。"""
from __future__ import annotations

import gzip
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))
import diag_tables as dt  # noqa: E402


def _daily(vals: list[float], start=date(2018, 1, 1)) -> dict[str, float]:
    return {(start + timedelta(days=i)).isoformat(): v for i, v in enumerate(vals)}


def test_outcome_broke_when_second_half_vanishes():
    rng = random.Random(1)
    vals = [100 + rng.gauss(0, 50) for _ in range(400)] + [rng.gauss(0, 50) for _ in range(400)]
    assert dt.d1(_daily(vals))["segments"]["outcome"] == "崩れた"


def test_outcome_undecided_when_small_and_few_days():
    vals = [3 + 60 * (1 if (i * 7) % 3 else -2) / 1.5 for i in range(60)]  # 平均は小さく、散らばりは大きい
    assert dt.d1(_daily(vals))["segments"]["outcome"] == "決まらない"


def test_outcome_continues_when_constant_and_many_days():
    rng = random.Random(3)
    vals = [20 + rng.gauss(0, 30) for _ in range(1500)]
    assert dt.d1(_daily(vals))["segments"]["outcome"] == "続いている"


def test_outcome_rules_direct():
    f = {"mean": 50, "lo": 30, "hi": 70}
    assert dt.d1_outcome(f, {"mean": -5, "lo": -20, "hi": 10}, {"lo": -80, "hi": -30}) == "崩れた"
    assert dt.d1_outcome(f, {"mean": 40, "lo": 10, "hi": 70}, {"lo": -30, "hi": 10}) == "続いている"
    assert dt.d1_outcome(f, {"mean": 20, "lo": -1, "hi": 40}, {"lo": -50, "hi": 5}) == "決まらない"
    assert dt.d1_outcome(f, {"mean": -40, "lo": -60, "hi": -20}, {"lo": -120, "hi": -70}) == "崩れた"  # 逆の符号
    assert dt.d1_outcome(f, {"mean": 30, "lo": 10, "hi": 50}, {"lo": -40, "hi": -2}) == "続いている(縮んだ)"


def test_direction_is_fixed_not_taken_from_first_half():
    """前半が負で後半が正は「崩れた」ではない。前半が 0 付近で後半が正は「続いている」ではない。"""
    neg = {"mean": -20, "lo": -35, "hi": -5}
    pos = {"mean": 20, "lo": 5, "hi": 35}
    zero = {"mean": 0, "lo": -15, "hi": 15}
    assert dt.d1_outcome(neg, pos, {"lo": 20, "hi": 60}) == "後半だけ"
    assert dt.d1_outcome(zero, pos, {"lo": -5, "hi": 40}) == "後半だけ"
    assert dt.d1_outcome(neg, neg, {"lo": -20, "hi": 20}) == "成り立たない(逆向き)"
    assert dt.d1_outcome(zero, zero, {"lo": -20, "hi": 20}) == "決まらない"


def test_bands_do_not_collapse_on_ties():
    vals = [0.0] * 60 + [1.0] * 20 + [5.0, 8.0, 9.0, 20.0] * 5
    edges, name = dt.bands_by_edges(vals)
    assert edges == sorted(set(edges))
    names = {name(v) for v in vals}
    assert len(names) == len(edges) + 1 or len(names) == len(edges)
    assert name(0.0) == "〜0 分"


def _write_run(d: Path, trades: list[dict], period):
    d.mkdir(parents=True)
    import csv
    with gzip.open(d / "trades.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["entry_t", "exit_t", "pnl_bp", "undecided", "exit_reason"])
        w.writeheader()
        for t in trades:
            w.writerow(t)
    (d / "summary.json").write_text(json.dumps({"period": period, "params": {}}), encoding="utf-8")


def test_assumption_free_part_and_stop(tmp_path):
    good, bad = [], []
    day = date(2020, 1, 1)
    for i in range(40):
        ds = (day + timedelta(days=i)).isoformat()
        good.append({"entry_t": f"{ds}T01:00:00Z", "exit_t": f"{ds}T02:00:00Z", "pnl_bp": 10, "undecided": 1, "exit_reason": "tp"})
        good.append({"entry_t": f"{ds}T03:00:00Z", "exit_t": f"{ds}T04:00:00Z", "pnl_bp": -4, "undecided": 0, "exit_reason": "brk"})
        bad.append({"entry_t": f"{ds}T01:00:00Z", "exit_t": f"{ds}T02:00:00Z", "pnl_bp": -6, "undecided": 1, "exit_reason": "brk"})
        bad.append({"entry_t": f"{ds}T03:00:00Z", "exit_t": f"{ds}T04:00:00Z", "pnl_bp": -4, "undecided": 0, "exit_reason": "brk"})
    period = ["2020-01-01T00:00:00Z", "2020-02-10T00:00:00Z"]
    _write_run(tmp_path / "g", good, period)
    _write_run(tmp_path / "b", bad, period)
    r = dt.d8(dt.load_run(str(tmp_path / "g")), dt.load_run(str(tmp_path / "b")))
    assert r["assumption_free"]["good"]["mean"] == pytest.approx(-4.0)
    assert r["stop"] is True
    assert r["undecided"]["good"]["trades"] == 40


def test_refuses_window_outputs(tmp_path):
    with pytest.raises(SystemExit):
        dt.load_run(str(REPO / "docs" / "RESEARCH" / "WINDOW1" / "runs" / "K-0"))
