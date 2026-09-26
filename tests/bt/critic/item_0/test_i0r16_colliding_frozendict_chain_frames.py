"""Critic, item 0, round 16 (i0-r16-01): comparing two FrozenDicts whose
keys collide in hash at EVERY level still takes frames per level.

Contract core-17 `process_state`: "from a FrozenDict down by the core's own
iterative comparison (values._plain_equal, round 16, i0-r15-03: no frame per
level ...) -- measured (freeze of a dict with the two as keys): ...
FrozenDicts at most 12 at any depth, a mixed nest at most 14; at most
CALL_FRAMES + one frame per level for every container kind ...; with less,
such a value is refused with the entry's own error".

`_plain_equal` is iterative only while every key has ONE candidate of its
hash on the other side. When the other side holds several keys of that hash
(values.py `_match`, the `for y in cands` branch), each candidate is tried by
a NESTED `_plain_equal(kx, ky)` -- a Python call (two frames: `_match` and
`_plain_equal`) per level. A chain whose keys collide at every level
(X_k = {X_{k-1}: 0, Z_k: 0}, Y_k = {Y_{k-1}: 0, Z_k: 0}, Z_k an int whose
hash is hash(X_{k-1}); X_0 = 5, Y_0 = 5 + (2**61 - 1)) needs about 2 frames a
level (measured: 20 levels 55, 40 levels 95, 90 levels 195;
<S>/r16_critic/item0_r16_critic_probe_plain_equal_chain.out). With the
headroom the contract says is enough (CALL_FRAMES + levels) the value is
refused; with more it is taken: whether it is taken depends on the stack
depth of the call.

Grid: levels {10, 20, 40, 90} (all under MAX_NESTING). Oracle: the
contract's own bound, CALL_FRAMES + levels.

Not in the grid: sets of such FrozenDicts (FrozenSet elements compare by
the same `_match`), and chains with three or more colliding keys a level
(they make the work exponential, not only the frames).
"""
from __future__ import annotations

import sys

import pytest

from bot.bt.core import values

M = (1 << 61) - 1


def _chain(n: int):
    x, y = 5, 5 + M
    for _ in range(n):
        h = hash(values.freeze(x))
        z = (h % M) + 2 * M  # an int whose hash is h, unequal to 5 and 5 + M
        assert hash(z) == h
        y, x = values.FrozenDict({y: 0, z: 0}), values.FrozenDict({x: 0, z: 0})
    return x, y


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


@pytest.mark.parametrize("levels", [10, 20, 40, 90])
def test_colliding_chain_needs_no_more_than_the_contract_says(levels):
    x, y = _chain(levels)
    fx, fy = values.freeze(x), values.freeze(y)
    assert hash(fx) == hash(fy) and not (fx == fy)  # the setting: distinct, equal hash
    need = _least({x: 1, y: 2})
    bound = values.CALL_FRAMES + levels
    assert need <= bound, (f"two colliding {levels}-level FrozenDict chains need {need} frames of headroom; "
                           f"the contract says CALL_FRAMES + levels = {bound} is enough")
