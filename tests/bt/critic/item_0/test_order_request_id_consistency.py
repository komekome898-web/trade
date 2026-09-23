"""Critic (item 0, round 1, i0-r1-01).

`StrategyContext.place_order` returns an engine-assigned `client_order_id`
when the caller supplies none (`engine.py: CoreEngine._place_order`), but
the `OrderRequest` object stored in `EngineResult.order_requests` is the
*original*, unmodified request -- it still carries the empty
`client_order_id` the strategy passed in. The ID handed back to the
strategy and the ID recorded in the engine's own order-flow record
therefore disagree. Any item (2: order bookkeeping, 8: reproducibility /
audit trail, 13: integration reporting) that tries to correlate a fill or a
cancel against `EngineResult.order_requests` by `client_order_id` will not
find the record it is looking for, because that record's `client_order_id`
is `""`, not the ID everyone else was told to use.
"""
from __future__ import annotations

import unittest

from bot.bt.core.api import OrderRequest, StrategyContext
from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")


class _PlaceOneOrder(Strategy):
    def __init__(self) -> None:
        self.returned_id: str | None = None

    def on_event(self, event, ctx: StrategyContext) -> None:
        if self.returned_id is None:
            self.returned_id = ctx.place_order(
                OrderRequest(side="buy", order_type="market", size=1.0)
            )


class OrderRequestRecordCarriesAssignedIdTest(unittest.TestCase):
    def test_recorded_order_request_client_order_id_matches_what_the_strategy_was_told(self):
        events = [ClockEvent(received_time_ns=T0, seq=0)]
        strategy = _PlaceOneOrder()
        engine = CoreEngine(strategy=strategy, events=events)
        result = engine.run()

        self.assertIsNotNone(strategy.returned_id)
        self.assertEqual(len(result.order_requests), 1)
        # This is the actual contract other items need: the record the
        # engine kept of "an order was requested" must be findable under
        # the same ID the engine handed back as that order's handle.
        self.assertEqual(
            result.order_requests[0].client_order_id,
            strategy.returned_id,
            "EngineResult.order_requests does not carry the client_order_id "
            "that was actually assigned and returned to the strategy -- "
            "the stored OrderRequest still has the empty id the strategy "
            "passed in, not the 'core-N' id CoreEngine._place_order "
            "generated and returned.",
        )


if __name__ == "__main__":
    unittest.main()
