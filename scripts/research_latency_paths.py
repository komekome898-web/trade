#!/usr/bin/env python3
"""Round 24 Step 2 -- WHERE THE DELAY IS: measured and estimated paths.

    DIAGNOSTIC ONLY.  Read-only, offline (this script touches no network;
    the live probe lives in scripts/measure_ws_latency.py).  It separates
    what is MEASURED from what is ESTIMATED and never mixes them in a
    table.

  (A) THIS VM, MEASURED, HISTORICAL
      data/ws/FX_BTC_JPY_*.jsonl.gz are raw WS recordings made FROM THIS
      VM (2026-08-20, via the agent proxy).  Every line carries "rts", the
      local receive time, next to the exchange's own stamp inside the
      message.  delay = rts - exchange stamp, per executions print and per
      ticker message.  This is a direct measurement; its only impurity is
      the host clock offset, which the live probe brackets separately.

  (B) THE HOME PC, ESTIMATED, INDIRECT
      data/tape/board_top5_*.csv.gz rows are stamped with the RECORDER's
      local second (floor of rts; each row is the LAST book state of that
      second), while data/tape/ticker_*.csv.gz rows carry the EXCHANGE
      stamp.  Cross-matching the (best_bid, best_ask) pair of a board row
      against the exchange-time interval during which that pair was
      prevailing brackets the recorder's receive delay:

          state received at local time u  <=>  exchange time u - L
          last state of local second s    <=>  u = s + 1 - eps, eps >= 0
          pair prevailed on exchange over [t_start, t_end)
          =>  L + eps  in  ( (s+1) - t_end , (s+1) - t_start ]

      So the bracket is on L + eps, i.e. the estimator is an UPPER BOUND
      on the true receive delay (eps = the gap between the last board
      message of the second and the end of the second).  Limits: 1 s
      flooring, board channel vs ticker channel are different feeds, and
      recurring quote pairs are disambiguated by nearest-in-time only.

  (C) VALIDATION OF (B) AGAINST GROUND TRUTH
      The same estimator is run on THIS VM's recordings, where the true
      delay is known from (A): the VM's ticker messages are floored to the
      local second, the last of each second is kept, and the estimator is
      applied to that surrogate "board" series.  The difference between
      the estimate and the measured truth is the estimator's bias, and it
      is reported before (B) is read.

Usage:  PYTHONPATH=src python scripts/research_latency_paths.py
"""
from __future__ import annotations

import gzip
import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WS_DIR = ROOT / "data" / "ws"
TAPE = ROOT / "data" / "tape"
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

MATCH_LO = -1.0        # plausible delay range for the cross-match, seconds
MATCH_HI = 6.0
MAX_RUN_S = 5.0        # a candidate quote run longer than this is a stale or
                       # gap-spanning run and carries no timing information


def line(c="-", n=104):
    print(c * n)


def header(t):
    print()
    line("=")
    print(t)
    line("=")


def sub(t):
    print()
    print("--- " + t + " " + "-" * max(0, 100 - len(t)))


def parse_iso(s: str) -> float:
    s = s.rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        frac = (frac + "000000")[:6]
        s = f"{head}.{frac}"
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def epoch_seconds(ts) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")


def dist(name, x, unit="s"):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        print(f"{name:<34}: (empty)")
        return
    print(f"{name:<34}: n={len(x):>8,}  p10={q(x,10):+7.3f} p50={q(x,50):+7.3f} "
          f"p90={q(x,90):+7.3f} p99={q(x,99):+7.3f} min={x.min():+7.3f} "
          f"max={x.max():+8.3f} mean={x.mean():+7.3f} [{unit}]")


# --------------------------------------------------------------------------
# (A) this VM, measured
# --------------------------------------------------------------------------
def vm_measured():
    files = sorted(WS_DIR.glob("FX_BTC_JPY_*.jsonl.gz"))
    if not files:
        print("no data/ws recordings on this host -- section A skipped")
        return None
    ex_delay, tk_delay = [], []
    tk_rows = []          # (rts, bid, ask) for the surrogate board series
    n_lines = 0
    for p in files:
        try:
            with gzip.open(p, "rt") as f:
                for ln in f:
                    n_lines += 1
                    try:
                        o = json.loads(ln)
                    except Exception:       # noqa: BLE001 (torn tail)
                        break
                    rts = o.get("rts")
                    m = o.get("m") or {}
                    params = m.get("params") or {}
                    ch = params.get("channel") or ""
                    msg = params.get("message")
                    if not isinstance(rts, (int, float)):
                        continue
                    if ch.startswith("lightning_executions_") and isinstance(msg, list):
                        for e in msg:
                            ed = e.get("exec_date")
                            if ed:
                                ex_delay.append(rts - parse_iso(ed))
                    elif ch.startswith("lightning_ticker_") and isinstance(msg, dict):
                        ts = msg.get("timestamp")
                        if ts:
                            tk_delay.append(rts - parse_iso(ts))
                            b, a = msg.get("best_bid"), msg.get("best_ask")
                            if b and a:
                                tk_rows.append((float(rts), float(b), float(a)))
        except (EOFError, OSError):
            continue
    print(f"files read                        : {len(files)} "
          f"({n_lines:,} recorded lines)")
    dist("VM executions receive delay", ex_delay)
    dist("VM ticker receive delay", tk_delay)
    return dict(ex=np.array(ex_delay), tk=np.array(tk_delay),
                tk_rows=np.array(tk_rows) if tk_rows else None)


