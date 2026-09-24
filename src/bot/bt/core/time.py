"""Single time representation for the whole core.

Every timestamp inside the core is an `int` count of nanoseconds since
1970-01-01T00:00:00Z (UTC), range-checked to int64. `TIME_CONTRACT` states
this in machine-readable form.

There is one sanctioned way to turn a raw, unit-labelled value into one:
`to_nanos`. Conversion is exact:

* integers are scaled with integer arithmetic;
* floats and numeric strings go through `decimal.Decimal` of their shortest
  decimal representation, so `1700000000.123456789` (as a string) or
  `1.5` (as a float) convert without binary-float rounding; a value whose
  decimal representation has sub-nanosecond digits is rejected instead of
  being rounded silently;
* ISO-8601 strings are parsed by this module (not by `datetime`, whose
  resolution stops at microseconds and would drop the last three digits of
  `...00.123456789Z`) and must carry an explicit offset.

After conversion `to_nanos` checks the result against a plausibility window,
1970..2100 by default. A value 1000x too LARGE for its label (ms labelled
s, us labelled ms, ...) lands past 2100 and is rejected. A value too SMALL
for its label (s labelled ms or ns) still lands inside 1970..2100 (near
1970), so the default window cannot catch it; a caller that knows its
data's era passes `plausible=(min_ns, max_ns)` to catch that direction too
(the data layer does this per source).
"""
from __future__ import annotations

import datetime as dt
import numbers
import re
from decimal import Decimal, InvalidOperation
from typing import NewType, Union

from .errors import TimestampUnitError

Nanos = NewType("Nanos", int)

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1

# 1970-01-01T00:00:00Z .. 2100-01-01T00:00:00Z.
PLAUSIBLE_MIN_NS = 0
PLAUSIBLE_MAX_NS = 4_102_444_800_000_000_000

_UNIT_TO_NS_FACTOR: dict[str, int] = {
    "s": 1_000_000_000,
    "ms": 1_000_000,
    "us": 1_000,
    "ns": 1,
}

TIME_CONTRACT: dict = {
    "type": "int",
    "bits": 64,
    "unit": "ns",
    "epoch": "1970-01-01T00:00:00Z",
    "timezone": "UTC",
    "accepted_input_units": sorted(_UNIT_TO_NS_FACTOR) + ["iso"],
    "rounding": "none (inputs with sub-nanosecond digits are rejected)",
    "default_plausible_range_ns": [PLAUSIBLE_MIN_NS, PLAUSIBLE_MAX_NS],
}

_EPOCH_UTC = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

_ISO_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})"
    r"(?:[.,](?P<frac>\d+))?"
    r"(?P<tz>Z|z|[+-]\d{2}:?\d{2})?$"
)


