#!/usr/bin/env python3
"""
Build a general BURST-event replay library for scalper backtesting.

This extends the storm library (data/storm_events/, built by
build_storm_library.py) with ordinary single-minute "burst" moves -- the
smaller, more frequent moves that are still large enough to plausibly contain
the scalper's 5s >= 10bps signals, but that don't qualify as a full storm
(|30m log-ret| >= 0.8%, >= 2h dedup).

Burst definition (pre-registered, not tuned):

    burst minute : |1m log-return| >= 0.15%   (on Binance BTCUSDT close)
    burst event  : detections within 30 minutes of each other are merged into
                   one event, anchored at the *first* minute of the cluster
                   (chained: a new detection extends the cluster if it is
                   within 30min of the *previous* detection in the cluster).

Events are detected on the full Binance BTCUSDT 1m history
(data/binance_BTCUSDT_1m_full.csv, so returns are computed on a continuous,
gap-ffilled series) and then restricted to the span where bitFlyer tick data
exists (data/executions_FX_BTC_JPY.csv, ~2026-07-21 08:17 .. 2026-08-20 08:22
UTC).

Any burst event whose window [anchor-10min, anchor+30min] overlaps an
existing storm-event window (data/storm_events/event_*.csv, read from each
file's first/last timestamp) is dropped -- that period is already covered by
the storm library.

If more than MAX_EVENTS (120) events survive, only the 120 with the largest
|1m return| are kept; the rest are logged as dropped (capacity).

Surviving events' windows ([-10min, +30min] around the anchor) are merged
when overlapping, then each merged window is fetched and written exactly like
build_storm_library.py:
  - data/burst_events/event_<YYYYmmdd_HHMM>.csv named after the earliest
    anchor in the merged window.
  - Same schema: ts, bn_price, bf_price, bf_buy, bf_sell.
  - Binance BTCUSDT aggTrades fetched via scripts/fetch_aggtrades.py's
    fetch_window() and resampled to 1s, last price -> bn_price (gaps = NaN,
    not filled).
  - bitFlyer trades sliced from executions_FX_BTC_JPY.csv, resampled to 1s:
    last price -> bf_price (ffilled *within the window only*), summed
    taker-side volume -> bf_buy / bf_sell.
  - A window is skipped (no CSV written) only if EITHER side has zero trades
    in the window.

Idempotent: a window whose output CSV already exists is skipped with no
network calls at all -- a killed run resumes cleanly.

Binance etiquette: fetch_window() already sleeps between paginated/hourly
requests; every request here is counted and any 429 response triggers a 10s
back-off and retry (not a failure).

Usage: PYTHONPATH=src python scripts/build_burst_library.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fetch_aggtrades as FA         # noqa: E402  -- reuse aggTrades fetch + 1s resample

ROOT = HERE.parent
DATA = ROOT / "data"
STORM_DIR = DATA / "storm_events"
OUT_DIR = DATA / "burst_events"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTCUSDT"
BURST_THRESHOLD = 0.0015       # 0.15% absolute 1m log return
CLUSTER_GAP_MIN = 30           # merge detections within 30min of each other
PRE_MIN = 10
POST_MIN = 30
MAX_EVENTS = 120
TRADES_PER_REQUEST = 1000      # aggTrades page size

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
# 1. burst events
# --------------------------------------------------------------------------- #
def load_binance_full() -> pd.DataFrame:
    p = DATA / "binance_BTCUSDT_1m_full.csv"
    df = pd.read_csv(p, parse_dates=["open_time"]).set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index[0], df.index[-1], freq="1min", tz="UTC")
    df = df.reindex(full)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()
    df["n_trades"] = df["n_trades"].fillna(0.0)
    df.index.name = "ts"
    return df


def bitflyer_span() -> tuple[pd.Timestamp, pd.Timestamp]:
    df = pd.read_csv(DATA / "executions_FX_BTC_JPY.csv", usecols=["exec_date"])
    d = pd.to_datetime(df["exec_date"], format="mixed", utc=True)
    return d.min(), d.max()


def detect_burst_events(b: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Returns a DataFrame indexed by cluster anchor ts with columns
    ret (signed 1m log-return of the *triggering* minute, i.e. max |ret| in
    the cluster) and n_members (# burst minutes merged into the cluster)."""
    logret = np.log(b["close"]).diff()
    burst_min = logret[logret.abs() >= BURST_THRESHOLD]

    bf_lo, bf_hi = bitflyer_span()
    burst_min = burst_min[(burst_min.index >= bf_lo) & (burst_min.index <= bf_hi)]

    clusters: list[dict] = []
    gap = pd.Timedelta(minutes=CLUSTER_GAP_MIN)
    for ts, r in burst_min.items():
        if clusters and (ts - clusters[-1]["last"]) <= gap:
            c = clusters[-1]
            c["last"] = ts
            c["members"].append(ts)
            if abs(r) > abs(c["ret"]):
                c["ret"] = r
        else:
            clusters.append({"anchor": ts, "last": ts, "members": [ts], "ret": r})

    rows = [{"anchor": c["anchor"], "ret": c["ret"], "n_members": len(c["members"])}
             for c in clusters]
    out = pd.DataFrame(rows).set_index("anchor").sort_index()
    return out, bf_lo, bf_hi


# --------------------------------------------------------------------------- #
# 2. exclude storm-covered windows, cap, merge
# --------------------------------------------------------------------------- #
def storm_windows() -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    wins = []
    for p in sorted(STORM_DIR.glob("event_*.csv")):
        df = pd.read_csv(p, usecols=["ts"])
        t = pd.to_datetime(df["ts"], utc=True)
        wins.append((t.iloc[0], t.iloc[-1]))
    return wins


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start <= b_end and a_end >= b_start


