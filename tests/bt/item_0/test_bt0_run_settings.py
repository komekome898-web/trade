"""Run settings and event fields pass the same checks as event times
(i0-r1-08, i0-r1-11, i0-r1-13)."""
import pytest

from bot.bt.core import (
    BarEvent,
    CoreEngine,
    EventType,
    EventValidationError,
    LookAheadError,
    Strategy,
    TimestampUnitError,
)

from bt0_util import SEC, T0, Recorder, trade


def _trades():
    return [trade(T0 + i * SEC) for i in range(5)]


@pytest.mark.parametrize("bad", [float(T0 + 2 * SEC), True, 2**63, "1700000002000000000"])
def test_end_time_must_be_an_int64_of_ns(bad):
    with pytest.raises(TimestampUnitError):
        CoreEngine(Recorder(), _trades(), end_time_ns=bad)


def test_end_time_in_seconds_is_refused_instead_of_processing_nothing():
    engine = CoreEngine(Recorder(), _trades(), end_time_ns=(T0 + 2 * SEC) // SEC)
    with pytest.raises(TimestampUnitError, match="before the first entry"):
        engine.run()


def test_end_time_inside_the_run_still_stops_there():
    rec = Recorder()
    res = CoreEngine(rec, _trades(), end_time_ns=T0 + 2 * SEC).run()
    assert [e.received_time_ns for e in rec.seen] == [T0, T0 + SEC, T0 + 2 * SEC]
    assert res.stopped_at_end_time is True


@pytest.mark.parametrize("bad", [2.5, 0, -1, True, "5"])
def test_history_limit_must_be_a_positive_int(bad):
    with pytest.raises((TypeError, ValueError)):
        CoreEngine(Recorder(), _trades(), history_limit=bad)


def test_bar_start_must_be_before_its_close():
    with pytest.raises(EventValidationError):
        BarEvent(received_time_ns=T0, start_time_ns=T0, open=100.0, high=110.0, low=90.0, close=105.0, volume=1.0)
    with pytest.raises(EventValidationError):
        BarEvent(received_time_ns=T0, start_time_ns=T0, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
    b = BarEvent(received_time_ns=T0, start_time_ns=T0 - 1, open=100.0, high=110.0, low=90.0, close=105.0, volume=1.0)
    assert b.start_time_ns == T0 - 1


class _Reads(Strategy):
    def __init__(self, at, call):
        self.at, self.call, self.out = at, call, None

    def on_event(self, e, ctx):
        if ctx.now_ns == self.at:
            try:
                self.out = ("returned", self.call(ctx))
            except LookAheadError:
                self.out = ("LookAheadError", None)


@pytest.mark.parametrize("kwargs", [
    {"since_ns": T0 + 2 * SEC + 1},
    {"until_ns": T0 + 2 * SEC + 1},
    {"since_ns": T0, "until_ns": T0 + 3 * SEC},
    {"since_ns": T0 + 4 * SEC, "until_ns": T0 + 4 * SEC},
])
def test_any_time_argument_after_now_stops(kwargs):
    s = _Reads(T0 + 2 * SEC, lambda ctx: ctx.visible_events(EventType.TRADE, **kwargs))
    CoreEngine(s, _trades()).run()
    assert s.out == ("LookAheadError", None)


def test_time_arguments_up_to_now_are_answered():
    s = _Reads(T0 + 2 * SEC, lambda ctx: [e.received_time_ns for e in
                                         ctx.visible_events(since_ns=T0 + SEC, until_ns=T0 + 2 * SEC)])
    CoreEngine(s, _trades()).run()
    assert s.out == ("returned", [T0 + SEC, T0 + 2 * SEC])
    s = _Reads(T0 + 2 * SEC, lambda ctx: list(ctx.visible_events(since_ns=T0 + 2 * SEC)))
    CoreEngine(s, _trades()).run()
    assert s.out[0] == "returned" and len(s.out[1]) == 1
