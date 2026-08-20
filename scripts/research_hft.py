#!/usr/bin/env python3
"""Seconds-scale lead-lag between Binance BTCUSDT and bitFlyer FX_BTC_JPY.

Answers: is there still exploitable lag at the 1-30 second horizon (the scale
an API-rate-limited scalper operates at), and does it clear FX costs?

Data: Binance aggTrades resampled to 1s vs bitFlyer executions resampled to
1s, for four 6-hour windows (2 volatile, 2 quiet). Trade-price based — quote
staleness caveats apply both ways and are printed with the results.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

WINDOWS = {
    "hi1 (8/19 vol)": ("2026-08-19T12:00", "2026-08-19T18:00"),
    "hi2 (7/31 vol)": ("2026-07-31T11:00", "2026-07-31T17:00"),
    "lo1 (8/08 quiet)": ("2026-08-08T12:00", "2026-08-08T18:00"),
    "lo2 (8/15 quiet)": ("2026-08-15T12:00", "2026-08-15T18:00"),
}
LABELS = {"hi1 (8/19 vol)": "hi1", "hi2 (7/31 vol)": "hi2",
          "lo1 (8/08 quiet)": "lo1", "lo2 (8/15 quiet)": "lo2"}

# FX cost floor for a taker scalp round trip: spread 2.35bp + slip 2bp x2 sides
TAKER_RT_BPS = 6.35
HALF_SPREAD_BPS = 1.18


def bf_1s(start: str, end: str) -> pd.Series:
    ex = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv")
    ex["ts"] = pd.to_datetime(ex["exec_date"], format="mixed", utc=True)
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC")
    ex = ex[(ex["ts"] >= lo) & (ex["ts"] < hi)].sort_values("ts")
    s = ex.set_index("ts")["price"].resample("1s").last().ffill()
    return s


def main() -> int:
    for name, (start, end) in WINDOWS.items():
        label = LABELS[name]
        bn = pd.read_csv(DATA / f"binance_BTCUSDT_1s_{label}.csv",
                         index_col=0, parse_dates=True)["price"]
        bn.index = pd.to_datetime(bn.index, utc=True)
        bf = bf_1s(start, end)
        joined = pd.DataFrame({"bf": bf, "bn": bn}).dropna()
        r_bf = np.log(joined["bf"]).diff()
        r_bn = np.log(joined["bn"]).diff()
        n_bf_trades = (r_bf != 0).sum()

        print(f"\n{'=' * 88}")
        print(f"{name}: {len(joined)} aligned seconds, bitFlyer active seconds: {n_bf_trades}")
        cells = []
        for k in [0, 1, 2, 3, 5, 10, 20, 30]:
            cells.append(f"k={k}s:{r_bf.corr(r_bn.shift(k)):+.3f}")
        print("corr( bitFlyer_ret[t], Binance_ret[t-k] ): " + "  ".join(cells))

        # Event study: Binance moved >= thr bps over the last 5s at time t.
        # Measure bitFlyer's signed drift from t to t+h (last-trade basis),
        # then net a taker scalp: cross spread in, cross spread out.
        sig = np.log(joined["bn"]).diff(5) * 1e4  # bps
        px = joined["bf"]
        print(f"{'thr(bps)':>8} {'events':>7} | " + " | ".join(
            f"h={h}s net_bps" for h in (2, 5, 10, 30)))
        for thr in (3, 5, 10, 20):
            mask = sig.abs() >= thr
            n = int(mask.sum())
            if n < 20:
                print(f"{thr:8.0f} {n:7d} | (too few events)")
                continue
            direction = np.sign(sig[mask])
            row = []
            for h in (2, 5, 10, 30):
                fwd = (np.log(px.shift(-h)) - np.log(px)) * 1e4
                captured = (fwd[mask] * direction).dropna()
                net = captured.mean() - TAKER_RT_BPS
                row.append(f"{net:+13.2f}")
            print(f"{thr:8.0f} {n:7d} | " + " | ".join(row))

    print(f"""
NOTES:
- net_bps = mean drift captured in signal direction minus taker round-trip
  cost ({TAKER_RT_BPS} bps). Positive = scalp would have paid AFTER costs.
- bitFlyer prices are last-trade based (~0.4 trades/s): staleness can both
  exaggerate apparent lag and hide fills you could not get. Quote-level
  confirmation requires the WS board recording now being collected.
- Overlapping events inflate counts; treat magnitudes, not t-stats.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
