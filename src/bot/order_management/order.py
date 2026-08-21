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


_TERMINAL = {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED}
_ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.PENDING_SUBMIT: {OrderState.SUBMITTED, OrderState.REJECTED, OrderState.STATE_UNKNOWN},
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

    @property
    def is_terminal(self) -> bool:
        return self.state in _TERMINAL


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
                updated_at REAL NOT NULL
            )"""
        )
        self._conn.commit()

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
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (order.local_id, symbol, side, size, order_type, price,
             order.state.value, None, 0.0, None, now, now),
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

    def known_acceptance_ids(self) -> set[str]:
        """Every exchange acceptance id this book has ever seen.

        Used to harden the pre-send snapshot: an id we already recorded cannot
        be the order we are about to send, even if getchildorders happened to
        omit it from the snapshot poll.
        """
        rows = self._conn.execute(
            "SELECT acceptance_id FROM orders WHERE acceptance_id IS NOT NULL")
        return {str(r[0]) for r in rows}

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
        )
