"""Pure overnight-return computation helpers.

Shared by ONR-family research scripts (`scripts/research_overnight_onr.py`)
and QA known-answer pipelines (`scripts/qa/pipeline_known_answer_daily.py`).
Everything here is generic time-series computation: the close(t) ->
open(t+1) "overnight" leg (as a log or a simple return), a gross
data-glitch filter, a one-sample mean/t-stat, two resampling-based
inference helpers (block bootstrap CI, sign-shuffle null), the
"edge trend" standard sub-indicator (`edge_trend`, PHASE2_TEMPLATES.md §5:
rolling-window mean+CI, yearly table, slope+CI+MDE, half-split difference,
optional regime table, and the fixed 拡大/縮小/判定不能 judgment sentence),
and the "condition analysis" standard sub-indicator (`state_split`,
PHASE2_TEMPLATES.md §6: per-state n/mean/CI, cost-net mean/CI, pairwise
state differences with CI and MDE, one joint block-permutation null for the
largest difference across every variable, and the fixed 候補/判定不能/差なし
verdict). No instrument, window, cost, or verdict is baked in — callers
supply their own data and interpret the numbers themselves.

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


def _moving_block_bootstrap_means(
    x: np.ndarray, block: int, n_boot: int, seed: int | None
) -> np.ndarray:
    """Raw array of `n_boot` moving-block-bootstrap resample means of `x`.

    Factored out of `block_bootstrap_ci` so callers that need the full
    bootstrap distribution (not just its percentile interval) -- e.g.
    `edge_trend`'s first-half/second-half difference -- draw with the exact
    same algorithm and RNG call sequence. `block_bootstrap_ci(x, block,
    n_boot, seed)` is equivalent to taking the alpha/2 and 1-alpha/2
    percentiles of this function's output with the same arguments.

    Returns an all-nan array of length `n_boot` if there are fewer than
    `block` observations (mirrors `block_bootstrap_ci`'s (nan, nan) case).
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < max(2, block):
        return np.full(n_boot, float("nan"))
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    boot_means = np.empty(n_boot)
    offsets = np.arange(block)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n] % n
        boot_means[b] = x[idx].mean()
    return boot_means


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
    boot_means = _moving_block_bootstrap_means(x, block, n_boot, seed)
    if np.isnan(boot_means).all():
        return float("nan"), float("nan")
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


# ---------------------------------------------------------------------------
# edge trend (standard sub-indicator, PHASE2_TEMPLATES.md §5)
# ---------------------------------------------------------------------------

# alpha=0.05 two-sided / power=0.8: Z_(1-alpha/2) + Z_power. Same convention as
# scripts/phase2/p2_01_run.py's MDE rows; PHASE2_TEMPLATES.md §5.4 quotes this
# rounded to 2.8016.
EDGE_TREND_SLOPE_MDE_Z = 1.959963985 + 0.8416212336


_EDGE_TREND_TIME_UNITS = ("year", "month", "week", "day", "hour", "minute", "sample")
_EDGE_TREND_PERIODS = ("year", "month", "week", "day", "hour")
# seconds-per-unit for "calendar" axis conversion (month = 365.25/12 days, the
# same average-month convention as the year constant it is derived from;
# week = 7 exact days, period key = ISO year-week).
_EDGE_TREND_UNIT_SECONDS = {
    "year": 365.25 * 86400.0,
    "month": (365.25 / 12.0) * 86400.0,
    "week": 7.0 * 86400.0,
    "day": 86400.0,
    "hour": 3600.0,
    "minute": 60.0,
}


