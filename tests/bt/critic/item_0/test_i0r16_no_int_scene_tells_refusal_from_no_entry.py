"""Critic, item 0, round 16 (i0-r16-04, 場面集): the P0-2 unit scenes whose
input has sub-nanosecond digits (expected `scenes.NO_INT`) cannot tell a
target that REFUSES to round from a target that has no time conversion at
all.

scenes.py: "no int64 ns is right (NO_INT: any int returned is a different
time = 不一致; a refusal is 対応なし, above it by rule 5)"; measures:
"対象自身の変換が、この単位の時刻を丸めずに int64 ナノ秒にするか(ナノ秒の整数にならない値を黙って丸めないか)".
adapters/common.py `unit_time`: a target with no entry for the unit is
`not_supported` ("対応なし"); an entry that raises is `not_supported` too.
run_battery.py `correctness`: every `not_supported` is "対応なし". So in the
five NO_INT scenes the target whose conversion refuses (the capability the
scene measures) and a target with no conversion (no capability) get the same
cell; nothing can be "正解と一致". The lead's answer before round 16
(VERDICTS run11 item0, 08:50 UTC, i0-r15-05): "正解は手計算の int ナノ秒 1 つで、
float が正確に持たない値では「断る」も正解に入れる(黙って丸めた値は不一致)". Rule 1:
a capability is decided by the result of using it, never by its absence
looking the same.

Grid: every NO_INT scene (scenes.UNIT_SCENES whose expected int64_ns is
NO_INT) x {the new implementation's adapter (its conversion refuses); a
target with no entry (common.unit_time with no entries)}. Oracle: the two
cells differ.

Not in the grid: the survey rows (a target with no entry is the best of
the survey side in these scenes: survey_results/opp_gobacktest.tsv).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

B = Path(__file__).resolve().parents[2] / "battery" / "item_0"
for p in (B, B / "adapters"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import scenes  # noqa: E402

NO_INT_SCENES = [s for s in scenes.SCENES
                 if s.id in scenes.UNIT_SCENES and s.expected.get("int64_ns") == scenes.NO_INT]


def test_the_grid_is_not_empty():
    assert len(NO_INT_SCENES) == 5


@pytest.mark.parametrize("sc", NO_INT_SCENES, ids=lambda s: s.id)
def test_a_refusal_is_told_from_no_conversion(sc):
    import common as C
    import run_battery as R
    new = R.load_adapter("new_impl")
    refused = new.run_scene(sc)
    none = C.unit_time(sc, [], "no entry")
    a = R.correctness(refused, sc.expected, sc, "new_impl")
    b = R.correctness(none, sc.expected, sc, "no_entry")
    assert a != b, (f"{sc.id}: the target that refuses to round ({refused.status}: {refused.detail[:80]}) and a "
                    f"target with no time conversion both grade {a!r}")
