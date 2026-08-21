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

# Exchange states that mean "still on the book" — the ones a reported
# executed_size can refine into a PARTIAL fill.
_RESTING = {OrderState.SUBMITTED, OrderState.PENDING_SUBMIT}

# Below this a position is flat and a size is nothing. Same value as
# `bot.main.FILL_EPSILON`: both are "float noise on a venue-reported size".
_SIZE_EPSILON = 1e-12


def _with_partial(state: OrderState | None, filled_size: float | None) -> OrderState | None:
    """ACTIVE-with-executed_size is PARTIALLY_FILLED, not SUBMITTED.

    bitFlyer reports a partially filled child order as ACTIVE and carries the
    filled amount in `executed_size`. Mapping that to plain SUBMITTED threw the
    fill away: the book showed a resting order with nothing done, so the
    already-executed size was never booked into the portfolio and the bot
    believed it was flatter than it was. It also made the record un-updatable —
    a later refresh of a PARTIALLY_FILLED order that the venue still calls
    ACTIVE tried PARTIALLY_FILLED -> SUBMITTED, which is not a legal transition
    and raised InvalidTransition out of the sweep.
    """
    if state in _RESTING and (filled_size or 0.0) > 0:
        return OrderState.PARTIALLY_FILLED
    return state


def _as_float(value) -> float | None:
    """Venue numbers arrive as strings, None, or junk. None = not a number."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class OrderManager:
    def __init__(self, store: OrderStore, gateway: ExecutionGateway,
                 kill_switch: KillSwitch, *,
                 reconciler: AutoReconciler | None = None, notifier=None,
                 on_canceled_fill=None):
        self._store = store
        self._gateway = gateway
        self._kill_switch = kill_switch
        # Query-only, bounded auto-reconciliation of an ambiguous send. None in
        # PAPER mode: the executor is local, so ambiguity cannot arise.
        self._reconciler = reconciler
        self._notifier = notifier
        # Called with the refreshed record of every order THIS manager
        # cancelled, so a partial fill the venue completed before the cancel
        # landed reaches the portfolio (`TradingApp._book_fill_delta`). The
        # manager owns orders, not positions; without this hook a self-cancel
        # is the one fill discovery path that books nothing.
        self._on_canceled_fill = on_canceled_fill

    def submit(self, *, symbol: str, side: str, size: float,
               order_type: str = "MARKET", price: float | None = None,
               opening: bool = True, size_resolver=None) -> Order | None:
        """Persist first, then submit. None = a CLOSE that is no longer needed.

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

        `size_resolver` is how a CLOSE stays a close. It answers "how much is
        open RIGHT NOW" (unsigned), and it is asked again after
        `_make_room_for_close` has cancelled the blockers and BOOKED whatever
        they filled on their way out — which is precisely the moment the
        caller's size went stale. `size` is then a CAP, not a quantity: the
        order goes out for `min(requested, |position|)`, and for nothing at all
        if the position is already flat. Without it a close decided at 0.01
        against a blocker that turned out to have filled 0.006 sends 0.01 into
        a 0.004 position and opens a REVERSE position — the bot flipping itself
        short while trying to flatten.

        A record is created for the RESOLVED size only, so nothing is persisted
        for an order that is not sent.

        Orders in an unknown state block a new ENTRY (nothing may be sent while
        the book is unresolved), but they may not block a CLOSE with a bare
        RuntimeError: a leftover PENDING_SUBMIT is a book problem, and refusing
        the exit over it is the 2019 failure. A close is routed on into the
        priority path, which either clears the way or takes the LOUD path
        (`_closing_blocked`: critical log, urgent alert, kill switch).
        """
        if opening and self._store.unknown_orders():
            raise RuntimeError("orders with unknown state exist; reconcile before submitting")
        snapshot = self._baseline(symbol)
        try:
            order = self._store.create(symbol, side, size, order_type, price)
        except DuplicateOrderError as refusal:
            if opening:
                raise
            made = self._make_room_for_close(symbol, side, size, order_type,
                                             price, refusal, size_resolver)
            if made is None:
                return None            # the close is already satisfied
            order, size = made
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
            if opening:
                # An entry the venue refused is a skipped opportunity: the bot
                # holds no more risk than it did a moment ago.
                logger.warning("order rejected", extra={"data": {
                    "event": "order_rejected", "local_id": order.local_id,
                    "error": str(e)}})
                return order
            # A refused CLOSE is the 2019 failure exactly: the position is
            # still open, the bot just found out it cannot exit, and a
            # `warning` line is not how that gets said. Same loud path as a
            # close the book blocked — critical log, urgent alert, kill switch.
            self._closing_blocked(symbol, side, size, [],
                                  f"the exchange rejected it ({type(e).__name__}: {e})")
            return order
        return self._store.transition(order.local_id, OrderState.SUBMITTED,
                                      acceptance_id=result.acceptance_id)

    # ---- a CLOSING order outranks the book ---------------------------------
    def _make_room_for_close(self, symbol: str, side: str, size: float,
                             order_type: str, price: float | None,
                             refusal: DuplicateOrderError,
                             size_resolver=None) -> tuple[Order, float] | None:
        """Clear resting orders so a CLOSING order can be placed, ONCE.

        Returns (record, size to send), or None when there is no longer
        anything to close.

        The wedge this exists for: an ambiguous send resolves to ACTIVE, so the
        book holds a live SUBMITTED order; the venue never fills it; the
        protective stop then asks for a new order and `OrderStore.create`
        refuses it — the duplicate-order guard silently refusing the one order
        that must never be refused. That is the 2019 failure with a different
        cause: a position that cannot be exited.

        Cancelling is safe in a way sending is not — it is idempotent, and
        cancelling an order that is already gone changes nothing — so the
        blocking orders are cancelled and the close retried exactly once. If it
        is STILL refused, the bot cannot flatten and a human must: urgent alert
        plus a tripped kill switch, never a quiet `submit_refused` log line.

        SCOPED, not blanket. Only the ids the store reports as blocking are
        cancelled — `OrderStore.blocking_order_ids`, which is exactly the set
        `create` refused for. Today that set is "every non-terminal order for
        the symbol", so the effect is unchanged; the difference is that this
        path can no longer reach past its own reason for existing.
        WARNING to any future design that keeps a protective order RESTING on
        the book (a venue-side stop, a bracket): such an order would be
        non-terminal, so it would appear here as a blocker and be cancelled to
        make room for a manual close. Before adding one, this list has to learn
        to exclude it — and the duplicate-order guard has to stop counting it.

        A cancel the venue ACKNOWLEDGED is not a cancel the venue HONOURED, so
        the acknowledgement is verified against getchildorders before the close
        is sent (`_verify_blockers_cleared`). Sending on the strength of a 2xx
        alone is how one intended exit becomes two live orders.

        And the size is re-resolved LAST, after the cancelled orders' fills
        have been booked (`_settle_canceled` -> `on_canceled_fill`): those
        fills change the very position this order is trying to close, so the
        size the caller decided on is stale by construction here
        (`_close_size_now`).
        """
        blockers = self._store.blocking_order_ids(symbol)
        try:
            sent = self._send_cancels(symbol, blockers)
        except Exception as e:
            self._closing_blocked(symbol, side, size, blockers,
                                  f"cancel failed ({type(e).__name__}: {e})")
            raise refusal from None
        ok, detail, listing = self._verify_blockers_cleared(symbol, blockers)
        if not ok:
            # The records stay as they are. An order the venue still lists as
            # ACTIVE is not cancelled, and a book that says CANCELED about it
            # would be a lie in the direction that hides a live order.
            self._closing_blocked(symbol, side, size, blockers, detail)
            raise refusal from None
        # The verification listing already carries each cancelled order's final
        # executed_size, so settling the records costs no further call.
        canceled = self._settle_canceled(symbol, sent, listing=listing)
        logger.warning("resting orders cancelled to clear a closing order",
                       extra={"data": {"event": "closing_order_priority",
                                       "symbol": symbol, "side": side,
                                       "size": size,
                                       "canceled": [o.local_id for o in canceled],
                                       "resting": blockers}})
        resolved = self._close_size_now(symbol, side, size, size_resolver)
        if resolved is None:
            return None
        size = resolved
        try:
            return self._store.create(symbol, side, size, order_type, price), size
        except DuplicateOrderError as e:
            self._closing_blocked(symbol, side, size, blockers,
                                  f"still refused after cancelling: {e}")
            raise

    def _close_size_now(self, symbol: str, side: str, requested: float,
                        size_resolver) -> float | None:
        """How much a CLOSE should be sent for, asked at SEND time.

        None means "nothing": the cancelled blocker turned out to have filled
        the whole position on its way out, so the close has already happened
        and sending it would open a position in the opposite direction.

        `min(requested, |position|)` and never more. The requested size is what
        the pre-trade checks approved, so the order may only ever shrink here —
        a position that GREW between the decision and the send is not this
        order's business, and enlarging it would send a size no risk check ever
        saw.

        Without a resolver the requested size stands (a caller that keeps no
        position, and every test that drives the manager directly). A resolver
        that RAISES is the same case, loudly: an exit must not be dropped
        because the bookkeeping it consults is broken.
        """
        if size_resolver is None:
            return requested
        try:
            current = abs(float(size_resolver()))
        except Exception:
            logger.exception("the live position could not be read; the closing "
                             "order keeps its requested size", extra={"data": {
                                 "event": "closing_size_unresolved",
                                 "symbol": symbol, "side": side,
                                 "size": requested}})
            return requested
        if current <= _SIZE_EPSILON:
            logger.warning("closing order no longer needed: the position is flat",
                           extra={"data": {"event": "closing_already_satisfied",
                                           "symbol": symbol, "side": side,
                                           "requested_size": requested}})
            return None
        if current >= requested:
            return requested
        logger.warning("closing order resized to the live position", extra={"data": {
            "event": "closing_size_reresolved", "symbol": symbol, "side": side,
            "requested_size": requested, "size": current}})
        return current

    def _verify_blockers_cleared(
            self, symbol: str,
            blockers: list[str]) -> tuple[bool, str, list[dict] | None]:
        """ONE diagnostic getchildorders poll before the close is sent.

        Returns (verified, detail, listing). THE RULE, stated exactly:

        - the poll SUCCEEDED and no blocker is listed ACTIVE -> verified. That
          includes a blocker that does not appear in the listing at all. The
          venue answered, and the thing this guards against is an order the
          venue is still holding LIVE — an id that is absent from a listing the
          venue served is not that.
        - the poll succeeded and a blocker is still ACTIVE -> NOT verified.
          This is the expensive failure: the venue took the cancel request with
          a 2xx, did not act on it, and the close would go out ALONGSIDE a live
          order — one intended exit, two real orders.
        - the poll FAILED (None) -> NOT verified. "We could not look" is not
          evidence that the book is clear.

        Deliberately NOT strict about absence: requiring positive evidence that
        each id is listed CANCELED would hand the venue's own listing lag a
        veto over the exit. getchildorders is eventually consistent (see
        bot/order_management/reconciler.py); a cancelled order can be dropped
        from the default listing, or reappear a poll later, and treating either
        as "unverified" would trip the kill switch and freeze the bot WITH an
        open position — the 2019 trap, reached from the other side. The
        asymmetry is the point: absence blocks nothing, a live ACTIVE blocks
        everything.

        The listing is returned so the caller can settle the cancelled records
        from it (`_settle_canceled`) instead of paying a second read per order.

        Query-only by construction — it borrows the auto-reconciler's
        `QueryOnlyExchange`, which has no method that can send or cancel.
        Without a reconciler (PAPER: the executor is local, so its cancel IS
        the venue's answer and there is no listing to poll) there is nothing to
        verify against and the cancel stands.
        """
        if self._reconciler is None:
            return True, "", None
        ids = {o.acceptance_id for o in
               (self._store.get(local_id) for local_id in blockers)
               if o is not None and o.acceptance_id}
        if not ids:
            return True, "", None
        listing = self._reconciler.list_orders(symbol)
        if listing is None:
            return False, ("the cancel was acknowledged but getchildorders could "
                           "not be read, so it is unverified"), None
        still_active = []
        for row in listing:
            acc = str(row.get("child_order_acceptance_id") or "")
            if acc in ids and str(row.get("child_order_state") or "").upper() == "ACTIVE":
                still_active.append(acc)
        if still_active:
            return False, (f"the cancel was acknowledged but the exchange still "
                           f"lists {still_active} as ACTIVE"), listing
        logger.info("cancel verified against getchildorders", extra={"data": {
            "event": "cancel_verified", "symbol": symbol,
            "acceptance_ids": sorted(ids)}})
        return True, "", listing

    def _closing_blocked(self, symbol: str, side: str, size: float,
                         resting: list[str], detail: str) -> None:
        """The bot cannot close. Say so as loudly as the system allows.

        `resting` is the order(s) in the way when the book blocked the close,
        and EMPTY when nothing was in the way and the venue simply refused it —
        both are the same fact for the operator (the position is open and the
        bot cannot exit it), so both take this path.
        """
        logger.critical("closing order blocked", extra={"data": {
            "event": "closing_order_blocked", "symbol": symbol, "side": side,
            "size": size, "resting": resting, "detail": detail}})
        blocked_by = (f"it is blocked by order(s) {resting} and {detail}"
                      if resting else detail)
        self._alert(
            "CANNOT CLOSE POSITION",
            f"The protective/closing order {side} {size} {symbol} could not be "
            f"placed: {blocked_by}. Trading is stopped. The exchange may still "
            f"hold both the resting order and the position — check bitFlyer, "
            f"flatten by hand if you need to, then reconcile and reset the "
            f"kill switch.")
        self._kill_switch.trip(
            KillReason.SYSTEM_ERROR,
            f"closing order {side} {size} {symbol} blocked by "
            f"{resting or 'the exchange'}: {detail}")

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
        # ACTIVE with an executed_size is a PARTIAL fill, and the size has to
        # reach the record or nothing will ever book it (`_with_partial`).
        new_state = _with_partial(_RESOLUTION_TO_LOCAL.get(res.state),
                                  res.filled_size)
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
        """Poll the gateway for fill/cancel state of a submitted order.

        The record is rewritten whenever the state changes OR the reported fill
        has GROWN. A partial fill that grows while the order stays on the book
        used to be dropped on the "same state, nothing to do" shortcut, so the
        book's `filled_size` froze at whatever the first poll happened to see
        and every later execution went unbooked.
        """
        if order.acceptance_id is None or order.is_terminal:
            return order
        status = self._gateway.fetch_order_status(
            symbol=order.symbol, acceptance_id=order.acceptance_id
        )
        if status is None:
            return order
        new_state = _with_partial(_GATEWAY_TO_LOCAL.get(status.state),
                                  status.filled_size)
        if new_state is None:
            return order
        grew = (status.filled_size or 0.0) > order.filled_size
        if new_state == order.state and not grew:
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
            state = None if status is None else _with_partial(
                _GATEWAY_TO_LOCAL.get(str(getattr(status, "state", "")).upper()),
                getattr(status, "filled_size", 0.0))
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

    # ---- LIVE BOOT: PENDING_SUBMIT records a dead process left --------------
    def adopt_stale_pending(self, symbol: str) -> dict[str, list[Order]]:
        """Resolve the PENDING_SUBMIT records this process did not write.

        A PENDING_SUBMIT with no acceptance id is the crash window itself: the
        record was INSERTed and the process died before the send returned (or
        before it was even made). At boot every such record is by definition
        from a previous process, and it is not harmless bookkeeping — it is
        non-terminal, so the duplicate-order guard counts it and the NEXT order
        for the symbol is refused. The next order may be the protective stop,
        and that refusal used to arrive as a bare RuntimeError nobody was told
        about: the position could not be exited, silently. That is the 2019
        failure reached through our own book.

        So each one is asked about ONCE, with the same positive-evidence
        matcher that resolves an ambiguous send (product + side + size, and
        price for a LIMIT order), against one getchildorders listing:

        - LISTED -> adopt it: the acceptance id and whatever state the venue
          reports, fill size and price included. The record becomes a normal
          order the sweep can follow.
        - NOT LISTED -> ABANDONED (terminal). Absence is not evidence for a
          FRESH send — getchildorders lags an acceptance by seconds — but this
          record outlived a process restart, which is far longer than that lag,
          so "the venue does not list it" is the answer here. The position is
          not being guessed at either way: the LIVE boot has just adopted the
          venue's own getpositions answer (`TradingApp._adopt_venue_position`),
          so the truth about what is held does not depend on this record at all.
        - the venue could NOT BE READ -> left exactly as it is. "We could not
          look" is not evidence, and a boot that cannot see the book is one
          that must not clear it. Entries stay refused while it sits there and
          a close takes the loud path; both are the safe direction.

        LIVE-only by wiring (PAPER has no reconciler and fills synchronously).
        Returns the three groups so the boot can tell the operator.
        """
        outcome: dict[str, list[Order]] = {"adopted": [], "abandoned": [],
                                           "unresolved": []}
        stale = [o for o in self._store.active_orders(symbol)
                 if o.state is OrderState.PENDING_SUBMIT and not o.acceptance_id]
        if not stale:
            return outcome
        # BEFORE the listing: `baseline` unions in every id the reconciler has
        # already seen, so taking it afterwards would exclude the very rows we
        # are about to match against.
        snapshot = self._baseline(symbol)
        listing = (None if self._reconciler is None or snapshot is None
                   else self._reconciler.list_orders(symbol))
        claimed: set[str] = set()
        for order in stale:
            snap = snapshot
            if claimed and snap is not None:
                # Two stale records must never adopt the SAME venue row.
                snap = ExchangeSnapshot(
                    frozenset(snap.acceptance_ids | claimed), snap.taken_at)
            res = (None if listing is None or snap is None
                   else self._reconciler.match_once(
                       symbol=symbol, side=order.side, size=order.size,
                       snapshot=snap, order_type=order.order_type,
                       price=order.price, listing=listing))
            if res is not None and res.resolved:
                state = _with_partial(_RESOLUTION_TO_LOCAL.get(res.state),
                                      res.filled_size)
                if state is not None:
                    claimed.add(str(res.acceptance_id))
                    outcome["adopted"].append(self._store.transition(
                        order.local_id, state, acceptance_id=res.acceptance_id,
                        filled_size=res.filled_size or None,
                        avg_fill_price=res.avg_fill_price))
                    logger.warning("stale PENDING_SUBMIT adopted from the venue",
                                   extra={"data": {
                                       "event": "stale_pending_adopted",
                                       "local_id": order.local_id,
                                       "acceptance_id": res.acceptance_id,
                                       "state": state.value,
                                       "filled_size": res.filled_size}})
                    continue
            if listing is None:
                outcome["unresolved"].append(order)
                logger.error("stale PENDING_SUBMIT could not be checked against "
                             "the venue; it is left for a human", extra={"data": {
                                 "event": "stale_pending_unresolved",
                                 "local_id": order.local_id,
                                 "symbol": order.symbol, "side": order.side,
                                 "size": order.size}})
                continue
            outcome["abandoned"].append(
                self._store.transition(order.local_id, OrderState.ABANDONED))
            logger.warning("stale PENDING_SUBMIT abandoned: the venue does not "
                           "list it", extra={"data": {
                               "event": "stale_pending_abandoned",
                               "local_id": order.local_id,
                               "symbol": order.symbol, "side": order.side,
                               "size": order.size}})
        return outcome

    def cancel_all_active(self, symbol: str) -> list[Order]:
        """Cancel everything non-terminal for the symbol (kill-switch shutdown).

        The blanket form, and it belongs to the shutdown path only. A caller
        clearing the way for ONE order wants `cancel_orders` with the ids the
        store said were in the way.
        """
        return self.cancel_orders(symbol, self._store.blocking_order_ids(symbol))

    def cancel_orders(self, symbol: str, local_ids: list[str]) -> list[Order]:
        """Cancel exactly these orders; returns their FINAL records.

        A cancel is not a rewind. bitFlyer can fill part of a resting order
        before the cancel lands, and it reports that on the cancelled child
        order as `executed_size` / `average_price`. Stamping the record
        CANCELED without re-reading those threw the fill away: the size was
        real and the position was real, but no discovery path would ever look
        at a terminal order again — a phantom flat over a live position, the
        exact state `TradingApp._book_fill_delta` exists to prevent, reached
        through our OWN cancel.

        So each cancelled order is re-read once, the fill is written to the
        record before it is closed (`_settle_canceled`), and the refreshed
        records are RETURNED. Booking them is the app's job and happens through
        the `on_canceled_fill` hook, which routes to the one idempotent
        booking path.
        """
        return self._settle_canceled(symbol, self._send_cancels(symbol, local_ids))

    def _send_cancels(self, symbol: str, local_ids: list[str]) -> list[Order]:
        """Send the cancel for every id still on the book; returns those orders.

        The records are NOT transitioned here: what they finally filled is only
        known after the cancel, and a caller that has to verify the cancel took
        (`_make_room_for_close`) must be able to leave them untouched when the
        venue says it did not.
        """
        sent = []
        for local_id in local_ids:
            order = self._store.get(local_id)
            if order is None:
                continue
            if order.acceptance_id and order.state in (OrderState.SUBMITTED,
                                                       OrderState.PARTIALLY_FILLED):
                self._gateway.cancel_order(symbol=symbol,
                                           acceptance_id=order.acceptance_id)
                sent.append(order)
        return sent

    def _settle_canceled(self, symbol: str, sent: list[Order], *,
                         listing: list[dict] | None = None) -> list[Order]:
        """Record each cancelled order's final fill, then close it CANCELED.

        The fill is written FIRST, through `_with_partial`, so the executed
        size is durable on a PARTIALLY_FILLED record before the terminal
        transition — a crash in between then leaves a book that knows about the
        fill rather than one that has forgotten it.

        `listing` is a getchildorders answer the caller already paid for; rows
        are read from it instead of issuing a read per order. Without one, each
        cancelled order costs one status read (the same read `refresh` uses).
        A read that fails is logged, not raised: the cancel went out, so the
        record has to close either way.
        """
        settled = []
        for order in sent:
            state, filled, avg = self._final_fill(symbol, order, listing)
            if filled is not None and filled > order.filled_size:
                partial = _with_partial(order.state, filled) or order.state
                order = self._store.transition(order.local_id, partial,
                                               filled_size=filled,
                                               avg_fill_price=avg)
            # A cancel that raced a COMPLETE fill cancelled nothing. The record
            # says what the venue says, or the book ends up holding a CANCELED
            # order whose entire size executed.
            closed = (OrderState.FILLED
                      if _GATEWAY_TO_LOCAL.get(state) is OrderState.FILLED
                      else OrderState.CANCELED)
            final = self._store.transition(order.local_id, closed)
            settled.append(final)
            self._announce_canceled_fill(final)
        return settled

    def _final_fill(self, symbol: str, order: Order, listing: list[dict] | None
                    ) -> tuple[str | None, float | None, float | None]:
        """(exchange state, executed_size, average_price) of a cancelled order.

        All three are None when the venue could not be re-read. The state
        string is the venue's own vocabulary, the keys of `_GATEWAY_TO_LOCAL`.
        """
        row = self._row_for(order.acceptance_id, listing)
        if row is not None:
            # A zero average_price is "the venue reported none", not a price.
            return (str(row.get("child_order_state") or "").upper() or None,
                    _as_float(row.get("executed_size")),
                    _as_float(row.get("average_price")) or None)
        try:
            status = self._gateway.fetch_order_status(
                symbol=symbol, acceptance_id=order.acceptance_id)
        except Exception as e:
            logger.warning("cancelled order could not be re-read; its final "
                           "fill is unknown", extra={"data": {
                               "event": "cancel_refresh_failed",
                               "local_id": order.local_id,
                               "error": type(e).__name__}})
            return None, None, None
        if status is None:
            return None, None, None
        return (str(status.state or "").upper() or None,
                _as_float(status.filled_size),
                _as_float(status.avg_fill_price) or None)

    @staticmethod
    def _row_for(acceptance_id: str | None,
                 listing: list[dict] | None) -> dict | None:
        for row in listing or ():
            if acceptance_id and str(row.get("child_order_acceptance_id") or "") \
                    == str(acceptance_id):
                return row
        return None

    def _announce_canceled_fill(self, order: Order) -> None:
        """Hand a cancelled order's record to whoever books fills.

        Guarded: the cancel has already happened, so a failure on the booking
        side must not leave this path half-done. The booking itself is
        idempotent (`booked_size`), so a retry from another discovery path
        cannot double it.
        """
        if self._on_canceled_fill is None or order.unbooked_size <= 0:
            return
        try:
            self._on_canceled_fill(order)
        except Exception:
            logger.exception("booking a cancelled order's partial fill failed",
                             extra={"data": {
                                 "event": "cancel_booking_failed",
                                 "local_id": order.local_id,
                                 "unbooked_size": order.unbooked_size}})
