"""P0-4 by position: a history read returns `DeliveredEvents`, where naming
a position after the last event of the answer -- by an index or by an
explicit non-negative slice bound, whatever the bound's role -- raises
`FuturePositionError` (an IndexError and a LookAheadError) instead of a
silently shortened or empty answer, as a time argument after now does.
Scene p4-future-read-attempt: "空・切り詰め … は素通り".

Round 6 (i0-r5-05) gave an answer ONE fact about the position after its
last event, and chose the error for EVERY outside position from it; round
7 (i0-r6-01): an answer past its end names, further out, events not
delivered yet, and a backward answer's negative index names the newer
side. An answer now knows its place in what the read reads
(`AnswerPlace`: answer position q is position first + q * step there;
`delivered` of those had been delivered), and the error follows from the
NAMED position: not delivered yet -> FuturePositionError (a
LookAheadError); delivered, outside -> OutsideAnswerError; before the
oldest -> DroppedPositionError (history_limit dropped it) or
BeforeFirstEventError (nothing there). The engine-level checks decide what
a named position is from the INPUT and the callback time (which input
events of the selection had been received by now), not from the core.

Round 5 (i0-r4-01): `[4:]` at the 4th bar returned () -- the rule was a
list of per-form inequalities and this file's oracle copied them. The
oracle here does NOT read the core's rule: it probes a plain tuple (an
inclusive bound must name an element that is there; the end of a forward
slice may be the end of the answer, `plain[:stop]` not cut short), and it
is compared on EVERY slice with bounds None / -9..9 and steps
None / +-1 / +-2 / +-3 over answers of 0..6 events (enumerated, not
sampled). A second, rule-free check: a read that is answered gives the
same answer in a world where more events were delivered after these.
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.core import (
    CORE_CONTRACT,
    POSITION_RULE,
    AnswerPlace,
    BeforeFirstEventError,
    CoreEngine,
    DeliveredEvents,
    DroppedPositionError,
    EventType,
    FuturePositionError,
    HistoryTruncatedError,
    LookAheadError,
    OutsideAnswerError,
)

from bt0_util import SEC, T0, Recorder, bar, trade

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


# At the 4th bar the answer holds bars 100..103 at positions 0..3; position 4
# is the 5th bar, not delivered. Every way below names position 4 (or later):
# an index, the first position a forward slice reads, the end of a forward
# slice past the end, the first position a backward slice reads, the old-side
# end of a backward slice, and a slice of a slice.
@pytest.mark.parametrize("name, read", [
    ("[4]", lambda ctx: ctx.visible_events(BAR)[4]),
    ("all [4]", lambda ctx: ctx.visible_events()[4]),
    ("n=5 [4]", lambda ctx: ctx.visible_events(BAR, n=5)[4]),
    ("[4:5]", lambda ctx: ctx.visible_events(BAR)[4:5]),
    ("[3:5]", lambda ctx: ctx.visible_events(BAR)[3:5]),
    ("[:5]", lambda ctx: ctx.visible_events(BAR)[:5]),
    ("[5:]", lambda ctx: ctx.visible_events(BAR)[5:]),
    ("[4:]", lambda ctx: ctx.visible_events(BAR)[4:]),
    ("all [4:]", lambda ctx: ctx.visible_events()[4:]),
    ("[4::]", lambda ctx: ctx.visible_events(BAR)[4::]),
    ("[4::2]", lambda ctx: ctx.visible_events(BAR)[4::2]),
    ("[len:]", lambda ctx: ctx.visible_events(BAR)[len(ctx.visible_events(BAR)):]),
    ("[4:4]", lambda ctx: ctx.visible_events(BAR)[4:4]),
    ("[0:100:2]", lambda ctx: ctx.visible_events(BAR)[0:100:2]),
    ("[4::-1]", lambda ctx: ctx.visible_events(BAR)[4::-1]),
    ("[:4:-1]", lambda ctx: ctx.visible_events(BAR)[:4:-1]),
    ("[9:2:-1]", lambda ctx: ctx.visible_events(BAR)[9:2:-1]),
    ("[1:][3]", lambda ctx: ctx.visible_events(BAR)[1:][3]),
    ("[1:][:4]", lambda ctx: ctx.visible_events(BAR)[1:][:4]),
    ("[1:][3:]", lambda ctx: ctx.visible_events(BAR)[1:][3:]),
])
def test_naming_a_position_after_the_newest_is_refused(name, read):
    exc = _raises(read)
    assert isinstance(exc, FuturePositionError), f"{name} was answered, not refused"
    assert isinstance(exc, IndexError) and isinstance(exc, LookAheadError)


def test_reads_within_the_delivered_positions_answer_as_a_tuple():
    def reads(ctx):
        bars = ctx.visible_events(BAR)
        return {
            "type": isinstance(bars, DeliveredEvents) and bars.next_is_undelivered,
            "all": [b.close for b in bars],
            "last": bars[-1].close,
            "first": bars[0].close,
            "head": [b.close for b in bars[:4]],  # the end of a forward slice may be len
            "tail2": [b.close for b in bars[-2:]],
            "from_newest": [b.close for b in bars[3:]],
            "newer_than_newest": [b.close for b in bars[:3:-1]],  # names position 3 (delivered): nothing
            "empty_at_newest": [b.close for b in bars[3:3]],
            "past_clamp": [b.close for b in bars[-10:]],
            "reverse": [b.close for b in bars[::-1]],
            "eq_tuple": bars == tuple(bars),
        }
    got = _reads_at_fourth_bar(reads)
    assert got["type"] is True
    assert got["all"] == [100.0, 101.0, 102.0, 103.0]
    assert got["last"] == 103.0 and got["first"] == 100.0
    assert got["head"] == got["all"] and got["tail2"] == [102.0, 103.0]
    assert got["from_newest"] == [103.0]
    assert got["newer_than_newest"] == [] and got["empty_at_newest"] == []
    assert got["past_clamp"] == got["all"]
    assert got["reverse"] == [103.0, 102.0, 101.0, 100.0] and got["eq_tuple"] is True


def test_negative_index_before_the_oldest_is_before_the_first_event():
    """At the 4th bar, `[-5]` names the position before the first bar ever
    delivered: nothing is there, which is the past, not the future."""
    def read(ctx):
        try:
            ctx.visible_events(BAR)[-5]
        except FuturePositionError:
            return "future"
        except BeforeFirstEventError as exc:
            return ("nothing", exc.answer_position, exc.read_position, exc.delivered)
    assert _reads_at_fourth_bar(read) == ("nothing", -1, -1, 4)


# -- the rule, checked against an oracle that does not read the core -------

def _outside_positions(n: int, key) -> list[int]:
    """Probe a plain tuple of n elements: the answer positions a key names
    outside the answer, one per refused bound. An index must name an
    element that is there (a negative one counts from the newest). A
    slice's start, and the old-side end of a backward slice (its stop,
    the element just before the range), must name an element that is
    there; the end of a forward slice (its stop, not read) names the
    position before it, so it may be the end of the answer, and
    `plain[:stop]` must not be cut short. Negative slice bounds are cut
    (as for any tuple) and name nothing outside."""
    plain = tuple(range(n))

    def is_there(p: int) -> bool:
        try:
            plain[p]
        except IndexError:
            return False
        return True

    if isinstance(key, int):
        return [] if is_there(key) else [key if key >= 0 else key + n]
    step = 1 if key.step is None else key.step
    out = []
    if key.start is not None and key.start >= 0 and not is_there(key.start):
        out.append(key.start)
    if key.stop is not None and key.stop >= 0:
        if step < 0 and not is_there(key.stop):
            out.append(key.stop)
        if step > 0 and len(plain[:key.stop]) != key.stop:
            out.append(key.stop - 1)
    return out


_BOUNDS = [None] + list(range(-9, 10))
_STEPS = [None, 1, 2, 3, -1, -2, -3]


def _all_keys():
    for i in range(-9, 10):
        yield i
    for start, stop, step in itertools.product(_BOUNDS, _BOUNDS, _STEPS):
        yield slice(start, stop, step)


def _what_is_there(u: int, delivered: int, dropped: int) -> type:
    """What a position of the read's list is, from the list itself: at or
    after the delivered count, not delivered yet; inside, a delivered
    event; before it, one of the `dropped` ones, then nothing."""
    world = ["nothing"] * 50 + ["dropped"] * dropped + ["kept"] * delivered + ["future"] * 50
    what = world[u + 50 + dropped]
    return {"nothing": BeforeFirstEventError, "dropped": DroppedPositionError,
            "kept": OutsideAnswerError, "future": FuturePositionError}[what]


# places of an answer of n events in a read's list of `delivered`: at the
# newest, cut in the past, stepped, backward, with and without a drop
def _places(n: int):
    yield "newest", 3, 1, n + 3, 0
    yield "past", 1, 1, n + 6, 0
    yield "past-dropped", 0, 1, n + 2, 4
    yield "stepped", 1, 2, 2 * n + 3, 0
    yield "stepped-dropped", 2, 3, 3 * n + 3, 5
    yield "backward-newest", n + 1, -1, n + 2, 0
    yield "backward-past", n + 2, -1, n + 5, 3
    yield "backward-stepped", 3 * n, -3, 3 * n + 1, 0


@pytest.mark.parametrize("n", range(0, 7))
def test_every_index_and_slice_matches_the_probe_oracle(n):
    checked = refused = 0
    for label, first, step, delivered, dropped in _places(n):
        world = [first + i * step for i in range(n)]  # each item is its own position in the read
        seq = DeliveredEvents(world, first=first, step=step, delivered=delivered, dropped=dropped)
        for key in _all_keys():
            checked += 1
            named = _outside_positions(n, key)
            if named:
                kinds = [_what_is_there(first + q * step, delivered, dropped) for q in named]
                want = FuturePositionError if FuturePositionError in kinds else kinds[0]
                with pytest.raises(IndexError) as info:
                    seq[key]
                assert type(info.value) is want, (label, key, type(info.value).__name__, want.__name__)
                assert isinstance(info.value, LookAheadError) is (want is FuturePositionError)
                refused += 1
                continue
            if isinstance(key, int):
                assert seq[key] == world[key]
                continue
            out = seq[key]
            assert isinstance(out, DeliveredEvents) and list(out) == world[key], (label, key)
            # the slice's place, read from its own items (each is its position)
            if len(out) >= 1:
                assert out.place.first == out[0], (label, key)
            if len(out) >= 2:
                assert out.place.step == out[1] - out[0], (label, key)
            assert out.place.delivered == delivered and out.place.dropped == dropped
    assert checked == 8 * (19 + 20 * 20 * 7) and refused > 0


def test_a_slice_that_ends_before_the_answer_names_the_past_not_the_future():
    """In an answer of 4 that ends at the newest, `[1:3]` ends at position
    2; its position 2 is the answer's position 3 (delivered). `[1:]`
    reaches the end; its position 3 is not delivered. A backward read's
    position after its last is before the first event (nothing)."""
    ans = DeliveredEvents(range(4), first=0, delivered=4)
    with pytest.raises(OutsideAnswerError) as info:
        ans[1:3][2]
    assert type(info.value) is OutsideAnswerError and not isinstance(info.value, LookAheadError)
    with pytest.raises(FuturePositionError):
        ans[1:][3]
    with pytest.raises(BeforeFirstEventError):
        ans[::-1][4]
    # a backward answer's negative index before its first names the NEWER side
    with pytest.raises(FuturePositionError):
        ans[::-1][-5]
    assert ans[0:4:2].next_is_undelivered is True
    assert ans[0:3:2].next_is_undelivered is True and ans[1:3:2].next_is_undelivered is False
    with pytest.raises(FuturePositionError):
        ans[0:4:2][2]


def test_a_stepped_answer_in_the_past_names_the_future_further_out():
    """The critic's case (i0-r6-01): all[0:6:3] of 10 delivered holds
    positions 0 and 3; its [2] is position 6 (delivered), its [4] is
    position 12 (not delivered)."""
    ans = DeliveredEvents(range(10), first=0, delivered=10)[0:6:3]
    with pytest.raises(OutsideAnswerError) as past:
        ans[2]
    assert type(past.value) is OutsideAnswerError and past.value.read_position == 6
    with pytest.raises(FuturePositionError) as future:
        ans[4]
    assert (future.value.answer_position, future.value.read_position, future.value.delivered) == (4, 12, 10)
    # two bounds outside: the one naming the future is reported
    cut = DeliveredEvents(range(7), first=0, delivered=10)
    with pytest.raises(FuturePositionError):
        cut[8:12]


def test_the_place_cannot_be_left_out_or_changed():
    with pytest.raises(TypeError):
        DeliveredEvents((1, 2))  # the maker states where it lies
    with pytest.raises(TypeError):
        DeliveredEvents((1, 2), first=0, delivered=2.0)
    with pytest.raises(TypeError):
        DeliveredEvents((1, 2), first=0, delivered=2, dropped=True)
    with pytest.raises(ValueError):
        DeliveredEvents((1, 2), first=0, delivered=2, dropped=-1)
    with pytest.raises(ValueError):
        DeliveredEvents((1, 2), first=1, delivered=2)  # position 2 was not delivered
    with pytest.raises(ValueError):
        DeliveredEvents((1, 2), first=0, step=0, delivered=2)
    ans = DeliveredEvents((1, 2), first=3, delivered=9, dropped=4)
    for name in ("place", "_place", "next_is_undelivered", "anything"):
        with pytest.raises(AttributeError):
            setattr(ans, name, None)
    with pytest.raises(AttributeError):
        del ans._place
    import copy
    import pickle
    for clone in (copy.copy(ans), copy.deepcopy(ans), pickle.loads(pickle.dumps(ans))):
        assert clone == ans and clone.place == ans.place == AnswerPlace(3, 1, 9, 4)


def test_a_slice_bound_is_read_once():
    """A bound whose `__index__` answers differently each time it is asked
    must not pass the check with one value and cut with another."""
    class Shifty:
        def __init__(self, values):
            self.values = list(values)

        def __index__(self):
            return self.values.pop(0) if len(self.values) > 1 else self.values[0]

    ans = DeliveredEvents(range(4), first=0, delivered=4)
    # asked first: 2 (inside); asked again: 9 (outside, would give ())
    got = ans[Shifty([2, 9]):]
    assert list(got) == [2, 3]
    with pytest.raises(FuturePositionError):
        ans[Shifty([9, 2]):]


DAY = 86_400 * SEC


def test_a_read_cut_in_the_past_names_delivered_events_outside_it():
    """The critic's case (i0-r5-05): at the 4th daily bar, the answer of
    `until_ns` = day 2 holds 2 bars; its position 2 is the 3rd bar, which
    was delivered. It is refused as outside the answer, not as the
    future."""
    def act(ctx):
        past = ctx.visible_events(BAR, until_ns=T0 + 2 * DAY)
        out = {"closes": [b.close for b in past], "fact": past.next_is_undelivered}
        for name, read in (("[2]", lambda: past[2]), ("[2:]", lambda: past[2:]), ("[:3]", lambda: past[:3])):
            try:
                read()
                out[name] = "answered"
            except IndexError as exc:
                out[name] = (type(exc).__name__, isinstance(exc, LookAheadError))
        return out

    got = {}

    def cb(ev, ctx):
        if ctx.now_ns == T0 + 4 * DAY:
            got.update(act(ctx))

    CoreEngine(Recorder(cb), [bar(T0 + i * DAY, 100.0 + i) for i in range(1, 6)]).run()
    assert got["closes"] == [101.0, 102.0] and got["fact"] is False
    for name in ("[2]", "[2:]", "[:3]"):
        assert got[name] == ("OutsideAnswerError", False), (name, got[name])


_SLICES = (None, slice(None, None, -1), slice(None, None, 2), slice(1, None, 3), (slice(None, None, -1), slice(1, None)))


def _apply(ans, rng_positions, sl):
    """Apply one slice (or a chain of them) to the answer and, with
    Python's own range slicing, to the read positions its items hold."""
    for key in (sl if isinstance(sl, tuple) else (sl,)):
        if key is None:
            continue
        if _outside_positions(len(ans), key):
            return None  # the slice itself names outside the answer (checked elsewhere)
        ans, rng_positions = ans[key], rng_positions[key]
    return ans, rng_positions


