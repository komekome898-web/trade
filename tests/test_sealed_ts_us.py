from datetime import datetime, timezone

from bot.research.sealed import TS_CANDIDATES, parse_ts


def test_parse_ts_epoch_micros():
    us = 1_756_000_000_123_456  # 2025-08-24T02:26:40.123456Z
    dt = parse_ts(us)
    assert dt == datetime(2025, 8, 24, 2, 26, 40, 123456, tzinfo=timezone.utc)
    assert parse_ts(str(us)) == dt


def test_parse_ts_epoch_millis_and_seconds_unchanged():
    assert parse_ts(1_756_000_000_123) == datetime(2025, 8, 24, 2, 26, 40, 123000, tzinfo=timezone.utc)
    assert parse_ts(1_756_000_000) == datetime(2025, 8, 24, 2, 26, 40, tzinfo=timezone.utc)


def test_ts_us_is_a_candidate_column():
    assert "ts_us" in TS_CANDIDATES
