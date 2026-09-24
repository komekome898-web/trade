"""P0-4 by position: a history read returns `DeliveredEvents`, where naming
a position after the last event of the answer -- by an index or by an
explicit non-negative slice bound, whatever the bound's role -- raises
`FuturePositionError` (an IndexError and a LookAheadError) instead of a
silently shortened or empty answer, as a time argument after now does.
Scene p4-future-read-attempt: "空・切り詰め … は素通り".

Round 6 (i0-r5-05): the error said "not delivered yet" also for an answer
that ends in the delivered past (`until_ns` before the newest, a slice
ending before the answer's end, a backward read). An answer now carries
`next_is_undelivered` (is the position after its last event an event not
delivered yet?), fixed when it is made; past its end it raises
`FuturePositionError` if True and `OutsideAnswerError` (an IndexError, not
a LookAheadError) if False. The oracles below run over both facts; the
engine-level check compares the fact with the INPUT (was the event after
the answer's last delivered at that time?), not with the core's rule.

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
    CoreEngine,
    DeliveredEvents,
    EventType,
    FuturePositionError,
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


def test_negative_index_before_the_oldest_is_a_plain_index_error():
    def read(ctx):
        try:
            ctx.visible_events(BAR)[-5]
        except FuturePositionError:
            return "future"
        except IndexError:
            return "past"
    assert _reads_at_fourth_bar(read) == "past"


# -- the rule, checked against an oracle that does not read the core -------

def _names_a_position_past_the_end(n: int, key) -> bool:
    """Probe a plain tuple of n elements. An index, the first position a
    slice reads (its start), and the old-side end of a backward slice (its
    stop, which names the element just before the range) must name an
    element that is there. The end of a forward slice (its stop, not read)
    may be the end of the answer, but `plain[:stop]` must not be cut short.
    Negative bounds count from the newest and never name the future."""
    plain = tuple(range(n))

    def is_there(p: int) -> bool:
        try:
            plain[p]
        except IndexError:
            return False
        return True

    if isinstance(key, int):
        return key >= 0 and not is_there(key)
    step = 1 if key.step is None else key.step
    must_be_there = [key.start] + ([key.stop] if step < 0 else [])
    if any(b is not None and b >= 0 and not is_there(b) for b in must_be_there):
        return True
    return step > 0 and key.stop is not None and key.stop >= 0 and len(plain[:key.stop]) != key.stop


_BOUNDS = [None] + list(range(-9, 10))
_STEPS = [None, 1, 2, 3, -1, -2, -3]


def _all_keys():
    for i in range(-9, 10):
        yield i
    for start, stop, step in itertools.product(_BOUNDS, _BOUNDS, _STEPS):
        yield slice(start, stop, step)


def _next_after_result(n: int, key: slice) -> int:
    """The position, in an answer of n events, of what follows the last
    event of `answer[key]` in the slice's own direction -- from Python's
    range semantics on plain positions, not from the core."""
    r = range(n)[key]
    return r.start + len(r) * r.step


@pytest.mark.parametrize("fact", [True, False])
@pytest.mark.parametrize("n", range(0, 7))
def test_every_index_and_slice_matches_the_probe_oracle(n, fact):
    seq = DeliveredEvents(range(n), next_is_undelivered=fact)
    past_end_error = FuturePositionError if fact else OutsideAnswerError
    plain = list(range(n))
    checked = refused = 0
    for key in _all_keys():
        checked += 1
        if _names_a_position_past_the_end(n, key):
            with pytest.raises(past_end_error) as info:
                seq[key]
            # the kind follows the answer's fact: never "not delivered yet"
            # for an answer that ends in the delivered past
            assert isinstance(info.value, LookAheadError) is fact, key
            refused += 1
            continue
        if isinstance(key, int):
            if key < -n:
                with pytest.raises(IndexError) as info:
                    seq[key]
                assert not isinstance(info.value, (FuturePositionError, OutsideAnswerError))
            else:
                assert seq[key] == plain[key]
            continue
        out = seq[key]
        assert isinstance(out, DeliveredEvents) and list(out) == plain[key], key
        # the slice carries the fact for its OWN last event: what follows it
        # is what follows the answer only if that position is past the
        # answer's end in the forward direction
        nxt = _next_after_result(n, key)
        step = 1 if key.step is None else key.step
        assert out.next_is_undelivered is (fact and step > 0 and nxt >= n), key
    assert checked == 19 + 20 * 20 * 7 and refused > 0


def test_a_slice_that_ends_before_the_answer_names_the_past_not_the_future():
    """i0-r5-05 by slicing: in an answer of 4 that ends at the newest,
    `[1:3]` ends at position 2; its position 2 is the answer's position 3
    (delivered). `[1:]` reaches the end; its position 3 is not delivered.
    A backward read's position after its last is older than the oldest."""
    ans = DeliveredEvents(range(4), next_is_undelivered=True)
    with pytest.raises(OutsideAnswerError) as info:
        ans[1:3][2]
    assert not isinstance(info.value, LookAheadError)
    with pytest.raises(FuturePositionError):
        ans[1:][3]
    with pytest.raises(OutsideAnswerError):
        ans[::-1][4]
    # positions 0 and 2; stepping 2 on from position 2 lands at 4, past the
    # answer's end, which is not delivered
    assert ans[0:4:2].next_is_undelivered is True
    assert ans[0:3:2].next_is_undelivered is True and ans[1:3:2].next_is_undelivered is False
    with pytest.raises(FuturePositionError):
        ans[0:4:2][2]


