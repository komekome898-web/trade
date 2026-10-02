"""C3 (reference series and available_at) and T2 (no reading the future).

T2 (spec): a reference series declared with a lag of 3 days, a card that reads
the newest value at t -> the values returned at t are only rows whose time is
<= t - 3 days; reading a row before it is available raises; peeking at the
next bar raises."""
from __future__ import annotations

import gzip
import json
import os

import numpy as np
import pytest

from bot.bt.core import FuturePositionError, LookAheadError, StaleContextError
from bot.bt.data.allowlist import AllowList
from bot.bt.data.errors import ParseError, PathRefused, SealedRangeError, SpecError
from bot.bt.data import reference as R
from bot.bt.data.reference import ReferenceSeries, load_reference, reference_series, reference_value
from bot.research.cards import CardError, RefLookAheadError, SeriesSpec, run_card

from w1_synth import DAY, M, NS, T0, bars_from_moves

HOUR = 3600 * NS
LAG3 = 3 * DAY
SRC = "試験の入力"


def decl(lag, name="X"):
    return {name: {"lag_ns": lag, "source": SRC}}


DECL3 = decl(LAG3)
T2 = dict(venue="synthetic", symbol="T2")


def _bars(days: int):
    return bars_from_moves(np.full(days * 1440, 1e-5))


def _hourly(name="X", lag=LAG3, days=10):
    rows = [(T0 + k * HOUR, float(k)) for k in range(days * 24)]
    return reference_series(name, rows, declarations=decl(lag, name))


class ReadLatest:
    name = "read_latest"

    def __init__(self, lag=LAG3):
        self.requires = [SeriesSpec("X", lag)]
        self.seen = []

    def exposure(self, view):
        self.seen.append((view.now_ns, view.ref_latest("X")))
        return 0.0


def check_t2_latest(seen, series: ReferenceSeries) -> list:
    """The value read at t must be the newest row with time <= t - lag (computed here from the rows alone)."""
    times = np.array(series.times_ns)
    bad = []
    for t, got in seen:
        k = int(np.searchsorted(times, t - series.lag_ns, side="right")) - 1
        want = None if k < 0 else (int(times[k]), series.values[k])
        if got != want:
            bad.append((t, got, want))
        if got is not None and got[0] > t - series.lag_ns:
            bad.append(("after t - lag", t, got))
    return bad


# -- C3: the data layer ------------------------------------------------------------------------------------

def test_undeclared_series_is_refused():
    with pytest.raises(SpecError, match="no declaration"):
        reference_series("X", [(T0, 1.0)], declarations=decl(0, "Y"))


@pytest.mark.parametrize("d", [{"lag_ns": 0}, {"lag_ns": 0, "source": " "}, {"available_at": "per_row"},
                               {"lag_ns": 0, "available_at": "per_row", "source": SRC}, {"lag": 0, "source": SRC},
                               0])
def test_a_declaration_needs_its_form_and_its_source(d):
    with pytest.raises(SpecError):
        reference_series("X", [(T0, 1.0)], declarations={"X": d})


def test_events_carry_available_at():
    s = reference_series("X", [(T0, 1.5), (T0 + HOUR, -0.25)], declarations=DECL3)
    ev = list(s.events())
    assert [(e.exchange_time_ns, e.received_time_ns) for e in ev] == [(T0, T0 + LAG3), (T0 + HOUR, T0 + HOUR + LAG3)]
    assert [reference_value(e) for e in ev] == [1.5, -0.25]


@pytest.mark.parametrize("rows, match", [
    ([(T0, 1.0), (T0, 2.0)], "strictly increasing"),
    ([(T0 + 1, 1.0), (T0, 2.0)], "strictly increasing"),
    ([(T0, float("nan"))], "not a finite"),
    ([(T0, True)], "must be a number"),
    ([(float(T0), 1.0)], "time must be int"),
    ([(T0, 1.0, T0 + 5)], "a row is"),
])
def test_bad_rows_are_refused(rows, match):
    with pytest.raises(ParseError, match=match):
        reference_series("X", rows, declarations=decl(0))


@pytest.mark.parametrize("lag", [-1, 1.0, True])
def test_bad_lag_is_refused(lag):
    with pytest.raises(SpecError):
        reference_series("X", [(T0, 1.0)], declarations=decl(lag))


