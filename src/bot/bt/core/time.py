"""Single time representation for the whole core (requirement V1).

Every timestamp that reaches an `Event` (src/bot/bt/core/events.py) is a
validated int64 nanosecond count since the Unix epoch, UTC. There is exactly
one sanctioned way to produce one from a raw number or string: `to_nanos`.
Constructing an `Event` bypasses this only if the caller already has a
correctly-scaled int, in which case `validate_nanos` (called from
`Event.__post_init__`) still runs — so the type/range check always applies,
even to values that skip unit conversion entirely.

Mixed units are the concrete failure mode this guards against: a feed that
mistakenly reports milliseconds while another reports seconds and both get
labelled "ns". `to_nanos` refuses to trust the caller's unit label blindly:
after conversion it checks the result against a plausibility window
(roughly 1970..2100). A value that is off by a factor of 1000 (the classic
s/ms/us mix-up) lands far outside that window and is rejected, rather than
silently producing a timestamp that is 1000x too large or too small.
"""
from __future__ import annotations

import datetime as dt
from typing import NewType, Union

Nanos = NewType("Nanos", int)

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1

# 1970-01-01T00:00:00Z .. 2100-01-01T00:00:00Z. Wide enough to never reject a
# real market timestamp in this project's lifetime, narrow enough that a
# unit mix-up (e.g. seconds mislabelled as nanoseconds, or vice versa) lands
# outside it by orders of magnitude.
_PLAUSIBLE_MIN_NS = 0
_PLAUSIBLE_MAX_NS = 4_102_444_800_000_000_000

_UNIT_TO_NS_FACTOR: dict[str, int] = {
    "s": 1_000_000_000,
    "ms": 1_000_000,
    "us": 1_000,
    "ns": 1,
}

_EPOCH_UTC = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


class TimestampUnitError(ValueError):
    """Unknown unit label, wrong value type, out-of-int64-range result, or a
    magnitude that is implausible for the declared unit (unit mislabeling)."""


def validate_nanos(value: object) -> Nanos:
    """The single choke point every `Event.received_time_ns` passes through.

    Rejects non-int values (including bool, which is an int subclass in
    Python but never a valid timestamp here) and values outside int64 range.
    Does NOT do a plausibility check by itself -- callers that go through
    `to_nanos` already had that check applied during unit conversion; a bare
    ns int handed straight to an Event constructor is trusted to already be
    ns (there is no unit label to cross-check it against at this point).
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TimestampUnitError(
            f"received_time_ns must be int, got {type(value).__name__}"
        )
    if not (_INT64_MIN <= value <= _INT64_MAX):
        raise TimestampUnitError(f"{value} does not fit in int64")
    return Nanos(value)


def to_nanos(value: Union[int, float, str], unit: str) -> Nanos:
    """Convert `value` in `unit` to a validated `Nanos`.

    `unit` in {"s", "ms", "us", "ns", "iso"}. This is the only sanctioned
    entry point for turning a raw, unit-labelled number or ISO-8601 string
    into a `Nanos` value; anything else must go through here rather than
    hand-rolling `int(seconds * 1e9)` at a call site, because the
    plausibility check below only runs here.
    """
    if unit == "iso":
        return _iso_to_nanos(value)
    if unit not in _UNIT_TO_NS_FACTOR:
        raise TimestampUnitError(
            f"unknown time unit {unit!r}; expected one of "
            f"{sorted(_UNIT_TO_NS_FACTOR)} or 'iso'"
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TimestampUnitError(
            f"timestamp value for unit {unit!r} must be int or float, "
            f"got {type(value).__name__}"
        )
    ns = round(value * _UNIT_TO_NS_FACTOR[unit])
    if not (_PLAUSIBLE_MIN_NS <= ns <= _PLAUSIBLE_MAX_NS):
        raise TimestampUnitError(
            f"{value} labelled unit={unit!r} converts to {ns} ns, which "
            f"falls outside the plausible 1970..2100 window -- likely a "
            f"unit mismatch (e.g. seconds mislabelled as {unit!r})"
        )
    return validate_nanos(ns)


def _iso_to_nanos(value: object) -> Nanos:
    if not isinstance(value, str):
        raise TimestampUnitError(
            f"iso timestamp must be str, got {type(value).__name__}"
        )
    text = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise TimestampUnitError(f"unparseable ISO timestamp {value!r}: {exc}") from exc
    if parsed.tzinfo is None:
        raise TimestampUnitError(
            f"ISO timestamp {value!r} has no timezone offset; UTC must be explicit"
        )
    parsed_utc = parsed.astimezone(dt.timezone.utc)
    delta = parsed_utc - _EPOCH_UTC
    # Exact integer arithmetic (no float seconds) -- datetime's own
    # resolution tops out at microseconds, so this is lossless relative to
    # what the ISO string could express in the first place.
    ns = (
        delta.days * 86_400_000_000_000
        + delta.seconds * 1_000_000_000
        + delta.microseconds * 1_000
    )
    if not (_PLAUSIBLE_MIN_NS <= ns <= _PLAUSIBLE_MAX_NS):
        raise TimestampUnitError(
            f"ISO timestamp {value!r} converts to {ns} ns, outside 1970..2100"
        )
    return validate_nanos(ns)
