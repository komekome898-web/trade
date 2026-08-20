#!/usr/bin/env python3
"""Fetch Kraken public Trades for XBTUSD (read-only, no auth) and build
1-minute last-price/volume candles.

Endpoint: https://api.kraken.com/0/public/Trades?pair=XBTUSD&since=<ns>
Pages forward from N days ago to now. Each response returns up to 1000
trades and a "last" cursor (nanosecond timestamp string) in result["last"].

Output: data/kraken_XBTUSD_1m.csv
    index: timestamp (UTC, 1-minute bins)
    columns: price (last trade price in bin), volume (sum size), n (trade count)

Usage:
    python scripts/fetch_kraken.py [--days 7] [--pair XBTUSD] [--max-minutes 20]
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
URL = "https://api.kraken.com/0/public/Trades"
session = requests.Session()


def fetch_trades(pair: str, days: float, sleep_sec: float, max_seconds: float):
    """Page forward through Kraken Trades from `days` ago to now.

    Returns (rows, stopped_early) where rows is a list of
    (timestamp_ns, price, volume) and stopped_early is True if the time
    budget ran out before catching up to now.
    """
    start_ns = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1e9)
    since = str(start_ns)
    now_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
    rows: list[tuple[int, float, float]] = []
    t0 = time.monotonic()
    req_count = 0
    stopped_early = False

    while True:
        if time.monotonic() - t0 > max_seconds:
            stopped_early = True
            print(f"[fetch_kraken] time budget ({max_seconds:.0f}s) exceeded after "
                  f"{req_count} requests; stopping early and saving what we have.",
                  flush=True)
            break

        resp = session.get(URL, params={"pair": pair, "since": since}, timeout=20)
        req_count += 1
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[fetch_kraken] request {req_count} failed: {exc}; retrying after 5s",
                  flush=True)
            time.sleep(5)
            continue

        if data.get("error"):
            print(f"[fetch_kraken] API error: {data['error']}; retrying after 5s", flush=True)
            time.sleep(5)
            continue

        result = data.get("result", {})
        # The trades list is keyed by the pair name Kraken assigns (may differ
        # from the requested pair string, e.g. "XXBTZUSD").
        trade_lists = [v for k, v in result.items() if k != "last"]
        batch = trade_lists[0] if trade_lists else []

        if not batch:
            break

        for t in batch:
            # trade tuple: [price, volume, time, side, orderType, misc, trade_id]
            price = float(t[0])
            volume = float(t[1])
            ts_ns = int(round(float(t[2]) * 1e9))
            rows.append((ts_ns, price, volume))

        last = result.get("last")
        if last is None:
            break
        new_since = last

        if page_progress := (req_count % 20 == 0):
            last_ts = datetime.fromtimestamp(int(new_since) / 1e9, tz=timezone.utc)
            print(f"[fetch_kraken] req {req_count}: trades={len(rows)} "
                  f"last={last_ts.isoformat()}", flush=True)

        # Stop when caught up to "now" (cursor has passed the current time,
        # or the batch was short meaning no more trades are buffered).
        if int(new_since) >= now_ns or len(batch) < 1000:
            since = new_since
            break

        if new_since == since:
            # No forward progress; avoid infinite loop.
            break
        since = new_since
        time.sleep(sleep_sec)

    print(f"[fetch_kraken] done: {req_count} requests, {len(rows)} trades fetched",
          flush=True)
    return rows, stopped_early


def to_1m_candles(rows: list[tuple[int, float, float]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["price", "volume", "n"])
    df = pd.DataFrame(rows, columns=["ts_ns", "price", "volume"])
    df["ts"] = pd.to_datetime(df["ts_ns"], unit="ns", utc=True)
    df = df.sort_values("ts").drop_duplicates()
    g = df.set_index("ts")
    out = pd.DataFrame({
        "price": g["price"].resample("1min").last(),
        "volume": g["volume"].resample("1min").sum(),
        "n": g["price"].resample("1min").count(),
    })
    out["price"] = out["price"].ffill()
    out = out.dropna(subset=["price"])
    out.index.name = "timestamp"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="XBTUSD")
    ap.add_argument("--days", type=float, default=7.0)
    ap.add_argument("--sleep", type=float, default=1.1)
    ap.add_argument("--max-minutes", type=float, default=20.0,
                     help="stop paging (saving partial results) after this many minutes")
    args = ap.parse_args()

    rows, stopped_early = fetch_trades(
        args.pair, args.days, args.sleep, args.max_minutes * 60.0
    )
    candles = to_1m_candles(rows)

    out_path = DATA_DIR / f"kraken_{args.pair}_1m.csv"
    candles.to_csv(out_path)

    if len(candles):
        span = f"{candles.index.min().isoformat()} .. {candles.index.max().isoformat()}"
    else:
        span = "n/a"
    print(f"[fetch_kraken] wrote {out_path}: {len(candles)} rows, span={span}, "
          f"raw_trades={len(rows)}, stopped_early={stopped_early}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
