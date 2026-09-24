"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-10.

ordering.py 120-126 keeps the order of ONE stream for same-time events of the
same type ("the stream's own sequence (for example the venue's print order
of two trades in one nanosecond)"), but re-sorts same-time events of
DIFFERENT types inside that same stream by TYPE_ORDER. A venue-sequenced
feed that printed a trade and then the book delta caused by that trade in the
same nanosecond reaches the fill model (and the strategy) as delta, then
trade: the core silently inverts the venue's own sequence, with no way for
the data layer to keep it. For queue-position models (item 3: "列の位置の追跡")
the order of a trade and a level decrease at one instant is the information
itself (consumed by the trade vs. canceled).
"""
from __future__ import annotations

from bot.bt.core import BookDeltaEvent, CoreEngine, NullCostModel, Strategy, TradeEvent

T = 1_700_006_400_000_000_000


class _Venue:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def on_market_event(self, event, venue_time_ns):
        self.seen.append(event.EVENT_TYPE.value)
        return ()

    def on_order(self, order, venue_time_ns):  # pragma: no cover
        return ()

    def on_cancel(self, request, venue_time_ns):  # pragma: no cover
        return ()


class _Quiet(Strategy):
    def __init__(self) -> None:
        self.seen: list[str] = []

    def on_event(self, event, ctx) -> None:
        self.seen.append(event.EVENT_TYPE.value)


def test_one_stream_same_instant_keeps_the_venue_sequence():
    stream = [  # the venue's own print order, one feed, one nanosecond
        TradeEvent(received_time_ns=T, price=100.0, size=1.0, side="sell"),
        BookDeltaEvent(received_time_ns=T, side="bid", price=100.0, size=0.0),
    ]
    venue, strat = _Venue(), _Quiet()
    CoreEngine(strat, stream, fill_model=venue, cost_model=NullCostModel()).run()
    assert venue.seen == ["TRADE", "BOOK_DELTA"], f"venue saw {venue.seen}"
    assert strat.seen == ["TRADE", "BOOK_DELTA"], f"strategy saw {strat.seen}"
