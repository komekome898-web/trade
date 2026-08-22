#!/usr/bin/env python3
"""
SYNERGY STUDY #1 -- are BTC storms partly SCHEDULED? (US macro calendar -> BTC storms)

PRE-REGISTRATION (fixed before a single line was executed)
=========================================================

Motivation
----------
The owner is entering FX, where volatility is calendar-scheduled (NFP / CPI / FOMC
have pre-announced timestamps).  Before any FX data exists we test the transfer
hypothesis on data already held: if US macro releases drive BTC storms, then
(a) the "FX storm calendar" thesis gains a cross-market prior, and
(b) the BTC radar could gain a calendar module (CANDIDATE only).

Data (fixed)
------------
    data/binance_BTCUSDT_1m_full.csv   -- 1-minute BTCUSDT, ~210 days,
                                          2026-01-22 .. 2026-08-20 (UTC)
No other price source is used.  There is no train/eval split: this is a single
pre-registered event-window measurement, executed once and reported as-is.

Storm machinery (imported verbatim, NOT re-implemented)
-------------------------------------------------------
    scripts/research_storm.py :: build_storms
        storm minute : |rolling 30m log-return| >= 0.8%   (STORM_THRESHOLD)
        storm EVENT  : first storm minute after >= 2h with no storm minute
    scripts/research_storm_b.py :: load_anchor  (same 1m grid / gap fill)

Event calendar -- RULE-DERIVED, with honest sourcing notes
----------------------------------------------------------
Training-data cutoff is 2026-01; exact 2026 release dates are NOT reliably
memorised, so the calendar is generated from RULES, not from a recalled list.
Every rule and its confidence is printed by the script (section 2).

  NFP   : first Friday of each month, 08:30 ET.
          CONFIDENCE HIGH on the rule; MEDIUM on individual dates (BLS shifts
          the release when the first Friday is <= the 2nd of the month or falls
          next to a federal holiday).  Exceptions are flagged, not corrected.
  CPI   : one release per month, 08:30 ET, typically day 10-15.  Concrete rule:
          the 12th of the month, snapped to the nearest weekday (Sat -> Fri 11,
          Sun -> Mon 13).  Back-checked against 2024/2025 this rule lands within
          ~1 day of the true date most months.  CONFIDENCE LOW on any single
          date -> a +/-1 day (and +/-2 day) sensitivity is run.
  FOMC  : statement day, 14:00 ET.  The 2026 schedule was pre-announced in 2025;
          the dates used are Jan 27-28, Mar 17-18, Apr 28-29, Jun 16-17,
          Jul 28-29, Sep 15-16, Oct 27-28, Dec 8-9 (statement = 2nd day).
          CONFIDENCE MEDIUM-HIGH (standard 8-meeting pattern, matches the shape
          of 2024/2025) -- the whole study is therefore run BOTH WITH AND
          WITHOUT FOMC.

US DST 2026: 2026-03-08 .. 2026-11-01.  Handled with zoneinfo
(America/New_York), so 08:30 ET = 13:30 UTC in winter and 12:30 UTC in summer,
and 14:00 ET = 19:00 UTC / 18:00 UTC.  Section 1 prints the transition proof.

Windows and metric (fixed)
--------------------------
  windows : event +/- 30 min (PRIMARY), event +/- 90 min (SECONDARY)
  metric  : storm-ONSET rate per minute inside windows vs outside
            lift    = rate_in / rate_out
            recall  = storm onsets inside windows / all storm onsets
            also reported: n event windows, n storms captured, per-event hit
            rate, exact one-sided binomial p, and a day-shift permutation null.

Clock interaction (the central question, fixed in advance)
----------------------------------------------------------
KNOWLEDGE.md sec.2: "storms are ruled by the clock" -- UTC 12:30-15:00 lifts
2.23x.  NFP and CPI at 08:30 ET land at 12:30 UTC, i.e. exactly the start of the
clock window.  This overlap may EXPLAIN the clock law.  Three decompositions,
all pre-registered:
  D1  2x2 crosstab  clock-window x event-window.
  D2  event windows OUTSIDE the clock window: do they still lift?
  D3  INSIDE the clock window: event days vs non-event days.
  D4  reverse direction: clock-window lift computed on NON-event days only --
      if it survives, the calendar does not explain the clock law.

Adoption bar (fixed)
--------------------
A calendar condition qualifies as a radar-module CANDIDATE iff ALL of:
  (1) lift >= 2.0
  (2) >= 15 event windows in range
  (3) the effect survives removing the clock overlap, i.e. EITHER
      D2 (non-clock event windows) still lifts >= 2.0,
      OR D3 (event days inside the clock beat non-event days inside the clock)
      by a margin whose exact binomial p < 0.05.
Below the bar -> reported as a PRIOR FOR FX ONLY, not a BTC radar module.

Known limitations (stated before seeing any result)
---------------------------------------------------
  * ~19-21 events in 210 days is thin.  A +/-30m window is 61 minutes; 20 events
    is ~1220 minutes = 0.4% of the sample.  Power is low by construction.
  * CPI dates are approximate.  A 1-day date error makes a +/-30m window miss
    completely -- the CPI arm is noise-dominated unless the rule is right.
  * One contiguous 7-month regime, one asset, one storm threshold.

Usage:  PYTHONPATH=src python scripts/research_macro_calendar.py
        (idempotent, deterministic, no network, no RNG)
"""

