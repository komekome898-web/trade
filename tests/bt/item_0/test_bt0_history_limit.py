"""history_limit has ONE retention rule (i0-r2-03, history.py).

Per type the latest N..2N delivered events are kept; the overall history is
exactly what the types keep. A read is either answered with the same answer
as a run without the limit, or refused with HistoryTruncatedError -- and it
is refused only when its window reaches into a dropped part."""
import random

import pytest

from bot.bt.core import (
    CoreEngine,
    EventType,
    FundingEvent,
    HistoryTruncatedError,
    OrderApiError,
    Strategy,
)

from bt0_util import MS, T0, Recorder, bar, trade

TYPES = (None, EventType.TRADE, EventType.BAR, EventType.FUNDING)


def funding(t: int) -> FundingEvent:
    return FundingEvent(received_time_ns=t, rate=0.0001)


def _mixed_input(rng: random.Random, n: int = 160) -> list:
    out, t = [], T0
    for _ in range(n):
        t += rng.choice([0, 1, 1, 2]) * MS
        r = rng.random()
        if r < 0.75:
            out.append(trade(t, 100.0))
        elif r < 0.93:
            out.append(bar(t, 100.0))
        else:
            out.append(funding(t))
    return out


class _Asker(Strategy):
    """At each callback asks a list of reads drawn from rng(seed, seq), so a
    limited and an unlimited run ask exactly the same reads."""

    def __init__(self, seed: int, engine_ref: list) -> None:
        self.seed = seed
        self.engine_ref = engine_ref
        self.answers: list = []  # (seq, query, answer seqs | "refused", dropped facts)

    def on_event(self, event, ctx) -> None:
        rng = random.Random(self.seed * 100_003 + event.seq)
        now = int(ctx.now_ns)
        eng = self.engine_ref[0] if self.engine_ref else None
        dropped = dict(eng._history.dropped) if eng is not None else {}
        for _ in range(6):
            etype = rng.choice(TYPES)
            since = rng.choice([None, None, now - rng.choice([0, 1, 5, 20, 80]) * MS])
            until = rng.choice([None, None, now, now - rng.choice([0, 3, 30]) * MS])
            if since is not None and until is not None and until < since:
                until = None
            n = rng.choice([None, None, 0, 1, 3, 7, 25])
            query = (etype, since, until, n)
            try:
                got = tuple(e.seq for e in ctx.visible_events(etype, n, since_ns=since, until_ns=until))
            except HistoryTruncatedError:
                got = "refused"
            self.answers.append((event.seq, query, got, dropped))
            # the typed view and the overall view filtered by type agree
            # whenever both answer (same window, no n)
            if etype is not None:
                try:
                    typed = ctx.visible_events(etype, since_ns=since, until_ns=until)
                    overall = ctx.visible_events(since_ns=since, until_ns=until)
                except HistoryTruncatedError:
                    continue
                assert list(typed) == [e for e in overall if e.EVENT_TYPE is etype]


def _run(events, seed, limit):
    ref = []
    strat = _Asker(seed, ref)
    eng = CoreEngine(strat, events, history_limit=limit)
    ref.append(eng)
    eng.run()
    return strat.answers, eng


def test_limited_reads_equal_unlimited_reads_or_are_refused_for_a_reason():
    refused = answered_after_drop = 0
    for seed in range(40):
        events = _mixed_input(random.Random(seed))
        full, _ = _run(events, seed, None)
        for limit in (1, 2, 3, 8):
            lim, eng = _run(events, seed, limit)
            assert len(lim) == len(full)
            for (seq, query, got, dropped), (seq_f, query_f, want, _) in zip(lim, full):
                assert (seq, query) == (seq_f, query_f)
                assert want != "refused"  # nothing is dropped without a limit
                etype, since, _until, _n = query
                covered = {t: d for t, d in dropped.items() if etype is None or t is etype}
                if got == "refused":
                    refused += 1
                    # refused only when the window reaches into a dropped part
                    assert any(since is None or since <= recv for _seq, recv in covered.values()), (
                        seed, limit, seq, query, covered)
                else:
                    if covered:
                        answered_after_drop += 1
                    assert got == want, (seed, limit, seq, query, got, want)
            # memory bound: per type at most 2N kept, overall = what the types keep
            h = eng._history
            assert all(len(lst) <= 2 * limit for lst in h.typed.values())
            assert sorted(e.seq for e in h.overall) == sorted(e.seq for lst in h.typed.values() for e in lst)
    assert refused > 0 and answered_after_drop > 0  # both branches were exercised


def test_critic_scene_bar_then_trades_limit_3():
    """The input of the round 2 finding: one bar then nine trades, limit 3."""
    events = [bar(1 * MS, 1.0)] + [trade((2 + i) * MS, 1.0) for i in range(9)]
    seen = []

    def act(ev, ctx):
        bars = ctx.visible_events(EventType.BAR)
        last3 = ctx.visible_events(EventType.TRADE, n=3)
        try:
            overall = ctx.visible_events()
        except HistoryTruncatedError:
            overall = None
        seen.append((ev.seq, [b.seq for b in bars], [t.seq for t in last3], overall))

    CoreEngine(Recorder(act), events, history_limit=3).run()
    for seq, bars, last3, overall in seen:
        assert bars == [1]  # the bar is never dropped: its type kept it
        assert last3 == [s for s in range(max(2, seq - 2), seq + 1)]
        if overall is not None:  # answered only while nothing was dropped
            assert [e.seq for e in overall] == list(range(1, seq + 1))
    assert any(o is None for *_, o in seen)  # after the first drop the full read is refused


def test_since_before_the_kept_part_is_refused_and_after_it_is_answered():
    events = [trade(T0 + i * MS) for i in range(20)]
    probe = {}

    def act(ev, ctx):
        if ev.seq == 20:
            with pytest.raises(HistoryTruncatedError):
                ctx.visible_events(since_ns=T0)
            probe["tail"] = [e.seq for e in ctx.visible_events(since_ns=T0 + 17 * MS)]

    eng = CoreEngine(Recorder(act), events, history_limit=4)
    eng.run()
    assert probe["tail"] == [18, 19, 20]


def test_a_rare_type_stays_readable_after_a_flood_of_another_type():
    events = [funding(T0)] + [trade(T0 + (1 + i) * MS) for i in range(200)]
    probe = {}

    def act(ev, ctx):
        if ev.seq == 201:
            probe["last_funding"] = ctx.last(EventType.FUNDING)
            probe["all_funding"] = ctx.visible_events(EventType.FUNDING)

    CoreEngine(Recorder(act), events, history_limit=5).run()
    assert probe["last_funding"].seq == 1
    assert [e.seq for e in probe["all_funding"]] == [1]


def test_count_argument_is_checked_in_one_place():
    got = {}

    def act(ev, ctx):
        got["zero"] = ctx.visible_events(n=0)
        for bad in (-1, -5, 1.0, True):
            with pytest.raises(OrderApiError):
                ctx.visible_events(n=bad)

    CoreEngine(Recorder(act), [trade(T0)]).run()
    assert got["zero"] == ()
