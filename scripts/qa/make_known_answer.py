#!/usr/bin/env python3
"""Generate a sealed KNOWN-ANSWER QA packet for auditing the blind-audit
procedure itself (docs/QA_PLAN_2026-09.md §2-2 item 1).

This does NOT touch any real trading data. It writes purely synthetic files
under backtest_data/qa_known_answer_<date>/ whose file formats mirror the
real ones (same column names/order as daily_btcusd_*.csv.gz,
binance_BTCUSDT_1m.csv, executions_FX_BTC_JPY_*.csv.gz), with known planted
effects and known traps. The truth is written to docs/QA/answers_sealed.json
and must NEVER be shown to an auditor; the packet's own manifest.md
describes the files without revealing planted values.

Determinism: a single fixed SEED drives every random draw (sub-streams via
np.random.default_rng(SEED).spawn(...)), so re-running with the same
--seed/--date reproduces byte-identical CSVs and identical numeric answers
(only the "generated_utc" field in the sealed answers changes).

Usage:
    python scripts/qa/make_known_answer.py
    python scripts/qa/make_known_answer.py --out-dir /tmp/x --answers-out /tmp/a.json \
        --claims-out /tmp/c.md --date 20260905 --seed 20260905
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

SEED = 20260905
REPO_ROOT = Path(__file__).resolve().parents[2]

# --- daily instruments: (name, planted overnight premium bps/day) ---------
INSTRUMENTS = [("QA_ALPHA", 0.0), ("QA_BRAVO", 2.0), ("QA_CHARLIE", 5.0)]
DAILY_START = "2011-01-03"
DAILY_END = "2026-08-31"
DAILY_INTRADAY_SIGMA = 0.012      # ~1.2% typical daily open->close vol
DAILY_OVERNIGHT_SIGMA_BPS = 18.0  # base overnight (close->next open) noise
GARCH_ALPHA, GARCH_BETA = 0.08, 0.90
EX_DIV_DROP_BPS = -120.0          # one-off ex-dividend overnight drop
SCALE_GLITCH_FACTOR = 1000.0

MINUTE_DAYS = 60
MINUTE_START = "2026-06-01T00:00:00+00:00"
MINUTE_SIGMA_BASE = 0.0009        # ~9bps per-minute vol, GARCH-modulated
AUTOCORR_PHI = 0.05
MAINT_WINDOW = ("19:00", "19:10")  # UTC, matches bitFlyer's real window

TAPE_DAYS = 3
TAPE_START = "2026-07-01T00:00:00+00:00"
QUOTE_SPREAD_BPS = 2.0
TAKER_SLIPPAGE_BPS = 0.8
TAKER_FEE_BPS = 0.0
CROSSED_BOOK_FRACTION = 0.001
COLLECTION_TIME_SHIFT_SEC = 2.0
QUOTE_MEAN_GAP_SEC = 5.0
EXEC_MEAN_GAP_SEC = 8.0
TAPE_PRICE_SIGMA_PER_SEC = 0.00006   # per-sqrt-second mid vol


# --------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------- #
def garch_sigma_path(rng: np.random.Generator, n: int, base_sigma: float,
                      alpha: float = GARCH_ALPHA, beta: float = GARCH_BETA) -> np.ndarray:
    """GARCH(1,1)-style vol-clustering path with unconditional std = base_sigma."""
    omega = base_sigma ** 2 * (1.0 - alpha - beta)
    sigma2 = np.empty(n)
    z = rng.standard_normal(n)
    sigma2[0] = base_sigma ** 2
    r = np.empty(n)
    r[0] = z[0] * math.sqrt(sigma2[0])
    for t in range(1, n):
        sigma2[t] = omega + alpha * r[t - 1] ** 2 + beta * sigma2[t - 1]
        r[t] = z[t] * math.sqrt(sigma2[t])
    sigma = np.sqrt(sigma2)
    return sigma, r  # sigma path + the raw N(0,sigma_t) draws (reused as intraday shocks)


def to_iso(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").isoformat()


def gzip_write(path: Path, text: str) -> None:
    # mtime=0 so re-running with the same seed is byte-identical (gzip
    # otherwise embeds the wall-clock write time in the header).
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(text.encode("utf-8"))


# --------------------------------------------------------------------- #
# (a) daily OHLC, 3 instruments
# --------------------------------------------------------------------- #
def make_daily(rng: np.random.Generator, out_dir: Path) -> dict:
    dates = pd.bdate_range(DAILY_START, DAILY_END, tz="UTC")
    n = len(dates)
    truth = {}
    # fixed contamination assignment: ALPHA (null) carries both traps so a
    # correct auditor must show robustness to outliers to reach ~0bps;
    # CHARLIE gets one ex-div drop only; BRAVO stays clean.
    ex_div_idx = {"QA_ALPHA": int(n * 0.31), "QA_CHARLIE": int(n * 0.68)}
    scale_glitch_start = {"QA_ALPHA": int(n * 0.55)}

    for name, premium_bps in INSTRUMENTS:
        sigma_intraday, intraday_shocks = garch_sigma_path(rng, n, DAILY_INTRADAY_SIGMA)
        overnight_noise_sigma = (DAILY_OVERNIGHT_SIGMA_BPS / 1e4) * (sigma_intraday / sigma_intraday.mean())
        overnight_z = rng.standard_normal(n)
        overnight_ret = premium_bps / 1e4 + overnight_z * overnight_noise_sigma

        ex_div_dates = []
        if name in ex_div_idx:
            i = ex_div_idx[name]
            overnight_ret[i] += EX_DIV_DROP_BPS / 1e4
            ex_div_dates.append(to_iso(dates[i]))

        # walk-forward: close_t = open_t*exp(intraday); open_{t+1}=close_t*exp(overnight_{t+1})
        open_ = np.empty(n)
        close = np.empty(n)
        open_[0] = 100.0
        close[0] = open_[0] * math.exp(intraday_shocks[0])
        for t in range(1, n):
            open_[t] = close[t - 1] * math.exp(overnight_ret[t])
            close[t] = open_[t] * math.exp(intraday_shocks[t])
        rng_intraday_hi = rng.uniform(0.0002, 0.004, n)
        rng_intraday_lo = rng.uniform(0.0002, 0.004, n)
        high = np.maximum(open_, close) * (1 + rng_intraday_hi)
        low = np.minimum(open_, close) * (1 - rng_intraday_lo)
        volume = rng.lognormal(mean=10.0, sigma=0.6, size=n)

        scale_dates = []
        if name in scale_glitch_start:
            s = scale_glitch_start[name]
            for j in (s, s + 1):
                open_[j] *= SCALE_GLITCH_FACTOR
                high[j] *= SCALE_GLITCH_FACTOR
                low[j] *= SCALE_GLITCH_FACTOR
                close[j] *= SCALE_GLITCH_FACTOR
                scale_dates.append(to_iso(dates[j]))

        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "open": open_, "high": high, "low": low, "close": close, "volume": volume,
        })
        fname = f"daily_{name.lower()}.csv.gz"
        gzip_write(out_dir / fname, df.to_csv(index=False))

        # ground truth recomputed FROM the generated series (this is what a
        # correct blind recomputation on the raw overnight leg should land on)
        clean_mask = np.ones(n, dtype=bool)
        clean_mask[0] = False
        realized = overnight_ret[clean_mask]
        mean_bps = float(realized.mean() * 1e4)
        se_bps = float(realized.std(ddof=1) / math.sqrt(realized.size) * 1e4)
        t_stat = mean_bps / se_bps if se_bps else float("nan")
        truth[name] = {
            "file": fname,
            "planted_overnight_premium_bps_per_day": premium_bps,
            "realized_overnight_mean_bps": round(mean_bps, 4),
            "realized_overnight_t_stat": round(t_stat, 3),
            "n_overnight_observations": int(realized.size),
            "date_range_utc": [to_iso(dates[0]), to_iso(dates[-1])],
            "ex_dividend_drop_dates_utc": ex_div_dates,
            "ex_dividend_drop_bps": EX_DIV_DROP_BPS if ex_div_dates else None,
            "price_scale_glitch_dates_utc": scale_dates,
            "price_scale_glitch_factor": SCALE_GLITCH_FACTOR if scale_dates else None,
        }
    return truth


# --------------------------------------------------------------------- #
# (b) 1-minute bars, 60 days: random walk vs planted +0.05 lag-1 autocorr
# --------------------------------------------------------------------- #
def apply_maintenance_window(ts_index: pd.DatetimeIndex) -> np.ndarray:
    hm = ts_index.strftime("%H:%M")
    return (hm >= MAINT_WINDOW[0]) & (hm < MAINT_WINDOW[1])


def make_minute_series(rng: np.random.Generator, n: int, phi: float) -> tuple[np.ndarray, np.ndarray]:
    sigma, _ = garch_sigma_path(rng, n, MINUTE_SIGMA_BASE)
    eps = rng.standard_normal(n)
    if phi == 0.0:
        z = eps
    else:
        z = np.empty(n)
        z[0] = eps[0]
        k = math.sqrt(1 - phi ** 2)
        for t in range(1, n):
            z[t] = phi * z[t - 1] + k * eps[t]
    return sigma * z, sigma


def make_minute_bars(rng: np.random.Generator, out_dir: Path) -> dict:
    start = pd.Timestamp(MINUTE_START)
    n = MINUTE_DAYS * 24 * 60
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    maint_mask = apply_maintenance_window(idx)
    truth = {}
    for slug, phi in (("qa_randomwalk", 0.0), ("qa_autocorr", AUTOCORR_PHI)):
        returns, _ = make_minute_series(rng, n, phi)
        returns = returns.copy()
        returns[maint_mask] = 0.0  # maintenance-window synthetic flat fill

        price = 1_000_000.0 * np.exp(np.cumsum(returns))
        close = price
        open_ = np.empty(n)
        open_[0] = 1_000_000.0
        open_[1:] = close[:-1]
        open_[maint_mask] = close[maint_mask]  # carried-forward flat bar
        hi_j = rng.uniform(0.0, 0.0003, n)
        lo_j = rng.uniform(0.0, 0.0003, n)
        high = np.maximum(open_, close) * (1 + hi_j)
        low = np.minimum(open_, close) * (1 - lo_j)
        volume = rng.lognormal(mean=1.5, sigma=0.8, size=n)
        high[maint_mask] = close[maint_mask]
        low[maint_mask] = close[maint_mask]
        volume[maint_mask] = 0.0

        df = pd.DataFrame({
            "timestamp": idx.strftime("%Y-%m-%d %H:%M:%S%z"),
            "open": open_, "high": high, "low": low, "close": close, "volume": volume,
        })
        df["timestamp"] = idx.strftime("%Y-%m-%d %H:%M:%S+00:00")
        fname = f"min1_{slug}.csv.gz"
        gzip_write(out_dir / fname, df.to_csv(index=False))

        ret_clean = returns[~maint_mask]
        r0, r1 = ret_clean[:-1], ret_clean[1:]
        lag1 = float(np.corrcoef(r0, r1)[0, 1])
        truth[slug] = {
            "file": fname,
            "planted_lag1_autocorr": phi,
            "realized_lag1_autocorr_ex_maintenance": round(lag1, 5),
            "n_minutes": int(n),
            "days": MINUTE_DAYS,
            "maintenance_window_utc": f"{MAINT_WINDOW[0]}-{MAINT_WINDOW[1]} daily",
            "maintenance_rows": int(maint_mask.sum()),
        }
    return truth


# --------------------------------------------------------------------- #
# (c) synthetic tape: quote changes + executions, 3 days
# --------------------------------------------------------------------- #
def make_tape(rng: np.random.Generator, out_dir: Path) -> dict:
    start = pd.Timestamp(TAPE_START)
    span_sec = TAPE_DAYS * 86400

    # quote-change event times (Poisson process)
    n_quotes_est = int(span_sec / QUOTE_MEAN_GAP_SEC * 1.2)
    gaps_q = rng.exponential(QUOTE_MEAN_GAP_SEC, n_quotes_est)
    t_q = np.cumsum(gaps_q)
    t_q = t_q[t_q < span_sec]
    n_q = len(t_q)

    # mid-price random walk sampled at quote-change times
    dt = np.diff(np.concatenate([[0.0], t_q]))
    z = rng.standard_normal(n_q)
    log_ret = TAPE_PRICE_SIGMA_PER_SEC * np.sqrt(dt) * z
    mid = 1_000_000.0 * np.exp(np.cumsum(log_ret))

    half_spread = mid * (QUOTE_SPREAD_BPS / 2 / 1e4)
    bid = mid - half_spread
    ask = mid + half_spread
    crossed = rng.random(n_q) < CROSSED_BOOK_FRACTION
    n_crossed = int(crossed.sum())
    if n_crossed:
        bid_c = bid[crossed].copy()
        bid[crossed] = ask[crossed]
        ask[crossed] = bid_c
    bid_sz = rng.uniform(0.005, 0.5, n_q)
    ask_sz = rng.uniform(0.005, 0.5, n_q)
    q_ts = start + pd.to_timedelta(t_q, unit="s")

    quotes = pd.DataFrame({
        "ts": q_ts.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
        "best_bid": bid, "best_ask": ask,
        "best_bid_size": bid_sz, "best_ask_size": ask_sz,
    })
    qfile = "ticker_qa_tape.csv.gz"
    gzip_write(out_dir / qfile, quotes.to_csv(index=False))

    # execution event times (independent Poisson process)
    n_exec_est = int(span_sec / EXEC_MEAN_GAP_SEC * 1.2)
    gaps_e = rng.exponential(EXEC_MEAN_GAP_SEC, n_exec_est)
    t_e = np.cumsum(gaps_e)
    t_e = t_e[t_e < span_sec]
    n_e = len(t_e)
    e_ts_sec = t_e

    quote_idx = np.searchsorted(t_q, e_ts_sec, side="right") - 1
    quote_idx = np.clip(quote_idx, 0, n_q - 1)
    trade_mid = mid[quote_idx]
    side = rng.choice(["BUY", "SELL"], size=n_e)
    slip_bps = TAKER_SLIPPAGE_BPS + rng.normal(0.0, 0.15, n_e)
    sign = np.where(side == "BUY", 1.0, -1.0)
    exec_half_spread = trade_mid * (QUOTE_SPREAD_BPS / 2 / 1e4)
    price = trade_mid + sign * exec_half_spread + sign * trade_mid * (slip_bps / 1e4)
    size = rng.lognormal(mean=-2.5, sigma=1.0, size=n_e)

    e_ts = start + pd.to_timedelta(e_ts_sec, unit="s")          # TRUE trade time
    t_collect = e_ts + pd.to_timedelta(COLLECTION_TIME_SHIFT_SEC, unit="s")  # collection time (trap)
    exec_id = 2_700_000_000 + np.arange(n_e)

    execs = pd.DataFrame({
        "id": exec_id,
        "t": t_collect.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
        "ts": e_ts.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
        "price": price, "size": size, "side": side,
    })
    efile = "executions_qa_tape.csv.gz"
    gzip_write(out_dir / efile, execs.to_csv(index=False))

    costs_yaml = {
        "_comment": "QA known-answer packet: DECLARED constant only. Spread and "
                    "slippage are NOT declared here — recompute both from the "
                    "tape yourself, per PROTOCOL.md Q3.",
        "taker_fee_bps": TAKER_FEE_BPS,
        "source": "synthetic, matches config/products.yaml FX_BTC_JPY convention (taker_fee_pct: 0.0)",
    }
    (out_dir / "costs_qa.yaml").write_text(yaml.safe_dump(costs_yaml, sort_keys=False, allow_unicode=True))

    realized_spread_bps = float(((ask - bid) / mid * 1e4)[~crossed].mean())
    realized_slip_bps = float((np.abs((price - trade_mid) / trade_mid * 1e4) - QUOTE_SPREAD_BPS / 2).mean())
    return {
        "quote_file": qfile, "execution_file": efile, "costs_file": "costs_qa.yaml",
        "n_quote_rows": int(n_q), "n_execution_rows": int(n_e),
        "quoted_spread_bps": QUOTE_SPREAD_BPS,
        "realized_spread_bps_ex_crossed": round(realized_spread_bps, 4),
        "taker_slippage_bps_per_side": TAKER_SLIPPAGE_BPS,
        "realized_slippage_bps_per_side": round(realized_slip_bps, 4),
        "taker_fee_bps": TAKER_FEE_BPS,
        "true_taker_roundtrip_floor_bps": round(2 * (QUOTE_SPREAD_BPS / 2 + TAKER_SLIPPAGE_BPS), 4),
        "crossed_book_fraction_target": CROSSED_BOOK_FRACTION,
        "crossed_book_rows": n_crossed,
        "crossed_book_fraction_realized": round(n_crossed / n_q, 6),
        "true_trade_time_column": "ts",
        "collection_time_column": "t",
        "collection_time_shift_sec": COLLECTION_TIME_SHIFT_SEC,
        "date_range_utc": [to_iso(q_ts[0]), to_iso(q_ts[-1])],
    }


# --------------------------------------------------------------------- #
# manifest (no planted values) + claims (deliberately includes wrong ones)
# --------------------------------------------------------------------- #
MANIFEST_TEMPLATE = """# QA known-answer packet — manifest

