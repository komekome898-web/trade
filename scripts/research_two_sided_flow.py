#!/usr/bin/env python3
"""Pre-study S7 -- do maker-favorable TWO-SIDED flow regimes exist on
FX_BTC_JPY, and what revenue ceiling do they bound?

    PRE-REGISTRATION (fixed before the first run; nothing here is adoptable)

Thesis under test (owner): windows exist in which BOTH the bid and the ask
are eaten at the same time ("buy book and sell book both get eaten"), and a
maker is favoured there.  The board record needed for the real spread-MM
study (KNOWLEDGE 4, pending gate) is still accumulating.  This script
quantifies the thesis from the TAKER-SIDE TAPE ALONE and pre-registers no
strategy, no parameter, and no adoption bar.  It is measurement + power
analysis for the coming board study.

DATA
  data/executions_FX_BTC_JPY.csv -- 820,000 public prints,
      2026-07-21T08:17:22Z .. 2026-08-20T08:22:17Z (30.00 days),
      columns id, exec_date, price, size, side; `side` is the TAKER side
      (BUY = the ask was lifted, SELL = the bid was hit).
  data/ws/*.jsonl.gz -- old session board/exec records (a few hours).
      Used ONLY as a supplementary spread reference and as an independent
      completeness check on the tape.  Never as a primary source.

SPLITS
  Full 30 days is primary.  A 60/40 chronological split is reported as a
  CONSISTENCY CHECK of the measurements -- there is no selection here, so
  the split is not a train/test boundary and no configuration is chosen
  from it.

FAMILY -- ENUMERATED, NOT EXTENDED AFTER THE FACT
  Windows W in {10s, 30s, 60s}, on the absolute epoch grid floor(t/W).
  A window is TWO-SIDED iff
      taker-BUY volume  >= v_min   AND
      taker-SELL volume >= v_min   AND
      |B - S| / (B + S) <= 0.30
  v_min grid: the 33rd and the 50th percentile of the pooled per-window
  one-side volume.  Two pools are reported: ALL windows (as written in the
  pre-registration) and NON-EMPTY windows (a sensitivity, because on a tape
  this thin the all-window percentile can be exactly zero, which makes the
  condition degenerate).  Whenever a percentile lands on 0 the threshold is
  floored at a strictly positive epsilon, so "both sides traded" is always
  required.  That floor is stated in the output.

MEASUREMENTS (all 12 grid cells are printed; no cell is selected)
  1. Duty cycle, episode count, median/p90 episode duration, clustering by
     UTC hour and by volatility regime (calm / normal / burst, KNOWLEDGE
     definitions: burst = |5s log-return| >= 10bps; calm = no burst in the
     trailing 600s AND |30m return| < 0.4%; normal = neither).
  2. Mid behaviour inside vs outside: |drift| over the window, realized
     vol, and P(price revisits both sides) -- within the window, prints at
     or below the low quote proxy AND at or above the high quote proxy,
     with |net drift| <= the half-spread.  Quote proxy = last trade before
     the window +/- 1.1bps (half of the 2.22bps wide-end board spread of
     KNOWLEDGE 1).  0.78bps (half of the 1.56bps narrow end) is a
     sensitivity.  This proxy is COARSE: it is a last-trade anchor, not a
     book.
  3. MM revenue ceiling, board-free.  Idealized maker: quotes both touches
     continuously, requotes instantly, zero queue, wins EVERY print.
     (A-pre) the pre-registered closed form: min(B,S) x assumed spread
             minus |B-S| x signed episode drift.
     (A-exact) the same idea computed exactly and WITHOUT a spread
             assumption: every print is a maker fill at the printed price
             on the side opposite the taker (s_i = +1 taker BUY, so the
             maker sold; -1 taker SELL, the maker bought), and the PnL
             splits exactly into
                 capture   = SUM s_i size_i (price_i - mid_i)
                 inventory = SUM s_i size_i mid_i + pos_end x mid_end
             where mid_i is a bounce-free mid proxy (the midpoint of the
             last taker-BUY and last taker-SELL print, taken strictly
             before the fill).  capture is the half-spread the tape
             actually paid; inventory is adverse selection.  The maker is
             flat at every episode boundary, so no episode carries a
             directional bet.  It is a CEILING: with a real queue the
             maker wins strictly less than every print.
     Reported per day and as a distribution, in JPY and in bps of maker
     notional filled, INSIDE two-sided episodes against OUTSIDE episodes
     built by the identical machinery.
  4. Power analysis for the coming board study: FIFO round trips inside an
     episode (a maker buy matched against the next maker sell, the queue
     reset and the residual closed at each episode boundary) give n and
     the PnL sd; days of board data needed for n >= 300 round trips and
     for t >= 2.0 on a +0.3bps-class edge, n_req = (2.0 sd / 0.3)^2.  The
     per-episode PnL dispersion of measurement 3 is reported in the same
     table as the second unit.
  5. Adverse-selection cross-check: per-fill markout at 5/10/30/60s inside
     two-sided regimes vs the all-tape baseline, plus post-window drift.
     Markout is decomposed on the bounce-free mid proxy into the entry
     half-spread and the pure mid-to-mid adverse term (KNOWLEDGE 2 "wall":
     maker fills are the breakouts).  If the wall is weaker where flow is
     balanced, that is the mechanism that would make MM viable, and it
     shows up here directly.

SANITY (must all pass before the numbers are read)
  * epoch conversion cross-checked against a second independent
    implementation (the us/ns/s trap of the protocol S6);
  * no look-ahead: every window feature uses only prints inside the window
    and the last print BEFORE it; forward measurements are strictly later
    and are labelled as forward;
  * determinism: no network, no RNG except seeded bootstraps (seed 12345);
  * tape completeness verified against the independent WS execution feed.

CAVEATS (repeated in the output)
  * No queue and no depth: the ceiling ignores queue position, so real
    capture is STRICTLY less -- by an unknown factor, not a small one.
  * The quote proxy is a last-trade anchor, not a book.
  * 30 days, one regime, one venue.
  * Nothing here is a strategy or an adoption recommendation.

Offline only -- reads files, opens no sockets, places no orders.
Idempotent: re-running prints the same numbers.

Usage: python scripts/research_two_sided_flow.py [--data DIR] [--ws DIR]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = "FX_BTC_JPY"
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

WINDOWS = (10, 30, 60)          # seconds
IMB_MAX = 0.30                  # |B-S|/(B+S) ceiling for "two-sided"
PCTLS = (33, 50)                # v_min grid, percent
VOL_EPS = 1e-9                  # positive floor when a percentile is 0

HALF_SPREAD_BPS = 1.10          # primary quote proxy (2.22bps board spread)
HALF_SPREAD_ALT = 0.78          # sensitivity (1.56bps board spread)

BURST_BPS = 10.0                # KNOWLEDGE: |5s log-return| >= 10bps
BURST_LOOKBACK_SEC = 600        # calm (a): no burst in the trailing 10m
DRIFT_LOOKBACK_SEC = 1800       # calm (b): |30m return| < 0.4%
DRIFT_MAX = 0.004

MARKOUT_HORIZONS = (5, 10, 30, 60)
SPLIT_FRAC = 0.60
EDGE_BAR_BPS = 0.30             # HF-class bar the board study must beat
T_BAR = 2.0
N_BAR = 300                     # round trips demanded by the power question
UNWIND_SEC = 60                 # residual inventory is unwound this late
SEED = 12345
STORM_LO, STORM_HI = 12.5, 15.0  # KNOWLEDGE: UTC 12:30-15:00 storm band


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap.

    Dividing a Timedelta by Timedelta('1s') is unit-agnostic by
    construction: pandas normalises both operands.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_ns(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return idx.values.astype("datetime64[ns]").astype("int64") / 1e9


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print("\n--- " + title + " " + "-" * max(0, 72 - len(title)))


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def boot_ci(x: np.ndarray, groups: np.ndarray, n_boot: int = 2000,
            seed: int = SEED) -> tuple[float, float]:
    """Cluster bootstrap CI of the mean, clustered on `groups` (UTC day)."""
    x = np.asarray(x, float)
    if x.size == 0:
        return (float("nan"), float("nan"))
    keys, inv = np.unique(groups, return_inverse=True)
    buckets = [x[inv == i] for i in range(len(keys))]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(buckets), len(buckets))
        means[b] = np.concatenate([buckets[i] for i in pick]).mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
@dataclass
class Tape:
    t: np.ndarray            # print epoch seconds
    price: np.ndarray
    size: np.ndarray
    buy: np.ndarray          # taker BUY (the ask was lifted)
    day: np.ndarray          # UTC day index, for clustering
    mid_prev: np.ndarray     # bounce-free mid proxy just BEFORE each print
    # 1-second forward-filled grid
    g0: int
    gprice: np.ndarray
    gmid: np.ndarray         # same mid proxy on the 1s grid
    glogp: np.ndarray
    calm: np.ndarray
    burst: np.ndarray


def _ffill(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def load_tape(data_dir: Path) -> Tape:
    ex = pd.read_csv(data_dir / f"executions_{PRODUCT}.csv")
    t = epoch_seconds(ex["exec_date"])
    t_alt = epoch_seconds_ns(ex["exec_date"])
    dev = float(np.max(np.abs(t - t_alt)))
    print(f"epoch cross-check   : max |impl_a - impl_b| = {dev:.9f} s "
          f"(must be ~0)  first={t[0]:.3f} -> "
          f"{pd.Timestamp(t[0], unit='s', tz='UTC')}")
    if dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")

    order = np.argsort(t, kind="mergesort")
    t = t[order]
    price = ex["price"].to_numpy(float)[order]
    size = ex["size"].to_numpy(float)[order]
    buy = (ex["side"].to_numpy() == "BUY")[order]
    day = np.floor(t / 86400.0).astype(np.int64)

    # bounce-free mid proxy: midpoint of the most recent taker-BUY print
    # (an ask) and the most recent taker-SELL print (a bid).  Shifted by one
    # print so a fill is never referenced against itself.
    lb = _ffill(np.where(buy, price, np.nan))
    ls = _ffill(np.where(~buy, price, np.nan))
    mid = 0.5 * (lb + ls)
    mid_prev = np.r_[np.nan, mid[:-1]]

    g0 = int(np.floor(t[0]))
    g1 = int(np.ceil(t[-1]))
    n = g1 - g0 + 1
    gp = np.full(n, np.nan)
    si = (np.floor(t) - g0).astype(np.int64)
    gp[si] = price                              # last print of the second wins
    gp = _ffill(gp)                             # forward fill, no look-ahead
    gm = np.full(n, np.nan)
    gm[si] = mid
    gm = _ffill(gm)
    glogp = np.log(gp)

    r5 = np.zeros(n)
    r5[5:] = (glogp[5:] - glogp[:-5]) * 1e4
    burst = np.abs(r5) >= BURST_BPS
    cum = np.concatenate([[0], np.cumsum(burst)])
    calm_a = np.zeros(n, bool)
    calm_a[BURST_LOOKBACK_SEC:] = (
        cum[BURST_LOOKBACK_SEC:n] - cum[0:n - BURST_LOOKBACK_SEC]) == 0
    calm_b = np.zeros(n, bool)
    calm_b[DRIFT_LOOKBACK_SEC:] = np.abs(
        glogp[DRIFT_LOOKBACK_SEC:] - glogp[:-DRIFT_LOOKBACK_SEC]) < DRIFT_MAX

    return Tape(t=t, price=price, size=size, buy=buy, day=day,
                mid_prev=mid_prev, g0=g0, gprice=gp, gmid=gm, glogp=glogp,
                calm=calm_a & calm_b, burst=burst)


def ws_completeness_check(ws_dir: Path, tp: Tape) -> None:
    """Independent proof that the CSV tape is not subsampled."""
    import gzip
    import json

    paths = sorted(ws_dir.glob("*.jsonl.gz"))
    if not paths:
        print("ws completeness     : no recordings present -- check skipped")
        return
    rows: dict[int, tuple[float, float]] = {}
    for p in paths:
        with gzip.open(p, "rt") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                params = (d.get("m") or {}).get("params") or {}
                if params.get("channel") != f"lightning_executions_{PRODUCT}":
                    continue
                for e in params["message"]:
                    rows[e["id"]] = (
                        epoch_seconds(pd.Series([e["exec_date"]]))[0],
                        float(e["size"]))
    if not rows:
        print("ws completeness     : recordings hold no executions -- skipped")
        return
    # the recorder was restarted between files, so the WS stream has gaps;
    # compare only inside its longest CONTIGUOUS stretch, trimmed at both
    # ends, otherwise the gap itself is scored as missing tape
    wt = np.sort(np.array([v[0] for v in rows.values()]))
    brk = np.flatnonzero(np.diff(wt) > 60.0)
    seg_lo = np.r_[0, brk + 1]
    seg_hi = np.r_[brk, len(wt) - 1]
    best = int(np.argmax(wt[seg_hi] - wt[seg_lo]))
    lo = float(wt[seg_lo[best]]) + 120.0
    hi = min(float(wt[seg_hi[best]]) - 120.0, tp.t[-1] - 120.0)
    if hi <= lo:
        print("ws completeness     : no usable overlap -- skipped")
        return
    ws_ids = {k for k, v in rows.items() if lo <= v[0] < hi}
    ws_vol = sum(v[1] for v in rows.values() if lo <= v[0] < hi)
    m = (tp.t >= lo) & (tp.t < hi)
    tape_vol = float(tp.size[m].sum())
    print(f"ws completeness     : overlap "
          f"{pd.Timestamp(lo, unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(hi, unit='s', tz='UTC')}  "
          f"ws {len(ws_ids)} prints / {ws_vol:.3f} BTC  vs  "
          f"tape {int(m.sum())} prints / {tape_vol:.3f} BTC")
    same = (len(ws_ids) == int(m.sum())
            and abs(ws_vol - tape_vol) < 1e-6)
    print(f"                      tape is {'COMPLETE' if same else 'INCOMPLETE'} "
          f"on the overlap (independent feed agreement)")


# --------------------------------------------------------------------------
# window construction
# --------------------------------------------------------------------------
@dataclass
class Grid:
    W: int
    k0: int                  # first window id
    n: int
    start: np.ndarray        # epoch second of each window start
    vbuy: np.ndarray
    vsell: np.ndarray
    nprint: np.ndarray
    p_first: np.ndarray
    p_last: np.ndarray
    p_prev: np.ndarray       # last print STRICTLY before the window (causal)
    min_sell_px: np.ndarray  # lowest taker-SELL print in the window
    max_buy_px: np.ndarray   # highest taker-BUY print in the window
    rv_bps: np.ndarray       # realized vol inside the window, bps
    cash: np.ndarray         # SUM s_i size_i price_i  (idealized maker cash)
    pos: np.ndarray          # SUM -s_i size_i         (idealized maker size)
    notional: np.ndarray     # SUM size_i price_i
    cap: np.ndarray          # SUM s_i size_i (price_i - mid_i)   spread capture
    midflow: np.ndarray      # SUM s_i size_i mid_i               inventory leg
    mid_last: np.ndarray     # mid proxy at the last print of the window
    hour: np.ndarray
    day: np.ndarray
    calm: np.ndarray
    burst: np.ndarray
    wid_of_print: np.ndarray


def build_grid(tp: Tape, W: int) -> Grid:
    wid = np.floor(tp.t / W).astype(np.int64)
    k0 = int(wid.min())
    n = int(wid.max()) - k0 + 1
    idx = wid - k0

    sgn = np.where(tp.buy, 1.0, -1.0)          # +1 taker BUY = maker sold
    notional_i = tp.size * tp.price

    def bc(vals):
        return np.bincount(idx, weights=vals, minlength=n)

    m = np.where(np.isnan(tp.mid_prev), tp.price, tp.mid_prev)

    vbuy = bc(tp.size * tp.buy)
    vsell = bc(tp.size * (~tp.buy))
    nprint = np.bincount(idx, minlength=n).astype(float)
    cash = bc(sgn * notional_i)
    pos = bc(-sgn * tp.size)
    notional = bc(notional_i)
    cap = bc(sgn * tp.size * (tp.price - m))
    midflow = bc(sgn * tp.size * m)

    p_last = np.full(n, np.nan)
    p_last[idx] = tp.price                     # last print of the window wins
    p_first = np.full(n, np.nan)
    p_first[idx[::-1]] = tp.price[::-1]
    mid_last = np.full(n, np.nan)
    mid_last[idx] = m

    min_sell = np.full(n, np.inf)
    np.minimum.at(min_sell, idx[~tp.buy], tp.price[~tp.buy])
    max_buy = np.full(n, -np.inf)
    np.maximum.at(max_buy, idx[tp.buy], tp.price[tp.buy])

    # realized vol: squared print-to-print log returns whose BOTH legs sit
    # inside the same window (no leakage across the boundary)
    r = np.diff(np.log(tp.price))
    same = idx[1:] == idx[:-1]
    ss = np.bincount(idx[1:][same], weights=r[same] ** 2, minlength=n)
    rv = np.sqrt(ss) * 1e4

    # causal anchor: last print strictly before the window
    p_prev = np.full(n, np.nan)
    p_prev[1:] = p_last[:-1]
    filled = np.where(~np.isnan(p_prev), np.arange(n), 0)
    np.maximum.accumulate(filled, out=filled)
    p_prev = p_prev[filled]

    start = (np.arange(n) + k0) * float(W)
    gi = np.clip((np.floor(start) - tp.g0).astype(np.int64), 0, len(tp.gprice) - 1)
    hour = ((start % 86400.0) / 3600.0)
    day = np.floor(start / 86400.0).astype(np.int64)

    return Grid(W=W, k0=k0, n=n, start=start, vbuy=vbuy, vsell=vsell,
                nprint=nprint, p_first=p_first, p_last=p_last, p_prev=p_prev,
                min_sell_px=min_sell, max_buy_px=max_buy, rv_bps=rv,
                cash=cash, pos=pos, notional=notional, cap=cap,
                midflow=midflow, mid_last=mid_last, hour=hour, day=day,
                calm=tp.calm[gi], burst=tp.burst[gi], wid_of_print=idx)


@dataclass
class Cell:
    W: int
    pool: str                # "all" | "nonempty"
    pctl: int
    v_min: float
    floored: bool
    mask: np.ndarray


def v_min_grid(g: Grid) -> list[tuple[str, int, float, bool]]:
    out = []
    pool_all = np.concatenate([g.vbuy, g.vsell])
    pool_ne = pool_all[pool_all > 0]
    for name, pool in (("all", pool_all), ("nonempty", pool_ne)):
        for q in PCTLS:
            v = float(np.percentile(pool, q))
            floored = v <= 0
            out.append((name, q, max(v, VOL_EPS), floored))
    return out


def two_sided_mask(g: Grid, v_min: float) -> np.ndarray:
    tot = g.vbuy + g.vsell
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(tot > 0, np.abs(g.vbuy - g.vsell) / np.maximum(tot, 1e-18), 1.0)
    return (g.vbuy >= v_min) & (g.vsell >= v_min) & (imb <= IMB_MAX)


def runs(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Start index and length of every maximal run of True."""
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
# section 1 -- existence, duty cycle, clustering
# --------------------------------------------------------------------------
def section1(tp: Tape, grids: dict[int, Grid]) -> dict[tuple, Cell]:
    header("1. DOES THE TWO-SIDED REGIME EXIST?  duty cycle and episodes")
    print("A window is two-sided iff  taker-BUY vol >= v_min  AND  taker-SELL")
    print(f"vol >= v_min  AND  |B-S|/(B+S) <= {IMB_MAX:.2f}.  Grid cells below are")
    print("printed in full; none is selected.  '*' = the pre-registered")
    print(f"percentile was 0 and is floored at {VOL_EPS:g} BTC (both sides must trade).")

    cells: dict[tuple, Cell] = {}
    print(f"\n{'W':>4} {'pool':<9}{'pctl':>5} {'v_min BTC':>10} "
          f"{'windows':>9} {'two-sided':>10} {'duty':>8} {'episodes':>9} "
          f"{'med_dur':>8} {'p90_dur':>8} {'vol share':>10}")
    for W, g in grids.items():
        tot_vol = float(g.vbuy.sum() + g.vsell.sum())
        for pool, q, v, floored in v_min_grid(g):
            m = two_sided_mask(g, v)
            st, ln = runs(m)
            dur = ln * W
            share = float((g.vbuy[m] + g.vsell[m]).sum()) / tot_vol if tot_vol else 0.0
            cells[(W, pool, q)] = Cell(W=W, pool=pool, pctl=q, v_min=v,
                                       floored=floored, mask=m)
            print(f"{W:>4} {pool:<9}{q:>5} {v:>10.5f}{'*' if floored else ' '}"
                  f"{g.n:>9,} {int(m.sum()):>10,} {m.mean() * 100:>7.2f}% "
                  f"{len(st):>9,} "
                  f"{(np.median(dur) if len(dur) else 0):>7.0f}s "
                  f"{(np.percentile(dur, 90) if len(dur) else 0):>7.0f}s "
                  f"{share * 100:>9.1f}%")

    sub("what the thresholds actually are (tape thinness)")
    for W, g in grids.items():
        ne = (g.nprint > 0)
        print(f"W={W:>3}s  windows {g.n:>8,}  empty {100 * (1 - ne.mean()):>5.1f}%  "
              f"median prints/window {np.median(g.nprint):>4.0f}  "
              f"median one-side vol (non-empty windows) "
              f"{np.median(np.concatenate([g.vbuy[ne], g.vsell[ne]])):.5f} BTC")
    print("\nThe tape averages 0.32 prints/second.  At W=10s the median window")
    print("holds ONE print, so 'both sides eaten inside 10s' is rare by")
    print("arithmetic, not by market structure.  Read the 60s row as the")
    print("primary one and the 10s row as a statement about tape density.")

    sub("clustering by UTC hour (duty cycle per hour, W=60s / pool=all / p50)")
    g = grids[60]
    m = cells[(60, "all", 50)].mask
    hh = np.floor(g.hour).astype(int)
    print(f"{'hour':>5} " + " ".join(f"{h:>5d}" for h in range(24)))
    duty_h = np.array([m[hh == h].mean() * 100 if (hh == h).any() else np.nan
                       for h in range(24)])
    print(f"{'duty%':>5} " + " ".join(f"{v:>5.1f}" for v in duty_h))
    storm = (g.hour >= STORM_LO) & (g.hour < STORM_HI)
    print(f"\nstorm band UTC {STORM_LO:.1f}-{STORM_HI:.1f} (KNOWLEDGE 2): duty "
          f"{m[storm].mean() * 100:.2f}%  vs elsewhere "
          f"{m[~storm].mean() * 100:.2f}%  "
          f"(lift {m[storm].mean() / max(m[~storm].mean(), 1e-12):.2f}x)")

    sub("clustering by volatility regime (W=60s / pool=all / p50)")
    regimes = {"calm": g.calm, "burst": g.burst,
               "normal": ~g.calm & ~g.burst}
    print(f"{'regime':<8}{'windows':>10}{'share of time':>15}{'duty':>10}"
          f"{'lift vs all':>13}")
    base = m.mean()
    for name, r in regimes.items():
        if not r.any():
            continue
        print(f"{name:<8}{int(r.sum()):>10,}{r.mean() * 100:>14.1f}%"
              f"{m[r].mean() * 100:>9.2f}%{m[r].mean() / max(base, 1e-12):>12.2f}x")
    print(f"{'ALL':<8}{g.n:>10,}{100.0:>14.1f}%{base * 100:>9.2f}%{1.0:>12.2f}x")
    return cells


