"""Critic, item 0, round 6 (i0-r6-02, scene-set side).

P0-5 (REQUIREMENTS.md section 2) measures "同時刻の複数事象に決定的な並び規則"
with "同時刻に複数型の事象を仕込んだ入力". Its two multi-type scenes,
p5-same-time-twice and p5-hand-over-order, put a trade, a bar, a funding
and a liquidation at one time. No survey candidate (run or reproduced) holds
all four types, so every survey cell of both scenes is 対応なし -- for a
lack that P0-3 already measures (p3-funding, p3-liquidation,
p3-mixed-one-run), not for a lack of an ordering rule. The scene keeper's
own probe (survey_results/attempts/1.log, "probe r6-1") shows Basana
passing both P0-5 checks on the same inputs restricted to its own types
(FOLLOWS True, distinct_orders_over_hand_overs 1), and the table shows the
survey side 1 / 3 on P0-5 against 3 / 3: the per-viewpoint comparison
(scene-set rule 3) reports an ordering gap that the records do not show.

The same coupling sits in p1-merge-by-time (P0-1, needs funding); there the
reproduced LEAN holds all its types, so the survey cell is not 対応なし.

The test states the condition for a multi-type scene of P0-1 / P0-5 to
measure its own viewpoint: where the survey side's best cell of the scene
(scene-set rule 5 order) is not 正解と一致, at least one survey target
(opp_* or repro_*) must show that it holds EVERY type the scene puts in (its
p3-<type> cell is 正解と一致), so that the survey side's shortfall on the
scene is about the viewpoint, not about P0-3.
"""
from __future__ import annotations

import csv
import glob
from pathlib import Path

import pytest

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_0"
csv.field_size_limit(10**9)

MULTI_TYPE_SCENES = ["p1-merge-by-time", "p5-same-time-twice", "p5-hand-over-order"]


def _survey_cells() -> dict[str, dict[str, str]]:
    out = {}
    for f in sorted(glob.glob(str(BATTERY / "survey_results" / "*.tsv"))):
        with open(f, encoding="utf-8") as fh:
            out[Path(f).stem] = {r["scene_id"]: r["correctness"] for r in csv.DictReader(fh, delimiter="\t")}
    return out


def _scene_kinds(scene_id: str) -> set[str]:
    import sys

    sys.path.insert(0, str(BATTERY))
    try:
        import scenes  # noqa: WPS433
    finally:
        sys.path.remove(str(BATTERY))
    sc = next(s for s in scenes.SCENES if s.id == scene_id)
    streams = sc.input["streams"]
    return {e.get("kind", "trade") for evs in streams.values() for e in evs}


_ORDER = {"正解と一致": 0, "対応なし": 1, "不一致": 2, "結果なし": 3}


@pytest.mark.parametrize("scene_id", MULTI_TYPE_SCENES)
def test_a_survey_shortfall_on_a_multi_type_scene_is_not_only_a_missing_type(scene_id):
    kinds = _scene_kinds(scene_id)
    cells = _survey_cells()
    best = min((c[scene_id] for c in cells.values() if scene_id in c), key=_ORDER.__getitem__)
    if best == "正解と一致":
        return
    holders = [t for t, c in cells.items() if all(c.get(f"p3-{k}") == "正解と一致" for k in kinds)]
    assert holders, (
        f"{scene_id}: the survey side's best cell is {best}, and the scene puts in the types {sorted(kinds)}, "
        f"which no survey target holds all of (none is 正解と一致 on every p3-<type>); the shortfall is decided "
        f"by P0-3, not by the viewpoint this scene belongs to"
    )
