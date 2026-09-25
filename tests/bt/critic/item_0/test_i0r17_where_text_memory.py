"""Critic, item 0, round 17 (i0-r17-02, implementation).

values.py `_freeze_open`: every child of a container is listed with its
`where` text, made at once for all children -- f"{where}[{i}]" for a list,
f"{where} key {text}" / f"{where}[{text}]" for a dict, where `text` is the
key's text (up to 300 characters, `value_text`) and `where` already holds
the whole path above. So a list of n items at depth d under dict keys of
300 characters makes n texts of about 300 * d characters each while the
list is walked: n * d * 300 bytes for a value of n + d objects. Contract
core-18: "The work of taking, handing out and comparing plain data is
decided by the OBJECTS handed over".

Measured by this critic (round 17): an 80000-item list under 95 such keys,
handed as an order's extra from on_event, raised the process's maximum
resident memory from 35 MB to 2338 MB (the same list at depth 1: 84 MB);
the machine has 16 GB and no swap, so a list of about 500000 small ints
there would end the process (not tried).

Grid: bottom list {2000, 8000} ints x depth {1, 95} (keys of 300
characters). Oracle: the peak memory traced while freezing the depth-95
value exceeds the depth-1 value's by at most 5 MB -- the 94 extra dicts and
keys the sender handed are under 100 kB (5 MB is 50 times that).

Not in the grid: settle (passes `where` down unchanged), the error texts of
a refusal (made once, for the one refused value).
"""
from __future__ import annotations

import tracemalloc

import pytest

from bot.bt.core import values as V


def _value(depth: int, width: int):
    x = list(range(width))
    for i in range(depth):
        x = {("k%03d" % i) + "x" * 296: x}
    return x


def _peak(value) -> int:
    tracemalloc.start()
    try:
        V.freeze(value)
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize("width", [2000, 8000])
def test_the_memory_of_freeze_is_decided_by_the_objects_not_their_depth(width):
    shallow, deep = _value(1, width), _value(95, width)
    p1, p95 = _peak(shallow), _peak(deep)
    assert p95 <= p1 + 5_000_000, (
        f"{width} ints under 95 keys: freeze peaked at {p95 / 1e6:.1f} MB, under 1 key {p1 / 1e6:.1f} MB; "
        f"the 94 extra dicts and keys are under 0.1 MB")
