"""Exceptions raised by the core. Every one of them means "the run is not
trustworthy as configured" -- the core never downgrades one of these to a
warning and carries on."""
from __future__ import annotations


class CoreError(Exception):
    """Base class for every error the core raises on purpose."""


class TimestampUnitError(CoreError, ValueError):
    """Unknown unit label, wrong value type, out-of-int64-range result, a
    magnitude implausible for the declared unit (unit mislabeling), or a
    timestamp that cannot be represented in integer nanoseconds without
    rounding."""


class EventValidationError(CoreError, ValueError):
    """An event's fields violate its type's contract (non-finite price,
    high < low, unsorted book side, exchange time after received time, ...)."""


class EventOrderError(CoreError, ValueError):
    """One input stream went backwards in `exchange_time_ns`. The core
    merges several streams by time (engine.py), but it does not re-sort a
    single stream silently: a backwards step inside one stream is a data
    defect the data layer must detect and report, not something to paper
    over."""


class SourceEventTypeError(CoreError, TypeError):
    """The event source supplied something that is not a market-data or
    clock event (for example an order notice). Order notices are produced by
    the engine from the fill model's reports, never read from a source."""


class LookAheadError(CoreError, RuntimeError):
    """The strategy asked for events at a time after its current time (any
    time argument of a history read -- `since_ns` or `until_ns` -- after
    `now_ns`). The history it can reach holds nothing later than `now_ns`
    anyway; asking for the future is a strategy bug, so it is refused loudly
    instead of answered with a silently empty or truncated result."""


class HistoryTruncatedError(CoreError, LookupError):
    """The strategy asked for history whose answer would reach into the part
    that `history_limit` dropped (a window starting at or before the last
    dropped event of a type it covers, and not confined to the kept part by
    `n`). The core does not know what the dropped part would have added, so
    it refuses instead of returning a silently shorter answer."""


class StaleContextError(CoreError, RuntimeError):
    """A `StrategyContext` was used after the callback it was built for had
    returned. Contexts are revoked on return so a stored one cannot be used
    to act or look at a later point in time."""


class OrderApiError(CoreError, ValueError):
    """The strategy used the order API incorrectly (duplicate client order
    id, cancel of an id it never placed, invalid size/price/side, timer in
    the past)."""


class AccountSocketError(CoreError, RuntimeError):
    """The account socket returned something the core cannot use: a
    pre-trade check answer that is neither None nor a non-empty str, or a
    forced order that is not an `OrderRequest` or reuses an id."""


class VenueProtocolError(CoreError, RuntimeError):
    """A fill model (venue socket) produced a report that contradicts the
    order's venue-side history: a report for an order that has not reached
    the venue yet, a fill before the acknowledgement, an overfill, a report
    after a terminal state, or no response at all to an order or cancel."""


class LatencyModelError(CoreError, ValueError):
    """A latency model returned something that is not a non-negative int."""


class MissingCostModelError(CoreError, RuntimeError):
    """A fill happened but no cost model was supplied. The core has no
    implicit fee: pass `NullCostModel()` explicitly to state zero cost."""


class CostModelError(CoreError, ValueError):
    """A cost model returned something that is not a finite number."""
