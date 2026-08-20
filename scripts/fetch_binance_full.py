#!/usr/bin/env python3
"""Fetch Binance spot klines for BTCUSDT (data-api.binance.vision, public,
no auth) at 1m resolution for the last N days, saving all useful kline
fields (not just OHLCV).

Endpoint: https://data-api.binance.vision/api/v3/klines
Paged forward with startTime, limit=1000 per request.

Kline array fields (per Binance docs):
    0 open_time, 1 open, 2 high, 3 low, 4 close, 5 volume,
    6 close_time, 7 quote_volume, 8 n_trades, 9 taker_buy_base,
    10 taker_buy_quote, 11 ignore

Output: data/binance_BTCUSDT_1m_full.csv
    index: open_time (UTC datetime)
    columns: open, high, low, close, volume, quote_volume, n_trades,
             taker_buy_base

Usage:
    python scripts/fetch_binance_full.py [--days 90] [--symbol BTCUSDT]
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
URL = "https://data-api.binance.vision/api/v3/klines"
session = requests.Session()

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "n_trades", "taker_buy_base",
    "taker_buy_quote", "ignore",
]


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int, sleep_sec: float):
    rows: list[list] = []
    cur = start_ms
    req_count = 0
    while cur < end_ms:
        req_count += 1
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cur,
            "limit": 1000,
        }
        resp = session.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < 1000:
            break
        cur = last_open + 1
        time.sleep(sleep_sec)
    print(f"[fetch_binance_full] {req_count} requests, {len(rows)} raw rows")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", default="1m")
    ap.add_argument("--days", type=float, default=90)
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    rows = fetch_klines(args.symbol, args.interval, start_ms, end_ms, args.sleep)
    if not rows:
        print("no rows fetched")
        return 1

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop_duplicates(subset="open_time").sort_values("open_time")
    df = df.set_index("open_time")

    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]:
        df[col] = df[col].astype(float)
    df["n_trades"] = df["n_trades"].astype(int)

    out_cols = ["open", "high", "low", "close", "volume", "quote_volume", "n_trades", "taker_buy_base"]
    out = df[out_cols]

    out_path = DATA_DIR / f"binance_{args.symbol}_{args.interval}_full.csv"
    out.to_csv(out_path)

    span_start = out.index.min()
    span_end = out.index.max()
    print(f"[fetch_binance_full] wrote {len(out)} rows -> {out_path}")
    print(f"[fetch_binance_full] span: {span_start} .. {span_end}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
