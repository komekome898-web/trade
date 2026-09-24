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

i0-r2-07. `p5-hand-over-order` tells single-input targets to take the four
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
    sc = _scene("p5-hand-over-order")
    seen = set()
    for order in itertools.permutations(sc.input["streams"]):
        one_input = [_event(e) for name in order for e in sc.input["streams"][name]]
        got: list[str] = []

        class _Rec(Strategy):
            def on_event(self, event, ctx) -> None:
                got.append(event.EVENT_TYPE.value)

        CoreEngine(_Rec(), one_input).run()
        seen.add(tuple(got))
    # the core keeps one input's own order (i0-r1-10), so the 24 concatenations
    # give 24 orders; the scene's expected answer for this form says 1
    assert sc.expected["distinct_orders"] == len(seen), (
        f"scene expects {sc.expected['distinct_orders']} order(s) for the single-input form; "
        f"keeping one input in its own order gives {len(seen)}"
    )