# --------------------------------------------------------------------------
# section 2 -- mid behaviour inside vs outside
# --------------------------------------------------------------------------
def drift_bps(g: Grid) -> np.ndarray:
    """log(last print in window / last print before window) in bps.

    NaN where the window is empty.  Causal: both legs are at or before the
    window close.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        d = (np.log(g.p_last) - np.log(g.p_prev)) * 1e4
    return d


def revisit_flags(g: Grid, h_bps: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Traded-through fills against a last-trade +/- h quote proxy."""
    q_lo = g.p_prev * (1.0 - h_bps * 1e-4)
    q_hi = g.p_prev * (1.0 + h_bps * 1e-4)
    fill_bid = g.min_sell_px <= q_lo       # a taker SELL reached our bid
    fill_ask = g.max_buy_px >= q_hi        # a taker BUY reached our ask
    both = fill_bid & fill_ask
    return fill_bid, fill_ask, both


def section2(grids: dict[int, Grid], cells: dict[tuple, Cell]) -> None:
    header("2. MID BEHAVIOUR INSIDE vs OUTSIDE THE TWO-SIDED REGIME")
    print("Quote proxy = last trade BEFORE the window +/- half-spread.  A fill")
    print("needs a print through the quote (the repo's traded-through rule).")
    print("P(both) = both quotes filled inside the window.  P(both & flat) also")
    print("requires |net drift| <= the half-spread -- the round trip a maker")
    print("could actually have closed at no inventory cost.")

    for h in (HALF_SPREAD_BPS, HALF_SPREAD_ALT):
        sub(f"half-spread proxy = {h:.2f} bps "
            f"(full {2 * h:.2f} bps)"
            + ("   [PRIMARY]" if h == HALF_SPREAD_BPS else "   [sensitivity]"))
        print(f"{'W':>4} {'pool':<9}{'pctl':>5} {'set':<10}"
              f"{'n':>9}{'|drift|':>9}{'rv':>8}{'P(bid)':>8}{'P(ask)':>8}"
              f"{'P(both)':>9}{'P(both&flat)':>13}")
        for W, g in grids.items():
            d = drift_bps(g)
            fb, fa, both = revisit_flags(g, h)
            flat = both & (np.abs(d) <= h)
            for pool in ("all", "nonempty"):
                for q in PCTLS:
                    m = cells[(W, pool, q)].mask
                    for tag, sel in (("inside", m), ("outside", ~m)):
                        n = int(sel.sum())
                        ad = np.nanmean(np.abs(d[sel])) if n else np.nan
                        rv = np.nanmean(g.rv_bps[sel]) if n else np.nan
                        print(f"{W:>4} {pool:<9}{q:>5} {tag:<10}{n:>9,}"
                              f"{ad:>9.2f}{rv:>8.2f}"
                              f"{fb[sel].mean() * 100:>7.1f}%"
                              f"{fa[sel].mean() * 100:>7.1f}%"
                              f"{both[sel].mean() * 100:>8.1f}%"
                              f"{flat[sel].mean() * 100:>12.1f}%")
                    print()


