#!/usr/bin/env python3
"""P2-02 iteration 0 -- main pre-registered test, development set only.

Implements docs/PHASE2/P2-02/PREREG.md (frozen 2026-09-06) EXACTLY, on the
development set (2009-01-05 .. 2021-04-12) reached via
``bot.research.sealed.load_unsealed(path, "P2-02")`` -- the sealed
(2021-04-13 onward, and everything from ``forward_start``) rows are never
read by this script.

Numbers only -- this script does NOT render a 採用/棄却/保留 verdict. It
writes the pre-registered indicators, the data check, and the MDE-vs-mean
gate as reported facts for the lead's later, separate judgment.

Run:
    PYTHONPATH=src python scripts/phase2/p2_02_run.py

Outputs -> backtest_data/phase2_runs/P2-02/iter0_20260906/:
    pairs_1343_dev.csv, pairs_1321_dev.csv, ex_dates_1343.csv,
    exclusion_summary.csv, train_val_summary.csv, controls_summary.csv,
    diagnostics_vol_tercile.csv, diagnostics_weekday.csv,
    diagnostics_month.csv, diagnostics_exdate.csv, main_summary.csv,
    sensitivity_fee.csv (historical non-SOR fee sensitivity, NOT used for
    judgment), RESULTS.md, RUN.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as _stats

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.constants import load_constants  # noqa: E402
from bot.research import overnight as onr  # noqa: E402
from bot.research.sealed import load_unsealed, md5_of  # noqa: E402

UNIT = "P2-02"
SEED = 20260906

DEV_START = pd.Timestamp("2009-01-05")
DEV_END = pd.Timestamp("2021-04-12")
TRAIN_END = pd.Timestamp("2017-12-31")
VAL_START = pd.Timestamp("2018-01-01")

BAD_PRINT_DEV_THRESHOLD = 0.30
BAD_PRINT_RECOVERY_THRESHOLD = 0.05
BAD_PRINT_MAX_RUN = 3
THIN_VOLUME_THRESHOLD = 5000  # units (口)
BLOCK = 20
N_BOOT = 2000
N_SHUFFLE = 1000
N_STRATA_BOOT = 1000
DIVIDEND_CHECK_MEDIAN_MAX_BPS = -50.0   # median r_night(x-1) must be <= this
DIVIDEND_CHECK_ADJ_TOLERANCE_BPS = 50.0  # |median adjusted| must be <= this

PRICE_1343 = "backtest_data/reit_onr_20260904/etf_1343_daily.csv"
DIV_1343 = "backtest_data/reit_onr_20260904/etf_1343_dividends.csv"
PRICE_1321 = "backtest_data/reit_onr_20260904/etf_1321_daily.csv"

OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-02" / "iter0_20260906"

Z_975 = float(_stats.norm.ppf(0.975))
Z_80 = float(_stats.norm.ppf(0.80))


# ---------------------------------------------------------------------------
# defect rules (PREREG "欠陥の扱い")
# ---------------------------------------------------------------------------

def detect_bad_print_runs(
    close: np.ndarray,
    open_: np.ndarray,
    dev_threshold: float = BAD_PRINT_DEV_THRESHOLD,
    recovery_threshold: float = BAD_PRINT_RECOVERY_THRESHOLD,
    max_run: int = BAD_PRINT_MAX_RUN,
) -> tuple[set[int], list[int]]:
    """Rule 1's bad-print run detector.

    A run of k (1<=k<=max_run) consecutive interior rows starting at i is a
    "bad print" run if, taking c0 = close[i-1] (the close of the row
    immediately before the run, held FIXED for every row in the run):
      * every row j in [i, i+k) has BOTH |open[j]-c0|/c0 > dev_threshold AND
        |close[j]-c0|/c0 > dev_threshold, and
      * the row immediately after the run (i+k) has
        |close[i+k]-c0|/c0 <= recovery_threshold.
    The first and last row of the series are never eligible to be run
    members (PREREG: "先頭・末尾行は判定対象外").
    A run whose natural (uncapped) length exceeds max_run is NOT flagged --
    it is treated as a real, if large, market move, per the PREREG's
    2024-08-05/06 example.

    Returns (flagged_row_indices, one_sided_row_indices) -- the latter are
    rows where exactly one of open/close deviates >dev_threshold from the
    run-context c0 (reported as info only, never excluded).
    """
    n = len(close)
    flagged: set[int] = set()
    one_sided: list[int] = []
    i = 1
    while i <= n - 2:
        c0 = close[i - 1]
        if c0 == 0 or np.isnan(c0):
            i += 1
            continue
        open_dev = abs(open_[i] - c0) / c0 > dev_threshold
        close_dev = abs(close[i] - c0) / c0 > dev_threshold
        if open_dev and close_dev:
            k = 1
            while (i + k) <= n - 2 and abs(open_[i + k] - c0) / c0 > dev_threshold \
                    and abs(close[i + k] - c0) / c0 > dev_threshold:
                k += 1
            post = i + k
            if k <= max_run and post <= n - 1 and abs(close[post] - c0) / c0 <= recovery_threshold:
                flagged.update(range(i, i + k))
            i += k
        elif open_dev != close_dev:
            one_sided.append(i)
            i += 1
        else:
            i += 1
    return flagged, one_sided


def detect_ghost_rows(open_: np.ndarray, high: np.ndarray, low: np.ndarray,
                       close: np.ndarray, volume: np.ndarray) -> set[int]:
    """Rule 2: phantom rows -- volume 0, OHLC identical, close == prev close.

    The row at index 0 can never be a ghost row (no previous close to
    compare against).
    """
    ghost = (volume == 0) & (open_ == high) & (high == low) & (low == close)
    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan
    ghost = ghost & (close == prev_close)
    return set(np.where(ghost)[0].tolist())


# ---------------------------------------------------------------------------
# tick-size cost model (config/constants.yaml, jpx_cash_equity.etf_tick_size_yen_by_price_band)
# ---------------------------------------------------------------------------

def _band_upper(key: str) -> float:
    # "up_to_1000_yen" -> 1000.0 ; "over_50000000_yen" -> inf
    if key.startswith("over_"):
        return float("inf")
    digits = key[len("up_to_"):-len("_yen")]
    return float(digits)


def build_tick_lookup(band_value: dict) -> list[tuple[float, float]]:
    """[(upper_bound_yen, tick_yen), ...] sorted ascending by upper bound."""
    pairs = [(_band_upper(k), float(v)) for k, v in band_value.items()]
    return sorted(pairs, key=lambda t: t[0])


def tick_for_price(price: float, bands: list[tuple[float, float]]) -> float:
    for upper, tick in bands:
        if price <= upper:
            return tick
    return bands[-1][1]


def conservative_cost_bps(close_t: np.ndarray, bands: list[tuple[float, float]]) -> np.ndarray:
    """Round-trip conservative cost: 2 ticks (1 per side) / close(t) * 1e4."""
    ticks = np.array([tick_for_price(c, bands) if c > 0 and not np.isnan(c) else np.nan
                       for c in close_t])
    return 2.0 * ticks / close_t * 1e4


# ---------------------------------------------------------------------------
# sensitivity ONLY (not used for judgment): the historical (pre-2026-05-18)
# non-SOR commission, applied retroactively at the pre-registered lot size
# (~100,000 yen notional). PREREG "費用の適用規則": the actual judgment uses
# the CURRENT regime (SOR, 0 yen commission) -- this is reported alongside
# as a sensitivity figure only, per the PREREG's explicit instruction to
# report the old-fee-schedule number for context, never to use it as a bar.
# ---------------------------------------------------------------------------

def old_fee_per_pair(close_t: np.ndarray, fee_bands: list[tuple[float, float]]
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(lot_units, notional_yen, fee_yen_per_execution, fee_bps_roundtrip).

    lot = round(100,000 / close_t) units, minimum 1 (PREREG's fixed assumed
    lot: "約定代金10万円相当(約50口)"). notional = lot * close_t decides
    which non_sor_fee_yen_by_notional band applies; fee_bps_roundtrip = 2 *
    fee_yen / notional * 1e4 (one commission per side, round trip).
    """
    lot = np.maximum(1, np.round(100_000.0 / close_t)).astype(float)
    notional = lot * close_t
    fee_yen = np.array([tick_for_price(nv, fee_bands) for nv in notional])
    fee_bps = 2.0 * fee_yen / notional * 1e4
    return lot, notional, fee_yen, fee_bps