def edge_trend(
    dates,
    values_bps: np.ndarray,
    *,
    window: int,
    block: int,
    time_unit: str,
    time_axis: str,
    period: str | None,
    n_boot: int = 2000,
    seed: int = 20260906,
    regime_dates: Iterable | None = None,
    rolling_step: int = 1,
) -> dict:
    """The standard "edge trend" sub-indicator (PHASE2_TEMPLATES.md §5).

    Describes whether the expected value of a per-observation series (e.g.
    a night's gross overnight return, its per-pair cost, or its net return,
    all in bps) has been expanding or shrinking over time, using a fixed,
    pre-registered procedure -- never a single number in isolation (§5's
    "どれか 1 つだけ出すことは禁止"). `window`, `block`, `time_unit`,
    `time_axis` and `period` have no defaults: every call must name them
    explicitly and a research unit's RESULTS.md must state the values used,
    because §5.8 pre-registers window/block and a change of any of these is
    itself a design choice, not a library default.

    Parameters
    ----------
    dates : per-observation dates (anything `pd.to_datetime` accepts).
        Need not already be sorted -- `edge_trend` sorts (dates, values_bps)
        together ascending before computing anything. Only read when
        `time_axis="calendar"` or `period` is not None; may be any constant
        placeholder otherwise (still validated for matching length).
    values_bps : per-observation values, in bps (gross return, cost, or net
        return -- `edge_trend` does not care which; run it once per leg and
        assemble the gross/cost/net decomposition table from the three
        calls, per §5.1).
    window : rolling-window length in observations (§5.2: 250 for daily
        data, ~1 trading year). Pre-registered fixed per §5.8 -- changing
        it for a given research unit counts as an iteration.
    block : moving-block-bootstrap block length (§5.2/§5.4: 20). Also
        pre-registered fixed per §5.8.
    time_unit : the unit the slope, its CI and its MDE are reported in --
        one of "year", "month", "day", "hour", "minute", "sample". The
        return dict's `slope_unit` echoes this as "bps/<time_unit>".
    time_axis : "calendar" -- elapsed time from `dates`, converted to
        `time_unit` (average-length month/year, exact otherwise); or
        "index" -- plain sample number 0..n-1, which REQUIRES
        `time_unit="sample"` (raises `ValueError` otherwise, as does
        `time_axis="calendar"` combined with `time_unit="sample"`: calendar
        time has no "sample" unit -- use `time_axis="index"` for that).
    period : grouping key for the period table (§5.3), one of "year",
        "month", "day", "hour", or None to skip that table entirely.
        Independent of `time_unit`/`time_axis` -- e.g. a slope in
        bps/month can still be tabulated by "year".
    n_boot : bootstrap resamples per CI (§5.2/§5.4 default: 2,000).
    seed : RNG seed, reused across every bootstrap draw this call makes
        (rolling windows, period cells, the slope, the half-split
        difference, and any regimes) so a rerun is bit-identical.
    regime_dates : optional pre-registered regime BOUNDARY dates (§5.6 --
        "事前登録した制度変更日でのみ区分する"). Each date starts a new
        regime; the data's own first and last date close the first and last
        regime. None (default) skips the regime table entirely.
    rolling_step : evaluate the rolling window (mean + bootstrap CI) at
        every `rolling_step`-th window end instead of every one (default 1
        = every end, the original behaviour). The LAST window end is always
        included, so "last_window" and the judgment sentence are unchanged
        by this setting; it only thins the "rolling" table, for series with
        tens of thousands of observations where a CI at every end would
        cost n × n_boot resamples.

    Returns
    -------
    dict with:
      "rolling"      DataFrame, one row per window end: end_date, n (==
                     window), mean, ci_lo, ci_hi (block-bootstrap 95% CI).
                     Empty if len(values_bps) < window.
      "period_table" DataFrame, one row per `period` bucket present:
                     period (label), n, mean, ci_lo, ci_hi (nan CI if
                     n < block). None if `period` is None.
      "slope"        OLS slope of values_bps regressed on time in
                     `time_unit` units (via `time_axis`) since the first
                     observation (or sample 0, for "index").
      "slope_unit"   f"bps/{time_unit}", naming the unit of "slope",
                     "slope_ci" and "slope_mde".
      "slope_ci"     (lo, hi) 95% CI of the slope, from a moving-block
                     bootstrap OF THE RESIDUALS (resample the OLS residuals
                     in blocks, add back to the fitted line at each
                     observation's own time, refit -- this is what
                     preserves the time design while still resampling
                     under the series' own short-range autocorrelation).
                     (nan, nan) if len(values_bps) < block.
      "slope_se"     bootstrap standard deviation of the slope draws (the
                     SE the MDE below is built from).
      "slope_mde"    EDGE_TREND_SLOPE_MDE_Z * slope_se -- "the slope MDE"
                     §5.4 requires alongside the slope itself.
      "half_split"   dict: n_first, n_second, mean_first, mean_second,
                     diff (= mean_second - mean_first), diff_ci (95% CI of
                     the difference, from independent block-bootstrap draws
                     of each half using the SAME seeded RNG stream, so the
                     draw is deterministic and reproducible).
      "last_window"  dict (mean/ci_lo/ci_hi/end_date/n) for the most recent
                     `window` observations, i.e. "rolling"'s last row --
                     surfaced separately because the judgment sentence
                     needs it. None if "rolling" is empty.
      "regime_table" DataFrame (regime label, lo, hi, n, mean, ci_lo,
                     ci_hi) if `regime_dates` given, else None.
      "judgment"     the fixed judgment sentence (§5.7, verbatim rule):
                     "拡大" if the slope CI excludes zero and is positive
                     AND the last window's CI is positive; "縮小" if the
                     slope CI excludes zero and is negative OR the last
                     window's CI is negative; else "判定不能(標本不足)".
                     A "判定不能" is never to be read as "安定" (§5.7).
                     (The judgment always reads the slope in whatever
                     `time_unit` was requested -- its sign is unit-free.)
      "params"       dict echoing window/block/time_unit/time_axis/period/
                     n_boot/seed/n for the RESULTS.md footnote.
    """
    if time_unit not in _EDGE_TREND_TIME_UNITS:
        raise ValueError(f"time_unit must be one of {_EDGE_TREND_TIME_UNITS}, got {time_unit!r}")
    if time_axis not in ("calendar", "index"):
        raise ValueError(f"time_axis must be 'calendar' or 'index', got {time_axis!r}")
    if time_axis == "index" and time_unit != "sample":
        raise ValueError("time_axis='index' requires time_unit='sample'")
    if time_axis == "calendar" and time_unit == "sample":
        raise ValueError(
            "time_axis='calendar' has no 'sample' unit -- use time_axis='index' for that"
        )
    if period is not None and period not in _EDGE_TREND_PERIODS:
        raise ValueError(f"period must be one of {_EDGE_TREND_PERIODS} or None, got {period!r}")
    rolling_step = int(rolling_step)
    if rolling_step < 1:
        raise ValueError(f"rolling_step must be >= 1, got {rolling_step}")

    ds = pd.to_datetime(pd.Series(list(dates)).reset_index(drop=True))
    x = np.asarray(values_bps, dtype=float)
    if len(ds) != len(x):
        raise ValueError(
            f"dates and values_bps must have the same length, got {len(ds)} and {len(x)}"
        )
    n = len(x)
    order = np.argsort(ds.to_numpy(), kind="stable")
    ds = ds.iloc[order].reset_index(drop=True)
    x = x[order]

    # ---- 1. rolling window mean + CI (§5.2) --------------------------------
    rolling_rows = []
    ends = list(range(window - 1, n, rolling_step))
    if n >= window and ends[-1] != n - 1:
        ends.append(n - 1)
    for end in ends:
        seg = x[end - window + 1 : end + 1]
        means = _moving_block_bootstrap_means(seg, block, n_boot, seed)
        if np.isnan(means).all():
            lo = hi = float("nan")
        else:
            lo, hi = np.percentile(means, [2.5, 97.5])
        rolling_rows.append({
            "end_date": ds.iloc[end], "n": window,
            "mean": float(seg.mean()), "ci_lo": float(lo), "ci_hi": float(hi),
        })
    rolling = pd.DataFrame(rolling_rows, columns=["end_date", "n", "mean", "ci_lo", "ci_hi"])
    last_window = rolling.iloc[-1].to_dict() if len(rolling) else None

    # ---- 2. period table (§5.3) --------------------------------------------
    period_table = None
    if period is not None:
        if period == "year":
            keys = ds.dt.strftime("%Y")
        elif period == "month":
            keys = ds.dt.strftime("%Y-%m")
        elif period == "week":
            keys = ds.dt.strftime("%G-W%V")
        elif period == "day":
            keys = ds.dt.strftime("%Y-%m-%d")
        else:  # "hour"
            keys = ds.dt.strftime("%Y-%m-%d %H:00")
        keys = keys.to_numpy()
        period_rows = []
        for key in dict.fromkeys(keys.tolist()):  # first-seen order == chronological
            seg = x[keys == key]
            lo, hi = block_bootstrap_ci(seg, block=block, n_boot=n_boot, seed=seed)
            period_rows.append({"period": key, "n": int(len(seg)),
                                "mean": float(seg.mean()), "ci_lo": lo, "ci_hi": hi})
        period_table = pd.DataFrame(
            period_rows, columns=["period", "n", "mean", "ci_lo", "ci_hi"])

    # ---- 3. slope + CI + MDE (§5.4), unit per time_unit/time_axis ---------
    if time_axis == "index":
        t = np.arange(n, dtype=float)
    else:
        seconds = (ds - ds.iloc[0]).dt.total_seconds().to_numpy()
        t = seconds / _EDGE_TREND_UNIT_SECONDS[time_unit]

    if n >= max(2, block):
        slope0, intercept0 = np.polyfit(t, x, 1)
        resid = x - (slope0 * t + intercept0)
        rng = np.random.default_rng(seed)
        n_blocks = int(np.ceil(n / block))
        offsets = np.arange(block)
        slopes_boot = np.empty(n_boot)
        for b in range(n_boot):
            starts = rng.integers(0, n, size=n_blocks)
            idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n] % n
            x_boot = slope0 * t + intercept0 + resid[idx]
            s, _ = np.polyfit(t, x_boot, 1)
            slopes_boot[b] = s
        slope_ci = tuple(float(v) for v in np.percentile(slopes_boot, [2.5, 97.5]))
        slope_se = float(np.std(slopes_boot, ddof=1))
    else:
        slope0 = float(np.nan) if n < 2 else float(np.polyfit(t, x, 1)[0])
        slope_ci = (float("nan"), float("nan"))
        slope_se = float("nan")
    slope_mde = EDGE_TREND_SLOPE_MDE_Z * slope_se

    # ---- 4. first half vs second half (§5.5) -------------------------------
    mid = n // 2
    first, second = x[:mid], x[mid:]
    means_first = _moving_block_bootstrap_means(first, block, n_boot, seed)
    means_second = _moving_block_bootstrap_means(second, block, n_boot, seed + 1)
    diff_boot = means_second - means_first
    if np.isnan(diff_boot).all():
        diff_ci = (float("nan"), float("nan"))
    else:
        diff_ci = tuple(float(v) for v in np.nanpercentile(diff_boot, [2.5, 97.5]))
    half_split = {
        "n_first": int(len(first)), "n_second": int(len(second)),
        "mean_first": float(first.mean()) if len(first) else float("nan"),
        "mean_second": float(second.mean()) if len(second) else float("nan"),
        "diff": (float(second.mean()) - float(first.mean()))
                if len(first) and len(second) else float("nan"),
        "diff_ci": diff_ci,
    }

    # ---- 5. regime table (§5.6, boundaries supplied by the caller only) ---
    regime_table = None
    if regime_dates:
        bounds = sorted(pd.Timestamp(d) for d in regime_dates)
        edges = [ds.iloc[0]] + bounds + [ds.iloc[-1] + pd.Timedelta(days=1)]
        rows = []
        for i in range(len(edges) - 1):
            lo_d, hi_d = edges[i], edges[i + 1]
            mask = (ds >= lo_d) & (ds < hi_d)
            seg = x[mask.to_numpy()]
            ci_lo, ci_hi = block_bootstrap_ci(seg, block=block, n_boot=n_boot, seed=seed) \
                if len(seg) else (float("nan"), float("nan"))
            label_hi = (hi_d - pd.Timedelta(days=1)).date() if i < len(edges) - 2 else ds.iloc[-1].date()
            rows.append({
                "regime": f"{lo_d.date()}..{label_hi}", "lo": lo_d, "hi": hi_d,
                "n": int(len(seg)), "mean": float(seg.mean()) if len(seg) else float("nan"),
                "ci_lo": ci_lo, "ci_hi": ci_hi,
            })
        regime_table = pd.DataFrame(rows)

    # ---- 6. judgment sentence (§5.7, fixed wording) ------------------------
    slope_lo, slope_hi = slope_ci
    last_lo = last_window["ci_lo"] if last_window is not None else float("nan")
    last_hi = last_window["ci_hi"] if last_window is not None else float("nan")
    expand = np.isfinite(slope_lo) and slope_lo > 0 and np.isfinite(last_lo) and last_lo > 0
    shrink = (np.isfinite(slope_hi) and slope_hi < 0) or (np.isfinite(last_hi) and last_hi < 0)
    if expand:
        judgment = "拡大"
    elif shrink:
        judgment = "縮小"
    else:
        judgment = "判定不能(標本不足)"

    return {
        "rolling": rolling,
        "period_table": period_table,
        "slope": float(slope0),
        "slope_unit": f"bps/{time_unit}",
        "slope_ci": slope_ci,
        "slope_se": slope_se,
        "slope_mde": slope_mde,
        "half_split": half_split,
        "last_window": last_window,
        "regime_table": regime_table,
        "judgment": judgment,
        "params": {"window": window, "block": block, "time_unit": time_unit,
                   "time_axis": time_axis, "period": period, "n_boot": n_boot,
                   "seed": seed, "n": n, "rolling_step": rolling_step},
    }


