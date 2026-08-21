"""Order manager: drives the store + gateway with safe submit/reconcile flow."""
from __future__ import annotations

import logging
from dataclasses import replace

from bot.exchange.bitflyer_client import BitflyerError, OrderStateUnknown
from bot.execution.gateway import ExecutionGateway
from bot.order_management.order import Order, OrderState, OrderStore
from bot.order_management.reconciler import AutoReconciler, ExchangeSnapshot
from bot.risk.kill_switch import KillReason, KillSwitch

logger = logging.getLogger("bot.orders")

_GATEWAY_TO_LOCAL = {
    "ACTIVE": OrderState.SUBMITTED,
    "COMPLETED": OrderState.FILLED,
    "CANCELED": OrderState.CANCELED,
    "REJECTED": OrderState.REJECTED,
    "EXPIRED": OrderState.CANCELED,
}

# AutoReconciler outcomes -> local states. NOT_PLACED closes the record as
# REJECTED, the same terminal state `reconcile_unknown` uses when the exchange
# definitively has no such order.
_RESOLUTION_TO_LOCAL = {
    "FILLED": OrderState.FILLED,
    "ACTIVE": OrderState.SUBMITTED,
    "CANCELED": OrderState.CANCELED,
    "REJECTED": OrderState.REJECTED,
    "NOT_PLACED": OrderState.REJECTED,
}


class OrderManager:
    def __init__(self, store: OrderStore, gateway: ExecutionGateway,
                 kill_switch: KillSwitch, *,
                 reconciler: AutoReconciler | None = None, notifier=None):
        self._store = store
        self._gateway = gateway
        self._kill_switch = kill_switch
        # Query-only, bounded auto-reconciliation of an ambiguous send. None in
        # PAPER mode: the executor is local, so ambiguity cannot arise.
        self._reconciler = reconciler
        self._notifier = notifier

    def submit(self, *, symbol: str, side: str, size: float,
               order_type: str = "MARKET", price: float | None = None) -> Order:
        """Persist first, then submit.

        An ambiguous failure is handed to the QUERY-ONLY auto-reconciler, which
        has a bounded budget to prove what happened from getchildorders /
        getpositions. Resolved -> the record takes the true state and trading
        continues. Unresolved (or no reconciler at all) -> STATE_UNKNOWN, kill
        switch, operator alert. Either way the order is NEVER resent (rule 12).
        """
        if self._store.unknown_orders():
            raise RuntimeError("orders with unknown state exist; reconcile before submitting")
        snapshot = self._pre_send_snapshot(symbol)
        order = self._store.create(symbol, side, size, order_type, price)
        try:
            result = self._gateway.submit_order(
                symbol=symbol, side=side, size=size, order_type=order_type, price=price
            )
        except OrderStateUnknown as e:
            order = self._store.transition(order.local_id, OrderState.STATE_UNKNOWN)
            resolved = self._auto_reconcile(order, symbol, side, size, snapshot)
            if resolved is not None:
                return resolved
            self._kill_switch.trip(KillReason.ORDER_STATE_UNKNOWN, str(e))
            logger.error("order state unknown after submit", extra={"data": {
                "event": "order_state_unknown", "local_id": order.local_id,
                "auto_reconciled": False}})
            self._alert_unknown(order)
            return order
        except (BitflyerError, ValueError) as e:
            order = self._store.transition(order.local_id, OrderState.REJECTED)
            logger.warning("order rejected", extra={"data": {
                "event": "order_rejected", "local_id": order.local_id, "error": str(e)}})
            return order
        return self._store.transition(order.local_id, OrderState.SUBMITTED,
                                      acceptance_id=result.acceptance_id)

    # ---- automatic, query-only reconciliation ------------------------------
    def _pre_send_snapshot(self, symbol: str) -> ExchangeSnapshot | None:
        """Acceptance ids + position size as they are BEFORE the send.

        Costs two read-only GETs before every LIVE send. That is deliberate:
        without a baseline there is nothing to diff an ambiguous failure
        against, and the alternative to a diff is a human at 3am.

        The ids the local book already knows are unioned in, so an acceptance
        id we recorded earlier can never be mistaken for the order we are about
        to send even if the snapshot poll happened to omit it.

        Best effort: if the snapshot cannot be taken there is nothing to diff
        against, so auto-reconciliation is simply skipped for this order and
        the existing STATE_UNKNOWN path stands. It must never block a send.
        """
        if self._reconciler is None:
            return None
        try:
            snapshot = self._reconciler.snapshot(symbol)
            return replace(snapshot, acceptance_ids=frozenset(
                snapshot.acceptance_ids | self._store.known_acceptance_ids()))
        except Exception as e:
            logger.warning("pre-send snapshot failed; auto-reconciliation disabled "
                           "for this order", extra={"data": {
                               "event": "presend_snapshot_failed",
                               "error": type(e).__name__}})
            return None

    def _auto_reconcile(self, order: Order, symbol: str, side: str, size: float,
                        snapshot: ExchangeSnapshot | None) -> Order | None:
        """Resolve STATE_UNKNOWN from read-only endpoints. None = still unknown.

        Nothing in this path can send an order: the reconciler holds a
        QueryOnlyExchange, which has no send/cancel method at all.
        """
        if self._reconciler is None or snapshot is None:
            return None
        try:
            res = self._reconciler.resolve(symbol=symbol, side=side, size=size,
                                           snapshot=snapshot)
        except Exception:
            logger.exception("auto-reconciliation failed; order stays STATE_UNKNOWN")
            return None
        if not res.resolved:
            logger.error("auto-reconciliation exhausted its budget", extra={"data": {
                "event": "reconcile_unresolved", "local_id": order.local_id,
                "polls": res.polls, "elapsed_sec": round(res.elapsed_sec, 2),
                "detail": res.detail}})
            return None
        new_state = _RESOLUTION_TO_LOCAL.get(res.state)
        if new_state is None:      # pragma: no cover - defensive
            return None
        resolved = self._store.transition(
            order.local_id, new_state, acceptance_id=res.acceptance_id,
            filled_size=res.filled_size or None,
            avg_fill_price=res.avg_fill_price)
        logger.warning("order state auto-reconciled", extra={"data": {
            "event": "order_auto_reconciled", "local_id": order.local_id,
            "resolution": res.state, "state": new_state.value,
            "polls": res.polls, "elapsed_sec": round(res.elapsed_sec, 2),
            "detail": res.detail}})
        return resolved

    def _alert_unknown(self, order: Order) -> None:
        """Tell the operator a human decision is now required. A dead webhook
        must not raise on top of an already-unknown order state."""
        if self._notifier is None:
            return
        try:
            self._notifier.send(
                "ORDER STATE UNKNOWN",
                f"{order.side} {order.size} {order.symbol} could not be resolved "
                f"automatically within the reconciliation budget. Trading is "
                f"stopped and the order will NOT be resent. Check the order on "
                f"bitFlyer, then reconcile and reset the kill switch by hand.",
                urgent=True)
        except Exception:
            logger.exception("unknown-state alert failed")

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
