from decimal import Decimal

import numpy as np
import pytest

from bot.bt.core import TIME_CONTRACT, TimestampUnitError, nanos_to_iso, to_nanos, validate_nanos


def test_iso_with_nanoseconds_is_exact():
    # 2024-01-01T00:00:00Z = 19723 days * 86400 s = 1_704_067_200 s (closed form).
    assert to_nanos("2024-01-01T00:00:00.123456789Z", "iso") == 1_704_067_200_123_456_789


def test_iso_offsets_and_padding():
    assert to_nanos("2024-01-01T09:00:00+09:00", "iso") == 1_704_067_200 * 10**9
    assert to_nanos("2024-01-01T00:00:00.5Z", "iso") == 1_704_067_200_500_000_000
    assert to_nanos("2024-01-01 00:00:00.000000001+0000", "iso") == 1_704_067_200_000_000_001
    assert to_nanos("2024-01-01T00:00:00.1234567890Z", "iso") == 1_704_067_200_123_456_789


@pytest.mark.parametrize(
    "bad",
    ["2024-01-01T00:00:00", "2024-01-01T00:00:00.1234567891Z", "2024-13-01T00:00:00Z", "yesterday", 5],
)
def test_iso_rejects(bad):
    with pytest.raises(TimestampUnitError):
        to_nanos(bad, "iso")


def test_units_scale_exactly():
    assert to_nanos(1_700_000_000, "s") == 1_700_000_000 * 10**9
    assert to_nanos(1_700_000_000_123, "ms") == 1_700_000_000_123_000_000
    assert to_nanos(1_700_000_000_123_456, "us") == 1_700_000_000_123_456_000
    assert to_nanos(1_700_000_000_123_456_789, "ns") == 1_700_000_000_123_456_789


def test_float_and_string_seconds_do_not_pick_up_binary_rounding():
    # Rewritten in round 16 (i0-r15-01): a float is read by the value it holds,
    # never by its shortest repr. float 1700000000.123456 holds
    # 1700000000.1234560012817...: sub-nanosecond digits -> refused (it was
    # taken as ...123456000 by reading the repr). A string or a Decimal gives
    # the written value; a float whose value is a whole number of ns is taken.
    with pytest.raises(TimestampUnitError):
        to_nanos(1700000000.123456, "s")
    assert to_nanos(1700000000.5, "s") == 1_700_000_000_500_000_000
    assert to_nanos("1700000000.123456", "s") == 1_700_000_000_123_456_000
    assert to_nanos("1700000000.123456789", "s") == 1_700_000_000_123_456_789
    assert to_nanos(Decimal("1700000000.000000001"), "s") == 1_700_000_000_000_000_001


def test_sub_nanosecond_input_is_refused_not_rounded():
    with pytest.raises(TimestampUnitError):
        to_nanos("1700000000.1234567891", "s")
    with pytest.raises(TimestampUnitError):
        to_nanos(1.5, "ns")


@pytest.mark.parametrize("value,unit", [(1_700_000_000_000, "s"), (1_700_000_000_000_000, "ms"), (1_700_000_000_000_000_000, "us")])
def test_value_too_large_for_its_label_is_rejected_by_default(value, unit):
    with pytest.raises(TimestampUnitError):
        to_nanos(value, unit)


def test_value_too_small_for_its_label_needs_an_era_window():
    # Seconds labelled ns land at 1970-01-01T00:00:01.7Z: inside the default
    # 1970..2100 window, so the default cannot catch this direction.
    assert to_nanos(1_700_000_000, "ns") == 1_700_000_000
    era = (to_nanos("2015-01-01T00:00:00Z", "iso"), to_nanos("2030-01-01T00:00:00Z", "iso"))
    with pytest.raises(TimestampUnitError):
        to_nanos(1_700_000_000, "ns", plausible=era)
    with pytest.raises(TimestampUnitError):
        to_nanos(1_700_000_000, "ms", plausible=era)
    assert to_nanos(1_700_000_000, "s", plausible=era) == 1_700_000_000 * 10**9


def test_rejects_bool_unknown_unit_and_nonfinite():
    with pytest.raises(TimestampUnitError):
        to_nanos(True, "s")
    with pytest.raises(TimestampUnitError):
        to_nanos(1, "minutes")
    with pytest.raises(TimestampUnitError):
        to_nanos(float("nan"), "s")
    with pytest.raises(TimestampUnitError):
        to_nanos(None, "s")  # type: ignore[arg-type]


def test_validate_nanos_accepts_numpy_int64_and_rejects_float():
    v = validate_nanos(np.int64(1_700_000_000_000_000_000))
    assert type(v) is int and v == 1_700_000_000_000_000_000
    with pytest.raises(TimestampUnitError):
        validate_nanos(1.7e18)
    with pytest.raises(TimestampUnitError):
        validate_nanos(2**63)
    with pytest.raises(TimestampUnitError):
        validate_nanos(False)


def test_iso_roundtrip():
    for ns in (0, 1, 1_704_067_200_123_456_789, 4_102_444_799_999_999_999):
        assert to_nanos(nanos_to_iso(ns), "iso") == ns


def test_time_contract_declares_int64_ns_utc():
    assert TIME_CONTRACT["type"] == "int"
    assert TIME_CONTRACT["bits"] == 64
    assert TIME_CONTRACT["unit"] == "ns"
    assert TIME_CONTRACT["timezone"] == "UTC"


def test_iso_offset_out_of_range_is_refused_not_shifted():
    import pytest as _pytest

    from bot.bt.core import TimestampUnitError, to_nanos

    for bad in ("2024-01-01T00:00:00+09:75", "2024-01-01T00:00:00+24:00", "2024-01-01T00:00:00-0960"):
        with _pytest.raises(TimestampUnitError):
            to_nanos(bad, "iso")
    assert to_nanos("2024-01-01T09:00:00+0900", "iso") == 1_704_067_200_000_000_000
    assert to_nanos("2023-12-31T18:30:00.000000001-05:30", "iso") == 1_704_067_200_000_000_001