def test_a_series_checks_itself_when_it_is_made():
    """Fix 1: a ReferenceSeries made by hand, not through `declared`, is checked by __post_init__."""
    d = R.ReferenceDecl("X", LAG3, SRC)
    ok = R.ReferenceSeries("X", d, (T0, T0 + HOUR), (1.0, 2.0), (T0 + LAG3, T0 + HOUR + LAG3))
    assert ok.available_at(1) == T0 + HOUR + LAG3
    bad = [
        dict(available_ns=(T0, T0 + HOUR)),  # rows available at once, under a 3-day declaration
        dict(times_ns=(T0 + HOUR, T0)),  # time going back
        dict(values=(1.0, float("nan"))),
        dict(values=(1, 2.0)),  # not floats
        dict(times_ns=[T0, T0 + HOUR]),  # not a tuple
        dict(decl=R.ReferenceDecl("Y", LAG3, SRC)),  # someone else's declaration
    ]
    base = dict(name="X", decl=d, times_ns=(T0, T0 + HOUR), values=(1.0, 2.0),
                available_ns=(T0 + LAG3, T0 + HOUR + LAG3))
    for change in bad:
        with pytest.raises((ParseError, SpecError)):
            R.ReferenceSeries(**dict(base, **change))
    per_row = R.ReferenceDecl("X", None, SRC)
    with pytest.raises(ParseError, match="before the row's time"):
        R.ReferenceSeries("X", per_row, (T0,), (1.0,), (T0 - 1,))
    with pytest.raises(ParseError, match="published earlier"):
        R.ReferenceSeries("X", per_row, (T0, T0 + HOUR), (1.0, 2.0), (T0 + 2 * DAY, T0 + DAY))


def _ds(paths, rng=None, available=None):
    d = {"name": "X", "paths": paths,
         "spec": {"format": "csv", "header": True, "delimiter": ",", "time": {"columns": ["ts"], "unit": "s"},
                  "value": "v"}}
    if available is not None:
        d["spec"]["available"] = available
    if rng is not None:
        d["range_ns"] = rng
    return d


def _write(root, rel, text, gz=False):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data = text.encode()
    with open(p, "wb") as fh:
        fh.write(gzip.compress(data) if gz else data)
    return rel


def test_load_reference_from_a_file(tmp_path):
    root = str(tmp_path)
    t0 = T0 // NS
    rel = _write(root, "backtest_data/ref/x.csv", f"ts,v\n{t0},1.5\n{t0 + 3600},2\n")
    s = load_reference(root, _ds([rel]), declarations=DECL3)
    assert s.times_ns == (T0, T0 + HOUR) and s.values == (1.5, 2.0) and s.lag_ns == LAG3
    assert s.manifest[0][0] == rel and s.manifest[0][2:] == (2, 2)
    with pytest.raises(SpecError, match="no declaration"):
        load_reference(root, _ds([rel]), declarations={})
    with pytest.raises(SpecError, match="spec.available is refused"):
        load_reference(root, _ds([rel], available="a"), declarations=DECL3)


def test_load_reference_with_per_row_available_at(tmp_path):
    root = str(tmp_path)
    t0 = T0 // NS
    rel = _write(root, "backtest_data/ref/x.csv", f"ts,v,a\n{t0},1.5,{t0 + 7200}\n{t0 + 3600},2,{t0 + 9000}\n")
    per_row = {"X": {"available_at": "per_row", "source": SRC}}
    s = load_reference(root, _ds([rel], available="a"), declarations=per_row)
    assert s.available_ns == (T0 + 2 * HOUR, T0 + 9000 * NS) and s.lag_ns is None
    with pytest.raises(SpecError, match="must name the column"):
        load_reference(root, _ds([rel]), declarations=per_row)


def test_load_reference_goes_through_the_allow_list(tmp_path):
    root = str(tmp_path)
    rel = _write(root, "backtest_data/qa_x/x.csv", "ts,v\n1704067200,1\n")
    with pytest.raises(PathRefused):
        load_reference(root, _ds([rel]), declarations=decl(0))
    rel2 = _write(root, "elsewhere/x.csv", "ts,v\n1704067200,1\n")
    with pytest.raises(PathRefused):
        load_reference(root, _ds([rel2]), declarations=decl(0), allowlist=AllowList())


def test_load_reference_respects_the_seals(tmp_path):
    root = str(tmp_path)
    t0 = T0 // NS
    rel = _write(root, "backtest_data/ref/x.csv", f"ts,v\n{t0},1\n{t0 + 86400},2\n")
    led = os.path.join(root, "backtest_data", "phase2_sealed", "PX")
    os.makedirs(led)
    with open(os.path.join(led, "SEALED.json"), "w") as fh:
        json.dump({"unit": "PX", "forward_start": "2030-01-01T00:00:00+00:00",
                   "files": [{"path": rel, "time_column": "ts", "seal_from_ts": "2024-01-02T00:00:00+00:00"}]}, fh)
    with pytest.raises(SealedRangeError):  # no range: refused unopened
        load_reference(root, _ds([rel]), declarations=decl(0))
    with pytest.raises(SealedRangeError):  # a range reaching past the cutoff
        load_reference(root, _ds([rel], [T0, T0 + 2 * DAY]), declarations=decl(0))
    s = load_reference(root, _ds([rel], [T0, T0 + DAY]), declarations=decl(0))
    assert s.times_ns == (T0,)


# -- T2 ----------------------------------------------------------------------------------------------------