# ---------------------------------------------------------------------------
# pair table construction (generic across 1343 / 1321)
# ---------------------------------------------------------------------------

def build_pair_table(df: pd.DataFrame, bands: list[tuple[float, float]]) -> pd.DataFrame:
    """One row per candidate overnight pair (t, t+1) over the WHOLE df
    (already restricted to the dev-set date window by the caller).

    Every exclusion is recorded as a flag column; nothing is dropped here --
    callers filter with the ``kept`` column so before/after counts can be
    reported without recomputation.
    """
    df = df.reset_index(drop=True)
    n = len(df)
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    volume = df["volume"].to_numpy(dtype=float)
    dates = pd.to_datetime(df["date"]).to_numpy()

    flagged, one_sided = detect_bad_print_runs(close, open_)
    ghost_idx = detect_ghost_rows(open_, high, low, close, volume)

    rows = []
    for t in range(n - 1):
        t1 = t + 1
        c_t = close[t]
        o_t1 = open_[t1]
        zero_blank = (c_t == 0 or np.isnan(c_t) or o_t1 == 0 or np.isnan(o_t1))
        bad_print = (t in flagged) or (t1 in flagged)
        rule1_excluded = bool(zero_blank or bad_print)
        ghost_excluded = bool((t in ghost_idx) or (t1 in ghost_idx))
        kept = (not rule1_excluded) and (not ghost_excluded)
        r_night_raw = (o_t1 / c_t - 1.0) if c_t > 0 else np.nan
        o_t = open_[t]
        r_day = (c_t / o_t - 1.0) if o_t > 0 else np.nan
        rows.append({
            "t_date": pd.Timestamp(dates[t]),
            "t1_date": pd.Timestamp(dates[t1]),
            "open_t": o_t,
            "close_t": c_t,
            "open_t1": o_t1,
            "volume_t": volume[t],
            "thin": bool(volume[t] < THIN_VOLUME_THRESHOLD),
            "zero_or_blank": bool(zero_blank),
            "bad_print": bool(bad_print),
            "ghost_excluded": bool(ghost_excluded),
            "rule1_excluded": rule1_excluded,
            "kept": kept,
            "r_night_raw_bps": r_night_raw * 1e4 if not np.isnan(r_night_raw) else np.nan,
            "r_day_bps": r_day * 1e4 if not np.isnan(r_day) else np.nan,
        })
    pairs = pd.DataFrame(rows)
    pairs["cost_conservative_bps"] = conservative_cost_bps(pairs["close_t"].to_numpy(), bands)
    pairs["cost_optimistic_bps"] = 0.0
    pairs["net_conservative_raw_bps"] = pairs["r_night_raw_bps"] - pairs["cost_conservative_bps"]
    pairs["net_optimistic_raw_bps"] = pairs["r_night_raw_bps"] - pairs["cost_optimistic_bps"]

    # Rolling 20-trading-day realized vol (trailing, computed over ALL rows
    # in df so a pair excluded by rule 1/2 doesn't distort the window seen
    # by its neighbors), assigned to the pair by its entry (t) date.
    log_ret = np.diff(np.log(np.clip(close, 1e-9, None)))
    log_ret = np.concatenate([[np.nan], log_ret])
    vol20 = pd.Series(log_ret).rolling(20, min_periods=20).std().shift(1)
    pairs["vol20_t"] = vol20.iloc[:-1].to_numpy()

    pairs["one_sided_info_count_total"] = len(one_sided)
    pairs["n_bad_print_rows_total"] = len(flagged)
    pairs["n_ghost_rows_total"] = len(ghost_idx)
    return pairs, flagged, one_sided, ghost_idx


