#!/usr/bin/env python3
"""Fetch Binance aggTrades (millisecond timestamps) for given UTC windows and
save 1-second last-price series for seconds-scale lead-lag research.

Usage:
    python scripts/fetch_aggtrades.py BTCUSDT 2026-08-19T12:00 2026-08-19T18:00 [label]
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
URL = "https://data-api.binance.vision/api/v3/aggTrades"
session = requests.Session()


def fetch_window(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    rows: list[tuple[int, float, float]] = []
    hour = start
    while hour < end:
        hour_end = min(hour + timedelta(hours=1), end)
        resp = session.get(URL, params={
            "symbol": symbol, "startTime": int(hour.timestamp() * 1000),
            "endTime": int(hour_end.timestamp() * 1000) - 1, "limit": 1000,
        }, timeout=15)
        resp.raise_for_status()
        batch = resp.json()
        while batch:
            rows.extend((t["T"], float(t["p"]), float(t["q"])) for t in batch)
            if len(batch) < 1000:
                break
            from_id = batch[-1]["a"] + 1
            time.sleep(0.08)
            resp = session.get(URL, params={"symbol": symbol, "fromId": from_id,
                                            "limit": 1000}, timeout=15)
            resp.raise_for_status()
            batch = [t for t in resp.json()
                     if t["T"] < int(hour_end.timestamp() * 1000)]
        hour = hour_end
        time.sleep(0.1)
    df = pd.DataFrame(rows, columns=["ms", "price", "qty"])
    df["ts"] = pd.to_datetime(df["ms"], unit="ms", utc=True)
    return df


def to_1s(df: pd.DataFrame) -> pd.DataFrame:
    g = df.set_index("ts")
    out = pd.DataFrame({
        "price": g["price"].resample("1s").last(),
        "volume": g["qty"].resample("1s").sum(),
        "n": g["price"].resample("1s").count(),
    })
    out["price"] = out["price"].ffill()
    return out.dropna(subset=["price"])


def main() -> int:
    symbol = sys.argv[1]
    start = datetime.fromisoformat(sys.argv[2]).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(sys.argv[3]).replace(tzinfo=timezone.utc)
    label = sys.argv[4] if len(sys.argv) > 4 else start.strftime("%Y%m%d_%H")
    df = fetch_window(symbol, start, end)
    out1s = to_1s(df)
    path = DATA / f"binance_{symbol}_1s_{label}.csv"
    out1s.to_csv(path)
    print(f"{label}: {len(df)} trades -> {len(out1s)} 1s rows -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
