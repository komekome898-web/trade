#!/usr/bin/env python3
"""
Fetch historical FX 1-minute BID/ASK candle data from Dukascopy's public
tick-data CDN, decode it, and merge it into a per-pair CSV.

--------------------------------------------------------------------------
VERIFIED FORMAT (empirically confirmed in this session, 2026-08-22)
--------------------------------------------------------------------------

Daily 1-minute candle file:

    https://datafeed.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM}/{DD}/{SIDE}_candles_min_1.bi5

    - PAIR is e.g. USDJPY (no slash).
    - MONTH IS ZERO-INDEXED: January = "00", December = "11".
    - SIDE is "BID" or "ASK".
    - Response body is LZMA-compressed (raw .7z/.lzma stream, decode with
      `lzma.decompress`, no container). An empty (0-byte) body decompresses
      to 0 bytes -- treat as "no data" rather than an error.
    - Decompressed payload is a flat array of 24-byte big-endian records,
      struct format ">IIIIIf" (5x uint32 + 1x float32):

          (time_offset_sec, open, close, low, high, volume)

      * time_offset_sec: seconds since 00:00:00 UTC of that calendar day
        (0, 60, 120, ... for each 1-minute bar -- confirmed by watching it
        increment by exactly 60 between consecutive records).
      * open/close/low/high: integer price * divisor. divisor is
        pair-dependent (Dukascopy "point value" convention):
          - JPY-quote pairs (pair ends in "JPY"): divisor = 1000
            (confirmed empirically for USDJPY against api.frankfurter.app
            reference rates on 2020-01-01 (~108.6), 2024-01-03 (~142.9-143.0
            intraday vs 143.02 fixing) and 2026-08-20 (~158.6-158.9 intraday
            vs 158.76 fixing) -- all within ~0.1%).
          - all other pairs (5-decimal quotes, e.g. EURUSD, GBPUSD):
            divisor = 100000 by documented Dukascopy convention. NOT
            independently re-verified in this session (only USDJPY was
            fetched) -- re-check empirically before trusting a non-JPY pair.
      * volume: float32, Dukascopy's own volume units (millions of the
        base currency notional per bar, roughly). Stored as-is.
    - Weekends/holidays still return HTTP 200 with a full 1440-record file
      where every record has volume == 0 and a constant flat price (not an
      error, not a short file). These are detected (total day volume == 0)
      and dropped rather than written -- the day is still marked "done" in
      the manifest so it is never re-fetched.
    - Dates with genuinely no file (future dates beyond what Dukascopy has
      published yet) return HTTP 404.
    - The endpoint intermittently returns HTTP 503 ("no server available")
      under completely ordinary load -- this is NOT a real failure, retry
      with backoff. A run of many consecutive 503s (see --max-503-streak)
      *is* treated as a signal to stop and report rather than hammering.

Hourly tick file (for later use, --ticks; NOT fetched by default):

    https://datafeed.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5

    LZMA-compressed, 20-byte big-endian records, struct ">IIIff":

        (time_offset_ms, ask, bid, ask_volume, bid_volume)

    time_offset_ms is milliseconds since the top of that UTC hour.
    ask/bid use the same pair-dependent divisor as the candle files.
    Verified against USDJPY 2024-01-03 13h: ask/bid ~142.93-142.94,
    consistent with the 1m BID candle at the same timestamp (142.947).

--------------------------------------------------------------------------

Usage:
    python scripts/fetch_dukascopy.py --pair USDJPY \\
        --start 2023-01-01 --end 2026-08-21 \\
        --out data/fx/USDJPY_1m.csv --workers 6

    # ASK side (for spread estimation), merged as ask_close:
    python scripts/fetch_dukascopy.py --pair USDJPY --side ASK \\
        --start 2026-07-23 --end 2026-08-21 \\
        --out data/fx/USDJPY_1m.csv --workers 6 --merge-ask-close

Idempotent / resumable: a sidecar manifest `{out}.manifest.json` records,
per calendar day, whether it was fetched ("ok"), found empty ("empty"), or
had no file ("nodata"). Re-running the same command only fetches days not
already in the manifest. Safe to Ctrl-C and re-run.
"""
from __future__ import annotations

import argparse
import json
import lzma
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "https://datafeed.dukascopy.com/datafeed"


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)

