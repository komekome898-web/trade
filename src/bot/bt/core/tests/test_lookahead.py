"""V3: strategies can only see events with received_time_ns <= now, enforced
structurally by the engine, not by a convention the strategy is trusted to
follow."""
from __future__ import annotations

import unittest

from bot.bt.core.api import StrategyContext
from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent, TradeEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos


def _clock_events(n: int, start_s: int = 1_700_000_000) -> list[ClockEvent]:
    return [ClockEvent(received_time_ns=to_nanos(start_s + i, "s"), seq=0) for i in range(n)]


class _RecordingStrategy(Strategy):
    def __init__(self) -> None:
        self.observations: list[tuple[int, int]] = []  # (now_ns, len(visible))
        self.contexts_seen: list[StrategyContext] = []

    def on_event(self, event, ctx: StrategyContext) -> None:
        self.observations.append((int(ctx.now_ns), len(ctx.visible_events())))
        self.contexts_seen.append(ctx)


class LookaheadStructuralTest(unittest.TestCase):
    def test_visible_events_never_exceed_current_index(self):
        events = _clock_events(5)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=events)
        engine.run()
        # at step i (0-indexed), exactly i+1 events must be visible
        self.assertEqual([n for _, n in strategy.observations], [1, 2, 3, 4, 5])

    def test_no_visible_event_is_ever_in_the_future(self):
        events = _clock_events(5)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=events)
        engine.run()
        for ctx in strategy.contexts_seen:
            now = ctx.now_ns
            for ev in ctx.visible_events():
                self.assertLessEqual(int(ev.received_time_ns), int(now))

    def test_full_log_is_strictly_larger_than_what_early_steps_see(self):
        # Proves the restriction is real filtering, not a coincidence of a
        # short log: the engine's full sorted log has 5 events, but the
        # first step's context can only see 1.
        events = _clock_events(5)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=events)
        engine.run()
        self.assertEqual(len(engine.event_log), 5)
        first_visible_count = len(strategy.contexts_seen[0].visible_events())
        self.assertEqual(first_visible_count, 1)
        self.assertLess(first_visible_count, len(engine.event_log))

    def test_stashed_context_does_not_gain_future_visibility(self):
        # A strategy that keeps the FIRST context around and queries it
        # again after later events have been processed must still only see
        # what was visible at the time that context was built -- because the
        # underlying tuple was fixed at construction and the engine never
        # mutates or replaces it.
        events = _clock_events(5)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=events)
        engine.run()
        first_ctx = strategy.contexts_seen[0]
        self.assertEqual(len(first_ctx.visible_events()), 1)

    def test_fresh_context_object_every_event(self):
        events = _clock_events(3)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=events)
        engine.run()
        ids = {id(ctx) for ctx in strategy.contexts_seen}
        self.assertEqual(len(ids), 3)

    def test_mixed_types_respect_visibility_too(self):
        trade_future = TradeEvent(
            received_time_ns=to_nanos(1_700_000_010, "s"), seq=0, price=1, size=1, side="buy", trade_id="future"
        )
        clock_now = ClockEvent(received_time_ns=to_nanos(1_700_000_000, "s"), seq=0)
        strategy = _RecordingStrategy()
        engine = CoreEngine(strategy=strategy, events=[trade_future, clock_now])
        engine.run()
        # clock_now is processed first (earlier time); at that point the
        # later trade must not be visible.
        first_ctx = strategy.contexts_seen[0]
        self.assertEqual(len(first_ctx.visible_events()), 1)
        self.assertEqual(first_ctx.current_event.EVENT_TYPE.value, "CLOCK")


if __name__ == "__main__":
    unittest.main()
