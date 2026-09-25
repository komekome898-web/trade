"""Critic, item 0, round 15 (i0-r15-03): the frames a comparison of two
colliding nested FrozenDicts needs.

Contract core-16 `process_state` (and values.py at MAX_NESTING / CALL_FRAMES):
"What is left of the interpreter's own recursion: when two DISTINCT nested
values whose hashes are equal are keys of one dict or elements of one set,
the interpreter compares them, one level of its recursion limit per
container of the two (measured: two distinct 98-level values need 106 frames
of headroom)".

That holds for tuples (measured below: n levels need about n + 6). A nested
FrozenDict compares through the core's OWN `FrozenDict.__eq__`, a Python
method that builds two dicts and compares them, so each level takes about 3
frames: 10 levels need 34, 30 need 94, 48 need 148
(<S>/r15_critic/item0_r15_critic_probe_headroom.out). The refusal is still
the entry's own error (the walk catches RecursionError), so no value is
wrong; the contract's fact is.

Grid: container of the colliding keys {tuple; FrozenDict} x levels {10, 30,
48}. Oracle (the most generous reading of the contract: one frame per
container of BOTH values): the least headroom freeze needs is at most
CALL_FRAMES + 2 x levels.

Not in the grid: frozensets (C comparison, like tuples) and mixed nests.
"""
from __future__ import annotations

import sys

import pytest

from bot.bt.core import values


def _depth() -> int:
    f, n = sys._getframe(1), 0
    while f is not None:
        n += 1
        f = f.f_back
    return n


def _ok(headroom: int, value) -> bool:
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(_depth() + headroom)
    try:
        values.freeze(value)
        return True
    except (RecursionError, ValueError):
        return False
    finally:
        sys.setrecursionlimit(old)


def _least(value) -> int:
    lo, hi = 1, 3000
    assert _ok(hi, value)
    while lo < hi:
        mid = (lo + hi) // 2
        if _ok(mid, value):
            hi = mid
        else:
            lo = mid + 1
    return lo


def _colliding(kind: str, levels: int) -> dict:
    a, b = -1, -2  # hash(-1) == hash(-2)
    for _ in range(levels - 1):
        a, b = ((a,), (b,)) if kind == "tuple" else (values.freeze({"k": a}), values.freeze({"k": b}))
    assert hash(a) == hash(b) and a != b
    return {a: 1, b: 2}


@pytest.mark.parametrize("levels", [10, 30, 48])
@pytest.mark.parametrize("kind", ["tuple", "FrozenDict"])
def test_colliding_nested_keys_need_at_most_one_frame_per_container(kind, levels):
    need = _least(_colliding(kind, levels))
    bound = values.CALL_FRAMES + 2 * levels
    assert need <= bound, (f"two colliding {levels}-level {kind} keys need {need} frames of headroom; the contract "
                           f"allows one per container of the two: {bound}")