CANDLE_DTYPE = np.dtype([
    ("offset", ">u4"), ("open", ">u4"), ("close", ">u4"),
    ("low", ">u4"), ("high", ">u4"), ("volume", ">f4"),
])
TICK_DTYPE = np.dtype([
    ("offset_ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"),
    ("ask_vol", ">f4"), ("bid_vol", ">f4"),
])

# Pair-dependent price divisor. JPY-quote pairs -> 1000 (verified, USDJPY).
# Everything else defaults to 100000 (documented Dukascopy convention for
# 5-decimal pairs, NOT independently re-verified in this repo).
DIVISOR_OVERRIDES = {
    "USDJPY": 1000, "EURJPY": 1000, "GBPJPY": 1000, "AUDJPY": 1000,
    "CHFJPY": 1000, "CADJPY": 1000, "NZDJPY": 1000,
    "EURUSD": 100000, "GBPUSD": 100000, "AUDUSD": 100000,
    "NZDUSD": 100000, "USDCAD": 100000, "USDCHF": 100000,
}


def price_divisor(pair: str) -> float:
    if pair in DIVISOR_OVERRIDES:
        return DIVISOR_OVERRIDES[pair]
    return 1000.0 if pair.endswith("JPY") else 100000.0


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def candle_url(pair: str, d: date, side: str) -> str:
    return f"{BASE_URL}/{pair}/{d.year:04d}/{d.month - 1:02d}/{d.day:02d}/{side}_candles_min_1.bi5"


def tick_url(pair: str, d: date, hour: int) -> str:
    return f"{BASE_URL}/{pair}/{d.year:04d}/{d.month - 1:02d}/{d.day:02d}/{hour:02d}h_ticks.bi5"


class FetchError(Exception):
    pass


# The endpoint returns HTTP 503 ("no server available") noticeably more
# often once requests start overlapping across worker threads -- observed
# empirically in this session (isolated serial requests: mostly 1st-try
# 200s; 4 concurrent workers: several days needed all 5 retries and still
# failed). A small global minimum-interval limiter smooths request starts
# across all worker threads without giving up the concurrency win (threads
# still overlap on the network-wait portion of each request).
class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.next_ok = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_ok - now)
            self.next_ok = max(now, self.next_ok) + self.min_interval
        if delay:
            time.sleep(delay)


_RATE_LIMITER = RateLimiter(min_interval=0.25)


def _http_get(url: str, timeout: float = 20.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "trade-bot-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as e:
        raise FetchError(str(e)) from e


def fetch_bytes(url: str, retries: int = 8, backoff: float = 3.0) -> tuple[str, bytes]:
    """Returns (status, body) where status in {"ok", "nodata"}.
    Raises FetchError if retries are exhausted on transient failures."""
    last_err = None
    for attempt in range(retries):
        _RATE_LIMITER.wait()
        try:
            code, body = _http_get(url)
        except FetchError as e:
            last_err = e
            time.sleep(min(30.0, backoff * (attempt + 1)))
            continue
        if code == 200:
            return "ok", body
        if code == 404:
            return "nodata", b""
        if code == 503:
            last_err = FetchError("503 service unavailable")
            time.sleep(min(30.0, backoff * (attempt + 1)))
            continue
        # unexpected status: treat like a transient error and retry
        last_err = FetchError(f"HTTP {code}")
        time.sleep(min(30.0, backoff * (attempt + 1)))
    raise FetchError(f"exhausted retries for {url}: {last_err}")


def decode_candles(raw: bytes, day: date, divisor: float) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    n = len(raw) // CANDLE_DTYPE.itemsize
    arr = np.frombuffer(raw[: n * CANDLE_DTYPE.itemsize], dtype=CANDLE_DTYPE)
    day_start = pd.Timestamp(day, tz="UTC")
    ts = day_start + pd.to_timedelta(arr["offset"].astype("int64"), unit="s")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": arr["open"] / divisor,
        "high": arr["high"] / divisor,
        "low": arr["low"] / divisor,
        "close": arr["close"] / divisor,
        "volume": arr["volume"].astype("float64"),
    })
    return df


