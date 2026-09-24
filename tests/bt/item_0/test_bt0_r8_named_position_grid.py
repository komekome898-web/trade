"""Round 8 (i0-r7-01, the family i0-r5-05 -> i0-r6-01 -> i0-r7-01): every
way a strategy names a position of its history, enumerated on a full grid
BEFORE the rule was changed (lead design round_7/LEAD_DESIGN.md s3.2,
s3.3). The inputs come from the space of names, not from the cases the
implementation distinguishes:

* every index in [-len-3, len+3];
* every slice with start and stop in {None} + [-len-3, len+3] and step in
  {None, 0, +-1, +-2, +-3};
* every `index(value, start, stop)` with start and stop in [-len-3, len+3];
* on answers of 0..6 events placed forward, backward, stepped (+-2, +-3),
  cut in the past, with and without events dropped by history_limit;
* the same names on the private window a context holds
  (`EventWindow`, reachable by attribute access);
* in a run of the engine: every answer of every read (by type and
  overall; with until_ns / n / since_ns), its mirror `[::-1]` and
  slices of it; its place is compared with the INPUT (which input events
  of the selection had been received by now).

The oracle states the principle once, in the answer's own coordinates
(a negative bound b means b + len, as Python reads it; nothing is cut):

* an index and a slice start name an ITEM: the position must hold one
  (0 <= c <= len-1);
* a slice stop names a GAP: a forward stop c is the gap between c-1 and c,
  a backward stop c the gap between c and c+1; the len+1 gaps from
  "before 0" to "after len-1" are inside; a gap outside names the one of
  its two neighbours nearer the answer;
* a position outside is what the read's list holds there (not delivered
  yet / delivered, outside the answer / dropped by history_limit /
  nothing), mapped by the answer's place: position q is
  first + q * step; when several bounds are outside, one naming an event
  not delivered yet is reported, else the first (start, then stop).

Two checks that do not use the principle: (1) the mirror -- a name on an
answer and the mirrored name on its reverse read the same events, or
raise the same error for the same position of the read's list;
(2) answered reads agree with Python's own slicing of a plain tuple and
with the uncut range of positions.

NOT in the lists (said here, A-10): steps with |step| > 3; bounds beyond
len+3 (they behave as len+3 does: the principle has no case for their
size, and a spot check of +-10**30 is below); answers longer than 6 in the
unit grid (the engine run reaches 14); with history_limit, reads of the
whole history (its kept list is not a run of the input: each type drops
its own oldest; only one-type reads are placed against the input there);
calling a base class's method on
the core's own object (`tuple.__getitem__(answer, key)`,
`list.__getitem__(win._log, key)`), which bypasses the object's own
behaviour like `object.__setattr__` bypasses a frozen one. The backing
list the private window holds (`win._log`) IS in: it follows the same
principle with its own place and refuses changes.
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
from bot.bt.core.window import EventWindow

from bt0_util import SEC, T0, Recorder, bar, trade

STEPS = (None, 0, 1, 2, 3, -1, -2, -3)


def _keys(n: int):
    span = range(-n - 3, n + 4)
    for i in span:
        yield i
    bounds = (None, *span)
    for a, b, s in itertools.product(bounds, bounds, STEPS):
        yield slice(a, b, s)


def _c(b: int, n: int) -> int:
    return b if b >= 0 else b + n


def _named_outside(n: int, key) -> list[int]:
    """The oracle's principle (module docstring): the answer positions the
    key's explicit bounds name outside the answer, start before stop."""
    if isinstance(key, int):
        c = _c(key, n)
        return [] if 0 <= c < n else [c]
    step = 1 if key.step is None else key.step
    out = []
    if key.start is not None:
        c = _c(key.start, n)
        if not 0 <= c < n:
            out.append(c)
    if key.stop is not None:
        c = _c(key.stop, n)
        lo, hi = (c - 1, c) if step > 0 else (c, c + 1)  # the gap's two neighbours
        if hi > n:
            out.append(lo)
        elif lo < -1:
            out.append(hi)
    return out


def _world(u: int, delivered: int, dropped: int) -> type:
    if u >= delivered:
        return FuturePositionError
    if u >= 0:
        return OutsideAnswerError
    if u >= -dropped:
        return DroppedPositionError
    return BeforeFirstEventError


