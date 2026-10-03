"""カツオの指値の読みの決まり(`scripts/w4_measure/c2_read_limit.py` の R1・R2・R4・R5)を、表を見る前に固める。"""
from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("c2_read_limit", REPO / "scripts" / "w4_measure" / "c2_read_limit.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)


def _run(pnl_day: float, years: dict, days: float = 100.0):
    return {"days": days, "per_day": {"pnl": pnl_day, "trades": 1.0}, "year_pnl": years}


def test_reference_pairs():
    assert rd.REF == {"a": "close_a", "b": "close_b", "c": "close_b"}


def test_label():
    assert rd.label(1, 2) == "増える(両側)"
    assert rd.label(-1, -2) == "減る(両側)"
    assert rd.label(1, -2) == "側で割れる"
    assert rd.label(0, 0) == "同じ"


def test_compare_pairs_within_group_and_side():
    runs = {
        "weak_f5_close_a": _run(10.0, {}), "weak_f5_close_b": _run(20.0, {}),
        "weak_f5_limit_a_good": _run(12.0, {}), "weak_f5_limit_a_bad": _run(8.0, {}),
        "weak_f5_limit_c_good": _run(25.0, {}), "weak_f5_limit_c_bad": _run(21.0, {}),
        "weak_f15_close_a": _run(-5.0, {}),
    }
    rows = {(r["group"], r["entry"]): r for r in rd.compare(runs)}
    a = rows[("weak_f5", "a")]
    assert a["ref"] == "weak_f5_close_a"
    assert a["pnl"]["d_good"] == 2.0 and a["pnl"]["d_bad"] == -2.0 and a["pnl"]["label"] == "側で割れる"
    c = rows[("weak_f5", "c")]
    assert c["ref"] == "weak_f5_close_b" and c["pnl"]["label"] == "増える(両側)"
    assert ("weak_f5", "b") not in rows  # 指値の b が無ければ作らない


def test_year_agreement_six_years():
    ref = _run(0.0, {y: 0.0 for y in range(2017, 2024)})
    years = {y: 1.0 for y in range(2018, 2024)}
    years[2017] = -50.0  # 2017 は数えない
    years[2020] = -1.0
    var = _run(0.05, years)
    assert rd.year_agreement(var, ref) == 5


def test_hold_bins(tmp_path):
    m = 60 * 10**9
    o = {"version": 1, "t_unit": "ns", "entry_t_ns": [0, 0, 0, 0], "exit_t_ns": [4 * m, 5 * m, 200 * m, 600 * m],
         "entry_px": [1] * 4, "exit_px": [1] * 4, "side": [1] * 4, "qty": [1] * 4, "pnl_bp": [1.0, 2.0, 3.0, 4.0]}
    p = tmp_path / "t.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(o, fh)
    h = rd.hold_sums(str(p))
    assert [x["trades"] for x in h] == [1, 1, 0, 1, 1]
    assert [x["sum_bp"] for x in h] == [1.0, 2.0, 0.0, 3.0, 4.0]
