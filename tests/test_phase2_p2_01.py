"""Tests for the P2-01 phase-2 runner (scripts/phase2/p2_01_run.py).

Two things are checked here, both on SYNTHETIC data only (no repo data file
is opened, so nothing can brush against the sealed window):

  1. a synthetic tape with a KNOWN planted overnight drift -- the runner's
     core pair-builder must recover it in the main indicator, gross and net
     of the per-pair micro-contract cost;
  2. the roll-marking function must mark exactly the pairs touching
     {2nd Friday, previous trading day} on a synthetic calendar, and nothing
     else -- including the holiday case where the 2nd Friday is not a
     trading day at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from bot.research.overnight import sign_shuffle_null  # noqa: E402
from phase2 import p2_01_run as p2  # noqa: E402


# ---------------------------------------------------------------------------
# 1. planted-drift recovery
# ---------------------------------------------------------------------------

def _synthetic_tape(n_days: int, overnight_bps: float, intraday_bps: float,
                    start_close: float = 20000.0, seed: int = 7) -> pd.DataFrame:
    """A daily tape with an exactly planted overnight and intraday drift.

    Day t: open(t) = close(t-1) * (1 + overnight), close(t) = open(t) *
    (1 + intraday). Weekends are skipped so the calendar is realistic, but
    the planted drift is per PAIR (not per calendar night), which is exactly
    what the strategy holds. No noise on the planted legs: the recovery must
    be exact to floating point, so a sign or off-by-one error cannot hide
    inside sampling error.
    """
    del seed
    dates = pd.bdate_range("2010-01-04", periods=n_days)
    on = 1.0 + overnight_bps / 1e4
    intra = 1.0 + intraday_bps / 1e4
    opens, closes = [], []
    prev_close = start_close
    for i in range(n_days):
        o = prev_close if i == 0 else prev_close * on
        c = o * intra
        opens.append(o)
        closes.append(c)
        prev_close = c
    return pd.DataFrame({"date": dates, "open": opens, "close": closes})


def test_build_pairs_recovers_planted_overnight_drift_exactly():
    planted = 8.0  # bps per overnight pair
    tape = _synthetic_tape(400, overnight_bps=planted, intraday_bps=-3.0)
    pairs = p2.build_pairs(tape)

    # endpoint rule: the last day has no t+1 open, so it yields no pair
    assert len(pairs) == len(tape) - 1
    assert pairs["date"].iloc[0] == tape["date"].iloc[0]
    assert pairs["date_t1"].iloc[-1] == tape["date"].iloc[-1]

    # gross recovery, exact
    assert pairs["r_night_bps"].to_numpy() == pytest.approx(planted, abs=1e-8)
    assert float(pairs["r_night_bps"].mean()) == pytest.approx(planted, abs=1e-8)
    # the intraday leg is recovered too (control 1)
    assert pairs["r_day_bps"].to_numpy() == pytest.approx(-3.0, abs=1e-8)

    # net = gross - the pair's own cost on that pair's own notional
    expected_cost = 122.0 / (tape["close"].iloc[:-1].to_numpy() * 10.0) * 1e4
    assert pairs["cost_bps_cons"].to_numpy() == pytest.approx(expected_cost)
    assert pairs["cost_bps_opt"].to_numpy() == pytest.approx(expected_cost * 22.0 / 122.0)
    assert pairs["r_net_bps_cons"].to_numpy() == pytest.approx(
        planted - expected_cost)

    # and the yen P&L of 1 micro contract agrees with the bps view
    expected_pnl = ((tape["open"].shift(-1).iloc[:-1].to_numpy()
                     - tape["close"].iloc[:-1].to_numpy()) * 10.0 - 122.0)
    assert pairs["pnl_yen_cons"].to_numpy() == pytest.approx(expected_pnl)


def test_planted_drift_recovered_through_ci_and_sharpe():
    """A noisy tape: the planted drift must sit inside the block-bootstrap CI
    and the sign-shuffle null must not reach the observed mean."""
    planted = 25.0
    rng = np.random.default_rng(20260906)
    n = 1500
    dates = pd.bdate_range("2010-01-04", periods=n)
    noise = rng.normal(0.0, 40.0, size=n)  # bps of overnight noise
    opens, closes = [], []
    prev_close = 20000.0
    for i in range(n):
        o = prev_close if i == 0 else prev_close * (1 + (planted + noise[i]) / 1e4)
        c = o * (1 + rng.normal(0.0, 60.0) / 1e4)
        opens.append(o)
        closes.append(c)
        prev_close = c
    tape = pd.DataFrame({"date": dates, "open": opens, "close": closes})

    pairs = p2.build_pairs(tape)
    x = pairs["r_night_bps"].to_numpy()
    assert float(x.mean()) == pytest.approx(planted, abs=5.0)

    from bot.research.overnight import block_bootstrap_ci
    lo, hi = block_bootstrap_ci(x, block=20, n_boot=2000, seed=p2.SEED)
    assert lo < planted < hi
    assert lo > 0  # a 25bps planted drift on this noise level is detectable

    years = p2.years_span(pairs)
    assert 5.0 < years < 7.0  # 1500 business days ~= 5.8 calendar years
    sharpe = p2.sharpe_annualised(x, years)
    means, sharpes = p2.sign_shuffle_mean_and_sharpe(x, 1000, p2.SEED, years)
    assert float(x.mean()) > float(np.percentile(means, 95))
    assert sharpe > float(np.percentile(sharpes, 95))


def test_sign_shuffle_helper_matches_tested_overnight_helper():
    """The Sharpe-carrying wrapper must reproduce the tested helper's means
    bit-for-bit for the same (x, n, seed) -- otherwise the reported null is
    not the pre-registered one."""
    x = np.array([1.0, -2.0, 3.5, -0.5, 7.0, -4.25, 0.75, 2.0])
    mine, _ = p2.sign_shuffle_mean_and_sharpe(x, 200, 20260906, years=1.0)
    theirs = sign_shuffle_null(x, 200, 20260906)
    assert np.array_equal(mine, theirs)


def test_max_drawdown_yen():
    # +100, -300, +50, -400, +1000 -> equity 100,-200,-150,-550,450
    # peak before each point: 100 -> max drop = 100 - (-550) = 650 at index 3
    dd, idx = p2.max_drawdown_yen([100, -300, 50, -400, 1000])
    assert dd == pytest.approx(650.0)
    assert idx == 3
    # a monotonically rising curve has zero drawdown
    dd2, _ = p2.max_drawdown_yen([10, 10, 10])
    assert dd2 == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 2. roll marking
# ---------------------------------------------------------------------------

def test_second_friday():
    # 2010-01: Fridays are 1, 8, 15 -> 2nd Friday = 8th
    assert p2.second_friday(2010, 1) == pd.Timestamp("2010-01-08")
    # 2010-10: Fridays are 1, 8, 15 -> 8th
    assert p2.second_friday(2010, 10) == pd.Timestamp("2010-10-08")
    # a month starting ON a Friday and one starting the day after
    assert p2.second_friday(2021, 1) == pd.Timestamp("2021-01-08")
    assert p2.second_friday(2021, 5) == pd.Timestamp("2021-05-14")


def test_roll_marking_marks_exactly_the_sq_and_previous_trading_day():
    """Synthetic Mon-Fri calendar over three months, no holidays."""
    days = pd.bdate_range("2010-01-04", "2010-03-31")
    tape = pd.DataFrame({
        "date": days,
        "open": np.full(len(days), 20000.0),
        "close": np.full(len(days), 20000.0),
    })
    pairs = p2.build_pairs(tape)

    marked_days = p2.roll_marked_days(days, "monthly")
    # 2nd Fridays: 2010-01-08, 2010-02-12, 2010-03-12; previous trading day is
    # the Thursday before each
    assert marked_days == {
        pd.Timestamp("2010-01-07"), pd.Timestamp("2010-01-08"),
        pd.Timestamp("2010-02-11"), pd.Timestamp("2010-02-12"),
        pd.Timestamp("2010-03-11"), pd.Timestamp("2010-03-12"),
    }

    mask = p2.mark_roll_adjacent(pairs, days, "monthly")
    got = {(str(a.date()), str(b.date())) for a, b in
           zip(pd.to_datetime(pairs.loc[mask, "date"]),
               pd.to_datetime(pairs.loc[mask, "date_t1"]))}
    # each month contributes 3 pairs: (Wed,Thu) (Thu,Fri=SQ) (SQ,next)
    assert got == {
        ("2010-01-06", "2010-01-07"), ("2010-01-07", "2010-01-08"),
        ("2010-01-08", "2010-01-11"),
        ("2010-02-10", "2010-02-11"), ("2010-02-11", "2010-02-12"),
        ("2010-02-12", "2010-02-15"),
        ("2010-03-10", "2010-03-11"), ("2010-03-11", "2010-03-12"),
        ("2010-03-12", "2010-03-15"),
    }
    assert int(mask.sum()) == 9
    # no widening to +/-2 trading days
    assert not mask[pd.to_datetime(pairs["date"]) == pd.Timestamp("2010-01-05")].any()
    assert not mask[pd.to_datetime(pairs["date"]) == pd.Timestamp("2010-01-11")].any()


def test_roll_marking_quarterly_rule_is_a_subset_of_monthly():
    days = pd.bdate_range("2010-01-04", "2010-12-31")
    tape = pd.DataFrame({"date": days,
                         "open": np.full(len(days), 20000.0),
                         "close": np.full(len(days), 20000.0)})
    pairs = p2.build_pairs(tape)
    m = p2.mark_roll_adjacent(pairs, days, "monthly")
    q = p2.mark_roll_adjacent(pairs, days, "quarterly")
    assert int(m.sum()) == 12 * 3
    assert int(q.sum()) == 4 * 3          # Mar / Jun / Sep / Dec only
    assert bool((q & ~m).sum()) is False  # quarterly ⊂ monthly
    with pytest.raises(ValueError):
        p2.roll_marked_days(days, "weekly")


def test_roll_marking_skips_a_month_whose_second_friday_is_a_holiday():
    days = [d for d in pd.bdate_range("2010-01-04", "2010-02-26")
            if d != pd.Timestamp("2010-02-12")]      # 2010-02 SQ day closed
    marked = p2.roll_marked_days(days, "monthly")
    assert pd.Timestamp("2010-01-08") in marked
    assert pd.Timestamp("2010-02-12") not in marked
    # and no substitute day is marked in that month
    assert not any(d.month == 2 for d in marked)


def test_roll_marking_quarterly_marks_exactly_the_sq_pair_and_not_other_months():
    """PREREG (b): once the series is confirmed to be the LARGE contract
    (quarterly Mar/Jun/Sep/Dec expiries only), the quarterly rule must mark
    exactly the SQ pair for a quarter month and nothing for a non-quarter
    month's 2nd Friday -- on a two-month synthetic calendar (Jan
    non-quarter, Mar quarter)."""
    days = pd.bdate_range("2010-01-04", "2010-03-31")
    tape = pd.DataFrame({"date": days,
                         "open": np.full(len(days), 20000.0),
                         "close": np.full(len(days), 20000.0)})
    pairs = p2.build_pairs(tape)

    mask = p2.mark_roll_adjacent(pairs, days, "quarterly")
    got = {(str(a.date()), str(b.date())) for a, b in
           zip(pd.to_datetime(pairs.loc[mask, "date"]),
               pd.to_datetime(pairs.loc[mask, "date_t1"]))}

    # January's 2nd Friday (2010-01-08) is NOT a quarter month -> no pairs.
    # March's 2nd Friday (2010-03-12) IS a quarter month -> exactly the three
    # pairs touching {previous trading day, SQ}: (Wed,Thu) (Thu,SQ) (SQ,next).
    assert got == {
        ("2010-03-10", "2010-03-11"), ("2010-03-11", "2010-03-12"),
        ("2010-03-12", "2010-03-15"),
    }
    assert int(mask.sum()) == 3
    # none of the January-Friday pairs (monthly-only roll days) are marked
    assert not any(a.startswith("2010-01") or b.startswith("2010-01")
                  for a, b in got)
    # cross-check against the monthly rule on the same calendar: monthly
    # marks January's SQ too, quarterly does not
    monthly_mask = p2.mark_roll_adjacent(pairs, days, "monthly")
    monthly_got = {(str(a.date()), str(b.date())) for a, b in
                  zip(pd.to_datetime(pairs.loc[monthly_mask, "date"]),
                      pd.to_datetime(pairs.loc[monthly_mask, "date_t1"]))}
    assert ("2010-01-07", "2010-01-08") in monthly_got
    assert ("2010-01-07", "2010-01-08") not in got
    assert ("2010-02-11", "2010-02-12") in monthly_got
    assert ("2010-02-11", "2010-02-12") not in got


def test_mark_nightless_matches_by_date_pair_not_by_single_date():
    pairs = pd.DataFrame({
        "date": pd.to_datetime(["2007-12-28", "2008-01-04", "2008-01-07"]),
        "date_t1": pd.to_datetime(["2008-01-04", "2008-01-07", "2008-01-08"]),
    })
    mask = p2.mark_nightless(pairs)
    assert list(mask) == [True, True, False]
    # a pair sharing only one endpoint with a registered pair is NOT marked
    other = pd.DataFrame({"date": pd.to_datetime(["2008-01-03"]),
                          "date_t1": pd.to_datetime(["2008-01-04"])})
    assert list(p2.mark_nightless(other)) == [False]


def test_cost_constants_match_the_prereg():
    assert p2.COST_YEN_CONSERVATIVE == 122
    assert p2.COST_YEN_OPTIMISTIC == 22
    assert p2.GLITCH_THRESHOLD == 0.10
    assert (p2.BLOCK, p2.N_BOOT, p2.N_SHUFFLE, p2.SEED) == (20, 2000, 1000, 20260906)