Synthetic data generated by `scripts/qa/make_known_answer.py` (fixed seed) for
calibrating the blind-audit procedure (docs/QA_PLAN_2026-09.md §2-2). Nothing
here is real market data. File formats mirror the repo's real ones so an
auditor's usual loaders apply unchanged.

Do not open `docs/QA/answers_sealed.json` before completing an audit of this
packet — it seals the ground truth this packet is designed to test against.

## Daily OHLC (3 synthetic instruments)

| file | columns | rows | date range (UTC) |
|---|---|---|---|
{daily_rows}

Business days only (weekends excluded), one row per trading day.

## 1-minute bars ({minute_days} days, 2 series)

| file | columns | rows |
|---|---|---|
{minute_rows}

Continuous 1-minute bars, UTC timestamps.

## Synthetic tape (quotes + executions, {tape_days} days)

| file | columns | rows |
|---|---|---|
{tape_rows}

`costs_qa.yaml` declares only the taker fee constant used to build this tape;
spread and slippage are not declared and must be measured from the data.

## Notes

- OHLC/volume columns are floats; timestamps are ISO-8601 UTC.
- As with any production feed, verify timestamp-column semantics
  independently rather than assuming a name's usual meaning elsewhere in
  this repo, and check for maintenance-window artifacts, crossed quotes, and
  price-scale discontinuities before drawing conclusions.
