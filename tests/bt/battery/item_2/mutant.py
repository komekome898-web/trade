"""Item 2 touchstone (試金石): the new implementation with ONE defect planted.

MUTANT = "taker の約定に maker の率で手数料を掛ける"

It wraps the new implementation's adapter (adapters/new_impl.py) and does not
touch the new implementation's code.  After the new implementation has run a
scene, every fill that took liquidity -- `liq == "taker"`, or, when the engine
reports no `liq`, a fill of a market order -- has its fee replaced by
`maker_rate * px * qty` (the scene's own maker rate).  Nothing else changes.

Scenes whose answer this must break (a taker fill under maker_rate != taker_rate):
c2-10-taker, c2-10-no-default, c2-10-source (their control run), c2-11-legs.
All other scenes see the new implementation's own result.  The defect is
deterministic, so the two runs of a scene stay identical: the touchstone
differs from the new implementation in correctness only.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MUTANT = "taker の約定に maker の率で手数料を掛ける"

_spec = importlib.util.spec_from_file_location("i2_mutant_base_new_impl", HERE / "adapters" / "new_impl.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def plant(inp: dict, obs: dict) -> dict:
    maker = (inp.get("costs") or {}).get("maker_rate")
    if maker is None:
        return obs
    types = {a["ref"]: a["type"] for a in inp["actions"] if a.get("op") == "place"}
    for side in [obs] + list((obs.get("range") or {}).values()):
        for f in side.get("fills", []):
            taker = f.get("liq") == "taker" or (f.get("liq") is None and types.get(f.get("ref")) == "market")
            if taker:
                f["fee"] = maker * f["px"] * f["qty"]
    return obs


class Mutant:
    name = "mutant"

    def run(self, inp: dict) -> dict:
        import copy
        obs = _base.TARGET.run(copy.deepcopy(inp))
        return plant(inp, obs)


TARGET = Mutant()
