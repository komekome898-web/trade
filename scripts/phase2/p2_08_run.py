#!/usr/bin/env python
"""P2-08 iteration 0 — the pre-registered main test, DEVELOPMENT SET ONLY.

Implements `docs/PHASE2/P2-08/PREREG.md` (凍結 第 4 稿 2026-09-06) with the
research engine `bot.research.xborder_p2` (reference rules) and its array
twin `bot.research.xborder_p2_fast` (identical ledgers, tested in
tests/test_xborder_p2_fast.py) for the 2,000-draw × 27-configuration null.

Blind: nothing under src/bot/strategy/, config/composite.yaml or the strategy
section of config/config.yaml is read. Every price file is read through
`bot.research.sealed.load_unsealed(path, "P2-08")` (scripts/phase2/p2_08_data.py),
so the sealed window (2023-12-18 ..) is structurally unreachable. The burst
coefficient uses the WS tape (paper_logs/tape, 2026-08-20 ..) only for the
quoted/effective spread, as the PREREG instructs; the signal minutes on the
tape are defined from the tape's OWN bitFlyer 1-minute closes (the Binance
series for that window is sealed for this unit).

Nothing here interprets a number: it writes tables.

Usage:  PYTHONPATH=src python scripts/phase2/p2_08_run.py --iteration 0
        ... --out backtest_data/phase2_runs/P2-08/iter0_20260906
        ... --n-null 40 --n-ctrl 20 --n-boot 200 --workers 4   (smoke test)

Iteration 1 (`--iteration 1`, PREREG 探索面「反復の梯子」反復 1): the same 27
configurations each conditioned on the realized-volatility (60-minute)
tercile at the signal minute — entries allowed only in that tercile — 27 × 3
= 81 new configurations, cumulative N = 108. The state is defined in
`bot.research.xborder_p2_state` (window, minimum bars, boundaries frozen on
the train period) and applied through `simulate_arrays(..., entry_gate=...)`.
The 27 unconditioned cells are recomputed with the SAME seeds as iteration 0
so their rows in configs.csv and their per-draw null statistics must equal
iteration 0's (reported in RESULTS.md as a consistency check). The best of
the 108 is chosen on val exactly as in iteration 0; the null is best-of-108
over the same 2,000 permuted worlds (same draw seeds); controls 2 and 3 and
the edge trend are produced for that best configuration only, and the
§6 condition analysis (`state_split`) is reported for the iteration-0 best
and the current configuration.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bot.research.overnight import (  # noqa: E402
    EDGE_TREND_SLOPE_MDE_Z,
    block_bootstrap_ci,
    edge_trend,
    state_split,
)
from bot.research.xborder_p2 import momentum_signal, simulate  # noqa: E402
from bot.research.xborder_p2_state import (  # noqa: E402
    TERCILE_CODES,
    TERCILE_LABELS,
    VOL_MIN_BARS,
    VOL_WINDOW_MIN,
    assign_tercile,
    realized_vol,
    tercile_bounds,
    tercile_gates,
    tercile_label,
)
from bot.research.xborder_p2_fast import (  # noqa: E402
    BinanceGrid,
    BlockPermuter,
    Grid,
    build_signals,
    daily_from_arrays,
    prepare_grid,
    sharpe_from_daily,
    simulate_arrays,
    simulate_fast,
)
from scripts.phase2.p2_08_data import (  # noqa: E402
    BF_DIR,
    BN_DIR,
    DEV_END,
    DEV_START,
    DEV_YEARS,
    UNIT,
    load_dev_frames,
    summarize,
)

# ---- pre-registered constants (PREREG 探索面 / コスト定数 / 指標と分母) --------
SEED = 20260906
KS = (15, 30, 60)
THRS = (0.4, 0.8, 1.2)
STOPS = (0.25, 0.5, 1.0)
EXIT_PCT = 0.05
CONFIGS = [(k, thr, stop) for k in KS for thr in THRS for stop in STOPS]      # N0 = 27
CURRENT = (30, 0.8, 0.5)
COST_CONS_1W = 1.3            # constants.yaml realized_taker_one_way_bps upper (measured)
COST_OPT_1W = 1.0             # lower (measured)
FUNDING_PCT = 0.02            # per settlement, UTC 05/13/21
FUNDING_TIMES = (5, 13, 21)
MAX_GAP_MIN = 5
BURST_ASSUMED = 2.0           # PREREG: used only when the coefficient cannot be measured
BURST_MIN_WINDOW_MINUTES = 30      # below this the cell is "not measurable" -> BURST_ASSUMED
BURST_THIN_WINDOW_MINUTES = 100    # below this the measured ratio is flagged "thin" (still used)
TRAIN_END = pd.Timestamp("2021-12-31 23:59:00", tz="UTC")
VAL_START = pd.Timestamp("2022-01-01 00:00:00", tz="UTC")
VAL_2022_END = pd.Timestamp("2022-12-31 23:59:00", tz="UTC")
N_BOOT = 2000
N_NULL = 2000
N_CTRL = 1000
EDGE_WINDOW = 50              # PREREG エッジ推移: 窓 = 50 取引
EDGE_BLOCK = 20               # not in the PREREG: block length for §5's bootstrap (recorded)
MDE_REGISTERED = 1.54
SIGMA_REGISTERED = 86.5
N_REGISTERED = 24717
MDE_Z = EDGE_TREND_SLOPE_MDE_Z
SEAL_FILE = "backtest_data/phase2_sealed/P2-08/SEALED.json"
TAPE_DIR = REPO_ROOT / "paper_logs" / "tape"
TAPE_DAYS = [d.strftime("%Y%m%d") for d in pd.date_range("2026-08-20", "2026-09-05")]
OUT_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-08" / "iter0_20260906"
LAGS = list(range(-10, 11))
SHIFTS = (-2, -1, 1, 2)

# ---- iteration 1 (PREREG 反復の梯子 1: 実現ボラ 60 分 三分位) -----------------
OUT_DIR_ITER1 = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-08" / "iter1_20260906"
ITER0_DIR = OUT_DIR                                      # iteration-0 outputs read for cross-checks
ITER0_BEST = (15, 0.4, 0.5)                              # iteration-0 RESULTS.md §4 "val の平均 net 最大"
STATES = (None,) + TERCILE_CODES                          # None = unconditioned
CONFIGS_ITER1 = [(k, thr, stop, st) for (k, thr, stop) in CONFIGS for st in STATES]   # 27 × 4 = 108
N_CUMULATIVE_ITER1 = len(CONFIGS_ITER1)

Z975 = 1.959963985


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception as exc:  # pragma: no cover
        return f"unavailable ({exc})"


def _fmt(v, nd: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not np.isfinite(fv):
        return "—"
    return f"{fv:,.{nd}f}"


def _table(rows: list[dict], cols: list[tuple[str, str, int]]) -> str:
    head = "| " + " | ".join(c[1] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = ["| " + " | ".join(
        (str(r.get(k, "")) if nd < 0 else _fmt(r.get(k), nd)) for k, _, nd in cols) + " |"
        for r in rows]
    return "\n".join([head, sep] + body)


def cfg_label(cfg) -> str:
    """'k/thr/stop' for a 3-tuple; 'k/thr/stop@state' for an iteration-1
    4-tuple (state None → '@all')."""
    if len(cfg) == 4:
        k, thr, stop, st = cfg
        return f"{k}/{thr}/{stop}@{tercile_label(st)}"
    k, thr, stop = cfg
    return f"{k}/{thr}/{stop}"


def mde_of(sd: float, n: int) -> float:
    """2.8016 × σ / √n (PREREG 指標と分母)."""
    return float(MDE_Z * sd / np.sqrt(n)) if n and np.isfinite(sd) else float("nan")


def cluster_boot_mean(values: np.ndarray, clusters: np.ndarray, n_boot: int, seed
                      ) -> tuple[float, float, float]:
    """Percentile 95% CI of the mean, resampling CLUSTERS (days) with
    replacement. Returns (lo, hi, se)."""
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    _, inv = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inv, weights=values)
    cnts = np.bincount(inv).astype(float)
    d = len(sums)
    if d < 2:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    chunk = max(1, min(n_boot, int(2e7 // max(d, 1))))
    for s in range(0, n_boot, chunk):
        e = min(n_boot, s + chunk)
        draws = rng.integers(0, d, size=(e - s, d))
        means[s:e] = sums[draws].sum(axis=1) / cnts[draws].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi), float(means.std(ddof=1))


def boot_sharpe(daily: np.ndarray, n_boot: int, seed) -> tuple[float, float]:
    """Percentile 95% CI of the annualised daily Sharpe, resampling calendar
    days with replacement (the day is the cluster)."""
    t = len(daily)
    if t < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    chunk = max(1, min(n_boot, int(2e7 // t)))
    for s in range(0, n_boot, chunk):
        e = min(n_boot, s + chunk)
        x = daily[rng.integers(0, t, size=(e - s, t))]
        sd = x.std(axis=1, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[s:e] = np.where(sd > 0, x.mean(axis=1) / sd * np.sqrt(365.0), np.nan)
    ok = out[np.isfinite(out)]
    if len(ok) < 2:
        return float("nan"), float("nan")
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return float(lo), float(hi)


def max_drawdown(x: np.ndarray) -> float:
    if len(x) == 0:
        return float("nan")
    eq = np.cumsum(x)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())


# ---------------------------------------------------------------------------
# burst coefficient from the WS tape (PREREG コスト定数「バースト時の費用」)
# ---------------------------------------------------------------------------

def _read_tape(kind: str) -> tuple[pd.DataFrame, list[Path]]:
    frames, files = [], []
    for day in TAPE_DAYS:
        p = TAPE_DIR / f"{kind}_{day}.csv.gz"
        if p.exists():
            frames.append(pd.read_csv(p))
            files.append(p)
    if not frames:
        return pd.DataFrame(), files
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    return df.sort_values("ts").reset_index(drop=True), files


def burst_coefficients() -> tuple[pd.DataFrame, dict, dict]:
    """Per (k, thr): effective and quoted half-spread (bps) in the minutes
    t−1..t+1 around |m_bf(t)| > thr, over the unconditional minute mean.

    m_bf is the tape's own bitFlyer 1-minute close momentum (the Binance
    minutes of this window are sealed for P2-08). Effective half-spread of an
    execution = |price − mid_prev| / mid_prev (mid_prev = best bid/ask
    midpoint of the last ticker row at or before the execution). Minute
    values are size-weighted (effective) / row means (quoted); the ratio is
    the mean over window minutes divided by the mean over all minutes.
    """
    ex, ex_files = _read_tape("executions")
    tk, tk_files = _read_tape("ticker")
    meta = {"files": [str(p.relative_to(REPO_ROOT)) for p in ex_files + tk_files],
            "n_executions": int(len(ex)), "n_ticker_rows": int(len(tk))}
    if not len(ex) or not len(tk):
        meta["measured"] = False
        meta["reason"] = "no tape executions/ticker rows on disk"
        return pd.DataFrame(), {}, meta
    tk = tk[(tk["best_bid"] > 0) & (tk["best_ask"] > 0)].copy()
    tk["mid"] = (tk["best_bid"] + tk["best_ask"]) / 2.0
    tk["half_quoted_bps"] = (tk["best_ask"] - tk["best_bid"]) / 2.0 / tk["mid"] * 1e4
    ex = pd.merge_asof(ex, tk[["ts", "mid"]], on="ts", direction="backward")
    ex = ex[ex["mid"].notna()].copy()
    ex["eff_bps"] = (ex["price"] - ex["mid"]).abs() / ex["mid"] * 1e4
    ex["minute"] = ex["ts"].dt.floor("min")
    ex["w"] = ex["eff_bps"] * ex["size"]
    g = ex.groupby("minute")
    eff_min = (g["w"].sum() / g["size"].sum()).rename("eff_bps")
    tk["minute"] = tk["ts"].dt.floor("min")
    quoted_min = tk.groupby("minute")["half_quoted_bps"].mean().rename("quoted_bps")
    close_min = g["price"].last().rename("close")
    full = pd.date_range(min(eff_min.index.min(), quoted_min.index.min()),
                         max(eff_min.index.max(), quoted_min.index.max()), freq="min")
    tab = pd.DataFrame(index=full).join(eff_min).join(quoted_min).join(close_min)
    meta.update({
        "minutes": int(len(tab)), "minutes_with_executions": int(tab["eff_bps"].notna().sum()),
        "minutes_with_ticker": int(tab["quoted_bps"].notna().sum()),
        "first_minute": str(tab.index[0]), "last_minute": str(tab.index[-1]),
        "uncond_eff_bps": float(tab["eff_bps"].mean()),
        "uncond_quoted_bps": float(tab["quoted_bps"].mean()),
        "uncond_eff_bps_exec_weighted": float(ex["w"].sum() / ex["size"].sum()),
    })
    rows, coef = [], {}
    for k in KS:
        m = tab["close"] / tab["close"].shift(k) - 1.0
        for thr in THRS:
            sig = (m.abs() > thr / 100.0).to_numpy()
            win = sig | np.roll(sig, 1) | np.roll(sig, -1)
            win[0] &= sig[0] | sig[1]
            win[-1] &= sig[-1] | sig[-2]
            eff_w = tab["eff_bps"].to_numpy()[win]
            q_w = tab["quoted_bps"].to_numpy()[win]
            n_eff = int(np.isfinite(eff_w).sum())
            r_eff = float(np.nanmean(eff_w) / meta["uncond_eff_bps"]) if n_eff else float("nan")
            r_q = float(np.nanmean(q_w) / meta["uncond_quoted_bps"]) if np.isfinite(q_w).any() else float("nan")
            measured = n_eff >= BURST_MIN_WINDOW_MINUTES and np.isfinite(r_eff)
            used = max(1.0, r_eff) if measured else BURST_ASSUMED
            coef[(k, thr)] = used
            rows.append({"k": k, "thr": thr, "n_signal_minutes": int(sig.sum()),
                         "n_window_minutes": int(win.sum()), "n_window_minutes_with_exec": n_eff,
                         "eff_bps_window": float(np.nanmean(eff_w)) if n_eff else float("nan"),
                         "eff_bps_uncond": meta["uncond_eff_bps"], "ratio_eff": r_eff,
                         "quoted_bps_window": float(np.nanmean(q_w)) if np.isfinite(q_w).any() else float("nan"),
                         "quoted_bps_uncond": meta["uncond_quoted_bps"], "ratio_quoted": r_q,
                         "measured": bool(measured), "thin": bool(n_eff < BURST_THIN_WINDOW_MINUTES),
                         "burst_coef_used": used,
                         "cons_one_way_bps": COST_CONS_1W * used})
    meta["measured"] = all(r["measured"] for r in rows)
    return pd.DataFrame(rows), coef, meta


# ---------------------------------------------------------------------------
# per-configuration statistics
# ---------------------------------------------------------------------------

def net_of(a: dict, one_way_bps: float) -> np.ndarray:
    return a["gross_bps"] - 2.0 * one_way_bps - a["funding_bps"]


def _day_id(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").tz_localize(None).value // 86_400_000_000_000)


def period_mask(a: dict, grid: Grid, period: str) -> np.ndarray:
    """Boolean mask over trades by ENTRY day (UTC): train = .. 2021-12-31,
    val = 2022-01-01 .. dev end, val2022 = 2022 only (既知欠陥 (8) の感度)."""
    n = a["n_trades"]
    if period == "full":
        return np.ones(n, dtype=bool)
    ed = grid.day_id[a["entry_i"]] if n else np.zeros(0, dtype=np.int64)
    if period == "train":
        return ed <= _day_id(TRAIN_END)
    if period == "val":
        return ed >= _day_id(VAL_START)
    if period == "val2022":
        return (ed >= _day_id(VAL_START)) & (ed <= _day_id(VAL_2022_END))
    raise ValueError(period)


def quick_stats(a: dict, one_way_bps: float, keep: np.ndarray) -> tuple[float, float, int]:
    """(mean net bps, daily Sharpe, n) on kept trades — the null statistic."""
    net = net_of(a, one_way_bps)
    n = int(keep.sum())
    if n == 0:
        return float("nan"), float("nan"), 0
    d = daily_from_arrays(a["exit_day"], net, keep)
    return float(net[keep].mean()), sharpe_from_daily(d), n


def full_stats(a: dict, grid: Grid, one_way_bps: float, period: str, n_boot: int, seed
               ) -> dict:
    pm = period_mask(a, grid, period)
    keep = pm & ~a["excluded_gap"]
    n = int(keep.sum())
    row = {"n_total_in_period": int(pm.sum()), "n_excluded_gap": int((pm & a["excluded_gap"]).sum()),
           "n": n}
    if n == 0:
        row.update(mean_net_bps=np.nan, ci_lo=np.nan, ci_hi=np.nan, se_cluster=np.nan,
                   sharpe=np.nan, sharpe_ci_lo=np.nan, sharpe_ci_hi=np.nan, win_rate=np.nan,
                   max_dd_bps=np.nan, mean_hold_min=np.nan, stop_rate=np.nan, mean_funding_bps=np.nan,
                   mean_gross_bps=np.nan, sd_net_bps=np.nan, n_days=0, deferred_minutes=0,
                   trades_with_deferral=0, mean_cost_bps=2.0 * one_way_bps, sum_pnl_jpy_001btc=np.nan)
        return row
    net = net_of(a, one_way_bps)[keep]
    base = (a["gross_bps"] - a["funding_bps"])[keep]          # cost-free: CI shifts by a constant
    clusters = a["exit_day"][keep]
    lo, hi, se = cluster_boot_mean(base, clusters, n_boot, seed)
    shift = 2.0 * one_way_bps
    daily = daily_from_arrays(a["exit_day"], net_of(a, one_way_bps), keep)
    s_lo, s_hi = boot_sharpe(daily, n_boot, seed)
    hold = (a["exit_i"] - a["entry_i"])[keep]
    nd = (a["ndef_e"] + a["ndef_x"])[keep]
    row.update({
        "mean_net_bps": float(net.mean()), "ci_lo": lo - shift, "ci_hi": hi - shift,
        "se_cluster": se, "sharpe": sharpe_from_daily(daily), "sharpe_ci_lo": s_lo,
        "sharpe_ci_hi": s_hi, "win_rate": float((net > 0).mean()), "max_dd_bps": max_drawdown(net),
        "mean_hold_min": float(hold.mean()), "stop_rate": float((a["reason"][keep] == 1).mean()),
        "mean_funding_bps": float(a["funding_bps"][keep].mean()),
        "mean_gross_bps": float(a["gross_bps"][keep].mean()), "sd_net_bps": float(net.std(ddof=1)),
        "n_days": int(len(daily)), "deferred_minutes": int(nd.sum()),
        "trades_with_deferral": int((nd > 0).sum()), "mean_cost_bps": shift,
        "sum_pnl_jpy_001btc": float((net / 1e4 * a["entry_px"][keep] * 0.01).sum()),
    })
    return row


# ---------------------------------------------------------------------------
# null draws (multiprocessing, fork)
# ---------------------------------------------------------------------------

_G: dict = {}


def _null_draw(draw: int) -> dict:
    """One permuted world: the SAME rng seed as iteration 0 ([SEED, 1, draw])
    so every iteration shares the worlds; `_G["cfgs"]` lists 4-tuples
    (k, thr, stop, state) and `_G["gates"]` the per-state entry gates
    (state None = no gate = iteration-0 engine call)."""
    t0 = time.perf_counter()
    grid: Grid = _G["grid"]
    bg: BinanceGrid = _G["bg"]
    bp: BlockPermuter = _G["bp"]
    burst: dict = _G["burst"]
    masks = _G["masks"]
    cfgs = _G["cfgs"]
    gates = _G["gates"]
    rng = np.random.default_rng([SEED, 1, draw])
    pc = bp.permute(rng)
    cg = bg.to_bn_grid(pc)
    ms = {k: bg.momentum_from_bn_grid(k, cg) for k in KS}
    out = {"draw": draw}
    for ci, (k, thr, stop, st) in enumerate(cfgs):
        a = simulate_arrays(grid, ms[k], thr, EXIT_PCT, stop, FUNDING_PCT,
                            None if st is None else gates[st])
        c1w = COST_CONS_1W * burst[(k, thr)]
        for period in ("full", "train", "val"):
            keep = masks[period](a) & ~a["excluded_gap"]
            m, s, n = quick_stats(a, c1w, keep)
            out[(ci, period)] = (m, s, n)
    out["seconds"] = time.perf_counter() - t0
    return out


def run_null(grid, bg, bp, burst, n_null: int, workers: int, cfgs=None, gates=None
             ) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """best-of-N null. ``cfgs`` = list of (k, thr, stop, state); default =
    the 27 unconditioned configurations (iteration 0, no `state` column in
    the long table). ``gates`` = {state code: bool grid mask}."""
    with_state = cfgs is not None
    if cfgs is None:
        cfgs = [(k, thr, stop, None) for (k, thr, stop) in CONFIGS]
    _G.update({"grid": grid, "bg": bg, "bp": bp, "burst": burst, "cfgs": cfgs, "gates": gates or {},
               "masks": {p: (lambda a, p=p: period_mask(a, grid, p)) for p in ("full", "train", "val")}})
    _null_draw(0)                                     # JIT warm-up in the parent (cache)
    t0 = time.perf_counter()
    ctx = mp.get_context("fork")
    with ctx.Pool(workers) as pool:
        results = pool.map(_null_draw, range(n_null), chunksize=4)
    wall = time.perf_counter() - t0
    long_rows, best_rows = [], []
    for r in results:
        rec = {"draw": r["draw"], "seconds": r["seconds"]}
        for period in ("full", "train", "val"):
            ms = [r[(ci, period)] for ci in range(len(cfgs))]
            rec[f"max_mean_net_bps_{period}"] = float(np.nanmax([x[0] for x in ms]))
            rec[f"max_sharpe_{period}"] = float(np.nanmax([x[1] for x in ms]))
            rec[f"min_n_{period}"] = int(min(x[2] for x in ms))
        best_rows.append(rec)
        for ci, cfg in enumerate(cfgs):
            for period in ("full", "train", "val"):
                m, s, n = r[(ci, period)]
                row = {"draw": r["draw"], "k": cfg[0], "thr": cfg[1], "stop": cfg[2]}
                if with_state:
                    row["state"] = tercile_label(cfg[3])
                row.update({"period": period, "mean_net_bps": m, "sharpe": s, "n": n})
                long_rows.append(row)
    return pd.DataFrame(best_rows), pd.DataFrame(long_rows), wall


# ---------------------------------------------------------------------------
# controls 1 / 2 on a ledger (arrays)
# ---------------------------------------------------------------------------

def _next_valid(grid: Grid) -> np.ndarray:
    """nv[i] = first valid grid position >= i (grid.n if none); length n + 1."""
    n = grid.n
    valid_pos = np.flatnonzero(grid.valid)
    j = np.searchsorted(valid_pos, np.arange(n + 1))
    nv = np.full(n + 1, n, dtype=np.int64)
    ok = j < len(valid_pos)
    nv[ok] = valid_pos[j[ok]]
    return nv


def _random_trade_stats(grid: Grid, entries: np.ndarray, holds: np.ndarray, sides: np.ndarray,
                        next_valid: np.ndarray, one_way_bps: float) -> tuple[float, float, int]:
    ex = next_valid[np.minimum(entries + holds, grid.n)]
    ok = ex < grid.n
    entries, ex, sides = entries[ok], ex[ok], sides[ok]
    gross = sides * (grid.o[ex] / grid.o[entries] - 1.0) * 1e4
    ns = (np.searchsorted(grid.settle64, grid.idx64[ex], side="right")
          - np.searchsorted(grid.settle64, grid.idx64[entries], side="right"))
    funding = ns * (FUNDING_PCT * 100.0)
    if len(grid.gap_pa):
        kpos = np.searchsorted(grid.gap_pa, entries, side="left")
        strad = (kpos < len(grid.gap_pa)) & (grid.gap_pb[np.minimum(kpos, len(grid.gap_pa) - 1)] <= ex)
    else:
        strad = np.zeros(len(entries), dtype=bool)
    keep = ~strad
    net = gross - 2.0 * one_way_bps - funding
    order = np.argsort(ex[keep], kind="stable")
    d = daily_from_arrays(grid.day_id[ex][keep][order], net[keep][order], np.ones(int(keep.sum()), bool))
    return float(net[keep].mean()), sharpe_from_daily(d), int(keep.sum())


def control_random_times(grid: Grid, a: dict, one_way_bps: float, n_draws: int, seed: int,
                         within_state: bool) -> pd.DataFrame:
    """Control 1: random entry minutes with the trade's own holding-time
    distribution (permuted) and random sides. `within_state=False` = 全時刻
    無作為 (uniform over valid minutes); True = 状態内無作為 (uniform within
    the same UTC hour-of-day × calendar year cell as the actual entry)."""
    keep = ~a["excluded_gap"]
    entry_i = a["entry_i"][keep]
    holds = (a["exit_i"] - a["entry_i"])[keep]
    n = len(entry_i)
    nv = _next_valid(grid)
    valid_pos = np.flatnonzero(grid.valid)
    rng = np.random.default_rng([SEED, 2 + int(within_state), seed])
    if within_state:
        hours = grid.idx.hour.to_numpy()
        years = grid.idx.year.to_numpy()
        cell_all = years * 100 + hours
        cell_tr = cell_all[entry_i]
        buckets = {c: valid_pos[cell_all[valid_pos] == c] for c in np.unique(cell_tr)}
        inv = {c: np.flatnonzero(cell_tr == c) for c in buckets}
    rows = []
    for d in range(n_draws):
        if within_state:
            entries = np.empty(n, dtype=np.int64)
            for c, pos in inv.items():
                b = buckets[c]
                entries[pos] = b[rng.integers(0, len(b), size=len(pos))]
        else:
            entries = valid_pos[rng.integers(0, len(valid_pos), size=n)]
        hold_perm = holds[rng.permutation(n)]
        sides = rng.choice(np.array([-1, 1]), size=n)
        m, s, nn = _random_trade_stats(grid, entries, hold_perm, sides, nv, one_way_bps)
        rows.append({"draw": d, "mean_net_bps": m, "sharpe": s, "n": nn})
    return pd.DataFrame(rows)


def control_sign_shuffle(a: dict, one_way_bps: float, n_draws: int, seed: int) -> pd.DataFrame:
    keep = ~a["excluded_gap"]
    gross = a["gross_bps"][keep]
    funding = a["funding_bps"][keep]
    day = a["exit_day"][keep]
    n = len(gross)
    rng = np.random.default_rng([SEED, 4, seed])
    rows = []
    for d in range(n_draws):
        signs = rng.choice(np.array([-1.0, 1.0]), size=n)
        net = signs * gross - 2.0 * one_way_bps - funding
        dd = daily_from_arrays(day, net, np.ones(n, bool))
        rows.append({"draw": d, "mean_net_bps": float(net.mean()), "sharpe": sharpe_from_daily(dd), "n": n})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------

def cross_correlation(grid: Grid, bg: BinanceGrid) -> pd.DataFrame:
    """corr(r_bn(t), r_bf(t+L)) for L = −10..10 on 1-minute log returns
    (both bars and their predecessors valid); positive L = Binance leads."""
    c_bf = grid.c
    r_bf = np.full(grid.n, np.nan)
    ok = grid.valid[1:] & grid.valid[:-1]
    r_bf[1:][ok] = np.log(c_bf[1:][ok] / c_bf[:-1][ok])
    cl = np.full(grid.n, np.nan)
    cl[bg._ok] = bg.close[bg._pos[bg._ok]]
    r_bn = np.full(grid.n, np.nan)
    ok2 = np.isfinite(cl[1:]) & np.isfinite(cl[:-1])
    r_bn[1:][ok2] = np.log(cl[1:][ok2] / cl[:-1][ok2])
    years = grid.idx.year.to_numpy()
    rows = []
    for lag in LAGS:
        if lag >= 0:
            x, y, yr = r_bn[:grid.n - lag], r_bf[lag:], years[lag:]
        else:
            x, y, yr = r_bn[-lag:], r_bf[:grid.n + lag], years[:grid.n + lag]
        fin = np.isfinite(x) & np.isfinite(y)
        row = {"lag_min": lag, "n": int(fin.sum()),
               "corr_all": float(np.corrcoef(x[fin], y[fin])[0, 1]) if fin.sum() > 2 else np.nan}
        for y_ in DEV_YEARS:
            f2 = fin & (yr == y_)
            row[f"corr_{y_}"] = float(np.corrcoef(x[f2], y[f2])[0, 1]) if f2.sum() > 2 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def per_year_defects(grid: Grid, a: dict, mm: np.ndarray, thr: float) -> pd.DataFrame:
    years = grid.idx.year.to_numpy()
    sig_raw = np.zeros(grid.n, dtype=np.int8)
    has = ~np.isnan(mm)
    sig_raw[has & (mm > thr / 100)] = 1
    sig_raw[has & (mm < -thr / 100)] = -1
    disc = (sig_raw != 0) & grid.discard if grid.discard is not None else np.zeros(grid.n, bool)
    ey = years[a["entry_i"]]
    rows = []
    for y in DEV_YEARS:
        gy = years == y
        ty = ey == y
        rows.append({
            "year": y, "grid_minutes": int(gy.sum()), "empty_minutes": int((gy & ~grid.valid).sum()),
            "big_gaps": int((years[grid.gap_pa] == y).sum()) if len(grid.gap_pa) else 0,
            "entry_signal_bars": int((gy & (sig_raw != 0)).sum()), "signals_discarded": int((gy & disc).sum()),
            "trades": int(ty.sum()), "excluded_gap": int((ty & a["excluded_gap"]).sum()),
            "deferred_entry_minutes": int(a["ndef_e"][ty].sum()), "deferred_exit_minutes": int(a["ndef_x"][ty].sum()),
            "trades_with_deferral": int(((a["ndef_e"] + a["ndef_x"])[ty] > 0).sum()),
            "stops": int((a["reason"][ty] == 1).sum()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# edge trend (§5: unit = week, window = 50 trades) for one ledger
# ---------------------------------------------------------------------------

def edge_trend_for(tag: str, a: dict, grid_m: Grid, c1w: float, n_boot: int, out: Path,
                   written: list[str]) -> dict:
    """{(tag, leg): edge_trend result (+ year_table)} for gross / cost / net,
    writing the rolling and weekly tables. Same computation as iteration 0."""
    edge = {}
    keep = ~a["excluded_gap"]
    dates = grid_m.idx[a["exit_i"][keep]]
    legs = {"gross": a["gross_bps"][keep],
            "cost": np.full(int(keep.sum()), 2.0 * c1w) + a["funding_bps"][keep],
            "net": net_of(a, c1w)[keep]}
    n = int(keep.sum())
    n_weeks = max(1, int(np.ceil((dates[-1] - dates[0]) / pd.Timedelta(days=7)))) if n else 1
    step = max(1, int(round(n / n_weeks)))
    for leg, vals in legs.items():
        res = edge_trend(dates, vals, window=EDGE_WINDOW, block=EDGE_BLOCK, time_unit="week",
                         time_axis="calendar", period="week", n_boot=n_boot, seed=SEED,
                         rolling_step=step)
        year_rows = []
        yrs = dates.year.to_numpy()
        for y in DEV_YEARS:
            seg = vals[yrs == y]
            lo, hi = block_bootstrap_ci(seg, block=EDGE_BLOCK, n_boot=n_boot, seed=SEED) \
                if len(seg) >= EDGE_BLOCK else (np.nan, np.nan)
            year_rows.append({"year": y, "n": int(len(seg)), "mean": float(seg.mean()) if len(seg) else np.nan,
                              "ci_lo": lo, "ci_hi": hi})
        res["year_table"] = pd.DataFrame(year_rows)
        edge[(tag, leg)] = res
        res["rolling"].to_csv(out / f"edge_trend_{tag}_{leg}_rolling.csv", index=False)
        res["period_table"].to_csv(out / f"edge_trend_{tag}_{leg}_weekly.csv", index=False)
        written += [f"edge_trend_{tag}_{leg}_rolling.csv", f"edge_trend_{tag}_{leg}_weekly.csv"]
    return edge


def edge_summary_rows(edge: dict) -> list[dict]:
    rows = []
    for (tag, leg), res in edge.items():
        hs = res["half_split"]
        lw = res["last_window"] or {}
        rows.append({"config": tag, "leg": leg, "n": res["params"]["n"], "slope_bps_per_week": res["slope"],
                     "slope_ci_lo": res["slope_ci"][0], "slope_ci_hi": res["slope_ci"][1],
                     "slope_mde": res["slope_mde"], "mean_first_half": hs["mean_first"],
                     "mean_second_half": hs["mean_second"], "half_diff": hs["diff"],
                     "half_diff_ci_lo": hs["diff_ci"][0], "half_diff_ci_hi": hs["diff_ci"][1],
                     "last_window_mean": lw.get("mean", np.nan), "last_window_ci_lo": lw.get("ci_lo", np.nan),
                     "last_window_ci_hi": lw.get("ci_hi", np.nan), "judgment": res["judgment"],
                     "rolling_step": res["params"]["rolling_step"]})
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(iteration: int, out: Path, n_null: int, n_ctrl: int, n_boot: int, workers: int) -> int:
    T = {}
    t_all = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        p = out / name
        df.to_csv(p, index=False)
        written.append(name)

    # ---- 1. data (dev set only; the loader removes the sealed rows) --------
    t0 = time.perf_counter()
    bf, bn = load_dev_frames()
    T["load_s"] = time.perf_counter() - t0
    summary = summarize(bf, bn, MAX_GAP_MIN)
    input_files = [f"{BF_DIR}/candles_1m_{y}.csv.gz" for y in DEV_YEARS] + \
                  [f"{BN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz" for y in DEV_YEARS]

    # ---- 2. burst coefficient ---------------------------------------------
    t0 = time.perf_counter()
    burst_df, burst, burst_meta = burst_coefficients()
    if not burst:
        burst = {(k, thr): BURST_ASSUMED for k in KS for thr in THRS}
    T["burst_s"] = time.perf_counter() - t0
    if len(burst_df):
        write(burst_df, "burst_factor.csv")

    # ---- 3. grids, signals, 27 configurations × masks ----------------------
    t0 = time.perf_counter()
    grid_m = prepare_grid(bf, MAX_GAP_MIN, True, FUNDING_TIMES)
    grid_u = prepare_grid(bf, MAX_GAP_MIN, False, FUNDING_TIMES)
    bg = BinanceGrid(bn["close"], grid_m)
    mom = {k: bg.momentum(k) for k in KS}
    T["grid_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    arrays: dict = {}
    for masks, grid in (("masked", grid_m), ("unmasked", grid_u)):
        for cfg in CONFIGS:
            k, thr, stop = cfg
            arrays[(masks, cfg)] = simulate_arrays(grid, mom[k], thr, EXIT_PCT, stop, FUNDING_PCT)
    T["sim27x2_s"] = time.perf_counter() - t0

    # reference check: the pandas engine on the current configuration must agree
    t0 = time.perf_counter()
    ref = simulate(bf, momentum_signal(bn["close"], CURRENT[0]), CURRENT[1], EXIT_PCT, CURRENT[2],
                   COST_CONS_1W, FUNDING_PCT, FUNDING_TIMES, MAX_GAP_MIN, True)
    a_cur = arrays[("masked", CURRENT)]
    assert len(ref) == a_cur["n_trades"], (len(ref), a_cur["n_trades"])
    assert np.allclose(ref["gross_bps"].to_numpy(), a_cur["gross_bps"], atol=1e-9)
    assert (pd.DatetimeIndex(ref["exit_ts"]) == grid_m.idx[a_cur["exit_i"]]).all()
    T["reference_check_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    cfg_rows = []
    cell = 0
    for masks, grid in (("masked", grid_m), ("unmasked", grid_u)):
        for cfg in CONFIGS:
            k, thr, stop = cfg
            a = arrays[(masks, cfg)]
            for period in ("full", "train", "val"):
                for cost_name, c1w in (("cons", COST_CONS_1W * burst[(k, thr)]), ("opt", COST_OPT_1W)):
                    cell += 1
                    row = {"k": k, "thr": thr, "stop": stop, "exit": EXIT_PCT, "masks": masks,
                           "period": period, "cost": cost_name, "one_way_bps": c1w,
                           "burst_coef": burst[(k, thr)] if cost_name == "cons" else 1.0,
                           "is_current": cfg == CURRENT,
                           "n_entry_signal_bars": a["n_entry_signal_bars"],
                           "n_entry_signals_discarded": a["n_entry_signals_discarded"]}
                    row.update(full_stats(a, grid, c1w, period, n_boot, [SEED, 5, cell]))
                    cfg_rows.append(row)
    configs = pd.DataFrame(cfg_rows)
    write(configs, "configs.csv")
    T["configs_stats_s"] = time.perf_counter() - t0

    # ---- 4. best configuration (val, masked, conservative) -----------------
    sel = configs[(configs["masks"] == "masked") & (configs["period"] == "val") & (configs["cost"] == "cons")]
    best_row = sel.sort_values("mean_net_bps", ascending=False).iloc[0]
    best = (int(best_row["k"]), float(best_row["thr"]), float(best_row["stop"]))
    best_sharpe_row = sel.sort_values("sharpe", ascending=False).iloc[0]
    best_by_sharpe = (int(best_sharpe_row["k"]), float(best_sharpe_row["thr"]), float(best_sharpe_row["stop"]))
    sel22 = pd.DataFrame([{"k": c[0], "thr": c[1], "stop": c[2],
                           **full_stats(arrays[("masked", c)], grid_m, COST_CONS_1W * burst[(c[0], c[1])],
                                        "val2022", n_boot, [SEED, 6, i])}
                          for i, c in enumerate(CONFIGS)])
    write(sel22, "sensitivity_val_2022_only.csv")
    best22_row = sel22.sort_values("mean_net_bps", ascending=False).iloc[0]
    best22 = (int(best22_row["k"]), float(best22_row["thr"]), float(best22_row["stop"]))

    def stat_of(cfg, period, masks="masked", cost="cons"):
        r = configs[(configs["k"] == cfg[0]) & (configs["thr"] == cfg[1]) & (configs["stop"] == cfg[2])
                    & (configs["masks"] == masks) & (configs["period"] == period) & (configs["cost"] == cost)]
        return r.iloc[0]

    # ledgers of the best and current configurations (masked)
    for tag, cfg in (("best", best), ("current", CURRENT)):
        led = simulate_fast(grid_m, mom[cfg[0]], cfg[1], EXIT_PCT, cfg[2], COST_CONS_1W * burst[(cfg[0], cfg[1])],
                            FUNDING_PCT)
        led["net_bps_opt"] = led["gross_bps"] - 2 * COST_OPT_1W - led["funding_bps"]
        led["split"] = np.where(pd.DatetimeIndex(led["entry_ts"]) <= TRAIN_END, "train", "val")
        led.to_csv(out / f"trades_{tag}.csv.gz", index=False)
        written.append(f"trades_{tag}.csv.gz")

    # ---- 5. null: best-of-27 under day-block permutation of Binance --------
    bp = BlockPermuter(bn["close"], "D")
    null_best, null_all, null_wall = run_null(grid_m, bg, bp, burst, n_null, workers)
    write(null_best, "null_best_of_27.csv")
    null_all.to_csv(out / "null_all_configs.csv.gz", index=False)
    written.append("null_all_configs.csv.gz")
    T["null_wall_s"] = null_wall
    T["null_seconds_per_draw_mean"] = float(null_best["seconds"].mean())
    T["null_seconds_per_draw_median"] = float(null_best["seconds"].median())
    null_p95 = {c: float(np.nanpercentile(null_best[c], 95)) for c in null_best.columns
                if c.startswith("max_")}

    # ---- 6. controls -------------------------------------------------------
    t0 = time.perf_counter()
    ctrl_rows = []
    ctrl_draws = {}
    for tag, cfg in (("best", best), ("current", CURRENT)):
        a = arrays[("masked", cfg)]
        c1w = COST_CONS_1W * burst[(cfg[0], cfg[1])]
        obs = stat_of(cfg, "full")
        for name, df in (("対照1a 全時刻無作為", control_random_times(grid_m, a, c1w, n_ctrl, 0, False)),
                         ("対照1b 状態内無作為(同 UTC 時×年)", control_random_times(grid_m, a, c1w, n_ctrl, 0, True)),
                         ("対照2 符号シャッフル", control_sign_shuffle(a, c1w, n_ctrl, 0))):
            ctrl_draws[(tag, name)] = df
            ctrl_rows.append({"config": tag, "label": cfg_label(cfg), "control": name, "draws": len(df),
                              "obs_mean_net_bps": obs["mean_net_bps"], "null_mean_mean": float(df["mean_net_bps"].mean()),
                              "null_mean_p95": float(np.nanpercentile(df["mean_net_bps"], 95)),
                              "null_mean_p5": float(np.nanpercentile(df["mean_net_bps"], 5)),
                              "obs_sharpe": obs["sharpe"], "null_sharpe_mean": float(df["sharpe"].mean()),
                              "null_sharpe_p95": float(np.nanpercentile(df["sharpe"], 95)),
                              "null_sharpe_p5": float(np.nanpercentile(df["sharpe"], 5)),
                              "n_obs": int(obs["n"]), "n_null_mean": float(df["n"].mean())})
        # control 3: the same configuration's own draws of the permutation null
        sub = null_all[(null_all["k"] == cfg[0]) & (null_all["thr"] == cfg[1]) & (null_all["stop"] == cfg[2])
                       & (null_all["period"] == "full")].head(n_ctrl)
        ctrl_rows.append({"config": tag, "label": cfg_label(cfg), "control": "対照3 先行市場の日ブロック置換(帰無の当該構成のみ)",
                          "draws": len(sub), "obs_mean_net_bps": obs["mean_net_bps"],
                          "null_mean_mean": float(sub["mean_net_bps"].mean()),
                          "null_mean_p95": float(np.nanpercentile(sub["mean_net_bps"], 95)),
                          "null_mean_p5": float(np.nanpercentile(sub["mean_net_bps"], 5)),
                          "obs_sharpe": obs["sharpe"], "null_sharpe_mean": float(sub["sharpe"].mean()),
                          "null_sharpe_p95": float(np.nanpercentile(sub["sharpe"], 95)),
                          "null_sharpe_p5": float(np.nanpercentile(sub["sharpe"], 5)),
                          "n_obs": int(obs["n"]), "n_null_mean": float(sub["n"].mean())})
    controls = pd.DataFrame(ctrl_rows)
    write(controls, "controls.csv")
    for (tag, name), df in ctrl_draws.items():
        key = {"対照1a 全時刻無作為": "control1a_random_all", "対照1b 状態内無作為(同 UTC 時×年)": "control1b_random_state",
               "対照2 符号シャッフル": "control2_sign_shuffle"}[name]
        write(df, f"{key}_{tag}.csv")
    # control 4: same rules on bitFlyer's own momentum
    bg_bf = BinanceGrid(bf["close"].dropna(), grid_m)
    c4_rows = []
    for i, cfg in enumerate(CONFIGS):
        k, thr, stop = cfg
        a4 = simulate_arrays(grid_m, bg_bf.momentum(k), thr, EXIT_PCT, stop, FUNDING_PCT)
        for period in ("full", "train", "val"):
            r = {"k": k, "thr": thr, "stop": stop, "period": period, "is_current": cfg == CURRENT,
                 "n_entry_signal_bars": a4["n_entry_signal_bars"],
                 "n_entry_signals_discarded": a4["n_entry_signals_discarded"]}
            r.update(full_stats(a4, grid_m, COST_CONS_1W * burst[(k, thr)], period, n_boot, [SEED, 7, i]))
            c4_rows.append(r)
    control4 = pd.DataFrame(c4_rows)
    write(control4, "control4_no_lead.csv")
    T["controls_s"] = time.perf_counter() - t0

    # ---- 7. diagnostics ----------------------------------------------------
    t0 = time.perf_counter()
    shift_rows = []
    for tag, cfg in (("best", best), ("current", CURRENT)):
        k, thr, stop = cfg
        for sh in (0,) + SHIFTS:
            if sh == 0:
                mm = mom[k]
            else:
                s2 = bn["close"].copy()
                s2.index = s2.index + pd.Timedelta(minutes=sh)
                mm = BinanceGrid(s2, grid_m).momentum(k)
            a_s = simulate_arrays(grid_m, mm, thr, EXIT_PCT, stop, FUNDING_PCT)
            for period in ("full", "val"):
                r = {"config": tag, "label": cfg_label(cfg), "shift_min": sh, "period": period}
                r.update(full_stats(a_s, grid_m, COST_CONS_1W * burst[(k, thr)], period, n_boot,
                                    [SEED, 8, k, int(sh) + 10]))
                shift_rows.append(r)
    diag_shift = pd.DataFrame(shift_rows)
    write(diag_shift, "diag_a_minute_shift.csv")
    xcorr = cross_correlation(grid_m, bg)
    write(xcorr, "diag_c_cross_correlation.csv")
    T["diagnostics_s"] = time.perf_counter() - t0

    # ---- 8. known defects --------------------------------------------------
    defects = {}
    for tag, cfg in (("best", best), ("current", CURRENT)):
        d = per_year_defects(grid_m, arrays[("masked", cfg)], mom[cfg[0]], cfg[1])
        d.insert(0, "config", tag)
        d.insert(1, "label", cfg_label(cfg))
        defects[tag] = d
    write(pd.concat(defects.values(), ignore_index=True), "known_defects_by_year.csv")
    write(summary["per_year"], "dev_set_summary_by_year.csv")

    # ---- 9. edge trend (§5: unit = week, window = 50 trades) ---------------
    t0 = time.perf_counter()
    edge = {}
    for tag, cfg in (("best", best), ("current", CURRENT)):
        edge.update(edge_trend_for(tag, arrays[("masked", cfg)], grid_m, COST_CONS_1W * burst[(cfg[0], cfg[1])],
                                   n_boot, out, written))
    edge_summary = pd.DataFrame(edge_summary_rows(edge))
    write(edge_summary, "edge_trend_summary.csv")
    for tag in ("best", "current"):
        yt = edge[(tag, "net")]["year_table"].copy()
        yt["gross_mean"] = edge[(tag, "gross")]["year_table"]["mean"]
        yt["cost_mean"] = edge[(tag, "cost")]["year_table"]["mean"]
        yt.insert(0, "config", tag)
        write(yt, f"edge_trend_{tag}_by_year.csv")
    T["edge_trend_s"] = time.perf_counter() - t0

    # ---- 10. MDE reproduction ----------------------------------------------
    mde_rows = []
    for tag, cfg in (("best", best), ("current", CURRENT)):
        r = stat_of(cfg, "full")
        mde_rows.append({"config": tag, "label": cfg_label(cfg), "n": int(r["n"]), "sigma_bps": r["sd_net_bps"],
                         "se_independent": r["sd_net_bps"] / np.sqrt(r["n"]),
                         "mde_independent": MDE_Z * r["sd_net_bps"] / np.sqrt(r["n"]),
                         "se_cluster": r["se_cluster"], "mde_cluster": MDE_Z * r["se_cluster"],
                         "mde_registered": MDE_REGISTERED})
    mde = pd.DataFrame(mde_rows)
    write(mde, "mde.csv")

    T["total_s"] = time.perf_counter() - t_all

    # ---- 11. RESULTS.md ----------------------------------------------------
    md = results_md(iteration, n_null, n_ctrl, n_boot, workers, T, summary, burst_df, burst, burst_meta,
                    configs, best, best_by_sharpe, best22, null_best, null_p95, controls, control4,
                    diag_shift, xcorr, defects, edge_summary, edge, mde, stat_of, written)
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    written.append("RESULTS.md")

    # ---- 12. manifest.json -------------------------------------------------
    manifest = {
        "unit": UNIT, "iteration": iteration, "run_date_utc": pd.Timestamp.now("UTC").isoformat(),
        "seed": SEED, "git_rev": _git_rev(), "script": "scripts/phase2/p2_08_run.py",
        "script_md5": _md5(Path(__file__)),
        "engine_md5": {"xborder_p2.py": _md5(REPO_ROOT / "src/bot/research/xborder_p2.py"),
                       "xborder_p2_fast.py": _md5(REPO_ROOT / "src/bot/research/xborder_p2_fast.py"),
                       "p2_08_data.py": _md5(REPO_ROOT / "scripts/phase2/p2_08_data.py")},
        "inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)} for p in input_files],
        "seal_record": {"path": SEAL_FILE, "md5": _md5(REPO_ROOT / SEAL_FILE)},
        "tape_inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)} for p in burst_meta.get("files", [])],
        "parameters": {"configs": CONFIGS, "exit_pct": EXIT_PCT, "current": CURRENT,
                       "cost_cons_one_way_bps": COST_CONS_1W, "cost_opt_one_way_bps": COST_OPT_1W,
                       "burst_coef": {f"{k}/{thr}": v for (k, thr), v in burst.items()},
                       "burst_assumed_fallback": BURST_ASSUMED, "burst_min_window_minutes": BURST_MIN_WINDOW_MINUTES,
                       "funding_pct_per_settlement": FUNDING_PCT, "funding_times_utc": FUNDING_TIMES,
                       "max_gap_min": MAX_GAP_MIN, "train_end": str(TRAIN_END), "val_start": str(VAL_START),
                       "dev_start": str(DEV_START), "dev_end": str(DEV_END), "n_boot": n_boot, "n_null": n_null,
                       "n_ctrl": n_ctrl, "workers": workers, "edge_window": EDGE_WINDOW, "edge_block": EDGE_BLOCK,
                       "null_block": "D", "null_statistic_periods": ["full", "train", "val"]},
        "burst_meta": burst_meta,
        "timings_s": T,
        "headline": {"best_by_val_mean": cfg_label(best), "best_by_val_sharpe": cfg_label(best_by_sharpe),
                     "best_by_val_2022_only": cfg_label(best22),
                     "null_p95": null_p95},
        "outputs": sorted(set(written)),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
                                       encoding="utf-8")
    print(json.dumps({"best": cfg_label(best), "null_p95": null_p95, "timings": T}, ensure_ascii=False, indent=2))
    print(f"wrote {len(set(written)) + 1} files to {out}")
    return 0


# ---------------------------------------------------------------------------
# iteration 1: realized-volatility tercile conditioning (27 × 3 = 81, N = 108)
# ---------------------------------------------------------------------------

def iter0_cell_index(mi: int, ci: int, pi: int, cost_i: int) -> int:
    """The `cell` counter iteration 0 used for its bootstrap seed
    ([SEED, 5, cell]): 1-based over masks(2) × CONFIGS(27) × period(3) ×
    cost(2) in that nesting order. Reused for the 27 unconditioned cells of
    iteration 1 so those rows reproduce iteration 0 exactly."""
    return ((mi * len(CONFIGS) + ci) * 3 + pi) * 2 + cost_i + 1


def state_minutes_table(grid: Grid, terc: np.ndarray, vol: np.ndarray) -> pd.DataFrame:
    """Per period (full / train / val) and per year: grid minutes, minutes
    with a finite realized vol, and the count / share of each tercile."""
    rows = []
    day = grid.day_id
    years = grid.idx.year.to_numpy()
    fin = np.isfinite(vol)
    groups = [("full", np.ones(grid.n, bool)), ("train", day <= _day_id(TRAIN_END)),
              ("val", day >= _day_id(VAL_START))] + [(str(y), years == y) for y in DEV_YEARS]
    for name, m in groups:
        n_fin = int((m & fin).sum())
        row = {"period": name, "grid_minutes": int(m.sum()), "vol_defined_minutes": n_fin,
               "vol_undefined_minutes": int((m & ~fin).sum()),
               "vol_mean": float(np.nanmean(vol[m])) if n_fin else np.nan,
               "vol_median": float(np.nanmedian(vol[m])) if n_fin else np.nan}
        for code, lab in zip(TERCILE_CODES, TERCILE_LABELS):
            c = int((m & (terc == code)).sum())
            row[f"n_{lab}"] = c
            row[f"share_{lab}"] = c / n_fin if n_fin else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def signal_bars_by_tercile(grid: Grid, mom: dict, terc: np.ndarray) -> pd.DataFrame:
    """Entry-signal bars (after the discard window) per (k, thr) split by the
    tercile at the signal minute, full period."""
    rows = []
    for k in KS:
        for thr in THRS:
            sig, _, n_bars, n_disc = build_signals(grid, mom[k], thr, EXIT_PCT)
            on = sig != 0
            row = {"k": k, "thr": thr, "signal_bars": n_bars, "discarded": n_disc,
                   "signal_bars_kept": int(on.sum()), "no_tercile": int((on & (terc < 0)).sum())}
            for code, lab in zip(TERCILE_CODES, TERCILE_LABELS):
                row[f"n_{lab}"] = int((on & (terc == code)).sum())
            rows.append(row)
    return pd.DataFrame(rows)


def gated_reference_check(bf: pd.DataFrame, grid_m: Grid, mm: np.ndarray, gate: np.ndarray,
                          k: int, thr: float, stop: float) -> dict:
    """The gate must equal, in the pure-pandas reference engine, a momentum
    series whose out-of-gate entry signals are clipped to exactly ±thr (not
    > thr → no entry; not < exit → no exit). Returns the comparison counts;
    raises on any mismatch."""
    m_ref = mm.copy()
    off = (~gate) & np.isfinite(m_ref) & (np.abs(m_ref) > thr / 100.0)
    m_ref[off] = np.sign(m_ref[off]) * (thr / 100.0)
    ref = simulate(bf, pd.Series(m_ref, index=grid_m.idx), thr, EXIT_PCT, stop, COST_CONS_1W,
                   FUNDING_PCT, FUNDING_TIMES, MAX_GAP_MIN, True)
    fast = simulate_fast(grid_m, mm, thr, EXIT_PCT, stop, COST_CONS_1W, FUNDING_PCT, entry_gate=gate)
    assert len(ref) == len(fast), (len(ref), len(fast))
    assert (pd.DatetimeIndex(ref["entry_ts"]) == pd.DatetimeIndex(fast["entry_ts"])).all()
    assert (pd.DatetimeIndex(ref["exit_ts"]) == pd.DatetimeIndex(fast["exit_ts"])).all()
    assert np.allclose(ref["gross_bps"].to_numpy(), fast["gross_bps"].to_numpy(), atol=1e-9)
    assert np.allclose(ref["funding_bps"].to_numpy(), fast["funding_bps"].to_numpy(), atol=1e-9)
    assert ref["excluded_gap"].tolist() == fast["excluded_gap"].tolist()
    return {"n_trades": int(len(fast)), "n_clipped_signal_bars": int(off.sum()),
            "n_entry_signals_gated": int(fast.attrs["n_entry_signals_gated"])}


def condition_analysis(a: dict, grid: Grid, terc: np.ndarray, c1w: float, period: str,
                       n_boot: int) -> dict:
    """PHASE2_TEMPLATES §6 on an UNCONDITIONED ledger: net (conservative)
    per trade split by the tercile at the entry-signal minute (`sig_i`),
    time-ordered, block = EDGE_BLOCK, joint permutation null from
    `state_split`."""
    keep = period_mask(a, grid, period) & ~a["excluded_gap"]
    net = net_of(a, c1w)[keep]
    codes = terc[a["sig_i"][keep]]
    labels = np.array([TERCILE_LABELS[c] if c >= 0 else "" for c in codes], dtype=object)
    res = state_split(net, {"realized_vol_60m_tercile": labels}, block=EDGE_BLOCK, n_boot=n_boot,
                      seed=SEED)
    st = res["state_table"]
    st["sd_bps"] = [float(net[labels == s].std(ddof=1)) if (labels == s).sum() > 1 else np.nan for s in st["state"]]
    st["mde_bps"] = [mde_of(sd, int(n_)) for sd, n_ in zip(st["sd_bps"], st["n"])]
    res["n_no_tercile"] = int((labels == "").sum())
    return res


def main_iter1(out: Path, n_null: int, n_ctrl: int, n_boot: int, workers: int) -> int:
    T = {}
    t_all = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    def write(df: pd.DataFrame, name: str):
        p = out / name
        df.to_csv(p, index=False)
        written.append(name)

    # ---- 1. data (dev set only; the loader removes the sealed rows) --------
    t0 = time.perf_counter()
    bf, bn = load_dev_frames()
    T["load_s"] = time.perf_counter() - t0
    summary = summarize(bf, bn, MAX_GAP_MIN)
    input_files = [f"{BF_DIR}/candles_1m_{y}.csv.gz" for y in DEV_YEARS] + \
                  [f"{BN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz" for y in DEV_YEARS]

    # ---- 2. burst coefficient (same measurement as iteration 0) -----------
    t0 = time.perf_counter()
    burst_df, burst, burst_meta = burst_coefficients()
    if not burst:
        burst = {(k, thr): BURST_ASSUMED for k in KS for thr in THRS}
    T["burst_s"] = time.perf_counter() - t0
    if len(burst_df):
        write(burst_df, "burst_factor.csv")

    # ---- 3. grids, signals, state variable ---------------------------------
    t0 = time.perf_counter()
    grid_m = prepare_grid(bf, MAX_GAP_MIN, True, FUNDING_TIMES)
    grid_u = prepare_grid(bf, MAX_GAP_MIN, False, FUNDING_TIMES)
    bg = BinanceGrid(bn["close"], grid_m)
    mom = {k: bg.momentum(k) for k in KS}
    T["grid_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    vol = {"masked": realized_vol(grid_m, VOL_WINDOW_MIN, VOL_MIN_BARS),
           "unmasked": realized_vol(grid_u, VOL_WINDOW_MIN, VOL_MIN_BARS)}
    in_train = grid_m.day_id <= _day_id(TRAIN_END)
    bounds = tercile_bounds(vol["masked"], in_train)          # frozen on train, masked grid
    terc = {m: assign_tercile(v, bounds) for m, v in vol.items()}
    gates = {m: tercile_gates(t) for m, t in terc.items()}
    grids = {"masked": grid_m, "unmasked": grid_u}
    state_tab = state_minutes_table(grid_m, terc["masked"], vol["masked"])
    write(state_tab, "state_minutes.csv")
    sig_tab = signal_bars_by_tercile(grid_m, mom, terc["masked"])
    write(sig_tab, "signal_bars_by_tercile.csv")
    n_terc_diff = int((terc["masked"] != terc["unmasked"]).sum())
    T["state_s"] = time.perf_counter() - t0

    # ---- 4. 108 configurations × masks -------------------------------------
    t0 = time.perf_counter()
    arrays: dict = {}
    for masks in ("masked", "unmasked"):
        for cfg in CONFIGS_ITER1:
            k, thr, stop, st = cfg
            arrays[(masks, cfg)] = simulate_arrays(grids[masks], mom[k], thr, EXIT_PCT, stop, FUNDING_PCT,
                                                   None if st is None else gates[masks][st])
    T["sim108x2_s"] = time.perf_counter() - t0

    # reference checks: (i) iteration 0's (current configuration, pandas engine);
    # (ii) the gate against the pandas engine with clipped out-of-gate signals
    t0 = time.perf_counter()
    ref = simulate(bf, momentum_signal(bn["close"], CURRENT[0]), CURRENT[1], EXIT_PCT, CURRENT[2],
                   COST_CONS_1W, FUNDING_PCT, FUNDING_TIMES, MAX_GAP_MIN, True)
    a_cur = arrays[("masked", CURRENT + (None,))]
    assert len(ref) == a_cur["n_trades"], (len(ref), a_cur["n_trades"])
    assert np.allclose(ref["gross_bps"].to_numpy(), a_cur["gross_bps"], atol=1e-9)
    assert (pd.DatetimeIndex(ref["exit_ts"]) == grid_m.idx[a_cur["exit_i"]]).all()
    gate_checks = []
    for st in TERCILE_CODES:
        r = gated_reference_check(bf, grid_m, mom[CURRENT[0]], gates["masked"][st], *CURRENT)
        r.update({"k": CURRENT[0], "thr": CURRENT[1], "stop": CURRENT[2], "state": tercile_label(st)})
        gate_checks.append(r)
    gate_checks = pd.DataFrame(gate_checks)
    write(gate_checks, "gate_reference_check.csv")
    T["reference_check_s"] = time.perf_counter() - t0

    # ---- 5. main statistics for every cell ---------------------------------
    t0 = time.perf_counter()
    cfg_rows = []
    cell1 = 0
    for mi, masks in enumerate(("masked", "unmasked")):
        for cfg in CONFIGS_ITER1:
            k, thr, stop, st = cfg
            ci0 = CONFIGS.index((k, thr, stop))
            a = arrays[(masks, cfg)]
            for pi, period in enumerate(("full", "train", "val")):
                for cost_i, (cost_name, c1w) in enumerate((("cons", COST_CONS_1W * burst[(k, thr)]),
                                                           ("opt", COST_OPT_1W))):
                    if st is None:
                        seed = [SEED, 5, iter0_cell_index(mi, ci0, pi, cost_i)]      # = iteration 0's seed
                    else:
                        cell1 += 1
                        seed = [SEED, 15, cell1]
                    row = {"k": k, "thr": thr, "stop": stop, "exit": EXIT_PCT, "state": tercile_label(st),
                           "masks": masks, "period": period, "cost": cost_name, "one_way_bps": c1w,
                           "burst_coef": burst[(k, thr)] if cost_name == "cons" else 1.0,
                           "is_current": (k, thr, stop) == CURRENT and st is None,
                           "is_iter0_best": (k, thr, stop) == ITER0_BEST and st is None,
                           "n_entry_signal_bars": a["n_entry_signal_bars"],
                           "n_entry_signals_discarded": a["n_entry_signals_discarded"],
                           "n_entry_signals_gated": a["n_entry_signals_gated"]}
                    row.update(full_stats(a, grids[masks], c1w, period, n_boot, seed))
                    row["mde_bps"] = mde_of(row["sd_net_bps"], row["n"])
                    row["mde_cluster_bps"] = float(MDE_Z * row["se_cluster"]) if np.isfinite(row["se_cluster"]) else np.nan
                    cfg_rows.append(row)
    configs = pd.DataFrame(cfg_rows)
    write(configs, "configs.csv")
    T["configs_stats_s"] = time.perf_counter() - t0

    # consistency with iteration 0's configs.csv (the 27 unconditioned cells)
    iter0_check = {"available": False}
    p0 = ITER0_DIR / "configs.csv"
    if p0.exists():
        c0 = pd.read_csv(p0)
        c1 = configs[configs["state"] == "all"].drop(columns=["state", "is_iter0_best", "n_entry_signals_gated",
                                                                "mde_bps", "mde_cluster_bps"])
        key = ["k", "thr", "stop", "masks", "period", "cost"]
        m = c0.merge(c1, on=key, suffixes=("_0", "_1"))
        num = [c for c in c0.columns if c not in key and pd.api.types.is_numeric_dtype(c0[c])
               and c0[c].dtype != bool]
        diffs = {c: float(np.nanmax(np.abs(m[f"{c}_0"].to_numpy(float) - m[f"{c}_1"].to_numpy(float))))
                 for c in num}
        iter0_check = {"available": True, "path": str(p0.relative_to(REPO_ROOT)), "md5": _md5(p0),
                       "rows_matched": int(len(m)), "rows_iter0": int(len(c0)),
                       "max_abs_diff_by_column": diffs, "max_abs_diff": max(diffs.values()) if diffs else np.nan}

    # ---- 6. best configuration among the 108 (val, masked, conservative) --
    sel = configs[(configs["masks"] == "masked") & (configs["period"] == "val") & (configs["cost"] == "cons")]

    def _cfg_of(row) -> tuple:
        st = None if row["state"] == "all" else TERCILE_LABELS.index(row["state"])
        return (int(row["k"]), float(row["thr"]), float(row["stop"]), st)

    best = _cfg_of(sel.sort_values("mean_net_bps", ascending=False).iloc[0])
    best_by_sharpe = _cfg_of(sel.sort_values("sharpe", ascending=False).iloc[0])
    sel22 = pd.DataFrame([{"k": c[0], "thr": c[1], "stop": c[2], "state": tercile_label(c[3]),
                           **full_stats(arrays[("masked", c)], grid_m, COST_CONS_1W * burst[(c[0], c[1])],
                                        "val2022", n_boot, [SEED, 16, i])}
                          for i, c in enumerate(CONFIGS_ITER1)])
    write(sel22, "sensitivity_val_2022_only.csv")
    best22 = _cfg_of(sel22.sort_values("mean_net_bps", ascending=False).iloc[0])
    best_uncond = _cfg_of(sel[sel["state"] == "all"].sort_values("mean_net_bps", ascending=False).iloc[0])

    def stat_of(cfg, period, masks="masked", cost="cons"):
        st = tercile_label(cfg[3]) if len(cfg) == 4 else "all"
        r = configs[(configs["k"] == cfg[0]) & (configs["thr"] == cfg[1]) & (configs["stop"] == cfg[2])
                    & (configs["state"] == st) & (configs["masks"] == masks) & (configs["period"] == period)
                    & (configs["cost"] == cost)]
        return r.iloc[0]

    iter0_best4 = ITER0_BEST + (None,)
    cur4 = CURRENT + (None,)
    val_best = float(stat_of(best, "val")["mean_net_bps"])
    val_iter0_best = float(stat_of(iter0_best4, "val")["mean_net_bps"])
    improvement = {"best_iter1": cfg_label(best), "val_mean_net_best_iter1": val_best,
                   "iter0_best": cfg_label(ITER0_BEST), "val_mean_net_iter0_best_recomputed": val_iter0_best,
                   "val_improvement_bps": val_best - val_iter0_best, "mde_registered": MDE_REGISTERED,
                   "val_improvement_over_mde": (val_best - val_iter0_best) / MDE_REGISTERED,
                   "n_val_best_iter1": int(stat_of(best, "val")["n"]),
                   "mde_val_best_iter1": float(stat_of(best, "val")["mde_bps"]),
                   "best_unconditioned_this_run": cfg_label(best_uncond)}
    if iter0_check["available"]:
        r0 = c0[(c0["k"] == ITER0_BEST[0]) & (c0["thr"] == ITER0_BEST[1]) & (c0["stop"] == ITER0_BEST[2])
                & (c0["masks"] == "masked") & (c0["period"] == "val") & (c0["cost"] == "cons")]
        improvement["val_mean_net_iter0_best_from_iter0_file"] = float(r0["mean_net_bps"].iloc[0]) if len(r0) else np.nan

    # ledger of the best configuration (masked)
    k, thr, stop, st = best
    led = simulate_fast(grid_m, mom[k], thr, EXIT_PCT, stop, COST_CONS_1W * burst[(k, thr)], FUNDING_PCT,
                        entry_gate=None if st is None else gates["masked"][st])
    led["net_bps_opt"] = led["gross_bps"] - 2 * COST_OPT_1W - led["funding_bps"]
    led["split"] = np.where(pd.DatetimeIndex(led["entry_ts"]) <= TRAIN_END, "train", "val")
    led["vol_tercile_at_signal"] = [TERCILE_LABELS[c] if c >= 0 else "" for c in
                                    terc["masked"][grid_m.idx.get_indexer(pd.DatetimeIndex(led["entry_signal_ts"]))]]
    led.to_csv(out / "trades_best.csv.gz", index=False)
    written.append("trades_best.csv.gz")

    # ---- 7. null: best-of-108 over the same permuted worlds ----------------
    bp = BlockPermuter(bn["close"], "D")
    null_best, null_all, null_wall = run_null(grid_m, bg, bp, burst, n_null, workers, CONFIGS_ITER1, gates["masked"])
    write(null_best, "null_best_of_108.csv")
    null_all.to_csv(out / "null_all_configs.csv.gz", index=False)
    written.append("null_all_configs.csv.gz")
    T["null_wall_s"] = null_wall
    T["null_seconds_per_draw_mean"] = float(null_best["seconds"].mean())
    T["null_seconds_per_draw_median"] = float(null_best["seconds"].median())
    null_p95 = {c: float(np.nanpercentile(null_best[c], 95)) for c in null_best.columns if c.startswith("max_")}
    # best-of-27 from the same draws (must reproduce iteration 0's null_best_of_27.csv)
    sub27 = null_all[null_all["state"] == "all"]
    b27 = sub27.groupby(["draw", "period"]).agg(max_mean=("mean_net_bps", "max"), max_sharpe=("sharpe", "max")).reset_index()
    null27 = b27.pivot(index="draw", columns="period", values=["max_mean", "max_sharpe"])
    null27.columns = [f"{'max_mean_net_bps' if a == 'max_mean' else 'max_sharpe'}_{p}" for a, p in null27.columns]
    null27 = null27.reset_index()
    write(null27, "null_best_of_27_from_same_draws.csv")
    null27_check = {"available": False}
    p27 = ITER0_DIR / "null_best_of_27.csv"
    if p27.exists():
        n0 = pd.read_csv(p27)
        mm27 = n0.merge(null27, on="draw", suffixes=("_0", "_1"))
        cols = [c for c in null27.columns if c != "draw"]
        d = {c: float(np.nanmax(np.abs(mm27[f"{c}_0"] - mm27[f"{c}_1"]))) for c in cols}
        null27_check = {"available": True, "path": str(p27.relative_to(REPO_ROOT)), "md5": _md5(p27),
                        "draws_matched": int(len(mm27)), "max_abs_diff_by_column": d,
                        "max_abs_diff": max(d.values()) if d else np.nan,
                        "p95_iter0": {c: float(np.nanpercentile(n0[c], 95)) for c in cols},
                        "p95_same_draws_here": {c: float(np.nanpercentile(null27[c], 95)) for c in cols}}

    # ---- 8. controls 2 and 3 for the best configuration only ---------------
    t0 = time.perf_counter()
    a_best = arrays[("masked", best)]
    c1w_best = COST_CONS_1W * burst[(best[0], best[1])]
    obs = stat_of(best, "full")
    ctrl_rows = []
    df2 = control_sign_shuffle(a_best, c1w_best, n_ctrl, 0)
    write(df2, "control2_sign_shuffle_best.csv")
    sub3 = null_all[(null_all["k"] == best[0]) & (null_all["thr"] == best[1]) & (null_all["stop"] == best[2])
                    & (null_all["state"] == tercile_label(best[3])) & (null_all["period"] == "full")].head(n_ctrl)
    for name, df in (("対照2 符号シャッフル", df2), ("対照3 先行市場の日ブロック置換(帰無の当該構成のみ)", sub3)):
        ctrl_rows.append({"config": "best", "label": cfg_label(best), "control": name, "draws": len(df),
                          "obs_mean_net_bps": obs["mean_net_bps"], "null_mean_mean": float(df["mean_net_bps"].mean()),
                          "null_mean_p95": float(np.nanpercentile(df["mean_net_bps"], 95)),
                          "null_mean_p5": float(np.nanpercentile(df["mean_net_bps"], 5)),
                          "obs_sharpe": obs["sharpe"], "null_sharpe_mean": float(df["sharpe"].mean()),
                          "null_sharpe_p95": float(np.nanpercentile(df["sharpe"], 95)),
                          "null_sharpe_p5": float(np.nanpercentile(df["sharpe"], 5)),
                          "n_obs": int(obs["n"]), "n_null_mean": float(df["n"].mean())})
    controls = pd.DataFrame(ctrl_rows)
    write(controls, "controls.csv")
    T["controls_s"] = time.perf_counter() - t0

    # ---- 9. §6 condition analysis on the unconditioned ledgers -------------
    t0 = time.perf_counter()
    cond = {}
    cond_state_rows, cond_diff_rows = [], []
    for tag, cfg in (("iter0_best", iter0_best4), ("current", cur4)):
        for period in ("full", "val"):
            res = condition_analysis(arrays[("masked", cfg)], grid_m, terc["masked"],
                                     COST_CONS_1W * burst[(cfg[0], cfg[1])], period, n_boot)
            cond[(tag, period)] = res
            st_ = res["state_table"].copy()
            st_.insert(0, "period", period)
            st_.insert(0, "label", cfg_label(cfg[:3]))
            st_.insert(0, "config", tag)
            st_["n_no_tercile"] = res["n_no_tercile"]
            cond_state_rows.append(st_)
            dt = res["diff_table"].copy()
            dt.insert(0, "period", period)
            dt.insert(0, "label", cfg_label(cfg[:3]))
            dt.insert(0, "config", tag)
            cond_diff_rows.append(dt)
    cond_state = pd.concat(cond_state_rows, ignore_index=True)
    cond_diff = pd.concat(cond_diff_rows, ignore_index=True)
    write(cond_state, "condition_state_table.csv")
    write(cond_diff, "condition_diff_table.csv")
    T["condition_s"] = time.perf_counter() - t0

    # ---- 10. known defects (best) + dev summary ----------------------------
    d = per_year_defects(grid_m, a_best, mom[best[0]], best[1])
    d.insert(0, "config", "best")
    d.insert(1, "label", cfg_label(best))
    defects = {"best": d}
    write(d, "known_defects_by_year.csv")
    write(summary["per_year"], "dev_set_summary_by_year.csv")

    # ---- 11. edge trend (best only) ----------------------------------------
    t0 = time.perf_counter()
    edge = edge_trend_for("best", a_best, grid_m, c1w_best, n_boot, out, written)
    edge_summary = pd.DataFrame(edge_summary_rows(edge))
    write(edge_summary, "edge_trend_summary.csv")
    yt = edge[("best", "net")]["year_table"].copy()
    yt["gross_mean"] = edge[("best", "gross")]["year_table"]["mean"]
    yt["cost_mean"] = edge[("best", "cost")]["year_table"]["mean"]
    yt.insert(0, "config", "best")
    write(yt, "edge_trend_best_by_year.csv")
    T["edge_trend_s"] = time.perf_counter() - t0

    # ---- 12. MDE -----------------------------------------------------------
    mde_rows = []
    for tag, cfg in (("best", best), ("iter0_best", iter0_best4), ("current", cur4)):
        for period in ("full", "val"):
            r = stat_of(cfg, period)
            mde_rows.append({"config": tag, "label": cfg_label(cfg), "period": period, "n": int(r["n"]),
                             "sigma_bps": r["sd_net_bps"],
                             "se_independent": r["sd_net_bps"] / np.sqrt(r["n"]) if r["n"] else np.nan,
                             "mde_independent": r["mde_bps"], "se_cluster": r["se_cluster"],
                             "mde_cluster": r["mde_cluster_bps"], "mde_registered": MDE_REGISTERED})
    mde = pd.DataFrame(mde_rows)
    write(mde, "mde.csv")

    T["total_s"] = time.perf_counter() - t_all

    # ---- 13. RESULTS.md / manifest.json ------------------------------------
    ctx = dict(n_null=n_null, n_ctrl=n_ctrl, n_boot=n_boot, workers=workers, T=T, summary=summary,
               burst_df=burst_df, burst=burst, burst_meta=burst_meta, bounds=bounds, state_tab=state_tab,
               sig_tab=sig_tab, n_terc_diff=n_terc_diff, gate_checks=gate_checks, configs=configs,
               iter0_check=iter0_check, best=best, best_by_sharpe=best_by_sharpe, best22=best22,
               best_uncond=best_uncond, improvement=improvement, null_best=null_best, null_p95=null_p95,
               null27_check=null27_check, controls=controls, cond=cond, cond_state=cond_state,
               cond_diff=cond_diff, defects=defects, edge_summary=edge_summary, edge=edge, mde=mde,
               stat_of=stat_of, written=written)
    md = results_md_iter1(**ctx)
    (out / "RESULTS.md").write_text(md, encoding="utf-8")
    written.append("RESULTS.md")

    manifest = {
        "unit": UNIT, "iteration": 1, "run_date_utc": pd.Timestamp.now("UTC").isoformat(),
        "seed": SEED, "git_rev": _git_rev(), "script": "scripts/phase2/p2_08_run.py",
        "script_md5": _md5(Path(__file__)),
        "engine_md5": {"xborder_p2.py": _md5(REPO_ROOT / "src/bot/research/xborder_p2.py"),
                       "xborder_p2_fast.py": _md5(REPO_ROOT / "src/bot/research/xborder_p2_fast.py"),
                       "xborder_p2_state.py": _md5(REPO_ROOT / "src/bot/research/xborder_p2_state.py"),
                       "overnight.py": _md5(REPO_ROOT / "src/bot/research/overnight.py"),
                       "p2_08_data.py": _md5(REPO_ROOT / "scripts/phase2/p2_08_data.py")},
        "inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)} for p in input_files],
        "seal_record": {"path": SEAL_FILE, "md5": _md5(REPO_ROOT / SEAL_FILE)},
        "tape_inputs": [{"path": p, "md5": _md5(REPO_ROOT / p)} for p in burst_meta.get("files", [])],
        "iteration0": {"dir": str(ITER0_DIR.relative_to(REPO_ROOT)), "best": cfg_label(ITER0_BEST),
                       "configs_check": iter0_check, "null_best_of_27_check": null27_check},
        "parameters": {"configs_base": CONFIGS, "states": ["all"] + list(TERCILE_LABELS),
                       "n_configs_new": len(CONFIGS_ITER1) - len(CONFIGS), "n_cumulative": N_CUMULATIVE_ITER1,
                       "exit_pct": EXIT_PCT, "current": CURRENT,
                       "state_variable": {"name": "realized_vol_60m_tercile", "window_min": VOL_WINDOW_MIN,
                                          "min_valid_returns": VOL_MIN_BARS, "ddof": 1,
                                          "boundaries_fixed_on": f"train (.. {TRAIN_END}), masked grid, all minutes with finite vol",
                                          "q1": bounds[0], "q2": bounds[1],
                                          "assignment": "vol<=q1 -> 1_low; q1<vol<=q2 -> 2_mid; vol>q2 -> 3_high; NaN -> none (no entry)",
                                          "n_minutes_tercile_differs_masked_vs_unmasked": n_terc_diff},
                       "cost_cons_one_way_bps": COST_CONS_1W, "cost_opt_one_way_bps": COST_OPT_1W,
                       "burst_coef": {f"{k}/{thr}": v for (k, thr), v in burst.items()},
                       "burst_assumed_fallback": BURST_ASSUMED, "burst_min_window_minutes": BURST_MIN_WINDOW_MINUTES,
                       "funding_pct_per_settlement": FUNDING_PCT, "funding_times_utc": FUNDING_TIMES,
                       "max_gap_min": MAX_GAP_MIN, "train_end": str(TRAIN_END), "val_start": str(VAL_START),
                       "dev_start": str(DEV_START), "dev_end": str(DEV_END), "n_boot": n_boot, "n_null": n_null,
                       "n_ctrl": n_ctrl, "workers": workers, "edge_window": EDGE_WINDOW, "edge_block": EDGE_BLOCK,
                       "null_block": "D", "null_statistic_periods": ["full", "train", "val"],
                       "null_draw_seed": "[SEED, 1, draw] (same worlds as iteration 0)"},
        "burst_meta": burst_meta,
        "timings_s": T,
        "headline": {"best_by_val_mean": cfg_label(best), "best_by_val_sharpe": cfg_label(best_by_sharpe),
                     "best_by_val_2022_only": cfg_label(best22), "best_unconditioned": cfg_label(best_uncond),
                     "val_improvement": improvement, "null_p95": null_p95},
        "outputs": sorted(set(written)),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
                                       encoding="utf-8")
    print(json.dumps({"best": cfg_label(best), "bounds": bounds, "val_improvement": improvement,
                      "null_p95": null_p95, "timings": T}, ensure_ascii=False, indent=2, default=str))
    print(f"wrote {len(set(written)) + 1} files to {out}")
    return 0


# ---------------------------------------------------------------------------
# RESULTS.md
# ---------------------------------------------------------------------------

def results_md(iteration, n_null, n_ctrl, n_boot, workers, T, summary, burst_df, burst, burst_meta,
               configs, best, best_by_sharpe, best22, null_best, null_p95, controls, control4,
               diag_shift, xcorr, defects, edge_summary, edge, mde, stat_of, written) -> str:
    md = []
    now_jst = pd.Timestamp.now("Asia/Tokyo")
    md.append(f"# P2-08 反復 {iteration} — 事前登録の主検定(開発セットのみ、2017-08-17 .. 2023-12-17)")
    md.append("")
    md.append(f"実行 {now_jst.strftime('%Y-%m-%d %H:%M')} JST / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT}。"
              "読み込みは `load_unsealed(path, \"P2-08\")` のみ(封印 2023-12-18 以降・フォワードには触れていない)。"
              "実装は盲検(`src/bot/strategy/`・`config/composite.yaml`・`config/config.yaml` の戦略節は読んでいない)。")
    md.append("")
    md.append("**本書は数値の報告のみで、良否・採用・棄却の解釈は行わない。**")
    md.append("")
    md.append("## 0. 実行条件と所要時間")
    md.append("")
    md.append(_table([
        {"a": "構成数 N0", "b": len(CONFIGS)},
        {"a": "帰無の抽選数(best-of-27)", "b": n_null},
        {"a": "対照 1・2・3 の抽選数", "b": n_ctrl},
        {"a": "ブートストラップ回数(CI)", "b": n_boot},
        {"a": "並列(プロセス)", "b": workers},
        {"a": "データ読込(s)", "b": round(T["load_s"], 1)},
        {"a": "格子・信号準備(s)", "b": round(T["grid_s"], 1)},
        {"a": "27 構成 × マスク前後の台帳(s)", "b": round(T["sim27x2_s"], 2)},
        {"a": "純 pandas 版との照合(現行構成 1 本、s)", "b": round(T["reference_check_s"], 1)},
        {"a": "主指標と CI(324 セル、s)", "b": round(T["configs_stats_s"], 1)},
        {"a": "帰無 壁時計(s)", "b": round(T["null_wall_s"], 1)},
        {"a": "帰無 1 抽選あたり(プロセス内、平均 s)", "b": round(T["null_seconds_per_draw_mean"], 3)},
        {"a": "帰無 1 抽選あたり(壁時計 ÷ 抽選数、s)", "b": round(T["null_wall_s"] / max(n_null, 1), 3)},
        {"a": "対照(s)", "b": round(T["controls_s"], 1)},
        {"a": "診断(s)", "b": round(T["diagnostics_s"], 1)},
        {"a": "エッジ推移(s)", "b": round(T["edge_trend_s"], 1)},
        {"a": "合計(s)", "b": round(T["total_s"], 1)},
    ], [("a", "項目", -1), ("b", "値", -1)]))
    md.append("")
    md.append("高速版 `xborder_p2_fast.py`(numba)は純 pandas 版 `xborder_p2.simulate` と、既知正解テスト 5 系統および "
              "開発セット 2021 年の 3 か月 × 3 構成 × マスク前後で台帳が完全一致(取引数・entry/exit ts・全金額列 1e-9)"
              "(`tests/test_xborder_p2_fast.py`)。本実行でも現行構成の台帳を純 pandas 版と突合している。")
    md.append("")

    # ---- 1. data -------------------------------------------------------------
    md.append("## 1. 開発セットの概況(年別)")
    md.append("")
    py = summary["per_year"]
    md.append(_table(py.to_dict("records"), [
        ("year", "年", -1), ("bf_rows", "bf 行", 0), ("bf_empty_rows", "空行", 0), ("bf_absent_minutes", "欠落分", 0),
        ("bf_valid_bars", "有効足", 0), ("bf_empty_share", "空率", 4), ("bf_big_gaps", "5 分超欠損", 0),
        ("bf_big_gap_minutes_missing", "同・欠け分", 0), ("bf_misprint_rows", "誤プリント", 0),
        ("bn_rows", "Binance 行", 0), ("bn_missing_minutes", "同・欠け分", 0)]))
    md.append("")

    # ---- 2. burst ------------------------------------------------------------
    md.append("## 2. バースト係数(WS 記録 `paper_logs/tape`、2026-08-20 .. 09-05)")
    md.append("")
    if len(burst_df):
        md.append(f"約定 {burst_meta['n_executions']:,} 件、ティッカー行 {burst_meta['n_ticker_rows']:,}、"
                  f"分 {burst_meta['minutes']:,}(約定あり {burst_meta['minutes_with_executions']:,}、"
                  f"ティッカーあり {burst_meta['minutes_with_ticker']:,})、{burst_meta['first_minute']} .. {burst_meta['last_minute']}。"
                  f"無条件の実効半スプレッド(分平均)= {burst_meta['uncond_eff_bps']:.3f} bps"
                  f"(約定サイズ加重 {burst_meta['uncond_eff_bps_exec_weighted']:.3f} bps)、"
                  f"無条件の気配半スプレッド = {burst_meta['uncond_quoted_bps']:.3f} bps。")
        md.append("")
        md.append("定義: 実効半スプレッド = |約定価格 − 直前気配の仲値| / 仲値(bps、分内はサイズ加重)、気配半スプレッド = (ask − bid)/2/仲値。"
                  "信号分 = テープ自身の bitFlyer 1 分終値の m_bf(t) = close(t)/close(t−k) − 1 が |m_bf| > thr の分"
                  "(この窓の Binance 分足は本単位では封印のため、bitFlyer 側の同一規則で代用。仮定)。窓 = 信号分 ±1 分。"
                  "比 = 窓内の分平均 ÷ 無条件の分平均。採用係数 = max(1, 実効比)、窓内の約定あり分が "
                  f"{BURST_MIN_WINDOW_MINUTES} 未満なら {BURST_ASSUMED}(仮定)、{BURST_THIN_WINDOW_MINUTES} 未満は「薄い」印。"
                  "(閾値の経緯: 初回のスモーク実行では「測れない」を 100 分未満としていたが、k=15/thr=1.2 のセルが 98 分で"
                  "実測比 2.58 > 仮定 2.0 となり、仮定値の方が甘くなるため、本実行の前に閾値を 30 分に下げて実測を採用した。)")
        md.append("")
        md.append(_table(burst_df.to_dict("records"), [
            ("k", "k", 0), ("thr", "thr(%)", 1), ("n_signal_minutes", "信号分", 0), ("n_window_minutes", "窓分", 0),
            ("n_window_minutes_with_exec", "窓分(約定あり)", 0), ("eff_bps_window", "実効 窓(bps)", 3),
            ("eff_bps_uncond", "実効 無条件", 3), ("ratio_eff", "実効比", 3), ("quoted_bps_window", "気配 窓", 3),
            ("quoted_bps_uncond", "気配 無条件", 3), ("ratio_quoted", "気配比", 3), ("measured", "実測", -1),
            ("thin", "薄い", -1), ("burst_coef_used", "採用係数", 3), ("cons_one_way_bps", "保守 片道(bps)", 3)]))
    else:
        md.append(f"テープが読めなかったため全構成に係数 {BURST_ASSUMED}(仮定)を置いた: {burst_meta.get('reason')}")
    md.append("")

    # ---- 3. configs ------------------------------------------------------------
    cols_main = [("k", "k", 0), ("thr", "thr", 1), ("stop", "stop", 2), ("n", "n", 0), ("n_excluded_gap", "除外", 0),
                 ("mean_net_bps", "平均 net(bps)", 3), ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3),
                 ("sharpe", "Sharpe", 3), ("sharpe_ci_lo", "S CI下", 3), ("sharpe_ci_hi", "S CI上", 3),
                 ("win_rate", "勝率", 4), ("max_dd_bps", "最大DD(bps)", 0), ("mean_hold_min", "保有分", 1),
                 ("stop_rate", "ストップ率", 4), ("mean_funding_bps", "資金調達", 3), ("deferred_minutes", "繰延分", 0),
                 ("trades_with_deferral", "繰延取引", 0), ("n_entry_signals_discarded", "捨て信号(全期間)", 0)]
    md.append("## 3. 27 構成の主指標(`configs.csv`: 27 × {全期間/train/val} × {保守/楽観} × {マスク後/前} = 324 行)")
    md.append("")
    md.append("CI = 取引を決済日(UTC)で束ねたクラスタ・ブートストラップ(percentile 法、"
              f"{n_boot:,} 回)。Sharpe = 日次損益(暦日、取引の無い日は 0)の 平均/SD × √365、CI は日を再抽出。"
              "保守 = 片道 1.3 bps × バースト係数(k, thr ごと)+ 資金調達、楽観 = 片道 1.0 bps + 資金調達。"
              "最大 DD は net bps の累積(1 単位元本)。除外 = 保有中に 5 分超欠損(マスク後のみ)。")
    sub_no = 0
    for masks in ("masked", "unmasked"):
        for cost in ("cons", "opt"):
            for period in ("full", "train", "val"):
                sub_no += 1
                sub = configs[(configs["masks"] == masks) & (configs["cost"] == cost) & (configs["period"] == period)]
                title = {"masked": "マスク後", "unmasked": "マスク前"}[masks] + " / " + \
                        {"cons": "保守", "opt": "楽観"}[cost] + " / " + \
                        {"full": "全期間", "train": "train(..2021-12-31)", "val": "val(2022-01-01..2023-12-17)"}[period]
                md.append("")
                md.append(f"### 3.{sub_no} {title}")
                md.append("")
                md.append(_table(sub.to_dict("records"), cols_main))
    md.append("")

    # ---- 4. best + null --------------------------------------------------------
    md.append("## 4. 最良構成(val で選ぶ)と帰無 A・B")
    md.append("")
    md.append(_table([
        {"a": "val の平均 net(保守・マスク後)最大", "b": cfg_label(best)},
        {"a": "val の日次 Sharpe(保守・マスク後)最大", "b": cfg_label(best_by_sharpe)},
        {"a": "val を 2022 年のみにした場合の平均 net 最大(感度、既知欠陥 (8))", "b": cfg_label(best22)},
        {"a": "現行構成", "b": cfg_label(CURRENT)},
    ], [("a", "選択", -1), ("b", "k/thr/stop", -1)]))
    md.append("")
    rows = []
    for tag, cfg in (("最良", best), ("現行", CURRENT)):
        for period in ("full", "val", "train"):
            r = stat_of(cfg, period)
            rows.append({"cfg": f"{tag} {cfg_label(cfg)}", "period": period, "n": int(r["n"]),
                         "mean": r["mean_net_bps"], "lo": r["ci_lo"], "hi": r["ci_hi"],
                         "nullA": null_p95[f"max_mean_net_bps_{period}"], "sharpe": r["sharpe"],
                         "slo": r["sharpe_ci_lo"], "shi": r["sharpe_ci_hi"], "nullB": null_p95[f"max_sharpe_{period}"]})
    md.append(f"帰無 = Binance の対数リターンを UTC 日ブロックで置換(水準は累積で再構成)して信号を作り直し、"
              f"同じ置換世界で 27 構成の主指標(保守・マスク後)を計算して最大を取る。{n_null:,} 回。"
              "帰無 A = 1 取引平均 net bps、帰無 B = 日次 Sharpe。95 点は期間ごと(全期間・val・train)に別々に取る。")
    md.append("")
    md.append(_table(rows, [("cfg", "構成", -1), ("period", "期間", -1), ("n", "n", 0), ("mean", "平均 net", 3),
                            ("lo", "CI下", 3), ("hi", "CI上", 3), ("nullA", "帰無A 95点", 3), ("sharpe", "Sharpe", 3),
                            ("slo", "S CI下", 3), ("shi", "S CI上", 3), ("nullB", "帰無B 95点", 3)]))
    md.append("")
    md.append("帰無分布の要約(`null_best_of_27.csv`; 全構成 × 全抽選は `null_all_configs.csv.gz`):")
    md.append("")
    nrows = []
    for c in [c for c in null_best.columns if c.startswith("max_")]:
        v = null_best[c].to_numpy(float)
        nrows.append({"stat": c, "mean": float(np.nanmean(v)), "p50": float(np.nanpercentile(v, 50)),
                      "p95": float(np.nanpercentile(v, 95)), "p99": float(np.nanpercentile(v, 99)),
                      "max": float(np.nanmax(v))})
    md.append(_table(nrows, [("stat", "統計量", -1), ("mean", "平均", 3), ("p50", "中央値", 3), ("p95", "95 点", 3),
                             ("p99", "99 点", 3), ("max", "最大", 3)]))
    md.append("")
    md.append(f"1 抽選あたりの所要: プロセス内平均 {T['null_seconds_per_draw_mean']:.3f} s"
              f"(中央値 {T['null_seconds_per_draw_median']:.3f} s)、壁時計 {T['null_wall_s']:.0f} s / {n_null:,} 抽選 = "
              f"{T['null_wall_s'] / max(n_null, 1):.3f} s(プロセス {workers})。1 抽選 = 置換 1 回 + 信号 3 本(k = 15/30/60)+ 27 構成。")
    md.append("")

    # ---- 5. controls -----------------------------------------------------------
    md.append("## 5. 対照")
    md.append("")
    md.append("対照 1a: 有効分から一様に無作為な建玉時刻、保有時間は実取引の分布を並べ替えて付与、方向は無作為(±1)、費用・資金調達・5 分超欠損またぎの除外は同規則。"
              "対照 1b: 同じだが建玉時刻を実取引と同じ UTC 時 × 暦年のセル内から抽出(時刻構造を保つ)。対照 2: 実取引のグロスの符号を無作為化。"
              "対照 3: 帰無(§4)の抽選のうち当該構成だけの分布(最大を取らない)。統計量は全期間・保守・マスク後。")
    md.append("")
    md.append(_table(controls.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop", -1), ("control", "対照", -1), ("draws", "抽選", 0),
        ("obs_mean_net_bps", "実測 平均 net", 3), ("null_mean_mean", "対照 平均", 3), ("null_mean_p5", "対照 5 点", 3),
        ("null_mean_p95", "対照 95 点", 3), ("obs_sharpe", "実測 Sharpe", 3), ("null_sharpe_mean", "対照 Sharpe 平均", 3),
        ("null_sharpe_p5", "5 点", 3), ("null_sharpe_p95", "95 点", 3), ("n_obs", "n 実測", 0), ("n_null_mean", "n 対照", 1)]))
    md.append("")
    md.append("### 対照 4 先行なし(同じ規則を bitFlyer 自身の m(t) に適用、保守・マスク後)")
    md.append("")
    for period in ("full", "val"):
        md.append(f"期間 = {period}")
        md.append("")
        md.append(_table(control4[control4["period"] == period].to_dict("records"), cols_main))
        md.append("")
    md.append("### 対照 5 円換算(BTCUSDT × USDJPY)")
    md.append("")
    md.append("**未実施**。USDJPY 1 分足(Dukascopy、2017-08〜2022-12)は取得中で封印台帳に未登録のため、本反復では枠のみ置く。"
              "取得完了・封印登録後に同じ 27 構成で追記する(判定に使わない対照)。")
    md.append("")

    # ---- 6. diagnostics ---------------------------------------------------------
    md.append("## 6. 診断(判定に使わない)")
    md.append("")
    md.append("### (a) 分の境界のずれ: Binance 系列を ±1、±2 分ずらした信号(保守・マスク後)")
    md.append("")
    md.append("shift = +1 は Binance の各足の時刻を 1 分遅らせる(信号が 1 分遅れて使える)、−1 は 1 分早める(先読み側)。")
    md.append("")
    md.append(_table(diag_shift.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop", -1), ("shift_min", "shift(分)", 0), ("period", "期間", -1),
        ("n", "n", 0), ("mean_net_bps", "平均 net", 3), ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3), ("sharpe", "Sharpe", 3),
        ("win_rate", "勝率", 4), ("stop_rate", "ストップ率", 4)]))
    md.append("")
    md.append("### (b) lightchart と WS 記録由来の分足の一致率")
    md.append("")
    md.append("**未実施**。重なり期間(2026-07-23 .. 09-05)は本単位の封印内(`fx_btc_jpy_1m_continuous_20260906` は全期間封印)のため、最終評価時に併記する。"
              "同じ理由で、既知欠陥 (2) の閉値差の分布と「公式約定と重なる期間での同規則の結果」も本反復では出していない。")
    md.append("")
    md.append("### (c) Binance と bitFlyer の 1 分対数リターンの交差相関(lag > 0 = Binance が先行)")
    md.append("")
    xr = xcorr.copy()
    best_lag = int(xr.loc[xr["corr_all"].idxmax(), "lag_min"])
    md.append(_table(xr.to_dict("records"), [("lag_min", "lag(分)", 0), ("n", "n", 0), ("corr_all", "全期間", 4)]
                     + [(f"corr_{y}", str(y), 4) for y in DEV_YEARS]))
    md.append("")
    md.append(f"全期間で相関が最大の lag = {best_lag} 分(記述のみ。k の候補は変えない)。")
    md.append("")
    md.append("### (d) 現物 BTC_JPY との乖離(CFD ベーシス)、SFD 期の印付け")
    md.append("")
    md.append("**未実施**。現物 BTC_JPY(lightchart)は取得中で封印台帳に未登録のため、本反復では枠のみ置く。"
              "登録後に |ベーシス| ≥ 5% の最中に建てた取引の件数と除外前後の主指標を追記する。")
    md.append("")

    # ---- 7. known defects -------------------------------------------------------
    md.append("## 7. 既知欠陥の報告(マスク後)")
    md.append("")
    for tag, d in defects.items():
        md.append(f"### {'最良' if tag == 'best' else '現行'}構成 {d['label'].iloc[0]}(年別)")
        md.append("")
        md.append(_table(d.to_dict("records"), [
            ("year", "年", -1), ("grid_minutes", "格子分", 0), ("empty_minutes", "空分", 0), ("big_gaps", "5 分超欠損", 0),
            ("entry_signal_bars", "信号足", 0), ("signals_discarded", "捨てた信号", 0), ("trades", "取引", 0),
            ("excluded_gap", "欠損またぎ除外", 0), ("deferred_entry_minutes", "繰延(建て)分", 0),
            ("deferred_exit_minutes", "繰延(決済)分", 0), ("trades_with_deferral", "繰延あり取引", 0), ("stops", "ストップ", 0)]))
        md.append("")
    md.append("制度区分: 開発セットの取引は全件 `lightning_fx`(Lightning FX 期、〜2024-03-28)。資金調達は PREREG のとおり"
              "現行制度(1 日 3 回 0.02%)を全期間に一様適用(保守仮定)。誤プリント(30% 超かつ翌分復帰)の空白化は 0 行。")
    md.append("")
    md.append(f"2023 を val から除いた場合(val = 2022 年のみ)の最良構成 = **{cfg_label(best22)}**"
              f"(val 全体では {cfg_label(best)})。`sensitivity_val_2022_only.csv`。")
    md.append("")

    # ---- 8. edge trend ----------------------------------------------------------
    md.append(f"## 8. エッジ推移(標準 §5、単位 = 週、窓 = {EDGE_WINDOW} 取引、ブロック長 {EDGE_BLOCK} 取引、"
              f"時間軸 = 暦時間、{n_boot:,} 回、保守・マスク後)")
    md.append("")
    md.append("分解: 費用後(net)= グロス − 費用(往復費用 + 資金調達)。傾きは bps/週、MDE = 2.8016 × SE。"
              "移動窓の CI は週あたり約 1 点(`rolling_step` = n ÷ 週数)で評価し、末尾窓は必ず含む。判定文は §5.7 の規則そのまま。")
    md.append("")
    md.append(_table(edge_summary.to_dict("records"), [
        ("config", "構成", -1), ("leg", "脚", -1), ("n", "n", 0), ("slope_bps_per_week", "傾き(bps/週)", 4),
        ("slope_ci_lo", "傾き CI下", 4), ("slope_ci_hi", "CI上", 4), ("slope_mde", "傾き MDE", 4),
        ("mean_first_half", "前半平均", 3), ("mean_second_half", "後半平均", 3), ("half_diff", "後半−前半", 3),
        ("half_diff_ci_lo", "差 CI下", 3), ("half_diff_ci_hi", "差 CI上", 3), ("last_window_mean", "直近窓平均", 3),
        ("last_window_ci_lo", "直近 CI下", 3), ("last_window_ci_hi", "直近 CI上", 3), ("judgment", "判定文", -1),
        ("rolling_step", "step", 0)]))
    md.append("")
    for tag in ("best", "current"):
        yt = edge[(tag, "net")]["year_table"].copy()
        yt["gross"] = edge[(tag, "gross")]["year_table"]["mean"]
        yt["cost"] = edge[(tag, "cost")]["year_table"]["mean"]
        md.append(f"### {'最良' if tag == 'best' else '現行'}構成 年別(net の平均と CI、グロス・費用の平均)")
        md.append("")
        md.append(_table(yt.to_dict("records"), [("year", "年", -1), ("n", "n", 0), ("mean", "net 平均", 3),
                                                 ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3), ("gross", "グロス平均", 3),
                                                 ("cost", "費用平均", 3)]))
        md.append("")
    md.append("週別の区切り表と移動窓は `edge_trend_<config>_<leg>_weekly.csv` / `_rolling.csv`。")
    md.append("")

    # ---- 9. MDE -------------------------------------------------------------------
    md.append("## 9. MDE の再現")
    md.append("")
    md.append(_table(mde.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop", -1), ("n", "n", 0), ("sigma_bps", "σ(bps)", 2),
        ("se_independent", "SE 独立", 4), ("mde_independent", "MDE 独立", 3), ("se_cluster", "SE クラスタ", 4),
        ("mde_cluster", "MDE クラスタ", 3), ("mde_registered", "事前登録 MDE", 2)]))
    md.append("")
    md.append(f"事前登録: σ = {SIGMA_REGISTERED} bps、n = {N_REGISTERED:,}、MDE = {MDE_REGISTERED} bps(現行構成、片道 1.3 bps・バースト係数なし)。"
              "本表の σ は保守費用(バースト係数込み)後の net で、費用は定数のため σ は係数に依存しない。")
    md.append("")

    # ---- 10. interpretation notes ---------------------------------------------------
    md.append("## 10. 事前登録の解釈・仮定・未実施(逸脱の記録)")
    md.append("")
    md.append("- バースト係数の「信号発火時刻」は、テープ窓(2026-08)の Binance 分足が本単位で封印のため、テープ自身の bitFlyer 1 分終値の同一規則(k, thr)で代用した(仮定)。"
              "係数は (k, thr) ごとに採用し、保守費用 = 片道 1.3 bps × 係数 を当該 (k, thr) の全 stop に適用した。")
    md.append("- 最良構成の選択規準は「val の 1 取引平均 net(保守・マスク後)」。日次 Sharpe で選んだ場合の構成も併記した。")
    md.append("- 帰無の主指標は全期間・train・val の 3 通りで別々に最大を取り、95 点を期間ごとに出した(PREREG は期間を明示していない)。")
    md.append("- 対照 1 の「状態内無作為」は「同じ UTC 時 × 暦年のセル内で無作為」と解釈した。")
    md.append(f"- エッジ推移のブロック長({EDGE_BLOCK} 取引)は PREREG に無いため本書で置いた。移動窓の CI は週あたり 1 点に間引いた(末尾窓は含む)。")
    md.append("- 対照 5(円換算)、診断 (b)(重なりが封印内)、診断 (d)(現物ベーシス)、既知欠陥 (2) の閉値差分布、lightchart/公式の同規則併記、"
              "執行差(PAPER 台帳)は本反復では未実施(枠のみ)。")
    md.append("- 資金調達は PREREG どおり全期間に現行制度を一様適用。train/val の区切りは建玉時刻(entry_ts)で判定した。")
    md.append("")
    md.append("## 11. 出力ファイル")
    md.append("")
    for w in sorted(set(written)) + ["RESULTS.md", "manifest.json"]:
        md.append(f"- `{w}`")
    md.append("")
    return "\n".join(md)


def results_md_iter1(n_null, n_ctrl, n_boot, workers, T, summary, burst_df, burst, burst_meta, bounds,
                     state_tab, sig_tab, n_terc_diff, gate_checks, configs, iter0_check, best, best_by_sharpe,
                     best22, best_uncond, improvement, null_best, null_p95, null27_check, controls, cond,
                     cond_state, cond_diff, defects, edge_summary, edge, mde, stat_of, written) -> str:
    md = []
    now_jst = pd.Timestamp.now("Asia/Tokyo")
    n_new = len(CONFIGS_ITER1) - len(CONFIGS)
    md.append("# P2-08 反復 1 — 実現ボラ(60 分)三分位で建玉可否を条件付け(開発セットのみ、2017-08-17 .. 2023-12-17)")
    md.append("")
    md.append(f"実行 {now_jst.strftime('%Y-%m-%d %H:%M')} JST / seed {SEED} / git {_git_rev()[:12]} / 単位 {UNIT}。"
              "読み込みは `load_unsealed(path, \"P2-08\")` のみ(封印 2023-12-18 以降・フォワードには触れていない)。"
              "実装は盲検(`src/bot/strategy/`・`config/composite.yaml`・`config/config.yaml` の戦略節は読んでいない)。"
              f"探索面: 反復 0 の 27 構成 × 三分位 3 = {n_new} 構成を追加、累計 N = {N_CUMULATIVE_ITER1}"
              "(PREREG 探索面「反復の梯子」反復 1)。")
    md.append("")
    md.append("**本書は数値の報告のみで、良否・採用・棄却の解釈は行わない。**")
    md.append("")

    # ---- 0 --------------------------------------------------------------------
    md.append("## 0. 実行条件と所要時間")
    md.append("")
    md.append(_table([
        {"a": "構成数(反復 0 / 追加 / 累計 N)", "b": f"{len(CONFIGS)} / {n_new} / {N_CUMULATIVE_ITER1}"},
        {"a": f"帰無の抽選数(best-of-{N_CUMULATIVE_ITER1})", "b": n_null},
        {"a": "対照 2・3 の抽選数", "b": n_ctrl},
        {"a": "ブートストラップ回数(CI)", "b": n_boot},
        {"a": "並列(プロセス)", "b": workers},
        {"a": "データ読込(s)", "b": round(T["load_s"], 1)},
        {"a": "格子・信号準備(s)", "b": round(T["grid_s"], 1)},
        {"a": "実現ボラ・三分位(s)", "b": round(T["state_s"], 1)},
        {"a": f"{N_CUMULATIVE_ITER1} 構成 × マスク前後の台帳(s)", "b": round(T["sim108x2_s"], 2)},
        {"a": "純 pandas 版との照合(現行構成 + ゲート 3 本、s)", "b": round(T["reference_check_s"], 1)},
        {"a": f"主指標と CI({len(configs):,} セル、s)", "b": round(T["configs_stats_s"], 1)},
        {"a": "帰無 壁時計(s)", "b": round(T["null_wall_s"], 1)},
        {"a": "帰無 1 抽選あたり(プロセス内、平均 s)", "b": round(T["null_seconds_per_draw_mean"], 3)},
        {"a": "帰無 1 抽選あたり(壁時計 ÷ 抽選数、s)", "b": round(T["null_wall_s"] / max(n_null, 1), 3)},
        {"a": "対照(s)", "b": round(T["controls_s"], 1)},
        {"a": "条件分析(s)", "b": round(T["condition_s"], 1)},
        {"a": "エッジ推移(s)", "b": round(T["edge_trend_s"], 1)},
        {"a": "合計(s)", "b": round(T["total_s"], 1)},
    ], [("a", "項目", -1), ("b", "値", -1)]))
    md.append("")
    md.append("反復 0 との整合: 27 の無条件構成は反復 0 と同じ乱数種で再計算しており、`configs.csv` の当該行と、帰無の各抽選の当該構成の統計量は反復 0 の出力と一致しなければならない(§4・§9 に差の最大値を記載)。")
    md.append("")

    # ---- 1 --------------------------------------------------------------------
    md.append("## 1. 開発セットの概況(年別)")
    md.append("")
    md.append(_table(summary["per_year"].to_dict("records"), [
        ("year", "年", -1), ("bf_rows", "bf 行", 0), ("bf_empty_rows", "空行", 0), ("bf_absent_minutes", "欠落分", 0),
        ("bf_valid_bars", "有効足", 0), ("bf_empty_share", "空率", 4), ("bf_big_gaps", "5 分超欠損", 0),
        ("bf_big_gap_minutes_missing", "同・欠け分", 0), ("bf_misprint_rows", "誤プリント", 0),
        ("bn_rows", "Binance 行", 0), ("bn_missing_minutes", "同・欠け分", 0)]))
    md.append("")

    # ---- 2 --------------------------------------------------------------------
    md.append("## 2. バースト係数(WS 記録 `paper_logs/tape`、2026-08-20 .. 09-05、反復 0 と同じ測定)")
    md.append("")
    if len(burst_df):
        md.append(_table(burst_df.to_dict("records"), [
            ("k", "k", 0), ("thr", "thr(%)", 1), ("n_window_minutes_with_exec", "窓分(約定あり)", 0),
            ("ratio_eff", "実効比", 3), ("measured", "実測", -1), ("thin", "薄い", -1),
            ("burst_coef_used", "採用係数", 3), ("cons_one_way_bps", "保守 片道(bps)", 3)]))
    else:
        md.append(f"テープが読めなかったため全構成に係数 {BURST_ASSUMED}(仮定)を置いた: {burst_meta.get('reason')}")
    md.append("")

    # ---- 3 state ---------------------------------------------------------------
    md.append("## 3. 状態変数: 実現ボラ(60 分)三分位")
    md.append("")
    md.append(f"定義: 信号分 t の実現ボラ = bitFlyer 1 分対数リターン r(j) = ln(c(j)/c(j−1)) の j = t−{VOL_WINDOW_MIN - 1} .. t "
              f"({VOL_WINDOW_MIN} 本、終値 c(t−{VOL_WINDOW_MIN}) .. c(t))の標本標準偏差(ddof = 1)。r(j) は c(j−1)・c(j) が"
              f"ともに有効足のときだけ存在(空分・誤プリント空白化分は除く)。有効な r が {VOL_MIN_BARS} 本未満なら NaN → どの三分位にも属さず、"
              "条件付き構成では建玉しない。窓は t を含む(m(t) 自体が close(t) から作られるため、t より後の情報は使わない)。"
              "三分位の境界 q1・q2 = train 期間(.. 2021-12-31 23:59 UTC)の**全格子分**(信号分に限らない)の有限な実現ボラの 33.3 / 66.7 パーセンタイル。"
              "マスク後の格子で決め、マスク前の格子にも同じ値を適用(val にも固定値のまま適用 = look-ahead なし)。"
              "割当: vol ≤ q1 → 1_low、q1 < vol ≤ q2 → 2_mid、vol > q2 → 3_high。条件付け = 「その三分位のときだけ建玉可」"
              "(建玉信号をゲートで落とす。決済・ストップ・繰り延べ・捨て信号・資金調達・欠損除外は無条件構成と同一)。")
    md.append("")
    md.append(_table([
        {"a": "q1(1_low / 2_mid 境界、1 分対数リターンの σ)", "b": f"{bounds[0]:.6e}"},
        {"a": "q2(2_mid / 3_high 境界)", "b": f"{bounds[1]:.6e}"},
        {"a": "q1・q2 を bps に直した値(σ × 1e4)", "b": f"{bounds[0] * 1e4:.3f} / {bounds[1] * 1e4:.3f}"},
        {"a": "マスク前後で三分位が異なる分", "b": f"{n_terc_diff:,}"},
    ], [("a", "項目", -1), ("b", "値", -1)]))
    md.append("")
    md.append("期間・年別の格子分と三分位の分布(マスク後の格子。`state_minutes.csv`):")
    md.append("")
    md.append(_table(state_tab.to_dict("records"), [
        ("period", "期間", -1), ("grid_minutes", "格子分", 0), ("vol_defined_minutes", "ボラ定義あり", 0),
        ("vol_undefined_minutes", "定義なし", 0), ("vol_mean", "ボラ平均", 6), ("vol_median", "中央値", 6),
        ("n_1_low", "n 1_low", 0), ("share_1_low", "比 1_low", 4), ("n_2_mid", "n 2_mid", 0), ("share_2_mid", "比 2_mid", 4),
        ("n_3_high", "n 3_high", 0), ("share_3_high", "比 3_high", 4)]))
    md.append("")
    md.append("建玉信号足(捨て信号除去後、全期間)の三分位別内訳(`signal_bars_by_tercile.csv`):")
    md.append("")
    md.append(_table(sig_tab.to_dict("records"), [
        ("k", "k", 0), ("thr", "thr", 1), ("signal_bars", "信号足", 0), ("discarded", "捨て", 0), ("signal_bars_kept", "残り", 0),
        ("n_1_low", "1_low", 0), ("n_2_mid", "2_mid", 0), ("n_3_high", "3_high", 0), ("no_tercile", "三分位なし", 0)]))
    md.append("")
    md.append("ゲートの既知正解: 現行構成 × 三分位 3 本について、純 pandas 版 `simulate` に「ゲート外の建玉信号を ±thr ちょうどに切り詰めた m」"
              "(建玉にならず、決済にもならない)を渡した台帳と、高速版のゲート付き台帳が完全一致(取引数・entry/exit ts・gross・資金調達・除外)。"
              "`gate_reference_check.csv`:")
    md.append("")
    md.append(_table(gate_checks.to_dict("records"), [
        ("k", "k", 0), ("thr", "thr", 1), ("stop", "stop", 2), ("state", "三分位", -1), ("n_trades", "取引", 0),
        ("n_clipped_signal_bars", "切り詰めた信号足", 0), ("n_entry_signals_gated", "ゲートで落とした信号", 0)]))
    md.append("")

    # ---- 4 configs -------------------------------------------------------------
    cols_main = [("k", "k", 0), ("thr", "thr", 1), ("stop", "stop", 2), ("state", "三分位", -1), ("n", "n", 0),
                 ("n_excluded_gap", "除外", 0), ("mean_net_bps", "平均 net(bps)", 3), ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3),
                 ("mde_bps", "MDE", 3), ("sharpe", "Sharpe", 3), ("sharpe_ci_lo", "S CI下", 3), ("sharpe_ci_hi", "S CI上", 3),
                 ("win_rate", "勝率", 4), ("max_dd_bps", "最大DD(bps)", 0), ("mean_hold_min", "保有分", 1),
                 ("stop_rate", "ストップ率", 4), ("mean_funding_bps", "資金調達", 3), ("deferred_minutes", "繰延分", 0),
                 ("trades_with_deferral", "繰延取引", 0), ("n_entry_signals_gated", "ゲート落ち信号", 0)]
    md.append(f"## 4. {N_CUMULATIVE_ITER1} 構成の主指標(`configs.csv`: {N_CUMULATIVE_ITER1} × {{全期間/train/val}} × {{保守/楽観}} × "
              f"{{マスク後/前}} = {len(configs):,} 行)")
    md.append("")
    md.append("CI = 取引を決済日(UTC)で束ねたクラスタ・ブートストラップ(percentile 法、"
              f"{n_boot:,} 回)。Sharpe = 日次損益(暦日、取引の無い日は 0)の 平均/SD × √365、CI は日を再抽出。"
              "保守 = 片道 1.3 bps × バースト係数(k, thr ごと)+ 資金調達、楽観 = 片道 1.0 bps + 資金調達。"
              "MDE = 2.8016 × σ(net)/√n(セルごと)。最大 DD は net bps の累積(1 単位元本)。除外 = 保有中に 5 分超欠損(マスク後のみ)。"
              "三分位 = all は無条件(反復 0 の構成そのもの)。")
    if iter0_check.get("available"):
        md.append("")
        md.append(f"反復 0 の `configs.csv`(md5 {iter0_check['md5']})との整合: 無条件 27 構成の {iter0_check['rows_matched']} 行"
                  f"(反復 0 は {iter0_check['rows_iter0']} 行)を突合し、数値列の差の最大 = {iter0_check['max_abs_diff']:.3e}。")
    sub_no = 0
    for masks in ("masked", "unmasked"):
        for cost in ("cons", "opt"):
            for period in ("full", "train", "val"):
                sub_no += 1
                sub = configs[(configs["masks"] == masks) & (configs["cost"] == cost) & (configs["period"] == period)]
                title = {"masked": "マスク後", "unmasked": "マスク前"}[masks] + " / " + \
                        {"cons": "保守", "opt": "楽観"}[cost] + " / " + \
                        {"full": "全期間", "train": "train(..2021-12-31)", "val": "val(2022-01-01..2023-12-17)"}[period]
                md.append("")
                md.append(f"### 4.{sub_no} {title}")
                md.append("")
                md.append(_table(sub.to_dict("records"), cols_main))
    md.append("")

    # ---- 5 best + null --------------------------------------------------------
    md.append(f"## 5. 最良構成(val で選ぶ、{N_CUMULATIVE_ITER1} の中)と帰無 A・B(best-of-{N_CUMULATIVE_ITER1})")
    md.append("")
    md.append(_table([
        {"a": "val の平均 net(保守・マスク後)最大", "b": cfg_label(best)},
        {"a": "val の日次 Sharpe(保守・マスク後)最大", "b": cfg_label(best_by_sharpe)},
        {"a": "val を 2022 年のみにした場合の平均 net 最大(感度、既知欠陥 (8))", "b": cfg_label(best22)},
        {"a": "無条件 27 の中での val 最良(本実行での再計算)", "b": cfg_label(best_uncond)},
        {"a": "反復 0 の val 最良(RESULTS.md §4 記載)", "b": cfg_label(ITER0_BEST)},
        {"a": "現行構成", "b": cfg_label(CURRENT)},
    ], [("a", "選択", -1), ("b", "k/thr/stop@三分位", -1)]))
    md.append("")
    imp = improvement
    line = (f"**val 改善量** = 最良 {imp['best_iter1']} の val 平均 net {imp['val_mean_net_best_iter1']:.3f} − "
            f"反復 0 最良 {imp['iter0_best']} の val 平均 net {imp['val_mean_net_iter0_best_recomputed']:.3f} = "
            f"**{imp['val_improvement_bps']:.3f} bps**(事前登録 MDE {imp['mde_registered']} bps、比 {imp['val_improvement_over_mde']:.3f}; "
            f"最良セルの n = {imp['n_val_best_iter1']:,}、同セルの MDE = {imp['mde_val_best_iter1']:.3f} bps)")
    if "val_mean_net_iter0_best_from_iter0_file" in imp:
        line += f"。反復 0 の `configs.csv` に記載の同値 = {imp['val_mean_net_iter0_best_from_iter0_file']:.3f}"
    md.append(line + "。")
    md.append("")
    rows = []
    for tag, cfg in (("最良", best), ("反復0最良", ITER0_BEST + (None,)), ("現行", CURRENT + (None,))):
        for period in ("full", "val", "train"):
            r = stat_of(cfg, period)
            rows.append({"cfg": f"{tag} {cfg_label(cfg)}", "period": period, "n": int(r["n"]),
                         "mean": r["mean_net_bps"], "lo": r["ci_lo"], "hi": r["ci_hi"], "mde": r["mde_bps"],
                         "nullA": null_p95[f"max_mean_net_bps_{period}"], "sharpe": r["sharpe"],
                         "slo": r["sharpe_ci_lo"], "shi": r["sharpe_ci_hi"], "nullB": null_p95[f"max_sharpe_{period}"]})
    md.append(f"帰無 = Binance の対数リターンを UTC 日ブロックで置換(水準は累積で再構成)して信号を作り直し(bitFlyer 側と三分位ゲートはそのまま)、"
              f"同じ置換世界で {N_CUMULATIVE_ITER1} 構成の主指標(保守・マスク後)を計算して最大を取る。{n_null:,} 回、抽選の乱数種は反復 0 と同一"
              "(同じ置換世界)。帰無 A = 1 取引平均 net bps、帰無 B = 日次 Sharpe。95 点は期間ごと(全期間・val・train)に別々に取る。")
    md.append("")
    md.append(_table(rows, [("cfg", "構成", -1), ("period", "期間", -1), ("n", "n", 0), ("mean", "平均 net", 3),
                            ("lo", "CI下", 3), ("hi", "CI上", 3), ("mde", "MDE", 3), ("nullA", "帰無A 95点", 3),
                            ("sharpe", "Sharpe", 3), ("slo", "S CI下", 3), ("shi", "S CI上", 3), ("nullB", "帰無B 95点", 3)]))
    md.append("")
    md.append(f"帰無分布の要約(`null_best_of_{N_CUMULATIVE_ITER1}.csv`; 全構成 × 全抽選は `null_all_configs.csv.gz`):")
    md.append("")
    nrows = []
    for c in [c for c in null_best.columns if c.startswith("max_")]:
        v = null_best[c].to_numpy(float)
        nrows.append({"stat": c, "mean": float(np.nanmean(v)), "p50": float(np.nanpercentile(v, 50)),
                      "p95": float(np.nanpercentile(v, 95)), "p99": float(np.nanpercentile(v, 99)),
                      "max": float(np.nanmax(v))})
    md.append(_table(nrows, [("stat", "統計量", -1), ("mean", "平均", 3), ("p50", "中央値", 3), ("p95", "95 点", 3),
                             ("p99", "99 点", 3), ("max", "最大", 3)]))
    md.append("")
    if null27_check.get("available"):
        p0, p1 = null27_check["p95_iter0"], null27_check["p95_same_draws_here"]
        md.append(f"同じ抽選から無条件 27 構成だけで最大を取った best-of-27(`null_best_of_27_from_same_draws.csv`)と反復 0 の "
                  f"`null_best_of_27.csv`(md5 {null27_check['md5']})の突合: {null27_check['draws_matched']:,} 抽選、"
                  f"差の最大 = {null27_check['max_abs_diff']:.3e}。95 点(反復 0 / 本実行): "
                  + "、".join(f"{c} {p0[c]:.3f} / {p1[c]:.3f}" for c in p0) + "。")
        md.append("")
    md.append(f"1 抽選あたりの所要: プロセス内平均 {T['null_seconds_per_draw_mean']:.3f} s"
              f"(中央値 {T['null_seconds_per_draw_median']:.3f} s)、壁時計 {T['null_wall_s']:.0f} s / {n_null:,} 抽選 = "
              f"{T['null_wall_s'] / max(n_null, 1):.3f} s(プロセス {workers})。"
              f"1 抽選 = 置換 1 回 + 信号 3 本(k = 15/30/60)+ {N_CUMULATIVE_ITER1} 構成(無条件 27 + ゲート付き 81)。")
    md.append("")

    # ---- 6 controls -------------------------------------------------------------
    md.append("## 6. 対照(最良構成のみ、反復 0 の対照 2・3)")
    md.append("")
    md.append("対照 2: 実取引のグロスの符号を無作為化。対照 3: 帰無(§5)の抽選のうち当該構成だけの分布(最大を取らない)。統計量は全期間・保守・マスク後。"
              "対照 1・4・5 と診断 (a)〜(d) は本反復では繰り返さない(反復 0 の出力を参照)。")
    md.append("")
    md.append(_table(controls.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop@三分位", -1), ("control", "対照", -1), ("draws", "抽選", 0),
        ("obs_mean_net_bps", "実測 平均 net", 3), ("null_mean_mean", "対照 平均", 3), ("null_mean_p5", "対照 5 点", 3),
        ("null_mean_p95", "対照 95 点", 3), ("obs_sharpe", "実測 Sharpe", 3), ("null_sharpe_mean", "対照 Sharpe 平均", 3),
        ("null_sharpe_p5", "5 点", 3), ("null_sharpe_p95", "95 点", 3), ("n_obs", "n 実測", 0), ("n_null_mean", "n 対照", 1)]))
    md.append("")

    # ---- 7 condition analysis ----------------------------------------------------
    md.append(f"## 7. 条件分析(標準 §6、`state_split`: 無条件台帳を建玉信号分の三分位で分割、ブロック長 {EDGE_BLOCK} 取引、{n_boot:,} 回、保守・マスク後)")
    md.append("")
    md.append("§4 の条件付き構成は「その三分位のときだけ建玉」した独立の台帳で、本節は反復 0 最良と現行構成の**無条件**台帳の各取引を"
              "建玉信号分の三分位で事後に分けたもの(同時に 1 建玉の制約のため両者の取引集合は一致しない)。差 = 状態 a − 状態 b、"
              "CI は両状態のブロック・ブートストラップ差、MDE = 2.8016 × SE、帰無 95 点 = 値系列のブロック順序置換で全対の最大絶対差を取ったものの 95 点。"
              "判定文は `state_split` の規則(候補 / 判定不能 / 差なし)そのまま。")
    md.append("")
    md.append(_table(cond_state.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop", -1), ("period", "期間", -1), ("state", "三分位", -1), ("n", "n", 0),
        ("mean", "平均 net", 3), ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3), ("sd_bps", "σ", 2), ("mde_bps", "MDE", 3),
        ("n_no_tercile", "三分位なし(除外)", 0)]))
    md.append("")
    md.append(_table(cond_diff.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop", -1), ("period", "期間", -1), ("state_a", "a", -1), ("state_b", "b", -1),
        ("n_a", "n a", 0), ("n_b", "n b", 0), ("mean_a", "平均 a", 3), ("mean_b", "平均 b", 3), ("diff", "差", 3),
        ("ci_lo", "差 CI下", 3), ("ci_hi", "差 CI上", 3), ("mde", "MDE", 3), ("null_p95", "帰無 95 点", 3), ("verdict", "判定文", -1)]))
    md.append("")
    for (tag, period), res in cond.items():
        vs = res["verdict"]
        by = {}
        for (var, a_, b_), v in vs.items():
            by.setdefault(v, []).append(f"{a_} vs {b_}")
        md.append(f"- {tag} / {period}: " + "; ".join(f"{v}: {', '.join(p)}" for v, p in by.items()))
    md.append("")

    # ---- 8 known defects -------------------------------------------------------
    md.append("## 8. 既知欠陥の報告(最良構成、マスク後)")
    md.append("")
    d = defects["best"]
    md.append(f"### 最良構成 {d['label'].iloc[0]}(年別)")
    md.append("")
    md.append(_table(d.to_dict("records"), [
        ("year", "年", -1), ("grid_minutes", "格子分", 0), ("empty_minutes", "空分", 0), ("big_gaps", "5 分超欠損", 0),
        ("entry_signal_bars", "信号足(ゲート前)", 0), ("signals_discarded", "捨てた信号", 0), ("trades", "取引", 0),
        ("excluded_gap", "欠損またぎ除外", 0), ("deferred_entry_minutes", "繰延(建て)分", 0),
        ("deferred_exit_minutes", "繰延(決済)分", 0), ("trades_with_deferral", "繰延あり取引", 0), ("stops", "ストップ", 0)]))
    md.append("")
    md.append("制度区分: 開発セットの取引は全件 `lightning_fx`。資金調達は PREREG のとおり現行制度(1 日 3 回 0.02%)を全期間に一様適用(保守仮定)。"
              f"2023 を val から除いた場合(val = 2022 年のみ)の最良構成 = **{cfg_label(best22)}**(val 全体では {cfg_label(best)})。"
              "`sensitivity_val_2022_only.csv`。")
    md.append("")

    # ---- 9 edge trend ---------------------------------------------------------------
    md.append(f"## 9. エッジ推移(最良構成のみ。標準 §5、単位 = 週、窓 = {EDGE_WINDOW} 取引、ブロック長 {EDGE_BLOCK} 取引、"
              f"時間軸 = 暦時間、{n_boot:,} 回、保守・マスク後)")
    md.append("")
    md.append(_table(edge_summary.to_dict("records"), [
        ("config", "構成", -1), ("leg", "脚", -1), ("n", "n", 0), ("slope_bps_per_week", "傾き(bps/週)", 4),
        ("slope_ci_lo", "傾き CI下", 4), ("slope_ci_hi", "CI上", 4), ("slope_mde", "傾き MDE", 4),
        ("mean_first_half", "前半平均", 3), ("mean_second_half", "後半平均", 3), ("half_diff", "後半−前半", 3),
        ("half_diff_ci_lo", "差 CI下", 3), ("half_diff_ci_hi", "差 CI上", 3), ("last_window_mean", "直近窓平均", 3),
        ("last_window_ci_lo", "直近 CI下", 3), ("last_window_ci_hi", "直近 CI上", 3), ("judgment", "判定文", -1),
        ("rolling_step", "step", 0)]))
    md.append("")
    yt = edge[("best", "net")]["year_table"].copy()
    yt["gross"] = edge[("best", "gross")]["year_table"]["mean"]
    yt["cost"] = edge[("best", "cost")]["year_table"]["mean"]
    md.append(f"### 最良構成 {cfg_label(best)} 年別(net の平均と CI、グロス・費用の平均)")
    md.append("")
    md.append(_table(yt.to_dict("records"), [("year", "年", -1), ("n", "n", 0), ("mean", "net 平均", 3),
                                             ("ci_lo", "CI下", 3), ("ci_hi", "CI上", 3), ("gross", "グロス平均", 3),
                                             ("cost", "費用平均", 3)]))
    md.append("")

    # ---- 10 MDE ----------------------------------------------------------------------
    md.append("## 10. MDE")
    md.append("")
    md.append(_table(mde.to_dict("records"), [
        ("config", "構成", -1), ("label", "k/thr/stop@三分位", -1), ("period", "期間", -1), ("n", "n", 0), ("sigma_bps", "σ(bps)", 2),
        ("se_independent", "SE 独立", 4), ("mde_independent", "MDE 独立", 3), ("se_cluster", "SE クラスタ", 4),
        ("mde_cluster", "MDE クラスタ", 3), ("mde_registered", "事前登録 MDE", 2)]))
    md.append("")

    # ---- 11 notes ----------------------------------------------------------------------
    md.append("## 11. 事前登録の解釈・仮定(本反復で決めた点の記録)")
    md.append("")
    md.append(f"- 実現ボラの窓は「信号分 t を末尾に含む {VOL_WINDOW_MIN} 本の 1 分対数リターン」(終値 c(t−{VOL_WINDOW_MIN}) .. c(t))とした。"
              "「直前 60 分」を t を含まない窓(c(t−61) .. c(t−1))と読む解釈も可能だが、m(t) が close(t) で作られる以上 close(t) は建玉判断時に既知なので、"
              "t を含める方を採った(仮定)。")
    md.append(f"- 「空分は除く」= 両端が有効足の r だけを数え、有効 r が {VOL_MIN_BARS} 本未満なら NaN(建玉なし)。σ は ddof = 1。")
    md.append("- 三分位の母集団は train の全格子分(ボラが定義される分)。信号分だけの分布で切る解釈もあるが、それは (k, thr) ごとに境界が変わり"
              "「状態変数」として一意でなくなるため採らなかった(仮定)。境界はマスク後の格子で決め、マスク前の格子にも同じ値を適用した。")
    md.append("- 条件付けは建玉信号のゲートのみ。三分位が NaN の分(窓の有効足不足)はどの条件付き構成でも建玉しない。")
    md.append("- 無条件 27 構成のブートストラップ乱数種は反復 0 と同一(`iter0_cell_index`)、条件付き 81 構成は別系列([SEED, 15, 通し番号])。"
              "帰無の抽選乱数種は反復 0 と同一([SEED, 1, draw])で、置換世界を共有する。")
    md.append("- val 改善量は「最良 108 の val 平均 net − 反復 0 最良(15/0.4/0.5)の val 平均 net」の点差のみ(差の CI は出していない)。"
              "反復 0 最良の値は本実行で再計算した値を使い、反復 0 の `configs.csv` の値を併記した。")
    md.append("- 対照 1・4・5、診断 (a)〜(d)、執行差は本反復では繰り返していない(反復 0 と同じ台帳・同じ未実施事項)。")
    md.append("- 条件分析(§7)は無条件台帳の事後分割であり、§4 の条件付き構成(独立に建玉した台帳)とは取引集合が異なる。")
    md.append("")
    md.append("## 12. 出力ファイル")
    md.append("")
    for w in sorted(set(written)) + ["RESULTS.md", "manifest.json"]:
        md.append(f"- `{w}`")
    md.append("")
    return "\n".join(md)


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--iteration", type=int, default=0, choices=(0, 1))
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--n-null", type=int, default=N_NULL)
    p.add_argument("--n-ctrl", type=int, default=N_CTRL)
    p.add_argument("--n-boot", type=int, default=N_BOOT)
    p.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    if args.iteration == 1:
        out = args.out if args.out is not None else OUT_DIR_ITER1
        raise SystemExit(main_iter1(out, args.n_null, args.n_ctrl, args.n_boot, args.workers))
    out = args.out if args.out is not None else OUT_DIR
    raise SystemExit(main(args.iteration, out, args.n_null, args.n_ctrl, args.n_boot, args.workers))
