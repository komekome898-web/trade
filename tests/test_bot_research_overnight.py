"""Tests for src/bot/research/overnight.py -- pure overnight-return
computation helpers shared by ONR-family research scripts and QA
known-answer pipelines. All data here is synthetic/tmp, built in-test."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from bot.research.overnight import (
    GLITCH_ABS_LOG_RET_DEFAULT,
    JPX_T2_CUTOVER_DEFAULT,
    block_bootstrap_ci,
    count_glitches,
    drop_glitches,
    ex_dates_from_record_dates,
    mean_t,
    overnight_returns,
    sign_shuffle_null,
)

# Synthetic Mon-Fri (no holidays) trading calendar, wide enough to cover all
# hand-derived cases below.
_SYNTHETIC_TRADING_DAYS = pd.bdate_range("2012-01-01", "2021-01-01")


# --------------------------------------------------------- overnight_returns


def _ohlc(dates, open_, close):
    return pd.DataFrame({"date": pd.to_datetime(list(dates)),
                          "open": list(open_), "close": list(close)})


def test_overnight_returns_basic_formula():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [100.0, 102.0, 105.0], [101.0, 103.0, 104.0])
    out = overnight_returns(df)
    # r_t = ln(open(t+1)/close(t)); last row dropped (no t+1)
    assert len(out) == 2
    assert out["r"].iloc[0] == pytest.approx(math.log(102.0 / 101.0))
    assert out["r"].iloc[1] == pytest.approx(math.log(105.0 / 103.0))
    assert list(out["date"]) == list(pd.to_datetime(["2024-01-01", "2024-01-02"]))


def test_overnight_returns_drops_last_row_with_no_lookahead():
    df = _ohlc(["2024-01-01", "2024-01-02"], [100.0, 102.0], [101.0, 103.0])
    out = overnight_returns(df)
    assert len(out) == 1  # the 2nd row has no t+1 open, so it can't be a leg


def test_overnight_returns_with_dividends_adds_amount_at_ex_date():
    # close(t)=1000 on day0, raw (ex-div-depressed) open(t+1)=998.0 on day1,
    # dividend of 5.0 goes ex on day1 -> adjusted open = 998.0 + 5.0
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [1000.0, 998.0, 1010.0], [1000.0, 1005.0, 1012.0])
    div = pd.DataFrame({"ex_date_effective": pd.to_datetime(["2024-01-02"]), "amount": [5.0]})

    raw = overnight_returns(df)
    adj = overnight_returns(df, dividends=div)

    assert raw["r"].iloc[0] == pytest.approx(math.log(998.0 / 1000.0))
    assert adj["r"].iloc[0] == pytest.approx(math.log((998.0 + 5.0) / 1000.0))
    # the leg NOT preceding an ex-date is untouched
    assert adj["r"].iloc[1] == pytest.approx(raw["r"].iloc[1])


def test_overnight_returns_dividends_none_matches_omitted_argument():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [100.0, 102.0, 105.0], [101.0, 103.0, 104.0])
    a = overnight_returns(df)
    b = overnight_returns(df, dividends=None)
    pd.testing.assert_frame_equal(a, b)


def test_overnight_returns_dividends_empty_table_is_a_no_op():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [100.0, 102.0, 105.0], [101.0, 103.0, 104.0])
    empty = pd.DataFrame({"ex_date_effective": pd.to_datetime([]), "amount": []})
    a = overnight_returns(df)
    b = overnight_returns(df, dividends=empty)
    pd.testing.assert_frame_equal(a, b)


def test_overnight_returns_dividends_date_not_matching_any_leg_is_ignored():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [100.0, 102.0, 105.0], [101.0, 103.0, 104.0])
    div = pd.DataFrame({"ex_date_effective": pd.to_datetime(["2099-01-01"]), "amount": [999.0]})
    a = overnight_returns(df)
    b = overnight_returns(df, dividends=div)
    pd.testing.assert_frame_equal(a, b)


# ------------------------------------------------------- kind="log"/"simple"


def test_overnight_returns_kind_simple_matches_planted_exactly():
    # planted EXACTLY 5bps of simple return: open(t+1) = close(t) * 1.0005
    close0 = 1000.0
    open1 = close0 * 1.0005
    df = _ohlc(["2024-06-03", "2024-06-04"], [close0, open1], [close0, open1])
    r_simple = overnight_returns(df, kind="simple")["r"].iloc[0]
    assert r_simple == pytest.approx(0.0005, abs=1e-15)


def test_overnight_returns_kind_log_is_default_and_unchanged():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [100.0, 102.0, 105.0], [101.0, 103.0, 104.0])
    default = overnight_returns(df)
    explicit_log = overnight_returns(df, kind="log")
    pd.testing.assert_frame_equal(default, explicit_log)


def test_overnight_returns_log_vs_simple_differ_by_r_squared_over_2():
    close0 = 1000.0
    open1 = close0 * 1.0005  # exactly 5bps simple
    df = _ohlc(["2024-06-03", "2024-06-04"], [close0, open1], [close0, open1])
    r_simple = overnight_returns(df, kind="simple")["r"].iloc[0]
    r_log = overnight_returns(df)["r"].iloc[0]
    diff = r_simple - r_log
    first_order = r_simple ** 2 / 2.0
    # remainder is O(r**3), so at 5bps the first-order term should match to
    # well within 1%
    assert abs(diff - first_order) / first_order < 0.01


def test_overnight_returns_kind_invalid_raises():
    df = _ohlc(["2024-01-01", "2024-01-02"], [100.0, 102.0], [101.0, 103.0])
    with pytest.raises(ValueError):
        overnight_returns(df, kind="bogus")


def test_overnight_returns_kind_with_dividends_uses_adjusted_open_for_both():
    df = _ohlc(["2024-01-01", "2024-01-02", "2024-01-03"],
               [1000.0, 998.0, 1010.0], [1000.0, 1005.0, 1012.0])
    div = pd.DataFrame({"ex_date_effective": pd.to_datetime(["2024-01-02"]), "amount": [5.0]})
    r_simple = overnight_returns(df, dividends=div, kind="simple")["r"].iloc[0]
    assert r_simple == pytest.approx((998.0 + 5.0) / 1000.0 - 1.0)


# ------------------------------------------------- ex_dates_from_record_dates

# Hand-derived cases (record date -> effective ex-date), from the JPX
# record-date/settlement-cycle chain:
#   1. record 2018-03-31 (Sat) -> eff record 2018-03-30 (Fri) -> T+3
#      (pre-cutover) -> ex 2018-03-28 (Wed, 2 trading days back).
#   2. record 2020-03-31 (Tue, itself a trading day) -> T+2 (post-cutover)
#      -> ex 2020-03-30 (Mon, 1 trading day back).
#   3. record 2013-02-10 (Sun) -> eff record 2013-02-08 (Fri) -> T+3
#      (pre-cutover) -> ex 2013-02-06 (Wed, 2 trading days back).
#   4. record 2019-08-10 (Sat) -> eff record 2019-08-09 (Fri) -> T+2
#      (post-cutover, 2019-08-09 >= 2019-07-16) -> ex 2019-08-08 (Thu).
_HAND_DERIVED_RECORD_TO_EX = [
    ("2018-03-31", "2018-03-28"),
    ("2020-03-31", "2020-03-30"),
    ("2013-02-10", "2013-02-06"),
    ("2019-08-10", "2019-08-08"),
]


@pytest.mark.parametrize("record_date,expected_ex_date", _HAND_DERIVED_RECORD_TO_EX)
def test_ex_dates_from_record_dates_hand_derived_cases(record_date, expected_ex_date):
    got = ex_dates_from_record_dates([record_date], _SYNTHETIC_TRADING_DAYS)
    assert got == [pd.Timestamp(expected_ex_date)]


def test_ex_dates_from_record_dates_batch_matches_individual_calls():
    records = [r for r, _ in _HAND_DERIVED_RECORD_TO_EX]
    expected = [pd.Timestamp(e) for _, e in _HAND_DERIVED_RECORD_TO_EX]
    got = ex_dates_from_record_dates(records, _SYNTHETIC_TRADING_DAYS)
    assert got == expected


def test_ex_dates_from_record_dates_default_cutover_is_jpx_2019_07_16():
    assert JPX_T2_CUTOVER_DEFAULT.isoformat() == "2019-07-16"


def test_ex_dates_from_record_dates_record_date_itself_a_trading_day():
    # 2020-03-31 is itself a Tuesday trading day -> eff_record == record date
    got = ex_dates_from_record_dates(["2020-03-31"], _SYNTHETIC_TRADING_DAYS)
    assert got == [pd.Timestamp("2020-03-30")]


def test_ex_dates_from_record_dates_no_trading_day_before_raises():
    tiny_calendar = pd.bdate_range("2020-01-06", periods=3)  # starts a Mon
    with pytest.raises(ValueError):
        ex_dates_from_record_dates(["2020-01-01"], tiny_calendar)


def test_ex_dates_from_record_dates_not_enough_history_to_step_back_raises():
    tiny_calendar = pd.bdate_range("2020-01-06", periods=1)  # only 1 trading day
    with pytest.raises(ValueError):
        ex_dates_from_record_dates(["2020-01-06"], tiny_calendar)


def test_ex_dates_from_record_dates_custom_cutover():
    # with an artificially early cutover, even a pre-2019 record date gets
    # the T+2 (1-trading-day) treatment
    from datetime import date
    got = ex_dates_from_record_dates(
        ["2013-02-10"], _SYNTHETIC_TRADING_DAYS, t2_cutover=date(2000, 1, 1)
    )
    assert got == [pd.Timestamp("2013-02-07")]  # eff 2013-02-08 minus 1 trading day


# -------------------------------------------------------------- drop_glitches


def test_drop_glitches_default_threshold():
    df = pd.DataFrame({"r": [0.01, -0.02, 0.15, -0.11, 0.03]})
    out, n = drop_glitches(df)
    assert n == 2
    assert (out["r"].abs() <= GLITCH_ABS_LOG_RET_DEFAULT).all()
    assert len(out) == 3


def test_drop_glitches_custom_threshold():
    df = pd.DataFrame({"r": [0.01, -0.02, 0.03]})
    out, n = drop_glitches(df, threshold=0.015)
    assert n == 2
    assert list(out["r"]) == [0.01]


def test_drop_glitches_none_over_threshold():
    df = pd.DataFrame({"r": [0.01, -0.02, 0.03]})
    out, n = drop_glitches(df)
    assert n == 0
    assert len(out) == 3


def test_count_glitches_matches_drop_glitches_second_element():
    df = pd.DataFrame({"r": [0.01, -0.02, 0.15, -0.11, 0.03]})
    _, n = drop_glitches(df)
    assert count_glitches(df) == n
    assert count_glitches(df, threshold=0.015) == drop_glitches(df, threshold=0.015)[1]


# -------------------------------------------------------------------- mean_t


def test_mean_t_known_values():
    x = np.array([1.0, 2.0, 3.0])
    m, t, n = mean_t(x)
    assert n == 3
    assert m == pytest.approx(2.0)
    # std(ddof=1) = 1.0, se = 1/sqrt(3), t = 2 / (1/sqrt(3)) = 2*sqrt(3)
    assert t == pytest.approx(2.0 * math.sqrt(3.0))


def test_mean_t_empty():
    m, t, n = mean_t(np.array([]))
    assert n == 0
    assert math.isnan(m)
    assert math.isnan(t)


def test_mean_t_single_value():
    m, t, n = mean_t(np.array([5.0]))
    assert n == 1
    assert m == pytest.approx(5.0)
    assert math.isnan(t)


def test_mean_t_zero_variance_is_nan_tstat():
    m, t, n = mean_t(np.array([3.0, 3.0, 3.0]))
    assert n == 3
    assert m == pytest.approx(3.0)
    assert math.isnan(t)


# ------------------------------------------------------------- bootstrap/null


def test_block_bootstrap_ci_contains_true_mean_on_iid_data():
    rng = np.random.default_rng(42)
    x = rng.normal(loc=0.001, scale=0.01, size=500)
    lo, hi = block_bootstrap_ci(x, block=10, n_boot=500, seed=1)
    assert lo < hi
    assert lo < 0.001 < hi


def test_block_bootstrap_ci_deterministic_with_seed():
    x = np.linspace(-1, 1, 200)
    lo1, hi1 = block_bootstrap_ci(x, block=5, n_boot=200, seed=7)
    lo2, hi2 = block_bootstrap_ci(x, block=5, n_boot=200, seed=7)
    assert (lo1, hi1) == (lo2, hi2)


def test_block_bootstrap_ci_different_seed_can_differ():
    x = np.linspace(-1, 1, 200)
    r1 = block_bootstrap_ci(x, block=5, n_boot=200, seed=1)
    r2 = block_bootstrap_ci(x, block=5, n_boot=200, seed=2)
    assert r1 != r2


def test_block_bootstrap_ci_too_short_returns_nan():
    lo, hi = block_bootstrap_ci(np.array([1.0, 2.0, 3.0]), block=20, n_boot=100, seed=1)
    assert math.isnan(lo)
    assert math.isnan(hi)


def test_sign_shuffle_null_centered_near_zero_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(loc=0.02, scale=0.01, size=300)  # a real, nonzero mean
    null = sign_shuffle_null(x, n=2000, seed=3)
    assert null.shape == (2000,)
    # the sign-shuffle null has expectation 0 regardless of x's true mean
    assert abs(null.mean()) < 0.01
    # the observed mean should look extreme relative to the null distribution
    observed = x.mean()
    assert observed > np.percentile(null, 99)


def test_sign_shuffle_null_deterministic_with_seed():
    x = np.linspace(-1, 1, 50)
    n1 = sign_shuffle_null(x, n=100, seed=5)
    n2 = sign_shuffle_null(x, n=100, seed=5)
    np.testing.assert_array_equal(n1, n2)


def test_sign_shuffle_null_empty_input():
    out = sign_shuffle_null(np.array([]), n=10, seed=1)
    assert out.shape == (0,)