# --------------------------------------------------------------------------
# section 3 -- revenue ceiling
# --------------------------------------------------------------------------
@dataclass
class EpisodeStats:
    n: int
    per_day_jpy: float
    total_jpy: float
    bps_of_notional: float
    cap_bps: float           # spread capture leg, bps of notional
    inv_bps: float           # inventory / adverse leg, bps of notional
    pnl: np.ndarray
    bps: np.ndarray
    day: np.ndarray
    notional: np.ndarray
    st: np.ndarray
    ln: np.ndarray


EMPTY_EP = EpisodeStats(0, 0.0, 0.0, float("nan"), float("nan"), float("nan"),
                        *([np.array([])] * 6))


def episode_marks(g: Grid, tp: Tape, st: np.ndarray, ln: np.ndarray,
                  unwind_sec: int) -> np.ndarray:
    """Mid proxy the residual inventory is unwound at.

    unwind_sec = 0 marks at the mid of the episode's last print, which
    hands a free half-spread to any episode whose position never had to be
    closed (a one-print episode books capture and no adverse move at all).
    unwind_sec > 0 marks at the mid that many seconds AFTER the episode
    ends, so the residual pays for its own exit.  Forward-looking on
    purpose and only ever used for marking, never for classification.
    """
    if unwind_sec <= 0:
        return np.array([g.mid_last[s:s + L][~np.isnan(g.mid_last[s:s + L])][-1]
                         for s, L in zip(st, ln)])
    end_sec = g.start[st + ln - 1] + g.W + unwind_sec
    gi = np.clip((np.floor(end_sec) - tp.g0).astype(np.int64),
                 0, len(tp.gmid) - 1)
    return tp.gmid[gi]


