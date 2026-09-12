#!/usr/bin/env python3
"""PIPELINE known-answer test — daily execution (the known-answer-test
requirement from the 2026-09-05 owner-agreed phase-2 design).

Not an auditor test: checks that the actual daily overnight-premium
computation path used by ON1/ONR research recovers a planted effect and
reports a null as null on synthetic data with known traps.

Computation path: this script IMPORTS (does not reimplement)
`overnight_returns` and `drop_glitches` from src/bot/research/overnight.py
-- the same pipeline-tested implementation scripts/research_overnight_onr.py
(the frozen ONR PREREG) itself imports, so both the research script and
this QA pipeline run the identical leg definition and glitch filter (ON1's
own daily judgment scripts use the same close->next-open leg definition).
Running the real leg definition + the real glitch filter on synthetic data
with known planted values is the actual test.

Construction (see generate()):
  - a synthetic INDEX FUTURE (clean, "指数水準" analogue) and a synthetic
    ETF that TRACKS it bar-for-bar (same overnight/intraday shocks), 3,000
    business days, GARCH(1,1) vol-clustered intraday vol.
  - overnight premium (close(t) -> open(t+1)) is planted at +Y bps/day,
    Y in {0, 2, 5}, ONLY on days whose GARCH intraday-vol lands in the
    trailing (in-sample) HIGH VOL TERCILE — a planted regime concentration
    (the phase-2 daily units include a regime-conditioned hypothesis
    class; low/mid tercile carry zero planted drift by construction).
  - the ETF (only) carries two data-quality traps real jpx_etf_daily.json
    known_defects have both been observed: a 10:1 UNADJUSTED split (a real
    corporate action, not an error, but indistinguishable from a glitch by
    a naive |log-return|>10% filter) and 5 isolated single-day "bad print"
    days (OHLC collapses to ~1-2% for exactly one day, non-propagating).

Outputs -> backtest_data/qa_pipeline_daily_<date>/:
  daily_idxf_Y{0,2,5}bps.csv / daily_etf_Y{0,2,5}bps.csv
  RESULTS.md, planted_values_sealed.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research import overnight as onr  # noqa: E402  (the actual ONR computation path)

SEED = 20260905
N_DAYS = 3000
Y_VALUES = (0.0, 2.0, 5.0)
PRICE0 = 3000.0

BASE_INTRADAY_SIGMA = 0.010          # ~1.0% daily open->close vol
OVERNIGHT_NOISE_SIGMA_BPS = 15.0
GARCH_ALPHA, GARCH_BETA = 0.08, 0.90

SPLIT_DAY_FRAC = 0.55                # unadjusted 10:1 split partway through
SPLIT_RATIO = 10.0
N_BAD_PRINT_DAYS = 5
BAD_PRINT_MIN_FACTOR, BAD_PRINT_MAX_FACTOR = 0.005, 0.02

GLITCH_THRESHOLD = onr.GLITCH_ABS_LOG_RET_DEFAULT  # reuse the shared default threshold (0.10)

# --- dividend-adjustment known-answer case: fully deterministic (no RNG) so
# the 3 adjusted-return values can be hand-derived independently of the
# function under test, ahead of running it. The 3 planted ex-dates are
# produced from RECORD dates via onr.ex_dates_from_record_dates() (not
# hardcoded row indices), so the record-date -> effective-ex-date chain
# itself is exercised, not just overnight_returns()'s dividend adjustment. ---
DIV_N_DAYS = 12
DIV_PRICE0_CLOSE = 1000.0
DIV_CLOSE_STEP = 5.0
DIV_OPEN0 = 999.5
DIV_NORMAL_DRIFT = 1.0005            # continuation open(t+1) = close(t) * this
# record dates (calendar dates, as real JPX-style "ex_date" columns actually
# are): 2 weekend record dates + 1 mid-week trading-day record date, all
# post-cutover (2024) so each steps back exactly 1 trading day (T+2).
DIV_RECORD_DATES = ("2024-01-06", "2024-01-10", "2024-01-14")
DIV_AMOUNTS = (12.5, 8.0, 20.25)     # per record-date amounts, same order

# Hand-derived helper cases (record date -> effective ex-date), independent
# of the synthetic tape above, exercising ex_dates_from_record_dates() across
# both the T+3 (pre-2019-07-16) and T+2 (post) settlement regimes and both a
# weekend and a trading-day record date. Verified against JPX's settlement-
# cycle shortening (2019-07-16, T+3 -> T+2).
DIV_HELPER_HAND_CASES = (
    ("2018-03-31", "2018-03-28"),  # Sat record -> eff Fri 2018-03-30 -> T+3 -> -2td
    ("2020-03-31", "2020-03-30"),  # Tue record (a trading day) -> T+2 -> -1td
    ("2013-02-10", "2013-02-06"),  # Sun record -> eff Fri 2013-02-08 -> T+3 -> -2td
    ("2019-08-10", "2019-08-08"),  # Sat record -> eff Fri 2019-08-09 -> T+2 -> -1td
)


def garch_sigma_and_shocks(rng: np.random.Generator, n: int, base_sigma: float,
                            alpha: float = GARCH_ALPHA, beta: float = GARCH_BETA
                            ) -> tuple[np.ndarray, np.ndarray]:
    omega = base_sigma ** 2 * (1.0 - alpha - beta)
    z = rng.standard_normal(n)
    sigma2 = np.empty(n)
    r = np.empty(n)
    sigma2[0] = base_sigma ** 2
    r[0] = z[0] * np.sqrt(sigma2[0])
    for t in range(1, n):
        sigma2[t] = omega + alpha * r[t - 1] ** 2 + beta * sigma2[t - 1]
        r[t] = z[t] * np.sqrt(sigma2[t])
    return np.sqrt(sigma2), r


def build_base(seed: int, n_days: int) -> dict:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2005-01-03", periods=n_days, tz=None)
    sigma_intraday, intraday_shocks = garch_sigma_and_shocks(rng, n_days, BASE_INTRADAY_SIGMA)

    tercile = pd.qcut(sigma_intraday, 3, labels=["low", "mid", "high"])
    tercile = np.asarray(tercile)

    overnight_noise_sigma = (OVERNIGHT_NOISE_SIGMA_BPS / 1e4) * (sigma_intraday / sigma_intraday.mean())
    overnight_z = rng.standard_normal(n_days)

    split_day = int(n_days * SPLIT_DAY_FRAC)
    forbidden = np.zeros(n_days, dtype=bool)
    forbidden[max(0, split_day - 2):split_day + 3] = True
    forbidden[0] = True
    forbidden[-1] = True
    candidates = np.flatnonzero(~forbidden)
    bad_days = np.sort(rng.choice(candidates, size=N_BAD_PRINT_DAYS, replace=False)).tolist()

    return {"rng": rng, "dates": dates, "sigma_intraday": sigma_intraday,
            "intraday_shocks": intraday_shocks, "tercile": tercile,
            "overnight_noise_sigma": overnight_noise_sigma, "overnight_z": overnight_z,
            "split_day": split_day, "bad_days": bad_days}


def build_series(base: dict, y_bps: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (open, close, overnight_ret) for the CLEAN (index-future) series
    at planted overnight premium y_bps (high-vol-tercile-only)."""
    n = len(base["dates"])
    tercile = base["tercile"]
    overnight_ret = np.where(tercile == "high", y_bps / 1e4, 0.0) \
        + base["overnight_z"] * base["overnight_noise_sigma"]
    intraday = base["intraday_shocks"]

    open_ = np.empty(n)
    close = np.empty(n)
    open_[0] = PRICE0
    close[0] = open_[0] * np.exp(intraday[0])
    for t in range(1, n):
        open_[t] = close[t - 1] * np.exp(overnight_ret[t - 1])
        close[t] = open_[t] * np.exp(intraday[t])
    return open_, close, overnight_ret


