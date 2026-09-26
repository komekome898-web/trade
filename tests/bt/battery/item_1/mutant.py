"""Item 1 touchstone (試金石): the new implementation with ONE defect planted.

MUTANT = "時間帯の宣言を無視する(オフセットの無い壁時計の時刻を、宣言が Asia/Tokyo でも UTC とみなす)"

It wraps the new implementation's adapter (adapters/new_impl.py) and does not
touch the new implementation's code.  After the new implementation has run a
scene, every event of a dataset whose spec declares a non-UTC time zone has its
time (t_ns / start_ns) moved by that zone's offset -- exactly what a loader that
drops the declared zone would produce (JST 09:00 read as 09:00Z = 9 hours late).
Nothing else changes.

Scenes whose answer this must break (a dataset declared Asia/Tokyo):
v1-jpx-1m, v1-all-assets-one-call, v2-naive-local-tz.
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

MUTANT = "時間帯の宣言を無視する(オフセットの無い壁時計の時刻を、宣言が Asia/Tokyo でも UTC とみなす)"

OFFSET_H = {"Asia/Tokyo": 9, "+09:00": 9}
NS = 1_000_000_000

_spec = importlib.util.spec_from_file_location("i1_mutant_base_new_impl", HERE / "adapters" / "new_impl.py")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def plant(inp: dict, obs: dict) -> dict:
    if inp.get("op") != "load":
        return obs
    for ds in inp.get("datasets", []):
        h = OFFSET_H.get(ds["spec"]["time"].get("tz", "UTC"))
        if not h:
            continue
        for rec in (obs.get("events") or {}).get(ds["name"], []) or []:
            for k in ("t_ns", "start_ns"):
                if isinstance(rec.get(k), int):
                    rec[k] += h * 3600 * NS
    return obs


class Mutant:
    name = "mutant"

    def run(self, inp: dict) -> dict:
        obs = _base.TARGET.run(copy.deepcopy(inp))
        return plant(inp, obs)


TARGET = Mutant()