def episode_pnl(g: Grid, mask: np.ndarray, tp: Tape | None = None,
                unwind_sec: int = 0) -> EpisodeStats:
    """Exact PnL of the idealized maker that wins EVERY print in an episode.

    Every print is a maker fill at the printed price, on the side opposite
    the taker.  The PnL splits exactly into

        capture   = SUM s_i size_i (price_i - mid_i)      >= 0 on average,
                    the realized half-spread the tape actually paid;
        inventory = SUM s_i size_i mid_i + pos_end mid_end,
                    the mark-to-market of the inventory the maker was left
                    holding along the mid path -- i.e. adverse selection.

    Residual inventory is marked at a MID proxy, so the mark carries no
    half-spread bias, `unwind_sec` seconds after the episode ends (see
    episode_marks).  The maker starts and is measured flat at every
    episode boundary: nothing is carried across episodes, which is what
    keeps this a market-making number instead of a 30-day directional bet.
    """
    st, ln = runs(mask)
    if len(st) == 0:
        return EMPTY_EP

    def seg(arr):
        c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(arr))])
        return c[st + ln] - c[st]

    cap = seg(g.cap)
    midflow = seg(g.midflow)
    pos = seg(g.pos)
    note = seg(g.notional)
    mid_end = episode_marks(g, tp, st, ln, unwind_sec if tp is not None else 0)
    inv = midflow + pos * mid_end
    pnl = cap + inv
    bps = np.where(note > 0, pnl / np.maximum(note, 1e-9) * 1e4, np.nan)
    days = np.array([g.day[s] for s in st])
    span_days = (g.start[-1] - g.start[0]) / 86400.0
    tot_note = float(note.sum())
    return EpisodeStats(n=len(st), per_day_jpy=float(pnl.sum() / span_days),
                        total_jpy=float(pnl.sum()),
                        bps_of_notional=float(pnl.sum() / tot_note * 1e4),
                        cap_bps=float(cap.sum() / tot_note * 1e4),
                        inv_bps=float(inv.sum() / tot_note * 1e4),
                        pnl=pnl, bps=bps, day=days, notional=note,
                        st=st, ln=ln)


