#!/usr/bin/env python3
"""Fetch external-exchange public market data (read-only, no auth).

Sources:
- Binance (data-api.binance.vision): 1m/4h/1d klines for XRPUSDT, BTCUSDT
- bitbank (public.bitbank.cc): 1min candlesticks for xrp_jpy (per-day endpoint)

Output CSVs in data/: timestamp(UTC), open, high, low, close, volume.
Usage: python scripts/fetch_external.py [--days 21] [--swing-days 730]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
BITBANK = "https://public.bitbank.cc"

session = requests.Session()


def binance_klines(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    rows = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    while cursor < end_ms:
        resp = session.get(BINANCE, params={
            "symbol": symbol, "interval": interval, "startTime": cursor,
            "endTime": end_ms, "limit": 1000,
        }, timeout=15)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + 1
        time.sleep(0.15)
    df = pd.DataFrame(
        [{"timestamp": pd.Timestamp(r[0], unit="ms", tz="UTC"),
          "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
          "close": float(r[4]), "volume": float(r[5])} for r in rows]
    )
    return df.drop_duplicates("timestamp").set_index("timestamp").sort_index()


def bitbank_1min(pair: str, days: int) -> pd.DataFrame:
    frames = []
    today = datetime.now(timezone.utc).date()
    for d in range(days, -1, -1):
        day = today - timedelta(days=d)
        url = f"{BITBANK}/{pair}/candlestick/1min/{day.strftime('%Y%m%d')}"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            continue
        payload = resp.json()
        if payload.get("success") != 1:
            continue
        for cs in payload["data"]["candlestick"]:
            frames.extend(cs["ohlcv"])
        time.sleep(0.25)
    df = pd.DataFrame(
        [{"timestamp": pd.Timestamp(int(r[5]), unit="ms", tz="UTC"),
          "open": float(r[0]), "high": float(r[1]), "low": float(r[2]),
          "close": float(r[3]), "volume": float(r[4])} for r in frames]
    )
    return df.drop_duplicates("timestamp").set_index("timestamp").sort_index()


def save(df: pd.DataFrame, name: str) -> None:
    """Merge with any existing file so short incremental fetches never
    truncate accumulated history."""
    out = DATA_DIR / name
    if out.exists() and len(df):
        old = pd.read_csv(out, index_col=0, parse_dates=True)
        old.index = pd.to_datetime(old.index, utc=True)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_csv(out)
    span = f"{df.index[0]} .. {df.index[-1]}" if len(df) else "EMPTY"
    print(f"{name}: {len(df)} rows ({span})", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21, help="1-minute history depth")
    ap.add_argument("--swing-days", type=int, default=730, help="4h/1d history depth")
    args = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)

    for symbol in ("XRPUSDT", "BTCUSDT"):
        save(binance_klines(symbol, "1m", now - timedelta(days=args.days), now),
             f"binance_{symbol}_1m.csv")
    for symbol in ("XRPUSDT", "BTCUSDT"):
        save(binance_klines(symbol, "4h", now - timedelta(days=args.swing_days), now),
             f"binance_{symbol}_4h.csv")
        save(binance_klines(symbol, "1d", now - timedelta(days=args.swing_days), now),
             f"binance_{symbol}_1d.csv")
    save(bitbank_1min("xrp_jpy", args.days), "bitbank_xrp_jpy_1m.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