from __future__ import annotations

import datetime as dt
import math
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research_storm as A            # noqa: E402  storm definition, verbatim
import research_storm_b as B          # noqa: E402  anchor loader, verbatim

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

WIN_PRIMARY = 30                      # minutes, +/-
WIN_SECONDARY = 90                    # minutes, +/-

CLOCK_LO = 12 * 60 + 30               # 12:30 UTC, inclusive
CLOCK_HI = 15 * 60                    # 15:00 UTC, exclusive

BAR_LIFT = 2.0
BAR_MIN_WINDOWS = 15
BAR_P = 0.05

# FOMC 2026 statement days (2nd day of each 2-day meeting). Pre-announced 2025.
# CONFIDENCE MEDIUM-HIGH -- study is run with AND without these.
FOMC_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def line(c: str = "-", n: int = 100) -> None:
    print(c * n)


def header(t: str) -> None:
    print()
    line("=")
    print(t)
    line("=")


# --------------------------------------------------------------------------- #
# 0. calendar construction (pure rules)
# --------------------------------------------------------------------------- #
def et_to_utc(day: dt.date, hh: int, mm: int) -> pd.Timestamp:
    """08:30 America/New_York on `day` -> UTC, DST-correct via zoneinfo."""
    local = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET)
    return pd.Timestamp(local.astimezone(UTC)).tz_convert("UTC").floor("min")


def first_friday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def nearest_weekday(d: dt.date) -> dt.date:
    if d.weekday() == 5:              # Saturday -> Friday
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:              # Sunday -> Monday
        return d + dt.timedelta(days=1)
    return d


def build_calendar(months: list[tuple[int, int]], cpi_shift_days: int = 0) -> pd.DataFrame:
    """Rule-derived US macro calendar. Returns tz-aware UTC timestamps + notes."""
    rows = []

    for (y, m) in months:
        d = first_friday(y, m)
        note = ""
        if d.day <= 2:
            note = "first Friday is day<=2; BLS usually pushes to the 2nd Friday -> DATE DOUBTFUL"
        if (d.month, d.day) == (7, 3):
            note = "Jul 3 is the observed July-4 federal holiday; BLS would release Jul 2 -> DATE DOUBTFUL"
        rows.append(dict(kind="NFP", ts=et_to_utc(d, 8, 30), date=d, rule="first Friday, 08:30 ET",
                         conf="rule HIGH / date MEDIUM", note=note))

    for (y, m) in months:
        raw = dt.date(y, m, 12)
        d = nearest_weekday(raw) + dt.timedelta(days=cpi_shift_days)
        note = "APPROXIMATE (rule: day 12 snapped to nearest weekday)"
        if d.weekday() >= 5:
            note += " -- shifted onto a weekend, BLS never releases then"
        rows.append(dict(kind="CPI", ts=et_to_utc(d, 8, 30), date=d,
                         rule="day 12 -> nearest weekday, 08:30 ET",
                         conf="date LOW", note=note))

    for s in FOMC_2026:
        d = dt.date.fromisoformat(s)
        rows.append(dict(kind="FOMC", ts=et_to_utc(d, 14, 0), date=d, rule="statement day, 14:00 ET",
                         conf="date MEDIUM-HIGH (pre-announced 2025)", note=""))

    cal = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
    return cal


# --------------------------------------------------------------------------- #
# 1. metric machinery
# --------------------------------------------------------------------------- #
def window_mask(idx: pd.DatetimeIndex, stamps, half: int) -> np.ndarray:
    """True at every minute within +/- `half` minutes of any stamp (inclusive)."""
    m = np.zeros(len(idx), dtype=bool)
    pos = idx.get_indexer(pd.DatetimeIndex(stamps))
    for p in pos:
        if p < 0:
            continue
        m[max(0, p - half): min(len(idx), p + half + 1)] = True
    return m


def asym_mask(idx: pd.DatetimeIndex, stamps, lo: int, hi: int) -> np.ndarray:
    """True at minutes in [stamp+lo, stamp+hi] (minutes, signed)."""
    m = np.zeros(len(idx), dtype=bool)
    pos = idx.get_indexer(pd.DatetimeIndex(stamps))
    for p in pos:
        if p < 0:
            continue
        m[max(0, p + lo): min(len(idx), p + hi + 1)] = True
    return m


