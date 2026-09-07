#!/usr/bin/env python3
"""Fetch Binance Vision monthly (with daily fallback) klines and consolidate
them into one concatenated CSV, for any symbol/interval/date range. Also
supports --kind aggTrades for per-day aggregated-trade dumps (P2-08b).

Source: https://data.binance.vision/data/<market>/{monthly,daily}/<kind>/<SYMBOL>/...
(public, unauthenticated, S3-backed static file dump maintained by Binance).
<market> is "spot" (default) or "futures/um" (--market um) -- see BLINDSPOT_AUDIT
#5 (USDT perpetual as a contrast signal source, docs/PHASE2/P2-08b/).

--kind klines (default, unchanged behaviour):
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

  Month range (--start/--end, YYYY-MM) or exact day range (--start-day/--end-day,
  YYYY-MM-DD, daily archives only -- no monthly lookup, no days outside the
  window) select the window to fetch.

--kind aggTrades (new): requires --start-day/--end-day (YYYY-MM-DD). Always
  daily archives (aggTrades has no monthly-consolidated shortcut used here).
  Layout produced under --out:
    raw/<SYMBOL>-aggTrades-YYYY-MM-DD.zip[.CHECKSUM]  -- one per UTC day
    <SYMBOL>-aggTrades-YYYY-MM-DD.csv.gz              -- one per UTC day (NOT
        concatenated -- P2-08b wants daily files), columns:
        agg_id, price, qty, first_id, last_id, ts_us, is_buyer_maker
        ts_us is the exchange timestamp normalized to UTC microseconds (spot
        dumps have shipped microseconds since 2025-01-01; futures/um dumps
        are still milliseconds -- see normalize_to_us()). is_buyer_maker is
        lowercased "true"/"false" regardless of source casing. The upstream
        is_best_match column (spot only) is dropped -- not part of the
        registered schema.
    MD5SUMS     -- md5 of every raw file + every daily csv.gz
    README.md   -- NOT written by this script (same rationale as above)

Format gotcha handled here: Binance Vision kline open_time/close_time
switched from millisecond to microsecond epoch integers starting with the
2025-01 files. Detected per-row (>= 1e14 => microseconds) rather than
assumed once for the whole range. aggTrades timestamps have the same
ms->us cutover; normalize_to_us() applies the same threshold.

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

    # exact day range, klines (e.g. a sub-month window), spot
    python scripts/fetch_binance_vision.py \
        --symbol BTCUSDT --interval 1s --start-day 2026-07-23 --end-day 2026-09-06 \
        --out backtest_data/binance_BTCUSDT_1s_20260723_20260906

    # aggTrades, daily csv.gz per day, USDT perpetual (futures/um) contrast source
    python scripts/fetch_binance_vision.py --kind aggTrades --market um \
        --symbol BTCUSDT --start-day 2026-07-23 --end-day 2026-09-06 \
        --out backtest_data/binance_um_BTCUSDT_aggTrades_20260723_20260906
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

MARKET_BASE = {
    "spot": "https://data.binance.vision/data/spot",
    "um": "https://data.binance.vision/data/futures/um",
}
BASE = MARKET_BASE["spot"]  # kept as module-level default for backward compat
OUT_COLUMNS = ["open_time", "open", "high", "low", "close", "volume",
               "quote_volume", "n_trades", "taker_buy_base"]
AGGTRADES_OUT_COLUMNS = ["agg_id", "price", "qty", "first_id", "last_id", "ts_us", "is_buyer_maker"]
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


def normalize_to_us(raw_ts: int) -> int:
    """Return epoch microseconds regardless of whether raw_ts is ms or us
    (see the ms->us cutover note in the module docstring)."""
    if raw_ts >= US_THRESHOLD:
        return raw_ts
    return raw_ts * 1000


def day_range(start_day: str, end_day: str):
    """Yield 'YYYY-MM-DD' strings inclusive from start_day to end_day."""
    d = datetime.strptime(start_day, "%Y-%m-%d").date()
    end = datetime.strptime(end_day, "%Y-%m-%d").date()
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def parse_aggtrades_zip(zip_path: Path) -> list[list[str]]:
    """Return rows from a Binance Vision aggTrades daily zip, header
    skipped, as lists of raw string fields (7 cols for futures/um -- no
    is_best_match -- or 8 cols for spot)."""
    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert len(names) == 1, f"expected 1 file in {zip_path}, got {names}"
        with zf.open(names[0]) as f:
            text = io.TextIOWrapper(f, encoding="utf-8")
            reader = csvmod.reader(text)
            for row in reader:
                if not row:
                    continue
                try:
                    int(row[0])
                except ValueError:
                    continue  # header row (agg_trade_id,price,...)
                rows.append(row)
    return rows


def write_aggtrades_day_csv(rows: list[list[str]], out_csv: Path) -> int:
    """Write one day's aggTrades rows to a gzipped csv with the registered
    P2-08b schema (agg_id, price, qty, first_id, last_id, ts_us,
    is_buyer_maker), sorted by agg_id. Returns the row count."""
    parsed = []
    for row in rows:
        agg_id, price, qty, first_id, last_id, ts_raw = row[0], row[1], row[2], row[3], row[4], row[5]
        is_buyer_maker = str(row[6]).strip().lower() == "true"
        parsed.append((int(agg_id), price, qty, int(first_id), int(last_id),
                        normalize_to_us(int(ts_raw)), is_buyer_maker))
    parsed.sort(key=lambda r: r[0])
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_csv, "wt", newline="") as f:
        w = csvmod.writer(f)
        w.writerow(AGGTRADES_OUT_COLUMNS)
        for agg_id, price, qty, first_id, last_id, ts_us, is_bm in parsed:
            w.writerow([agg_id, price, qty, first_id, last_id, ts_us, "true" if is_bm else "false"])
    return len(parsed)


def fetch_aggtrades_daily(session: requests.Session, root: Path, symbol: str, base: str,
                           start_day: str, end_day: str, sleep: float, dry_run: bool) -> dict:
    """Fetch one aggTrades daily zip per UTC day in [start_day, end_day] and
    write one csv.gz per day (P2-08b wants daily files, not one big
    concatenation -- unlike the klines consolidate() path)."""
    days = list(day_range(start_day, end_day))
    if dry_run:
        print(f"[dry-run] kind=aggTrades symbol={symbol} base={base}")
        print(f"[dry-run] {len(days)} days: {days[0]} .. {days[-1]}")
        print(f"[dry-run] out={root}")
        print("[dry-run] no network request made")
        return {}

    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ok_days, missing_days, total_rows = [], [], 0
    for day in days:
        url = f"{base}/daily/aggTrades/{symbol}/{symbol}-aggTrades-{day}.zip"
        dest = raw_dir / f"{symbol}-aggTrades-{day}.zip"
        print(f"day {day}: aggTrades ...", end=" ", flush=True)
        ok = fetch_one(session, url, dest, sleep)
        if not ok:
            print("404 (no data)")
            missing_days.append(day)
            continue
        rows = parse_aggtrades_zip(dest)
        out_csv = root / f"{symbol}-aggTrades-{day}.csv.gz"
        n = write_aggtrades_day_csv(rows, out_csv)
        total_rows += n
        ok_days.append(day)
        print(f"OK ({n} rows)")

    stats = {"n_days_ok": len(ok_days), "n_days_missing": len(missing_days),
              "missing_days": missing_days, "total_rows": total_rows,
              "range_start_day": days[0], "range_end_day": days[-1]}
    print(f"aggTrades: days_ok={len(ok_days)} days_missing={len(missing_days)} "
          f"total_rows={total_rows} missing={missing_days}")
    return stats


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
    ap.add_argument("--kind", choices=["klines", "aggTrades"], default="klines",
                     help="klines (default, unchanged) or aggTrades (P2-08b, always daily files)")
    ap.add_argument("--market", choices=["spot", "um"], default="spot",
                     help="spot (default) or um (USDT-margined perpetual futures, contrast source)")
    ap.add_argument("--start", help="YYYY-MM, first month (inclusive; klines only)")
    ap.add_argument("--end", help="YYYY-MM, last month (inclusive; klines only)")
    ap.add_argument("--start-day", help="YYYY-MM-DD, first UTC day (inclusive; exact day-range mode)")
    ap.add_argument("--end-day", help="YYYY-MM-DD, last UTC day (inclusive; exact day-range mode)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between requests")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--consolidate-only", action="store_true",
                     help="no network: just rebuild the csv.gz + MD5SUMS from raw/ already on disk (klines only)")
    args = ap.parse_args()

    root = Path(args.out)
    out_csv = root / f"{root.name}.csv.gz"
    base = MARKET_BASE[args.market]

    if args.consolidate_only:
        if args.kind == "aggTrades":
            ap.error("--consolidate-only is klines-only; aggTrades writes daily files as it fetches")
        consolidate(root, out_csv, args.symbol, args.interval)
        write_md5sums(root, [out_csv])
        print(f"wrote {root / 'MD5SUMS'}")
        return 0

    if args.kind == "aggTrades":
        if not args.start_day or not args.end_day:
            ap.error("--kind aggTrades requires --start-day/--end-day")
        session = requests.Session()
        session.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data)"})
        stats = fetch_aggtrades_daily(session, root, args.symbol, base,
                                       args.start_day, args.end_day, args.sleep, args.dry_run)
        if args.dry_run:
            return 0
        write_md5sums(root, [])
        print(f"wrote {root / 'MD5SUMS'}")
        print(f"stats: {stats}")
        return 0

    if args.start_day and args.end_day:
        # exact day-range mode for klines: daily archives only, no monthly
        # lookup, no days outside the window (unlike --start/--end below).
        if args.dry_run:
            days = list(day_range(args.start_day, args.end_day))
            print(f"[dry-run] symbol={args.symbol} interval={args.interval} kind=klines market={args.market}")
            print(f"[dry-run] {len(days)} days: {days[0]} .. {days[-1]}")
            print(f"[dry-run] out={root}")
            print("[dry-run] no network request made")
            return 0
        raw_dir = root / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data)"})
        for day in day_range(args.start_day, args.end_day):
            url = f"{base}/daily/klines/{args.symbol}/{args.interval}/{args.symbol}-{args.interval}-{day}.zip"
            dest = raw_dir / f"{args.symbol}-{args.interval}-{day}.zip"
            print(f"day {day}: klines ...", end=" ", flush=True)
            ok = fetch_one(session, url, dest, args.sleep)
            print("OK" if ok else "404 (no data)")
        stats = consolidate(root, out_csv, args.symbol, args.interval)
        write_md5sums(root, [out_csv])
        print(f"wrote {root / 'MD5SUMS'}")
        print(f"stats: {stats}")
        return 0

    if not args.start or not args.end:
        ap.error("--start/--end (or --start-day/--end-day) required unless --consolidate-only")

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
        url = f"{base}/monthly/klines/{args.symbol}/{args.interval}/{args.symbol}-{args.interval}-{ym}.zip"
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
            durl = f"{base}/daily/klines/{args.symbol}/{args.interval}/{args.symbol}-{args.interval}-{day_str}.zip"
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
