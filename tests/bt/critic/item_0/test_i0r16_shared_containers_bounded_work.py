"""Critic, item 0, round 16 (i0-r16-03): the work of taking plain data is not
bounded by what the sender hands over.

The core's walk (values.py `_walk`, freeze / settle / renew / thaw) rebuilds
a container once per PATH to it, not once per object: a value whose
containers are SHARED (a DAG, not a cycle -- `_walk` refuses only a
container on its own path) is rebuilt as the tree it unfolds to. A sender
holding n + 1 tuples, t_k = (t_{k-1}, t_{k-1}), hands over a value of
nesting n (within MAX_NESTING = 100) that the core rebuilds as 2**n tuples:
freeze took 0.65 s at n = 18, 2.8 s at n = 20, 11.7 s at n = 22
(<S>/r16_critic/item0_r16_critic_probe_shared_dag.out); at n = 40 the run
never ends, whether the value comes through place_order in the strategy's
call or through the outbox the engine settles after on_event returned. No
value is wrong; the core neither takes nor refuses.

Grid: entry {values.freeze; values.settle} x nesting {30}, each in a child
process with a time limit of 20 s. Oracle: the entry returns or refuses
(ValueError) within the limit.

Not in the grid: a DAG of lists / dicts (the same walk), and the engine's
outbox (the same settle).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

CHILD = textwrap.dedent("""
    import sys
    from bot.bt.core import values
    t = ()
    for _ in range({n}):
        t = (t, t)
    try:
        values.{entry}(t)
        print("taken")
    except ValueError:
        print("refused")
""")


@pytest.mark.parametrize("entry", ["freeze", "settle"])
def test_a_shared_value_is_taken_or_refused_in_bounded_time(entry):
    code = CHILD.format(n=30, entry=entry)
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=20,
                             env={**__import__("os").environ})
        done = out.stdout.strip()
    except subprocess.TimeoutExpired:
        done = "timeout"
    assert done in ("taken", "refused"), (f"{entry} of a value whose 31 tuples each hold the one below twice "
                                          f"(nesting 30): {done} after 20 s")