def exclude_storm_covered(events: pd.DataFrame, s_windows) -> tuple[pd.DataFrame, int]:
    keep_idx = []
    skipped = 0
    for anchor in events.index:
        w_start = anchor - pd.Timedelta(minutes=PRE_MIN)
        w_end = anchor + pd.Timedelta(minutes=POST_MIN)
        if any(overlaps(w_start, w_end, s0, s1) for s0, s1 in s_windows):
            skipped += 1
        else:
            keep_idx.append(anchor)
    return events.loc[keep_idx], skipped


def cap_events(events: pd.DataFrame, max_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(events) <= max_n:
        return events, events.iloc[0:0]
    ranked = events.reindex(events["ret"].abs().sort_values(ascending=False).index)
    keep = ranked.iloc[:max_n].sort_index()
    dropped = ranked.iloc[max_n:].sort_index()
    return keep, dropped


def build_merged_windows(events: pd.DataFrame) -> list[dict]:
    items = sorted(events.index)
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
# 3. per-window build (identical machinery to build_storm_library.py)
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
    print("1. BURST EVENT DETECTION")
    line("=")
    b = load_binance_full()
    events, bf_lo, bf_hi = detect_burst_events(b)
    print(f"burst rule    : |1m log-ret| >= {BURST_THRESHOLD*100:.2f}%, "
          f"cluster gap <= {CLUSTER_GAP_MIN}min")
    print(f"bitFlyer span : {bf_lo} .. {bf_hi}")
    print(f"burst clusters in span (pre-exclusion) : {len(events)}")

    line("-")
    print("1b. EXCLUDE STORM-COVERED EVENTS")
    line("-")
    s_windows = storm_windows()
    print(f"existing storm windows: {len(s_windows)}")
    events, n_storm_skip = exclude_storm_covered(events, s_windows)
    print(f"burst clusters after storm exclusion    : {len(events)}  "
          f"(skipped as storm-covered: {n_storm_skip})")

    line("-")
    print("1c. CAP TO MAX_EVENTS")
    line("-")
    events_kept, events_dropped = cap_events(events, MAX_EVENTS)
    if len(events_dropped):
        print(f"survivors ({len(events)}) > cap ({MAX_EVENTS}) -- "
              f"keeping the {MAX_EVENTS} largest |1m return|, "
              f"dropping {len(events_dropped)}:")
        for ts, row in events_dropped.iterrows():
            print(f"    DROPPED (capacity)  {ts}  ret={row['ret']*100:+.3f}%  "
                  f"members={int(row['n_members'])}")
    else:
        print(f"survivors ({len(events)}) <= cap ({MAX_EVENTS}) -- no capacity drop")
    events = events_kept
    print(f"final burst events : {len(events)}")
    for i, (ts, row) in enumerate(events.iterrows(), 1):
        print(f"  {i:>3}. {ts}  ret={row['ret']*100:+.3f}%  members={int(row['n_members'])}")

    line("=")
    print(f"2. WINDOW MERGE  ([-{PRE_MIN}min, +{POST_MIN}min] around each anchor)")
    line("=")
    windows = build_merged_windows(events)
    print(f"merged windows: {len(windows)} (from {len(events)} events)")
    for i, w in enumerate(windows, 1):
        print(f"  {i:>3}. {w['start']} .. {w['end']}  "
              f"({len(w['events'])} event(s): "
              f"{', '.join(e.strftime('%Y-%m-%d %H:%M') for e in w['events'])})")

    line("-")
    print("2b. REQUEST VOLUME ESTIMATE (before fetching)")
    line("-")
    est_requests = 0
    for w in windows:
        n_trades = b.loc[w["start"]:w["end"], "n_trades"].sum()
        est_requests += max(1, int(np.ceil(n_trades / TRADES_PER_REQUEST)))
    print(f"estimated Binance trade count in windows : "
          f"{sum(b.loc[w['start']:w['end'], 'n_trades'].sum() for w in windows):,.0f} "
          f"(from binance 1m n_trades, proxy for aggTrades count)")
    print(f"estimated requests (@ {TRADES_PER_REQUEST}/req, "
          f"+1 hourly-page request per window-hour not counted here) : ~{est_requests}")

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
    print(f"burst events (final, in span, post-exclusion/cap) : {len(events)}")
    print(f"  skipped as storm-covered                         : {n_storm_skip}")
    print(f"  dropped for capacity (> {MAX_EVENTS})                       : {len(events_dropped)}")
    print(f"merged windows                     : {len(windows)}")
    print(f"windows written this run           : {len(written)}")
    print(f"windows already built (skipped)    : {len(exists)}")
    print(f"windows skipped -- no data          : {len(skipped)}")
    for r in skipped:
        print(f"    {r['label']}: missing on {', '.join(r['missing'])}")
    print(f"total 1s rows in library (all files): {total_rows}")
    print(f"total Binance requests (this run)  : {REQUEST_COUNT}")
    print(f"data/burst_events/ : {len(all_csvs)} files, {total_bytes/1e6:.2f} MB")

    if len(events):
        rets = events["ret"].abs() * 100
        in_pm = events.index[(events.index.time >= pd.Timestamp("12:30").time()) &
                              (events.index.time <= pd.Timestamp("15:00").time())]
        print(f"per-event |1m return| distribution (%) : "
              f"min={rets.min():.3f}  median={rets.median():.3f}  max={rets.max():.3f}")
        print(f"events with anchor inside 12:30-15:00 UTC : {len(in_pm)} / {len(events)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
