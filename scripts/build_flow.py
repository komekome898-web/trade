#!/usr/bin/env python3
"""Build per-minute order-flow candles (OHLCV + taker buy/sell volume split)
from stored executions CSVs. The side column of /v1/executions is the TAKER
side, i.e. aggressive buying vs aggressive selling — the signal いなご
(volume-surge) trading keys on.

Usage: python scripts/build_flow.py [PRODUCT ...]   (default: all stored)
Writes data/flow_<product>.csv with columns:
open, high, low, close, volume, buy_vol, sell_vol, trades
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def build(product: str) -> Path | None:
    src = DATA / f"executions_{product}.csv"
    if not src.exists():
        print(f"[{product}] no executions file, skipping")
        return None
    df = pd.read_csv(src)
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
    flow[["open", "high", "low", "close"]] = flow[["open", "high", "low", "close"]].ffill()
    flow = flow.dropna(subset=["open"])
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