# ---------------------------------------------------------------------------
# dividend adjustment (1343 only)
# ---------------------------------------------------------------------------

def add_dividend_adjustment(pairs: pd.DataFrame, price_df: pd.DataFrame,
                             div_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    trading_days = pd.to_datetime(price_df["date"]).tolist()
    record_dates = pd.to_datetime(div_df["ex_date"]).tolist()
    eff = onr.ex_dates_from_record_dates(record_dates, trading_days)
    div = div_df.copy()
    div["record_date"] = pd.to_datetime(div_df["ex_date"])
    div["ex_date_effective"] = pd.to_datetime(eff)
    div["is_non_trading_record_date"] = ~div["record_date"].isin(pd.to_datetime(price_df["date"]))

    amount_by_ex = div.set_index("ex_date_effective")["amount"]
    add = pairs["t1_date"].map(amount_by_ex).fillna(0.0)
    pairs = pairs.copy()
    pairs["dividend_add_yen"] = add.to_numpy()
    pairs["r_night_adj_bps"] = ((pairs["open_t1"] + pairs["dividend_add_yen"])
                                 / pairs["close_t"] - 1.0) * 1e4
    pairs["net_conservative_adj_bps"] = pairs["r_night_adj_bps"] - pairs["cost_conservative_bps"]
    pairs["net_optimistic_adj_bps"] = pairs["r_night_adj_bps"] - pairs["cost_optimistic_bps"]
    pairs["is_ex_date_pair"] = pairs["dividend_add_yen"] > 0
    return pairs, div


def dividend_data_check(pairs: pd.DataFrame, div: pd.DataFrame) -> dict:
    """PREREG data check: for each derived ex-date x, look at the pair whose
    t1_date == x (i.e. r_night(x-1)); a pair only enters this check if it
    survived rule 1 + rule 2 (``kept``)."""
    ex_pairs = pairs[pairs["t1_date"].isin(div["ex_date_effective"]) & pairs["kept"]]
    raw_bps = ex_pairs["r_night_raw_bps"].to_numpy()
    adj_bps = ex_pairs["r_night_adj_bps"].to_numpy()
    median_raw = float(np.median(raw_bps)) if len(raw_bps) else float("nan")
    median_adj = float(np.median(adj_bps)) if len(adj_bps) else float("nan")
    passes = (median_raw <= DIVIDEND_CHECK_MEDIAN_MAX_BPS) and \
             (abs(median_adj) <= DIVIDEND_CHECK_ADJ_TOLERANCE_BPS)
    return {
        "n_ex_date_pairs_checked": int(len(ex_pairs)),
        "median_raw_bps": median_raw,
        "median_adj_bps": median_adj,
        "passes": bool(passes),
        "use_correction": bool(passes),
    }


# ---------------------------------------------------------------------------
# inference helpers
# ---------------------------------------------------------------------------

def mean_ci_bootstrap(x: np.ndarray, seed: int) -> tuple[float, float, float]:
    mean = float(np.mean(x)) if len(x) else float("nan")
    lo, hi = onr.block_bootstrap_ci(x, block=BLOCK, n_boot=N_BOOT, seed=seed)
    return mean, lo, hi


def mde_bps(sigma_bps: float, n: int) -> float:
    if n <= 0:
        return float("nan")
    se = sigma_bps / np.sqrt(n)
    return (Z_975 + Z_80) * se


def sharpe_annualized(x: np.ndarray, dates: pd.Series) -> float:
    if len(x) < 2:
        return float("nan")
    mean = np.mean(x)
    std = np.std(x, ddof=1)
    if std == 0:
        return float("nan")
    span_days = (pd.Timestamp(dates.max()) - pd.Timestamp(dates.min())).days
    years = span_days / 365.25 if span_days > 0 else float("nan")
    periods_per_year = len(x) / years if years and years > 0 else float("nan")
    return float(mean / std * np.sqrt(periods_per_year))


def max_drawdown(pnl: np.ndarray) -> float:
    if len(pnl) == 0:
        return float("nan")
    cum = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cum)
    dd = running_max - cum
    return float(dd.max())


def block_bootstrap_max_dd_median(pnl: np.ndarray, block: int, n_boot: int, seed: int) -> float:
    x = np.asarray(pnl, dtype=float)
    n = len(x)
    if n < max(2, block):
        return float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    offsets = np.arange(block)
    dds = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n] % n
        dds[b] = max_drawdown(x[idx])
    return float(np.median(dds))


def stratified_bootstrap_mean_dist(x: np.ndarray, strata: np.ndarray, n_draws: int, seed: int) -> np.ndarray:
    """Control 2 (diagnostic): resample WITH replacement independently
    within each vol-tercile stratum (no time-block structure preserved --
    unlike the main indicator's block bootstrap) and return the resulting
    distribution of the overall mean. Purely descriptive: it shows how much
    the observed mean could vary under a "same vol-regime mix, random
    night" resampling scheme; it is not a null distribution and carries no
    accept/reject weight (PREREG control 2 is diagnostic only)."""
    rng = np.random.default_rng(seed)
    groups = [x[strata == g] for g in np.unique(strata) if len(x[strata == g])]
    out = np.empty(n_draws)
    for d in range(n_draws):
        pieces = [rng.choice(g, size=len(g), replace=True) for g in groups]
        out[d] = np.concatenate(pieces).mean() if pieces else np.nan
    return out


