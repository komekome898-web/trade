"""Order manager: drives the store + gateway with safe submit/reconcile flow."""
from __future__ import annotations

import logging

from bot.exchange.bitflyer_client import BitflyerError, OrderStateUnknown
from bot.execution.gateway import ExecutionGateway
from bot.order_management.order import (
    DuplicateOrderError, Order, OrderState, OrderStore,
)
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
               order_type: str = "MARKET", price: float | None = None,
               opening: bool = True) -> Order:
        """Persist first, then submit.

        An ambiguous failure is handed to the QUERY-ONLY auto-reconciler, which
        has a bounded budget to find POSITIVE evidence of the order on
        getchildorders. Found -> the record takes the state the exchange
        reports and trading continues. Not found, or no reconciler at all ->
        STATE_UNKNOWN, kill switch, operator alert; never "assumed not placed".
        Either way the order is NEVER resent (rule 12).

        `opening` says what the order is FOR, and only the CLOSING case may act
        on it: a close outranks anything resting on the book (see
        `_make_room_for_close`). An entry refused because an order already
        exists is simply skipped, as before.
        """
        if self._store.unknown_orders():
            raise RuntimeError("orders with unknown state exist; reconcile before submitting")
        snapshot = self._baseline(symbol)
        try:
            order = self._store.create(symbol, side, size, order_type, price)
        except DuplicateOrderError as refusal:
            if opening:
                raise
            order = self._make_room_for_close(symbol, side, size, order_type,
                                              price, refusal)
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

    # ---- a CLOSING order outranks the book ---------------------------------
    def _make_room_for_close(self, symbol: str, side: str, size: float,
                             order_type: str, price: float | None,
                             refusal: DuplicateOrderError) -> Order:
        """Clear resting orders so a CLOSING order can be placed, ONCE.

        The wedge this exists for: an ambiguous send resolves to ACTIVE, so the
        book holds a live SUBMITTED order; the venue never fills it; the
        protective stop then asks for a new order and `OrderStore.create`
        refuses it — the duplicate-order guard silently refusing the one order
        that must never be refused. That is the 2019 failure with a different
        cause: a position that cannot be exited.

        Cancelling is safe in a way sending is not — it is idempotent, and
        cancelling an order that is already gone changes nothing — so the
        resting order is cancelled and the close retried exactly once. If it is
        STILL refused, the bot cannot flatten and a human must: urgent alert
        plus a tripped kill switch, never a quiet `submit_refused` log line.
        """
        resting = [o.local_id for o in self._store.active_orders(symbol)]
        try:
            canceled = self.cancel_all_active(symbol)
        except Exception as e:
            self._closing_blocked(symbol, side, size, resting,
                                  f"cancel failed ({type(e).__name__}: {e})")
            raise refusal from None
        logger.warning("resting orders cancelled to clear a closing order",
                       extra={"data": {"event": "closing_order_priority",
                                       "symbol": symbol, "side": side,
                                       "size": size, "canceled": canceled,
                                       "resting": resting}})
        try:
            return self._store.create(symbol, side, size, order_type, price)
        except DuplicateOrderError as e:
            self._closing_blocked(symbol, side, size, resting,
                                  f"still refused after cancelling: {e}")
            raise

    def _closing_blocked(self, symbol: str, side: str, size: float,
                         resting: list[str], detail: str) -> None:
        """The bot cannot close. Say so as loudly as the system allows."""
        logger.critical("closing order blocked", extra={"data": {
            "event": "closing_order_blocked", "symbol": symbol, "side": side,
            "size": size, "resting": resting, "detail": detail}})
        self._alert(
            "CANNOT CLOSE POSITION",
            f"The protective/closing order {side} {size} {symbol} could not be "
            f"placed: it is blocked by order(s) {resting} and {detail}. Trading "
            f"is stopped. The exchange may still hold both the resting order "
            f"and the position — check bitFlyer, flatten by hand if you need "
            f"to, then reconcile and reset the kill switch.")
        self._kill_switch.trip(
            KillReason.SYSTEM_ERROR,
            f"closing order {side} {size} {symbol} blocked by {resting}: {detail}")

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

    def _alert(self, title: str, message: str) -> None:
        """Urgent operator alert. A dead webhook must never raise on top of the
        order-state problem it is trying to report."""
        if self._notifier is None:
            return
        try:
            self._notifier.send(title, message, urgent=True)
        except Exception:
            logger.exception("operator alert failed")

    def _alert_unknown(self, order: Order) -> None:
        """Tell the operator a human decision is now required."""
        self._alert(
            "ORDER STATE UNKNOWN",
            f"{order.side} {order.size} {order.symbol} could not be resolved "
            f"automatically within the reconciliation budget. The exchange "
            f"may or may not hold it. Trading is stopped and the order will "
            f"NOT be resent — and while the kill switch is tripped the bot "
            f"cannot CLOSE anything either. Check the order on bitFlyer, "
            f"flatten by hand if you need to, then reconcile and reset the "
            f"kill switch.")

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
        """Resolve STATE_UNKNOWN/PENDING_SUBMIT orders from CONFIRMED answers.

        lookup_fn(order) -> OrderStatus | None: the operator's query against
        getchildorders, by acceptance id or by (product, side, size, time
        window). It answers with what the EXCHANGE said, and only an explicit
        exchange state — ACTIVE / COMPLETED / CANCELED / EXPIRED / REJECTED —
        resolves the record.

        Everything else keeps STATE_UNKNOWN, deliberately:

        - `None` means the query came back with nothing. That is the absence of
          evidence, not evidence of absence — it used to close the record as
          REJECTED, the same ghost-order path the AUTOMATIC reconciler had
          already been fixed for (bot/order_management/reconciler.py). A venue
          that is lagging its own listing would have the bot believe it is flat
          while a real position is open.
        - a state string of "UNKNOWN", or anything unrecognised, is the caller
          saying it could not tell. It used to fall back to SUBMITTED, which
          invents an order on the book.

        Returns only the orders that were actually resolved. Whatever is left
        is still in `unknown_orders()` and still needs a human.
        """
        resolved = []
        for order in self._store.unknown_orders():
            status = lookup_fn(order)
            state = None if status is None else _GATEWAY_TO_LOCAL.get(
                str(getattr(status, "state", "")).upper())
            if state is None:
                logger.warning("manual reconcile: no confirmed state; order "
                               "stays STATE_UNKNOWN", extra={"data": {
                                   "event": "reconcile_unconfirmed",
                                   "local_id": order.local_id,
                                   "reported": (None if status is None
                                                else str(status.state))}})
                continue
            resolved.append(self._store.transition(
                order.local_id, state,
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
