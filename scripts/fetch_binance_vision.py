#!/usr/bin/env python3
"""Fetch Binance Vision monthly (with daily fallback) klines and consolidate
them into one concatenated CSV, for any symbol/interval/date range.

Source: https://data.binance.vision/data/spot/{monthly,daily}/klines/<SYMBOL>/<INTERVAL>/...
(public, unauthenticated, S3-backed static file dump maintained by Binance).

Layout produced under --out:
    raw/<SYMBOL>-<INTERVAL>-YYYY-MM.zip[.CHECKSUM]        -- one per month that
        has a published monthly archive
    raw/daily_YYYY_MM/<SYMBOL>-<INTERVAL>-YYYY-MM-DD.zip[.CHECKSUM]
        -- fallback for a month whose monthly archive isn't published yet
           (e.g. the most recent, still-incomplete month)
    <out_basename>.csv.gz  -- concatenated, columns:
        open_time, open, high, low, close, volume, quote_volume,
        n_trades, taker_buy_base
        (close_time, taker_buy_quote, ignore dropped, matching the
        existing backtest_data/binance_BTCUSDT_1m_20240101_20260831 build)
    README.md   -- NOT written by this script (left to the caller, since the
                   README needs range/overlap context this script doesn't have)
    MD5SUMS     -- md5 of every raw file + the concatenated csv.gz

Format gotcha handled here: Binance Vision kline open_time/close_time
switched from millisecond to microsecond epoch integers starting with the
2025-01 files. Detected per-row (>= 1e14 => microseconds) rather than
assumed once for the whole range.

Resumable: a zip already on disk that passes its own .CHECKSUM is never
re-downloaded. Re-run any time to continue / retry.

Usage:
    python scripts/fetch_binance_vision.py --dry-run \
        --symbol BTCUSDT --interval 1m --start 2017-08 --end 2023-12 \
        --out backtest_data/binance_BTCUSDT_1m_20170801_20231231

    python scripts/fetch_binance_vision.py \
        --symbol BTCUSDT --interval 1m --start 2017-08 --end 2023-12 \
        --out backtest_data/binance_BTCUSDT_1m_20170801_20231231

    # offline: just re-consolidate raw/ already on disk into the csv.gz + MD5SUMS
    python scripts/fetch_binance_vision.py --out <dir> --consolidate-only
"""
from __future__ import annotations

import argparse
import calendar
import csv as csvmod
import gzip
import hashlib
import io
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import requests

BASE = "https://data.binance.vision/data/spot"
OUT_COLUMNS = ["open_time", "open", "high", "low", "close", "volume",
               "quote_volume", "n_trades", "taker_buy_base"]
US_THRESHOLD = 1e14  # ms epoch for now is ~1.8e12; us epoch is ~1.8e15 -- 1e14 cleanly separates them


def month_range(start: str, end: str):
    """Yield (year, month) inclusive from 'YYYY-MM' start to end."""
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_checksum(data: bytes, checksum_text: str) -> bool:
    expected = checksum_text.strip().split()[0].lower()
    return sha256_of(data) == expected


def download(session: requests.Session, url: str, timeout: float = 60.0, retries: int = 5):
    """Returns (status_code, content_bytes_or_None). Retries transient
    network errors (timeouts, resets) with exponential backoff -- a 404 is
    returned immediately, not retried."""
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
            return resp.status_code, None
        return 200, resp.content
    raise RuntimeError(f"exhausted {retries} retries fetching {url}: {last_exc}")


