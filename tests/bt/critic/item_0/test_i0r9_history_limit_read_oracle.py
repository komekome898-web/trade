"""Critic, item 0, round 9: an independent oracle for history reads under
`history_limit` (history.py was rebuilt in round 9: the core's own records
beside the lists).

The oracle is built from the documented rule only (history.py docstring,
CORE_CONTRACT["visibility"]["history_limit"]), not from the code: per event
type the latest N..2N delivered events are kept (when a type holds 2N, its
oldest are dropped down to N-1, then the new one is kept); a read either
raises HistoryTruncatedError or returns exactly the answer the same read
gives without the limit; an answer that is returned knows its place in the
kept events of what the read reads (first = index there, step 1, delivered
= how many are kept, dropped = delivered events before the oldest kept one).

What this test does NOT assert: that every read whose no-limit answer lies in
the kept events is answered (the core refuses some of those, CRITIC.md
i0-r9-01); only that nothing is returned silently short or wrong.

Grid: 3 input types (trade, bar, funding) in one stream with ties in the
received time, N in {1, 2, 3}, 12 seeds; at every callback every read of
event_type in {None, the 3 types} x n in {None, 0, 1, 2, 3, 5} x 4 sampled
since_ns x 4 sampled until_ns (sampled from the received times seen, +-1 ns,
and None). Not in the grid: book, liquidation, notices and timers as
history types; feed delays (the history is in delivery order either way).
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import BarEvent, CoreEngine, EventType, FundingEvent, HistoryTruncatedError, TradeEvent

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
TYPES = (EventType.TRADE, EventType.BAR, EventType.FUNDING)


def _make(etype, i: int, recv: int):
    if etype is EventType.TRADE:
        return TradeEvent(received_time_ns=recv, price=100.0 + i, size=1.0, side="buy")
    if etype is EventType.BAR:
        return BarEvent(received_time_ns=recv, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
    return FundingEvent(received_time_ns=recv, rate=0.0001 * (i + 1))


def _run(seed: int) -> dict:
    rng = random.Random(seed)
    limit = rng.choice([1, 2, 3])
    recv = T0
    events = []
    for i in range(rng.randint(5, 25)):
        recv += rng.choice([0, SEC, SEC, 2 * SEC])
        events.append(_make(rng.choice(TYPES), i, recv))
    found = {"checked": 0, "silent_short": [], "wrong": [], "place_wrong": []}
    full: list = []  # (seq, type, recv) of every delivered event
    kept: dict = {t: [] for t in TYPES}

    class Reader:
        def on_event(self, event, ctx):
            seq, etype, r = event.seq, event.EVENT_TYPE, event.received_time_ns
            if len(kept[etype]) >= 2 * limit:  # the documented rule
                del kept[etype][: len(kept[etype]) - (limit - 1)]
            kept[etype].append(seq)
            full.append((seq, etype, r))
            keep = {s for t in TYPES for s in kept[t]}
            times = sorted({x[2] for x in full})
            picks = [None] + [v for t in times for v in (t - 1, t, t + 1) if v <= ctx.now_ns]
            for et in (None, *TYPES):
                for n in (None, 0, 1, 2, 3, 5):
                    for since in rng.sample(picks, min(4, len(picks))):
                        for until in rng.sample(picks, min(4, len(picks))):
                            scope = [x for x in full if et is None or x[1] is et]
                            want = [x for x in scope
                                    if (since is None or x[2] >= since) and (until is None or x[2] <= until)]
                            if n is not None:
                                want = want[max(0, len(want) - n):] if n else []
                            case = (seed, limit, seq, et, n, since, until)
                            try:
                                got = ctx.visible_events(et, n, since_ns=since, until_ns=until)
                            except HistoryTruncatedError:
                                continue
                            found["checked"] += 1
                            seqs = [e.seq for e in got]
                            if any(x[0] not in keep for x in want):
                                found["silent_short"].append((case, [x[0] for x in want], seqs))
                            elif seqs != [x[0] for x in want]:
                                found["wrong"].append((case, [x[0] for x in want], seqs))
                            elif seqs:
                                kscope = [x[0] for x in scope if x[0] in keep]
                                exp = (kscope.index(seqs[0]), 1, len(kscope),
                                       sum(1 for x in scope if x[0] < kscope[0]))
                                if tuple(got.place) != exp:
                                    found["place_wrong"].append((case, tuple(got.place), exp))

    CoreEngine(Reader(), events, history_limit=limit).run()
    return found


@pytest.mark.parametrize("seed", range(1, 13))
def test_a_read_under_history_limit_is_the_no_limit_answer_or_refused(seed):
    found = _run(seed)
    assert found["checked"] > 0
    assert not found["silent_short"], found["silent_short"][:3]
    assert not found["wrong"], found["wrong"][:3]
    assert not found["place_wrong"], found["place_wrong"][:3]
