#!/usr/bin/env python3
"""Fetch bitFlyer lightchart 1-minute OHLC history for FX_BTC_JPY.

Source: https://lightchart.bitflyer.com/api/ohlc?symbol=FX_BTC_JPY&period=m
(unauthenticated, public chart backend used by bitFlyer's own web chart).

Behaviour discovered by probing (see
backtest_data/audit_fetch_bitflyer_history_20260906/README.md):
  - period=m is the only working period value (h/d return HTTP 501).
  - The server snaps `before` (epoch ms) down to a 12-hour UTC grid boundary
    and 301-redirects to the canonical URL (?...&before=<aligned>&type=full
    &grouping=1). Each canonical page returns up to 720 rows (12h of 1m
    bars), newest-first, oldest row exactly at aligned-12h+60000 unless the
    market has gaps.
  - Row shape (10 fields), newest examples:
        [ts_ms, open, high, low, close, volume,
         col7, col8, buy_volume, sell_volume]
    buy_volume + sell_volume == volume on every row checked. col7/col8 are
    much larger than the bar's own volume and drift slowly bar-to-bar --
    inferred (NOT confirmed by bitFlyer docs) to be long/short open
    interest snapshots for the FX product. Bars before ~2017-07 carry
    col7..col10 as null (only OHLCV populated back then).
  - Data was observed to start around 2015-11-30 (page for `before`
    2015-12-01 00:00 UTC returned 719 rows ending 2015-11-30 23:41 UTC;
    2015-11-01 and earlier returned 0 rows). Not re-verified to the minute
    by this script; it simply stops when a page comes back empty.

This script is resumable and polite:
  - Each 12h window is written to its own raw JSON file
    raw/page_<start_ts_ms>_<end_ts_ms>.json. A page already on disk (valid
    JSON, non-empty, unless it was the terminal empty page) is never
    re-fetched -- rerun the script anytime to continue where it left off.
  - `--sleep` (default 0.5s) between requests.
  - `--until-empty` (default) walks backward from `--before` (default: now)
    until a page returns zero rows (or `--stop-before-ts` is reached).
  - `--dry-run` prints the plan (first window, sleep, output dir) and exits
    without making any network request.
  - `--rebuild` skips fetching entirely and just (re)consolidates whatever
    raw/page_*.json files already exist under `--out` into
    candles_1m.csv.gz / gaps_gt5min.txt / MD5SUMS -- delegates to
    scripts/build_bitflyer_lightchart_csv.py's rebuild(), makes NO network
    request. Use this after a fetch run adds new pages, instead of
    re-fetching to regenerate the derived files.

Usage:
    python scripts/fetch_bitflyer_lightchart.py --dry-run
    python scripts/fetch_bitflyer_lightchart.py \
        --out backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906 \
        --sleep 0.5
    python scripts/fetch_bitflyer_lightchart.py \
        --out backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906 \
        --rebuild
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

BASE_URL = "https://lightchart.bitflyer.com/api/ohlc"
WINDOW_MS = 12 * 60 * 60 * 1000  # server buckets requests into 12h windows
COLUMNS = [
    "ts_ms", "open", "high", "low", "close", "volume",
    "col7_inferred_long_oi", "col8_inferred_short_oi",
    "buy_volume", "sell_volume",
]


def floor_window(ts_ms: int) -> int:
    return (ts_ms // WINDOW_MS) * WINDOW_MS


def fetch_page(session: requests.Session, before_ms: int, symbol: str, timeout: float = 20.0):
    params = {"symbol": symbol, "period": "m", "before": before_ms}
    resp = session.get(BASE_URL, params=params, timeout=timeout, allow_redirects=True)
    return resp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="FX_BTC_JPY",
                     help="lightchart symbol, e.g. FX_BTC_JPY (default, CFD) or BTC_JPY (spot). "
                          "Same endpoint/pagination behaviour observed for BTC_JPY in the "
                          "P2-08 blindspot audit (2026-09-06): 301-redirects the same way, "
                          "unauthenticated, no separate probing done here beyond that.")
    ap.add_argument("--out", default="backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_run",
                     help="output directory (raw/ subdir + manifest live here)")
    ap.add_argument("--before", default=None,
                     help="ISO timestamp (UTC) to start paginating backward from; default: now")
    ap.add_argument("--stop-before-ts", type=int, default=0,
                     help="stop once the window end is <= this epoch-ms (0 = only stop on empty page)")
    ap.add_argument("--sleep", type=float, default=0.5, help="seconds between requests")
    ap.add_argument("--max-pages", type=int, default=0, help="0 = unlimited")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild", action="store_true",
                     help="no network: just consolidate existing raw/page_*.json "
                          "under --out into candles_1m.csv.gz/gaps_gt5min.txt/MD5SUMS")
    args = ap.parse_args()

    if args.rebuild:
        import build_bitflyer_lightchart_csv as build_mod
        build_mod.rebuild(Path(args.out))
        return 0

    if args.before:
        start_dt = datetime.fromisoformat(args.before.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        start_ms = int(start_dt.timestamp() * 1000)
    else:
        start_ms = int(time.time() * 1000)

    out_dir = Path(args.out)
    raw_dir = out_dir / "raw"

    # The server itself floors `before` to the 12h UTC grid (00:00/12:00)
    # and serves the window *ending* at that floor, so mirror that here.
    window_end = floor_window(start_ms)

    if args.dry_run:
        print(f"[dry-run] would fetch backward from window_end={window_end} "
              f"({datetime.fromtimestamp(window_end/1000, tz=timezone.utc).isoformat()})")
        print(f"[dry-run] output dir: {out_dir}  raw/: {raw_dir}")
        print(f"[dry-run] sleep between requests: {args.sleep}s")
        print(f"[dry-run] stop-before-ts: {args.stop_before_ts or '(only on empty page)'}")
        print("[dry-run] no network request made")
        return 0

    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "trade-bot-research/1.0 (+backtest data audit)"})

    pages_fetched = 0
    pages_skipped = 0
    consecutive_errors = 0

    while True:
        if args.stop_before_ts and window_end <= args.stop_before_ts:
            print(f"reached stop-before-ts, stopping at window_end={window_end}")
            break
        if args.max_pages and pages_fetched >= args.max_pages:
            print(f"reached --max-pages={args.max_pages}, stopping")
            break

        window_start = window_end - WINDOW_MS
        fname = raw_dir / f"page_{window_start}_{window_end}.json"

        if fname.exists():
            try:
                data = json.loads(fname.read_text())
                pages_skipped += 1
                if len(data) == 0:
                    print(f"existing page {fname.name} is the empty terminator; stopping")
                    break
                window_end = window_start
                continue
            except Exception:
                pass  # corrupt cache file, refetch

        try:
            resp = fetch_page(session, window_end, args.symbol)
        except requests.RequestException as exc:
            consecutive_errors += 1
            print(f"ERROR fetching before={window_end}: {exc}", file=sys.stderr)
            if consecutive_errors >= 5:
                print("5 consecutive errors, aborting", file=sys.stderr)
                return 1
            time.sleep(min(30, args.sleep * (2 ** consecutive_errors)))
            continue

        consecutive_errors = 0
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code} at before={window_end}: {resp.text[:200]}", file=sys.stderr)
            return 1

        fname.write_text(resp.text)
        try:
            data = json.loads(resp.text)
        except json.JSONDecodeError:
            print(f"non-JSON response at before={window_end}, saved raw to {fname}", file=sys.stderr)
            return 1

        pages_fetched += 1
        if pages_fetched % 20 == 0:
            print(f"...{pages_fetched} pages fetched, {pages_skipped} skipped (cached), "
                  f"currently at {datetime.fromtimestamp(window_end/1000, tz=timezone.utc).isoformat()}")

        if len(data) == 0:
            print(f"empty page at before={window_end}; history exhausted, stopping")
            break

        window_end = window_start
        time.sleep(args.sleep)

    print(f"done. pages_fetched={pages_fetched} pages_skipped={pages_skipped}")
    print(f"raw pages under: {raw_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
