"""Critic, item 0, round 6 (i0-r6-01, same cause as i0-r5-05).

The round-6 fix gives a history answer ONE fact, `next_is_undelivered`: is
the position right after its last event an event not delivered yet? The
error for naming ANY position past the answer is then chosen from that one
fact: `FuturePositionError` (a `LookAheadError`) or `OutsideAnswerError`
(not a `LookAheadError`, whose text says "the events after it were
delivered but are outside this answer").

The fact is about the NEXT position only. An answer that ends in the
delivered past (cut by `until_ns`, or a forward slice with a step) still has,
further out, positions that name events NOT delivered yet. Naming them is a
read of the future, and it raises `OutsideAnswerError`, which is not a
`LookAheadError` and says those events "were delivered".

The worker's own rule (round_6/ROOTCAUSE.md B-6): "名指した位置に「届いた事象」
があれば過去" -- the kind is decided by the NAMED position. These tests hold
that rule: the named position is mapped back to the full delivered list of
what the read reads, and the error must be a `LookAheadError` exactly when
that position is not delivered yet.
"""
from __future__ import annotations

import pytest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.errors import LookAheadError
from bot.bt.core.events import BarEvent, EventType

D = 86_400_000_000_000
T0 = 1_700_000_000_000_000_000
N_BARS, AT_BAR = 12, 9  # the callback of the 10th bar: 10 delivered, 2 not yet


def _bars():
    return [BarEvent(received_time_ns=T0 + i * D, open=100.0 + i, high=100.0 + i, low=100.0 + i,
                     close=100.0 + i, volume=1.0) for i in range(N_BARS)]


# (label, how the answer is read, slice applied to it or None, position named)
CASES = [
    ("until day 6 [7] (reads[7], delivered)", {"until_days": 6}, None, 7),
    ("until day 6 [12] (reads[12], NOT delivered)", {"until_days": 6}, None, 12),
    ("until day 6 [10] (reads[10], NOT delivered)", {"until_days": 6}, None, 10),
    ("all[0:6:3] [2] (reads[6], delivered)", {}, slice(0, 6, 3), 2),
    ("all[0:6:3] [4] (reads[12], NOT delivered)", {}, slice(0, 6, 3), 4),
    ("all[1:8:2] [5] (reads[11], NOT delivered)", {}, slice(1, 8, 2), 5),
]


def _run_case(read, sl, p):
    got = {}

    class S:
        def on_event(self, ev, ctx):
            if ev.received_time_ns != T0 + AT_BAR * D:
                return
            reads = ctx.visible_events(EventType.BAR)
            kw = {}
            if "until_days" in read:
                kw["until_ns"] = T0 + read["until_days"] * D
            ans = ctx.visible_events(EventType.BAR, **kw)
            lo = [e.seq for e in reads].index(ans[0].seq)
            a = ans
            start, step = 0, 1
            if sl is not None:
                a = ans[sl]
                start, _, step = sl.indices(len(ans))
            orig = lo + start + p * step
            got["delivered"] = 0 <= orig < len(reads)
            got["orig"] = orig
            try:
                a[p]
                got["error"] = None
            except IndexError as exc:
                got["error"] = exc

    CoreEngine(S(), _bars()).run()
    return got


@pytest.mark.parametrize("label,read,sl,p", CASES, ids=[c[0] for c in CASES])
def test_error_kind_follows_the_named_position(label, read, sl, p):
    got = _run_case(read, sl, p)
    err = got["error"]
    assert err is not None, f"{label}: a value came back for a position past the answer"
    if got["delivered"]:
        assert not isinstance(err, LookAheadError), (
            f"{label}: reads[{got['orig']}] is delivered, but the error is a LookAheadError: {err!r}"
        )
    else:
        assert isinstance(err, LookAheadError), (
            f"{label}: reads[{got['orig']}] is NOT delivered yet (a read of the future), but the error is "
            f"{type(err).__name__}, not a LookAheadError, and says: {str(err)[-140:]!r}"
        )
