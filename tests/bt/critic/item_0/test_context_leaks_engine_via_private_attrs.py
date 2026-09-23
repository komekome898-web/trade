"""Critic (item 0, round 2, i0-r2-01).

api.py's module docstring and `test_api_coupling.py` claim that a
`StrategyContext` gives a strategy no path to the `CoreEngine` object or its
internal state, other than the five public methods. The claim rests on
Python's leading-double-underscore "name mangling"
(`self.__place_order_cb` -> `self._StrategyContext__place_order_cb`), and the
existing test only checks `dir(ctx)` names that do NOT start with `_`
(`test_public_surface_is_exactly_five_members`) and that no *attribute value*
`is` the engine object itself (`test_engine_is_never_an_attribute_of_context_
even_privately_named`).

Name mangling is not access control -- it is a compile-time rename, and the
mangled name is a completely ordinary, readable instance attribute. This
test shows two independent ways a strategy reaches engine-internal state
through it, both currently unguarded:

1. `ctx._StrategyContext__place_order_cb` is `CoreEngine._place_order`, a
   BOUND method. Its `.__self__` IS the `CoreEngine` instance -- not the
   engine object as an attribute *value* (which the existing test checks),
   but reachable one hop away, which the existing test does not check.
   Through it, a strategy reaches `engine._log` (the full run log),
   `engine._account`, `engine._order_requests`, etc: everything V5 is
   supposed to make unreachable.
2. `ctx._StrategyContext__visible_events` is the raw `EventWindow` object
   engine.py builds. Its `_log` attribute (single underscore, not mangled at
   all) is the ENTIRE, untruncated run log -- including events strictly
   after `now_ns`. `EventWindow`'s public surface (`len`, `__getitem__`,
   `__iter__`) correctly bounds access to `[:end]`, but the raw `_log`
   attribute bypasses that bound entirely. This is a structural lookahead
   bypass (V3), not just an API-coupling one (V5): a strategy that reaches
   `ctx._StrategyContext__visible_events._log` sees the future.
"""
from __future__ import annotations

import unittest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")


def _clock_events(n: int) -> list[ClockEvent]:
    return [ClockEvent(received_time_ns=to_nanos(1_700_000_000 + i, "s"), seq=0) for i in range(n)]


class ContextLeaksEngineTest(unittest.TestCase):
    def test_place_order_callback_self_is_not_the_engine(self):
        events = _clock_events(3)
        captured = []

        class _Capture(Strategy):
            def on_event(self, event, ctx) -> None:
                captured.append(ctx)

        engine = CoreEngine(strategy=_Capture(), events=events)
        engine.run()
        ctx = captured[0]
        cb = ctx._StrategyContext__place_order_cb
        leaked_engine = getattr(cb, "__self__", None)
        self.assertIsNot(
            leaked_engine,
            engine,
            "ctx._StrategyContext__place_order_cb.__self__ IS the CoreEngine "
            "instance -- a strategy can reach the full engine (its _log, "
            "_account, _order_requests, ...) one attribute hop past the "
            "'private' callback, defeating V5's 'no path to engine-internal "
            "state' claim. Name-mangling is not access control.",
        )

    def test_visible_events_private_window_does_not_expose_future_log(self):
        events = _clock_events(5)
        captured = []

        class _Capture(Strategy):
            def on_event(self, event, ctx) -> None:
                captured.append(ctx)

        engine = CoreEngine(strategy=_Capture(), events=events)
        engine.run()
        first_ctx = captured[0]  # only 1 event should ever be visible here
        window = first_ctx._StrategyContext__visible_events
        raw_log = getattr(window, "_log", None)
        self.assertIsNotNone(raw_log, "EventWindow has no _log attribute to inspect")
        now_ns = int(first_ctx.now_ns)
        future_events = [e for e in raw_log if int(e.received_time_ns) > now_ns]
        self.assertEqual(
            future_events,
            [],
            f"ctx._StrategyContext__visible_events._log contains "
            f"{len(future_events)} event(s) strictly after now_ns "
            f"({now_ns}), even though ctx.visible_events() correctly "
            "reports only 1 event -- the raw window's backing log is the "
            "FULL untruncated run log, reachable one attribute hop past "
            "the 'private' view. V3's lookahead prevention is bypassable.",
        )


if __name__ == "__main__":
    unittest.main()