def sign_reversal_stats(r_night_bps: np.ndarray, cost_bps: np.ndarray) -> dict:
    """Control 3: flip the overnight position to short. Cost is a round-trip
    cost paid regardless of direction, so it is still subtracted."""
    reversed_net = -r_night_bps - cost_bps
    m = float(np.mean(reversed_net))
    lo, hi = onr.block_bootstrap_ci(reversed_net, block=BLOCK, n_boot=N_BOOT, seed=SEED + 3)
    return {"mean_bps": m, "ci_lo_bps": lo, "ci_hi_bps": hi, "n": int(len(reversed_net))}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def restrict_dev(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= DEV_START) & (df["date"] <= DEV_END)].reset_index(drop=True)
    return df


def exclusion_stage_stats(pairs: pd.DataFrame, col: str = "r_night_raw_bps") -> list[dict]:
    stages = []
    raw = pairs
    stages.append(("raw (before any exclusion)", raw))
    after_rule1 = pairs[~pairs["rule1_excluded"]]
    stages.append(("after rule 1 (formula-input 0/blank/bad-print)", after_rule1))
    after_both = pairs[pairs["kept"]]
    stages.append(("after rule 1 + rule 2 (phantom rows)", after_both))
    out = []
    for label, sub in stages:
        vals = sub[col].dropna().to_numpy()
        out.append({
            "stage": label,
            "n": int(len(vals)),
            "mean_bps": float(np.mean(vals)) if len(vals) else float("nan"),
            "std_bps": float(np.std(vals, ddof=1)) if len(vals) > 1 else float("nan"),
        })
    return out


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    constants = load_constants(REPO_ROOT)
    band_value = constants["jpx_cash_equity.etf_tick_size_yen_by_price_band"].value
    bands = build_tick_lookup(band_value)

    price_1343_full = load_unsealed(PRICE_1343, UNIT)
    div_1343_full = load_unsealed(DIV_1343, UNIT)
    price_1321_full = load_unsealed(PRICE_1321, UNIT)

    price_1343 = restrict_dev(price_1343_full)
    price_1321 = restrict_dev(price_1321_full)
    div_1343_full["ex_date"] = pd.to_datetime(div_1343_full["ex_date"])

    # ---------------- 1343 ----------------
    pairs_1343, flagged_1343, one_sided_1343, ghost_1343 = build_pair_table(price_1343, bands)
    pairs_1343, div_1343_eff = add_dividend_adjustment(pairs_1343, price_1343, div_1343_full)
    data_check = dividend_data_check(pairs_1343, div_1343_eff)
    use_correction = data_check["use_correction"]

    kept_1343 = pairs_1343[pairs_1343["kept"]].reset_index(drop=True)
    main_col = "r_night_adj_bps" if use_correction else "r_night_raw_bps"
    net_cons_col = "net_conservative_adj_bps" if use_correction else "net_conservative_raw_bps"
    net_opt_col = "net_optimistic_adj_bps" if use_correction else "net_optimistic_raw_bps"

    net_cons = kept_1343[net_cons_col].to_numpy()
    net_opt = kept_1343[net_opt_col].to_numpy()
    r_night = kept_1343[main_col].to_numpy()
    r_night_raw_only = kept_1343["r_night_raw_bps"].to_numpy()
    r_day = kept_1343["r_day_bps"].dropna().to_numpy()

    sigma_bps = float(np.std(net_cons, ddof=1))
    n_main = int(len(net_cons))
    se_bps = sigma_bps / np.sqrt(n_main)
    mde = mde_bps(sigma_bps, n_main)

    mean_cons, ci_lo_cons, ci_hi_cons = mean_ci_bootstrap(net_cons, seed=SEED)
    mean_opt, ci_lo_opt, ci_hi_opt = mean_ci_bootstrap(net_opt, seed=SEED + 1)

    hit_rate = float(np.mean(net_cons > 0))
    sharpe = sharpe_annualized(net_cons, kept_1343["t_date"])

    # night vs day (paired on the same t_date, both non-null)
    nd = kept_1343.dropna(subset=["r_day_bps"])
    diff = (nd[main_col] - nd["r_day_bps"]).to_numpy()
    diff_mean, diff_lo, diff_hi = mean_ci_bootstrap(diff, seed=SEED + 2)

    # ---- sensitivity ONLY: historical non-SOR fee retroactively applied ----
    fee_band_value = constants["jpx_cash_equity.non_sor_fee_yen_by_notional"].value
    fee_bands = build_tick_lookup(fee_band_value)
    close_arr = kept_1343["close_t"].to_numpy()
    lot_arr, notional_arr, fee_yen_arr, fee_bps_arr = old_fee_per_pair(close_arr, fee_bands)
    cost_cons_plus_oldfee = kept_1343["cost_conservative_bps"].to_numpy() + fee_bps_arr
    net_cons_plus_oldfee = r_night - cost_cons_plus_oldfee
    mean_oldfee, ci_lo_oldfee, ci_hi_oldfee = mean_ci_bootstrap(net_cons_plus_oldfee, seed=SEED + 9)
    # single-1-unit-lot illustrative case (PREREG: "1口だけなら290bps/片側"),
    # using the dev-set's own representative (median) close price.
    median_close_1343 = float(np.median(close_arr))
    fee_1unit_bps_one_side = float(55.0 / median_close_1343 * 1e4)
    sensitivity_fee_df = pd.DataFrame({
        "t_date": kept_1343["t_date"],
        "t1_date": kept_1343["t1_date"],
        "close_t": close_arr,
        "lot_units": lot_arr,
        "notional_yen": notional_arr,
        "fee_yen_per_execution": fee_yen_arr,
        "fee_bps_roundtrip": fee_bps_arr,
        "cost_conservative_bps": kept_1343["cost_conservative_bps"].to_numpy(),
        "cost_conservative_plus_oldfee_bps": cost_cons_plus_oldfee,
        "r_night_used_bps": r_night,
        "net_conservative_plus_oldfee_bps": net_cons_plus_oldfee,
    })

    # ---- drawdown bar ----
    pnl_yen = kept_1343["close_t"].to_numpy() * (net_cons / 1e4)
    dd = max_drawdown(pnl_yen)
    span_days = (kept_1343["t_date"].max() - kept_1343["t_date"].min()).days
    years = span_days / 365.25
    periods_per_year = n_main / years
    annualized_mean_profit_yen = float(np.mean(pnl_yen) * periods_per_year)
    dd_bar_multiple = 3.0
    dd_ok = bool(dd <= dd_bar_multiple * annualized_mean_profit_yen) if annualized_mean_profit_yen > 0 else False
    dd_median_boot = block_bootstrap_max_dd_median(pnl_yen, BLOCK, N_BOOT, SEED + 4)

    # ---- 1321 comparison (same procedure, no dividend file used) ----
    pairs_1321, flagged_1321, one_sided_1321, ghost_1321 = build_pair_table(price_1321, bands)
    kept_1321 = pairs_1321[pairs_1321["kept"]].reset_index(drop=True)
    net_cons_1321 = kept_1321["net_conservative_raw_bps"].to_numpy()
    mean_1321, ci_lo_1321, ci_hi_1321 = mean_ci_bootstrap(net_cons_1321, seed=SEED + 5)
    n_1321 = int(len(net_cons_1321))
    sign_match = bool(np.sign(mean_cons) == np.sign(mean_1321)) if mean_cons != 0 and mean_1321 != 0 else False
    both_ci_positive = bool(ci_lo_cons > 0 and ci_lo_1321 > 0)
    futures_like = bool(sign_match and both_ci_positive)

    # ---- controls ----
    null_means = onr.sign_shuffle_null(net_cons, n=N_SHUFFLE, seed=SEED + 6)
    null_95pct = float(np.percentile(null_means, 95))
    null_percentile_of_observed = float(np.mean(null_means <= mean_cons) * 100.0)

    vol20 = kept_1343["vol20_t"].to_numpy()
    valid_vol = ~np.isnan(vol20)
    terciles = np.full(len(vol20), -1, dtype=int)
    if valid_vol.sum() >= 3:
        qs = np.nanquantile(vol20, [1 / 3, 2 / 3])
        terciles[valid_vol] = np.digitize(vol20[valid_vol], qs)
    strata_dist = stratified_bootstrap_mean_dist(
        net_cons[valid_vol], terciles[valid_vol], N_STRATA_BOOT, SEED + 7
    ) if valid_vol.sum() >= 3 else np.array([])

    reversal = sign_reversal_stats(
        kept_1343[main_col].to_numpy(), kept_1343["cost_conservative_bps"].to_numpy()
    )

    # ---- diagnostics (descriptive only) ----
    diag = kept_1343.copy()
    diag["net_cons_bps"] = net_cons
    diag["vol_tercile"] = np.where(valid_vol, terciles, -1)
    vol_tercile_diag = (
        diag[diag["vol_tercile"] >= 0]
        .groupby("vol_tercile")["net_cons_bps"]
        .agg(["mean", "std", "count"]).reset_index()
    )
    diag["weekday"] = diag["t_date"].dt.dayofweek
    weekday_diag = diag.groupby("weekday")["net_cons_bps"].agg(["mean", "std", "count"]).reset_index()
    diag["month"] = diag["t_date"].dt.month
    month_diag = diag.groupby("month")["net_cons_bps"].agg(["mean", "std", "count"]).reset_index()

    eff_ex_dates = pd.to_datetime(div_1343_eff["ex_date_effective"])
    ex_set = set(eff_ex_dates)
    ex_prev = set(eff_ex_dates - pd.tseries.offsets.BDay(1))
    ex_next = set(eff_ex_dates + pd.tseries.offsets.BDay(1))

    def _ex_label(t1_date):
        if t1_date in ex_set:
            return "ex_date"
        if t1_date in ex_prev:
            return "ex_date-1"
        if t1_date in ex_next:
            return "ex_date+1"
        return "other"

    diag["ex_date_window"] = diag["t1_date"].map(_ex_label)
    exdate_diag = diag.groupby("ex_date_window")["net_cons_bps"].agg(["mean", "std", "count"]).reset_index()

    # ---- thin-trading sensitivity (info only; judgment uses the full set) ----
    thin_mask = kept_1343["thin"].to_numpy()
    n_thin_total = int(thin_mask.sum())
    n_thin_overlap_ghost = int(pairs_1343.loc[pairs_1343["thin"] & pairs_1343["ghost_excluded"]].shape[0])
    n_thin_true = int(pairs_1343.loc[pairs_1343["thin"] & (~pairs_1343["ghost_excluded"])].shape[0])
    mean_excl_thin = float(np.mean(net_cons[~thin_mask])) if (~thin_mask).sum() else float("nan")

    # ---- train / val split ----
    def split_stats(sub_df: pd.DataFrame) -> dict:
        vals = sub_df[net_cons_col].to_numpy()
        m, lo, hi = mean_ci_bootstrap(vals, seed=SEED + 8)
        return {"n": int(len(vals)), "mean_bps": m, "ci_lo_bps": lo, "ci_hi_bps": hi}

    train_df = kept_1343[kept_1343["t_date"] <= TRAIN_END]
    val_df = kept_1343[kept_1343["t_date"] >= VAL_START]
    train_stats = split_stats(train_df)
    val_stats = split_stats(val_df)

    # ---- exclusion (before/after) summary, both instruments ----
    excl_1343 = exclusion_stage_stats(pairs_1343)
    excl_1321 = exclusion_stage_stats(pairs_1321)

    # =========================== write CSVs ===========================
    pairs_1343.to_csv(OUT_DIR / "pairs_1343_dev.csv", index=False)
    pairs_1321.to_csv(OUT_DIR / "pairs_1321_dev.csv", index=False)
    div_1343_eff.to_csv(OUT_DIR / "ex_dates_1343.csv", index=False)

    pd.DataFrame([{"instrument": "1343", **s} for s in excl_1343] +
                 [{"instrument": "1321", **s} for s in excl_1321]).to_csv(
        OUT_DIR / "exclusion_summary.csv", index=False)

    pd.DataFrame([
        {"split": "train (2009-01-05..2017-12-31)", **train_stats},
        {"split": "val (2018-01-01..2021-04-12)", **val_stats},
    ]).to_csv(OUT_DIR / "train_val_summary.csv", index=False)

    pd.DataFrame([
        {"control": "1_sign_shuffle", "n_draws": N_SHUFFLE,
         "observed_mean_bps": mean_cons, "null_95pct_bps": null_95pct,
         "observed_percentile_in_null": null_percentile_of_observed},
        {"control": "2_vol_tercile_stratified_bootstrap_diagnostic",
         "n_draws": len(strata_dist),
         "dist_mean_bps": float(np.mean(strata_dist)) if len(strata_dist) else float("nan"),
         "dist_std_bps": float(np.std(strata_dist, ddof=1)) if len(strata_dist) > 1 else float("nan")},
        {"control": "3_sign_reversal", "n_draws": None,
         "mean_bps": reversal["mean_bps"], "ci_lo_bps": reversal["ci_lo_bps"],
         "ci_hi_bps": reversal["ci_hi_bps"], "n": reversal["n"]},
    ]).to_csv(OUT_DIR / "controls_summary.csv", index=False)

    vol_tercile_diag.to_csv(OUT_DIR / "diagnostics_vol_tercile.csv", index=False)
    weekday_diag.to_csv(OUT_DIR / "diagnostics_weekday.csv", index=False)
    month_diag.to_csv(OUT_DIR / "diagnostics_month.csv", index=False)
    exdate_diag.to_csv(OUT_DIR / "diagnostics_exdate.csv", index=False)

    sensitivity_fee_df.to_csv(OUT_DIR / "sensitivity_fee.csv", index=False)

    summary = {
        "n_raw_pairs_1343": int(len(pairs_1343)),
        "n_after_rule1_1343": int((~pairs_1343["rule1_excluded"]).sum()),
        "n_after_rule2_1343": int(pairs_1343["kept"].sum()),
        "n_bad_print_rows_1343": len(flagged_1343),
        "n_one_sided_info_rows_1343": len(one_sided_1343),
        "n_ghost_rows_1343": len(ghost_1343),
        "n_thin_total_1343": n_thin_total,
        "n_thin_overlap_ghost_1343": n_thin_overlap_ghost,
        "n_thin_true_1343": n_thin_true,
        "dividend_data_check_median_raw_bps": data_check["median_raw_bps"],
        "dividend_data_check_median_adj_bps": data_check["median_adj_bps"],
        "dividend_data_check_n_ex_pairs": data_check["n_ex_date_pairs_checked"],
        "dividend_data_check_passes": data_check["passes"],
        "dividend_correction_used": use_correction,
        "n_main": n_main,
        "sigma_bps": sigma_bps,
        "se_bps": se_bps,
        "mde_bps": mde,
        "mean_net_conservative_bps": mean_cons,
        "ci_lo_conservative_bps": ci_lo_cons,
        "ci_hi_conservative_bps": ci_hi_cons,
        "mean_net_optimistic_bps": mean_opt,
        "ci_lo_optimistic_bps": ci_lo_opt,
        "ci_hi_optimistic_bps": ci_hi_opt,
        "mean_excl_thin_bps": mean_excl_thin,
        "hit_rate": hit_rate,
        "sharpe_annualized": sharpe,
        "night_minus_day_mean_bps": diff_mean,
        "night_minus_day_ci_lo_bps": diff_lo,
        "night_minus_day_ci_hi_bps": diff_hi,
        "max_drawdown_yen_1unit": dd,
        "annualized_mean_net_profit_yen_1unit": annualized_mean_profit_yen,
        "drawdown_bar_multiple": dd_bar_multiple,
        "drawdown_ok": dd_ok,
        "max_drawdown_bootstrap_median_yen": dd_median_boot,
        "n_1321": n_1321,
        "mean_net_conservative_bps_1321": mean_1321,
        "ci_lo_bps_1321": ci_lo_1321,
        "ci_hi_bps_1321": ci_hi_1321,
        "sign_match_1343_vs_1321": sign_match,
        "both_ci_positive": both_ci_positive,
        "futures_like_criterion_met": futures_like,
        "gate_mean_net_conservative_vs_mde": bool(mean_cons >= mde),
        "sign_shuffle_null_95pct_bps": null_95pct,
        "sign_shuffle_observed_percentile": null_percentile_of_observed,
        "sign_reversal_mean_bps": reversal["mean_bps"],
        "sign_reversal_ci_lo_bps": reversal["ci_lo_bps"],
        "sign_reversal_ci_hi_bps": reversal["ci_hi_bps"],
        # ---- sensitivity ONLY (PREREG "費用の適用規則"): historical
        # non-SOR fee retroactively applied at the fixed ~100,000-yen lot.
        # NOT used for judgment; the judgment bar uses the current (0-yen
        # SOR) regime's mean_net_conservative_bps above, unchanged.
        "sensitivity_mean_net_conservative_plus_oldfee_bps": mean_oldfee,
        "sensitivity_ci_lo_conservative_plus_oldfee_bps": ci_lo_oldfee,
        "sensitivity_ci_hi_conservative_plus_oldfee_bps": ci_hi_oldfee,
        "sensitivity_median_close_1343_bps_denominator": median_close_1343,
        "sensitivity_fee_1unit_lot_bps_one_side": fee_1unit_bps_one_side,
    }
    pd.DataFrame([summary]).T.reset_index().rename(
        columns={"index": "metric", 0: "value"}).to_csv(OUT_DIR / "main_summary.csv", index=False)

    return {
        "summary": summary,
        "train_stats": train_stats,
        "val_stats": val_stats,
        "excl_1343": excl_1343,
        "excl_1321": excl_1321,
        "vol_tercile_diag": vol_tercile_diag,
        "weekday_diag": weekday_diag,
        "month_diag": month_diag,
        "exdate_diag": exdate_diag,
        "strata_dist": strata_dist,
        "n_div_rows": int(len(div_1343_eff)),
        "n_div_non_trading_record_dates": int(div_1343_eff["is_non_trading_record_date"].sum()),
    }


