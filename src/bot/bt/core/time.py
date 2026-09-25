"""Single time representation for the whole core.

Every timestamp inside the core is an `int` count of nanoseconds since
1970-01-01T00:00:00Z (UTC), range-checked to int64. `TIME_CONTRACT` states
this in machine-readable form.

There is one sanctioned way to turn a raw, unit-labelled value into one:
`to_nanos`. Conversion is exact:

* integers are scaled with integer arithmetic;
* a Fraction is scaled with integer arithmetic too (numerator x factor must
  divide by the denominator), never through a float (round 15, i0-r14-03);
* floats go through `decimal.Decimal` of their shortest decimal
  representation, and numeric strings and Decimals are read as the decimal
  they write, so `1700000000.123456789` (as a string) or `1.5` (as a
  float) convert without binary-float rounding; a value whose decimal
  representation has sub-nanosecond digits is rejected instead of being
  rounded silently;
* a number of another class is converted exactly first (values.py `scalar`):
  numpy's integers and float16/32/64 as they are; a numpy longdouble only
  when a float holds its value exactly (else refused, never rounded);
  numpy's timedelta64 / datetime64 -- a count in a unit of their own -- are
  refused (round 15, i0-r14-04);
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
import re
from decimal import Decimal, InvalidOperation
from typing import NewType, Union

from .errors import TimestampUnitError
from .values import (PlainDecimal, PlainFraction, as_int, as_text, derives, exact_context, fraction_parts,
                     int_text, scalar, type_name, value_text)

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


# The decimal arithmetic of `to_nanos` never reads the thread's decimal context
# (process state any party can change: its precision, rounding and traps would
# decide the result; round 14, i0-r13-01): each conversion makes a context of
# its own (values.exact_context: exact, every error trapped).
# a scaled value whose exponent says it has more than this many digits is far
# outside int64 (19 digits); it is refused before an int is made of it
_MAX_SCALED_DIGITS = 30
# a Fraction whose numerator has this many more bits than its denominator is
# far outside int64 ns in every unit; refused before the product is made
_MAX_SCALED_BITS = 200


def _decimal_context():
    return exact_context()


def _shown(value: object, ctx) -> str:
    """A caller's value in an error text, made without running its code and
    never failing (a Decimal written by the fixed context, not the thread's)."""
    if derives(type(value), Decimal):
        return f"Decimal('{ctx.to_sci_string(value)}')"
    return value_text(value)


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
    # one rule for what is an int (values.py `as_int`): the REAL type is an
    # int (a subclass gives the int it holds, read by int) or an integral
    # number of the numeric tower (numpy's, say), converted once, here;
    # never a bool, never an object that only claims to be an int
    try:
        ivalue = as_int(value, "timestamp")
    except ValueError:
        raise TimestampUnitError(
            f"timestamp must be an int of nanoseconds, got {type_name(value)}"
        ) from None
    if not (INT64_MIN <= ivalue <= INT64_MAX):
        raise TimestampUnitError(f"{int_text(ivalue)} does not fit in int64")
    return Nanos(ivalue)


def _check_plausible(ns: int, what: str, plausible: tuple[int, int]) -> Nanos:
    lo, hi = plausible
    if not (lo <= ns <= hi):
        raise TimestampUnitError(
            f"{what} converts to {int_text(ns)} ns, outside the plausible window "
            f"[{value_text(lo)}, {value_text(hi)}] -- likely a unit mismatch"
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
    # the value as a built-in scalar, by its REAL type (values.py `scalar`:
    # numpy numbers converted once, a subclass read by its built-in type)
    try:
        v = scalar(value, "timestamp")
    except ValueError:
        v = None
    if type(v) is bool:
        raise TimestampUnitError(f"a bool ({type_name(value)}) is not a timestamp")
    ctx = _decimal_context()
    shown = _shown(value, ctx)
    t = type(v)
    if t is int:
        ns = v * factor
    elif t is PlainFraction:
        # exactly, with ints: numerator x factor must divide by the denominator
        n, d = fraction_parts(v)
        if n.bit_length() - d.bit_length() > _MAX_SCALED_BITS:
            raise TimestampUnitError(f"{shown} labelled unit={unit!r} is far outside int64 ns")
        q, r = divmod(n * factor, d)
        if r:
            raise TimestampUnitError(f"{shown} {unit} has sub-nanosecond digits; refusing to round")
        ns = q
    elif t is float or t is str or t is PlainDecimal:
        text = v.strip() if t is str else ctx.to_sci_string(v) if t is PlainDecimal else float.__repr__(v)
        try:
            dec = ctx.create_decimal(text)
        except InvalidOperation as exc:
            raise TimestampUnitError(f"not a number: {shown}") from exc
        if not dec.is_finite():
            raise TimestampUnitError(f"non-finite timestamp {shown}")
        # every operation in the core's own context (the comparison and the
        # int too: Decimal's != and int() would read the thread's context)
        scaled = ctx.multiply(dec, ctx.create_decimal(factor))
        if not scaled.is_zero() and scaled.adjusted() >= _MAX_SCALED_DIGITS:
            raise TimestampUnitError(f"{shown} labelled unit={unit!r} is far outside int64 ns")
        if not ctx.compare(scaled, ctx.to_integral_value(scaled)).is_zero():
            raise TimestampUnitError(
                f"{shown} {unit} has sub-nanosecond digits; refusing to round"
            )
        # at most _MAX_SCALED_DIGITS digits: far below any int <-> str digit limit
        ns = int(ctx.to_sci_string(ctx.quantize(scaled, ctx.create_decimal(1))))
    else:
        raise TimestampUnitError(
            f"timestamp value for unit {unit!r} must be int, float, Decimal, Fraction or "
            f"numeric str, got {type_name(value)}"
        )
    return _check_plausible(ns, f"{shown} labelled unit={unit!r}", plausible)


def _iso_to_nanos(value: object, plausible: tuple[int, int]) -> Nanos:
    try:
        value = as_text(value, "iso timestamp")  # a str itself (its own strip, not a subclass's)
    except ValueError:
        raise TimestampUnitError(f"iso timestamp must be str, got {type_name(value)}") from None
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
