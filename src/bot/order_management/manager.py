"""Order manager: drives the store + gateway with safe submit/reconcile flow."""
from __future__ import annotations

import logging

from bot.exchange.bitflyer_client import BitflyerError, OrderStateUnknown
from bot.execution.gateway import ExecutionGateway
from bot.order_management.order import Order, OrderState, OrderStore
from bot.risk.kill_switch import KillReason, KillSwitch

logger = logging.getLogger("bot.orders")

_GATEWAY_TO_LOCAL = {
    "ACTIVE": OrderState.SUBMITTED,
    "COMPLETED": OrderState.FILLED,
    "CANCELED": OrderState.CANCELED,
    "REJECTED": OrderState.REJECTED,
    "EXPIRED": OrderState.CANCELED,
}


class OrderManager:
    def __init__(self, store: OrderStore, gateway: ExecutionGateway, kill_switch: KillSwitch):
        self._store = store
        self._gateway = gateway
        self._kill_switch = kill_switch

    def submit(self, *, symbol: str, side: str, size: float,
               order_type: str = "MARKET", price: float | None = None) -> Order:
        """Persist first, then submit. Ambiguous failures leave STATE_UNKNOWN and
        trip the kill switch — the bot never blindly resends (rule 12)."""
        if self._store.unknown_orders():
            raise RuntimeError("orders with unknown state exist; reconcile before submitting")
        order = self._store.create(symbol, side, size, order_type, price)
        try:
            result = self._gateway.submit_order(
                symbol=symbol, side=side, size=size, order_type=order_type, price=price
            )
        except OrderStateUnknown as e:
            order = self._store.transition(order.local_id, OrderState.STATE_UNKNOWN)
            self._kill_switch.trip(KillReason.ORDER_STATE_UNKNOWN, str(e))
            logger.error("order state unknown after submit", extra={"data": {
                "event": "order_state_unknown", "local_id": order.local_id}})
            return order
        except (BitflyerError, ValueError) as e:
            order = self._store.transition(order.local_id, OrderState.REJECTED)
            logger.warning("order rejected", extra={"data": {
                "event": "order_rejected", "local_id": order.local_id, "error": str(e)}})
            return order
        return self._store.transition(order.local_id, OrderState.SUBMITTED,
                                      acceptance_id=result.acceptance_id)

    def refresh(self, order: Order) -> Order:
        """Poll the gateway for fill/cancel state of a submitted order."""
        if order.acceptance_id is None or order.is_terminal:
            return order
        status = self._gateway.fetch_order_status(
            symbol=order.symbol, acceptance_id=order.acceptance_id
        )
        if status is None:
            return order
        new_state = _GATEWAY_TO_LOCAL.get(status.state)
        if new_state is None or new_state == order.state:
            return order
        return self._store.transition(order.local_id, new_state,
                                      filled_size=status.filled_size,
                                      avg_fill_price=status.avg_fill_price)

    def reconcile_unknown(self, lookup_fn) -> list[Order]:
        """Resolve STATE_UNKNOWN/PENDING_SUBMIT orders by querying the exchange.

        lookup_fn(order) -> OrderStatus | None: caller queries getchildorders by
        acceptance id or by (product, side, size, time window). None means the
        exchange definitively has no such order -> safe to mark REJECTED.
        """
        resolved = []
        for order in self._store.unknown_orders():
            status = lookup_fn(order)
            if status is None:
                resolved.append(self._store.transition(order.local_id, OrderState.REJECTED))
            else:
                new_state = _GATEWAY_TO_LOCAL.get(status.state, OrderState.SUBMITTED)
                resolved.append(self._store.transition(
                    order.local_id, new_state,
                    acceptance_id=status.acceptance_id,
                    filled_size=status.filled_size,
                    avg_fill_price=status.avg_fill_price,
                ))
        return resolved

    def cancel_all_active(self, symbol: str) -> int:
        n = 0
        for order in self._store.active_orders(symbol):
            if order.acceptance_id and order.state in (OrderState.SUBMITTED,
                                                       OrderState.PARTIALLY_FILLED):
                self._gateway.cancel_order(symbol=symbol, acceptance_id=order.acceptance_id)
                self._store.transition(order.local_id, OrderState.CANCELED)
                n += 1
        return n