def _git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def write_run_json(result: dict) -> None:
    files_md5 = {}
    for p in (PRICE_1343, DIV_1343, PRICE_1321):
        full = REPO_ROOT / p
        files_md5[p] = md5_of(full)
    run_record = {
        "unit": UNIT,
        "iteration": 0,
        "seed": SEED,
        "git_rev": _git_rev(),
        "file_md5": files_md5,
        "n_per_step": {
            "1343_raw_pairs": result["summary"]["n_raw_pairs_1343"],
            "1343_after_rule1": result["summary"]["n_after_rule1_1343"],
            "1343_after_rule1_and_2": result["summary"]["n_after_rule2_1343"],
            "1321_raw_pairs": result["excl_1321"][0]["n"],
            "1321_after_rule1": result["excl_1321"][1]["n"],
            "1321_after_rule1_and_2": result["excl_1321"][2]["n"],
        },
        "generated_utc": pd.Timestamp.now("UTC").isoformat(),
    }
    (OUT_DIR / "RUN.json").write_text(
        json.dumps(run_record, indent=2, ensure_ascii=False), encoding="utf-8")


def _markdown_table(df: pd.DataFrame) -> str:
    """Minimal markdown table renderer (no tabulate dependency)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                cells.append(f"{v:.3f}" if not np.isnan(v) else "NaN")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_results_md(result: dict) -> None:
    s = result["summary"]

    def f(x, nd=2):
        if x is None:
            return "N/A"
        try:
            if isinstance(x, bool):
                return "はい" if x else "いいえ"
            if np.isnan(x):
                return "NaN"
        except TypeError:
            return str(x)
        return f"{x:.{nd}f}"

    lines = []
    lines.append("# P2-02 反復 0 主検定結果（開発セットのみ，封印データは一切参照していない）")
    lines.append("")
    lines.append("数値のみ。采用/棄却の判定は下さない。")
    lines.append("")
    lines.append("## 0. データ範囲")
    lines.append(f"- 開発セット: {DEV_START.date()} .. {DEV_END.date()}（`bot.research.sealed.load_unsealed` 経由、封印行は除外済み）")
    lines.append(f"- train: {DEV_START.date()} .. {TRAIN_END.date()} / val: {VAL_START.date()} .. {DEV_END.date()}")
    lines.append("")
    lines.append("## 1. 欠陥規則の適用（前後）")
    lines.append("")
    lines.append("### 1343")
    lines.append("| 段階 | n | 平均(bps) | σ(bps) |")
    lines.append("|---|---:|---:|---:|")
    for row in result["excl_1343"]:
        lines.append(f"| {row['stage']} | {row['n']} | {f(row['mean_bps'])} | {f(row['std_bps'])} |")
    lines.append("")
    lines.append(f"- 規則１でフラグされた誤プリント行数: {s['n_bad_print_rows_1343']}（片方だけ飛ぶ行の情報件数: {s['n_one_sided_info_rows_1343']}、除外はしない）")
    lines.append(f"- 幽霊行(規則２)件数: {s['n_ghost_rows_1343']}")
    lines.append(f"- 薄商い（出来高 < {THIN_VOLUME_THRESHOLD}）全体: {s['n_thin_total_1343']}、幽霊行と重なる: {s['n_thin_overlap_ghost_1343']}、真の薄商い: {s['n_thin_true_1343']}")
    lines.append(f"- 薄商いを除いた主指標(参考): {f(s['mean_excl_thin_bps'])} bps（判定は全体を使用）")
    lines.append("")
    lines.append("### 1321（同手順）")
    lines.append("| 段階 | n | 平均(bps) | σ(bps) |")
    lines.append("|---|---:|---:|---:|")
    for row in result["excl_1321"]:
        lines.append(f"| {row['stage']} | {row['n']} | {f(row['mean_bps'])} | {f(row['std_bps'])} |")
    lines.append("")
    lines.append("## 2. 権利落ち日の導出とデータ検証")
    lines.append(f"- 分配金ファイルの開発セット内件数: {result['n_div_rows']}、うち非取引日の権利確定日: {result['n_div_non_trading_record_dates']}")
    lines.append(f"- データ検証に使ったペア数: {s['dividend_data_check_n_ex_pairs']}")
    lines.append(f"- r_night(x−1) の中央値（補正前）: {f(s['dividend_data_check_median_raw_bps'])} bps（規約: ≤ -50bps）")
    lines.append(f"- r_night(x−1) + 分配/close(x−1) の中央値（補正後）: {f(s['dividend_data_check_median_adj_bps'])} bps（規約: ±50bps以内）")
    lines.append(f"- 判定: {'合格' if s['dividend_data_check_passes'] else '不合格'} → 補正を{'使用する' if s['dividend_correction_used'] else '使用しない（両方を以下に併記）'}")
    lines.append("")
    lines.append("## 3. 主指標（保守コスト後平均夜間リターン，ブロックブートストラップ 95%CI）")
    lines.append(f"- n = {s['n_main']}、σ = {f(s['sigma_bps'])} bps、SE = {f(s['se_bps'], 3)} bps、MDE(α=0.05, power=0.8) = {f(s['mde_bps'])} bps")
    lines.append(f"- 保守コスト後平均: {f(s['mean_net_conservative_bps'])} bps、95%CI = [{f(s['ci_lo_conservative_bps'])}, {f(s['ci_hi_conservative_bps'])}] bps")
    lines.append(f"- 楽観コスト（0）平均: {f(s['mean_net_optimistic_bps'])} bps、95%CI = [{f(s['ci_lo_optimistic_bps'])}, {f(s['ci_hi_optimistic_bps'])}] bps")
    lines.append(f"- 関門（平均 ≥ MDE）: {f(s['gate_mean_net_conservative_vs_mde'])}（参考値であり判定ではない）")
    lines.append(f"- 勝率: {f(s['hit_rate'])}、Sharpe(年率): {f(s['sharpe_annualized'])}")
    lines.append(f"- 夜間−日中差: {f(s['night_minus_day_mean_bps'])} bps、CI = [{f(s['night_minus_day_ci_lo_bps'])}, {f(s['night_minus_day_ci_hi_bps'])}]")
    lines.append(f"- 保守 + 旧手数料(感度): 平均 {f(s['sensitivity_mean_net_conservative_plus_oldfee_bps'])} bps、95%CI = [{f(s['sensitivity_ci_lo_conservative_plus_oldfee_bps'])}, {f(s['sensitivity_ci_hi_conservative_plus_oldfee_bps'])}] bps"
                 "（判定には使わない。旧非SOR手数料55円/99円/115円/275円を`config/constants.yaml`の代金帯に従い"
                 "想定ロット≈10万円分（lot=round(100000/close(t))、最小1口）に往復2回課したもの。現行制度はSOR手数料0円）")
    lines.append(f"- 参考: 1口だけの場合、開発セット代表値（1343の中央値close={f(s['sensitivity_median_close_1343_bps_denominator'])}円）で55円/close×1e4 ≈ {f(s['sensitivity_fee_1unit_lot_bps_one_side'])} bps/片側（実質取引不能な水準）")
    lines.append("")
    lines.append("## 4. ドローダウン基準（1口固定）")
    lines.append(f"- 最大ドローダウン（単一実現値）: {f(s['max_drawdown_yen_1unit'])} 円")
    lines.append(f"- 年率換算平均ネット利益 × 3: {f(3 * s['annualized_mean_net_profit_yen_1unit'])} 円（年率平均利益 {f(s['annualized_mean_net_profit_yen_1unit'])} 円）")
    lines.append(f"- 基準内: {f(s['drawdown_ok'])}")
    lines.append(f"- ブロックブートストラップによる最大DDの中央値: {f(s['max_drawdown_bootstrap_median_yen'])} 円")
    lines.append("")
    lines.append("## 5. 「先物と同様」比較（1321）")
    lines.append(f"- 1321 n = {s['n_1321']}、平均 = {f(s['mean_net_conservative_bps_1321'])} bps、CI = [{f(s['ci_lo_bps_1321'])}, {f(s['ci_hi_bps_1321'])}]")
    lines.append(f"- 符号一致: {f(s['sign_match_1343_vs_1321'])}、両方ともCI正: {f(s['both_ci_positive'])}、基準充足: {f(s['futures_like_criterion_met'])}")
    lines.append("")
    lines.append("## 6. 対照（反事実）")
    lines.append(f"- (1) 符号シャッフル {N_SHUFFLE} 回: 帰無分布95点 = {f(s['sign_shuffle_null_95pct_bps'])} bps、実測平均以下の帰無サンプル割合 = {f(s['sign_shuffle_observed_percentile'], 1)}%（0%=帰無分布の最下位）")
    strata_dist = result.get("strata_dist", np.array([]))
    strata_mean = float(np.mean(strata_dist)) if len(strata_dist) else float("nan")
    strata_std = float(np.std(strata_dist, ddof=1)) if len(strata_dist) > 1 else float("nan")
    lines.append(f"- (2) 20日実現ボラ三分位内層別ブートストラップ（診断のみ，時間順序を保存しない）: 平均の分布 平均={f(strata_mean)} bps、標準偏差={f(strata_std)} bps（詳細は controls_summary.csv）")
    lines.append(f"- (3) 符号反転（夜間売り持ち）: 平均 = {f(s['sign_reversal_mean_bps'])} bps、CI = [{f(s['sign_reversal_ci_lo_bps'])}, {f(s['sign_reversal_ci_hi_bps'])}]")
    lines.append("")
    lines.append("## 7. train/val")
    lines.append("| split | n | 平均(bps) | CI |")
    lines.append("|---|---:|---:|---|")
    lines.append(f"| train | {result['train_stats']['n']} | {f(result['train_stats']['mean_bps'])} | [{f(result['train_stats']['ci_lo_bps'])}, {f(result['train_stats']['ci_hi_bps'])}] |")
    lines.append(f"| val | {result['val_stats']['n']} | {f(result['val_stats']['mean_bps'])} | [{f(result['val_stats']['ci_lo_bps'])}, {f(result['val_stats']['ci_hi_bps'])}] |")
    lines.append("")
    lines.append("## 8. 診断（記述的のみ，選択には使用しない）")
    lines.append("")
    lines.append("### ボラ三分位")
    lines.append(_markdown_table(result["vol_tercile_diag"]))
    lines.append("")
    lines.append("### 曜日（0=月...4=金）")
    lines.append(_markdown_table(result["weekday_diag"]))
    lines.append("")
    lines.append("### 月")
    lines.append(_markdown_table(result["month_diag"]))
    lines.append("")
    lines.append("### 権利落ち日±1")
    lines.append(_markdown_table(result["exdate_diag"]))
    lines.append("")
    lines.append("## 9. 付記")
    lines.append(f"- seed = {SEED}、ブロックブートストラップ block={BLOCK}, n_boot={N_BOOT}")
    lines.append("- 本スクリプトは開発セットのみを読む（`load_unsealed`）。封印データは一切読まない。")
    lines.append("- 集計すべては `RUN.json` / 各種CSV に小数点付きで保存済み。")
    (OUT_DIR / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    result = run()
    write_run_json(result)
    write_results_md(result)
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
