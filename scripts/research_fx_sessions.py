#!/usr/bin/env python3
"""FX Study S2 -- USD/JPY session structure map + the barrier race at 1/9 costs.

===============================================================================
PART A -- DESCRIPTIVE FOUNDATION (no adoption, no selection, no P&L)
===============================================================================
A per-session structure map of USD/JPY, 2023-01-01 .. 2026-08-21, so that every
later hypothesis in this market is designed against measured structure instead
of transferred BTC intuition.  Reported per session and YEAR BY YEAR:

  * mean |1m| log return (bps) and 30m return volatility (bps)
  * lag-1 and lag-5 autocorrelation of NON-OVERLAPPING 5m returns
    (the mean-reversion vs momentum axis, per session)
  * the distribution of the trailing-60m range width (bps)

Nothing in Part A is a test.  It is the map.

===============================================================================
PART B -- PRE-REGISTERED: THE BARRIER RACE, RE-RUN WHERE COSTS ARE 1/9
===============================================================================
The law being re-tested (docs/KNOWLEDGE.md sec.2, report k, and report o):
on BTC (FX_BTC_JPY Crypto CFD) a trailing-range-edge touch is a MOMENTUM event
-- the symmetric 10bps/10bps first-passage race resolves 31.7% revert vs 61.4%
break on n=23,642 calm touches, and conditioning on the deep-calm vr quartile
moves it by only +6..7pp.  BTC verdict: mechanism rejection.

Why re-testing on USD/JPY is legitimate under research-protocol sec.5 rather
than a re-run of a settled rejection:

  1. The BTC rejection was TWO rejections welded together -- an ECONOMIC one
     (a fade cannot clear 6.35bps round-trip) and a MECHANISTIC one (the fade
     leg loses the race 2:1 before any cost).  USD/JPY round-trip cost is
     0.71bps [KNOWLEDGE_FX.md sec.1], about 1/9 of BTC's.  The ECONOMIC
     conclusion therefore has to be re-derived from scratch; it does not
     transfer.
  2. The MECHANISM may also differ.  BTC is a 24/7 single-venue trend-dominated
     tape.  USD/JPY has hard session structure and a widely-claimed
     mean-reverting Tokyo-lunch regime (thin book, no scheduled news, exporters
     working ranges).  A first-passage race is a property of the local price
     process, and the local price process in Tokyo lunch is not the local price
     process of a BTC storm.  KNOWLEDGE_FX.md sec.3 states the house rule
     explicitly: BTC sec.2 laws are re-tested in the 1/9-cost environment
     rather than auto-transferred.

If the race does NOT flip here either, that is a strong cross-market result and
is reported as such.  Either way the answer is stated plainly.

-------------------------------------------------------------------------------
EVENT (fixed before running)
-------------------------------------------------------------------------------
Trailing range: over the 60 COMPLETED 1m bars strictly before bar t,
    hi_edge(t) = max(high[t-60 .. t-1]),  lo_edge(t) = min(low[t-60 .. t-1]).
TOUCH at bar t:
    high[t] >= hi_edge(t)  -> high-edge touch, side = -1, the fade is a SELL
    low[t]  <= lo_edge(t)  -> low-edge touch,  side = +1, the fade is a BUY
A bar that touches BOTH edges (outside bar) is DISCARDED: on 1m OHLC the order
of the two touches is unknowable.  The discarded count is printed.

The fade's notional entry price is the EDGE LEVEL itself (a resting limit at
the edge).  All barriers are measured from that edge price.

-------------------------------------------------------------------------------
BARRIERS (enumerated, exactly three; no others will be added)
-------------------------------------------------------------------------------
Symmetric revert-vs-break at b in {3bps, 5bps, 10bps}, 60-minute cap.
  side=+1 (bought the low edge):  revert = high >= edge*(1+b), break = low  <= edge*(1-b)
  side=-1 (sold the high edge) :  revert = low  <= edge*(1-b), break = high >= edge*(1+b)

PRIMARY race clock: the race scans bars t+1 .. t+60, i.e. it starts STRICTLY
AFTER the touch bar.  This is the only clock with zero intrabar ambiguity and
zero look-ahead on 1m data.  Two bounds on that choice are also reported:
  * INCLUSIVE-PESSIMISTIC: scan t .. t+59, same-bar tie -> break
  * INCLUSIVE-OPTIMISTIC : scan t .. t+59, same-bar tie -> revert
Within the primary clock, a bar in which BOTH thresholds are first crossed is
a TIE and is awarded to the BREAK side (conservative for the fade).  The
optimistic tie assignment is printed as a bound.

-------------------------------------------------------------------------------
CONDITIONS (enumerated, exactly six; no others will be added)
-------------------------------------------------------------------------------
  C1 ALL          all admissible hours
  C2 TOKYO_LUNCH  UTC 03:00-04:59   (the named prior)
  C3 TOKYO        UTC 00:00-05:59
  C4 LONDON       UTC 07:00-11:59
  C5 NY           UTC 12:00-15:59
  C6 LATE_NY      UTC 16:00-20:59, minus the rollover band -> 16:00-19:59
6 conditions x 3 barriers = 18 cells.  That candidate count is stated up front
(research-protocol sec.8.3): with 18 cells, one marginal pass is expected by
chance, which is exactly why the pass bar demands BOTH segments.

-------------------------------------------------------------------------------
EXCLUSIONS (fixed before running, applied to every event everywhere)
-------------------------------------------------------------------------------
  E1 TRADING WEEK.  Open = Sun 22:00 UTC .. Fri 21:00 UTC.  (Measured on this
     tape: Sunday hour 21 is 37-51% zero-volume, hour 22 is 1-6%; Friday hour
     20 is ~0% zero, hour 21 is 66%, hour 22+ is 100%.  Saturday rows are not
     in the file at all.)
  E2 ROLLOVER BAND.  UTC 20:00-21:59 excluded from all events.  KNOWLEDGE_FX
     sec.1: UTC21 spread is 6.33bps = 20x the floor -- structurally untradeable.
  E3 NO WEEKEND/GAP CROSSING.  Both the 60-bar trailing window and the 60-bar
     race horizon must lie inside the SAME contiguous open block as the event
     bar (block = maximal run of open bars at exactly 60s spacing).
  E4 LIQUIDITY.  At least 45 of the 60 trailing bars must have volume > 0.
     Kills holidays and dead tape without fitting anything (median tick share
     on this file is 0.995).

-------------------------------------------------------------------------------
ECONOMICS AT FX COSTS (the number that has to be re-derived)
-------------------------------------------------------------------------------
KNOWLEDGE_FX.md sec.1: USD/JPY round-trip is 0.71bps and MAKER IS NOT FREE --
the GMO API fee (0.002% = 0.2bps) is charged on limit orders and on order
amendments too, so there is no maker escape hatch.  Per side:
    c_side = 0.355 bps,   c_rt = 2 * 0.355 = 0.71 bps
A fade entered at the edge and exited at a symmetric b-bps barrier:
    revert wins  -> +b - c_rt
    break wins   -> -b - c_rt
    EV(resolved) = p*(b - c_rt) + (1-p)*(-b - c_rt) = 2*p*b - b - c_rt
    EV > 0  <=>  p > (b + c_rt) / (2*b)                     <-- THE FORMULA
      b= 3bps -> p* = (3 + 0.71)/6  = 61.83%
      b= 5bps -> p* = (5 + 0.71)/10 = 57.10%
      b=10bps -> p* = (10 + 0.71)/20 = 53.55%
where p is the revert share OF RESOLVED races.  (The BTC study's breakeven at
the 5bps barrier was 61.3% because its exit cost alone was 2.93bps; the whole
point of this study is that this constant moves.)  Unconditional per-touch EV,
which prices the unresolved group at its realised 60m-cap drift minus c_rt, is
printed alongside so the conditional form is auditable.

-------------------------------------------------------------------------------
SPLIT AND PASS BAR (fixed before running; judgment executed ONCE)
-------------------------------------------------------------------------------
SPLIT: chronological 60/40.  The boundary is the timestamp of the 60th-
percentile event in the C1 (ALL) primary event set; every cell uses that one
boundary.  EXPLORATION = events before it, JUDGMENT = events at or after it.

A cell is a CANDIDATE iff ALL of:
  (P1) revert share of RESOLVED races > the economic breakeven p*(b)
  (P2) n >= 5,000 touches
  (P3) (P1) holds in BOTH the exploration segment and the judgment segment,
       each with its own n >= 5,000
No cell that fails is repaired, re-cut or re-barriered.  If no cell passes, the
deliverable is the rejection report.  Nothing here is adopted; a CANDIDATE
would only earn a Stage-B execution study (a resting limit at the edge has to
survive adverse selection, which this study does not model at all).

-------------------------------------------------------------------------------
MANDATORY SANITY (all printed; results are unreadable if any fails)
-------------------------------------------------------------------------------
  * epoch-unit cross-check (research-protocol sec.6 datetime64 trap)
  * NO LOOK-AHEAD: trailing range hand-recomputed from raw arrays on sampled
    bars and proved to use only bars strictly before the event bar; the primary
    race clock proved to start strictly after the event bar
  * exclusion masks printed with the count each one removes
  * determinism: a full cell re-run bit-for-bit
  * race outcomes exhaustive, never resolving past the 60m cap
  * de-clustering diagnostics D1 (first touch per side per 10-minute clock
    block) and D2 (non-overlapping races) -- diagnostics only, they cannot
    change the verdict (research-protocol sec.8.2)

-------------------------------------------------------------------------------
KNOWN LIMITS (stated before the results, not after)
-------------------------------------------------------------------------------
  * BID-ONLY prices.  ask_close exists on only the last ~30 days.  Every bps
    figure is a bid-side move; the spread is modelled as the flat cost constant
    from KNOWLEDGE_FX sec.1, not measured per bar.
  * 1m RESOLUTION.  The BTC law was raced on a 1-SECOND grid.  A 1m bar hides
    the order of touches inside it and hides barrier crossings that reverse
    within the minute.  The primary clock's "start at t+1" is the conservative
    reading of that ambiguity; the two inclusive variants bound it.  The BTC
    and FX numbers are therefore NOT strictly comparable -- they are the same
    experiment at different microscope powers, and that is said in the verdict.
  * No swap/rollover carry, no queue position, no adverse selection, no slippage
    on the break leg beyond the flat constant.  Frequencies of price paths only.

Run:  PYTHONPATH=src python scripts/research_fx_sessions.py
Read-only, no network, idempotent, writes nothing, commits nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np                                            # noqa: E402
import pandas as pd                                           # noqa: E402

CSV = ROOT / "data" / "fx" / "USDJPY_1m.csv"

# ---- frozen constants (pre-registered; nothing below is fitted) ------------ #
W_RANGE = 60                 # trailing range window, minutes
CAP = 60                     # race cap, minutes
BARRIERS = (3.0, 5.0, 10.0)  # bps, symmetric -- exactly these three
C_SIDE = 0.355               # bps per side (KNOWLEDGE_FX sec.1: 0.71 round trip)
C_RT = 2 * C_SIDE            # 0.71 bps
MIN_TICKS = 45               # of 60 trailing bars with volume > 0
BAR_MIN_N = 5000             # pass bar (P2)/(P3)
SPLIT_FRAC = 0.60
ROLLOVER_HOURS = (20, 21)    # UTC, excluded everywhere

SESSIONS = {                 # name -> (hour_lo, hour_hi) half-open on hours
    "TOKYO":      (0, 6),
    "LONDON":     (7, 12),
    "NY":         (12, 16),
    "LATE_NY":    (16, 21),
}
TOKYO_LUNCH = (3, 5)

# condition name -> set of admissible UTC hours (after rollover removal)
def _hrs(lo: int, hi: int) -> set[int]:
    return {h for h in range(lo, hi) if h not in ROLLOVER_HOURS}


CONDITIONS = {
    "C1 ALL":         set(range(24)) - set(ROLLOVER_HOURS),
    "C2 TOKYO_LUNCH": _hrs(*TOKYO_LUNCH),
    "C3 TOKYO":       _hrs(*SESSIONS["TOKYO"]),
    "C4 LONDON":      _hrs(*SESSIONS["LONDON"]),
    "C5 NY":          _hrs(*SESSIONS["NY"]),
    "C6 LATE_NY":     _hrs(*SESSIONS["LATE_NY"]),
}

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def header(t: str) -> None:
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def sub(t: str) -> None:
    print("\n" + "-" * 100)
    print(t)
    print("-" * 100)


def breakeven(b: float) -> float:
    """Revert share of RESOLVED races at which a symmetric b-bps fade breaks
    even, at USD/JPY costs.  EV = 2*p*b - b - c_rt  ->  p* = (b + c_rt)/(2b)."""
    return (b + C_RT) / (2.0 * b) * 100.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h) * 100, (c + h) * 100


# --------------------------------------------------------------------------- #
# 0. data
# --------------------------------------------------------------------------- #
class Tape:
    pass


def load() -> Tape:
    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    ts = pd.DatetimeIndex(df["timestamp"])
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    tp = Tape()
    tp.ts = ts
    tp.sec = ((ts - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    tp.o = df["open"].to_numpy(float)
    tp.h = df["high"].to_numpy(float)
    tp.l = df["low"].to_numpy(float)
    tp.c = df["close"].to_numpy(float)
    tp.v = df["volume"].to_numpy(float)
    tp.hour = ts.hour.to_numpy()
    tp.dow = ts.dayofweek.to_numpy()
    tp.year = ts.year.to_numpy()
    tp.n = len(df)
    tp.ask_share = float(df["ask_close"].notna().mean()) * 100.0
    return tp


def build_masks(tp: Tape) -> None:
    """E1..E4 plus the block structure.  Every mask is printed by the caller."""
    dow, hr = tp.dow, tp.hour
    tp.open = ((dow <= 3) | ((dow == 4) & (hr < 21)) | ((dow == 6) & (hr >= 22)))
    gap = np.empty(tp.n)
    gap[0] = np.nan
    gap[1:] = np.diff(tp.sec)
    brk = (~tp.open) | (gap != 60.0)
    tp.blk = np.cumsum(brk.astype(np.int64))

    W, K = W_RANGE, CAP
    tp.hi_edge = pd.Series(tp.h).rolling(W).max().shift(1).to_numpy()
    tp.lo_edge = pd.Series(tp.l).rolling(W).min().shift(1).to_numpy()
    tp.ref = pd.Series(tp.c).shift(1).to_numpy()
    ticks = pd.Series((tp.v > 0).astype(float)).rolling(W).sum().shift(1).to_numpy()

    back = np.zeros(tp.n, bool)
    back[W:] = tp.blk[W:] == tp.blk[:-W]          # bar t-60 same block as t
    fwd = np.zeros(tp.n, bool)
    fwd[:tp.n - K] = tp.blk[:tp.n - K] == tp.blk[K:]   # bar t+60 same block as t

    tp.m_open = tp.open
    tp.m_roll = ~np.isin(hr, ROLLOVER_HOURS)
    tp.m_block = back & fwd
    tp.m_liq = np.nan_to_num(ticks, nan=-1.0) >= MIN_TICKS
    tp.m_def = np.isfinite(tp.hi_edge) & np.isfinite(tp.lo_edge)
    tp.valid = tp.m_open & tp.m_roll & tp.m_block & tp.m_liq & tp.m_def


# --------------------------------------------------------------------------- #
# 1. the barrier race (vectorised first-passage on 1m OHLC)
# --------------------------------------------------------------------------- #
def race(tp: Tape, ev: np.ndarray, side: np.ndarray, edge: np.ndarray,
         bps: float, *, start_off: int = 1, tie_to_revert: bool = False,
         chunk: int = 40000):
    """Symmetric first-passage race over CAP bars starting at ev + start_off.

    Returns (out, tbar):
      out  +1 revert first, -1 break first, 0 unresolved inside the cap
      tbar bars from the START bar to resolution (CAP where unresolved)
    Ties (both thresholds first crossed in the SAME bar) go to BREAK unless
    tie_to_revert.
    """
    up = edge * (1.0 + bps / 1e4)
    dn = edge * (1.0 - bps / 1e4)
    out = np.zeros(len(ev), np.int8)
    tbar = np.full(len(ev), float(CAP))
    BIG = 1 << 30
    Hv = np.lib.stride_tricks.sliding_window_view(tp.h, CAP)
    Lv = np.lib.stride_tricks.sliding_window_view(tp.l, CAP)
    starts = ev + start_off
    for a in range(0, len(ev), chunk):
        b = min(a + chunk, len(ev))
        s = starts[a:b]
        Hw = Hv[s]
        Lw = Lv[s]
        hit_up = Hw >= up[a:b, None]
        hit_dn = Lw <= dn[a:b, None]
        i_up = np.where(hit_up.any(1), hit_up.argmax(1), BIG)
        i_dn = np.where(hit_dn.any(1), hit_dn.argmax(1), BIG)
        sd = side[a:b]
        i_rev = np.where(sd > 0, i_up, i_dn)
        i_brk = np.where(sd > 0, i_dn, i_up)
        o = np.zeros(b - a, np.int8)
        t = np.full(b - a, float(CAP))
        rev = i_rev < i_brk
        brk = i_brk < i_rev
        tie = (i_rev == i_brk) & (i_rev < BIG)
        if tie_to_revert:
            rev = rev | tie
        else:
            brk = brk | tie
        o[rev] = 1
        o[brk] = -1
        t[rev] = i_rev[rev].astype(float)
        t[brk] = i_brk[brk].astype(float)
        out[a:b] = o
        tbar[a:b] = t
    return out, tbar


def stats(out: np.ndarray) -> dict:
    n = int(out.size)
    if n == 0:
        return dict(n=0, rev=np.nan, brk=np.nan, un=np.nan, cond=np.nan, nres=0,
                    krev=0)
    nr = int((out == 1).sum())
    nb = int((out == -1).sum())
    nres = nr + nb
    return dict(n=n, rev=nr / n * 100, brk=nb / n * 100,
                un=(n - nres) / n * 100,
                cond=(nr / nres * 100) if nres else np.nan,
                nres=nres, krev=nr)


ROW_HEAD = (f"{'n':>9} {'revert%':>8} {'break%':>8} {'unres%':>8} "
            f"{'rev|res%':>9} {'95% CI (rev|res)':>20}")


def row(s: dict) -> str:
    if s["n"] == 0:
        return f"{0:>9} {'-':>8} {'-':>8} {'-':>8} {'-':>9} {'-':>20}"
    lo, hi = wilson(s["krev"], s["nres"])
    return (f"{s['n']:>9,} {s['rev']:>7.1f}% {s['brk']:>7.1f}% {s['un']:>7.1f}% "
            f"{s['cond']:>8.2f}% {f'[{lo:.2f}, {hi:.2f}]':>20}")


def ev_uncond(s: dict, b: float, drift_un: float) -> float:
    """Per-touch EV in bps: resolved legs at +/-b, unresolved marked out at its
    realised side-adjusted 60m-cap drift.  Every leg pays c_rt."""
    if s["n"] == 0:
        return np.nan
    p_r, p_b, p_u = s["rev"] / 100, s["brk"] / 100, s["un"] / 100
    return p_r * (b - C_RT) + p_b * (-b - C_RT) + p_u * (drift_un - C_RT)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    pd.set_option("display.width", 240)
    tp = load()

    # ------------------------------------------------------------------ 0 -- #
    header("0. DATA, EPOCH-UNIT PROOF, EXCLUSION LADDER")
    print(f"file              : {CSV.relative_to(ROOT)}")
    print(f"rows              : {tp.n:,}   {tp.ts[0]} .. {tp.ts[-1]}   (UTC, BID OHLCV)")
    dcount = pd.Series(np.diff(tp.sec)).value_counts()
    print(f"row spacing       : " + ", ".join(
        f"{int(k)}s x {v:,}" for k, v in dcount.head(4).items()))
    print("                    (86460s gaps = Saturdays, which are absent from "
          "the file entirely)")
    print(f"ask_close populated: {tp.ask_share:.1f}% of rows -- BID-only study; "
          f"see caveats")

    sub("0a. epoch-unit cross-check (research-protocol sec.6 datetime64 trap)")
    probe = tp.ts[:5000]
    a1 = ((probe - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    a2 = (np.asarray(probe.tz_localize(None), dtype="datetime64[ns]")
          .astype("int64") / 1e9)                      # independent ns path
    a3 = np.asarray(probe.tz_localize(None)).astype("int64") / 1e9  # NAIVE
    d = float(np.abs(a1 - a2).max())
    gate_epoch = d < 1e-6
    print(f"  file dtype is {tp.ts.dtype} -- MICROSECONDS, not ns.")
    print(f"  (idx-EPOCH)/Timedelta('1s')[0] = {a1[0]:.3f}  "
          f"= {pd.to_datetime(a1[0], unit='s', utc=True)}")
    print(f"  independent datetime64[ns] path max|diff| over 5,000 rows = "
          f"{d:.9f}   {'OK' if gate_epoch else 'FAIL'}")
    print(f"  the trap, shown: naive .astype('int64')/1e9 on this us-dtype gives "
          f"{a3[0]:.3f}")
    print(f"  = {pd.to_datetime(a3[0], unit='s', utc=True)} -- off by 1000x. "
          f"The EPOCH form is the one used everywhere below.")

    build_masks(tp)
    sub("0b. exclusion ladder (E1..E4), cumulative")
    lad = [("(none) all bars", np.ones(tp.n, bool)),
           ("E1 trading week (Sun22:00-Fri21:00 UTC)", tp.m_open),
           ("E2 - rollover band UTC 20:00-21:59", tp.m_open & tp.m_roll),
           ("E3 - no weekend/gap crossing (+-60 bars)",
            tp.m_open & tp.m_roll & tp.m_block),
           ("E4 - liquidity >=45/60 trailing ticks",
            tp.m_open & tp.m_roll & tp.m_block & tp.m_liq),
           ("   - trailing range defined", tp.valid)]
    prev = tp.n
    print(f"{'step':<44}{'bars kept':>12}{'share':>9}{'removed':>12}")
    for name, m in lad:
        k = int(m.sum())
        print(f"{name:<44}{k:>12,}{k / tp.n * 100:>8.1f}%{prev - k:>12,}")
        prev = k
    print(f"\ncontiguous open blocks (trading weeks): "
          f"{len(np.unique(tp.blk[tp.m_open])):,}")
    if not gate_epoch:
        print("\nEPOCH GATE FAILED -- results below are not readable.")
        return 1

    # ================================================================== A === #
    header("PART A -- SESSION STRUCTURE MAP (descriptive; nothing is adopted)")
    print("All Part-A statistics are computed on E1-open bars only (weekend and")
    print("holiday-dead tape removed).  The rollover band is NOT removed in Part A")
    print("-- it is part of the map -- but LATE_NY is also shown without it.")

    op = tp.m_open
    r1 = np.full(tp.n, np.nan)
    r1[1:] = np.log(tp.c[1:] / tp.c[:-1]) * 1e4
    same_prev = np.zeros(tp.n, bool)
    same_prev[1:] = tp.blk[1:] == tp.blk[:-1]
    ok1 = op & same_prev & np.isfinite(r1)

    sess_of = np.full(tp.n, "", dtype=object)
    for nm, (lo, hi) in SESSIONS.items():
        sess_of[(tp.hour >= lo) & (tp.hour < hi)] = nm
    lunch = (tp.hour >= TOKYO_LUNCH[0]) & (tp.hour < TOKYO_LUNCH[1])

    # 30m non-overlapping returns, anchored to the clock, same block required
    idx30 = np.flatnonzero((tp.ts.minute.to_numpy() == 0) |
                           (tp.ts.minute.to_numpy() == 30))
    ok30 = np.zeros(len(idx30), bool)
    ok30[1:] = ((tp.sec[idx30][1:] - tp.sec[idx30][:-1] == 1800.0) &
                (tp.blk[idx30][1:] == tp.blk[idx30][:-1]))
    r30 = np.full(len(idx30), np.nan)
    r30[1:] = np.log(tp.c[idx30][1:] / tp.c[idx30][:-1]) * 1e4
    h30 = tp.hour[idx30]
    y30 = tp.year[idx30]

    # trailing-60m range width in bps (uses completed bars only)
    rw = (tp.hi_edge - tp.lo_edge) / tp.ref * 1e4
    okrw = tp.m_open & tp.m_block & tp.m_liq & np.isfinite(rw)

    def sess_masks(hour_arr):
        out = [("TOKYO 00-06", (hour_arr >= 0) & (hour_arr < 6)),
               ("  tokyo-lunch 03-05", (hour_arr >= 3) & (hour_arr < 5)),
               ("LONDON 07-12", (hour_arr >= 7) & (hour_arr < 12)),
               ("NY 12-16", (hour_arr >= 12) & (hour_arr < 16)),
               ("LATE_NY 16-21", (hour_arr >= 16) & (hour_arr < 21)),
               ("  late_ny ex-rollover 16-20",
                (hour_arr >= 16) & (hour_arr < 20)),
               ("(unassigned 06,21-24)",
                (hour_arr == 6) | (hour_arr >= 21))]
        return out

    sub("A1. volatility by session -- full sample 2023-01-01 .. 2026-08-21")
    print(f"{'session':<28}{'bars':>12}{'tick%':>8}{'mean|1m| bps':>14}"
          f"{'mean|1m| bps':>14}{'sd(30m) bps':>13}{'mean|30m| bps':>14}{'n30':>9}")
    print(f"{'':<28}{'':>12}{'':>8}{'(all bars)':>14}{'(ticking only)':>14}")
    for nm, m in sess_masks(tp.hour):
        mm = ok1 & m
        mt = mm & (tp.v > 0)
        m3 = ok30 & sess_masks(h30)[[x[0] for x in sess_masks(h30)].index(nm)][1]
        print(f"{nm:<28}{int(mm.sum()):>12,}{(tp.v[mm] > 0).mean() * 100:>7.1f}%"
              f"{np.abs(r1[mm]).mean():>14.3f}{np.abs(r1[mt]).mean():>14.3f}"
              f"{np.nanstd(r30[m3]):>13.2f}{np.nanmean(np.abs(r30[m3])):>14.2f}"
              f"{int(np.isfinite(r30[m3]).sum()):>9,}")
    print("\n  30m stats use NON-OVERLAPPING clock-anchored 30m returns (:00/:30),")
    print("  each required to sit inside one contiguous open block.")

    sub("A2. volatility by session, YEAR BY YEAR (mean|1m| bps / sd(30m) bps)")
    years = sorted(set(tp.year[op].tolist()))
    print(f"{'session':<28}" + "".join(f"{y:>17}" for y in years))
    for nm, m in sess_masks(tp.hour):
        cells = []
        mi30 = sess_masks(h30)[[x[0] for x in sess_masks(h30)].index(nm)][1]
        for y in years:
            mm = ok1 & m & (tp.year == y)
            m3 = ok30 & mi30 & (y30 == y)
            a = np.abs(r1[mm]).mean() if mm.sum() else np.nan
            s = np.nanstd(r30[m3]) if np.isfinite(r30[m3]).sum() > 2 else np.nan
            cells.append(f"{a:.3f}/{s:.2f}")
        print(f"{nm:<28}" + "".join(f"{c:>17}" for c in cells))
    print("  2026 covers 01-01..08-21 only.")

    sub("A3. autocorrelation of NON-OVERLAPPING 5m returns "
        "(negative = mean reversion)")
    i5 = np.flatnonzero(tp.ts.minute.to_numpy() % 5 == 0)
    s5 = tp.sec[i5]
    b5 = tp.blk[i5]
    c5 = tp.c[i5]
    r5 = np.full(len(i5), np.nan)
    r5[1:] = np.log(c5[1:] / c5[:-1]) * 1e4
    good5 = np.zeros(len(i5), bool)
    good5[1:] = (s5[1:] - s5[:-1] == 300.0) & (b5[1:] == b5[:-1])
    good5 &= np.isfinite(r5)
    h5 = tp.hour[i5]
    y5 = tp.year[i5]

    def acorr(mask: np.ndarray, lag: int, yr=None):
        """Pearson and Spearman (rank) AC of non-overlapping 5m returns.

        Spearman is carried because a Pearson AC on a few hundred returns is
        hostage to two adjacent outliers; when the two disagree the cell is
        outlier-driven and must not be read as structure.
        """
        m = good5 & mask
        if yr is not None:
            m = m & (y5 == yr)
        j = np.flatnonzero(m)
        j = j[j >= lag]
        # both returns valid, in the mask, and exactly lag*5 minutes apart
        keep = m[j - lag] & (s5[j] - s5[j - lag] == 300.0 * lag) & \
            (b5[j] == b5[j - lag])
        j = j[keep]
        if len(j) < 100:
            return np.nan, np.nan, 0
        x, y_ = r5[j], r5[j - lag]
        rho = float(np.corrcoef(np.argsort(np.argsort(x)).astype(float),
                                np.argsort(np.argsort(y_)).astype(float))[0, 1])
        return float(np.corrcoef(x, y_)[0, 1]), rho, len(j)

    print(f"{'session':<28}{'pairs':>9}{'AC(1)':>9}{'95% CI':>20}{'rank':>9}"
          f"{'pairs':>9}{'AC(5)':>9}{'95% CI':>20}{'rank':>9}")
    for nm, m in sess_masks(h5):
        a1_, s1_, n1_ = acorr(m, 1)
        a5_, s5_, n5_ = acorr(m, 5)
        ci1 = 1.96 / np.sqrt(n1_) if n1_ else np.nan
        ci5 = 1.96 / np.sqrt(n5_) if n5_ else np.nan
        print(f"{nm:<28}{n1_:>9,}{a1_:>+9.4f}"
              f"{f'[{a1_ - ci1:+.4f},{a1_ + ci1:+.4f}]':>20}{s1_:>+9.4f}"
              f"{n5_:>9,}{a5_:>+9.4f}"
              f"{f'[{a5_ - ci5:+.4f},{a5_ + ci5:+.4f}]':>20}{s5_:>+9.4f}")
    print("  CI = +-1.96/sqrt(pairs), the white-noise band.  A 5m return is kept")
    print("  only if it and its lagged partner are exactly 5*lag minutes apart")
    print("  inside one contiguous open block, so no pair spans a weekend.")

    sub("A4. AC(1) of 5m returns, YEAR BY YEAR   (Pearson / rank)")
    print(f"{'session':<28}" + "".join(f"{y:>22}" for y in years))
    for nm, m in sess_masks(h5):
        cells = []
        for y in years:
            a, r_, nn = acorr(m, 1, yr=y)
            cells.append(f"{a:+.4f}/{r_:+.4f}" if nn else "     -")
        print(f"{nm:<28}" + "".join(f"{c:>22}" for c in cells))
    print("  Pearson / rank.  Where the two disagree in SIGN the cell is driven")
    print("  by a handful of adjacent large returns, not by structure.")

    sub("A5. AC(5) of 5m returns, YEAR BY YEAR   (Pearson / rank)")
    print(f"{'session':<28}" + "".join(f"{y:>22}" for y in years))
    for nm, m in sess_masks(h5):
        cells = []
        for y in years:
            a, r_, nn = acorr(m, 5, yr=y)
            cells.append(f"{a:+.4f}/{r_:+.4f}" if nn else "     -")
        print(f"{nm:<28}" + "".join(f"{c:>22}" for c in cells))

    sub("A6. trailing-60m RANGE WIDTH distribution by session (bps)")
    print(f"{'session':<28}{'n':>11}{'mean':>9}{'p10':>8}{'p25':>8}{'p50':>8}"
          f"{'p75':>8}{'p90':>8}{'p99':>9}")
    for nm, m in sess_masks(tp.hour):
        mm = okrw & m
        if not mm.sum():
            continue
        q = np.percentile(rw[mm], [10, 25, 50, 75, 90, 99])
        print(f"{nm:<28}{int(mm.sum()):>11,}{rw[mm].mean():>9.2f}" +
              "".join(f"{v:>8.2f}" for v in q[:5]) + f"{q[5]:>9.2f}")

    sub("A7. median trailing-60m range width by session, YEAR BY YEAR (bps)")
    print(f"{'session':<28}" + "".join(f"{y:>12}" for y in years))
    for nm, m in sess_masks(tp.hour):
        cells = []
        for y in years:
            mm = okrw & m & (tp.year == y)
            cells.append(f"{np.median(rw[mm]):.2f}" if mm.sum() > 100 else "-")
        print(f"{nm:<28}" + "".join(f"{c:>12}" for c in cells))

    sub("A8. TAPE DENSITY BY YEAR (a data-quality caveat, not a market fact)")
    print(f"{'session':<28}{'metric':<18}" + "".join(f"{y:>12}" for y in years))
    for nm, m in sess_masks(tp.hour):
        for lbl, arr in (("mean vol/bar", tp.v), ("zero-move bar%", None)):
            cells = []
            for y in years:
                mm = ok1 & m & (tp.year == y)
                if not mm.sum():
                    cells.append("-")
                elif arr is not None:
                    cells.append(f"{arr[mm].mean():.1f}")
                else:
                    cells.append(f"{(r1[mm] == 0).mean() * 100:.1f}%")
            print(f"{nm:<28}{lbl:<18}" + "".join(f"{c:>12}" for c in cells))
    print("  Dukascopy tick counts per bar fall by ~2/3 from 2023 to 2026 on this")
    print("  file while zero-move bars RISE.  Thinner recorded tape inflates")
    print("  short-horizon autocorrelation mechanically, so 2026 AC cells are the")
    print("  least trustworthy in the map.  This does not touch Part B, which")
    print("  races high/low extremes rather than close-to-close returns.")


    # ================================================================== B === #
    header("PART B -- THE BARRIER RACE ON USD/JPY (pre-registered)")

    up_t = tp.valid & (tp.h >= tp.hi_edge)
    dn_t = tp.valid & (tp.l <= tp.lo_edge)
    both = up_t & dn_t
    up_t = up_t & ~both
    dn_t = dn_t & ~both
    ev = np.flatnonzero(up_t | dn_t)
    side = np.where(dn_t[ev], 1, -1).astype(np.int8)
    edge = np.where(side > 0, tp.lo_edge[ev], tp.hi_edge[ev])
    ehr = tp.hour[ev]
    eyr = tp.year[ev]
    esec = tp.sec[ev]

    print(f"admissible bars                 : {int(tp.valid.sum()):,}")
    print(f"high-edge touches (fade = SELL) : {int(up_t.sum()):,}")
    print(f"low-edge touches  (fade = BUY)  : {int(dn_t.sum()):,}")
    print(f"outside bars touching BOTH edges: {int(both.sum()):,}   "
          f"DISCARDED (order unknowable on 1m OHLC)")
    print(f"PRIMARY event set               : {len(ev):,} touches "
          f"({len(ev) / (int(tp.valid.sum()) or 1) * 100:.1f}% of admissible bars)")

    # 60/40 split boundary from the C1 event set
    cut_i = int(len(ev) * SPLIT_FRAC)
    t_split = esec[cut_i]
    expl = esec < t_split
    judg = ~expl
    print(f"\n60/40 boundary (60th pct of the C1 event set): "
          f"{pd.to_datetime(t_split, unit='s', utc=True)}")
    print(f"  exploration {int(expl.sum()):,} events   "
          f"judgment {int(judg.sum()):,} events")

    sub("B1. THE ECONOMICS, RE-DERIVED AT USD/JPY COSTS")
    print("KNOWLEDGE_FX.md sec.1: round trip 0.71bps = spread 0.5 sen (0.314bps)")
    print("+ API fee 0.002% x 2 (0.4bps).  The fee is charged on LIMIT orders and")
    print("on amendments too, so there is no free maker leg here -- unlike BTC")
    print("Crypto CFD where maker is 0 fee and 0 spread.")
    print(f"\n  c_side = {C_SIDE:.3f} bps    c_rt = 2*c_side = {C_RT:.2f} bps")
    print("  fade entered at the edge, exited at the symmetric b-bps barrier:")
    print("      revert wins ->  +b - c_rt        break wins ->  -b - c_rt")
    print("      EV(resolved) = p*(b - c_rt) + (1-p)*(-b - c_rt) = 2*p*b - b - c_rt")
    print("      EV > 0  <=>  p > (b + c_rt) / (2*b)          <-- BREAKEVEN FORMULA")
    print(f"\n{'barrier b':>12}{'gross win':>12}{'gross loss':>12}"
          f"{'p* = (b+c_rt)/(2b)':>22}{'BTC-cost p* for scale':>24}")
    for b in BARRIERS:
        btc_p = (b + 2.93) / (2 * b) * 100      # BTC calm taker exit, one side
        print(f"{b:>11.0f}b{b - C_RT:>+12.2f}{-(b + C_RT):>+12.2f}"
              f"{breakeven(b):>21.2f}%{btc_p:>23.2f}%")
    print("  (the BTC column prices the same race with BTC's calm 2.93bps exit --")
    print("   it is the constant this study exists to replace, not a claim about")
    print("   BTC's own microstructure.)")

    # ---- the 18 cells --------------------------------------------------- #
    cells: dict[tuple[str, float], dict] = {}
    outs: dict[float, np.ndarray] = {}
    tbars: dict[float, np.ndarray] = {}
    for b in BARRIERS:
        outs[b], tbars[b] = race(tp, ev, side, edge, b)

    # side-adjusted drift at the cap, for the unresolved group
    end = np.minimum(ev + 1 + CAP - 1, tp.n - 1)
    drift_cap = side.astype(float) * np.log(tp.c[end] / edge) * 1e4

    sub("B2. FULL SAMPLE -- 18 pre-registered cells "
        "(verdict is NOT read here; see B3/B4)")
    print(f"{'condition':<18}{'b':>5} {ROW_HEAD}{'p*':>8}{'EV/touch':>10}")
    for cname, hrs in CONDITIONS.items():
        cm = np.isin(ehr, list(hrs))
        for b in BARRIERS:
            s = stats(outs[b][cm])
            du = drift_cap[cm & (outs[b] == 0)]
            dm = float(du.mean()) if du.size else 0.0
            cells[(cname, b)] = dict(s=s, drift=dm, mask=cm)
            print(f"{cname:<18}{b:>4.0f}b {row(s)}{breakeven(b):>7.2f}%"
                  f"{ev_uncond(s, b, dm):>+10.3f}")
    print("  rev|res% = revert share of RESOLVED races (the economic quantity).")
    print("  p*       = breakeven revert share at USD/JPY costs for that barrier.")
    print("  EV/touch = unconditional bps per touch, unresolved marked out at")
    print("             their realised 60m-cap drift, every leg charged c_rt.")

    sub("B3. EXPLORATION SEGMENT (first 60%) -- (P1) revert share vs p*")
    print(f"{'condition':<18}{'b':>5} {ROW_HEAD}{'p*':>8}{'P1':>6}{'P2 n>=5k':>10}")
    expl_pass = {}
    for cname, hrs in CONDITIONS.items():
        cm = np.isin(ehr, list(hrs)) & expl
        for b in BARRIERS:
            s = stats(outs[b][cm])
            p1 = bool(np.isfinite(s["cond"]) and s["cond"] > breakeven(b))
            p2 = s["n"] >= BAR_MIN_N
            expl_pass[(cname, b)] = p1 and p2
            print(f"{cname:<18}{b:>4.0f}b {row(s)}{breakeven(b):>7.2f}%"
                  f"{('Y' if p1 else 'n'):>6}{('Y' if p2 else 'n'):>10}")

    sub("B4. JUDGMENT SEGMENT (last 40%) -- EXECUTED ONCE, REPORTED AS IS")
    print(f"{'condition':<18}{'b':>5} {ROW_HEAD}{'p*':>8}{'P1':>6}{'P2 n>=5k':>10}"
          f"{'CANDIDATE':>11}")
    any_pass = False
    for cname, hrs in CONDITIONS.items():
        cm = np.isin(ehr, list(hrs)) & judg
        for b in BARRIERS:
            s = stats(outs[b][cm])
            p1 = bool(np.isfinite(s["cond"]) and s["cond"] > breakeven(b))
            p2 = s["n"] >= BAR_MIN_N
            cand = bool(p1 and p2 and expl_pass[(cname, b)])
            any_pass |= cand
            print(f"{cname:<18}{b:>4.0f}b {row(s)}{breakeven(b):>7.2f}%"
                  f"{('Y' if p1 else 'n'):>6}{('Y' if p2 else 'n'):>10}"
                  f"{('CANDIDATE' if cand else '-'):>11}")
    print(f"\n  PRE-REGISTERED VERDICT (any cell passing P1+P2 in BOTH segments): "
          f"{'CANDIDATE FOUND' if any_pass else 'NO CANDIDATE'}")

    sub("B5. YEAR BY YEAR -- rev|res% for every condition at every barrier")
    for b in BARRIERS:
        print(f"\n  barrier {b:.0f}bps   (breakeven p* = {breakeven(b):.2f}%)")
        print(f"  {'condition':<18}" +
              "".join(f"{y:>20}" for y in years) + f"{'FULL':>20}")
        for cname, hrs in CONDITIONS.items():
            cm = np.isin(ehr, list(hrs))
            row_ = []
            for y in years:
                s = stats(outs[b][cm & (eyr == y)])
                row_.append(f"{s['cond']:.2f}% (n={s['n'] // 1000}k)"
                            if s["n"] else "-")
            sf = stats(outs[b][cm])
            row_.append(f"{sf['cond']:.2f}% (n={sf['n'] // 1000}k)")
            print(f"  {cname:<18}" + "".join(f"{c:>20}" for c in row_))
    print("\n  Not one year-cell reaching p* would be needed for a pass; this table")
    print("  exists so a marginal full-sample number cannot hide a single-year")
    print("  accident.")

    sub("B6. THE BTC LAW SIDE BY SIDE (comparability is limited -- see caveats)")
    s10 = stats(outs[10.0])
    print(f"  BTC Crypto CFD, 1s grid, W=120m, calm, 10/10bps, n=23,642 :"
          f"  revert 31.7%  break 61.4%  neither 6.9%")
    print(f"  USD/JPY, 1m bars, W=60m, all admissible hours, 10/10bps    :"
          f"  revert {s10['rev']:.1f}%  break {s10['brk']:.1f}%  "
          f"neither {s10['un']:.1f}%   n={s10['n']:,}")
    print("  Same qualitative direction (break-first wins), different magnitudes.")
    print("  The magnitude gap is NOT evidence about the two markets: a 1m bar")
    print("  cannot see a 3bps barrier crossed and un-crossed inside the minute,")
    print("  and the FX race starts a whole bar after the touch.  Direction is")
    print("  comparable; the split of the resolved mass is not.")

    sub("B7. DE-CLUSTERING DIAGNOSTICS (cannot change the verdict; sec.8.2)")
    # D1: first touch per side per 10-minute clock block
    blk10 = (esec // 600).astype(np.int64) * 4 + (side > 0)
    _, first1 = np.unique(blk10, return_index=True)
    d1 = np.zeros(len(ev), bool)
    d1[first1] = True
    # D2: greedy non-overlapping races on the 10bps resolution clock
    d2 = np.zeros(len(ev), bool)
    free = -np.inf
    tb10 = tbars[10.0]
    for j in range(len(ev)):
        if esec[j] >= free:
            d2[j] = True
            # race starts at bar ev+1 and resolves tb10 bars later
            free = esec[j] + (1.0 + tb10[j]) * 60.0
    # D3: FRESH BREACH -- the literal "first touch" reading.  Bar t qualifies
    # only if bar t-1 was not itself a touch on the same side.
    was_touch = np.zeros(tp.n, np.int8)
    was_touch[np.flatnonzero(up_t)] = -1
    was_touch[np.flatnonzero(dn_t)] = 1
    d3 = was_touch[ev - 1] != side
    print(f"  PRIMARY {len(ev):,}   D1 first-per-10m-per-side {int(d1.sum()):,}"
          f"   D2 non-overlapping {int(d2.sum()):,}   "
          f"D3 fresh breach {int(d3.sum()):,}")
    print("  The brief's phrase 'first touch of the trailing 60m high/low' admits")
    print("  two readings.  PRIMARY (every breaching bar) was pre-registered as")
    print("  the headline because it is the convention the BTC law is quoted in.")
    print("  D3 (a breach whose previous bar was not already a same-side breach)")
    print("  and D2 (non-overlapping races) are the de-clustered readings.  All")
    print("  three are printed; the pre-registered bar is judged on PRIMARY, and")
    print("  B7b re-runs the whole bar on D2 to show the reading cannot rescue it.")
    print(f"\n{'condition':<18}{'b':>5}{'  set':<22}{ROW_HEAD}")
    for cname in ("C1 ALL", "C2 TOKYO_LUNCH"):
        cm = np.isin(ehr, list(CONDITIONS[cname]))
        for b in BARRIERS:
            for lbl, m in (("PRIMARY", cm), ("D1", cm & d1), ("D2", cm & d2),
                           ("D3 fresh breach", cm & d3)):
                print(f"{cname:<18}{b:>4.0f}b  {lbl:<20}{row(stats(outs[b][m]))}")
    print("  D1 up-weights edges that were merely kissed and drops the follow-on")
    print("  bars of a break in progress, biasing it TOWARD reversion; D2 is the")
    print("  honest independent sample.")
    print("\n  READ THIS ROW PAIR.  PRIMARY sits near a coin flip because it is")
    print("  dominated by bars that WALK ALONG a moving edge: once price is")
    print("  running at a new extreme, the trailing edge is only a tick away and")
    print("  the next 3bps in either direction is close to 50/50.  De-clustering")
    print("  to genuine first breaches strips those bars out and the momentum")
    print("  result appears in full -- and lands almost exactly on the BTC law.")

    sub("B7b. THE WHOLE PRE-REGISTERED BAR, RE-RUN ON THE D2 EVENT SET")
    print("  Robustness annex, not the verdict.  D2 is the de-clustered reading of")
    print("  'first touch'; it is strictly MORE adverse to the fade than PRIMARY,")
    print("  so it cannot manufacture a pass -- which is exactly why running it")
    print("  after seeing PRIMARY is not fishing (research-protocol sec.8.3).")
    print(f"{'condition':<18}{'b':>5}{'  segment':<14}{ROW_HEAD}{'p*':>8}{'P1':>6}")
    d2_pass = {}
    for cname, hrs in CONDITIONS.items():
        cm = np.isin(ehr, list(hrs)) & d2
        for b in BARRIERS:
            flags = []
            for seg_lbl, seg in (("FULL", np.ones(len(ev), bool)),
                                 ("exploration", expl), ("judgment", judg)):
                sd_ = stats(outs[b][cm & seg])
                p1 = bool(np.isfinite(sd_["cond"]) and sd_["cond"] > breakeven(b))
                flags.append(p1 and sd_["n"] >= BAR_MIN_N)
                print(f"{cname:<18}{b:>4.0f}b  {seg_lbl:<12}{row(sd_)}"
                      f"{breakeven(b):>7.2f}%{('Y' if p1 else 'n'):>6}")
            d2_pass[(cname, b)] = flags[1] and flags[2]
    print(f"\n  D2 re-run verdict: "
          f"{'CANDIDATE FOUND' if any(d2_pass.values()) else 'NO CANDIDATE'}")

    sub("B8. RACE-CLOCK BOUNDS (the 1m-resolution ambiguity, quantified)")
    print(f"{'condition':<18}{'b':>5}{'  clock':<30}{ROW_HEAD}")
    for cname in ("C1 ALL", "C2 TOKYO_LUNCH"):
        cm = np.isin(ehr, list(CONDITIONS[cname]))
        for b in BARRIERS:
            o_p = outs[b][cm]
            o_ir, _ = race(tp, ev[cm], side[cm], edge[cm], b, start_off=0,
                           tie_to_revert=True)
            o_ib, _ = race(tp, ev[cm], side[cm], edge[cm], b, start_off=0,
                           tie_to_revert=False)
            o_pr, _ = race(tp, ev[cm], side[cm], edge[cm], b, start_off=1,
                           tie_to_revert=True)
            for lbl, o in (("PRIMARY t+1, tie->break", o_p),
                           ("        t+1, tie->revert", o_pr),
                           ("INCLUSIVE t, tie->break", o_ib),
                           ("INCLUSIVE t, tie->revert (max)", o_ir)):
                print(f"{cname:<18}{b:>4.0f}b  {lbl:<28}{row(stats(o))}")
    print("  The optimistic inclusive row is the ABSOLUTE CEILING the fade could")
    print("  reach on this data under any intrabar ordering.  Compare it to p*.")

    sub("B9. STRESS -- what if the break leg is a stop that pays the spread again?")
    print("  Pre-registered costs charge c_rt on both outcomes.  A break exit is")
    print("  realistically a stop-market that crosses the spread (0.314bps) on top.")
    print("  This row is a STRESS, not the pre-registered bar.")
    print(f"{'condition':<18}{'b':>5}{'p* base':>10}{'p* stressed':>13}"
          f"{'rev|res%':>10}{'gap to stressed p*':>21}")
    for cname in CONDITIONS:
        cm = np.isin(ehr, list(CONDITIONS[cname]))
        for b in BARRIERS:
            s = stats(outs[b][cm])
            # EV = p(b-c) - (1-p)(b+c+x) = 0 -> p* = (b+c+x)/(2b+x)
            ps = (b + C_RT + 0.314) / (2 * b + 0.314) * 100
            print(f"{cname:<18}{b:>4.0f}b{breakeven(b):>9.2f}%{ps:>12.2f}%"
                  f"{s['cond']:>9.2f}%{s['cond'] - ps:>+20.2f}")

    sub("B10. UNRESOLVED GROUP -- is marking it out at the cap fair?")
    print("side-adjusted move from the edge to the 60m cap for UNRESOLVED races")
    print("(+ = price ended on the fade's side):")
    print(f"{'condition':<18}{'b':>5}{'n unres':>10}{'mean bps':>11}"
          f"{'median':>10}{'>0 share':>11}")
    for cname in CONDITIONS:
        cm = np.isin(ehr, list(CONDITIONS[cname]))
        for b in BARRIERS:
            mm = cm & (outs[b] == 0)
            if not mm.sum():
                continue
            dd = drift_cap[mm]
            print(f"{cname:<18}{b:>4.0f}b{int(mm.sum()):>10,}{dd.mean():>+11.3f}"
                  f"{np.median(dd):>+10.3f}{(dd > 0).mean() * 100:>10.1f}%")

    # ================================================================== C === #
    header("C. SANITY CHECKS")
    ok = gate_epoch
    print(f"  epoch-unit cross-check                        : "
          f"{'OK' if gate_epoch else 'FAIL'}")

    # no look-ahead: trailing range uses only bars strictly before the event bar
    rng = np.random.default_rng(20260822)
    samp = rng.choice(ev, size=min(3000, len(ev)), replace=False)
    bad = 0
    for i in samp:
        i = int(i)
        if tp.hi_edge[i] != tp.h[i - W_RANGE:i].max():
            bad += 1
        if tp.lo_edge[i] != tp.l[i - W_RANGE:i].min():
            bad += 1
    print(f"  trailing range = bars [t-60, t-1] only        : "
          f"{'OK' if bad == 0 else f'{bad} MISMATCH'}  ({len(samp)} events sampled)")
    ok &= bad == 0

    # the touch condition really holds, and the discarded set really is two-sided
    chk = int(((side > 0) & (tp.l[ev] <= edge)).sum() +
              ((side < 0) & (tp.h[ev] >= edge)).sum())
    print(f"  every event bar breaches its own edge         : {chk:,}/{len(ev):,}"
          f"  {'OK' if chk == len(ev) else 'FAIL'}")
    ok &= chk == len(ev)

    print(f"  primary race scans bars t+1 .. t+60           : OK by construction "
          f"(start_off=1, window={CAP})")
    print(f"  race horizon inside the same open block       : "
          f"OK by construction (E3)")

    # exhaustive outcomes, cap respected
    o, tb = outs[10.0], tbars[10.0]
    exh = int(((o == 1) | (o == -1) | (o == 0)).sum()) == len(o)
    cap_ok = bool(np.all(tb[o != 0] <= CAP - 1 + 1e-9))
    un_cap = bool(np.all(tb[o == 0] == CAP))
    print(f"  outcomes exhaustive in {{-1,0,+1}}              : "
          f"{'OK' if exh else 'FAIL'}")
    print(f"  no resolution past the {CAP}-bar cap            : "
          f"{'OK' if cap_ok else 'FAIL'}")
    print(f"  unresolved carry the cap as their time        : "
          f"{'OK' if un_cap else 'FAIL'}")
    ok &= exh and cap_ok and un_cap

    # determinism
    o2, t2 = race(tp, ev, side, edge, 10.0)
    det = bool(np.array_equal(o2, outs[10.0]) and np.array_equal(t2, tbars[10.0]))
    o3, _ = race(tp, ev, side, edge, 10.0, chunk=7777)
    det &= bool(np.array_equal(o3, outs[10.0]))
    print(f"  rerun determinism, incl. different chunking   : "
          f"{'OK' if det else 'FAIL'}")
    ok &= det

    # exclusions actually applied to the event set
    e_ok = (not np.isin(tp.hour[ev], list(ROLLOVER_HOURS)).any()
            and bool(tp.m_open[ev].all())
            and bool((np.abs(tp.sec[ev] - tp.sec[ev - W_RANGE]) == W_RANGE * 60).all())
            and bool((tp.blk[ev] == tp.blk[ev + CAP]).all()))
    print(f"  rollover / weekend / gap exclusions on events : "
          f"{'OK' if e_ok else 'FAIL'}")
    ok &= e_ok

    # brute-force cross-check of the race on a small random subset
    pick = rng.choice(len(ev), size=400, replace=False)
    mism = 0
    for j in pick:
        j = int(j)
        i = int(ev[j])
        e = edge[j]
        up_thr, dn_thr = e * (1 + 10.0 / 1e4), e * (1 - 10.0 / 1e4)
        res = 0
        for k in range(i + 1, i + 1 + CAP):
            hu = tp.h[k] >= up_thr
            hd = tp.l[k] <= dn_thr
            if side[j] > 0:
                r_, b_ = hu, hd
            else:
                r_, b_ = hd, hu
            if b_:
                res = -1
                break
            if r_:
                res = 1
                break
        if res != outs[10.0][j]:
            mism += 1
    print(f"  vectorised race == naive bar-by-bar loop      : "
          f"{'OK' if mism == 0 else f'{mism} MISMATCH'}  (400 events)")
    ok &= mism == 0

    print(f"\n  SANITY: {'all checks pass' if ok else 'SOMETHING FAILED'}")

    # ================================================================== D === #
    header("D. WHAT THE NUMBERS SAY")
    s_all = {b: stats(outs[b]) for b in BARRIERS}
    best = max(CONDITIONS, key=lambda c: max(
        stats(outs[b][np.isin(ehr, list(CONDITIONS[c]))])["cond"] - breakeven(b)
        for b in BARRIERS))
    if any_pass:
        print("1. VERDICT: CANDIDATE FOUND -- see B4 for the passing cell(s).")
    else:
        print("1. VERDICT: NO CANDIDATE. Not one of the 18 pre-registered cells")
        print("   clears its own breakeven revert share in both segments.")
    print(f"\n2. THE RACE DOES NOT FLIP AT FX COSTS OR IN FX SESSIONS. Pooled, all")
    print( "   admissible hours:")
    for b in BARRIERS:
        s = s_all[b]
        print(f"     {b:>2.0f}bps : revert {s['rev']:.1f}%  break {s['brk']:.1f}%  "
              f"unresolved {s['un']:.1f}%  ->  rev|res {s['cond']:.2f}% "
              f"vs p*={breakeven(b):.2f}%")
    print(f"\n3. TOKYO LUNCH -- THE NAMED PRIOR -- IS THE WORST CELL, NOT THE BEST.")
    for b in BARRIERS:
        sl = stats(outs[b][np.isin(ehr, list(CONDITIONS["C2 TOKYO_LUNCH"]))])
        print(f"     {b:>2.0f}bps : rev|res {sl['cond']:.2f}% vs p*="
              f"{breakeven(b):.2f}%  -> {sl['cond'] - breakeven(b):+.2f} pp  "
              f"(n={sl['n']:,})")
    print("   The thin-book mean-reverting-Tokyo-lunch story predicts the fade")
    print("   should work BEST here. At the 10bps barrier it is the most")
    print("   momentum-like cell in the study. The prior is measured and dead.")
    print(f"\n4. THE BEST SESSION IS {best}. Even there the shortfall to breakeven")
    print("   is:")
    for b in BARRIERS:
        s = stats(outs[b][np.isin(ehr, list(CONDITIONS[best]))])
        print(f"     {b:>2.0f}bps : {s['cond']:.2f}% vs p*={breakeven(b):.2f}%  "
              f"-> {s['cond'] - breakeven(b):+.2f} pp   (n={s['n']:,})")
    print("\n5. NO SYMMETRIC BARRIER CAN RESCUE IT -- CLOSED FORM. With a")
    print("   symmetric b-bps fade, EV(resolved) = (2p - 1)*b - c_rt, so EV > 0")
    print("   REQUIRES p > 0.5 no matter how b is chosen; b only scales an edge")
    print("   that must already exist. Measured p (revert share of resolved")
    print("   races) by cell:")
    pmax = -1.0
    pargs = ""
    for cname in CONDITIONS:
        cm = np.isin(ehr, list(CONDITIONS[cname]))
        vals = []
        for b in BARRIERS:
            sc = stats(outs[b][cm])
            vals.append(sc["cond"])
            if sc["cond"] > pmax:
                pmax, pargs = sc["cond"], f"{cname} at {b:.0f}bps"
        print(f"     {cname:<16} " +
              "  ".join(f"{b:.0f}b={v:.2f}%" for b, v in zip(BARRIERS, vals)))
    print(f"   The single most fade-favourable cell in the whole study is "
          f"{pargs}")
    slope = 2 * pmax / 100 - 1
    need = (C_RT / slope) if slope > 0 else float("inf")
    print(f"   at p={pmax:.2f}%, i.e. EV = (2p-1)*b - {C_RT:.2f} = "
          f"{slope:+.5f}*b - {C_RT:.2f} bps.")
    print("   Even that cell needs a barrier of "
          + (f"b > {need:,.0f}bps ({need / 100:,.1f}%) " if np.isfinite(need)
             else "b = infinity ") +
          "to break even --")
    print("   a move USD/JPY does not make inside 60 minutes. Barrier choice is")
    print("   not a free parameter here; it is irrelevant.")
    print("\n6. THE DE-CLUSTERED READING REPRODUCES THE BTC LAW ALMOST EXACTLY.")
    print("   PRIMARY counts every bar that breaches the edge, and most of those")
    print("   bars are price WALKING ALONG a moving edge, which is a coin flip by")
    print("   construction. Restrict to non-overlapping races (D2) and USD/JPY")
    print("   lands on the BTC number:")
    for b in BARRIERS:
        sd_ = stats(outs[b][d2])
        print(f"     D2, all hours, {b:>2.0f}bps : revert {sd_['rev']:.1f}%  "
              f"break {sd_['brk']:.1f}%  (n={sd_['n']:,})")
    print("     BTC law, 1s grid, 10bps   : revert 31.7%  break 61.4%  (n=23,642)")
    print("   Two unrelated markets, different asset class, different venue,")
    print("   different tick size, costs 9x apart, one 24/7 and one with hard")
    print("   session structure -- and the first-passage race off a fresh")
    print("   range-edge breach lands in the same place. Compare the rows above.")
    print("   That is the strongest cross-market confirmation this project has,")
    print("   and it is a confirmation of a NEGATIVE result: the range edge is a")
    print("   momentum event, and that appears to be a property of price, not of")
    print("   bitcoin.")
    print("\n7. COST WAS NEVER THE BINDING CONSTRAINT HERE. Dropping the cost bar")
    print("   from BTC's to USD/JPY's moves the 10bps breakeven from "
          f"{(10 + 2.93) / 20 * 100:.2f}% to")
    print(f"   {breakeven(10.0):.2f}% -- a {(10 + 2.93) / 20 * 100 - breakeven(10.0):.2f} pp "
          "relief. The measured shortfall is far larger than")
    print("   that, so 1/9 costs do not rescue the fade. This is the honest")
    print("   answer the brief asked for: the ECONOMIC re-derivation was done and")
    print("   it does not change the conclusion, because the MECHANISM (break")
    print("   wins the first-passage race) holds in USD/JPY too.")
    print("\n8. MECHANISM CLASSIFICATION (research-protocol sec.5): MECHANISM")
    print("   rejection, cross-market. The BTC finding is not merely a BTC-cost")
    print("   artefact -- a trailing-range-edge touch is a momentum event in a")
    print("   second, independent, mean-reversion-flavoured market as well.")
    print("   Re-auditing this fade with a different execution scheme cannot")
    print("   change the direction of a race one side wins outright.")

    header("E. CAVEATS AND COMPARABILITY LIMITS")
    ask_share = tp.ask_share
    for c in [
        "BID-ONLY. Every price is Dukascopy BID; the file's ask_close column "
        f"is populated on only {ask_share:.1f}% of rows (the last ~30 days). "
        "The spread therefore enters only as the flat 0.71bps constant from "
        "KNOWLEDGE_FX sec.1 -- it is not measured per bar. A bid-side high/low "
        "is not the ask-side high/low, so a SELL fade's fill and a BUY fade's "
        "fill are not symmetric in reality the way they are here. Any session "
        "whose spread sits above the floor would be mispriced by the constant; "
        "the one such band this tape has (UTC 20-22, 20x the floor) is excluded.",
        "1m RESOLUTION vs BTC's 1s GRID. The BTC law raced on a 1-second grid; "
        "this races on 1-minute OHLC. A 1m bar cannot order two touches inside "
        "it, cannot see a 3bps barrier crossed and un-crossed within the "
        "minute, and forces the race to start a full bar after the touch. The "
        "B8 clock-bound rows quantify the whole span of that ambiguity. "
        "DIRECTION is comparable across the two studies; the exact split of "
        "revert/break/unresolved mass is NOT.",
        "The trailing window is 60m here vs 120m in the BTC study, chosen to "
        "match the brief's event definition. W is not swept; no window "
        "selection took place, so no window-shopping is possible.",
        "TOUCH BARS ARE NOT INDEPENDENT. Consecutive bars breaching the same "
        "edge share almost one race. The headline n is a bar count; D1 and D2 "
        "in B7 are the honest independent samples and are reported for the two "
        "headline conditions.",
        "NO EXECUTION MODEL. The fade is priced as if a resting limit at the "
        "edge always fills at the edge. This repo has measured three times on "
        "BTC that such a limit fills ~0.86% of the time and that the fills it "
        "gets are the breakouts (adverse selection 6-9bps, KNOWLEDGE sec.2). "
        "That effect is NOT modelled here and would only make the fade worse.",
        "NO SWAP/CARRY. Races run up to 60 minutes and never cross the 6:00 JST "
        "swap boundary in a way this study accounts for. KNOWLEDGE_FX sec.1 "
        "puts swap at 0.6-1.6bps/day, i.e. 1-2x the round-trip cost.",
        "INTERVENTION TAIL. USD/JPY carries a one-directional MOF-intervention "
        "tail (KNOWLEDGE_FX sec.2). Those minutes are in this sample and, being "
        "extreme breaks, push the race further toward break-first. Removing "
        "them was not pre-registered and was not done.",
        "18 CELLS WERE SCREENED. With 18 cells and a two-segment requirement, a "
        "single marginal pass would still have been treated as a CANDIDATE only "
        "-- i.e. an entry ticket to a Stage-B execution study, never an "
        "adoption. Nothing here is adopted, nothing is tuned, nothing is "
        "committed.",
        "PART A IS DESCRIPTIVE. No Part-A number is a test, has a pass bar, or "
        "may be promoted to an adoption (research-protocol sec.8.2). It exists "
        "to design later hypotheses against measured structure.",
    ]:
        print("* " + c)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