def validate_nanos(value: object) -> Nanos:
    """The choke point every event timestamp passes through.

    Accepts Python ints and integral numpy scalars and returns an `int`
    itself (never a subclass: what crosses a path is a value, values.py);
    rejects bool (an int subclass in Python, never a timestamp), floats (a
    float cannot carry nanoseconds at epoch scale) and anything outside
    int64. Does not apply
    the plausibility window: a bare int handed to an event constructor has
    no unit label to cross-check. Use `to_nanos` for labelled raw values.
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise TimestampUnitError(
            f"timestamp must be an int of nanoseconds, got {type(value).__name__}"
        )
    # an int itself; an int subclass gives the int it holds (read by int,
    # never by the subclass: values.py); another integral type is
    # converted once, here
    ivalue = int.__index__(value) if isinstance(value, int) else int.__index__(int(value))
    if not (INT64_MIN <= ivalue <= INT64_MAX):
        raise TimestampUnitError(f"{ivalue} does not fit in int64")
    return Nanos(ivalue)


def _check_plausible(ns: int, what: str, plausible: tuple[int, int]) -> Nanos:
    lo, hi = plausible
    if not (lo <= ns <= hi):
        raise TimestampUnitError(
            f"{what} converts to {ns} ns, outside the plausible window "
            f"[{lo}, {hi}] -- likely a unit mismatch"
        )
    return validate_nanos(ns)


def to_nanos(
    value: Union[int, float, str, Decimal],
    unit: str,
    plausible: tuple[int, int] = (PLAUSIBLE_MIN_NS, PLAUSIBLE_MAX_NS),
) -> Nanos:
    """Convert `value` expressed in `unit` to validated `Nanos`, exactly.

    `unit` is one of "s", "ms", "us", "ns" or "iso". `plausible` is the
    inclusive ns window the result must fall in (default 1970..2100).
    """
    if unit == "iso":
        return _iso_to_nanos(value, plausible)
    if unit not in _UNIT_TO_NS_FACTOR:
        raise TimestampUnitError(
            f"unknown time unit {unit!r}; expected one of "
            f"{sorted(_UNIT_TO_NS_FACTOR)} or 'iso'"
        )
    factor = _UNIT_TO_NS_FACTOR[unit]
    if isinstance(value, bool):
        raise TimestampUnitError("bool is not a timestamp")
    if isinstance(value, numbers.Integral):
        ns = int(value) * factor
    elif isinstance(value, (float, str, Decimal)) or isinstance(value, numbers.Real):
        if isinstance(value, float) or (
            isinstance(value, numbers.Real) and not isinstance(value, (str, Decimal))
        ):
            text = repr(float(value))
        else:
            text = str(value).strip()
        try:
            dec = Decimal(text)
        except InvalidOperation as exc:
            raise TimestampUnitError(f"not a number: {value!r}") from exc
        if not dec.is_finite():
            raise TimestampUnitError(f"non-finite timestamp {value!r}")
        scaled = dec * factor
        if scaled != scaled.to_integral_value():
            raise TimestampUnitError(
                f"{value!r} {unit} has sub-nanosecond digits; refusing to round"
            )
        ns = int(scaled)
    else:
        raise TimestampUnitError(
            f"timestamp value for unit {unit!r} must be int, float, Decimal or "
            f"numeric str, got {type(value).__name__}"
        )
    return _check_plausible(ns, f"{value!r} labelled unit={unit!r}", plausible)


def _iso_to_nanos(value: object, plausible: tuple[int, int]) -> Nanos:
    if not isinstance(value, str):
        raise TimestampUnitError(f"iso timestamp must be str, got {type(value).__name__}")
    m = _ISO_RE.match(value.strip())
    if m is None:
        raise TimestampUnitError(f"unparseable ISO-8601 timestamp {value!r}")
    tz = m.group("tz")
    if tz is None:
        raise TimestampUnitError(
            f"ISO timestamp {value!r} has no timezone offset; UTC must be explicit"
        )
    frac = m.group("frac") or ""
    if len(frac) > 9:
        if frac[9:].strip("0"):
            raise TimestampUnitError(
                f"ISO timestamp {value!r} has sub-nanosecond digits; refusing to round"
            )
        frac = frac[:9]
    frac_ns = int(frac.ljust(9, "0")) if frac else 0
    try:
        base = dt.datetime.fromisoformat(
            f"{m.group('date')}T{m.group('h')}:{m.group('m')}:{m.group('s')}"
        )
    except ValueError as exc:
        raise TimestampUnitError(f"invalid calendar value in {value!r}: {exc}") from exc
    if tz in ("Z", "z"):
        offset = dt.timedelta(0)
    else:
        sign = 1 if tz[0] == "+" else -1
        digits = tz[1:].replace(":", "")
        hh, mm = int(digits[:2]), int(digits[2:])
        # An offset outside hh 00..23 / mm 00..59 is malformed; reading
        # "+09:75" as 10:15 would shift the time silently.
        if hh > 23 or mm > 59:
            raise TimestampUnitError(
                f"ISO timestamp {value!r} has an invalid UTC offset {tz!r} "
                f"(hours 00..23, minutes 00..59)"
            )
        offset = sign * dt.timedelta(hours=hh, minutes=mm)
    base_utc = base.replace(tzinfo=dt.timezone(offset)).astimezone(dt.timezone.utc)
    delta = base_utc - _EPOCH_UTC
    ns = (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + frac_ns
    return _check_plausible(ns, f"ISO timestamp {value!r}", plausible)


def nanos_to_iso(ns: int) -> str:
    """Render validated nanoseconds as `YYYY-MM-DDTHH:MM:SS.fffffffffZ`
    (exact inverse of `to_nanos(..., "iso")` for in-range values)."""
    ns = int(validate_nanos(ns))
    seconds, frac = divmod(ns, 1_000_000_000)
    base = _EPOCH_UTC + dt.timedelta(seconds=seconds)
    return base.strftime("%Y-%m-%dT%H:%M:%S") + f".{frac:09d}Z"
