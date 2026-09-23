"""Self-checks of the item-0 scene set (scene keeper's tests, rule 7).

They check the battery itself, not any engine: the definitions document is
in sync with scenes.py, every viewpoint has a value scene, the runner grades
by the expected result, the canary changes exactly the stated behaviour of
the new core, and the candidate pool is reproducible from its script.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "adapters"))

import gen_definitions  # noqa: E402
import run_battery  # noqa: E402
import scenes  # noqa: E402
from adapters.protocol import SceneResult  # noqa: E402


def test_definitions_in_sync_with_scenes():
    assert (HERE / "DEFINITIONS.md").read_text(encoding="utf-8") == gen_definitions.render()


def test_every_viewpoint_has_a_value_scene_and_every_scene_an_expected():
    for vp in scenes.VIEWPOINTS:
        assert any(s.viewpoint == vp and s.kind == "value" for s in scenes.SCENES)
    for s in scenes.SCENES:
        assert s.expected is not None and s.derivation and s.measures


def test_grading_uses_expected_not_the_adapters_word():
    exp = {"a": 1}
    assert run_battery.correctness(SceneResult("ok", {"a": 1, "extra": 2}), exp) == "正解と一致"
    assert run_battery.correctness(SceneResult("ok", {"a": 2}), exp) == "不一致"
    assert run_battery.correctness(SceneResult("ok", None), exp) == "不一致"
    assert run_battery.correctness(SceneResult("not_supported"), exp) == "対応なし"
    assert run_battery.correctness(SceneResult("error"), exp) == "結果なし"


def test_current_impl_runs_every_scene_twice_identically():
    rows = run_battery.run_target("current_impl")
    assert len(rows) == len(scenes.SCENES)
    assert all(r["reproducibility"] == "2 回の実行で同じ" for r in rows)
    assert all(r["status_1"] != "error" for r in rows), [r["detail_1"] for r in rows if r["status_1"] == "error"]


def test_mutant_core_delivers_early_and_nothing_else():
    core = pytest.importorskip("bot.bt.core")
    import mutant

    def delivered(ns):
        seen = []

        class S(ns.Strategy):
            def on_event(self, event, ctx):
                seen.append((type(event).__name__, int(ctx.now_ns)))

        evs = [ns.TradeEvent(exchange_time_ns=10, received_time_ns=30, price=1.0, size=1.0, side="buy"),
               ns.TradeEvent(exchange_time_ns=20, received_time_ns=20, price=1.0, size=1.0, side="buy")]
        ns.CoreEngine(S(), evs).run()
        return seen

    real = delivered(core)
    mut = delivered(mutant.mutant_core())
    assert real == [("TradeEvent", 20), ("TradeEvent", 30)]
    assert mut == [("TradeEvent", 10), ("TradeEvent", 20)]


def test_pool_reproducible(tmp_path):
    out = tmp_path / "pool.tsv"
    subprocess.run([sys.executable, str(HERE / "gen_pool.py"), "--out", str(out)], check=True, capture_output=True)
    assert out.read_text(encoding="utf-8") == (HERE / "pool.tsv").read_text(encoding="utf-8")