def _expected(n: int, key, place: AnswerPlace):
    if isinstance(key, slice) and key.step == 0:
        return ("step0",)
    named = _named_outside(n, key)
    if named:
        kinds = [(_world(place.first + q * place.step, place.delivered, place.dropped), q) for q in named]
        future = [k for k in kinds if k[0] is FuturePositionError]
        cls, q = (future or kinds)[0]
        return ("raise", cls, q, place.first + q * place.step)
    if isinstance(key, int):
        return ("item", _c(key, n))
    step = 1 if key.step is None else key.step
    start = (0 if step > 0 else n - 1) if key.start is None else _c(key.start, n)
    stop = (n if step > 0 else -1) if key.stop is None else _c(key.stop, n)
    return ("slice", list(range(start, stop, step)),
            AnswerPlace(place.first + start * place.step, place.step * step, place.delivered, place.dropped))


def _outcome(seq, key):
    try:
        got = seq[key]
    except IndexError as exc:
        return ("raised", type(exc), getattr(exc, "answer_position", None), getattr(exc, "read_position", None),
                isinstance(exc, LookAheadError))
    except ValueError:
        return ("valueerror",)
    return ("value", got)


def _agrees(items: list, place: AnswerPlace, key, got) -> tuple[bool, object]:
    n = len(items)
    want = _expected(n, key, place)
    if want[0] == "step0":
        return got == ("valueerror",), want
    if want[0] == "raise":
        _, cls, q, u = want
        ok = got[0] == "raised" and got[1] is cls and got[2] == q and got[3] == u and got[4] is (cls is FuturePositionError)
        return ok, want
    if want[0] == "item":
        return got[0] == "value" and got[1] == items[want[1]], want
    _, positions, wplace = want
    if got[0] != "value":
        return False, want
    out = got[1]
    ok = type(out) is DeliveredEvents and list(out) == [items[p] for p in positions]
    ok = ok and list(out) == list(tuple(items)[key])  # rule-free: Python's own slicing when nothing is outside
    ok = ok and out.place == wplace
    return ok, want


def _places(n: int):
    """(label, first, step, delivered, dropped): forward, backward, stepped,
    cut in the past, with and without a drop, at the newest and not."""
    yield "forward-newest", 0, 1, n, 0
    yield "forward-newest-dropped", 0, 1, n, 3
    yield "forward-past", 2, 1, n + 5, 0
    yield "forward-past-dropped", 0, 1, n + 4, 2
    yield "stepped2", 1, 2, 2 * n + 2, 0
    yield "stepped3-dropped", 2, 3, 3 * n + 4, 5
    if n:
        yield "backward-newest", n - 1, -1, n, 0
        yield "backward-newest-dropped", n - 1, -1, n, 4
        yield "backward-past", n + 1, -1, n + 4, 2
        yield "backward-stepped2", 2 * (n - 1), -2, 2 * n - 1, 0
        yield "backward-stepped3-past", 3 * (n - 1) + 1, -3, 3 * n + 3, 1
    else:
        yield "empty-at-0", 0, 1, 0, 0
        yield "empty-in-past", 2, 1, 5, 1
        yield "empty-backward", 3, -1, 4, 0


@pytest.mark.parametrize("n", range(0, 7))
def test_every_name_on_every_place_agrees_with_the_principle(n):
    checked = raised = 0
    problems = []
    for label, first, step, delivered, dropped in _places(n):
        items = [first + i * step for i in range(n)]  # each item is its position in the read's list
        seq = DeliveredEvents(items, first=first, step=step, delivered=delivered, dropped=dropped)
        place = seq.place
        for key in _keys(n):
            got = _outcome(seq, key)
            ok, want = _agrees(items, place, key, got)
            checked += 1
            raised += want[0] == "raise"
            if not ok:
                problems.append((label, key, want, got))
    assert not problems, problems[:8]
    assert raised > 0 and checked > 1000


def _mirror_bound(b, n: int):
    if b is None:
        return None
    m = n - 1 - _c(b, n)
    return m if m >= 0 else m - n  # a raw bound whose c is m (a negative raw counts from the end)


