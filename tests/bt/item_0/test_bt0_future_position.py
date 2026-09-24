"""P0-4 by position: a history read returns `DeliveredEvents`, where naming
a position after the last event of the answer -- by an index or by an
explicit non-negative slice bound, whatever the bound's role -- raises
`FuturePositionError` (an IndexError and a LookAheadError) instead of a
silently shortened or empty answer, as a time argument after now does.
Scene p4-future-read-attempt: "空・切り詰め … は素通り".

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
            "type": type(bars),
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
    assert got["type"] is DeliveredEvents
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


@pytest.mark.parametrize("n", range(0, 7))
def test_every_index_and_slice_matches_the_probe_oracle(n):
    seq = DeliveredEvents(range(n))
    plain = list(range(n))
    checked = refused = 0
    for key in _all_keys():
        checked += 1
        if _names_a_position_past_the_end(n, key):
            with pytest.raises(FuturePositionError):
                seq[key]
            refused += 1
            continue
        if isinstance(key, int):
            if key < -n:
                with pytest.raises(IndexError) as info:
                    seq[key]
                assert not isinstance(info.value, FuturePositionError)
            else:
                assert seq[key] == plain[key]
            continue
        out = seq[key]
        assert type(out) is DeliveredEvents and list(out) == plain[key], key
    assert checked == 19 + 20 * 20 * 7 and refused > 0


@pytest.mark.parametrize("n", range(0, 7))
def test_an_answered_read_does_not_depend_on_what_comes_after(n):
    """Rule-free: for bounds whose meaning does not depend on the answer's
    length (non-negative, or None where None means position 0 / the oldest
    end), a read that is answered gives the same positions had 12 more
    events been delivered after these."""
    seq = DeliveredEvents(range(n))
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
    seq = DeliveredEvents(range(n))
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
        # one less is answered
        if isinstance(key, int):
            assert seq[key - 1] == 3
        else:
            fix = {"start": key.start, "stop": key.stop}
            which = "start" if "start" in role else "stop"
            fix[which] -= 1
            seq[slice(fix["start"], fix["stop"], key.step)]
    assert CORE_CONTRACT["visibility"]["position_rule"]["max_position_by_role_as_offset_from_len"] == POSITION_RULE
