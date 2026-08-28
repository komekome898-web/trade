#!/usr/bin/env python3
"""
Build the 2005-2014 FX EVENT-TICK LIBRARY: Dukascopy USD/JPY ticks in a tight
window around every primary-source macro event of the S4 judgment set.

    input   backtest_data/fx_event_ticks_2005_2014/calendar.csv
            (scripts/fetch_fx_calendar_2005_2014.py -- 100% primary source)
    output  backtest_data/fx_event_ticks_2005_2014/{TYPE}_{YYYYMMDD}.csv.gz
            columns: ts_utc,bid,ask,bidvol,askvol   (ts_utc = epoch ms, UTC)
            -- byte-for-byte the same schema as fx_event_ticks_2015_2026/
    state   backtest_data/fx_event_ticks_2005_2014/manifest.json (idempotent resume)

WINDOW (fixed by docs/PREREG_fx_s4_judgment.md sec.2, not tunable)
------------------------------------------------------------------
    [E - 10 min, E + 10 min] for every event.  E = calendar.csv time_utc.
    That is narrower than the 2015-2026 library's [E-15min, E+45min] because the
    judgment only needs E-300s (the pre-event spread baseline) through E+300s
    (the exit).  The narrower window is what makes 320 events affordable inside
    Dukascopy's 0.25 s/request politeness floor.

DUKASCOPY TICK FORMAT (docs/KNOWLEDGE_FX.md sec.5)
--------------------------------------------------
    {BASE}/{PAIR}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5   MONTH IS ZERO-INDEXED.
    LZMA raw stream; 20-byte big-endian ">IIIff" = (ms offset in hour, ask, bid,
    ask_vol, bid_vol); JPY divisor 1000.
The decode, the URL builder and the RateLimiter are IMPORTED from
scripts/fetch_dukascopy.py, and the fetch/politeness governor is IMPORTED from
scripts/build_fx_event_library.py, so this library cannot drift in format from
the 2015-2026 one it will be compared against.

Missing hours (404 / empty) are recorded in the manifest and reported, never
retried into the ground.  Nothing outside backtest_data/fx_event_ticks_2005_2014/
is written.

Usage
    python scripts/build_fx_event_library_2005_2014.py [--workers 4] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_dukascopy as duka                                       # noqa: E402
import build_fx_event_library as lib                                 # noqa: E402

OUTDIR = ROOT / "backtest_data" / "fx_event_ticks_2005_2014"
CAL = OUTDIR / "calendar.csv"
MANIFEST = OUTDIR / "manifest.json"

PAIR = "USDJPY"
PRE_MIN = POST_MIN = 10
UTC = dt.timezone.utc


def load_calendar() -> list[dict]:
    ev = []
    with CAL.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = dt.datetime.strptime(row["time_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            d = dt.date.fromisoformat(row["date"])
            ev.append(dict(key=f"{row['type']}_{d:%Y%m%d}", type=row["type"], date=d, ts=ts,
                           start=ts - dt.timedelta(minutes=PRE_MIN),
                           end=ts + dt.timedelta(minutes=POST_MIN)))
    return ev


def build_event(ev: dict, divisor: float) -> dict:
    frames, n_hours, n_nodata, n_fail = [], 0, 0, 0
    for day, hour in lib.hours_for(ev["start"], ev["end"]):
        status, raw = lib.fetch_hour(day, hour)
        n_hours += 1
        if status == "fail":
            n_fail += 1
            continue
        if status == "nodata" or not raw:
            n_nodata += 1
            continue
        frames.append(duka.decode_ticks(raw, day, hour, divisor))
    if not frames:
        return dict(status="fail" if n_fail else "empty", rows=0, hours=n_hours,
                    nodata=n_nodata, failed=n_fail)

    df = pd.concat(frames, ignore_index=True)
    df = df[(df["timestamp"] >= ev["start"]) & (df["timestamp"] <= ev["end"])]
    df = df.sort_values("timestamp")
    if df.empty:
        return dict(status="empty", rows=0, hours=n_hours, nodata=n_nodata, failed=n_fail)

    # epoch MILLISECONDS, via datetime64[ms] explicitly (research-protocol sec.6:
    # a raw .astype("int64") is pandas-version dependent and silently drops the
    # sub-second part, which is the entire point of a tick library).
    ms = (df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
          .to_numpy().astype("datetime64[ms]").astype("int64"))
    out = pd.DataFrame({"ts_utc": ms, "bid": df["bid"].to_numpy(), "ask": df["ask"].to_numpy(),
                        "bidvol": df["bid_vol"].to_numpy(), "askvol": df["ask_vol"].to_numpy()})
    path = OUTDIR / f"{ev['key']}.csv.gz"
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="", compresslevel=9) as f:
        out.to_csv(f, index=False, float_format="%.6g")
    tmp.replace(path)
    return dict(status="ok", rows=len(out), hours=n_hours, nodata=n_nodata, failed=n_fail,
                bytes=path.stat().st_size, first_ms=int(out.ts_utc.iloc[0]),
                last_ms=int(out.ts_utc.iloc[-1]))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    events = load_calendar()
    manifest = lib.Manifest(MANIFEST)
    divisor = duka.price_divisor(PAIR)

    todo = []
    for e in events:
        rec = manifest.get(e["key"])
        if rec and rec["status"] == "empty":
            continue
        if rec and rec["status"] == "ok" and (OUTDIR / f"{e['key']}.csv.gz").exists():
            continue
        todo.append(e)
    if args.limit:
        todo = todo[: args.limit]

    n_files = sum(len(lib.hours_for(e["start"], e["end"])) for e in todo)
    print(f"pair={PAIR} divisor={divisor} events={len(events)} pending={len(todo)} "
          f"hourly files~{n_files} workers={args.workers} window=E+/-{PRE_MIN}min", flush=True)

    t0, done = time.monotonic(), 0
    counts = {"ok": 0, "empty": 0, "fail": 0}
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(build_event, e, divisor): e for e in todo}
        for fut in as_completed(futs):
            e = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:                                  # noqa: BLE001
                rec = dict(status="fail", rows=0, hours=0, nodata=0, failed=1, error=str(exc)[:200])
            manifest.mark(e["key"], rec)
            with lock:
                done += 1
                counts[rec["status"]] = counts.get(rec["status"], 0) + 1
                manifest.save()
                if done % 20 == 0 or done == len(todo):
                    print(f"  progress {done}/{len(todo)} ok={counts['ok']} "
                          f"empty={counts['empty']} fail={counts['fail']} "
                          f"429s={lib.GOV.n_429} 503s={lib.GOV.n_503} "
                          f"elapsed={time.monotonic()-t0:.0f}s", flush=True)
    manifest.save()

    recs = [(e, manifest.get(e["key"])) for e in events]
    recs = [(e, r) for e, r in recs if r]
    ok = [(e, r) for e, r in recs if r["status"] == "ok"]
    print("\n" + "=" * 100)
    print("LIBRARY SUMMARY -- backtest_data/fx_event_ticks_2005_2014/")
    print("=" * 100)
    print(f"  calendar events            : {len(events)}")
    print(f"  windows written (ok)       : {len(ok)}")
    print(f"  windows empty (no ticks)   : {sum(1 for _e, r in recs if r['status']=='empty')}")
    print(f"  windows failed             : {sum(1 for _e, r in recs if r['status']=='fail')}")
    print(f"  total tick rows            : {sum(r['rows'] for _e, r in ok):,}")
    print(f"  total size on disk         : {sum(r.get('bytes',0) for _e,r in ok)/1e6:.1f} MB gz")
    print(f"  hourly files requested     : {sum(r['hours'] for _e, r in recs)} "
          f"(404/empty {sum(r['nodata'] for _e,r in recs)}, failed {sum(r['failed'] for _e,r in recs)})")
    print(f"  HTTP 429 / 503             : {lib.GOV.n_429} / {lib.GOV.n_503}")
    print(f"\n  tick density by year (ticks per E+/-10min window)")
    print(f"  {'year':<6}{'n':>5}{'median':>9}{'p25':>9}{'p75':>9}{'min':>8}{'max':>9}")
    for y in sorted({e["date"].year for e, _r in ok}):
        v = np.array([r["rows"] for e, r in ok if e["date"].year == y], float)
        print(f"  {y:<6}{len(v):>5}{np.median(v):>9.0f}{np.percentile(v,25):>9.0f}"
              f"{np.percentile(v,75):>9.0f}{v.min():>8.0f}{v.max():>9.0f}")
    bad = [(e, r) for e, r in recs if r["status"] != "ok"]
    if bad:
        print(f"\n  MISSING/EXCLUDED WINDOWS ({len(bad)}):")
        for e, r in bad:
            print(f"    {e['key']:<16}{e['date'].strftime('%a')} {e['ts']:%H:%M}Z "
                  f"status={r['status']:<6} hours={r['hours']} nodata={r['nodata']} "
                  f"failed={r['failed']}")
    with (OUTDIR / "MISSING.txt").open("w", encoding="utf-8") as f:
        for e, r in bad:
            f.write(f"{e['key']}\t{r['status']}\thours={r['hours']}\tnodata={r['nodata']}\t"
                    f"failed={r['failed']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
