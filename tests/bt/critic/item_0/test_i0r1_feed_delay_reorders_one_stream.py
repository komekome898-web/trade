"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-12.

ordering.py 116-118: "Inside one stream the stream's own order is kept";
engine.py 14-19 says the order and notice channels are FIFO "as on a single
connection". The market-data feed is not: `_ingest` (engine.py 407-417)
schedules each event at `received_time_ns + feed_delay_ns(event)` with no
clamp against the previous event of the same stream, so a latency model
whose feed delay varies per event (item 4: "実測の分布・種つきの乱数")
makes a later trade of one stream overtake an earlier one. The strategy
receives the stream out of its own order, silently.
"""
from __future__ import annotations

from bot.bt.core import CoreEngine, Strategy, TradeEvent, ZeroLatency

T0 = 1_700_006_400_000_000_000
MS = 1_000_000


class _Jitter(ZeroLatency):
    """First print 5 ms feed delay, second print 0 (a jittered distribution)."""

    def feed_delay_ns(self, event):
        return 5 * MS if event.price == 100.0 else 0


class _Rec(Strategy):
    def __init__(self) -> None:
        self.prices: list[float] = []

    def on_event(self, event, ctx) -> None:
        if event.EVENT_TYPE.value == "TRADE":
            self.prices.append(event.price)


def test_feed_delay_does_not_make_a_stream_overtake_itself():
    stream = [TradeEvent(received_time_ns=T0, price=100.0, size=1.0, side="buy"),
              TradeEvent(received_time_ns=T0 + 1 * MS, price=101.0, size=1.0, side="buy")]
    strat = _Rec()
    CoreEngine(strat, stream, latency_model=_Jitter()).run()
    assert strat.prices == [100.0, 101.0], f"one stream delivered as {strat.prices}"
