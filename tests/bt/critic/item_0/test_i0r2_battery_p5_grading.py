"""Critic, item 0, round 2: the P0-5 scenes of the scene set (場面係の持ち物).

i0-r2-06 (repeat of i0-r1-15). REQUIREMENTS.md line 21 fixes P0-5 as
"同時刻に複数型の事象を仕込んだ入力を作り、規則どおりの順で処理されるか(値)、2 回
実行して一致するか(再現)". `p5-same-time-twice` expects only
`{"same_order_in_two_runs": True}` and the grader ignores every other key of
the output (run_battery.py `_matches`: "extra keys in the output are
ignored"). A target that delivers ONE of the four same-time events and drops
the other three silently is graded 正解と一致 -- it happened in round 2: the
survey target whose adapter notes "足・資金調達・清算は未定義の番号" output
`{"orders": [[["trade", ...]], [["trade", ...]]], "same_order_in_two_runs":
true}` and was graded 正解と一致 (round_2/materials/runs/opp_hftbacktest.tsv).
Rule 1 of the scene set: a result counts only if the result a working
capability produces is there.

i0-r2-07 (test rewritten in round 4 and again in round 5; see the test). `p5-hand-over-order` tells single-input targets to take the four
streams "その回の順で連結して" and expects ONE order for all 24
concatenations. For a one-input target the concatenation IS that input's
own order, which `p5-same-stream-order` (and the core's rule since round 2,
i0-r1-10) says must be kept: the core itself yields 24 orders for the 24
concatenations (tests/bt/item_0/test_bt0_scene_set.py asserts
`len(by_concat) == 24`). The expected value rewards a one-input target for
re-sorting its own input by type, and marks one that keeps it as 不一致.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_0"
sys.path.insert(0, str(BATTERY))
sys.path.insert(0, str(BATTERY / "adapters"))

import run_battery  # noqa: E402
import scenes  # noqa: E402
from adapters.protocol import SceneResult  # noqa: E402

from bot.bt.core import (  # noqa: E402
    BarEvent,
    CoreEngine,
    FundingEvent,
    LiquidationEvent,
    Strategy,
    TradeEvent,
)


def _scene(scene_id: str):
    return next(s for s in scenes.SCENES if s.id == scene_id)


def test_dropping_three_of_four_same_time_events_is_not_graded_as_correct():
    sc = _scene("p5-same-time-twice")
    t = scenes.T0 + scenes.DAY
    dropped = SceneResult("ok", {"same_order_in_two_runs": True,
                                 "orders": [[["trade", t]], [["trade", t]]]})
    assert run_battery.correctness(dropped, sc.expected) != "正解と一致", (
        "a run that delivered 1 of the 4 same-time events is graded 正解と一致"
    )


def _event(d: dict):
    ts = d["ts_ns"]
    if d["kind"] == "trade":
        return TradeEvent(received_time_ns=ts, price=d["price"], size=d["qty"], side=d["side"])
    if d["kind"] == "bar":
        return BarEvent(received_time_ns=ts, open=d["open"], high=d["high"], low=d["low"],
                        close=d["close"], volume=d["volume"])
    if d["kind"] == "funding":
        return FundingEvent(received_time_ns=ts, rate=d["rate"])
    return LiquidationEvent(received_time_ns=ts, price=d["price"], size=d["qty"], side=d["side"])


def test_single_input_form_of_hand_over_order_agrees_with_keeping_one_input_in_order():
    # Rewritten in round 5 (critic, scene-set rule 8). Since the scene
    # keeper's round r5-1 (critic i0-r4-05) the rule a target is graded by is
    # fixed on the scene-set side (stated_rules.py) and looked up by target
    # name; an adapter no longer reports `stated_rule` / `predicted`. The
    # round-4 version put them into the output and graded without a target
    # name, so it failed on the retired protocol -- an error of this test, as
    # the scene keeper reported (ROOTCAUSE_r5-1.md). The property is
    # unchanged: a one-input target whose fixed rule keeps the input's own
    # order (p5-same-stream-order; here the scene set's single_input rule of
    # opp_hftbacktest, recipe stable_by_time) and that keeps it must be graded
    # 正解と一致, and a one-input target that re-sorts the concatenation by a
    # fixed type order must not be.
    import stated_rules  # noqa: E402  (scene-set side, on sys.path above)

    single = [t for t, r in stated_rules.STATED_RULES.items() if r.form == "single_input"]
    assert single, "the scene set fixes no single_input rule: the single-input form cannot be graded at all"
    target = single[0]
    assert stated_rules.STATED_RULES[target].recipe == "stable_by_time"
    # Round 7 (critic, scene-set rule 8): since the scene keeper's round
    # r7-1 (critic i0-r6-02) a P0-5 scene takes its event types from the
    # target's own types (scenes.for_target_types); the scene as listed is
    # the one for a target with all six types, whose first four include the
    # two book types this test's `_event` does not build (KeyError 'price'
    # -- an error of this test, as the scene keeper reported in
    # ROOTCAUSE_r7-1.md). The property is unchanged; the scene is built here
    # for a target with the four types `_event` builds.
    sc = scenes.for_target_types(_scene("p5-hand-over-order"), ["trade", "bar", "funding", "liquidation"])
    assert sc is not None and len(sc.input["hand_over_orders"]) == 24
    runs, seen = [], set()
    for order in sc.input["hand_over_orders"]:
        one_input = [_event(e) for name in order for e in sc.input["streams"][name]]
        got: list = []

        class _Rec(Strategy):
            def on_event(self, event, ctx) -> None:
                got.append([str(event.EVENT_TYPE.value).lower(), int(event.exchange_time_ns)])

        CoreEngine(_Rec(), one_input).run()
        runs.append({"hand_over": list(order), "order": got})
        seen.add(repr(got))
    assert len(seen) == 24  # the core keeps one input's own order
    keeps = SceneResult("ok", {"form": "single_input", "runs": runs})
    assert run_battery.correctness(keeps, sc.expected, sc, target) == "正解と一致", (
        f"a one-input target keeping its input's order is graded "
        f"{run_battery.correctness(keeps, sc.expected, sc, target)}: "
        f"{ {k: v for k, v in run_battery.graded_output(keeps, sc, target).items() if k != 'raw'} }"
    )
    # the same target re-sorting the concatenation by one fixed type order must not pass
    rank = ["liquidation", "funding", "trade", "bar"]
    resorted = [dict(r, order=sorted(r["order"], key=lambda kt: rank.index(kt[0]))) for r in runs]
    wrong = SceneResult("ok", {"form": "single_input", "runs": resorted})
    assert run_battery.correctness(wrong, sc.expected, sc, target) != "正解と一致"
