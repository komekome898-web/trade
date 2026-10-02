"""The card's mouth (W1 spec C1) and the view a card reads.

    class Card(Protocol):
        name: str
        requires: list[SeriesSpec]     # the reference series it reads, each with its lag
        def exposure(self, view: CardView) -> float: ...   # called at the end t of a bar; -1.0 .. +1.0

A card is called at the end t of each bar of one instrument's bar series
(run.py) and answers how much to hold, -1.0 .. +1.0. It may keep internal
state, but the same input must give the same output (no random numbers).

`CardView` shows only what was available at t:
  * `bars(n)` -- the last `n` bars of the run's instrument whose end is <= t,
    read from the core's history (`StrategyContext.visible_events`): naming a
    position after the newest raises the core's `FuturePositionError` (a
    `LookAheadError`).
  * `ref(name)`, `ref_latest(name)`, `ref_at(name, row_time_ns)` -- the rows
    of a declared reference series whose available_at (row time + declared
    lag, bot.bt.data.reference) is <= t. They are the rows the core has
    delivered (nothing else is ever put in the lists the view reads), so a
    row not yet available is not there to be read. Naming one anyway -- a
    position after the newest delivered row, or `ref_at` a row time whose
    available_at is after t -- raises `RefLookAheadError` (a `LookAheadError`).
  * a series the card did not declare in `requires` is refused (`CardError`).
After the call returns the view is dead: every read raises the core's
`StaleContextError` (as the core does for its context), so a view kept by a
card cannot show rows delivered later.

The answer is checked (`check_exposure`): a number (int or float; a bool is
refused, as everywhere in bot.bt), finite, and inside [-1, 1]; otherwise
`ExposureError`.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence, runtime_checkable

import numpy as np

from bot.bt.core import EventType, LookAheadError, StaleContextError


class CardError(ValueError):
    """A card or its run is malformed (undeclared series, lag mismatch, bad bars)."""


class ExposureError(CardError):
    """A card answered something other than a finite number in [-1, 1]."""


class RefLookAheadError(LookAheadError, IndexError):
    """A read of a reference row that is not available at the view's time."""


@dataclass(frozen=True)
class SeriesSpec:
    """A reference series a card reads, and the lag the card states for it
    (int ns >= 0), or None for a series whose rows carry their own
    available_at (bot.bt.data.reference, per-row). The run refuses a card
    whose statement differs from the series' declaration."""
    name: str
    lag_ns: Optional[int]

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise CardError(f"SeriesSpec.name must be a non-empty str, got {self.name!r}")
        if self.lag_ns is not None and (type(self.lag_ns) is not int or self.lag_ns < 0):
            raise CardError(f"SeriesSpec {self.name!r}: lag_ns must be an int >= 0 or None, got {self.lag_ns!r}")


@runtime_checkable
class Card(Protocol):
    name: str
    requires: Sequence[SeriesSpec]

    def exposure(self, view: "CardView") -> float: ...


def check_exposure(value: Any, card_name: str, t_ns: int) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ExposureError(f"card {card_name!r} at t={t_ns}: exposure must be a number, "
                            f"got {type(value).__name__} {value!r}")
    x = float(value)
    if math.isnan(x):
        raise ExposureError(f"card {card_name!r} at t={t_ns}: exposure is NaN")
    if not (-1.0 <= x <= 1.0):
        raise ExposureError(f"card {card_name!r} at t={t_ns}: exposure {x!r} is outside [-1, 1]")
    return x


