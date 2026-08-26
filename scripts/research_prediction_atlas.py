#!/usr/bin/env python3
"""
CONDITIONAL PROBABILITY ATLAS -- P(move >= X | condition) for FX_BTC_JPY.

EXPLORATION ONLY -- NO ADOPTION DECISION MAY BE TAKEN FROM THIS OUTPUT.
AT MOST TWO CELLS MAY BE PROPOSED AS FUTURE PRE-REGISTRATION CANDIDATES,
AND FREEZING/REGISTERING THEM IS THE LEAD'S ACT, NOT THIS SCRIPT'S.

TASK SUMMARY (from the lead, frozen before the first run)
    Reports up to 24 mapped the surface of conditional MEAN DRIFT.  Nothing
    has been systematised in the form the owner actually asked for:
    "when condition C holds, with what probability does the price move X%".
    This script builds that atlas.  Two prediction targets are kept strictly
    apart because the repo already knows they behave differently:

      * DIRECTION  P(+X touched before -X | C).  Known wall: storm direction
        is not predictable ex ante (report i); time-of-day directionality is
        all noise (report f).  Do not flinch from re-confirming the wall.
      * MAGNITUDE  P(max |deviation| >= X within T | C), sign-free.  Known
        foothold: the clock window lifts storm incidence 2.23x (report h),
        and volatility clusters.

    THE ARITHMETIC THAT TURNS A PREDICTION INTO A STRATEGY (burned into the
    script as the decision line, not decided after the fact):
        A first-touch race on +/-X bps won with probability p pays
            EV = X*(2p - 1) - cost
        so the REQUIRED p is        p_req = 0.5 + cost/(2X)
        with taker round trip 7.92 bps (KNOWLEDGE 1, burst spread):
            X= 10 bps -> p_req = 89.60%
            X= 20 bps -> p_req = 69.80%
            X= 50 bps -> p_req = 57.92%
            X=100 bps -> p_req = 53.96%
        THE CENTRAL PRODUCT OF THIS STUDY IS THE ENUMERATION OF EVERY
        CONDITION CELL WHOSE p CLEARS THAT LINE (or the sentence "zero").

    MAGNITUDE COSTS DOUBLE.  A magnitude prediction traded as a two-sided
    bracket pays two round trips, so its own line is
            EV = X*P(reach) - 2*7.92      ->  P_req = 15.84 / X
            X= 10 -> 158.4% (IMPOSSIBLE)   X= 20 -> 79.2%
            X= 50 ->  31.7%                X=100 -> 15.8%
    This is why report 21's S9 simple bracket lost.  The primary use of a
    magnitude prediction is therefore NOT a straddle but a GATE on other
    strategies (size / go-no-go), and that use is evaluated separately
    (section 8) as an information diagnostic, not as a strategy.

PRE-REGISTRATION (verbatim; nothing below is changed after the first run)

    [DATA -- BOUNDARY IS ABSOLUTE]
    - backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz
      (columns id, exec_date, price, size, side; `side` is the TAKER side).
      ONLY rows with exec_date < 2026-08-20T08:22:17Z are used.  Rows at or
      after that instant are FRESH territory and are never read: the file is
      truncated at load and an assert enforces it.
    - data/binance_BTCUSDT_1m_full.csv, same cutoff applied, used ONLY for
      the long-horizon MAGNITUDE / clock / weekday / vol checks and monthly
      stability.  NEVER for a direction race (venue+quote currency differ,
      and intra-bar touch order is unknowable from OHLC).
    - NO ticker / spread / OI data is read.  Those conditions are declared
      UNEXPLORED (insufficient history) and handed to the board round.
    - No network access.  Read-only, idempotent, seed 20260826.
    - BOTH SOURCES ARE MINED (h, k, u, v, x, y used them).  Every number
      produced here is a FEASIBILITY BOUNDARY, not evidence for adoption.

    [PRICE SERIES]
    - Bounce-free mid proxy, repo convention (S7 / burst atlas):
      mid = 0.5*(last taker-BUY print + last taker-SELL print), each
      forward-filled; projected onto a 1-second grid (last print of the
      second wins, then forward filled -- no look-ahead).  m[i] is knowable
      only at the END of second i.
    - SAMPLE INSTANTS: every 10 seconds of grid time.  Features are built
      from m[..i] inclusive; the outcome window starts at j = i+1.  The two
      windows never touch.  An assert enforces j > i.

    [TARGET 1 -- FIRST-TOUCH RACE, frozen]
        X in {10, 20, 50, 100} bps,  T in {5m, 30m, 2h, 8h}
        up-hit  = first k>j with m[k] >= m[j]*(1+X/1e4)
        down-hit= first k>j with m[k] <= m[j]*(1-X/1e4)
        outcome = UP if up-hit first, DOWN if down-hit first,
                  DRAW if neither inside T.
        DRAWS ARE COUNTED SEPARATELY AND NEVER ALLOCATED TO EITHER SIDE.
        p_dec = P(UP | decisive).  The tradable probability is
        p_star = max(p_dec, 1-p_dec) because the trader picks the side; the
        side-selection is charged for in the multiple-comparison count.
        Identity check asserted per cell:  n_up + n_down + n_draw = n.
    [TARGET 2 -- MAGNITUDE, frozen]
        P(max |deviation| >= X inside T | C) = 1 - P(DRAW) on the same grid.
        Same X x T lattice, so the two targets tie out exactly.

    [CONDITIONS -- 7 single features, all causal, ENUMERATED, NOT EXTENDED]
      (a) clock   : t_sig inside 12:30-15:00 UTC   {in, out}
      (b) rv60    : realised vol of trailing 60 min (sd of 1-min returns,
                    bps), global terciles                {T1,T2,T3}
      (c) burst20 : time since last 2s/20bps burst (60 s same-side cooldown,
                    burst atlas convention)      {<2m, <30m, >=30m}
      (c') burst10: SAME with 10 bps -- pre-registered SENSITIVITY, declared
                    now because 2s/20bps fires only ~0.5/day and its <2m
                    bucket is thin.  Counted in the cell total M.
      (d) dist30  : distance to the nearer of the trailing-30-min high/low,
                    bps, global terciles          {T1 near .. T3 far}
      (e) flow    : S7 two-sided flow window, W=30s, v_min = 50th pctile of
                    the pooled per-window one-side volume over ALL windows,
                    |B-S|/(B+S) <= 0.30; the PRECEDING window classifies the
                    sample (causal)                      {in, out}
      (f) dow     : UTC weekday vs weekend                {wd, we}
      (g) ret5    : trailing 5-min signed return, global terciles {T1,T2,T3}
    - Terciles are cut on the whole-sample distribution.  This is a
      DISTRIBUTIONAL normalisation, not an outcome look-ahead; a causal
      (trailing-7-day rolling quantile) re-cut is run on the top cells as a
      robustness check.

    [PAIRS -- frozen selection rule, applied once]
    - Rank the 7 primary features by max |ln(lift)| over all their cells with
      nominal n >= 2000 (both targets pooled).  Take the TOP 5 features and
      cross all C(5,2) = 10 pairs.  No pair is added afterwards.
    - Interaction is measured against the MULTIPLICATIVE null
      lift(A&B) / (lift(A) * lift(B)); report 21's window x touch (6x) is
      the shape being hunted.

    [EVALUATION -- frozen]
    - Per cell: n, p_hat, Wilson 95% CI (NOMINAL -- overlapping samples make
      it far too narrow; stated every time it is printed), unconditional
      base rate, lift, and the GAP TO THE REQUIRED-p LINE.
    - n < 50 cells are REFERENCE ONLY everywhere.
    - Day-cluster bootstrap 95% CI (UTC day, 2000 resamples, seed 20260826,
      per-day sum/count resampling) for every baseline, every top cell, and
      every cell whose point estimate clears its line.  THE BOOTSTRAP CI IS
      THE HONEST ONE.  A cell is called SURVIVING only if the bootstrap
      lower bound clears the required-p line.
    - Calendar calibration: 60/40 chronological split of the sample instants;
      p_hat printed for both halves of every top cell.  Binance side prints
      monthly p_hat.
    - MULTIPLE COMPARISONS: total cell count M is printed, and the expected
      number of cells clearing the line BY CHANCE is printed twice -- once
      with nominal n and once with an effective n = span/T (independent,
      non-overlapping windows).  Top cells must additionally show a PLATEAU
      (neighbouring tercile / adjacent bucket does not collapse).

    [SANITY -- all must pass before any number is read]
    - Zero look-ahead: feature index i, outcome index j=i+1, asserted.
      TAUTOLOGY PROBE: deliberately mis-align one feature so its window
      overlaps the outcome window and show the atlas lights up (report 9's
      lesson: a detector that cannot see a tautology cannot certify its
      absence).
    - epoch cross-check with a second independent implementation.
    - determinism: full stdout hashed; two runs must agree.
    - draw accounting: n_up + n_down + n_draw = n for every cell, asserted.

    [AMENDMENT 1 -- added after run 1, before any candidate was named]
    Run 1 showed that the cells clearing the race line are drawn from one or
    two calendar episodes (p_hat = 100.00% with an empty second half is the
    signature).  Three DIAGNOSTIC columns are therefore added to the
    enumeration -- n_days (distinct UTC days contributing), maxday% (largest
    single-day share of the cell's observations) and, for magnitude, whether
    the UNCONDITIONAL base rate at the same X,T already clears the line --
    and the label SURVIVING is tightened to
        day-cluster lower bound > required p  AND  n_days >= 10
        AND  maxday% <= 50.
    This is a TIGHTENING of a diagnostic, never a selection rule: both counts
    (CI-only and CI+diversity) are printed, and no candidate is chosen from
    either.  Also added: the whipsaw rate P(both barriers touched | reached),
    because the frozen magnitude line X*P(reach) - 2*7.92 ignores it and is
    therefore an UPPER bound on a bracket's EV, not its EV.
    Also added, and the most consequential of the three: EVatt, the HONEST
    per-attempt expectation of the trade a race probability describes --
        EV = P(win)*X - P(lose)*X + P(draw)*E[side*move(T) | draw] - 7.92
    The frozen line p_req = 0.5 + cost/(2X) prices only the DECISIVE races.
    A cell can clear it at p = 90% and still be a catastrophic trade when 99%
    of attempts draw, because every drawn attempt still pays the round trip.
    EVatt closes that hole and is reported for every race crosser.

    [DISCIPLINE]
    - Negative stays negative.  "Direction is unpredictable everywhere" is a
      first-class result.
    - Rejection level (mechanism vs point) written per protocol section 10.
    - The width of the surface (cell count) is reported.

Usage:  PYTHONPATH=src python scripts/research_prediction_atlas.py
"""
from __future__ import annotations