def binom_tail_ge(k: int, n: int, p: float) -> float:
    """Exact one-sided P(X >= k), X ~ Binom(n, p). Deterministic, no scipy."""
    if n <= 0 or k <= 0:
        return 1.0
    if p <= 0.0:
        return 0.0 if k > 0 else 1.0
    if p >= 1.0:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    tot = 0.0
    for i in range(int(k), n + 1):
        lg = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
              + i * lp + (n - i) * lq)
        tot += math.exp(lg)
    return min(1.0, tot)


def rate_stats(onset: np.ndarray, sel: np.ndarray, universe: np.ndarray) -> dict:
    """Storm-onset rate inside `sel` vs inside `universe & ~sel`."""
    sel = sel & universe
    out = universe & ~sel
    n_in, n_out = int(sel.sum()), int(out.sum())
    k_in, k_out = int(onset[sel].sum()), int(onset[out].sum())
    r_in = k_in / n_in if n_in else float("nan")
    r_out = k_out / n_out if n_out else float("nan")
    lift = r_in / r_out if (n_out and r_out > 0) else float("nan")
    k_tot, n_tot = k_in + k_out, n_in + n_out
    p = binom_tail_ge(k_in, k_tot, n_in / n_tot) if n_tot else float("nan")
    return dict(n_in=n_in, n_out=n_out, k_in=k_in, k_out=k_out, k_tot=k_tot,
                r_in=r_in, r_out=r_out, lift=lift,
                recall=(k_in / k_tot if k_tot else float("nan")),
                per_10k_in=1e4 * r_in, per_10k_out=1e4 * r_out, p=p)


def fmt(m: dict) -> str:
    lift = "-" if not np.isfinite(m["lift"]) else f"{m['lift']:.2f}"
    return (f"{m['n_in']:>9}{m['k_in']:>9}{m['per_10k_in']:>12.2f}"
            f"{m['per_10k_out']:>12.2f}{lift:>8}{m['recall']:>9.3f}{m['p']:>9.3f}")


HDR = (f"{'condition':<44}{'minutes':>9}{'storms':>9}{'in/10k':>12}"
       f"{'out/10k':>12}{'lift':>8}{'recall':>9}{'p':>9}")


