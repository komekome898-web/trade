"""Critic, item 0, round 15 (i0-r15-01): a refusal of plain data is the
entry's own error.

Contract `type_decisions`: "a refusal is the error type of the place it
enters (OrderApiError, VenueProtocolError, EventValidationError,
TimestampUnitError, LatencyModelError, CostModelError, AccountSocketError,
SourceEventTypeError)"; `values.settle`: anything it cannot take "raises
`Unsettled`, a ValueError"; `values.freeze`: "`ValueError` for anything that
is not plain data".

A sender CAN hold a signaling-NaN Decimal as a dict key or a set element:
its own Decimal subclass gives it a hash. The core reads the value by the
base type (PLAIN_DATA_RULE) and builds `PlainDecimal('sNaN')`, whose hash is
Decimal's C hash, which raises the built-in `TypeError("Cannot hash a
signaling NaN value")`. The core builds its dict / set of the new keys in
`_dict_of` / `_set_of`, outside any `try` that turns this into the entry's
error (`_walk` catches RecursionError only), so the built-in TypeError
escapes: from place_order in the strategy's call, from the settle of an
outbox message after on_event returned (the engine goes FAILED with a
TypeError), and from the core's rebuild of the account's forced order.

Grid: shape of the key {dict key; set element; set element inside a tuple;
frozenset element; key of a dict nested in a list} x entry {values.freeze;
values.settle; place_order inside on_event; an outbox message written around
place_order (settled after the callback); the account's forced order whose
extra slot the account set (rebuilt after its call)}. Oracle: the entry's
own error (ValueError / Unsettled / OrderApiError / AccountSocketError);
never the built-in TypeError.

Not in the grid: an sNaN as a dict VALUE or list element (taken, like the
library's Decimal: nothing hashes it), and the public FrozenDict(...)
constructor called by a user.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from bot.bt.core import BarEvent, CoreEngine, values
from bot.bt.core.api import OrderRequest
from bot.bt.core.errors import AccountSocketError, OrderApiError
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount

T0 = 1_700_000_000_000_000_000


class HashedDecimal(Decimal):
    """The sender's Decimal: a hash for every value (a signaling NaN too)."""

    def __hash__(self):
        return 7


def _shapes():
    k = HashedDecimal("sNaN")
    return {
        "dict-key": {k: 1},
        "set-element": {k},
        "set-element-in-tuple": {(k,)},
        "frozenset-element": frozenset([k]),
        "nested-dict-key": [{"a": {k: 1}}],
    }


SHAPES = list(_shapes())


@pytest.mark.parametrize("shape", SHAPES)
def test_freeze_refuses_with_its_own_error(shape):
    value = _shapes()[shape]
    try:
        values.freeze(value)
        got = None
    except BaseException as exc:  # noqa: BLE001 - judged below
        got = exc
    assert isinstance(got, ValueError), f"freeze of an sNaN {shape}: {type(got).__name__}: {got}"


@pytest.mark.parametrize("shape", SHAPES)
def test_settle_refuses_with_unsettled(shape):
    value = _shapes()[shape]
    try:
        values.settle(value)
        got = None
    except BaseException as exc:  # noqa: BLE001 - judged below
        got = exc
    assert isinstance(got, values.Unsettled), f"settle of an sNaN {shape}: {type(got).__name__}: {got}"


def _bars():
    return [BarEvent(received_time_ns=T0 + k, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
            for k in (0, 10, 20)]


@pytest.mark.parametrize("shape", SHAPES)
def test_place_order_refuses_with_order_api_error(shape):
    seen = []

    class S:
        n = 0

        def on_event(self, ev, ctx):
            S.n += 1
            if S.n == 1:
                try:
                    ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1",
                                                 extra=(("k", _shapes()[shape]),)))
                    seen.append(None)
                except BaseException as exc:  # noqa: BLE001 - judged below
                    seen.append(exc)

    CoreEngine(S(), _bars(), fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
               cost_model=NullCostModel()).run()
    assert isinstance(seen[0], OrderApiError), f"place_order with an sNaN {shape}: {type(seen[0]).__name__}"


def _outbox(ctx):
    return object.__getattribute__(ctx, "_StrategyContext__place_order_cb").__self__[2]


@pytest.mark.parametrize("shape", SHAPES)
def test_an_outbox_message_is_refused_with_order_api_error(shape):
    class S:
        n = 0

        def on_event(self, ev, ctx):
            S.n += 1
            if S.n == 1:
                req = OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="o1")
                object.__setattr__(req, "extra", (("k", _shapes()[shape]),))
                list.append(_outbox(ctx), ("new", req, ev.received_time_ns))

    eng = CoreEngine(S(), _bars(), fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
                     cost_model=NullCostModel())
    with pytest.raises(BaseException) as info:
        eng.run()
    assert isinstance(info.value, OrderApiError), \
        f"an outbox message with an sNaN {shape}: the engine failed with {type(info.value).__name__}"


@pytest.mark.parametrize("shape", SHAPES)
def test_the_accounts_forced_order_is_refused_with_account_socket_error(shape):
    class Forcing(RecordingAccount):
        def on_market_event(self, event, t):
            super().on_market_event(event, t)
            if event.received_time_ns == T0 + 10:
                req = OrderRequest(side="sell", order_type="market", size=1.0, client_order_id="f1")
                object.__setattr__(req, "extra", (("k", _shapes()[shape]),))
                return [req]
            return []

    class Quiet:
        def on_event(self, ev, ctx):
            pass

    eng = CoreEngine(Quiet(), _bars(), fill_model=ImmediateFillModel(100.0), account=Forcing(),
                     cost_model=NullCostModel())
    with pytest.raises(BaseException) as info:
        eng.run()
    assert isinstance(info.value, AccountSocketError), \
        f"the account's forced order with an sNaN {shape}: the engine failed with {type(info.value).__name__}"
