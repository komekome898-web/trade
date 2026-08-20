#!/usr/bin/env python3
"""Fetch Deribit public BTC DVOL history and current perpetual ticker
(www.deribit.com, no auth required).

1. DVOL (BTC volatility index) history via public/get_volatility_index_data,
   paged backwards using the response's "continuation" cursor as the next
   end_timestamp (verified: continuation == start of the returned window,
   1000 candles per call max).
     - resolution=3600 (1h): paged back as far as the API allows
       (target >=180 days) -> data/deribit_dvol_1h.csv
     - resolution=60 (1m): last 7 days -> data/deribit_dvol_1m_7d.csv
   Both files have columns: open, high, low, close (index: UTC datetime).

2. Current BTC-PERPETUAL snapshot via public/ticker - open_interest and
   funding-related fields (current_funding, funding_8h, mark_price,
   index_price) are printed for verification.

Usage:
    python scripts/fetch_deribit.py [--days 200]
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BASE = "https://www.deribit.com/api/v2/public"
SLEEP = 0.5
session = requests.Session()


def get_vol_page(currency: str, resolution: int, start_ms: int, end_ms: int):
    resp = session.get(
        f"{BASE}/get_volatility_index_data",
        params={
            "currency": currency,
            "resolution": resolution,
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "result" not in body:
        raise RuntimeError(f"unexpected response: {body}")
    return body["result"]


def fetch_dvol_history(currency: str, resolution: int, target_days: float, sleep_sec: float):
    """Page backwards from now using the continuation cursor until the API
    stops returning older data or we exceed target_days."""
    now = datetime.now(timezone.utc)
    end_ms = int(now.timestamp() * 1000)
    start_ms = 0  # let the API bound it; we page via continuation
    target_start_ms = int((now - timedelta(days=target_days)).timestamp() * 1000)

    all_rows: list[list] = []
    req_count = 0
    cur_end = end_ms
    seen_starts: set[int] = set()

    while True:
        req_count += 1
        result = get_vol_page(currency, resolution, start_ms, cur_end)
        data = result.get("data") or []
        if not data:
            break
        all_rows.extend(data)
        continuation = result.get("continuation")
        oldest_ts = data[0][0]

        if continuation is None or continuation in seen_starts:
            break
        seen_starts.add(continuation)

        if oldest_ts <= target_start_ms:
            break
        if len(data) < 2:  # no more progress possible
            break

        cur_end = continuation
        time.sleep(sleep_sec)

    print(f"[fetch_deribit] resolution={resolution}: {req_count} requests, {len(all_rows)} raw candles")
    return all_rows


def build_df(rows: list[list]):
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df = df.drop_duplicates(subset="ts").sort_values("ts").set_index("ts")
    return df


def fetch_ticker(instrument: str):
    resp = session.get(f"{BASE}/ticker", params={"instrument_name": instrument}, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if "result" not in body:
        print(f"[fetch_deribit] ticker FAILED: {body}")
        return
    res = body["result"]
    print(f"[fetch_deribit] {instrument} open_interest={res.get('open_interest')} "
          f"current_funding={res.get('current_funding')} funding_8h={res.get('funding_8h')} "
          f"mark_price={res.get('mark_price')} index_price={res.get('index_price')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=200, help="target history depth for 1h DVOL")
    ap.add_argument("--sleep", type=float, default=SLEEP)
    args = ap.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    # 1h DVOL, as much history as possible (target 180+ days)
    rows_1h = fetch_dvol_history("BTC", 3600, args.days, args.sleep)
    if rows_1h:
        df_1h = build_df(rows_1h)
        out_1h = DATA_DIR / "deribit_dvol_1h.csv"
        df_1h.to_csv(out_1h)
        span_days = (df_1h.index.max() - df_1h.index.min()).total_seconds() / 86400
        print(f"[fetch_deribit] dvol_1h: {len(df_1h)} rows, span {df_1h.index.min()} .. "
              f"{df_1h.index.max()} ({span_days:.1f} days) -> {out_1h}")
    else:
        print("[fetch_deribit] dvol_1h FAILED: no data")

    time.sleep(args.sleep)

    # 1m DVOL, last 7 days
    rows_1m = fetch_dvol_history("BTC", 60, 7, args.sleep)
    if rows_1m:
        df_1m = build_df(rows_1m)
        out_1m = DATA_DIR / "deribit_dvol_1m_7d.csv"
        df_1m.to_csv(out_1m)
        span_days = (df_1m.index.max() - df_1m.index.min()).total_seconds() / 86400
        print(f"[fetch_deribit] dvol_1m_7d: {len(df_1m)} rows, span {df_1m.index.min()} .. "
              f"{df_1m.index.max()} ({span_days:.1f} days) -> {out_1m}")
    else:
        print("[fetch_deribit] dvol_1m_7d FAILED: no data")

    time.sleep(args.sleep)
    fetch_ticker("BTC-PERPETUAL")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
