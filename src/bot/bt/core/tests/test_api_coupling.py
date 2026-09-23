"""V5: the strategy API surface is exactly event-callback + place/cancel
order, and no path from a `StrategyContext` reaches the engine object or its
internal state."""
from __future__ import annotations

import unittest

from bot.bt.core.api import CancelRequest, OrderRequest, StrategyContext
from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")

_EXPECTED_PUBLIC_SURFACE = {
    "now_ns",
    "current_event",
    "visible_events",
    "place_order",
    "cancel_order",
}


class StrategyContextSurfaceTest(unittest.TestCase):
    def _make_ctx(self) -> StrategyContext:
        ev = ClockEvent(received_time_ns=T0, seq=0)
        return StrategyContext(
            visible_events=(ev,),
            current=ev,
            place_order_cb=lambda r: "id",
            cancel_order_cb=lambda r: None,
        )

    def test_public_surface_is_exactly_five_members(self):
        ctx = self._make_ctx()
        public = {name for name in dir(ctx) if not name.startswith("_")}
        self.assertEqual(public, _EXPECTED_PUBLIC_SURFACE)
        self.assertEqual(len(public), 5)

    def test_no_public_attribute_is_the_engine_or_an_engine_internal(self):
        events = [ClockEvent(received_time_ns=T0, seq=0)]

        captured: list[StrategyContext] = []

        class _Capture(Strategy):
            def on_event(self, event, ctx: StrategyContext) -> None:
                captured.append(ctx)

        engine = CoreEngine(strategy=_Capture(), events=events)
        engine.run()
        ctx = captured[0]
        for name in _EXPECTED_PUBLIC_SURFACE:
            value = getattr(ctx, name)
            self.assertNotIsInstance(value, CoreEngine)

    def test_engine_is_never_an_attribute_of_context_even_privately_named(self):
        # The engine object itself must not appear anywhere in the context's
        # instance dict under any name -- not just under the public names
        # checked above.
        events = [ClockEvent(received_time_ns=T0, seq=0)]
        captured: list[StrategyContext] = []

        class _Capture(Strategy):
            def on_event(self, event, ctx: StrategyContext) -> None:
                captured.append(ctx)

        engine = CoreEngine(strategy=_Capture(), events=events)
        engine.run()
        ctx = captured[0]
        for value in vars(ctx).values():
            self.assertIsNot(value, engine)

    def test_visible_events_returns_a_tuple_not_a_mutable_list(self):
        ctx = self._make_ctx()
        self.assertIsInstance(ctx.visible_events(), tuple)

    def test_place_order_and_cancel_order_are_the_only_mutators(self):
        calls = {"placed": [], "cancelled": []}

        def place(req: OrderRequest) -> str:
            calls["placed"].append(req)
            return "oid-1"

        def cancel(req: CancelRequest) -> None:
            calls["cancelled"].append(req)

        ev = ClockEvent(received_time_ns=T0, seq=0)
        ctx = StrategyContext(
            visible_events=(ev,), current=ev, place_order_cb=place, cancel_order_cb=cancel
        )
        oid = ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0))
        self.assertEqual(oid, "oid-1")
        ctx.cancel_order(CancelRequest(client_order_id="oid-1"))
        self.assertEqual(len(calls["placed"]), 1)
        self.assertEqual(len(calls["cancelled"]), 1)


if __name__ == "__main__":
    unittest.main()