def _run_every_naming(events, history_limit=None):
    """At every callback, for reads by type and overall, cut at every
    delivered time and not, with n and since_ns, and slices of them: name
    every position from -len-3 to len+3 and compare the error with what
    the INPUT holds there -- the read's list rebuilt from the input
    events of the selection received by now (zero latency: an input event
    is delivered at its received time), not from the core."""
    checked = 0
    problems: list = []

    def selection(etype, now):
        return [e for e in events if (etype is None or e.EVENT_TYPE is etype) and e.received_time_ns <= now]

    def cb(ev, ctx):
        nonlocal checked
        now = ctx.now_ns
        # with a limit, the overall kept list is not a run of the input (each
        # type drops its own oldest), so only one-type reads are placed here;
        # test_positions_before_the_kept_history_are_dropped_not_nothing
        # covers the whole history
        for etype in ((None, BAR, EventType.TRADE) if history_limit is None else (BAR, EventType.TRADE)):
            sel = selection(etype, now)
            times = [int(e.received_time_ns) for e in sel]
            for until in sorted(set(times))[::3] + [None]:
                for kw in ({}, {"n": 2}, {"since_ns": times[len(times) // 2] if times else None}):
                    try:
                        ans = ctx.visible_events(etype, until_ns=until, **kw)
                    except HistoryTruncatedError:
                        continue
                    # where the answer's events sit in the input's list (times are distinct)
                    if ans:
                        lo = times.index(int(ans[0].received_time_ns))
                    else:
                        hi = len([t for t in times if until is None or t <= until])
                        lo = hi
                    positions = range(lo, lo + len(ans))
                    for sl in _SLICES:
                        applied = _apply(ans, positions, sl)
                        if applied is None:
                            continue
                        a, pos = applied
                        pstep = pos.step
                        for q in range(-len(a) - 3, len(a) + 3):
                            if -len(a) <= q < len(a):
                                if int(a[q].received_time_ns) != times[pos[q]]:
                                    problems.append(("value", now, etype, until, kw, sl, q))
                                continue
                            qq = q if q >= 0 else q + len(a)
                            u = pos.start + qq * pstep
                            if u >= len(times):
                                want = FuturePositionError
                            elif u >= 0:
                                want = OutsideAnswerError
                            else:
                                want = BeforeFirstEventError
                            try:
                                a[q]
                                got = None
                            except IndexError as exc:
                                got = type(exc)
                            if history_limit is not None and want is OutsideAnswerError:
                                # a delivered event: kept (outside the answer) or dropped
                                ok = got in (OutsideAnswerError, DroppedPositionError)
                            else:
                                ok = got is want
                            if not ok:
                                problems.append((now, etype, until, kw, sl, q, u, len(times), got, want))
                            checked += 1

    CoreEngine(Recorder(cb), events, history_limit=history_limit).run()
    return checked, problems


def _random_input(seed: int, count: int = 40):
    import random

    rng = random.Random(seed)
    events = []
    t = T0
    for i in range(count):
        t += rng.choice([1, 2, 3]) * SEC
        events.append(bar(t, 100.0 + i) if rng.random() < 0.5 else trade(t, 200.0 + i))
    return events


def test_every_named_position_agrees_with_the_input_at_every_callback():
    checked, problems = _run_every_naming(_random_input(606))
    assert checked > 10_000 and problems == [], problems[:5]


def test_the_fact_after_the_last_event_agrees_with_the_input():
    """`next_is_undelivered` (derived from the place) is True exactly when
    the input event after the answer's last one (of the selection) had not
    been received by now."""
    events = _random_input(607)
    problems: list = []
    checked = 0

    def cb(ev, ctx):
        nonlocal checked
        now = ctx.now_ns
        for etype in (None, BAR, EventType.TRADE):
            sel = [e for e in events if etype is None or e.EVENT_TYPE is etype]
            cuts = sorted({int(e.received_time_ns) for e in sel if e.received_time_ns <= now}) + [None]
            for until in cuts:
                for kw in ({}, {"n": 2}, {"since_ns": T0}):
                    ans = ctx.visible_events(etype, until_ns=until, **kw)
                    if not ans:
                        continue
                    later = [e for e in sel if e.received_time_ns > ans[-1].received_time_ns]
                    undelivered = not later or later[0].received_time_ns > now
                    if ans.next_is_undelivered is not undelivered:
                        problems.append((now, etype, until, kw))
                    checked += 1

    CoreEngine(Recorder(cb), events).run()
    assert checked > 1000 and problems == []


def test_positions_before_the_kept_history_are_dropped_not_nothing():
    """With history_limit, a position before the oldest KEPT event of a
    type that dropped some is a delivered event no longer held
    (DroppedPositionError, also a HistoryTruncatedError); before the first
    event ever delivered it is BeforeFirstEventError; after the newest it
    is still FuturePositionError."""
    got: dict = {}

    def kind(read):
        try:
            read()
        except IndexError as exc:
            return (type(exc).__name__, isinstance(exc, HistoryTruncatedError), isinstance(exc, LookAheadError))
        return "value"

    def cb(ev, ctx):
        if ev.EVENT_TYPE is BAR and ev.close == 109.0:
            # the kept bars: the largest n the history answers (10 were delivered)
            kept = 0
            while kept < 10:
                try:
                    ctx.visible_events(BAR, n=kept + 1)
                except HistoryTruncatedError:
                    break
                kept += 1
            bars = ctx.visible_events(BAR, n=kept)
            got["kept"] = kept
            got["bars[-kept-1]"] = kind(lambda: bars[-kept - 1])            # the newest dropped bar
            got["bars[-10]"] = kind(lambda: bars[-10])                      # the first bar (dropped)
            got["bars[-11]"] = kind(lambda: bars[-11])                      # before the first bar
            got["bars[::-1][kept]"] = kind(lambda: bars[::-1][kept])
            got["bars[kept]"] = kind(lambda: bars[kept])
            got["trades[-1]"] = kind(lambda: ctx.visible_events(EventType.TRADE)[-1])  # none delivered
            last = ctx.visible_events(n=1)
            got["all[-10]"] = kind(lambda: last[-10])                      # delivery #1 (dropped)
            got["all[-11]"] = kind(lambda: last[-11])                      # before delivery #1

    events = [bar(T0 + i * SEC, 100.0 + i) for i in range(10)] + [trade(T0 + 20 * SEC)]
    CoreEngine(Recorder(cb), events, history_limit=3).run()
    dropped, before, future = ("DroppedPositionError", True, False), ("BeforeFirstEventError", False, False), \
        ("FuturePositionError", False, True)
    assert 3 <= got["kept"] < 10
    assert got["bars[-kept-1]"] == dropped and got["bars[-10]"] == dropped and got["bars[-11]"] == before
    assert got["bars[::-1][kept]"] == dropped
    assert got["bars[kept]"] == future
    assert got["trades[-1]"] == before
    assert got["all[-10]"] == dropped and got["all[-11]"] == before


def test_every_named_position_with_a_history_limit():
    checked, problems = _run_every_naming(_random_input(608), history_limit=4)
    assert checked > 1000 and problems == [], problems[:5]


@pytest.mark.parametrize("n", range(0, 7))
def test_an_answered_read_does_not_depend_on_what_comes_after(n):
    """Rule-free: for bounds whose meaning does not depend on the answer's
    length (non-negative, or None where None means position 0 / the oldest
    end), a read that is answered gives the same positions had 12 more
    events been delivered after these."""
    seq = DeliveredEvents(range(n), first=0, delivered=n)
    for key in _all_keys():
        if isinstance(key, int):
            fixed, later = key >= 0, list(range(n + 12))
        else:
            step = 1 if key.step is None else key.step
            ok_start = key.start is not None and key.start >= 0 or (key.start is None and step > 0)
            ok_stop = key.stop is not None and key.stop >= 0 or (key.stop is None and step < 0)
            fixed, later = ok_start and ok_stop, list(range(n + 12))
        if not fixed:
            continue
        try:
            got = seq[key]
        except IndexError:
            continue  # refused (FuturePositionError is an IndexError)
        want = later[key]
        assert (list(got) if not isinstance(key, int) else got) == want, key


def test_each_role_of_the_table_refuses_by_itself_and_is_named():
    """Every role of POSITION_RULE refuses a bound one past its limit, and
    the error names the role (the rule is the table, not per-form code)."""
    n = 4
    seq = DeliveredEvents(range(n), first=0, delivered=n)
    past = DeliveredEvents(range(n), first=0, delivered=n + 6)
    one_past = {
        "index": 4,
        "forward slice start": slice(4, None),
        "forward slice stop": slice(None, 5),
        "backward slice start": slice(4, None, -1),
        "backward slice stop": slice(None, 4, -1),
    }
    assert set(one_past) == set(POSITION_RULE)
    for role, key in one_past.items():
        with pytest.raises(FuturePositionError, match=role):
            seq[key]
        with pytest.raises(OutsideAnswerError, match=role):
            past[key]
        # one less is answered
        if isinstance(key, int):
            assert seq[key - 1] == 3
        else:
            fix = {"start": key.start, "stop": key.stop}
            which = "start" if "start" in role else "stop"
            fix[which] -= 1
            seq[slice(fix["start"], fix["stop"], key.step)]
    assert CORE_CONTRACT["visibility"]["position_rule"]["max_position_by_role_as_offset_from_len"] == POSITION_RULE


def test_an_empty_answer_cut_inside_the_dropped_part_is_refused():
    """An empty answer lies where its range was cut. With history_limit,
    `until_ns` before the newest dropped event cuts somewhere among the
    dropped events, which the history no longer holds: the answer could
    not state what its positions are, so the read is refused (as any read
    reaching into the dropped part is). Cut at or after the newest dropped
    event, it is placed exactly and answered."""
    got = {}

    def cb(ev, ctx):
        if ev.EVENT_TYPE is BAR and ev.close == 109.0:
            for name, kw in (("inside", {"until_ns": T0 + 2 * SEC, "since_ns": T0 + 9 * SEC}),
                             ("n=0 inside", {"until_ns": T0 + 2 * SEC, "n": 0})):
                try:
                    ctx.visible_events(BAR, **kw)
                    got[name] = "answered"
                except HistoryTruncatedError:
                    got[name] = "refused"
            # the newest dropped bar: the largest n the history answers, then one more
            kept = 1
            while True:
                try:
                    ctx.visible_events(BAR, n=kept + 1)
                    kept += 1
                except HistoryTruncatedError:
                    break
            newest_dropped = T0 + (9 - kept) * SEC
            at_edge = ctx.visible_events(BAR, until_ns=newest_dropped, since_ns=T0 + 9 * SEC)
            got["edge"] = (len(at_edge), at_edge.place.first, at_edge.place.dropped)
            try:
                at_edge[-1]
            except DroppedPositionError:
                got["edge[-1]"] = "dropped"
            try:
                at_edge[0]
            except OutsideAnswerError as exc:
                got["edge[0]"] = (type(exc).__name__, exc.read_position)

    CoreEngine(Recorder(cb), [bar(T0 + i * SEC, 100.0 + i) for i in range(10)], history_limit=3).run()
    assert got["inside"] == "refused" and got["n=0 inside"] == "refused"
    assert got["edge"][0] == 0 and got["edge"][1] == 0 and got["edge"][2] > 0
    assert got["edge[-1]"] == "dropped" and got["edge[0]"] == ("OutsideAnswerError", 0)
