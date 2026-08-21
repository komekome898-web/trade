"""Order creation/cancel/fill confirmation, duplicate prevention and
unknown-state reconciliation (items 5-8 and rule 12)."""
from __future__ import annotations

import pytest

from bot.exchange.bitflyer_client import OrderStateUnknown
from bot.execution.gateway import ExecutionGateway, OrderStatus, SubmitResult
from bot.order_management.manager import OrderManager
from bot.order_management.order import (
    DuplicateOrderError, InvalidTransition, OrderState, OrderStore,
)
from bot.risk.kill_switch import KillReason, KillSwitch


class ScriptedGateway(ExecutionGateway):
    def __init__(self):
        self.submitted = []
        self.canceled = []
        self.fail_with: Exception | None = None
        self.status: OrderStatus | None = None

    def submit_order(self, *, symbol, side, size, order_type, price):
        if self.fail_with:
            raise self.fail_with
        self.submitted.append((symbol, side, size))
        return SubmitResult(acceptance_id=f"ACC-{len(self.submitted)}")

    def cancel_order(self, *, symbol, acceptance_id):
        self.canceled.append(acceptance_id)

    def fetch_order_status(self, *, symbol, acceptance_id):
        return self.status


@pytest.fixture
def store(tmp_path):
    return OrderStore(tmp_path / "orders.sqlite3")


@pytest.fixture
def gateway():
    return ScriptedGateway()


@pytest.fixture
def manager(store, gateway, tmp_path):
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    return OrderManager(store, gateway, ks)


def test_order_created_and_submitted(manager, store, gateway):
    order = manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    assert order.state is OrderState.SUBMITTED
    assert order.acceptance_id == "ACC-1"
    assert gateway.submitted == [("XRP_JPY", "BUY", 10.0)]


def test_duplicate_order_prevented(manager, store):
    manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    with pytest.raises(DuplicateOrderError):
        store.create("XRP_JPY", "BUY", 10.0, "MARKET", None)


def test_ambiguous_failure_marks_unknown_trips_kill_and_blocks_resend(
        manager, store, gateway, tmp_path):
    gateway.fail_with = OrderStateUnknown("timeout on send")
    order = manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    assert order.state is OrderState.STATE_UNKNOWN
    ks = KillSwitch(state_dir=tmp_path, manual_file=tmp_path / "KILL")
    assert ks.is_tripped and ks.state["reason"] == KillReason.ORDER_STATE_UNKNOWN.value
    gateway.fail_with = None
    with pytest.raises(RuntimeError, match="unknown state"):
        manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    assert len(gateway.submitted) == 0  # nothing was ever resent


def test_reconcile_unknown_order_found_filled(manager, store, gateway):
    gateway.fail_with = OrderStateUnknown("timeout")
    order = manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    resolved = manager.reconcile_unknown(
        lambda o: OrderStatus("ACC-X", "COMPLETED", 10.0, 100.0))
    assert resolved[0].state is OrderState.FILLED
    assert resolved[0].avg_fill_price == 100.0
    assert store.unknown_orders() == []


@pytest.mark.parametrize("answer", [
    None,                                          # the query came back empty
    OrderStatus("ACC-X", "UNKNOWN", 0.0, None),    # the caller could not tell
    OrderStatus("ACC-X", "", 0.0, None),
])
def test_reconcile_unknown_keeps_unconfirmed_orders_unknown(manager, store,
                                                            gateway, answer):
    """(m7) Only an explicit exchange state resolves a record. 'Not found' is
    absence of evidence — closing it as REJECTED is how the book goes flat
    while the venue still holds a live order."""
    gateway.fail_with = OrderStateUnknown("timeout")
    manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    resolved = manager.reconcile_unknown(lambda o: answer)
    assert resolved == []
    assert [o.state for o in store.unknown_orders()] == [OrderState.STATE_UNKNOWN]


def test_reconcile_unknown_resolves_a_confirmed_cancel(manager, store, gateway):
    gateway.fail_with = OrderStateUnknown("timeout")
    manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    resolved = manager.reconcile_unknown(
        lambda o: OrderStatus("ACC-X", "CANCELED", 0.0, None))
    assert resolved[0].state is OrderState.CANCELED
    assert store.unknown_orders() == []


def test_fill_confirmation_via_refresh(manager, gateway):
    order = manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    gateway.status = OrderStatus(order.acceptance_id, "COMPLETED", 10.0, 101.5)
    order = manager.refresh(order)
    assert order.state is OrderState.FILLED
    assert order.filled_size == 10.0
    assert order.avg_fill_price == 101.5


def test_cancel_all_active(manager, gateway):
    order = manager.submit(symbol="XRP_JPY", side="BUY", size=10.0)
    canceled = manager.cancel_all_active("XRP_JPY")
    assert [o.local_id for o in canceled] == [order.local_id]
    assert canceled[0].state is OrderState.CANCELED
    assert gateway.canceled == [order.acceptance_id]


def test_invalid_state_transition_rejected(store):
    order = store.create("XRP_JPY", "BUY", 1.0, "MARKET", None)
    store.transition(order.local_id, OrderState.REJECTED)
    with pytest.raises(InvalidTransition):
        store.transition(order.local_id, OrderState.FILLED)  # terminal -> anything
