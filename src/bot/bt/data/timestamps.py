"""Time normalisation of the data layer: every time a file carries becomes
int64 UTC nanoseconds, exactly, through the core's one conversion
(`bot.bt.core.time.to_nanos`).

Accepted forms (`unit` of the time declaration):

* ``s`` / ``ms`` / ``us`` / ``ns`` -- a decimal number of that unit since the
  epoch (UTC by definition). The text of the cell is handed to the core as a
  str, so ``1767571200.123456789`` s converts without a binary float; a value
  with digits below one nanosecond is refused, never rounded. A JSON number
  reaches here as an int or a Decimal (the JSON reader keeps the digits).
  A float is refused: its digits are no longer the ones the file wrote.
* ``iso`` -- ``YYYY-MM-DD``, ``YYYY-MM-DD[T| ]HH:MM`` or
  ``YYYY-MM-DD[T| ]HH:MM:SS[.fraction]``, with an optional offset (``Z``,
  ``+HH:MM``, ``+HHMM``). With an offset the text is exact as written. Without
  one, the declared time zone (``tz``) is applied: ``UTC`` or an IANA name
  (``Asia/Tokyo``); a wall-clock time that the zone skips (a DST gap) or
  repeats (a DST fold) is refused instead of guessed, and a time without an
  offset and without a declared zone is refused (no default zone).

Numeric units never take a zone other than UTC (an epoch count has no zone;
a declaration that says otherwise is contradictory and refused). A leap
second (``23:59:60``) is refused (the core's calendar has none).

`plausible_ns` (optional, inclusive [lo, hi]) narrows the core's default
1970..2100 window for a dataset whose era is known, so a value 1000x too
small for its unit (seconds labelled ms) is caught too.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..core.errors import TimestampUnitError
from ..core.time import PLAUSIBLE_MAX_NS, PLAUSIBLE_MIN_NS, to_nanos
from .errors import SpecError, TimeParseError

UNITS = ("s", "ms", "us", "ns", "iso")

_ISO_IN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:[T ](?P<h>\d{2}):(?P<m>\d{2})(?::(?P<s>\d{2})(?:[.,](?P<frac>\d+))?)?)?"
    r"(?P<tz>Z|z|[+-]\d{2}:?\d{2})?$"
)
_DEC = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


def check_zone(tz: Optional[str], unit: str) -> Optional[str]:
    """Validate a declared zone for a unit; returns it (None = not declared)."""
    if tz is None:
        return None
    if type(tz) is not str or not tz:
        raise SpecError(f"time.tz must be a non-empty str, got {tz!r}")
    if unit != "iso":
        if tz != "UTC":
            raise SpecError(f"time.tz {tz!r} with unit {unit!r}: an epoch count is UTC by definition")
        return tz
    if tz != "UTC":
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise SpecError(f"time.tz {tz!r} is not a known IANA time zone: {exc}") from None
    return tz


class TimeReader:
    """Reads one dataset's time cells: unit, zone and plausible window fixed
    at construction (from the dataset's declaration)."""

    def __init__(self, unit: str, tz: Optional[str] = None,
                 plausible_ns: Optional[tuple[int, int]] = None) -> None:
        if unit not in UNITS:
            raise SpecError(f"time.unit {unit!r} is not one of {list(UNITS)}")
        self.unit = unit
        self.tz = check_zone(tz, unit)
        self._zone = ZoneInfo(tz) if (unit == "iso" and tz not in (None, "UTC")) else None
        if plausible_ns is None:
            self.plausible = (PLAUSIBLE_MIN_NS, PLAUSIBLE_MAX_NS)
        else:
            try:
                lo, hi = plausible_ns
            except (TypeError, ValueError):
                raise SpecError(f"time.plausible_ns must be [lo, hi], got {plausible_ns!r}") from None
            if type(lo) is not int or type(hi) is not int or lo > hi:
                raise SpecError(f"time.plausible_ns must be two ints lo <= hi, got {plausible_ns!r}")
            self.plausible = (lo, hi)

    def read(self, value: Any) -> int:
        """One cell (a str from a CSV, an int / Decimal / str from JSON) -> ns."""
        try:
            if self.unit == "iso":
                return int(to_nanos(self._iso_text(value), "iso", self.plausible))
            t = type(value)
            if t is bool or t is float:
                raise TimeParseError(
                    f"time {value!r} ({t.__name__}) for unit {self.unit!r}: pass the digits as written "
                    f"(str, int or Decimal), not a {t.__name__}")
            if t is str:
                text = value.strip()
                if not _DEC.match(text):
                    raise TimeParseError(f"time {value!r} for unit {self.unit!r} is not a plain decimal number")
                return int(to_nanos(text, self.unit, self.plausible))
            if t is int or t is Decimal:
                return int(to_nanos(value, self.unit, self.plausible))
            raise TimeParseError(f"time {value!r} ({t.__name__}) for unit {self.unit!r} is not a number")
        except TimestampUnitError as exc:
            raise TimeParseError(f"time {value!r}: {exc}") from None

    def _iso_text(self, value: Any) -> str:
        if type(value) is not str:
            raise TimeParseError(f"iso time must be text, got {type(value).__name__} {value!r}")
        m = _ISO_IN.match(value.strip())
        if m is None:
            raise TimeParseError(f"unparseable ISO-8601 time {value!r}")
        h, mi, s = m.group("h") or "00", m.group("m") or "00", m.group("s") or "00"
        frac = m.group("frac")
        body = f"{m.group('date')}T{h}:{mi}:{s}" + (f".{frac}" if frac else "")
        tz = m.group("tz")
        if tz is not None:
            return body + tz
        if self.tz is None:
            raise TimeParseError(f"time {value!r} has no UTC offset and the dataset declares no time zone")
        if self.tz == "UTC":
            return body + "Z"
        return body + self._offset(m.group("date"), int(h), int(mi), int(s), value)

    def _offset(self, date: str, h: int, mi: int, s: int, shown: str) -> str:
        try:
            y, mo, d = (int(x) for x in date.split("-"))
            naive = dt.datetime(y, mo, d, h, mi, s)
        except ValueError as exc:
            raise TimeParseError(f"invalid calendar value in {shown!r}: {exc}") from None
        a = naive.replace(tzinfo=self._zone, fold=0)
        b = naive.replace(tzinfo=self._zone, fold=1)
        off_a, off_b = a.utcoffset(), b.utcoffset()
        if off_a != off_b:
            # either repeated (fold) or skipped (gap): which one it is, the
            # wall clock alone cannot say
            back = a.astimezone(dt.timezone.utc).astimezone(self._zone).replace(tzinfo=None)
            what = "does not exist (skipped by a DST change)" if back != naive else "is ambiguous (repeated by a DST change)"
            raise TimeParseError(f"wall-clock time {shown!r} in {self.tz} {what}; refusing to guess")
        total = int(off_a.total_seconds())
        if total % 60:
            raise TimeParseError(f"zone {self.tz} has a sub-minute offset at {shown!r}; not representable")
        sign = "+" if total >= 0 else "-"
        hh, mm = divmod(abs(total) // 60, 60)
        return f"{sign}{hh:02d}:{mm:02d}"
