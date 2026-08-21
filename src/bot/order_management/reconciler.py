"""Fast, bounded, QUERY-ONLY reconciliation of an ambiguous order send.

CLAUDE.md §1 says an ambiguous order failure is held as STATE_UNKNOWN and
never auto-retried. That invariant is untouched here — what this module adds is
an automatic way to *find out* what actually happened, using nothing but
read-only endpoints, so a transient timeout during a storm no longer parks the
bot until a human looks at it.

Protocol
--------
1. BEFORE the send, `snapshot()` records the acceptance ids the exchange
   already knows about plus the current position size.
2. On `OrderStateUnknown`, `resolve()` polls getchildorders / getpositions with
   backoff inside a bounded budget (default 15s) and diffs against the
   snapshot:
     - a NEW acceptance id matching (side, size)  -> FILLED / ACTIVE / CANCELED
     - the position moved by the ordered amount   -> FILLED
     - neither, confirmed on N consecutive polls  -> NOT_PLACED
3. Anything still undecided at the budget end stays UNRESOLVED: the caller
   keeps STATE_UNKNOWN, alerts, and the human path is unchanged.

The reconciler is handed a `QueryOnlyExchange`, not the client. That class has
no method that can send or cancel an order, so "auto-reconciliation cannot
place an order" is a property of the object graph rather than of this code
being careful — the property test in tests/test_resilience.py checks it holds
across randomized fault sequences.

Absence of evidence is treated carefully in one direction only: NOT_PLACED
needs `confirmations` consecutive clean polls (getchildorders can lag a fresh
acceptance by a moment), while a positive match resolves on the first sighting.
A failed poll never counts as evidence of absence.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("bot.reconcile")

# getchildorders child_order_state -> our resolution outcome
_EXCHANGE_STATE = {
    "COMPLETED": "FILLED",
    "ACTIVE": "ACTIVE",
    "CANCELED": "CANCELED",
    "EXPIRED": "CANCELED",
    "REJECTED": "REJECTED",
}


@dataclass(frozen=True)
class ExchangeSnapshot:
    """What the exchange looked like immediately BEFORE the order was sent."""
    acceptance_ids: frozenset[str]
    position_size: float
    taken_at: float


@dataclass(frozen=True)
class Resolution:
    """FILLED / ACTIVE / CANCELED / REJECTED / NOT_PLACED / UNRESOLVED."""
    state: str
    acceptance_id: str | None = None
    filled_size: float = 0.0
    avg_fill_price: float | None = None
    polls: int = 0
    elapsed_sec: float = 0.0
    detail: str = ""

    @property
    def resolved(self) -> bool:
        return self.state != "UNRESOLVED"


class QueryOnlyExchange:
    """Read-only view of BitflyerClient handed to the auto-reconciler.

    Exactly two GET endpoints, and deliberately NO send/cancel method: the
    component that runs automatically after an ambiguous failure is physically
    incapable of placing an order.
    """

    def __init__(self, client, product_code: str | None = None):
        self._client = client
        self._product_code = product_code

    def child_orders(self, symbol: str) -> list[dict]:
        return self._client.get_child_orders(symbol)

    def positions(self, symbol: str) -> list[dict]:
        return self._client.get_positions(symbol)


def position_size_of(rows) -> float:
    """Signed size from /v1/me/getpositions rows (BUY positive, SELL negative)."""
    total = 0.0
    for row in rows or []:
        try:
            size = float(row.get("size") or 0.0)
        except (TypeError, ValueError):
            continue
        side = str(row.get("side") or "").upper()
        total += -size if side == "SELL" else size
    return total


class AutoReconciler:
    def __init__(self, exchange: QueryOnlyExchange, *, budget_sec: float = 15.0,
                 poll_interval_sec: float = 1.0, max_poll_interval_sec: float = 4.0,
                 confirmations: int = 2, size_tolerance: float = 1e-9,
                 clock=time.monotonic, sleep=time.sleep):
        self._exchange = exchange
        self.budget_sec = budget_sec
        self.poll_interval_sec = poll_interval_sec
        self.max_poll_interval_sec = max_poll_interval_sec
        self.confirmations = max(1, confirmations)
        self.size_tolerance = size_tolerance
        self._clock = clock
        self._sleep = sleep

    # ---- step 1: before the send ------------------------------------------
    def snapshot(self, symbol: str) -> ExchangeSnapshot:
        orders = self._exchange.child_orders(symbol)
        ids = frozenset(
            str(o.get("child_order_acceptance_id"))
            for o in (orders or []) if o.get("child_order_acceptance_id")
        )
        position = position_size_of(self._exchange.positions(symbol))
        return ExchangeSnapshot(ids, position, self._clock())

    # ---- step 2: after an ambiguous failure --------------------------------
    def resolve(self, *, symbol: str, side: str, size: float,
                snapshot: ExchangeSnapshot) -> Resolution:
        started = self._clock()
        deadline = started + self.budget_sec
        signed = size if str(side).upper() == "BUY" else -size
        delay = self.poll_interval_sec
        negatives = 0
        polls = 0
        while True:
            polls += 1
            orders = self._safe(lambda: self._exchange.child_orders(symbol))
            match = None
            if orders is not None:
                match = self._match(orders, snapshot, side, size)
            if match is not None:
                return self._from_order(match, polls, self._clock() - started)
            positions = self._safe(lambda: self._exchange.positions(symbol))
            if orders is not None and positions is not None:
                delta = position_size_of(positions) - snapshot.position_size
                if signed != 0 and delta * signed > 0 and \
                        abs(delta) + self.size_tolerance >= abs(signed):
                    # A fill can show up in the position before getchildorders
                    # lists the order. That is still definitive: it happened.
                    return Resolution("FILLED", None, filled_size=abs(signed),
                                      polls=polls, elapsed_sec=self._clock() - started,
                                      detail="position moved by the ordered size")
                if abs(delta) <= self.size_tolerance:
                    negatives += 1
                    if negatives >= self.confirmations:
                        return Resolution("NOT_PLACED", polls=polls,
                                          elapsed_sec=self._clock() - started,
                                          detail=f"no new order and flat position on "
                                                 f"{negatives} consecutive polls")
                else:
                    negatives = 0
            if self._clock() >= deadline:
                return Resolution("UNRESOLVED", polls=polls,
                                  elapsed_sec=self._clock() - started,
                                  detail=f"undecided after {self.budget_sec:.0f}s")
            remaining = deadline - self._clock()
            self._sleep(max(0.0, min(delay, remaining)))
            delay = min(delay * 2, self.max_poll_interval_sec)

    # ---- internals ---------------------------------------------------------
    @staticmethod
    def _safe(fn):
        """A failed READ during reconciliation is just a missing sample."""
        try:
            return fn()
        except Exception as e:
            logger.warning("reconcile poll failed", extra={"data": {
                "event": "reconcile_poll_failed", "error": type(e).__name__}})
            return None

    def _match(self, orders, snapshot: ExchangeSnapshot, side: str,
               size: float) -> dict | None:
        wanted = str(side).upper()
        best = None
        for o in orders or []:
            acc = o.get("child_order_acceptance_id")
            if not acc or str(acc) in snapshot.acceptance_ids:
                continue
            if str(o.get("side") or "").upper() != wanted:
                continue
            try:
                o_size = float(o.get("size") or 0.0)
            except (TypeError, ValueError):
                continue
            if abs(o_size - size) > max(self.size_tolerance, size * 1e-6):
                continue
            best = o          # last one wins: getchildorders is newest-first
        return best

    @staticmethod
    def _from_order(order: dict, polls: int, elapsed: float) -> Resolution:
        raw = str(order.get("child_order_state") or "ACTIVE").upper()
        state = _EXCHANGE_STATE.get(raw, "ACTIVE")
        try:
            filled = float(order.get("executed_size") or 0.0)
        except (TypeError, ValueError):
            filled = 0.0
        avg = order.get("average_price")
        try:
            avg_price = float(avg) if avg else None
        except (TypeError, ValueError):
            avg_price = None
        return Resolution(state,
                          acceptance_id=str(order.get("child_order_acceptance_id")),
                          filled_size=filled, avg_fill_price=avg_price,
                          polls=polls, elapsed_sec=elapsed,
                          detail=f"exchange reports {raw}")
