#!/usr/bin/env python3
"""TP (tape-scale burst precursor) -- continuous-time operating curve.

Reference record for docs/PREREG_board_round.md section 3, stage 2. NOT a
judgment: it turns the screened features into real-time alarm statistics so
that a stage-2 operating point can be fixed BEFORE stage-2 data exists.

Real-time definition (5-second bins, validity mask as in judge_board_round):
  feature(t) = statistic over the trailing window [t-120s, t]
      avg_spread_bps  : mean spread_bps
      board_update_rate: sum of n_board_updates
      realized_move    : |ln(mid_t / mid_{t-120s})| in bps  (benchmark: vol persistence)
      combined         : mean of the two screened features' percentile ranks
  burst onset t0     : first bin where |60s mid move| >= 20bps after >= 30 min
                       without such a move (same as the judge)
  alarm at t         : feature(t) >= threshold; a 60s refractory period after
                       each alarm so one episode is counted once
  hit                : a burst onset occurs in (t, t+180s]
  recall             : bursts with >= 1 alarm inside [t0-180s, t0-60s]
Thresholds are the feature's percentiles over all valid bins: 90/95/97.5/99/99.5.

Usage: PYTHONPATH=src python scripts/tp_operating_curve.py [--series PATH] [--report PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from judge_board_round import apply_qc, load_series  # noqa: E402

BIN = 5
WIN = 120 // BIN          # trailing feature window, bins
LEAD_MAX = 180 // BIN     # alarm horizon, bins
LEAD_MIN = 60 // BIN      # precursor window ends 60s before onset
REFRACT = 60 // BIN
QUIET = 1800 // BIN
PCTS = (90.0, 95.0, 97.5, 99.0, 99.5)


def burst_onsets(mid: pd.Series) -> np.ndarray:
    """Indices of burst onsets on the (possibly NaN-holed) 5s grid."""
    m60 = (np.log(mid) - np.log(mid.shift(60 // BIN))).abs() * 1e4
    hit = (m60 >= 20.0).to_numpy()
    onsets, last = [], -10**9
    for i, h in enumerate(hit):
        if h:
            if i - last >= QUIET:
                onsets.append(i)
            last = i
    return np.asarray(onsets, dtype=int)


def features(s: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=s.index)
    f["avg_spread_bps"] = s["spread_bps"].rolling(WIN, min_periods=WIN).mean()
    f["board_update_rate"] = s["n_board_updates"].rolling(WIN, min_periods=WIN).sum()
    f["realized_move"] = (np.log(s["mid"]) - np.log(s["mid"].shift(WIN))).abs() * 1e4
    ranks = f[["avg_spread_bps", "board_update_rate"]].rank(pct=True)
    f["combined"] = ranks.mean(axis=1)
    # relative-to-baseline variants: current 120s window divided by the median
    # of the same statistic over the preceding 30 minutes (window excluded),
    # i.e. "quiet -> restless" change rather than absolute level
    base_n = QUIET  # 30 min of bins
    for col in ["avg_spread_bps", "board_update_rate", "realized_move"]:
        base = f[col].shift(WIN).rolling(base_n, min_periods=base_n // 2).median()
        f["rel_" + col] = f[col] / base.replace(0, np.nan)
    rel_ranks = f[["rel_avg_spread_bps", "rel_board_update_rate"]].rank(pct=True)
    f["rel_combined"] = rel_ranks.mean(axis=1)
    return f


def curve(f: pd.Series, onsets: np.ndarray, valid: np.ndarray, days: float,
          burst_bins: np.ndarray) -> list[dict]:
    x = f.to_numpy()
    ok = valid & np.isfinite(x)
    # for each bin: is there an onset (first burst after >=30 min quiet) in (t, t+LEAD_MAX]?
    fut = np.zeros(len(x), dtype=bool)
    for o in onsets:
        fut[max(0, o - LEAD_MAX):o] = True
    # "any burst" variant: hit if ANY burst bin (|60s move| >= 20bps) lies in
    # (t, t+LEAD_MAX]; only alarms raised while no burst bin occurred in the
    # last 60s are eligible (the burst must not have started yet)
    fut_any = np.zeros(len(x), dtype=bool)
    for b in np.flatnonzero(burst_bins):
        fut_any[max(0, b - LEAD_MAX):b] = True
    recent = np.zeros(len(x), dtype=bool)
    for b in np.flatnonzero(burst_bins):
        recent[b:b + LEAD_MIN + 1] = True
    eligible = ok & ~recent
    rows = []
    for p in PCTS:
        thr = np.nanpercentile(x[ok], p)
        alarm_idx = []
        last = -10**9
        for i in np.flatnonzero(ok & (x >= thr)):
            if i - last >= REFRACT:
                alarm_idx.append(i)
                last = i
        alarm_idx = np.asarray(alarm_idx, dtype=int)
        hits = int(fut[alarm_idx].sum()) if len(alarm_idx) else 0
        el = alarm_idx[eligible[alarm_idx]] if len(alarm_idx) else alarm_idx
        hits_any = int(fut_any[el].sum()) if len(el) else 0
        prec_any = hits_any / len(el) if len(el) else float("nan")
        # recall: onset with >= 1 alarm bin (pre-refractory) in [t0-180s, t0-60s]
        raw_alarm = ok & (x >= thr)
        rec = sum(bool(raw_alarm[max(0, o - LEAD_MAX):max(0, o - LEAD_MIN) + 1].any())
                  for o in onsets)
        rows.append(dict(pct=p, thr=thr, alarms=len(alarm_idx),
                         alarms_per_day=len(alarm_idx) / days,
                         precision=hits / len(alarm_idx) if len(alarm_idx) else float("nan"),
                         recall=rec / len(onsets) if len(onsets) else float("nan"),
                         eligible=len(el), precision_any=prec_any))
    return rows


def base_rate_any(valid: np.ndarray, burst_bins: np.ndarray) -> float:
    """Share of eligible (no burst in the last 60s) valid bins that are
    followed by a burst bin within LEAD_MAX -- the 'any burst' base rate."""
    fut_any = np.zeros(len(valid), dtype=bool)
    recent = np.zeros(len(valid), dtype=bool)
    for b in np.flatnonzero(burst_bins):
        fut_any[max(0, b - LEAD_MAX):b] = True
        recent[b:b + LEAD_MIN + 1] = True
    el = valid & ~recent
    return float(fut_any[el].mean()) if el.any() else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="backtest_data/board_round_20260904/board_round_series_5s.csv.gz")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    df, _counts = apply_qc(load_series(Path(a.series)))
    # complete 5s grid so every shift/rolling is time-based; recording gaps
    # become NaN rows and break windows exactly like the judge's gap rule
    grid = np.arange(df["bin_idx"].min(), df["bin_idx"].max() + 1)
    s = df.set_index("bin_idx").reindex(grid)
    s.index = pd.to_datetime(s.index * BIN, unit="s", utc=True)
    valid = s["valid"].fillna(False).to_numpy(bool) & s["mid"].notna().to_numpy()
    s.loc[~valid, "spread_bps"] = np.nan
    days = valid.sum() * BIN / 86400
    onsets = burst_onsets(s["mid"])
    m60 = (np.log(s["mid"]) - np.log(s["mid"].shift(60 // BIN))).abs() * 1e4
    burst_bins = (m60 >= 20.0).to_numpy()
    onset_base = len(onsets) * LEAD_MAX / max(valid.sum(), 1)
    f = features(s)
    lines = [f"series {s.index[0]} .. {s.index[-1]}  valid_days={days:.2f}  onsets={len(onsets)} "
             f"({len(onsets)/days:.2f}/day)  burst bins={int(burst_bins.sum())}  alarm horizon 180s, refractory 60s",
             f"base rate: onset-within-180s {onset_base:.3f}   any-burst-within-180s (eligible bins) "
             f"{base_rate_any(valid, burst_bins):.3f}",
             ""]
    for col in ["avg_spread_bps", "board_update_rate", "combined", "realized_move",
                "rel_avg_spread_bps", "rel_board_update_rate", "rel_combined", "rel_realized_move"]:
        lines.append(f"[{col}]" + ("  (benchmark)" if "realized_move" in col else ""))
        lines.append(f"{'pct':>6} {'thr':>10} {'alarms':>7} {'per_day':>8} {'prec_onset':>10} {'recall':>7} "
                     f"{'eligible':>8} {'prec_any':>8}")
        for r in curve(f[col], onsets, valid, days, burst_bins):
            lines.append(f"{r['pct']:6.1f} {r['thr']:10.3f} {r['alarms']:7d} {r['alarms_per_day']:8.2f} "
                         f"{r['precision']:10.3f} {r['recall']:7.3f} {r['eligible']:8d} {r['precision_any']:8.3f}")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if a.report:
        Path(a.report).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
