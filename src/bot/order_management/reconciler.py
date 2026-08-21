"""Fast, bounded, QUERY-ONLY reconciliation of an ambiguous order send.

CLAUDE.md §1 says an ambiguous order failure is held as STATE_UNKNOWN and
never auto-retried. That invariant is untouched here — what this module adds is
an automatic way to *find out* what actually happened, using nothing but
read-only endpoints, so a transient timeout during a storm no longer parks the
bot until a human looks at it.

POSITIVE EVIDENCE ONLY
----------------------
The reconciler can end in exactly two ways:

- it SAW our order on the exchange — a `child_order_acceptance_id` that is NOT
  in the baseline, on the same product and side, for the same size (and, for a
  LIMIT order, the same price) — and resolves it to what getchildorders says it
  is (FILLED / ACTIVE / CANCELED / REJECTED), taking the fill size and price
  FROM THAT RECORD; or
- it did not, and the order stays STATE_UNKNOWN for a human.

There is deliberately no NOT_PLACED outcome. Absence of evidence inside a 15s
budget is not evidence of absence: getchildorders is eventually consistent and
has been observed to lag a fresh acceptance, so "I polled twice and saw
nothing" used to close the order record as REJECTED while the venue was in fact
holding a live position — a ghost order the bot then believed it did not have.
The old position-diff shortcut is gone for the same reason in the other
direction: a position that moved says only that SOMETHING filled, and it was
booked at the decision-time quote rather than at a real fill price.

Baseline (no pre-send network I/O)
----------------------------------
The baseline is the set of acceptance ids OUR OWN BOOK already knows
(`OrderStore.known_acceptance_ids`, bounded), unioned with the ids this
reconciler saw during earlier resolves. It costs nothing on the send path: the
previous design took two blocking GETs before EVERY send, including the
protective stop-loss, which put diagnostic I/O in front of the one order that
must never be delayed.

SINGLE-WRITER ASSUMPTION. Matching an order by "an acceptance id that is new to
us, with our product/side/size/price" is sound only because this bitFlyer
account is traded by this bot alone. If a human (or a second bot) places orders
on the same account while a reconciliation window is open, an order of theirs
that happens to match our product, side, size and price would be attributed to
us. Everything that does NOT match is ignored, and a mismatch simply leaves the
order STATE_UNKNOWN — the safe direction. Do not run a second writer against a
LIVE account without revisiting this rule (docs/OPERATIONS.md §3.5).

The reconciler is handed a `QueryOnlyExchange`, not the client. That class has
no method that can send or cancel an order, so "auto-reconciliation cannot
place an order" is a property of the object graph rather than of this code
being careful — the property test in tests/test_resilience.py checks it holds
across randomized fault sequences.
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable

from bot.exchange.resilience import DIAGNOSTIC_TIMEOUTS

logger = logging.getLogger("bot.reconcile")

# getchildorders child_order_state -> our resolution outcome
_EXCHANGE_STATE = {
    "COMPLETED": "FILLED",
    "ACTIVE": "ACTIVE",
    "CANCELED": "CANCELED",
    "EXPIRED": "CANCELED",
    "REJECTED": "REJECTED",
}

# Poll offsets as a FRACTION of the budget. The last one lands ON the budget
# end, so a listing lag anywhere inside the window is still caught: the old
# schedule (1s doubling to a 4s cap, started from a clock that only moved when
# read) stopped polling long before a 15s budget expired and reported "not
# placed" at t≈7s.
POLL_FRACTIONS = (1 / 30, 1 / 15, 2 / 15, 4 / 15, 8 / 15, 1.0)

# ...but the FIRST poll is capped in absolute time. It is the one that catches
# an order the venue listed straight away, and with a long budget a purely
# proportional first offset would leave the caller — which is holding an order
# in an unknown state — waiting seconds for a question the venue can answer at
# once.
FIRST_POLL_MAX_SEC = 2.0

# How many acceptance ids seen on the venue are carried forward as baseline.
MAX_OBSERVED_IDS = 500


@dataclass(frozen=True)
class ExchangeSnapshot:
    """The acceptance ids that were already OURS before the order was sent.

    Built from the local order book plus what earlier resolves observed; taking
    it costs no network call (see the module docstring).
    """
    acceptance_ids: frozenset[str]
    taken_at: float


@dataclass(frozen=True)
class Resolution:
    """FILLED / ACTIVE / CANCELED / REJECTED / UNRESOLVED.

    UNRESOLVED is not a failure of this module: it is the honest answer when no
    positive evidence turned up, and it keeps the order STATE_UNKNOWN.
    """
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


@contextmanager
def _no_context():
    yield None


class QueryOnlyExchange:
    """Read-only view of BitflyerClient handed to the auto-reconciler.

    ONE GET endpoint, and deliberately NO send/cancel method: the component
    that runs automatically after an ambiguous failure is physically incapable
    of placing an order.

    Every call runs inside the client's `diagnostic_call` window — short fixed
    timeouts, one attempt — so a reconciliation poll can never inherit the
    widened trading read timeout it was triggered by.
    """

    def __init__(self, client, product_code: str | None = None,
                 timeouts=DIAGNOSTIC_TIMEOUTS):
        self._client = client
        self._product_code = product_code
        self._timeouts = timeouts

    def _diagnostic(self):
        hook = getattr(self._client, "diagnostic_call", None)
        return hook(self._timeouts) if callable(hook) else _no_context()

    def child_orders(self, symbol: str) -> list[dict]:
        with self._diagnostic():
            return self._client.get_child_orders(symbol)


class AutoReconciler:
    def __init__(self, exchange: QueryOnlyExchange, *, budget_sec: float = 15.0,
                 size_tolerance: float = 1e-9, price_tolerance: float = 1e-9,
                 clock=time.monotonic, sleep=time.sleep):
        self._exchange = exchange
        self.budget_sec = budget_sec
        self.size_tolerance = size_tolerance
        self.price_tolerance = price_tolerance
        self._clock = clock
        self._sleep = sleep
        # Ids seen on the venue during earlier resolves, newest last. Bounded:
        # an unbounded set in a process that runs for months is a slow leak.
        self._observed: OrderedDict[str, None] = OrderedDict()

    # ---- step 1: before the send (NO network I/O) ---------------------------
    def baseline(self, known_ids: Iterable[str] | None = None) -> ExchangeSnapshot:
        ids = set(known_ids or ())
        ids.update(self._observed)
        return ExchangeSnapshot(frozenset(ids), self._clock())

    # ---- one-shot diagnostic listing ---------------------------------------
    def list_orders(self, symbol: str) -> list[dict] | None:
        """ONE getchildorders poll. None = the venue could not be read.

        Exposed because "did the cancel actually take?" is the same question
        this module already answers about a send, asked once instead of on a
        schedule (`OrderManager._verify_blockers_cleared`). It runs through the
        same QueryOnlyExchange, on the same diagnostic timeouts, and a failed
        read returns None — never an empty list, which would read as "the book
        is clear".
        """
        orders = self._safe(lambda: self._exchange.child_orders(symbol))
        if orders is None:
            return None
        self._remember(orders)
        return list(orders)

    # ---- one-shot match for a record that is NOT a fresh send ---------------
    def match_once(self, *, symbol: str, side: str, size: float,
                   snapshot: ExchangeSnapshot, order_type: str = "MARKET",
                   price: float | None = None,
                   listing: list[dict] | None = None) -> Resolution:
        """Same positive-evidence matcher as `resolve`, asked ONCE.

        For an order record whose send happened in a PREVIOUS PROCESS
        (`OrderManager.adopt_stale_pending`). The poll schedule in `resolve`
        exists to outlast getchildorders' listing lag right after a send; a
        record that survived a process restart is far older than that lag, so
        one listing is the whole question — and the caller is a boot sequence
        that must not spend a reconciliation budget per stale record.

        `listing` lets one getchildorders answer serve several records. Not
        found is UNRESOLVED, exactly as everywhere else in this module: what
        the caller does with "no evidence" is the caller's decision, and it is
        a different decision at boot (nothing has been sent yet in this
        process) than it is mid-flight.
        """
        orders = self.list_orders(symbol) if listing is None else listing
        if orders is None:
            return Resolution("UNRESOLVED",
                              detail="getchildorders could not be read")
        match = self._match(orders, snapshot, symbol, side, size,
                            order_type, price)
        if match is None:
            return Resolution("UNRESOLVED", polls=1,
                              detail="no matching order on the venue's listing")
        return self._from_order(match, 1, 0.0)

    # ---- step 2: after an ambiguous failure --------------------------------
    def resolve(self, *, symbol: str, side: str, size: float,
                snapshot: ExchangeSnapshot, order_type: str = "MARKET",
                price: float | None = None) -> Resolution:
        """Poll getchildorders on a schedule that spans the whole budget.

        Returns as soon as positive evidence appears. Otherwise UNRESOLVED —
        never "not placed".
        """
        started = self._clock()
        polls = 0
        for i, offset in enumerate(self._schedule()):
            if i and self._clock() - started > self.budget_sec:
                # Slow polls ate the remaining slots. Stop instead of running
                # the schedule past the budget: the caller is holding an order
                # in an unknown state and is waiting on this answer.
                break
            self._sleep_until(started + offset)
            polls += 1
            orders = self._safe(lambda: self._exchange.child_orders(symbol))
            if orders is None:
                continue
            self._remember(orders)
            match = self._match(orders, snapshot, symbol, side, size,
                                order_type, price)
            if match is not None:
                return self._from_order(match, polls, self._clock() - started)
        return Resolution("UNRESOLVED", polls=polls,
                          elapsed_sec=self._clock() - started,
                          detail=f"no matching order listed within "
                                 f"{self.budget_sec:.0f}s; state stays UNKNOWN")

    # ---- internals ---------------------------------------------------------
    def _schedule(self) -> list[float]:
        offsets = [f * self.budget_sec for f in POLL_FRACTIONS]
        offsets[0] = min(FIRST_POLL_MAX_SEC, offsets[0])
        return offsets

    def _sleep_until(self, target: float) -> None:
        wait = target - self._clock()
        if wait > 0:
            self._sleep(wait)

    def _remember(self, orders) -> None:
        """Carry the venue's ids forward so the NEXT resolve starts from a
        fresher baseline without paying a pre-send GET for it."""
        for o in orders or []:
            acc = o.get("child_order_acceptance_id")
            if not acc:
                continue
            self._observed[str(acc)] = None
            self._observed.move_to_end(str(acc))
        while len(self._observed) > MAX_OBSERVED_IDS:
            self._observed.popitem(last=False)

    @staticmethod
    def _safe(fn):
        """A failed READ during reconciliation is just a missing sample. It is
        never evidence — of presence or of absence."""
        try:
            return fn()
        except Exception as e:
            logger.warning("reconcile poll failed", extra={"data": {
                "event": "reconcile_poll_failed", "error": type(e).__name__}})
            return None

    def _match(self, orders, snapshot: ExchangeSnapshot, symbol: str, side: str,
               size: float, order_type: str, price: float | None) -> dict | None:
        wanted = str(side).upper()
        is_limit = str(order_type).upper() == "LIMIT"
        candidates = []
        for o in orders or []:
            acc = o.get("child_order_acceptance_id")
            if not acc or str(acc) in snapshot.acceptance_ids:
                continue
            product = o.get("product_code")
            if product and str(product) != str(symbol):
                continue
            if str(o.get("side") or "").upper() != wanted:
                continue
            if not self._close(o.get("size"), size, self.size_tolerance):
                continue
            if is_limit and price is not None and \
                    not self._close(o.get("price"), price, self.price_tolerance):
                continue
            candidates.append(o)
        if not candidates:
            return None
        if len(candidates) > 1:
            # Under the single-writer assumption this cannot happen for one
            # intended order; say so loudly rather than picking silently.
            logger.error("reconcile matched more than one new order", extra={
                "data": {"event": "reconcile_ambiguous_match",
                         "count": len(candidates), "symbol": symbol}})
        # getchildorders answers NEWEST FIRST, so the first candidate is the
        # most recent; `child_order_date` is used when the venue supplies it
        # rather than trusting the ordering. (The previous code kept the LAST
        # row while its comment claimed newest-first — it took the OLDEST.)
        best, best_key = None, None
        for i, o in enumerate(candidates):
            key = (str(o.get("child_order_date") or ""), -i)
            if best_key is None or key > best_key:
                best, best_key = o, key
        return best

    @staticmethod
    def _close(raw, wanted: float, tolerance: float) -> bool:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return False
        return abs(value - wanted) <= max(tolerance, abs(wanted) * 1e-6)

    @staticmethod
    def _from_order(order: dict, polls: int, elapsed: float) -> Resolution:
        """Everything comes from the exchange's own record — never from the
        quote the decision was made on."""
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
