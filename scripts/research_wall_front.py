#!/usr/bin/env python3
"""WALL-FRONT LIMIT ORDER -- the pre-registered verdict (run once, report as is).

    PRE-REGISTRATION.  Everything below the line "FROZEN" was fixed in
    KNOWLEDGE.md section 4 on 2026-08-21 and re-specified scale-invariantly on
    2026-08-25, i.e. BEFORE this board record existed in usable form.  This
    docstring transcribes it verbatim; nothing here is tuned after a reading.

WHAT THIS IS
  matilda (docs/legacy/, the owner's 2019-2020 bot) placed its limit orders a
  little IN FRONT OF a large wall in the book, on the theory that the wall
  absorbs the incoming flow first, so a quote sheltered behind it suffers less
  adverse selection than a quote sitting naked at the touch.  This is an
  EXECUTION OPTION, not a strategy: the verdict is a difference between two
  ways of placing the same quote at the same instant.

  Report #26 (docs/RESEARCH_REPORT_2026-08-27aa.md) measured the naked-touch
  arm on top-of-book only and could not run this study for lack of depth.
  data/tape/board_top5_*.csv.gz (1 Hz top-5 depth) now exists, so the frozen
  bar can be applied once.

DATA
  data/tape/board_top5_YYYYMMDD.csv.gz   2026-08-20..26, 1 s sampled top-5
      depth: ts, bid_px_1..5, bid_sz_1..5, ask_px_1..5, ask_sz_1..5.
      *** ts is the LOCAL RECEIVE time. ***  It can be a few hundred ms off
      the exchange clock, so (a) every mid used for a markout is built from
      the board's OWN best bid/ask, never from another feed, and (b) matching
      against executions carries a conservative +/- 1 s margin (RTS_MARGIN):
      a print only counts as a fill if it lands strictly after t0+1 s.  The
      margin is applied IDENTICALLY to both arms, so the paired difference --
      the quantity the bar is written on -- is first-order immune to it.
      Margin 0 s is reported as a sensitivity, not as the primary.
  data/tape/executions_YYYYMMDD.csv.gz   ts, price, size, side (TAKER side).
  Recorder gaps are real (the largest is 2026-08-25T18:47Z..2026-08-26T02:54Z,
  ~8.1 h).  Same detection and discard discipline as the calibration:
  GAP_SEC = 30 s of silence; any grid point whose whole measurement span
  (quote life + the longest markout horizon) touches a gap is DISCARDED.
  Because the fills come from the execution tape and the prices from the
  board, the gap set is the UNION of board silence and execution silence
  (strictly more conservative than the calibration's single-series rule).

IMPLEMENTATION REUSE (structural, not by eye)
  epoch_seconds / epoch_seconds_alt / find_gaps / span_touches_gap /
  next_greater / next_smaller / boot_ci / boot_diff_ci / fmt_pct are IMPORTED
  from scripts/research_board_calibration.py.  The fill scan reproduces that
  script's inner loop clause for clause (at-or-through mask, strictly-through
  mask, cumulative volume vs Q, min(qvol, through)), and the same nesting
  assertion conservative subset queue subset optimistic guards every cell:
  a violation aborts before a single number is read.

============================ FROZEN ============================

WALL DEFINITION
  M24 = rolling median, over the trailing 24 h, of the BEST-LEVEL size, both
  sides pooled (bid_sz_1 and ask_sz_1 of every board row with ts < t0).
  A wall on our side = a level among our own top-5 whose size >= k * M24.
  k in {10, 30, 100}.  No absolute BTC anywhere.
  Day 1 (2026-08-20) is burn-in: it initialises M24 and carries NO measured
  quote.  Measurement starts 2026-08-21T00:00:00Z.
  If more than one level qualifies, the wall is the one NEAREST THE BEST
  (smallest level index) -- the only wall a quote can be placed in front of.

PLACEMENT RULE
  The absolute 30 s epoch grid, floor(t/30), the same grid the calibration
  and S7 live on.  At each grid point, per side:
    * if that side has NO wall, NEITHER arm places anything (the two arms are
      compared on exactly the same population of instants);
    * if it has a wall at price Wp, the WALL-FRONT arm quotes one offset in
      front of it -- bid: Wp + offset, ask: Wp - offset -- and the CONTROL
      arm quotes the plain touch (bid_px_1 / ask_px_1) at the same instant,
      the calibration's protocol unchanged.
  If the wall IS the best (level 1), "in front" is one offset inside the
  spread, as the pre-registration states.
  A wall-front price that would be marketable (bid price >= best ask, ask
  price <= best bid) cannot be placed; that grid point is dropped from BOTH
  arms and the count is reported.

OFFSET (second axis of the family)
  1 tick = 1 JPY (PRIMARY) / 24 JPY (the 2020-equivalent of matilda's 2 JPY,
  0.2 bps of the price of the day).

FILL MODEL -- the calibration's primary configuration, verbatim
  queue-realistic + overtake-cancel (C1) + 10 s lifetime.
    queue-realistic  we join BEHIND the size Q already resting at our price
                     and fill when cumulative opposite-side volume printed
                     at-or-through our price exceeds Q; a print strictly
                     through our price takes us with it regardless of Q.
    Q                the size at our exact price in our own top-5 at
                     placement.  A wall-front price with no resting size --
                     which is the mechanism's whole point -- gets Q = 0, i.e.
                     WE ARE THE FRONT OF THE QUEUE.
    C1               the calibration's next_greater/next_smaller clause,
                     unchanged: cancel at the first board row after t0 whose
                     best on our side has improved past the best AT
                     PLACEMENT (bid_px_1 > bid_px_1[t0]).  Note this is the
                     literal calibration formula -- it is a property of the
                     market, not of our price -- so the two arms share one
                     cancel clock and the pairing stays clean.  C0 (no
                     cancel) is reported as a bracket.
  A quote fills at most once, at its own price, zero fee, zero slippage
  (KNOWLEDGE section 1: maker is free on this product).

METRIC AND BAR (KNOWLEDGE section 4, registered 2026-08-21, unchanged)
  capture      = signed (mid at fill - fill price), + for the maker
  adverse(5s)  = signed mid change from fill to fill + 5 s, + in the
                 direction of the position taken
  mid          = board mid, last board row strictly BEFORE the fill print.
  The fill-conditional expected-value difference
      (wall-front) - (plain touch), on capture + adverse(5s)
  must be >= +2 bps, AND the day-clustered t >= 2.0, AND each arm must have
  >= 100 fills.  30 s markout is reported as a secondary horizon only.

MULTIPLICITY AND SELECTION (frozen now, before the run)
  Cells = k{10,30,100} x offset{1 tick, 24 JPY} = 6.  If any cell clears the
  bar, a k-plateau is required (the neighbouring k must not decay below 50 %
  of the selected cell's difference), and the number of passing cells is
  reported against the chance expectation for 6 tries.  If none clears, this
  is a rejection report, and section 10 of the research protocol decides
  whether the death is at MECHANISM level or only at POINT level.

RUN ONCE.  REPORT AS IS.

DIAGNOSTICS THE TASK REQUIRES (they are readings, never promotions)
  1. the reality of the scale: the M24 series, wall frequency per k and side,
     wall size and wall distance distributions, and how many times matilda's
     ORIGINAL absolute rule (>= 1 BTC, 2 JPY in front) would have fired
  2. the 6-cell verdict table
  3. the decomposition of the difference into capture and adverse, and the
     contribution of the Q = 0 queue advantage
  4. the 30 s horizon
  5. a direct test of the mechanism's premise: how much of the flow that
     reaches a wall the wall actually absorbs, and how often the wall is
     simply pulled
  6. sanity: zero look-ahead, nesting, gap accounting, epoch cross-check,
     determinism, the receive-time margin
  7. limits

Offline only -- reads files, opens no sockets, places no orders.
seed 20260828.

Usage: PYTHONPATH=src python scripts/research_wall_front.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# ---- structural reuse of the calibration's implementation -----------------
from research_board_calibration import (          # noqa: E402
    epoch_seconds, epoch_seconds_alt, span_touches_gap,
    next_greater, next_smaller, boot_ci, boot_diff_ci, fmt_pct,
    header, sub, GAP_SEC, W, default_tape_dir,
)

SEED = 20260828
K_FAMILY = (10, 30, 100)
OFFSETS = ((1.0, "1 tick"), (24.0, "24 JPY"))
PRIMARY_OFFSET = 1.0
TICK = 1.0                       # FX_BTC_JPY price increment, JPY
LIFE = 10.0                      # s, the calibration's frozen quote life
MARKOUT = 5.0                    # s, the bar's horizon
MARKOUT2 = 30.0                  # s, secondary horizon
SPAN_MAX = LIFE + MARKOUT2       # the measurement span that must be gap-free
RTS_MARGIN = 1.0                 # s, receive-time conservatism
BAR_BPS = 2.0
BAR_T = 2.0
BAR_N = 100
MEASURE_START = "2026-08-21T00:00:00Z"    # day 1 is M24 burn-in
M24_WINDOW = 86400.0
MATILDA_WALL_BTC = 1.0           # the original absolute rule, diagnostic only
MATILDA_OFFSET_JPY = 2.0
NLEV = 5


# --------------------------------------------------------------------------
def load_board(data_dir: Path):
    paths = sorted(data_dir.glob("board_top5_*.csv.gz"))
    if not paths:
        raise SystemExit(f"no board_top5 files under {data_dir}")
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    t = epoch_seconds(df["ts"])
    dev = float(np.max(np.abs(t - epoch_seconds_alt(df["ts"]))))
    print(f"epoch cross-check   : board max |a-b| = {dev:.9f} s (must be ~0)")
    o = np.argsort(t, kind="stable")
    t, df = t[o], df.iloc[o].reset_index(drop=True)

    bpx = np.column_stack([df[f"bid_px_{i}"].to_numpy(float) for i in range(1, NLEV + 1)])
    bsz = np.column_stack([df[f"bid_sz_{i}"].to_numpy(float) for i in range(1, NLEV + 1)])
    apx = np.column_stack([df[f"ask_px_{i}"].to_numpy(float) for i in range(1, NLEV + 1)])
    asz = np.column_stack([df[f"ask_sz_{i}"].to_numpy(float) for i in range(1, NLEV + 1)])

    ok = (np.isfinite(bpx).all(1) & np.isfinite(apx).all(1)
          & np.isfinite(bsz).all(1) & np.isfinite(asz).all(1)
          & (apx[:, 0] > bpx[:, 0]) & (bpx[:, 0] > 0)
          & (np.diff(bpx, axis=1) < 0).all(1)       # strictly decreasing bids
          & (np.diff(apx, axis=1) > 0).all(1))      # strictly increasing asks
    n_bad = int((~ok).sum())
    t, bpx, bsz, apx, asz = t[ok], bpx[ok], bsz[ok], apx[ok], asz[ok]
    mid = 0.5 * (bpx[:, 0] + apx[:, 0])
    print(f"board rows          : {len(t):,} kept, {n_bad:,} dropped "
          f"(crossed / non-monotone / non-finite)")
    print(f"board span          : {pd.Timestamp(t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t[-1], unit='s', tz='UTC')} "
          f"({(t[-1] - t[0]) / 86400:.3f} d wall clock)")
    return t, bpx, bsz, apx, asz, mid


def load_exec(data_dir: Path):
    paths = sorted(data_dir.glob("executions_*.csv.gz"))
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    t = epoch_seconds(df["ts"])
    dev = float(np.max(np.abs(t - epoch_seconds_alt(df["ts"]))))
    print(f"epoch cross-check   : exec  max |a-b| = {dev:.9f} s (must be ~0)")
    o = np.argsort(t, kind="stable")
    t = t[o]
    px = df["price"].to_numpy(float)[o]
    sz = df["size"].to_numpy(float)[o]
    buy = (df["side"].to_numpy()[o] == "BUY")
    print(f"exec prints         : {len(px):,} "
          f"({int(buy.sum()):,} taker-BUY / {int((~buy).sum()):,} taker-SELL)")
    return t, px, sz, buy


def silence_gaps(t: np.ndarray, label: str):
    d = np.diff(t)
    k = np.flatnonzero(d > GAP_SEC)
    gs, ge = t[k], t[k + 1]
    lost = float((ge - gs).sum())
    print(f"{label:<20}: {len(gs)} silences > {GAP_SEC:.0f}s, "
          f"{lost / 3600:.2f} h ({100 * lost / (t[-1] - t[0]):.2f}% of span)")
    if len(gs):
        for i in np.argsort(ge - gs)[::-1][:3]:
            print(f"    largest: {pd.Timestamp(gs[i], unit='s', tz='UTC')} .. "
                  f"{pd.Timestamp(ge[i], unit='s', tz='UTC')} "
                  f"({(ge[i] - gs[i]) / 3600:.2f} h)")
    return gs, ge


def union_gaps(gs_list, ge_list):
    gs = np.concatenate(gs_list)
    ge = np.concatenate(ge_list)
    o = np.argsort(gs)
    gs, ge = gs[o], ge[o]
    out_s, out_e = [], []
    for s, e in zip(gs, ge):
        if out_s and s <= out_e[-1]:
            out_e[-1] = max(out_e[-1], e)
        else:
            out_s.append(s)
            out_e.append(e)
    return np.asarray(out_s), np.asarray(out_e)


# --------------------------------------------------------------------------
# fill scan -- clause for clause the calibration's inner loop
# --------------------------------------------------------------------------
def scan_fills(t0, P, Q, is_bid, t_ex, px, sz, buy, life=LIFE,
               margin=RTS_MARGIN):
    """Return (t_at, t_thr, t_qvol) per quote; inf where the event never
    happens inside (t0+margin, t0+life].  Mirrors research_board_calibration
    .place_quotes: at-or-through mask, strictly-through mask, cumulative
    at-or-through volume against Q."""
    n = len(t0)
    t_at = np.full(n, np.inf)
    t_thr = np.full(n, np.inf)
    t_qvol = np.full(n, np.inf)
    lo_all = np.searchsorted(t_ex, t0 + margin, "right")
    hi_all = np.searchsorted(t_ex, t0 + life, "right")
    for i in range(n):
        lo, hi = lo_all[i], hi_all[i]
        if hi <= lo:
            continue
        tt_s, p_s, z_s, b_s = t_ex[lo:hi], px[lo:hi], sz[lo:hi], buy[lo:hi]
        Pi = P[i]
        if is_bid[i]:
            m_at = (~b_s) & (p_s <= Pi)
            m_thr = (~b_s) & (p_s < Pi)
        else:
            m_at = b_s & (p_s >= Pi)
            m_thr = b_s & (p_s > Pi)
        if m_at.any():
            t_at[i] = tt_s[int(np.argmax(m_at))]
            cv = np.cumsum(np.where(m_at, z_s, 0.0))
            # the fill must happen ON an at-or-through print.  With Q > 0 this
            # is automatic (cv only steps up on such prints); with Q = 0 -- the
            # wall-front case the pre-registration names, where we are the
            # front of the queue -- it is what stops cv >= 0 from "filling" us
            # on an unrelated same-side print.
            hit = np.flatnonzero(m_at & (cv >= Q[i]))
            if hit.size:
                t_qvol[i] = tt_s[hit[0]]
        if m_thr.any():
            t_thr[i] = tt_s[int(np.argmax(m_thr))]
    return t_at, t_thr, t_qvol


def fill_time(t_at, t_thr, t_qvol, t0, cancel, model, policy, life=LIFE):
    end = np.minimum(t0 + life, cancel if policy == "C1" else np.inf)
    if model == "optimistic":
        ft = t_at
    elif model == "conservative":
        ft = t_thr
    elif model == "queue":
        ft = np.minimum(t_qvol, t_thr)
    elif model == "queue_volonly":
        ft = t_qvol
    else:
        raise ValueError(model)
    return np.where(ft <= end, ft, np.inf)


def markout(ft, price, sign, tb, mid, horizon):
    """capture / adverse(horizon) in bps for the quotes that filled."""
    idx = np.flatnonzero(np.isfinite(ft))
    tf = ft[idx]
    i0 = np.searchsorted(tb, tf, "left") - 1        # strictly before the fill
    i1 = np.searchsorted(tb, tf + horizon, "right") - 1
    good = (i0 >= 0) & (i1 >= 0)
    idx, i0, i1 = idx[good], i0[good], i1[good]
    m0, mh = mid[i0], mid[i1]
    s = sign[idx]
    capture = s * (m0 - price[idx]) / m0 * 1e4
    adverse = s * (mh - m0) / m0 * 1e4
    return idx, capture, adverse


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(default_tape_dir()))
    args = ap.parse_args()
    np.seterr(all="ignore")

    header("WALL-FRONT LIMIT ORDER -- PRE-REGISTERED VERDICT (single run)")
    print("Execution option, not a strategy.  Bar (frozen 2026-08-21): "
          f"fill-conditional\ncapture+adverse(5s) difference >= {BAR_BPS:+.1f} bps, "
          f"day-clustered t >= {BAR_T}, >= {BAR_N} fills per arm.")
    print(f"seed {SEED}, no network, read-only.")
    print(f"[data] tape dir: {args.data}\n")

    data_dir = Path(args.data)
    tb, bpx, bsz, apx, asz, mid = load_board(data_dir)
    t_ex, px, sz, buy = load_exec(data_dir)

    gsb, geb = silence_gaps(tb, "board gaps")
    gse, gee = silence_gaps(t_ex, "exec gaps")
    gs, ge = union_gaps([gsb, gse], [geb, gee])
    print(f"union gap set       : {len(gs)} intervals, "
          f"{float((ge - gs).sum()) / 3600:.2f} h")

    # ---- grid ------------------------------------------------------------
    t_start = epoch_seconds(pd.Series([MEASURE_START]))[0]
    k0 = int(np.floor(tb[0] / W))
    k1 = int(np.floor(tb[-1] / W))
    grid = (np.arange(k1 - k0 + 1) + k0) * float(W)
    n_grid_all = len(grid)
    ip = np.searchsorted(tb, grid, "right") - 1          # last row <= t0
    usable = (ip >= 0) & (grid >= t_start)
    n_burn = int(((ip >= 0) & (grid < t_start)).sum())
    usable &= ~span_touches_gap(grid, grid + SPAN_MAX, gs, ge)
    n_gapdrop = int(((grid >= t_start) & (ip >= 0)).sum() - usable.sum())
    stale = grid - np.where(ip >= 0, tb[np.maximum(ip, 0)], -1e18)
    usable &= stale <= GAP_SEC
    usable &= (grid + SPAN_MAX) <= min(tb[-1], t_ex[-1])
    gsel = np.flatnonzero(usable)
    ipg = ip[gsel]
    t0g = grid[gsel]
    print(f"\n30s grid            : {n_grid_all:,} points; "
          f"{n_burn:,} in the 8/20 M24 burn-in (no measured quote), "
          f"{n_gapdrop:,} discarded for a gap-touching span")
    print(f"usable grid points  : {len(gsel):,} "
          f"({len(gsel) * W / 86400:.3f} board-days at 30 s spacing)")
    day = np.floor(t0g / 86400.0).astype(np.int64)

    # ---- M24 (rolling 24 h median of the pooled best-level size) ----------
    pool = np.empty(2 * len(tb))
    pool[0::2] = bsz[:, 0]
    pool[1::2] = asz[:, 0]
    lo24 = np.searchsorted(tb, t0g - M24_WINDOW, "left")
    hi24 = np.searchsorted(tb, t0g, "left")              # strictly before t0
    m24 = np.empty(len(gsel))
    n24 = np.empty(len(gsel), np.int64)
    for i in range(len(gsel)):
        a, b = 2 * lo24[i], 2 * hi24[i]
        n24[i] = b - a
        m24[i] = np.median(pool[a:b]) if b > a else np.nan
    ok24 = np.isfinite(m24) & (n24 >= 2 * 3600)          # >= 1 h of history
    print(f"M24 available       : {int(ok24.sum()):,} of {len(gsel):,} grid "
          f"points (needs >= 1 h of trailing board rows)")

    # =====================================================================
    header("1. THE REALITY OF THE SCALE (the owner's point, quantified)")
    # =====================================================================
    sub("1a. M24 -- rolling 24 h median of the best-level size, both sides")
    print(f"{'UTC day':<12}{'n grid':>9}{'M24 min':>10}{'M24 med':>10}"
          f"{'M24 max':>10}   thresholds k*M24 (BTC), median of the day")
    for d in np.unique(day[ok24]):
        s = ok24 & (day == d)
        v = m24[s]
        med = float(np.median(v))
        print(f"{str(pd.Timestamp(d * 86400.0, unit='s', tz='UTC').date()):<12}"
              f"{int(s.sum()):>9,}{v.min():>10.4f}{med:>10.4f}{v.max():>10.4f}"
              f"   k=10 {10 * med:6.3f}  k=30 {30 * med:6.3f}  "
              f"k=100 {100 * med:6.3f}")
    print(f"\nwhole record: M24 median {np.median(m24[ok24]):.4f} BTC "
          f"(report aa measured the best-level median at 0.0182 BTC on the "
          f"ticker record)")
    print(f"best-level size now: bid median {np.median(bsz[:, 0]):.4f}, "
          f"ask median {np.median(asz[:, 0]):.4f} BTC; "
          f"top-5 level median {np.median(np.r_[bsz.ravel(), asz.ravel()]):.4f}")

    # wall detection at every usable grid point, per k, per side
    b_px_g, b_sz_g = bpx[ipg], bsz[ipg]
    a_px_g, a_sz_g = apx[ipg], asz[ipg]
    mid_g = mid[ipg]

    walls = {}       # (k, side) -> dict(has, lev, wpx, wsz)
    for k in K_FAMILY:
        thr = k * m24
        for side, szg, pxg in ((0, b_sz_g, b_px_g), (1, a_sz_g, a_px_g)):
            hit = szg >= thr[:, None]
            hit &= ok24[:, None]
            has = hit.any(1)
            lev = np.where(has, hit.argmax(1), -1)       # nearest to the best
            rows = np.arange(len(gsel))
            wpx = np.where(has, pxg[rows, np.maximum(lev, 0)], np.nan)
            wsz = np.where(has, szg[rows, np.maximum(lev, 0)], np.nan)
            walls[(k, side)] = dict(has=has, lev=lev, wpx=wpx, wsz=wsz)

    sub("1b. how often is there a wall at all?  (share of usable grid points)")
    print(f"{'k':>5}{'thr med BTC':>13}{'bid side':>11}{'ask side':>11}"
          f"{'either':>10}{'n bid':>9}{'n ask':>9}")
    for k in K_FAMILY:
        hb = walls[(k, 0)]["has"]
        ha = walls[(k, 1)]["has"]
        print(f"{k:>5}{k * np.median(m24[ok24]):>13.3f}"
              f"{fmt_pct(hb[ok24].mean()):>11}{fmt_pct(ha[ok24].mean()):>11}"
              f"{fmt_pct((hb | ha)[ok24].mean()):>10}"
              f"{int(hb.sum()):>9,}{int(ha.sum()):>9,}")
    print("  (a grid point can have a wall on both sides; the two sides are "
          "separate\n   quote populations.)")

    sub("1c. wall size and wall distance from the best")
    print(f"{'k':>5}{'side':<6}{'n':>8}{'size p50':>10}{'size p90':>10}"
          f"{'size max':>10}{'size/M24 p50':>14}"
          f"{'lvl 1/2/3/4/5 share':>34}{'dist bps p50':>14}")
    for k in K_FAMILY:
        for side, nm in ((0, "bid"), (1, "ask")):
            wl = walls[(k, side)]
            s = wl["has"]
            if s.sum() == 0:
                print(f"{k:>5}{nm:<6}{0:>8}   -- no wall ever detected --")
                continue
            wsz = wl["wsz"][s]
            lev = wl["lev"][s]
            dist = np.abs(wl["wpx"][s] - (b_px_g[:, 0] if side == 0
                                          else a_px_g[:, 0])[s]) / mid_g[s] * 1e4
            shares = " ".join(f"{100 * (lev == j).mean():5.1f}" for j in range(NLEV))
            print(f"{k:>5}{nm:<6}{int(s.sum()):>8,}{np.percentile(wsz, 50):>10.3f}"
                  f"{np.percentile(wsz, 90):>10.3f}{wsz.max():>10.3f}"
                  f"{np.percentile(wsz / m24[s], 50):>14.1f}"
                  f"{shares:>34}{np.percentile(dist, 50):>14.2f}")
    print("  dist = |wall price - best on that side| in bps of mid; level 1 "
          "means the\n  wall IS the best, in which case 'in front' is inside "
          "the spread.")

    sub("1d. matilda's ORIGINAL absolute rule as a diagnostic "
        f"(wall >= {MATILDA_WALL_BTC} BTC, {MATILDA_OFFSET_JPY:.0f} JPY in front)")
    m_hit_b = (b_sz_g >= MATILDA_WALL_BTC).any(1)
    m_hit_a = (a_sz_g >= MATILDA_WALL_BTC).any(1)
    print(f"  grid points with a >= {MATILDA_WALL_BTC} BTC level in top-5: "
          f"bid {int(m_hit_b.sum()):,}  ask {int(m_hit_a.sum()):,}  "
          f"of {len(gsel):,} ({fmt_pct((m_hit_b | m_hit_a).mean())} either side)")
    allsz = np.r_[bsz.ravel(), asz.ravel()]
    print(f"  any top-5 level >= {MATILDA_WALL_BTC} BTC anywhere in the record: "
          f"{int((allsz >= MATILDA_WALL_BTC).sum()):,} of {allsz.size:,} "
          f"level observations ({100 * (allsz >= MATILDA_WALL_BTC).mean():.4f}%)")
    print(f"  largest single top-5 level in the record: {allsz.max():.3f} BTC; "
          f"p99.9 {np.percentile(allsz, 99.9):.3f}; p99 "
          f"{np.percentile(allsz, 99):.3f}")
    px_med = float(np.median(mid))
    print(f"  matilda's {MATILDA_OFFSET_JPY:.0f} JPY offset at today's price "
          f"({px_med:,.0f} JPY) = {MATILDA_OFFSET_JPY / px_med * 1e4:.4f} bps; "
          f"in 2020 (1,000,000 JPY) it was "
          f"{MATILDA_OFFSET_JPY / 1e6 * 1e4:.2f} bps.")
    print(f"  the 24 JPY sensitivity offset = {24.0 / px_med * 1e4:.3f} bps "
          f"today; the 1 tick offset = {1.0 / px_med * 1e4:.4f} bps.")

    # =====================================================================
    # build the quote populations
    # =====================================================================
    next_up = next_greater(bpx[:, 0])
    next_dn = next_smaller(apx[:, 0])
    tb_inf = np.r_[tb, np.inf]
    cancel_bid = tb_inf[next_up[ipg]]
    cancel_ask = tb_inf[next_dn[ipg]]

    def build(k, offset):
        """Return the paired (wall-front, control) quote arrays for cell
        (k, offset), both sides stacked.  Every field is PER QUOTE."""
        cols = {n: [] for n in ("t0", "P", "Q", "sign", "cancel", "day",
                                "side", "arm", "lev", "inside", "pair")}
        n_marketable = 0
        rows = np.arange(len(gsel))
        pair0 = 0
        for side in (0, 1):
            wl = walls[(k, side)]
            sgn = 1.0 if side == 0 else -1.0
            P_all = wl["wpx"] + sgn * offset
            best_own = (b_px_g[:, 0] if side == 0 else a_px_g[:, 0])
            best_opp = (a_px_g[:, 0] if side == 0 else b_px_g[:, 0])
            legal = (P_all < best_opp) if side == 0 else (P_all > best_opp)
            n_marketable += int((wl["has"] & ~legal).sum())
            idx = rows[wl["has"] & legal]
            if idx.size == 0:
                continue
            own_px = (b_px_g if side == 0 else a_px_g)[idx]
            own_sz = (b_sz_g if side == 0 else a_sz_g)[idx]
            P = P_all[idx]
            match = own_px == P[:, None]
            Qw = np.where(match.any(1),
                          own_sz[np.arange(len(idx)), match.argmax(1)], 0.0)
            cx = (cancel_bid if side == 0 else cancel_ask)[idx]
            lev = wl["lev"][idx]
            inside = (P > best_own[idx]) if side == 0 else (P < best_own[idx])
            pair = pair0 + np.arange(len(idx))
            pair0 += len(idx)
            for arm, pr, qq in (("wall", P, Qw),
                                ("touch", best_own[idx], own_sz[:, 0])):
                cols["t0"].append(t0g[idx])
                cols["P"].append(pr)
                cols["Q"].append(qq)
                cols["sign"].append(np.full(len(idx), sgn))
                cols["cancel"].append(cx)
                cols["day"].append(day[idx])
                cols["side"].append(np.full(len(idx), side, np.int8))
                cols["arm"].append(np.full(len(idx), arm, dtype=object))
                cols["lev"].append(lev)
                cols["inside"].append(inside)
                cols["pair"].append(pair)
        if not cols["t0"]:
            return None
        out = {n: np.concatenate(v) for n, v in cols.items()}
        out["n_marketable"] = n_marketable
        out["is_bid"] = out["side"] == 0
        return out

    cells = {}
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            c = build(k, off)
            if c is None:
                cells[(k, off)] = None
                continue
            t_at, t_thr, t_qvol = scan_fills(c["t0"], c["P"], c["Q"],
                                             c["is_bid"], t_ex, px, sz, buy)
            c["t_at"], c["t_thr"], c["t_qvol"] = t_at, t_thr, t_qvol
            cells[(k, off)] = c

    # =====================================================================
    header("SANITY -- FILL-MODEL NESTING (asserted before any number is read)")
    # =====================================================================
    viol = 0
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            c = cells[(k, off)]
            if c is None:
                print(f"  k={k:<4} {oname:<8}: no quotes")
                continue
            for pol in ("C0", "C1"):
                fo = np.isfinite(fill_time(c["t_at"], c["t_thr"], c["t_qvol"],
                                           c["t0"], c["cancel"], "optimistic", pol))
                fq = np.isfinite(fill_time(c["t_at"], c["t_thr"], c["t_qvol"],
                                           c["t0"], c["cancel"], "queue", pol))
                fc = np.isfinite(fill_time(c["t_at"], c["t_thr"], c["t_qvol"],
                                           c["t0"], c["cancel"], "conservative", pol))
                v1 = int((fc & ~fq).sum())
                v2 = int((fq & ~fo).sum())
                viol += v1 + v2
                print(f"  k={k:<4} {oname:<8} {pol}: cons {int(fc.sum()):>6,} "
                      f"<= queue {int(fq.sum()):>6,} <= opt {int(fo.sum()):>6,}"
                      f"   violations {v1}/{v2}")
    assert viol == 0, "fill-model nesting violated -- results not read"
    print("  nesting OK on every (cell x policy) combination")

    # =====================================================================
    header("2. THE SIX-CELL VERDICT TABLE (primary: queue-realistic, C1, "
           "L=10s, markout 5s)")
    # =====================================================================
    print(f"bar: diff >= {BAR_BPS:+.1f} bps AND day-clustered t >= {BAR_T} "
          f"AND >= {BAR_N} fills per arm\n")
    print(f"{'k':>4} {'offset':<8}{'arm':<7}{'placed':>8}{'fills':>7}{'f':>8}"
          f"{'capture':>9}{'adv5s':>9}{'cap+adv':>9}"
          f"{'diff':>8}{'95% CI (diff)':>21}{'t':>7}  verdict")
    verdicts = {}
    detail = {}
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            c = cells[(k, off)]
            if c is None:
                print(f"{k:>4} {oname:<8}  -- no quote could be placed --")
                verdicts[(k, off)] = None
                continue
            ft = fill_time(c["t_at"], c["t_thr"], c["t_qvol"], c["t0"],
                           c["cancel"], "queue", "C1")
            res = {}
            for arm in ("wall", "touch"):
                m = c["arm"] == arm
                ftm = np.where(m, ft, np.inf)
                idx, cap, adv = markout(ftm, c["P"], c["sign"], tb, mid, MARKOUT)
                res[arm] = (int(m.sum()), idx, cap, adv,
                            float(np.isfinite(ft)[m].mean()))
            nw, iw, capw, advw, fw = res["wall"]
            nt, it_, capt, advt, fto = res["touch"]
            netw, nett = capw + advw, capt + advt
            if len(netw) >= 2 and len(nett) >= 2:
                diff = netw.mean() - nett.mean()
                lo, hi, tst = boot_diff_ci(netw, c["day"][iw], nett,
                                           c["day"][it_], seed=SEED)
            else:
                diff = lo = hi = tst = np.nan
            passes = (np.isfinite(diff) and diff >= BAR_BPS and tst >= BAR_T
                      and len(netw) >= BAR_N and len(nett) >= BAR_N)
            verdicts[(k, off)] = dict(diff=diff, t=tst, lo=lo, hi=hi,
                                      nw=len(netw), nt=len(nett), passes=passes)
            detail[(k, off)] = dict(capw=capw, advw=advw, capt=capt, advt=advt,
                                    iw=iw, it=it_, c=c, ft=ft)
            for arm, (nq, idx, cap, adv, fv) in (("wall", res["wall"]),
                                                 ("touch", res["touch"])):
                net = cap + adv
                is_w = arm == "wall"
                extra = (f"{diff:>8.3f}  [{lo:+7.3f},{hi:+7.3f}]{tst:>7.2f}  "
                         f"{'PASS' if passes else 'FAIL'}") if is_w else ""
                print(f"{k if is_w else '':>4} {oname if is_w else '':<8}"
                      f"{arm:<7}{nq:>8,}{len(net):>7,}{fmt_pct(fv):>8}"
                      f"{cap.mean():>9.3f}{adv.mean():>9.3f}{net.mean():>9.3f}"
                      f"{extra}")
            mw_ = c["arm"] == "wall"
            print(f"{'':>4} {'':<8}{'':<7}  (dropped as marketable: "
                  f"{c['n_marketable']:,} placements; wall-front price inside "
                  f"the spread: {fmt_pct(c['inside'][mw_].mean())})")
    n_pass = sum(1 for v in verdicts.values() if v and v["passes"])
    print(f"\ncells examined: 6.  cells clearing the bar: {n_pass}.")
    print("chance expectation for the t>=2.0 leg alone (one-sided, 6 tries): "
          "6 x 0.023 = 0.14 cells.")

    # =====================================================================
    header("3. DECOMPOSITION -- is the difference in capture or in adverse?")
    # =====================================================================
    print(f"{'k':>4} {'offset':<8}{'d capture':>11}{'d adv(5s)':>11}"
          f"{'d cap+adv':>11}{'CI(d capture)':>22}{'CI(d adv)':>22}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            d = detail.get((k, off))
            if d is None:
                continue
            c = d["c"]
            dc = d["capw"].mean() - d["capt"].mean()
            da = d["advw"].mean() - d["advt"].mean()
            lc, hc, _ = boot_diff_ci(d["capw"], c["day"][d["iw"]],
                                     d["capt"], c["day"][d["it"]], seed=SEED)
            la, ha, _ = boot_diff_ci(d["advw"], c["day"][d["iw"]],
                                     d["advt"], c["day"][d["it"]], seed=SEED)
            print(f"{k:>4} {oname:<8}{dc:>11.3f}{da:>11.3f}"
                  f"{dc + da:>11.3f}  [{lc:+8.3f},{hc:+8.3f}]"
                  f"  [{la:+8.3f},{ha:+8.3f}]")

    sub("3b. the queue advantage -- how often is the wall-front quote at the "
        "FRONT (Q = 0)?")
    print(f"{'k':>4} {'offset':<8}{'arm':<7}{'Q=0 share':>11}{'Q p50':>9}"
          f"{'Q p90':>9}{'f | Q=0':>10}{'f | Q>0':>10}"
          f"{'cap+adv | Q=0':>15}{'cap+adv | Q>0':>15}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            d = detail.get((k, off))
            if d is None:
                continue
            c, ft = d["c"], d["ft"]
            filled = np.isfinite(ft)
            for arm in ("wall", "touch"):
                m = c["arm"] == arm
                q0 = m & (c["Q"] <= 0)
                qp = m & (c["Q"] > 0)
                ftm = np.where(m, ft, np.inf)
                idx, cap, adv = markout(ftm, c["P"], c["sign"], tb, mid, MARKOUT)
                net = cap + adv
                sel0 = (c["Q"][idx] <= 0)
                n0 = net[sel0].mean() if sel0.any() else np.nan
                n1 = net[~sel0].mean() if (~sel0).any() else np.nan
                print(f"{k if arm == 'wall' else '':>4} "
                      f"{oname if arm == 'wall' else '':<8}{arm:<7}"
                      f"{fmt_pct(q0.sum() / max(m.sum(), 1)):>11}"
                      f"{np.percentile(c['Q'][m], 50):>9.4f}"
                      f"{np.percentile(c['Q'][m], 90):>9.4f}"
                      f"{fmt_pct(filled[q0].mean() if q0.any() else np.nan):>10}"
                      f"{fmt_pct(filled[qp].mean() if qp.any() else np.nan):>10}"
                      f"{n0:>15.3f}{n1:>15.3f}")

    sub("3c. by wall level (is the effect different when the wall IS the best?)")
    print(f"{'k':>4} {'offset':<8}{'lvl':>4}{'pairs':>8}"
          f"{'wall f':>8}{'touch f':>9}{'wall net':>10}{'touch net':>11}"
          f"{'diff':>9}{'n fill w/t':>13}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            d = detail.get((k, off))
            if d is None:
                continue
            c, ft = d["c"], d["ft"]
            filled = np.isfinite(ft)
            idx, cap, adv = markout(ft, c["P"], c["sign"], tb, mid, MARKOUT)
            net = cap + adv
            for lv in range(NLEV):
                mw = (c["arm"] == "wall") & (c["lev"] == lv)
                mt = (c["arm"] == "touch") & (c["lev"] == lv)
                if mw.sum() == 0:
                    continue
                sw, st = mw[idx], mt[idx]
                nw_ = net[sw].mean() if sw.any() else np.nan
                nt_ = net[st].mean() if st.any() else np.nan
                print(f"{k:>4} {oname:<8}{lv + 1:>4}{int(mw.sum()):>8,}"
                      f"{fmt_pct(filled[mw].mean()):>8}"
                      f"{fmt_pct(filled[mt].mean()):>9}"
                      f"{nw_:>10.3f}{nt_:>11.3f}{nw_ - nt_:>9.3f}"
                      f"{int(sw.sum()):>7,}/{int(st.sum()):<5,}")

    # =====================================================================
    header("4. HORIZON SENSITIVITY -- 5 s is the bar, 30 s is a reading")
    # =====================================================================
    print(f"{'k':>4} {'offset':<8}{'horizon':>9}{'wall net':>10}"
          f"{'touch net':>11}{'diff':>9}{'95% CI':>21}{'t':>7}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            d = detail.get((k, off))
            if d is None:
                continue
            c, ft = d["c"], d["ft"]
            for h in (MARKOUT, MARKOUT2):
                idx, cap, adv = markout(ft, c["P"], c["sign"], tb, mid, h)
                net = cap + adv
                sw = (c["arm"] == "wall")[idx]
                st = (c["arm"] == "touch")[idx]
                if sw.sum() < 2 or st.sum() < 2:
                    continue
                diff = net[sw].mean() - net[st].mean()
                lo, hi, tst = boot_diff_ci(net[sw], c["day"][idx][sw],
                                           net[st], c["day"][idx][st], seed=SEED)
                print(f"{k:>4} {oname:<8}{h:>8.0f}s{net[sw].mean():>10.3f}"
                      f"{net[st].mean():>11.3f}{diff:>9.3f}"
                      f"  [{lo:+8.3f},{hi:+8.3f}]{tst:>7.2f}")

    # =====================================================================
    header("5. DOES THE WALL ACTUALLY ABSORB?  (the mechanism's premise)")
    # =====================================================================
    print("For every grid point with a wall, over the next 10 s (the quote "
          "life),\nmeasured on prints strictly after t0 + "
          f"{RTS_MARGIN:.0f} s:")
    print(f"{'k':>4}{'side':<6}{'n walls':>9}{'reached':>9}{'through':>9}"
          f"{'absorbed':>10}{'vol@wall/size p50':>19}{'absorb frac':>13}"
          f"{'pulled':>9}{'traded away':>13}{'survives':>10}")
    for k in K_FAMILY:
        for side, nm in ((0, "bid"), (1, "ask")):
            wl = walls[(k, side)]
            s = np.flatnonzero(wl["has"])
            if s.size == 0:
                print(f"{k:>4}{nm:<6}{0:>9}   -- no wall ever detected --")
                continue
            t0w = t0g[s]
            Wp = wl["wpx"][s]
            Ws = wl["wsz"][s]
            lo_all = np.searchsorted(t_ex, t0w + RTS_MARGIN, "right")
            hi_all = np.searchsorted(t_ex, t0w + LIFE, "right")
            v_at = np.zeros(len(s))
            v_thr = np.zeros(len(s))
            for i in range(len(s)):
                lo, hi = lo_all[i], hi_all[i]
                if hi <= lo:
                    continue
                p_s, z_s, b_s = px[lo:hi], sz[lo:hi], buy[lo:hi]
                if side == 0:
                    m_at = (~b_s) & (p_s <= Wp[i])
                    m_thr = (~b_s) & (p_s < Wp[i])
                else:
                    m_at = b_s & (p_s >= Wp[i])
                    m_thr = b_s & (p_s > Wp[i])
                v_at[i] = float(z_s[m_at].sum())
                v_thr[i] = float(z_s[m_thr].sum())
            reached = v_at > 0
            through = v_thr > 0
            absorbed = reached & ~through
            frac = np.where(v_at > 0, 1.0 - v_thr / np.maximum(v_at, 1e-12),
                            np.nan)
            # wall fate at t0 + LIFE
            jp = np.searchsorted(tb, t0w + LIFE, "right") - 1
            pxs = (bpx if side == 0 else apx)[jp]
            szs = (bsz if side == 0 else asz)[jp]
            match = pxs == Wp[:, None]
            still_sz = np.where(match.any(1),
                                szs[np.arange(len(s)), match.argmax(1)], 0.0)
            drop = Ws - still_sz
            survives = still_sz >= k * m24[s]
            gone = ~survives
            traded_away = gone & (drop > 0) & (v_at >= 0.5 * drop)
            pulled = gone & ~traded_away
            ratio = (float(np.percentile(v_at[reached] / Ws[reached], 50))
                     if reached.any() else float("nan"))
            afrac = (float(np.nanmean(frac[reached])) if reached.any()
                     else float("nan"))
            print(f"{k:>4}{nm:<6}{len(s):>9,}{fmt_pct(reached.mean()):>9}"
                  f"{fmt_pct(through.mean()):>9}{fmt_pct(absorbed.mean()):>10}"
                  f"{ratio:>19.3f}{afrac:>13.3f}"
                  f"{fmt_pct(pulled.mean()):>9}"
                  f"{fmt_pct(traded_away.mean()):>13}"
                  f"{fmt_pct(survives.mean()):>10}")
    print("  reached  = some opposite-side taker volume printed at or through "
          "the wall\n  through  = some volume printed strictly THROUGH it "
          "(the wall did not hold)\n  absorbed = flow arrived and none of it "
          "got through\n  absorb frac = mean 1 - vol_through / vol_at_or_"
          "through, over reached walls\n  pulled   = wall no longer >= k*M24 "
          "10 s later WITHOUT the trades to explain it")

    # =====================================================================
    header("6. SANITY")
    # =====================================================================
    sub("6a. determinism, look-ahead, margin, gaps")
    print(f"  epoch cross-check     : printed at load, board and exec, ~0 s")
    print(f"  look-ahead            : M24 uses board rows with ts STRICTLY < "
          f"t0;\n                          wall / prices / Q use the last "
          f"board row <= t0;\n                          fills use prints "
          f"strictly after t0 + {RTS_MARGIN:.0f}s;\n"
          f"                          markout mids come from the board's own "
          f"best,\n                          m0 = last row strictly before "
          f"the fill print")
    print(f"  receive-time margin   : {RTS_MARGIN:.1f} s, applied identically "
          f"to both arms")
    print(f"  nesting               : asserted above, 0 violations")
    print(f"  gap discipline        : union of board and exec silence > "
          f"{GAP_SEC:.0f}s;\n                          {len(gs)} intervals, "
          f"{float((ge - gs).sum()) / 3600:.2f} h; "
          f"{n_gapdrop:,} grid points discarded")
    print(f"  burn-in               : {n_burn:,} grid points before "
          f"{MEASURE_START} carry no quote")
    print(f"  seed                  : {SEED}; bootstraps seeded; no network; "
          f"no RNG elsewhere")

    sub("6b. margin sensitivity -- the same primary cells with margin 0 s")
    print(f"{'k':>4} {'offset':<8}{'wall f':>8}{'touch f':>9}{'wall net':>10}"
          f"{'touch net':>11}{'diff':>9}{'t':>7}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            c = cells[(k, off)]
            if c is None:
                continue
            t_at0, t_thr0, t_qvol0 = scan_fills(c["t0"], c["P"], c["Q"],
                                                c["is_bid"], t_ex, px, sz, buy,
                                                margin=0.0)
            ft0 = fill_time(t_at0, t_thr0, t_qvol0, c["t0"], c["cancel"],
                            "queue", "C1")
            idx, cap, adv = markout(ft0, c["P"], c["sign"], tb, mid, MARKOUT)
            net = cap + adv
            sw = (c["arm"] == "wall")[idx]
            st = (c["arm"] == "touch")[idx]
            if sw.sum() < 2 or st.sum() < 2:
                continue
            fl = np.isfinite(ft0)
            _, _, tst = boot_diff_ci(net[sw], c["day"][idx][sw], net[st],
                                     c["day"][idx][st], seed=SEED)
            print(f"{k:>4} {oname:<8}"
                  f"{fmt_pct(fl[c['arm'] == 'wall'].mean()):>8}"
                  f"{fmt_pct(fl[c['arm'] == 'touch'].mean()):>9}"
                  f"{net[sw].mean():>10.3f}{net[st].mean():>11.3f}"
                  f"{net[sw].mean() - net[st].mean():>9.3f}{tst:>7.2f}")

    sub("6c. cancel-policy bracket -- C0 (no cancel) on the primary offset")
    print(f"{'k':>4} {'offset':<8}{'policy':<7}{'wall f':>8}{'touch f':>9}"
          f"{'wall net':>10}{'touch net':>11}{'diff':>9}{'t':>7}")
    for k in K_FAMILY:
        for off, oname in OFFSETS:
            c = cells[(k, off)]
            if c is None:
                continue
            for pol in ("C0", "C1"):
                ft = fill_time(c["t_at"], c["t_thr"], c["t_qvol"], c["t0"],
                               c["cancel"], "queue", pol)
                idx, cap, adv = markout(ft, c["P"], c["sign"], tb, mid, MARKOUT)
                net = cap + adv
                sw = (c["arm"] == "wall")[idx]
                st = (c["arm"] == "touch")[idx]
                if sw.sum() < 2 or st.sum() < 2:
                    continue
                fl = np.isfinite(ft)
                _, _, tst = boot_diff_ci(net[sw], c["day"][idx][sw], net[st],
                                         c["day"][idx][st], seed=SEED)
                print(f"{k:>4} {oname:<8}{pol:<7}"
                      f"{fmt_pct(fl[c['arm'] == 'wall'].mean()):>8}"
                      f"{fmt_pct(fl[c['arm'] == 'touch'].mean()):>9}"
                      f"{net[sw].mean():>10.3f}{net[st].mean():>11.3f}"
                      f"{net[sw].mean() - net[st].mean():>9.3f}{tst:>7.2f}")

    sub("6d. control-arm cross-check against report aa")
    for k in K_FAMILY:
        c = cells[(k, PRIMARY_OFFSET)]
        if c is None:
            continue
        ft = fill_time(c["t_at"], c["t_thr"], c["t_qvol"], c["t0"],
                       c["cancel"], "queue", "C1")
        m = c["arm"] == "touch"
        idx, cap, adv = markout(np.where(m, ft, np.inf), c["P"], c["sign"],
                                tb, mid, MARKOUT)
        net = cap + adv
        lo, hi, tst = boot_ci(net, c["day"][idx], seed=SEED)
        print(f"  k={k:<4} touch arm, margin {RTS_MARGIN:.0f}s: "
              f"f {fmt_pct(np.isfinite(ft)[m].mean())}, "
              f"n {len(net):,}, capture {cap.mean():+.3f}, adv5s "
              f"{adv.mean():+.3f}, cap+adv {net.mean():+.3f} "
              f"[{lo:+.3f},{hi:+.3f}]")
        t_at0, t_thr0, t_qvol0 = scan_fills(c["t0"], c["P"], c["Q"],
                                            c["is_bid"], t_ex, px, sz, buy,
                                            margin=0.0)
        ft0 = fill_time(t_at0, t_thr0, t_qvol0, c["t0"], c["cancel"],
                        "queue", "C1")
        idx0, cap0, adv0 = markout(np.where(m, ft0, np.inf), c["P"], c["sign"],
                                   tb, mid, MARKOUT)
        print(f"  {'':<6}  touch arm, margin 0s: "
              f"f {fmt_pct(np.isfinite(ft0)[m].mean())}, n {len(cap0):,}, "
              f"capture {cap0.mean():+.3f}, adv5s {adv0.mean():+.3f}, "
              f"cap+adv {(cap0 + adv0).mean():+.3f}   <- the like-for-like "
              f"reading against aa")
    print("  report aa (whole record, touch, queue/C1/10s): f 18.1%, "
          "capture +0.604,\n  adv(5s) -1.321, cap+adv -0.716.  This study's "
          "touch arm is the SUBSET of\n  grid points that had a wall, on a 1 Hz "
          "board rather than an event-sampled\n  ticker, so exact equality is "
          "not expected -- only the same order.")

    # =====================================================================
    header("7. LIMITS")
    # =====================================================================
    print("""  * 7 board-days, one venue, one regime.  6 usable days after the
    M24 burn-in, minus the 8.1 h recorder gap.
  * TOP-5 ONLY.  A wall deeper than level 5 is invisible, so the wall
    frequencies below are lower bounds and the "no wall" grid points are not
    proof that no wall existed anywhere in the book.
  * The board is sampled at 1 Hz.  A wall that appears and is pulled inside
    one second is not seen; the fill scan uses the full print tape, so fills
    are at print resolution but the book state behind them is 1 Hz.
  * ts is local receive time.  The +/-1 s margin makes fills conservative but
    cannot repair the ordering of events inside one second.
  * The queue decrements only on trades, never on cancels ahead of us
    (conservative for both arms); our own quote adds no size, so a sweep that
    would have stopped on our size is still counted as a sweep.
  * No inventory, no round trip, no P&L: this is a per-quote execution
    reading, exactly as the pre-registration defines it.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
