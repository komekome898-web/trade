"""V4: deterministic same-instant event ordering."""
from __future__ import annotations

import unittest

from bot.bt.core.clock import TYPE_PRIORITY, build_event_log
from bot.bt.core.events import (
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    EventType,
    FundingEvent,
    LiquidationEvent,
    OrderAckEvent,
    OrderFillEvent,
    OrderRejectEvent,
    TradeEvent,
)
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")
T1 = to_nanos(1_700_000_001, "s")


class TypePriorityCoverageTest(unittest.TestCase):
    def test_every_event_type_has_a_priority(self):
        self.assertEqual(set(TYPE_PRIORITY), set(EventType))

    def test_priorities_are_a_dense_unique_ranking(self):
        values = sorted(TYPE_PRIORITY.values())
        self.assertEqual(values, list(range(len(EventType))))


class SameInstantOrderingTest(unittest.TestCase):
    def _all_types_at_same_instant(self):
        # One event of every type, all at T0, handed in a deliberately
        # scrambled arrival order so the sort key -- not insertion order --
        # is what has to produce the documented sequence.
        return [
            ClockEvent(received_time_ns=T0, seq=0),
            OrderFillEvent(received_time_ns=T0, seq=0, client_order_id="c", price=1, size=1),
            BarEvent(received_time_ns=T0, seq=0, open=1, high=1, low=1, close=1, volume=1),
            OrderRejectEvent(received_time_ns=T0, seq=0, client_order_id="c", reason="x"),
            TradeEvent(received_time_ns=T0, seq=0, price=1, size=1, side="buy", trade_id="t"),
            BookDeltaEvent(received_time_ns=T0, seq=0, side="bid", price=1, size=1),
            OrderAckEvent(received_time_ns=T0, seq=0, client_order_id="c", venue_order_id="v"),
            FundingEvent(received_time_ns=T0, seq=0, rate=0.0001),
            BookSnapshotEvent(received_time_ns=T0, seq=0, bids=(), asks=()),
            LiquidationEvent(received_time_ns=T0, seq=0, price=1, size=1, side="long"),
        ]

    def test_documented_priority_order_is_applied(self):
        ordered = build_event_log(self._all_types_at_same_instant())
        got = [e.EVENT_TYPE for e in ordered]
        expected = [
            EventType.LIQUIDATION,
            EventType.FUNDING,
            EventType.BOOK_SNAPSHOT,
            EventType.BOOK_DELTA,
            EventType.TRADE,
            EventType.BAR,
            EventType.ORDER_ACK,
            EventType.ORDER_REJECT,
            EventType.ORDER_FILL,
            EventType.CLOCK,
        ]
        self.assertEqual(got, expected)

    def test_primary_key_is_time_regardless_of_type(self):
        later_liquidation = LiquidationEvent(received_time_ns=T1, seq=0, price=1, size=1, side="long")
        earlier_clock = ClockEvent(received_time_ns=T0, seq=0)
        ordered = build_event_log([later_liquidation, earlier_clock])
        self.assertEqual([e.EVENT_TYPE for e in ordered], [EventType.CLOCK, EventType.LIQUIDATION])

    def test_same_type_same_instant_tie_break_is_arrival_order(self):
        a = TradeEvent(received_time_ns=T0, seq=0, price=1, size=1, side="buy", trade_id="a")
        b = TradeEvent(received_time_ns=T0, seq=0, price=2, size=1, side="buy", trade_id="b")
        ordered_ab = build_event_log([a, b])
        self.assertEqual([e.trade_id for e in ordered_ab], ["a", "b"])
        ordered_ba = build_event_log([b, a])
        self.assertEqual([e.trade_id for e in ordered_ba], ["b", "a"])

    def test_replay_is_reproducible(self):
        events = self._all_types_at_same_instant()
        first = [e.trade_id if isinstance(e, TradeEvent) else e.EVENT_TYPE for e in build_event_log(events)]
        second = [e.trade_id if isinstance(e, TradeEvent) else e.EVENT_TYPE for e in build_event_log(events)]
        self.assertEqual(first, second)

    def test_total_order_no_ties_possible(self):
        # seq is unique per event (assigned by position in the input), so no
        # two distinct events can ever compare equal under sort_key even if
        # they share both time and type.
        events = [
            TradeEvent(received_time_ns=T0, seq=0, price=float(i), size=1, side="buy", trade_id=str(i))
            for i in range(20)
        ]
        ordered = build_event_log(events)
        keys = [(e.received_time_ns, e.seq) for e in ordered]
        self.assertEqual(len(set(keys)), len(keys))


if __name__ == "__main__":
    unittest.main()