def to_ohlc_df(base: dict, open_: np.ndarray, close: np.ndarray, rng: np.random.Generator) -> pd.DataFrame:
    n = len(open_)
    hi_j = rng.uniform(0.0005, 0.004, n)
    lo_j = rng.uniform(0.0005, 0.004, n)
    high = np.maximum(open_, close) * (1 + hi_j)
    low = np.minimum(open_, close) * (1 - lo_j)
    volume = rng.lognormal(mean=10.0, sigma=0.6, size=n)
    return pd.DataFrame({
        "date": pd.DatetimeIndex(base["dates"]),  # real Timestamp, as
                                                    # research_overnight_onr.load_ohlc's
                                                    # parse_dates=["date"] would produce
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })


def apply_etf_defects(df: pd.DataFrame, base: dict) -> pd.DataFrame:
    """Unadjusted 10:1 split from split_day onward + N isolated non-propagating
    bad-print days, applied to a COPY so the CLEAN series (used to compute
    the next day's open) is never touched."""
    out = df.copy()
    s = base["split_day"]
    for col in ("open", "high", "low", "close"):
        out.loc[s:, col] = out.loc[s:, col] / SPLIT_RATIO
    rng = base["rng"]
    for j in base["bad_days"]:
        f = rng.uniform(BAD_PRINT_MIN_FACTOR, BAD_PRINT_MAX_FACTOR)
        for col in ("open", "high", "low", "close"):
            out.loc[j, col] = out.loc[j, col] * f
        out.loc[j, "volume"] = out.loc[j, "volume"] * 0.05
    return out


def mean_se_t_bps(x: np.ndarray) -> tuple[float, float, float, int]:
    n = len(x)
    if n < 2:
        return float("nan"), float("nan"), float("nan"), n
    m = float(x.mean()) * 1e4
    se = float(x.std(ddof=1) / np.sqrt(n)) * 1e4
    t = m / se if se else float("nan")
    return m, se, t, n


