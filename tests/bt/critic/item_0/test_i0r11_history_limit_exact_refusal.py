"""Critic, item 0, round 11: re-check of i0-r9-01 (fixed in round 10) with an
oracle written from the contract's words only (visibility.history_limit):
"a read raises HistoryTruncatedError exactly when its answer without the
limit holds a dropped event ...; every answer returned, empty or not, is the
answer without the limit; its place is in the kept events of its scope with
the dropped deliveries before the oldest kept one at -dropped..-1; an empty
answer lies where its range was cut on that line".

Unlike round 9's test, this one also counts refusals of reads whose no-limit
answer is kept whole (over-refusal) and checks the place of EMPTY answers.
Retention (history.py): per type, at 2N held, the oldest are dropped down to
N-1, then the new one is kept.

Grid: 1-4 of {trade, bar, funding, clock-free market types} in one stream,
bursts of equal received times, N in {1..4}, up to 40 events, 10 seeds; at
every callback every event_type in {None, each type seen} x n in {None, 0, 1,
2, 3, 5, 9} x 3 sampled since_ns x 3 sampled until_ns (received times +-1 ns
and None). Not in the grid: notices and timers in the history, feed delays.
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import (BarEvent, CoreEngine, FundingEvent, HistoryTruncatedError, LiquidationEvent,
                         TradeEvent)

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


def _make(k: int, i: int, recv: int):
    if k == 0:
        return TradeEvent(received_time_ns=recv, price=100.0 + i, size=1.0, side="buy")
    if k == 1:
        return BarEvent(received_time_ns=recv, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
    if k == 2:
        return FundingEvent(received_time_ns=recv, rate=0.0001 * (i + 1))
    return LiquidationEvent(received_time_ns=recv, price=100.0, size=1.0, side="sell")


@pytest.mark.parametrize("seed", range(2001, 2011))
def test_history_reads_under_the_limit_are_the_no_limit_answer_or_refused_exactly(seed):
    rng = random.Random(seed)
    limit = rng.choice([1, 2, 3, 4])
    kinds = rng.sample([0, 1, 2, 3], rng.choice([1, 2, 3, 4]))
    recv, events = T0, []
    for i in range(rng.randint(5, 40)):
        recv += rng.choice([0, 0, SEC, 2 * SEC])
        events.append(_make(rng.choice(kinds), i, recv))
    full: list = []
    kept: dict = {}
    bad: list = []
    counts = {"reads": 0, "refused": 0}

    class S:
        def on_event(self, ev, ctx):
            held = kept.setdefault(ev.EVENT_TYPE, [])
            if len(held) >= 2 * limit:
                del held[:len(held) - (limit - 1)]
            held.append(ev.seq)
            full.append((ev.seq, ev.EVENT_TYPE, ev.received_time_ns))
            keptset = {s for v in kept.values() for s in v}
            recvs = sorted({x[2] for x in full})
            cands = [None] + [t for v in recvs for t in (v - 1, v, v + 1) if t <= ctx.now_ns]
            for et in [None] + sorted({x[1] for x in full}, key=lambda e: e.value):
                scope = [x for x in full if et is None or x[1] is et]
                kscope = [x for x in scope if x[0] in keptset]
                before = [x for x in scope if x[0] < kscope[0][0]]
                for n in (None, 0, 1, 2, 3, 5, 9):
                    for since in rng.sample(cands, min(3, len(cands))):
                        for until in rng.sample(cands, min(3, len(cands))):
                            a = [x for x in scope if (since is None or x[2] >= since)
                                 and (until is None or x[2] <= until)]
                            if n is not None:
                                a = a[len(a) - n:] if 0 < n < len(a) else (a if n else [])
                            reaches = any(x[0] not in keptset for x in a)
                            counts["reads"] += 1
                            try:
                                got = ctx.visible_events(et, n, since_ns=since, until_ns=until)
                            except HistoryTruncatedError:
                                counts["refused"] += 1
                                if not reaches:
                                    bad.append(("over-refused", et, n, since, until))
                                continue
                            if reaches:
                                bad.append(("silently short", et, n, since, until))
                                continue
                            seqs = [e.seq for e in got]
                            if seqs != [x[0] for x in a]:
                                bad.append(("wrong", et, n, since, until, seqs))
                                continue
                            if seqs:
                                want = ([x[0] for x in kscope].index(seqs[0]), 1, len(kscope), len(before))
                            else:
                                line = before + kscope
                                cut = len(line) if until is None else sum(1 for x in line if x[2] <= until)
                                want = (cut - len(before), 1, len(kscope), len(before))
                            p = got.place
                            if (p.first, p.step, p.delivered, p.dropped) != want:
                                bad.append(("place", et, n, since, until, tuple(p), want))

    CoreEngine(S(), events, history_limit=limit).run()
    assert counts["reads"] > 0 and (counts["refused"] > 0 or len(full) <= 2 * limit), counts
    assert bad == [], bad[:5]
