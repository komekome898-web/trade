"""The one shape every target is driven through (item-0 battery).

Targets: the new implementation, our current engine, each runnable survey
tool, each reproduction of an unrunnable survey candidate, and the canary
(mutant). `run_battery.py` calls `Adapter.run_scene(scene)` for every scene
in `scenes.SCENES`, twice, and grades `SceneResult.output` against
`scene.expected` itself. An adapter never grades.

Rules for adapter authors (they are what the critic checks):
  * Drive the target only through its public API and its public plug-in
    points. Do not assign attributes on the target's modules or classes
    (no monkeypatching) and do not edit its files: a scene that needs that
    is "not_supported" for the target.
  * Hand events over in the order and grouping the scene gives. Never sort,
    merge or drop them in the adapter (that is what is measured).
  * "observed" values are recorded by the strategy inside its callbacks.
  * `not_supported` needs a real attempt: `detail` says what was called and
    the error / refusal it gave (rule 6: a declaration or a missing name is
    not evidence). A target that silently does something else returns "ok"
    with what it did and is graded "不一致".
  * `error` is for an unexpected exception while running the scene.
  * There is no status for "not run this round" (rule 4): every adapter
    implements every scene id.
  * Do not switch off a survey tool's own protective default (risk limits,
    cash checks, look-ahead guards) for convenience: the survey side must be
    at least as strong as the tool is out of the box. A non-default setting
    is used only when the scene states it (e.g. the scene's account) or when
    the adapter runs BOTH the default and the setting and reports both
    (e.g. backtrader's `preload`); the detail says which one the output is.
    (Round r4-1, critic i0-r2-04 / i0-r3-05: one adapter had turned a
    tool's risk limits off for every scene; `test_battery_item0.py` now
    looks for that.)
  * For a scene with `graded_from` (scenes.py) report the raw observations
    the scene names (each read and its exception / value; the delivered
    order and the input form) and nothing graded: the runner computes the
    graded values. The P0-5 same-time rule of a target and the order it
    gives are NOT reported by the adapter: the scene keeper fixes them in
    `stated_rules.py` before any run and the runner applies them to the
    scene's own input (round r5-1, critic i0-r4-05). An adapter output with
    `stated_rule` or `predicted` fails `test_battery_item0.py`.

The new implementation's adapter (written each round by the materials
person, not by the scene keeper) lives at `adapters/new_impl.py` and must
expose

    def make_adapter(core) -> Adapter

where `core` is a module-like object exposing the public names of
`bot.bt.core`. The adapter must reach the engine ONLY through `core.<name>`
(no `import bot.bt.core...` inside the adapter): the canary (`mutant.py`)
passes a wrapped `core` with one defect, and the canary check in
`mutant.py --check` fails if the adapter bypasses it.
"""
from __future__ import annotations

import sys
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenes import SCENES, Scene  # noqa: E402

Status = Literal["ok", "not_supported", "error"]


@dataclass
class SceneResult:
    status: Status
    output: Any = None
    detail: str = ""


def method_name(scene_id: str) -> str:
    return "scene_" + scene_id.replace("-", "_")


class Adapter(ABC):
    """One adapter wraps one target. Subclasses define one method per scene:
    `scene_<id with - replaced by _>(self, scene) -> SceneResult`."""

    name: str = "?"

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        if getattr(cls, "_abstract", False):
            return
        missing = [method_name(s.id) for s in SCENES if not hasattr(cls, method_name(s.id))]
        if missing:
            raise TypeError(f"{cls.__name__} does not implement scenes: {missing}")

    def run_scene(self, scene: Scene) -> SceneResult:
        try:
            res = getattr(self, method_name(scene.id))(scene)
        except Exception as exc:  # noqa: BLE001 - recorded, graded as a failed check
            return SceneResult("error", detail=f"{type(exc).__name__}: {exc}")
        if not isinstance(res, SceneResult):
            return SceneResult("error", detail=f"adapter returned {type(res).__name__}, not SceneResult")
        return res


class _Abstract(Adapter):
    _abstract = True


def not_supported(what_was_tried: str, output: Any = None) -> SceneResult:
    return SceneResult("not_supported", output=output, detail=what_was_tried)


def ok(output: Any, detail: str = "") -> SceneResult:
    return SceneResult("ok", output=output, detail=detail)
