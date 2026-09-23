"""Extension-point sockets (requirement V6).

`CoreEngine` (engine.py) calls these four hooks -- fill, latency, cost,
account -- but implements none of their logic itself. Each is a
`typing.Protocol`, not a base class: item 3 (fill/queue model), item 4
(latency model), item 5 (costs/funding) and item 6 (portfolio/account) each
write their own concrete class elsewhere (`src/bot/bt/fill/`,
`src/bot/bt/latency/`, `src/bot/bt/costs/`, `src/bot/bt/portfolio/`) that
structurally satisfies one of these Protocols, and hand an instance of it
into `CoreEngine.__init__`. None of that requires editing this file or
engine.py -- that is what "pluggable without touching the core" means here,
and `tests/test_extension_points.py` proves it by defining a throwaway
implementation of each Protocol from outside `core/` and running the engine
with it.

`FillNotice` is the minimal shared contract between a `FillModel` and the
`CostModel`/`Account` sockets it feeds. Item 3/5/6 may find they need a
richer shape; changing it is their call to make when they build against it,
not item 0's to anticipate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from .events import Event
from .time import Nanos


@dataclass(frozen=True)
class FillNotice:
    client_order_id: str
    price: float
    size: float
    fee: float = 0.0


@runtime_checkable
class FillModel(Protocol):
    def on_event(self, event: Event, visible_events: Sequence[Event]) -> list[FillNotice]:
        """Given the current event and everything visible up to and
        including it, return zero or more fills it produces. Must not read
        anything beyond `visible_events` -- the same V3 visibility rule the
        strategy is held to applies here, because a fill model that could
        peek ahead would make backtested fills unreachable in real trading.

        `visible_events` is a read-only `Sequence[Event]` -- in practice
        `CoreEngine.run` passes a `window.EventWindow` (O(1) to construct,
        see i0-r1-03), not necessarily a `tuple`. Index it, slice it or
        iterate it like a tuple; do not assume `isinstance(..., tuple)`."""
        ...


@runtime_checkable
class LatencyModel(Protocol):
    def delay_ns(self, event: Event) -> Nanos:
        """How long after `event.received_time_ns` this model's effect (a
        book update becoming visible, an order reaching the venue, ...)
        should actually take. Item 0 calls this hook per event; using the
        result to delay/reorder delivery is item 4's engine-wiring work."""
        ...


@runtime_checkable
class CostModel(Protocol):
    def cost(self, fill: FillNotice) -> float:
        """Total cost (fees, spread paid, funding, ...) attributed to `fill`,
        in the account's home currency. No default value -- item 5's own
        requirement row bars an implicit-zero default; `NullCostModel` below
        exists only so `CoreEngine` is runnable before item 5 exists, and
        returns 0.0 openly, never silently."""
        ...


@runtime_checkable
class Account(Protocol):
    def apply_fill(self, fill: FillNotice) -> None: ...

    def apply_funding(self, event: Event) -> None: ...

    def apply_liquidation(self, event: Event) -> None:
        """Symmetric with `apply_funding`: both are venue-side settlement
        events that can move the account without any `FillNotice` (round-1
        critic finding i0-r1-04). `LiquidationEvent` (events.py) can
        represent our own forced liquidation, not just a market-wide print,
        so it needs the same account socket funding already has -- wired in
        `CoreEngine.run` (engine.py) the same way, not as a special case."""
        ...


class NullFillModel:
    """Produces no fills. Lets `CoreEngine` run before item 3 exists."""

    def on_event(self, event: Event, visible_events: Sequence[Event]) -> list[FillNotice]:
        return []


class NullLatencyModel:
    """Zero delay. Lets `CoreEngine` run before item 4 exists."""

    def delay_ns(self, event: Event) -> Nanos:
        return Nanos(0)


class NullCostModel:
    """Zero cost, reported openly as a stand-in -- never a silent default in
    a run that is meant to price real costs (item 5 owns that)."""

    def cost(self, fill: FillNotice) -> float:
        return 0.0


class NullAccount:
    """Discards fills/funding/liquidations. Lets `CoreEngine` run before
    item 6 exists."""

    def apply_fill(self, fill: FillNotice) -> None:
        return None

    def apply_funding(self, event: Event) -> None:
        return None

    def apply_liquidation(self, event: Event) -> None:
        return None