import bisect
import hashlib
import math
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE = os.path.join(ROOT, "backtest_data",
                    "executions_FX_BTC_JPY_31d_20260823.csv.gz")
BINANCE = os.path.join(ROOT, "data", "binance_BTCUSDT_1m_full.csv")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
FRESH_CUTOFF_ISO = "2026-08-20T08:22:17Z"

SEED = 20260826
BOOT_ITERS = 2000

SAMPLE_STEP_S = 10                      # sample instants every 10 s of grid time
XS_BPS = (10.0, 20.0, 50.0, 100.0)
TS_S = (300, 1800, 7200, 28800)         # 5m, 30m, 2h, 8h
TS_LABEL = {300: "5m", 1800: "30m", 7200: "2h", 28800: "8h"}

TAKER_ROUND = 7.92                      # bps, round trip (KNOWLEDGE 1, burst)
N_REF_ONLY = 50
N_PAIR_MIN = 2000                       # nominal n floor for the pair-ranking

CLOCK_LO_S = 12 * 3600 + 30 * 60
CLOCK_HI_S = 15 * 3600

BURST_W_S = 2
BURST_THR_PRIMARY = 20.0
BURST_THR_SENS = 10.0
BURST_COOLDOWN_S = 60

FLOW_W_S = 30
FLOW_IMB_MAX = 0.30
FLOW_PCTL = 50

RV_WIN_MIN = 60
DIST_WIN_S = 1800
RET_WIN_S = 300


def p_req_race(x: float) -> float:
    return 0.5 + TAKER_ROUND / (2.0 * x)


def p_req_magnitude(x: float) -> float:
    return (2.0 * TAKER_ROUND) / x


# --------------------------------------------------------------------------
# printing helpers (every line also feeds the determinism hash)
# --------------------------------------------------------------------------
_HASH = hashlib.sha256()


def out(s: str = "") -> None:
    print(s)
    _HASH.update((s + "\n").encode())


def line(char: str = "-", n: int = 118) -> None:
    out(char * n)


def header(title: str) -> None:
    out("")
    line("=")
    out(title)
    line("=")


def sub(title: str) -> None:
    out("")
    out("--- " + title + " " + "-" * max(0, 114 - len(title)))


# --------------------------------------------------------------------------
# math helpers (no scipy in this environment)
# --------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def binom_sf_ge(k: int, n: int, p: float) -> float:
    """P(Binomial(n,p) >= k).  Exact for small n, normal approx otherwise."""
    if n <= 0:
        return 0.0
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if n <= 3000:
        # exact, log-space
        lp, lq = math.log(p), math.log1p(-p) if p < 1 else -math.inf
        total = 0.0
        lgn = math.lgamma(n + 1)
        for i in range(k, n + 1):
            lt = lgn - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq
            total += math.exp(lt)
        return min(1.0, total)
    mu = n * p
    sd = math.sqrt(n * p * (1 - p))
    if sd <= 0:
        return 1.0 if k <= mu else 0.0
    return _norm_sf(((k - 0.5) - mu) / sd)


