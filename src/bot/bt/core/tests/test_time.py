"""V1: single time representation, unit-mismatch detection."""
from __future__ import annotations

import unittest

from bot.bt.core.time import TimestampUnitError, to_nanos, validate_nanos


class ValidateNanosTest(unittest.TestCase):
    def test_accepts_plain_int(self):
        self.assertEqual(int(validate_nanos(123)), 123)

    def test_rejects_float(self):
        with self.assertRaises(TimestampUnitError):
            validate_nanos(123.0)

    def test_rejects_bool(self):
        # bool is an int subclass in Python; explicitly excluded because it
        # is never a meaningful timestamp.
        with self.assertRaises(TimestampUnitError):
            validate_nanos(True)

    def test_rejects_str(self):
        with self.assertRaises(TimestampUnitError):
            validate_nanos("123")

    def test_rejects_out_of_int64_range(self):
        with self.assertRaises(TimestampUnitError):
            validate_nanos(2**63)
        with self.assertRaises(TimestampUnitError):
            validate_nanos(-(2**63) - 1)

    def test_accepts_int64_bounds(self):
        validate_nanos(2**63 - 1)
        validate_nanos(-(2**63))


class ToNanosUnitConversionTest(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(int(to_nanos(1_700_000_000, "s")), 1_700_000_000_000_000_000)

    def test_milliseconds(self):
        self.assertEqual(int(to_nanos(1_700_000_000_000, "ms")), 1_700_000_000_000_000_000)

    def test_microseconds(self):
        self.assertEqual(int(to_nanos(1_700_000_000_000_000, "us")), 1_700_000_000_000_000_000)

    def test_nanoseconds_passthrough(self):
        self.assertEqual(int(to_nanos(1_700_000_000_000_000_000, "ns")), 1_700_000_000_000_000_000)

    def test_iso_utc_z(self):
        ns = to_nanos("2023-11-14T22:13:20Z", "iso")
        self.assertEqual(int(ns), 1_700_000_000_000_000_000)

    def test_iso_explicit_offset(self):
        ns = to_nanos("2023-11-14T22:13:20+00:00", "iso")
        self.assertEqual(int(ns), 1_700_000_000_000_000_000)

    def test_iso_non_utc_offset_is_normalized(self):
        # 22:13:20+00:00 == 07:13:20+09:00 the same instant (JST, e.g. bitFlyer local reports)
        ns = to_nanos("2023-11-15T07:13:20+09:00", "iso")
        self.assertEqual(int(ns), 1_700_000_000_000_000_000)

    def test_iso_without_tzinfo_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos("2023-11-14T22:13:20", "iso")

    def test_iso_unparseable_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos("not-a-timestamp", "iso")

    def test_iso_wrong_type_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos(1234, "iso")

    def test_unknown_unit_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos(1_700_000_000, "minutes")

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos("1700000000", "s")

    def test_bool_value_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos(True, "s")


class UnitMismatchDetectionTest(unittest.TestCase):
    """The core failure mode V1 exists to catch: a value scaled for one unit
    but labelled with another."""

    def test_nanoseconds_value_mislabelled_as_seconds_is_rejected(self):
        # An ns-scale epoch value (~1.7e18) labelled "s" would convert to
        # seconds*1e9 -- a date far past year 2100 -- and is caught by the
        # plausibility window.
        with self.assertRaises(TimestampUnitError):
            to_nanos(1_700_000_000_000_000_000, "s")

    def test_milliseconds_value_mislabelled_as_seconds_is_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos(1_700_000_000_000, "s")

    def test_microseconds_value_mislabelled_as_milliseconds_is_rejected(self):
        with self.assertRaises(TimestampUnitError):
            to_nanos(1_700_000_000_000_000, "ms")


if __name__ == "__main__":
    unittest.main()
