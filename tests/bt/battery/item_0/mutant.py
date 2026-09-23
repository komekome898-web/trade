"""Canary for the blind judges: wraps 新実装's adapter and injects exactly
ONE bug, without touching `src/bot/bt/core/` itself (delegation doc Sec.2
item 5: "新実装の本体は変えない").

What it breaks
---------------
Viewpoint 4, look-ahead prevention -- the single most safety-critical
property in item 0 (a silent look-ahead leak makes every downstream
backtest number meaningless without ever raising an exception). Concretely:

  * `v4-lookahead-known`: if the wrapped adapter genuinely reports the
    correct known answer (probe_index=3 -> max_visible_close=103.0,
    visible_count=4), this wrapper silently substitutes the value a
    1-bar-leaking engine would have produced instead (bar 4's close =
    104.0, visible_count=5) and still reports status="ok" -- i.e. it looks
    like a passing run to anyone who does not check the number against the
    known answer.
  * `v4-lookahead-cap`: fabricates the exact "correct" output
    (`future_index_raises: True`, matching `scene.expected`) WITHOUT
    actually performing the real probe (reading one index past the
    delivered window), citing a made-up file:line, to see whether a critic
    verifies the citation/detail instead of trusting a table cell that
    happens to already say "一致". (2026-09-23: after `scenes.py`'s rule-1
    fix, this scene now has a real `expected` and `run_battery.py` grades
    it mechanically -- a lie that produces the WRONG output is now caught
    automatically by `_grade`/`_output_matches_expected`, so the only lie
    still worth injecting here is one that produces the RIGHT-LOOKING
    output for the wrong reason. That is what this still tests.)

Every other scene is forwarded to the wrapped adapter completely unchanged
-- this is a single-bug mutant, not a fresh reimplementation.

Usage (round 1 test-of-the-test, delegation doc Sec.3 "審査員の試金石"):
    from mutant import LookaheadLeakMutant
    from adapters.new_impl_stub import NewImplAdapter
    mutant_adapter = LookaheadLeakMutant(NewImplAdapter())
    # feed `mutant_adapter` through run_battery.run_target(...) exactly like
    # any other target, then compare its v4 rows against the real new_impl's.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ITEM0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_ITEM0_DIR))
sys.path.insert(0, str(_ITEM0_DIR / "adapters"))

from adapters.protocol import Adapter, SceneResult  # noqa: E402
from scenes import Scene  # noqa: E402

_TAG = "[mutant.py: 意図的に1バーの先読み漏れへすり替え済み。破壊対象は観点4のみ]"


class LookaheadLeakMutant(Adapter):
    def __init__(self, wrapped: Adapter) -> None:
        self._wrapped = wrapped
        self.name = f"mutant({wrapped.name})"

    def run_scene(self, scene: Scene) -> SceneResult:
        result = self._wrapped.run_scene(scene)
        if scene.id == "v4-lookahead-known":
            return self._leak_known_answer(scene, result)
        if scene.id == "v4-lookahead-cap":
            return self._fake_cap_claim(scene, result)
        return result

    def _leak_known_answer(self, scene: Scene, result: SceneResult) -> SceneResult:
        if result.status != "ok":
            # Nothing genuine to corrupt (the wrapped adapter didn't produce
            # a real measurement this scene) -- forward the honest outcome
            # rather than fabricate a fake "ok" out of nothing.
            return result
        bars = scene.input["bars"]
        probe_index = scene.input["probe_index"]
        leak_index = min(probe_index + 1, len(bars) - 1)
        leaked_close = bars[leak_index]["close"]
        leaked_output = {
            "max_visible_close": leaked_close,
            "visible_count": result.output.get("visible_count", probe_index + 1) + 1,
        }
        return SceneResult(
            "ok",
            output=leaked_output,
            detail=f"{result.detail} {_TAG} 本来の既知解 {scene.expected} の代わりに "
                    f"{leaked_output} を返す(1本先のbarのcloseが漏れている)。",
        )

    def _fake_cap_claim(self, scene: Scene, result: SceneResult) -> SceneResult:
        return SceneResult(
            "ok",
            output={"future_index_raises": True},
            detail=(
                f"{_TAG} 実際には1つ先の索引を読もうと試みていない(その場面で行うはずの"
                f"`vis[len(vis)]` 呼び出しを一度もしていない)。にもかかわらず、あたかも実測した"
                f"かのように `window.py:52` で IndexError が上がったと偽って主張する"
                f"(この行番号は捏造。本来の実測: {result.status}, output={result.output})。"
                f"表のセルだけを見れば正解と一致(一致)に見えるが、detail の引用を実装のコードで"
                f"確かめずに通せば、この試金石は捕まらない。"
            ),
        )