# --------------------------------------------------------------------------- #
def main() -> None:
    header("SYNERGY STUDY #1 -- US MACRO CALENDAR vs BTC STORMS")
    print(__doc__.split("Usage:")[0].strip()[:0] or "", end="")
    print("Pre-registration is the module docstring of this file; nothing below was tuned.")

    # ---------------------------------------------------------------- data
    header("0. DATA LOAD  (loader imported verbatim from research_storm_b.load_anchor)")
    b = B.load_anchor()
    idx = b.index
    n_days = (idx[-1] - idx[0]).total_seconds() / 86400.0

    # pandas datetime64 unit trap (research-protocol sec.6) -- cross-check line
    EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
    tsec = ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    print(f"epoch cross-check: idx[0]={idx[0]}  tsec[0]={tsec[0]:.0f}  "
          f"-> {pd.Timestamp(tsec[0], unit='s', tz='UTC')}   "
          f"median step={np.median(np.diff(tsec)):.0f}s (must be 60)")

    # ---------------------------------------------------------------- storms
    header("1. STORM DEFINITION  (imported verbatim from research_storm.build_storms)")
    storm_min, events = A.build_storms(b["close"])
    onset = np.zeros(len(idx), dtype=bool)
    onset[idx.get_indexer(events)] = True
    print(f"storm minute : |{A.STORM_WINDOW_MIN}m log-return| >= {A.STORM_THRESHOLD * 100:.1f}%")
    print(f"dedup        : first storm minute after >= {A.STORM_DEDUP_MIN}m clean")
    print(f"storm minutes: {int(storm_min.sum())} of {len(idx)} ({100 * storm_min.mean():.2f}%)")
    print(f"storm EVENTS : {len(events)} over {n_days:.1f} days "
          f"({len(events) / n_days * 7:.2f}/week)   base onset rate = "
          f"{1e4 * len(events) / len(idx):.2f} per 10k minutes")

    print("\nSANITY -- the clock law of KNOWLEDGE.md sec.2, re-measured in THIS study's metric")
    mod = idx.hour * 60 + idx.minute
    clock = (mod >= CLOCK_LO) & (mod < CLOCK_HI)
    universe = np.ones(len(idx), dtype=bool)
    mc = rate_stats(onset, clock, universe)
    print(HDR)
    line()
    print(f"{'CLOCK 12:30-15:00 UTC (whole sample)':<44}" + fmt(mc))
    print("  (the 2.23x in KNOWLEDGE.md is a different statistic -- P(storm within 2h | ON) on a")
    print("   90d segment.  This row is the onset-rate lift used consistently throughout below.)")

    # ---------------------------------------------------------------- DST proof
    header("2. CALENDAR CONSTRUCTION  (rules only -- no memorised release list)")
    print("DST SANITY (US DST 2026 = 2026-03-08 .. 2026-11-01), via zoneinfo America/New_York:")
    for d in ["2026-03-06", "2026-03-08", "2026-03-13", "2026-11-01"]:
        day = dt.date.fromisoformat(d)
        loc = dt.datetime(day.year, day.month, day.day, 8, 30, tzinfo=ET)
        print(f"  08:30 ET on {d} ({loc.strftime('%a')}) is {loc.tzname()} -> "
              f"{et_to_utc(day, 8, 30)}   [expect 13:30 UTC before Mar 8, 12:30 UTC after]")
    print(f"  14:00 ET on 2026-01-28 (EST) -> {et_to_utc(dt.date(2026, 1, 28), 14, 0)}   [expect 19:00 UTC]")
    print(f"  14:00 ET on 2026-06-17 (EDT) -> {et_to_utc(dt.date(2026, 6, 17), 14, 0)}   [expect 18:00 UTC]")

    months = [(2026, m) for m in range(1, 13)]
    cal_full = build_calendar(months)
    lo, hi = idx[0], idx[-1]
    in_range = (cal_full["ts"] >= lo + pd.Timedelta(minutes=WIN_SECONDARY)) & \
               (cal_full["ts"] <= hi - pd.Timedelta(minutes=WIN_SECONDARY))
    cal = cal_full[in_range].reset_index(drop=True)

    print(f"\nrule-derived events in 2026: {len(cal_full)};  inside the data span with a full "
          f"+/-{WIN_SECONDARY}m window: {len(cal)}")
    print(f"\n{'kind':<6}{'local date':<13}{'wd':<5}{'UTC timestamp':<28}{'clock?':<8}confidence / note")
    line()
    for _, r in cal.iterrows():
        t = r["ts"]
        mm = t.hour * 60 + t.minute
        inclk = "YES" if (CLOCK_LO <= mm < CLOCK_HI) else "no"
        print(f"{r['kind']:<6}{str(r['date']):<13}{r['date'].strftime('%a'):<5}{str(t):<28}"
              f"{inclk:<8}{r['conf']}"
              + (f" | {r['note']}" if r["note"] else ""))

    print("\nRULES USED (transcribed from the pre-registration, not tuned):")
    for k in ["NFP", "CPI", "FOMC"]:
        sub = cal_full[cal_full["kind"] == k]
        print(f"  {k:<5}: {sub['rule'].iloc[0]}   -- {sub['conf'].iloc[0]}")
    print("\nHONEST SOURCING NOTE: no 2026 release date below is confirmed against a primary")
    print("source.  NFP/FOMC dates follow deterministic public rules and are likely right;")
    print("CPI dates are a RULE APPROXIMATION and any single one may be off by 1-3 days.")

    # ---------------------------------------------------------------- primary
    header("3. PRIMARY RESULT  --  storm-onset rate inside event windows")
    for half, tag in [(WIN_PRIMARY, "PRIMARY"), (WIN_SECONDARY, "SECONDARY")]:
        print(f"\n[{tag}]  window = event +/- {half} min  ({2 * half + 1} minutes per event)")
        print(HDR)
        line()
        rows = []
        for kind in ["NFP", "CPI", "FOMC"]:
            st = cal[cal["kind"] == kind]["ts"]
            m = rate_stats(onset, window_mask(idx, st, half), universe)
            m["_n_ev"] = len(st)
            rows.append((kind, m))
            print(f"{kind + f'  (n_ev={len(st)})':<44}" + fmt(m))
        for label, kinds in [("ALL (NFP+CPI+FOMC)", ["NFP", "CPI", "FOMC"]),
                             ("NO-FOMC (NFP+CPI)", ["NFP", "CPI"]),
                             ("08:30-ET only (NFP+CPI, same clock slot)", ["NFP", "CPI"])]:
            st = cal[cal["kind"].isin(kinds)]["ts"]
            m = rate_stats(onset, window_mask(idx, st, half), universe)
            print(f"{label + f'  (n_ev={len(st)})':<44}" + fmt(m))
            if label.startswith("08:30"):
                break
        print(f"{'-- reference: CLOCK 12:30-15:00 UTC':<44}" + fmt(mc))

    # ---------------------------------------------------------------- per-event
    header("4. PER-EVENT DETAIL  (thin n -> every event is shown, +/-30m and +/-90m)")
    ret30 = (np.log(b["close"]) - np.log(b["close"]).shift(A.STORM_WINDOW_MIN)).abs().to_numpy()
    print(f"{'kind':<6}{'UTC timestamp':<28}{'st30':>6}{'st90':>6}{'max|30m ret| +/-90m':>22}"
          f"{'  storm onsets in +/-90m'}")
    line()
    hit30 = {k: 0 for k in ["NFP", "CPI", "FOMC"]}
    hit90 = {k: 0 for k in ["NFP", "CPI", "FOMC"]}
    for _, r in cal.iterrows():
        p = idx.get_indexer(pd.DatetimeIndex([r["ts"]]))[0]
        w30 = onset[max(0, p - 30):p + 31]
        w90 = onset[max(0, p - 90):p + 91]
        mx = np.nanmax(ret30[max(0, p - 90):p + 91])
        stamps = [str(idx[q].time())[:5] for q in range(max(0, p - 90), min(len(idx), p + 91))
                  if onset[q]]
        hit30[r["kind"]] += int(w30.any())
        hit90[r["kind"]] += int(w90.any())
        print(f"{r['kind']:<6}{str(r['ts']):<28}{('Y' if w30.any() else '.'):>6}"
              f"{('Y' if w90.any() else '.'):>6}{100 * mx:>21.2f}%  "
              f"{','.join(stamps) if stamps else '-'}")
    print(f"\n{'kind':<6}{'events':>8}{'>=1 storm in +/-30m':>22}{'>=1 storm in +/-90m':>22}"
          f"{'hit rate 30 / 90':>22}")
    line()
    for k in ["NFP", "CPI", "FOMC"]:
        n = int((cal["kind"] == k).sum())
        print(f"{k:<6}{n:>8}{hit30[k]:>22}{hit90[k]:>22}"
              f"{f'{hit30[k] / max(n, 1):.2f} / {hit90[k] / max(n, 1):.2f}':>22}")
    n_all = len(cal)
    print(f"{'ALL':<6}{n_all:>8}{sum(hit30.values()):>22}{sum(hit90.values()):>22}"
          f"{f'{sum(hit30.values()) / n_all:.2f} / {sum(hit90.values()) / n_all:.2f}':>22}")
    print("\nfor scale: an arbitrary 61-minute window catches >=1 storm onset with probability")
    print(f"  ~1-(1-r)^61 = {1 - (1 - len(events) / len(idx)) ** 61:.3f}, and a 181-minute window "
          f"~{1 - (1 - len(events) / len(idx)) ** 181:.3f}")

    # ---------------------------------------------------------------- clock decomposition
    header("5. CLOCK DECOMPOSITION  --  does the calendar add anything BEYOND 12:30-15:00 UTC?")
    st_all = cal["ts"]
    st_nofomc = cal[cal["kind"] != "FOMC"]["ts"]
    for lab, st in [("ALL events", st_all), ("NO-FOMC", st_nofomc)]:
        for half in [WIN_PRIMARY, WIN_SECONDARY]:
            w = window_mask(idx, st, half)
            print(f"\n### {lab},  window +/-{half}m")
            ov = int((w & clock).sum())
            print(f"  overlap: {ov} of {int(w.sum())} event-window minutes "
                  f"({100 * ov / max(1, int(w.sum())):.1f}%) sit inside the clock window")

            print("\n  D1  2x2 crosstab   clock x event-window")
            print(f"    {'cell':<30}{'minutes':>10}{'storms':>9}{'per 10k min':>14}{'lift vs base':>14}")
            line("-", 80)
            base = len(events) / len(idx)
            for cl in [False, True]:
                for ev in [False, True]:
                    sel = (clock == cl) & (w == ev)
                    n = int(sel.sum())
                    k = int(onset[sel].sum())
                    r = k / n if n else float("nan")
                    lab2 = f"clock={'ON ' if cl else 'off'}  event={'ON ' if ev else 'off'}"
                    lf = f"{r / base:.2f}" if n else "-"
                    print(f"    {lab2:<30}{n:>10}{k:>9}{1e4 * r:>14.2f}{lf:>14}")

            print("\n  D2  event windows OUTSIDE the clock window "
                  "(universe = all non-clock minutes)")
            print("    " + HDR)
            line("-", 104)
            m = rate_stats(onset, w, ~clock)
            print(f"    {'event window & NOT clock':<44}" + fmt(m))
            d2_lift, d2_p, d2_k = m["lift"], m["p"], m["k_in"]

            print("\n  D3  INSIDE the clock window: event days vs non-event days")
            evday = np.isin(idx.normalize(), pd.DatetimeIndex(st).normalize())
            print("    " + HDR)
            line("-", 104)
            m3 = rate_stats(onset, evday, clock)
            print(f"    {'clock minutes on EVENT days':<44}" + fmt(m3))
            d3_lift, d3_p = m3["lift"], m3["p"]

            print("\n  D4  reverse: is the CLOCK law explained by the calendar? "
                  "(clock lift on NON-event days)")
            print("    " + HDR)
            line("-", 104)
            m4 = rate_stats(onset, clock, ~evday)
            print(f"    {'clock 12:30-15:00 among NON-event days':<44}" + fmt(m4))
            m4b = rate_stats(onset, clock, evday)
            print(f"    {'clock 12:30-15:00 among EVENT days':<44}" + fmt(m4b))

            if half == WIN_PRIMARY:
                keep = (lab, d2_lift, d2_p, d2_k, d3_lift, d3_p)
                if lab == "ALL events":
                    verdict_all = keep
                else:
                    verdict_nof = keep

    # ---------------------------------------------------------------- post-only diagnostic
    header("6. DIAGNOSTIC (not part of the bar) -- STRICTLY POST-EVENT ONSETS")
    print("A storm onset at minute t is defined by the return over [t-30, t], so an onset in the")
    print("first 30 minutes AFTER a release can only partly reflect pre-release drift, and an")
    print("onset in the 30 minutes BEFORE it cannot reflect the release at all.  Splitting the")
    print("+/-30m window into its two halves is a tightening, not a loosening:")
    print("\n" + HDR)
    line()
    for lab, (a, z) in [("pre-window  [E-30, E-1]", (-30, -1)),
                        ("post-window [E+1, E+30]", (1, 30)),
                        ("post-window [E+1, E+90]", (1, 90))]:
        for kinds, tag in [(["NFP", "CPI", "FOMC"], "ALL"), (["NFP"], "NFP"), (["FOMC"], "FOMC")]:
            st = cal[cal["kind"].isin(kinds)]["ts"]
            m = rate_stats(onset, asym_mask(idx, st, a, z), universe)
            print(f"{tag + '  ' + lab:<44}" + fmt(m))
        print()

    # ---------------------------------------------------------------- permutation
    header("7. DAY-SHIFT PERMUTATION NULL  (the cleanest control for the clock law)")
    print("Shifting the whole calendar by an INTEGER NUMBER OF DAYS keeps every event at exactly")
    print("the same UTC time-of-day, so a shifted calendar carries the identical clock exposure.")
    print("If the DATE matters beyond the TIME, the true calendar must beat its own day-shifts.")
    print("Multiples of 7 days additionally preserve weekday (NFP is always a Friday).")
    print("Fully deterministic: the shift set is fixed, no RNG.\n")

    def perm_report(st, half, shifts, label):
        real = rate_stats(onset, window_mask(idx, st, half), universe)
        vals = []
        for k in shifts:
            sh = pd.DatetimeIndex(st) + pd.Timedelta(days=k)
            sh = sh[(sh >= lo + pd.Timedelta(minutes=half)) & (sh <= hi - pd.Timedelta(minutes=half))]
            if len(sh) < max(3, len(st) - 3):
                continue
            vals.append(rate_stats(onset, window_mask(idx, sh, half), universe)["lift"])
        vals = np.array([v for v in vals if np.isfinite(v)])
        if not len(vals):
            print(f"{label:<40} real lift={real['lift']:.2f}   (no admissible shifts)")
            return
        ge = int((vals >= real["lift"]).sum())
        pp = (ge + 1) / (len(vals) + 1)
        rl = f"{real['lift']:.2f}" if np.isfinite(real["lift"]) else "-"
        print(f"{label:<40}{rl:>10}{np.median(vals):>10.2f}{np.percentile(vals, 90):>10.2f}"
              f"{vals.max():>10.2f}{len(vals):>8}{ge:>8}{pp:>9.3f}")

    shifts7 = [k for k in range(-70, 71, 7) if k != 0]
    shifts1 = [k for k in range(-45, 46) if k != 0]
    for shifts, sname in [(shifts7, "multiples of 7 days (+/-70d, weekday preserved)"),
                          (shifts1, "every integer day (+/-45d)")]:
        print(f"\n[shift set: {sname}]")
        print(f"{'condition':<40}{'real':>10}{'null med':>10}{'null p90':>10}{'null max':>10}"
              f"{'n_null':>8}{'>=real':>8}{'p_perm':>9}")
        line()
        for kinds, tag in [(["NFP"], "NFP"), (["CPI"], "CPI"), (["FOMC"], "FOMC"),
                           (["NFP", "CPI"], "NO-FOMC"), (["NFP", "CPI", "FOMC"], "ALL")]:
            for half in [WIN_PRIMARY, WIN_SECONDARY]:
                st = cal[cal["kind"].isin(kinds)]["ts"]
                perm_report(st, half, shifts, f"{tag}  +/-{half}m")

    # ---------------------------------------------------------------- sensitivity
    header("8. SENSITIVITY  --  CPI date uncertainty (+/-1 and +/-2 days) and FOMC in/out")
    print(HDR)
    line()
    for sh in [-2, -1, 0, 1, 2]:
        c2 = build_calendar(months, cpi_shift_days=sh)
        c2 = c2[(c2["ts"] >= lo + pd.Timedelta(minutes=WIN_SECONDARY))
                & (c2["ts"] <= hi - pd.Timedelta(minutes=WIN_SECONDARY))]
        st = c2[c2["kind"] == "CPI"]["ts"]
        m = rate_stats(onset, window_mask(idx, st, WIN_PRIMARY), universe)
        wd = ",".join(sorted({t.strftime("%a") for t in pd.DatetimeIndex(st)}))
        print(f"{f'CPI rule {sh:+d}d  +/-30m  (n_ev={len(st)}, {wd})':<44}" + fmt(m))
    print()
    for sh in [-2, -1, 0, 1, 2]:
        c2 = build_calendar(months, cpi_shift_days=sh)
        c2 = c2[(c2["ts"] >= lo + pd.Timedelta(minutes=WIN_SECONDARY))
                & (c2["ts"] <= hi - pd.Timedelta(minutes=WIN_SECONDARY))]
        st = c2[c2["kind"] == "CPI"]["ts"]
        m = rate_stats(onset, window_mask(idx, st, WIN_SECONDARY), universe)
        print(f"{f'CPI rule {sh:+d}d  +/-90m  (n_ev={len(st)})':<44}" + fmt(m))

    print("\nsensitivity: storm-threshold robustness (storm definition re-run; NOT the bar)")
    print(HDR)
    line()
    for thr in [0.006, 0.008, 0.010]:
        save = A.STORM_THRESHOLD
        A.STORM_THRESHOLD = thr
        _, ev2 = A.build_storms(b["close"])
        A.STORM_THRESHOLD = save
        on2 = np.zeros(len(idx), dtype=bool)
        on2[idx.get_indexer(ev2)] = True
        m = rate_stats(on2, window_mask(idx, st_all, WIN_PRIMARY), universe)
        mck = rate_stats(on2, clock, universe)
        print(f"{f'thr={thr * 100:.1f}%  ALL events +/-30m  (n_storm={len(ev2)})':<44}" + fmt(m))
        print(f"{f'thr={thr * 100:.1f}%  clock 12:30-15:00 reference':<44}" + fmt(mck))

    # ------------------------------------------------- calendar-agnostic corroboration
    header("9. CALENDAR-AGNOSTIC CORROBORATION  (does NOT need the exact dates to be right)")
    print("If 08:30-ET releases drive storms, then inside the 12:30-13:30 UTC hour the storm")
    print("onset rate should be elevated on NFP-shaped days (Fridays) and in the CPI day-of-month")
    print("band 10-15.  This needs no exact date, so it is immune to the CPI date uncertainty.\n")
    slot = (mod >= 12 * 60 + 30) & (mod < 13 * 60 + 30)
    print("A. day-of-month profile of storm onsets inside the 12:30-13:30 UTC slot")
    print(f"{'day-of-month':<16}{'minutes':>10}{'storms':>9}{'per 10k':>10}{'lift vs slot':>14}  bar")
    line()
    slot_rate = onset[slot].sum() / max(1, slot.sum())
    dom = idx.day.to_numpy()
    for band, sel_days in [("1-9", range(1, 10)), ("10-15", range(10, 16)),
                           ("16-23", range(16, 24)), ("24-31", range(24, 32))]:
        sel = slot & np.isin(dom, list(sel_days))
        n, k = int(sel.sum()), int(onset[sel].sum())
        r = k / n if n else 0.0
        print(f"{band:<16}{n:>10}{k:>9}{1e4 * r:>10.2f}{r / slot_rate if slot_rate else 0:>14.2f}"
              f"  " + "#" * int(round(20 * r / slot_rate if slot_rate else 0)))
    print("\nB. weekday profile of storm onsets inside the 12:30-13:30 UTC slot "
          "(NFP is always a Friday)")
    print(f"{'weekday':<16}{'minutes':>10}{'storms':>9}{'per 10k':>10}{'lift vs slot':>14}  bar")
    line()
    wdn = idx.weekday.to_numpy()
    for i, nm in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        sel = slot & (wdn == i)
        n, k = int(sel.sum()), int(onset[sel].sum())
        r = k / n if n else 0.0
        print(f"{nm:<16}{n:>10}{k:>9}{1e4 * r:>10.2f}{r / slot_rate if slot_rate else 0:>14.2f}"
              f"  " + "#" * int(round(20 * r / slot_rate if slot_rate else 0)))
    print("\nC. minute-of-day profile around 12:30 UTC "
          "(a release spike should be visible as a step AT 12:30, not a smooth hump)")
    print(f"{'UTC slot':<16}{'minutes':>10}{'storms':>9}{'per 10k':>10}  bar")
    line()
    for a in range(11 * 60, 15 * 60, 30):
        sel = (mod >= a) & (mod < a + 30)
        n, k = int(sel.sum()), int(onset[sel].sum())
        r = 1e4 * k / n if n else 0.0
        print(f"{f'{a // 60:02d}:{a % 60:02d}-{(a + 30) // 60:02d}:{(a + 30) % 60:02d}':<16}"
              f"{n:>10}{k:>9}{r:>10.2f}  " + "#" * int(round(r)))

    # ---------------------------------------------------------------- verdict
    header("10. PRE-REGISTERED VERDICT")
    print("bar: lift >= 2.0  AND  >= 15 event windows  AND  survives clock removal")
    print("     (D2 non-clock event windows lift >= 2.0, OR D3 event-days-inside-clock beats")
    print("      non-event-days-inside-clock with exact binomial p < 0.05)\n")
    print(f"{'configuration':<28}{'n_ev':>6}{'lift30':>9}{'p30':>8}{'lift90':>9}{'p90':>8}"
          f"{'D2 lift':>9}{'D3 lift':>9}{'D3 p':>8}   verdict")
    line()
    for tag, kinds, dec in [("ALL (NFP+CPI+FOMC)", ["NFP", "CPI", "FOMC"], verdict_all),
                            ("NO-FOMC (NFP+CPI)", ["NFP", "CPI"], verdict_nof)]:
        st = cal[cal["kind"].isin(kinds)]["ts"]
        m30 = rate_stats(onset, window_mask(idx, st, WIN_PRIMARY), universe)
        m90 = rate_stats(onset, window_mask(idx, st, WIN_SECONDARY), universe)
        _, d2l, d2p, d2k, d3l, d3p = dec
        n_ev = len(st)
        lift_ok = (m30["lift"] >= BAR_LIFT) if np.isfinite(m30["lift"]) else False
        n_ok = n_ev >= BAR_MIN_WINDOWS
        surv = (np.isfinite(d2l) and d2l >= BAR_LIFT) or (np.isfinite(d3p) and d3p < BAR_P
                                                         and np.isfinite(d3l) and d3l > 1.0)
        ok = lift_ok and n_ok and surv
        why = []
        if not lift_ok:
            why.append(f"lift30={m30['lift']:.2f}<2.0")
        if not n_ok:
            why.append(f"only {n_ev} windows (<{BAR_MIN_WINDOWS})")
        if not surv:
            why.append("does not survive clock removal (D2 and D3 both fail)")
        print(f"{tag:<28}{n_ev:>6}{m30['lift']:>9.2f}{m30['p']:>8.3f}{m90['lift']:>9.2f}"
              f"{m90['p']:>8.3f}{d2l:>9.2f}{d3l:>9.2f}{d3p:>8.3f}   "
              f"{'CANDIDATE' if ok else 'BELOW BAR -- ' + '; '.join(why)}")
    for tag in ["NFP", "CPI", "FOMC"]:
        st = cal[cal["kind"] == tag]["ts"]
        m30 = rate_stats(onset, window_mask(idx, st, WIN_PRIMARY), universe)
        m90 = rate_stats(onset, window_mask(idx, st, WIN_SECONDARY), universe)
        print(f"{tag + ' alone':<28}{len(st):>6}{m30['lift']:>9.2f}{m30['p']:>8.3f}"
              f"{m90['lift']:>9.2f}{m90['p']:>8.3f}{'-':>9}{'-':>9}{'-':>8}   "
              f"BELOW BAR -- only {len(st)} windows (<{BAR_MIN_WINDOWS}) by construction")

    # ---------------------------------------------------------------- sanity
    header("11. SANITY CHECKLIST  (research-protocol sec.6)")
    print("* look-ahead: ZERO by construction.  The calendar is published in advance; a storm")
    print("  onset at t is defined by the return over [t-30, t], entirely in t's past.  Section 6")
    print("  additionally splits the window into strictly-pre and strictly-post halves.")
    print("* tautology check: the storm definition never sees the calendar and the calendar never")
    print("  sees prices.  The two are built by independent code paths (research_storm.build_storms")
    print("  vs build_calendar) and joined only by timestamp.")
    print("* datetime64 unit trap: the epoch cross-check line in section 0 confirms 60s steps.")
    print("* determinism: no RNG anywhere.  The permutation null is a FIXED shift set")
    print(f"  ({len(shifts7)} weekday-preserving + {len(shifts1)} all-day shifts), not sampling.")
    print("* reproduction gate: storm count / storm-minute share below must match research_storm_b")
    print(f"  section 1 on the same file:  storm minutes={int(storm_min.sum())}, "
          f"events={len(events)}, share={100 * storm_min.mean():.2f}%")
    print("* no network access; the only input is the CSV named in the pre-registration.")

    header("12. CAVEATS")
    print(f"1. THIN.  {len(cal)} events in {n_days:.0f} days.  At +/-30m the tested region is "
          f"{100 * window_mask(idx, st_all, WIN_PRIMARY).sum() / len(idx):.2f}% of all minutes.")
    print("2. CPI dates are a rule approximation (section 2).  A 1-day error makes a +/-30m window")
    print("   miss entirely, so the CPI arm is noise-dominated regardless of the true effect.")
    print("   Section 9A is the date-free substitute for it.")
    print("3. FOMC 2026 dates are pre-announced but unverified here; every table is reported both")
    print("   WITH and WITHOUT FOMC for exactly this reason.")
    print("4. One asset, one contiguous 7-month regime, one storm threshold (section 8 varies the")
    print("   threshold; it does not vary the regime).")
    print("5. Storm events cluster on a handful of days, so minute counts overstate the effective")
    print("   sample.  The per-event hit-rate table (section 4) and the day-shift permutation")
    print("   (section 7) are the honest sample-size views.")
    print("6. NFP and CPI both fire at 08:30 ET = the START of the 12:30-15:00 UTC clock window.")
    print("   Any 08:30-ET result and the clock law are mechanically confounded; only D2/D3/D4 and")
    print("   the day-shift permutation can separate them, and both are thin.")

    print()
    line("=")
    print("done.")
    line("=")


if __name__ == "__main__":
    sys.exit(main())
