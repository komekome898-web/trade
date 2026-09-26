"""Critic (item 0, round 1, i0-r1-03).

`CoreEngine.run` (engine.py) recomputes `visible = self._log[: i + 1]` on
every iteration of the main loop. Slicing a tuple copies it, so the total
work across a run of N events is 1 + 2 + ... + N = O(N^2), not O(N). This
is a real scalability defect, not a micro-optimization nit: item 0's own
committed row lists board snapshots/deltas and ticks among the event
types, item 3 (fill/queue model) is required to "walk the book" on top of
this core, and item 13 (integration) is required to run a full day of
bitFlyer top10-book data and Binance aggTrades through this exact engine.
A single trading day of book-delta/tick data easily reaches hundreds of
thousands of events; at the measured growth rate below, that is not a
"slow but usable" run, it is a run that does not finish.

This test does not assert an absolute latency bound (that would be
environment-dependent and flaky). It asserts the *shape* of the scaling:
quadrupling the event count should cost roughly 4x the time if the loop
body's cost is O(1) per event (the intended shape for an event-driven
core), not ~16x. The threshold (8x) sits strictly between the linear
prediction (~4x) and the quadratic reality measured on this machine
(~10x), so it is not a hair-trigger on ordinary timing noise while still
failing against the current implementation.

Measured on this machine (not asserted, recorded for the report):
    n=5000   -> 0.05s
    n=20000  -> 1.04s  (4x n -> ~20x time)
    n=50000  -> 6.41s  (2.5x n -> ~6.2x time)
    n=2000   -> ~0.011s
    n=8000   -> ~0.11s (4x n -> ~10x time, 3 repeats)
"""
from __future__ import annotations

import time
import unittest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos


class _NoOpStrategy(Strategy):
    def on_event(self, event, ctx) -> None:
        return None


def _run_and_time(n: int) -> float:
    events = [
        ClockEvent(received_time_ns=to_nanos(1_700_000_000 + i, "s"), seq=0)
        for i in range(n)
    ]
    t0 = time.perf_counter()
    CoreEngine(strategy=_NoOpStrategy(), events=events).run()
    return time.perf_counter() - t0


class EngineLoopIsNotQuadraticInEventCountTest(unittest.TestCase):
    def test_quadrupling_event_count_does_not_cost_roughly_sixteenx_time(self):
        small = min(_run_and_time(2000) for _ in range(3))
        large = min(_run_and_time(8000) for _ in range(3))
        ratio = large / small if small > 0 else float("inf")
        self.assertLess(
            ratio,
            8.0,
            f"run() took {ratio:.1f}x longer for 4x the events "
            f"(small={small:.4f}s, large={large:.4f}s) -- consistent with "
            "the O(n^2) cost of re-slicing self._log[:i+1] every "
            "iteration in CoreEngine.run (engine.py), not the O(n) an "
            "event-driven core needs to be usable on a real day of "
            "tick/book data (item 13's integration input).",
        )


if __name__ == "__main__":
    unittest.main()
