#!/usr/bin/env python3
"""
Build a storm-event replay library for scalper backtesting.

Storm definition is reused verbatim from scripts/research_storm.py
(`build_storms`, imported as RS below):

    storm minute : |rolling 30m log-return| >= 0.8%
    storm event  : first storm minute after >= 2h with no storm minute

Events are detected on the full Binance BTCUSDT 1m history
(data/binance_BTCUSDT_1m_full.csv, so the rolling/dedup windows are warmed up
correctly) and then restricted to the span where bitFlyer tick data exists
(data/executions_FX_BTC_JPY.csv, 2026-07-21 .. 2026-08-20 -- the last ~30 days).

For each surviving event a window [onset-30min, onset+90min] is built.
Overlapping windows are merged; each merged window is written once, named
after the *earliest* event onset it contains: data/storm_events/event_<YYYYmmdd_HHMM>.csv

For each merged window:
  - Binance BTCUSDT aggTrades are fetched via scripts/fetch_aggtrades.py's
    fetch_window() and resampled to a 1s grid, last price only -> bn_price
    (seconds with no trade are left as NaN gaps -- not filled).
  - bitFlyer trades are sliced from executions_FX_BTC_JPY.csv for the same
    window and resampled to 1s: last price -> bf_price, and per-second summed
    taker-side volume -> bf_buy / bf_sell.
  - Both are placed on the same 1s grid (equivalent to an outer join over the
    window's second range); bf_price is then forward-filled *within the
    window only*; bn_price gaps are left as-is.
  - A window is skipped (no CSV written) only if EITHER side has zero trades
    in the window; the report says which side was empty.

Idempotent: a window whose output CSV already exists is skipped with no
network calls at all.

Binance etiquette: fetch_window() already sleeps between paginated/hourly
requests; on top of that every request here is counted and any 429 response
triggers a 10s back-off and retry (not a failure).

Usage: PYTHONPATH=src python scripts/build_storm_library.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import research_storm as RS          # noqa: E402  -- reuse storm/event machinery
import fetch_aggtrades as FA         # noqa: E402  -- reuse aggTrades fetch + 1s resample

ROOT = HERE.parent
DATA = ROOT / "data"
OUT_DIR = DATA / "storm_events"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTCUSDT"
PRE_MIN = 30
POST_MIN = 90

REQUEST_COUNT = 0


def line(c: str = "-", n: int = 88) -> None:
    print(c * n)


# --------------------------------------------------------------------------- #
# rate-limit-aware request counting wrapped around fetch_aggtrades' session
# --------------------------------------------------------------------------- #
def _install_counted_get() -> None:
    orig_get = FA.session.get

    def counted_get(*args, **kwargs):
        global REQUEST_COUNT
        while True:
            REQUEST_COUNT += 1
            resp = orig_get(*args, **kwargs)
            if resp.status_code == 429:
                print("    ! 429 from Binance -- backing off 10s and retrying")
                time.sleep(10)
                continue
            return resp

    FA.session.get = counted_get


# --------------------------------------------------------------------------- #
# 1. storm events (reuses research_storm.build_storms)
# --------------------------------------------------------------------------- #
def load_binance_full() -> pd.DataFrame:
    p = DATA / "binance_BTCUSDT_1m_full.csv"
    df = pd.read_csv(p, parse_dates=["open_time"]).set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    df = df.reindex(full)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df.index.name = "ts"
    return df


def bitflyer_span() -> tuple[pd.Timestamp, pd.Timestamp]:
    df = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv", usecols=["exec_date"])
    d = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    return d.min(), d.max()


def detect_storm_events() -> tuple[pd.DatetimeIndex, pd.Timestamp, pd.Timestamp]:
    b = load_binance_full()
    # build_storms is run on the FULL history so the 30m return / 2h dedup
    # windows are correctly warmed up; we only *restrict* the resulting
    # events to the bitFlyer-covered span afterwards.
    _storm_min, events_all = RS.build_storms(b["close"])
    bf_lo, bf_hi = bitflyer_span()
    events = events_all[(events_all >= bf_lo) & (events_all <= bf_hi)]
    return events, bf_lo, bf_hi


# --------------------------------------------------------------------------- #
# 2. merge windows
# --------------------------------------------------------------------------- #
def build_merged_windows(events: pd.DatetimeIndex) -> list[dict]:
    items = sorted(events)
    windows: list[dict] = []
    for e in items:
        s = e - pd.Timedelta(minutes=PRE_MIN)
        en = e + pd.Timedelta(minutes=POST_MIN)
        if windows and s <= windows[-1]["end"]:
            windows[-1]["end"] = max(windows[-1]["end"], en)
            windows[-1]["events"].append(e)
        else:
            windows.append({"start": s, "end": en, "events": [e]})
    return windows


# --------------------------------------------------------------------------- #
# 3. per-window build
# --------------------------------------------------------------------------- #
def load_bitflyer_trades() -> pd.DataFrame:
    df = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv",
                      usecols=["exec_date", "price", "size", "side"])
    df["ts"] = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    df = df.set_index("ts").sort_index()
    return df[["price", "size", "side"]]


def process_window(win: dict, idx_num: int, total: int, bf_all: pd.DataFrame) -> dict:
    start, end, events_in = win["start"], win["end"], win["events"]
    label = events_in[0].strftime("%Y%m%d_%H%M")
    out_path = OUT_DIR / f"event_{label}.csv"

    if out_path.exists():
        n_rows = sum(1 for _ in open(out_path)) - 1
        print(f"[{idx_num}/{total}] {label}  SKIP (exists, {n_rows} rows)   "
              f"{start} .. {end}  ({len(events_in)} event(s))")
        return {"status": "exists", "label": label, "rows": n_rows}

    print(f"[{idx_num}/{total}] {label}  fetching  {start} .. {end}  "
          f"({len(events_in)} event(s) merged)")

    idx1s = pd.date_range(start, end, freq="1s")

    bn_raw = FA.fetch_window(SYMBOL, start, end + pd.Timedelta(seconds=1))
    time.sleep(0.1)

    bf_slice = bf_all.loc[start:end]

    missing = []
    if bn_raw.empty:
        missing.append("binance")
    if bf_slice.empty:
        missing.append("bitflyer")
    if missing:
        print(f"    SKIPPED -- no data on: {', '.join(missing)}")
        return {"status": "skipped_nodata", "label": label, "missing": missing}

    bn_price = bn_raw.set_index("ts")["price"].resample("1s").last().reindex(idx1s)

    bf_price = bf_slice["price"].resample("1s").last().reindex(idx1s).ffill()
    buy = bf_slice.loc[bf_slice["side"] == "BUY", "size"]
    sell = bf_slice.loc[bf_slice["side"] == "SELL", "size"]
    bf_buy = buy.resample("1s").sum().reindex(idx1s).fillna(0.0)
    bf_sell = sell.resample("1s").sum().reindex(idx1s).fillna(0.0)

    out = pd.DataFrame({
        "bn_price": bn_price,
        "bf_price": bf_price,
        "bf_buy": bf_buy,
        "bf_sell": bf_sell,
    })
    out.index.name = "ts"
    out.to_csv(out_path)
    print(f"    wrote {len(out)} rows -> {out_path.relative_to(ROOT)}   "
          f"(bn trades={len(bn_raw)}, bf trades={len(bf_slice)})")
    return {"status": "written", "label": label, "rows": len(out)}


# --------------------------------------------------------------------------- #
def main() -> int:
    _install_counted_get()

    line("=")
    print("1. STORM EVENT DETECTION  (reusing research_storm.build_storms)")
    line("=")
    events, bf_lo, bf_hi = detect_storm_events()
    print(f"storm rule    : |{RS.STORM_WINDOW_MIN}m log-ret| >= {RS.STORM_THRESHOLD*100:.1f}%, "
          f"dedup >= {RS.STORM_DEDUP_MIN//60}h")
    print(f"bitFlyer span : {bf_lo} .. {bf_hi}")
    print(f"storm events in span : {len(events)}")
    for i, e in enumerate(events, 1):
        print(f"  {i:>3}. {e}")

    line("=")
    print("2. WINDOW MERGE  ([-30min, +90min] around each onset)")
    line("=")
    windows = build_merged_windows(events)
    print(f"merged windows: {len(windows)} (from {len(events)} events)")
    for i, w in enumerate(windows, 1):
        print(f"  {i:>3}. {w['start']} .. {w['end']}  "
              f"({len(w['events'])} event(s): "
              f"{', '.join(e.strftime('%Y-%m-%d %H:%M') for e in w['events'])})")

    line("=")
    print("3. FETCH + BUILD PER WINDOW")
    line("=")
    bf_all = load_bitflyer_trades()
    results = [process_window(w, i, len(windows), bf_all) for i, w in enumerate(windows, 1)]

    written = [r for r in results if r["status"] == "written"]
    exists = [r for r in results if r["status"] == "exists"]
    skipped = [r for r in results if r["status"] == "skipped_nodata"]

    # -------- directory summary over the WHOLE library (post-run state) -----
    all_csvs = sorted(OUT_DIR.glob("event_*.csv"))
    total_bytes = sum(p.stat().st_size for p in all_csvs)
    total_rows = 0
    for p in all_csvs:
        with open(p) as fh:
            total_rows += sum(1 for _ in fh) - 1

    line("=")
    print("4. FINAL REPORT")
    line("=")
    print(f"storm events (bitFlyer span)      : {len(events)}")
    print(f"merged windows                     : {len(windows)}")
    print(f"windows written this run           : {len(written)}")
    print(f"windows already built (skipped)    : {len(exists)}")
    print(f"windows skipped -- no data          : {len(skipped)}")
    for r in skipped:
        print(f"    {r['label']}: missing on {', '.join(r['missing'])}")
    print(f"total 1s rows in library (all files): {total_rows}")
    print(f"total Binance requests (this run)  : {REQUEST_COUNT}")
    print(f"data/storm_events/ : {len(all_csvs)} files, {total_bytes/1e6:.2f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
