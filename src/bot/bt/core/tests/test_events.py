"""V2: event-type coverage under a single type system."""
from __future__ import annotations

import unittest

from bot.bt.core.events import (
    ALL_EVENT_CLASSES,
    EVENT_TYPE_TO_CLASS,
    BarEvent,
    BookDeltaEvent,
    BookSnapshotEvent,
    ClockEvent,
    Event,
    EventType,
    FundingEvent,
    LiquidationEvent,
    OrderAckEvent,
    OrderFillEvent,
    OrderRejectEvent,
    TradeEvent,
)
from bot.bt.core.time import TimestampUnitError, to_nanos

_REQUIRED_KINDS = {
    "trade",
    "book snapshot",
    "book delta",
    "bar",
    "funding",
    "liquidation",
    "clock",
    "order accept",
    "order reject",
    "order fill",
}


class EventTypeCoverageTest(unittest.TestCase):
    def test_at_least_eight_event_types(self):
        self.assertGreaterEqual(len(EventType), 8)

    def test_exactly_ten_event_types_committed_row(self):
        # 執行・板の写真・板の差分・足・資金調達・清算・時計・受付/拒否/約定
        # の逐語どおりの種類数(受付/拒否/約定は3種に数える)。
        self.assertEqual(len(EventType), 10)

    def test_required_kinds_are_all_representable(self):
        names = {member.value for member in EventType}
        self.assertIn("TRADE", names)
        self.assertIn("BOOK_SNAPSHOT", names)
        self.assertIn("BOOK_DELTA", names)
        self.assertIn("BAR", names)
        self.assertIn("FUNDING", names)
        self.assertIn("LIQUIDATION", names)
        self.assertIn("CLOCK", names)
        self.assertIn("ORDER_ACK", names)
        self.assertIn("ORDER_REJECT", names)
        self.assertIn("ORDER_FILL", names)

    def test_every_event_type_has_exactly_one_class(self):
        self.assertEqual(set(EVENT_TYPE_TO_CLASS), set(EventType))
        self.assertEqual(len(ALL_EVENT_CLASSES), len(EventType))
        self.assertEqual(len(set(ALL_EVENT_CLASSES)), len(ALL_EVENT_CLASSES))

    def test_every_class_is_an_event_subclass(self):
        for cls in ALL_EVENT_CLASSES:
            self.assertTrue(issubclass(cls, Event))
            self.assertIsNot(cls, Event)

    def test_every_class_declares_its_own_event_type(self):
        for event_type, cls in EVENT_TYPE_TO_CLASS.items():
            self.assertIs(cls.EVENT_TYPE, event_type)


def _ts(seconds: int = 1_700_000_000):
    return to_nanos(seconds, "s")


class EventConstructionTest(unittest.TestCase):
    def test_trade_event(self):
        ev = TradeEvent(received_time_ns=_ts(), seq=0, price=100.0, size=1.0, side="buy", trade_id="t1")
        self.assertIs(ev.EVENT_TYPE, EventType.TRADE)

    def test_book_snapshot_event(self):
        ev = BookSnapshotEvent(
            received_time_ns=_ts(), seq=0, bids=((99.0, 1.0),), asks=((101.0, 1.0),)
        )
        self.assertIs(ev.EVENT_TYPE, EventType.BOOK_SNAPSHOT)

    def test_book_delta_event(self):
        ev = BookDeltaEvent(received_time_ns=_ts(), seq=0, side="bid", price=99.0, size=0.0)
        self.assertIs(ev.EVENT_TYPE, EventType.BOOK_DELTA)

    def test_bar_event(self):
        ev = BarEvent(received_time_ns=_ts(), seq=0, open=1, high=2, low=0.5, close=1.5, volume=10)
        self.assertIs(ev.EVENT_TYPE, EventType.BAR)

    def test_funding_event(self):
        ev = FundingEvent(received_time_ns=_ts(), seq=0, rate=0.0001)
        self.assertIs(ev.EVENT_TYPE, EventType.FUNDING)

    def test_liquidation_event(self):
        ev = LiquidationEvent(received_time_ns=_ts(), seq=0, price=100.0, size=1.0, side="long")
        self.assertIs(ev.EVENT_TYPE, EventType.LIQUIDATION)

    def test_clock_event(self):
        ev = ClockEvent(received_time_ns=_ts(), seq=0)
        self.assertIs(ev.EVENT_TYPE, EventType.CLOCK)

    def test_order_ack_event(self):
        ev = OrderAckEvent(received_time_ns=_ts(), seq=0, client_order_id="c1", venue_order_id="v1")
        self.assertIs(ev.EVENT_TYPE, EventType.ORDER_ACK)

    def test_order_reject_event(self):
        ev = OrderRejectEvent(received_time_ns=_ts(), seq=0, client_order_id="c1", reason="bad price")
        self.assertIs(ev.EVENT_TYPE, EventType.ORDER_REJECT)

    def test_order_fill_event(self):
        ev = OrderFillEvent(received_time_ns=_ts(), seq=0, client_order_id="c1", price=100.0, size=1.0)
        self.assertIs(ev.EVENT_TYPE, EventType.ORDER_FILL)

    def test_events_are_frozen(self):
        ev = ClockEvent(received_time_ns=_ts(), seq=0)
        with self.assertRaises(Exception):
            ev.seq = 1  # type: ignore[misc]

    def test_bad_timestamp_rejected_at_construction(self):
        with self.assertRaises(TimestampUnitError):
            ClockEvent(received_time_ns=1.5, seq=0)  # type: ignore[arg-type]

    def test_bad_seq_rejected_at_construction(self):
        with self.assertRaises(TypeError):
            ClockEvent(received_time_ns=_ts(), seq="0")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
