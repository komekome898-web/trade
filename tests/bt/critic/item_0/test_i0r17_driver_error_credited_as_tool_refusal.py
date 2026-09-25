"""Critic, item 0, round 17 (i0-r17-03, scene set; claim family 15 of
ROOTCAUSE_r17-1.md, whose hand-written part (b) "driver のコードが道具の断りを
印したかは批評家が読む" this critic read).

The barter driver (survey_results/attempts/61.log 373-382, round r16-1)
prints the key `de_error` both for the tool's own `Err` (line 381) and for
its OWN error, an unknown deserializer name (line 377). The adapter
(opponents/barter_adapter.py `_de`, round r17-1) carries every `de_error` as
`common.CompiledRefusal`, and run_battery.py `refusal_problem` credits a
CompiledRefusal to the entry the adapter NAMES (`reader`) -- nothing ties the
name the adapter gives to the deserializer the driver was asked to call. So
a call the tool never received is graded as the tool refusing the scene's
input: "正解と一致" in a NO_INT scene.

Grid: the deserializer name the call passes {the entry's own name, a name
the tool does not have} x the NO_INT ms-text scene, with the entry's
`reader` the tool's real deserializer. Oracle: only a call the tool received
can be credited (refusal_problem not None and correctness not 正解と一致 for
the unknown name). Runs the real driver binary of the configured target
(skipped when its venv is not on this machine).

Not in the grid: what the driver is handed for a float input of a text
deserializer (the adapter writes its repr, while the refusal record says the
float itself was handed -- unit_time's rule "nothing converted"); the table
is unchanged today (no barter NO_INT cell is a credited refusal:
survey_results/opp_barter.tsv).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

B = Path(__file__).resolve().parents[2] / "battery" / "item_0"
for p in (B, B / "adapters", B / "opponents"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

EXE = Path("/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_0/c61/bin/c61_driver")


@pytest.mark.skipif(not EXE.exists(), reason="the configured target's driver binary is not on this machine")
@pytest.mark.parametrize("called", ["de_str_f64_epoch_ms_as_datetime_utc", "no_such_deserializer"])
def test_only_a_call_the_tool_received_is_credited_as_its_refusal(called, monkeypatch):
    import common as C
    import run_battery as R
    import scenes
    import barter_adapter as BA

    monkeypatch.setattr(BA, "EXE", str(EXE))
    sc = next(s for s in scenes.SCENES if s.id == "p2-ms-text-subns")
    name = "rust:barter_integration::serde::de::de_str_f64_epoch_ms_as_datetime_utc"
    entries = [{"unit": "ms", "forms": ("str",), "how": "barter ms text", "reader": C.compiled(name),
                "call": lambda v: BA.BarterAdapter._de(called, v)}]
    res = C.unit_time(sc, entries)
    grade = R.correctness(res, sc.expected, sc, "opp_barter")
    if called == "no_such_deserializer":
        assert grade != "正解と一致", (res.detail, R.refusal_problem(res, sc, "opp_barter"))
    else:
        assert res.status == "ok" and grade == "不一致", (res.status, res.detail, grade)
