"""Critic, item 0, round 17 (i0-r17-01, implementation; family of i0-r16-03).

Contract core-18 (contract.py process_state): "a FrozenDict's hash is made
once, when it is first asked for (the core asks only for a dict key or a set
element, which the sender's own dict or set hashed already)". values.py
`FrozenDict.__hash__` / `_fd_hash` / `_pairs_hash`: the pair hash is taken by
the interpreter, whose tuple hash (not kept by Python 3.11) unfolds a tuple
that holds one tuple twice at every level: 2**depth tuples for depth + 1
objects.

The premise "the sender's own dict hashed it already" does not hold for a
sender that writes its OWN FrozenDict's slots with object.__setattr__ (the
same means values.py `_frozen_pairs` and `rebuild_carrier` already treat as a
sender's; L-445 keeps "the strategy's own objects, handled by any means,
rewriting included" inside the core's promise -- it writes no module, no
builtin, no class, no ABC):
- "forged-hash": the sender sets its key's `_hash` slot to an int, so its own
  dict {key: 1} is made without hashing the value (round 17 made the
  FrozenDict's construction O(1): the hash is no longer made there);
- "pairs-slot": the sender's FrozenDict whose `_items` slot holds the pairs
  (key, 1), made with object.__new__ -- no dict of the sender hashed the key.
The core's copy of the key has no hash yet, so freeze / settle (and
place_order from on_event) hash it: 2**40 tuples, hours.

Grid: form {forged-hash, pairs-slot} x entry {freeze, settle, place_order}
x the value's shared tuple depth 40 (41 tuples the sender holds). Oracle
(the contract's own sentence "the work ... is decided by the OBJECTS handed
over"): a child process finishes within 20 s -- the value taken, or refused
with the entry's own error (ValueError / OrderApiError); any other exception
or no end fails. 20 s is 2**20 times less than unfolding needs and over
10**4 times what 41 objects need (round 17 worker: 46..91 shared containers
in at most 5 ms).

Not in the grid: a sender that hashes its key honestly (it pays the same
unfolding itself; the contract's premise holds); classes the sender writes
(L-445).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

from bot.bt.core import values as V

SRC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(V.__file__)))))

CHILD = textwrap.dedent("""
    import sys
    from bot.bt.core import BarEvent, CoreEngine, values as V
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.errors import OrderApiError
    from bot.bt.core.interfaces import NullCostModel
    from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
    form, entry, depth = sys.argv[1], sys.argv[2], int(sys.argv[3])
    t = ()
    for _ in range(depth):
        t = (t, t)
    key = V.FrozenDict({"v": t})
    if form == "forged-hash":
        object.__setattr__(key, "_hash", 12345)
        x = {key: 1}
    else:
        x = object.__new__(V.FrozenDict)
        object.__setattr__(x, "_items", ((key, 1),))
        object.__setattr__(x, "_map", None)
        object.__setattr__(x, "_hash", None)
    try:
        if entry == "freeze":
            V.freeze(x)
        elif entry == "settle":
            V.settle(x)
        else:
            T0 = 1_700_000_000_000_000_000
            class S:
                n = 0
                def on_event(self, ev, ctx):
                    S.n += 1
                    if S.n == 1:
                        try:
                            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0,
                                                         client_order_id="o1", extra=(("k", x),)))
                        except OrderApiError:
                            print("refused", flush=True)
            bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0,
                             volume=1.0) for k in (0, 10)]
            CoreEngine(S(), bars, fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
                       cost_model=NullCostModel()).run()
        print("done", flush=True)
    except (ValueError, OrderApiError):
        print("refused", flush=True)
""")


@pytest.mark.parametrize("entry", ["freeze", "settle", "place_order"])
@pytest.mark.parametrize("form", ["forged-hash", "pairs-slot"])
def test_a_key_the_sender_never_hashed_is_taken_in_bounded_time(form, entry):
    env = {**os.environ, "PYTHONPATH": SRC}
    try:
        out = subprocess.run([sys.executable, "-c", CHILD, form, entry, "40"], capture_output=True, text=True,
                             timeout=20, env=env)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{form} via {entry}: the core did not take or refuse a value of 41 tuples within 20 s "
                    f"(its copy of the key is hashed by the interpreter's tuple hash, unfolding 2**40 tuples)")
    assert out.returncode == 0 and out.stdout.strip().splitlines()[-1:] in (["done"], ["refused"]), \
        (form, entry, out.stdout[-500:], out.stderr[-1500:])
