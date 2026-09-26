import time

import pytest

from bot.bt.core import (
    ClockEvent,
    CoreEngine,
    EventOrderError,
    EventType,
    OrderAckEvent,
    SourceEventTypeError,
)

from bt0_util import SEC, T0, Recorder, trade


def test_source_going_backwards_is_an_error_not_a_resort():
    with pytest.raises(EventOrderError):
        CoreEngine(Recorder(), [trade(T0 + 1), trade(T0)]).run()


def test_order_notices_cannot_come_from_the_source():
    with pytest.raises(SourceEventTypeError):
        CoreEngine(Recorder(), [OrderAckEvent(received_time_ns=T0, client_order_id="x")]).run()
    with pytest.raises(SourceEventTypeError):
        CoreEngine(Recorder(), ["not an event"]).run()


def test_step_processes_one_entry_at_a_time():
    rec = Recorder()
    eng = CoreEngine(rec, [trade(T0), trade(T0 + 1)])
    steps = 0
    while eng.step():
        steps += 1
    # 2 venue entries + 2 deliveries
    assert steps == 4 and len(rec.seen) == 2 and eng.now_ns == T0 + 1


def test_end_time_stops_before_later_entries():
    rec = Recorder()
    res = CoreEngine(rec, [trade(T0 + i * SEC) for i in range(5)], end_time_ns=T0 + 2 * SEC).run()
    assert len(rec.seen) == 3 and res.stopped_at_end_time


def test_history_limit_bounds_memory_but_keeps_the_latest():
    # rewritten in round 3: an unbounded read after a drop now raises
    # HistoryTruncatedError (i0-r2-03), so the kept size is read from the
    # engine's history and the latest events through a read bounded by n
    lens, latest = [], []
    eng = CoreEngine(Recorder(lambda ev, ctx: latest.append(ctx.visible_events(n=5))),
                     [trade(T0 + i) for i in range(50)], history_limit=5)
    while eng.step():
        lens.append(eng._history.count())  # the core's own count of the kept events (round 10)
    assert max(lens) <= 10 and lens[-1] >= 5
    assert [e.received_time_ns for e in latest[-1]] == [T0 + i for i in range(45, 50)]
    with pytest.raises(ValueError):
        CoreEngine(Recorder(), [], history_limit=0)


def test_visible_events_n_and_type_filters():
    got = {}

    def act(ev, ctx):
        got["n0"] = ctx.visible_events(n=0)
        got["last2"] = [e.EVENT_TYPE for e in ctx.visible_events(n=2)]
        got["trades1"] = ctx.visible_events(EventType.TRADE, n=1)
        got["last_clock"] = ctx.last(EventType.CLOCK)

    CoreEngine(Recorder(act), [trade(T0, 1.0), trade(T0 + 1, 2.0), ClockEvent(received_time_ns=T0 + 2)]).run()
    assert got["n0"] == ()
    assert got["last2"] == [EventType.TRADE, EventType.CLOCK]
    assert got["trades1"][0].price == 2.0
    assert got["last_clock"].received_time_ns == T0 + 2


def _time_run(n):
    events = [trade(T0 + i) for i in range(n)]
    t = time.perf_counter()
    CoreEngine(Recorder(), events).run()
    return time.perf_counter() - t


def test_cost_grows_close_to_linearly():
    small = min(_time_run(3000) for _ in range(3))
    large = min(_time_run(12000) for _ in range(3))
    assert large / small < 8.0  # 4x events; quadratic would be ~16x