def _build_dividend_series() -> tuple[pd.DataFrame, pd.DataFrame, list[int], list[float]]:
    """Deterministic ETF tape + dividends table for the dividend-adjustment
    known-answer case. The 3 planted ex-dividend dates are derived from
    DIV_RECORD_DATES via onr.ex_dates_from_record_dates() (using the tape's
    own trading days as the calendar) rather than hardcoded row indices, so
    the record-date -> effective-ex-date chain is exercised end to end.

    Returns (etf_df, dividends_df, ex_row_indices, hand_open_at_ex) where
    hand_open_at_ex are the RAW (ex-dividend-depressed) opens the market
    actually prints at the planted ex-dividend rows -- the quantity the
    hand derivation adds `amount` back onto."""
    n = DIV_N_DAYS
    dates = pd.bdate_range("2024-01-02", periods=n)
    ex_dates = onr.ex_dates_from_record_dates(DIV_RECORD_DATES, dates)
    ex_row_indices = [int(dates.get_indexer([d])[0]) for d in ex_dates]
    assert all(i >= 1 for i in ex_row_indices), "ex-date landed on the first row (no close(t))"

    close = np.array([DIV_PRICE0_CLOSE + DIV_CLOSE_STEP * t for t in range(n)], dtype=float)
    cont_open = np.empty(n)
    cont_open[0] = DIV_OPEN0
    for t in range(1, n):
        cont_open[t] = close[t - 1] * DIV_NORMAL_DRIFT
    open_ = cont_open.copy()
    for j, amount in zip(ex_row_indices, DIV_AMOUNTS):
        open_[j] = cont_open[j] - amount  # market opens lower by exactly the distribution
    high = np.maximum(open_, close) * 1.0001
    low = np.minimum(open_, close) * 0.9999
    volume = np.full(n, 1e6)
    etf_df = pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low,
                            "close": close, "volume": volume})
    div_df = pd.DataFrame({"ex_date_effective": ex_dates, "amount": list(DIV_AMOUNTS)})
    hand_open_at_ex = [float(open_[j]) for j in ex_row_indices]
    return etf_df, div_df, ex_row_indices, hand_open_at_ex


def _hand_derive_helper_cases() -> list[dict]:
    """Independently checks onr.ex_dates_from_record_dates() against the 4
    hand-derived (record date -> effective ex-date) cases in
    DIV_HELPER_HAND_CASES, using a wide synthetic Mon-Fri trading calendar
    (no holidays -- not needed for these 4 dates)."""
    calendar = pd.bdate_range("2012-01-01", "2021-01-01")
    rows = []
    for record_date, expected_ex_date in DIV_HELPER_HAND_CASES:
        got = onr.ex_dates_from_record_dates([record_date], calendar)[0]
        rows.append({
            "record_date": record_date, "expected_ex_date": expected_ex_date,
            "got_ex_date": str(got.date()), "matches": str(got.date()) == expected_ex_date,
        })
    return rows


