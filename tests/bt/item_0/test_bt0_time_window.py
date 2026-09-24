"""P0-4: reading history by time. Asking for anything after now is a
runtime error (LookAheadError), never a silently shortened answer."""
import random

import pytest

from bot.bt.core import (
    CoreEngine,
    EventType,
    HistoryTruncatedError,
    LookAheadError,
    StaleContextError,
)

from bt0_util import SEC, T0, Recorder, bar, clock, trade


def _bars(n=6):
    return [bar(T0 + i * 60 * SEC, 100.0 + i) for i in range(n)]


def test_until_after_now_raises_lookahead_error():
    raised = []

    def act(ev, ctx):
        with pytest.raises(LookAheadError):
            ctx.visible_events(until_ns=int(ctx.now_ns) + 1)
        with pytest.raises(LookAheadError):
            ctx.visible_events(EventType.BAR, until_ns=int(ctx.now_ns) + 60 * SEC)
        raised.append(True)

    CoreEngine(Recorder(act), _bars()).run()
    assert len(raised) == 6


def test_until_now_is_allowed_and_equals_everything():
    def act(ev, ctx):
        assert ctx.visible_events(until_ns=ctx.now_ns) == ctx.visible_events()

    CoreEngine(Recorder(act), _bars()).run()


def test_time_window_known_answer():
    # at the bar of 300s (index 5) the bars in [60s, 180s] are 101, 102, 103
    probe = {}

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.BAR and ev.close == 105.0:
            got = ctx.visible_events(EventType.BAR, since_ns=T0 + 60 * SEC, until_ns=T0 + 180 * SEC)
            probe["closes"] = [e.close for e in got]
            probe["last2"] = [e.close for e in ctx.visible_events(
                EventType.BAR, n=2, until_ns=T0 + 180 * SEC)]
            probe["empty"] = ctx.visible_events(since_ns=T0 + 181 * SEC, until_ns=T0 + 239 * SEC)

    CoreEngine(Recorder(act), _bars()).run()
    assert probe == {"closes": [101.0, 102.0, 103.0], "last2": [102.0, 103.0], "empty": ()}


def test_typed_view_equals_filtered_full_history_on_random_input():
    rng = random.Random(3)
    events, t = [], T0
    for _ in range(400):
        t += rng.choice([0, 1, 10])
        events.append(trade(t, 100.0) if rng.random() < 0.7 else (bar(t, 100.0) if rng.random() < 0.5 else clock(t)))
    checks = []

    def act(ev, ctx):
        full = ctx.visible_events()
        for et in (EventType.TRADE, EventType.BAR, EventType.CLOCK):
            filtered = tuple(e for e in full if e.EVENT_TYPE is et)
            assert ctx.visible_events(et) == filtered
            k = rng.randint(0, 5)
            assert ctx.visible_events(et, n=k) == (filtered[-k:] if k else ())
            since = int(ctx.now_ns) - rng.randint(0, 50)
            assert ctx.visible_events(et, since_ns=since) == tuple(
                e for e in filtered if int(e.received_time_ns) >= since)
        checks.append(1)

    CoreEngine(Recorder(act), events).run()
    assert len(checks) == 400


def test_typed_views_are_revoked_with_the_context():
    kept = []

    def act(ev, ctx):
        kept.append(ctx)

    CoreEngine(Recorder(act), _bars(2)).run()
    for ctx in kept:
        with pytest.raises(StaleContextError):
            ctx.visible_events(EventType.BAR)
        with pytest.raises(StaleContextError):
            ctx.visible_events(until_ns=T0)


def test_history_limit_applies_per_type_too():
    events = [trade(T0 + i, 1.0) for i in range(50)] + [bar(T0 + 100, 1.0)]
    probe = {}

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.BAR:
            probe["bars"] = len(ctx.visible_events(EventType.BAR))
            probe["trades10"] = len(ctx.visible_events(EventType.TRADE, n=10))
            # rewritten in round 3 (i0-r2-03): reading every trade after some
            # were dropped is refused, not answered with the kept part only
            with pytest.raises(HistoryTruncatedError):
                ctx.visible_events(EventType.TRADE)

    CoreEngine(Recorder(act), events, history_limit=10).run()
    assert probe["bars"] == 1  # the bar is kept although 50 trades came first
    assert probe["trades10"] == 10
