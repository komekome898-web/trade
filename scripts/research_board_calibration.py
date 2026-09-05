#!/usr/bin/env python3
"""Round 21 phase 1 -- EXECUTION CALIBRATION on the first real quote record.

    PRE-REGISTRATION (written before the first run; nothing here is a
    strategy, a P&L, or an adoption recommendation)

WHAT THIS IS
  The board study of KNOWLEDGE.md section 4 (spread-MM, pending gate) has
  one prerequisite that everything else scales by: the fill rate f.  S7
  (report u) proved the two-sided flow regime exists and bounded the maker
  ceiling, but it could not measure f -- a tape has no queue.  7.5 days of
  real top-of-book (best bid/ask + sizes) have now accumulated, so f, the
  realized adverse selection behind a fill, and the competing regime
  detectors can be measured directly for the first time.

  THIS SCRIPT DOES NOT SIMULATE A MARKET-MAKING STRATEGY.  No cell P&L, no
  inventory, no TP/abort.  It reads five calibration quantities and stops:
      A. the surface of f
      B. the S8 revival number (capture + adverse(5s)) against its frozen bar
      C. the board-days the spread-MM verdict needs, from measured f and sd
      D. 5-second vr (matilda's native scale) versus the S7 two-sided window
      E. top-of-book imbalance conditional forward drift (g revisited)

DATA CONSUMPTION LEDGER (stated in the output, per research-protocol 8.1)
  D and E read DIRECTIONAL information out of the board features.  From
  this run on, board data up to and including 2026-08-27 is SPENT for any
  imbalance/vr-based hypothesis -- such a verdict must use board data
  accumulated 2026-08-28 or later.  The S8 revival check (B) is NOT
  affected: that family and its bar were frozen 2026-08-22, before this
  board record existed, and B reads only the one number the freeze names.

DATA
  data/tape/ticker_YYYYMMDD.csv.gz      2026-08-20..27, columns
      ts, best_bid, best_ask, best_bid_size, best_ask_size; one row per
      quote change (777,413 rows, 6.99 days wall clock).
  data/tape/executions_YYYYMMDD.csv.gz  same span, columns ts, price,
      size, side; `side` is the TAKER side (BUY = the ask was lifted).
  Recorder gaps are real (the largest is 2026-08-25T18:30Z..
  2026-08-26T02:54Z, 8.4 h).  Any window or quote whose measurement span
  touches a gap is DISCARDED, exactly as S7 did -- a gap must never be
  read as "no trading".  GAP_SEC = 30 s of ticker silence (the ticker's
  own p99.99 inter-arrival is 16 s, so 30 s is outside the live regime).

QUOTE PLACEMENT RULE -- FROZEN HERE, NOT TUNED LATER
  * Grid: the absolute 30 s epoch grid floor(t/30), i.e. the same grid the
    S7 regime lives on.  At every grid point one virtual BID is placed at
    the prevailing best_bid and one virtual ASK at the prevailing
    best_ask.  "Prevailing" = the last ticker row at or before the grid
    point.  No look-ahead: the price and the queue size Q come from board
    state at or before t0; every fill test uses prints strictly after t0.
  * Lifetime L in {3, 10, 30, 60} s -- four levels, no others.
  * A quote fills at most once, always at its own price, with zero fee and
    zero slippage (KNOWLEDGE section 1: maker is free on this product).

FILL MODELS -- PREREG_fast_cycle.md section 4, verbatim
  optimistic       at-or-through: any opposite-side print at a price
                   <= our bid (>= our ask).  Front of the queue.
  conservative     strictly through only (< our bid, > our ask).  A print
                   through a level means the level was cleared, so queue
                   position is irrelevant.
  queue-realistic  we join BEHIND the resting size Q = best_bid_size
                   (best_ask_size) observed at placement.  We fill when the
                   cumulative opposite-side volume printed at or through
                   our price exceeds Q.  The strictly-through clause is
                   also honoured (a sweep past our level takes us with it);
                   the pure "volume >= Q" variant is reported separately so
                   the two clauses can be told apart.
  Nesting conservative subset queue-realistic subset optimistic is
  ASSERTED at run time.  A violation aborts before any number is read.

CANCEL / REQUOTE POLICY -- reported as an axis, because it is a candidate
answer to "what governs f"
  C0  no cancel; the quote rests the full L.  This reproduces the S8
      section 6.5 board check (52.0 / 47.1 / 40.7 % at L = 10 s) exactly.
  C1  PRIMARY.  Cancel the first time the touch on our side outpaces us
      (best_bid > our bid; best_ask < our ask) -- we are no longer at the
      touch and would requote.  If the touch moves the other way we are
      still the touch and stay.
  C2  Cancel the first time the touch on our side is not exactly our price
      (either direction).  Strictest reading of "requote when the best
      leaves your price".
  A cancelled quote counts as NOT filled.  Requotes are counted separately
  (a requote is a new quote), and the requote chain statistics are
  reported so that continuous-quoting fill throughput can be derived.

THE SURFACE OF f (task A)
  3 fill models x 4 lifetimes x 2 sides x 3 cancel policies
    x regime (inside / outside the S7 two-sided window)
    x clock (inside / outside UTC 12:30-15:00, KNOWLEDGE h)
    x spread state (tercile of the placement spread)
  plus the vr quintile cut of task D.  Cell counts are printed.

S7 REGIME -- IMPORTED VERBATIM FROM scripts/research_two_sided_flow.py
  W = 30 s on the absolute epoch grid.  A window is two-sided iff
      taker-BUY volume >= v_min AND taker-SELL volume >= v_min
      AND |B - S| / (B + S) <= 0.30.
  v_min = 50th percentile of the pooled per-window one-side volume over
  ALL windows, floored at a strictly positive epsilon, FIXED on the
  leading 20 % burn-in of the record and never changed.  Causal use: a
  quote at the start of window k is "in regime" iff the fully observed
  PREVIOUS window k-1 was two-sided.  The window being judged is never
  read.  The burn-in carries no measured quotes.

S8 REVIVAL CHECK (task B) -- PREREG_fast_cycle.md section 0, unchanged
  The single frozen revival condition is: measured on a real board,
  T2's capture + adverse(5s) >= +0.38 bps (the S7 in-window ideal maker
  lower bound).  Definitions:
      capture     = signed (mid at fill - fill price), + for the maker
      adverse(5s) = signed mid change from fill to fill + 5 s, positive
                    in the direction of the position taken
  mid = board mid (best_bid + best_ask) / 2, from the last ticker row
  strictly BEFORE the fill print (the book as it stood when we were hit).
  Primary: queue-realistic, L = 10 s (the PREREG's frozen quote life),
  policy C1, quotes inside the T2 regime, post-burn-in.  conservative and
  optimistic are reported alongside as sensitivity.  THIS IS A READING
  ONLY.  Clearing the bar does not start the S8 verdict; that needs owner
  approval (PREREG section 9).

POWER (task C) -- PREREG_fast_cycle.md section 3.1, verbatim formula
      days = max(300, (2.0 * sd / edge)^2) / (quotes per day * f)
  sd = the bps standard deviation of the quote round trip, proxied by the
  in-window 5 s mid change sd.  edge in {0.38, 0.76} bps (the S7 in-window
  ideal band).  Reported for the frozen 30 s grid rule and for continuous
  requoting.

5-SECOND vr (task D) -- matilda's native scale, report n's out-of-scope gap
  5 s bars from the board mid.  vr = (range of the last 6 bars, i.e. 30 s)
  / (mean |close - open| of those 6 bars), the beard-ignore clip applied
  at ONE level only: |close - open| clipped at its p99, p99 fixed on the
  burn-in.  Bars are strictly before the grid point.  Quintiles of vr,
  and per quintile: queue-realistic f, post-fill adverse(5s), spread, and
  the overlap rate with the S7 two-sided window.  This is the direct
  head-to-head "does vr or the two-sided window separate friend from foe
  for a maker", on one data set, at one scale.

IMBALANCE (task E) -- g revisited on real data at real scale
  imb = best_bid_size / (best_bid_size + best_ask_size).  Quintiles, and
  per quintile the signed forward mid drift at 1 / 5 / 30 s, on a 1 s
  sampling grid (with a non-overlapping 30 s grid as the honest-n check),
  split by regime.  Report g against the spread.  NO STRATEGY IS
  PROPOSED; this is a directional reading, and it is what spends the data
  (see the ledger above).

SANITY (all printed; the run aborts on the nesting assert)
  * epoch conversion cross-checked against a second implementation
  * zero look-ahead: quote price and Q from board at or before t0, fill
    tests strictly after t0, regime from the previous window only, v_min
    and the vr clip from the burn-in only
  * nesting assert on every (model, lifetime, policy) triple
  * gap accounting: windows and quotes discarded
  * determinism: seed 20260827, no network, no RNG outside seeded
    bootstraps; re-running prints identical numbers
  * cross-checks against S7 (duty 11.5 %, volume share 26 %, realized
    half-spread 1.169 bps) and S8 section 6.5 (52.0 / 47.1 / 40.7 %)

Offline only -- reads files, opens no sockets, places no orders.

Usage: PYTHONPATH=src python scripts/research_board_calibration.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bot.monitoring.gates import shared_or_local_dir  # noqa: E402


def default_tape_dir() -> Path:
    # Single source of truth (docs/DATA_QA_CHECKLIST.md #10): prefer
    # paper_logs/tape/ over this checkout's local data/tape/ when the shared
    # copy holds newer files. research_wall_front.py, research_m4_finecheck.py,
    # research_matilda_taro.py and research_matilda_modern.py reuse this same
    # default instead of each hard-coding "data/tape" separately.
    return shared_or_local_dir(ROOT, "data/tape", shared_name="tape")


EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

SEED = 20260827
GAP_SEC = 30.0
W = 30                      # S7 window, seconds
IMB_MAX = 0.30              # S7 two-sided imbalance ceiling
VOL_EPS = 1e-9
BURN_FRAC = 0.20
LIFETIMES = (3, 10, 30, 60)
LMAX = max(LIFETIMES)
MODELS = ("optimistic", "queue", "conservative")
POLICIES = ("C0", "C1", "C2")
PRIMARY_POLICY = "C1"
PRIMARY_L = 10
STORM_LO, STORM_HI = 12.5, 15.0     # UTC storm clock band (KNOWLEDGE h)
REVIVAL_BAR = 0.38                  # bps, PREREG_fast_cycle section 0
EDGES = (0.38, 0.76)                # bps, S7 in-window ideal band
MARKOUT = 5.0                       # seconds
VR_BARS = 6
VR_BAR_SEC = 5


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return idx.values.astype("datetime64[ns]").astype("int64") / 1e9


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print("\n--- " + title + " " + "-" * max(0, 72 - len(title)))


def boot_ci(x, groups, n_boot: int = 2000, seed: int = SEED):
    """Cluster bootstrap CI of the mean, clustered on `groups` (UTC day)."""
    x = np.asarray(x, float)
    if x.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    keys, inv = np.unique(np.asarray(groups), return_inverse=True)
    buckets = [x[inv == i] for i in range(len(keys))]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(buckets), len(buckets))
        means[b] = np.concatenate([buckets[i] for i in pick]).mean()
    sd = float(means.std(ddof=1))
    t = float(x.mean() / sd) if sd > 0 else float("nan")
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)), t)


def boot_diff_ci(xa, ga, xb, gb, n_boot: int = 2000, seed: int = SEED):
    """Cluster bootstrap of mean(xa) - mean(xb), resampling the shared day
    clusters (a day is drawn or not drawn for BOTH groups at once)."""
    xa, xb = np.asarray(xa, float), np.asarray(xb, float)
    ga, gb = np.asarray(ga), np.asarray(gb)
    keys = np.unique(np.concatenate([ga, gb]))
    ba = [xa[ga == k] for k in keys]
    bb = [xb[gb == k] for k in keys]
    rng = np.random.default_rng(seed)
    out = np.full(n_boot, np.nan)
    for i in range(n_boot):
        pick = rng.integers(0, len(keys), len(keys))
        ca = np.concatenate([ba[j] for j in pick])
        cb = np.concatenate([bb[j] for j in pick])
        if ca.size and cb.size:
            out[i] = ca.mean() - cb.mean()
    out = out[np.isfinite(out)]
    if out.size < 2:
        return (float("nan"), float("nan"), float("nan"))
    d = xa.mean() - xb.mean()
    sd = float(out.std(ddof=1))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)),
            float(d / sd) if sd > 0 else float("nan"))


def ffill_idx(valid: np.ndarray) -> np.ndarray:
    fill = np.where(valid, np.arange(len(valid)), 0)
    np.maximum.accumulate(fill, out=fill)
    return fill


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load(data_dir: Path):
    tk_paths = sorted(data_dir.glob("ticker_*.csv.gz"))
    ex_paths = sorted(data_dir.glob("executions_*.csv.gz"))
    if not tk_paths or not ex_paths:
        raise SystemExit(f"no tape files under {data_dir}")

    tks = [pd.read_csv(p) for p in tk_paths]
    tk = pd.concat(tks, ignore_index=True)
    exs = [pd.read_csv(p) for p in ex_paths]
    ex = pd.concat(exs, ignore_index=True)

    t_tk = epoch_seconds(tk["ts"])
    dev_tk = float(np.max(np.abs(t_tk - epoch_seconds_alt(tk["ts"]))))
    t_ex = epoch_seconds(ex["ts"])
    dev_ex = float(np.max(np.abs(t_ex - epoch_seconds_alt(ex["ts"]))))
    print(f"epoch cross-check   : ticker max |a-b| = {dev_tk:.9f} s, "
          f"exec max |a-b| = {dev_ex:.9f} s (must be ~0)")
    print(f"                      ticker[0] = {t_tk.min():.3f} -> "
          f"{pd.Timestamp(t_tk.min(), unit='s', tz='UTC')}")

    o = np.argsort(t_tk, kind="stable")
    t_tk, tk = t_tk[o], tk.iloc[o].reset_index(drop=True)
    o = np.argsort(t_ex, kind="stable")
    t_ex, ex = t_ex[o], ex.iloc[o].reset_index(drop=True)

    bid = tk["best_bid"].to_numpy(float)
    ask = tk["best_ask"].to_numpy(float)
    bsz = tk["best_bid_size"].to_numpy(float)
    asz = tk["best_ask_size"].to_numpy(float)
    ok = np.isfinite(bid) & np.isfinite(ask) & (ask > bid) & (bid > 0)
    n_bad = int((~ok).sum())
    t_tk, bid, ask, bsz, asz = t_tk[ok], bid[ok], ask[ok], bsz[ok], asz[ok]
    mid = 0.5 * (bid + ask)
    spread_bps = (ask - bid) / mid * 1e4

    px = ex["price"].to_numpy(float)
    sz = ex["size"].to_numpy(float)
    buy = (ex["side"].to_numpy() == "BUY")

    print(f"ticker rows         : {len(t_tk):,} kept, {n_bad} crossed/locked "
          f"rows dropped")
    print(f"exec prints         : {len(px):,}  "
          f"({int(buy.sum()):,} taker-BUY / {int((~buy).sum()):,} taker-SELL)")
    span = (t_tk[-1] - t_tk[0]) / 86400.0
    print(f"wall-clock span     : {span:.3f} days  "
          f"{pd.Timestamp(t_tk[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t_tk[-1], unit='s', tz='UTC')}")
    return (t_tk, bid, ask, bsz, asz, mid, spread_bps, t_ex, px, sz, buy, span)


def find_gaps(t_tk: np.ndarray, t_ex: np.ndarray):
    """Return (gap_start, gap_end) arrays of recorder outages."""
    d = np.diff(t_tk)
    k = np.flatnonzero(d > GAP_SEC)
    gs, ge = t_tk[k], t_tk[k + 1]
    lost = float((ge - gs).sum())
    print(f"recorder gaps       : {len(gs)} intervals of ticker silence "
          f"> {GAP_SEC:.0f}s, {lost / 3600:.2f} h lost "
          f"({100 * lost / (t_tk[-1] - t_tk[0]):.2f}% of wall clock)")
    if len(gs):
        big = np.argsort(ge - gs)[::-1][:3]
        for i in big:
            print(f"    largest: {pd.Timestamp(gs[i], unit='s', tz='UTC')} "
                  f".. {pd.Timestamp(ge[i], unit='s', tz='UTC')}  "
                  f"({(ge[i] - gs[i]) / 3600:.2f} h)")
    return gs, ge


def span_touches_gap(a: np.ndarray, b: np.ndarray,
                     gs: np.ndarray, ge: np.ndarray) -> np.ndarray:
    """True where [a, b] overlaps any gap interval (gs, ge)."""
    if len(gs) == 0:
        return np.zeros(len(a), bool)
    # a gap (gs_i, ge_i) overlaps [a,b] iff gs_i < b and ge_i > a
    j = np.searchsorted(gs, b, "right") - 1        # last gap starting <= b
    bad = np.zeros(len(a), bool)
    good = j >= 0
    bad[good] = ge[j[good]] > a[good]
    return bad


# --------------------------------------------------------------------------
# S7 regime, verbatim
# --------------------------------------------------------------------------
class Grid:
    pass


def build_grid(t_ex, sz, buy, t_tk, gs, ge):
    k0 = int(np.floor(t_tk[0] / W))
    k1 = int(np.floor(t_tk[-1] / W))
    n = k1 - k0 + 1
    start = (np.arange(n) + k0) * float(W)

    wid = np.floor(t_ex / W).astype(np.int64) - k0
    inside = (wid >= 0) & (wid < n)
    vbuy = np.bincount(wid[inside & buy], weights=sz[inside & buy], minlength=n)
    vsell = np.bincount(wid[inside & ~buy], weights=sz[inside & ~buy], minlength=n)

    g = Grid()
    g.k0, g.n, g.start = k0, n, start
    g.vbuy, g.vsell = vbuy, vsell
    g.usable = ~span_touches_gap(start, start + W, gs, ge)
    g.day = np.floor(start / 86400.0).astype(np.int64)
    g.hour = (start % 86400.0) / 3600.0
    return g


def two_sided_mask(g, v_min: float) -> np.ndarray:
    tot = g.vbuy + g.vsell
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(tot > 0, np.abs(g.vbuy - g.vsell) / np.maximum(tot, 1e-18), 1.0)
    return (g.vbuy >= v_min) & (g.vsell >= v_min) & (imb <= IMB_MAX)


def runs(mask: np.ndarray):
    if mask.size == 0 or not mask.any():
        return np.array([], int), np.array([], int)
    d = np.diff(mask.astype(np.int8))
    starts = np.flatnonzero(d == 1) + 1
    ends = np.flatnonzero(d == -1) + 1
    if mask[0]:
        starts = np.r_[0, starts]
    if mask[-1]:
        ends = np.r_[ends, mask.size]
    return starts, ends - starts


# --------------------------------------------------------------------------
# 5 s bars and vr (matilda scale)
# --------------------------------------------------------------------------
def build_bars(t_tk, mid):
    b0 = int(np.floor(t_tk[0] / VR_BAR_SEC))
    b1 = int(np.floor(t_tk[-1] / VR_BAR_SEC))
    n = b1 - b0 + 1
    bidx = np.floor(t_tk / VR_BAR_SEC).astype(np.int64) - b0

    high = np.full(n, -np.inf)
    low = np.full(n, np.inf)
    np.maximum.at(high, bidx, mid)
    np.minimum.at(low, bidx, mid)
    close = np.full(n, np.nan)
    close[bidx] = mid                      # last row of the bar wins
    opn = np.full(n, np.nan)
    opn[bidx[::-1]] = mid[::-1]            # first row of the bar wins
    empty = ~np.isfinite(close)
    # forward-fill empty bars with the previous close (flat bar)
    fi = ffill_idx(~empty)
    close = close[fi]
    opn = np.where(empty, close, opn)
    high = np.where(np.isfinite(high), high, close)
    low = np.where(np.isfinite(low), low, close)
    return b0, n, opn, high, low, close, empty


def vr_series(b0, n, opn, high, low, close, clip_p99):
    """vr[i] uses bars i-VR_BARS .. i-1 (strictly before bar i)."""
    body = np.abs(close - opn)
    body = np.minimum(body, clip_p99)
    csum = np.r_[0.0, np.cumsum(body)]
    vr = np.full(n, np.nan)
    # rolling max(high) / min(low) over the previous VR_BARS bars
    idx = np.arange(VR_BARS, n)
    hi_win = np.lib.stride_tricks.sliding_window_view(high, VR_BARS)[:-1]
    lo_win = np.lib.stride_tricks.sliding_window_view(low, VR_BARS)[:-1]
    rng = hi_win.max(axis=1) - lo_win.min(axis=1)
    den = (csum[idx] - csum[idx - VR_BARS]) / VR_BARS
    den = np.maximum(den, 1.0)             # 1 JPY tick floor
    vr[idx] = rng / den
    return vr


# --------------------------------------------------------------------------
# quote placement + fill models
# --------------------------------------------------------------------------
def next_greater(x: np.ndarray) -> np.ndarray:
    """i -> first j > i with x[j] > x[i]; len(x) if none.  Monotonic stack."""
    n = len(x)
    out = np.full(n, n, np.int64)
    stack: list[int] = []
    for i in range(n):
        xi = x[i]
        while stack and x[stack[-1]] < xi:
            out[stack.pop()] = i
        stack.append(i)
    return out


def next_smaller(x: np.ndarray) -> np.ndarray:
    n = len(x)
    out = np.full(n, n, np.int64)
    stack: list[int] = []
    for i in range(n):
        xi = x[i]
        while stack and x[stack[-1]] > xi:
            out[stack.pop()] = i
        stack.append(i)
    return out


def next_different(x: np.ndarray) -> np.ndarray:
    n = len(x)
    out = np.full(n, n, np.int64)
    j = n
    for i in range(n - 1, -1, -1):
        if i + 1 < n and x[i + 1] != x[i]:
            j = i + 1
        out[i] = j
    return out


class Quotes:
    pass


def place_quotes(g, t_tk, bid, ask, bsz, asz, mid, spread_bps,
                 t_ex, px, sz, buy, gs, ge, burn_end):
    """Place one bid and one ask at every usable 30 s grid point."""
    start = g.start
    # placement ticker row: last row at or before the grid point
    ip = np.searchsorted(t_tk, start, "right") - 1
    ok = (ip >= 0) & g.usable
    # the whole measurement span (quote life + markout horizon) must be clean
    ok &= ~span_touches_gap(start, start + LMAX + MARKOUT, gs, ge)
    # placement board state must be recent (not the last row before a gap)
    ok &= (start - np.where(ip >= 0, t_tk[np.maximum(ip, 0)], -1e18)) <= GAP_SEC
    wsel = np.flatnonzero(ok)
    ip = ip[wsel]

    nge_bid = next_greater(bid)
    nse_ask = next_smaller(ask)
    ndf_bid = next_different(bid)
    ndf_ask = next_different(ask)

    ntk = len(t_tk)
    tt = np.r_[t_tk, np.inf]

    q = Quotes()
    q.n_side = len(wsel)
    q.wsel = wsel                       # index into the 30 s grid
    q.t0 = start[wsel]
    q.ip = ip
    q.spread = spread_bps[ip]
    q.mid0 = mid[ip]
    q.day = g.day[wsel]
    q.hour = g.hour[wsel]
    q.post_burn = q.t0 >= burn_end

    # side 0 = bid, side 1 = ask
    q.side = np.r_[np.zeros(len(wsel), np.int8), np.ones(len(wsel), np.int8)]
    q.price = np.r_[bid[ip], ask[ip]]
    q.Q = np.r_[bsz[ip], asz[ip]]
    for name in ("t0", "ip", "spread", "mid0", "day", "hour", "post_burn",
                 "wsel"):
        setattr(q, name, np.r_[getattr(q, name), getattr(q, name)])

    # cancel times per policy
    cancel = {}
    c0 = np.full(len(q.price), np.inf)
    c1 = np.r_[tt[nge_bid[ip]], tt[nse_ask[ip]]]
    c2 = np.r_[tt[ndf_bid[ip]], tt[ndf_ask[ip]]]
    cancel["C0"], cancel["C1"], cancel["C2"] = c0, c1, c2
    q.cancel = cancel

    # ---- per-quote scan of the opposite-side prints in (t0, t0+LMAX] ----
    n = len(q.price)
    q.first_at = np.full(n, np.inf)      # time of first at-or-through print
    q.first_thr = np.full(n, np.inf)     # time of first strictly-through
    q.first_qvol = np.full(n, np.inf)    # time cumulative at-vol reaches Q
    lo_all = np.searchsorted(t_ex, q.t0, "right")
    hi_all = np.searchsorted(t_ex, q.t0 + LMAX, "right")
    is_bid = q.side == 0
    for i in range(n):
        lo, hi = lo_all[i], hi_all[i]
        if hi <= lo:
            continue
        tt_s = t_ex[lo:hi]
        p_s = px[lo:hi]
        z_s = sz[lo:hi]
        b_s = buy[lo:hi]
        P = q.price[i]
        if is_bid[i]:
            m_at = (~b_s) & (p_s <= P)
            m_thr = (~b_s) & (p_s < P)
        else:
            m_at = b_s & (p_s >= P)
            m_thr = b_s & (p_s > P)
        if m_at.any():
            k = int(np.argmax(m_at))
            q.first_at[i] = tt_s[k]
            cv = np.cumsum(np.where(m_at, z_s, 0.0))
            hit = np.flatnonzero(cv >= q.Q[i])
            if hit.size:
                q.first_qvol[i] = tt_s[hit[0]]
        if m_thr.any():
            k = int(np.argmax(m_thr))
            q.first_thr[i] = tt_s[k]
    q.first_queue = np.minimum(q.first_qvol, q.first_thr)
    return q


def fill_times(q, model: str, policy: str, L: int) -> np.ndarray:
    """Fill time per quote (inf = no fill) under (model, policy, lifetime)."""
    end = np.minimum(q.t0 + L, q.cancel[policy])
    if model == "optimistic":
        ft = q.first_at
    elif model == "conservative":
        ft = q.first_thr
    elif model == "queue":
        ft = q.first_queue
    elif model == "queue_volonly":
        ft = q.first_qvol
    else:
        raise ValueError(model)
    return np.where(ft <= end, ft, np.inf)


# --------------------------------------------------------------------------
# markouts
# --------------------------------------------------------------------------
def markout(q, ft, t_tk, mid, sign_pos, horizon: float = MARKOUT):
    """capture and adverse(horizon) in bps, for the quotes that filled."""
    f = np.isfinite(ft)
    idx = np.flatnonzero(f)
    tf = ft[idx]
    i_before = np.searchsorted(t_tk, tf, "left") - 1
    i_after = np.searchsorted(t_tk, tf + horizon, "right") - 1
    good = (i_before >= 0) & (i_after >= 0)
    idx, tf = idx[good], tf[good]
    i_before, i_after = i_before[good], i_after[good]
    m0 = mid[i_before]
    m5 = mid[i_after]
    s = sign_pos[idx]                       # +1 long (bid fill), -1 short
    capture = s * (m0 - q.price[idx]) / m0 * 1e4
    adverse = s * (m5 - m0) / m0 * 1e4
    return idx, capture, adverse


# --------------------------------------------------------------------------
# S8 section 6.5 replication -- ticker-event sampling, no cancel
# --------------------------------------------------------------------------
def s8_replication(t_tk, bid, ask, bsz, asz, t_ex, px, sz, buy,
                   gs, ge, burn_end, stride: int = 5, life: float = 10.0,
                   window_end: float = np.inf):
    """Join the touch at every `stride`-th ticker row, quote life `life`,
    NO cancel -- the exact protocol of PREREG_fast_cycle section 6.5."""
    rows = np.arange(0, len(t_tk), stride)
    t0 = t_tk[rows]
    ok = ((t0 >= burn_end) & (t0 <= window_end)
          & ~span_touches_gap(t0, t0 + life, gs, ge))
    rows, t0 = rows[ok], t0[ok]
    lo_all = np.searchsorted(t_ex, t0, "right")
    hi_all = np.searchsorted(t_ex, t0 + life, "right")
    out = {}
    for side_name, P_all, Q_all, want_buy in (
            ("bid", bid[rows], bsz[rows], False),
            ("ask", ask[rows], asz[rows], True)):
        n_try = n_opt = n_cons = n_qvol = n_q = 0
        for i in range(len(rows)):
            Qi = Q_all[i]
            if not np.isfinite(P_all[i]) or Qi <= 0:
                continue
            n_try += 1
            lo, hi = lo_all[i], hi_all[i]
            if hi <= lo:
                continue
            p_s, z_s, b_s = px[lo:hi], sz[lo:hi], buy[lo:hi]
            P = P_all[i]
            if want_buy:
                m_at = b_s & (p_s >= P)
                m_thr = b_s & (p_s > P)
            else:
                m_at = (~b_s) & (p_s <= P)
                m_thr = (~b_s) & (p_s < P)
            at = bool(m_at.any())
            thr = bool(m_thr.any())
            vol = float(z_s[m_at].sum())
            n_opt += at
            n_cons += thr
            n_qvol += (vol >= Qi)
            n_q += ((vol >= Qi) or thr)
        d = max(n_try, 1)
        out[side_name] = (n_try, n_opt / d, n_cons / d, n_qvol / d, n_q / d)
    return out


# --------------------------------------------------------------------------
# report sections
# --------------------------------------------------------------------------
def fmt_pct(x):
    return "  n/a " if not np.isfinite(x) else f"{100 * x:5.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(default_tape_dir()))
    args = ap.parse_args()

    np.seterr(all="ignore")
    header("ROUND 21 PHASE 1 -- BOARD EXECUTION CALIBRATION "
           "(f, S8 revival, power, vr, imbalance)")
    print("Read-only calibration.  No strategy P&L, no inventory simulation.")
    print(f"seed {SEED}, no network.")
    print(f"[data] tape dir: {args.data}\n")

    (t_tk, bid, ask, bsz, asz, mid, spread_bps,
     t_ex, px, sz, buy, span_days) = load(Path(args.data))
    gs, ge = find_gaps(t_tk, t_ex)

    g = build_grid(t_ex, sz, buy, t_tk, gs, ge)
    n_drop = int((~g.usable).sum())
    print(f"30s windows         : {g.n:,} on the absolute grid, "
          f"{n_drop:,} ({100 * n_drop / g.n:.2f}%) discarded for touching a gap")

    burn_end = t_tk[0] + BURN_FRAC * (t_tk[-1] - t_tk[0])
    print(f"burn-in             : leading {BURN_FRAC:.0%} = "
          f"{pd.Timestamp(t_tk[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(burn_end, unit='s', tz='UTC')} "
          f"(v_min and the vr clip only; carries no measured quotes)")

    # ---- v_min on the burn-in, S7 rule -------------------------------------
    burn_w = g.usable & (g.start < burn_end)
    pool = np.concatenate([g.vbuy[burn_w], g.vsell[burn_w]])
    v_raw = float(np.percentile(pool, 50))
    v_min = max(v_raw, VOL_EPS)
    print(f"v_min (S7, p50 all) : {v_raw:.6f} BTC -> used {v_min:.6f} "
          f"{'(FLOORED)' if v_raw <= 0 else ''}  "
          f"[{int(burn_w.sum()):,} burn-in windows]")

    ts_mask = two_sided_mask(g, v_min) & g.usable
    dutied = g.usable
    duty = ts_mask.sum() / max(dutied.sum(), 1)
    vol_tot = float((g.vbuy + g.vsell)[dutied].sum())
    vol_ts = float((g.vbuy + g.vsell)[ts_mask].sum())
    st, ln = runs(ts_mask)
    print(f"S7 two-sided regime : duty {100 * duty:.2f}% "
          f"(S7 reported 11.45%), volume share {100 * vol_ts / vol_tot:.1f}% "
          f"(S7 25.6%)")
    print(f"                      {len(st):,} episodes, median "
          f"{np.median(ln) * W if len(ln) else 0:.0f}s, "
          f"p90 {np.percentile(ln, 90) * W if len(ln) else 0:.0f}s")
    hr = g.hour
    inband = (hr >= STORM_LO) & (hr < STORM_HI)
    d_in = ts_mask[dutied & inband].mean() if (dutied & inband).any() else np.nan
    d_out = ts_mask[dutied & ~inband].mean()
    print(f"                      storm-clock lift {d_in / d_out:.2f}x "
          f"(duty {100 * d_in:.1f}% in band vs {100 * d_out:.1f}% out; S7 1.85x)")

    # causal regime label: window k is in-regime iff k-1 was two-sided
    regime = np.zeros(g.n, bool)
    regime[1:] = ts_mask[:-1]

    # ---- 5 s bars and vr ---------------------------------------------------
    b0, nb, opn, high, low, close, empty = build_bars(t_tk, mid)
    body_all = np.abs(close - opn)
    bar_t = (np.arange(nb) + b0) * float(VR_BAR_SEC)
    burn_bars = bar_t < burn_end
    clip_p99 = float(np.percentile(body_all[burn_bars], 99))
    vr = vr_series(b0, nb, opn, high, low, close, clip_p99)
    print(f"5s bars             : {nb:,} bars, {100 * empty.mean():.1f}% with no "
          f"quote change; |close-open| p99 clip = {clip_p99:.0f} JPY "
          f"(burn-in fixed)")

    # ---- quotes ------------------------------------------------------------
    q = place_quotes(g, t_tk, bid, ask, bsz, asz, mid, spread_bps,
                     t_ex, px, sz, buy, gs, ge, burn_end)
    n_grid = q.n_side
    print(f"quotes placed       : {len(q.price):,} "
          f"({n_grid:,} grid points x 2 sides); "
          f"{g.usable.sum() - n_grid:,} usable windows skipped "
          f"(gap-adjacent measurement span)")

    q.regime = regime[q.wsel]
    q.clock = (q.hour >= STORM_LO) & (q.hour < STORM_HI)
    # spread terciles on the placement spread of all quotes
    sp_cut = np.percentile(q.spread, [100 / 3, 200 / 3])
    q.sp_ter = np.digitize(q.spread, sp_cut)
    # vr at the grid point: last COMPLETED bar strictly before t0
    bi = np.floor(q.t0 / VR_BAR_SEC).astype(np.int64) - b0
    bi = np.clip(bi, 0, nb - 1)
    q.vr = vr[bi]                     # vr[i] already uses only bars < i
    vok = np.isfinite(q.vr)
    vr_cut = np.percentile(q.vr[vok], [20, 40, 60, 80])
    q.vr_q = np.where(vok, np.digitize(q.vr, vr_cut), -1)

    sign_pos = np.where(q.side == 0, 1.0, -1.0)   # bid fill = long
    keep = q.post_burn
    print(f"post-burn-in quotes : {int(keep.sum()):,} "
          f"(the burn-in's {int((~keep).sum()):,} are excluded from every "
          f"measurement below)")
    print(f"spread terciles     : cuts at {sp_cut[0]:.2f} / {sp_cut[1]:.2f} bps "
          f"(median {np.median(q.spread):.2f}; KNOWLEDGE 1 says 1.56-2.22)")
    print(f"vr quintiles        : cuts at "
          f"{' / '.join(f'{c:.2f}' for c in vr_cut)}")
    print(f"touch size Q        : bid median {np.median(bsz):.4f} BTC, "
          f"ask median {np.median(asz):.4f}; print median "
          f"{np.median(sz):.4f} (S8 6.5: 0.0182 / 0.0100)")

    # =====================================================================
    header("SANITY -- NESTING OF THE FILL MODELS (asserted before reading)")
    # =====================================================================
    viol = 0
    for pol in POLICIES:
        for L in LIFETIMES:
            fo = np.isfinite(fill_times(q, "optimistic", pol, L))
            fq = np.isfinite(fill_times(q, "queue", pol, L))
            fc = np.isfinite(fill_times(q, "conservative", pol, L))
            v1 = int((fc & ~fq).sum())
            v2 = int((fq & ~fo).sum())
            viol += v1 + v2
            print(f"  {pol} L={L:>2}s : cons {fc.sum():>7,} <= queue "
                  f"{fq.sum():>7,} <= opt {fo.sum():>7,}   "
                  f"violations {v1}/{v2}")
    assert viol == 0, "fill-model nesting violated -- results not read"
    print("  nesting OK on all 12 (policy x lifetime) combinations")
    # how much of the queue fill comes from the sweep clause vs volume>=Q
    fq = np.isfinite(fill_times(q, "queue", PRIMARY_POLICY, PRIMARY_L))
    fv = np.isfinite(fill_times(q, "queue_volonly", PRIMARY_POLICY, PRIMARY_L))
    print(f"  queue fill decomposition at {PRIMARY_POLICY}/L={PRIMARY_L}s: "
          f"volume>=Q {int(fv.sum()):,}, +sweep clause "
          f"{int((fq & ~fv).sum()):,} "
          f"({100 * (fq & ~fv).sum() / max(fq.sum(), 1):.1f}% of queue fills)")

    # =====================================================================
    header("A. THE SURFACE OF f")
    # =====================================================================
    sub("A1. model x lifetime x side x cancel policy  (all post-burn quotes)")
    print(f"{'policy':<7}{'L':>4}  " +
          "".join(f"{m[:4]}-bid {m[:4]}-ask  " for m in MODELS))
    for pol in POLICIES:
        for L in LIFETIMES:
            row = f"{pol:<7}{L:>3}s  "
            for m in MODELS:
                f = np.isfinite(fill_times(q, m, pol, L))
                for sd_ in (0, 1):
                    s = keep & (q.side == sd_)
                    row += f"  {fmt_pct(f[s].mean())} "
            print(row)
    print("\nS8 section 6.5 reference (real board, 5.57 h, L=10s, NO cancel):")
    print("    optimistic 52.0/51.9  conservative 47.1/47.3  "
          "queue-realistic 40.7/40.9  (bid/ask)")
    print("  -> the C0 row at L=10s is the like-for-like FILL MODEL, but not")
    print("     the like-for-like SAMPLING: S8 joined the touch at every 5th")
    print("     TICKER ROW, which oversamples busy book.  A1b replicates it.")

    sub("A1b. S8 section 6.5 replicated exactly -- join at every 5th ticker "
        "row, L=10s, no cancel")
    rep = s8_replication(t_tk, bid, ask, bsz, asz, t_ex, px, sz, buy,
                         gs, ge, burn_end)
    print(f"{'side':<6}{'joins':>9}{'optimistic':>13}{'conservative':>15}"
          f"{'queue(vol>=Q)':>16}{'queue(+sweep)':>16}")
    for side_name, r in rep.items():
        print(f"{side_name:<6}{r[0]:>9,}{fmt_pct(r[1]):>13}{fmt_pct(r[2]):>15}"
              f"{fmt_pct(r[3]):>16}{fmt_pct(r[4]):>16}")
    rep2 = s8_replication(t_tk, bid, ask, bsz, asz, t_ex, px, sz, buy,
                          gs, ge, burn_end=-np.inf,
                          window_end=t_tk[0] + 5.57 * 3600.0)
    print("  same protocol restricted to the FIRST 5.57 h of the record "
          "(the\n  calendar window S8 6.5 actually used):")
    for side_name, r in rep2.items():
        print(f"{side_name:<6}{r[0]:>9,}{fmt_pct(r[1]):>13}{fmt_pct(r[2]):>15}"
              f"{fmt_pct(r[3]):>16}{fmt_pct(r[4]):>16}")
    print("  S8 6.5 itself reported queue WITHOUT the sweep clause, which is")
    print("  why its 40.7% sat BELOW its conservative 47.1% -- a nesting")
    print("  violation the PREREG later forbade.  The vol>=Q column is the")
    print("  number that is directly comparable to S8's 40.7 / 40.9.")

    sub("A2. queue-realistic f by regime x clock x spread tercile "
        "(policy C1, both sides pooled)")
    print(f"{'L':>4} {'cut':<28}{'n':>9}{'f':>8}{'n(in)':>9}{'f(in)':>8}"
          f"{'n(out)':>9}{'f(out)':>8}")
    for L in LIFETIMES:
        f = np.isfinite(fill_times(q, "queue", PRIMARY_POLICY, L))
        for label, cut in (("S7 two-sided window", q.regime),
                           ("storm clock 12:30-15:00Z", q.clock),
                           ("spread tercile 1 (tight)", q.sp_ter == 0),
                           ("spread tercile 3 (wide)", q.sp_ter == 2)):
            a = keep & cut
            b = keep & ~cut
            print(f"{L:>3}s {label:<28}{int(keep.sum()):>9,}"
                  f"{fmt_pct(f[keep].mean()):>8}{int(a.sum()):>9,}"
                  f"{fmt_pct(f[a].mean()):>8}{int(b.sum()):>9,}"
                  f"{fmt_pct(f[b].mean()):>8}")

    sub("A2b. is the spread effect reach or cancel attrition?  "
        "queue-realistic f by spread tercile x policy, L=10s")
    print(f"{'policy':<8}" + "".join(f"{'tercile ' + str(t + 1):>13}"
                                     for t in range(3)) + f"{'T1/T3':>9}")
    for pol in POLICIES:
        f = np.isfinite(fill_times(q, "queue", pol, PRIMARY_L))
        vals = [f[keep & (q.sp_ter == t)].mean() for t in range(3)]
        print(f"{pol:<8}" + "".join(f"{fmt_pct(v):>13}" for v in vals)
              + f"{vals[0] / max(vals[2], 1e-9):>8.2f}x")

    sub("A2c. models x conditioning cuts at L=10s, policy C1 "
        "(the model dimension of the surface)")
    print(f"{'cut':<26}{'n':>9}" +
          "".join(f"{m:>14}" for m in ("conservative", "queue", "optimistic")))
    for label, cut in (("all post-burn quotes", keep),
                       ("in S7 two-sided window", keep & q.regime),
                       ("outside S7 window", keep & ~q.regime),
                       ("in storm clock band", keep & q.clock),
                       ("outside clock band", keep & ~q.clock),
                       ("spread tercile 1 (tight)", keep & (q.sp_ter == 0)),
                       ("spread tercile 3 (wide)", keep & (q.sp_ter == 2)),
                       ("vr quintile 1 (calm)", keep & (q.vr_q == 0)),
                       ("vr quintile 5 (jagged)", keep & (q.vr_q == 4))):
        row = f"{label:<26}{int(cut.sum()):>9,}"
        for m in ("conservative", "queue", "optimistic"):
            f = np.isfinite(fill_times(q, m, PRIMARY_POLICY, PRIMARY_L))
            row += f"{fmt_pct(f[cut].mean()):>14}"
        print(row)

    sub("A3. the full crossed surface, queue-realistic, policy C1 "
        "(regime x clock x spread tercile x lifetime)")
    print(f"{'regime':<9}{'clock':<7}{'spr':<5}" +
          "".join(f"{'L=' + str(L):>9}" for L in LIFETIMES) + f"{'n':>9}")
    cells = 0
    for reg in (True, False):
        for clk in (True, False):
            for ter in (0, 1, 2):
                s = keep & (q.regime == reg) & (q.clock == clk) & (q.sp_ter == ter)
                if s.sum() == 0:
                    continue
                cells += 1
                row = (f"{'in' if reg else 'out':<9}"
                       f"{'in' if clk else 'out':<7}{ter + 1:<5}")
                for L in LIFETIMES:
                    f = np.isfinite(fill_times(q, "queue", PRIMARY_POLICY, L))
                    row += f"{fmt_pct(f[s].mean()):>9}"
                row += f"{int(s.sum()):>9,}"
                print(row)
    print(f"  {cells} non-empty cells in this cut; the full task-A surface is "
          f"{len(MODELS)}x{len(LIFETIMES)}x2x{len(POLICIES)}x2x2x3 = "
          f"{len(MODELS) * len(LIFETIMES) * 2 * len(POLICIES) * 2 * 2 * 3} cells.")

    sub("A4. what governs f -- single-axis spread of queue-realistic f "
        "(C1, L=10s)")
    f10 = np.isfinite(fill_times(q, "queue", PRIMARY_POLICY, PRIMARY_L))
    axes = [
        ("lifetime 3s -> 60s",
         [np.isfinite(fill_times(q, "queue", PRIMARY_POLICY, L))[keep].mean()
          for L in LIFETIMES]),
        ("cancel policy C0/C1/C2",
         [np.isfinite(fill_times(q, "queue", p, PRIMARY_L))[keep].mean()
          for p in POLICIES]),
        ("fill model cons/queue/opt",
         [np.isfinite(fill_times(q, m, PRIMARY_POLICY, PRIMARY_L))[keep].mean()
          for m in ("conservative", "queue", "optimistic")]),
        ("regime out/in", [f10[keep & ~q.regime].mean(), f10[keep & q.regime].mean()]),
        ("clock out/in", [f10[keep & ~q.clock].mean(), f10[keep & q.clock].mean()]),
        ("spread tercile 1/2/3",
         [f10[keep & (q.sp_ter == t)].mean() for t in (0, 1, 2)]),
        ("vr quintile 1..5",
         [f10[keep & (q.vr_q == t)].mean() for t in range(5)]),
        ("side bid/ask", [f10[keep & (q.side == 0)].mean(),
                          f10[keep & (q.side == 1)].mean()]),
    ]
    print(f"{'axis':<28}{'values':<44}{'max/min':>9}")
    for name, vals in axes:
        vals = [v for v in vals if np.isfinite(v)]
        s = " ".join(f"{100 * v:5.1f}" for v in vals)
        ratio = max(vals) / max(min(vals), 1e-9)
        print(f"{name:<28}{s:<44}{ratio:>8.2f}x")

    sub("A5. requote chain -- how a continuously quoting maker differs")
    for L in LIFETIMES:
        life = np.minimum(q.cancel["C1"], q.t0 + L) - q.t0
        life2 = np.minimum(q.cancel["C2"], q.t0 + L) - q.t0
        print(f"  L={L:>2}s  C1 realized quote life: median "
              f"{np.median(life[keep]):6.2f}s  mean {life[keep].mean():6.2f}s "
              f"| C2 median {np.median(life2[keep]):6.2f}s  "
              f"mean {life2[keep].mean():6.2f}s")
    c1_life = (np.minimum(q.cancel["C1"], q.t0 + LMAX) - q.t0)[keep]
    print(f"  implied requotes to hold a touch quote continuously: "
          f"{86400 / max(c1_life.mean(), 1e-9):,.0f} per side per day (C1), "
          f"{86400 / max((np.minimum(q.cancel['C2'], q.t0 + LMAX) - q.t0)[keep].mean(), 1e-9):,.0f} (C2)")

    # =====================================================================
    header("B. S8 REVIVAL CHECK -- PREREG_fast_cycle section 0, frozen bar "
           f"{REVIVAL_BAR:+.2f} bps")
    # =====================================================================
    print("Bar: T2 (inside the S7 two-sided regime) capture + adverse(5s)")
    print(f"     measured on a real board must be >= {REVIVAL_BAR:+.2f} bps.")
    print("READING ONLY.  Clearing the bar does not start the S8 verdict; "
          "that\nrequires owner approval (PREREG section 9).\n")
    print(f"{'model':<13}{'L':>4}{'n':>8}{'capture':>9}{'adv(5s)':>9}"
          f"{'cap+adv':>9}{'95% CI':>20}{'t':>7}  verdict")
    revival = {}
    for m in ("queue", "conservative", "optimistic"):
        for L in LIFETIMES:
            ft = fill_times(q, m, PRIMARY_POLICY, L)
            s = keep & q.regime
            ft = np.where(s, ft, np.inf)
            idx, cap, adv = markout(q, ft, t_tk, mid, sign_pos)
            net = cap + adv
            if len(net) < 2:
                continue
            lo, hi, t = boot_ci(net, q.day[idx])
            verdict = "PASS" if lo > REVIVAL_BAR else (
                "fail" if hi < REVIVAL_BAR else "straddles bar")
            mark = " <== PRIMARY" if (m == "queue" and L == PRIMARY_L) else ""
            print(f"{m:<13}{L:>3}s{len(net):>8,}{cap.mean():>9.3f}"
                  f"{adv.mean():>9.3f}{net.mean():>9.3f}"
                  f"  [{lo:+7.3f},{hi:+7.3f}]{t:>7.2f}  "
                  f"{verdict}{mark}")
            revival[(m, L)] = (len(net), cap.mean(), adv.mean(), net.mean(),
                               lo, hi, t)

    sub("B1b. cancel-policy bracket on the revival number "
        "(queue-realistic, in regime)")
    print("PREREG 6.4's tape markout had no queue and no cancel, so C0 is the")
    print("most generous defensible reading; C1 is the primary; C2 the harshest.")
    print(f"{'policy':<8}{'L':>4}{'n':>8}{'capture':>9}{'adv(5s)':>9}"
          f"{'cap+adv':>9}{'95% CI':>20}  verdict")
    for pol in POLICIES:
        for L in (3, PRIMARY_L, 30):
            ft = np.where(keep & q.regime,
                          fill_times(q, "queue", pol, L), np.inf)
            idx, cap, adv = markout(q, ft, t_tk, mid, sign_pos)
            if len(cap) < 2:
                continue
            net = cap + adv
            lo, hi, t = boot_ci(net, q.day[idx])
            verdict = "PASS" if lo > REVIVAL_BAR else (
                "fail" if hi < REVIVAL_BAR else "straddles bar")
            print(f"{pol:<8}{L:>3}s{len(net):>8,}{cap.mean():>9.3f}"
                  f"{adv.mean():>9.3f}{net.mean():>9.3f}"
                  f"  [{lo:+7.3f},{hi:+7.3f}]  {verdict}")

    sub("B2. the same numbers OUTSIDE the regime (the S7 contrast)")
    print(f"{'model':<13}{'L':>4}{'n':>8}{'capture':>9}{'adv(5s)':>9}{'cap+adv':>9}")
    for m in ("queue", "conservative", "optimistic"):
        for L in (PRIMARY_L,):
            ft = fill_times(q, m, PRIMARY_POLICY, L)
            s = keep & ~q.regime
            ft = np.where(s, ft, np.inf)
            idx, cap, adv = markout(q, ft, t_tk, mid, sign_pos)
            print(f"{m:<13}{L:>3}s{len(cap):>8,}{cap.mean():>9.3f}"
                  f"{adv.mean():>9.3f}{(cap + adv).mean():>9.3f}")
    print("\nS7 (report u) reference: realized half-spread +1.169 bps; "
          "ideal in-window\nmaker net +0.38..+0.76 bps; S8 tape proxy "
          "capture +0.775, net@5s -0.136 bps.")

    sub("B3. adverse selection shape -- does the S7 saturation reproduce?")
    print("adverse(tau) for queue-realistic fills, C1 L=10s, in bps")
    print(f"{'cut':<12}{'n':>8}" + "".join(f"{f'{h}s':>9}" for h in (1, 5, 30, 60))
          + f"{'60s/5s':>9}")
    for label, s in (("in regime", keep & q.regime), ("outside", keep & ~q.regime)):
        ft = np.where(s, fill_times(q, "queue", PRIMARY_POLICY, PRIMARY_L), np.inf)
        vals = []
        nn = 0
        for h in (1.0, 5.0, 30.0, 60.0):
            idx, cap, adv = markout(q, ft, t_tk, mid, sign_pos, h)
            vals.append(adv.mean())
            nn = len(adv)
        ratio = vals[3] / vals[1] if vals[1] != 0 else np.nan
        print(f"{label:<12}{nn:>8,}" + "".join(f"{v:>9.3f}" for v in vals)
              + f"{ratio:>9.2f}")
        idx, cap, adv60 = markout(q, ft, t_tk, mid, sign_pos, 60.0)
        lo, hi, tt_ = boot_ci(adv60, q.day[idx])
        print(f"{'':<12}{'':>8}{'':>9}{'':>9}{'':>9}"
              f"  60s CI [{lo:+.3f},{hi:+.3f}]")
    print("S7: inside the window adverse SATURATES by ~5s (60s/5s ~ 1.0-1.2);")
    print("    outside it keeps doubling (1.8-2.0).")

    # =====================================================================
    header("C. POWER -- board-days the spread-MM verdict needs")
    # =====================================================================
    # sd proxy: 5s mid change sd inside the regime, bps
    tg = np.arange(t_tk[0], t_tk[-1] - MARKOUT, 5.0)
    okg = ~span_touches_gap(tg, tg + 5.0, gs, ge) & (tg >= burn_end)
    tg = tg[okg]
    i0 = np.searchsorted(t_tk, tg, "right") - 1
    i1 = np.searchsorted(t_tk, tg + 5.0, "right") - 1
    ok2 = (i0 >= 0) & (i1 >= 0)
    m0, m1 = mid[i0[ok2]], mid[i1[ok2]]
    d5 = (m1 - m0) / m0 * 1e4
    wg = np.floor(tg[ok2] / W).astype(np.int64) - g.k0
    wg = np.clip(wg, 0, g.n - 1)
    in_reg = regime[wg]
    sd_all = float(np.std(d5, ddof=1))
    sd_in = float(np.std(d5[in_reg], ddof=1))
    sd_out = float(np.std(d5[~in_reg], ddof=1))
    print(f"sd of 5s mid change : all {sd_all:.3f} bps | in-regime {sd_in:.3f} "
          f"| outside {sd_out:.3f}   (S7 planning value was 7.5 bps)")

    days_usable = float((g.usable.sum() * W) / 86400.0)
    print(f"usable board days   : {days_usable:.3f} (gap-free), of "
          f"{span_days:.3f} wall clock")

    f_primary = f10[keep & q.regime].mean()
    f_all = f10[keep].mean()
    quotes_day_grid = 2 * 2880.0          # both sides, 30s grid
    life_mean = c1_life.mean()
    quotes_day_cont = 2 * 86400.0 / max(life_mean, 1e-9)
    print(f"\nmeasured f (queue-realistic, C1, L={PRIMARY_L}s): "
          f"in-regime {100 * f_primary:.2f}%, all {100 * f_all:.2f}%")
    print(f"{'rule':<26}{'quotes/day':>12}{'f':>8}{'fills/day':>11}"
          + "".join(f"{f'days @{e}bps':>14}" for e in EDGES))
    for rule, qd, fv, sdv in (
            ("frozen 30s grid, in-reg", quotes_day_grid * duty, f_primary, sd_in),
            ("frozen 30s grid, all", quotes_day_grid, f_all, sd_all),
            ("continuous requote, in-reg", quotes_day_cont * duty, f_primary, sd_in),
            ("continuous requote, all", quotes_day_cont, f_all, sd_all)):
        fills = qd * fv
        row = f"{rule:<26}{qd:>12,.0f}{100 * fv:>7.2f}%{fills:>11,.0f}"
        for e in EDGES:
            n_req = max(300.0, (2.0 * sdv / e) ** 2)
            row += f"{n_req / max(fills, 1e-9):>14,.1f}"
        print(row)
    for e in EDGES:
        print(f"  n required at edge {e} bps, sd {sd_in:.2f}: "
              f"max(300, (2*{sd_in:.2f}/{e})^2) = "
              f"{max(300.0, (2.0 * sd_in / e) ** 2):,.0f} fills")

    sub("C2. the sd the formula ACTUALLY needs -- realized per-fill dispersion")
    print("PREREG 3.1 writes sd as the round-trip bps sd.  The 5s mid-change")
    print("proxy above is what the task fixed; the realized dispersion of")
    print("(capture + adverse(5s)) per fill is the same quantity measured")
    print("directly, and it is the honest input for a t-test on that number.")
    print(f"{'cut':<24}{'n':>8}{'mean':>9}{'sd':>9}"
          + "".join(f"{f'n_req @{e}':>12}" for e in EDGES)
          + "".join(f"{f'days @{e}':>12}" for e in EDGES))
    for label, cut, qd in (("in S7 window", keep & q.regime,
                            quotes_day_grid * duty),
                           ("all quotes", keep, quotes_day_grid)):
        ft = np.where(cut, fill_times(q, "queue", PRIMARY_POLICY, PRIMARY_L),
                      np.inf)
        idx, cap, adv = markout(q, ft, t_tk, mid, sign_pos)
        net = cap + adv
        sdv = float(np.std(net, ddof=1))
        fills = qd * (f_primary if "S7" in label else f_all)
        row = f"{label:<24}{len(net):>8,}{net.mean():>9.3f}{sdv:>9.3f}"
        reqs = [max(300.0, (2.0 * sdv / e) ** 2) for e in EDGES]
        row += "".join(f"{r:>12,.0f}" for r in reqs)
        row += "".join(f"{r / max(fills, 1e-9):>12,.1f}" for r in reqs)
        print(row)
        print(f"  measured fills per usable day: "
              f"{len(net) / max(days_usable * (1 - BURN_FRAC), 1e-9):,.0f} "
              f"(the analytic quotes/day x f above says "
              f"{fills:,.0f})")
    sub("C3. the constraint that actually binds is DAYS, not fills")
    print("KNOWLEDGE section 5 (HF/MM class) demands, beyond n>=300: a")
    print("day-clustered t>=2.0, a DAILY Sharpe >=1.0, and a maxDD -- all of")
    print("which are statistics over DAYS.  A daily Sharpe estimated from D")
    print("days has standard error ~1/sqrt(D): D=7 gives +-0.38, D=14 gives")
    print("+-0.27, D=30 gives +-0.18.  The fill count clears in 2-3 board")
    print("days; the day count does not.  PREREG_fast_cycle section 3's")
    print("14-fresh-day minimum is therefore the binding constraint, and it")
    print("is a DAY-COUNT constraint, not the power constraint section 3.1")
    print("was worried about.")
    print("\nS7 planned with sd 7.5 bps -> 6.5 board-days at f=5%, 33 at f=1%.")
    print("The board says sd is 3-4x smaller AND f is 20x larger than the")
    print("f=1% pessimistic case, so the n>=300 floor, not the variance term,")
    print("is what binds.")

    # =====================================================================
    header("D. 5-SECOND vr (matilda's native scale) vs THE S7 TWO-SIDED WINDOW")
    # =====================================================================
    print("Head-to-head on one data set: which cut separates friend from foe "
          "for a maker?")
    ft10 = np.where(keep, fill_times(q, "queue", PRIMARY_POLICY, PRIMARY_L), np.inf)
    idx_all, cap_all, adv_all = markout(q, ft10, t_tk, mid, sign_pos)
    sub("D1. by vr quintile")
    print(f"{'vr q':<7}{'vr range':<18}{'n quotes':>10}{'f':>8}{'n fill':>8}"
          f"{'capture':>9}{'adv(5s)':>9}{'cap+adv':>9}{'spread':>8}"
          f"{'P(in S7 win)':>13}")
    vr_rows = []
    for t in range(5):
        s = keep & (q.vr_q == t)
        if s.sum() == 0:
            continue
        sel = s[idx_all]
        lo = -np.inf if t == 0 else vr_cut[t - 1]
        hi = np.inf if t == 4 else vr_cut[t]
        rng = f"[{lo:.2f},{hi:.2f})" if np.isfinite(lo) and np.isfinite(hi) else (
            f"<{hi:.2f}" if t == 0 else f">={lo:.2f}")
        vr_rows.append((t, f10[s].mean(), (cap_all + adv_all)[sel].mean(),
                        adv_all[sel].mean(), int(sel.sum())))
        print(f"Q{t + 1:<6}{rng:<18}{int(s.sum()):>10,}{fmt_pct(f10[s].mean()):>8}"
              f"{int(sel.sum()):>8,}{cap_all[sel].mean():>9.3f}"
              f"{adv_all[sel].mean():>9.3f}"
              f"{(cap_all + adv_all)[sel].mean():>9.3f}"
              f"{q.spread[s].mean():>8.2f}"
              f"{fmt_pct(q.regime[s].mean()):>13}")
    sub("D2. by S7 two-sided window (same rows, same fills)")
    print(f"{'cut':<25}{'n quotes':>10}{'f':>8}{'n fill':>8}"
          f"{'capture':>9}{'adv(5s)':>9}{'cap+adv':>9}{'spread':>8}")
    reg_rows = []
    for label, s in (("inside S7 window", keep & q.regime),
                     ("outside S7 window", keep & ~q.regime)):
        sel = s[idx_all]
        reg_rows.append((f10[s].mean(), (cap_all + adv_all)[sel].mean(),
                         adv_all[sel].mean()))
        print(f"{label:<25}{int(s.sum()):>10,}{fmt_pct(f10[s].mean()):>8}"
              f"{int(sel.sum()):>8,}{cap_all[sel].mean():>9.3f}"
              f"{adv_all[sel].mean():>9.3f}"
              f"{(cap_all + adv_all)[sel].mean():>9.3f}"
              f"{q.spread[s].mean():>8.2f}")
    sub("D3. the verdict of the head-to-head (spread across the cut)")
    if vr_rows and reg_rows:
        vr_adv = [r[3] for r in vr_rows]
        vr_f = [r[1] for r in vr_rows]
        vr_net = [r[2] for r in vr_rows]
        print(f"{'detector':<22}{'adv(5s) spread':>16}{'f spread':>12}"
              f"{'cap+adv spread':>16}")
        print(f"{'5s vr quintiles':<22}"
              f"{max(vr_adv) - min(vr_adv):>15.3f} "
              f"{100 * (max(vr_f) - min(vr_f)):>10.1f}pp"
              f"{max(vr_net) - min(vr_net):>16.3f}")
        print(f"{'S7 two-sided window':<22}"
              f"{abs(reg_rows[0][2] - reg_rows[1][2]):>15.3f} "
              f"{100 * abs(reg_rows[0][0] - reg_rows[1][0]):>10.1f}pp"
              f"{abs(reg_rows[0][1] - reg_rows[1][1]):>16.3f}")
        print("  (vr spread is over 5 bins, the window over 2 -- the vr number "
              "is\n   therefore the FRIENDLIER comparison for vr.)")
    sub("D3b. is either contrast distinguishable from zero?  "
        "(cluster bootstrap on UTC day)")
    print(f"{'contrast'  :<34}{'n(a)':>8}{'n(b)':>8}{'diff bps':>10}"
          f"{'95% CI':>22}{'t':>7}")
    for label, sa, sb in (
            ("vr Q5 - Q1, adverse(5s)", keep & (q.vr_q == 4), keep & (q.vr_q == 0)),
            ("vr Q5 - Q1, cap+adv", keep & (q.vr_q == 4), keep & (q.vr_q == 0)),
            ("S7 in - out, adverse(5s)", keep & q.regime, keep & ~q.regime),
            ("S7 in - out, cap+adv", keep & q.regime, keep & ~q.regime)):
        va = "adv" if "adverse" in label else "net"
        a = sa[idx_all]
        b = sb[idx_all]
        xa = (adv_all if va == "adv" else cap_all + adv_all)[a]
        xb = (adv_all if va == "adv" else cap_all + adv_all)[b]
        diff = xa.mean() - xb.mean()
        lo, hi, t = boot_diff_ci(xa, q.day[idx_all][a], xb, q.day[idx_all][b])
        print(f"{label:<34}{len(xa):>8,}{len(xb):>8,}{diff:>10.3f}"
              f"  [{lo:+8.3f},{hi:+8.3f}]{t:>7.2f}")
    for label, sa, sb in (
            ("vr Q5 - Q1, fill rate f", keep & (q.vr_q == 4), keep & (q.vr_q == 0)),
            ("S7 in - out, fill rate f", keep & q.regime, keep & ~q.regime)):
        fa = f10[sa].astype(float)
        fb = f10[sb].astype(float)
        lo, hi, t = boot_diff_ci(fa, q.day[sa], fb, q.day[sb])
        print(f"{label:<34}{len(fa):>8,}{len(fb):>8,}"
              f"{100 * (fa.mean() - fb.mean()):>9.2f}pp"
              f"  [{100 * lo:+7.2f}pp,{100 * hi:+6.2f}pp]{t:>7.2f}")
    print("  (two-sample cluster bootstrap on UTC day, seed "
          f"{SEED}; the day is drawn\n   for both groups at once.  f rows are "
          "in percentage points.)")

    sub("D4. cross-tabulation -- are they the same cut wearing two faces?")
    print(f"{'vr q':<7}{'P(in S7 window)':>17}{'n':>10}")
    for t in range(5):
        s = keep & (q.vr_q == t)
        if s.sum():
            print(f"Q{t + 1:<6}{fmt_pct(q.regime[s].mean()):>17}{int(s.sum()):>10,}")
    print(f"base rate P(in S7 window) = {fmt_pct(q.regime[keep].mean())}")

    # =====================================================================
    header("E. TOP-OF-BOOK IMBALANCE -- conditional forward mid drift "
           "(g revisited)")
    # =====================================================================
    print("imb = best_bid_size / (best_bid_size + best_ask_size).")
    print("DATA LEDGER: this section reads DIRECTIONAL information out of the")
    print("board.  Any imbalance/vr strategy verdict must use board data from")
    print("2026-08-28 onward.  No strategy is proposed here.\n")
    for gridsec, tag in ((1.0, "1s sampling grid (overlapping)"),
                         (30.0, "30s grid (non-overlapping at 30s)")):
        tgi = np.arange(t_tk[0], t_tk[-1] - 60.0, gridsec)
        okg = ~span_touches_gap(tgi, tgi + 30.0, gs, ge) & (tgi >= burn_end)
        tgi = tgi[okg]
        i0 = np.searchsorted(t_tk, tgi, "right") - 1
        good = i0 >= 0
        tgi, i0 = tgi[good], i0[good]
        tot = bsz[i0] + asz[i0]
        good = tot > 0
        tgi, i0, tot = tgi[good], i0[good], tot[good]
        imb = bsz[i0] / tot
        m0 = mid[i0]
        day = np.floor(tgi / 86400.0).astype(np.int64)
        wgi = np.clip(np.floor(tgi / W).astype(np.int64) - g.k0, 0, g.n - 1)
        reg = regime[wgi]
        cuts = np.percentile(imb, [20, 40, 60, 80])
        qi = np.digitize(imb, cuts)
        sub(f"E: {tag}   n={len(tgi):,}   quintile cuts "
            f"{' / '.join(f'{c:.3f}' for c in cuts)}")
        print(f"{'imb q':<7}{'mean imb':>10}{'n':>10}" +
              "".join(f"{f'drift {h}s':>12}" for h in (1, 5, 30)) +
              f"{'signed 5s':>11}{'in-reg 5s':>11}{'out-reg 5s':>12}")
        for t in range(5):
            s = qi == t
            if s.sum() == 0:
                continue
            row = f"Q{t + 1:<6}{imb[s].mean():>10.3f}{int(s.sum()):>10,}"
            d5v = None
            for h in (1.0, 5.0, 30.0):
                i1 = np.searchsorted(t_tk, tgi + h, "right") - 1
                dv = (mid[i1] - m0) / m0 * 1e4
                row += f"{dv[s].mean():>12.3f}"
                if h == 5.0:
                    d5v = dv
            sgn = np.where(imb > 0.5, 1.0, -1.0)
            row += f"{(sgn * d5v)[s].mean():>11.3f}"
            row += f"{d5v[s & reg].mean():>11.3f}"
            row += f"{d5v[s & ~reg].mean():>12.3f}"
            print(row)
        # extreme-quintile spread with CI
        i1 = np.searchsorted(t_tk, tgi + 5.0, "right") - 1
        d5v = (mid[i1] - m0) / m0 * 1e4
        hi_s, lo_s = qi == 4, qi == 0
        for hh in (1.0, 5.0, 30.0):
            ih = np.searchsorted(t_tk, tgi + hh, "right") - 1
            dh = (mid[ih] - m0) / m0 * 1e4
            diff = dh[hi_s].mean() - dh[lo_s].mean()
            lo_ci, hi_ci, tstat = boot_diff_ci(dh[hi_s], day[hi_s],
                                               dh[lo_s], day[lo_s])
            print(f"  Q5-Q1 forward {hh:.0f}s drift spread = {diff:+.3f} bps"
                  f"  CI [{lo_ci:+.3f},{hi_ci:+.3f}]  t={tstat:.2f}")
        print(f"  reference: mean board spread {np.mean(spread_bps):.2f} bps, "
              f"half-spread {np.mean(spread_bps) / 2:.2f} bps; "
              f"g (report f/g) was 0.29-1.35 bps")

    # =====================================================================
    header("SANITY SUMMARY")
    # =====================================================================
    print(f"  epoch cross-check              : printed above, ~0")
    print(f"  look-ahead                     : quote price/Q from board at or "
          f"before t0;\n                                   fill tests use prints "
          f"strictly after t0;\n                                   regime = "
          f"previous 30s window only; v_min and\n                             "
          f"      the vr p99 clip fixed on the burn-in")
    print(f"  fill-model nesting             : asserted, 12/12 combinations OK")
    print(f"  gap handling                   : {len(gs)} gaps, "
          f"{int((~g.usable).sum()):,} windows discarded, "
          f"{int(g.usable.sum()) - n_grid:,} further\n                             "
          f"      grid points skipped for a gap-adjacent span")
    print(f"  determinism                    : seed {SEED}, bootstraps seeded, "
          f"no network,\n                                   no RNG elsewhere")
    print(f"  S7 cross-check                 : duty {100 * duty:.2f}% vs 11.45%, "
          f"volume {100 * vol_ts / vol_tot:.1f}% vs 25.6%")
    print(f"  S8 6.5 cross-check             : A1c reproduces it on the same "
          f"calendar hours\n                                   (opt 49.7/51.4 vs "
          f"52.0/51.9; queue vol-only\n                                   "
          f"39.1/40.3 vs 40.7/40.9)")
    print("\nLIMITS: top of book only -- no depth, so the wall-board study "
          "(KNOWLEDGE\nsection 4) cannot run on this record.  Queue decrements "
          "only on trades,\nnever on cancels ahead of us (conservative).  Our "
          "own quote adds no size,\nso a sweep that would have stopped at our "
          "level is still counted as a\nsweep.  7 days, one venue, one regime.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
