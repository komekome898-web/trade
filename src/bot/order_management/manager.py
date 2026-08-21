"""Order manager: drives the store + gateway with safe submit/reconcile flow."""
from __future__ import annotations

import logging

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

# AutoReconciler outcomes -> local states. Every one of them is POSITIVE
# evidence: the exchange listed the order and said what it is. There is no
# "the exchange did not list it" outcome — that stays STATE_UNKNOWN for a
# human (bot/order_management/reconciler.py module docstring).
_RESOLUTION_TO_LOCAL = {
    "FILLED": OrderState.FILLED,
    "ACTIVE": OrderState.SUBMITTED,
    "CANCELED": OrderState.CANCELED,
    "REJECTED": OrderState.REJECTED,
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
        has a bounded budget to find POSITIVE evidence of the order on
        getchildorders. Found -> the record takes the state the exchange
        reports and trading continues. Not found, or no reconciler at all ->
        STATE_UNKNOWN, kill switch, operator alert; never "assumed not placed".
        Either way the order is NEVER resent (rule 12).
        """
        if self._store.unknown_orders():
            raise RuntimeError("orders with unknown state exist; reconcile before submitting")
        snapshot = self._baseline(symbol)
        order = self._store.create(symbol, side, size, order_type, price)
        try:
            result = self._gateway.submit_order(
                symbol=symbol, side=side, size=size, order_type=order_type, price=price
            )
        except OrderStateUnknown as e:
            order = self._store.transition(order.local_id, OrderState.STATE_UNKNOWN)
            resolved = self._auto_reconcile(order, symbol, side, size, snapshot,
                                            order_type=order_type, price=price)
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
    def _baseline(self, symbol: str) -> ExchangeSnapshot | None:
        """Acceptance ids that are already OURS, with ZERO network calls.

        The previous version issued two blocking GETs before every send. On the
        exit path that is exactly backwards: it put diagnostic I/O in front of
        the protective stop, on a venue that is degraded often enough for this
        whole module to exist. The baseline is instead the local book's known
        acceptance ids (bounded) plus whatever the reconciler saw on the venue
        during earlier resolves — it has to fetch getchildorders then anyway.

        Best effort: if even that cannot be assembled, auto-reconciliation is
        skipped for this order and the STATE_UNKNOWN path stands. It must never
        block a send.
        """
        if self._reconciler is None:
            return None
        try:
            return self._reconciler.baseline(self._store.known_acceptance_ids())
        except Exception as e:
            logger.warning("reconciliation baseline unavailable; auto-reconciliation "
                           "disabled for this order", extra={"data": {
                               "event": "reconcile_baseline_failed",
                               "error": type(e).__name__}})
            return None

    def _auto_reconcile(self, order: Order, symbol: str, side: str, size: float,
                        snapshot: ExchangeSnapshot | None, *,
                        order_type: str = "MARKET",
                        price: float | None = None) -> Order | None:
        """Resolve STATE_UNKNOWN from read-only endpoints. None = still unknown.

        Nothing in this path can send an order: the reconciler holds a
        QueryOnlyExchange, which has no send/cancel method at all.
        """
        if self._reconciler is None or snapshot is None:
            return None
        try:
            res = self._reconciler.resolve(symbol=symbol, side=side, size=size,
                                           snapshot=snapshot,
                                           order_type=order_type, price=price)
        except Exception:
            logger.exception("auto-reconciliation failed; order stays STATE_UNKNOWN")
            return None
        if not res.resolved:
            logger.error("auto-reconciliation found no evidence either way", extra={"data": {
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
                f"automatically within the reconciliation budget. The exchange "
                f"may or may not hold it. Trading is stopped and the order will "
                f"NOT be resent — and while the kill switch is tripped the bot "
                f"cannot CLOSE anything either. Check the order on bitFlyer, "
                f"flatten by hand if you need to, then reconcile and reset the "
                f"kill switch.",
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