def test_t2_values_read_at_t_are_rows_at_or_before_t_minus_3_days():
    s = _hourly()
    card = ReadLatest()
    run_card(card, _bars(10), references={"X": s}, declarations=DECL3, **T2)
    assert len(card.seen) == 10 * 1440 - 0
    assert check_t2_latest(card.seen, s) == []
    first_visible = next(t for t, got in card.seen if got is not None)
    assert first_visible == T0 + LAG3  # the first row (time T0) becomes readable exactly at T0 + 3 days
    assert all(got is None for t, got in card.seen if t < T0 + LAG3)


def test_t2_broken_version_without_the_lag_is_caught(monkeypatch):
    """The check above fails when the data layer forgets the lag (events received at the row time)."""
    from bot.bt.core import ClockEvent

    def no_lag(self):
        for t, v in zip(self.times_ns, self.values):
            yield ClockEvent(received_time_ns=t, exchange_time_ns=t, tag=float.__repr__(v))

    monkeypatch.setattr(R.ReferenceSeries, "events", no_lag)
    s = _hourly()
    card = ReadLatest()
    run_card(card, _bars(10), references={"X": s}, declarations=DECL3, **T2)
    assert check_t2_latest(card.seen, s) != []


class ReadAt:
    name = "read_at"

    def __init__(self, back_ns):
        self.requires = [SeriesSpec("X", LAG3)]
        self.back_ns = back_ns

    def exposure(self, view):
        if view.now_ns >= T0 + 5 * DAY:
            row_t = (view.now_ns - self.back_ns) // HOUR * HOUR
            view.ref_at("X", row_t)
        return 0.0


def test_t2_reading_a_row_before_it_is_available_raises():
    with pytest.raises(RefLookAheadError):  # a row 1 day old is available only after 3 days
        run_card(ReadAt(DAY), _bars(6), references={"X": _hourly()}, declarations=DECL3, **T2)
    run_card(ReadAt(LAG3), _bars(6), references={"X": _hourly()}, declarations=DECL3, **T2)  # 3 days: allowed


class PastTheNewestRow:
    name = "ref_index"
    requires = [SeriesSpec("X", LAG3)]

    def exposure(self, view):
        rows = view.ref("X")
        if view.now_ns >= T0 + 4 * DAY:
            rows[len(rows)]
        return 0.0


def test_t2_indexing_after_the_newest_row_raises():
    with pytest.raises(RefLookAheadError):
        run_card(PastTheNewestRow(), _bars(5), references={"X": _hourly()}, declarations=DECL3, **T2)
    assert issubclass(RefLookAheadError, LookAheadError)


class PeekNextBar:
    name = "peek"
    requires = ()

    def exposure(self, view):
        b = view.bars(1)
        b[1]  # the bar after the newest: not delivered yet
        return 0.0


def test_t2_peeking_at_the_next_bar_raises():
    with pytest.raises(FuturePositionError) as ei:
        run_card(PeekNextBar(), _bars(1), declarations={}, **T2)
    assert isinstance(ei.value, LookAheadError)


class KeepsTheView:
    name = "keeps"
    requires = [SeriesSpec("X", LAG3)]

    def __init__(self):
        self.kept = None

    def exposure(self, view):
        if self.kept is not None:
            self.kept.ref_latest("X")
        self.kept = view
        return 0.0


def test_a_view_kept_after_its_call_is_dead():
    with pytest.raises(StaleContextError):
        run_card(KeepsTheView(), _bars(1), references={"X": _hourly()}, declarations=DECL3, **T2)


class ReadsUndeclared:
    name = "undeclared"
    requires = ()

    def exposure(self, view):
        view.ref_latest("X")
        return 0.0


def test_a_series_not_in_requires_is_refused():
    with pytest.raises(CardError, match="not in the card's requires"):
        run_card(ReadsUndeclared(), _bars(1), references={"X": _hourly()}, declarations=DECL3, **T2)


def test_a_lag_the_card_states_differently_is_refused():
    with pytest.raises(CardError, match="states lag"):
        run_card(ReadLatest(lag=0), _bars(1), references={"X": _hourly()}, declarations=DECL3, **T2)
    with pytest.raises(CardError, match="was not given"):
        run_card(ReadLatest(), _bars(1), declarations={}, **T2)


def test_a_lag_zero_row_stamped_at_a_bar_close_is_seen_at_that_bar():
    """The merge order puts a CLOCK after a BAR of the same instant; the card is called from a timer after
    every delivery of the instant, so the row available at t is seen at t (and not at the bar before)."""
    rows = [(T0 + k * M, float(k)) for k in range(1, 60)]  # a row at every bar close
    s = reference_series("X", rows, declarations=decl(0))
    card = ReadLatest(lag=0)
    run_card(card, _bars(1)[:60], references={"X": s}, declarations=decl(0), **T2)
    assert card.seen[0] == (T0 + M, (T0 + M, 1.0))
    assert all(got == (t, float((t - T0) // M)) for t, got in card.seen[:59])
