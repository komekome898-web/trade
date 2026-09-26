"""Item 4 touchstone (試金石): the new implementation with ONE defect planted.

MUTANT = "maker の指値の寿命を 1 本長く読む(maker_timeout_bars を 1 足した値で渡し、時間切れの取消が 1 本遅れる)"

It wraps the new implementation's adapter (adapters/new_impl.py) and does not
touch the new implementation's code.  Before the new implementation runs an
op "bars" input, the bar-model option `maker_timeout_bars` is raised by one --
exactly what an engine that counts a resting order's life from the bar AFTER
the placing bar (an off-by-one in the timeout) would do.  Nothing else changes.

Scenes whose answer this must break (a resting limit that should be cancelled
at its timeout, followed by a bar that trades through it):
i4-16-missed (bar 4 low 98.8 < 101 fills the order that should have been
cancelled at bar 3), i4-3-e2e-maker and i4-1-ref-maker (bar 15 low 103 < 104
fills the order that should have been cancelled at bar 14).
All other scenes see the new implementation's own result.  The defect is
deterministic, so the two runs of a scene stay identical: the touchstone
differs from the new implementation in correctness only.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MUTANT = "maker の指値の寿命を 1 本長く読む(maker_timeout_bars を 1 足した値で渡し、時間切れの取消が 1 本遅れる)"

_spec = importlib.util.spec_from_file_location("i4_mutant_base_new_impl", HERE / "adapters" / "new_impl.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def plant(inp: dict) -> dict:
    """The one defect: a bars input's maker_timeout_bars + 1."""
    inp = copy.deepcopy(inp)
    if inp.get("op") == "bars" and isinstance(inp.get("config"), dict):
        inp["config"]["maker_timeout_bars"] = int(inp["config"]["maker_timeout_bars"]) + 1
    return inp


class Mutant:
    name = "mutant"

    def __init__(self, base=None):
        self._base = base or _base.TARGET

    def run(self, inp: dict) -> dict:
        return self._base.run(plant(inp))


TARGET = Mutant()
