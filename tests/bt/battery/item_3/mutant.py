"""Item 3 touchstone (試金石): the new implementation with ONE defect planted.

MUTANT = "purge を黙って外す(ラベルの終わりを行の始まりに潰して渡すので、ラベルの重なりの除去が働かない。embargo はそのまま)"

It wraps the new implementation's adapter (adapters/new_impl.py) and does not
touch the new implementation's code.  For the requests that carry label ends
(ops purged_split, cpcv, cpcv_paths) it replaces every label end by the row's
own start time before handing the request on -- exactly what an implementation
that ignores the label horizon when purging would compute.  Nothing else
changes; the defect is deterministic, so both passes of a scene stay identical
and the touchstone differs from the new implementation in correctness only.

Scenes whose answer this must break: v2-purge-embargo (train would be rows
0-11 and 20-29 instead of 0-9 and 22-29) and v2-cpcv-split (its train set).
a2-cpcv-paths is unaffected (paths do not depend on purging).  All other scenes
see the new implementation's own result.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MUTANT = "purge を黙って外す(ラベルの終わりを行の始まりに潰して渡すので、ラベルの重なりの除去が働かない。embargo はそのまま)"
AFFECTED_OPS = ("purged_split", "cpcv", "cpcv_paths")

_spec = importlib.util.spec_from_file_location("i3_mutant_base_new_impl", HERE / "adapters" / "new_impl.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def plant(inp: dict) -> dict:
    inp = copy.deepcopy(inp)
    if inp.get("op") in AFFECTED_OPS and "label_end" in inp:
        inp["label_end"] = list(inp["rows"])
    return inp


class Mutant:
    name = "mutant"

    def run(self, inp: dict) -> dict:
        return _base.TARGET.run(plant(inp))


TARGET = Mutant()