@pytest.mark.parametrize("n", range(0, 7))
def test_a_name_and_its_mirror_on_the_reverse_name_the_same_events(n):
    """Rule-free: `a[k]` and `a[::-1][mirror(k)]` read the same events of
    the read's list, or raise the same error for the same position."""
    problems = []
    for label, first, step, delivered, dropped in _places(n):
        a = DeliveredEvents([first + i * step for i in range(n)], first=first, step=step,
                            delivered=delivered, dropped=dropped)
        r = a[::-1]
        if n:
            assert r.place == AnswerPlace(first + (n - 1) * step, -step, delivered, dropped), label
        for key in _keys(n):
            if isinstance(key, int):
                mkey = _mirror_bound(key, n)
            else:
                if key.step == 0:
                    continue
                s = 1 if key.step is None else key.step
                mkey = slice(_mirror_bound(key.start, n), _mirror_bound(key.stop, n), -s)
            x, y = _outcome(a, key), _outcome(r, mkey)
            if x[0] == "raised" or y[0] == "raised":
                same = x[0] == y[0] == "raised" and x[1] is y[1] and x[3] == y[3]
            elif isinstance(key, int):
                same = x == y
            else:
                same = list(x[1]) == list(y[1]) and (not len(x[1]) or x[1].place == y[1].place)
            if not same:
                problems.append((label, key, mkey, x, y))
    assert not problems, problems[:8]


