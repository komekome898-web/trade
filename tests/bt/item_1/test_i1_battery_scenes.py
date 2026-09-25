"""Every scene of the item-1 battery (tests/bt/battery/item_1, fixed by the
scene keeper; read, not changed) through the new implementation's public
API (i1_driver.py), judged by the battery's own judge: every scene must
give 「正解と一致」, a scene with a variant must have the variant REFUSED
(a DataError), and two runs must give the same observation digest.
"""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BATTERY = HERE.parent / "battery" / "item_1"
for p in (str(HERE), str(BATTERY)):
    if p not in sys.path:
        sys.path.insert(0, p)

import i1_driver as D  # noqa: E402
import i1_judge as J  # noqa: E402
import i1_scenes as S  # noqa: E402
import run_battery as R  # noqa: E402

from bot.bt.data import DataError  # noqa: E402


def _run(inp, base):
    inp = copy.deepcopy(inp)
    root = None
    try:
        if inp.get("files"):
            root = R.materialize(inp, base)
            inp["root"] = root
        obs = D.run(inp)
        if root and "hashes" in obs:
            pass
        return obs
    finally:
        if root:
            shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("scene", S.SCENES, ids=[s["id"] for s in S.SCENES])
def test_scene(scene, tmp_path):
    base = str(tmp_path)
    obs1 = _run(scene["input"], base)
    cls, detail = J.compare(S.expected(scene), obs1, scene)
    assert cls == "正解と一致", detail
    if "variant" in scene:
        with pytest.raises(DataError):
            _run(scene["variant"], base)
    if scene["id"] != "v7-speed":  # the speed scene's timings differ by nature; its values are judged above
        obs2 = _run(scene["input"], base)
        assert J.digest(obs1) == J.digest(obs2)


def test_all_viewpoints_are_covered():
    assert {s["viewpoint"] for s in S.SCENES} == {f"V{k}" for k in range(1, 8)}
    assert len(S.SCENES) == 35