# ---------------------------------------------------------------------------
# condition analysis (standard sub-indicator, PHASE2_TEMPLATES.md §6)
# ---------------------------------------------------------------------------

# Same alpha=0.05 two-sided / power=0.8 constant the slope MDE uses
# (§5.4 / §6.2 quote it rounded to 2.8016). Aliased rather than re-derived so
# every MDE in the phase-2 templates is literally the same number.
STATE_DIFF_MDE_Z = EDGE_TREND_SLOPE_MDE_Z

STATE_VERDICT_CANDIDATE = "候補"
STATE_VERDICT_UNDECIDABLE = "判定不能"
STATE_VERDICT_NO_DIFF = "差なし"


def _state_masks(labels: pd.Series) -> dict[str, np.ndarray]:
    """Ordered {label: boolean mask} for one state variable.

    Missing labels (NaN/None/empty string) are dropped -- an observation for
    which a state variable is not defined (e.g. the first 20 days, which have
    no 20-sample realized vol yet) simply does not take part in that
    variable's table. Labels are sorted as strings, so a caller that wants a
    particular order names its levels accordingly ("1_低" / "2_中" / "3_高").
    """
    values = labels.to_numpy(dtype=object)
    present = ~pd.isna(labels).to_numpy() & np.array(
        [str(v) != "" for v in values], dtype=bool)
    as_str = np.array([str(v) for v in values], dtype=object)
    out: dict[str, np.ndarray] = {}
    for lab in sorted({str(v) for v, ok in zip(as_str, present) if ok}):
        out[lab] = present & (as_str == lab)
    return out


