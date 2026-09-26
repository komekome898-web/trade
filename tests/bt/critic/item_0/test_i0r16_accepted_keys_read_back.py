"""Critic, item 0, round 16 (i0-r16-02): plain data the core ACCEPTS must
read back.

values.py (module docstring): containers "each remembers what it was, so
`thaw` gives back a fresh list / dict / set"; PLAIN_DATA_RULE: containers of
plain data "become new immutable containers and are read back as fresh
copies"; api.py `OrderRequest.extra_dict()`: "`extra` as a fresh dict, lists
/ dicts / sets as they were given (values.py `thaw`)". Round 16 (worker's
ROOTCAUSE §4): "the receiver's thaw and renew make containers only from
containers the core made (a key had a hash when it was made), so they are
not changed".

`freeze` takes a dict key or a set element that is a container the core
itself builds -- a FrozenDict or a FrozenSet made with the public
constructor, a tuple holding a FrozenList -- and keeps its class. `thaw`
then turns that key into a dict / set / list (what it "was") and builds the
fresh dict or set of such keys: the interpreter raises
`TypeError: unhashable type`. So a value the core took at the entry cannot
be read by the receiver: a fill model reading `order.extra_dict()` in its
own call gets the interpreter's TypeError
(<S>/r16_critic/item0_r16_critic_probe_thaw_container_keys.out).

Grid: shape {FrozenDict as a dict key; FrozenSet as a dict key; a tuple
holding a FrozenList as a dict key; FrozenDict as a set element; FrozenSet
in a frozenset} x reader {values.thaw; the fill model's
order.extra_dict() in the engine}. Oracle: what freeze accepted reads back
as a value equal to what was given (or freeze refuses it with ValueError).

Not in the grid: a dict subclass with a __hash__ as a key (read as a dict,
built as a FrozenDict: the same path).
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, CoreEngine, values
from bot.bt.core.api import OrderRequest
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

T0 = 1_700_000_000_000_000_000

SHAPES = {
    "frozendict-dict-key": lambda: {values.FrozenDict({"a": 1}): 3},
    "frozenset-class-dict-key": lambda: {values.FrozenSet({1}): 3},
    "tuple-holding-frozenlist-key": lambda: {(values.FrozenList([1]),): 3},
    "frozendict-set-element": lambda: {values.FrozenDict({"a": 1})},
    "frozenset-class-in-frozenset": lambda: frozenset({values.FrozenSet({1})}),
}


@pytest.mark.parametrize("shape", list(SHAPES))
def test_thaw_reads_back_what_freeze_took(shape):
    given = SHAPES[shape]()
    try:
        frozen = values.freeze(given)
    except ValueError:
        return  # refused at the entry: allowed
    try:
        back = values.thaw(frozen)
        got = None
    except BaseException as exc:  # noqa: BLE001 - judged below
        back, got = None, exc
    assert got is None, f"freeze took {shape}; thaw raised {type(got).__name__}: {got}"
    assert back == given


@pytest.mark.parametrize("shape", list(SHAPES))
def test_a_fill_model_reads_the_extra_of_an_accepted_order(shape):
    seen: list = []
    placed: list = []

    class Reader(ImmediateFillModel):
        def on_order(self, order, venue_time_ns):
            try:
                seen.append(order.extra_dict())
            except BaseException as exc:  # noqa: BLE001 - judged below
                seen.append(exc)
            return super().on_order(order, venue_time_ns)

    class S:
        n = 0

        def on_event(self, ev, ctx):
            S.n += 1
            if S.n == 1:
                try:
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1",
                                                 extra=(("k", SHAPES[shape]()),)))
                    placed.append(True)
                except BaseException:  # noqa: BLE001 - a refusal at the entry is allowed
                    placed.append(False)

    bars = [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]
    CoreEngine(S(), bars, fill_model=Reader(100.0), account=RecordingAccount(), cost_model=NullCostModel()).run()
    if placed == [False]:
        return
    assert seen and not isinstance(seen[0], BaseException), \
        f"the order with {shape} was accepted; the fill model's extra_dict() raised {type(seen[0]).__name__}: {seen[0]}"
    assert seen[0] == {"k": SHAPES[shape]()}
