"""Critic (item 0, round 1, i0-r1-02).

`StrategyContext.visible_events(n=...)` implements "limited to the last n"
as `events[-n:]` (api.py). Python's slicing treats `-0` as `0`, so
`n=0` does not mean "give me zero events" -- it silently falls back to
"give me the whole slice", i.e. the full lookahead-bounded history. A
strategy (or a fill/latency model built on top of this API) that computes
a lookback count that can legitimately be zero (e.g. "no history needed
yet") gets the opposite of what it asked for: the entire visible history
instead of none of it. This is not a lookahead violation (everything
returned still satisfies received_time_ns <= now), but it is a real,
silent breach of the documented "limited to the last n" contract, and is
untested by the delivered test suite.
"""
from __future__ import annotations

import unittest

from bot.bt.core.api import StrategyContext
from bot.bt.core.events import ClockEvent
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")


class VisibleEventsZeroLimitTest(unittest.TestCase):
    def test_n_equals_zero_returns_zero_events(self):
        events = tuple(
            ClockEvent(received_time_ns=to_nanos(1_700_000_000 + i, "s"), seq=i)
            for i in range(5)
        )
        ctx = StrategyContext(
            visible_events=events,
            current=events[-1],
            place_order_cb=lambda r: "id",
            cancel_order_cb=lambda r: None,
        )
        got = ctx.visible_events(n=0)
        self.assertEqual(
            len(got),
            0,
            f"visible_events(n=0) returned {len(got)} events (expected 0) -- "
            "'events[-n:]' with n=0 degenerates to 'events[0:]' (the whole "
            "slice) because Python treats -0 as 0.",
        )


if __name__ == "__main__":
    unittest.main()
