"""i0-r1-01: feed_delay_ns can push a delivered event's received_time_ns
past int64 without the engine ever raising.

The core's own contract (src/bot/bt/core/time.py docstring, TIME_CONTRACT
in contract.py, and REQUIREMENTS.md observation 3, "UTC の int64 ナノ秒
... を原典の型定義・契約で確認する") is that every timestamp inside the
core is an int, range-checked to int64. `engine.py:199-205` (`_check_delay`)
only checks that a latency model's delay is a non-negative int -- it never
bounds it, and `engine.py:392-408` (`_deliver`) sets the delivered event's
`received_time_ns` with `object.__setattr__`, bypassing `Event.__post_init__`
/ `validate_nanos` entirely ("the event was validated at construction ...
re-running validation would only cost time" -- true for the ORIGINAL value,
false for `time_ns` after a delay has been added to it).

This test shows the asymmetry directly: the exact same style of oversized
delay from `order_delay_ns` / `notice_delay_ns` DOES raise TimestampUnitError
(because those paths construct notice events with the normal constructor /
`dataclasses.replace`, which re-run `__post_init__`), but `feed_delay_ns`
does not, because market-data delivery goes through `object.__setattr__`
instead. A latency model (item 4's job, not written yet) that has a unit
bug -- exactly the class of bug `to_nanos` exists to catch on the way IN --
is not caught on the way OUT here, and the resulting event silently carries
a `received_time_ns` that is not a valid int64 any more, undetected.
"""
from __future__ import annotations

import pytest

from bot.bt.core import CoreEngine, Strategy, TimestampUnitError
from bot.bt.core.time import INT64_MAX

T0 = 1_700_000_000_000_000_000  # 2023-11-14T22:13:20Z in ns, matches core tests' _util.T0

_HUGE_DELAY = 10**30  # a plausible "unit bug" magnitude (e.g. ns mistaken for something else)


class _Recorder(Strategy):
    def __init__(self) -> None:
        self.seen: list = []

    def on_event(self, event, ctx) -> None:
        self.seen.append(event)


class _HugeFeedDelay:
    """A latency model that is protocol-legal (returns a non-negative int
    from every method) but has a unit bug in feed_delay_ns specifically."""

    def feed_delay_ns(self, event):
        return _HUGE_DELAY

    def order_delay_ns(self, order, sent_time_ns):
        return 0

    def cancel_delay_ns(self, request, sent_time_ns):
        return 0

    def notice_delay_ns(self, report, venue_time_ns):
        return 0


def test_feed_delay_must_not_silently_produce_a_received_time_ns_outside_int64():
    """The desired contract (this is what should be true): a delivered
    market-data event's `received_time_ns` is always a valid int64 --
    either because the engine keeps it in range, or because it raises
    `TimestampUnitError` the way the order/notice channels do below.

    Currently this FAILS: the engine neither keeps it in range nor raises;
    it silently hands the strategy an event whose own declared contract
    (time.py's int64 range check) has been violated. `pytest.raises` is
    used with a fallback assertion so the failure is legible either way
    (a raise that is the wrong type, or no raise at all)."""
    from bot.bt.core import TradeEvent

    rec = _Recorder()
    events = [TradeEvent(received_time_ns=T0, price=100.0, size=1.0, side="buy")]
    try:
        CoreEngine(rec, events, latency_model=_HugeFeedDelay()).run()
    except TimestampUnitError:
        return  # acceptable: failed loudly, like the order/notice channels do
    assert len(rec.seen) == 1
    delivered_ns = rec.seen[0].received_time_ns
    assert delivered_ns <= INT64_MAX, (
        f"delivered event received_time_ns={delivered_ns} exceeds INT64_MAX="
        f"{INT64_MAX} and no TimestampUnitError was raised: engine.py's "
        "_deliver() sets received_time_ns via object.__setattr__ (bypassing "
        "Event.__post_init__ / validate_nanos), so a latency model's "
        "feed_delay_ns can push a delivered event's timestamp outside the "
        "core's own declared int64 contract without detection -- unlike "
        "order_delay_ns / notice_delay_ns, which DO raise (see the two "
        "tests below)."
    )


def test_order_channel_raises_loudly_on_the_same_magnitude_of_delay():
    """Contrast case: the order-request channel does NOT have this bug --
    it fails loudly. This shows the gap is specific to feed_delay_ns /
    market-data delivery, not a blanket "the core never checks this"."""
    from bot.bt.core import ClockEvent, OrderRequest

    class _HugeOrderDelay:
        def feed_delay_ns(self, event):
            return 0

        def order_delay_ns(self, order, sent_time_ns):
            return _HUGE_DELAY

        def cancel_delay_ns(self, request, sent_time_ns):
            return 0

        def notice_delay_ns(self, report, venue_time_ns):
            return 0

    class _Placer(Strategy):
        def on_event(self, event, ctx):
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    with pytest.raises(TimestampUnitError):
        CoreEngine(_Placer(), [ClockEvent(received_time_ns=T0)], latency_model=_HugeOrderDelay()).run()


def test_notice_channel_raises_loudly_on_the_same_magnitude_of_delay():
    from bot.bt.core import ClockEvent, NullCostModel, OrderRequest
    from bot.bt.core.testing import ImmediateFillModel

    class _HugeNoticeDelay:
        def feed_delay_ns(self, event):
            return 0

        def order_delay_ns(self, order, sent_time_ns):
            return 0

        def cancel_delay_ns(self, request, sent_time_ns):
            return 0

        def notice_delay_ns(self, report, venue_time_ns):
            return _HUGE_DELAY

    class _Placer(Strategy):
        def on_event(self, event, ctx):
            ctx.place_order(OrderRequest("buy", "market", 1.0))

    with pytest.raises(TimestampUnitError):
        CoreEngine(
            _Placer(),
            [ClockEvent(received_time_ns=T0)],
            fill_model=ImmediateFillModel(fixed_price=1.0),
            cost_model=NullCostModel(),
            latency_model=_HugeNoticeDelay(),
        ).run()
