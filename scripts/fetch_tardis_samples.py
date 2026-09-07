#!/usr/bin/env python3
"""Fetch Tardis.dev free monthly samples (first day of each month, no API
key) of bitFlyer FX_BTC_JPY trades, for P2-08b diagnostic use only (NOT for
selection -- see docs/PHASE2/P2-08b/PREREG.md). ToS 9.2 forbids redistributing
raw/sub-10-min data, so output goes under data/tardis/ (gitignored), never
backtest_data/.

Source: https://datasets.tardis.dev/v1/bitflyer/trades/YYYY/MM/01/FX_BTC_JPY.csv.gz
(public, unauthenticated, first-of-month sample only -- any other day 401s).

Usage:
    python fetch_tardis_samples.py --start 2019-09 --end 2026-09 --out data/tardis/bitflyer_FX_BTC_JPY_trades
"""
import argparse
import csv
import gzip
import hashlib
import io
import statistics
import sys
import time
from pathlib import Path

import requests

BASE = "https://datasets.tardis.dev/v1/bitflyer/trades"


def month_range(start, end):
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def fetch_one(session, url, tries=5):
    for attempt in range(tries):
        try:
            resp = session.get(url, timeout=60)
        except requests.RequestException as exc:
            print(f"    ! network error {exc.__class__.__name__}, retry", file=sys.stderr)
            time.sleep(min(30, 2 ** attempt))
            continue
        if resp.status_code == 200:
            return 200, resp.content
        if resp.status_code == 429:
            wait = 8 * (attempt + 1)
            print(f"    429, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        return resp.status_code, None
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM")
    ap.add_argument("--end", required=True, help="YYYY-MM")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "trade-bot-research/1.0 (P2-08b diagnostic sample)"})

    rows_summary = []
    md5s = {}
    for y, m in month_range(args.start, args.end):
        day_str = f"{y:04d}-{m:02d}-01"
        url = f"{BASE}/{y:04d}/{m:02d}/01/FX_BTC_JPY.csv.gz"
        dest = root / f"FX_BTC_JPY_{y:04d}{m:02d}01.csv.gz"
        print(f"{day_str}: ...", end=" ", flush=True)
        if dest.exists():
            content = dest.read_bytes()
            status = 200
        else:
            status, content = fetch_one(session, url)
            if status == 200:
                dest.write_bytes(content)
            time.sleep(args.sleep)
        if status != 200:
            print(f"HTTP {status}")
            rows_summary.append({"date": day_str, "status": status, "n_rows": 0,
                                  "delay_p50_s": None, "delay_p10_s": None, "delay_p90_s": None})
            continue

        # stream-parse for row count + exchange-ts vs local-ts delay
        n = 0
        delays = []
        with gzip.open(io.BytesIO(content), "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                n += 1
                try:
                    ex_us = int(row["timestamp"])
                    local_us = int(row["local_timestamp"])
                    delays.append((local_us - ex_us) / 1_000_000.0)
                except (KeyError, ValueError):
                    pass
        md5s[dest.name] = hashlib.md5(content).hexdigest()
        p50 = statistics.median(delays) if delays else None
        p10 = statistics.quantiles(delays, n=10)[0] if len(delays) >= 10 else None
        p90 = statistics.quantiles(delays, n=10)[8] if len(delays) >= 10 else None
        print(f"OK {n} rows, delay p50={p50}")
        rows_summary.append({"date": day_str, "status": 200, "n_rows": n,
                              "delay_p50_s": p50, "delay_p10_s": p10, "delay_p90_s": p90})

    # MD5SUMS (append-safe: rewrite in full from what's on disk each run)
    md5_file = root / "MD5SUMS"
    with md5_file.open("w") as f:
        for name in sorted(p.name for p in root.glob("*.csv.gz")):
            h = hashlib.md5((root / name).read_bytes()).hexdigest()
            f.write(f"{h}  ./{name}\n")

    import json
    with open(root / "_fetch_summary.json", "w") as f:
        json.dump(rows_summary, f, indent=2)
    print(f"done. {sum(1 for r in rows_summary if r['status']==200)}/{len(rows_summary)} days ok")


if __name__ == "__main__":
    main()