def _block_slices(n: int, block: int) -> list[np.ndarray]:
    """Consecutive index blocks [0..block), [block..2*block), ... covering n.

    The last block is short when `block` does not divide `n`. Used by the
    joint permutation null: permuting the ORDER of these blocks reshuffles
    the values against the (fixed) state labels while leaving runs of length
    `block` intact, so short-range autocorrelation survives into the null.
    """
    return [np.arange(s, min(s + block, n)) for s in range(0, n, block)]


def state_split(
    values_bps,
    states: dict,
    *,
    block: int,
    n_boot: int,
    seed: int,
    cost_bps=None,
) -> dict:
    """The standard "condition analysis" sub-indicator (PHASE2_TEMPLATES.md §6).

    Describes WHERE a per-observation edge is larger or smaller, over state
    variables the caller pre-registered, without ever letting that answer
    change the unconditional main test (§6.4). Everything is descriptive:
    this function labels each state difference 候補 / 判定不能 / 差なし by the
    fixed §6.3 rule and nothing else.

    `block`, `n_boot` and `seed` have no defaults for the same reason as in
    `edge_trend`: they are pre-registered design choices, so every call must
    name them and every RESULTS.md must state the values used.

    Parameters
    ----------
    values_bps : 1-D per-observation values in bps, IN TIME ORDER (the block
        bootstrap and the block permutation both read the ordering as time).
        The primary quantity — every difference, CI, MDE, the permutation
        null and every verdict are computed on THIS series; `cost_bps` only
        adds descriptive cost-net columns to the per-state table.
    states : {variable name: array-like of per-observation labels}. Each
        array must have the same length as `values_bps`. A NaN/None/empty
        label drops that observation from that variable only (other variables
        still use it). Variables keep the dict's order in the output; levels
        within a variable are ordered by their label sorted as a string.
    block : moving-block length in observations, used BOTH for the bootstrap
        CIs and for the permutation null's blocks (§6.3 reuses §5's block).
    n_boot : resamples per CI and draws for the permutation null (§5/§6:
        2,000).
    seed : RNG seed. Every draw this call makes is derived from it, so a
        rerun is bit-identical.
    cost_bps : optional per-observation cost in bps, same length. When given,
        the per-state table also carries the cost mean and the cost-net
        (values - cost) mean and CI. Differences and verdicts stay on
        `values_bps`.

    Returns
    -------
    dict with:
      "state_table"  DataFrame, one row per (variable, state): variable,
                     state, n, mean, ci_lo, ci_hi and -- only when `cost_bps`
                     is given -- cost_mean, net_mean, net_ci_lo, net_ci_hi.
                     CIs are block-bootstrap percentile intervals of that
                     state's own observations (nan when n < block).
      "diff_table"   DataFrame, one row per (variable, state_a, state_b) with
                     a < b in the level order above: variable, state_a,
                     state_b, n_a, n_b, mean_a, mean_b, diff (= mean_a -
                     mean_b), ci_lo, ci_hi (95% CI of the difference from the
                     two states' independent bootstrap draws), se (their
                     standard deviation), mde (STATE_DIFF_MDE_Z * se) and
                     verdict.
      "null_p95"     the 95th percentile of the joint permutation null of the
                     LARGEST absolute difference across ALL variables and all
                     state pairs (§6.3): each of `n_boot` draws permutes the
                     ORDER of the value series' `block`-long blocks once,
                     recomputes every state mean of every variable from that
                     one permuted world, takes the largest absolute pairwise
                     difference anywhere, and the 95th percentile of those
                     maxima is the bar. nan if no variable has >= 2 levels.
      "null_max_abs_diff" the raw 1-D array of those `n_boot` maxima, for a
                     caller that wants to plot or re-percentile them.
      "verdict"      {(variable, state_a, state_b): verdict}, the same
                     verdicts as `diff_table`, keyed for lookup. Per §6.3/§6.2:
                     候補 when |diff| exceeds `null_p95` AND the difference's
                     CI excludes zero; otherwise 判定不能 when the MDE is not
                     finite or exceeds |diff| (the difference is not VISIBLE
                     at this n -- never to be read as "no difference"); else
                     差なし.
      "params"       dict echoing block/n_boot/seed/n/n_variables/
                     n_comparisons/has_cost for the RESULTS.md footnote.
    """
    x = np.asarray(values_bps, dtype=float)
    n = len(x)
    if n == 0:
        raise ValueError("values_bps must not be empty")
    if not states:
        raise ValueError("states must not be empty")
    net = None
    cost = None
    if cost_bps is not None:
        cost = np.asarray(cost_bps, dtype=float)
        if len(cost) != n:
            raise ValueError(
                f"cost_bps must have the same length as values_bps, got {len(cost)} and {n}"
            )
        net = x - cost

    masks_by_var: dict[str, dict[str, np.ndarray]] = {}
    for var, labels in states.items():
        ser = pd.Series(list(labels)).reset_index(drop=True)
        if len(ser) != n:
            raise ValueError(
                f"states[{var!r}] must have the same length as values_bps, "
                f"got {len(ser)} and {n}"
            )
        masks_by_var[var] = _state_masks(ser)

    # ---- 1. per-state table + the bootstrap draws the differences reuse ----
    draw_seed = seed
    state_rows: list[dict] = []
    boot: dict[tuple[str, str], np.ndarray] = {}
    for var, masks in masks_by_var.items():
        for lab, mask in masks.items():
            seg = x[mask]
            draws = _moving_block_bootstrap_means(seg, block, n_boot, draw_seed)
            draw_seed += 1
            boot[(var, lab)] = draws
            lo, hi = ((float("nan"), float("nan")) if np.isnan(draws).all()
                      else tuple(float(v) for v in np.percentile(draws, [2.5, 97.5])))
            row = {"variable": var, "state": lab, "n": int(mask.sum()),
                   "mean": float(seg.mean()) if len(seg) else float("nan"),
                   "ci_lo": lo, "ci_hi": hi}
            if net is not None:
                nseg = net[mask]
                ndraws = _moving_block_bootstrap_means(nseg, block, n_boot, draw_seed)
                draw_seed += 1
                nlo, nhi = ((float("nan"), float("nan")) if np.isnan(ndraws).all()
                            else tuple(float(v) for v in np.percentile(ndraws, [2.5, 97.5])))
                row.update({
                    "cost_mean": float(cost[mask].mean()) if len(nseg) else float("nan"),
                    "net_mean": float(nseg.mean()) if len(nseg) else float("nan"),
                    "net_ci_lo": nlo, "net_ci_hi": nhi,
                })
            state_rows.append(row)
    state_cols = ["variable", "state", "n", "mean", "ci_lo", "ci_hi"]
    if net is not None:
        state_cols += ["cost_mean", "net_mean", "net_ci_lo", "net_ci_hi"]
    state_table = pd.DataFrame(state_rows, columns=state_cols)

    # ---- 2. joint permutation null over EVERY variable and pair (§6.3) -----
    # The largest absolute pairwise difference within a variable is just the
    # RANGE of its state means, so one bincount per variable per draw covers
    # every pair at once.
    codes_counts = []
    for var, masks in masks_by_var.items():
        if len(masks) < 2:
            continue
        codes = np.full(n, -1, dtype=np.int64)
        for k, mask in enumerate(masks.values()):
            codes[mask] = k
        valid = codes >= 0
        counts = np.bincount(codes[valid], minlength=len(masks)).astype(float)
        codes_counts.append((codes[valid], valid, counts, len(masks)))

    if codes_counts:
        rng = np.random.default_rng(seed)
        blocks = _block_slices(n, block)
        n_blocks = len(blocks)
        maxima = np.empty(n_boot)
        for b in range(n_boot):
            order = rng.permutation(n_blocks)
            perm = np.concatenate([blocks[i] for i in order])
            xp = x[perm]
            best = 0.0
            for codes_v, valid, counts, k in codes_counts:
                sums = np.bincount(codes_v, weights=xp[valid], minlength=k)
                means = sums / counts
                rng_span = float(np.nanmax(means) - np.nanmin(means))
                if rng_span > best:
                    best = rng_span
            maxima[b] = best
        null_p95 = float(np.percentile(maxima, 95))
    else:
        maxima = np.full(n_boot, float("nan"))
        null_p95 = float("nan")

    # ---- 3. pairwise differences, MDE and the fixed verdict (§6.2/§6.3) ----
    diff_rows: list[dict] = []
    verdicts: dict[tuple[str, str, str], str] = {}
    means_by_state = {(r["variable"], r["state"]): r["mean"] for r in state_rows}
    n_by_state = {(r["variable"], r["state"]): r["n"] for r in state_rows}
    for var, masks in masks_by_var.items():
        labs = list(masks.keys())
        for i in range(len(labs)):
            for j in range(i + 1, len(labs)):
                a, b_lab = labs[i], labs[j]
                diff = means_by_state[(var, a)] - means_by_state[(var, b_lab)]
                dboot = boot[(var, a)] - boot[(var, b_lab)]
                if np.isnan(dboot).all():
                    ci_lo = ci_hi = se = float("nan")
                else:
                    ci_lo, ci_hi = (float(v) for v in np.percentile(dboot, [2.5, 97.5]))
                    se = float(np.std(dboot, ddof=1))
                mde = STATE_DIFF_MDE_Z * se
                ci_excludes_zero = (
                    np.isfinite(ci_lo) and np.isfinite(ci_hi) and (ci_lo > 0 or ci_hi < 0)
                )
                if (np.isfinite(null_p95) and np.isfinite(diff)
                        and abs(diff) > null_p95 and ci_excludes_zero):
                    verdict = STATE_VERDICT_CANDIDATE
                elif (not np.isfinite(mde)) or (not np.isfinite(diff)) or mde > abs(diff):
                    verdict = STATE_VERDICT_UNDECIDABLE
                else:
                    verdict = STATE_VERDICT_NO_DIFF
                verdicts[(var, a, b_lab)] = verdict
                diff_rows.append({
                    "variable": var, "state_a": a, "state_b": b_lab,
                    "n_a": n_by_state[(var, a)], "n_b": n_by_state[(var, b_lab)],
                    "mean_a": means_by_state[(var, a)],
                    "mean_b": means_by_state[(var, b_lab)],
                    "diff": diff, "ci_lo": ci_lo, "ci_hi": ci_hi,
                    "se": se, "mde": mde, "null_p95": null_p95,
                    "verdict": verdict,
                })
    diff_table = pd.DataFrame(diff_rows, columns=[
        "variable", "state_a", "state_b", "n_a", "n_b", "mean_a", "mean_b",
        "diff", "ci_lo", "ci_hi", "se", "mde", "null_p95", "verdict"])

    return {
        "state_table": state_table,
        "diff_table": diff_table,
        "null_p95": null_p95,
        "null_max_abs_diff": maxima,
        "verdict": verdicts,
        "params": {"block": block, "n_boot": n_boot, "seed": seed, "n": n,
                   "n_variables": len(masks_by_var), "n_comparisons": len(diff_rows),
                   "has_cost": cost is not None},
    }