# --------------------------------------------------------------------------
# quote runs and the cross-match estimator
# --------------------------------------------------------------------------
def build_runs(t: np.ndarray, bid: np.ndarray, ask: np.ndarray):
    """Merge consecutive ticker rows with an unchanged (bid, ask) pair."""
    chg = np.r_[True, (bid[1:] != bid[:-1]) | (ask[1:] != ask[:-1])]
    k = np.flatnonzero(chg)
    t_start = t[k]
    t_end = np.r_[t_start[1:], t[-1]]
    return t_start, t_end, bid[k], ask[k]


def cross_match(sec: np.ndarray, b_row: np.ndarray, a_row: np.ndarray,
                t_start, t_end, r_bid, r_ask):
    """Bracket (L + eps) for every local-second row that can be matched."""
    key = {}
    for i in range(len(t_start)):
        key.setdefault((r_bid[i], r_ask[i]), []).append(i)
    lo_l, hi_l, day_l = [], [], []
    matched = 0
    for s, b, a in zip(sec, b_row, a_row):
        cand = key.get((b, a))
        if not cand:
            continue
        target = s + 1.0
        best = None
        for i in cand:
            if t_end[i] - t_start[i] > MAX_RUN_S:
                continue                      # stale / gap-spanning run
            lo = target - t_end[i]
            hi = target - t_start[i]
            if hi < MATCH_LO or lo > MATCH_HI:
                continue
            mid = 0.5 * (lo + hi)
            if best is None or abs(mid) < abs(best[0]):
                best = (mid, lo, hi)
        if best is None:
            continue
        matched += 1
        lo_l.append(best[1])
        hi_l.append(best[2])
        day_l.append(int(s // 86400))
    return np.array(lo_l), np.array(hi_l), matched, np.array(day_l)


# --------------------------------------------------------------------------
def main() -> int:
    header("ROUND 24 STEP 2 -- LATENCY PATHS (A measured on this VM, "
           "B estimated for the PC)")

    header("A. THIS VM -- MEASURED (historical WS recordings, 2026-08-20)")
    vm = vm_measured()

    # ---- load the home-PC tape ---------------------------------------
    header("B/C. CROSS-MATCH ESTIMATOR")
    tk = pd.concat([pd.read_csv(p) for p in sorted(TAPE.glob("ticker_*.csv.gz"))],
                   ignore_index=True)
    t_tk = epoch_seconds(tk["ts"])
    o = np.argsort(t_tk, kind="stable")
    t_tk = t_tk[o]
    bid = tk["best_bid"].to_numpy(float)[o]
    ask = tk["best_ask"].to_numpy(float)[o]
    ok = np.isfinite(bid) & np.isfinite(ask) & (ask > bid) & (bid > 0)
    t_tk, bid, ask = t_tk[ok], bid[ok], ask[ok]
    t_start, t_end, r_bid, r_ask = build_runs(t_tk, bid, ask)
    print(f"exchange-stamped quote runs       : {len(t_start):,} "
          f"(from {len(t_tk):,} ticker rows); median run length "
          f"{np.median(t_end - t_start):.3f} s")

    # ---- (C) validation on this VM's own ticker stream ----------------
    sub("C. VALIDATION -- estimator vs ground truth on THIS VM's recordings")
    if vm is None or vm["tk_rows"] is None:
        print("no VM ticker rows -- validation skipped")
    else:
        rts = vm["tk_rows"][:, 0]
        vb = vm["tk_rows"][:, 1]
        va = vm["tk_rows"][:, 2]
        secs = np.floor(rts).astype(np.int64)
        # keep the LAST row of each local second (the board extractor's rule)
        last = np.r_[secs[1:] != secs[:-1], True]
        s_v, b_v, a_v = secs[last].astype(float), vb[last], va[last]
        lo, hi, matched, _d = cross_match(s_v, b_v, a_v, t_start, t_end,
                                          r_bid, r_ask)
        print(f"surrogate board rows              : {len(s_v):,}, "
              f"matched {matched:,} ({100*matched/max(1,len(s_v)):.1f}%)")
        dist("  estimator lower bound (L+eps)", lo)
        dist("  estimator upper bound (L+eps)", hi)
        dist("  estimator midpoint", 0.5 * (lo + hi))
        truth = vm["tk"]
        print(f"  ground truth (measured p50)      : {q(truth,50):+.3f} s "
              f"(p90 {q(truth,90):+.3f})")
        print(f"  BIAS of the midpoint estimator   : "
              f"{q(0.5*(lo+hi),50) - q(truth,50):+.3f} s at the median "
              f"(estimate - truth); the estimator brackets L+eps, so a "
              f"positive bias is expected")

    # ---- (B) the home PC ---------------------------------------------
    sub("B. HOME PC -- ESTIMATED from board_top5 (local second) vs ticker "
        "(exchange stamp)")
    bd_paths = sorted(TAPE.glob("board_top5_*.csv.gz"))
    if not bd_paths:
        print("no board_top5 files -- section B skipped")
    else:
        bd = pd.concat([pd.read_csv(p, usecols=["ts", "bid_px_1", "ask_px_1"])
                        for p in bd_paths], ignore_index=True)
        s_b = epoch_seconds(bd["ts"])
        bb = bd["bid_px_1"].to_numpy(float)
        ba = bd["ask_px_1"].to_numpy(float)
        okb = np.isfinite(bb) & np.isfinite(ba) & (ba > bb)
        s_b, bb, ba = s_b[okb], bb[okb], ba[okb]
        print(f"board rows (1 Hz, local second)   : {len(s_b):,} "
              f"({bd_paths[0].name} .. {bd_paths[-1].name})")
        lo, hi, matched, day = cross_match(s_b, bb, ba, t_start, t_end,
                                           r_bid, r_ask)
        print(f"matched to a ticker quote run     : {matched:,} "
              f"({100*matched/max(1,len(s_b)):.1f}%)")
        dist("  estimator lower bound (L+eps)", lo)
        dist("  estimator upper bound (L+eps)", hi)
        mid = 0.5 * (lo + hi)
        dist("  estimator midpoint", mid)
        print()
        print("  per-UTC-day median of the midpoint (a DRIFTING value is a "
              "clock, not a network):")
        for d in np.unique(day):
            m = day == d
            print(f"    {pd.Timestamp(d*86400, unit='s', tz='UTC').date()} : "
                  f"n={int(m.sum()):>7,}  median {np.median(mid[m]):+7.3f} s  "
                  f"p10 {q(mid[m],10):+7.3f}  p90 {q(mid[m],90):+7.3f}")
        print()
        print("  READ THIS AS: measured bracket = (true receive delay L) + "
              "(intra-second sampling lag eps >= 0) + (recorder clock offset) "
              "+ (any board-channel vs ticker-channel stamping offset).")
        print("  A NEGATIVE median is physically impossible for L + eps alone; "
              "section D separates the last two terms.")

    # ---- (D) channel control: THIS VM's own board rows -----------------
    sub("D. CHANNEL CONTROL -- the same estimator on THIS VM's BOARD rows "
        "(clock known good)")
    vmb = os.environ.get("LATENCY_VM_BOARD_DIR", "")
    paths = sorted(Path(vmb).glob("board_top5_*.csv.gz")) if vmb else []
    if not paths:
        print("set LATENCY_VM_BOARD_DIR to a directory holding board_top5_*.csv.gz "
              "extracted from THIS VM's data/ws -- section D skipped")
    else:
        bd = pd.concat([pd.read_csv(p, usecols=["ts", "bid_px_1", "ask_px_1"])
                        for p in paths], ignore_index=True)
        s_b = epoch_seconds(bd["ts"])
        bb = bd["bid_px_1"].to_numpy(float)
        ba = bd["ask_px_1"].to_numpy(float)
        okb = np.isfinite(bb) & np.isfinite(ba) & (ba > bb)
        s_b, bb, ba = s_b[okb], bb[okb], ba[okb]
        lo, hi, matched, _d = cross_match(s_b, bb, ba, t_start, t_end,
                                          r_bid, r_ask)
        print(f"VM board rows (1 Hz, local second): {len(s_b):,}, matched "
              f"{matched:,} ({100*matched/max(1,len(s_b)):.1f}%)")
        dist("  estimator midpoint (VM board)", 0.5 * (lo + hi))
        print("  The VM's clock is known good (section C: ticker estimate +0.057 "
              "vs measured truth +0.042).  Whatever this row shows beyond that "
              "is the BOARD-vs-TICKER channel offset, and it must be subtracted "
              "from section B before B is read as a clock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