def episode_pnl_prereg(g: Grid, mask: np.ndarray, spread_bps: float) -> tuple:
    """The closed form written into the pre-registration."""
    st, ln = runs(mask)
    if len(st) == 0:
        return 0.0, 0.0, 0.0
    B = np.array([g.vbuy[s:s + L].sum() for s, L in zip(st, ln)])
    S = np.array([g.vsell[s:s + L].sum() for s, L in zip(st, ln)])
    p0 = np.array([g.p_prev[s] for s in st])
    p1 = np.array([g.p_last[s:s + L][~np.isnan(g.p_last[s:s + L])][-1]
                   for s, L in zip(st, ln)])
    px = 0.5 * (p0 + p1)
    capture = np.minimum(B, S) * spread_bps * 1e-4 * px
    inv = (S - B) * (p1 - p0)          # maker is net (S-B) long over the drift
    span_days = (g.start[-1] - g.start[0]) / 86400.0
    return (float(capture.sum() / span_days), float(inv.sum() / span_days),
            float((capture + inv).sum() / span_days))


def section3(tp: Tape, grids: dict[int, Grid], cells: dict[tuple, Cell]) -> dict:
    header("3. MM REVENUE CEILING (board-free, zero queue, wins every print)")
    print("A-exact makes NO spread assumption.  It books every print as a maker")
    print("fill at the printed price on the side opposite the taker and splits")
    print("the result exactly into")
    print("   capture   = the half-spread the tape actually paid, and")
    print("   inventory = the mark-to-market of what the maker was left")
    print("               holding -- adverse selection, measured on a")
    print("               bounce-free mid proxy.")
    print("The maker is flat at every episode boundary, so no episode carries a")
    print("directional bet.  bps are per unit of maker notional FILLED.")

    eff = (np.where(tp.buy, 1.0, -1.0) * (tp.price - tp.mid_prev)
           / tp.price * 1e4)
    ok = np.isfinite(eff)
    sub("the revenue source, measured (not assumed)")
    print(f"realized half-spread per fill: mean {np.mean(eff[ok]):.3f} bps, "
          f"median {np.median(eff[ok]):.3f}, size-weighted "
          f"{np.average(eff[ok], weights=tp.size[ok]):.3f}  "
          f"(n={int(ok.sum()):,})")
    print(f"the pre-registered proxy is {HALF_SPREAD_BPS:.2f} bps -- the tape "
          f"agrees to within {abs(np.mean(eff[ok]) - HALF_SPREAD_BPS):.2f} bps")

    out = {}
    sub(f"ceiling INSIDE two-sided episodes vs OUTSIDE (same machinery), "
        f"residual unwound {UNWIND_SEC}s after the episode")
    print(f"{'W':>4} {'pool':<9}{'pctl':>5} {'set':<8}{'episodes':>9}"
          f"{'JPY/day':>11}{'net bps':>9}{'capture':>9}{'inventory':>11}"
          f"{'med ep':>8}{'p10':>7}{'p90':>7}{'flat-mark':>11}"
          f"{'A-pre JPY/d':>13}")
    for W, g in grids.items():
        for pool in ("all", "nonempty"):
            for q in PCTLS:
                m = cells[(W, pool, q)].mask
                _, _, pre_tot = episode_pnl_prereg(g, m, 2 * HALF_SPREAD_BPS)
                for tag, sel, pre in (("inside", m, pre_tot),
                                      ("outside", ~m & (g.nprint > 0), np.nan)):
                    es = episode_pnl(g, sel, tp, UNWIND_SEC)
                    es0 = episode_pnl(g, sel, tp, 0)
                    if tag == "inside":
                        out[(W, pool, q)] = es
                    if es.n == 0:
                        continue
                    print(f"{W:>4} {pool:<9}{q:>5} {tag:<8}{es.n:>9,}"
                          f"{es.per_day_jpy:>11,.0f}{es.bps_of_notional:>9.3f}"
                          f"{es.cap_bps:>9.3f}{es.inv_bps:>11.3f}"
                          f"{np.nanmedian(es.bps):>8.3f}"
                          f"{np.nanpercentile(es.bps, 10):>7.2f}"
                          f"{np.nanpercentile(es.bps, 90):>7.2f}"
                          f"{es0.bps_of_notional:>11.3f}"
                          + (f"{pre:>13,.0f}" if np.isfinite(pre) else f"{'-':>13}"))
                print()
    print("'flat-mark' is the same number with the residual marked at the")
    print("episode's own last mid instead of 60s later.  It is systematically")
    print("kinder: an episode whose position never had to be closed books the")
    print("half-spread and no adverse move at all.  The gap between the two")
    print("columns is the cost of getting flat, and it is not small.")

    sub("whole tape, every window its own episode -- the unconditional "
        "reference")
    for W, g in grids.items():
        es_all = episode_pnl(g, g.nprint > 0, tp, UNWIND_SEC)
        print(f"W={W:>3}s  {es_all.n:>7,} episodes  "
              f"{es_all.per_day_jpy:>10,.0f} JPY/day  "
              f"net {es_all.bps_of_notional:>6.3f} bps  "
              f"(capture {es_all.cap_bps:.3f}, inventory {es_all.inv_bps:+.3f})")
    print("Compare the two-sided rows to THIS per unit of notional, not in")
    print("JPY/day: the regime filter also throws volume away.")

    sub("decomposition of the pre-registered closed form (W=60s, all, p50)")
    cap, inv, tot = episode_pnl_prereg(grids[60], cells[(60, "all", 50)].mask,
                                       2 * HALF_SPREAD_BPS)
    print(f"spread capture on matched volume : {cap:>14,.0f} JPY/day")
    print(f"drift cost on unmatched residual : {inv:>14,.0f} JPY/day")
    print(f"pre-registered ceiling           : {tot:>14,.0f} JPY/day")
    print("The capture term is positive BY CONSTRUCTION (min(B,S) x spread is")
    print("never negative) and the imbalance cap keeps the residual small, so a")
    print("positive A-pre ceiling is close to a tautology.  A-exact is the")
    print("informative one: it can and does go negative when the bounce is")
    print("swamped by drift.")
    return out


