"""The venue's rules, as the run declares them.

Two kinds of rule, and neither has a default:

* **Policies** decide what the venue does in a situation: an off-tick price
  (`off_tick`), a size under the minimum (`below_min_qty`), a size off the
  size grid (`off_step`), a post-only order that would take (`post_only`), a
  market order that exhausts the book (`market_remainder`), a self-match
  (`self_trade`), a size-down amend (`amend_qty_down`), a market order with
  no book to price it (`market_ref`), an order outside trading hours
  (`outside_session`). A policy the run did not declare is `None`
  ("not declared"); when its situation arises the venue raises
  `RuleNotDeclaredError` -- it never picks a behaviour for the run.
* **Constraints** exist only when declared: trading hours (`sessions`,
  `closed`) and a daily price band (`price_limit`). Not declared = the model
  has no such constraint for this run (a 24/7 crypto venue has none). A
  constraint carries the `source` of what it encodes (the exchange's rule
  text), because its values come from an exchange rulebook.

A price change of a resting order always loses its queue priority (every
venue works that way; it is the definition of a new price, not a policy), so
`amend_price` accepts only "lose_priority". A size increase always loses
priority too. Only a size decrease is a policy (`amend_qty_down`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from .errors import RuleNotDeclaredError, RuleValueError

NS_PER_MIN = 60 * 1_000_000_000
NS_PER_DAY = 24 * 60 * NS_PER_MIN

POLICY_VALUES: dict[str, tuple[str, ...]] = {
    "off_tick": ("reject", "round_passive"),
    "below_min_qty": ("reject",),
    "off_step": ("reject", "round_down"),
    "post_only": ("reject_if_crossing", "cancel_if_crossing"),
    "market_remainder": ("cancel",),
    "self_trade": ("cancel_taker", "cancel_maker", "cancel_both"),
    "amend_qty_down": ("keep_priority", "lose_priority"),
    "amend_price": ("lose_priority",),
    "market_ref": ("last_trade", "next_bar_open"),
    "outside_session": ("reject", "queue_to_next_open"),
}


def _source(value) -> str:
    if type(value) is not str or not value.strip():
        raise RuleValueError(f"a constraint needs a non-empty source (the rule text it encodes), got {value!r}")
    return value


_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _minutes(text: str) -> int:
    m = _HHMM.match(text) if type(text) is str else None
    if m is None:
        raise RuleValueError(f"a session time must be 'HH:MM', got {text!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


@dataclass(frozen=True)
class Sessions:
    """Daily trading windows in local time. `windows`: ("HH:MM", "HH:MM")
    pairs, start included, end excluded. `utc_offset_minutes`: local time - UTC
    (JST = 540). `weekdays`: the days the windows apply, 0 = Monday ...
    6 = Sunday (a holiday calendar goes in `ClosedWindows`)."""

    windows: tuple[tuple[str, str], ...]
    utc_offset_minutes: int
    weekdays: tuple[int, ...]
    source: str

    def __post_init__(self) -> None:
        if not self.windows:
            raise RuleValueError("sessions need at least one window")
        spans = []
        for w in self.windows:
            if len(w) != 2:
                raise RuleValueError(f"a session window is (start, end), got {w!r}")
            a, b = _minutes(w[0]), _minutes(w[1])
            if a >= b:
                raise RuleValueError(f"a session window must start before it ends, got {w!r}")
            spans.append((a, b))
        spans.sort()
        for (a0, b0), (a1, _b1) in zip(spans, spans[1:]):
            if a1 < b0:
                raise RuleValueError(f"session windows overlap: {self.windows!r}")
        object.__setattr__(self, "_spans", tuple(spans))
        if type(self.utc_offset_minutes) is not int or not -24 * 60 < self.utc_offset_minutes < 24 * 60:
            raise RuleValueError(f"utc_offset_minutes must be an int in (-1440, 1440), got {self.utc_offset_minutes!r}")
        days = tuple(self.weekdays)
        if not days or any(type(d) is not int or not 0 <= d <= 6 for d in days) or len(set(days)) != len(days):
            raise RuleValueError(f"weekdays must be distinct ints 0..6, got {self.weekdays!r}")
        object.__setattr__(self, "weekdays", days)
        object.__setattr__(self, "source", _source(self.source))

    def _local(self, t: int) -> tuple[int, int, int]:
        local = t + self.utc_offset_minutes * NS_PER_MIN
        day = local // NS_PER_DAY
        weekday = (day + 3) % 7  # 1970-01-01 was a Thursday
        return day, weekday, local - day * NS_PER_DAY

    def is_open(self, t: int) -> bool:
        _day, weekday, in_day = self._local(t)
        if weekday not in self.weekdays:
            return False
        minute_ns = in_day
        return any(a * NS_PER_MIN <= minute_ns < b * NS_PER_MIN for a, b in self._spans)  # type: ignore[attr-defined]

    def next_open(self, t: int) -> int:
        """The first window start strictly after `t` (or `t` itself when open)."""
        if self.is_open(t):
            return t
        day, _wd, _ = self._local(t)
        offset = self.utc_offset_minutes * NS_PER_MIN
        for d in range(day, day + 15):
            if (d + 3) % 7 not in self.weekdays:
                continue
            for a, _b in self._spans:  # type: ignore[attr-defined]
                start = d * NS_PER_DAY + a * NS_PER_MIN - offset
                if start > t:
                    return start
        raise RuleValueError("no session opens within 15 days")  # pragma: no cover - weekdays is non-empty


@dataclass(frozen=True)
class ClosedWindows:
    """Periods in UTC ns, [start, end), when the venue does not trade (a
    weekend for FX, a holiday for JPX)."""

    windows: tuple[tuple[int, int], ...]
    source: str

    def __post_init__(self) -> None:
        out = []
        for w in self.windows:
            if len(w) != 2 or any(type(x) is not int for x in w) or w[0] >= w[1]:
                raise RuleValueError(f"a closed window is (start_ns, end_ns) ints with start < end, got {w!r}")
            out.append((w[0], w[1]))
        object.__setattr__(self, "windows", tuple(sorted(out)))
        object.__setattr__(self, "source", _source(self.source))

    def containing(self, t: int) -> Optional[tuple[int, int]]:
        for a, b in self.windows:
            if a <= t < b:
                return (a, b)
        return None


@dataclass(frozen=True)
class PriceLimit:
    """A daily price band: prices in [base - width, base + width] are allowed."""

    base: float
    width: float
    source: str

    def __post_init__(self) -> None:
        for name in ("base", "width"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
                raise RuleValueError(f"price_limit.{name} must be a number > 0, got {v!r}")
            object.__setattr__(self, name, float(v))
        if self.width >= self.base:
            raise RuleValueError("price_limit.width must be below base")
        object.__setattr__(self, "source", _source(self.source))

    @property
    def low(self) -> float:
        return self.base - self.width

    @property
    def high(self) -> float:
        return self.base + self.width

    def allows(self, price: float) -> bool:
        return self.low <= price <= self.high


@dataclass(frozen=True)
class VenueRules:
    """The rules one run declares. Every field is "not declared" (None)
    unless the run states it; see the module docstring for what that means."""

    off_tick: Optional[str] = None
    below_min_qty: Optional[str] = None
    off_step: Optional[str] = None
    post_only: Optional[str] = None
    market_remainder: Optional[str] = None
    self_trade: Optional[str] = None
    amend_qty_down: Optional[str] = None
    amend_price: Optional[str] = None
    market_ref: Optional[str] = None
    outside_session: Optional[str] = None
    sessions: Optional[Sessions] = None
    closed: Optional[ClosedWindows] = None
    price_limit: Optional[PriceLimit] = None

    def __post_init__(self) -> None:
        for name, allowed in POLICY_VALUES.items():
            v = getattr(self, name)
            if v is None:
                continue
            if type(v) is not str or v not in allowed:
                raise RuleValueError(f"rule {name}={v!r}: the model knows {allowed}")
        for name, cls in (("sessions", Sessions), ("closed", ClosedWindows), ("price_limit", PriceLimit)):
            v = getattr(self, name)
            if v is not None and type(v) is not cls:
                raise RuleValueError(f"rule {name} must be a {cls.__name__}, got {type(v).__name__}")
        if (self.sessions is not None or self.closed is not None) and self.outside_session is None:
            # hours without a policy for an order outside them: refused now,
            # not when the first such order arrives
            raise RuleNotDeclaredError("trading hours are declared but outside_session is not")

    def need(self, name: str) -> str:
        """The declared value of policy `name`; RuleNotDeclaredError if the run
        did not declare it (the situation it decides has arisen)."""
        if name not in POLICY_VALUES:
            raise KeyError(name)
        v = getattr(self, name)
        if v is None:
            raise RuleNotDeclaredError(
                f"the venue rule {name!r} decides this situation and the run did not declare it "
                f"(one of {POLICY_VALUES[name]})"
            )
        return v

    # -- hours ---------------------------------------------------------------
    @property
    def has_hours(self) -> bool:
        return self.sessions is not None or self.closed is not None

    def is_open(self, t: int) -> bool:
        if self.sessions is not None and not self.sessions.is_open(t):
            return False
        if self.closed is not None and self.closed.containing(t) is not None:
            return False
        return True

    def next_open(self, t: int) -> int:
        """The first instant >= t at which the venue is open."""
        for _ in range(64):
            moved = False
            if self.sessions is not None and not self.sessions.is_open(t):
                t, moved = self.sessions.next_open(t), True
            if self.closed is not None:
                w = self.closed.containing(t)
                if w is not None:
                    t, moved = w[1], True
            if not moved:
                return t
        raise RuleValueError("trading hours never open (sessions and closed windows cover every instant)")


def sessions_from_pairs(pairs: Sequence[Sequence[str]], *, utc_offset_minutes: int, weekdays: Sequence[int],
                        source: str) -> Sessions:
    return Sessions(tuple((str(a), str(b)) for a, b in pairs), utc_offset_minutes, tuple(weekdays), source)