def fetch_one(session: requests.Session, url: str, dest: Path, sleep: float) -> bool:
    """Download url+'.CHECKSUM' and verify; write both to dest (zip) and
    dest with .CHECKSUM appended. Returns True on success (incl. already
    cached + verified), False if the zip URL 404s (caller may fall back)."""
    checksum_dest = Path(str(dest) + ".CHECKSUM")
    if dest.exists() and checksum_dest.exists():
        try:
            if verify_checksum(dest.read_bytes(), checksum_dest.read_text()):
                return True
        except Exception:
            pass  # corrupt cache, refetch

    status, zip_bytes = download(session, url, timeout=120.0)
    if status == 404:
        return False
    if status != 200 or zip_bytes is None:
        raise RuntimeError(f"HTTP {status} fetching {url}")

    cs_status, cs_bytes = download(session, url + ".CHECKSUM")
    if cs_status != 200 or cs_bytes is None:
        raise RuntimeError(f"HTTP {cs_status} fetching {url}.CHECKSUM")
    checksum_text = cs_bytes.decode("utf-8")

    if not verify_checksum(zip_bytes, checksum_text):
        raise RuntimeError(f"checksum mismatch for {url}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(zip_bytes)
    checksum_dest.write_text(checksum_text)
    time.sleep(sleep)
    return True


def iter_zip_rows(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert len(names) == 1, f"expected 1 file in {zip_path}, got {names}"
        with zf.open(names[0]) as f:
            text = io.TextIOWrapper(f, encoding="utf-8")
            reader = csvmod.reader(text)
            for row in reader:
                if not row:
                    continue
                # Binance Vision started shipping a header row (open_time,...)
                # in newer monthly archives -- skip it if the first field
                # isn't numeric.
                try:
                    int(row[0])
                except ValueError:
                    continue
                yield row


def normalize_epoch(raw_ts: int) -> int:
    """Return epoch milliseconds regardless of whether raw_ts is ms or us."""
    if raw_ts >= US_THRESHOLD:
        return raw_ts // 1000
    return raw_ts


def consolidate(root: Path, out_csv: Path, symbol: str, interval: str) -> dict:
    raw_dir = root / "raw"
    zips = sorted(raw_dir.glob(f"{symbol}-{interval}-*.zip")) + \
        sorted(raw_dir.glob(f"daily_*/{symbol}-{interval}-*.zip"))
    if not zips:
        raise SystemExit(f"no zip files found under {raw_dir}")

    rows: dict[int, list] = {}
    for zp in zips:
        for row in iter_zip_rows(zp):
            # Kline fields: 0 open_time,1 open,2 high,3 low,4 close,5 volume,
            # 6 close_time,7 quote_volume,8 n_trades,9 taker_buy_base,
            # 10 taker_buy_quote,11 ignore
            ts = normalize_epoch(int(row[0]))
            rows[ts] = [ts, row[1], row[2], row[3], row[4], row[5], row[7], row[8], row[9]]

    ts_sorted = sorted(rows.keys())
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_csv, "wt", newline="") as f:
        w = csvmod.writer(f)
        w.writerow(OUT_COLUMNS)
        for ts in ts_sorted:
            r = rows[ts]
            from datetime import datetime, timezone
            iso = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
            w.writerow([iso] + r[1:])

    # gap check: strict 1-minute cadence expected
    gaps = 0
    for a, b in zip(ts_sorted, ts_sorted[1:]):
        if b - a != 60000:
            gaps += 1

    stats = {
        "n_zips": len(zips),
        "n_rows": len(ts_sorted),
        "gaps": gaps,
        "range_start_ms": ts_sorted[0],
        "range_end_ms": ts_sorted[-1],
    }
    print(f"zips={len(zips)} rows={len(ts_sorted)} non-60s-gaps={gaps}")
    print(f"wrote {out_csv}")
    return stats


def write_md5sums(root: Path, extra_files: list[Path]) -> Path:
    md5_file = root / "MD5SUMS"
    with md5_file.open("w") as f:
        paths = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "MD5SUMS")
        for p in paths:
            h = hashlib.md5(p.read_bytes()).hexdigest()
            f.write(f"{h}  ./{p.relative_to(root)}\n")
    return md5_file


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", default="1m")
    ap.add_argument("--start", help="YYYY-MM, first month (inclusive)")
    ap.add_argument("--end", help="YYYY-MM, last month (inclusive)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between requests")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--consolidate-only", action="store_true",
                     help="no network: just rebuild the csv.gz + MD5SUMS from raw/ already on disk")
    args = ap.parse_args()

    root = Path(args.out)
    out_csv = root / f"{root.name}.csv.gz"

    if args.consolidate_only:
        consolidate(root, out_csv, args.symbol, args.interval)
        write_md5sums(root, [out_csv])
        print(f"wrote {root / 'MD5SUMS'}")
        return 0

    if not args.start or not args.end:
        ap.error("--start/--end required unless --consolidate-only")

    months = list(month_range(args.start, args.end))

    if args.dry_run:
        print(f"[dry-run] symbol={args.symbol} interval={args.interval}")
        print(f"[dry-run] {len(months)} months: {months[0]} .. {months[-1]}")
        print(f"[dry-run] out={root}")
        print("[dry-run] no network request made")
        return 0

    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data)"})

    monthly_ok, daily_fallback_months = [], []
    for y, m in months:
        ym = f"{y:04d}-{m:02d}"
        url = f"{BASE}/monthly/klines/{args.symbol}/{args.interval}/{args.symbol}-{args.interval}-{ym}.zip"
        dest = raw_dir / f"{args.symbol}-{args.interval}-{ym}.zip"
        print(f"month {ym}: monthly archive ...", end=" ", flush=True)
        ok = fetch_one(session, url, dest, args.sleep)
        if ok:
            print("OK")
            monthly_ok.append(ym)
            continue
        print("404, falling back to daily archives")
        daily_fallback_months.append(ym)
        n_days = calendar.monthrange(y, m)[1]
        for d in range(1, n_days + 1):
            day_str = f"{ym}-{d:02d}"
            if date(y, m, d) > date.today():
                break
            durl = f"{BASE}/daily/klines/{args.symbol}/{args.interval}/{args.symbol}-{args.interval}-{day_str}.zip"
            ddest = raw_dir / f"daily_{y:04d}_{m:02d}" / f"{args.symbol}-{args.interval}-{day_str}.zip"
            ok_d = fetch_one(session, durl, ddest, args.sleep)
            status = "OK" if ok_d else "404 (no data yet)"
            print(f"  day {day_str}: {status}")

    print(f"monthly archives ok: {len(monthly_ok)}; daily-fallback months: {daily_fallback_months}")
    stats = consolidate(root, out_csv, args.symbol, args.interval)
    write_md5sums(root, [out_csv])
    print(f"wrote {root / 'MD5SUMS'}")
    print(f"stats: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