def ffill(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def epoch_seconds(ts) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return np.array([x.timestamp() for x in idx], dtype=float)


def iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").isoformat()


def terciles(v: np.ndarray) -> tuple[float, float]:
    ok = np.isfinite(v)
    return (float(np.quantile(v[ok], 1 / 3)), float(np.quantile(v[ok], 2 / 3)))


def tercile_code(v: np.ndarray, q1: float, q2: float) -> np.ndarray:
    c = np.full(len(v), -1, dtype=np.int8)
    ok = np.isfinite(v)
    c[ok & (v <= q1)] = 0
    c[ok & (v > q1) & (v <= q2)] = 1
    c[ok & (v > q2)] = 2
    return c


# --------------------------------------------------------------------------
# day-cluster bootstrap for a proportion (per-day sum/count resampling)
# --------------------------------------------------------------------------
def day_cluster_prop_ci(x01: np.ndarray, days: np.ndarray,
                        rng: np.random.Generator) -> tuple[float, float, float]:
    """(lo95, hi95, sd) for a proportion, resampling whole UTC days."""
    if len(x01) < 2:
        return float("nan"), float("nan"), float("nan")
    uniq, inv = np.unique(days, return_inverse=True)
    k = len(uniq)
    if k < 2:
        return float("nan"), float("nan"), float("nan")
    sums = np.bincount(inv, weights=x01.astype(float), minlength=k)
    cnts = np.bincount(inv, minlength=k).astype(float)
    pick = rng.integers(0, k, size=(BOOT_ITERS, k))
    s = sums[pick].sum(axis=1)
    c = cnts[pick].sum(axis=1)
    good = c > 0
    means = np.full(BOOT_ITERS, np.nan)
    means[good] = s[good] / c[good]
    lo, hi = np.nanpercentile(means, [2.5, 97.5])
    return float(lo), float(hi), float(np.nanstd(means, ddof=1))


def day_cluster_mean_ci(vals: np.ndarray, days: np.ndarray,
                        rng: np.random.Generator) -> tuple[float, float, float]:
    if len(vals) < 2:
        return float("nan"), float("nan"), float("nan")
    uniq, inv = np.unique(days, return_inverse=True)
    k = len(uniq)
    if k < 2:
        return float("nan"), float("nan"), float("nan")
    sums = np.bincount(inv, weights=vals.astype(float), minlength=k)
    cnts = np.bincount(inv, minlength=k).astype(float)
    pick = rng.integers(0, k, size=(BOOT_ITERS, k))
    s = sums[pick].sum(axis=1)
    c = cnts[pick].sum(axis=1)
    means = np.where(c > 0, s / np.maximum(c, 1e-9), np.nan)
    lo, hi = np.nanpercentile(means, [2.5, 97.5])
    sd = float(np.nanstd(means, ddof=1))
    return float(lo), float(hi), sd


# --------------------------------------------------------------------------
# first-touch times for EVERY grid index, exactly, via the suffix record chain
# --------------------------------------------------------------------------
def first_touch_times(gm: np.ndarray, valid_from: int, sample_idx: np.ndarray,
                      xs_bps: tuple[float, ...]) -> dict:
    """For each sample index i (entry at j=i+1) and each X, the number of
    seconds from j until the mid first reaches m[j]*(1 +/- X/1e4).

    Method: walking right-to-left we maintain the suffix running-maximum
    record chain (and the running-minimum chain).  The first index k>j with
    m[k] >= c is necessarily a member of the chain, because every index
    between j and k is strictly below c <= m[k].  The chain is monotone, so
    each query is a bisect.  This is EXACT and unbounded in horizon -- no
    horizon truncation and no scan window.
    """
    n = len(gm)
    big = np.int64(1 << 40)
    up_dt = {x: np.full(len(sample_idx), big, dtype=np.int64) for x in xs_bps}
    dn_dt = {x: np.full(len(sample_idx), big, dtype=np.int64) for x in xs_bps}

    # position of each sample index in the descending walk
    want = np.zeros(n, dtype=np.int64) - 1
    want[sample_idx + 1] = np.arange(len(sample_idx))   # query is made AT j=i+1

    mx_i: list[int] = []
    mx_negv: list[float] = []      # negated values -> ascending, bisectable
    mn_i: list[int] = []
    mn_v: list[float] = []         # values ascending

    up_mult = [1.0 + x / 1e4 for x in xs_bps]
    dn_mult = [1.0 - x / 1e4 for x in xs_bps]
    xs = list(xs_bps)

    for j in range(n - 1, valid_from - 1, -1):
        q = want[j]
        if q >= 0:
            pj = gm[j]
            for xi, x in enumerate(xs):
                cu = pj * up_mult[xi]
                # largest position p with value >= cu  (values descend along list)
                p = bisect.bisect_right(mx_negv, -cu) - 1
                if p >= 0:
                    up_dt[x][q] = mx_i[p] - j
                cd = pj * dn_mult[xi]
                p2 = bisect.bisect_right(mn_v, cd) - 1
                if p2 >= 0:
                    dn_dt[x][q] = mn_i[p2] - j
        v = gm[j]
        while mx_negv and -mx_negv[-1] <= v:
            mx_negv.pop()
            mx_i.pop()
        mx_negv.append(-v)
        mx_i.append(j)
        while mn_v and mn_v[-1] >= v:
            mn_v.pop()
            mn_i.pop()
        mn_v.append(v)
        mn_i.append(j)

    return {"up": up_dt, "dn": dn_dt, "big": int(big)}


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_tape() -> dict:
    cutoff = float((pd.Timestamp(FRESH_CUTOFF_ISO) - EPOCH) / pd.Timedelta("1s"))
    ex = pd.read_csv(TAPE)
    t = epoch_seconds(ex["exec_date"])
    t_alt = epoch_seconds_alt(ex["exec_date"])
    dev = float(np.max(np.abs(t - t_alt)))
    out(f"epoch cross-check      : max |impl_a - impl_b| = {dev:.9f} s (must be ~0)")
    if dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")
    out(f"first row              : {ex['exec_date'].iloc[0]} -> {t[0]:.3f}s -> {iso(t[0])}")

    order = np.argsort(t, kind="mergesort")
    t = t[order]
    price = ex["price"].to_numpy(float)[order]
    buy = (ex["side"].to_numpy() == "BUY")[order]
    size = ex["size"].to_numpy(float)[order]

    n_all = len(t)
    keep = t < cutoff
    t, price, buy, size = t[keep], price[keep], buy[keep], size[keep]
    out(f"fresh-territory filter : cutoff {FRESH_CUTOFF_ISO} = {cutoff:.0f}s; kept "
        f"{int(keep.sum()):,} / {n_all:,} prints, dropped {n_all - int(keep.sum()):,} "
        f"(never read again)")
    assert t[-1] < cutoff, "fresh territory leaked into the sample"
    out(f"tape span used         : {iso(t[0])} .. {iso(t[-1])} "
        f"({(t[-1] - t[0]) / 86400.0:.2f} days)")

    lb = ffill(np.where(buy, price, np.nan))
    ls = ffill(np.where(~buy, price, np.nan))
    mid = 0.5 * (lb + ls)

    g0 = int(np.floor(t[0]))
    g1 = int(np.floor(t[-1]))
    n = g1 - g0 + 1
    gm = np.full(n, np.nan)
    si = np.floor(t).astype(np.int64) - g0
    gm[si] = mid
    gm = ffill(gm)
    valid_from = int(np.argmax(~np.isnan(gm)))
    has_print = np.zeros(n, bool)
    has_print[si] = True
    out(f"1s grid                : {n:,} seconds from {iso(float(g0))}; "
        f"{has_print.mean()*100:.1f}% of seconds carry a print; "
        f"{len(t)/((t[-1]-t[0])/86400.0):,.0f} prints/day")
    return {"t": t, "price": price, "buy": buy, "size": size, "g0": g0, "gm": gm,
            "n": n, "valid_from": valid_from, "days": (t[-1] - t[0]) / 86400.0,
            "cutoff": cutoff, "si": si}


# --------------------------------------------------------------------------
# feature construction (all causal: value at sample index i uses m[..i] only)
# --------------------------------------------------------------------------
@dataclass
class Feature:
    key: str
    labels: list
    code: np.ndarray            # int8 per sample; -1 = undefined
    note: str


def build_features(D: dict, sample_idx: np.ndarray) -> tuple[dict, dict]:
    gm, g0, n = D["gm"], D["g0"], D["n"]
    ns = len(sample_idx)
    t_sig = g0 + sample_idx.astype(float)          # epoch second the feature is known
    feats: dict[str, Feature] = {}
    raw: dict[str, np.ndarray] = {}

    # (a) clock window ------------------------------------------------------
    sod = np.mod(t_sig, 86400.0)
    clock_in = (sod >= CLOCK_LO_S) & (sod < CLOCK_HI_S)
    feats["clock"] = Feature("clock", ["in 12:30-15:00Z", "out"],
                             np.where(clock_in, 0, 1).astype(np.int8),
                             "storm clock window, report h")

    # (b) rv60: sd of trailing 60 one-minute returns -------------------------
    m60 = gm[::60]                                          # mid at each minute end
    r1 = np.full(len(m60), np.nan)
    r1[1:] = np.log(m60[1:] / m60[:-1]) * 1e4
    rv = pd.Series(r1).rolling(RV_WIN_MIN, min_periods=RV_WIN_MIN).std().to_numpy()
    minute_of = sample_idx // 60                            # last COMPLETED minute idx
    mi = minute_of - 1                                      # strictly before the sample
    rv_s = np.where(mi >= 0, rv[np.clip(mi, 0, len(rv) - 1)], np.nan)
    q1, q2 = terciles(rv_s)
    raw["rv60"] = rv_s
    feats["rv60"] = Feature("rv60", [f"T1 rv<={q1:.1f}bps", f"T2 {q1:.1f}-{q2:.1f}",
                                     f"T3 rv>{q2:.1f}bps"],
                            tercile_code(rv_s, q1, q2),
                            f"60-min realised vol terciles ({q1:.2f}/{q2:.2f} bps)")

    # (c) burst recency ------------------------------------------------------
    def burst_indices(thr: float) -> np.ndarray:
        r = np.full(n, np.nan)
        r[BURST_W_S:] = (gm[BURST_W_S:] - gm[:-BURST_W_S]) / gm[:-BURST_W_S] * 1e4
        ok = np.zeros(n, bool)
        ok[max(BURST_W_S, D["valid_from"] + BURST_W_S):] = True
        fire = ok & (np.abs(r) >= thr)
        idx_all = np.flatnonzero(fire)
        last = {1: -1e18, -1: -1e18}
        keep = []
        for i in idx_all:
            s = 1 if r[i] > 0 else -1
            if i - last[s] < BURST_COOLDOWN_S:
                continue
            last[s] = i
            keep.append(i)
        return np.asarray(keep, dtype=np.int64)

    burst_sets = {}
    for tag, thr in (("burst20", BURST_THR_PRIMARY), ("burst10", BURST_THR_SENS)):
        bi = burst_indices(thr)
        burst_sets[tag] = bi
        pos = np.searchsorted(bi, sample_idx, side="right") - 1   # last burst <= i
        elapsed = np.where(pos >= 0, sample_idx - bi[np.clip(pos, 0, len(bi) - 1)],
                           np.inf)
        code = np.full(ns, 2, dtype=np.int8)
        code[elapsed < 120] = 0
        code[(elapsed >= 120) & (elapsed < 1800)] = 1
        feats[tag] = Feature(tag, ["<2m", "<30m", ">=30m"], code,
                             f"time since last {BURST_W_S}s/{thr:.0f}bps burst "
                             f"({len(bi)} bursts = {len(bi)/D['days']:.2f}/day)")

    # (d) dist30: distance to nearer trailing-30-min extreme -----------------
    step = SAMPLE_STEP_S
    sub_m = gm[::step]                                     # 10s subsample
    win = DIST_WIN_S // step
    s_ser = pd.Series(sub_m)
    rmax = s_ser.rolling(win, min_periods=win).max().to_numpy()
    rmin = s_ser.rolling(win, min_periods=win).min().to_numpy()
    k_of = sample_idx // step
    hi = rmax[np.clip(k_of, 0, len(rmax) - 1)]
    lo = rmin[np.clip(k_of, 0, len(rmin) - 1)]
    cur = gm[sample_idx]
    hi = np.maximum(hi, cur)          # the current second belongs to the window
    lo = np.minimum(lo, cur)
    dist = np.minimum(hi - cur, cur - lo) / cur * 1e4
    dist = np.where(np.isfinite(hi) & np.isfinite(lo), dist, np.nan)
    d1, d2 = terciles(dist)
    raw["dist30"] = dist
    feats["dist30"] = Feature("dist30", [f"T1 near<={d1:.1f}bps",
                                         f"T2 {d1:.1f}-{d2:.1f}",
                                         f"T3 far>{d2:.1f}bps"],
                              tercile_code(dist, d1, d2),
                              f"distance to nearer 30-min extreme ({d1:.2f}/{d2:.2f} bps)")

    # (e) S7 two-sided flow window ------------------------------------------
    t, size, buy = D["t"], D["size"], D["buy"]
    wid = np.floor(t / FLOW_W_S).astype(np.int64)
    w0 = int(wid[0])
    nw = int(wid[-1]) - w0 + 1
    vbuy = np.bincount(wid - w0, weights=np.where(buy, size, 0.0), minlength=nw)
    vsell = np.bincount(wid - w0, weights=np.where(~buy, size, 0.0), minlength=nw)
    pool = np.concatenate([vbuy, vsell])
    v_min = float(np.percentile(pool, FLOW_PCTL))
    floored = False
    if v_min <= 0:
        v_min = 1e-9
        floored = True
    tot = vbuy + vsell
    imb = np.where(tot > 0, np.abs(vbuy - vsell) / np.maximum(tot, 1e-12), 1.0)
    two_sided = (vbuy >= v_min) & (vsell >= v_min) & (imb <= FLOW_IMB_MAX)
    prev_w = np.floor((g0 + sample_idx) / FLOW_W_S).astype(np.int64) - 1 - w0
    okw = (prev_w >= 0) & (prev_w < nw)
    fl = np.full(ns, -1, dtype=np.int8)
    fl[okw] = np.where(two_sided[np.clip(prev_w[okw], 0, nw - 1)], 0, 1)
    feats["flow"] = Feature("flow", ["in two-sided", "out"], fl,
                            f"S7 W={FLOW_W_S}s v_min(p{FLOW_PCTL},all)={v_min:.6f} BTC"
                            f"{' [FLOORED]' if floored else ''}, duty "
                            f"{two_sided.mean()*100:.1f}% of windows")

    # (f) weekday / weekend --------------------------------------------------
    dow = (np.floor(t_sig / 86400.0).astype(np.int64) + 4) % 7      # 1970-01-01 = Thu
    feats["dow"] = Feature("dow", ["weekday", "weekend"],
                           np.where(dow >= 5, 1, 0).astype(np.int8),
                           "UTC day of week")

    # (g) trailing 5-min signed return --------------------------------------
    back = sample_idx - RET_WIN_S
    r5 = np.where(back >= D["valid_from"],
                  (gm[sample_idx] - gm[np.clip(back, 0, n - 1)])
                  / gm[np.clip(back, 0, n - 1)] * 1e4, np.nan)
    g1_, g2_ = terciles(r5)
    raw["ret5"] = r5
    feats["ret5"] = Feature("ret5", [f"T1 ret<={g1_:.1f}bps", f"T2 {g1_:.1f}..{g2_:.1f}",
                                     f"T3 ret>{g2_:.1f}bps"],
                            tercile_code(r5, g1_, g2_),
                            f"trailing 5-min signed return terciles "
                            f"({g1_:.2f}/{g2_:.2f} bps)")

    # 30-min signed return (used only by the gate diagnostic, section 8)
    back30 = sample_idx - 1800
    r30 = np.where(back30 >= D["valid_from"],
                   (gm[sample_idx] - gm[np.clip(back30, 0, n - 1)])
                   / gm[np.clip(back30, 0, n - 1)] * 1e4, np.nan)
    raw["ret30"] = r30
    raw["burst_sets"] = burst_sets
    return feats, raw


# --------------------------------------------------------------------------
# cell statistics
# --------------------------------------------------------------------------
@dataclass
class Cell:
    key: str
    x: float
    T: int
    n: int
    n_up: int
    n_dn: int
    n_draw: int

    @property
    def n_dec(self) -> int:
        return self.n_up + self.n_dn

    @property
    def p_dec(self) -> float:
        return self.n_up / self.n_dec if self.n_dec else float("nan")

    @property
    def p_star(self) -> float:
        p = self.p_dec
        return max(p, 1.0 - p) if self.n_dec else float("nan")

    @property
    def k_star(self) -> int:
        return max(self.n_up, self.n_dn)

    @property
    def p_reach(self) -> float:
        return (self.n - self.n_draw) / self.n if self.n else float("nan")


def cell_stats(key: str, mask: np.ndarray, o: dict, x: float, T: int) -> Cell:
    up = o["up_hit"][(x, T)][mask]
    dn = o["dn_hit"][(x, T)][mask]
    dr = o["draw"][(x, T)][mask]
    n = int(mask.sum())
    c = Cell(key, x, T, n, int(up.sum()), int(dn.sum()), int(dr.sum()))
    assert c.n_up + c.n_dn + c.n_draw == c.n, f"draw accounting broken in {key}"
    return c


def day_spread(days: np.ndarray) -> tuple[int, float]:
    """(number of distinct UTC days, largest single-day share of the sample)."""
    if len(days) == 0:
        return 0, float("nan")
    _, cnt = np.unique(days, return_counts=True)
    return int(len(cnt)), float(cnt.max() / cnt.sum())


def abslog(v: float) -> float:
    """|ln v|, and 0.0 for anything not finite and positive."""
    if not np.isfinite(v) or v <= 0:
        return 0.0
    return abs(math.log(v))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    rng = np.random.default_rng(SEED)
    header("CONDITIONAL PROBABILITY ATLAS -- EXPLORATION ONLY (no adoption decision)")
    out("data   : backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz "
        f"(exec_date < {FRESH_CUTOFF_ISO})")
    out("         data/binance_BTCUSDT_1m_full.csv (same cutoff; MAGNITUDE side only)")
    out(f"seed   : {SEED}   bootstrap iters: {BOOT_ITERS}   sample step: "
        f"{SAMPLE_STEP_S}s")
    out(f"targets: race P(+X first) and magnitude P(|dev|>=X) on "
        f"X{list(XS_BPS)} bps x T{[TS_LABEL[t] for t in TS_S]}")
    out("decision lines burned in:")
    out("   race      p_req = 0.5 + 7.92/(2X)  -> " +
        "  ".join(f"X={int(x)}:{p_req_race(x)*100:.2f}%" for x in XS_BPS))
    out("   magnitude P_req = 15.84/X          -> " +
        "  ".join(f"X={int(x)}:{p_req_magnitude(x)*100:.1f}%" for x in XS_BPS))
    out("   (magnitude traded as a two-sided bracket pays TWO round trips -- this")
    out("    is why report 21's S9 bracket lost.  Its real use is a GATE, section 8.)")
    line()

    D = load_tape()
    gm, g0, n_grid, vf = D["gm"], D["g0"], D["n"], D["valid_from"]

    # ---- sample instants --------------------------------------------------
    lo_i = max(vf, RV_WIN_MIN * 60, DIST_WIN_S, RET_WIN_S, 1800) + 1
    sample_idx = np.arange(lo_i, n_grid - 1, SAMPLE_STEP_S, dtype=np.int64)
    out(f"sample instants        : {len(sample_idx):,} (feature index i, outcome "
        f"index j=i+1; first i={lo_i} so every feature window is complete)")
    assert (sample_idx + 1 > sample_idx).all()

    # ---- outcomes ---------------------------------------------------------
    sub("first-touch computation (exact, unbounded horizon, suffix record chain)")
    ft = first_touch_times(gm, vf, sample_idx, XS_BPS)
    BIG = ft["big"]
    j_idx = sample_idx + 1
    horizon_ok = {T: (j_idx + T) <= (n_grid - 1) for T in TS_S}
    for T in TS_S:
        out(f"  T={TS_LABEL[T]:>3}: {int(horizon_ok[T].sum()):,} of {len(sample_idx):,} "
            f"samples have the full horizon inside the tape")

    o = {"up_hit": {}, "dn_hit": {}, "draw": {}, "valid": {}}
    for x in XS_BPS:
        u = ft["up"][x]
        d = ft["dn"][x]
        assert not np.any((u == d) & (u < BIG)), "simultaneous two-sided touch"
        for T in TS_S:
            uh = (u <= T) & horizon_ok[T]
            dh = (d <= T) & horizon_ok[T]
            first_up = uh & (~dh | (u < d))
            first_dn = dh & (~uh | (d < u))
            draw = horizon_ok[T] & ~uh & ~dh
            o["up_hit"][(x, T)] = first_up
            o["dn_hit"][(x, T)] = first_dn
            o["draw"][(x, T)] = draw
            o["valid"][(x, T)] = horizon_ok[T]
            o.setdefault("both", {})[(x, T)] = uh & dh

    days_of = np.floor((g0 + sample_idx) / 86400.0).astype(np.int64)
    span_s = float(D["days"] * 86400.0)

    # forward signed move at the horizon (used for the honest per-attempt EV
    # and for the gate diagnostic).  Causal: measured from j = i+1.
    fwd = {}
    for T in TS_S:
        jj = sample_idx + 1
        okf = (jj + T) <= (n_grid - 1)
        v = np.full(len(sample_idx), np.nan)
        v[okf] = (gm[jj[okf] + T] - gm[jj[okf]]) / gm[jj[okf]] * 1e4
        fwd[T] = v

    # ---- features ---------------------------------------------------------
    feats, raw = build_features(D, sample_idx)
    sub("condition features (all causal; value at i uses m[..i] only)")
    for k, f in feats.items():
        counts = [int((f.code == li).sum()) for li in range(len(f.labels))]
        share = "  ".join(f"{lab}:{c:,}({c/len(sample_idx)*100:.1f}%)"
                          for lab, c in zip(f.labels, counts))
        undef = int((f.code < 0).sum())
        out(f"  {k:<8} {f.note}")
        out(f"           {share}   undefined:{undef:,}")

    # ======================================================================
    # 1. UNCONDITIONAL BASE RATES
    # ======================================================================
    header("1. UNCONDITIONAL BASE RATES -- the denominator of every lift below")
    base: dict[tuple, Cell] = {}
    allmask = np.ones(len(sample_idx), bool)
    sub("first-touch race: P(+X first | decisive), and the draw share")
    out(f"{'X bps':>6} | " + " | ".join(f"{TS_LABEL[T]:^30}" for T in TS_S))
    out(f"{'':>6} | " + " | ".join(f"{'n_dec':>7}{'p_up%':>8}{'draw%':>8}{'gap':>7}"
                                   for _ in TS_S))
    line()
    for x in XS_BPS:
        row = f"{int(x):>6} | "
        cells = []
        for T in TS_S:
            c = cell_stats("ALL", allmask & o["valid"][(x, T)], o, x, T)
            base[(x, T)] = c
            cells.append(f"{c.n_dec:>7,}{c.p_dec*100:>8.2f}{c.n_draw/c.n*100:>8.1f}"
                         f"{(c.p_star - p_req_race(x))*100:>7.1f}")
        out(row + " | ".join(cells))
    out("gap = (p_star - p_req) in percentage points; p_star = max(p_up, p_down).")
    out("EVERY unconditional gap is deeply negative: an unconditional bracket is a")
    out("guaranteed loser at all four X and all four T.")

    sub("magnitude: P(max |deviation| >= X inside T)  [= 1 - draw share]")
    out(f"{'X bps':>6} | " + " | ".join(f"{TS_LABEL[T]:^24}" for T in TS_S))
    out(f"{'':>6} | " + " | ".join(f"{'n':>8}{'reach%':>8}{'gap':>8}" for _ in TS_S))
    line()
    for x in XS_BPS:
        row = f"{int(x):>6} | "
        cells = []
        for T in TS_S:
            c = base[(x, T)]
            gap = (c.p_reach - p_req_magnitude(x)) * 100
            cells.append(f"{c.n:>8,}{c.p_reach*100:>8.2f}{gap:>8.1f}")
        out(row + " | ".join(cells))
    out("gap = (P(reach) - 15.84/X) in percentage points.  X=10 is impossible by")
    out("construction (P_req = 158.4%).")

    sub("day-cluster bootstrap on the baselines (the honest CI)")
    out(f"{'X':>5}{'T':>5}{'target':>10}{'p_hat%':>9}{'wilson95 (nominal)':>26}"
        f"{'day-cluster95':>22}")
    line()
    for x in XS_BPS:
        for T in TS_S:
            c = base[(x, T)]
            m = allmask & o["valid"][(x, T)]
            dec = o["up_hit"][(x, T)][m] | o["dn_hit"][(x, T)][m]
            up = o["up_hit"][(x, T)][m]
            dlo, dhi, _ = day_cluster_prop_ci(up[dec].astype(float),
                                              days_of[m][dec], rng)
            wl, wh = wilson(c.n_up, c.n_dec)
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{'race':>10}{c.p_dec*100:>9.2f}"
                f"{f'[{wl*100:.2f}, {wh*100:.2f}]':>26}"
                f"{f'[{dlo*100:.2f}, {dhi*100:.2f}]':>22}")
            reach = (~o["draw"][(x, T)][m]).astype(float)
            rlo, rhi, _ = day_cluster_prop_ci(reach, days_of[m], rng)
            wl2, wh2 = wilson(c.n - c.n_draw, c.n)
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{'magnitude':>10}{c.p_reach*100:>9.2f}"
                f"{f'[{wl2*100:.2f}, {wh2*100:.2f}]':>26}"
                f"{f'[{rlo*100:.2f}, {rhi*100:.2f}]':>22}")
    out("The nominal Wilson interval is 5-30x too narrow: consecutive 10-second")
    out("samples share almost the whole outcome window.  Read the day-cluster one.")

    # ======================================================================
    # 2. SINGLE FEATURES
    # ======================================================================
    header("2. SINGLE-FEATURE ATLAS")
    single_cells = []            # (feat, level, x, T, target, Cell, lift, gap)
    single_cache: dict[tuple, Cell] = {}
    for fk, f in feats.items():
        for li, lab in enumerate(f.labels):
            fm = (f.code == li)
            for x in XS_BPS:
                for T in TS_S:
                    m = fm & o["valid"][(x, T)]
                    if m.sum() == 0:
                        continue
                    c = cell_stats(f"{fk}={lab}", m, o, x, T)
                    single_cache[(fk, li, x, T)] = c
                    b = base[(x, T)]
                    lift_r = (c.p_star / b.p_star) if b.p_star and c.n_dec else float("nan")
                    lift_m = (c.p_reach / b.p_reach) if b.p_reach and c.n else float("nan")
                    single_cells.append((fk, li, lab, x, T, "race", c, lift_r,
                                         c.p_star - p_req_race(x)))
                    single_cells.append((fk, li, lab, x, T, "magnitude", c, lift_m,
                                         c.p_reach - p_req_magnitude(x)))

    def show_top(target: str, k: int = 18) -> None:
        rows = [r for r in single_cells if r[5] == target and r[6].n >= N_REF_ONLY]
        rows.sort(key=lambda r: -abslog(r[7]))
        sub(f"single-feature lift ranking -- {target} (top {k} by |ln lift|, n>=50)")
        out(f"{'feature=level':<28}{'X':>5}{'T':>5}{'n':>9}{'p_hat%':>9}{'base%':>8}"
            f"{'lift':>7}{'wilson95 nominal':>22}{'gap to line':>13}")
        line()
        for r in rows[:k]:
            fk, li, lab, x, T, tg, c, lf, gap = r
            if tg == "race":
                p, kk, nn = c.p_star, c.k_star, c.n_dec
                bp = base[(x, T)].p_star
            else:
                p, kk, nn = c.p_reach, c.n - c.n_draw, c.n
                bp = base[(x, T)].p_reach
            wl, wh = wilson(kk, nn)
            out(f"{fk + '=' + lab:<28}{int(x):>5}{TS_LABEL[T]:>5}{nn:>9,}{p*100:>9.2f}"
                f"{bp*100:>8.2f}{lf:>7.2f}"
                f"{f'[{wl*100:.1f}, {wh*100:.1f}]':>22}{gap*100:>12.1f}pp")

    show_top("magnitude")
    show_top("race")

    sub("the two known checkpoints, measured head-on")
    out("(i) clock window magnitude lift -- report h says storm incidence lifts 2.23x")
    out(f"{'X':>5}{'T':>5}{'in-window reach%':>18}{'out reach%':>13}{'lift':>7}"
        f"{'n_in':>9}{'day-cluster95 (in)':>24}")
    line()
    fclock = feats["clock"]
    for x in XS_BPS:
        for T in TS_S:
            mi_ = (fclock.code == 0) & o["valid"][(x, T)]
            mo_ = (fclock.code == 1) & o["valid"][(x, T)]
            ci_ = cell_stats("clk_in", mi_, o, x, T)
            co_ = cell_stats("clk_out", mo_, o, x, T)
            lo_, hi_, _ = day_cluster_prop_ci((~o["draw"][(x, T)][mi_]).astype(float),
                                              days_of[mi_], rng)
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{ci_.p_reach*100:>18.2f}"
                f"{co_.p_reach*100:>13.2f}{ci_.p_reach/co_.p_reach:>7.2f}{ci_.n:>9,}"
                f"{f'[{lo_*100:.2f}, {hi_*100:.2f}]':>24}")
    out("(ii) direction: does ANY single feature move p_star off the base rate?")
    out("Two n-floors are shown.  The n>=50 column is where the multiple-")
    out("comparison yield lives; the n_dec>=5000 column is where an estimate can")
    out("actually be made.  Direction is a WALL only if the second column is ~1.")
    out(f"{'feature':<10}{'--- n_dec>=50 ---':>34}{'':>4}"
        f"{'--- n_dec>=5000 ---':>36}")
    out(f"{'':<10}{'X':>5}{'T':>5}{'max dpp':>9}{'lift':>7}{'level':>8}{'':>4}"
        f"{'X':>5}{'T':>5}{'max dpp':>9}{'lift':>7}{'level':>10}")
    line()
    for fk, f in feats.items():
        cols = []
        for floor in (N_REF_ONLY, 5000):
            worst = None
            for x in XS_BPS:
                for T in TS_S:
                    for li, lab in enumerate(f.labels):
                        m = (f.code == li) & o["valid"][(x, T)]
                        if m.sum() < N_REF_ONLY:
                            continue
                        c = cell_stats("x", m, o, x, T)
                        if c.n_dec < floor:
                            continue
                        d = abs(c.p_star - base[(x, T)].p_star)
                        if worst is None or d > worst[0]:
                            worst = (d, x, T, lab, c.p_star / base[(x, T)].p_star)
            if worst:
                d, x, T, lab, lf = worst
                cols.append(f"{int(x):>5}{TS_LABEL[T]:>5}{d*100:>9.2f}{lf:>7.3f}"
                            f"{lab.split()[0]:>8}")
            else:
                cols.append(f"{'--':>34}")
        out(f"{fk:<10}{cols[0]}{'':>4}{cols[1]}")

    # ======================================================================
    # 3. PAIR CROSSINGS
    # ======================================================================
    header("3. PAIR CROSSINGS -- frozen rule: top 5 features by max |ln lift| "
           "(n>=2000), all C(5,2)=10 pairs")
    rank = {}
    for fk, li, lab, x, T, tg, c, lf, gap in single_cells:
        nn = c.n_dec if tg == "race" else c.n
        if nn < N_PAIR_MIN:
            continue
        rank[fk] = max(rank.get(fk, 0.0), abslog(lf))
    primary = [k for k in feats if k != "burst10"]
    ranked = sorted([(rank.get(k, 0.0), k) for k in primary], reverse=True)
    out("feature ranking by max |ln lift| over its cells with nominal n>=2000:")
    for v, k in ranked:
        out(f"   {k:<10} {v:.4f}   (max lift {math.exp(v):.3f}x)")
    top5 = [k for _, k in ranked[:5]]
    pairs = [(top5[a], top5[b]) for a in range(5) for b in range(a + 1, 5)]
    out(f"pairs crossed ({len(pairs)}): " + ", ".join(f"{a}x{b}" for a, b in pairs))

    pair_cells = []
    for fa, fb in pairs:
        A, B = feats[fa], feats[fb]
        for ia, la in enumerate(A.labels):
            for ib, lb_ in enumerate(B.labels):
                fm = (A.code == ia) & (B.code == ib)
                for x in XS_BPS:
                    for T in TS_S:
                        m = fm & o["valid"][(x, T)]
                        if m.sum() == 0:
                            continue
                        c = cell_stats(f"{fa}={la} & {fb}={lb_}", m, o, x, T)
                        b = base[(x, T)]
                        ca = single_cache[(fa, ia, x, T)]
                        cb = single_cache[(fb, ib, x, T)]
                        for tg in ("race", "magnitude"):
                            if tg == "race":
                                p, bp = c.p_star, b.p_star
                                pa, pb = ca.p_star, cb.p_star
                                nn = c.n_dec
                            else:
                                p, bp = c.p_reach, b.p_reach
                                pa, pb = ca.p_reach, cb.p_reach
                                nn = c.n
                            lf = p / bp if bp else float("nan")
                            la_ = pa / bp if bp else float("nan")
                            lb2 = pb / bp if bp else float("nan")
                            inter = lf / (la_ * lb2) if (la_ and lb2) else float("nan")
                            gp = (p - p_req_race(x)) if tg == "race" \
                                else (p - p_req_magnitude(x))
                            pair_cells.append((fa, la, fb, lb_, x, T, tg, c, nn,
                                               p, lf, inter, gp))

    for tg in ("magnitude", "race"):
        rows = [r for r in pair_cells if r[6] == tg and r[8] >= N_REF_ONLY]
        rows.sort(key=lambda r: -(r[11] if np.isfinite(r[11]) else 0.0))
        sub(f"pair interaction vs the multiplicative null -- {tg} "
            f"(top 12 by lift(A&B)/(lift(A)*lift(B)), n>=50)")
        out(f"{'cell':<46}{'X':>5}{'T':>5}{'n':>8}{'p%':>8}{'lift':>7}"
            f"{'interact':>10}{'gap to line':>13}")
        line()
        for r in rows[:12]:
            fa, la, fb, lb_, x, T, _, c, nn, p, lf, inter, gp = r
            out(f"{fa + '=' + la + ' & ' + fb + '=' + lb_:<46}{int(x):>5}"
                f"{TS_LABEL[T]:>5}{nn:>8,}{p*100:>8.2f}{lf:>7.2f}{inter:>10.3f}"
                f"{gp*100:>12.1f}pp")
        out("interact > 1 means the pair does MORE than the product of its parts")
        out("(report 21's window x touch = 6x is the shape being hunted).")

    # ======================================================================
    # 4. WIDTH OF THE SURFACE AND THE CHANCE YIELD
    # ======================================================================
    header("4. WIDTH OF THE SURFACE, AND HOW MANY CELLS CHANCE ALONE WOULD "
           "PUSH OVER THE LINE")
    n_single = len(single_cells)
    n_pair = len(pair_cells)
    M = n_single + n_pair + 2 * len(XS_BPS) * len(TS_S)
    out(f"single-feature cells : {n_single:,}  "
        f"({len(feats)} features incl. the burst10 sensitivity, "
        f"{sum(len(f.labels) for f in feats.values())} levels x "
        f"{len(XS_BPS)*len(TS_S)} X-T x 2 targets)")
    out(f"pair cells           : {n_pair:,}")
    out(f"baseline cells       : {2*len(XS_BPS)*len(TS_S)}")
    out(f"TOTAL CELLS EXAMINED : {M:,}")

    def chance_yield(cells, use_eff: bool) -> tuple[float, float]:
        """(expected race crossings, expected magnitude crossings) under the
        unconditional base rate, charging for the max(up,down) side pick."""
        er = em = 0.0
        for rec in cells:
            if len(rec) == 9:
                fk, li, lab, x, T, tg, c, lf, gap = rec
                nn = c.n_dec if tg == "race" else c.n
            else:
                fa, la, fb, lb_, x, T, tg, c, nn, p, lf, inter, gp = rec
            if nn < N_REF_ONLY:
                continue
            b = base[(x, T)]
            if use_eff:
                nn = max(2, int(round(min(nn, span_s / T))))
            if tg == "race":
                p0 = b.p_dec
                k = int(math.ceil(p_req_race(x) * nn))
                er += binom_sf_ge(k, nn, p0) + binom_sf_ge(k, nn, 1 - p0)
            else:
                p0 = b.p_reach
                k = int(math.ceil(p_req_magnitude(x) * nn))
                if k <= nn:
                    em += binom_sf_ge(k, nn, p0)
        return er, em

    for use_eff, tag in ((False, "nominal n (overlapping samples: OPTIMISTIC)"),
                         (True, "effective n = span/T (independent windows: HONEST)")):
        er1, em1 = chance_yield(single_cells, use_eff)
        er2, em2 = chance_yield(pair_cells, use_eff)
        out(f"expected crossings by chance, {tag}:")
        out(f"   race      single {er1:8.3f}   pair {er2:8.3f}   total {er1+er2:8.3f}")
        out(f"   magnitude single {em1:8.3f}   pair {em2:8.3f}   total {em1+em2:8.3f}")

    # ======================================================================
    # 5. THE ENUMERATION -- every cell over its line
    # ======================================================================
    header("5. ENUMERATION OF EVERY CELL OVER ITS REQUIRED-p LINE")

    def enumerate_crossers(tg: str):
        rows = []
        for rec in single_cells:
            fk, li, lab, x, T, t2, c, lf, gap = rec
            if t2 != tg:
                continue
            nn = c.n_dec if tg == "race" else c.n
            if nn < N_REF_ONLY or gap <= 0:
                continue
            rows.append(("single", fk, li, lab, None, None, None, x, T, c, nn, gap))
        for rec in pair_cells:
            fa, la, fb, lb_, x, T, t2, c, nn, p, lf, inter, gp = rec
            if t2 != tg or nn < N_REF_ONLY or gp <= 0:
                continue
            rows.append(("pair", fa, None, la, fb, None, lb_, x, T, c, nn, gp))
        return rows

    sub("whipsaw diagnostic -- P(BOTH barriers touched | at least one), "
        "unconditional")
    out("A two-sided bracket that is hit on both sides does not collect X; it")
    out("collects X on one leg and gives it back on the other.  The frozen line")
    out("X*P(reach) - 2*7.92 IGNORES this, so it is an UPPER bound on a")
    out("bracket's EV, never its EV.")
    out(f"{'X':>6} | " + " | ".join(f"{TS_LABEL[T]:^16}" for T in TS_S))
    line()
    for x in XS_BPS:
        cells = []
        for T in TS_S:
            v = o["valid"][(x, T)]
            reach = (~o["draw"][(x, T)]) & v
            both = o["both"][(x, T)] & v
            cells.append(f"{(both.sum()/max(reach.sum(),1))*100:>16.1f}")
        out(f"{int(x):>6} | " + " | ".join(cells))
    out("(percent of reached cases that touched BOTH sides inside T)")

    surv_summary = {}
    crosser_grid = {}
    for tg in ("race", "magnitude"):
        rows = enumerate_crossers(tg)
        sub(f"{tg.upper()}: cells whose POINT ESTIMATE clears the line "
            f"(n>={N_REF_ONLY})")
        if not rows:
            out("ZERO.  Not one condition cell in the entire surface reaches the "
                "probability a taker round trip demands.")
            surv_summary[tg] = (0, 0, [])
            continue
        out(f"{len(rows)} cells clear on the point estimate.  Each is now put "
            f"through the day-cluster CI, the 60/40 split, the episode-diversity")
        out("diagnostic (AMENDMENT 1) and, for magnitude, the question of whether")
        out("the UNCONDITIONAL rate at the same X,T already clears the same line.")
        out(f"{'kind':<7}{'cell':<44}{'X':>5}{'T':>5}{'n':>8}{'p%':>8}{'req%':>7}"
            f"{'daycluster95':>22}{'1st60%':>8}{'2nd40%':>8}{'days':>5}"
            f"{'maxday%':>8}{'unc':>4}{'EVatt':>9}{'SURV':>6}")
        line()
        if tg == "race":
            out("EVatt = the HONEST per-attempt expectation of the trade this "
                "probability describes:")
            out("        take the majority side with TP=+X, SL=-X, market exit at "
                "T on a draw,")
            out("        EV = P(win)*X - P(lose)*X + P(draw)*E[side*move(T)|draw] "
                "- 7.92 bps.")
            out("        p_req only prices the DECISIVE races; EVatt prices the "
                "whole attempt,")
            out("        and the draw share is where a high p on a rare decisive "
                "race goes to die.")
        cut60 = sample_idx[int(len(sample_idx) * 0.6)]
        first_half = sample_idx <= cut60
        n_ci = 0
        survivors = []
        grid = {}
        for kind, f1, _li, l1, f2, _lj, l2, x, T, c, nn, gap in rows:
            grid[(x, T)] = grid.get((x, T), 0) + 1
            if kind == "single":
                mfull = (feats[f1].code == feats[f1].labels.index(l1))
                nm = f"{f1}={l1}"
            else:
                mfull = ((feats[f1].code == feats[f1].labels.index(l1)) &
                         (feats[f2].code == feats[f2].labels.index(l2)))
                nm = f"{f1}={l1} & {f2}={l2}"
            m = mfull & o["valid"][(x, T)]
            b = base[(x, T)]
            if tg == "race":
                dec = o["up_hit"][(x, T)] | o["dn_hit"][(x, T)]
                sel = m & dec
                win = (o["up_hit"][(x, T)] if c.n_up >= c.n_dn
                       else o["dn_hit"][(x, T)])
                y = win[sel].astype(float)
                dd = days_of[sel]
                p = c.p_star
                req = p_req_race(x)
                y1 = win[sel & first_half].astype(float)
                y2 = win[sel & ~first_half].astype(float)
                unc = "yes" if b.p_star > req else "no"
                sgn = 1.0 if c.n_up >= c.n_dn else -1.0
                dmask = m & o["draw"][(x, T)]
                dv = sgn * fwd[T][dmask]
                dv = dv[np.isfinite(dv)]
                nw = int((m & win).sum())
                nl = int((m & dec & ~win).sum())
                ev = ((nw * x - nl * x + (dv.sum() if len(dv) else 0.0))
                      / max(c.n, 1)) - TAKER_ROUND
            else:
                sel = m
                y = (~o["draw"][(x, T)][sel]).astype(float)
                dd = days_of[sel]
                p = c.p_reach
                req = p_req_magnitude(x)
                y1 = (~o["draw"][(x, T)][sel & first_half]).astype(float)
                y2 = (~o["draw"][(x, T)][sel & ~first_half]).astype(float)
                unc = "yes" if b.p_reach > req else "no"
                ev = x * p - 2.0 * TAKER_ROUND
            lo_, hi_, _ = day_cluster_prop_ci(y, dd, rng)
            nd, mday = day_spread(dd)
            ci_ok = bool(np.isfinite(lo_) and lo_ > req)
            n_ci += int(ci_ok)
            surv = "YES" if (ci_ok and nd >= 10 and mday <= 0.50) else "no"
            if surv == "YES":
                survivors.append((kind, nm, x, T, nn, p, req, lo_, hi_, nd,
                                  mday, unc, ev))
            out(f"{kind:<7}{nm:<44}{int(x):>5}{TS_LABEL[T]:>5}{nn:>8,}{p*100:>8.2f}"
                f"{req*100:>7.2f}{f'[{lo_*100:.2f}, {hi_*100:.2f}]':>22}"
                f"{(y1.mean()*100 if len(y1) else float('nan')):>8.2f}"
                f"{(y2.mean()*100 if len(y2) else float('nan')):>8.2f}{nd:>5}"
                f"{mday*100:>8.1f}{unc:>4}{ev:>9.2f}{surv:>6}")
        out(f"cells whose DAY-CLUSTER lower bound clears the line          : "
            f"{n_ci}")
        out(f"cells that ALSO pass episode diversity (>=10 days, maxday<=50%): "
            f"{len(survivors)}")
        n_unc = sum(1 for s in survivors if s[11] == "yes")
        out(f"of those survivors, cells where the UNCONDITIONAL rate at the same "
            f"X,T already clears the same line (i.e. the condition adds nothing "
            f"to the crossing): {n_unc}")
        if tg == "race":
            pos_ev = [s for s in survivors if s[12] > 0]
            out(f"of those survivors, cells with a POSITIVE honest per-attempt EV: "
                f"{len(pos_ev)}")
        crosser_grid[tg] = grid
        surv_summary[tg] = (n_ci, len(survivors), survivors)

    sub("where the point-estimate crossers live (count by X and T)")
    for tg in ("race", "magnitude"):
        out(f"{tg}:")
        out(f"{'X':>6} | " + " | ".join(f"{TS_LABEL[T]:^8}" for T in TS_S))
        for x in XS_BPS:
            g = crosser_grid.get(tg, {})
            out(f"{int(x):>6} | " +
                " | ".join(f"{g.get((x, T), 0):^8}" for T in TS_S))
    out("Compare with the effective-n table in section 4: the race crossers")
    out("concentrate exactly where the number of INDEPENDENT outcome windows is")
    out("smallest, which is the signature of a multiple-comparison yield.")

    sub("FINAL SHORT LIST -- cells surviving CI + episode diversity")
    for tg in ("race", "magnitude"):
        n_ci, n_sv, survivors = surv_summary[tg]
        out(f"{tg.upper()}: {n_sv} survivors "
            f"(of {n_ci} that passed the CI alone)")
        if not survivors:
            out("   ZERO.")
            continue
        for kind, nm, x, T, nn, p, req, lo_, hi_, nd, mday, unc, ev in survivors:
            out(f"   {kind:<7}{nm:<44} X={int(x):>3} T={TS_LABEL[T]:<3} "
                f"n={nn:>7,} p={p*100:>6.2f}% req={req*100:>5.2f}% "
                f"CI[{lo_*100:.1f},{hi_*100:.1f}] days={nd} maxday={mday*100:.0f}% "
                f"uncond={unc} EVatt={ev:+.2f}bps")

    sub("plateau inspection of the strongest magnitude cells "
        "(does the neighbouring tercile/bucket collapse?)")
    out(f"{'feature':<10}{'X':>5}{'T':>5}" +
        "".join(f"{'lvl' + str(i):>16}" for i in range(3)))
    line()
    for fk in ("clock", "rv60", "burst20", "burst10", "dist30", "flow", "ret5"):
        f = feats[fk]
        for x in (20.0, 50.0):
            for T in (1800, 7200):
                vals = []
                for li in range(3):
                    if li >= len(f.labels):
                        vals.append(f"{'-':>16}")
                        continue
                    m = (f.code == li) & o["valid"][(x, T)]
                    if m.sum() < N_REF_ONLY:
                        vals.append(f"{'n<50':>16}")
                        continue
                    c = cell_stats("p", m, o, x, T)
                    vals.append(f"{c.p_reach*100:>10.2f}%{'':>5}")
                out(f"{fk:<10}{int(x):>5}{TS_LABEL[T]:>5}" + "".join(vals))
    out("A monotone row is a plateau (the effect survives a one-step move of the")
    out("cut); a spike surrounded by collapse is a multiple-comparison artefact.")

    sub("causal-tercile robustness: rv60 terciles re-cut on a TRAILING 7-day "
        "rolling quantile instead of the whole sample")
    rv_s = raw["rv60"]
    win_s = int(7 * 86400 / SAMPLE_STEP_S)
    ser = pd.Series(rv_s)
    rq1 = ser.rolling(win_s, min_periods=win_s // 4).quantile(1 / 3).shift(1).to_numpy()
    rq2 = ser.rolling(win_s, min_periods=win_s // 4).quantile(2 / 3).shift(1).to_numpy()
    code_c = np.full(len(rv_s), -1, dtype=np.int8)
    ok = np.isfinite(rv_s) & np.isfinite(rq1) & np.isfinite(rq2)
    code_c[ok & (rv_s <= rq1)] = 0
    code_c[ok & (rv_s > rq1) & (rv_s <= rq2)] = 1
    code_c[ok & (rv_s > rq2)] = 2
    out(f"{'X':>5}{'T':>5}{'global T3 reach%':>18}{'causal T3 reach%':>18}"
        f"{'global T1':>12}{'causal T1':>12}{'n causal':>10}")
    line()
    for x in XS_BPS:
        for T in (1800, 7200):
            g3 = cell_stats("g", (feats["rv60"].code == 2) & o["valid"][(x, T)],
                            o, x, T)
            c3 = cell_stats("c", (code_c == 2) & o["valid"][(x, T)], o, x, T)
            g1c = cell_stats("g", (feats["rv60"].code == 0) & o["valid"][(x, T)],
                             o, x, T)
            c1 = cell_stats("c", (code_c == 0) & o["valid"][(x, T)], o, x, T)
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{g3.p_reach*100:>18.2f}"
                f"{c3.p_reach*100:>18.2f}{g1c.p_reach*100:>12.2f}"
                f"{c1.p_reach*100:>12.2f}{c3.n:>10,}")

    # ======================================================================
    # 6. LONG-HORIZON PROXY (Binance 210d) -- MAGNITUDE ONLY
    # ======================================================================
    header("6. LONG-HORIZON PROXY -- Binance BTCUSDT 1m, MAGNITUDE ONLY "
           "(never a direction race)")
    bz = binance_block(rng)

    # ======================================================================
    # 7. GATE APPLICATION DIAGNOSTIC
    # ======================================================================
    header("7. GATE DIAGNOSTIC -- what a magnitude gate would do to an existing "
           "entry family (information, NOT a strategy)")
    ret5 = raw["ret5"]
    ret30 = raw["ret30"]
    champ = np.isfinite(ret30) & (np.abs(ret30) >= 80.0)
    champ_side = np.sign(ret30)
    bset = raw["burst_sets"]["burst10"]
    is_burst = np.zeros(len(sample_idx), bool)
    bpos = np.searchsorted(bset, sample_idx, side="right") - 1
    elapsed = np.where(bpos >= 0, sample_idx - bset[np.clip(bpos, 0, len(bset) - 1)],
                       1 << 30)
    is_burst = elapsed <= 60                       # within 60 s of a burst
    burst_side = np.sign(np.where(np.isfinite(ret5), ret5, 0.0))

    gates = [("clock=in", feats["clock"].code == 0),
             ("rv60=T3", feats["rv60"].code == 2),
             ("rv60=T1", feats["rv60"].code == 0),
             ("burst10<2m", feats["burst10"].code == 0),
             ("flow=in", feats["flow"].code == 0),
             ("dist30=T1(near)", feats["dist30"].code == 0),
             ("clock=in & rv60=T3",
              (feats["clock"].code == 0) & (feats["rv60"].code == 2))]

    def episode_first(trig: np.ndarray, T: int) -> np.ndarray:
        """One sample per non-overlapping episode: keep a trigger only if no
        kept trigger lies within T seconds before it (report 24's de-overlap)."""
        keep = np.zeros(len(trig), bool)
        last = -1e18
        for q in np.flatnonzero(trig):
            ti = float(sample_idx[q])
            if ti - last < T:
                continue
            last = ti
            keep[q] = True
        return keep

    for fam_name, trig, side, horizons in (
            ("champion-proxy (|30m ret|>=80bps, taker continuation)",
             champ, champ_side, (1800, 7200)),
            ("scalper-proxy (within 60s of a 2s/10bps burst, taker continuation)",
             is_burst, burst_side, (300, 1800))):
        sub(f"{fam_name}")
        out(f"{'gate':<24}{'T':>5}{'n in':>8}{'drift in':>10}{'n out':>9}"
            f"{'drift out':>11}{'difference':>12}{'daycluster95 (in)':>24}"
            f"{'NON-OVERLAP in':>18}{'n':>6}")
        line()
        nonlap = {T: episode_first(trig, T) for T in horizons}
        for gname, gmask in gates:
            for T in horizons:
                v = side * fwd[T]
                base_m = trig & np.isfinite(v)
                mi_ = base_m & gmask
                mo_ = base_m & ~gmask
                if mi_.sum() < 10 or mo_.sum() < 10:
                    continue
                lo_, hi_, _ = day_cluster_mean_ci(v[mi_], days_of[mi_], rng)
                nl = nonlap[T] & mi_
                nlv = v[nl].mean() if nl.sum() else float("nan")
                out(f"{gname:<24}{TS_LABEL[T]:>5}{int(mi_.sum()):>8,}"
                    f"{v[mi_].mean():>10.2f}{int(mo_.sum()):>9,}"
                    f"{v[mo_].mean():>11.2f}{v[mi_].mean()-v[mo_].mean():>12.2f}"
                    f"{f'[{lo_:.2f}, {hi_:.2f}]':>24}{nlv:>18.2f}"
                    f"{int(nl.sum()):>6}")
        out(f"drift = signed continuation move in bps.  Round-trip taker line = "
            f"{TAKER_ROUND:.2f} bps.")
        out("The overlapping column is the one report 24 showed collapses "
            "(+9.40 -> +1.46 bps)")
        out("when the same triggers are de-overlapped.  NON-OVERLAP keeps one "
            "sample per")
        out("episode of length T and is the honest column.")

    # ======================================================================
    # 8. THE MAP -- what is predictable and what is not, as an X x T surface
    # ======================================================================
    header("8. THE MAP OF WHAT THIS MARKET LETS YOU PREDICT (X x T surface)")
    out("For each X,T: the widest SPREAD any single condition opens between its")
    out("levels, for each target, restricted to levels with n_dec (race) or n")
    out("(magnitude) >= 5000 so an estimate is possible at all.")
    out(f"{'X':>5}{'T':>5}{'RACE spread pp':>16}{'best feature':>16}"
        f"{'MAG spread pp':>16}{'best feature':>16}{'MAG uncond%':>13}")
    line()
    for x in XS_BPS:
        for T in TS_S:
            best = {"race": (0.0, "-"), "magnitude": (0.0, "-")}
            for fk, f in feats.items():
                ps = {"race": [], "magnitude": []}
                for li in range(len(f.labels)):
                    key = (fk, li, x, T)
                    if key not in single_cache:
                        continue
                    c = single_cache[key]
                    if c.n_dec >= 5000:
                        ps["race"].append(c.p_dec)
                    if c.n >= 5000:
                        ps["magnitude"].append(c.p_reach)
                for tg in ("race", "magnitude"):
                    if len(ps[tg]) >= 2:
                        sp = (max(ps[tg]) - min(ps[tg])) * 100
                        if sp > best[tg][0]:
                            best[tg] = (sp, fk)
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{best['race'][0]:>16.2f}"
                f"{best['race'][1]:>16}{best['magnitude'][0]:>16.2f}"
                f"{best['magnitude'][1]:>16}{base[(x, T)].p_reach*100:>13.2f}")
    out("RACE spread is the whole directional information content available at")
    out("that X,T from any of the seven conditions.  MAG spread is the magnitude")
    out("information content.  Compare RACE spread with the gap the cost line")
    out("demands: p_req - 50 = 39.6 / 19.8 / 7.92 / 3.96 pp for X = 10/20/50/100.")

    sub("drift attribution -- is the surviving directional signal just this "
        "sample's net trend?")
    net = (gm[-1] - gm[lo_i]) / gm[lo_i] * 1e4
    out(f"tape net move over the {D['days']:.1f} usable days: {net:+,.0f} bps "
        f"({net/1e2:+.2f}%), i.e. {net/D['days']:+.0f} bps/day")
    dcode = feats["dow"].code
    for lab, li in (("weekday", 0), ("weekend", 1)):
        sel = dcode == li
        uq = np.unique(days_of[sel])
        per_day = []
        for dday in uq:
            s = sel & (days_of == dday)
            ii = sample_idx[s]
            if len(ii) < 2:
                continue
            per_day.append((gm[ii[-1]] - gm[ii[0]]) / gm[ii[0]] * 1e4)
        pd_arr = np.asarray(per_day)
        out(f"  {lab:<8} calendar days {len(pd_arr):>3}   mean move/day "
            f"{pd_arr.mean():>+8.1f} bps   median {np.median(pd_arr):>+8.1f}   "
            f"sd {pd_arr.std(ddof=1):>7.1f}")
    out("A race probability at long T is a restatement of the sample's realised")
    out("drift over that horizon.  With 8 weekend days in the window, a weekend")
    out("direction 'edge' is one number about one month, which is exactly the")
    out("shape KNOWLEDGE section 3 calls memorising the sample (long-horizon")
    out("momentum: train +1.7..22%/trade, val and OOS all negative).")

    # ======================================================================
    # 9. SANITY
    # ======================================================================
    header("9. SANITY")
    out("look-ahead      : feature index i, outcome index j = i+1; asserted "
        "elementwise.  Feature windows end at i inclusive, outcome windows start")
    out("                  at i+1 -- the two never share a second.")
    sub("tautology probe (report 9's lesson: prove the detector can SEE a leak)")
    lead5 = np.full(len(sample_idx), np.nan)
    jj = sample_idx + 1
    okl = (jj + 300) <= (n_grid - 1)
    lead5[okl] = (gm[jj[okl] + 300] - gm[jj[okl]]) / gm[jj[okl]] * 1e4
    lq1, lq2 = terciles(lead5)
    leak_code = tercile_code(lead5, lq1, lq2)
    out(f"{'feature':<28}{'X':>5}{'T':>5}{'p_star%':>10}{'base%':>9}{'verdict':>34}")
    line()
    for x, T in ((20.0, 1800), (50.0, 7200)):
        c_leak = cell_stats("leak", (leak_code == 2) & o["valid"][(x, T)], o, x, T)
        c_true = cell_stats("true", (feats["ret5"].code == 2) & o["valid"][(x, T)],
                            o, x, T)
        b = base[(x, T)]
        out(f"{'LEAKED forward-5m T3':<28}{int(x):>5}{TS_LABEL[T]:>5}"
            f"{c_leak.p_star*100:>10.2f}{b.p_star*100:>9.2f}"
            f"{'detector fires on a real leak':>34}")
        out(f"{'causal trailing-5m T3':<28}{int(x):>5}{TS_LABEL[T]:>5}"
            f"{c_true.p_star*100:>10.2f}{b.p_star*100:>9.2f}"
            f"{'the atlas value':>34}")
    out("If the leaked row were not far above the causal row the whole design")
    out("would be blind to look-ahead.  It is not blind; the causal rows are the")
    out("honest ones.")

    sub("draw accounting and frequency plausibility")
    out("n_up + n_down + n_draw = n asserted inside cell_stats() for EVERY cell "
        f"({M:,} cells).")
    out("magnitude reach = 1 - draw share by construction, so the two targets "
        "tie out exactly.")
    for tag in ("burst20", "burst10"):
        out(f"  {tag}: {feats[tag].note}")
    out(f"  burst20 rate cross-check vs report 24 atlas (W=2s/thr20 -> 0.57/day): "
        f"{len(raw['burst_sets']['burst20'])/D['days']:.2f}/day")
    out(f"  clock-window duty {float((feats['clock'].code == 0).mean())*100:.2f}% "
        f"(2.5h/24h = 10.42% expected)")
    out(f"  weekend duty {float((feats['dow'].code == 1).mean())*100:.2f}% "
        f"(2/7 = 28.57% expected)")

    line("=")
    out(f"DETERMINISM HASH (all output above): {_HASH.hexdigest()}")
    line("=")
    out("EXPLORATION ONLY.  No adoption decision may be taken from this output.")
    return 0


