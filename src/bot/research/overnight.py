"""Pure overnight-return computation helpers.

Shared by ONR-family research scripts (`scripts/research_overnight_onr.py`)
and QA known-answer pipelines (`scripts/qa/pipeline_known_answer_daily.py`).
Everything here is generic time-series computation: the close(t) ->
open(t+1) "overnight" leg (as a log or a simple return), a gross
data-glitch filter, a one-sample mean/t-stat, and two resampling-based
inference helpers (block bootstrap CI, sign-shuffle null). No instrument,
window, cost, or verdict is baked in — callers supply their own data and
interpret the numbers themselves.

`GLITCH_ABS_LOG_RET_DEFAULT = 0.10` (an absolute log return of 10%) is a
pre-registered constant: it is the glitch threshold the frozen ONR PREREG
(docs/PREREG_overnight_onr.md) specifies for `drop_glitches()`, carried
here as the default so callers get it without repeating the literal.
Passing an explicit `threshold` overrides it for a given call.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

GLITCH_ABS_LOG_RET_DEFAULT = 0.10
JPX_T2_CUTOVER_DEFAULT = date(2019, 7, 16)  # JPX settlement shortened T+3 -> T+2


def overnight_returns(
    df: pd.DataFrame,
    dividends: pd.DataFrame | None = None,
    kind: Literal["log", "simple"] = "log",
) -> pd.DataFrame:
    """Compute the overnight leg from close(t) to open(t+1).

    Parameters
    ----------
    df : DataFrame with "date", "open", "close" columns, sorted ascending
        by date with one row per trading day.
    dividends : optional DataFrame with "ex_date_effective" and "amount"
        columns. "ex_date_effective" must already be the actual TRADING DAY
        on which the market stops pricing in the distribution -- NOT a raw
        record date (JPX's own 権利確定日, which is a calendar date, often a
        weekend, and is what e.g. reit_onr_20260904/etf_1343_dividends.csv's
        "ex_date" column actually holds despite its name). Convert record
        dates with `ex_dates_from_record_dates()` first if that's what you
        have. When given, for each leg whose t+1 date is an effective
        ex-date, the matching amount is added to open(t+1) before computing
        the return -- the holder of the overnight position (bought at
        close(t)) is the one entitled to the distribution, so its exclusion
        from the raw open print is a pure price-mechanics artifact, not a
        return. Dates not present in `dividends` get 0. Default None: no
        adjustment (matches calling the function with dividends omitted
        entirely).
    kind : "log" (default) returns r_t = ln(open(t+1) / close(t)); "simple"
        returns r_t = open(t+1) / close(t) - 1. Both use the same
        (dividend-adjusted, if given) open(t+1); for small returns
        r_simple - r_log ~= r_simple**2 / 2 to first order (from
        ln(1+x) = x - x**2/2 + O(x**3)). Default "log" keeps prior callers'
        numbers unchanged.

    Returns
    -------
    DataFrame with "date" (the close date t, i.e. the entry date) and "r"
    (the return of holding from close(t) to open(t+1), in the units given
    by `kind`). The last row of `df` has no t+1 open and is dropped.
    """
    o1 = df["open"].shift(-1)
    if dividends is not None and len(dividends):
        dates_t1 = df["date"].shift(-1)
        div_by_date = dividends.set_index("ex_date_effective")["amount"]
        add = dates_t1.map(div_by_date).fillna(0.0)
        o1 = o1 + add.to_numpy()
    ratio = o1 / df["close"]
    if kind == "log":
        r = np.log(ratio)
    elif kind == "simple":
        r = ratio - 1.0
    else:
        raise ValueError(f"kind must be 'log' or 'simple', got {kind!r}")
    out = pd.DataFrame({"date": df["date"], "r": r})
    return out.iloc[:-1].reset_index(drop=True)


def drop_glitches(
    df: pd.DataFrame, threshold: float = GLITCH_ABS_LOG_RET_DEFAULT
) -> tuple[pd.DataFrame, int]:
    """Drop rows whose |r| exceeds `threshold`.

    A coarse gross-data-glitch filter: it does not distinguish a genuine
    data error from any other large single-bar move (e.g. an unadjusted
    corporate action) that happens to exceed the threshold.

    Parameters
    ----------
    df : DataFrame with an "r" column (log returns).
    threshold : absolute log-return above which a row is dropped
        (default GLITCH_ABS_LOG_RET_DEFAULT = 0.10, the pre-registered
        ONR PREREG value).

    Returns
    -------
    (filtered_df, n_dropped) -- n_dropped is the row count removed, so a
    caller can report it (e.g. in a results table) without recomputing.
    """
    mask = df["r"].abs() > threshold
    n = int(mask.sum())
    return df.loc[~mask].reset_index(drop=True), n


def count_glitches(df: pd.DataFrame, threshold: float = GLITCH_ABS_LOG_RET_DEFAULT) -> int:
    """Convenience wrapper: how many rows `drop_glitches` would drop.

    Equivalent to `drop_glitches(df, threshold)[1]`, for callers that only
    need the count (e.g. a report line) without the filtered frame.
    """
    return drop_glitches(df, threshold)[1]


def ex_dates_from_record_dates(
    record_dates: Iterable,
    trading_days: Iterable,
    t2_cutover: date = JPX_T2_CUTOVER_DEFAULT,
) -> list[pd.Timestamp]:
    """Map dividend RECORD dates to effective (tradable) ex-dividend dates.

    A JPX record date (権利確定日) is a calendar date -- often a weekend --
    on which shareholders of record are entitled to a distribution; it is
    NOT the trading day the market prices the distribution out on. This
    derives that trading day from the record date and the exchange's
    settlement cycle, entirely in TRADING-day units:

      1. `eff_record` = the last date in `trading_days` on or before the
         record date (the record date itself, if it is already a trading
         day).
      2. `ex_date_effective` = `eff_record` minus 2 trading days if
         `eff_record` is before `t2_cutover` (T+3 settlement), else
         `eff_record` minus 1 trading day (T+2 settlement).

    Parameters
    ----------
    record_dates : raw record dates (any calendar date, weekends included)
        -- e.g. the misleadingly-named "ex_date" column of
        backtest_data/reit_onr_20260904/etf_1343_dividends.csv.
    trading_days : the trading-day calendar to walk, covering at least a
        few trading days before the earliest record date. Real runs should
        pass the trading days present in the price file itself; tests may
        pass a synthetic Mon-Fri-minus-holidays calendar.
    t2_cutover : the settlement-cycle change date. JPX shortened cash
        equity/ETF settlement from T+3 to T+2 on 2019-07-16 (the default);
        pass a different date for a different market or instrument.

    Returns
    -------
    List of effective ex-dates (pd.Timestamp), one per input record date,
    in the same order as `record_dates`.
    """
    td = pd.DatetimeIndex(sorted(pd.Timestamp(d) for d in trading_days))
    cutover_ts = pd.Timestamp(t2_cutover)
    out: list[pd.Timestamp] = []
    for rd in record_dates:
        rd_ts = pd.Timestamp(rd)
        pos = int(td.searchsorted(rd_ts, side="right")) - 1
        if pos < 0:
            raise ValueError(f"no trading day on or before record date {rd_ts.date()}")
        eff_record = td[pos]
        step = 2 if eff_record < cutover_ts else 1
        idx = pos - step
        if idx < 0:
            raise ValueError(
                f"not enough trading days before {eff_record.date()} to step back {step}"
            )
        out.append(td[idx])
    return out


def mean_t(x: np.ndarray) -> tuple[float, float, int]:
    """Sample mean, one-sample t-stat against 0, and n for `x`.

    Returns
    -------
    (mean, t_stat, n). t_stat is nan when n < 2 or the sample has zero
    variance; mean is nan when n == 0.
    """
    n = len(x)
    if n < 2:
        return (float(x.mean()) if n else float("nan"), float("nan"), n)
    m = float(x.mean())
    s = float(x.std(ddof=1))
    t = m / (s / np.sqrt(n)) if s > 0 else float("nan")
    return m, t, n


def block_bootstrap_ci(
    x: np.ndarray,
    block: int = 20,
    n_boot: int = 1000,
    seed: int | None = None,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Moving-block bootstrap confidence interval of the mean.

    Resamples fixed-length contiguous blocks (wrapping around the end of
    the series) to approximately preserve short-range autocorrelation,
    then takes the empirical percentile interval of the resulting
    bootstrap mean distribution.

    Parameters
    ----------
    x : 1-D array of observations (e.g. daily log returns).
    block : block length in observations.
    n_boot : number of bootstrap resamples.
    seed : RNG seed; None for a non-reproducible draw.
    alpha : two-sided interval level (default 0.05 -> a 95% CI).

    Returns
    -------
    (lo, hi): the alpha/2 and 1-alpha/2 percentiles of the bootstrap mean
    distribution. (nan, nan) if there are fewer than `block` observations.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < max(2, block):
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    boot_means = np.empty(n_boot)
    offsets = np.arange(block)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n] % n
        boot_means[b] = x[idx].mean()
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def sign_shuffle_null(
    x: np.ndarray, n: int = 1000, seed: int | None = None
) -> np.ndarray:
    """Sign-shuffle null distribution of the mean.

    Randomly flips the sign of each observation independently, `n` times,
    and returns the resulting array of resample means. This gives a null
    distribution consistent with a true mean of 0 while preserving the
    empirical distribution of |x| (magnitude, heteroskedasticity, fat
    tails), for use as a non-parametric reference against the observed
    mean of `x`.

    Parameters
    ----------
    x : 1-D array of observations.
    n : number of sign-shuffle resamples.
    seed : RNG seed; None for a non-reproducible draw.

    Returns
    -------
    1-D array of length `n` holding the resampled means. Empty array if
    `x` is empty.
    """
    x = np.asarray(x, dtype=float)
    m = len(x)
    if m == 0:
        return np.array([], dtype=float)
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n, m))
    return (signs * x).mean(axis=1)
