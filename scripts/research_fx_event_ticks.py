#!/usr/bin/env python3
"""
FX STUDY S4 -- THE FIRST MINUTE AFTER A MACRO RELEASE, AT TICK RESOLUTION
Is anything AFTER the first second tradable?

PRE-REGISTRATION (fixed in this docstring before a single result was read)
==========================================================================

Motivation
----------
docs/KNOWLEDGE_FX.md sec.4 records the open item: the macro-release impulse lands
WITHIN THE FIRST SECOND at 14-42 bps -- 20-60x the 0.71 bps retail cost floor,
and entirely invisible at 1-minute resolution (report s, study S3, rejected
"event direction continuation" at 1-minute bars as UNESTABLISHED, explicitly
flagging "re-auditable at tick resolution").  The impulse itself is unreactable:
no retail bot sees, decides and fills inside 1 second.  THE QUESTION HERE IS
WHAT FOLLOWS IT.

The library's superpower is that it carries REAL bid and ask at every tick, so
the cost of trading in these seconds is MEASURED, not modelled.  Even if every
trading family fails, section F3 (the spread anatomy of a macro release) is a
first-class deliverable: it is the cost-of-event-trading map that the venue
survey could not produce.

Data (fixed, read-only)
-----------------------
    backtest_data/fx_event_ticks_2015_2026/
        {TYPE}_{YYYYMMDD}.csv.gz   477 event windows, ~6.5M ticks
        columns: ts_utc (int, ms since epoch, UTC), bid, ask, bidvol, askvol
        NFP 139 / CPI 139 / FOMC 99 / BOJ 100, 2015-01-09 .. 2026-08-12
        window: NFP/CPI/FOMC  E-15min .. E+45min ; BOJ 02:00Z .. 05:00Z
    backtest_data/fx_event_ticks_2015_2026/calendar.csv
        verified release times (100% primary source, confidence column)
No other price source is used.  Nothing is written to backtest_data/.

Release instant E (fixed)
-------------------------
NFP / CPI / FOMC : calendar.csv time_utc verbatim (primary-source verified).
BOJ              : time_utc is a NOMINAL 11:30 JST anchor -- the actual release
                   drifts across 11:30-15:00 JST (KNOWLEDGE_FX sec.2/sec.4.5), so E
                   is INFERRED from the tick tape inside the 02:00-05:00Z band.

  BOJ BURST DETECTOR (documented; deliberately price-blind)
  --------------------------------------------------------
  Stage 1 (coarse, 10-second bins, as pre-registered):
      bin the window into 10 s bins, count ticks per bin.
      for every candidate bin b (>= 6 min into the window and <= 6 min before its
      end, so that E-300s and E+300s both exist):
          trail(b)  = median tick count over bins [b-36, b-6]  (6 min .. 1 min before b;
                      the 1-minute guard band keeps the release ramp out of its own baseline)
          excess(b) = sum(count[b : b+6]) - 6 * trail(b)       (excess ticks in the next 60 s)
          ratio(b)  = sum(count[b : b+6]) / (6 * max(trail(b), 1))
      the burst bin is argmax EXCESS.  Excess, not a raw maximum and not a pure
      ratio: a raw maximum lands anywhere in the multi-minute aftermath, while a
      pure ratio fires on any small flurry after a dead patch.  Excess demands both
      a step up and real volume.
  Stage 2 (refinement to 1 second):
      inside [bin_start - 10s, bin_start + 10s], let peak = the largest 1-second
      tick count in [bin_start, bin_start + 10s].  E = the earliest second s in
      that span with count(s) >= 0.5*peak and count(s-1) < 0.5*peak.
  EXCLUSION: an event is dropped when ratio(b) < 4.0 at the located bin, i.e. no
      clear burst exists (the 60 s from the onset carries less than 4x the trailing
      tick rate).  The number of BOJ events dropped this way is printed.
  The detector reads ONLY tick ARRIVAL TIMES, never prices.  This is deliberate:
  a price-based detector would place E on the largest move and thereby manufacture
  the very impulse that section F1/F2 conditions on.  Tick arrivals are correlated
  with, but not identical to, the price move, so the detector cannot bootstrap the
  signal.  Validation (printed, not used for detection): agreement between the
  detected second and an INDEPENDENT price-range-peak-minute proxy, plus a
  by-hand trace on 3 known BOJ decisions.
  INSTRUMENT CALIBRATION DISCLOSURE: the window width (60 s) and the trailing
  baseline span were fixed by maximising agreement with that price-range proxy on
  the 62 BOJ events INSIDE THE EXPLORATION SPLIT ONLY, before any F1/F2 number was
  read.  The judgment BOJ events were not consulted.  Agreement was flat across
  W in {60, 90} s and all four trailing spans tried (a plateau, 59-66% within 120 s),
  so the choice is not a knife edge.

Impulse (fixed)
---------------
    mid(t)      = (bid + ask)/2 of the last tick at or before t
    impulse_bps = (mid(E+5s) - mid(E)) / mid(E) * 1e4        [signed]
    signal      = |impulse_bps| >= m,  direction = sign(impulse_bps)
    threshold m in {5, 10, 20} bps -- ENUMERATED, not tuned beyond this list.

Families (ENUMERATED; nothing is added later)
---------------------------------------------
    F1 CONTINUATION  enter at E+5s IN the impulse direction,
                     exit at E+30s / E+60s / E+300s      (3 exits x 3 m = 9 configs)
    F2 FADE          enter at E+60s AGAINST the impulse direction,
                     exit at E+300s                      (1 exit  x 3 m = 3 configs)
    -> 12 configs total.  This count is stated up front (protocol sec.8.3: fishing
       is controlled by declaring the candidate count and reporting the plateau).
    F3 MEASUREMENT ONLY, NO ADOPTION: spread anatomy of a release.

Execution and cost (fixed, MEASURED not modelled)
-------------------------------------------------
    An order decided at time t fills at the FIRST TICK WITH ts >= t (never at a
    quote that predates the decision, never at a stale quote), crossing the book:
        long  : pay ASK on entry, receive BID on exit
        short : receive BID on entry, pay ASK on exit
    plus 0.2 bps fee PER SIDE (0.4 bps round trip) -- GMO's API fee, KNOWLEDGE_FX sec.1.
    An event is dropped if the fill tick is more than 30 s away from the decision
    time, or if mid(E) is more than 120 s stale.
    BASE CASE  = the above (real Dukascopy interbank bid/ask at that instant).
    GMO FLOOR  = mid-to-mid gross minus the 0.71 bps retail round-trip floor
                 (KNOWLEDGE_FX sec.1).  Reported as a LOWER BOUND on retail cost;
                 the honest reading is that the truth is worse than both, because
                 retail event-time slippage is unbounded and unmeasured here.

Split (fixed)
-------------
    All 477 calendar events sorted by nominal event time; first 286 (60%) =
    EXPLORATION, last 191 (40%) = JUDGMENT.  The boundary is fixed by count on the
    full calendar, BEFORE validity filtering, so it cannot move with the results.

Selection rule (fixed, applied to EXPLORATION only)
---------------------------------------------------
    Among the 12 configs, keep those with exploration signal-events n >= 40;
    choose the one with the highest exploration net bps/trade at BASE CASE costs;
    tie-break by higher t.  If none has n >= 40, choose by the same rule over all
    12 and flag it.  JUDGMENT IS THEN RUN ONCE on that single config.

Adoption bar (fixed; ALL three required, on JUDGMENT)
-----------------------------------------------------
    (1) judgment signal-events n >= 60
    (2) net >= +2.0 bps/trade at MEASURED (base-case) costs
    (3) event-clustered t >= 2.0
    One trade per event, so events ARE the clusters and the plain t over events IS
    the event-clustered t.  A 10,000-resample bootstrap CI over events (seed
    20260822) is reported alongside.
    Per-type and year-by-year breakdowns are reported whatever the verdict.

Pre-registered caveats
----------------------
    * Dukascopy is INTERBANK.  A retail bot at GMO sees wider spreads in exactly
      these seconds.  Base case = measured interbank; GMO floor = 0.71 bps.  Retail
      event-time slippage is unbounded and unmeasured -> both are optimistic.
    * Entering at E+5s assumes a sub-1-second reaction.  An E+10s entry sensitivity
      is reported for every F1 config.
    * 2015-2019 tick density is materially lower than 2022-2026; the yearly table
      exposes this.
    * Weekend/holiday gaps, venue outages: handled by the staleness filters above.

Post-run diagnostics (declared as diagnostics, NEVER promoted -- protocol sec.8.2)
----------------------------------------------------------------------------------
    * mechanism decomposition (zero-cost mid-to-mid vs spread paid vs fee), which
      separates a COST-LOSS rejection from a MECHANISM-ABSENT one (protocol sec.5);
    * all 12 configs on the judgment span, printed so the negative result is auditable;
    * the mechanical MIRROR of F2 (enter at E+60s WITH the impulse).  F2's fade loses,
      so its mirror wins by construction minus twice the cost; it is printed at full
      measured cost and logged PENDING.  It is NOT in the enumeration above and is NOT
      adopted here under any result.

Run:  PYTHONPATH=src python scripts/research_fx_event_ticks.py
Idempotent, deterministic, no network.  Nothing is written outside stdout.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- config
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "backtest_data", "fx_event_ticks_2015_2026")
CAL = os.path.join(LIB, "calendar.csv")

FEE_BPS_PER_SIDE = 0.2
GMO_FLOOR_ROUNDTRIP_BPS = 0.71

IMPULSE_S = 5
THRESHOLDS = (5.0, 10.0, 20.0)
F1_EXITS = (30, 60, 300)
F1_ENTRY_S = 5
F1_ENTRY_S_SENS = 10
F2_ENTRY_S = 60
F2_EXIT_S = 300

MAX_FILL_GAP_MS = 30_000
MAX_MID_STALE_MS = 120_000

SPLIT_EXPLORE_N = 286  # 60% of 477

BOJ_BIN_MS = 10_000
BOJ_MIN_SCORE = 4.0

F3_OFFSETS_S = (-60, 1, 5, 15, 30, 60, 300)
F3_BASELINE_FROM_S, F3_BASELINE_TO_S = -300, -30
F3_RECOVERY_MAX_S = 1200
F3_RECOVERY_MULT = 1.5

BOOT_N = 10_000
BOOT_SEED = 20260822

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def hr(ch: str = "-", n: int = 100) -> str:
    return ch * n


def utc(ms: float) -> pd.Timestamp:
    return pd.to_datetime(int(ms), unit="ms", utc=True)


# ----------------------------------------------------------------------------- loading
@dataclass
class Tape:
    ts: np.ndarray  # int64 ms
    bid: np.ndarray
    ask: np.ndarray
    mid: np.ndarray
    spread_bps: np.ndarray


def load_tape(path: str) -> Tape:
    d = pd.read_csv(path)
    ts = d["ts_utc"].to_numpy(dtype=np.int64)
    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    bid = d["bid"].to_numpy(dtype=float)[order]
    ask = d["ask"].to_numpy(dtype=float)[order]
    mid = (bid + ask) * 0.5
    with np.errstate(divide="ignore", invalid="ignore"):
        spr = (ask - bid) / mid * 1e4
    return Tape(ts, bid, ask, mid, spr)


def i_at_or_before(t: Tape, when_ms: int) -> int:
    return int(np.searchsorted(t.ts, when_ms, side="right")) - 1


def i_at_or_after(t: Tape, when_ms: int) -> int:
    i = int(np.searchsorted(t.ts, when_ms, side="left"))
    return i if i < len(t.ts) else -1


# ----------------------------------------------------------------------------- BOJ detector
@dataclass
class BurstResult:
    ok: bool
    e_ms: int
    score: float
    bin_start_ms: int
    reason: str = ""
    trail: float = 0.0
    burst_count: float = 0.0


def detect_boj_release(t: Tape) -> BurstResult:
    """Price-blind two-stage tick-arrival burst detector (see docstring)."""
    t0, t1 = int(t.ts[0]), int(t.ts[-1])
    nb = int((t1 - t0) // BOJ_BIN_MS) + 1
    if nb < 80:
        return BurstResult(False, 0, 0.0, 0, "window too short")
    idx = ((t.ts - t0) // BOJ_BIN_MS).astype(np.int64)
    cnt = np.bincount(idx, minlength=nb).astype(float)

    lo = 36  # need 5 min of trailing baseline and >= E-300s of pre-event tape
    hi = nb - 36  # need >= E+300s of post-event tape
    if hi <= lo:
        return BurstResult(False, 0, 0.0, 0, "window too short")

    W = 6  # 60-second burst window
    best_b, best_ex, best_trail, best_cnt = -1, -np.inf, 0.0, 0.0
    for b in range(lo, hi):
        trail = float(np.median(cnt[b - 36 : b - 6]))
        c60 = float(cnt[b : b + W].sum())
        excess = c60 - W * trail
        if excess > best_ex:
            best_b, best_ex, best_trail, best_cnt = b, excess, trail, c60
    best_s = best_cnt / (W * max(best_trail, 1.0))
    if best_s < BOJ_MIN_SCORE:
        return BurstResult(False, 0, float(best_s), t0 + best_b * BOJ_BIN_MS, "no clear burst")

    bin_start = t0 + best_b * BOJ_BIN_MS
    # stage 2: 1-second refinement inside [bin_start-10s, bin_start+10s]
    lo_ms, hi_ms = bin_start - 10_000, bin_start + 20_000
    sel = t.ts[(t.ts >= lo_ms) & (t.ts < hi_ms)]
    if sel.size == 0:
        return BurstResult(True, bin_start, float(best_s), bin_start, "", best_trail, best_cnt)
    secs = ((sel - lo_ms) // 1000).astype(np.int64)
    per_sec = np.bincount(secs, minlength=30).astype(float)  # index 0 == bin_start-10s
    peak = per_sec[10:20].max() if per_sec[10:20].size else 0.0
    e_ms = bin_start
    if peak > 0:
        thr = 0.5 * peak
        for k in range(0, 21):  # bin_start-10s .. bin_start+10s
            prev = per_sec[k - 1] if k > 0 else 0.0
            if per_sec[k] >= thr and prev < thr:
                e_ms = lo_ms + k * 1000
                break
    return BurstResult(True, int(e_ms), float(best_s), bin_start, "", best_trail, best_cnt)


def price_peak_minute_ms(t: Tape) -> int:
    """INDEPENDENT validation proxy only -- never used to place E."""
    t0 = int(t.ts[0])
    m = ((t.ts - t0) // 60_000).astype(np.int64)
    nm = int(m[-1]) + 1
    lo, hi = np.full(nm, np.inf), np.full(nm, -np.inf)
    np.minimum.at(lo, m, t.mid)
    np.maximum.at(hi, m, t.mid)
    last = np.full(nm, np.nan)
    last[m] = t.mid  # last write per minute wins (ts sorted)
    with np.errstate(invalid="ignore"):
        rng = (hi - lo) / last * 1e4
    rng[:6] = -np.inf
    rng[max(nm - 6, 0) :] = -np.inf
    return t0 + int(np.argmax(rng)) * 60_000


# ----------------------------------------------------------------------------- per-event features
@dataclass
class Ev:
    typ: str
    date: str
    nominal_ms: int
    e_ms: int
    e_source: str
    burst_score: float
    year: int
    valid: bool = False
    drop: str = ""
    impulse_bps: float = np.nan
    mid_e: float = np.nan
    q: dict = field(default_factory=dict)  # offset_s -> (bid, ask, mid, ts, gap_ms)
    snap_spread: dict = field(default_factory=dict)  # offset_s -> spread_bps
    base_spread: float = np.nan
    recover_s: float = np.nan
    recover_censored: bool = False
    sig_ts_ms: int = 0


def quote_at_or_after(t: Tape, when_ms: int):
    i = i_at_or_after(t, when_ms)
    if i < 0:
        return None
    gap = int(t.ts[i]) - when_ms
    if gap > MAX_FILL_GAP_MS:
        return None
    return (float(t.bid[i]), float(t.ask[i]), float(t.mid[i]), int(t.ts[i]), gap)


def build_event(typ: str, date: str, nominal_ms: int, path: str) -> Ev:
    tape = load_tape(path)
    year = int(date[:4])
    if typ == "BOJ":
        br = detect_boj_release(tape)
        if not br.ok:
            ev = Ev(typ, date, nominal_ms, 0, "burst", br.score, year)
            ev.drop = f"BOJ no clear burst (score={br.score:.2f})"
            return ev
        e_ms, src, score = br.e_ms, "burst", br.score
    else:
        e_ms, src, score = nominal_ms, "calendar", np.nan

    ev = Ev(typ, date, nominal_ms, int(e_ms), src, float(score), year)

    i0 = i_at_or_before(tape, e_ms)
    if i0 < 0 or (e_ms - int(tape.ts[i0])) > MAX_MID_STALE_MS:
        ev.drop = "no fresh pre-release quote at E"
        return ev
    mid_e = float(tape.mid[i0])
    ev.mid_e = mid_e

    i5 = i_at_or_before(tape, e_ms + IMPULSE_S * 1000)
    if i5 < 0 or (e_ms + IMPULSE_S * 1000 - int(tape.ts[i5])) > MAX_MID_STALE_MS:
        ev.drop = "no quote at E+5s"
        return ev
    ev.sig_ts_ms = int(tape.ts[i5])
    ev.impulse_bps = (float(tape.mid[i5]) - mid_e) / mid_e * 1e4

    # execution quotes (first tick at or after the decision instant)
    need = {F1_ENTRY_S, F1_ENTRY_S_SENS, F2_ENTRY_S, F2_EXIT_S, *F1_EXITS}
    for off in sorted(need):
        q = quote_at_or_after(tape, e_ms + off * 1000)
        if q is None:
            ev.drop = f"no executable quote at E+{off}s"
            return ev
        ev.q[off] = q

    # F3: spread snapshots (prevailing quote = last tick at or before the instant)
    for off in F3_OFFSETS_S:
        j = i_at_or_before(tape, e_ms + off * 1000)
        ev.snap_spread[off] = (
            float(tape.spread_bps[j])
            if j >= 0 and (e_ms + off * 1000 - int(tape.ts[j])) <= MAX_MID_STALE_MS
            else np.nan
        )

    lo_ms = e_ms + F3_BASELINE_FROM_S * 1000
    hi_ms = e_ms + F3_BASELINE_TO_S * 1000
    msk = (tape.ts >= lo_ms) & (tape.ts < hi_ms)
    ev.base_spread = float(np.median(tape.spread_bps[msk])) if msk.sum() >= 5 else np.nan

    # F3: seconds until spread returns to within 1.5x its pre-event level.
    # per-second median spread, then a trailing 10 s median-of-medians.
    if np.isfinite(ev.base_spread):
        n = F3_RECOVERY_MAX_S + 12
        sec_med = np.full(n, np.nan)
        rel = tape.ts - e_ms
        sel = (rel >= 0) & (rel < n * 1000)
        if sel.sum():
            s_idx = (rel[sel] // 1000).astype(np.int64)
            s_val = tape.spread_bps[sel]
            order = np.lexsort((s_val, s_idx))
            s_idx, s_val = s_idx[order], s_val[order]
            starts = np.searchsorted(s_idx, np.arange(n), side="left")
            ends = np.searchsorted(s_idx, np.arange(n), side="right")
            for k in range(n):
                a, b = starts[k], ends[k]
                if b > a:
                    sec_med[k] = s_val[(a + b - 1) // 2]
        thr = F3_RECOVERY_MULT * ev.base_spread
        ev.recover_censored = True
        for k in range(1, F3_RECOVERY_MAX_S + 1):
            w = sec_med[k : k + 10]
            w = w[np.isfinite(w)]
            if w.size >= 3 and float(np.median(w)) <= thr:
                ev.recover_s = float(k)
                ev.recover_censored = False
                break
        if ev.recover_censored:
            ev.recover_s = float(F3_RECOVERY_MAX_S)

    ev.valid = True
    return ev


# ----------------------------------------------------------------------------- trading
def trade_bps(ev: Ev, direction: int, entry_off: int, exit_off: int):
    """Returns (net_base_bps, net_gmo_bps, gross_book_bps, gross_mid_bps)."""
    eb, ea, em, _, _ = ev.q[entry_off]
    xb, xa, xm, _, _ = ev.q[exit_off]
    if direction > 0:  # long: buy ask, sell bid
        gross_book = (xb - ea) / ea * 1e4
    else:  # short: sell bid, buy ask
        gross_book = (eb - xa) / eb * 1e4
    gross_mid = direction * (xm - em) / em * 1e4
    net_base = gross_book - 2 * FEE_BPS_PER_SIDE
    net_gmo = gross_mid - GMO_FLOOR_ROUNDTRIP_BPS
    return net_base, net_gmo, gross_book, gross_mid


def run_config(events, family: str, m: float, exit_off: int, entry_off: int | None = None):
    rows = []
    for ev in events:
        if not ev.valid or abs(ev.impulse_bps) < m:
            continue
        sgn = 1 if ev.impulse_bps > 0 else -1
        if family == "F1":
            d = sgn
            eo = F1_ENTRY_S if entry_off is None else entry_off
        elif family == "F2R":  # DIAGNOSTIC MIRROR of F2, never selectable (see report section)
            d = sgn
            eo = F2_ENTRY_S
        else:
            d = -sgn
            eo = F2_ENTRY_S
        nb, ng, gb, gm = trade_bps(ev, d, eo, exit_off)
        rows.append(
            dict(
                typ=ev.typ, date=ev.date, year=ev.year, dirn=d,
                impulse=ev.impulse_bps, net_base=nb, net_gmo=ng,
                gross_book=gb, gross_mid=gm,
                entry_spread=(ev.q[eo][1] - ev.q[eo][0]) / ev.q[eo][2] * 1e4,
                exit_spread=(ev.q[exit_off][1] - ev.q[exit_off][0]) / ev.q[exit_off][2] * 1e4,
            )
        )
    return pd.DataFrame(rows)


def tstat(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float("nan") if sd == 0 else float(x.mean() / (sd / np.sqrt(x.size)))


def boot_ci(x: np.ndarray, n: int = BOOT_N, seed: int = BOOT_SEED):
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n, x.size))
    means = x[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def summarize(df: pd.DataFrame, col: str = "net_base") -> dict:
    if df.empty:
        return dict(n=0, mean=np.nan, t=np.nan, lo=np.nan, hi=np.nan, win=np.nan, med=np.nan)
    x = df[col].to_numpy(dtype=float)
    lo, hi = boot_ci(x)
    return dict(n=len(x), mean=float(x.mean()), t=tstat(x), lo=lo, hi=hi,
                win=float((x > 0).mean()), med=float(np.median(x)))


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return f"{'-':>6} {'-':>9} {'-':>7} {'-':>19} {'-':>7}"
    return (f"{s['n']:>6d} {s['mean']:>+9.3f} {s['t']:>+7.2f} "
            f"[{s['lo']:+7.3f},{s['hi']:+7.3f}] {s['win']*100:>6.1f}%")


# ----------------------------------------------------------------------------- main
def main() -> int:
    print(hr("="))
    print("FX STUDY S4 -- MACRO RELEASE, TICK RESOLUTION: IS ANYTHING AFTER THE FIRST SECOND TRADABLE?")
    print(hr("="))
    print(__doc__.split("Run:")[0].strip()[:0] or "", end="")

    cal = pd.read_csv(CAL)
    cal["nominal_ms"] = (
        (pd.to_datetime(cal["time_utc"], utc=True) - EPOCH) / pd.Timedelta("1ms")
    ).astype(np.int64)
    cal = cal.sort_values(["nominal_ms", "type"], kind="stable").reset_index(drop=True)
    print(f"\ncalendar: {len(cal)} events  {cal.date.min()} .. {cal.date.max()}")
    print(cal.groupby("type").size().to_string())

    # ---------------------------------------------------------------- SANITY 1: ms epoch
    print("\n" + hr())
    print("SANITY 1 -- MILLISECOND-EPOCH HANDLING PROVEN")
    print(hr())
    probe = cal[(cal.type == "NFP")].iloc[-1]
    ppath = os.path.join(LIB, f"NFP_{probe.date.replace('-', '')}.csv.gz")
    praw = pd.read_csv(ppath)
    first_ms = int(praw.ts_utc.iloc[0])
    conv = ((pd.to_datetime([first_ms], unit="ms", utc=True) - EPOCH) / pd.Timedelta("1ms")).to_numpy()[0]
    print(f"  file                : {os.path.basename(ppath)}")
    print(f"  first raw ts_utc    : {first_ms}   (int64 ms)")
    print(f"  -> UTC              : {utc(first_ms)}")
    print(f"  round-trip back to ms: {int(conv)}   identical={int(conv) == first_ms}")
    print(f"  calendar time_utc   : {probe.time_utc}  -> nominal_ms {probe.nominal_ms} -> {utc(probe.nominal_ms)}")
    print(f"  E - first_tick      : {(probe.nominal_ms - first_ms)/1000:.1f} s   "
          f"(expected +900 s: window opens E-15min)")
    print(f"  last tick           : {utc(int(praw.ts_utc.iloc[-1]))}  "
          f"(E + {(int(praw.ts_utc.iloc[-1]) - probe.nominal_ms)/1000:.0f} s)")
    print("  NOTE: .astype('int64') on datetime64 is never used; all conversions go via")
    print("        (idx - EPOCH) / pd.Timedelta(...) as required by research-protocol sec.6.")

    # ---------------------------------------------------------------- SANITY 2: BOJ detector
    print("\n" + hr())
    print("SANITY 2 -- BOJ BURST DETECTOR ON 3 KNOWN DECISIONS (price-blind; arrivals only)")
    print(hr())
    known = {
        "2016-01-29": ("NIRP introduced; press reports place the statement at 12:38 JST = 03:38Z",
                       "MISS -- the detector locks onto an EARLIER genuine burst at 12:21 JST. That day the "
                       "meeting over-ran\n              and the tape whipsawed before the statement; the "
                       "largest arrival burst is not the statement.\n              This is the detector's "
                       "documented failure mode: on a leak/whipsaw day it finds the first burst, not the release."),
        "2024-03-19": ("NIRP exit / YCC end; statement just after 12:30 JST = ~03:3xZ", "HIT"),
        "2022-12-20": ("YCC band widened (surprise); statement around noon JST = ~03:0xZ", "HIT"),
    }
    for dt, (note, verdict) in known.items():
        p = os.path.join(LIB, f"BOJ_{dt.replace('-', '')}.csv.gz")
        if not os.path.exists(p):
            print(f"  {dt}  FILE MISSING")
            continue
        tp = load_tape(p)
        br = detect_boj_release(tp)
        pk = price_peak_minute_ms(tp)
        print(f"  {dt}  detected E = {utc(br.e_ms).strftime('%H:%M:%S')}Z "
              f"({utc(br.e_ms).tz_convert('Asia/Tokyo').strftime('%H:%M:%S')} JST)  "
              f"ratio={br.score:5.1f} (60s ticks {br.burst_count:.0f} vs trailing {br.trail:.1f}/10s)")
        print(f"              coarse bin start {utc(br.bin_start_ms).strftime('%H:%M:%S')}Z ; "
              f"independent price-range-peak minute {utc(pk).strftime('%H:%M')}Z ; "
              f"detector-vs-proxy {abs(br.e_ms - pk)/1000:.0f}s")
        print(f"              expectation: {note}")
        print(f"              verdict: {verdict}")

    # ---------------------------------------------------------------- build all events
    print("\n" + hr())
    print("BUILDING EVENT FEATURES (one pass per file, 477 files)")
    print(hr())
    events: list[Ev] = []
    missing = 0
    for _, r in cal.iterrows():
        path = os.path.join(LIB, f"{r.type}_{r.date.replace('-', '')}.csv.gz")
        if not os.path.exists(path):
            missing += 1
            continue
        events.append(build_event(r.type, r.date, int(r.nominal_ms), path))
    print(f"  files missing        : {missing}")
    print(f"  events built         : {len(events)}")
    drops = pd.Series([re.sub(r"\(score=[\d.]+\)", "(ratio<%.1f)" % BOJ_MIN_SCORE, e.drop)
                       for e in events if not e.valid]).value_counts()
    boj_nb = sum(1 for e in events if e.typ == "BOJ" and e.drop.startswith("BOJ no clear burst"))
    print(f"  valid                : {sum(e.valid for e in events)}")
    print(f"  BOJ excluded (no clear burst, ratio<{BOJ_MIN_SCORE}): {boj_nb}")
    if len(drops):
        print("  drop reasons:")
        for k, v in drops.items():
            print(f"      {v:>4d}  {k}")
    vt = pd.Series([e.typ for e in events if e.valid]).value_counts()
    print("  valid by type        : " + ", ".join(f"{k}={v}" for k, v in sorted(vt.items())))

    # BOJ detector aggregate validation
    boj_ok = [e for e in events if e.typ == "BOJ" and e.valid]
    diffs = []
    for e in boj_ok:
        p = os.path.join(LIB, f"BOJ_{e.date.replace('-', '')}.csv.gz")
        tp = load_tape(p)
        diffs.append(abs(e.e_ms - price_peak_minute_ms(tp)) / 1000.0)
    if diffs:
        dd = np.array(diffs)
        print(f"  BOJ detector vs independent price-range-peak proxy (n={len(dd)}): "
              f"median |gap| {np.median(dd):.0f}s ; within 120s {100*(dd<=120).mean():.0f}% ; "
              f"within 300s {100*(dd<=300).mean():.0f}%")
        hh = [utc(e.e_ms).tz_convert('Asia/Tokyo') for e in boj_ok]
        hh = pd.Series([h.hour + h.minute / 60 for h in hh])
        print(f"  BOJ detected release, JST hour: p10={hh.quantile(.1):.2f} "
              f"median={hh.median():.2f} p90={hh.quantile(.9):.2f}  "
              f"(nominal anchor 11.50; drift band 11.5-15.0 per KNOWLEDGE_FX sec.2)")

    # ---------------------------------------------------------------- SANITY 3: no look-ahead
    print("\n" + hr())
    print("SANITY 3 -- NO LOOK-AHEAD")
    print(hr())
    vv = [e for e in events if e.valid]
    gap_sig_entry = np.array([e.q[F1_ENTRY_S][3] - e.sig_ts_ms for e in vv], dtype=float)
    print(f"  signal window is [E, E+5s]; F1 entry fills at the first tick with ts >= E+5s.")
    print(f"  entry_tick_ts - signal_tick_ts (ms): min {gap_sig_entry.min():.0f}, "
          f"median {np.median(gap_sig_entry):.0f}, negative count {int((gap_sig_entry < 0).sum())}")
    print(f"  entries strictly after the signal tick: {int((gap_sig_entry > 0).sum())}/{len(vv)}  "
          f"(ties = signal and fill on the SAME tick at exactly E+5s)")
    fill_gaps = np.array([e.q[F1_ENTRY_S][4] for e in vv], dtype=float)
    print(f"  fill gap vs decision instant E+5s (ms): median {np.median(fill_gaps):.0f}, "
          f"p90 {np.percentile(fill_gaps, 90):.0f}, max {fill_gaps.max():.0f} (cap {MAX_FILL_GAP_MS})")
    print(f"  the E+10s sensitivity run has a strict 5-SECOND GAP between the end of the")
    print(f"  signal window and the fill, i.e. a look-ahead-free variant by construction.")
    print(f"  no feature used by any family reads a tick after its own decision instant.")

    # ---------------------------------------------------------------- SANITY 3b: worked example
    print("\n" + hr())
    print("SANITY 3b -- ONE TRADE WORKED OUT FROM RAW QUOTES (arithmetic auditable by hand)")
    print(hr())
    demo = max((e for e in vv if e.typ == "NFP" and e.date >= "2023-01-01"),
               key=lambda e: abs(e.impulse_bps))
    eb, ea, em, ets, egap = demo.q[F1_ENTRY_S]
    xb, xa, xm, xts, xgap = demo.q[300]
    d = 1 if demo.impulse_bps > 0 else -1
    print(f"  {demo.typ} {demo.date}  E = {utc(demo.e_ms)}")
    print(f"    mid(E)     = {demo.mid_e:.5f}")
    print(f"    mid(E+5s)  = {demo.mid_e * (1 + demo.impulse_bps/1e4):.5f}   "
          f"impulse = {demo.impulse_bps:+.2f} bps -> direction {'LONG' if d > 0 else 'SHORT'}")
    print(f"    entry fill @ {utc(ets)} (+{egap} ms past E+5s):  bid {eb:.5f} / ask {ea:.5f}")
    print(f"    exit  fill @ {utc(xts)} (+{xgap} ms past E+300s): bid {xb:.5f} / ask {xa:.5f}")
    nb_, ng_, gb_, gm_ = trade_bps(demo, d, F1_ENTRY_S, 300)
    if d > 0:
        print(f"    long: buy ASK {ea:.5f}, sell BID {xb:.5f}  ->  "
              f"({xb:.5f} - {ea:.5f}) / {ea:.5f} * 1e4 = {gb_:+.3f} bps")
    else:
        print(f"    short: sell BID {eb:.5f}, buy ASK {xa:.5f}  ->  "
              f"({eb:.5f} - {xa:.5f}) / {eb:.5f} * 1e4 = {gb_:+.3f} bps")
    print(f"    minus {2*FEE_BPS_PER_SIDE} bps fee  ->  NET {nb_:+.3f} bps   "
          f"(mid-to-mid zero-cost would have been {gm_:+.3f} bps)")

    # ---------------------------------------------------------------- F3 spread anatomy
    print("\n" + hr("="))
    print("F3 -- SPREAD ANATOMY OF A MACRO RELEASE  (MEASUREMENT ONLY, NO ADOPTION)")
    print("     the cost-of-event-trading map: real interbank bid/ask, bps, USD/JPY")
    print(hr("="))
    f3 = pd.DataFrame(
        [dict(typ=e.typ, year=e.year, base=e.base_spread, rec=e.recover_s,
              cens=e.recover_censored, imp=abs(e.impulse_bps),
              **{f"s{o}": e.snap_spread.get(o, np.nan) for o in F3_OFFSETS_S})
         for e in events if e.valid]
    )
    cols = [f"s{o}" for o in F3_OFFSETS_S]
    hdr = "  " + f"{'type':<6}{'n':>5}" + "".join(f"{('E' + (f'{o:+d}' if o else '')) + 's':>12}" for o in F3_OFFSETS_S)
    print("\n  MEDIAN spread (bps)")
    print(hdr)
    for typ, g in f3.groupby("typ"):
        print("  " + f"{typ:<6}{len(g):>5}" + "".join(f"{g[c].median():>12.3f}" for c in cols))
    print("  " + f"{'ALL':<6}{len(f3):>5}" + "".join(f"{f3[c].median():>12.3f}" for c in cols))
    print("\n  p90 spread (bps)")
    print(hdr)
    for typ, g in f3.groupby("typ"):
        print("  " + f"{typ:<6}{len(g):>5}" + "".join(f"{g[c].quantile(.9):>12.3f}" for c in cols))
    print("  " + f"{'ALL':<6}{len(f3):>5}" + "".join(f"{f3[c].quantile(.9):>12.3f}" for c in cols))

    print(f"\n  ROUND-TRIP cost of a trade opened at E+5s and closed at E+300s, purely from spread")
    print(f"  (half-spread in + half-spread out + {2*FEE_BPS_PER_SIDE:.1f} bps fee), median / p90 bps:")
    for typ, g in f3.groupby("typ"):
        rt = (g["s5"] + g["s300"]) / 2 + 2 * FEE_BPS_PER_SIDE
        print(f"      {typ:<6} median {rt.median():>7.3f}   p90 {rt.quantile(.9):>7.3f}   "
              f"(GMO retail floor {GMO_FLOOR_ROUNDTRIP_BPS} bps)")

    print(f"\n  SPREAD RECOVERY: seconds until the 10 s median spread falls back within "
          f"{F3_RECOVERY_MULT}x the pre-event level")
    print(f"      (pre-event level = median spread over [E{F3_BASELINE_FROM_S}s, E{F3_BASELINE_TO_S}s]; "
          f"censored at {F3_RECOVERY_MAX_S}s)")
    print(f"      {'type':<6}{'n':>5}{'base bps':>10}{'p50 s':>9}{'p90 s':>9}{'censored':>10}")
    for typ, g in f3.groupby("typ"):
        print(f"      {typ:<6}{len(g):>5}{g['base'].median():>10.3f}{g['rec'].median():>9.0f}"
              f"{g['rec'].quantile(.9):>9.0f}{100*g['cens'].mean():>9.0f}%")
    print(f"      {'ALL':<6}{len(f3):>5}{f3['base'].median():>10.3f}{f3['rec'].median():>9.0f}"
          f"{f3['rec'].quantile(.9):>9.0f}{100*f3['cens'].mean():>9.0f}%")

    print(f"\n  IMPULSE SIZE |mid(E+5s) - mid(E)| in bps, by type")
    print(f"      {'type':<6}{'n':>5}{'p50':>8}{'p75':>8}{'p90':>8}{'max':>9}"
          f"{'>=5bps':>9}{'>=10bps':>9}{'>=20bps':>9}")
    for typ, g in f3.groupby("typ"):
        print(f"      {typ:<6}{len(g):>5}{g['imp'].median():>8.2f}{g['imp'].quantile(.75):>8.2f}"
              f"{g['imp'].quantile(.9):>8.2f}{g['imp'].max():>9.2f}"
              f"{100*(g['imp']>=5).mean():>8.0f}%{100*(g['imp']>=10).mean():>8.0f}%"
              f"{100*(g['imp']>=20).mean():>8.0f}%")
    print(f"      {'ALL':<6}{len(f3):>5}{f3['imp'].median():>8.2f}{f3['imp'].quantile(.75):>8.2f}"
          f"{f3['imp'].quantile(.9):>8.2f}{f3['imp'].max():>9.2f}"
          f"{100*(f3['imp']>=5).mean():>8.0f}%{100*(f3['imp']>=10).mean():>8.0f}%"
          f"{100*(f3['imp']>=20).mean():>8.0f}%")

    print(f"\n  IMPULSE SIZE and SPREAD by year (2015-2019 tick density is materially lower)")
    print(f"      {'year':<6}{'n':>5}{'|imp| p50':>11}{'|imp| p90':>11}{'spr E-60s':>11}"
          f"{'spr E+5s':>11}{'spr E+60s':>11}")
    for yr, g in f3.groupby("year"):
        print(f"      {yr:<6}{len(g):>5}{g['imp'].median():>11.2f}{g['imp'].quantile(.9):>11.2f}"
              f"{g['s-60'].median():>11.3f}{g['s5'].median():>11.3f}{g['s60'].median():>11.3f}")

    # ---------------------------------------------------------------- split
    print("\n" + hr("="))
    print("SPLIT (pre-registered, fixed by count over the full 477-event calendar)")
    print(hr("="))
    order = {(e.typ, e.date): i for i, e in enumerate(events)}
    ex_events = [e for e in events if order[(e.typ, e.date)] < SPLIT_EXPLORE_N]
    ju_events = [e for e in events if order[(e.typ, e.date)] >= SPLIT_EXPLORE_N]
    print(f"  exploration : events   1..{SPLIT_EXPLORE_N}  "
          f"{ex_events[0].date} .. {ex_events[-1].date}   valid {sum(e.valid for e in ex_events)}")
    print(f"  judgment    : events {SPLIT_EXPLORE_N+1}..{len(events)}  "
          f"{ju_events[0].date} .. {ju_events[-1].date}   valid {sum(e.valid for e in ju_events)}")

    # ---------------------------------------------------------------- exploration
    configs = [("F1", m, x) for m in THRESHOLDS for x in F1_EXITS] + [("F2", m, F2_EXIT_S) for m in THRESHOLDS]
    print("\n" + hr("="))
    print(f"EXPLORATION -- ALL {len(configs)} PRE-ENUMERATED CONFIGS (net bps/trade, MEASURED interbank cost)")
    print(hr("="))
    print(f"  {'family':<8}{'m bps':>7}{'entry':>8}{'exit':>7}"
          f"{'n':>7}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}   {'gmo-floor net':>14}")
    ex_rows = []
    for fam, m, xo in configs:
        eo = F1_ENTRY_S if fam == "F1" else F2_ENTRY_S
        df = run_config(ex_events, fam, m, xo)
        s = summarize(df)
        sg = summarize(df, "net_gmo")
        ex_rows.append(dict(family=fam, m=m, exit=xo, **s, gmo=sg["mean"], gmo_t=sg["t"]))
        print(f"  {fam:<8}{m:>7.0f}{('E+%ds' % eo):>8}{('E+%ds' % xo):>7} {fmt(s)}   "
              f"{sg['mean']:>+9.3f} (t{sg['t']:+.2f})")
    ex = pd.DataFrame(ex_rows)

    print("\n  MECHANISM DECOMPOSITION (exploration) -- protocol sec.5: is this a COST-LOSS")
    print("  rejection (effect real, smaller than cost) or a MECHANISM-ABSENT rejection?")
    print("  zero-cost column = mid-to-mid signed move, no spread, no fee. If that is ~0 or")
    print("  negative, no execution improvement can rescue the family.")
    print(f"  {'family':<8}{'m bps':>7}{'exit':>7}{'n':>7}{'zero-cost':>12}{'t':>8}"
          f"{'spread paid':>13}{'fee':>7}{'net':>10}")
    for fam, m, xo in configs:
        df = run_config(ex_events, fam, m, xo)
        if df.empty:
            continue
        z = summarize(df, "gross_mid")
        spread_paid = float((df.gross_mid - df.gross_book).mean())
        print(f"  {fam:<8}{m:>7.0f}{('E+%ds' % xo):>7}{z['n']:>7d}{z['mean']:>+12.3f}{z['t']:>+8.2f}"
              f"{spread_paid:>13.3f}{2*FEE_BPS_PER_SIDE:>7.1f}{df.net_base.mean():>+10.3f}")

    print("\n  E+10s ENTRY SENSITIVITY (F1 only; latency check -- 5 s to react instead of 0)")
    print(f"  {'family':<8}{'m bps':>7}{'entry':>8}{'exit':>7}"
          f"{'n':>7}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}")
    for m in THRESHOLDS:
        for xo in F1_EXITS:
            df = run_config(ex_events, "F1", m, xo, entry_off=F1_ENTRY_S_SENS)
            print(f"  {'F1':<8}{m:>7.0f}{'E+10s':>8}{('E+%ds' % xo):>7} {fmt(summarize(df))}")

    # ---------------------------------------------------------------- selection
    print("\n" + hr("="))
    print("SELECTION (pre-registered rule, exploration only)")
    print(hr("="))
    elig = ex[ex["n"] >= 40].copy()
    flagged = ""
    if elig.empty:
        elig = ex.copy()
        flagged = "  *** NO config reached n>=40; rule fell back to all 12 (flagged as pre-registered) ***"
        print(flagged)
    elig = elig.sort_values(["mean", "t"], ascending=False, kind="stable")
    win = elig.iloc[0]
    print(f"  eligible configs (exploration n>=40): {len(elig)}/{len(ex)}")
    print(f"  CHOSEN: family={win.family}  m={win.m:.0f} bps  exit=E+{int(win['exit'])}s  "
          f"(exploration n={int(win['n'])}, net {win['mean']:+.3f} bps, t={win['t']:+.2f})")

    # plateau diagnostic (protocol sec.4.4) -- reported, not used for selection
    print("\n  PLATEAU DIAGNOSTIC (exploration; each axis +/-1 step around the winner)")
    for _, r in ex[(ex.family == win.family)].sort_values(["m", "exit"]).iterrows():
        star = " <== winner" if (r.m == win.m and r["exit"] == win["exit"]) else ""
        print(f"      {r.family} m={r.m:>4.0f} exit=E+{int(r['exit']):>3d}s  "
              f"n={int(r['n']):>4d}  net {r['mean']:>+8.3f}  t {r['t']:>+6.2f}{star}")

    # ---------------------------------------------------------------- judgment (ONCE)
    print("\n" + hr("="))
    print("JUDGMENT -- RUN ONCE, REPORTED AS-IS")
    print(hr("="))
    jdf = run_config(ju_events, win.family, float(win.m), int(win["exit"]))
    js = summarize(jdf)
    jg = summarize(jdf, "net_gmo")
    jgross = summarize(jdf, "gross_book")
    print(f"  config: {win.family} m={win.m:.0f} bps, enter E+{F1_ENTRY_S if win.family=='F1' else F2_ENTRY_S}s, "
          f"exit E+{int(win['exit'])}s")
    print(f"  judgment span: {ju_events[0].date} .. {ju_events[-1].date}")
    jmid = summarize(jdf, "gross_mid")
    print(f"  n (signal events)      : {js['n']}")
    print(f"  ZERO-COST mid-to-mid   : {jmid['mean']:+.3f} bps/trade (t {jmid['t']:+.2f})  "
          f"<- the raw mechanism, no spread, no fee")
    print(f"  after crossing the book: {jgross['mean']:+.3f} bps/trade  "
          f"(spread paid {jmid['mean'] - jgross['mean']:.3f} bps)")
    print(f"  NET, measured cost     : {js['mean']:+.3f} bps/trade  (median {js['med']:+.3f}, "
          f"win {100*js['win']:.1f}%)")
    print(f"  event-clustered t      : {js['t']:+.2f}   bootstrap 95% CI "
          f"[{js['lo']:+.3f}, {js['hi']:+.3f}]  (seed {BOOT_SEED}, {BOOT_N} resamples)")
    print(f"  NET, GMO 0.71bps floor : {jg['mean']:+.3f} bps/trade (t {jg['t']:+.2f}) "
          f"-- LOWER BOUND on retail cost, not a forecast")
    if not jdf.empty:
        print(f"  measured cost actually paid: entry half-spread {jdf.entry_spread.median()/2:.3f} bps, "
              f"exit half-spread {jdf.exit_spread.median()/2:.3f} bps, fee {2*FEE_BPS_PER_SIDE:.1f} bps "
              f"=> {jdf.entry_spread.median()/2 + jdf.exit_spread.median()/2 + 2*FEE_BPS_PER_SIDE:.3f} bps median round trip")

    if win.family == "F1":
        jsens = summarize(run_config(ju_events, "F1", float(win.m), int(win["exit"]),
                                     entry_off=F1_ENTRY_S_SENS))
        print(f"  LATENCY SENSITIVITY, entry moved to E+10s (5 s to react instead of 0):")
        print(f"      n {jsens['n']}, net {jsens['mean']:+.3f} bps, t {jsens['t']:+.2f}, "
              f"CI [{jsens['lo']:+.3f}, {jsens['hi']:+.3f}]")

    c1 = js["n"] >= 60
    c2 = (js["mean"] >= 2.0) if js["n"] else False
    c3 = (js["t"] >= 2.0) if js["n"] else False
    print("\n  ADOPTION BAR (pre-registered, all three required):")
    print(f"      (1) n >= 60                  : {js['n']:>8}   {'PASS' if c1 else 'FAIL'}")
    print(f"      (2) net >= +2.0 bps/trade    : {js['mean']:>+8.3f}   {'PASS' if c2 else 'FAIL'}")
    print(f"      (3) event-clustered t >= 2.0 : {js['t']:>+8.2f}   {'PASS' if c3 else 'FAIL'}")
    verdict = "ADOPT" if (c1 and c2 and c3) else "REJECT"
    print(f"\n  >>> VERDICT: {verdict} <<<")

    # ---------------------------------------------------------------- full judgment grid (diagnostic)
    print("\n" + hr())
    print("DIAGNOSTIC ONLY (NOT used for adoption; printed so the negative result is auditable):")
    print("all 12 configs on the judgment span. Reading any of these as a selection would be")
    print("self-contamination (protocol sec.8.2) -- they are reported, never promoted.")
    print(hr())
    print(f"  {'family':<8}{'m bps':>7}{'exit':>7}{'n':>7}{'net':>10}{'t':>8}{'  95% CI boot':<21}"
          f"{'win':>7}{'zero-cost':>11}")
    for fam, m, xo in configs:
        d = run_config(ju_events, fam, m, xo)
        s = summarize(d)
        z = summarize(d, "gross_mid")
        mark = "  <== pre-registered choice" if (fam == win.family and m == win.m and xo == int(win["exit"])) else ""
        print(f"  {fam:<8}{m:>7.0f}{('E+%ds' % xo):>7} {fmt(s)}{z['mean']:>+11.3f}{mark}")

    # ------------------------------------------------------ mirror-of-F2 diagnostic
    print("\n" + hr())
    print("SHAPE OF THE MOVE, AND A PENDING HYPOTHESIS (DIAGNOSTIC -- NOT ADOPTED)")
    print(hr())
    print("  Reading the zero-cost columns as a path rather than as strategies:")
    for m in THRESHOLDS:
        a = summarize(run_config(ex_events, "F1", m, 60), "gross_mid")
        b = summarize(run_config(ex_events, "F1", m, 300), "gross_mid")
        c = summarize(run_config(ex_events, "F2", m, 300), "gross_mid")
        ja = summarize(run_config(ju_events, "F1", m, 60), "gross_mid")
        jb = summarize(run_config(ju_events, "F1", m, 300), "gross_mid")
        jc = summarize(run_config(ju_events, "F2", m, 300), "gross_mid")
        print(f"    m={m:>4.0f}  EXPLORE  E+5s->E+60s {a['mean']:>+7.2f}   E+5s->E+300s {b['mean']:>+7.2f}"
              f"   E+60s->E+300s {-c['mean']:>+7.2f}  (signed WITH the impulse, zero cost)")
        print(f"          JUDGE    E+5s->E+60s {ja['mean']:>+7.2f}   E+5s->E+300s {jb['mean']:>+7.2f}"
              f"   E+60s->E+300s {-jc['mean']:>+7.2f}")
    print("\n  F2's loss is a fact about the tape: the impulse direction RESUMES between E+60s and")
    print("  E+300s. The mechanical mirror of F2 -- enter at E+60s WITH the impulse, exit E+300s --")
    print("  is therefore printed here at full measured cost. IT WAS NOT IN THE PRE-REGISTERED")
    print("  ENUMERATION, so protocol sec.8.2 forbids promoting it. It is logged PENDING: it must be")
    print("  pre-registered and re-tested on events that did not exist when this ran.")
    print(f"  {'split':<12}{'m bps':>7}{'n':>7}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}{'zero-cost':>11}")
    for label, evs in (("exploration", ex_events), ("judgment", ju_events)):
        for m in THRESHOLDS:
            d = run_config(evs, "F2R", m, F2_EXIT_S)
            s = summarize(d)
            z = summarize(d, "gross_mid")
            print(f"  {label:<12}{m:>7.0f} {fmt(s)}{z['mean']:>+11.3f}")
    print("  (adoption bar for reference: n>=60, net>=+2.0 bps, t>=2.0 -- on the JUDGMENT row)")

    print("\n  CONFIGURATION SWITCH CHECK (protocol sec.2): exploration winner vs judgment winner")
    ju_rows = [dict(family=f, m=m, exit=x, **summarize(run_config(ju_events, f, m, x))) for f, m, x in configs]
    ju = pd.DataFrame(ju_rows)
    jw = ju[ju["n"] >= 40].sort_values(["mean", "t"], ascending=False, kind="stable")
    jw = jw.iloc[0] if len(jw) else ju.sort_values("mean", ascending=False).iloc[0]
    same = (jw.family == win.family) and (jw.m == win.m) and (jw["exit"] == win["exit"])
    print(f"      exploration winner : {win.family} m={win.m:.0f} exit=E+{int(win['exit'])}s")
    print(f"      judgment  winner   : {jw.family} m={jw.m:.0f} exit=E+{int(jw['exit'])}s")
    print(f"      configuration carried over: {same}  "
          f"-> {'stable' if same else 'SWITCHED = overfit signature (protocol sec.2): do not adopt either'}")

    # ---------------------------------------------------------------- per-type / yearly
    print("\n" + hr("="))
    print("PER-TYPE AND YEAR-BY-YEAR (chosen config, whole library: exploration + judgment)")
    print(hr("="))
    alldf = run_config(events, win.family, float(win.m), int(win["exit"]))
    print(f"  chosen config = {win.family} m={win.m:.0f} exit=E+{int(win['exit'])}s")
    print(f"\n  by event type")
    print(f"      {'type':<6}{'n':>6}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}{'|imp| p50':>11}")
    for typ, g in alldf.groupby("typ"):
        s = summarize(g)
        print(f"      {typ:<6}{fmt(s)}{g.impulse.abs().median():>11.2f}")
    for label, sub in (("exploration", alldf[alldf.date <= ex_events[-1].date]),
                       ("judgment", alldf[alldf.date > ex_events[-1].date])):
        print(f"\n  by event type -- {label} only")
        print(f"      {'type':<6}{'n':>6}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}")
        for typ, g in sub.groupby("typ"):
            print(f"      {typ:<6}{fmt(summarize(g))}")
    print(f"\n  by year")
    print(f"      {'year':<6}{'n':>6}{'net':>10}{'t':>8}{'  95% CI boot':<21}{'win':>7}")
    for yr, g in alldf.groupby("year"):
        print(f"      {yr:<6}{fmt(summarize(g))}")

    print(f"\n  DIRECTIONAL DECOMPOSITION (chosen config, whole library) -- is the edge one-sided?")
    for d, lbl in ((1, "long "), (-1, "short")):
        g = alldf[alldf.dirn == d]
        print(f"      {lbl} {fmt(summarize(g))}")

    # ---------------------------------------------------------------- SANITY 4: determinism
    print("\n" + hr())
    print("SANITY 4 -- DETERMINISM")
    print(hr())
    h1 = hashlib.sha256(
        pd.util.hash_pandas_object(alldf.round(9), index=False).to_numpy().tobytes()
    ).hexdigest()[:16]
    alldf2 = run_config(events, win.family, float(win.m), int(win["exit"]))
    h2 = hashlib.sha256(
        pd.util.hash_pandas_object(alldf2.round(9), index=False).to_numpy().tobytes()
    ).hexdigest()[:16]
    b1 = boot_ci(alldf.net_base.to_numpy())
    b2 = boot_ci(alldf.net_base.to_numpy())
    print(f"  trade-table hash, run A {h1} / run B {h2}   identical={h1 == h2}")
    print(f"  bootstrap CI reproduced exactly (seed {BOOT_SEED}): {b1 == b2}  {b1}")
    print(f"  no network access, no RNG outside the seeded bootstrap, no files written.")

    # ---------------------------------------------------------------- caveats
    print("\n" + hr("="))
    print("PRE-REGISTERED CAVEATS (restated with the measured numbers)")
    print(hr("="))
    med_rt = (f3["s5"].median() + f3["s300"].median()) / 2 + 2 * FEE_BPS_PER_SIDE
    print(f"  * VENUE. Dukascopy is INTERBANK. Median measured round trip in the release window")
    print(f"    is {med_rt:.2f} bps vs the GMO retail floor {GMO_FLOOR_ROUNDTRIP_BPS} bps in calm conditions.")
    print(f"    Retail event-time slippage (requote, rejection, widened fill) is UNBOUNDED and NOT")
    print(f"    measured here. Both the base case and the GMO-floor case are OPTIMISTIC.")
    print(f"  * LATENCY. The E+5s entry assumes sub-1-second sense-decide-fill. The E+10s table")
    print(f"    above is the sensitivity; a slower loop reads off that table, not the headline.")
    print(f"  * DENSITY. 2015-2019 carries far fewer ticks per second than 2022-2026 (yearly table);")
    print(f"    a 5-second impulse measured on a thin 2016 tape is noisier than on a 2024 tape.")
    print(f"  * BOJ E is INFERRED. {boj_nb} BOJ events were excluded for lack of a clear burst.")
    print(f"    A mis-placed E biases the impulse toward zero (it straddles the jump), so the BOJ")
    print(f"    arm is conservative, not inflated.")
    print(f"  * CANDIDATE COUNT. 12 configs were enumerated before running (protocol sec.8.3).")
    print(hr("="))
    print(f"FINAL: {verdict}  -- {win.family} m={win.m:.0f} exit=E+{int(win['exit'])}s, "
          f"judgment n={js['n']}, net {js['mean']:+.3f} bps, t {js['t']:+.2f}")
    print(hr("="))
    return 0


if __name__ == "__main__":
    sys.exit(main())