@pytest.mark.parametrize("n", range(0, 7))
def test_index_with_start_and_stop_names_positions_by_the_same_principle(n):
    """`answer.index(value, start, stop)` names positions like a forward
    slice [start:stop]: outside, the same error; inside, the position of
    the first equal item in range(start, stop), or ValueError."""
    problems = []
    span = range(-n - 3, n + 4)
    for label, first, step, delivered, dropped in _places(n):
        items = [first + i * step for i in range(n)]
        seq = DeliveredEvents(items, first=first, step=step, delivered=delivered, dropped=dropped)
        for value in (items[n // 2] if n else 0, -999):
            for args in [()] + [(s,) for s in span] + list(itertools.product(span, span)):
                key = slice(args[0] if args else None, args[1] if len(args) > 1 else None, 1)
                want = _expected(n, key, seq.place)
                try:
                    got = ("value", seq.index(value, *args))
                except IndexError as exc:
                    got = ("raised", type(exc), getattr(exc, "read_position", None))
                except ValueError:
                    got = ("absent",)
                if want[0] == "raise":
                    ok = got == ("raised", want[1], want[3])
                else:
                    hits = [p for p in want[1] if items[p] == value]
                    ok = got == (("value", hits[0]) if hits else ("absent",))
                if not ok:
                    problems.append((label, value, args, want, got))
    assert not problems, problems[:8]


@pytest.mark.parametrize("n", range(0, 7))
def test_the_private_window_names_positions_like_an_answer(n):
    """The window a context holds (`ctx._StrategyContext__visible_events`,
    reachable by attribute access) follows the same principle, with its
    own place: first 0, step 1, delivered = its length, dropped as given."""
    problems = []
    for dropped in (0, 3):
        backing = [f"e{i}" for i in range(n)] + ["not-in-the-window"] * 4  # never shown: past the window's end
        win = EventWindow(backing, n, dropped=dropped)
        place = AnswerPlace(0, 1, n, dropped)
        items = backing[:n]
        for key in _keys(n):
            ok, want = _agrees(items, place, key, _outcome(win, key))
            if not ok:
                problems.append((dropped, key, want, _outcome(win, key)))
        for value in (items[0] if n else "x", "absent"):
            for s, t in itertools.product(range(-n - 3, n + 4), repeat=2):
                want = _expected(n, slice(s, t, 1), place)
                try:
                    got = ("value", win.index(value, s, t))
                except IndexError as exc:
                    got = ("raised", type(exc))
                except ValueError:
                    got = ("absent",)
                if want[0] == "raise":
                    ok = got == ("raised", want[1])
                else:
                    hits = [p for p in want[1] if items[p] == value]
                    ok = got == (("value", hits[0]) if hits else ("absent",))
                if not ok:
                    problems.append(("index", dropped, value, s, t, want, got))
    assert not problems, problems[:8]


def test_huge_bounds_behave_as_any_bound_outside():
    a = DeliveredEvents(range(4), first=0, delivered=4)
    for key in (10**30, slice(10**30, None), slice(None, 10**30), slice(-10**30, None), slice(None, -10**30, -1)):
        with pytest.raises(IndexError):
            a[key]
    with pytest.raises(FuturePositionError):
        a[::-1][-10**30:]
    with pytest.raises(BeforeFirstEventError):
        a[-10**30:]


# -- in a run of the engine: places from the INPUT ---------------------------

def _input(seed: int, count: int = 14):
    import random

    rng = random.Random(seed)
    events, t = [], T0
    for i in range(count):
        t += rng.choice([1, 2, 3]) * SEC
        events.append(bar(t, 100.0 + i) if rng.random() < 0.5 else trade(t, 200.0 + i))
    return events


_TRANSFORMS = (None, slice(None, None, -1), slice(None, None, 2), slice(1, None, 3), slice(None, None, -2))


def test_every_name_in_a_run_agrees_with_the_input():
    """At every callback, for reads by type and overall, cut by until_ns,
    n and since_ns: the answer's place is what the INPUT says (which input
    events of the selection had been received by now), and every name of
    the grid on it and on its transforms agrees with the principle applied
    to that input place."""
    events = _input(808)
    checked = 0
    problems: list = []

    def cb(ev, ctx):
        nonlocal checked
        now = ctx.now_ns
        for etype in (None, EventType.BAR, EventType.TRADE):
            sel = [e for e in events if (etype is None or e.EVENT_TYPE is etype) and e.received_time_ns <= now]
            times = [int(e.received_time_ns) for e in sel]
            cuts = [None] + times[::4]
            for until in cuts:
                for kw in ({}, {"n": 3}, {"since_ns": times[len(times) // 2] if times else None}):
                    ans = ctx.visible_events(etype, until_ns=until, **kw)
                    if ans:
                        lo = times.index(int(ans[0].received_time_ns))
                    else:
                        lo = len([t for t in times if until is None or t <= until])
                    place = AnswerPlace(lo, 1, len(times), 0)  # from the input
                    if ans.place != place or [int(e.received_time_ns) for e in ans] != times[lo:lo + len(ans)]:
                        problems.append(("place", now, etype, until, kw, ans.place, place))
                        continue
                    for tkey in _TRANSFORMS:
                        if tkey is None:
                            a, p = ans, place
                        else:
                            want = _expected(len(ans), tkey, place)
                            if want[0] == "raise":  # the transform itself names outside (short answer)
                                ok, _ = _agrees(list(ans), place, tkey, _outcome(ans, tkey))
                                checked += 1
                                if not ok:
                                    problems.append(("transform refused", now, etype, until, kw, tkey))
                                continue
                            a, p = ans[tkey], want[2]
                            if a.place != p:
                                problems.append(("transform", now, etype, until, kw, tkey, a.place, p))
                                continue
                        items = list(a)
                        grid = _keys(len(a)) if len(a) <= 5 else range(-len(a) - 3, len(a) + 4)
                        for key in grid:
                            got = _outcome(a, key)
                            ok, want = _agrees(items, p, key, got)
                            checked += 1
                            if not ok:
                                problems.append((now, etype, until, kw, tkey, key, want, got))
        # the private window: the same principle, place (0, 1, len, 0)
        win = ctx._StrategyContext__visible_events
        items = list(win)
        for key in range(-len(items) - 3, len(items) + 4):
            ok, want = _agrees(items, AnswerPlace(0, 1, len(items), 0), key, _outcome(win, key))
            checked += 1
            if not ok:
                problems.append(("window", now, key, want))

    CoreEngine(Recorder(cb), events).run()
    assert problems == [], problems[:6]
    assert checked > 100_000


def test_the_critics_backward_slices_name_the_future():
    """i0-r7-01's four names on the newest-first answer (4 delivered bars,
    newest first) name only positions after the newest delivered bar."""
    got = {}

    def cb(ev, ctx):
        if ctx.now_ns != T0 + 3 * SEC:
            return
        r = ctx.visible_events(EventType.BAR)[::-1]
        for label, key in (("r[-6:-5]", slice(-6, -5)), ("r[-6:-4]", slice(-6, -4)),
                           ("r[-5::-1]", slice(-5, None, -1)), ("r[-6:-5:-1]", slice(-6, -5, -1)),
                           ("r[-5:]", slice(-5, None)), ("r[:-5]", slice(None, -5))):
            try:
                r[key]
                got[label] = None
            except IndexError as exc:
                got[label] = (type(exc), exc.read_position)

    CoreEngine(Recorder(cb), [bar(T0 + i * SEC, 100.0 + i) for i in range(6)]).run()
    assert got["r[-6:-5]"] == (FuturePositionError, 5)
    assert got["r[-6:-4]"] == (FuturePositionError, 5)
    assert got["r[-5::-1]"] == (FuturePositionError, 4)
    assert got["r[-6:-5:-1]"] == (FuturePositionError, 5)
    assert got["r[-5:]"] == (FuturePositionError, 4)
    assert got["r[:-5]"] == (FuturePositionError, 4)


def test_the_rule_is_one_table_of_ranges_and_the_contract_states_it():
    assert set(POSITION_RULE) == {"index", "forward slice start", "forward slice stop",
                                  "backward slice start", "backward slice stop"}
    rule = CORE_CONTRACT["visibility"]["position_rule"]
    assert rule["range_by_role"] == {role: list(v) for role, v in POSITION_RULE.items()}
    assert rule["range_by_role"]["backward slice stop"] == [-1, -1]  # the gap before the oldest
    assert "never cut before the check" in rule["bounds"]
    assert "negative_bounds" not in rule  # no second rule for a sign


def test_the_backing_list_names_positions_like_an_answer_and_cannot_be_changed():
    """The list the private window holds (`win._log`, the core's own list
    of delivered events) reads by position under the same principle, with
    its own place (0, 1, len, dropped), and refuses changes; it holds only
    events delivered by now, and the window drops it on return."""
    seen = {}
    problems = []

    def cb(ev, ctx):
        win = ctx._StrategyContext__visible_events
        log = win._log
        items = list(iter(log))
        place = AnswerPlace(0, 1, len(items), 0)
        for key in _keys(len(items)) if len(items) <= 4 else range(-len(items) - 3, len(items) + 4):
            ok, want = _agrees(items, place, key, _outcome(log, key))
            if not ok:
                problems.append((ctx.now_ns, key, want, _outcome(log, key)))
        for change in (lambda: log.append(ev), lambda: log.clear(), lambda: log.pop(),
                       lambda: log.__setitem__(0, ev), lambda: log.__delitem__(0), lambda: log.extend([ev]),
                       lambda: log.insert(0, ev), lambda: log.remove(ev), lambda: log.sort(),
                       lambda: log.reverse(), lambda: log.__iadd__([ev]), lambda: log.__imul__(2)):
            try:
                change()
                problems.append(("changed", ctx.now_ns))
            except TypeError:
                pass
        if ctx.now_ns == T0 + 2 * SEC:
            seen["backing"] = [int(e.received_time_ns) for e in log]
            seen["win"] = win
            for key, want in ((3, FuturePositionError), (slice(3, 4), FuturePositionError),
                              (slice(-4, None), BeforeFirstEventError)):
                try:
                    log[key]
                    seen[repr(key)] = None
                except IndexError as exc:
                    seen[repr(key)] = type(exc)
                assert seen[repr(key)] is want, (key, seen[repr(key)])

    CoreEngine(Recorder(cb), [bar(T0 + i * SEC, 1.0 + i) for i in range(5)]).run()
    assert problems == [], problems[:5]
    assert seen["backing"] == [T0, T0 + SEC, T0 + 2 * SEC]
    assert seen["win"]._log == ()


def test_now_is_the_engines_time_not_the_strategys_copy():
    """`ctx.now_ns` and the time check of a read come from the engine: a
    strategy that changes its own copy of the current event (bypassing
    frozen) does not move them."""
    got = {}

    def cb(ev, ctx):
        if ctx.now_ns == T0 + SEC:
            object.__setattr__(ctx.current_event, "received_time_ns", T0 + 99 * SEC)
            got["now"] = ctx.now_ns
            try:
                ctx.visible_events(until_ns=T0 + 50 * SEC)
                got["until"] = "answered"
            except LookAheadError:
                got["until"] = "refused"

    CoreEngine(Recorder(cb), [bar(T0 + i * SEC, 1.0 + i) for i in range(3)]).run()
    assert got == {"now": T0 + SEC, "until": "refused"}


def test_a_history_limit_run_places_dropped_positions():
    """With history_limit, one-type reads: a position before the oldest kept
    event is dropped (not nothing) until before the first delivered."""
    problems = []

    def cb(ev, ctx):
        now = ctx.now_ns
        for etype in (EventType.BAR, EventType.TRADE):
            try:
                ans = ctx.visible_events(etype, n=2)
            except HistoryTruncatedError:  # pragma: no cover - n=2 <= the limit is always kept
                continue
            p = ans.place
            if len(ans) == 2 and p.dropped:
                seen_drop.append(p)
            r = ans[::-1] if len(ans) else ans
            # every index down to far before the first delivered, and every
            # slice of the grid, on the answer and on its reverse
            names = list(range(-len(ans) - 20, len(ans) + 4)) + [k for k in _keys(len(ans)) if isinstance(k, slice)]
            for key in names:
                for label, a in (("a", ans), ("r", r)):
                    ok, want = _agrees(list(a), a.place, key, _outcome(a, key))
                    if not ok:
                        problems.append((label, now, etype, key, want))

    seen_drop: list = []
    CoreEngine(Recorder(cb), _input(809, 30), history_limit=2).run()
    assert problems == [], problems[:6]
    assert seen_drop  # answers with dropped events before them were checked