def decode_ticks(raw: bytes, day: date, hour: int, divisor: float) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(columns=["timestamp", "ask", "bid", "ask_vol", "bid_vol"])
    n = len(raw) // TICK_DTYPE.itemsize
    arr = np.frombuffer(raw[: n * TICK_DTYPE.itemsize], dtype=TICK_DTYPE)
    hour_start = pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=hour)
    ts = hour_start + pd.to_timedelta(arr["offset_ms"].astype("int64"), unit="ms")
    df = pd.DataFrame({
        "timestamp": ts,
        "ask": arr["ask"] / divisor,
        "bid": arr["bid"] / divisor,
        "ask_vol": arr["ask_vol"].astype("float64"),
        "bid_vol": arr["bid_vol"].astype("float64"),
    })
    return df


def fetch_day_candles(pair: str, d: date, side: str, divisor: float) -> tuple[str, pd.DataFrame]:
    url = candle_url(pair, d, side)
    status, body = fetch_bytes(url)
    if status == "nodata":
        return "nodata", pd.DataFrame()
    try:
        raw = lzma.decompress(body) if body else b""
    except lzma.LZMAError:
        # zero-byte / malformed compressed body -> treat as no data for the day
        return "nodata", pd.DataFrame()
    df = decode_candles(raw, d, divisor)
    if df.empty or df["volume"].sum() == 0.0:
        return "empty", pd.DataFrame()
    return "ok", df


# --------------------------------------------------------------------------- #
# manifest (idempotent resume)
# --------------------------------------------------------------------------- #
class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        if path.exists():
            self.data = json.loads(path.read_text())
        else:
            self.data = {"days": {}}

    def done_dates(self) -> set[str]:
        return set(self.data["days"].keys())

    def mark(self, d: date, status: str) -> None:
        with self.lock:
            self.data["days"][d.isoformat()] = status

    def save(self) -> None:
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=0, sort_keys=True))
            tmp.replace(self.path)


# --------------------------------------------------------------------------- #
# CSV merge (append-as-you-go, final sort/dedupe pass)
# --------------------------------------------------------------------------- #
CSV_LOCK = threading.Lock()


def append_csv(out_path: Path, df: pd.DataFrame) -> None:
    if df.empty:
        return
    with CSV_LOCK:
        header = not out_path.exists()
        df.to_csv(out_path, mode="a", header=header, index=False)


def finalize_csv(out_path: Path) -> pd.DataFrame:
    if not out_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(out_path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
    df.to_csv(out_path, index=False)
    return df


# --------------------------------------------------------------------------- #
def run_candles(pair: str, start: date, end: date, out_path: Path, workers: int,
                 side: str, max_503_streak: int, merge_ask_close: bool) -> int:
    divisor = price_divisor(pair)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = out_path.with_suffix(out_path.suffix + f".{side.lower()}.manifest.json")
    manifest = Manifest(manifest_path)

    all_days = list(daterange(start, end))
    todo = [d for d in all_days if d.isoformat() not in manifest.done_dates()]
    print(f"[{side}] pair={pair} divisor={divisor} range={start}..{end} "
          f"({len(all_days)} days, {len(todo)} pending, "
          f"{len(all_days) - len(todo)} already in manifest)")

    # ask_close merge mode: an ASK day has a DIFFERENT column set than the
    # BID csv it's merging into, so it can't be appended row-by-row into the
    # same file (columns would misalign). Buffer ASK frames in memory and
    # merge them into the existing target CSV once, at the end, instead.
    ask_close_buf: list[pd.DataFrame] = []
    ask_buf_lock = threading.Lock()
    target_path = out_path

    consecutive_fail = 0
    n_ok = n_empty = n_nodata = n_fail = 0
    lock = threading.Lock()

    def worker(d: date):
        nonlocal consecutive_fail, n_ok, n_empty, n_nodata, n_fail
        try:
            status, df = fetch_day_candles(pair, d, side, divisor)
        except FetchError as e:
            with lock:
                n_fail += 1
                consecutive_fail += 1
            print(f"  ! {d} FAILED after retries: {e}", flush=True)
            return "fail", d
        with lock:
            consecutive_fail = 0
            if status == "ok":
                n_ok += 1
            elif status == "empty":
                n_empty += 1
            else:
                n_nodata += 1
        if status == "ok":
            if merge_ask_close and side == "ASK":
                df = df.rename(columns={"close": "ask_close"})[["timestamp", "ask_close"]]
                with ask_buf_lock:
                    ask_close_buf.append(df)
            else:
                append_csv(target_path, df)
        manifest.mark(d, status)
        return status, d

    stop = False
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(worker, d): d for d in todo}
        n_done = 0
        for fut in as_completed(futures):
            n_done += 1
            status, d = fut.result()
            if n_done % 50 == 0 or n_done == len(todo):
                print(f"  progress {n_done}/{len(todo)}  ok={n_ok} empty={n_empty} "
                      f"nodata={n_nodata} fail={n_fail}", flush=True)
                manifest.save()  # periodic checkpoint so a kill mid-run can resume cleanly
            if status == "fail" and consecutive_fail >= max_503_streak:
                print(f"  !! {consecutive_fail} consecutive failures -- stopping early "
                      f"(politeness threshold). Re-run to resume.", flush=True)
                stop = True
                break
        if stop:
            for f in futures:
                f.cancel()

    manifest.save()
    print(f"[{side}] done: ok={n_ok} empty={n_empty} nodata={n_nodata} fail={n_fail} "
          f"(manifest={rel(manifest_path)})")

    if merge_ask_close and side == "ASK":
        if ask_close_buf and target_path.exists():
            ask_df = pd.concat(ask_close_buf, ignore_index=True)
            ask_df["timestamp"] = pd.to_datetime(ask_df["timestamp"], utc=True)
            ask_df = ask_df.drop_duplicates(subset="timestamp").sort_values("timestamp")
            base = pd.read_csv(target_path, parse_dates=["timestamp"])
            base["timestamp"] = pd.to_datetime(base["timestamp"], utc=True)
            base = base.drop(columns=["ask_close"], errors="ignore")
            merged = base.merge(ask_df, on="timestamp", how="left")
            merged = merged.sort_values("timestamp")
            merged.to_csv(target_path, index=False)
            print(f"[ASK] merged ask_close for {len(ask_df)} rows into "
                  f"{rel(target_path)} ({merged['ask_close'].notna().sum()} "
                  f"rows now have ask_close)")
        else:
            print("[ASK] nothing to merge (no ASK rows fetched or target csv missing)")
    else:
        df = finalize_csv(target_path)
        print(f"[{side}] {rel(target_path)}: {len(df)} rows total")
    return 0 if consecutive_fail < max_503_streak else 1


