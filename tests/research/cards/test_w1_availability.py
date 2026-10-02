"""The critic's fixes 1 and 2 (2026-10-02).

1. Every reference series a run receives -- also one used only as a scene --
   is compared with the run's declarations: a series built with lag 0 where
   the declaration says 3 days is refused. The broken version without that
   comparison runs, and its scene reads rows before they were published.
2. A series published at a fixed local time (Friday 15:30 New York time for
   Tuesday's value) cannot be declared as one constant lag across a daylight-
   saving change: the constant taken from a summer week reads the first
   winter week's row an hour before it is published. Per-row available_at
   reads nothing early."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from bot.bt.data.reference import reference_series
from bot.research.cards import CardError, SeriesSpec, run_card
from bot.research.cards import run as run_module

from w1_synth import DAY, M, NS, T0, bars_from_moves

HOUR = 3600 * NS
SRC = "試験の入力"
LAG3 = 3 * DAY
RUN = dict(venue="synthetic", symbol="avail")


class Nothing:
    name = "nothing"
    requires = ()

    def exposure(self, view):
        return 0.0


def _hourly(lag):
    rows = [(T0 + k * HOUR, float(k)) for k in range(10 * 24)]
    return reference_series("X", rows, declarations={"X": {"lag_ns": lag, "source": SRC}})


def test_a_scene_series_with_another_lag_is_refused():
    bars = bars_from_moves(np.full(6 * 1440, 1e-5))
    with pytest.raises(CardError, match="was made with"):
        run_card(Nothing(), bars, references={"X": _hourly(0)},
                 declarations={"X": {"lag_ns": LAG3, "source": SRC}}, **RUN)
    with pytest.raises(CardError, match="no declaration"):
        run_card(Nothing(), bars, references={"X": _hourly(LAG3)}, declarations={}, **RUN)


def test_broken_version_without_the_comparison_reads_the_future(monkeypatch):
    monkeypatch.setattr(run_module, "check_declared", lambda refs, declarations: None)
    bars = bars_from_moves(np.full(6 * 1440, 1e-5))
    run = run_card(Nothing(), bars, references={"X": _hourly(0)},
                   declarations={"X": {"lag_ns": LAG3, "source": SRC}}, **RUN)
    seen = run.ref_time["X"]
    early = (seen >= 0) & (seen + LAG3 > run.end_ns)  # a row recorded at t although it is published at time + 3 days
    assert early.sum() > 0


NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc


def _ns(d: dt.datetime) -> int:
    return int(d.timestamp()) * NS


def _weekly():
    """Tuesday's value (row time Tuesday 00:00 UTC), published Friday 15:30 New York time."""
    out = []
    for tue in (dt.date(2024, 10, 22), dt.date(2024, 10, 29), dt.date(2024, 11, 5)):
        fri = tue + dt.timedelta(days=3)
        pub = dt.datetime(fri.year, fri.month, fri.day, 15, 30, tzinfo=NY)
        out.append((_ns(dt.datetime(tue.year, tue.month, tue.day, tzinfo=UTC)), _ns(pub)))
    return out


class ReadLatest:
    def __init__(self, lag):
        self.name, self.requires, self.seen = "latest", [SeriesSpec("C", lag)], []

    def exposure(self, view):
        self.seen.append((view.now_ns, view.ref_latest("C")))
        return 0.0


def _early_reads(card, published: dict) -> list:
    return [(t, got) for t, got in card.seen if got is not None and published[got[0]] > t]


def test_daylight_saving_constant_lag_reads_early_per_row_does_not():
    weekly = _weekly()
    published = dict(weekly)
    # the summer week: Tuesday 2024-10-29 -> Friday 2024-11-01 15:30 EDT = 19:30 UTC
    lag_summer = weekly[1][1] - weekly[1][0]
    assert lag_summer == 3 * DAY + 19 * HOUR + 30 * 60 * NS
    # the winter week: Tuesday 2024-11-05 -> Friday 2024-11-08 15:30 EST = 20:30 UTC (one hour later)
    assert weekly[2][1] - weekly[2][0] == lag_summer + HOUR
    start = _ns(dt.datetime(2024, 10, 28, tzinfo=UTC))
    bars = bars_from_moves(np.full(13 * 1440, 1e-5), start=start)
    rows = [(t, float(k)) for k, (t, _p) in enumerate(weekly)]

    const = {"C": {"lag_ns": lag_summer, "source": "金曜 15:30 ET を 2024-11-01(夏時間)で換算した一定の遅れ(試験)"}}
    s_const = reference_series("C", rows, declarations=const)
    card = ReadLatest(lag_summer)
    run_card(card, bars, references={"C": s_const}, declarations=const, **RUN)
    early = _early_reads(card, published)
    assert len(early) == 60  # 19:30..20:29 UTC on 2024-11-08: the winter row read before it is published
    assert all(got[0] == weekly[2][0] for _t, got in early)

    per_row = {"C": {"available_at": "per_row", "source": "金曜 15:30 America/New_York(行ごとに換算、試験)"}}
    s_row = reference_series("C", [(t, float(k), p) for k, (t, p) in enumerate(weekly)], declarations=per_row)
    card2 = ReadLatest(None)
    run_card(card2, bars, references={"C": s_row}, declarations=per_row, **RUN)
    assert _early_reads(card2, published) == []
    first = next(t for t, got in card2.seen if got is not None and got[0] == weekly[2][0])
    assert first == weekly[2][1]  # seen from the bar that closes at the publication, not before
    assert first - start == (first - start) // M * M
