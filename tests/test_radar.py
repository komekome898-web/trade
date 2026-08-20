"""Storm radar clock window (src/bot/radar.py).

The window is the one adopted precursor from scripts/research_storm_b.py
(G3, 12:30-15:00 UTC, lift 2.23). These tests pin the boundary semantics
(half-open [start, end)), the cross-midnight case and both input types.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bot.radar import StormRadar


def ts(hour: int, minute: int, day: int = 20) -> float:
    """Unix seconds for 2026-08-{day} {hour}:{minute} UTC."""
    return datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc).timestamp()


def dt(hour: int, minute: int, day: int = 20) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc)


# --------------------------------------------------------------------- #
# default window
# --------------------------------------------------------------------- #
def test_default_window_is_the_researched_one():
    r = StormRadar()
    assert r.start == "12:30"
    assert r.end == "15:00"
    assert r.window == "12:30-15:00 UTC"


@pytest.mark.parametrize("hour,minute", [(12, 30), (12, 31), (13, 0), (14, 59)])
def test_inside_window_is_armed(hour, minute):
    assert StormRadar().is_armed(ts(hour, minute)) is True


@pytest.mark.parametrize("hour,minute", [(0, 0), (12, 29), (15, 0), (15, 1), (23, 59)])
def test_outside_window_is_not_armed(hour, minute):
    assert StormRadar().is_armed(ts(hour, minute)) is False


def test_boundary_minutes_are_half_open():
    """Start minute inside, end minute outside — same as the research mask
    (mod >= 12*60+30) & (mod < 15*60)."""
    r = StormRadar()
    assert r.is_armed(ts(12, 29)) is False
    assert r.is_armed(ts(12, 30)) is True
    assert r.is_armed(ts(14, 59)) is True
    assert r.is_armed(ts(15, 0)) is False


def test_seconds_within_the_end_minute_are_still_outside():
    r = StormRadar()
    assert r.is_armed(ts(15, 0) + 59) is False
    assert r.is_armed(ts(12, 30) - 1) is False


# --------------------------------------------------------------------- #
# input types
# --------------------------------------------------------------------- #
def test_datetime_and_unix_ts_agree():
    r = StormRadar()
    for hour, minute in [(11, 0), (12, 30), (13, 45), (15, 0), (22, 10)]:
        assert r.is_armed(dt(hour, minute)) == r.is_armed(ts(hour, minute))


def test_naive_datetime_is_read_as_utc():
    r = StormRadar()
    assert r.is_armed(datetime(2026, 8, 20, 13, 0)) is True
    assert r.is_armed(datetime(2026, 8, 20, 16, 0)) is False


def test_non_utc_datetime_is_converted():
    r = StormRadar()
    jst = timezone(timedelta(hours=9))
    # 22:00 JST == 13:00 UTC -> armed
    assert r.is_armed(datetime(2026, 8, 20, 22, 0, tzinfo=jst)) is True
    # 13:00 JST == 04:00 UTC -> idle
    assert r.is_armed(datetime(2026, 8, 20, 13, 0, tzinfo=jst)) is False


def test_int_timestamp_accepted():
    assert StormRadar().is_armed(int(ts(13, 0))) is True


def test_ts_none_uses_now():
    """Omitting ts reads the UTC clock: a window built around the current
    minute is armed, the complementary one is not."""
    now = datetime.now(timezone.utc)
    # 1h wide so a minute rollover between the two clock reads cannot flip it
    lo = (now - timedelta(minutes=30)).strftime("%H:%M")
    hi = (now + timedelta(minutes=30)).strftime("%H:%M")
    assert StormRadar(start=lo, end=hi).is_armed() is True
    assert StormRadar(start=hi, end=lo).is_armed() is False
    assert StormRadar(start=lo, end=hi).state()["armed"] is True


# --------------------------------------------------------------------- #
# parameterisation
# --------------------------------------------------------------------- #
def test_custom_window():
    r = StormRadar(start="09:00", end="10:15")
    assert r.is_armed(ts(9, 0)) is True
    assert r.is_armed(ts(10, 14)) is True
    assert r.is_armed(ts(10, 15)) is False
    assert r.is_armed(ts(8, 59)) is False


def test_cross_midnight_window():
    r = StormRadar(start="23:00", end="01:00")
    assert r.wraps is True
    assert r.is_armed(ts(23, 0)) is True
    assert r.is_armed(ts(23, 59)) is True
    assert r.is_armed(ts(0, 0)) is True
    assert r.is_armed(ts(0, 59)) is True
    assert r.is_armed(ts(1, 0)) is False
    assert r.is_armed(ts(12, 0)) is False
    assert r.is_armed(ts(22, 59)) is False


def test_empty_window_never_arms():
    r = StormRadar(start="12:00", end="12:00")
    assert r.is_armed(ts(12, 0)) is False
    assert r.is_armed(ts(0, 0)) is False


@pytest.mark.parametrize("bad", ["12", "12:60", "24:00", "abc", "12:xx", ""])
def test_bad_window_rejected(bad):
    with pytest.raises(ValueError):
        StormRadar(start=bad)


# --------------------------------------------------------------------- #
# state()
# --------------------------------------------------------------------- #
def test_state_armed():
    s = StormRadar().state(ts(13, 0))
    assert s["armed"] is True
    assert s["window"] == "12:30-15:00 UTC"
    assert "2.23" in s["reason"]
    assert set(s) == {"armed", "window", "reason"}


def test_state_idle():
    s = StormRadar().state(ts(3, 0))
    assert s["armed"] is False
    assert s["window"] == "12:30-15:00 UTC"
    assert "outside" in s["reason"]


def test_state_is_json_safe():
    import json
    json.dumps(StormRadar().state(ts(13, 0)))