def run_dividend_known_answer(out_dir: Path) -> dict:
    """Dividend-adjustment known-answer case: plants 3 ex-dividend days
    (derived from RECORD dates through onr.ex_dates_from_record_dates()) on
    a fully deterministic ETF tape (see _build_dividend_series),
    hand-derives the 3 dividend-adjusted overnight returns BEFORE calling
    src/bot/research/overnight.py's overnight_returns(df, dividends=...),
    then asserts the function reproduces them exactly and that the
    unadjusted (no-dividends) mean is lower by exactly the analytically
    expected amount. Also independently checks ex_dates_from_record_dates()
    itself against 4 hand-derived record-date cases (see
    _hand_derive_helper_cases).
    """
    etf_df, div_df, ex_row_indices, hand_open_at_ex = _build_dividend_series()
    etf_df.to_csv(out_dir / "dividend_case_etf.csv", index=False,
                  date_format="%Y-%m-%d")
    div_df.to_csv(out_dir / "dividend_case_dividends.csv", index=False,
                  date_format="%Y-%m-%d")

    helper_cases = _hand_derive_helper_cases()

    close = etf_df["close"].to_numpy()
    hand_rows = []
    for j, amount, raw_open in zip(ex_row_indices, DIV_AMOUNTS, hand_open_at_ex):
        t = j - 1  # leg dated t=j-1 (close date); t+1=j is the ex-dividend date
        hand_r = math.log((raw_open + amount) / close[t])
        hand_rows.append({"row_index_t_plus_1": j, "date_t": str(etf_df["date"].iloc[t].date()),
                           "date_ex": str(etf_df["date"].iloc[j].date()), "amount": amount,
                           "raw_open_t1": raw_open, "close_t": float(close[t]),
                           "hand_r": hand_r})

    raw = onr.overnight_returns(etf_df)
    adj = onr.overnight_returns(etf_df, dividends=div_df)

    max_abs_diff = 0.0
    for row in hand_rows:
        got = float(adj.loc[adj["date"] == pd.Timestamp(row["date_t"]), "r"].iloc[0])
        row["function_r"] = got
        row["abs_diff"] = abs(got - row["hand_r"])
        max_abs_diff = max(max_abs_diff, row["abs_diff"])
    exact_match = max_abs_diff < 1e-12

    expected_mean_diff = sum(
        math.log((row["raw_open_t1"] + row["amount"]) / row["raw_open_t1"]) for row in hand_rows
    ) / len(raw)
    actual_mean_diff = float(adj["r"].mean() - raw["r"].mean())
    mean_diff_matches = abs(actual_mean_diff - expected_mean_diff) < 1e-12

    helper_all_match = all(row["matches"] for row in helper_cases)

    findings = []
    if not exact_match:
        findings.append(
            f"dividend case: overnight_returns(df, dividends=...) did NOT reproduce the hand "
            f"derivation exactly (max abs diff {max_abs_diff}) -- dividend adjustment path "
            "in src/bot/research/overnight.py is suspect."
        )
    if not mean_diff_matches:
        findings.append(
            f"dividend case: unadjusted-vs-adjusted mean difference ({actual_mean_diff}) does "
            f"not match the analytically expected planted amount effect ({expected_mean_diff})."
        )
    if not helper_all_match:
        bad = [row for row in helper_cases if not row["matches"]]
        findings.append(
            f"dividend case: ex_dates_from_record_dates() disagreed with {len(bad)} hand-derived "
            f"record-date case(s): {bad} -- the record-date/settlement-cycle chain in "
            "src/bot/research/overnight.py is suspect."
        )

    derivation_lines = [
        "# Hand derivation — dividend-adjustment known-answer case", "",
        "## Part 1: record date -> effective ex-date (ex_dates_from_record_dates)", "",
        "Independently checked against 4 hand-derived cases spanning both the T+3",
        "(pre 2019-07-16) and T+2 (post) JPX settlement regimes, and both a weekend and a",
        "trading-day record date:", "",
        "| record date | expected ex-date | got ex-date | matches |",
        "|---|---|---|---|",
    ]
    for row in helper_cases:
        derivation_lines.append(
            f"| {row['record_date']} | {row['expected_ex_date']} | {row['got_ex_date']} | "
            f"{row['matches']} |"
        )
    derivation_lines += [
        "", f"all 4 hand-derived record-date cases match: {helper_all_match}", "",
        "## Part 2: dividend-adjusted overnight return (overnight_returns dividends=...)", "",
        "The 3 ex-dates below are the ex_date_effective values Part 1's function produced",
        f"from the record dates {list(DIV_RECORD_DATES)} against the synthetic tape's own",
        "trading-day calendar -- NOT hardcoded row indices.", "",
        "Computed independently of `overnight_returns`, before running it, using",
        "`r_adj = ln((raw_open(t+1) + amount) / close(t))` where `raw_open(t+1)` is the",
        "as-printed (ex-dividend-depressed) open and `amount` is the planted distribution.",
        "", "| t+1 row | date(t) | date(ex) | amount | raw_open(t+1) | close(t) | hand r |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in hand_rows:
        derivation_lines.append(
            f"| {row['row_index_t_plus_1']} | {row['date_t']} | {row['date_ex']} | "
            f"{row['amount']} | {row['raw_open_t1']:.6f} | {row['close_t']:.6f} | "
            f"{row['hand_r']:.10f} |"
        )
    derivation_lines += [
        "", f"Expected mean(adjusted r) - mean(raw r) over all {len(raw)} legs "
            f"= sum(ln((raw_open+amount)/raw_open)) / n = {expected_mean_diff:.10f}",
        "", "## Result of running overnight_returns(df, dividends=...)", "",
        "| t+1 row | hand r | function r | abs diff |", "|---|---|---|---|",
    ]
    for row in hand_rows:
        derivation_lines.append(
            f"| {row['row_index_t_plus_1']} | {row['hand_r']:.10f} | "
            f"{row['function_r']:.10f} | {row['abs_diff']:.2e} |"
        )
    derivation_lines += [
        "", f"actual mean(adjusted r) - mean(raw r) = {actual_mean_diff:.10f}",
        f"exact_match (max abs diff < 1e-12): {exact_match}",
        f"mean_diff_matches (< 1e-12): {mean_diff_matches}",
    ]
    (out_dir / "HAND_DERIVATION_dividend.md").write_text(
        "\n".join(derivation_lines) + "\n", encoding="utf-8"
    )

    return {
        "hand_rows": hand_rows,
        "expected_mean_diff": expected_mean_diff,
        "actual_mean_diff": actual_mean_diff,
        "exact_match": exact_match,
        "mean_diff_matches": mean_diff_matches,
        "max_abs_diff": max_abs_diff,
        "helper_cases": helper_cases,
        "helper_all_match": helper_all_match,
        "findings": findings,
        "files": {"etf": "dividend_case_etf.csv", "dividends": "dividend_case_dividends.csv",
                  "hand_derivation": "HAND_DERIVATION_dividend.md"},
    }


RETKIND_PLANTED_SIMPLE_BPS = 5.0  # exact simple-return drift planted below


def run_return_kind_known_answer(out_dir: Path) -> dict:
    """Return-kind known-answer case: a single deterministic leg planted at
    EXACTLY `RETKIND_PLANTED_SIMPLE_BPS` (5bps) of SIMPLE overnight return
    (open(t+1) = close(t) * (1 + 5bps)). Hand-derives, before calling
    overnight_returns(df, kind=...):
      - kind="simple" must recover exactly the planted 5.0bps.
      - kind="log" (the default) recovers ln(1 + 5bps), which differs from
        the simple return by r_simple**2/2 to first order
        (ln(1+x) = x - x**2/2 + O(x**3)).
    """
    close0 = 1000.0
    planted_simple = RETKIND_PLANTED_SIMPLE_BPS / 1e4
    open1 = close0 * (1.0 + planted_simple)
    df = pd.DataFrame({
        "date": pd.bdate_range("2024-06-03", periods=2),
        "open": [close0, open1], "close": [close0, open1],
    })

    r_simple = float(onr.overnight_returns(df, kind="simple")["r"].iloc[0])
    r_log = float(onr.overnight_returns(df)["r"].iloc[0])  # default kind="log"

    hand_r_simple = (open1 / close0) - 1.0
    hand_r_log = math.log(open1 / close0)
    simple_matches_planted = abs(r_simple * 1e4 - RETKIND_PLANTED_SIMPLE_BPS) < 1e-9
    simple_exact_match = abs(r_simple - hand_r_simple) < 1e-15
    log_exact_match = abs(r_log - hand_r_log) < 1e-15

    diff = r_simple - r_log
    first_order = r_simple ** 2 / 2.0
    # remainder is O(x**3); at x~5bps that's ~1e4x smaller than the x**2/2
    # term itself, so a loose relative tolerance still discriminates a
    # broken formula (e.g. off by a factor) from the expected residual.
    first_order_matches = abs(diff - first_order) / first_order < 0.01

    findings = []
    if not simple_matches_planted:
        findings.append(
            f"return-kind case: kind='simple' recovered {r_simple * 1e4}bps, not the planted "
            f"{RETKIND_PLANTED_SIMPLE_BPS}bps exactly."
        )
    if not simple_exact_match or not log_exact_match:
        findings.append(
            "return-kind case: overnight_returns(df, kind=...) did not reproduce the hand "
            f"derivation (simple diff={abs(r_simple - hand_r_simple)}, "
            f"log diff={abs(r_log - hand_r_log)})."
        )
    if not first_order_matches:
        findings.append(
            f"return-kind case: log-vs-simple diff ({diff}) does not match the expected "
            f"first-order r**2/2 approximation ({first_order}) within tolerance -- kind='log' "
            "and kind='simple' may not be using the same (dividend-adjusted) open(t+1)."
        )

    lines = [
        "# Hand derivation — return-kind (log vs simple) known-answer case", "",
        f"Planted EXACTLY {RETKIND_PLANTED_SIMPLE_BPS}bps of simple overnight return: "
        f"open(t+1) = close(t) * (1 + {planted_simple}).", "",
        f"close(t) = {close0}, open(t+1) = {open1}", "",
        f"hand r_simple = open(t+1)/close(t) - 1 = {hand_r_simple:.10f} "
        f"({hand_r_simple * 1e4:.6f}bps)",
        f"hand r_log    = ln(open(t+1)/close(t)) = {hand_r_log:.10f}",
        f"function r_simple = {r_simple:.10f}  (matches hand: {simple_exact_match})",
        f"function r_log    = {r_log:.10f}  (matches hand: {log_exact_match})",
        f"simple recovers planted {RETKIND_PLANTED_SIMPLE_BPS}bps exactly: {simple_matches_planted}",
        "", f"r_simple - r_log = {diff:.12f}",
        f"first-order approx r_simple**2/2 = {first_order:.12f}",
        f"relative error = {abs(diff - first_order) / first_order:.6f} "
        f"(first_order_matches <1%: {first_order_matches})",
    ]
    (out_dir / "HAND_DERIVATION_return_kind.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "planted_simple_bps": RETKIND_PLANTED_SIMPLE_BPS,
        "r_simple": r_simple, "r_log": r_log,
        "simple_matches_planted": simple_matches_planted,
        "simple_exact_match": simple_exact_match, "log_exact_match": log_exact_match,
        "diff": diff, "first_order_approx": first_order,
        "first_order_matches": first_order_matches,
        "findings": findings,
        "files": {"hand_derivation": "HAND_DERIVATION_return_kind.md"},
    }


def generate(out_dir: Path, seed: int = SEED, n_days: int = N_DAYS) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = build_base(seed, n_days)
    tercile = base["tercile"]

    per_y = {}
    files = {}
    findings: list[str] = []
    dropped_dates_by_y = {}

    for y in Y_VALUES:
        open_, close, _ = build_series(base, y)
        idx_df = to_ohlc_df(base, open_, close, base["rng"])
        etf_df = apply_etf_defects(idx_df, base)

        # --- the actual ONR computation path, run on the clean index series ---
        onr_df = onr.overnight_returns(idx_df)
        r = onr_df["r"].to_numpy()
        tercile_aligned = tercile[: len(r)]

        regime_stats = {}
        for regime in ("low", "mid", "high"):
            sub = r[tercile_aligned == regime]
            m, se, t, n = mean_se_t_bps(sub)
            mde = 2.8 * se
            regime_stats[regime] = {
                "n": n, "mean_bps": round(m, 4), "se_bps": round(se, 4),
                "t_stat": round(t, 4), "mde_bps": round(mde, 4),
            }

        high = regime_stats["high"]
        within_mde = abs(high["mean_bps"] - y) < high["mde_bps"]
        regime_stats["high"]["within_mde"] = within_mde
        if not within_mde:
            findings.append(
                f"Y={y}bps: high-vol-tercile recovered mean {high['mean_bps']}bps is outside "
                f"the MDE ({high['mde_bps']}bps) of planted {y}bps (research_overnight_onr.py's "
                "overnight_returns/mean_t path)."
            )
        for regime in ("low", "mid"):
            if abs(regime_stats[regime]["t_stat"]) >= 1.96:
                findings.append(
                    f"Y={y}bps: {regime}-vol tercile t-stat={regime_stats[regime]['t_stat']} is "
                    "significant -- the planted effect leaked outside the high-vol tercile it was "
                    "concentrated in, or the tercile split itself is confounded."
                )
        if y == 0.0 and abs(high["t_stat"]) >= 1.96:
            findings.append(f"Y=0bps: high-vol-tercile t-stat={high['t_stat']} is significant -- "
                             "pipeline reported a null as non-null (false positive).")

        # --- ETF: same effect, but contaminated; drop_glitches is the ONLY
        # cleaning step research_overnight_onr.py itself applies before ①-④.
        onr_etf_df = onr.overnight_returns(etf_df)
        cleaned, n_dropped = onr.drop_glitches(onr_etf_df)
        dropped_mask = ~onr_etf_df["date"].isin(cleaned["date"])
        dropped_dates = sorted(onr_etf_df.loc[dropped_mask, "date"].dt.strftime("%Y-%m-%d").tolist())
        dropped_dates_by_y[y] = dropped_dates

        cleaned_tercile = tercile_aligned[np.isin(onr_etf_df["date"], cleaned["date"])] \
            if len(cleaned) else np.array([])
        cleaned_r = cleaned["r"].to_numpy()
        m_c, se_c, t_c, n_c = mean_se_t_bps(cleaned_r[cleaned_tercile == "high"]) if n_c_check(cleaned_tercile) else (float("nan"),) * 3 + (0,)

        per_y[y] = {
            "planted_overnight_premium_bps": y,
            "regime": regime_stats,
            "etf_glitches_dropped": n_dropped,
            "etf_glitches_dropped_dates": dropped_dates,
            "etf_high_tercile_after_cleaning_mean_bps": round(m_c, 4) if m_c == m_c else None,
            "etf_high_tercile_after_cleaning_n": int(n_c),
        }

        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        yi = int(y)
        idx_fname = f"daily_idxf_Y{yi}bps_{date_str}.csv"
        etf_fname = f"daily_etf_Y{yi}bps_{date_str}.csv"
        idx_out = idx_df.copy(); idx_out["date"] = idx_out["date"].dt.strftime("%Y-%m-%d")
        etf_out = etf_df.copy(); etf_out["date"] = etf_out["date"].dt.strftime("%Y-%m-%d")
        idx_out.to_csv(out_dir / idx_fname, index=False)
        etf_out.to_csv(out_dir / etf_fname, index=False)
        files[y] = {"index_future": idx_fname, "etf": etf_fname}

    split_date = base["dates"][base["split_day"] - 1].strftime("%Y-%m-%d")
    bad_dates_boundaries = sorted(set(
        [base["dates"][j - 1].strftime("%Y-%m-%d") for j in base["bad_days"]]
        + [base["dates"][j].strftime("%Y-%m-%d") for j in base["bad_days"]]
    ))
    expected_dropped = sorted(set(bad_dates_boundaries + [split_date]))
    for y in Y_VALUES:
        missing = sorted(set(expected_dropped) - set(dropped_dates_by_y[y]))
        if missing:
            findings.append(
                f"Y={y}bps: scripts/research_overnight_onr.py's drop_glitches() FAILED to catch "
                f"{len(missing)} known defect date(s) {missing} (threshold={GLITCH_THRESHOLD}) -- "
                "these would silently contaminate the judgment."
            )
        extra = sorted(set(dropped_dates_by_y[y]) - set(expected_dropped))
        if len(extra) > 2:  # a small amount of incidental noise-driven drops is expected at n=3000
            findings.append(
                f"Y={y}bps: drop_glitches() dropped {len(extra)} dates beyond the planted defects "
                f"(threshold={GLITCH_THRESHOLD}) -- check for false-positive glitch exclusion."
            )
    findings.append(
        f"The unadjusted 10:1 split at {split_date} and the 5 genuine bad-print days are "
        "INDISTINGUISHABLE to drop_glitches() (both are just |log-return|>10%): a real corporate "
        "action gets silently dropped exactly like a data error. This reproduces, on synthetic "
        "data, the same failure mode schema/jpx_etf_daily.json's known_defects records for the "
        "real 1306.T 2015-01-05 split (once misclassified as a bad print by an earlier audit pass)."
    )

    # --- dividend-adjustment known-answer case: deterministic, hand-derived
    # ahead of running overnight_returns(df, dividends=...) (see the function
    # docstring for the derivation this reproduces).
    dividend_case = run_dividend_known_answer(out_dir)
    findings.extend(dividend_case["findings"])

    # --- return-kind (log vs simple) known-answer case: single deterministic
    # leg, hand-derived ahead of calling overnight_returns(df, kind=...).
    return_kind_case = run_return_kind_known_answer(out_dir)
    findings.extend(return_kind_case["findings"])

    # --- scripts/data_quality.py, run for real, on a throwaway root with a
    # temporary schema (never touches the repo's real data/ or schema/).
    dq_report = run_data_quality_check(out_dir, files[Y_VALUES[-1]]["etf"], base)
    dq_hits = dq_report.get("extreme_return_count", 0)
    if dq_hits < len(expected_dropped):
        if dq_hits == 5:  # scripts/data_quality.py's MAX_EXAMPLES
            findings.append(
                f"scripts/data_quality.py:scan_file() reports extreme_return \"count\" as "
                "len(extreme_examples) where extreme_examples is capped at MAX_EXAMPLES=5 "
                "(same bug pattern in the crossed_book/maintenance_window/non_monotonic/"
                "zero_volume checks -- only duplicate_keys and gaps use an uncapped counter). "
                f"On this ETF tape with {len(expected_dropped)} genuine extreme-return "
                f"transitions, data_quality.py under-reports the count as exactly 5, silently "
                "hiding how widespread the problem actually is once a file has more than 5 hits."
            )
        else:
            findings.append(
                f"scripts/data_quality.py's extreme_return check only flagged {dq_hits} rows on "
                f"the ETF tape, fewer than the {len(expected_dropped)} known defect-adjacent "
                "transitions -- some traps are invisible to the intake-time quality scan."
            )

    sealed = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed, "n_days": n_days,
        "computation_path": "src/bot/research/overnight.py: overnight_returns, drop_glitches "
                             "(imported directly, not reimplemented; the same module "
                             "scripts/research_overnight_onr.py itself imports)",
        "glitch_threshold_abs_log_return": GLITCH_THRESHOLD,
        "y_values_bps": list(Y_VALUES),
        "split_day_index": base["split_day"], "split_date_flagged_leg": split_date,
        "split_ratio_unadjusted": SPLIT_RATIO,
        "bad_print_days_index": base["bad_days"],
        "bad_print_dates_flagged_legs": bad_dates_boundaries,
        "expected_dropped_dates": expected_dropped,
        "results_by_y": {str(y): per_y[y] for y in Y_VALUES},
        "data_quality_scan": dq_report,
        "dividend_case": {k: v for k, v in dividend_case.items() if k != "findings"},
        "return_kind_case": {k: v for k, v in return_kind_case.items() if k != "findings"},
        "files": {str(y): files[y] for y in Y_VALUES},
        "dividend_case_files": dividend_case["files"],
        "return_kind_case_files": return_kind_case["files"],
        "findings": findings,
    }
    with open(out_dir / "planted_values_sealed.json", "w", encoding="utf-8") as f:
        json.dump(sealed, f, ensure_ascii=False, sort_keys=True, indent=1, default=str)

    lines = ["# PIPELINE known-answer test — daily execution", "",
             f"Generated {sealed['generated_utc']}. seed={seed} n_days={n_days}. "
             f"Computation path: {sealed['computation_path']}.", "",
             "| Y planted (bps/day, high-vol tercile) | recovered mean | SE | t-stat | MDE | within MDE | "
             "low-tercile t | mid-tercile t |",
             "|---|---|---|---|---|---|---|---|"]
    for y in Y_VALUES:
        r_ = per_y[y]["regime"]
        lines.append(
            f"| {y} | {r_['high']['mean_bps']} | {r_['high']['se_bps']} | {r_['high']['t_stat']} | "
            f"{r_['high']['mde_bps']} | {'YES' if r_['high']['within_mde'] else 'NO'} | "
            f"{r_['low']['t_stat']} | {r_['mid']['t_stat']} |"
        )
    lines += ["", "## ETF traps (drop_glitches / data_quality.py)", "",
              f"planted defect dates expected to be flagged: {expected_dropped}", ""]
    for y in Y_VALUES:
        lines.append(f"- Y={y}: drop_glitches dropped {per_y[y]['etf_glitches_dropped']} date(s): "
                      f"{per_y[y]['etf_glitches_dropped_dates']}")
    lines += ["", f"data_quality.py extreme_return hits on the ETF tape: {dq_hits}", ""]
    lines += ["## Dividend-adjustment case (see HAND_DERIVATION_dividend.md)", "",
              f"planted record dates: {list(DIV_RECORD_DATES)}, amounts: {list(DIV_AMOUNTS)}",
              f"ex_dates_from_record_dates() hand-derived cases match "
              f"(4/4, both settlement regimes): {dividend_case['helper_all_match']}",
              f"max abs diff vs hand derivation: {dividend_case['max_abs_diff']:.2e} "
              f"(exact_match={dividend_case['exact_match']})",
              f"expected mean(adjusted)-mean(raw) diff: {dividend_case['expected_mean_diff']:.10f}",
              f"actual mean(adjusted)-mean(raw) diff: {dividend_case['actual_mean_diff']:.10f} "
              f"(mean_diff_matches={dividend_case['mean_diff_matches']})", ""]
    lines += ["## Return-kind case (log vs simple, see HAND_DERIVATION_return_kind.md)", "",
              f"planted simple overnight return: {return_kind_case['planted_simple_bps']}bps",
              f"kind='simple' recovered: {return_kind_case['r_simple']*1e4:.6f}bps "
              f"(matches planted exactly: {return_kind_case['simple_matches_planted']})",
              f"kind='log' recovered: {return_kind_case['r_log']:.10f}",
              f"r_simple - r_log = {return_kind_case['diff']:.12f}, "
              f"first-order r_simple**2/2 = {return_kind_case['first_order_approx']:.12f} "
              f"(matches within 1%: {return_kind_case['first_order_matches']})", ""]
    lines += ["## パイプラインの欠陥 (findings)", ""]
    lines += [f"- {finding}" for finding in findings] if findings else ["- none"]
    (out_dir / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"per_y": per_y, "findings": findings, "sealed": sealed,
            "dividend_case": dividend_case, "return_kind_case": return_kind_case,
            "out_dir": str(out_dir)}


