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
    """The event source went backwards in `exchange_time_ns`. The core does
    not re-sort a source silently: a backwards step is a data defect the
    data layer must detect and report, not something to paper over."""


class SourceEventTypeError(CoreError, TypeError):
    """The event source supplied something that is not a market-data or
    clock event (for example an order notice). Order notices are produced by
    the engine from the fill model's reports, never read from a source."""


class StaleContextError(CoreError, RuntimeError):
    """A `StrategyContext` was used after the callback it was built for had
    returned. Contexts are revoked on return so a stored one cannot be used
    to act or look at a later point in time."""


class OrderApiError(CoreError, ValueError):
    """The strategy used the order API incorrectly (duplicate client order
    id, cancel of an id it never placed, invalid size/price/side, timer in
    the past)."""


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
