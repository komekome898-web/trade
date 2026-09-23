"""P0-5 on the venue side: at one instant the fill model and the account see
market events in the declared type order, whatever order the input had."""
import random

from bot.bt.core import (
    BookDeltaEvent,
    BookSnapshotEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    LiquidationEvent,
)
from bot.bt.core.ordering import TYPE_ORDER

from bt0_util import T0, Recorder, bar, trade


class _SeeingVenue:
    def __init__(self):
        self.seen = []

    def on_market_event(self, e, t):
        self.seen.append(e.EVENT_TYPE)
        return ()

    def on_order(self, o, t):  # pragma: no cover - no orders here
        return ()

    def on_cancel(self, r, t):  # pragma: no cover
        return ()


def test_fill_model_sees_same_instant_market_events_in_type_order():
    base = [
        trade(T0, 100.0),
        bar(T0, 100.0),
        BookDeltaEvent(received_time_ns=T0, side="ask", price=101.0, size=1.0),
        BookSnapshotEvent(received_time_ns=T0, bids=[[99.0, 1.0]], asks=[[101.0, 1.0]]),
        FundingEvent(received_time_ns=T0, rate=0.0001),
        LiquidationEvent(received_time_ns=T0, price=100.0, size=1.0, side="sell"),
    ]
    expected = [t for t in TYPE_ORDER if t in {e.EVENT_TYPE for e in base}]
    for seed in range(20):
        shuffled = base[:]
        random.Random(seed).shuffle(shuffled)
        venue = _SeeingVenue()
        CoreEngine(Recorder(), shuffled, fill_model=venue).run()
        assert venue.seen == expected
    assert expected == [
        EventType.LIQUIDATION, EventType.FUNDING, EventType.BOOK_SNAPSHOT,
        EventType.BOOK_DELTA, EventType.TRADE, EventType.BAR,
    ]
