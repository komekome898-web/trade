"""Critic, item 0, round 4 (i0-r4-01): a slice that starts at the next
position after the newest delivered event returns an empty tuple silently.

Scene p4-future-read-attempt (tests/bt/battery/item_0/scenes.py) fixes the
answer from REQUIREMENTS.md P0-4 ("実行時エラーか型エラーで止まるか(素通りし
たら不合格)"): every read that names the 5th bar -- by time or by POSITION
("今の最新の次の位置を、添字・先の参照・次を覗く手段で読む") -- must stop with
an exception; "空の結果・切り詰めた結果 … は素通りで、正解ではない".

At the 4th bar the newest delivered position is 3; position 4 is the 5th
bar, not yet delivered. The core's own rule (window.py `DeliveredEvents`,
round_4/ROOTCAUSE.md D: "位置 0 .. len-1 は届いた事象、len 以後は未来") makes
`[4]` and `[4:5]` raise FuturePositionError, but `[4:]`, `[4::]` and
`[4::2]` -- slices that START at position 4 -- return `()` (the check is
`start > n`, not `start >= n`, for a forward slice). The worker's own test
(tests/bt/item_0/test_bt0_future_position.py, "from_end") asserts that
empty answer, and its seeded oracle copies the implementation's formula,
so it cannot catch this.

The second test runs the scene itself through the battery runner with the
new-implementation adapter (the materials person's round-4 adapter tries
`ctx.visible_events()[4:]`): the scene must grade 正解と一致.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bot.bt.core import BarEvent, CoreEngine, EventType, FuturePositionError, Strategy

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_0"
T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
BAR = EventType.BAR


def _at_fourth_bar(read):
    out = {}

    class _S(Strategy):
        def on_event(self, event, ctx) -> None:
            if event.close == 103.0:
                try:
                    out["returned"] = read(ctx)
                except FuturePositionError as exc:
                    out["raised"] = exc

    bars = [BarEvent(received_time_ns=T0 + i * SEC, open=100.0 + i, high=100.0 + i, low=100.0 + i,
                     close=100.0 + i, volume=1.0) for i in range(6)]
    CoreEngine(_S(), bars).run()
    return out


@pytest.mark.parametrize("name, read", [
    ("visible_events(BAR)[4:]", lambda ctx: ctx.visible_events(BAR)[4:]),
    ("visible_events()[4:]", lambda ctx: ctx.visible_events()[4:]),
    ("visible_events(BAR)[4::]", lambda ctx: ctx.visible_events(BAR)[4::]),
    ("visible_events(BAR)[4::2]", lambda ctx: ctx.visible_events(BAR)[4::2]),
    ("visible_events(BAR)[len(bars):]", lambda ctx: ctx.visible_events(BAR)[len(ctx.visible_events(BAR)):]),
])
def test_slice_starting_at_the_next_position_is_refused(name, read):
    got = _at_fourth_bar(read)
    assert "raised" in got, (
        f"{name} at the 4th bar names position 4 (the 5th bar, not delivered) and returned "
        f"{got.get('returned')!r} silently"
    )


def test_scene_p4_future_read_attempt_grades_correct_for_the_new_implementation():
    sys.path.insert(0, str(BATTERY))
    sys.path.insert(0, str(BATTERY / "adapters"))
    import run_battery  # noqa: E402
    import scenes  # noqa: E402

    sc = next(s for s in scenes.SCENES if s.id == "p4-future-read-attempt")
    res = run_battery.load_adapter("new_impl").run_scene(sc)
    graded = run_battery.graded_output(res, sc)
    silent = [a for a in (res.output or {}).get("attempts", [])
              if a.get("form") in ("time", "position") and not a.get("raised")]
    assert run_battery.correctness(res, sc.expected, sc) == "正解と一致", (
        f"scene p4-future-read-attempt: {graded.get('every_attempt_stopped_by_error')=}; "
        f"named reads that did not stop: {silent}"
    )
