#!/usr/bin/env python3
"""Build per-minute order-flow candles (OHLCV + taker buy/sell volume split)
from stored executions CSVs. The side column of /v1/executions is the TAKER
side, i.e. aggressive buying vs aggressive selling — the signal いなご
(volume-surge) trading keys on.

Usage: python scripts/build_flow.py [PRODUCT ...]   (default: all stored)
Writes data/flow_<product>.csv with columns:
open, high, low, close, volume, buy_vol, sell_vol, trades, synthetic

DATA QA 2026-09-05 (docs/DATA_QA_TRIAGE.md bitflyer_execution_flow/
maintenance_window+zero_volume): a minute with zero executions used to be
forward-filled (open/high/low/close copied from the previous real minute,
volume/buy_vol/sell_vol/trades zeroed) with no way to tell it apart from a
real bar -- the exact same defect already found and fixed in
scripts/fetch_deep.py's candle builder (see its `synthetic` column and
tests/test_fetch_history_candles.py). `synthetic` (1 = forward-filled gap
minute, 0 = real) marks these rows the same way; existing data/flow_*.csv
files are NOT rewritten (only future runs gain the column).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def build_flow(executions: "pd.DataFrame") -> "pd.DataFrame":
    """1-minute OHLCV + taker buy/sell volume split from an executions frame
    (columns: exec_date, price, size, side). A minute with zero executions
    is forward-filled from the previous real minute (never dropped, unlike
    scripts/fetch_history.py's candle builder) and flagged `synthetic=1` so
    it can be told apart from a real bar -- see module docstring."""
    df = executions.copy()
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.sort_values("ts").set_index("ts")

    o = df["price"].resample("1min").ohlc()
    vol = df["size"].resample("1min").sum().rename("volume")
    buys = df.loc[df["side"] == "BUY", "size"].resample("1min").sum().rename("buy_vol")
    sells = df.loc[df["side"] == "SELL", "size"].resample("1min").sum().rename("sell_vol")
    trades = df["price"].resample("1min").count().rename("trades")

    flow = o.join([vol, buys, sells, trades])
    flow[["volume", "buy_vol", "sell_vol", "trades"]] = \
        flow[["volume", "buy_vol", "sell_vol", "trades"]].fillna(0.0)
    # a minute with zero executions has NaN open (nothing to resample) --
    # capture that BEFORE ffill overwrites it, so a forward-filled bar can
    # still be told apart from a real one.
    flow["synthetic"] = flow["open"].isna().astype(int)
    flow[["open", "high", "low", "close"]] = flow[["open", "high", "low", "close"]].ffill()
    flow = flow.dropna(subset=["open"])
    return flow


def build(product: str) -> Path | None:
    src = DATA / f"executions_{product}.csv"
    if not src.exists():
        print(f"[{product}] no executions file, skipping")
        return None
    flow = build_flow(pd.read_csv(src))
    out = DATA / f"flow_{product}.csv"
    flow.to_csv(out)
    print(f"[{product}] {len(flow)} flow candles ({flow.index[0]} .. {flow.index[-1]}) -> {out}")
    return out


def main() -> int:
    products = sys.argv[1:] or [
        p.name.replace("executions_", "").replace(".csv", "")
        for p in DATA.glob("executions_*.csv")
    ]
    for product in products:
        build(product)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
