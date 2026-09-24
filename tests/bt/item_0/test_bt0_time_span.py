"""P0-2, the refusing side (i0-r4-06): a run can state its time span, and
then an input event whose time is in another unit (seconds, milliseconds,
microseconds handed over as ns) is refused instead of being taken as a
1970 event. A bare int carries no unit, so the core cannot tell by itself
-- every int64 is a time (test_bt0_no_time_sentinel.py) -- and the run's
declared span is what the magnitude is checked against. A run that does
not state it records "time_span" in `defaults_used`."""
from __future__ import annotations

import pytest

from bot.bt.core import CORE_CONTRACT, CoreEngine, EngineFailedError, TimestampUnitError

from bt0_util import SEC, T0, Recorder, trade

SPAN = (T0, T0 + 3600 * SEC)
T0_S = T0 // 1_000_000_000  # the same instant in s, ms, us
T0_MS = T0 // 1_000_000
T0_US = T0 // 1_000


@pytest.mark.parametrize("unit, value", [("s", T0_S), ("ms", T0_MS), ("us", T0_US)])
@pytest.mark.parametrize("which", ["received", "exchange"])
def test_a_time_in_another_unit_is_refused_when_the_span_is_stated(unit, value, which):
    if which == "received":
        bad = trade(value)  # its exchange time defaults to the same value; both are outside
    else:
        bad = trade(T0 + SEC, exch=value)  # exchange time <= received time still holds
    with pytest.raises(TimestampUnitError, match=f"_time_ns {value}, outside.*another unit"):
        CoreEngine(Recorder(), [trade(T0), bad], time_span_ns=SPAN).run()


def test_mixing_a_seconds_stream_with_a_ns_stream_stops_at_the_first_seconds_event():
    streams = {"ns": [trade(T0), trade(T0 + SEC)], "secs": [trade(T0_S), trade(T0_S + 1)]}
    rec = Recorder()
    with pytest.raises(TimestampUnitError, match="stream 'secs' event #1"):
        CoreEngine(rec, streams, time_span_ns=SPAN).run()
    assert rec.seen == []  # refused while reading the streams, before anything was delivered


def test_the_ends_of_the_span_are_included():
    rec = Recorder()
    res = CoreEngine(rec, [trade(SPAN[0]), trade(SPAN[1])], time_span_ns=SPAN).run()
    assert [e.received_time_ns for e in rec.seen] == list(SPAN)
    assert res.time_span_ns == SPAN and "time_span" not in res.defaults_used


def test_one_past_either_end_is_refused():
    for t in (SPAN[0] - 1, SPAN[1] + 1):
        with pytest.raises(TimestampUnitError, match="outside the run's time_span_ns"):
            CoreEngine(Recorder(), [trade(t)], time_span_ns=SPAN).run()


def test_a_refused_event_later_in_the_run_leaves_the_engine_failed():
    """The check runs when an event is read from its stream, inside a step:
    the engine is FAILED afterwards, never continued (i0-r3-01)."""
    eng = CoreEngine(Recorder(), [trade(T0), trade(T0 + SEC), trade(T0_S + 10**9)], time_span_ns=SPAN)
    with pytest.raises(TimestampUnitError):
        eng.run()
    with pytest.raises(EngineFailedError):
        eng.run()


def test_without_a_span_every_int64_is_a_time_and_the_result_says_so():
    rec = Recorder()
    res = CoreEngine(rec, [trade(T0_S), trade(T0)]).run()
    assert [e.received_time_ns for e in rec.seen] == [T0_S, T0]
    assert "time_span" in res.defaults_used and res.time_span_ns is None


@pytest.mark.parametrize("span, match", [
    ((T0 + 1, T0), "after the last"),
    ((float(T0), T0 + 1), "time_span_ns"),
    ((T0, 2**63), "time_span_ns"),
    ([T0, T0 + 1], "tuple"),
    ((T0,), "tuple"),
])
def test_a_malformed_span_is_refused_at_construction(span, match):
    with pytest.raises(TimestampUnitError, match=match):
        CoreEngine(Recorder(), [trade(T0)], time_span_ns=span)


def test_the_contract_states_the_run_setting():
    rule = CORE_CONTRACT["run_settings"]["time_span_ns"]
    assert "TimestampUnitError" in rule and "defaults_used" in rule
