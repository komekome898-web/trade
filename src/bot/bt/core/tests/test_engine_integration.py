"""End-to-end: a strategy that reacts to events, places/cancels orders, and
never sees the future, driven through mixed event types in scrambled
arrival order."""
from __future__ import annotations

import unittest

from bot.bt.core.api import CancelRequest, OrderRequest, StrategyContext
from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import BarEvent, ClockEvent, EventType, TradeEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos


class _BuyOnFirstTradeThenCancel(Strategy):
    def __init__(self) -> None:
        self.placed_order_id: str | None = None
        self.order_events_seen: list[EventType] = []

    def on_event(self, event, ctx: StrategyContext) -> None:
        if isinstance(event, TradeEvent) and self.placed_order_id is None:
            self.placed_order_id = ctx.place_order(
                OrderRequest(side="buy", order_type="market", size=1.0)
            )
        if isinstance(event, BarEvent) and self.placed_order_id is not None:
            ctx.cancel_order(CancelRequest(client_order_id=self.placed_order_id))
        self.order_events_seen.append(event.EVENT_TYPE)


class EngineIntegrationTest(unittest.TestCase):
    def test_full_run_places_and_cancels_in_deterministic_order(self):
        t0 = to_nanos(1_700_000_000, "s")
        t1 = to_nanos(1_700_000_001, "s")

        events = [
            BarEvent(received_time_ns=t1, seq=0, open=1, high=1, low=1, close=1, volume=1),  # given last, sorts 2nd
            ClockEvent(received_time_ns=t0, seq=0),
            TradeEvent(received_time_ns=t0, seq=0, price=100.0, size=1.0, side="buy", trade_id="t1"),
        ]
        strategy = _BuyOnFirstTradeThenCancel()
        engine = CoreEngine(strategy=strategy, events=events)
        result = engine.run()

        self.assertEqual(result.events_processed, 3)
        # t0: TRADE (priority 4) before CLOCK (priority 9); t1: BAR alone.
        self.assertEqual(
            strategy.order_events_seen,
            [EventType.TRADE, EventType.CLOCK, EventType.BAR],
        )
        self.assertIsNotNone(strategy.placed_order_id)
        self.assertEqual(len(result.order_requests), 1)
        self.assertEqual(len(result.cancel_requests), 1)
        self.assertEqual(result.cancel_requests[0].client_order_id, strategy.placed_order_id)

    def test_deterministic_replay_produces_identical_results(self):
        t0 = to_nanos(1_700_000_000, "s")
        events = [
            TradeEvent(received_time_ns=t0, seq=0, price=100.0, size=1.0, side="buy", trade_id="t1"),
            ClockEvent(received_time_ns=t0, seq=0),
        ]

        def run_once():
            strategy = _BuyOnFirstTradeThenCancel()
            engine = CoreEngine(strategy=strategy, events=list(events))
            result = engine.run()
            return strategy.order_events_seen, len(result.order_requests)

        first = run_once()
        second = run_once()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
