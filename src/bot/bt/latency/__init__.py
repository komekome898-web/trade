"""Item 2 (old 4): the latency model.

Four delays, each its own distribution and each required (no default):
`feed` (market data: the venue's event -> the strategy, on top of the
event's recorded received time), `order` (the strategy's new order -> the
venue), `cancel` (the strategy's cancel -> the venue) and `notice` (a venue
answer -- ack, reject, fill, cancel, state unknown -- -> the strategy). The
core turns every venue answer into a notice EVENT delivered after `notice`
(`bot.bt.core.engine`), so accept and reject notices are events.

Distributions: `Constant(ns)`, `Empirical(samples_ns, seed)` (a measured
distribution: each draw picks one of the samples with a seeded generator),
`SeededUniform(low_ns, high_ns, seed)`. A seeded distribution owns its own
`random.Random(seed)`: the same seed gives the same sequence of delays, and
the core has no seed of its own (LEAD_DESIGN_items_1-12 section 1.1).
The model draws each channel from its own distribution object, so changing
one channel's delay changes nothing on the others (unless the caller passes
the same object for two channels, which then share one sequence).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence, Union

from bot.bt.core import CancelRequest, Event, OrderRequest, VenueReport
from bot.bt.orders.errors import ExecutionModelError

MAX_DELAY_NS = 3_600 * 1_000_000_000  # an hour: a larger delay is a unit error, refused


class LatencySpecError(ExecutionModelError):
    pass


def _ns(name: str, v) -> int:
    if type(v) is not int or v < 0 or v > MAX_DELAY_NS:
        raise LatencySpecError(f"{name} must be an int of ns in [0, {MAX_DELAY_NS}], got {v!r}")
    return v


@dataclass(frozen=True)
class Constant:
    ns: int

    def __post_init__(self) -> None:
        _ns("Constant.ns", self.ns)

    def draw(self) -> int:
        return self.ns


class Empirical:
    """A measured distribution: `samples_ns` (the measurements, ints of ns)
    and `seed`. Each draw is one of the samples, picked uniformly by a
    `random.Random(seed)` owned by this object."""

    def __init__(self, samples_ns: Sequence[int], seed: int) -> None:
        samples = tuple(samples_ns)
        if not samples:
            raise LatencySpecError("Empirical needs at least one sample")
        self.samples_ns = tuple(_ns("Empirical sample", s) for s in samples)
        if type(seed) is not int:
            raise LatencySpecError(f"seed must be an int, got {seed!r}")
        self.seed = seed
        self._rng = random.Random(seed)

    def draw(self) -> int:
        return self.samples_ns[self._rng.randrange(len(self.samples_ns))]


class SeededUniform:
    """A uniform integer delay in [low_ns, high_ns] from `random.Random(seed)`."""

    def __init__(self, low_ns: int, high_ns: int, seed: int) -> None:
        self.low_ns, self.high_ns = _ns("low_ns", low_ns), _ns("high_ns", high_ns)
        if self.low_ns > self.high_ns:
            raise LatencySpecError("low_ns must be <= high_ns")
        if type(seed) is not int:
            raise LatencySpecError(f"seed must be an int, got {seed!r}")
        self.seed = seed
        self._rng = random.Random(seed)

    def draw(self) -> int:
        return self._rng.randint(self.low_ns, self.high_ns)


Delay = Union[Constant, Empirical, SeededUniform]
_DELAY_TYPES = (Constant, Empirical, SeededUniform)


class LatencyModel:
    """The core latency socket. Every channel is required."""

    def __init__(self, *, feed: Delay, order: Delay, cancel: Delay, notice: Delay) -> None:
        for name, d in (("feed", feed), ("order", order), ("cancel", cancel), ("notice", notice)):
            if type(d) not in _DELAY_TYPES:
                raise LatencySpecError(f"{name} must be one of Constant / Empirical / SeededUniform, "
                                       f"got {type(d).__name__}")
        self.feed, self.order, self.cancel, self.notice = feed, order, cancel, notice
        # per channel: how many delays were drawn and their sum (for a run
        # record; the draws themselves follow from the seeds)
        self.draws: dict[str, int] = {"feed": 0, "order": 0, "cancel": 0, "notice": 0}
        self.total_ns: dict[str, int] = {"feed": 0, "order": 0, "cancel": 0, "notice": 0}

    def _draw(self, name: str, d: Delay) -> int:
        v = d.draw()
        self.draws[name] += 1
        self.total_ns[name] += v
        return v

    def feed_delay_ns(self, event: Event) -> int:
        return self._draw("feed", self.feed)

    def order_delay_ns(self, order: OrderRequest, sent_time_ns: int) -> int:
        return self._draw("order", self.order)

    def cancel_delay_ns(self, request: CancelRequest, sent_time_ns: int) -> int:
        return self._draw("cancel", self.cancel)

    def notice_delay_ns(self, report: VenueReport, venue_time_ns: int) -> int:
        return self._draw("notice", self.notice)


__all__ = ["MAX_DELAY_NS", "Constant", "Delay", "Empirical", "LatencyModel", "LatencySpecError", "SeededUniform"]