def run_ticks(pair: str, start: date, end: date, out_dir: Path, workers: int,
              side: str) -> int:
    """Stub for future use -- NOT invoked by default. Fetches per-hour tick
    files and writes one CSV per UTC day to out_dir."""
    divisor = price_divisor(pair)
    out_dir.mkdir(parents=True, exist_ok=True)
    for d in daterange(start, end):
        day_path = out_dir / f"{pair}_ticks_{d.isoformat()}.csv"
        if day_path.exists():
            continue
        frames = []
        for h in range(24):
            url = tick_url(pair, d, h)
            try:
                status, body = fetch_bytes(url)
            except FetchError as e:
                print(f"  ! {d} {h:02d}h FAILED: {e}")
                continue
            if status == "nodata":
                continue
            try:
                raw = lzma.decompress(body) if body else b""
            except lzma.LZMAError:
                continue
            frames.append(decode_ticks(raw, d, h, divisor))
        if frames:
            out = pd.concat(frames, ignore_index=True).sort_values("timestamp")
            out.to_csv(day_path, index=False)
            print(f"  {d}: {len(out)} ticks -> {rel(day_path)}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pair", required=True, help="e.g. USDJPY")
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC, inclusive)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (UTC, inclusive)")
    p.add_argument("--out", required=True, help="output CSV path")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--side", choices=["BID", "ASK"], default="BID")
    p.add_argument("--merge-ask-close", action="store_true",
                    help="when --side ASK, merge as an ask_close column into "
                         "--out (existing BID csv) instead of writing a "
                         "separate file")
    p.add_argument("--max-503-streak", type=int, default=25,
                    help="stop early after this many consecutive failed days "
                         "(politeness circuit breaker)")
    p.add_argument("--ticks", action="store_true",
                    help="fetch hourly tick files instead of daily 1m "
                         "candles (writes one CSV per day under --out as a "
                         "directory). Not used in the initial collection run.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    pair = args.pair.upper()

    if args.ticks:
        return run_ticks(pair, start, end, Path(args.out), args.workers, args.side)

    if args.merge_ask_close and args.side != "ASK":
        print("--merge-ask-close only makes sense with --side ASK", file=sys.stderr)
        return 2

    return run_candles(pair, start, end, Path(args.out), args.workers, args.side,
                        args.max_503_streak, args.merge_ask_close)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