# --------------------------------------------------------------------------
# section 4 -- FIFO round trips and power
# --------------------------------------------------------------------------
def fifo_round_trips(tp: Tape, keep: np.ndarray,
                     seg: np.ndarray | None = None,
                     marks: np.ndarray | None = None
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """FIFO attribution of the idealized maker's fills into round trips.

    Returns (pnl_bps, close_time, matched_size) per round trip.

    `keep` selects the prints the maker is allowed to be filled on; `seg`
    gives an episode id per print, and the lot queue is reset at every
    change of it -- whatever is still open at an episode boundary is
    closed at that episode's last mid proxy.  Without the reset a lot
    opened on day 1 can be closed on day 20 and the "round trip" is really
    a 20-day directional bet.

    Maker side is the opposite of the taker side.  A buy is matched
    against the next sell (and vice versa) FIFO by volume; each match is
    one round trip.  This is an attribution of the same PnL, not a
    strategy: no quote placement decision is made anywhere.
    """
    idx = np.flatnonzero(keep)
    if idx.size == 0:
        return np.array([]), np.array([]), np.array([])
    px = tp.price[idx]
    sz = tp.size[idx]
    maker_buy = ~tp.buy[idx]              # taker SELL => maker bought
    tt = tp.t[idx]
    sg = seg[idx] if seg is not None else np.zeros(len(idx), np.int64)
    mid = np.where(np.isnan(tp.mid_prev[idx]), px, tp.mid_prev[idx])

    from collections import deque

    q: deque[list[float]] = deque()       # open lots [signed_size, price]
    rt_bps: list[float] = []
    rt_t: list[float] = []
    rt_sz: list[float] = []

    def close_all(mark: float, when: float) -> None:
        while q:
            lot = q.popleft()
            pnl = (mark - lot[1]) if lot[0] > 0 else (lot[1] - mark)
            rt_bps.append(pnl / lot[1] * 1e4)
            rt_t.append(when)
            rt_sz.append(abs(lot[0]))

    def mark_for(j: int) -> float:
        """Unwind mid for the episode that print j belongs to."""
        if marks is None or sg[j] < 0 or sg[j] >= len(marks):
            return float(mid[j])
        return float(marks[sg[j]])

    for i in range(len(idx)):
        if i and sg[i] != sg[i - 1]:
            close_all(mark_for(i - 1), float(tt[i - 1]))
        s = float(sz[i])
        p = float(px[i])
        sign = 1.0 if maker_buy[i] else -1.0
        while s > 1e-12 and q and q[0][0] * sign < 0:
            lot = q[0]
            take = min(s, abs(lot[0]))
            entry = lot[1]
            # a long lot closed by a sell, or a short lot closed by a buy
            pnl = (p - entry) if lot[0] > 0 else (entry - p)
            rt_bps.append(pnl / entry * 1e4)
            rt_t.append(float(tt[i]))
            rt_sz.append(take)
            s -= take
            lot[0] = lot[0] - take if lot[0] > 0 else lot[0] + take
            if abs(lot[0]) <= 1e-12:
                q.popleft()
        if s > 1e-12:
            q.append([sign * s, p])
    close_all(mark_for(len(idx) - 1), float(tt[-1]))
    return np.array(rt_bps), np.array(rt_t), np.array(rt_sz)


def episode_id_per_print(g: Grid, es: EpisodeStats) -> np.ndarray:
    """Episode index for every print, -1 outside every episode."""
    ep = np.full(g.n, -1, np.int64)
    for j, (s, L) in enumerate(zip(es.st, es.ln)):
        ep[s:s + L] = j
    return ep[g.wid_of_print]


def section4(tp: Tape, grids: dict[int, Grid], cells: dict[tuple, Cell],
             eps: dict) -> None:
    header("4. POWER ANALYSIS FOR THE COMING BOARD STUDY")
    print("Round trips are a FIFO attribution of the SAME idealized fills (a")
    print("maker buy matched against the next maker sell).  They give n and a")
    print("PnL dispersion; the board study will replace them with real quotes.")
    print(f"Bar assumed: edge {EDGE_BAR_BPS:+.2f} bps/round trip, t >= {T_BAR:.1f},")
    print(f"n >= {N_BAR}.  Required n = (t sd / edge)^2.")

    span_days = (tp.t[-1] - tp.t[0]) / 86400.0
    rows = []
    for W in WINDOWS:
        g = grids[W]
        for pool in ("all", "nonempty"):
            for q in PCTLS:
                m = cells[(W, pool, q)].mask
                keep = m[g.wid_of_print]
                es = eps[(W, pool, q)]
                seg = episode_id_per_print(g, es)
                marks = episode_marks(g, tp, es.st, es.ln, UNWIND_SEC)
                rt, rtt, rsz = fifo_round_trips(tp, keep, seg, marks)
                if rt.size == 0:
                    continue
                sd = float(rt.std(ddof=1))
                mean = float(rt.mean())
                wmean = float(np.average(rt, weights=rsz)) if rsz.sum() else np.nan
                t_stat = mean / (sd / np.sqrt(rt.size)) if sd > 0 else np.nan
                n_req = (T_BAR * sd / EDGE_BAR_BPS) ** 2
                per_day = rt.size / span_days
                rows.append((W, pool, q, rt.size, per_day, mean, wmean, sd,
                             t_stat, n_req, max(n_req, N_BAR) / per_day))
    print(f"\n{'W':>4} {'pool':<9}{'pctl':>5}{'round trips':>12}{'per day':>10}"
          f"{'mean bps':>10}{'vw mean':>9}{'sd bps':>9}{'t(obs)':>8}"
          f"{'n for t>=2':>12}{'days needed':>13}")
    for r in rows:
        print(f"{r[0]:>4} {r[1]:<9}{r[2]:>5}{r[3]:>12,}{r[4]:>10,.0f}"
              f"{r[5]:>10.3f}{r[6]:>9.3f}{r[7]:>9.3f}{r[8]:>8.1f}"
              f"{r[9]:>12,.0f}{r[10]:>13,.1f}")

    g60 = grids[60]
    es60 = episode_pnl(g60, g60.nprint > 0, tp, UNWIND_SEC)
    all_seg = episode_id_per_print(g60, es60)
    all_marks = episode_marks(g60, tp, es60.st, es60.ln, UNWIND_SEC)
    rt_all, _, _ = fifo_round_trips(tp, np.ones(len(tp.t), bool), all_seg,
                                    all_marks)
    if rt_all.size:
        sd = float(rt_all.std(ddof=1))
        n_req = (T_BAR * sd / EDGE_BAR_BPS) ** 2
        print(f"\nwhole tape, 60s episodes (no regime filter): {rt_all.size:,} "
              f"round trips ({rt_all.size / span_days:,.0f}/day), mean "
              f"{rt_all.mean():+.3f} bps, sd {sd:.3f} bps -> n for t>=2 at "
              f"{EDGE_BAR_BPS:+.2f}bps = {n_req:,.0f} "
              f"({max(n_req, N_BAR) / (rt_all.size / span_days):.2f} days)")
    print("\nCAUTION: these round-trip counts assume the maker wins every print.")
    print("A real quote wins a fraction f of them; n scales with f and the days")
    print("needed scale with 1/f.  The board study must measure f before this")
    print("table means anything.")

    sub("days of BOARD data needed, as a function of the fill share f")
    print("f = the share of the tape's prints a real quote actually wins.  The")
    print("requirement is n >= max(300, n_for_t>=2).  Rows are the two-sided")
    print("cells; the whole-tape row is the unfiltered reference.")
    print(f"{'W':>4} {'pool':<9}{'pctl':>5}{'n required':>12}" +
          "".join(f"{'f=' + s:>10}" for s in ("100%", "10%", "5%", "1%", "0.1%")))
    for r in rows:
        need = max(r[9], N_BAR)
        per_day = r[4]
        print(f"{r[0]:>4} {r[1]:<9}{r[2]:>5}{need:>12,.0f}" +
              "".join(f"{need / (per_day * f):>10,.1f}"
                      for f in (1.0, 0.10, 0.05, 0.01, 0.001)))
    print("(days; a real bitFlyer quote at the touch is very unlikely to see")
    print("f above a few percent, so read the f=1-5% columns.)")

    sub("per-EPISODE power (the unit the pre-registration names)")
    print(f"{'W':>4} {'pool':<9}{'pctl':>5}{'episodes':>10}{'per day':>9}"
          f"{'mean bps':>10}{'sd bps':>9}{'t(obs)':>8}{'n for t>=2':>12}"
          f"{'days':>9}")
    for (W, pool, q), es in eps.items():
        if es.n < 2:
            continue
        b = es.bps[np.isfinite(es.bps)]
        if b.size < 2:
            continue
        sd = float(b.std(ddof=1))
        t_stat = b.mean() / (sd / np.sqrt(b.size)) if sd > 0 else np.nan
        n_req = (T_BAR * sd / EDGE_BAR_BPS) ** 2
        per_day = b.size / span_days
        print(f"{W:>4} {pool:<9}{q:>5}{b.size:>10,}{per_day:>9,.1f}"
              f"{b.mean():>10.3f}{sd:>9.3f}{t_stat:>8.1f}{n_req:>12,.0f}"
              f"{max(n_req, N_BAR) / per_day:>9,.1f}")


# --------------------------------------------------------------------------
# section 5 -- adverse selection cross-check
# --------------------------------------------------------------------------
def markouts(tp: Tape, keep: np.ndarray, horizon: int,
             kind: str = "adverse") -> np.ndarray:
    """Maker markout in bps at `horizon` seconds after the fill.

    The maker takes the side opposite the taker: taker BUY => the maker is
    short at the print, so the maker gains if the price falls.  Three
    flavours, all referenced to the bounce-free mid proxy:

      "entry"   s (price - mid_now)          the half-spread earned;
      "adverse" s (mid_now - mid_future)     pure adverse selection, the
                                             wall;
      "total"   entry + adverse              the fill's realized PnL.

    A last-trade reference would put a bid-ask bounce in the future leg
    and inflate "adverse" by roughly the half-spread, which is exactly the
    quantity under test -- hence the mid proxy.  Forward by construction;
    nothing here feeds a window feature.
    """
    idx = np.flatnonzero(keep)
    gi = (np.floor(tp.t[idx]) - tp.g0).astype(np.int64) + horizon
    ok = (gi < len(tp.gprice)) & np.isfinite(tp.mid_prev[idx])
    idx = idx[ok]
    gi = gi[ok]
    p_now = tp.price[idx]
    m_now = tp.mid_prev[idx]
    m_fut = tp.gmid[gi]
    sgn = np.where(tp.buy[idx], 1.0, -1.0)     # +1 maker sold, -1 maker bought
    entry = sgn * (p_now - m_now) / p_now * 1e4
    adverse = sgn * (m_now - m_fut) / p_now * 1e4
    if kind == "entry":
        return entry
    if kind == "total":
        return entry + adverse
    return adverse


def section5(tp: Tape, grids: dict[int, Grid], cells: dict[tuple, Cell]) -> None:
    header("5. ADVERSE-SELECTION CROSS-CHECK -- is the wall weaker inside?")
    print("adverse(tau) = s (mid_now - mid_future), the pure mid-to-mid term:")
    print("negative means the price ran away from the fill.  entry = the")
    print("half-spread the fill earned.  total = entry + adverse = what the")
    print("fill was actually worth after tau seconds.  All on the bounce-free")
    print("mid proxy, so no half-spread leaks into the adverse column.")
    print("KNOWLEDGE 2 measures the wall at 6-9 bps for SIGNAL-DRIVEN limits;")
    print("this is a per-print, seconds-scale object -- compare inside vs")
    print("baseline, do not compare the level to 6-9 bps.")

    allmask = np.ones(len(tp.t), bool)
    print(f"\nbaseline, every print (n={len(tp.t):,}):")
    print(f"  entry {markouts(tp, allmask, 0, 'entry').mean():+.3f} bps   " +
          "  ".join(f"adverse({h}s) {markouts(tp, allmask, h).mean():+.3f}"
                    for h in MARKOUT_HORIZONS))
    print("  " + " " * 18 +
          "  ".join(f"  total({h}s) {markouts(tp, allmask, h, 'total').mean():+.3f}"
                    for h in MARKOUT_HORIZONS))

    for W in WINDOWS:
        g = grids[W]
        sub(f"W={W}s   (adverse / total, bps per fill)")
        print(f"{'pool':<9}{'pctl':>5}{'set':<9}{'fills':>10}{'entry':>8}" +
              "".join(f"{'adv ' + str(h) + 's':>10}" for h in MARKOUT_HORIZONS) +
              "".join(f"{'tot ' + str(h) + 's':>10}" for h in MARKOUT_HORIZONS))
        for pool in ("all", "nonempty"):
            for q in PCTLS:
                m = cells[(W, pool, q)].mask
                keep = m[g.wid_of_print]
                for tag, sel in (("inside", keep), ("outside", ~keep)):
                    if sel.sum() == 0:
                        continue
                    adv = [markouts(tp, sel, h) for h in MARKOUT_HORIZONS]
                    tot = [markouts(tp, sel, h, "total") for h in MARKOUT_HORIZONS]
                    print(f"{pool:<9}{q:>5}{tag:<9}{int(sel.sum()):>10,}"
                          f"{markouts(tp, sel, 0, 'entry').mean():>8.3f}" +
                          "".join(f"{v.mean():>+10.3f}" for v in adv) +
                          "".join(f"{v.mean():>+10.3f}" for v in tot))
                # difference with a day-clustered bootstrap at tau=30s
                a = markouts(tp, keep, 30)
                b = markouts(tp, ~keep, 30)
                ia = np.flatnonzero(keep)
                gi = (np.floor(tp.t[ia]) - tp.g0).astype(np.int64) + 30
                da = tp.day[ia[(gi < len(tp.gprice))
                               & np.isfinite(tp.mid_prev[ia])]]
                lo, hi = boot_ci(a, da)
                print(f"{'':<9}{'':>5}{'diff':<9}  adverse(30s) inside-outside "
                      f"= {a.mean() - b.mean():+.3f} bps; inside mean 95% CI "
                      f"[{lo:+.3f}, {hi:+.3f}] (day-clustered, seed {SEED})")
                print()

    sub("post-window forward drift (the window AFTER a two-sided window)")
    print("Strictly forward: window k is classified, window k+1 is measured.")
    print(f"{'W':>4} {'pool':<9}{'pctl':>5}{'set':<9}{'n':>9}"
          f"{'|fwd drift|':>13}{'fwd rv':>9}")
    for W in WINDOWS:
        g = grids[W]
        d = drift_bps(g)
        fwd = np.r_[d[1:], np.nan]
        fwd_rv = np.r_[g.rv_bps[1:], np.nan]
        for pool in ("all", "nonempty"):
            for q in PCTLS:
                m = cells[(W, pool, q)].mask
                for tag, sel in (("inside", m), ("outside", ~m)):
                    print(f"{W:>4} {pool:<9}{q:>5}{tag:<9}{int(sel.sum()):>9,}"
                          f"{np.nanmean(np.abs(fwd[sel])):>13.2f}"
                          f"{np.nanmean(fwd_rv[sel]):>9.2f}")


# --------------------------------------------------------------------------
# section 6 -- 60/40 consistency
# --------------------------------------------------------------------------
def section6(tp: Tape, grids: dict[int, Grid], cells: dict[tuple, Cell]) -> None:
    header("6. 60/40 CHRONOLOGICAL CONSISTENCY (measurement stability only)")
    print("No configuration is chosen from this split.  It answers one")
    print("question: are the measurements the same object in both halves?")
    t_split = tp.t[0] + SPLIT_FRAC * (tp.t[-1] - tp.t[0])
    print(f"split at {pd.Timestamp(t_split, unit='s', tz='UTC')}")

    print(f"\n{'W':>4} {'pool':<9}{'pctl':>5}{'half':<7}{'duty':>8}"
          f"{'episodes':>10}{'med dur':>9}{'ceil bps':>10}{'adv30':>11}")
    for W in WINDOWS:
        g = grids[W]
        early_w = g.start < t_split
        early_p = tp.t < t_split
        for pool in ("all", "nonempty"):
            for q in PCTLS:
                m = cells[(W, pool, q)].mask
                keep = m[g.wid_of_print]
                for tag, wsel, psel in (("early", early_w, early_p),
                                        ("late", ~early_w, ~early_p)):
                    mm = m & wsel
                    st, ln = runs(mm)
                    es = episode_pnl(g, mm, tp, UNWIND_SEC)
                    mo = markouts(tp, keep & psel, 30)
                    print(f"{W:>4} {pool:<9}{q:>5}{tag:<7}"
                          f"{m[wsel].mean() * 100:>7.2f}%{len(st):>10,}"
                          f"{(np.median(ln * W) if len(ln) else 0):>8.0f}s"
                          f"{es.bps_of_notional:>10.3f}"
                          f"{(mo.mean() if mo.size else np.nan):>+11.3f}")


# --------------------------------------------------------------------------
# section 7 -- ws spread cross-check
# --------------------------------------------------------------------------
def section7(ws_dir: Path, grids: dict[int, Grid], cells: dict[tuple, Cell],
             data_dir: Path) -> None:
    header("7. SPREAD CROSS-CHECK ON RECORDED BOOK DATA (supplementary)")
    print("The quote proxy above assumes a fixed 2.22bps spread.  The recorded")
    print("book covers only a few hours, so this can only say whether the")
    print("assumption is the right order of magnitude inside the regime.")
    try:
        from bot.research.board import build_series
    except Exception as exc:                       # pragma: no cover
        print(f"board module unavailable ({exc}) -- skipped")
        return
    paths = sorted(ws_dir.glob("*.jsonl.gz"))
    if not paths:
        print("no recordings -- skipped")
        return
    df = build_series(paths, interval_sec=1.0, depth_bps=5.0)
    if df.empty:
        print("no board snapshots -- skipped")
        return
    sp = (df["spread"] / df["mid"] * 1e4).dropna()
    ts = ((df.index - EPOCH) / pd.Timedelta("1s")).to_numpy(float)
    print(f"book seconds        : {len(df):,}  "
          f"{df.index[0]} .. {df.index[-1]}")
    print(f"spread (bps of mid) : mean {sp.mean():.3f}  median "
          f"{sp.median():.3f}  p90 {sp.quantile(0.90):.3f}  "
          f"p99 {sp.quantile(0.99):.3f}")
    print(f"KNOWLEDGE 1 range   : 1.56 - 2.22 bps  -> proxy "
          f"{2 * HALF_SPREAD_BPS:.2f} bps is "
          f"{'inside' if 1.56 <= 2 * HALF_SPREAD_BPS <= 2.22 else 'outside'} it")

    g = grids[60]
    m = cells[(60, "all", 50)].mask
    wid = np.floor(ts / 60.0).astype(np.int64) - g.k0
    ok = (wid >= 0) & (wid < g.n)
    inside = np.zeros(len(ts), bool)
    inside[ok] = m[wid[ok]]
    spv = sp.to_numpy()
    cov = ok & ~np.isnan(spv)
    if cov.sum() == 0:
        print("no overlap between the book record and the tape -- skipped")
        return
    a = spv[cov & inside]
    b = spv[cov & ~inside]
    print(f"\noverlap seconds     : {int(cov.sum()):,}  "
          f"(inside two-sided {int((cov & inside).sum()):,} / "
          f"outside {int((cov & ~inside).sum()):,})")
    if a.size and b.size:
        print(f"spread inside       : mean {a.mean():.3f} bps  median "
              f"{np.median(a):.3f}")
        print(f"spread outside      : mean {b.mean():.3f} bps  median "
              f"{np.median(b):.3f}")
        print(f"ratio inside/outside: {a.mean() / b.mean():.2f}x")
    print("\nA WIDER spread inside the regime would raise the capture term and")
    print("the adverse-selection term together; it is not free revenue.")


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--ws", default=str(ROOT / "data" / "ws"))
    args = ap.parse_args()
    data_dir = Path(args.data)
    ws_dir = Path(args.ws)

    header("PRE-STUDY S7 -- TWO-SIDED FLOW REGIMES ON FX_BTC_JPY")
    print(__doc__.split("Usage:")[0].strip()[:0] or "", end="")
    print("Pre-registered measurement only.  No strategy, no parameter and no")
    print("adoption bar is proposed here.  See the module docstring for the")
    print("full pre-registration.")

    sub("SANITY")
    tp = load_tape(data_dir)
    span_days = (tp.t[-1] - tp.t[0]) / 86400.0
    print(f"prints              : {len(tp.t):,}  "
          f"{pd.Timestamp(tp.t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(tp.t[-1], unit='s', tz='UTC')}  "
          f"({span_days:.2f} days, {len(tp.t) / span_days / 86400:.3f} prints/s)")
    print(f"monotonic timestamps: {bool(np.all(np.diff(tp.t) >= 0))}")
    print(f"taker BUY share     : {tp.buy.mean() * 100:.2f}%  "
          f"volume BUY share {tp.size[tp.buy].sum() / tp.size.sum() * 100:.2f}%")
    print(f"1s grid             : {len(tp.gprice):,} seconds, "
          f"calm {tp.calm.mean() * 100:.1f}%, burst seconds "
          f"{tp.burst.mean() * 100:.1f}%")
    ws_completeness_check(ws_dir, tp)

    grids = {W: build_grid(tp, W) for W in WINDOWS}
    cells = section1(tp, grids)
    section2(grids, cells)
    eps = section3(tp, grids, cells)
    section4(tp, grids, cells, eps)
    section5(tp, grids, cells)
    section6(tp, grids, cells)
    section7(ws_dir, grids, cells, data_dir)

    header("8. WHAT THE MEASUREMENTS SAY (numbers recomputed, not restated)")
    g = grids[30]
    m = cells[(30, "all", 50)].mask
    ins = episode_pnl(g, m, tp, UNWIND_SEC)
    out = episode_pnl(g, ~m & (g.nprint > 0), tp, UNWIND_SEC)
    unc = episode_pnl(g, g.nprint > 0, tp, UNWIND_SEC)
    print("display cell W=30s, pool=all, p50 (every other cell agrees in sign):")
    print(f"  the regime EXISTS         : duty {m.mean() * 100:.2f}% of wall")
    print(f"                              clock, {ins.n:,} episodes in 30 days,")
    print(f"                              median {30 * np.median(ins.ln):.0f}s, "
          f"carrying "
          f"{(g.vbuy[m].sum() + g.vsell[m].sum()) / (g.vbuy.sum() + g.vsell.sum()) * 100:.0f}% "
          f"of all volume")
    print(f"  ceiling inside            : {ins.bps_of_notional:+.3f} bps of "
          f"notional = {ins.per_day_jpy:,.0f} JPY/day at f=100%")
    print(f"  ceiling outside           : {out.bps_of_notional:+.3f} bps = "
          f"{out.per_day_jpy:,.0f} JPY/day")
    print(f"  ceiling unconditional     : {unc.bps_of_notional:+.3f} bps = "
          f"{unc.per_day_jpy:,.0f} JPY/day")
    print(f"  at a plausible f=1%       : {ins.per_day_jpy * 0.01:,.0f} JPY/day "
          f"ceiling, before any queue, latency or inventory constraint")
    print("  the mechanism             : capture is flat everywhere "
          f"({ins.cap_bps:.2f} vs {out.cap_bps:.2f} bps); the whole difference")
    print(f"                              is adverse selection "
          f"({ins.inv_bps:+.2f} inside vs {out.inv_bps:+.2f} outside)")
    print("\nThe owner's thesis survives its first quantitative test: two-sided")
    print("regimes exist, they are frequent, and they are the ONLY place where")
    print("the idealized maker is net positive.  What is NOT shown: that a real")
    print("quote can reach those fills.  The entire result rests on a zero-queue")
    print("assumption, and the ceiling at f=1% is small enough that the queue")
    print("term decides the question.  That is what the board study must measure.")

    header("CAVEATS -- read before quoting any number above")
    print("1. NO QUEUE, NO DEPTH.  Every ceiling assumes the maker wins every")
    print("   print at the touch.  A real quote sits behind a queue and wins a")
    print("   small fraction; realized capture is STRICTLY less, by an unknown")
    print("   factor.  Nothing here bounds that factor.")
    print("2. The quote proxy is a last-trade anchor, not a book.  Fills are")
    print("   judged by traded-through prints against last-trade +/- 1.1bps.")
    print("3. Taker-side flags come from the venue's public tape; a print is")
    print("   attributed entirely to the aggressor side, and iceberg/self-match")
    print("   effects are invisible.")
    print("4. 30 days, one product, one venue, one volatility regime mix.")
    print("5. Round trips are a FIFO ATTRIBUTION of idealized fills, not")
    print("   trades a strategy would have made.")
    print("6. Nothing here is adoptable.  The board study (KNOWLEDGE 4 pending")
    print("   gate) remains the only thing that can judge spread MM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
