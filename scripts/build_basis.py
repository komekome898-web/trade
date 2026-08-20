#!/usr/bin/env python3
"""Build the FX/spot basis series: inner-join 1-minute candles for
FX_BTC_JPY and BTC_JPY on their (UTC) timestamp index and compute the
percentage basis of the FX price over spot.

Reads:  data/candles_FX_BTC_JPY.csv, data/candles_BTC_JPY.csv
Writes: data/basis_1m.csv  (columns: ts, fx_close, spot_close, basis_pct)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"

    fx = pd.read_csv(data_dir / "candles_FX_BTC_JPY.csv", index_col=0, parse_dates=True)
    spot = pd.read_csv(data_dir / "candles_BTC_JPY.csv", index_col=0, parse_dates=True)

    joined = fx[["close"]].join(spot[["close"]], how="inner", lsuffix="_fx", rsuffix="_spot")
    joined = joined.rename(columns={"close_fx": "fx_close", "close_spot": "spot_close"})
    joined["basis_pct"] = (joined["fx_close"] / joined["spot_close"] - 1) * 100
    joined.index.name = "ts"

    out = data_dir / "basis_1m.csv"
    joined.to_csv(out)
    print(f"wrote {len(joined)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
