"""The core's carry-over from item 0 (PASS.md 「持ち越しの指摘」, round-17 critic
tests tests/bt/critic/item_0/test_i0r17_*.py), fixed in item 4 round 1
(core-19): a key's hash is counted over the objects before it is asked for;
freeze's error places are made only when named.

Grid (the rule's input space, not the code's branches): the depth d of a
tuple that holds the one below twice {0, 1, 5, 10, 17, 18, 19, 20, 40} x
where it sits {the value of a FrozenDict key, a set element} x entry
{freeze, settle}. Expected from the counting rule alone: a tuple of depth d
is visited 2**(d+1) - 1 times; a FrozenDict key adds itself, its pair and
its key (3); a set element adds nothing. Taken iff the visits <= 10**6,
else refused with ValueError -- in either case within 5 s.
Not in the grid: FrozenList chains (a tuple subclass, the same count),
frozensets inside (their hash is kept by the interpreter).
"""
from __future__ import annotations

import time

import pytest

from bot.bt.core import values as V


def chain(d):
    t = ()
    for _ in range(d):
        t = (t, t)
    return t


def visits(d, place):
    return 2 ** (d + 1) - 1 + (3 if place == "fd_key" else 0)


def forged_fd(value):
    fd = object.__new__(V.FrozenDict)
    object.__setattr__(fd, "_items", (("v", value),))
    object.__setattr__(fd, "_map", None)
    object.__setattr__(fd, "_hash", 12345)  # forged by the sender: its own dict never hashes the value
    return fd


def make(d, place):
    t = chain(d)
    if place == "fd_key":
        return {forged_fd(t): 1}
    return {t}


@pytest.mark.parametrize("entry", ["freeze", "settle"])
@pytest.mark.parametrize("place", ["fd_key", "set_element"])
@pytest.mark.parametrize("d", [0, 1, 5, 10, 17, 18, 19, 20, 40])
def test_a_key_is_taken_iff_its_hash_visits_are_bounded(d, place, entry):
    if place == "set_element" and d > 20:
        pytest.skip("the sender's own set would hash the tuple (2**41 visits) to be made at all")
    x = make(d, place)
    fn = getattr(V, entry)
    t0 = time.perf_counter()
    try:
        fn(x)
        taken = True
    except ValueError:
        taken = False
    assert time.perf_counter() - t0 < 5
    assert taken == (visits(d, place) <= V.MAX_HASH_VISITS), (d, place, entry)


def test_freeze_error_places_read_as_before():
    """The places an error names are the same text as when they were made eagerly: where[i], where key K,
    where[K], where element."""
    bad = object()
    for value, want in (([1, [2, bad]], "value[1][1]"), ({"k": [bad]}, "value['k'][0]"),
                        ({"k": {"j": bad}}, "value['k']['j']")):
        with pytest.raises(ValueError) as ei:
            V.freeze(value)
        assert str(ei.value).startswith(want), (str(ei.value), want)
