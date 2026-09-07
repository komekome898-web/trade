"""`parse_ts` must accept microsecond epochs (Binance aggTrades `ts_us`, WS tape).

Expected values are built from a reference datetime and converted to epochs, so
the test never depends on hand-computed epoch arithmetic.
"""
from datetime import datetime, timezone

from bot.research.sealed import TS_CANDIDATES, parse_ts

REF = datetime(2025, 8, 24, 1, 46, 40, tzinfo=timezone.utc)
EPOCH_S = int(REF.timestamp())


def test_parse_ts_epoch_micros():
    us = EPOCH_S * 1_000_000 + 123_456
    expected = REF.replace(microsecond=123_456)
    assert parse_ts(us) == expected
    assert parse_ts(str(us)) == expected


def test_parse_ts_epoch_millis_and_seconds_unchanged():
    assert parse_ts(EPOCH_S * 1_000 + 123) == REF.replace(microsecond=123_000)
    assert parse_ts(EPOCH_S) == REF


def test_ts_us_is_a_candidate_column():
    assert "ts_us" in TS_CANDIDATES
