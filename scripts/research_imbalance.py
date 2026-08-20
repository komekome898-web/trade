#!/usr/bin/env python3
"""Book-imbalance vs forward mid return on recorded FX_BTC_JPY board data.

Replays every recording in data/ws/ into a 1-second order-book series and
asks one causal question: does depth imbalance at time t predict the mid
log-return over the NEXT {1,3,5,10,30} seconds? Imbalance at t is measured
from the book state at the close of second t; every return it is compared
against starts at t and ends strictly later, so nothing peeks forward.

Offline only — reads files, opens no sockets, places no orders.

Usage: python scripts/research_imbalance.py [--depth-bps 5] [--data DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bot.research.board import build_series  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (1, 3, 5, 10, 30)
THRESHOLD = 0.3
MIN_MINUTES = 30.0  # below this the table is a smoke test, not evidence


def forward_bps(mid: pd.Series, horizon: int) -> pd.Series:
    """Mid log-return from t to t+horizon seconds, in bps.

    Looked up by TIMESTAMP, not by row offset: t+h must actually exist in
    the series, so a return is never taken across a gap between recording
    sessions. Causal — the future leg is strictly later than t.
    """
    future = mid.reindex(mid.index + pd.Timedelta(seconds=horizon))
    aligned = pd.Series(future.to_numpy(), index=mid.index)
    return (np.log(aligned) - np.log(mid)) * 1e4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "ws"),
                    help="directory of *.jsonl.gz recordings")
    ap.add_argument("--depth-bps", type=float, default=5.0,
                    help="half-width of the depth band around the mid")
    args = ap.parse_args()

    paths = sorted(Path(args.data).glob("*.jsonl.gz"))
    if not paths:
        print(f"no recordings found in {args.data}")
        return 1

    print(f"files: {len(paths)}")
    for p in paths:
        print(f"  {p.name}  ({p.stat().st_size / 1024:.0f} KiB)")

    df = build_series(paths, interval_sec=1.0, depth_bps=args.depth_bps)
    if df.empty:
        print("no board snapshots in the recordings — nothing to build")
        return 1

    rows = len(df)
    minutes = rows / 60.0  # one row = one recorded second of book state
    wall_sec = (df.index[-1] - df.index[0]).total_seconds() + 1.0
    gaps = int((df.index.to_series().diff() > pd.Timedelta(seconds=1)).sum())
    spread_bps = (df["spread"] / df["mid"] * 1e4).dropna()

    print(f"\n=== series (depth band +/-{args.depth_bps:g} bps of mid) ===")
    print(f"rows            : {rows} seconds of book state "
          f"in {gaps + 1} contiguous session(s)")
    print(f"time span       : {df.index[0]} -> {df.index[-1]} "
          f"({wall_sec / 60:.1f} min wall, {minutes:.1f} min recorded)")
    print(f"mean spread     : {spread_bps.mean():.3f} bps of mid "
          f"(median {spread_bps.median():.3f}, p95 {spread_bps.quantile(0.95):.3f})")
    print(f"mid range       : {df['mid'].min():,.0f} - {df['mid'].max():,.0f}")
    print(f"depth in band   : bid {df['bid_depth'].mean():.3f} BTC, "
          f"ask {df['ask_depth'].mean():.3f} BTC (mean)")
    print(f"imbalance       : mean {df['imbalance'].mean():+.3f}, "
          f"sd {df['imbalance'].std():.3f}, "
          f"|imb|>{THRESHOLD} on {(df['imbalance'].abs() > THRESHOLD).mean() * 100:.1f}% of seconds")
    imb_next = pd.Series(df["imbalance"].reindex(
        df.index + pd.Timedelta(seconds=1)).to_numpy(), index=df.index)
    rho1 = df["imbalance"].corr(imb_next)
    print(f"imb autocorr(1s): {rho1:+.3f}")

    insufficient = minutes < MIN_MINUTES
    if insufficient:
        print(f"\n*** INSUFFICIENT SAMPLE — SMOKE TEST ONLY ***\n"
              f"*** {minutes:.1f} min of board data (< {MIN_MINUTES:.0f} min). The numbers "
              f"below prove the pipeline runs end to end. They are NOT evidence "
              f"about the signal: at this length the correlations are dominated "
              f"by a handful of overlapping, autocorrelated observations. ***")

    imb = df["imbalance"]
    print(f"\n=== corr(imbalance[t], forward mid log-return t -> t+h) ===")
    print(f"{'h (s)':>6} {'corr':>9} {'n':>7} {'mean fwd(bps)':>15} {'sd fwd(bps)':>13}")
    for h in HORIZONS:
        fwd = forward_bps(df["mid"], h)
        pair = pd.concat([imb, fwd], axis=1).dropna()
        pair.columns = ["imb", "fwd"]
        n = len(pair)
        if n < 3 or pair["imb"].std() == 0 or pair["fwd"].std() == 0:
            print(f"{h:6d} {'n/a':>9} {n:7d}")
            continue
        corr = pair["imb"].corr(pair["fwd"])
        print(f"{h:6d} {corr:+9.4f} {n:7d} {pair['fwd'].mean():+15.3f} "
              f"{pair['fwd'].std():13.3f}")

    print(f"\n=== conditional mean forward return (bps) by imbalance state ===")
    print(f"{'h (s)':>6} | " + " | ".join(
        f"{lbl:>22}" for lbl in (f"imb > +{THRESHOLD}", f"imb < -{THRESHOLD}", "spread (bps)")))
    for h in HORIZONS:
        fwd = forward_bps(df["mid"], h)
        cells = []
        for sign in (+1, -1):
            mask = (imb > THRESHOLD) if sign > 0 else (imb < -THRESHOLD)
            sel = fwd[mask].dropna()
            if sel.empty:
                cells.append(f"{'no events':>22}")
            else:
                se = sel.std() / np.sqrt(len(sel)) if len(sel) > 1 else float("nan")
                cells.append(f"{sel.mean():+9.3f} (n={len(sel)}, se={se:.2f})".rjust(22))
        cells.append(f"{spread_bps.mean():22.3f}")
        print(f"{h:6d} | " + " | ".join(cells))

    print(f"""
READING THE TABLE
- Sign convention: imbalance > 0 means more resting size on the bid side
  within +/-{args.depth_bps:g} bps of the mid. A positive conditional mean under
  "imb > +{THRESHOLD}" means the mid drifted UP after bid-heavy books.
- Every observation overlaps its neighbours (1s grid, horizons up to 30s)
  and imbalance is strongly autocorrelated (lag-1 {rho1:+.3f}), so the
  effective sample is far smaller than n. The se column is therefore an
  optimistic lower bound; do not read it as a t-stat.
- Mean spread is printed alongside because any drift smaller than the
  spread is not capturable, whatever its statistical status.""")
    if insufficient:
        print(f"\n*** Reminder: {minutes:.1f} min of data. Smoke test, not a result. ***")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
