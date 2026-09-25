"""Critic, item 0, round 14 (i0-r14-05): contract core-15 `process_state`:
"plain data nests at most MAX_NESTING containers, counted from the field that
holds it (the core's own bound, not the recursion limit or the stack depth of
the call)", and the lead's answer to the worker (VERDICTS run11 item0, round
14) reads the worker's grid 4 as showing that the refusal is "the core's
typed refusal, not RecursionError". The worker's grid 4 tries only two stack
depths of the strategy's own, {0, 300} frames.

Grid: the strategy's own stack depth when it calls place_order {0, 300, 600,
800, 900} x nesting of `extra` within the bound {10, 50, MAX_NESTING - 2}.
Oracle: an order whose extra nests within the bound is taken (or refused by
OrderApiError) the same way at every depth -- never RecursionError.

Not in the grid: a recursion limit lowered by a party (the contract's "not
covered"); depths above 900 (the interpreter's default limit is 1000).
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, CoreEngine
from bot.bt.core.api import OrderRequest
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
from bot.bt.core.values import MAX_NESTING

T0 = 1_700_000_000_000_000_000


def _nested(n):
    v = 1
    for _ in range(n):
        v = [v]
    return v


def _at_depth(k, fn):
    if k <= 0:
        return fn()
    return _at_depth(k - 1, fn)


def _place_at(depth, nest):
    class S:
        out = None

        def on_event(self, ev, ctx):
            if S.out is not None or type(ev).__name__ != "BarEvent":
                return
            try:
                _at_depth(depth, lambda: ctx.place_order(OrderRequest(
                    side="buy", order_type="market", size=1.0, client_order_id="o1",
                    extra=(("k", _nested(nest)),))))
                S.out = "taken"
            except BaseException as exc:  # noqa: BLE001 - the kind of refusal is what is measured
                S.out = type(exc).__name__

    CoreEngine(S(), [BarEvent(received_time_ns=T0, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)],
               fill_model=ImmediateFillModel(1.0), account=RecordingAccount(), cost_model=NullCostModel()).run()
    return S.out


@pytest.mark.parametrize("nest", [10, 50, MAX_NESTING - 2])
@pytest.mark.parametrize("depth", [0, 300, 600, 800, 900])
def test_an_order_within_the_nesting_bound_is_taken_alike_at_every_stack_depth(depth, nest):
    at_top = _place_at(0, nest)
    here = _place_at(depth, nest)
    assert here == at_top, (f"extra nesting {nest} (<= MAX_NESTING {MAX_NESTING}) from the strategy's stack depth "
                            f"{depth}: {here}; from depth 0: {at_top}")
