"""The strategy-facing API (requirement V5): an event callback plus
place/cancel order, and nothing else.

`StrategyContext` is the ONLY object a `Strategy` (strategy.py) ever
receives. It never receives `CoreEngine` itself, so there is no path from
strategy code to engine-internal state (account balance, open orders, order
book) other than the read-only, visibility-bounded methods defined here.
`test_api_coupling.py` measures this directly: it walks `dir(ctx)` and
asserts the public surface is exactly the five members below, and that none
of them is (or returns) the engine.

Structural lookahead prevention (requirement V3) lives here too:
`_StrategyContext__visible_events` (name-mangled by the leading `__`) is a
bounded view (`window.EventWindow`, or a plain tuple -- both are read-only
`Sequence[Event]`) of the run's event log ending at, and including, the
current event -- and `CoreEngine.run` (engine.py) computes that bound BEFORE
constructing the `StrategyContext` and calling the strategy, so the view
itself never contains a future event; there is nothing to withhold from a
public method because the object was never given it. `visible_events()`
below is the only read path into event history, and every event it can
possibly return already satisfies `received_time_ns <= now_ns` -- not by a
runtime filter that could have a bug, but because nothing later ever enters
the view in the first place. A fresh `StrategyContext` is built for every
single event and never reused, so a strategy cannot stash one and use it
later to see a `now` that has since moved forward.

Round-1 critic finding i0-r1-03: the view handed in is O(1) to construct
(see `window.py`) precisely so that `CoreEngine.run` does not have to copy
the whole visible history on every iteration just in case a strategy asks
for it. `visible_events()` only materializes an actual `tuple` -- and only
as much of one as was actually requested -- when a strategy calls it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .events import Event, EventType
from .time import Nanos


@dataclass(frozen=True)
class OrderRequest:
    side: str  # "buy" | "sell"
    order_type: str  # "market" | "limit" | ... (item 2 defines the full set)
    size: float
    price: Optional[float] = None
    client_order_id: str = ""


@dataclass(frozen=True)
class CancelRequest:
    client_order_id: str


class StrategyContext:
    def __init__(
        self,
        visible_events: Sequence[Event],
        current: Event,
        place_order_cb: Callable[[OrderRequest], str],
        cancel_order_cb: Callable[[CancelRequest], None],
    ) -> None:
        # Accepts any read-only Sequence[Event] -- a plain tuple (as tests
        # construct directly) or a `window.EventWindow` (as CoreEngine.run
        # passes, for O(1) construction -- see the module docstring and
        # i0-r1-03). Nothing here assumes it is already a tuple; only
        # `visible_events()` below decides when to materialize one.
        self.__visible_events = visible_events
        self.__current = current
        self.__place_order_cb = place_order_cb
        self.__cancel_order_cb = cancel_order_cb

    @property
    def now_ns(self) -> Nanos:
        return self.__current.received_time_ns

    @property
    def current_event(self) -> Event:
        return self.__current

    def visible_events(
        self, event_type: Optional[EventType] = None, n: Optional[int] = None
    ) -> tuple[Event, ...]:
        """Events with `received_time_ns <= now_ns`, oldest first, optionally
        filtered to one `event_type` and/or limited to the last `n`. Cannot
        return an event past `current_event` -- see module docstring.

        `n` is a count contract, not a slice index: `n=0` means "zero
        events", full stop. It is handled as an explicit branch rather than
        delegated to `events[-n:]`, because Python's slicing treats `-0` as
        `0` and that idiom silently degenerates `n=0` into "the whole
        history" instead (round-1 critic finding i0-r1-02)."""
        events: Sequence[Event] = self.__visible_events
        if event_type is not None:
            events = tuple(e for e in events if e.EVENT_TYPE is event_type)
        else:
            events = tuple(events)
        if n is not None:
            if n <= 0:
                return ()
            events = events[-n:]
        return events

    def place_order(self, request: OrderRequest) -> str:
        """Returns the engine-assigned client_order_id (echoes
        `request.client_order_id` if the strategy supplied a non-empty one)."""
        return self.__place_order_cb(request)

    def cancel_order(self, request: CancelRequest) -> None:
        self.__cancel_order_cb(request)
