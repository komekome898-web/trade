"""Critic, item 0, round 2, finding i0-r2-03 -- rewritten by the round-3 critic.

Round 2: with `history_limit`, the overall history and the per-type
histories were trimmed on independent schedules, so `visible_events(T)` and
"`visible_events()` filtered by T" disagreed, and neither said it was cut.

Why rewritten (rule 8 of the battery rules): the round-2 test called
`ctx.visible_events()` unguarded. The round-3 core refuses a read that
reaches into a dropped part with `HistoryTruncatedError` -- the behaviour
the finding asked for ("neither answer says it was cut"). The old test then
failed on that refusal, not on a disagreement: an error of the test, not of
the core. The property is restated so that it can fail only on the defect:

* whenever both reads of the same window are answered, the typed read
  equals the overall read filtered by type;
* every answered read equals the same read in a run without the limit;
* reads that a limit of N can always answer -- the last n <= N events,
  overall or of one type -- are never refused (a core that refused
  everything would pass the first two points).
"""
from __future__ import annotations

import random

from bot.bt.core import (
    BarEvent,
    CoreEngine,
    EventType,
    FundingEvent,
    HistoryTruncatedError,
    Strategy,
    TradeEvent,
)

MS = 1_000_000
TYPES = (EventType.BAR, EventType.TRADE, EventType.FUNDING)


def _input(rng: random.Random, n: int = 150) -> list:
    out, t = [], 1_700_006_400_000_000_000
    for _ in range(n):
        t += rng.choice([0, 1, 2]) * MS
        r = rng.random()
        if r < 0.7:
            out.append(TradeEvent(received_time_ns=t, price=1.0, size=1.0, side="buy"))
        elif r < 0.92:
            out.append(BarEvent(received_time_ns=t, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0))
        else:
            out.append(FundingEvent(received_time_ns=t, rate=0.0))
    return out


class _Compare(Strategy):
    def __init__(self, seed: int, limit) -> None:
        self.seed, self.limit = seed, limit
        self.answers: list = []
        self.problems: list = []

    def on_event(self, event, ctx) -> None:
        rng = random.Random(self.seed * 7919 + event.seq)
        now = int(ctx.now_ns)
        for _ in range(5):
            since = rng.choice([None, now - rng.choice([0, 2, 10, 60]) * MS])
            until = rng.choice([None, now, now - rng.choice([1, 5, 20]) * MS])
            if since is not None and until is not None and until < since:
                until = None
            for etype in TYPES:
                try:
                    typed = tuple(e.seq for e in ctx.visible_events(etype, since_ns=since, until_ns=until))
                except HistoryTruncatedError:
                    typed = "refused"
                try:
                    overall = tuple(e.seq for e in ctx.visible_events(since_ns=since, until_ns=until)
                                    if e.EVENT_TYPE is etype)
                except HistoryTruncatedError:
                    overall = "refused"
                self.answers.append((event.seq, etype.value, since, until, typed, overall))
                if typed != "refused" and overall != "refused" and typed != overall:
                    self.problems.append(("typed != filtered overall", event.seq, etype.value, typed, overall))
        if self.limit is not None:
            for n in sorted({1, self.limit}):
                for etype in (None,) + TYPES:
                    try:
                        ctx.visible_events(etype, n)
                    except HistoryTruncatedError as exc:
                        self.problems.append(("last n <= limit refused", event.seq, n,
                                              None if etype is None else etype.value, str(exc)[:80]))


def test_typed_view_equals_filtered_overall_view_under_history_limit():
    problems, answered_after_drop = [], 0
    for seed in range(25):
        events = _input(random.Random(seed))
        full = _Compare(seed, None)
        CoreEngine(full, events).run()
        assert full.problems == []
        for limit in (1, 2, 5):
            lim = _Compare(seed, limit)
            eng = CoreEngine(lim, events, history_limit=limit)
            eng.run()
            problems += [(seed, limit) + p for p in lim.problems]
            for a, b in zip(lim.answers, full.answers):
                assert a[:4] == b[:4]
                for got, want in ((a[4], b[4]), (a[5], b[5])):
                    if got != "refused":
                        if got != want:
                            problems.append((seed, limit, "answer != unlimited", a[:4], got, want))
                        elif eng.result().events_processed > 2 * limit:
                            answered_after_drop += 1
    assert answered_after_drop > 1000  # answered reads were exercised after drops
    assert problems == [], f"{len(problems)} problems; first: {problems[:3]}"