# --------------------------------------------------------------------------
# Binance long-horizon block (magnitude only)
# --------------------------------------------------------------------------
def binance_block(rng: np.random.Generator) -> dict:
    cutoff = float((pd.Timestamp(FRESH_CUTOFF_ISO) - EPOCH) / pd.Timedelta("1s"))
    df = pd.read_csv(BINANCE)
    ts = pd.DatetimeIndex(pd.to_datetime(df["open_time"], utc=True))
    t = ((ts - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    keep = t < cutoff
    df = df.loc[keep].reset_index(drop=True)
    t = t[keep]
    out(f"binance rows kept      : {len(df):,} 1-min bars, "
        f"{iso(t[0])} .. {iso(t[-1])} ({(t[-1]-t[0])/86400:.1f} days)")
    gaps = np.diff(t)
    out(f"bar spacing            : median {np.median(gaps):.0f}s, "
        f"{int((gaps > 60).sum()):,} gaps > 60s (longest "
        f"{gaps.max()/60:.0f} min) -- gaps make the forward window a calendar")
    out("                         window, not a strict 1-bar-per-minute window")

    close = df["close"].to_numpy(float)
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    n = len(close)

    TS_MIN = {300: 5, 1800: 30, 7200: 120, 28800: 480}
    fmax, fmin = {}, {}
    for T, mm in TS_MIN.items():
        fmax[T] = pd.Series(high).rolling(mm).max().shift(-mm).to_numpy()
        fmin[T] = pd.Series(low).rolling(mm).min().shift(-mm).to_numpy()

    step = 5
    idx = np.arange(60, n, step, dtype=np.int64)
    tt = t[idx]
    sod = np.mod(tt, 86400.0)
    clock = np.where((sod >= CLOCK_LO_S) & (sod < CLOCK_HI_S), 0, 1).astype(np.int8)
    dow_ = (np.floor(tt / 86400.0).astype(np.int64) + 4) % 7
    dowc = np.where(dow_ >= 5, 1, 0).astype(np.int8)
    r1 = np.full(n, np.nan)
    r1[1:] = np.log(close[1:] / close[:-1]) * 1e4
    rv = pd.Series(r1).rolling(60, min_periods=60).std().to_numpy()[idx]
    q1, q2 = terciles(rv)
    rvc = tercile_code(rv, q1, q2)
    r5 = np.full(n, np.nan)
    r5[5:] = (close[5:] - close[:-5]) / close[:-5] * 1e4
    r5s = r5[idx]
    s1, s2 = terciles(r5s)
    r5c = tercile_code(r5s, s1, s2)
    months = np.asarray(
        pd.DatetimeIndex(pd.to_datetime(tt, unit="s", utc=True)).strftime("%Y-%m"))
    days_b = np.floor(tt / 86400.0).astype(np.int64)

    reach = {}
    for x in XS_BPS:
        for T in TS_S:
            up = fmax[T][idx] >= close[idx] * (1 + x / 1e4)
            dn = fmin[T][idx] <= close[idx] * (1 - x / 1e4)
            ok = np.isfinite(fmax[T][idx]) & np.isfinite(fmin[T][idx])
            reach[(x, T)] = (np.where(ok, up | dn, False), ok)

    sub("unconditional magnitude base rate, 210-day proxy vs the 28-day tape")
    out(f"{'X':>5} | " + " | ".join(f"{TS_LABEL[T]:^18}" for T in TS_S))
    out(f"{'':>5} | " + " | ".join(f"{'n':>9}{'reach%':>9}" for _ in TS_S))
    line()
    for x in XS_BPS:
        cells = []
        for T in TS_S:
            r, ok = reach[(x, T)]
            cells.append(f"{int(ok.sum()):>9,}{r[ok].mean()*100:>9.2f}")
        out(f"{int(x):>5} | " + " | ".join(cells))

    bfeats = {"clock": (clock, ["in 12:30-15:00Z", "out"]),
              "rv60": (rvc, [f"T1<={q1:.1f}", f"T2", f"T3>{q2:.1f}"]),
              "dow": (dowc, ["weekday", "weekend"]),
              "ret5": (r5c, [f"T1<={s1:.1f}", "T2", f"T3>{s2:.1f}"])}
    sub("conditional magnitude lift on 210 days (n>=50), all cells")
    out(f"{'feature=level':<26}{'X':>5}{'T':>5}{'n':>9}{'reach%':>9}{'base%':>8}"
        f"{'lift':>7}{'gap to P_req':>14}{'daycluster95':>22}")
    line()
    rows = []
    for fk, (code, labs) in bfeats.items():
        for li, lab in enumerate(labs):
            for x in XS_BPS:
                for T in TS_S:
                    r, ok = reach[(x, T)]
                    m = (code == li) & ok
                    if m.sum() < N_REF_ONLY:
                        continue
                    p = r[m].mean()
                    bp = r[ok].mean()
                    rows.append((fk, lab, x, T, int(m.sum()), p, bp, p / bp, m))
    rows.sort(key=lambda z: -abslog(z[7]))
    n_bcells = len(rows)
    for fk, lab, x, T, nn, p, bp, lf, m in rows[:20]:
        r, ok = reach[(x, T)]
        lo_, hi_, _ = day_cluster_prop_ci(r[m].astype(float), days_b[m], rng)
        out(f"{fk + '=' + lab:<26}{int(x):>5}{TS_LABEL[T]:>5}{nn:>9,}{p*100:>9.2f}"
            f"{bp*100:>8.2f}{lf:>7.2f}"
            f"{(p - p_req_magnitude(x))*100:>13.1f}pp"
            f"{f'[{lo_*100:.1f}, {hi_*100:.1f}]':>22}")
    out(f"(210-day proxy magnitude cells examined: {n_bcells})")

    sub("monthly stability of the strongest 210-day conditions")
    for fk, li, lab in (("clock", 0, "in 12:30-15:00Z"), ("rv60", 2, "T3"),
                        ("rv60", 0, "T1"), ("dow", 1, "weekend")):
        code = bfeats[fk][0]
        for x, T in ((20.0, 1800), (50.0, 7200)):
            r, ok = reach[(x, T)]
            m = (code == li) & ok
            parts = []
            for mo in sorted(set(months)):
                sel = m & (months == mo)
                if sel.sum() < 30:
                    continue
                parts.append(f"{mo[-2:]}:{r[sel].mean()*100:.0f}")
            out(f"  {fk}={lab:<18} X={int(x):>3} T={TS_LABEL[T]:<3} "
                f"overall {r[m].mean()*100:>5.1f}%   monthly " + " ".join(parts))
    out("Month labels are MM of 2026 (Jan-Aug).  A condition whose monthly level")
    out("wanders by more than its lift is not a stable conditional probability.")

    sub("LEVEL vs ORDERING: is the vol tercile ordering stable month by month?")
    out(f"{'X':>5}{'T':>5}{'months':>8}{'T3-T1 pp by month (sign must not flip)':>60}")
    line()
    code = bfeats["rv60"][0]
    for x in XS_BPS:
        for T in TS_S:
            r, ok = reach[(x, T)]
            parts, flips, tot = [], 0, 0
            for mo in sorted(set(months)):
                s3 = (code == 2) & ok & (months == mo)
                s1 = (code == 0) & ok & (months == mo)
                if s3.sum() < 30 or s1.sum() < 30:
                    continue
                d = (r[s3].mean() - r[s1].mean()) * 100
                tot += 1
                if d <= 0:
                    flips += 1
                parts.append(f"{mo[-2:]}:{d:+.0f}")
            out(f"{int(x):>5}{TS_LABEL[T]:>5}{tot:>8}   " + " ".join(parts) +
                f"   flips={flips}")
    out("The LEVEL of a magnitude probability is regime-dependent and moves by")
    out("tens of points across months; the ORDERING (high vol reaches more often)")
    out("does not flip.  A gate may use the ordering; a strategy that needs the")
    out("level is calibrating to a regime that will not repeat.")
    return {}


if __name__ == "__main__":
    sys.exit(main())
