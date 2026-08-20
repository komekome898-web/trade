"""Storm radar — the one validated storm precursor, as a runtime gate.

Research provenance (scripts/research_storm_b.py, pre-registered phase B):

    Of the seven pre-registered precursor hypotheses G1..G7, exactly one
    cleared the adoption rule (lift >= 2.0 at 2h or 6h, recall >= 0.10,
    >= 30 storm events in the mask) on the FRESH primary segment
    (2026-01-24 .. 2026-05-22, never touched by any prior study):

        G3  "clock 12:30-15:00 UTC"   lift = 2.23   (234 storm events)

    i.e. a storm event (first minute of |30m log-return| >= 0.8% after a
    >= 2h clean stretch) is ~2.23x more likely to begin within the horizon
    during 12:30-15:00 UTC than during a random admissible minute. The
    month-by-month breakdown in section 7b of that script shows the lift is
    monthly-stable, not one cluster of storm days.

    Everything else failed: DVOL complacency/rise (G1/G2) and stealth-size
    (G7) missed the lift or recall bar, and the OKX OI / long-short features
    (G4/G5/G6) could not qualify at all because the rubik endpoints only
    return a fixed ~30-day window and do not exist on the fresh segment.

So the radar is deliberately just a clock window. It is armed inside the
window and idle outside it; consumers decide what "armed" means for them
(the scalper lowers its entry threshold — see scripts/run_scalp_paper.py).

Dependency-free on purpose: stdlib only, no I/O, no clock reads except the
default "now" in :meth:`state`, so it stays trivially testable.
"""
from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_START = "12:30"
DEFAULT_END = "15:00"

#: research reference, surfaced in state() and in logs/UI
RESEARCH_LIFT = 2.23
RESEARCH_EVENTS = 234
RESEARCH_SOURCE = "scripts/research_storm_b.py G3"


def _parse_hhmm(value: str) -> int:
    """"HH:MM" -> minutes since UTC midnight (0..1439)."""
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"expected HH:MM, got {value!r}")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ValueError(f"expected HH:MM, got {value!r}") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"out-of-range HH:MM: {value!r}")
    return hour * 60 + minute


def _minute_of_day(ts: float | int | datetime | None) -> int:
    """Minutes since UTC midnight for a unix timestamp, datetime, or now."""
    if ts is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(ts, datetime):
        # a naive datetime is read as UTC (the whole module is UTC-only)
        dt = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
    else:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    return dt.hour * 60 + dt.minute


class StormRadar:
    """Armed during a UTC clock window; idle outside it.

    The window is half-open [start, end): the start minute is inside, the
    end minute is not — matching the ``(mod >= 12*60+30) & (mod < 15*60)``
    mask the research used. A window whose end is before its start wraps
    around midnight (e.g. "23:00"-"01:00" is armed at 23:30 and at 00:30).
    """

    def __init__(self, start: str = DEFAULT_START, end: str = DEFAULT_END):
        self.start = str(start).strip()
        self.end = str(end).strip()
        self._start_min = _parse_hhmm(self.start)
        self._end_min = _parse_hhmm(self.end)
        self.wraps = self._end_min < self._start_min

    # ------------------------------------------------------------------
    @property
    def window(self) -> str:
        """Human/log form of the window, e.g. "12:30-15:00 UTC"."""
        return f"{self.start}-{self.end} UTC"

    def is_armed(self, ts: float | int | datetime | None = None) -> bool:
        """True if ``ts`` (unix seconds, datetime, or now) is in the window."""
        if self._start_min == self._end_min:
            return False  # empty window: never armed
        minute = _minute_of_day(ts)
        if self.wraps:
            return minute >= self._start_min or minute < self._end_min
        return self._start_min <= minute < self._end_min

    def state(self, ts: float | int | datetime | None = None) -> dict:
        """Loggable/UI snapshot: {armed, window, reason}."""
        armed = self.is_armed(ts)
        if armed:
            reason = (f"storm window {self.window} "
                      f"(lift {RESEARCH_LIFT:.2f}, {RESEARCH_EVENTS} events, "
                      f"{RESEARCH_SOURCE})")
        else:
            reason = f"outside storm window {self.window}"
        return {"armed": armed, "window": self.window, "reason": reason}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"StormRadar(start={self.start!r}, end={self.end!r})"
