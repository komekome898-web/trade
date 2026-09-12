#!/usr/bin/env python3
"""Fetch BitMEX insurance fund daily balance history (all currencies, full history).

Endpoint: GET https://www.bitmex.com/api/v1/insurance
No API key required. Paginates with count/start, reverse=false (ascending
timestamp). BitMEX is scheduled to shut down 2026-09-23; this is a one-shot
permanent-snapshot fetch, not a recurring job.

Usage:
    python scripts/fetch_bitmex_insurance.py

Output (fixed paths):
    backtest_data/bitmex_insurance_20260912/insurance.jsonl.gz
    backtest_data/bitmex_insurance_20260912/insurance_daily.csv
    backtest_data/bitmex_insurance_20260912/README.md (written by caller, not this script)

Network: uses HTTPS_PROXY env var (agent proxy) and the CA bundle at
/root/.ccr/ca-bundle.crt when present. No secrets involved (public endpoint).
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://www.bitmex.com/api/v1/insurance"
PAGE_SIZE = 500
SLEEP_SECONDS = 1.0
MAX_RETRIES = 3
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"

OUT_DIR = Path("backtest_data/bitmex_insurance_20260912")
JSONL_GZ = OUT_DIR / "insurance.jsonl.gz"
CSV_PATH = OUT_DIR / "insurance_daily.csv"
LOG_PATH = Path("docs/DATA/probes/20260912_bitmex_insurance_fetch.log")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_line(fh, text: str) -> None:
    line = f"{utc_now_iso()} {text}"
    print(line)
    fh.write(line + "\n")
    fh.flush()


def fetch_page(session: requests.Session, start: int, log_fh) -> list[dict]:
    params = {
        "count": PAGE_SIZE,
        "start": start,
        "reverse": "false",
    }
    url = f"{BASE_URL}?{requests.compat.urlencode(params)}"
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(BASE_URL, params=params, timeout=30)
            code = resp.status_code
            if code == 200:
                data = resp.json()
                log_line(log_fh, f"GET {url} HTTP {code} records={len(data)}")
                return data
            else:
                log_line(
                    log_fh,
                    f"GET {url} HTTP {code} attempt={attempt}/{MAX_RETRIES} body={resp.text[:200]!r}",
                )
        except requests.RequestException as exc:
            last_exc = exc
            log_line(
                log_fh,
                f"GET {url} EXCEPTION attempt={attempt}/{MAX_RETRIES} err={exc!r}",
            )
        if attempt < MAX_RETRIES:
            backoff = 2 ** attempt
            time.sleep(backoff)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"failed to fetch page start={start} after {MAX_RETRIES} attempts")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        session.proxies.update({"https": proxy, "http": proxy})
    if os.path.exists(CA_BUNDLE):
        session.verify = CA_BUNDLE

    all_records: list[dict] = []
    start = 0

    with open(LOG_PATH, "a", encoding="utf-8") as log_fh:
        log_line(log_fh, f"=== fetch_bitmex_insurance.py start proxy={proxy!r} verify={session.verify!r} ===")
        while True:
            page = fetch_page(session, start, log_fh)
            if not page:
                break
            all_records.extend(page)
            if len(page) < PAGE_SIZE:
                break
            start += PAGE_SIZE
            time.sleep(SLEEP_SECONDS)
        log_line(log_fh, f"=== fetch complete: total_records={len(all_records)} ===")

    # Write JSONL gz (raw API JSON, one record per line, in fetched order)
    with gzip.open(JSONL_GZ, "wt", encoding="utf-8") as gz:
        for rec in all_records:
            gz.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

    # Write flattened CSV, sorted by (timestamp, currency)
    sorted_records = sorted(all_records, key=lambda r: (r.get("timestamp", ""), r.get("currency", "")))
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["timestamp", "currency", "walletBalance"])
        for rec in sorted_records:
            writer.writerow([rec.get("timestamp"), rec.get("currency"), rec.get("walletBalance")])

    print(f"Wrote {len(all_records)} records to {JSONL_GZ} and {CSV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
