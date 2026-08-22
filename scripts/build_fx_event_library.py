#!/usr/bin/env python3
"""
Build the FX EVENT-TICK LIBRARY: raw Dukascopy USD/JPY ticks inside a tight
window around every verified macro event in data/fx/calendar.csv.

    input   data/fx/calendar.csv        (scripts/fetch_fx_calendar.py)
    output  data/fx/events/{TYPE}_{YYYYMMDD}.csv.gz
            columns: ts_utc,bid,ask,bidvol,askvol      (ts_utc = epoch ms, UTC)
    state   data/fx/events/manifest.json (idempotent resume)

WHY TICKS
---------
docs/KNOWLEDGE_FX.md sec.3.5 records "event direction continuation (1-minute)"
as UNESTABLISHED AT 1-MINUTE RESOLUTION: the volatility mechanism is real
(range 2.6-4.5x on 29/29) but a release impulse is often complete within 2-10
seconds, so a 1-minute bar close is a LATE and PARTIAL view of it and the entry
price is one a real order would never have obtained.  This library is the
re-audit substrate: the first seconds, with both sides of the book quoted.

WINDOWS (fixed here, not tunable)
---------------------------------
  NFP / CPI / FOMC   [E - 15 min, E + 45 min]        E = calendar.csv time_utc
  BOJ                [date 02:00 UTC, date 05:00 UTC]
                     BOJ does not pre-announce a release clock time; the
                     release DRIFTS across roughly 11:30-13:30 JST and the
                     drift is itself the volatility source (KNOWLEDGE_FX sec.2,
                     report s).  So the whole band is kept, not a minute.

DUKASCOPY TICK FORMAT (docs/KNOWLEDGE_FX.md sec.5, verified in-repo)
-------------------------------------------------------------------
    {BASE}/{PAIR}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5
    MONTH IS ZERO-INDEXED (January = 00); day and hour are 1-/0-based normally.
    LZMA raw stream; 20-byte big-endian records ">IIIff" =
    (ms offset in hour, ask, bid, ask_vol, bid_vol); JPY divisor 1000.
The decode, the URL builder and the RateLimiter are IMPORTED from
scripts/fetch_dukascopy.py rather than re-implemented, so this library cannot
drift from the 1-minute candle data it will be cross-checked against.

POLITENESS
----------
The documented floor is ~0.25 s between request starts.  This script uses a
GLOBAL 0.35 s floor and, if HTTP 429s arrive in a wave (>= 5 inside 120 s), it
permanently slows to 0.60 s for the rest of the run and says so in the log.
Only 4 threads overlap, and only because measured per-request latency through
the proxy is 7-14 s -- request STARTS never go faster than the floor, i.e. under
3 requests/second even at full tilt.  HTTP 503 is the endpoint's routine
"try again" under overlap (documented in fetch_dukascopy.py) and is retried with
backoff, counted but not treated as a failure.  404 / empty hours are tolerated
and logged (weekends, holidays, the 2020-03-15 Sunday emergency FOMC), never
retried into the ground.

Usage
-----
    python scripts/build_fx_event_library.py                      # all events
    python scripts/build_fx_event_library.py --types FOMC BOJ
    python scripts/build_fx_event_library.py --validate-only      # step-3 table

Resume-safe: every finished event is recorded in manifest.json with its status
and row count; re-running only fetches what is missing.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import lzma
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_dukascopy as duka                                   # noqa: E402

CAL = ROOT / "data" / "fx" / "calendar.csv"
OUTDIR = ROOT / "data" / "fx" / "events"
MANIFEST = OUTDIR / "manifest.json"
CANDLES = ROOT / "data" / "fx" / "USDJPY_1m.csv"

PAIR = "USDJPY"
PRE_MIN, POST_MIN = 15, 45
BOJ_WINDOW = (dt.time(2, 0), dt.time(5, 0))

MIN_INTERVAL = 0.35
SLOW_INTERVAL = 0.60
UTC = dt.timezone.utc


# --------------------------------------------------------------------------- #
# global politeness governor
# --------------------------------------------------------------------------- #
class Governor:
    """duka.RateLimiter plus a 429-wave detector that slows the whole run."""

    def __init__(self) -> None:
        self.limiter = duka.RateLimiter(MIN_INTERVAL)
        self.lock = threading.Lock()
        self.hits_429: list[float] = []
        self.slowed = False
        self.n_429 = 0
        self.n_503 = 0

    def wait(self) -> None:
        self.limiter.wait()

    def saw_503(self) -> None:
        with self.lock:
            self.n_503 += 1

    def saw_429(self) -> None:
        now = time.monotonic()
        with self.lock:
            self.n_429 += 1
            self.hits_429.append(now)
            self.hits_429 = [t for t in self.hits_429 if now - t <= 120.0]
            if not self.slowed and len(self.hits_429) >= 5:
                self.slowed = True
                self.limiter.min_interval = SLOW_INTERVAL
                print(f"  !! 429 WAVE ({len(self.hits_429)} in 120s) -- global request "
                      f"interval slowed {MIN_INTERVAL}s -> {SLOW_INTERVAL}s for the rest "
                      f"of the run", flush=True)


GOV = Governor()


def fetch_hour(day: dt.date, hour: int, retries: int = 10) -> tuple[str, bytes]:
    """('ok'|'nodata'|'fail', raw_decompressed_bytes).

    HTTP 503 from this endpoint is NOT a real failure -- fetch_dukascopy.py
    documents it as routine once requests overlap across threads -- so it is
    retried with backoff rather than counted.  Measured single-request latency
    through the proxy is 7-14 s, which is why a few workers overlap at all;
    the global limiter still floors request STARTS at MIN_INTERVAL.
    """
    url = duka.tick_url(PAIR, day, hour)
    last = ""
    for attempt in range(retries):
        GOV.wait()
        try:
            code, body = duka._http_get(url, timeout=45.0)
        except duka.FetchError as e:
            last = str(e)
            time.sleep(min(30.0, 2.0 * (attempt + 1)))
            continue
        if code == 200:
            if not body:
                return "nodata", b""
            try:
                return "ok", lzma.decompress(body)
            except lzma.LZMAError:
                return "nodata", b""
        if code == 404:
            return "nodata", b""
        if code == 429:
            GOV.saw_429()
            time.sleep(min(60.0, 5.0 * (attempt + 1)))
            last = "HTTP 429"
            continue
        if code == 503:
            GOV.saw_503()
            time.sleep(min(30.0, 2.0 * (attempt + 1)))
            last = "HTTP 503"
            continue
        last = f"HTTP {code}"
        time.sleep(min(30.0, 3.0 * (attempt + 1)))
    print(f"  ! {day} {hour:02d}h FAILED after {retries} tries: {last}", flush=True)
    return "fail", b""


# --------------------------------------------------------------------------- #
def load_calendar(types: list[str] | None) -> list[dict]:
    ev: list[dict] = []
    with CAL.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if types and row["type"] not in types:
                continue
            ts = dt.datetime.strptime(row["time_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            d = dt.date.fromisoformat(row["date"])
            if row["type"] == "BOJ":
                start = dt.datetime.combine(d, BOJ_WINDOW[0], tzinfo=UTC)
                end = dt.datetime.combine(d, BOJ_WINDOW[1], tzinfo=UTC)
            else:
                start = ts - dt.timedelta(minutes=PRE_MIN)
                end = ts + dt.timedelta(minutes=POST_MIN)
            ev.append(dict(key=f"{row['type']}_{d:%Y%m%d}", type=row["type"], date=d,
                           ts=ts, start=start, end=end, source=row["source"],
                           confidence=row["confidence"], note=row["note"]))
    return ev


def hours_for(start: dt.datetime, end: dt.datetime) -> list[tuple[dt.date, int]]:
    h = start.replace(minute=0, second=0, microsecond=0)
    out = []
    while h <= end:
        out.append((h.date(), h.hour))
        h += dt.timedelta(hours=1)
    # an end exactly on an hour boundary needs no extra file
    if end.minute == 0 and end.second == 0 and len(out) > 1:
        out = out[:-1]
    return out


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.data = json.loads(path.read_text()) if path.exists() else {}

    def get(self, k: str):
        return self.data.get(k)

    def mark(self, k: str, rec: dict) -> None:
        with self.lock:
            self.data[k] = rec

    def save(self) -> None:
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=0, sort_keys=True))
            tmp.replace(self.path)


def build_event(ev: dict, divisor: float) -> dict:
    frames = []
    n_hours = n_nodata = n_fail = 0
    for day, hour in hours_for(ev["start"], ev["end"]):
        status, raw = fetch_hour(day, hour)
        n_hours += 1
        if status == "fail":
            n_fail += 1
            continue
        if status == "nodata" or not raw:
            n_nodata += 1
            continue
        frames.append(duka.decode_ticks(raw, day, hour, divisor))
    if n_fail and not frames:
        return dict(status="fail", rows=0, hours=n_hours, nodata=n_nodata, failed=n_fail)
    if not frames:
        return dict(status="empty", rows=0, hours=n_hours, nodata=n_nodata, failed=n_fail)

    df = pd.concat(frames, ignore_index=True)
    df = df[(df["timestamp"] >= ev["start"]) & (df["timestamp"] <= ev["end"])]
    df = df.sort_values("timestamp")
    if df.empty:
        return dict(status="empty", rows=0, hours=n_hours, nodata=n_nodata, failed=n_fail)

    # epoch MILLISECONDS.  Go through datetime64[ms] explicitly: the decoded
    # frame's datetime resolution is pandas-version dependent (ns or us), so
    # dividing a raw .astype("int64") by a fixed constant silently drops the
    # sub-second part -- which is the entire point of a tick library.
    ms = (df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
          .to_numpy().astype("datetime64[ms]").astype("int64"))
    out = pd.DataFrame({
        "ts_utc": ms,
        "bid": df["bid"].to_numpy(),
        "ask": df["ask"].to_numpy(),
        "bidvol": df["bid_vol"].to_numpy(),
        "askvol": df["ask_vol"].to_numpy(),
    })
    path = OUTDIR / f"{ev['key']}.csv.gz"
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="", compresslevel=9) as f:
        out.to_csv(f, index=False, float_format="%.6g")
    tmp.replace(path)
    return dict(status="ok", rows=len(out), hours=n_hours, nodata=n_nodata,
                failed=n_fail, bytes=path.stat().st_size,
                first_ms=int(out["ts_utc"].iloc[0]), last_ms=int(out["ts_utc"].iloc[-1]))


# --------------------------------------------------------------------------- #
# validation (step 3)
# --------------------------------------------------------------------------- #
VALIDATION_EVENTS = [
    ("FOMC_20240918", "FOMC 2024-09-18: first cut of the cycle, 50bp"),
    ("BOJ_20240731",  "BOJ 2024-07-31: rate hike + taper -> the yen-carry unwind"),
    ("NFP_20240802",  "NFP 2024-08-02: the Sahm-rule payrolls miss"),
    ("CPI_20221110",  "CPI 2022-11-10: the big downside CPI surprise"),
    ("FOMC_20220921", "FOMC 2022-09-21: 75bp hike, USD/JPY at intervention levels"),
]


def read_event(key: str) -> pd.DataFrame | None:
    p = OUTDIR / f"{key}.csv.gz"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    df["mid"] = 0.5 * (df["bid"] + df["ask"])
    return df


def validate(events: list[dict]) -> None:
    print("\n" + "=" * 108)
    print("VALIDATION -- what 1-minute bars could never see")
    print("=" * 108)
    by_key = {e["key"]: e for e in events}
    print(f"{'event':<16}{'release UTC':<22}{'ticks':>7}{'ticks/s':>9}"
          f"{'max 1s mid move (first 60s)':>30}{'at t+s':>9}{'60s net':>10}")
    print("-" * 108)
    for key, _label in VALIDATION_EVENTS:
        df = read_event(key)
        ev = by_key.get(key)
        if df is None or ev is None:
            print(f"{key:<16}{'-- not in library --'}")
            continue
        rel = ev["ts"] if ev["type"] != "BOJ" else None
        if rel is None:
            # BOJ: the release minute is unknown, so use the biggest 1s move in
            # the whole band and report where it landed (that IS the release).
            t0_ms = int(df["ts_utc"].iloc[0])
            span = df
        else:
            t0_ms = int(rel.timestamp() * 1000)
            span = df[(df["ts_utc"] >= t0_ms) & (df["ts_utc"] <= t0_ms + 60_000)]
        if span.empty:
            print(f"{key:<16}{'-- no ticks in the post-release minute --'}")
            continue
        sec = (span["ts_utc"] - t0_ms) // 1000
        g = span.groupby(sec)["mid"]
        first, last = g.first(), g.last()
        # move within each 1-second bucket, in bps
        mv = 1e4 * np.abs(np.log(last / first))
        # also the second-to-second jump
        allsec = pd.concat([first, last]).sort_index()
        best_s = int(mv.idxmax()) if len(mv) else -1
        max1s = float(mv.max()) if len(mv) else float("nan")
        net = 1e4 * float(np.log(span["mid"].iloc[-1] / span["mid"].iloc[0]))
        dur = (df["ts_utc"].iloc[-1] - df["ts_utc"].iloc[0]) / 1000.0
        relstr = ev["ts"].strftime("%Y-%m-%d %H:%M:%SZ") if ev["type"] != "BOJ" else \
            f"{ev['date']} 02:00-05:00Z"
        print(f"{key:<16}{relstr:<22}{len(df):>7}{len(df)/max(dur,1):>9.2f}"
              f"{max1s:>27.1f}bps{best_s:>9}{net:>+10.1f}")
    print("\n  'max 1s mid move' = largest |log(last/first)| inside a single 1-second bucket of")
    print("  the first 60 seconds after the release.  A 1-minute bar reports ONE number for the")
    print("  whole 60s; every bps in this column is invisible to it.  BOJ has no announced")
    print("  release minute, so its row scans the whole 02:00-05:00Z band and 'at t+s' is the")
    print("  seconds-offset from the band start where the impulse actually landed.")

    # ---- cross-check one window's mid against the 1m BID closes -------------
    print("\n" + "-" * 108)
    print("CROSS-CHECK vs data/fx/USDJPY_1m.csv (BID closes, +/-2bps tolerance)")
    print("-" * 108)
    key = "FOMC_20240918"
    df = read_event(key)
    if df is None or not CANDLES.exists():
        print("  skipped (event or candle file missing)")
        return
    c = pd.read_csv(CANDLES, parse_dates=["timestamp"])
    c["timestamp"] = pd.to_datetime(c["timestamp"], utc=True)
    df["ts"] = pd.to_datetime(df["ts_utc"], unit="ms", utc=True)
    df["minute"] = df["ts"].dt.floor("min")
    lastbid = df.groupby("minute")["bid"].last()
    cc = c.set_index("timestamp")["close"].reindex(lastbid.index)
    ok = cc.notna()
    diff = 1e4 * np.abs(np.log(lastbid[ok] / cc[ok]))
    print(f"  {key}: {int(ok.sum())} minutes compared")
    print(f"  max |diff| = {diff.max():.3f} bps   median = {diff.median():.3f} bps"
          f"   within 2bps: {int((diff <= 2).sum())}/{len(diff)}")
    print(f"  {'minute':<26}{'tick last BID':>15}{'1m close':>12}{'bps':>9}")
    for m in list(diff.index)[:6]:
        print(f"  {str(m):<26}{lastbid[m]:>15.3f}{cc[m]:>12.3f}{diff[m]:>9.3f}")
    print(f"  VERDICT: {'PASS' if diff.max() <= 2.0 else 'CHECK'} "
          f"(tick stream and the 1m candle file are the same instrument/scale)")


def density_report(manifest: Manifest, events: list[dict]) -> None:
    recs = [(e, manifest.get(e["key"])) for e in events]
    recs = [(e, r) for e, r in recs if r]
    ok = [(e, r) for e, r in recs if r["status"] == "ok"]
    print("\n" + "=" * 108)
    print("LIBRARY SUMMARY")
    print("=" * 108)
    tot_rows = sum(r["rows"] for _e, r in ok)
    tot_bytes = sum(r.get("bytes", 0) for _e, r in ok)
    print(f"  events in calendar        : {len(events)}")
    print(f"  windows written (ok)      : {len(ok)}")
    print(f"  windows empty (no ticks)  : {sum(1 for _e, r in recs if r['status'] == 'empty')}")
    print(f"  windows failed            : {sum(1 for _e, r in recs if r['status'] == 'fail')}")
    print(f"  total tick rows           : {tot_rows:,}")
    print(f"  total size on disk        : {tot_bytes / 1e6:.1f} MB (gzip)")
    print(f"  hourly files requested    : {sum(r['hours'] for _e, r in recs)}"
          f"   (404/empty hours: {sum(r['nodata'] for _e, r in recs)},"
          f" failed: {sum(r['failed'] for _e, r in recs)})")
    print(f"  HTTP 429 seen             : {GOV.n_429}"
          f"{'  [rate slowed to 0.60s]' if GOV.slowed else ''}")
    print(f"  HTTP 503 seen (retried)   : {GOV.n_503}   "
          f"[503 is routine for this endpoint, not a failure]")

    print(f"\n  tick density by year (median ticks per event window)")
    print(f"  {'year':<6}{'n':>5}{'median':>9}{'p25':>9}{'p75':>9}{'min':>8}{'max':>9}")
    print("  " + "-" * 60)
    for y in sorted({e["date"].year for e, _r in ok}):
        v = np.array([r["rows"] for e, r in ok if e["date"].year == y], dtype=float)
        print(f"  {y:<6}{len(v):>5}{np.median(v):>9.0f}{np.percentile(v,25):>9.0f}"
              f"{np.percentile(v,75):>9.0f}{v.min():>8.0f}{v.max():>9.0f}")

    print(f"\n  tick density by type (median ticks per event window)")
    print(f"  {'type':<6}{'n':>5}{'median':>9}{'window':>16}")
    print("  " + "-" * 40)
    for t in ("NFP", "CPI", "FOMC", "BOJ"):
        v = np.array([r["rows"] for e, r in ok if e["type"] == t], dtype=float)
        if not len(v):
            continue
        w = "02:00-05:00Z" if t == "BOJ" else "E-15m..E+45m"
        print(f"  {t:<6}{len(v):>5}{np.median(v):>9.0f}{w:>16}")

    empt = [(e, r) for e, r in recs if r["status"] != "ok"]
    if empt:
        print(f"\n  ANOMALIES ({len(empt)}) -- empty or failed windows, kept in the manifest:")
        for e, r in empt:
            print(f"    {e['key']:<16}{e['date'].strftime('%a')}  status={r['status']:<6}"
                  f"hours={r['hours']} nodata={r['nodata']} failed={r['failed']}")


# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--types", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    events = load_calendar(args.types)
    manifest = Manifest(MANIFEST)
    divisor = duka.price_divisor(PAIR)

    if args.validate_only:
        density_report(manifest, events)
        validate(events)
        return 0

    todo = []
    for e in events:
        rec = manifest.get(e["key"])
        if rec and rec["status"] == "empty":
            continue                                   # genuinely no ticks there
        if rec and rec["status"] == "ok" and (OUTDIR / f"{e['key']}.csv.gz").exists():
            continue                                   # already on disk
        todo.append(e)                                 # missing, failed, or lost file
    if args.limit:
        todo = todo[: args.limit]

    n_files = sum(len(hours_for(e["start"], e["end"])) for e in todo)
    print(f"pair={PAIR} divisor={divisor}  events={len(events)}  pending={len(todo)}  "
          f"hourly files to fetch~{n_files}  workers={args.workers}  "
          f"min interval={MIN_INTERVAL}s", flush=True)

    T0 = time.monotonic()
    done = 0
    counts = {"ok": 0, "empty": 0, "fail": 0}
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(build_event, e, divisor): e for e in todo}
        for fut in as_completed(futs):
            e = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:                              # noqa: BLE001
                rec = dict(status="fail", rows=0, hours=0, nodata=0, failed=1,
                           error=str(exc)[:200])
            manifest.mark(e["key"], rec)
            with lock:
                done += 1
                counts[rec["status"]] = counts.get(rec["status"], 0) + 1
                # tiny json -- checkpoint after EVERY event so an interrupted or
                # chunked run re-fetches nothing it already has
                manifest.save()
                if done % 10 == 0 or done == len(todo):
                    print(f"  progress {done}/{len(todo)}  ok={counts['ok']} "
                          f"empty={counts['empty']} fail={counts['fail']}  "
                          f"429s={GOV.n_429} 503s={GOV.n_503}  "
                          f"elapsed={time.monotonic()-T0:.0f}s", flush=True)
    manifest.save()
    print(f"done: ok={counts['ok']} empty={counts['empty']} fail={counts['fail']}", flush=True)

    density_report(manifest, events)
    validate(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
