"""Every scene of the item 2 battery (tests/bt/battery/item_2, read-only here)
through the new implementation's public API (i2_driver.py), judged by the
battery's own judge: the answer must be "正解と一致", a variant must be refused
for the reason it is built to be refused, and two runs must give the same
observation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i2_driver as D  # noqa: E402

import i2_judge as J  # noqa: E402  (battery dir put on sys.path by scene_driver)
import i2_scenes as S  # noqa: E402
from i2_protocol import Refused  # noqa: E402

REPO = HERE.parents[2]

# the refusal each variant is built for (the scene's own "変形" text) -> the
# error the new implementation must name
VARIANT_REASON = {
    "c2-8-both-required": "a range needs both sides",
    "c2-10-no-default": "maker_rate",
    "c2-10-source": "'source'",
    "c2-12-jpx-wait": "DataUnavailableError",
}


def test_scene_count_is_the_fixed_battery():
    assert len(S.SCENES) == 66
    assert {s["id"] for s in S.SCENES if "variant" in s} == set(VARIANT_REASON)


@pytest.mark.parametrize("scene", S.SCENES, ids=[s["id"] for s in S.SCENES])
def test_scene_matches_answer(scene):
    obs = D.run_scene(scene["input"])
    cls, detail = J.compare(S.expected(scene), obs, scene["input"])
    assert cls == "正解と一致", detail
    if "variant" in scene:
        with pytest.raises(Refused) as ei:
            D.run_scene(scene["variant"])
        assert VARIANT_REASON[scene["id"]] in str(ei.value)


@pytest.mark.parametrize("scene", S.SCENES, ids=[s["id"] for s in S.SCENES])
def test_scene_same_observation_twice_in_process(scene):
    a = D.run_scene(scene["input"])
    b = D.run_scene(scene["input"])
    assert J.canon(a) == J.canon(b)


def test_scenes_same_observation_across_processes():
    """The battery runs each pass in a fresh process: the digests of two
    separate interpreters must agree for every scene (hash seeds differ)."""
    code = (
        "import sys,json; sys.path.insert(0,%r); import i2_driver as D; import i2_scenes as S, i2_judge as J;"
        "print(json.dumps({s['id']: J.digest(D.run_scene(s['input'])) for s in S.SCENES}))" % str(HERE)
    )
    outs = []
    for seed in ("1", "2"):
        env = {"PYTHONPATH": str(REPO / "src"), "PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}
        r = subprocess.run([sys.executable, "-c", code], env=env, cwd=str(REPO), capture_output=True, text=True,
                           timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        outs.append(json.loads(r.stdout.strip().splitlines()[-1]))
    assert outs[0] == outs[1]
    assert len(outs[0]) == 66
