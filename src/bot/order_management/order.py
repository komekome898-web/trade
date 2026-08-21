"""Order model, state machine and persistent store (duplicate-order prevention).

Protocol for every order (rule 12):
1. INSERT a PENDING_SUBMIT record with a locally generated idempotency key
   BEFORE any network call.
2. Submit. On success store the exchange acceptance id -> SUBMITTED.
3. On ambiguous failure (OrderStateUnknown) mark STATE_UNKNOWN. The manager
   must reconcile against the exchange before any resend; while any order for
   the symbol is PENDING_SUBMIT/STATE_UNKNOWN, new submissions are refused.

bitFlyer child orders have no client order id, so reconciliation matches by
acceptance id when we have one, else by (product, side, size, time window).

`booked_size` is the second half of that protocol and belongs to the ORDER, not
to whoever noticed the fill: it records how much of `filled_size` has already
been turned into a portfolio position. Every discovery path (the submit-path
refresh, the periodic sweep, auto-reconciliation) books only the delta above it
(`TradingApp._book_fill_delta`), so a fill seen twice is booked once and a fill
seen only by the sweep is booked at all. It is persisted with the record
because the alternative — in-memory bookkeeping — loses the distinction across
a restart, in the direction that doubles a REAL position.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OrderState(Enum):
    PENDING_SUBMIT = "PENDING_SUBMIT"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    STATE_UNKNOWN = "STATE_UNKNOWN"
    # A PENDING_SUBMIT record a DEAD PROCESS left behind, which the LIVE boot
    # looked for on the venue's recent listing and did not find
    # (`OrderManager.adopt_stale_pending`). Terminal on purpose: the record
    # never reached the exchange as far as the exchange can be seen to know,
    # and leaving it non-terminal makes the duplicate-order guard refuse every
    # later order for the symbol — including the protective close. It is a
    # state of its own rather than CANCELED because nobody cancelled anything:
    # an operator reading the book must be able to tell "we gave up on this
    # record at boot" from "the venue confirmed a cancel".
    ABANDONED = "ABANDONED"


_TERMINAL = {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED,
             OrderState.ABANDONED}
_ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    # PENDING_SUBMIT can resolve straight to a fill: `reconcile_unknown` walks
    # PENDING_SUBMIT records too (the crash-between-INSERT-and-send case), and
    # the venue may answer that it holds the order — partly or fully filled, or
    # cancelled. Refusing those transitions did not make the fill unreal, it
    # only raised InvalidTransition out of the reconciler that was trying to
    # record it.
    OrderState.PENDING_SUBMIT: {OrderState.SUBMITTED, OrderState.PARTIALLY_FILLED,
                                OrderState.FILLED, OrderState.CANCELED,
                                OrderState.REJECTED, OrderState.STATE_UNKNOWN,
                                OrderState.ABANDONED},
    OrderState.SUBMITTED: {OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELED,
                           OrderState.REJECTED, OrderState.STATE_UNKNOWN},
    OrderState.PARTIALLY_FILLED: {OrderState.FILLED, OrderState.CANCELED, OrderState.STATE_UNKNOWN},
    OrderState.STATE_UNKNOWN: {OrderState.SUBMITTED, OrderState.PARTIALLY_FILLED, OrderState.FILLED,
                               OrderState.CANCELED, OrderState.REJECTED},
}


class InvalidTransition(Exception):
    pass


class DuplicateOrderError(Exception):
    """A non-terminal order already exists for this symbol; refusing a new one."""


@dataclass
class Order:
    local_id: str
    symbol: str
    side: str
    size: float
    order_type: str               # MARKET / LIMIT
    price: float | None
    state: OrderState
    acceptance_id: str | None = None
    filled_size: float = 0.0
    avg_fill_price: float | None = None
    created_at: float = 0.0
    updated_at: float = 0.0
    # How much of `filled_size` the portfolio has already been told about.
    booked_size: float = 0.0

    @property
    def is_terminal(self) -> bool:
        return self.state in _TERMINAL

    @property
    def unbooked_size(self) -> float:
        """Filled but not yet booked into the portfolio."""
        return float(self.filled_size) - float(self.booked_size)


class OrderStore:
    def __init__(self, db_path: str | Path = "data/orders.sqlite3", clock=time.time):
        db = Path(db_path)
        if db.parent != Path("."):
            db.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db)
        self._clock = clock
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                local_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                size REAL NOT NULL,
                order_type TEXT NOT NULL,
                price REAL,
                state TEXT NOT NULL,
                acceptance_id TEXT,
                filled_size REAL NOT NULL DEFAULT 0,
                avg_fill_price REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                booked_size REAL NOT NULL DEFAULT 0
            )"""
        )
        self._migrate_booked_size()
        self._conn.commit()

    def _migrate_booked_size(self) -> None:
        """Add `booked_size` to a book written before it existed.

        Backfilled as `booked_size = filled_size`, not 0: everything already in
        an older book that had filled was booked by the old submit-path code,
        and the safe direction for a migration is "already booked" — a missed
        booking is a phantom flat, but a repeated one is a DOUBLED real
        position.
        """
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(orders)")}
        if "booked_size" in columns:
            return
        self._conn.execute(
            "ALTER TABLE orders ADD COLUMN booked_size REAL NOT NULL DEFAULT 0")
        self._conn.execute("UPDATE orders SET booked_size = filled_size")

    def create(self, symbol: str, side: str, size: float, order_type: str,
               price: float | None) -> Order:
        """Insert a PENDING_SUBMIT record. Refuses if any non-terminal order exists."""
        active = self.active_orders(symbol)
        if active:
            raise DuplicateOrderError(
                f"{len(active)} non-terminal order(s) exist for {symbol}: "
                f"{[o.local_id for o in active]}"
            )
        now = self._clock()
        order = Order(
            local_id=str(uuid.uuid4()), symbol=symbol, side=side, size=size,
            order_type=order_type, price=price, state=OrderState.PENDING_SUBMIT,
            created_at=now, updated_at=now,
        )
        self._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (order.local_id, symbol, side, size, order_type, price,
             order.state.value, None, 0.0, None, now, now, 0.0),
        )
        self._conn.commit()
        return order

    def transition(self, local_id: str, new_state: OrderState, *,
                   acceptance_id: str | None = None,
                   filled_size: float | None = None,
                   avg_fill_price: float | None = None) -> Order:
        order = self.get(local_id)
        if order is None:
            raise KeyError(local_id)
        if new_state != order.state:
            allowed = _ALLOWED_TRANSITIONS.get(order.state, set())
            if new_state not in allowed:
                raise InvalidTransition(f"{order.state.value} -> {new_state.value}")
        self._conn.execute(
            "UPDATE orders SET state=?, acceptance_id=COALESCE(?, acceptance_id), "
            "filled_size=COALESCE(?, filled_size), avg_fill_price=COALESCE(?, avg_fill_price), "
            "updated_at=? WHERE local_id=?",
            (new_state.value, acceptance_id, filled_size, avg_fill_price,
             self._clock(), local_id),
        )
        self._conn.commit()
        return self.get(local_id)  # type: ignore[return-value]

    def mark_booked(self, local_id: str, booked_size: float) -> Order:
        """Record how much of this order the portfolio has been told about.

        Monotone by construction (`MAX`): a stale reader that saw a smaller
        `filled_size` can never walk the watermark back and re-open an already
        booked fill for a second booking.
        """
        self._conn.execute(
            "UPDATE orders SET booked_size=MAX(booked_size, ?), updated_at=? "
            "WHERE local_id=?", (float(booked_size), self._clock(), local_id))
        self._conn.commit()
        order = self.get(local_id)
        if order is None:
            raise KeyError(local_id)
        return order

    def blocking_order_ids(self, symbol: str) -> list[str]:
        """local_ids of the non-terminal orders that would make `create` refuse.

        The duplicate-order guard refuses a new order when ANY non-terminal
        order exists for the symbol, so this IS that set — asked for explicitly
        so a caller that has to clear the way (a closing order, see
        `OrderManager._make_room_for_close`) can cancel exactly those ids
        instead of issuing a blanket cancel over whatever is active by the time
        it runs.
        """
        return [o.local_id for o in self.active_orders(symbol)]

    def get(self, local_id: str) -> Order | None:
        row = self._conn.execute(
            "SELECT * FROM orders WHERE local_id=?", (local_id,)
        ).fetchone()
        return self._row_to_order(row) if row else None

    def active_orders(self, symbol: str | None = None) -> list[Order]:
        terminal = tuple(s.value for s in _TERMINAL)
        q = f"SELECT * FROM orders WHERE state NOT IN ({','.join('?' * len(terminal))})"
        args: list = list(terminal)
        if symbol:
            q += " AND symbol=?"
            args.append(symbol)
        return [self._row_to_order(r) for r in self._conn.execute(q, args)]

    def known_acceptance_ids(self, max_terminal: int = 200) -> set[str]:
        """Acceptance ids this book knows, BOUNDED.

        This is the reconciliation baseline: an id we already recorded cannot
        be the order we are about to send. Every non-terminal order is included
        unconditionally (those are the ones that could still be confused with a
        fresh send), plus the most recently updated `max_terminal` closed ones.
        A months-old book would otherwise load every id it ever saw before every
        single send, and only the recent ones can still be listed inside a
        reconciliation window.
        """
        terminal = tuple(s.value for s in _TERMINAL)
        placeholders = ",".join("?" * len(terminal))
        rows = self._conn.execute(
            f"SELECT acceptance_id FROM orders WHERE acceptance_id IS NOT NULL "
            f"AND state NOT IN ({placeholders})", terminal)
        ids = {str(r[0]) for r in rows}
        rows = self._conn.execute(
            f"SELECT acceptance_id FROM orders WHERE acceptance_id IS NOT NULL "
            f"AND state IN ({placeholders}) ORDER BY updated_at DESC LIMIT ?",
            (*terminal, max(0, int(max_terminal))))
        ids.update(str(r[0]) for r in rows)
        return ids

    def unknown_orders(self) -> list[Order]:
        rows = self._conn.execute(
            "SELECT * FROM orders WHERE state IN (?, ?)",
            (OrderState.STATE_UNKNOWN.value, OrderState.PENDING_SUBMIT.value),
        )
        return [self._row_to_order(r) for r in rows]

    @staticmethod
    def _row_to_order(row) -> Order:
        return Order(
            local_id=row[0], symbol=row[1], side=row[2], size=row[3],
            order_type=row[4], price=row[5], state=OrderState(row[6]),
            acceptance_id=row[7], filled_size=row[8], avg_fill_price=row[9],
            created_at=row[10], updated_at=row[11],
            booked_size=(row[12] if len(row) > 12 else 0.0),
        )
