#!/usr/bin/env python3
"""Fetch OKX public BTC derivatives data (www.okx.com, no auth required).

1. Current open interest snapshot for BTC-USDT-SWAP and BTC-USD-SWAP
   (public/open-interest) - printed for verification, not saved to CSV.
2. OI + volume history (rubik/stat/contracts/open-interest-volume) for
   period=5m and period=1H -> data/okx_btc_oi_5m.csv, okx_btc_oi_1h.csv
   columns: ts (UTC datetime), oi, volume
3. Long/short account ratio history (rubik/stat/contracts/
   long-short-account-ratio) for period=5m and period=1H ->
   data/okx_btc_lsratio_5m.csv, okx_btc_lsratio_1h.csv
   columns: ts (UTC datetime), ratio

Note: the rubik endpoints return a fixed-depth window and do not support
paging further back via after/before (verified empirically - both params
return the identical response), so this script issues one request per
period and reports whatever depth OKX actually returns.

Usage:
    python scripts/fetch_okx.py
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BASE = "https://www.okx.com"
SLEEP = 0.5
session = requests.Session()


def get(path: str, params: dict):
    resp = session.get(BASE + path, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise RuntimeError(f"{path} {params} -> {data}")
    return data


def fetch_oi_snapshot():
    for inst_id in ("BTC-USDT-SWAP", "BTC-USD-SWAP"):
        try:
            data = get("/api/v5/public/open-interest", {"instType": "SWAP", "instId": inst_id})
            print(f"[fetch_okx] open-interest {inst_id}: {data['data']}")
        except Exception as exc:
            print(f"[fetch_okx] open-interest {inst_id} FAILED: {exc}")
        time.sleep(SLEEP)


def fetch_oi_history(ccy: str, period: str):
    try:
        data = get("/api/v5/rubik/stat/contracts/open-interest-volume", {"ccy": ccy, "period": period})
    except Exception as exc:
        print(f"[fetch_okx] oi-volume period={period} FAILED: {exc}")
        return None
    rows = data["data"]
    df = pd.DataFrame(rows, columns=["ts", "oi", "volume"])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df["oi"] = df["oi"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df = df.sort_values("ts").set_index("ts")
    return df


def fetch_lsratio_history(ccy: str, period: str):
    try:
        data = get("/api/v5/rubik/stat/contracts/long-short-account-ratio", {"ccy": ccy, "period": period})
    except Exception as exc:
        print(f"[fetch_okx] long-short-ratio period={period} FAILED: {exc}")
        return None
    rows = data["data"]
    df = pd.DataFrame(rows, columns=["ts", "ratio"])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df["ratio"] = df["ratio"].astype(float)
    df = df.sort_values("ts").set_index("ts")
    return df


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    fetch_oi_snapshot()

    for period, suffix in (("5m", "5m"), ("1H", "1h")):
        df = fetch_oi_history("BTC", period)
        time.sleep(SLEEP)
        if df is not None:
            out = DATA_DIR / f"okx_btc_oi_{suffix}.csv"
            df.to_csv(out)
            print(f"[fetch_okx] oi period={period}: {len(df)} rows, "
                  f"span {df.index.min()} .. {df.index.max()} -> {out}")

    for period, suffix in (("5m", "5m"), ("1H", "1h")):
        df = fetch_lsratio_history("BTC", period)
        time.sleep(SLEEP)
        if df is not None:
            out = DATA_DIR / f"okx_btc_lsratio_{suffix}.csv"
            df.to_csv(out)
            print(f"[fetch_okx] lsratio period={period}: {len(df)} rows, "
                  f"span {df.index.min()} .. {df.index.max()} -> {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
