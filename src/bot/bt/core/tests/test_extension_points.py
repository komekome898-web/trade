"""V6: fill/latency/cost/account are pluggable sockets, not logic baked into
the core. Defines throwaway implementations OUTSIDE `core/` (right here, in
a test file) that satisfy the Protocols in interfaces.py, and shows
`CoreEngine` runs with them -- and with none of them (defaults) -- without
any change to engine.py."""
from __future__ import annotations

import unittest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import ClockEvent, FundingEvent, LiquidationEvent, TradeEvent
from bot.bt.core.interfaces import (
    Account,
    CostModel,
    FillModel,
    FillNotice,
    LatencyModel,
    NullAccount,
    NullCostModel,
    NullFillModel,
    NullLatencyModel,
)
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import Nanos, to_nanos

T0 = to_nanos(1_700_000_000, "s")


class _NoOpStrategy(Strategy):
    def on_event(self, event, ctx) -> None:
        return None


class _FillEveryTrade:
    """A minimal FillModel implementation living outside core/, proving the
    Protocol -- not a base class -- is the actual contract."""

    def __init__(self) -> None:
        self.calls = 0

    def on_event(self, event, visible_events) -> list[FillNotice]:
        self.calls += 1
        if isinstance(event, TradeEvent):
            return [FillNotice(client_order_id="x", price=event.price, size=event.size)]
        return []


class _FixedLatency:
    def __init__(self, ns: int) -> None:
        self._ns = ns
        self.calls = 0

    def delay_ns(self, event) -> Nanos:
        self.calls += 1
        return Nanos(self._ns)


class _FlatFeeCost:
    def __init__(self, fee: float) -> None:
        self._fee = fee
        self.calls = 0

    def cost(self, fill: FillNotice) -> float:
        self.calls += 1
        return self._fee


class _RecordingAccount:
    def __init__(self) -> None:
        self.fills: list[FillNotice] = []
        self.funding_events: list = []
        self.liquidation_events: list = []

    def apply_fill(self, fill: FillNotice) -> None:
        self.fills.append(fill)

    def apply_funding(self, event) -> None:
        self.funding_events.append(event)

    def apply_liquidation(self, event) -> None:
        self.liquidation_events.append(event)


class ProtocolConformanceTest(unittest.TestCase):
    def test_throwaway_implementations_satisfy_the_runtime_checkable_protocols(self):
        self.assertIsInstance(_FillEveryTrade(), FillModel)
        self.assertIsInstance(_FixedLatency(0), LatencyModel)
        self.assertIsInstance(_FlatFeeCost(0.0), CostModel)
        self.assertIsInstance(_RecordingAccount(), Account)

    def test_null_defaults_also_satisfy_the_protocols(self):
        self.assertIsInstance(NullFillModel(), FillModel)
        self.assertIsInstance(NullLatencyModel(), LatencyModel)
        self.assertIsInstance(NullCostModel(), CostModel)
        self.assertIsInstance(NullAccount(), Account)


class EngineWiringTest(unittest.TestCase):
    def test_runs_with_no_extension_points_supplied(self):
        engine = CoreEngine(strategy=_NoOpStrategy(), events=[ClockEvent(received_time_ns=T0, seq=0)])
        result = engine.run()
        self.assertEqual(result.events_processed, 1)

    def test_custom_fill_model_is_invoked_once_per_event_without_touching_engine_py(self):
        events = [
            TradeEvent(received_time_ns=T0, seq=0, price=100.0, size=1.0, side="buy", trade_id="t1"),
            ClockEvent(received_time_ns=to_nanos(1_700_000_001, "s"), seq=0),
        ]
        fill_model = _FillEveryTrade()
        cost_model = _FlatFeeCost(fee=1.5)
        account = _RecordingAccount()
        engine = CoreEngine(
            strategy=_NoOpStrategy(),
            events=events,
            fill_model=fill_model,
            cost_model=cost_model,
            account=account,
        )
        engine.run()
        self.assertEqual(fill_model.calls, 2)  # once per event
        self.assertEqual(len(account.fills), 1)  # only the TradeEvent produced a fill
        self.assertEqual(cost_model.calls, 1)
        self.assertEqual(account.fills[0].price, 100.0)

    def test_custom_latency_model_is_invoked_per_event(self):
        events = [ClockEvent(received_time_ns=T0, seq=0), ClockEvent(received_time_ns=to_nanos(1_700_000_001, "s"), seq=0)]
        latency_model = _FixedLatency(ns=500)
        engine = CoreEngine(strategy=_NoOpStrategy(), events=events, latency_model=latency_model)
        engine.run()
        self.assertEqual(latency_model.calls, 2)

    def test_funding_events_reach_the_account_socket(self):
        events = [FundingEvent(received_time_ns=T0, seq=0, rate=0.0001)]
        account = _RecordingAccount()
        engine = CoreEngine(strategy=_NoOpStrategy(), events=events, account=account)
        engine.run()
        self.assertEqual(len(account.funding_events), 1)

    def test_liquidation_events_reach_the_account_socket(self):
        # Symmetric with the FUNDING case above (round-1 critic finding
        # i0-r1-04): LIQUIDATION is wired to the account the same way.
        events = [
            LiquidationEvent(received_time_ns=T0, seq=0, price=100.0, size=1.0, side="long")
        ]
        account = _RecordingAccount()
        engine = CoreEngine(strategy=_NoOpStrategy(), events=events, account=account)
        engine.run()
        self.assertEqual(len(account.liquidation_events), 1)

    def test_swapping_the_fill_model_changes_behavior_without_engine_changes(self):
        # Same engine.py code path, two different outcomes purely from what
        # was plugged in -- this is the measurable form of "separated as a
        # pluggable component" the requirement asks for.
        events = [TradeEvent(received_time_ns=T0, seq=0, price=1, size=1, side="buy", trade_id="t")]

        account_a = _RecordingAccount()
        CoreEngine(strategy=_NoOpStrategy(), events=events, fill_model=NullFillModel(), account=account_a).run()
        self.assertEqual(len(account_a.fills), 0)

        account_b = _RecordingAccount()
        CoreEngine(strategy=_NoOpStrategy(), events=events, fill_model=_FillEveryTrade(), account=account_b).run()
        self.assertEqual(len(account_b.fills), 1)


if __name__ == "__main__":
    unittest.main()
