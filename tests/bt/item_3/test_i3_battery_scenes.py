"""Every scene of the item-3 battery (tests/bt/battery/item_3, fixed by the
scene keeper; read, not changed) through the new implementation's public
API (i3_driver.py), judged by the battery's own judge (i3_judge.compare /
variant_outcome): every scene must give 「正解と一致」 (a scene with a variant
is judged on its variant, as the battery's runner does), and two passes must
give the same digest of the stable view (the battery's reproducibility cell).
"""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BATTERY = HERE.parent / "battery" / "item_3"
for p in (str(HERE), str(BATTERY)):
    if p not in sys.path:
        sys.path.insert(0, p)

import i3_driver as D  # noqa: E402
import i3_judge as J  # noqa: E402
import i3_scenes as S  # noqa: E402
import run_battery as R  # noqa: E402


class _Target:
    name = "new_impl(driver)"

    def run(self, inp):
        return D.run(inp)


def _refusal_types():
    from bot.bt.repro import ReproError
    from bot.bt.report import ReportError
    from bot.bt.validation import ValidationError
    return (ValidationError, ReproError, ReportError)


class _RefusingTarget(_Target):
    """The API's own refusals are the target's refusals (i3_protocol.Refused)."""

    def run(self, inp):
        from i3_protocol import Refused
        try:
            return D.run(inp)
        except _refusal_types() as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from None


@pytest.mark.parametrize("scene", S.SCENES, ids=[s["id"] for s in S.SCENES])
def test_scene(scene, tmp_path, monkeypatch):
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    base = str(tmp_path)
    t = _RefusingTarget()
    cls1, detail1, obs1 = R.classify(scene, t, base)
    assert cls1 == "正解と一致", detail1
    cls2, detail2, obs2 = R.classify(copy.deepcopy(scene), t, base)
    assert cls2 == cls1
    assert J.digest({"class": cls1, "obs": obs1}) == J.digest({"class": cls2, "obs": obs2})


def test_every_viewpoint_is_driven():
    assert {s["viewpoint"] for s in S.SCENES} == set(S.VIEWPOINTS)
