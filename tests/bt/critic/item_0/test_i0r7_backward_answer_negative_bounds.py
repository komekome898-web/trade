"""Critic, item 0, round 7 (same cause as i0-r6-01): a slice of a BACKWARD
answer whose negative bounds name only events not delivered yet returns an
empty tuple silently.

window.py POSITION_RULE: "Negative SLICE bounds count back from the newest
and are cut at the answer's ends, as for any tuple (a cut only ever
shortens towards what the answer holds)". That holds for an answer in
delivery order. A backward answer (`ans[::-1]`, place step -1, newest
first) counts negative bounds back from the OLDEST: its position -1 lies
before `r[0]`, i.e. after the newest delivered event -- an event not
delivered yet. Negative INDICES follow the named position since round 7
(`r[-len-1]` raises `FuturePositionError`), but negative SLICE bounds are
still decided by their sign alone: `r[-len-2:-len-1]` names two positions
that are both not delivered yet and returns `()`, where the forward mirror
`ans[len:len+1]` raises `FuturePositionError`.

Fixed requirement P0-4 (REQUIREMENTS.md): code that reads a future event
must stop with an error ("素通りしたら不合格"); the scene set says an empty
or shortened result is passing through. The oracle here is the input (6
daily bars, the callback of the 4th): the named positions are mapped back
to the read's delivery order; every slice below names only positions
that are not delivered yet, so it must raise a LookAheadError.
"""
from __future__ import annotations

import pytest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.errors import LookAheadError
from bot.bt.core.events import BarEvent, EventType

D = 86_400_000_000_000
T0 = 1_700_000_000_000_000_000


def _bars():
    return [BarEvent(received_time_ns=T0 + i * D, open=100.0 + i, high=100.0 + i, low=100.0 + i,
                     close=100.0 + i, volume=1.0) for i in range(6)]


# every slice below, on r = ans[::-1] (4 delivered bars, newest first), names
# ONLY positions before r[0], i.e. after the newest delivered bar
CASES = [
    ("r[-6:-5]", slice(-6, -5)),
    ("r[-6:-4]", slice(-6, -4)),
    ("r[-5::-1]", slice(-5, None, -1)),
    ("r[-6:-5:-1]", slice(-6, -5, -1)),
]


def _run(sl):
    got = {}

    class S:
        def on_event(self, ev, ctx):
            if ev.received_time_ns != T0 + 3 * D:
                return
            ans = ctx.visible_events(EventType.BAR)
            got["forward_mirror"] = None
            try:
                ans[4:5]
            except IndexError as exc:
                got["forward_mirror"] = exc
            r = ans[::-1]
            try:
                got["returned"] = tuple(e.close for e in r[sl])
                got["error"] = None
            except IndexError as exc:
                got["error"] = exc

    CoreEngine(S(), _bars()).run()
    return got


@pytest.mark.parametrize("label,sl", CASES, ids=[c[0] for c in CASES])
def test_a_backward_slice_naming_only_undelivered_positions_stops(label, sl):
    got = _run(sl)
    assert isinstance(got["forward_mirror"], LookAheadError), "the forward mirror ans[4:5] no longer stops"
    assert isinstance(got["error"], LookAheadError), (
        f"{label} on the newest-first answer names only positions after the newest delivered bar (not "
        f"delivered yet) and returned {got.get('returned')!r} with error {got['error']!r}; the forward "
        f"mirror ans[4:5] raises {type(got['forward_mirror']).__name__}"
    )