- Generated: {generated_utc} (seed {seed}).
"""


def build_manifest(daily_truth, minute_truth, tape_truth, seed: int) -> str:
    daily_rows = "\n".join(
        f"| `{v['file']}` | date,open,high,low,close,volume | {v['n_overnight_observations'] + 1} | "
        f"{v['date_range_utc'][0][:10]} .. {v['date_range_utc'][1][:10]} |"
        for v in daily_truth.values()
    )
    minute_rows = "\n".join(
        f"| `{v['file']}` | timestamp,open,high,low,close,volume | {v['n_minutes']} |"
        for v in minute_truth.values()
    )
    tape_rows = (
        f"| `{tape_truth['quote_file']}` | ts,best_bid,best_ask,best_bid_size,best_ask_size | "
        f"{tape_truth['n_quote_rows']} |\n"
        f"| `{tape_truth['execution_file']}` | id,t,ts,price,size,side | "
        f"{tape_truth['n_execution_rows']} |"
    )
    return MANIFEST_TEMPLATE.format(
        daily_rows=daily_rows, minute_rows=minute_rows, tape_rows=tape_rows,
        minute_days=MINUTE_DAYS, tape_days=TAPE_DAYS,
        generated_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
    )


def build_claims(daily_truth, minute_truth, tape_truth) -> tuple[str, list[dict]]:
    bravo = daily_truth["QA_BRAVO"]
    alpha = daily_truth["QA_ALPHA"]
    autocorr = minute_truth["qa_autocorr"]
    rwalk = minute_truth["qa_randomwalk"]
    floor = tape_truth["true_taker_roundtrip_floor_bps"]

    claims = [
        {
            "id": "QA-1", "category": "premium", "truth_class": "true_effect", "claim_correct": True,
            "instrument": "QA_BRAVO",
            "text": (f"QA_BRAVO は close→翌 open のオーバーナイト・プレミアムが"
                     f"+{bravo['realized_overnight_mean_bps']:.1f}bps/日、"
                     f"t={bravo['realized_overnight_t_stat']:.1f} で存在する"
                     f"({bravo['date_range_utc'][0][:10]}〜{bravo['date_range_utc'][1][:10]}、平日のみ)。"),
        },
        {
            "id": "QA-2", "category": "premium", "truth_class": "zero_effect", "claim_correct": False,
            "instrument": "QA_ALPHA",
            "text": (f"QA_ALPHA は close→翌 open のオーバーナイト・プレミアムが"
                     f"+3.5bps/日、t=4.2 で存在する"
                     f"({alpha['date_range_utc'][0][:10]}〜{alpha['date_range_utc'][1][:10]}、平日のみ)。"),
        },
        {
            "id": "QA-3", "category": "momentum", "truth_class": "true_effect", "claim_correct": True,
            "instrument": "qa_autocorr",
            "text": (f"1分足系列 qa_autocorr はリターンの lag-1 自己相関が"
                     f"+{autocorr['realized_lag1_autocorr_ex_maintenance']:.3f} と有意に正"
                     f"({autocorr['days']}日、対照系列 qa_randomwalk との比較で確認)。"),
        },
        {
            "id": "QA-4", "category": "momentum", "truth_class": "zero_effect", "claim_correct": False,
            "instrument": "qa_randomwalk",
            "text": (f"1分足系列 qa_randomwalk はリターンの lag-1 自己相関が"
                     f"+0.04 で有意なモメンタムが存在する({rwalk['days']}日)。"),
        },
        {
            "id": "QA-5", "category": "cost_floor", "truth_class": "cost_trap", "claim_correct": True,
            "instrument": "qa_tape",
            "text": (f"合成テープの taker 往復コスト床は{floor:.1f}bps"
                     f"(スプレッド{tape_truth['quoted_spread_bps']:.1f}bpsの半分+"
                     f"片道スリッページ{tape_truth['taker_slippage_bps_per_side']:.1f}bps、"
                     f"手数料{tape_truth['taker_fee_bps']:.1f}bps)である。"),
        },
        {
            "id": "QA-6", "category": "cost_floor", "truth_class": "cost_trap", "claim_correct": False,
            "instrument": "qa_tape",
            "text": ("合成テープの実測スプレッドは1.2bpsに縮小しており"
                     "(全 quote 行の単純平均。交差板・メンテ窓等の除外は行っていない)、"
                     "taker 往復コスト床は2.8bpsまで圧縮できる。"),
        },
    ]
    lines = ["# QA known-answer packet — claims for auditors", "",
             "以下 6 件を PROTOCOL.md の 10 問に従って判定せよ。番号 (QA-1..QA-6) を報告の見出しに使うこと。", ""]
    for c in claims:
        lines.append(f"## {c['id']}\n\n{c['text']}\n")
    return "\n".join(lines), claims


# --------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------- #
def generate(out_dir: Path, seed: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    daily_truth = make_daily(np.random.default_rng(rng.integers(0, 2**63 - 1)), out_dir)
    minute_truth = make_minute_bars(np.random.default_rng(rng.integers(0, 2**63 - 1)), out_dir)
    tape_truth = make_tape(np.random.default_rng(rng.integers(0, 2**63 - 1)), out_dir)

    manifest = build_manifest(daily_truth, minute_truth, tape_truth, seed)
    (out_dir / "manifest.md").write_text(manifest)

    claims_md, claims = build_claims(daily_truth, minute_truth, tape_truth)

    answers = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "dataset_dir": str(out_dir.relative_to(REPO_ROOT)) if out_dir.is_relative_to(REPO_ROOT) else str(out_dir),
        "daily_overnight_premium": daily_truth,
        "minute_bars": minute_truth,
        "tape": tape_truth,
        "traps": {
            "crossed_book_rows": {
                "file": tape_truth["quote_file"],
                "fraction_target": CROSSED_BOOK_FRACTION,
                "n_rows": tape_truth["crossed_book_rows"],
            },
            "maintenance_window_flat_segment": {
                "files": [minute_truth["qa_randomwalk"]["file"], minute_truth["qa_autocorr"]["file"]],
                "window_utc": minute_truth["qa_randomwalk"]["maintenance_window_utc"],
                "rows_per_series": minute_truth["qa_randomwalk"]["maintenance_rows"],
            },
            "t_ts_collection_vs_trade_time": {
                "file": tape_truth["execution_file"],
                "collection_time_column": "t",
                "true_trade_time_column": "ts",
                "shift_sec": COLLECTION_TIME_SHIFT_SEC,
            },
            "price_scale_glitch": {
                "file": daily_truth["QA_ALPHA"]["file"],
                "dates_utc": daily_truth["QA_ALPHA"]["price_scale_glitch_dates_utc"],
                "factor": SCALE_GLITCH_FACTOR,
            },
        },
        "claims": claims,
    }
    return {"manifest": manifest, "claims_md": claims_md, "answers": answers}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", default=None, help="override backtest_data/qa_known_answer_<date>")
    ap.add_argument("--answers-out", default=None, help="override docs/QA/answers_sealed.json")
    ap.add_argument("--claims-out", default=None, help="override docs/QA/claims_for_auditors.md")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_known_answer_{args.date}"
    answers_out = Path(args.answers_out) if args.answers_out else REPO_ROOT / "docs" / "QA" / "answers_sealed.json"
    claims_out = Path(args.claims_out) if args.claims_out else REPO_ROOT / "docs" / "QA" / "claims_for_auditors.md"
    answers_out.parent.mkdir(parents=True, exist_ok=True)
    claims_out.parent.mkdir(parents=True, exist_ok=True)

    result = generate(out_dir, args.seed)
    answers_out.write_text(json.dumps(result["answers"], indent=2, ensure_ascii=False, sort_keys=False))
    claims_out.write_text(result["claims_md"])

    print(f"wrote dataset -> {out_dir}")
    print(f"wrote sealed answers -> {answers_out}")
    print(f"wrote claims -> {claims_out}")


if __name__ == "__main__":
    main()
