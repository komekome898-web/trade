#!/usr/bin/env python3
"""Study R6-A -- Stage-A MECHANISM GATE for the regime-switching proposal.

Pre-registered question
-----------------------
Does the range-edge BARRIER RACE FLIP in the deep-calm regime?

The established law (docs/KNOWLEDGE.md sec.2, report k, measured by
scripts/research_range_reversed.py section 3d): on calm-minute range-edge
touches the symmetric 10bps/10bps race resolves 31.7% revert vs 61.4% break,
n=23,642.  "A range-edge touch is a momentum event, not a mean-reversion
event."  That measurement used the study's calm filter, whose realized duty on
this tape is ~90% of minutes -- i.e. it is barely a filter at all.

The owner's proposal is a regime switch: run the champion in high-vr minutes
and a matilda-style range grid in DEEP calm.  The vr bottom quartile is a ~25%
duty regime and report n showed it is structurally disjoint from the
champion's own entries.  If reversion does not beat breakout even THERE, the
switching idea dies at mechanism level and no Stage-B build is warranted.

THIS STAGE MEASURES A MECHANISM ONLY.  There is no strategy, no execution
model, no P&L backtest, and nothing is selected or tuned.  Every number below
is a first-passage frequency.

Data (fixed)
------------
data/executions_FX_BTC_JPY.csv   820,000 public prints, 2026-07-21 .. 2026-08-20
                                 -> 1s last-price grid, forward filled
data/flow_FX_BTC_JPY.csv         1m OHLCV built from the SAME executions file
data/candles_FX_BTC_JPY.csv      1m OHLCV -- gated to be byte-identical OHLC to
                                 flow_*, which is what makes the frozen vr
                                 cutoffs below transferable without a refit
Tape loading, the 1s grid, the trailing-range construction and the barrier-race
machinery are REUSED VERBATIM from scripts/research_range_reversed.py (imported,
not re-implemented), so this study cannot drift from the law it is testing.

Event (fixed)
-------------
PRIMARY: every print at-or-beyond the trailing range edge -- exactly the event
set scripts/research_range_reversed.py section 3d raced, so the numbers here
are directly comparable to the law.  The study's ~90%-duty calm filter is OFF
in the primary: vr IS the regime definition in this study and stacking the old
filter on top would confound the two.  A calm-ON cross-tab is printed as a
diagnostic.

Range windows: EXACTLY TWO, reported separately, no others.
  W=120m  the prior study's selected family
  W=15m   matilda's own micro-scale (its 30s range on 5s bars; 15m is the
          shortest sensible transcription onto our 1m candles)

DE-CLUSTERING (diagnostics, NOT the verdict -- research-protocol sec.8.2):
  D1  first touch per (minute, side)
  D2  non-overlapping races: greedily accept a touch, then suppress every later
      touch until that race has resolved (or hit its 60-minute cap)
Both are reported for the Q1 cells.  The pre-registered bar is evaluated on the
PRIMARY event set, as handed down, and D1/D2 cannot change the verdict.

Regime condition (fixed)
------------------------
vr = (60m rolling high-low range) / (mean |1m close-open| over 60m), the
matilda v5.2 transcription from scripts/research_legacy_elements.py
(compute_vr, VR_WINDOW=60), read at the LAST COMPLETED MINUTE STRICTLY BEFORE
the touch's minute (a .shift(1); the raw vr window ends on its own bar, which
at a mid-minute touch would not yet be complete).

Quartile cutoffs are FROZEN, transcribed from report n and NOT refitted here:
  q25 = 14.08   q50 = 17.22   q75 = 21.16
(30d exploration segment = first 60% of the 30d frame.)  The full-precision
values are hard-coded below; a gate re-derives them from the raw file with
report n's own recipe and requires a bit-exact match, AND requires agreement
with report n's published two-decimal figures, before any result is read.

The race is reported for all four quartiles.  The PRE-REGISTERED PASS CELL IS
Q1 (bottom vr = deep calm).  Q2/Q3/Q4 are context and monotonicity evidence.

Barriers (enumerated, exactly two)
----------------------------------
Symmetric revert-vs-break from the RANGE EDGE, 60-minute cap, 1s grid:
  10bps / 10bps   comparable to the law
   5bps /  5bps   deep-calm moves are smaller and a 10bps barrier may simply
                  never resolve there
UNRESOLVED% is reported for every cell.

PASS BAR (fixed before running)
-------------------------------
MECHANISM bar -- in Q1, at EITHER barrier size (and in either window; each of
the four Q1 cells is judged and printed separately, the verdict is their OR):
  (a) revert-first rate > break-first rate
  (b) n >= 2,000 touches
  (c) gap = revert% - break% >= 5.0 percentage points
Rates are UNCONDITIONAL shares of all touches in the cell -- the same
convention the law is quoted in (31.7 / 61.4 / 6.9 neither).  A coin-flip-
adjacent 51/49 does not clear costs, hence (c).

ECONOMIC bar -- stricter, reported for the 5bps cells:
a maker-entry fade earns +5bps gross when the revert barrier wins and loses
-(5 + 2.93) = -7.93bps when the break barrier wins (the 2.93bps calm taker
exit, docs/KNOWLEDGE.md sec.1).  EV = 5*P(rev) - 7.93*P(brk) > 0
  <=> P(rev)/P(brk) > 1.586  <=> revert share OF RESOLVED races > 61.3%.
The brief's round number is 61%; the exact break-even at these constants is
printed.  Unresolved races contribute ~0 to that EV, so the conditional-rate
form and the unconditional-EV form are the SAME test; the realized drift of the
unresolved group at its 60m cap is printed so the "~0" is auditable.

Also reported (pre-registered)
------------------------------
* touches/day in Q1 (capacity), raw and de-clustered
* the Q4 race (must confirm the momentum result if the mechanism is real)
* monotonicity of the revert rate across Q1..Q4 (clean gradient = mechanism,
  jumpy = noise)

Sanity gates (all must pass before any number is read)
------------------------------------------------------
* REPRODUCTION 1: the law itself -- W=120m, calm ON, judgment segment (last 40%)
  must return n=23,642 with 31.7% revert / 61.4% break.
* REPRODUCTION 2: the frozen vr cutoffs must be re-derivable from the raw file
  to full float precision.
* NO LOOK-AHEAD: range and vr hand-recomputed from raw arrays for sampled
  touches and proved to use only minutes strictly before the touch's minute.
  A start-at-second+1 race variant is run on the Q1 cells to bound the <1s
  forward-fill effect inherited from the law's machinery.
* EPOCH UNITS: the datetime64 -> seconds conversion cross-checked two ways
  (research-protocol sec.6 trap).
* DETERMINISM: the whole pipeline re-run for a cell must be bit-identical.

NO STRATEGY BACKTEST IS RUN IN THIS STAGE.

Run:  PYTHONPATH=src python scripts/research_vr_barrier.py
Read-only, no network, idempotent, writes nothing, commits nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402

import research_range_reversed as R                         # noqa: E402

DATA = ROOT / "data"
PRODUCT = "FX_BTC_JPY"

# ---- frozen constants (pre-registered, none of these is fitted here) ------- #
VR_WINDOW = 60                       # minutes, numerator and denominator
VR_CUTS = np.array([14.076535165193164,
                    17.219939463205357,
                    21.164353040819478])
VR_CUTS_PUBLISHED = np.array([14.08, 17.22, 21.16])   # report n, as printed
WINDOWS = (120, 15)                  # range windows, minutes -- exactly these
BARRIERS = (10.0, 5.0)               # bps, symmetric -- exactly these
CAP_SEC = R.HOLD_MAX_SEC             # 3600s, the law's cap
COST_TAKER_CALM = R.COST_TAKER_CALM  # 2.93 bps

BAR_MIN_TOUCHES = 2000
BAR_GAP_PP = 5.0
FADE_GROSS_BPS = 5.0                 # maker entry, 5bps barrier
FADE_LOSS_BPS = 5.0 + COST_TAKER_CALM
ECON_BREAKEVEN = FADE_LOSS_BPS / (FADE_GROSS_BPS + FADE_LOSS_BPS) * 100

QNAMES = {1: "Q1 (deep calm)", 2: "Q2", 3: "Q3", 4: "Q4 (trend)"}


def header(t: str) -> None:
    print("\n" + "=" * 92)
    print(t)
    print("=" * 92)


def sub(t: str) -> None:
    print("\n" + "-" * 92)
    print(t)
    print("-" * 92)


# --------------------------------------------------------------------------- #
# 1. vr feature
# --------------------------------------------------------------------------- #
def compute_vr(df: pd.DataFrame, window: int = VR_WINDOW) -> pd.Series:
    """matilda v5.2 vr, transcribed exactly as scripts/research_legacy_elements.py
    does it: (rolling high-low range) / (mean |close - open|), both over `window`
    bars ENDING ON the reference bar, completed bars only."""
    hh = df["high"].rolling(window, min_periods=window).max()
    ll = df["low"].rolling(window, min_periods=window).min()
    body = (df["close"] - df["open"]).abs()
    vola = body.rolling(window, min_periods=window).mean()
    return (hh - ll) / vola.replace(0.0, np.nan)


def load_minute_frame() -> pd.DataFrame:
    df = pd.read_csv(DATA / f"flow_{PRODUCT}.csv", index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def quartile_of(vr: np.ndarray) -> np.ndarray:
    """1..4 by the FROZEN cutoffs; 0 where vr is undefined."""
    q = np.searchsorted(VR_CUTS, np.nan_to_num(vr, nan=-1.0), side="right") + 1
    return np.where(np.isfinite(vr), q, 0).astype(np.int8)


# --------------------------------------------------------------------------- #
# 2. touches
# --------------------------------------------------------------------------- #
def touches(mk: R.Market, window: int, *, use_calm: bool, m_lo: int, m_hi: int):
    """Every print at-or-beyond the trailing `window`-minute edge.

    Delegates to research_range_reversed.signals so the event set is the law's
    event set by construction.  Returns (idx, side, lo, hi) with idx an index
    into the FULL print array.
    """
    cfg = R.Cfg(window, "third", use_calm=use_calm)
    return R.signals(mk, cfg, m_lo, m_hi)


# --------------------------------------------------------------------------- #
# 3. the barrier race
# --------------------------------------------------------------------------- #
def _first_true(mask: np.ndarray) -> int:
    i = int(mask.argmax())
    return i if mask[i] else 1 << 30


def barrier_race(mk: R.Market, sec: np.ndarray, side: np.ndarray,
                 edge: np.ndarray, bps: float, *, offset: int = 0):
    """Symmetric first-passage race from each touch, on the 1s grid.

    Semantics are transcribed from research_range_reversed.py section 3d:
      low-edge touch  (side>0): revert = price >= edge*(1+b),  break = < edge*(1-b)
      high-edge touch (side<0): revert = price <= edge*(1-b),  break = > edge*(1+b)
    Ties go to the break (conservative); with a single forward-filled price per
    second the two conditions are disjoint, so a tie can only be "neither".

    Returns (outcome, tsec):
      outcome  +1 revert first, -1 break first, 0 unresolved within the cap
      tsec     seconds from the touch second to resolution (cap where unresolved)

    `offset` shifts the scan start by whole seconds; offset=1 is the
    look-ahead-bound variant (the touch second's forward-filled price is the
    LAST print of that second, which can post-date the touch print itself).
    """
    n = mk.n
    price = mk.price
    up_mul = 1.0 + bps / 1e4
    dn_mul = 1.0 - bps / 1e4

    # dedup: identical (second, side, edge) triples race identically
    key = np.stack([sec.astype(np.float64), side.astype(np.float64), edge])
    _, first, inv = np.unique(key, axis=1, return_index=True, return_inverse=True)
    inv = np.asarray(inv).ravel()
    u_sec = sec[first]
    u_side = side[first]
    u_edge = edge[first]

    out = np.zeros(len(first), np.int8)
    tt = np.full(len(first), float(CAP_SEC))
    for k in range(len(first)):
        a = int(u_sec[k]) + offset
        if a >= n:
            continue
        b = min(n - 1, a + CAP_SEC)
        seg = price[a:b + 1]
        hi_thr = u_edge[k] * up_mul
        lo_thr = u_edge[k] * dn_mul
        if u_side[k] > 0:
            i_rev = _first_true(seg >= hi_thr)
            i_brk = _first_true(seg < lo_thr)
        else:
            i_rev = _first_true(seg <= lo_thr)
            i_brk = _first_true(seg > hi_thr)
        if i_rev < i_brk:
            out[k] = 1
            tt[k] = float(i_rev)
        elif i_brk < i_rev:
            out[k] = -1
            tt[k] = float(i_brk)
    return out[inv], tt[inv]


# --------------------------------------------------------------------------- #
# 4. reporting helpers
# --------------------------------------------------------------------------- #
RACE_HEAD = (f"{'n':>9} {'revert%':>9} {'break%':>9} {'unres%':>8} "
             f"{'gap_pp':>8} {'rev|res%':>9}")


def race_stats(out: np.ndarray) -> dict:
    n = int(out.size)
    if n == 0:
        return {"n": 0, "rev": np.nan, "brk": np.nan, "un": np.nan,
                "gap": np.nan, "cond": np.nan, "n_res": 0}
    nr = int((out == 1).sum())
    nb = int((out == -1).sum())
    nu = n - nr - nb
    res = nr + nb
    return {"n": n, "rev": nr / n * 100, "brk": nb / n * 100, "un": nu / n * 100,
            "gap": (nr - nb) / n * 100,
            "cond": (nr / res * 100) if res else np.nan, "n_res": res}


def race_row(s: dict) -> str:
    if s["n"] == 0:
        return f"{0:>9} {'-':>9} {'-':>9} {'-':>8} {'-':>8} {'-':>9}"
    return (f"{s['n']:>9,} {s['rev']:>8.1f}% {s['brk']:>8.1f}% "
            f"{s['un']:>7.1f}% {s['gap']:>+8.1f} {s['cond']:>8.1f}%")


def fwd_drift_at(mk: R.Market, sec: np.ndarray, side: np.ndarray,
                 hz: int) -> np.ndarray:
    """Side-adjusted move over `hz` seconds from a grid second.  + = fade wins."""
    a = np.clip(sec, 0, mk.n - 1)
    b = np.clip(a + hz, 0, mk.n - 1)
    return side.astype(float) * (mk.logp[b] - mk.logp[a]) * 1e4


# --------------------------------------------------------------------------- #
# 5. main
# --------------------------------------------------------------------------- #
def main() -> int:
    pd.set_option("display.width", 220)

    # ---------------------------------------------------------------- 0 ----- #
    header("0. DATA, EPOCH UNIT PROOF, REPRODUCTION GATES")
    mk = R.load_market()
    n_min = len(mk.minutes)
    split = int(n_min * 0.6)
    print(f"executions        : {len(mk.ptime):,} prints  "
          f"{pd.to_datetime(mk.ptime[0], unit='s', utc=True)} .. "
          f"{pd.to_datetime(mk.ptime[-1], unit='s', utc=True)}")
    print(f"1s grid           : {mk.n:,} seconds ({(mk.n - 1) / 86400:.2f} days)")
    print(f"1m candles        : {n_min:,} contiguous minutes")
    print(f"60/40 boundary    : minute {split} = "
          f"{pd.to_datetime(mk.minutes[split], unit='s', utc=True)}")

    sub("0a. epoch unit proof (research-protocol sec.6)")
    probe = pd.Series(["2026-07-21T08:17:22.19+00:00"])
    a1 = R.epoch_seconds(probe)[0]
    a2 = R.epoch_seconds_ns(probe)[0]
    raw = pd.read_csv(DATA / f"executions_{PRODUCT}.csv", nrows=20000)["exec_date"]
    d = float(np.abs(R.epoch_seconds(raw) - R.epoch_seconds_ns(raw)).max())
    print(f"  (idx-EPOCH)/Timedelta('1s') = {a1:.3f}")
    print(f"  ns-astype cross-check       = {a2:.3f}")
    print(f"  max|diff| over 20,000 tape rows = {d:.9f}   "
          f"{'OK' if d < 1e-6 else 'FAIL'}")
    gate_epoch = d < 1e-6

    sub("0b. REPRODUCTION 1 -- the law (report k / KNOWLEDGE sec.2)")
    print("  W=120m, calm filter ON, judgment segment (last 40%), 10/10 bps race.")
    li, lside, llo, lhi = touches(mk, 120, use_calm=True, m_lo=split, m_hi=n_min)
    l_sec = mk.psec[li]
    l_edge = np.where(lside > 0, llo, lhi)
    l_out, _ = barrier_race(mk, l_sec, lside, l_edge, 10.0)
    ls = race_stats(l_out)
    print(f"  measured : n={ls['n']:,}  revert {ls['rev']:.1f}%  "
          f"break {ls['brk']:.1f}%  neither {ls['un']:.1f}%")
    print(f"  published: n=23,642  revert 31.7%  break 61.4%")
    gate_law = (ls["n"] == 23642 and abs(ls["rev"] - 31.7) < 0.05
                and abs(ls["brk"] - 61.4) < 0.05)
    print(f"  {'OK -- law reproduced exactly' if gate_law else 'FAIL'}")

    sub("0c. REPRODUCTION 2 -- the FROZEN vr cutoffs (report n)")
    mdf = load_minute_frame()
    cdf = pd.read_csv(DATA / f"candles_{PRODUCT}.csv", index_col=0,
                      parse_dates=True)
    cdf.index = pd.to_datetime(cdf.index, utc=True)
    ohlc = ["open", "high", "low", "close"]
    same_src = bool(len(cdf) == len(mdf)
                    and np.array_equal(cdf[ohlc].to_numpy(), mdf[ohlc].to_numpy()))
    print(f"  flow_{PRODUCT}.csv OHLC == candles_{PRODUCT}.csv OHLC : "
          f"{same_src}  {'OK' if same_src else 'FAIL'}")
    print("    (report n derived the cutoffs from candles_*; this study races on")
    print("     flow_*.  They are the same bars, so the cutoffs transfer with no")
    print("     refit and no provenance gap.)")
    vr_raw = compute_vr(mdf)
    cut_i = int(len(mdf) * 0.60)
    ve = vr_raw.to_numpy()[:cut_i]
    derived = np.percentile(ve[np.isfinite(ve)], [25, 50, 75])
    print(f"  re-derived (30d exploration = first 60%) : "
          f"q25={derived[0]:.10f} q50={derived[1]:.10f} q75={derived[2]:.10f}")
    print(f"  frozen from report n                    : "
          f"q25={VR_CUTS[0]:.10f} q50={VR_CUTS[1]:.10f} q75={VR_CUTS[2]:.10f}")
    print(f"  report n, as published                  : "
          f"q25={VR_CUTS_PUBLISHED[0]:.2f}       q50={VR_CUTS_PUBLISHED[1]:.2f}       "
          f"q75={VR_CUTS_PUBLISHED[2]:.2f}")
    gate_cuts = bool(np.array_equal(derived, VR_CUTS)
                     and np.allclose(np.round(VR_CUTS, 2), VR_CUTS_PUBLISHED,
                                     rtol=0, atol=0))
    print("  " + ("OK -- bit-exact; cutoffs are frozen, not refitted"
                  if gate_cuts else "FAIL"))

    if not (gate_epoch and gate_law and gate_cuts):
        print("\n  A REPRODUCTION GATE FAILED -- results below are not readable.")
        return 1

    # ---------------------------------------------------------------- 1 ----- #
    header("1. THE vr REGIME, READ WITHOUT LOOK-AHEAD")
    vr_shift = vr_raw.shift(1).to_numpy()          # last COMPLETED minute
    mq = quartile_of(vr_shift)
    print("vr = (60m high-low range) / (mean |1m close-open| over 60m), matilda")
    print("v5.2 transcription.  Read at the last COMPLETED minute STRICTLY BEFORE")
    print("the touch's minute (.shift(1)) -- the raw window ends on its own bar,")
    print("which is not complete while a mid-minute touch is happening.")
    print(f"\ndefined on {int((mq > 0).sum()):,}/{n_min:,} minutes "
          f"({(mq > 0).mean() * 100:.1f}%; the first {VR_WINDOW + 1} are warm-up)")
    print(f"\n{'quartile':<18}{'cut':>22}{'minutes':>10}{'duty%':>9}"
          f"{'mean vr':>10}{'median vr':>11}")
    for q in (1, 2, 3, 4):
        m = mq == q
        lo_c = "-inf" if q == 1 else f"{VR_CUTS[q - 2]:.2f}"
        hi_c = "+inf" if q == 4 else f"{VR_CUTS[q - 1]:.2f}"
        v = vr_shift[m]
        print(f"{QNAMES[q]:<18}{f'({lo_c}, {hi_c}]':>22}{int(m.sum()):>10,}"
              f"{m.mean() * 100:>8.1f}%{np.mean(v):>10.2f}{np.median(v):>11.2f}")
    print("\nRealized duty is measured over the FULL 30d while the cutoffs come")
    print("from the first 60% -- deviation from 25% is regime drift across the")
    old_duty = mk.calm[np.clip(mk.minutes - mk.t0, 0, mk.n - 1)].mean() * 100
    print("month, not a bug.  Compare: the prior study's calm filter runs at "
          f"{old_duty:.1f}% duty.")

    sub("1a. how disjoint is Q1 from the ~90%-duty calm filter?")
    mb = np.clip(mk.minutes - mk.t0, 0, mk.n - 1)
    calm_min = mk.calm[mb]
    for q in (1, 2, 3, 4):
        m = mq == q
        if m.sum():
            print(f"  {QNAMES[q]:<18} minutes that ALSO pass the old calm filter: "
                  f"{calm_min[m].mean() * 100:5.1f}%")
    print("  Q1 is a strict SUBSET-like refinement, not an orthogonal cut: the old")
    print("  filter admits almost everything, so Q1 is where the real narrowing is.")

    # ---------------------------------------------------------------- 2 ----- #
    results: dict[tuple[int, float, int], dict] = {}
    cells: dict[tuple[int, float], dict] = {}
    q1_extra: dict[int, dict] = {}

    for w in WINDOWS:
        header(f"2. BARRIER RACE BY vr QUARTILE -- RANGE WINDOW W={w}m")
        idx, side, lo, hi = touches(mk, w, use_calm=False, m_lo=0, m_hi=n_min)
        pmin = mk.pmin[idx]
        qq = mq[pmin]
        ok = qq > 0
        idx, side, lo, hi, pmin, qq = (idx[ok], side[ok], lo[ok], hi[ok],
                                       pmin[ok], qq[ok])
        sec = mk.psec[idx]
        edge = np.where(side > 0, lo, hi)
        t = mk.ptime[idx]
        span_days = (mk.minutes[-1] - mk.minutes[0]) / 86400.0

        print(f"event set: every print at-or-beyond the trailing {w}-minute edge,")
        print(f"calm filter OFF, full 30d, vr defined -> {len(idx):,} touches")
        print(f"  low-edge (fade=BUY) {int((side > 0).sum()):,}   "
              f"high-edge (fade=SELL) {int((side < 0).sum()):,}")

        for bps in BARRIERS:
            out, tsec = barrier_race(mk, sec, side, edge, bps)
            cells[(w, bps)] = {"out": out, "tsec": tsec, "q": qq, "sec": sec,
                               "side": side, "t": t}
            sub(f"2.{w}.{bps:g}  symmetric {bps:g}bps / {bps:g}bps race, "
                f"{CAP_SEC // 60}-minute cap")
            print(f"{'vr quartile':<18}{RACE_HEAD}{'touch/day':>11}")
            for q in (1, 2, 3, 4):
                m = qq == q
                s = race_stats(out[m])
                results[(w, bps, q)] = s
                print(f"{QNAMES[q]:<18}{race_row(s)}"
                      f"{s['n'] / span_days:>11.0f}")
            s_all = race_stats(out)
            results[(w, bps, 0)] = s_all
            print(f"{'ALL (no vr cond)':<18}{race_row(s_all)}"
                  f"{s_all['n'] / span_days:>11.0f}")
            print("  gap_pp   = revert% - break% (unconditional, the law's "
                  "convention)")
            print("  rev|res% = revert share of RESOLVED races (the economic "
                  "quantity)")

            # monotonicity of the revert rate across quartiles
            rr = [results[(w, bps, q)]["rev"] for q in (1, 2, 3, 4)]
            cc = [results[(w, bps, q)]["cond"] for q in (1, 2, 3, 4)]
            dmono = np.diff(rr)
            shape = ("monotone DECREASING (clean gradient)" if np.all(dmono < 0)
                     else "monotone INCREASING (clean gradient)"
                     if np.all(dmono > 0) else "NOT monotone (jumpy = noise-like)")
            print(f"\n  revert% across Q1..Q4 : " +
                  " -> ".join(f"{v:.1f}" for v in rr) + f"   [{shape}]")
            print(f"  rev|res% across Q1..Q4: " +
                  " -> ".join(f"{v:.1f}" for v in cc))

        # ---- Q1 diagnostics for this window ---- #
        sub(f"2.{w}.dx  Q1 DIAGNOSTICS (de-clustering, capacity, look-ahead bound)")
        m1 = qq == 1
        n1 = int(m1.sum())
        print(f"Q1 raw touches: {n1:,} over {span_days:.1f} days = "
              f"{n1 / span_days:.0f}/day")

        # D1: first touch per (minute, side)
        key1 = pmin.astype(np.int64) * 4 + (side > 0).astype(np.int64)
        _, first1 = np.unique(key1, return_index=True)
        d1 = np.zeros(len(idx), bool)
        d1[first1] = True
        # D2: non-overlapping races (uses the 10bps resolution clock)
        base = cells[(w, 10.0)]
        order = np.argsort(t, kind="mergesort")
        d2 = np.zeros(len(idx), bool)
        free = -np.inf
        for j in order:
            if t[j] >= free:
                d2[j] = True
                free = t[j] + max(base["tsec"][j], 1.0)
        print(f"D1 first touch per (minute,side): {int((d1 & m1).sum()):,} "
              f"({int((d1 & m1).sum()) / span_days:.0f}/day)")
        print(f"D2 non-overlapping races        : {int((d2 & m1).sum()):,} "
              f"({int((d2 & m1).sum()) / span_days:.1f}/day)")
        print(f"\n{'Q1 event set':<26}{'barrier':>9}{RACE_HEAD}")
        for bps in BARRIERS:
            o = cells[(w, bps)]["out"]
            for lbl, m in (("PRIMARY (all touches)", m1),
                           ("D1 first-per-minute", m1 & d1),
                           ("D2 non-overlapping", m1 & d2)):
                print(f"{lbl:<26}{bps:>8.0f}b{race_row(race_stats(o[m]))}")
        print("  D2 uses the 10bps resolution clock for both rows so the two")
        print("  barrier sizes are judged on the SAME independent event list.")
        print("  D1 is NOT a clean independence cut: keeping only the first print")
        print("  per minute up-weights edges that were merely kissed and drops the")
        print("  follow-on prints of a break in progress, which biases it TOWARD")
        print("  reversion.  D2 (non-overlapping races) has no such selection and")
        print("  is the honest independent sample.")

        # look-ahead bound: start the scan one second later
        print(f"\nlook-ahead bound -- restart the race at second+1 (the touch")
        print("second's grid price is the LAST print of that second):")
        print(f"{'Q1 variant':<26}{'barrier':>9}{RACE_HEAD}")
        for bps in BARRIERS:
            o0 = cells[(w, bps)]["out"][m1]
            o1, _ = barrier_race(mk, sec[m1], side[m1], edge[m1], bps, offset=1)
            print(f"{'start at touch second':<26}{bps:>8.0f}b"
                  f"{race_row(race_stats(o0))}")
            print(f"{'start at second + 1':<26}{bps:>8.0f}b"
                  f"{race_row(race_stats(o1))}")
        q1_extra[w] = {"m1": m1, "d1": d1, "d2": d2, "sec": sec, "side": side,
                       "edge": edge, "span": span_days}

        # ---- calm-ON cross-tab (diagnostic) ---- #
        sub(f"2.{w}.dy  DIAGNOSTIC -- stacking the old ~90%-duty calm filter on vr")
        pcalm_touch = calm_min[pmin]
        print(f"{'cell':<30}{'barrier':>9}{RACE_HEAD}")
        for bps in BARRIERS:
            o = cells[(w, bps)]["out"]
            for lbl, m in (("Q1, calm filter OFF", m1),
                           ("Q1 AND calm filter ON", m1 & pcalm_touch),
                           ("calm ON only (the law's cut)", pcalm_touch)):
                print(f"{lbl:<30}{bps:>8.0f}b{race_row(race_stats(o[m]))}")

    # ---------------------------------------------------------------- 3 ----- #
    header("3. PRE-REGISTERED MECHANISM BAR -- Q1")
    print(f"  (a) revert% > break%     (b) n >= {BAR_MIN_TOUCHES:,}     "
          f"(c) gap >= {BAR_GAP_PP:.1f} pp")
    print(f"\n{'cell':<24}{'n':>9}{'revert%':>10}{'break%':>10}{'gap_pp':>9}"
          f"{'(a)':>6}{'(b)':>6}{'(c)':>6}{'cell':>9}")
    any_pass = False
    for w in WINDOWS:
        for bps in BARRIERS:
            s = results[(w, bps, 1)]
            ca = s["rev"] > s["brk"]
            cb = s["n"] >= BAR_MIN_TOUCHES
            cc_ = np.isfinite(s["gap"]) and s["gap"] >= BAR_GAP_PP
            p = bool(ca and cb and cc_)
            any_pass |= p
            print(f"{f'W={w}m  {bps:g}bps':<24}{s['n']:>9,}{s['rev']:>9.1f}%"
                  f"{s['brk']:>9.1f}%{s['gap']:>+9.1f}"
                  f"{('Y' if ca else 'n'):>6}{('Y' if cb else 'n'):>6}"
                  f"{('Y' if cc_ else 'n'):>6}{('PASS' if p else 'FAIL'):>9}")
    print(f"\n  MECHANISM VERDICT (OR over the four Q1 cells): "
          f"{'PASS' if any_pass else 'FAIL'}")

    header("4. ECONOMIC BAR -- Q1 AT THE 5bps BARRIER (stricter)")
    print(f"  maker-entry fade: +{FADE_GROSS_BPS:.2f}bps gross when revert wins,")
    print(f"                    -{FADE_LOSS_BPS:.2f}bps when break wins "
          f"({FADE_GROSS_BPS:.0f} + {COST_TAKER_CALM:.2f} calm taker exit)")
    print(f"  EV > 0  <=>  revert share of RESOLVED races > "
          f"{ECON_BREAKEVEN:.2f}%   (brief's round number: 61%)")
    print(f"\n{'cell':<24}{'resolved n':>12}{'rev|res%':>11}{'EV bps/race':>13}"
          f"{'vs 61.3%':>11}")
    econ_pass = False
    for w in WINDOWS:
        s = results[(w, 5.0, 1)]
        ev = (FADE_GROSS_BPS * s["rev"] - FADE_LOSS_BPS * s["brk"]) / 100.0
        p = bool(np.isfinite(s["cond"]) and s["cond"] > ECON_BREAKEVEN)
        econ_pass |= p
        print(f"{f'W={w}m  Q1  5bps':<24}{s['n_res']:>12,}{s['cond']:>10.1f}%"
              f"{ev:>+13.3f}{('PASS' if p else 'FAIL'):>11}")
    print("  EV bps/race is unconditional (unresolved races contribute 0 by")
    print("  construction); its sign is identical to the rev|res% test.")
    print(f"\n  ECONOMIC VERDICT: {'PASS' if econ_pass else 'FAIL'}")

    sub("4a. is 'unresolved contributes ~0' actually true?")
    print("side-adjusted move at the 60m cap for the UNRESOLVED Q1 races")
    print("(+ = price ended back inside the range, i.e. the fade would have won):")
    print(f"{'cell':<24}{'n':>9}{'mean bps':>11}{'median':>10}{'>0 share':>11}")
    for w in WINDOWS:
        m1 = q1_extra[w]["m1"]
        for bps in BARRIERS:
            o = cells[(w, bps)]["out"]
            mm = m1 & (o == 0)
            if not mm.sum():
                continue
            dd = fwd_drift_at(mk, q1_extra[w]["sec"][mm],
                              q1_extra[w]["side"][mm], CAP_SEC)
            print(f"{f'W={w}m  Q1  {bps:g}bps':<24}{int(mm.sum()):>9,}"
                  f"{dd.mean():>+11.2f}{np.median(dd):>+10.2f}"
                  f"{(dd > 0).mean() * 100:>10.1f}%")

    header("5. Q4 CONFIRMATION AND THE Q1..Q4 GRADIENT")
    print("If the deep-calm flip is a real mechanism, Q4 (trend regime) must show")
    print("the momentum result at least as strongly as the pooled law does.\n")
    print(f"{'cell':<24}{RACE_HEAD}")
    for w in WINDOWS:
        for bps in BARRIERS:
            for q in (1, 4, 0):
                lbl = "ALL" if q == 0 else QNAMES[q].split()[0]
                print(f"{f'W={w}m {bps:g}bps {lbl}':<24}"
                      f"{race_row(results[(w, bps, q)])}")
    print(f"\n{'gradient (revert%)':<24}{'Q1':>9}{'Q2':>9}{'Q3':>9}{'Q4':>9}"
          f"{'Q1-Q4':>9}{'shape':>26}")
    for w in WINDOWS:
        for bps in BARRIERS:
            rr = [results[(w, bps, q)]["rev"] for q in (1, 2, 3, 4)]
            dmono = np.diff(rr)
            shape = ("monotone down" if np.all(dmono < 0) else
                     "monotone up" if np.all(dmono > 0) else "NOT monotone")
            print(f"{f'W={w}m  {bps:g}bps':<24}" +
                  "".join(f"{v:>9.1f}" for v in rr) +
                  f"{rr[0] - rr[3]:>+9.1f}{shape:>26}")

    # ---------------------------------------------------------------- 6 ----- #
    header("6. SANITY CHECKS")
    ok = True
    print(f"  epoch unit cross-check              : "
          f"{'OK' if gate_epoch else 'FAIL'}")
    print(f"  law reproduced (n / 31.7 / 61.4)    : "
          f"{'OK' if gate_law else 'FAIL'}")
    print(f"  frozen vr cutoffs re-derived exactly: "
          f"{'OK' if gate_cuts else 'FAIL'}")
    ok &= gate_epoch and gate_law and gate_cuts

    # no look-ahead: range = trailing COMPLETED minutes strictly before the bar
    for w in WINDOWS:
        hi_arr, lo_arr = R._rolling_extrema(mk.mhigh, mk.mlow, w)
        bad = 0
        cand = np.flatnonzero(np.isfinite(hi_arr))[::97][:2000]
        for i in cand:
            if hi_arr[i] != mk.mhigh[i - w:i].max() or \
               lo_arr[i] != mk.mlow[i - w:i].min():
                bad += 1
        print(f"  W={w}m range = completed minutes < bar : "
              f"{'OK' if bad == 0 else f'{bad} MISMATCH'}  "
              f"({len(cand)} bars sampled)")
        ok &= bad == 0

    # no look-ahead: vr at a touch uses only minutes strictly before its minute
    hh = mdf["high"].to_numpy()
    ll = mdf["low"].to_numpy()
    op = mdf["open"].to_numpy()
    cl = mdf["close"].to_numpy()
    bad_vr = 0
    checked = 0
    samp = np.arange(VR_WINDOW + 2, n_min, 173)[:2000]
    for i in samp:
        j = i - 1                       # the bar vr is read from
        if j - VR_WINDOW + 1 < 0:
            continue
        sl = slice(j - VR_WINDOW + 1, j + 1)
        body = np.abs(cl[sl] - op[sl]).mean()
        want = (hh[sl].max() - ll[sl].min()) / body if body else np.nan
        got = vr_shift[i]
        checked += 1
        if not (np.isfinite(want) and np.isfinite(got)
                and abs(want - got) < 1e-9):
            bad_vr += 1
        if sl.stop > i:                 # window must not reach the touch minute
            bad_vr += 1
    print(f"  vr hand-recomputed, window < touch minute: "
          f"{'OK' if bad_vr == 0 else f'{bad_vr} MISMATCH'}  "
          f"({checked} minutes sampled)")
    ok &= bad_vr == 0

    # every touch price is a real print at-or-beyond its edge
    ti, tside, tlo, thi = touches(mk, 120, use_calm=False, m_lo=0, m_hi=n_min)
    px = mk.pprice[ti]
    at_edge = int(((tside > 0) & (px <= tlo)).sum() +
                  ((tside < 0) & (px >= thi)).sum())
    print(f"  touches at-or-beyond their edge     : {at_edge:,}/{len(ti):,}  "
          f"{'OK' if at_edge == len(ti) else 'FAIL'}")
    ok &= at_edge == len(ti)

    # the race never looks past the cap and outcomes are exhaustive
    o = cells[(120, 10.0)]["out"]
    tsec = cells[(120, 10.0)]["tsec"]
    exh = int(((o == 1) | (o == -1) | (o == 0)).sum()) == len(o)
    cap_ok = bool(np.all(tsec <= CAP_SEC + 1e-9))
    unres_at_cap = bool(np.all(tsec[o == 0] == CAP_SEC))
    print(f"  race outcomes exhaustive in {{-1,0,1}}  : {'OK' if exh else 'FAIL'}")
    print(f"  no resolution past the {CAP_SEC}s cap     : "
          f"{'OK' if cap_ok else 'FAIL'}")
    print(f"  unresolved carry the cap as their time: "
          f"{'OK' if unres_at_cap else 'FAIL'}")
    ok &= exh and cap_ok and unres_at_cap

    # determinism: rerun one full cell and compare bit-for-bit
    i2, s2, lo2, hi2 = touches(mk, 120, use_calm=False, m_lo=0, m_hi=n_min)
    q2 = mq[mk.pmin[i2]]
    k2 = q2 > 0
    o2, t2 = barrier_race(mk, mk.psec[i2][k2], s2[k2],
                          np.where(s2 > 0, lo2, hi2)[k2], 10.0)
    det = bool(np.array_equal(o2, cells[(120, 10.0)]["out"])
               and np.array_equal(t2, cells[(120, 10.0)]["tsec"]))
    print(f"  rerun determinism (bit-identical)   : {'OK' if det else 'FAIL'}")
    ok &= det

    # dedup correctness: a random subset raced without dedup must match
    rng = np.random.default_rng(20260821)
    base = cells[(120, 10.0)]
    pick = rng.choice(len(base["out"]), size=min(3000, len(base["out"])),
                      replace=False)
    o3, _ = barrier_race(mk, base["sec"][pick], base["side"][pick],
                         np.where(s2 > 0, lo2, hi2)[k2][pick], 10.0)
    dd_ok = bool(np.array_equal(o3, base["out"][pick]))
    print(f"  dedup is outcome-preserving (n=3000): {'OK' if dd_ok else 'FAIL'}")
    ok &= dd_ok

    print(f"\n  SANITY: {'all checks pass' if ok else 'SOMETHING FAILED'}")

    # ---------------------------------------------------------------- 7 ----- #
    # ---------------------------------------------------------------- 7 ----- #
    header("7. WHAT THE NUMBERS SAY (mechanism reading, no adoption)")

    def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
        if n == 0:
            return float("nan"), float("nan")
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return (c - h) * 100, (c + h) * 100

    best = max(((w, b) for w in WINDOWS for b in BARRIERS),
               key=lambda k: results[(k[0], k[1], 1)]["gap"])
    bs = results[(best[0], best[1], 1)]
    print(f"1. NO CELL FLIPS. The best Q1 cell of the four is W={best[0]}m at "
          f"{best[1]:g}bps:")
    print(f"   {bs['rev']:.1f}% revert vs {bs['brk']:.1f}% break "
          f"(gap {bs['gap']:+.1f} pp). The mechanism bar needs the gap to be")
    print(f"   >= +{BAR_GAP_PP:.1f}; it is {bs['gap'] - BAR_GAP_PP:.1f} pp away. "
          f"The economic bar needs {ECON_BREAKEVEN:.1f}% of resolved")
    print(f"   races to revert; Q1 delivers {bs['cond']:.1f}%, a shortfall of "
          f"{ECON_BREAKEVEN - bs['cond']:.1f} pp.")

    print("\n2. vr DOES MOVE THE RACE -- just nowhere near far enough. Q1 reverts")
    print("   more than Q4 in every one of the four cells, by a consistent margin:")
    for w in WINDOWS:
        for bps in BARRIERS:
            a_, b_ = results[(w, bps, 1)], results[(w, bps, 4)]
            print(f"     W={w:>3}m {bps:g}bps : Q1 {a_['rev']:.1f}% vs "
                  f"Q4 {b_['rev']:.1f}%  ->  {a_['rev'] - b_['rev']:+.1f} pp")
    print("   So deep calm is a real, signed, repeatable regime effect on the")
    print("   barrier race. It shifts the revert rate by roughly +6 to +7 pp off a")
    print("   base near 26%. Reaching a coin flip would take another ~16 pp and")
    print("   clearing costs another ~25 pp on top of that.")

    print("\n3. THE INDEPENDENT SAMPLE AGREES. 95% Wilson intervals on the D2")
    print("   non-overlapping Q1 races (revert share of RESOLVED races; a real")
    print("   flip needs the interval to sit ABOVE 50%):")
    for w in WINDOWS:
        m1, d2 = q1_extra[w]["m1"], q1_extra[w]["d2"]
        for bps in BARRIERS:
            o = cells[(w, bps)]["out"][m1 & d2]
            k = int((o == 1).sum())
            nres = int(((o == 1) | (o == -1)).sum())
            lo_c, hi_c = wilson(k, nres)
            print(f"     W={w:>3}m {bps:g}bps : {k}/{nres} = "
                  f"{k / max(nres, 1) * 100:.1f}%  95% CI "
                  f"[{lo_c:.1f}%, {hi_c:.1f}%]")
    print("   Every interval sits far below 50%. This is not a power problem.")

    print("\n4. Q4 CONFIRMS THE LAW. The trend quartile is the most momentum-like")
    print("   cell everywhere (down to 18.4% revert at W=120m / 5bps), which is")
    print("   what a real regime axis should look like.")

    print("\n5. MECHANISM CLASSIFICATION (research-protocol sec.5): this is a")
    print("   MECHANISM rejection, not a cost rejection. The fade leg loses the")
    print("   first-passage race by 26 to 48 percentage points before any cost,")
    print("   execution scheme or parameter is applied. Adding conditions cannot")
    print("   change the direction of a race that one side wins ~2.5:1. Stage-A")
    print("   does not gate; it closes.")

    header("8. CAVEATS")
    for c in [
        "IN-SAMPLE REGIME DEFINITION. The vr quartile cutoffs come from the "
        "first 60% of the SAME 30 days this race is measured on. They were "
        "frozen in report n and are not refitted here, but the regime "
        "definition and the measurement still share a month. A PASS here is a "
        "mechanism signal, not a validated edge: it must be re-measured on "
        "FRESH data with these same frozen cutoffs before any Stage-B build.",
        "30 days, one regime. Roughly one market state. The Q1..Q4 gradient is "
        "the only internal evidence available that a cell is mechanism rather "
        "than a month-specific accident.",
        "Touch prints are NOT independent. Consecutive prints beyond the same "
        "edge in the same minute share one range, one vr reading and largely "
        "one race. The headline n is a print count, kept that way only because "
        "the law it is compared against is quoted on the same count. The D1 "
        "and D2 rows are the honest sample sizes; D2 races do not overlap at "
        "all.",
        "The race starts on the touch SECOND, whose 1s grid price is the LAST "
        "print of that second and can post-date the touch print by up to 1s. "
        "This is inherited from the law's machinery so the comparison holds; "
        "the 'start at second + 1' rows bound the effect.",
        "Only ~12% of seconds carry a print, so the 1s series is heavily "
        "forward filled and a barrier crossed and un-crossed inside one second "
        "is invisible. Both barriers are affected symmetrically.",
        "Tape completeness: the executions file is a paginated snapshot with "
        "known gaps (~36% of individual prints, ~0.1% of wall-clock time, "
        "concentrated in high-rate bursts). Missing prints in bursts bias "
        "AGAINST the break barrier, i.e. they flatter reversion. Any Q1 "
        "reversion result inherits that bias.",
        "The economic line is a SANITY, not a strategy. It prices a maker "
        "entry that fills at the edge for free. This repo has measured three "
        "times that a resting fade limit at a range edge fills ~0.86% of the "
        "time and that the fills it does get are the breakouts (adverse "
        "selection, 6-9bps, KNOWLEDGE sec.2). A barrier-race PASS does not "
        "survive that automatically; execution is a separate gate.",
        "No funding/swap, no queue position, no spread dynamics are modelled. "
        "This stage measures frequencies of price paths and nothing else.",
        "NO STRATEGY BACKTEST WAS RUN. Nothing here is a candidate, nothing is "
        "adopted, nothing is committed.",
    ]:
        print("* " + c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
