"""Adapter contract for the item-0 scene battery.

`run_battery.py` drives every target (当方の現状 / 新実装 / 調査結果の候補) through
the exact same scene list (`scenes.SCENES`) via this one shape. This file is
the "口だけ決める" deliverable for the new engine's adapter (delegation doc
Sec.2 item 2): the new engine itself, and its adapter body, are written by
the worker/materials-person each round against this interface -- nothing here
is allowed to depend on `src/bot/bt/core` existing yet.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenes import Scene  # noqa: E402

Status = Literal["ok", "not_supported", "error", "no_record"]
# ok           -- the target executed the scene and produced `output`.
# not_supported-- the target was actually invoked/inspected and this
#                 capability/event-type genuinely does not exist for it
#                 (a real negative, not a guess -- `detail` says how it was
#                 checked).
# error        -- the target was invoked and raised/misbehaved unexpectedly.
# no_record    -- the target could not be invoked at all for this scene this
#                 round (not installed, no bridge written yet, etc). This is
#                 the "実行の記録なし" bucket from the delegation doc.


@dataclass
class SceneResult:
    status: Status
    output: Any = None
    detail: str = ""  # what was actually done / observed; cite file:line or the command run


class Adapter(ABC):
    """One adapter instance wraps exactly one target (blinded by the runner)."""

    #: internal symbolic name (never shown to a blind judge; the runner maps
    #: it to a random single-letter label per round -- see run_battery.py)
    name: str

    @abstractmethod
    def run_scene(self, scene: Scene) -> SceneResult:
        """Execute one scene and return a SceneResult.

        Implementations MUST NOT raise for an unsupported scene -- return
        status="not_supported" instead, with `detail` explaining how the
        absence was confirmed (grep'd source, called and got an explicit
        "not implemented", introspected the public API, ...). An uncaught
        exception is recorded by the runner as status="error" so it still
        shows up in the report rather than crashing the whole run.
        """
        raise NotImplementedError
