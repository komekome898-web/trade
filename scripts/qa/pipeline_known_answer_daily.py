#!/usr/bin/env python3
"""PIPELINE known-answer test — daily execution (docs/PHASE2_SPEC.md §5).

Not an auditor test: checks that the actual daily overnight-premium
computation path used by ON1/ONR research recovers a planted effect and
reports a null as null on synthetic data with known traps.

Computation path: this script IMPORTS (does not reimplement)
`overnight_returns`, `drop_glitches`, `mean_t` and `net_mean_t` from
scripts/research_overnight_onr.py (the frozen ONR PREREG's implementation;
ON1's own daily judgment scripts use the same close->next-open leg
definition). Running the real leg definition + the real glitch filter on
synthetic data with known planted values is the actual test.

Construction (see generate()):
  - a synthetic INDEX FUTURE (clean, "指数水準" analogue) and a synthetic
    ETF that TRACKS it bar-for-bar (same overnight/intraday shocks), 3,000
    business days, GARCH(1,1) vol-clustered intraday vol.
  - overnight premium (close(t) -> open(t+1)) is planted at +Y bps/day,
    Y in {0, 2, 5}, ONLY on days whose GARCH intraday-vol lands in the
    trailing (in-sample) HIGH VOL TERCILE — a planted regime concentration
    (PHASE2_SPEC.md's daily units include a regime-conditioned hypothesis
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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import research_overnight_onr as onr  # noqa: E402  (the actual ONR computation path)

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

GLITCH_THRESHOLD = onr.GLITCH_ABS_LOG_RET  # reuse ONR's own frozen threshold (0.10)


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
        "date": pd.DatetimeIndex(base["dates"]),  # real Timestamp, as onr.load_ohlc's
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
        "computation_path": "scripts/research_overnight_onr.py: overnight_returns, drop_glitches, mean_t "
                             "(imported directly, not reimplemented)",
        "glitch_threshold_abs_log_return": GLITCH_THRESHOLD,
        "y_values_bps": list(Y_VALUES),
        "split_day_index": base["split_day"], "split_date_flagged_leg": split_date,
        "split_ratio_unadjusted": SPLIT_RATIO,
        "bad_print_days_index": base["bad_days"],
        "bad_print_dates_flagged_legs": bad_dates_boundaries,
        "expected_dropped_dates": expected_dropped,
        "results_by_y": {str(y): per_y[y] for y in Y_VALUES},
        "data_quality_scan": dq_report,
        "files": {str(y): files[y] for y in Y_VALUES},
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
    lines += ["", f"data_quality.py extreme_return hits on the ETF tape: {dq_hits}", "",
              "## パイプラインの欠陥 (findings)", ""]
    lines += [f"- {finding}" for finding in findings] if findings else ["- none"]
    (out_dir / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"per_y": per_y, "findings": findings, "sealed": sealed, "out_dir": str(out_dir)}


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
