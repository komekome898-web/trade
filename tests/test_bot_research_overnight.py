"""Tests for src/bot/research/overnight.py -- pure overnight-return
computation helpers shared by ONR-family research scripts and QA
known-answer pipelines. All data here is synthetic/tmp, built in-test."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from bot.research.overnight import (
    EDGE_TREND_SLOPE_MDE_Z,
    STATE_DIFF_MDE_Z,
    STATE_VERDICT_CANDIDATE,
    STATE_VERDICT_NO_DIFF,
    STATE_VERDICT_UNDECIDABLE,
    GLITCH_ABS_LOG_RET_DEFAULT,
    JPX_T2_CUTOVER_DEFAULT,
    block_bootstrap_ci,
    count_glitches,
    drop_glitches,
    edge_trend,
    ex_dates_from_record_dates,
    mean_t,
    overnight_returns,
    sign_shuffle_null,
    state_split,
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


# ------------------------------------------------------------------ edge_trend
#
# All the edge_trend tests here use a reduced n_boot (100 instead of the
# pre-registered 2,000) purely to keep the test suite fast -- window=250 and
# block=20 stay at the PHASE2_TEMPLATES.md §5.8 pre-registered values, and a
# smaller n_boot only widens the bootstrap CIs slightly, it does not bias
# them, so effects several times past the MDE (as planted below) still
# recover cleanly. Each planted scenario is computed ONCE per test module
# (module-scoped fixtures) and shared across the assertions that need it, so
# the 15-year/n_boot=100 cost (a few seconds each) is not paid repeatedly.

_EDGE_TREND_N_BOOT_TEST = 100
_EDGE_TREND_YEARS = 15
_EDGE_TREND_N = _EDGE_TREND_YEARS * 250  # ~15 years of "daily" observations
_EDGE_TREND_SIGMA_BPS = 110.0


def _planted_series(slope_bps_per_year: float, seed: int):
    """`_EDGE_TREND_N` bdate-spaced observations = slope_bps_per_year * t_years
    + N(0, sigma=110bps) noise, t_years counted in units of 250 obs/year (the
    PREREG's own day-count convention, §5.4's line: "sigma ~= 110bps の日次で
    15 年")."""
    dates = pd.bdate_range("2011-01-03", periods=_EDGE_TREND_N)
    t_years = np.arange(_EDGE_TREND_N) / 250.0
    rng = np.random.default_rng(seed)
    x = slope_bps_per_year * t_years + rng.normal(0.0, _EDGE_TREND_SIGMA_BPS, _EDGE_TREND_N)
    return dates, x


def _run_edge_trend(dates, x, **overrides):
    kwargs = dict(window=250, block=20, time_unit="year", time_axis="calendar",
                  period="year", n_boot=_EDGE_TREND_N_BOOT_TEST, seed=20260906)
    kwargs.update(overrides)
    return edge_trend(dates, x, **kwargs)


@pytest.fixture(scope="module")
def positive_series():
    return _planted_series(2.0, seed=101)


@pytest.fixture(scope="module")
def zero_series():
    return _planted_series(0.0, seed=202)


@pytest.fixture(scope="module")
def negative_series():
    return _planted_series(-2.0, seed=303)


@pytest.fixture(scope="module")
def positive_result(positive_series):
    dates, x = positive_series
    return _run_edge_trend(dates, x)


@pytest.fixture(scope="module")
def zero_result(zero_series):
    dates, x = zero_series
    return _run_edge_trend(dates, x)


@pytest.fixture(scope="module")
def negative_result(negative_series):
    dates, x = negative_series
    return _run_edge_trend(dates, x)


@pytest.fixture(scope="module")
def positive_result_month(positive_series):
    dates, x = positive_series
    return _run_edge_trend(dates, x, time_unit="month")


@pytest.fixture(scope="module")
def positive_result_index(positive_series):
    dates, x = positive_series
    return _run_edge_trend(dates, x, time_unit="sample", time_axis="index", period=None)


def test_edge_trend_planted_positive_slope_judges_expansion(positive_result):
    res = positive_result
    assert res["judgment"] == "拡大"
    lo, hi = res["slope_ci"]
    assert lo < hi
    assert lo <= 2.0 <= hi           # planted slope recovered inside the CI
    assert lo > 0                    # CI excludes zero and is positive
    assert res["slope_unit"] == "bps/year"
    assert res["slope_mde"] == pytest.approx(EDGE_TREND_SLOPE_MDE_Z * res["slope_se"], rel=1e-9)
    assert res["slope_mde"] == pytest.approx(2.8016 * res["slope_se"], rel=1e-4)
    assert res["last_window"] is not None
    assert res["last_window"]["ci_lo"] > 0


def test_edge_trend_zero_slope_judges_indeterminate(zero_result):
    res = zero_result
    assert res["judgment"] == "判定不能(標本不足)"
    lo, hi = res["slope_ci"]
    assert lo <= 0.0 <= hi            # CI contains zero, as planted
    assert res["judgment"] != "安定"  # PREREG: never re-read 判定不能 as 安定


def test_edge_trend_planted_negative_slope_judges_shrinkage(negative_result):
    res = negative_result
    assert res["judgment"] == "縮小"
    lo, hi = res["slope_ci"]
    assert lo < hi
    assert lo <= -2.0 <= hi           # planted slope recovered inside the CI
    assert hi < 0                     # CI excludes zero and is negative


def test_edge_trend_month_slope_times_12_approximately_matches_year_slope(
    positive_result, positive_result_month,
):
    res_year, res_month = positive_result, positive_result_month
    assert res_year["slope_unit"] == "bps/year"
    assert res_month["slope_unit"] == "bps/month"
    # both fit the SAME (t, x) relationship rescaled linearly in time, so the
    # two slopes agree to float precision, not just approximately
    assert res_month["slope"] * 12 == pytest.approx(res_year["slope"], rel=1e-9)


def test_edge_trend_index_axis_requires_sample_unit_and_runs(
    positive_result, positive_result_index,
):
    res_year, res = positive_result, positive_result_index
    assert res["slope_unit"] == "bps/sample"
    assert res["period_table"] is None
    # `dates` is a real business-day calendar (~261.9 sessions/year), while
    # the series was planted on a synthetic 250-obs/year grid, so the
    # calendar-year slope and 250*sample-slope agree only approximately
    # (both estimate the same planted +2bps/year trend, from two different
    # time axes over the same observations) -- exact equality is not
    # expected and would indicate the two time axes were accidentally
    # collapsed into the same one.
    assert res["slope"] * 250.0 == pytest.approx(res_year["slope"], rel=0.1)
    assert res["slope"] > 0  # same sign as the planted positive trend


def test_edge_trend_time_axis_calendar_rejects_sample_unit(zero_series):
    dates, x = zero_series
    with pytest.raises(ValueError):
        _run_edge_trend(dates, x, time_unit="sample", time_axis="calendar")


def test_edge_trend_time_axis_index_rejects_non_sample_unit(zero_series):
    dates, x = zero_series
    with pytest.raises(ValueError):
        _run_edge_trend(dates, x, time_axis="index")  # time_unit stays "year"


def test_edge_trend_invalid_period_raises(zero_series):
    dates, x = zero_series
    with pytest.raises(ValueError):
        _run_edge_trend(dates, x, period="quarter")


def test_edge_trend_mismatched_lengths_raises(zero_series):
    dates, x = zero_series
    with pytest.raises(ValueError):
        _run_edge_trend(dates[:-1], x)


def test_edge_trend_deterministic_with_seed(positive_series):
    dates, x = positive_series
    r1 = _run_edge_trend(dates, x, seed=7)
    r2 = _run_edge_trend(dates, x, seed=7)
    assert r1["slope"] == r2["slope"]
    assert r1["slope_ci"] == r2["slope_ci"]
    pd.testing.assert_frame_equal(r1["rolling"], r2["rolling"])
    pd.testing.assert_frame_equal(r1["period_table"], r2["period_table"])


def test_edge_trend_period_table_year_buckets_and_counts(zero_result, zero_series):
    res, (_, x) = zero_result, zero_series
    pt = res["period_table"]
    assert list(pt.columns) == ["period", "n", "mean", "ci_lo", "ci_hi"]
    assert pt["n"].sum() == len(x)
    assert list(pt["period"]) == sorted(pt["period"])  # chronological order


def test_edge_trend_regime_table_partitions_the_full_span(zero_series):
    dates, x = zero_series
    boundary = dates[len(dates) // 2]
    res = _run_edge_trend(dates, x, regime_dates=[boundary])
    rt = res["regime_table"]
    assert len(rt) == 2
    assert rt["n"].sum() == len(x)


def test_edge_trend_half_split_matches_manual_split(positive_result, positive_series):
    res, (_, x) = positive_result, positive_series
    mid = len(x) // 2
    hs = res["half_split"]
    assert hs["n_first"] == mid
    assert hs["n_second"] == len(x) - mid
    assert hs["mean_first"] == pytest.approx(x[:mid].mean())
    assert hs["mean_second"] == pytest.approx(x[mid:].mean())
    assert hs["diff"] == pytest.approx(hs["mean_second"] - hs["mean_first"])
    lo, hi = hs["diff_ci"]
    assert lo < hi
    # second half is drawn from a higher-mean segment of the planted trend
    assert lo > 0


# ------------------------------------------------------------- state_split
#
# PHASE2_TEMPLATES.md §6 ("条件分析"). The two headline tests are known-answer
# tapes: a tape with a planted +30bps offset on ONE state of ONE variable at
# sigma 110 must flag exactly that variable's pairs as 候補, and the same tape
# without the offset must flag nothing.

_STATE_SIGMA_BPS = 110.0
_STATE_PLANTED_OFFSET_BPS = 30.0
_STATE_TAPE_N = 3000
_STATE_TAPE_SEED = 20260906
_STATE_RUN_SEED = 20260906


def _state_tape(planted: bool, n: int = _STATE_TAPE_N, seed: int = _STATE_TAPE_SEED):
    """Synthetic tape: 3 pre-registered-shaped state variables over N(0, 110).

    Labels are shuffled (not laid down in contiguous runs) so each state is
    spread across the whole tape; `planted` adds +30bps to the "3_高" level of
    "vol" and to nothing else.
    """
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, _STATE_SIGMA_BPS, n)
    vol = np.array(["1_低", "2_中", "3_高"] * (n // 3))
    rng.shuffle(vol)
    weekday = np.array(["1_月", "2_火", "3_水", "4_木", "5_金"] * (n // 5))
    rng.shuffle(weekday)
    sign = np.where(rng.random(n) < 0.5, "1_上昇", "2_非上昇")
    if planted:
        x = x + np.where(vol == "3_高", _STATE_PLANTED_OFFSET_BPS, 0.0)
    return x, {"vol": vol, "weekday": weekday, "sign": sign}


def _run_state_split(x, states, **overrides):
    kwargs = {"block": 20, "n_boot": 2000, "seed": _STATE_RUN_SEED}
    kwargs.update(overrides)
    return state_split(x, states, **kwargs)


@pytest.fixture(scope="module")
def planted_state_result():
    x, states = _state_tape(planted=True)
    return _run_state_split(x, states, cost_bps=np.full(len(x), 5.0)), (x, states)


@pytest.fixture(scope="module")
def null_state_result():
    x, states = _state_tape(planted=False)
    return _run_state_split(x, states), (x, states)


def test_state_split_planted_offset_is_the_only_candidate(planted_state_result):
    res, _ = planted_state_result
    cand = res["diff_table"][res["diff_table"]["verdict"] == STATE_VERDICT_CANDIDATE]
    # exactly the two pairs that straddle the planted state, and nothing else
    assert set(zip(cand["variable"], cand["state_a"], cand["state_b"])) == {
        ("vol", "1_低", "3_高"), ("vol", "2_中", "3_高"),
    }
    for row in cand.itertuples():
        # the planted state is the higher one, so a - b is negative
        assert row.diff < 0
        assert abs(row.diff) > res["null_p95"]
        assert row.ci_hi < 0  # CI excludes zero
        assert row.mde < abs(row.diff)  # and the difference is visible at this n


def test_state_split_planted_offset_recovered_in_the_state_means(planted_state_result):
    res, (x, states) = planted_state_result
    st = res["state_table"].set_index(["variable", "state"])
    high = st.loc[("vol", "3_高"), "mean"]
    others = [st.loc[("vol", lab), "mean"] for lab in ("1_低", "2_中")]
    # planted 30bps recovered to within a fraction of the per-state SE
    # (sigma 110 / sqrt(1000) ~= 3.5bps)
    for other in others:
        assert high - other == pytest.approx(_STATE_PLANTED_OFFSET_BPS, abs=12.0)


def test_state_split_no_effect_tape_has_no_candidate(null_state_result):
    res, _ = null_state_result
    assert (res["diff_table"]["verdict"] != STATE_VERDICT_CANDIDATE).all()
    assert res["null_p95"] > 0


def test_state_split_diff_table_shape_and_arithmetic(null_state_result):
    res, (x, states) = null_state_result
    dt = res["diff_table"]
    assert list(dt.columns) == [
        "variable", "state_a", "state_b", "n_a", "n_b", "mean_a", "mean_b",
        "diff", "ci_lo", "ci_hi", "se", "mde", "null_p95", "verdict"]
    # 3 vol pairs + 10 weekday pairs + 1 sign pair
    assert len(dt) == 3 + 10 + 1 == res["params"]["n_comparisons"]
    assert (dt["null_p95"] == res["null_p95"]).all()
    for row in dt.itertuples():
        assert row.diff == pytest.approx(row.mean_a - row.mean_b)
        assert row.mde == pytest.approx(STATE_DIFF_MDE_Z * row.se)
        assert row.ci_lo <= row.ci_hi


def test_state_split_state_table_counts_and_means_match_the_input(null_state_result):
    res, (x, states) = null_state_result
    st = res["state_table"]
    assert list(st.columns) == ["variable", "state", "n", "mean", "ci_lo", "ci_hi"]
    for var, labels in states.items():
        rows = st[st["variable"] == var]
        assert rows["n"].sum() == len(x)  # no missing labels on this tape
        for row in rows.itertuples():
            seg = x[np.asarray(labels) == row.state]
            assert row.n == len(seg)
            assert row.mean == pytest.approx(seg.mean())
            assert row.ci_lo < row.mean < row.ci_hi


def test_state_split_cost_columns_only_when_cost_given(planted_state_result,
                                                       null_state_result):
    with_cost, (x, _) = planted_state_result
    without_cost, _ = null_state_result
    assert "net_mean" not in without_cost["state_table"].columns
    assert without_cost["params"]["has_cost"] is False
    st = with_cost["state_table"]
    assert with_cost["params"]["has_cost"] is True
    assert st["cost_mean"].to_numpy() == pytest.approx(5.0)
    # net = gross - cost exactly; its CI is a separate bootstrap draw of the
    # shifted series, so it brackets the net mean and has a comparable width
    # rather than being the gross CI shifted by exactly 5.0.
    assert st["net_mean"].to_numpy() == pytest.approx(st["mean"].to_numpy() - 5.0)
    assert (st["net_ci_lo"] < st["net_mean"]).all()
    assert (st["net_mean"] < st["net_ci_hi"]).all()
    assert (st["net_ci_hi"] - st["net_ci_lo"]).to_numpy() == pytest.approx(
        (st["ci_hi"] - st["ci_lo"]).to_numpy(), rel=0.2)


def test_state_split_verdicts_are_the_three_fixed_labels(planted_state_result):
    res, _ = planted_state_result
    allowed = {STATE_VERDICT_CANDIDATE, STATE_VERDICT_UNDECIDABLE,
               STATE_VERDICT_NO_DIFF}
    assert set(res["diff_table"]["verdict"]) <= allowed
    # the lookup dict agrees with the table row for row
    for row in res["diff_table"].itertuples():
        assert res["verdict"][(row.variable, row.state_a, row.state_b)] == row.verdict


def test_state_split_undecidable_when_n_is_far_too_small():
    # 60 observations at sigma 110 cannot see a 30bps difference: MDE >> |diff|
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, _STATE_SIGMA_BPS, 60)
    labels = np.array(["1_a", "2_b"] * 30)
    x = x + np.where(labels == "2_b", _STATE_PLANTED_OFFSET_BPS, 0.0)
    res = _run_state_split(x, {"v": labels}, n_boot=500)
    row = res["diff_table"].iloc[0]
    assert row["mde"] > abs(row["diff"])
    assert row["verdict"] == STATE_VERDICT_UNDECIDABLE


def test_state_split_no_diff_verdict_when_visible_but_under_the_null():
    # A tiny-sigma tape with a planted 4bps step: n is large enough that the
    # MDE is under 4bps (so the difference IS visible), but the joint null of
    # the largest difference across 12 monthly levels sits above it.
    n = 3600
    rng = np.random.default_rng(11)
    x = rng.normal(0.0, 10.0, n)
    two = np.array(["1_a", "2_b"] * (n // 2))
    month = np.array([f"{m:02d}" for m in range(1, 13)] * (n // 12))
    rng.shuffle(month)
    x = x + np.where(two == "2_b", 4.0, 0.0)
    res = _run_state_split(x, {"two": two, "month": month})
    row = res["diff_table"].iloc[0]
    assert row["variable"] == "two"
    assert row["mde"] < abs(row["diff"])
    assert abs(row["diff"]) < res["null_p95"]
    assert row["verdict"] == STATE_VERDICT_NO_DIFF


def test_state_split_missing_labels_drop_only_that_variable():
    n = 400
    rng = np.random.default_rng(5)
    x = rng.normal(0.0, 50.0, n)
    partial = np.array([None] * 100 + ["1_a", "2_b"] * 150, dtype=object)
    full = np.array(["1_x", "2_y"] * 200)
    res = _run_state_split(x, {"partial": partial, "full": full}, n_boot=200)
    st = res["state_table"]
    assert st[st["variable"] == "partial"]["n"].sum() == 300
    assert st[st["variable"] == "full"]["n"].sum() == 400


def test_state_split_deterministic_with_seed(null_state_result):
    res, (x, states) = null_state_result
    again = _run_state_split(x, states)
    pd.testing.assert_frame_equal(res["state_table"], again["state_table"])
    pd.testing.assert_frame_equal(res["diff_table"], again["diff_table"])
    assert res["null_p95"] == again["null_p95"]


def test_state_split_single_level_variable_makes_no_comparison():
    x = np.arange(100, dtype=float)
    res = _run_state_split(x, {"only": np.array(["1_a"] * 100)}, n_boot=200)
    assert len(res["diff_table"]) == 0
    assert math.isnan(res["null_p95"])
    assert len(res["state_table"]) == 1


def test_state_split_rejects_length_mismatch_and_empty_input():
    x = np.zeros(10)
    with pytest.raises(ValueError, match="same length"):
        _run_state_split(x, {"v": np.array(["a"] * 9)})
    with pytest.raises(ValueError, match="same length"):
        _run_state_split(x, {"v": np.array(["a"] * 10)}, cost_bps=np.zeros(9))
    with pytest.raises(ValueError, match="must not be empty"):
        _run_state_split(np.array([]), {"v": np.array([])})
    with pytest.raises(ValueError, match="must not be empty"):
        _run_state_split(x, {})


def test_state_split_null_p95_is_the_95th_percentile_of_the_maxima(null_state_result):
    res, _ = null_state_result
    maxima = res["null_max_abs_diff"]
    assert len(maxima) == 2000
    assert (maxima >= 0).all()
    assert res["null_p95"] == pytest.approx(float(np.percentile(maxima, 95)))
