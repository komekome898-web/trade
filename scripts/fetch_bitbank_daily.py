#!/usr/bin/env python3
"""Fetch bitbank BTC/JPY daily execution history (public REST, no key) for a
list of specific UTC-adjacent JST calendar days -- built for P2-08b's
long-term (2017-2026) diagnostic proxy for the yen market side of
Binance -> yen-market propagation (docs/PHASE2/P2-08b/PREREG.md,
BLINDSPOT_AUDIT.md #1). NOT used for selection; diagnostic only.

Source: https://public.bitbank.cc/btc_jpy/transactions/YYYYMMDD
(public, unauthenticated; see https://github.com/bitbankinc/bitbank-api-docs
public-api_JP.md "約定履歴" -- returns bitbank's own JST trading-day
transactions, `executed_at` is Unix ms). No key required, no documented rate
limit beyond generic abuse throttling; this script sleeps between requests.

Layout produced under --out:
    btc_jpy_transactions_YYYYMMDD.csv.gz   -- one per requested day, columns:
        transaction_id, side, price, amount, ts_us (executed_at normalized
        to UTC microseconds)
    MD5SUMS
    README.md   -- NOT written by this script (left to the caller)

Usage:
    python scripts/fetch_bitbank_daily.py --start 2017-09 --end 2026-09 \
        --day-of-month 1 --out backtest_data/bitbank_btc_jpy_transactions_monthly_first_days
"""
from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://public.bitbank.cc/btc_jpy/transactions"
OUT_COLUMNS = ["transaction_id", "side", "price", "amount", "ts_us"]


def month_range(start: str, end: str):
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def fetch_day(session: requests.Session, day_str: str, tries: int = 5):
    """Returns (status_code, list_of_transaction_dicts_or_None)."""
    url = f"{BASE}/{day_str}"
    for attempt in range(tries):
        try:
            resp = session.get(url, timeout=30)
        except requests.RequestException as exc:
            print(f"    ! network error {exc.__class__.__name__}, retry", file=sys.stderr)
            time.sleep(min(30, 2 ** attempt))
            continue
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"    429, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return resp.status_code, None
        body = resp.json()
        if body.get("success") != 1:
            return -1, None  # API-level error (e.g. bad date, code in body.data.code)
        return 200, body["data"]["transactions"]
    return None, None


def write_day_csv(transactions: list[dict], out_csv: Path) -> int:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(transactions, key=lambda t: t["transaction_id"])
    with gzip.open(out_csv, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUT_COLUMNS)
        for t in rows:
            ts_us = int(t["executed_at"]) * 1000
            w.writerow([t["transaction_id"], t["side"], t["price"], t["amount"], ts_us])
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, help="YYYY-MM, first month (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM, last month (inclusive)")
    ap.add_argument("--day-of-month", type=int, default=1, help="which day of each month to fetch (default 1)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.out)
    months = list(month_range(args.start, args.end))
    day_strs = []
    for y, m in months:
        d = min(args.day_of_month, calendar.monthrange(y, m)[1])
        day_strs.append(f"{y:04d}{m:02d}{d:02d}")

    if args.dry_run:
        print(f"[dry-run] {len(day_strs)} days: {day_strs[0]} .. {day_strs[-1]}")
        print(f"[dry-run] out={root}")
        return 0

    root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data)"})

    summary = []
    for day_str in day_strs:
        out_csv = root / f"btc_jpy_transactions_{day_str}.csv.gz"
        if out_csv.exists():
            with gzip.open(out_csv, "rt") as f:
                n_cached = sum(1 for _ in f) - 1  # minus header
            print(f"{day_str}: cached, skip ({n_cached} rows)")
            summary.append({"date": day_str, "status": 200, "n_rows": n_cached, "cached": True})
            continue
        print(f"{day_str}: ...", end=" ", flush=True)
        status, txs = fetch_day(session, day_str)
        if status != 200:
            print(f"HTTP/API {status}")
            summary.append({"date": day_str, "status": status, "n_rows": 0})
            time.sleep(args.sleep)
            continue
        n = write_day_csv(txs, out_csv)
        print(f"OK {n} rows")
        summary.append({"date": day_str, "status": 200, "n_rows": n})
        time.sleep(args.sleep)

    md5_file = root / "MD5SUMS"
    with md5_file.open("w") as f:
        for p in sorted(root.glob("*.csv.gz")):
            h = hashlib.md5(p.read_bytes()).hexdigest()
            f.write(f"{h}  ./{p.name}\n")
    with open(root / "_fetch_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    ok = sum(1 for r in summary if r["status"] == 200)
    print(f"done. {ok}/{len(day_strs)} days ok (some may have been pre-cached and skipped from summary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
