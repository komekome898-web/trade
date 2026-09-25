"""V2 adversary: the time normalisation over the full grid of
(unit x instant x written form x declared zone), judged by an oracle that
works from the calendar with integers and fractions (never through the
code under test's path: no `to_nanos`, no fold comparison).

Grid axes (enumerated by machine, count asserted below):
  instants  -- epoch 0, +1 ns, 2038-01-19T03:14:07 and :08 (int32 seconds
               edge), 2026 instants with 0..9 fraction digits, the last ns
               of 2099, 2100-01-01T00:00:00 (inclusive upper edge), 1 ns after
               it, 1 ns before the epoch
  numeric forms -- decimal text in s / ms / us / ns (exact digits), the same
               with trailing zero digits, an int (when whole), a Decimal, a
               float (refused: its digits are not the written ones), a bool
  ISO forms -- Z / +00:00 / +09:00 / -05:00 / +0530 offsets, "T" and " ",
               0..9 fraction digits, 10+ digits with zero tail (accepted) and
               non-zero tail (refused), naive text under tz UTC / Asia/Tokyo /
               America/New_York / none (refused), minute-only and date-only
Not in the grid (named so the gap is visible): leap seconds other than
23:59:60 on 2016-12-31 (one is enough: the calendar has none); zones other
than the three (the zone rule is one code path, the oracle checks it on a
DST zone and a fixed-offset zone); exponent notation (refused by the
decimal-number rule, one case below).
"""
from __future__ import annotations

import calendar
import datetime as dt
import itertools
from decimal import Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo

import pytest

from bot.bt.data import SpecError, TimeParseError, TimeReader

NS = 10**9
LO, HI = 0, 4_102_444_800 * NS  # the core's default window, inclusive


def utc_ns(y, mo, d, h=0, mi=0, s=0, f=0):
    return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) * NS + f


INSTANTS = [0, 1, utc_ns(2038, 1, 19, 3, 14, 7), utc_ns(2038, 1, 19, 3, 14, 8),
            *(utc_ns(2026, 1, 5, 12, 34, 56) + int("123456789"[:k].ljust(9, "0") or 0) for k in range(10)),
            HI - 1, HI, HI + 1, -1]
UNIT_NS = {"s": NS, "ms": 10**6, "us": 10**3, "ns": 1}


def dec_text(t, unit, pad=0):
    q, r = divmod(t, UNIT_NS[unit])
    if r == 0 and not pad:
        return str(q)
    width = len(str(UNIT_NS[unit])) - 1
    frac = f"{r:0{width}d}".rstrip("0") if width else ""
    frac = (frac + "0" * pad) if (frac or pad) else ""
    if q < 0 and r:  # write negative values as -(|t|)
        a = -t
        q2, r2 = divmod(a, UNIT_NS[unit])
        f2 = (f"{r2:0{width}d}".rstrip("0") + "0" * pad) if width else ""
        return f"-{q2}" + (f".{f2}" if f2 else "")
    return f"{q}" + (f".{frac}" if frac else "")


def expect_numeric(value_exact: Fraction):
    """Oracle: exact ns or 'refuse'."""
    if value_exact.denominator != 1:
        return "refuse"
    n = value_exact.numerator
    return n if LO <= n <= HI else "refuse"


