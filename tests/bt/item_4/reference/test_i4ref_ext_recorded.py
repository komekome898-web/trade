"""Pins the recorded cross-check against backtesting.py 0.6.6 (synthetic
scenes only) so that it keeps holding without the external tool installed.

The record was produced by ext_backtesting_compare.py in an isolated venv
(see SPEC.md section 5). Here the reference side is recomputed from the
recorded inputs and compared with the recorded external numbers:
  * every scene without a favourable open gap must match exactly as recorded
    (tolerance 1e-6 on prices / pnl / final equity);
  * every scene with a favourable open gap must still match on all trades
    that exit before the first such bar (the documented rule difference).
"""
from __future__ import annotations

import json
import pathlib

import ext_backtesting_compare as cmp

REC = pathlib.Path(__file__).parent / "ext_results" / "backtesting_py_0.6.6.json"


def load():
    return json.loads(REC.read_text(encoding="utf-8"))


def test_record_is_synthetic_and_complete():
    d = load()
    s = d["summary"]
    assert s["tool"] == "backtesting.py" and s["tool_version"] == "0.6.6"
    assert s["data"].startswith("synthetic")
    assert len(d["rows"]) == s["scenes"] == 200
    assert s["matched_without_favourable_gap"] == s["scenes_without_favourable_gap"] > 100
    assert s["trades_compared"] > 500


def test_reference_still_matches_recorded_external_numbers():
    d = load()
    no_gap = gap = 0
    for row in d["rows"]:
        ref = cmp.run_reference(row["input"])
        r = cmp.summarise_reference(ref)
        gaps = cmp.favourable_gaps(row["input"], ref)
        assert gaps == row["favourable_gaps"]
        if not gaps:
            assert cmp.same(r, row["external"]), row["scene"]
            no_gap += 1
        else:
            first = min(b for _, b in gaps)
            rb = [t for t in r["trades"] if t["exit_bar"] < first]
            eb = [t for t in row["external"]["trades"] if t["exit_bar"] < first]
            assert len(rb) == len(eb)
            for x, y in zip(rb, eb):
                assert cmp.same({"trades": [x], "missed_fills": 0, "equity_final": 0},
                                {"trades": [y], "missed_fills": 0, "equity_final": 0})
            gap += 1
    assert no_gap == d["summary"]["scenes_without_favourable_gap"]
    assert gap == d["summary"]["scenes_with_favourable_gap"]


def test_flipping_a_mapped_mode_breaks_the_match():
    """The comparison can see each mapped rule: flipping one loses matches."""
    d = load()
    rows = [r for r in d["rows"] if not r["favourable_gaps"]]
    for k, v in cmp.SENSITIVITY_VARIANTS.items():
        m = sum(cmp.same(cmp.summarise_reference(cmp.run_reference(r["input"], **{k: v})), r["external"])
                for r in rows)
        assert m < len(rows), k
        assert m == d["summary"]["sensitivity_matches_without_gap"][f"{k}={v}"]