class RefRows:
    """The rows of one reference series available at the view's time:
    (row_time_ns, value) pairs, oldest first. Index and slice like a tuple
    inside 0 .. len-1; a position after the newest raises
    `RefLookAheadError`, one before the oldest an `IndexError`."""

    __slots__ = ("_times", "_values", "_end", "_alive", "_name")

    def __init__(self, name: str, times: list, values: list, end: int, alive: list) -> None:
        self._name, self._times, self._values, self._end, self._alive = name, times, values, end, alive

    def _check(self) -> None:
        if not self._alive[0]:
            raise StaleContextError("a card's view was used after its call returned")

    def __len__(self) -> int:
        self._check()
        return self._end

    def _pos(self, i: int) -> int:
        if type(i) is not int:
            raise TypeError(f"a row position must be an int, got {type(i).__name__}")
        p = i + self._end if i < 0 else i
        if p >= self._end:
            raise RefLookAheadError(f"reference {self._name!r}: position {i} is after the newest row available "
                                    f"now ({self._end} rows)")
        if p < 0:
            raise IndexError(f"reference {self._name!r}: position {i} is before the oldest row ({self._end} rows)")
        return p

    def __getitem__(self, i):
        self._check()
        if isinstance(i, slice):
            for b in (i.start, i.stop):
                if b is not None:
                    q = b + self._end if b < 0 else b
                    if q > self._end:
                        raise RefLookAheadError(f"reference {self._name!r}: slice bound {b} is after the newest "
                                                f"row available now ({self._end} rows)")
            idx = range(self._end)[i]
            return tuple((self._times[k], self._values[k]) for k in idx)
        p = self._pos(i)
        return (self._times[p], self._values[p])

    def __iter__(self):
        self._check()
        for k in range(self._end):
            yield (self._times[k], self._values[k])


class CardView:
    """What a card sees at the end t of one bar (module docstring)."""

    __slots__ = ("_ctx", "_now", "_refs", "_allowed", "_alive")

    def __init__(self, ctx: Any, now_ns: int, refs: dict, allowed: frozenset) -> None:
        self._ctx = ctx
        self._now = now_ns
        self._refs = refs  # name -> (times list, values list, lag_ns); lists hold delivered rows only
        self._allowed = allowed
        self._alive = [True]

    def _kill(self) -> None:
        self._alive[0] = False
        self._ctx = None
        self._refs = {}

    def _check(self) -> None:
        if not self._alive[0]:
            raise StaleContextError("a card's view was used after its call returned")

    @property
    def now_ns(self) -> int:
        return self._now

    def bars(self, n: int):
        """The last `n` bars (BarEvent, oldest first) with end <= now; fewer if
        fewer were delivered. The core's answer: a position after the newest
        raises FuturePositionError."""
        self._check()
        return self._ctx.visible_events(EventType.BAR, n=n)

    def _series(self, name: str) -> tuple:
        self._check()
        if name not in self._allowed:
            raise CardError(f"reference {name!r} is not in the card's requires {sorted(self._allowed)}")
        return self._refs[name]

    def ref(self, name: str) -> RefRows:
        times, values, _lag = self._series(name)
        return RefRows(name, times, values, len(times), self._alive)

    def ref_latest(self, name: str) -> Optional[tuple[int, float]]:
        times, values, _lag = self._series(name)
        if not times:
            return None
        return (times[-1], values[-1])

    def ref_at(self, name: str, row_time_ns: int) -> float:
        """The value of the row whose time is `row_time_ns`. With a constant
        lag, a row time whose available_at (row time + lag) is after now raises
        RefLookAheadError (whether or not such a row exists). With per-row
        availability, a row time after the newest row delivered so far raises
        RefLookAheadError (rows become available in time order). Otherwise a
        time with no row raises KeyError."""
        times, values, lag = self._series(name)
        if type(row_time_ns) is not int:
            raise TypeError(f"row_time_ns must be an int, got {type(row_time_ns).__name__}")
        if lag is not None and row_time_ns + lag > self._now:
            raise RefLookAheadError(f"reference {name!r}: a row at {row_time_ns} is available at "
                                    f"{row_time_ns + lag} (lag {lag}), after now {self._now}")
        if lag is None and (not times or row_time_ns > times[-1]):
            raise RefLookAheadError(f"reference {name!r}: no row at {row_time_ns} is available at now "
                                    f"{self._now} (newest available row: {times[-1] if times else None})")
        k = bisect.bisect_left(times, row_time_ns)
        if k < len(times) and times[k] == row_time_ns:
            return values[k]
        raise KeyError(f"reference {name!r} has no row at {row_time_ns}")


__all__ = ["Card", "CardError", "CardView", "ExposureError", "RefLookAheadError", "RefRows", "SeriesSpec",
           "check_exposure"]
