#!/usr/bin/env python3
"""Resident multi-venue PUBLIC market-data recorder -> daily gz CSVs in
data/venues/.

Why this exists (Round 22 venue survey): the effective-cost floor race is
tight between bitFlyer CFD (~5.4bps) and GMO Coin exchange leverage
(~5.3bps); bitbank dropped its BTC/JPY rebate but keeps maker -0.02% on the
other JPY pairs, and GMO spot pays maker -0.01..-0.03%. Deciding the next
research steps (cross-venue lead/lag, CFD-spot basis re-audit, rebate-maker
feasibility) needs a CONTINUOUS multi-venue record — a 4h snapshot is a
single regime and cannot settle any of it. This recorder promotes that
collection to a permanent one, on the always-on home PC.

READ-ONLY: public REST endpoints only, no authentication, no order
endpoints, no API keys.

Streams and cadences (chosen by the lead — do not change):
    bitbank  ticker BTC/JPY + XRP/JPY       every  5s  (2 requests)
    bitbank  transactions BTC/JPY + XRP/JPY every 15s  (2 requests, tid-deduped)
    GMO      ticker, ALL symbols, 1 call    every 10s
    GMO      trades, BTC / BTC_JPY altern.  every 30s  (each symbol every 60s)
    bitFlyer ticker BTC_JPY (spot)          every 10s  (CFD side already
                                                        covered by the WS
                                                        recorder — not here)

GMO RATE LIMIT (hard requirement): the Round 22 survey measured GMO's
public API throttling at ~1 req/s effective — bursts above it answer
ERR-5003 (rate limit). This recorder therefore keeps the TOTAL GMO request
rate at 1/10 + 1/30 = 0.133 req/s, and must stay below 0.5 req/s under any
future edit (statically checked in tests/test_record_venues.py).

Outputs (data/venues/, all files daily, UTC dates, gzip):
    quotes_YYYYMMDD.csv.gz — all venues mixed, columns:
        ts_utc, venue, pair, bid, ask, last
        ts_utc is the exchange timestamp from the response where one exists
        (bitbank ms epoch, GMO ISO, bitFlyer ISO), ISO-8601 UTC.
    trades_{venue}_{pair}_YYYYMMDD.csv.gz — one file per venue+pair:
        ts_utc, price, size, side, tid
        side is normalized to BUY/SELL. tid is bitbank's transaction_id;
        GMO's public trades carry no id, so tid is a hash of
        (ts, price, size, side) — two genuinely identical prints in the
        same millisecond would collapse into one (rare, accepted).

Robustness:
  - one thread per stream with its OWN backoff (interval * 2^k, capped at
    5 min): a venue outage never stalls the other venues' cadence;
  - every error is one stderr line and the stream continues;
  - empty / unexpectedly-shaped responses are skipped without a row;
  - rows are buffered and flushed every ~60s as a NEW gzip member appended
    to the daily file (same multi-member concatenation extract_tape.py
    uses; gzip.open('rt') reads all members back as one stream), so a hard
    kill loses at most the last buffer and never corrupts earlier members;
  - files roll over at the UTC date boundary (row date picks the file);
  - on (re)start the known tids are restored from today's AND yesterday's
    trades files (tolerating a truncated gz tail), so a restart does not
    re-emit trades the previous run already wrote.

Expected volume (rough): quotes ~290k rows/day (GMO's all-symbol ticker
measured 29 symbols on 2026-08-27, x 8,640 calls/day; bitbank 34.6k;
bitFlyer 8.6k) ~= 2-4 MB/day gz; the four trades files well under 1 MB/day
together. Order of 5 MB/day, ~150 MB/month.

Usage:
    python scripts/record_venues.py                 # run until Ctrl+C
    python scripts/record_venues.py --minutes 5     # timed run (smoke test)
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
import sys
import threading
import time
import zlib
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data" / "venues"

BITBANK = "https://public.bitbank.cc"
GMO = "https://api.coin.z.com/public/v1"
BITFLYER = "https://api.bitflyer.com/v1"

BITBANK_PAIRS = ("btc_jpy", "xrp_jpy")
GMO_TRADE_SYMBOLS = ("BTC", "BTC_JPY")   # spot BTC / leverage BTC_JPY, alternating

BITBANK_TICKER_INTERVAL = 5.0
BITBANK_TX_INTERVAL = 15.0
GMO_TICKER_INTERVAL = 10.0
GMO_TRADES_INTERVAL = 30.0
BITFLYER_TICKER_INTERVAL = 10.0

# Total GMO request rate. HARD CEILING 0.5 req/s (measured throttle ~1 req/s,
# ERR-5003 beyond it) — statically asserted in tests.
GMO_REQS_PER_SEC = 1.0 / GMO_TICKER_INTERVAL + 1.0 / GMO_TRADES_INTERVAL

TIMEOUT = 10.0
MAX_BACKOFF = 300.0
FLUSH_INTERVAL = 60.0

QUOTE_FIELDS = ["ts_utc", "venue", "pair", "bid", "ask", "last"]
TRADE_FIELDS = ["ts_utc", "price", "size", "side", "tid"]

# Raised by gzip/zlib when a compressed stream stops short (recorder killed
# mid-member). gzip.BadGzipFile is an OSError.
_TRUNCATED_GZ_ERRORS = (EOFError, OSError, zlib.error)

_FRACTION_RE = re.compile(r"^(.*T\d{2}:\d{2}:\d{2})\.(\d+)(.*)$")


# ---- timestamp helpers -----------------------------------------------------
def _iso_from_ms(ms: object) -> str:
    """ms epoch (bitbank) -> ISO-8601 UTC."""
    return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc
                                  ).isoformat(timespec="milliseconds")


def _iso_from_str(s: str) -> str:
    """Exchange ISO string (GMO '...Z', bitFlyer naive-UTC, any fraction
    length) -> normalized ISO-8601 UTC."""
    s = s.strip()
    m = _FRACTION_RE.match(s)
    if m:  # cap fractional seconds at 6 digits for fromisoformat
        s = f"{m.group(1)}.{m.group(2)[:6]}{m.group(3)}"
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:  # bitFlyer timestamps are UTC without a suffix
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _yyyymmdd(ts_iso: str) -> str:
    return ts_iso[:10].replace("-", "")


# ---- pure parsers (unit-tested on mock payloads) ---------------------------
def parse_bitbank_ticker(payload: dict, pair: str) -> list | None:
    """bitbank GET /{pair}/ticker -> quote row, or None on unexpected shape.
    bitbank: 'buy' is best bid, 'sell' is best ask."""
    if payload.get("success") != 1:
        raise RuntimeError(f"bitbank success={payload.get('success')} "
                           f"data={payload.get('data')!r}")
    d = payload.get("data") or {}
    try:
        float(d["buy"]), float(d["sell"]), float(d["last"])  # validate
        return [_iso_from_ms(d["timestamp"]), "bitbank", pair,
                d["buy"], d["sell"], d["last"]]
    except (KeyError, TypeError, ValueError):
        return None


def parse_bitbank_transactions(payload: dict) -> list[list]:
    """bitbank GET /{pair}/transactions -> chronological trade rows."""
    if payload.get("success") != 1:
        raise RuntimeError(f"bitbank success={payload.get('success')} "
                           f"data={payload.get('data')!r}")
    rows = []
    for t in (payload.get("data") or {}).get("transactions") or []:
        try:
            float(t["price"]), float(t["amount"])  # validate
            rows.append([_iso_from_ms(t["executed_at"]), t["price"],
                         t["amount"], str(t["side"]).upper(),
                         str(t["transaction_id"])])
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda r: (r[0], r[4]))
    return rows


def parse_gmo_ticker(payload: dict) -> list[list]:
    """GMO GET /ticker (no symbol -> every symbol) -> quote rows."""
    if payload.get("status") != 0:
        raise RuntimeError(f"gmo status={payload.get('status')} "
                           f"messages={payload.get('messages')!r}")
    rows = []
    for item in payload.get("data") or []:
        try:
            float(item["bid"]), float(item["ask"]), float(item["last"])
            rows.append([_iso_from_str(item["timestamp"]), "gmo",
                         item["symbol"], item["bid"], item["ask"],
                         item["last"]])
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def _gmo_tid(ts: str, price: str, size: str, side: str) -> str:
    """GMO trades carry no id: derive a stable one from the print itself."""
    return hashlib.sha1(f"{ts}|{price}|{size}|{side}".encode()
                        ).hexdigest()[:16]


def parse_gmo_trades(payload: dict) -> list[list]:
    """GMO GET /trades?symbol=... (newest first) -> chronological rows."""
    if payload.get("status") != 0:
        raise RuntimeError(f"gmo status={payload.get('status')} "
                           f"messages={payload.get('messages')!r}")
    rows = []
    for t in reversed((payload.get("data") or {}).get("list") or []):
        try:
            float(t["price"]), float(t["size"])
            ts = _iso_from_str(t["timestamp"])
            side = str(t["side"]).upper()
            rows.append([ts, t["price"], t["size"], side,
                         _gmo_tid(ts, str(t["price"]), str(t["size"]), side)])
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def parse_bitflyer_ticker(payload: dict) -> list | None:
    """bitFlyer GET /ticker?product_code=BTC_JPY -> quote row or None."""
    try:
        float(payload["best_bid"]), float(payload["best_ask"])
        float(payload["ltp"])
        return [_iso_from_str(payload["timestamp"]), "bitflyer", "BTC_JPY",
                payload["best_bid"], payload["best_ask"], payload["ltp"]]
    except (KeyError, TypeError, ValueError):
        return None


# ---- output ----------------------------------------------------------------
class TidSet:
    """Bounded remembered-tid set. The public endpoints only return the
    most recent prints, so a few-thousand window is ample headroom."""

    def __init__(self, maxlen: int = 50_000):
        self._seen: set[str] = set()
        self._order: deque[str] = deque()
        self._maxlen = maxlen

    def add(self, tid: str) -> bool:
        """True if tid was unseen (and is now remembered)."""
        if tid in self._seen:
            return False
        self._seen.add(tid)
        self._order.append(tid)
        if len(self._order) > self._maxlen:
            self._seen.discard(self._order.popleft())
        return True


class DailyGzCsvWriter:
    """Buffered appender to per-UTC-day .csv.gz files. flush() writes each
    day's buffered rows as one new gzip member appended to that day's file
    (multi-member concatenation, as in extract_tape.py); the header row is
    written only when the file is created. Thread-safe."""

    def __init__(self, path_fn, fields: list[str]):
        self._path_fn = path_fn
        self._fields = fields
        self._buf: dict[str, list[list]] = {}
        self._lock = threading.Lock()

    def add(self, row: list) -> None:
        with self._lock:
            self._buf.setdefault(_yyyymmdd(row[0]), []).append(row)

    def flush(self) -> int:
        with self._lock:
            pending, self._buf = self._buf, {}
        written = 0
        for date_str in sorted(pending):
            path = self._path_fn(date_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            new_file = not path.exists() or path.stat().st_size == 0
            with gzip.open(path, "wt" if new_file else "at",
                           encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                if new_file:
                    w.writerow(self._fields)
                w.writerows(pending[date_str])
            written += len(pending[date_str])
        return written


class _Stream:
    def __init__(self, name: str, interval: float, fn):
        self.name, self.interval, self.fn = name, interval, fn


class VenueRecorder:
    def __init__(self, out_dir: str | Path = DEFAULT_OUT_DIR,
                 session: requests.Session | None = None):
        self.out_dir = Path(out_dir)
        self.session = session or requests.Session()
        self.quotes = DailyGzCsvWriter(
            lambda d: self.out_dir / f"quotes_{d}.csv.gz", QUOTE_FIELDS)
        self._trades: dict[tuple[str, str], tuple[DailyGzCsvWriter, TidSet]] = {}
        self._gmo_trade_i = 0
        self._stop = threading.Event()
        self.rows_written = 0
        self.streams = [
            _Stream("bitbank-ticker", BITBANK_TICKER_INTERVAL,
                    self._tick_bitbank_ticker),
            _Stream("bitbank-trades", BITBANK_TX_INTERVAL,
                    self._tick_bitbank_trades),
            _Stream("gmo-ticker", GMO_TICKER_INTERVAL, self._tick_gmo_ticker),
            _Stream("gmo-trades", GMO_TRADES_INTERVAL, self._tick_gmo_trades),
            _Stream("bitflyer-ticker", BITFLYER_TICKER_INTERVAL,
                    self._tick_bitflyer_ticker),
        ]

    # ---- plumbing ----------------------------------------------------------
    def _get(self, url: str, params: dict | None = None) -> dict:
        r = self.session.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    def _trades_path(self, venue: str, pair: str, date_str: str) -> Path:
        return self.out_dir / f"trades_{venue}_{pair.lower()}_{date_str}.csv.gz"

    def _trades_writer(self, venue: str, pair: str
                       ) -> tuple[DailyGzCsvWriter, TidSet]:
        key = (venue, pair)
        if key not in self._trades:
            writer = DailyGzCsvWriter(
                lambda d, v=venue, p=pair: self._trades_path(v, p, d),
                TRADE_FIELDS)
            tids = TidSet()
            self._restore_tids(venue, pair, tids)
            self._trades[key] = (writer, tids)
        return self._trades[key]

    def _restore_tids(self, venue: str, pair: str, tids: TidSet) -> None:
        """Reload known tids from yesterday's and today's files so a restart
        never re-emits a trade the previous run already wrote. Yesterday
        first, so today's tids sit newest in the eviction order. A truncated
        gz tail (previous run killed mid-flush) keeps whatever parsed."""
        now = datetime.now(timezone.utc)
        restored = 0
        for delta in (1, 0):
            path = self._trades_path(venue, pair,
                                     (now - timedelta(days=delta)
                                      ).strftime("%Y%m%d"))
            if not path.exists():
                continue
            try:
                with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # header
                    for row in reader:
                        if len(row) >= 5 and tids.add(row[4]):
                            restored += 1
            except _TRUNCATED_GZ_ERRORS:
                pass
        if restored:
            print(f"[record_venues] restored {restored} known tids "
                  f"for {venue} {pair}", flush=True)

    def _add_trades(self, venue: str, pair: str, rows: list[list]) -> None:
        writer, tids = self._trades_writer(venue, pair)
        for row in rows:
            if tids.add(row[4]):
                writer.add(row)
                self.rows_written += 1

    def _add_quote(self, row: list | None) -> None:
        if row is not None:
            self.quotes.add(row)
            self.rows_written += 1

    # ---- one poll per stream ----------------------------------------------
    def _tick_bitbank_ticker(self) -> None:
        for pair in BITBANK_PAIRS:
            payload = self._get(f"{BITBANK}/{pair}/ticker")
            self._add_quote(parse_bitbank_ticker(payload, pair))

    def _tick_bitbank_trades(self) -> None:
        for pair in BITBANK_PAIRS:
            payload = self._get(f"{BITBANK}/{pair}/transactions")
            self._add_trades("bitbank", pair, parse_bitbank_transactions(payload))

    def _tick_gmo_ticker(self) -> None:
        payload = self._get(f"{GMO}/ticker")
        for row in parse_gmo_ticker(payload):
            self._add_quote(row)

    def _tick_gmo_trades(self) -> None:
        # Advance BEFORE the request so one failing symbol cannot starve
        # the other one out of its turn.
        symbol = GMO_TRADE_SYMBOLS[self._gmo_trade_i % len(GMO_TRADE_SYMBOLS)]
        self._gmo_trade_i += 1
        payload = self._get(f"{GMO}/trades",
                            params={"symbol": symbol, "page": 1, "count": 100})
        self._add_trades("gmo", symbol, parse_gmo_trades(payload))

    def _tick_bitflyer_ticker(self) -> None:
        payload = self._get(f"{BITFLYER}/ticker",
                            params={"product_code": "BTC_JPY"})
        self._add_quote(parse_bitflyer_ticker(payload))

    # ---- run loop ----------------------------------------------------------
    def flush_all(self) -> int:
        n = self.quotes.flush()
        for writer, _tids in self._trades.values():
            n += writer.flush()
        return n

    def _stream_loop(self, stream: _Stream) -> None:
        fails = 0
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                stream.fn()
                fails = 0
            except Exception as e:  # noqa: BLE001 - resident by design
                fails += 1
                print(f"[record_venues] {stream.name} FAILED "
                      f"({fails}x): {type(e).__name__}: {e}",
                      file=sys.stderr, flush=True)
            if fails:
                delay = min(stream.interval * (2 ** min(fails, 8)), MAX_BACKOFF)
            else:
                delay = max(0.5, stream.interval - (time.monotonic() - t0))
            self._stop.wait(delay)

    def _flush_loop(self) -> None:
        while not self._stop.wait(FLUSH_INTERVAL):
            self.flush_all()

    def run(self, duration_sec: float | None = None) -> None:
        print(f"[record_venues] writing {self.out_dir} "
              f"({len(self.streams)} streams; GMO {GMO_REQS_PER_SEC:.3f} req/s)",
              flush=True)
        threads = [threading.Thread(target=self._stream_loop, args=(s,),
                                    name=s.name, daemon=True)
                   for s in self.streams]
        threads.append(threading.Thread(target=self._flush_loop,
                                        name="flusher", daemon=True))
        for t in threads:
            t.start()
        try:
            self._stop.wait(duration_sec)  # None = run until interrupted
        finally:
            self._stop.set()
            for t in threads:
                t.join(timeout=15)
            self.flush_all()
            print(f"[record_venues] stopped ({self.rows_written} rows total)",
                  flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--minutes", type=float, default=None,
                    help="run for N minutes then exit (default: forever)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    recorder = VenueRecorder(out_dir=args.out_dir)
    try:
        recorder.run(args.minutes * 60 if args.minutes else None)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