def test_the_fact_cannot_be_left_out_or_changed():
    with pytest.raises(TypeError):
        DeliveredEvents((1, 2))  # the maker states what follows
    with pytest.raises(TypeError):
        DeliveredEvents((1, 2), next_is_undelivered=1)
    ans = DeliveredEvents((1, 2), next_is_undelivered=False)
    with pytest.raises(AttributeError):
        ans.next_is_undelivered = True
    import copy
    import pickle
    for clone in (copy.copy(ans), copy.deepcopy(ans), pickle.loads(pickle.dumps(ans))):
        assert clone == ans and clone.next_is_undelivered is False


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


def test_the_fact_agrees_with_the_input_at_every_callback():
    """Rule-free: at every callback, for reads cut at every delivered
    time (and uncut, by type and overall, with n and since_ns), the fact
    is True exactly when the INPUT event after the answer's last one (of
    what the read selects) had not been delivered by now -- decided from
    the input list and the callback time, not from the core -- and the
    position after the answer's last raises the matching error."""
    import random

    rng = random.Random(606)
    events = []
    t = T0
    for i in range(40):
        t += rng.choice([1, 2, 3]) * SEC
        events.append(bar(t, 100.0 + i) if rng.random() < 0.5 else trade(t, 200.0 + i))
    checked = 0
    problems: list = []

    def selection(etype):
        return [e for e in events if etype is None or e.EVENT_TYPE is etype]

    def cb(ev, ctx):
        nonlocal checked
        now = ctx.now_ns
        for etype in (None, BAR, EventType.TRADE):
            sel = selection(etype)
            cuts = sorted({int(e.received_time_ns) for e in sel if e.received_time_ns <= now}) + [None]
            for until in cuts:
                for kw in ({}, {"n": 2}, {"since_ns": T0}):
                    ans = ctx.visible_events(etype, until_ns=until, **kw)
                    if not ans:
                        continue
                    last = ans[-1]
                    later = [e for e in sel if e.received_time_ns > last.received_time_ns]  # times are distinct
                    undelivered = not later or later[0].received_time_ns > now
                    if ans.next_is_undelivered is not undelivered:
                        problems.append((now, etype, until, kw, ans.next_is_undelivered, undelivered))
                    try:
                        ans[len(ans)]
                    except FuturePositionError:
                        kind = True
                    except OutsideAnswerError:
                        kind = False
                    if kind is not undelivered:
                        problems.append(("error", now, etype, until, kw))
                    checked += 1

    CoreEngine(Recorder(cb), events).run()
    assert checked > 1000 and problems == []


@pytest.mark.parametrize("n", range(0, 7))
def test_an_answered_read_does_not_depend_on_what_comes_after(n):
    """Rule-free: for bounds whose meaning does not depend on the answer's
    length (non-negative, or None where None means position 0 / the oldest
    end), a read that is answered gives the same positions had 12 more
    events been delivered after these."""
    seq = DeliveredEvents(range(n), next_is_undelivered=True)
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
    seq = DeliveredEvents(range(n), next_is_undelivered=True)
    past = DeliveredEvents(range(n), next_is_undelivered=False)
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