NUMERIC_CASES = []
for t, unit, pad in itertools.product(INSTANTS, UNIT_NS, (0, 3)):
    exact = Fraction(t)  # the instant, in ns
    text = dec_text(t, unit, pad)
    value = Fraction(Decimal(text)) * UNIT_NS[unit]
    assert value == exact, (t, unit, text)
    NUMERIC_CASES.append((text, unit, expect_numeric(value)))
    if value.denominator == 1 and (t % UNIT_NS[unit] == 0) and pad == 0:
        NUMERIC_CASES.append((t // UNIT_NS[unit], unit, expect_numeric(value)))
        NUMERIC_CASES.append((Decimal(text), unit, expect_numeric(value)))
# sub-unit digits beyond a nanosecond: refused, never rounded
for unit in UNIT_NS:
    NUMERIC_CASES.append((dec_text(utc_ns(2026, 1, 5), unit) + ".0000000001", unit, "refuse"))
NUMERIC_CASES += [(1767571200.5, "s", "refuse"), (True, "s", "refuse"), ("1.7e9", "s", "refuse"),
                  ("", "s", "refuse"), ("1_767_571_200", "s", "refuse"), ("nan", "s", "refuse")]


def test_numeric_grid_size():
    assert len(NUMERIC_CASES) == 238


@pytest.mark.parametrize("value,unit,want", NUMERIC_CASES, ids=[f"{u}:{v!r}"[:60] for v, u, _ in NUMERIC_CASES])
def test_numeric_units(value, unit, want):
    r = TimeReader(unit, "UTC")
    if want == "refuse":
        with pytest.raises(TimeParseError):
            r.read(value)
    else:
        got = r.read(value)
        assert type(got) is int and got == want


OFFSETS = {"Z": 0, "+00:00": 0, "+09:00": 9 * 3600, "-05:00": -5 * 3600, "+0530": 5 * 3600 + 1800}


def iso_text(t, off_s, sep, digits, suffix, extra=""):
    sec, frac = divmod(t + off_s * NS, NS)
    d = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=sec)
    f9 = f"{frac:09d}"
    body = d.strftime(f"%Y-%m-%d{sep}%H:%M:%S")
    if digits:
        body += "." + f9[:digits] + extra
    return body + suffix, f9[digits:].strip("0") == ""


ISO_CASES = []
for t in INSTANTS:
    if t < 0:
        continue  # pre-epoch ISO: one case below
    for (suf, off), sep, digits in itertools.product(OFFSETS.items(), ("T", " "), (0, 3, 6, 9)):
        if t + off * NS < 0:
            continue
        text, exact = iso_text(t, off, sep, digits, suf)
        if not exact:
            continue  # the text cannot carry this instant at this precision
        want = t if LO <= t <= HI else "refuse"
        ISO_CASES.append((text, "UTC", want))
    text, _ = iso_text(t, 0, "T", 9, "Z", extra="000")
    ISO_CASES.append((text, "UTC", t if LO <= t <= HI else "refuse"))  # 12 digits, zero tail
ISO_CASES += [("1969-12-31T23:59:59.999999999Z", "UTC", "refuse"),  # 1 ns before the epoch
              ("2026-01-05T12:34:56.1234567891Z", "UTC", "refuse"),  # sub-ns digit
              ("2016-12-31T23:59:60Z", "UTC", "refuse"),  # leap second
              ("2026-02-30T00:00:00Z", "UTC", "refuse"),
              ("2026-01-05T12:34:56+09:75", "UTC", "refuse"),
              ("2026-01-05 12:34", "UTC", utc_ns(2026, 1, 5, 12, 34)),
              ("2026-01-05", "UTC", utc_ns(2026, 1, 5)),
              ("2026-01-05 12:34:56", None, "refuse"),  # no offset, no declared zone
              ("20260105T123456Z", "UTC", "refuse")]


def zone_oracle(text, zone):
    """Every UTC instant whose wall clock in `zone` reads `text` (naive),
    found by trying each offset the zone uses within two days of it."""
    naive = dt.datetime.fromisoformat(text.replace(" ", "T")) if len(text) > 10 else dt.datetime.fromisoformat(text)
    z = ZoneInfo(zone)
    offs = set()
    for h in range(-48, 49):
        probe = (naive + dt.timedelta(hours=h)).replace(tzinfo=dt.timezone.utc).astimezone(z)
        offs.add(probe.utcoffset())
    hits = []
    for off in offs:
        u = (naive - off).replace(tzinfo=dt.timezone.utc)
        if u.astimezone(z).replace(tzinfo=None) == naive:
            hits.append(calendar.timegm(u.timetuple()) * NS)
    hits = sorted(set(hits))
    return hits[0] if len(hits) == 1 else "refuse"


ZONE_TEXTS = ["2026-01-05 08:45", "2026-01-05 00:00:00", "2026-01-04 23:59:59", "2026-07-01 12:00:00",
              "2026-03-08 02:30:00", "2026-03-08 01:59:59", "2026-03-08 03:00:00",  # New York spring gap
              "2026-11-01 01:30:00", "2026-11-01 00:59:59", "2026-11-01 02:00:00",  # New York autumn fold
              "2026-12-31 23:59:59"]
for text, zone in itertools.product(ZONE_TEXTS, ("Asia/Tokyo", "America/New_York")):
    ISO_CASES.append((text, zone, zone_oracle(text, zone)))
for text in ZONE_TEXTS:
    base = text if len(text) > 16 else text + ":00"
    ISO_CASES.append((text, "UTC", calendar.timegm(dt.datetime.fromisoformat(base.replace(" ", "T")).timetuple()) * NS))


def test_iso_grid_size_and_zone_cases_cover_gap_and_fold():
    assert len(ISO_CASES) == 459
    refused_ny = [t for t, z, w in ISO_CASES if z == "America/New_York" and w == "refuse"]
    assert "2026-03-08 02:30:00" in refused_ny and "2026-11-01 01:30:00" in refused_ny


@pytest.mark.parametrize("text,zone,want", ISO_CASES, ids=[f"{z}:{t}" for t, z, _ in ISO_CASES])
def test_iso(text, zone, want):
    r = TimeReader("iso", zone)
    if want == "refuse":
        with pytest.raises(TimeParseError):
            r.read(text)
    else:
        got = r.read(text)
        assert type(got) is int and got == want


@pytest.mark.parametrize("unit,tz", [("s", "Asia/Tokyo"), ("ms", "+09:00"), ("iso", "Mars/Olympus"), ("iso", ""),
                                     ("minutes", "UTC")])
def test_contradictory_or_unknown_declarations_are_refused(unit, tz):
    with pytest.raises(SpecError):
        TimeReader(unit, tz)


def test_plausible_window_catches_a_unit_too_small():
    # seconds labelled ms land near 1970: the default window lets it pass, a declared era refuses it
    t_s = str(utc_ns(2026, 1, 5) // NS)
    assert TimeReader("ms", "UTC").read(t_s) == int(t_s) * 10**6
    with pytest.raises(TimeParseError):
        TimeReader("ms", "UTC", (utc_ns(2000, 1, 1), utc_ns(2100, 1, 1))).read(t_s)
