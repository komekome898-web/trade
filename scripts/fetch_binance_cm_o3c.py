#!/usr/bin/env python3
"""Fetch Binance Vision COIN-M (futures/cm) archives for BTCUSD_PERP:
liquidationSnapshot, metrics, aggTrades (daily) and fundingRate (monthly --
the monthly archive is the only one that carries a fundingRate column;
the daily fundingRate archive does not exist, KeyCount=0).

Written for the O-3c data-preservation pull (2026-09-13): Binance Vision has
already stopped serving the USD-M equivalent of these archives (KeyCount=0
for the whole range) and the COIN-M feed itself stops publishing after
2024-10-14, so this pulls the full available window once, verifies every zip
against its published .CHECKSUM, and leaves the raw zips on disk exactly as
served (no reformatting/concatenation -- unlike fetch_binance_vision.py's
klines path).

Source (daily kinds -- liquidationSnapshot, metrics, aggTrades):
    https://data.binance.vision/data/futures/cm/daily/<kind>/<SYMBOL>/
        <SYMBOL>-<kind>-YYYY-MM-DD.zip[.CHECKSUM]
Source (monthly kinds -- fundingRate):
    https://data.binance.vision/data/futures/cm/monthly/<kind>/<SYMBOL>/
        <SYMBOL>-<kind>-YYYY-MM.zip[.CHECKSUM]
(public, unauthenticated, S3-backed static dump maintained by Binance.)

Layout produced under --out:
    <kind>/<SYMBOL>/<SYMBOL>-<kind>-YYYY-MM-DD.zip   (daily kinds)
    <kind>/<SYMBOL>/<SYMBOL>-<kind>-YYYY-MM.zip      (monthly kinds)
    (+ same-named .CHECKSUM next to each)

Per-period outcomes are one of: ok (downloaded + checksum verified),
missing (404 from the server -- no such period published), checksum_fail
(downloaded twice, sha256 never matched the published CHECKSUM).

Resumable: a zip already on disk that passes its own .CHECKSUM is never
re-downloaded.

Usage:
    python scripts/fetch_binance_cm_o3c.py --kind liquidationSnapshot \
        --start-day 2023-06-25 --end-day 2024-10-14 \
        --out backtest_data/binance_cm_o3c_20260913 \
        --log docs/DATA/probes/20260913_binance_cm_o3c_fetch.log

    python scripts/fetch_binance_cm_o3c.py --kind fundingRate \
        --start-day 2023-05-01 --end-day 2024-11-30 \
        --out backtest_data/binance_cm_o3c_20260913 \
        --log docs/DATA/probes/20260913_binance_cm_o3c_fetch.log
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DAILY = "https://data.binance.vision/data/futures/cm/daily"
BASE_MONTHLY = "https://data.binance.vision/data/futures/cm/monthly"
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"

# Which kinds are published as monthly-only archives (no daily equivalent).
MONTHLY_KINDS = {"fundingRate"}


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_checksum(data: bytes, checksum_text: str) -> bool:
    expected = checksum_text.strip().split()[0].lower()
    return sha256_of(data) == expected


def day_range(start_day: str, end_day: str):
    d = datetime.strptime(start_day, "%Y-%m-%d").date()
    end = datetime.strptime(end_day, "%Y-%m-%d").date()
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def month_range(start_day: str, end_day: str):
    """Yield 'YYYY-MM' for every month between start_day and end_day
    (inclusive, by month), given YYYY-MM-DD boundaries."""
    start = datetime.strptime(start_day, "%Y-%m-%d").date()
    end = datetime.strptime(end_day, "%Y-%m-%d").date()
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def download(session: requests.Session, url: str, timeout: float, retries: int = 5):
    """Returns (status_code, content_bytes_or_None). Retries transient
    network errors; a 404 is returned immediately, not retried."""
    last_exc = None
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=timeout)
        except requests.RequestException as exc:
            last_exc = exc
            wait = min(30, 2 ** attempt)
            print(f"    ! network error ({exc.__class__.__name__}), retry {attempt + 1}/{retries} in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return resp.status_code, resp.content
        return 200, resp.content
    raise RuntimeError(f"exhausted {retries} retries fetching {url}: {last_exc}")


def fetch_period(session: requests.Session, base_url: str, kind: str, symbol: str, period: str,
                  out_dir: Path, log_f, sleep: float) -> str:
    """Fetch one period's (day or month) zip + .CHECKSUM, verify, write to
    disk. Returns one of 'ok', 'cached', 'missing', 'checksum_fail'."""
    url = f"{base_url}/{kind}/{symbol}/{symbol}-{kind}-{period}.zip"
    dest = out_dir / f"{symbol}-{kind}-{period}.zip"
    cs_dest = Path(str(dest) + ".CHECKSUM")

    if dest.exists() and cs_dest.exists():
        try:
            if verify_checksum(dest.read_bytes(), cs_dest.read_text()):
                log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}\tCACHED\t{dest.stat().st_size}\tOK\n")
                return "cached"
        except Exception:
            pass  # corrupt cache, refetch

    for attempt in (1, 2):
        status, body = download(session, url, timeout=120.0)
        if status == 404:
            log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}\t404\t0\tN/A\n")
            return "missing"
        if status != 200 or body is None:
            log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}\t{status}\t0\tERROR\n")
            if attempt == 2:
                return "checksum_fail"
            time.sleep(2)
            continue

        cs_status, cs_body = download(session, url + ".CHECKSUM", timeout=60.0)
        if cs_status != 200 or cs_body is None:
            log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}.CHECKSUM\t{cs_status}\t0\tERROR\n")
            if attempt == 2:
                return "checksum_fail"
            time.sleep(2)
            continue
        checksum_text = cs_body.decode("utf-8")

        if verify_checksum(body, checksum_text):
            out_dir.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            cs_dest.write_text(checksum_text)
            log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}\t200\t{len(body)}\tOK\n")
            time.sleep(sleep)
            return "ok"
        else:
            log_f.write(f"{now_utc()}\t{kind}\t{period}\t{url}\t200\t{len(body)}\tMISMATCH(attempt{attempt})\n")
            if attempt == 2:
                return "checksum_fail"
            time.sleep(1)

    return "checksum_fail"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="BTCUSD_PERP")
    ap.add_argument("--kind", required=True,
                     choices=["liquidationSnapshot", "metrics", "aggTrades", "fundingRate"])
    ap.add_argument("--start-day", required=True, help="YYYY-MM-DD, first UTC day (inclusive)")
    ap.add_argument("--end-day", required=True, help="YYYY-MM-DD, last UTC day (inclusive)")
    ap.add_argument("--out", required=True, help="root output directory (kind/symbol/ subdir created under it)")
    ap.add_argument("--log", required=True, help="append-mode tsv log path")
    ap.add_argument("--sleep", type=float, default=0.15, help="seconds between successful requests")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    is_monthly = args.kind in MONTHLY_KINDS
    base_url = BASE_MONTHLY if is_monthly else BASE_DAILY
    periods = list(month_range(args.start_day, args.end_day)) if is_monthly \
        else list(day_range(args.start_day, args.end_day))
    out_dir = Path(args.out) / args.kind / args.symbol
    log_path = Path(args.log)

    if args.dry_run:
        print(f"[dry-run] kind={args.kind} symbol={args.symbol} granularity={'monthly' if is_monthly else 'daily'} "
              f"periods={len(periods)} ({periods[0]}..{periods[-1]}) out={out_dir} log={log_path}")
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.verify = CA_BUNDLE
    session.headers.update({"User-Agent": "trade-bot-research/1.0 (+O-3c data preservation)"})

    counts = {"ok": 0, "cached": 0, "missing": 0, "checksum_fail": 0}
    missing_periods, checksum_fail_periods = [], []
    with log_path.open("a") as log_f:
        for period in periods:
            print(f"{args.kind} {period} ...", end=" ", flush=True)
            result = fetch_period(session, base_url, args.kind, args.symbol, period, out_dir, log_f, args.sleep)
            counts[result] += 1
            print(result)
            if result == "missing":
                missing_periods.append(period)
            elif result == "checksum_fail":
                checksum_fail_periods.append(period)

    print(f"kind={args.kind} total={len(periods)} ok={counts['ok']} cached={counts['cached']} "
          f"missing={counts['missing']} checksum_fail={counts['checksum_fail']}")
    if missing_periods:
        print(f"missing_periods: {missing_periods}")
    if checksum_fail_periods:
        print(f"checksum_fail_periods: {checksum_fail_periods}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
