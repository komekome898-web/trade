"""Critic, item 0, round 11 (i0-r11-03): a strategy that only HOLDS a
read-only view of what it can reach makes the core's own step fail.

The facts of dropped events live in two `array('q')` per type on the
strategy's side (history.py `HistoryLists`), reachable from the context
through the default of its `dropped_of` function. The core extends them at
every drop (`array.array.extend`, a base-type C function), and the contract
says the strategy changing anything it reaches "by any means ... reaches
only what the strategy itself reads" and the engine docstring "nothing it
changes there, by any means, reaches the core, the venue, another receiver
or the caller's result". A `memoryview` of such an array writes nothing, but
while it exists the array cannot be resized: the core's `array.extend` at the
next drop raises BufferError, inside the core's step, outside on_event, and
the run is over.

Oracle (the contract's words): holding views of what the strategy reaches
leaves the run's result equal to the run without them.
Not in the grid: other buffer exporters (bytearray: none is reachable).
"""
from __future__ import annotations

import gc
import types
from array import array

from bot.bt.core import CoreEngine, TradeEvent

T0 = 1_700_000_000_000_000_000
SEC = 1_000_000_000


def _arrays(ctx) -> list:
    seen, todo, out = set(), [ctx], []
    while todo:
        o = todo.pop()
        if id(o) in seen or isinstance(o, (type, types.ModuleType)):
            continue
        seen.add(id(o))
        if type(o) is array:
            out.append(o)
        elif isinstance(o, types.FunctionType):
            todo.extend(o.__closure__ or ())
            todo.extend(o.__defaults__ or ())
        elif isinstance(o, types.CellType):
            try:
                todo.append(o.cell_contents)
            except ValueError:
                pass
        elif isinstance(o, types.MethodType):
            todo.append(o.__self__)
        else:
            todo.extend(gc.get_referents(o))
    return out


def _run(hold: bool):
    views: list = []

    class S:
        def on_event(self, ev, ctx):
            if hold and not views:
                views.extend(memoryview(a) for a in _arrays(ctx))

    evs = [TradeEvent(received_time_ns=T0 + i * SEC, price=100.0 + i, size=1.0, side="buy") for i in range(12)]
    res = CoreEngine(S(), evs, history_limit=1).run()
    return views, (res.events_processed, res.delivery_digest)


def test_holding_views_of_the_dropped_facts_does_not_change_the_run():
    _, plain = _run(False)
    views, held = _run(True)
    assert views, "the probe found no array on the strategy's side"
    assert held == plain
