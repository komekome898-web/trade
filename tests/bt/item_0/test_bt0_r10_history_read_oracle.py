"""Round 10 (i0-r9-01): a history read under `history_limit` is refused
EXACTLY when the answer the same read gives without the limit contains an
event the limit dropped -- never more, never less -- and an answer that is
returned, empty or not, is the unlimited answer at its place. Written
BEFORE the fix (lead design round_7/LEAD_DESIGN.md s3.3).

The oracle is built from the rule's text only (the contract's
`visibility.history_limit` and `window.AnswerPlace`), never from the
implementation's case split:

* retention: per event type the latest N..2N delivered events are kept
  (when a type holds 2N, its oldest are dropped down to N-1, then the new
  one is appended); the overall history is what the types keep;
* the unlimited answer of a read (type or all, since_ns <= received <=
  until_ns, then the last n) is computed from every delivered event;
* the read must raise HistoryTruncatedError iff that answer holds a dropped
  event; the error names the newest dropped event the read asks for
  (`delivery #<seq>`, `received at <t>`) and, when the read's newest events
  after it are all kept, how many (`n <= <m>`);
* a returned answer equals the unlimited one; its place is in "what the
  read reads" = the kept events of its scope, with the `dropped` scope
  deliveries before the oldest kept one at positions -dropped..-1: a
  non-empty answer's `first` is its first event's index among the kept
  ones; an empty answer lies where its range was cut: on the line (dropped
  prefix, then kept), `first` = (how many of the line were received at or
  before until_ns, or the whole line without until_ns) - dropped.

The grid (every axis in full): input seed x history_limit {1, 2, 3} x the
callback x event_type {None, TRADE, BAR, FUNDING} x n {None, 0, 1, 2, 3, 5,
50} x since_ns x until_ns, each time in {None} + {t-1, t, t+1 for every
distinct received time t so far, not after now}. The cell count is computed
and printed by each test (-s) and asserted to be under 100,000 per test
function (LEAD_DESIGN s7.2 12: then every cell is run); one seed per test
function (12 seeds) so that holds.

NOT in the grid (A-10): event types other than the three (the rule is per
type and does not name a type); reads with since_ns > until_ns are in the
grid (they are just empty); history_limit > 3 (a larger N only moves when
the first drop happens); callbacks for notices (the input has market events
only; the retention rule does not look at the kind of a type).
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import BarEvent, CoreEngine, EventType, FundingEvent, HistoryTruncatedError, TradeEvent

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000
TYPES = (EventType.TRADE, EventType.BAR, EventType.FUNDING)
NS = (None, 0, 1, 2, 3, 5, 50)
LIMITS = (1, 2, 3)
SEED_GROUPS = {f"s{i}": (i,) for i in range(1, 13)}  # one seed per test function


def _make(t: EventType, i: int, recv: int):
    if t is EventType.TRADE:
        return TradeEvent(received_time_ns=recv, price=100.0 + i, size=1.0, side="buy")
    if t is EventType.BAR:
        return BarEvent(received_time_ns=recv, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
    return FundingEvent(received_time_ns=recv, rate=0.0001 * (i + 1))


def _input(seed: int, limit: int) -> list:
    """Enough events of one type that it drops (2N + 1 of them is the
    first drop), a few of the others, times with ties."""
    rng = random.Random(seed * 10 + limit)
    recv = T0
    out = []
    kinds = [rng.choice(TYPES) for _ in range(2 * limit + 1)] + [rng.choice(TYPES) for _ in range(3)]
    kinds[: 2 * limit + 1] = [kinds[0]] * (2 * limit + 1)  # one type drops at least once
    rng.shuffle(kinds)
    for i, kind in enumerate(kinds):
        recv += rng.choice([0, 0, SEC, 2 * SEC])
        out.append(_make(kind, i, recv))
    return out


def _times(delivered: list, now: int) -> list:
    distinct = sorted({r for _s, _t, r in delivered})
    out = [None]
    for r in distinct:
        for x in (r - 1, r, r + 1):
            if x <= now and x not in out:
                out.append(x)
    return out


def _oracle(delivered, kept, et, n, since, until):
    """(the unlimited answer as [(seq, type, recv)], whether it holds a
    dropped event, the expected place of a returned answer)."""
    scope = [x for x in delivered if et is None or x[1] is et]
    rng_ = [x for x in scope if (since is None or x[2] >= since) and (until is None or x[2] <= until)]
    ans = rng_ if n is None else (rng_[max(0, len(rng_) - n):] if n else [])
    reaches = any(x[0] not in kept for x in ans)
    kept_scope = [x for x in scope if x[0] in kept]
    oldest = kept_scope[0][0] if kept_scope else None
    prefix = [x for x in scope if oldest is not None and x[0] < oldest] if kept_scope else list(scope)
    d = len(prefix)
    if reaches:
        return ans, reaches, None
    if ans:
        first = [x[0] for x in kept_scope].index(ans[0][0])
    else:
        line = prefix + kept_scope
        c = len(line) if until is None else sum(1 for x in line if x[2] <= until)
        first = c - d
    return ans, reaches, (first, 1, len(kept_scope), d)


def _run_one(seed: int, limit: int, problems: list, counts: dict) -> None:
    events = _input(seed, limit)
    delivered: list = []  # (seq, type, recv) of every delivered event
    kept_by_type = {t: [] for t in TYPES}

    class S:
        def on_event(self, ev, ctx):
            seq, t, r = ev.seq, ev.EVENT_TYPE, ev.received_time_ns
            if len(kept_by_type[t]) >= 2 * limit:  # the retention rule, from its text
                del kept_by_type[t][:len(kept_by_type[t]) - (limit - 1)]
            kept_by_type[t].append(seq)
            delivered.append((seq, t, r))
            kept = {s for lst in kept_by_type.values() for s in lst}
            times = _times(delivered, ctx.now_ns)
            for et in (None, *TYPES):
                for n in NS:
                    for since in times:
                        for until in times:
                            counts["cells"] += 1
                            ans, reaches, place = _oracle(delivered, kept, et, n, since, until)
                            where = (seed, limit, seq, et and et.value, n, since and since - T0,
                                     until and until - T0)
                            try:
                                got = ctx.visible_events(et, n, since_ns=since, until_ns=until)
                            except HistoryTruncatedError as exc:
                                counts["refused"] += 1
                                if not reaches:
                                    problems.append(("refused, but the unlimited answer is all kept", where,
                                                     [x[0] for x in ans], str(exc)[:200]))
                                    continue
                                newest = max(x for x in ans if x[0] not in kept)
                                m = sum(1 for x in ans if x[0] > newest[0])
                                text = str(exc)
                                want = [f"delivery #{newest[0]} ", f"received at {newest[2]})"]
                                if m:
                                    want.append(f"n <= {m}")
                                missing = [w for w in want if w not in text]
                                if missing:
                                    problems.append(("refusal text", where, missing, text[:300]))
                                continue
                            counts["answered"] += 1
                            if reaches:
                                problems.append(("answered, but the unlimited answer holds a dropped event",
                                                 where, [x[0] for x in ans], [e.seq for e in got]))
                                continue
                            if [e.seq for e in got] != [x[0] for x in ans]:
                                problems.append(("answer differs", where, [x[0] for x in ans],
                                                 [e.seq for e in got]))
                                continue
                            if tuple(got.place) != place:
                                problems.append(("place differs", where, place, tuple(got.place)))
                                continue
                            if not ans:
                                counts["empty"] += 1

    CoreEngine(S(), events, history_limit=limit).run()


@pytest.mark.parametrize("limit", LIMITS)
@pytest.mark.parametrize("group", sorted(SEED_GROUPS))
def test_a_read_is_refused_exactly_when_its_unlimited_answer_holds_a_dropped_event(group, limit):
    problems: list = []
    counts = {"cells": 0, "refused": 0, "answered": 0, "empty": 0}
    for seed in SEED_GROUPS[group]:
        _run_one(seed, limit, problems, counts)
    print(f"\n[{group} L={limit}] {counts}")
    assert counts["cells"] < 100_000  # every cell was run (LEAD_DESIGN s7.2 12)
    assert counts["refused"] and counts["answered"] and counts["empty"]  # every branch was exercised
    assert not problems, "\n".join(map(str, problems[:12])) + f"\n... {len(problems)} in all"


def test_the_critic_scene_reads_that_hold_no_dropped_event_are_answered():
    """i0-r9-01's input: history_limit=1, bars @1s and 2s, funding @5s, 6s,
    7s (funding drops 5s and 6s). At the 5th callback: until_ns=T0+3s ->
    [1, 2]; n=1 with it -> [2]; until_ns=T0 (before every event) -> [] placed
    before everything (first = -dropped of the whole history = 0 here: the
    two dropped funding events come after the kept bars)."""
    def bar(t):
        return BarEvent(received_time_ns=t, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)

    evs = [bar(T0 + SEC), bar(T0 + 2 * SEC)] + [FundingEvent(received_time_ns=T0 + s * SEC, rate=0.0001)
                                                for s in (5, 6, 7)]
    out = {}

    class S:
        def on_event(self, ev, ctx):
            if ev.seq != 5:
                return
            a = ctx.visible_events(until_ns=T0 + 3 * SEC)
            b = ctx.visible_events(n=1, until_ns=T0 + 3 * SEC)
            c = ctx.visible_events(until_ns=T0)
            out.update(a=([e.seq for e in a], tuple(a.place)), b=([e.seq for e in b], tuple(b.place)),
                       c=([e.seq for e in c], tuple(c.place)))
            ctx.visible_events(EventType.FUNDING, until_ns=T0 + 5 * SEC + 1)

    with pytest.raises(HistoryTruncatedError) as err:
        CoreEngine(S(), evs, history_limit=1).run()
    # the funding read up to 5s+1ns asks for #3, which was dropped: refused, naming it
    assert "delivery #3 " in str(err.value)
    assert out["a"] == ([1, 2], (0, 1, 3, 0))
    assert out["b"] == ([2], (1, 1, 3, 0))
    assert out["c"] == ([], (0, 1, 3, 0))
