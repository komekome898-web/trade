"""P0-4 by position: a history read returns `DeliveredEvents`, where naming
a position after the newest delivered event -- an index `>= len`, or a
slice with an explicit non-negative bound past the end -- raises
`FuturePositionError` (an IndexError and a LookAheadError) instead of a
silently shortened or empty answer, as a time argument after now does.
Scene p4-future-read-attempt: "空・切り詰め … は素通り".
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import (
    CoreEngine,
    DeliveredEvents,
    EventType,
    FuturePositionError,
    LookAheadError,
)

from bt0_util import SEC, T0, Recorder, bar

BAR = EventType.BAR


def _reads_at_fourth_bar(fn):
    got = {}

    def act(ev, ctx):
        if ev.EVENT_TYPE is BAR and ev.close == 103.0:
            got["value"] = fn(ctx)

    CoreEngine(Recorder(act), [bar(T0 + i * SEC, 100.0 + i) for i in range(6)]).run()
    return got["value"]


def _raises(fn):
    def attempt(ctx):
        try:
            fn(ctx)
        except FuturePositionError as exc:
            return exc
        return None
    return _reads_at_fourth_bar(attempt)


@pytest.mark.parametrize("read", [
    lambda ctx: ctx.visible_events(BAR)[4],
    lambda ctx: ctx.visible_events()[4],
    lambda ctx: ctx.visible_events(BAR, n=5)[4],
    lambda ctx: ctx.visible_events(BAR)[4:5],
    lambda ctx: ctx.visible_events(BAR)[3:5],
    lambda ctx: ctx.visible_events(BAR)[:5],
    lambda ctx: ctx.visible_events(BAR)[5:],
    lambda ctx: ctx.visible_events(BAR)[0:100:2],
    lambda ctx: ctx.visible_events(BAR)[4::-1],
    lambda ctx: ctx.visible_events(BAR)[1:][3],
    lambda ctx: ctx.visible_events(BAR)[1:][:4],
])
def test_naming_a_position_after_the_newest_is_refused(read):
    exc = _raises(read)
    assert isinstance(exc, FuturePositionError)
    assert isinstance(exc, IndexError) and isinstance(exc, LookAheadError)


def test_reads_within_the_delivered_positions_answer_as_a_tuple():
    def reads(ctx):
        bars = ctx.visible_events(BAR)
        return {
            "type": type(bars),
            "all": [b.close for b in bars],
            "last": bars[-1].close,
            "first": bars[0].close,
            "head": [b.close for b in bars[:4]],
            "tail2": [b.close for b in bars[-2:]],
            "from_end": [b.close for b in bars[4:]],  # "from position 4 on" = nothing new yet
            "past_clamp": [b.close for b in bars[-10:]],
            "reverse": [b.close for b in bars[::-1]],
            "eq_tuple": bars == tuple(bars),
        }
    got = _reads_at_fourth_bar(reads)
    assert got["type"] is DeliveredEvents
    assert got["all"] == [100.0, 101.0, 102.0, 103.0]
    assert got["last"] == 103.0 and got["first"] == 100.0
    assert got["head"] == got["all"] and got["tail2"] == [102.0, 103.0]
    assert got["from_end"] == [] and got["past_clamp"] == got["all"]
    assert got["reverse"] == [103.0, 102.0, 101.0, 100.0] and got["eq_tuple"] is True


def test_negative_index_before_the_oldest_is_a_plain_index_error():
    def read(ctx):
        try:
            ctx.visible_events(BAR)[-5]
        except FuturePositionError:
            return "future"
        except IndexError:
            return "past"
    assert _reads_at_fourth_bar(read) == "past"


def test_random_indexes_and_slices_match_a_list_or_are_refused_seeded():
    rng = random.Random(20260924)
    for _ in range(3000):
        n = rng.randrange(0, 7)
        seq = DeliveredEvents(range(n))
        ref = list(range(n))

        def bound():
            return rng.choice([None, rng.randrange(-9, 10)])
        if rng.random() < 0.3:
            i = rng.randrange(-9, 10)
            if i >= n:
                with pytest.raises(FuturePositionError):
                    seq[i]
            elif i < -n:
                with pytest.raises(IndexError):
                    seq[i]
            else:
                assert seq[i] == ref[i]
            continue
        start, stop = bound(), bound()
        step = rng.choice([None, 1, 2, -1, -2])
        st = 1 if step is None else step
        ahead = ((start is not None and start >= 0 and (start > n if st > 0 else start >= n))
                 or (st > 0 and stop is not None and stop > n))
        if ahead:
            with pytest.raises(FuturePositionError):
                seq[start:stop:step]
        else:
            out = seq[start:stop:step]
            assert list(out) == ref[start:stop:step] and type(out) is DeliveredEvents
