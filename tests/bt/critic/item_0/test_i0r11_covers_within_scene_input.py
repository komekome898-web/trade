"""Critic, item 0, round 11 (i0-r11-02, scene-set side): a cell of the grid
table is "場面にした" only if a scene of its viewpoint actually runs an event
of that market type.

Round r11-1 makes each cell's verdict from the scenes' `covers` alone
(grid_c.py `verdict`), and `covers` is a declaration written by hand
(scenes.py `COVERS`: "A scene whose events the scene leaves to the target
... covers each market type it may be run with"). The lead's answer to the
audit br11-1-1 (LEAD_DESIGN.md section 8.5 item 24): "`covers` の事象の軸は、
その場面の入力(scenes.py の入力の事象と `type_plan` で作る事象)に実際に含まれる
型から機械で出す". A scene that runs ONE type the target picks (p1-one-call-
per-event, p2-event-time-exact, p2-one-ns-apart, p5-same-stream-order), one
that runs no event at all (p2-iso-*), and a `type_plan` scene that builds 2-4
of the 6 types even for a target that has all 6 (p1-merge-by-time,
p1-typed-events, p5-*) each declare all 6 market types.

Oracle: for every scene, the market-type values of its `covers` are a subset
of the kinds in its input events (`events` and `streams`), with `type_plan`
scenes built for a target that has every type (scenes.for_target_types).
The event values that are not market types (notices, the clock, the
out-of-axis cancel notice) are not judged here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_0"
sys.path.insert(0, str(BATTERY))

import scenes  # noqa: E402  (scene-set side, on sys.path above)

MARKET = {scenes.JP[k] for k in scenes.TYPE_ORDER}


def _kinds(scene) -> set:
    built = scenes.for_target_types(scene, scenes.TYPE_ORDER) if scene.type_plan is not None else scene
    inp = built.input if isinstance(built.input, dict) else {}
    out = set()
    for e in inp.get("events", []) or []:
        if isinstance(e, dict) and e.get("kind"):
            out.add(scenes.JP[e["kind"]])
    for stream in (inp.get("streams") or {}).values():
        for e in stream:
            if isinstance(e, dict) and e.get("kind"):
                out.add(scenes.JP[e["kind"]])
    return out


@pytest.mark.parametrize("scene", scenes.SCENES, ids=[s.id for s in scenes.SCENES])
def test_a_scene_covers_only_market_types_its_input_runs(scene):
    declared = {c[0] for c in scene.covers} & MARKET
    ran = _kinds(scene)
    assert declared <= ran, (scene.id, sorted(declared - ran), sorted(ran))