def n_c_check(arr) -> bool:
    return len(arr) > 0 and (arr == "high").sum() > 1


def run_data_quality_check(qa_out_dir: Path, etf_fname: str, base: dict) -> dict:
    """Runs the REAL scripts/intake_ledger.py + scripts/data_quality.py
    against a throwaway root (never the repo's own data/ or schema/) that
    contains only a copy of the ETF tape plus a temporary schema entry."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        data_dir = tmp_root / "backtest_data" / "qa_pipeline_daily_temp"
        data_dir.mkdir(parents=True)
        shutil.copy(qa_out_dir / etf_fname, data_dir / etf_fname)
        schema_dir = tmp_root / "schema"
        schema_dir.mkdir(parents=True)
        schema = {
            "dataset": "qa_pipeline_daily_temp",
            "path_glob": ["backtest_data/qa_pipeline_daily_temp/*.csv"],
            "columns": {"date": {}, "open": {}, "high": {}, "low": {}, "close": {}, "volume": {}},
        }
        with open(schema_dir / "qa_pipeline_daily_temp.json", "w", encoding="utf-8") as f:
            json.dump(schema, f)

        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "intake_ledger.py"),
                         "--root", str(tmp_root), "--full"], check=True, capture_output=True)
        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "data_quality.py"),
                         "--root", str(tmp_root)], check=True, capture_output=True)
        quality_path = tmp_root / "data" / "QUALITY.json"
        report = json.loads(quality_path.read_text()) if quality_path.exists() else {}

    ds = report.get("datasets", {}).get("qa_pipeline_daily_temp", {})
    checks = ds.get("checks", {})
    return {
        "files_checked": ds.get("files_checked", 0),
        "checks_fired": list(checks.keys()),
        "extreme_return_count": checks.get("extreme_return", {}).get("count", 0),
        "extreme_return_examples": checks.get("extreme_return", {}).get("examples", []),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n-days", type=int, default=N_DAYS)
    ap.add_argument("--out-dir", type=str, default=None)
    args = ap.parse_args()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_pipeline_daily_{date_str}"
    result = generate(out_dir, seed=args.seed, n_days=args.n_days)
    print(f"wrote {out_dir}")
    for y, r in result["per_y"].items():
        h = r["regime"]["high"]
        print(f"Y={y}bps: high-tercile recovered={h['mean_bps']}bps t={h['t_stat']} "
              f"within_mde={h['within_mde']}")
    for finding in result["findings"]:
        print(f"FINDING: {finding}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
