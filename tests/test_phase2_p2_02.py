"""Tests for scripts/phase2/p2_02_run.py (docs/PHASE2/P2-02/PREREG.md,
frozen 2026-09-06) -- synthetic-tape tests for the defect rules, and a
planted-drift recovery test for the pair-construction + costing pipeline.

All data here is synthetic, built in-test. No sealed or dev-set file is
read by this module.
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

from phase2 import p2_02_run as p2  # noqa: E402
from bot.research import overnight as onr  # noqa: E402

FLAT_BANDS = [(float("inf"), 1.0)]  # a single flat 1-yen tick band, for tests


def _df(dates, open_, high, low, close, volume):
    return pd.DataFrame({
        "date": pd.to_datetime(list(dates)),
        "open": list(open_),
        "high": list(high),
        "low": list(low),
        "close": list(close),
        "volume": list(volume),
    })


# --------------------------------------------------------------- rule 2: ghost rows

def test_detect_ghost_rows_flags_zero_volume_flat_ohlc_matching_prev_close():
    close = np.array([100.0, 100.0, 105.0, 105.0])
    open_ = close.copy()
    high = close.copy()
    low = close.copy()
    volume = np.array([1000.0, 0.0, 1000.0, 0.0])
    ghost = p2.detect_ghost_rows(open_, high, low, close, volume)
    assert ghost == {1, 3}


def test_detect_ghost_rows_does_not_flag_listing_period_zero_volume_with_moving_ohlc():
    # zero volume but OHLC actually MOVES (e.g. a listing-period print) --
    # PREREG: "上場直後の出来高0の行(四本値が動く)は除外しない"
    close = np.array([100.0, 102.0, 98.0])
    open_ = np.array([100.0, 101.0, 99.0])
    high = np.array([100.0, 103.0, 99.5])
    low = np.array([100.0, 100.5, 97.5])
    volume = np.array([1000.0, 0.0, 1000.0])
    ghost = p2.detect_ghost_rows(open_, high, low, close, volume)
    assert ghost == set()


def test_detect_ghost_rows_first_row_never_flagged():
    # row 0 has no previous close to compare to close==prev_close against
    close = np.array([100.0, 100.0])
    open_ = close.copy()
    high = close.copy()
    low = close.copy()
    volume = np.array([0.0, 0.0])
    ghost = p2.detect_ghost_rows(open_, high, low, close, volume)
    assert 0 not in ghost


def test_detect_ghost_rows_volume_nonzero_not_flagged_even_if_flat():
    close = np.array([100.0, 100.0])
    open_ = close.copy()
    high = close.copy()
    low = close.copy()
    volume = np.array([1000.0, 500.0])  # not a holiday phantom -- real flat day
    ghost = p2.detect_ghost_rows(open_, high, low, close, volume)
    assert ghost == set()


# --------------------------------------------------------- rule 1: bad-print runs

def test_bad_print_single_row_spike_with_recovery_is_flagged():
    # c0 = 1000 (row 0's close). Row 1 spikes both open & close > 30% away,
    # row 2 recovers close to within 5% of c0.
    close = np.array([1000.0, 1500.0, 1010.0, 1005.0])
    open_ = np.array([1000.0, 1490.0, 1005.0, 1010.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == {1}
    assert one_sided == []


def test_bad_print_run_of_two_rows_with_recovery_is_flagged():
    close = np.array([1000.0, 1500.0, 1520.0, 1010.0, 1005.0])
    open_ = np.array([1000.0, 1490.0, 1510.0, 1005.0, 1010.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == {1, 2}


def test_bad_print_run_longer_than_max_run_not_flagged_real_market_move():
    # a genuine move: deviates for 4 consecutive rows (exceeds k<=3), never
    # "recovers" within the window checked -- must NOT be flagged (the
    # PREREG's 2024-08-05/06 real-market-move example).
    close = np.array([1000.0, 1500.0, 1520.0, 1530.0, 1540.0, 1550.0])
    open_ = np.array([1000.0, 1490.0, 1510.0, 1520.0, 1530.0, 1540.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == set()


def test_bad_print_run_without_recovery_not_flagged():
    # deviates for 1 row but the following row does NOT come back within 5%
    close = np.array([1000.0, 1500.0, 1480.0, 1470.0])
    open_ = np.array([1000.0, 1490.0, 1475.0, 1465.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == set()


def test_bad_print_one_sided_deviation_not_excluded_but_counted():
    # only OPEN deviates >30% from c0; close stays near c0 -- PREREG:
    # "片方だけ飛ぶ行は除外せず件数を報告"
    close = np.array([1000.0, 1010.0, 1005.0])
    open_ = np.array([1000.0, 1600.0, 1005.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == set()
    assert one_sided == [1]


def test_bad_print_first_and_last_row_never_flagged():
    # row 0 is first, row -1 is last -- "先頭・末尾行は判定対象外"; even if
    # they'd otherwise look anomalous relative to a neighbor, they can't be
    # run members since detect_bad_print_runs only scans interior indices.
    close = np.array([1000.0, 1010.0])
    open_ = np.array([1000.0, 1005.0])
    flagged, one_sided = p2.detect_bad_print_runs(close, open_)
    assert flagged == set()


# ----------------------------------------------------- pair table: rule application

def test_build_pair_table_zero_open_only_drops_the_pair_using_it_as_input():
    # PREREG worked example: open(t)=0 on row t drops pair (t-1,t) only;
    # if close(t) is fine, pair (t, t+1) survives.
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    df = _df(dates,
             open_=[100.0, 0.0, 102.0, 103.0],
             high=[101.0, 105.0, 103.0, 104.0],
             low=[99.0, 95.0, 101.0, 102.0],
             close=[100.0, 101.0, 102.0, 103.0],
             volume=[1000, 1000, 1000, 1000])
    pairs, flagged, one_sided, ghost = p2.build_pair_table(df, FLAT_BANDS)
    pair_0_1 = pairs[(pairs["t_date"] == dates[0]) & (pairs["t1_date"] == dates[1])].iloc[0]
    pair_1_2 = pairs[(pairs["t_date"] == dates[1]) & (pairs["t1_date"] == dates[2])].iloc[0]
    assert bool(pair_0_1["kept"]) is False  # open(t1)=0 is the pair's input -> dropped
    assert bool(pair_1_2["kept"]) is True   # close(t)=101 (not open(t)=0) is the input -> kept


def test_build_pair_table_ghost_row_drops_both_adjacent_pairs():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    df = _df(dates,
             open_=[100.0, 100.0, 105.0, 108.0],
             high=[101.0, 100.0, 106.0, 109.0],
             low=[99.0, 100.0, 104.0, 107.0],
             close=[100.0, 100.0, 105.0, 108.0],
             volume=[1000, 0, 1000, 1000])  # row 1 is a ghost (flat at prev close 100, vol 0)
    pairs, flagged, one_sided, ghost = p2.build_pair_table(df, FLAT_BANDS)
    assert ghost == {1}
    kept_flags = dict(zip(zip(pairs["t_date"], pairs["t1_date"]), pairs["kept"]))
    assert bool(kept_flags[(dates[0], dates[1])]) is False
    assert bool(kept_flags[(dates[1], dates[2])]) is False
    assert bool(kept_flags[(dates[2], dates[3])]) is True


def test_build_pair_table_thin_flag_matches_volume_threshold():
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    df = _df(dates, open_=[100, 101, 102], high=[101, 102, 103],
             low=[99, 100, 101], close=[100, 101, 102],
             volume=[4999, 5000, 100000])
    pairs, *_ = p2.build_pair_table(df, FLAT_BANDS)
    thin_by_t = dict(zip(pairs["t_date"], pairs["thin"]))
    assert bool(thin_by_t[dates[0]]) is True   # 4999 < 5000
    assert bool(thin_by_t[dates[1]]) is False  # 5000 is not < 5000


# --------------------------------------------------------------- tick-size lookup

def test_tick_for_price_picks_correct_band():
    bands = p2.build_tick_lookup({
        "up_to_1000_yen": 1, "up_to_30000_yen": 5, "over_50000000_yen": 10000,
    })
    assert p2.tick_for_price(900.0, bands) == 1.0
    assert p2.tick_for_price(1000.0, bands) == 1.0
    assert p2.tick_for_price(1000.01, bands) == 5.0
    assert p2.tick_for_price(10_000_000.0, bands) == 10000.0


def test_conservative_cost_bps_is_two_ticks_over_close_in_bps():
    bands = [(float("inf"), 1.0)]
    close = np.array([1000.0, 2000.0])
    cost = p2.conservative_cost_bps(close, bands)
    assert cost[0] == pytest.approx(2.0 / 1000.0 * 1e4)
    assert cost[1] == pytest.approx(2.0 / 2000.0 * 1e4)


# ------------------------------------------------------ planted-drift recovery

def test_planted_drift_recovered_by_pair_and_cost_pipeline():
    """Build a clean synthetic tape with an exactly-planted overnight drift
    (no defects) and confirm the pair table + conservative-cost pipeline
    recovers it within the block-bootstrap CI -- the daily-pipeline
    equivalent of the PREREG's known-answer test, for THIS script's own
    pair-construction/costing code path (not a re-test of overnight.py,
    which has its own known-answer coverage)."""
    rng = np.random.default_rng(20260906)
    n = 800
    planted_bps = 12.0
    close0 = 1500.0

    close = np.empty(n)
    open_ = np.empty(n)
    close[0] = close0
    open_[0] = close0
    for i in range(1, n):
        # overnight leg close(i-1) -> open(i): planted drift + tiny noise
        open_[i] = close[i - 1] * (1.0 + planted_bps / 1e4 + rng.normal(0, 1e-6))
        # intraday leg open(i) -> close(i): pure noise, no drift
        close[i] = open_[i] * (1.0 + rng.normal(0, 0.001))
    high = np.maximum(open_, close) + 1.0
    low = np.minimum(open_, close) - 1.0
    volume = np.full(n, 50_000.0)
    dates = pd.bdate_range("2015-01-01", periods=n)
    df = _df(dates, open_, high, low, close, volume)

    pairs, flagged, one_sided, ghost = p2.build_pair_table(df, [(float("inf"), 0.0)])
    assert flagged == set()
    assert ghost == set()
    kept = pairs[pairs["kept"]]
    assert len(kept) == n - 1

    r_night = kept["r_night_raw_bps"].to_numpy()
    mean, lo, hi = p2.mean_ci_bootstrap(r_night, seed=1)
    assert mean == pytest.approx(planted_bps, abs=1.0)
    assert lo < planted_bps < hi


def test_dividend_adjustment_recovers_planted_ex_date_drop():
    """A synthetic ex-dividend drop of exactly `div` yen on the open print,
    corrected by add_dividend_adjustment, must give back the pre-drop
    (undepressed) overnight return exactly."""
    dates = pd.bdate_range("2020-01-01", periods=10)
    close = np.full(10, 1000.0)
    div_amount = 8.0
    ex_idx = 5
    open_ = close.copy()
    open_[ex_idx] = close[ex_idx - 1] - div_amount  # depressed by the payout
    high = np.maximum(open_, close) + 1
    low = np.minimum(open_, close) - 1
    df = _df(dates, open_, high, low, close, np.full(10, 10000.0))

    pairs, *_ = p2.build_pair_table(df, [(float("inf"), 0.0)])
    # Post-T+2-cutover (2020 > 2019-07-16): ex_dates_from_record_dates maps
    # a record date that is itself a trading day 1 trading day BACK to get
    # the effective ex-date -- so a record date of dates[ex_idx + 1] derives
    # to dates[ex_idx], matching where the price drop was planted above.
    div_df = pd.DataFrame({"ex_date": [dates[ex_idx + 1]], "amount": [div_amount]})
    pairs2, div_eff = p2.add_dividend_adjustment(pairs, df, div_df)
    assert pd.Timestamp(div_eff["ex_date_effective"].iloc[0]) == dates[ex_idx]

    row = pairs2[pairs2["t1_date"] == dates[ex_idx]].iloc[0]
    assert row["r_night_raw_bps"] == pytest.approx(-div_amount / 1000.0 * 1e4)
    assert row["r_night_adj_bps"] == pytest.approx(0.0, abs=1e-9)
