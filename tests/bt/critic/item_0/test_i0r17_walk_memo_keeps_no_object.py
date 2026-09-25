"""Critic, item 0, round 17 (i0-r17-01, implementation; family of i0-r16-03).

values.py `_walk` (round 17) remembers each rebuilt container by `id(v)`
(`memo[top[5]] = (built, height)`) and keeps no reference to `v`; its comment
says "the walk holds the value, so no id is reused during it". The walk holds
the ROOT only: when the sender's value changes while the walk runs, a
container the walk has already rebuilt can be freed, and its id given to a new
container that the walk meets later -- the memo then puts the OLD container's
copy in its place. The value that comes out holds, at that place, something
the sender's container never held (neither before nor after the change).

The change here is made by the sender's own function: the callback of a
`weakref.ref` to its own set, run by the cyclic garbage collection that the
walk's own allocations trigger (a chain of such callbacks lets the K-th
collection make the change). The sender writes no module, builtin, class, ABC
or interpreter setting -- it changes its own lists (requirements §0, L-445:
"戦略が核から受け取った物と自分の物をどう扱っても(書き換え・保持・例外)").

Grid: entry {freeze, settle, an order's extra read by the fill model with
`extra_dict()`} x K {3, 6} (the number of collections that change it), N =
400 pairs (P_i = [("secret", i, 0)], Q_i = []; the k-th change replaces P_i's
item by ("secret", i, k) and appends ("new", i, k) to Q_i). Oracle: each Q_i
comes out as a state Q_i held -- [("new", i, 1), ..., ("new", i, m)] for some
m >= 0 -- and at least 2 changes ran during the walk (the first collection
comes right as the walk opens the root, before anything is remembered; with
fewer the cell is not measured and fails as such). Each cell runs in a child
process (the collector's timing is decided by that process's allocations).

Measured by this critic: the core at 1d8a107 (before round 17, no memo)
gives 0 such entries in every cell; the round-17 core gives such entries in
every cell (the counts are in the critic's record, round_17/CRITIC.md).

Not in the grid: threads (the same freed id, reached without the collector);
renew / thaw (they walk values the core built, which no one can change).
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
    import gc, sys, weakref
    from bot.bt.core import BarEvent, CoreEngine, values as V
    from bot.bt.core.api import OrderRequest
    from bot.bt.core.interfaces import NullCostModel
    from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

    entry, N, K = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    state = {"n": 0}
    refs = []

    def make():
        P = [[("secret", i, 0)] for i in range(N)]
        Q = [[] for _ in range(N)]
        L = []
        for i in range(N):
            L.append(P[i]); L.append(Q[i])
        def cb(_ref):
            state["n"] += 1
            k = state["n"]
            if k < K:
                arm(cb)
            for p in P:
                p.clear()  # the tuples walked so far are freed here
            for i, q in enumerate(Q):
                q.append(("new", i, k))  # new tuples of that size: the freed addresses come back
            for i, p in enumerate(P):
                p.append(("secret", i, k))
        return L, cb

    def arm(cb):
        s = set(); d = {"s": s}; d["d"] = d
        refs.append(weakref.ref(s, cb))

    if entry in ("freeze", "settle"):
        L, cb = make()
        gc.collect()
        arm(cb)
        out = V.freeze(L) if entry == "freeze" else V.settle(L)
        got = [list(out[2 * i + 1]) for i in range(N)]
    else:
        seen = []
        T0 = 1_700_000_000_000_000_000
        class Fill(ImmediateFillModel):
            def on_order(self, order, t):
                seen.append(order.extra_dict()["k"])
                return super().on_order(order, t)
        class S:
            n = 0
            def on_event(self, ev, ctx):
                S.n += 1
                if S.n == 1:
                    L, cb = make()
                    gc.collect()
                    arm(cb)
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0,
                                                 client_order_id="o1", extra=(("k", L),)))
        bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0,
                         volume=1.0) for k in (0, 10, 20)]
        CoreEngine(S(), bars, fill_model=Fill(100.0), account=RecordingAccount(),
                   cost_model=NullCostModel()).run()
        got = [list(seen[0][2 * i + 1]) for i in range(N)]
    held = lambda i, x: x == [("new", i, k) for k in range(1, len(x) + 1)]  # a state Q_i held
    bad = [(i, got[i]) for i in range(N) if not held(i, got[i])]
    print(state["n"] >= 2, len(bad), bad[:3])
""")


@pytest.mark.parametrize("K", [3, 6])
@pytest.mark.parametrize("entry", ["freeze", "settle", "extra_dict"])
def test_a_rebuilt_container_is_never_put_where_another_object_now_is(entry, K):
    env = {**os.environ, "PYTHONPATH": SRC}
    out = subprocess.run([sys.executable, "-c", CHILD, entry, "400", str(K)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr[-2000:]
    changed, nbad, sample = out.stdout.strip().splitlines()[-1].split(" ", 2)
    assert changed == "True", f"{entry} K={K}: fewer than 2 changes ran during the walk (cell not measured)"
    assert nbad == "0", (f"{entry} K={K}: {nbad} of 400 places came out holding a value the sender's container "
                         f"never held (the copy of a container freed during the walk, whose id a new one got): "
                         f"{sample}")
