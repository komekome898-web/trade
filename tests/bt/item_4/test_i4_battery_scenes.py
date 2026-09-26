"""Every scene of the item-4 battery through the new engine's public API
(drive.py), judged by the battery's own judge (i4_judge.compare), twice.

A scene with a `variant` must have its variant refused (drive.Refused).
Grid scenes run every case. The observation of two runs must be the same
(i4_judge.digest). Pipeline scenes have their files written into a fresh
root per run (as the battery's runner does)."""
from __future__ import annotations

import copy
import os
import tempfile

import pytest

import i4w_drive as drive
import i4_judge as J
import i4_scenes as S


def _materialize(inp: dict) -> dict:
    inp = copy.deepcopy(inp)
    if inp.get("op") == "pipeline":
        root = tempfile.mkdtemp(prefix="i4w_scene_")
        for f in inp["files"]:
            p = os.path.join(root, f["path"])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(S.file_bytes(f))
        inp["root"] = root
        inp["runs_dir"] = tempfile.mkdtemp(prefix="i4w_runs_")
    return inp


def _observe(scene):
    if "cases" in scene:
        return [drive.run(_materialize(c)) for c in scene["cases"]]
    return drive.run(_materialize(scene["input"]))


@pytest.mark.parametrize("sid", [s["id"] for s in S.SCENES])
def test_scene_is_answered_right_and_the_same_twice(sid):
    scene = S.by_id(sid)
    a, b = _observe(scene), _observe(scene)
    cls, detail = J.compare(scene["expect"], a, scene)
    assert cls == "正解と一致", detail
    assert J.digest(a) == J.digest(b)


@pytest.mark.parametrize("sid", [s["id"] for s in S.SCENES if "variant" in s])
def test_variant_is_refused(sid):
    scene = S.by_id(sid)
    with pytest.raises(drive.Refused):
        drive.run(_materialize(scene["variant"]))


def test_every_viewpoint_with_scenes_is_driven():
    vps = {s["viewpoint"] for s in S.SCENES}
    assert vps == set(S.VIEWPOINTS) - set(S.NOT_SCENES)
