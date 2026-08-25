#!/usr/bin/env python3
"""
BURST MECHANISM ATLAS -- bitFlyer self-triggered bursts, drift map.

EXPLORATION ONLY -- NO ADOPTION DECISION MAY BE TAKEN FROM THIS OUTPUT.
AT MOST TWO CELLS MAY BE PROPOSED AS FUTURE PRE-REGISTRATION CANDIDATES,
AND FREEZING/REGISTERING THEM IS THE LEAD'S ACT, NOT THIS SCRIPT'S.

TASK SUMMARY (from the lead, frozen before the first run)
    Map the whole SURFACE of the bitFlyer self-triggered burst mechanism on
    the mined tape, not two points on it.  S9 (30-min extreme touch,
    +6.81bps@30m < 7.92bps round-trip taker) and S10 (2s/20bps avalanche,
    +7.09bps@120s < 7.92bps) are two points; fill in what lies between and
    outside them, and say in mechanism terms WHERE THE EDGE LIVES AND WHERE
    IT DIES.  Drift maps are the primary product; strategy simulation is
    secondary.  Negative results stay negative.  The report must state the
    WIDTH OF THE SURFACE (total number of cells examined) and must separate
    MECHANISM-LEVEL death (arithmetic no parameter can beat) from
    POINT-LEVEL death (the cells examined died), per research-protocol §10.

PRE-REGISTRATION (verbatim; nothing below is changed after the first run)

    [DATA]
    - backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz
      (columns id, exec_date, price, size, side; `side` is the TAKER side).
      ONLY rows with exec_date < 2026-08-20T08:22:17Z are used.  Rows at or
      after that instant are FRESH territory and are never read.
    - No other data source.  No network access.  Read-only, idempotent,
      seed 20260825.
    - THIS TAPE IS MINED (h, k, u, v, x all used it).  Every number produced
      here is a FEASIBILITY BOUNDARY, not evidence for adoption.

    [PRICE SERIES]
    - Bounce-free mid proxy, repo convention (S7 / research_two_sided_flow):
      mid = 0.5*(last taker-BUY print price + last taker-SELL print price),
      each forward-filled.  Projected onto a 1-second grid (last print of the
      second wins, then forward-filled -- no look-ahead).  m[i] denotes the
      grid mid of second i, which is knowable only at the END of second i,
      so the instant a signal built from m[i] exists is t_sig = g0 + i + 1.

    [1. TRIGGER SURFACE -- 36 CELLS, ENUMERATED, NOTHING ADDED]
    - W in {2, 10, 30, 60, 300, 1800} seconds
    - thr in {5, 10, 15, 20, 30, 50} bps
    - r_W[i] = 1e4 * (m[i] - m[i-W]) / m[i-W]   (net displacement = bounce
      free by construction: an up-then-down round trip cancels)
    - fire when |r_W[i]| >= thr; side = sign(r_W[i])
    - same-direction re-fire cooldown = max(W, 60) seconds
    - The firings-per-day table is produced FIRST.  Any cell with n < 20 is
      labelled REFERENCE ONLY in every table that follows.

    [2. DRIFT SURFACE (PRE-COST) -- delays x horizons]
    - delay d in {0, 1, 5, 30, 120} seconds; reference index j = i + 1 + d
    - horizon h in {5, 30, 120, 600, 1800, 7200} seconds
    - signed forward move (positive = the trigger's own direction):
      drift = side * 1e4 * (m[j+h] - m[j]) / m[j]
    - mean, median, n for every (W, thr, d, h) = 36 x 5 x 6 = 1080 combos.
    - Day-cluster bootstrap 95% CI (UTC day of the reference instant,
      2000 resamples, seed 20260825) for every combo with n >= 30.
    - A trigger is dropped from a combo if j+h falls outside the grid
      (dropped counts reported).  n therefore varies mildly with d+h.

    [3. COST LINE OVERLAY]
    - taker one-way 3.96 bps, round trip 7.92 bps (KNOWLEDGE §1, burst).
    - EXHAUSTIVELY enumerate every (W, thr, d, h) whose mean drift is
      > +7.92 (TREND region beatable by a taker round trip),
      > +3.96 (beatable only by a one-way-taker hybrid),
      < -7.92 and < -3.96 (REVERSAL region: overshoot given back; a fade
      entered at delay d would beat the same cost lines).
    - Both regions are searched.  The reversal search is the generalisation
      of S10's "the avalanche gives it back within 120 s".

    [4. MAKER REALISATION OF THE REVERSAL REGION]
    - Frozen selection rule: among (W, thr, d) triples with n >= 30, rank by
      min over h of the mean drift (most negative first); take the TOP 3.
    - Fade limit at t_ref = t_sig + d.  After an UP trigger we fade by
      SELLING: L = most recent taker-BUY print price at or before t_ref (ask
      proxy).  After a DOWN trigger we fade by BUYING: L = most recent
      taker-SELL print price at or before t_ref (bid proxy).  (S11 flavour.)
    - Fill rule = the repo's print-level traded-through conservative rule,
      strictly on prints AFTER t_ref: a resting SELL at L fills on a print
      with taker side BUY and price >= L; a resting BUY at L fills on a print
      with taker side SELL and price <= L.
    - Fill window F = 60 seconds (frozen, not swept).
    - For the FILLED group only: signed forward move IN THE FADE DIRECTION
      from the fill price, at 30 / 120 / 600 / 1800 s after the fill, on the
      bounce-free mid grid.  Gross (maker entry = 0 bps) and net with a taker
      exit (3.96 bps) are both printed.
    - Adverse-selection counterfactual (protocol §3, MANDATORY): the same
      forward move for the MISSED group measured from t_ref, i.e. "what the
      signals we failed to fill would have done".
    - Rationale (S11's lesson): the unconditional drift is NOT the fill
      group's drift.  Speed and certainty of fill IS the strength of adverse
      selection.

    [5. CLOCK-WINDOW CROSSING]
    - For the top cells, split on whether t_sig lies in 12:30-15:00 UTC
      (report h: the only surviving storm precursor) and report in/out.

    [6. MECHANISM WRITE-UP]
    - Edge lifetime vs window, overshoot depth vs threshold, whether any
      region clears the cost line and at what frequency.  Check that the
      known points of reports e, 21 (v) and 23 (x) sit consistently on the
      surface.

    [DISCIPLINE]
    - Report the width of the surface (cell count).  Multiple comparisons
      WILL manufacture positive cells: any top cell must be killed by
      neighbour-cell plateau inspection and day-cluster CI before it may be
      offered as a future candidate (max 2, lead freezes).
    - Negative stays negative.  Rejection level (mechanism vs point) written
      per protocol §10.
    - Sanity: zero look-ahead, epoch cross-check (EPOCH division;
      `.astype("int64")` FORBIDDEN), determinism (two identical runs),
      order-of-magnitude plausibility of firing counts.

Usage:  PYTHONPATH=src python scripts/research_burst_atlas.py
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE = os.path.join(ROOT, "backtest_data",
                    "executions_FX_BTC_JPY_31d_20260823.csv.gz")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
FRESH_CUTOFF_ISO = "2026-08-20T08:22:17Z"

# --- pre-registered surface -------------------------------------------------
WINDOWS_S = (2, 10, 30, 60, 300, 1800)
THRS_BPS = (5.0, 10.0, 15.0, 20.0, 30.0, 50.0)
DELAYS_S = (0, 1, 5, 30, 120)
HORIZONS_S = (5, 30, 120, 600, 1800, 7200)

MIN_COOLDOWN_S = 60
N_REFERENCE_ONLY = 20        # cells below this n are "reference only"
N_CI = 30                    # cells at/above this n get a day-cluster CI

TAKER_ONE_WAY = 3.96
TAKER_ROUND = 7.92

FILL_WINDOW_S = 60.0
FADE_HORIZONS_S = (30, 120, 600, 1800)
TOP_TRIPLES = 3

CLOCK_LO_S = 12 * 3600 + 30 * 60      # 12:30 UTC
CLOCK_HI_S = 15 * 3600                # 15:00 UTC

BOOT_ITERS = 2000
SEED = 20260825


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def line(char: str = "-", n: int = 110) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


def sub(title: str) -> None:
    print()
    print("--- " + title + " " + "-" * max(0, 106 - len(title)))


def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return np.array([x.timestamp() for x in idx], dtype=float)


def iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").isoformat()


def ffill(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def day_cluster_ci(vals: np.ndarray, days: np.ndarray,
                   rng: np.random.Generator) -> tuple[float, float, float]:
    """(t_stat, lo95, hi95) from a bootstrap over whole UTC days."""
    uniq = np.unique(days)
    if len(uniq) < 2 or len(vals) < 2:
        return float("nan"), float("nan"), float("nan")
    groups = [vals[days == d] for d in uniq]
    k = len(groups)
    means = np.empty(BOOT_ITERS)
    for b in range(BOOT_ITERS):
        pick = rng.integers(0, k, k)
        means[b] = np.concatenate([groups[p] for p in pick]).mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    sd = means.std(ddof=1)
    tstat = float(vals.mean() / sd) if sd > 0 else float("nan")
    return tstat, float(lo), float(hi)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load() -> dict:
    cutoff = float((pd.Timestamp(FRESH_CUTOFF_ISO) - EPOCH) / pd.Timedelta("1s"))
    ex = pd.read_csv(TAPE)
    t = epoch_seconds(ex["exec_date"])
    t_alt = epoch_seconds_alt(ex["exec_date"])
    dev = float(np.max(np.abs(t - t_alt)))
    print(f"epoch cross-check      : max |impl_a - impl_b| = {dev:.9f} s (must be ~0)")
    print(f"first row              : {ex['exec_date'].iloc[0]} -> {t[0]:.3f} s "
          f"-> {iso(t[0])}")
    if dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")

    order = np.argsort(t, kind="mergesort")
    t = t[order]
    price = ex["price"].to_numpy(float)[order]
    buy = (ex["side"].to_numpy() == "BUY")[order]

    n_all = len(t)
    keep = t < cutoff
    t, price, buy = t[keep], price[keep], buy[keep]
    print(f"fresh-territory filter : cutoff {FRESH_CUTOFF_ISO} = {cutoff:.0f} s; "
          f"kept {int(keep.sum()):,} / {n_all:,} prints, "
          f"dropped {n_all - int(keep.sum()):,} (never read again)")
    print(f"tape span used         : {iso(t[0])} .. {iso(t[-1])} "
          f"({(t[-1] - t[0]) / 86400.0:.2f} days)")
    assert t[-1] < cutoff

    # bounce-free mid proxy at print level
    lb = ffill(np.where(buy, price, np.nan))     # ask proxy
    ls = ffill(np.where(~buy, price, np.nan))    # bid proxy
    mid = 0.5 * (lb + ls)

    # 1-second grid
    g0 = int(np.floor(t[0]))
    g1 = int(np.floor(t[-1]))
    n = g1 - g0 + 1
    gm = np.full(n, np.nan)
    si = np.floor(t).astype(np.int64) - g0
    gm[si] = mid                                  # last print of the second wins
    gm = ffill(gm)
    valid_from = int(np.argmax(~np.isnan(gm)))
    print(f"1s grid                : {n:,} seconds, g0={g0} ({iso(float(g0))}), "
          f"first non-nan index {valid_from}")
    # gap diagnostics (seconds with no print at all)
    has_print = np.zeros(n, bool)
    has_print[si] = True
    runs = np.diff(np.flatnonzero(np.r_[True, np.diff(has_print.astype(int)) != 0,
                                        True]))
    print(f"grid coverage          : {has_print.mean()*100:.1f}% of seconds carry "
          f"a print; longest print-free run = "
          f"{int(runs.max()) if len(runs) else 0} s")
    print(f"print density          : {len(t)/((t[-1]-t[0])/86400.0):,.0f} prints/day")

    return {"t": t, "price": price, "buy": buy, "lb": lb, "ls": ls,
            "g0": g0, "gm": gm, "n": n, "valid_from": valid_from,
            "days": (t[-1] - t[0]) / 86400.0, "cutoff": cutoff}


# --------------------------------------------------------------------------
# trigger surface
# --------------------------------------------------------------------------
def build_triggers(D: dict, W: int, thr: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (grid indices i, sides) of firings for one (W, thr) cell."""
    gm, n, vf = D["gm"], D["n"], D["valid_from"]
    r = np.full(n, np.nan)
    r[W:] = (gm[W:] - gm[:-W]) / gm[:-W] * 1e4
    ok = np.zeros(n, bool)
    ok[max(W, vf + W):] = True          # both ends of the window must be defined
    fire = ok & (np.abs(r) >= thr)
    idx_all = np.flatnonzero(fire)

    cd = float(max(W, MIN_COOLDOWN_S))
    last = {1: -np.inf, -1: -np.inf}
    keep_i, keep_s = [], []
    n_cd = 0
    for i in idx_all:
        s = 1 if r[i] > 0 else -1
        ti = float(i)
        if ti - last[s] < cd:
            n_cd += 1
            continue
        last[s] = ti
        keep_i.append(i)
        keep_s.append(s)
    stats = {"raw": int(len(idx_all)), "cooldown_dropped": n_cd,
             "kept": len(keep_i), "cooldown_s": cd}
    return (np.asarray(keep_i, dtype=np.int64),
            np.asarray(keep_s, dtype=np.int64), stats)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    rng_master = np.random.default_rng(SEED)
    header("BURST MECHANISM ATLAS -- EXPLORATION ONLY (no adoption decision)")
    print("data  : backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz "
          f"(exec_date < {FRESH_CUTOFF_ISO})")
    print(f"seed  : {SEED};  cost lines: taker one-way {TAKER_ONE_WAY} bps, "
          f"round trip {TAKER_ROUND} bps")
    print(f"surface: W{list(WINDOWS_S)} x thr{list(THRS_BPS)} = "
          f"{len(WINDOWS_S)*len(THRS_BPS)} trigger cells; "
          f"x d{list(DELAYS_S)} x h{list(HORIZONS_S)} = "
          f"{len(WINDOWS_S)*len(THRS_BPS)*len(DELAYS_S)*len(HORIZONS_S)} "
          f"drift combos")
    line()

    D = load()
    gm, g0, n_grid = D["gm"], D["g0"], D["n"]
    days_span = D["days"]

    # ---------------- 1. trigger surface ---------------------------------
    header("1. TRIGGER SURFACE -- firings and firings/day")
    trig: dict[tuple[int, float], tuple[np.ndarray, np.ndarray]] = {}
    tstat: dict[tuple[int, float], dict] = {}
    print(f"{'W':>6} | " + " | ".join(f"thr{int(x):>2}" for x in THRS_BPS))
    line()
    for W in WINDOWS_S:
        cells = []
        for thr in THRS_BPS:
            i, s, st = build_triggers(D, W, thr)
            trig[(W, thr)] = (i, s)
            tstat[(W, thr)] = st
            cells.append(f"{len(i):>5}")
        print(f"{W:>6} | " + " | ".join(cells) + "   (raw firings, after cooldown)")
    line()
    print(f"{'W':>6} | " + " | ".join(f"thr{int(x):>2}" for x in THRS_BPS))
    line()
    for W in WINDOWS_S:
        cells = []
        for thr in THRS_BPS:
            i, _ = trig[(W, thr)]
            cells.append(f"{len(i)/days_span:>5.2f}")
        print(f"{W:>6} | " + " | ".join(cells) + "   (per day)")
    line()
    n_ref_only = sum(1 for k in trig if len(trig[k][0]) < N_REFERENCE_ONLY)
    print(f"cells with n < {N_REFERENCE_ONLY} (REFERENCE ONLY hereafter): "
          f"{n_ref_only} / {len(trig)}")
    print("cooldown per cell = max(W, 60) s, applied per direction.")
    sub("cooldown accounting (raw |r_W|>=thr seconds -> kept firings)")
    for W in WINDOWS_S:
        row = []
        for thr in THRS_BPS:
            st = tstat[(W, thr)]
            row.append(f"{st['raw']:>7}->{st['kept']:<5}")
        print(f"W={W:>5}: " + " ".join(row))
    sub("direction balance (up-fires share)")
    for W in WINDOWS_S:
        row = []
        for thr in THRS_BPS:
            _, s = trig[(W, thr)]
            row.append(f"{(s > 0).mean()*100:>5.1f}%" if len(s) else "   -- ")
        print(f"W={W:>5}: " + " ".join(row))

    # ---------------- 2. drift surface -----------------------------------
    header("2. DRIFT SURFACE (PRE-COST) -- signed forward move, trigger direction = +")
    print("positive = the burst continues (TREND);  negative = it is given back "
          "(REVERSAL)")
    print("values are bps.  n varies mildly with d+h (triggers whose horizon "
          "leaves the grid are dropped).")

    surface: dict[tuple, dict] = {}
    for W in WINDOWS_S:
        for thr in THRS_BPS:
            i_arr, s_arr = trig[(W, thr)]
            for d in DELAYS_S:
                j = i_arr + 1 + d
                for h in HORIZONS_S:
                    end = j + h
                    ok = (end < n_grid) & (j < n_grid)
                    if not ok.any():
                        surface[(W, thr, d, h)] = {
                            "n": 0, "mean": float("nan"),
                            "med": float("nan"), "vals": np.array([]),
                            "days": np.array([]), "sides": np.array([]),
                            "tsig": np.array([])}
                        continue
                    jj, ee, ss = j[ok], end[ok], s_arr[ok]
                    m0 = gm[jj]
                    m1 = gm[ee]
                    good = np.isfinite(m0) & np.isfinite(m1) & (m0 > 0)
                    jj, ee, ss, m0, m1 = jj[good], ee[good], ss[good], m0[good], m1[good]
                    vals = ss * (m1 - m0) / m0 * 1e4
                    dd = np.floor((g0 + jj) / 86400.0).astype(np.int64)
                    tsig = (g0 + i_arr[ok][good] + 1).astype(np.float64)
                    surface[(W, thr, d, h)] = {
                        "n": len(vals), "mean": float(vals.mean()) if len(vals) else float("nan"),
                        "med": float(np.median(vals)) if len(vals) else float("nan"),
                        "vals": vals, "days": dd, "sides": ss, "tsig": tsig}

    for W in WINDOWS_S:
        sub(f"W = {W}s   (rows: thr x delay;  columns: horizon)")
        print(f"{'thr':>4} {'d':>4} {'n':>7} | " +
              " | ".join(f"h={h:<6}" for h in HORIZONS_S))
        for thr in THRS_BPS:
            for d in DELAYS_S:
                cells = []
                nn = surface[(W, thr, d, HORIZONS_S[0])]["n"]
                for h in HORIZONS_S:
                    r = surface[(W, thr, d, h)]
                    cells.append(f"{r['mean']:>+8.2f}" if r["n"] else "      --")
                flag = "  *ref-only" if len(trig[(W, thr)][0]) < N_REFERENCE_ONLY else ""
                print(f"{int(thr):>4} {d:>4} {nn:>7} | " +
                      " | ".join(cells) + flag)
        # medians for the same block
        print(f"{'thr':>4} {'d':>4} {'n':>7} | " +
              " | ".join(f"h={h:<6}" for h in HORIZONS_S) + "   [MEDIANS]")
        for thr in THRS_BPS:
            for d in DELAYS_S:
                cells = []
                nn = surface[(W, thr, d, HORIZONS_S[0])]["n"]
                for h in HORIZONS_S:
                    r = surface[(W, thr, d, h)]
                    cells.append(f"{r['med']:>+8.2f}" if r["n"] else "      --")
                print(f"{int(thr):>4} {d:>4} {nn:>7} | " + " | ".join(cells))

    # ---------------- 3. cost line overlay --------------------------------
    header("3. COST LINE OVERLAY -- exhaustive enumeration of cells above/below the lines")
    trend_rt, trend_ow, rev_rt, rev_ow = [], [], [], []
    for key, r in surface.items():
        if r["n"] < N_REFERENCE_ONLY:
            continue
        m = r["mean"]
        if not np.isfinite(m):
            continue
        if m > TAKER_ROUND:
            trend_rt.append((key, r))
        elif m > TAKER_ONE_WAY:
            trend_ow.append((key, r))
        if m < -TAKER_ROUND:
            rev_rt.append((key, r))
        elif m < -TAKER_ONE_WAY:
            rev_ow.append((key, r))

    n_eval = sum(1 for k, r in surface.items() if r["n"] >= N_REFERENCE_ONLY)
    print(f"cells evaluated (n >= {N_REFERENCE_ONLY}): {n_eval} of {len(surface)}")

    rng = np.random.default_rng(SEED)

    def show(title: str, rows: list, sign: int) -> None:
        sub(title + f"   [{len(rows)} cells]")
        if not rows:
            print("   (empty)")
            return
        print(f"{'W':>6} {'thr':>4} {'d':>4} {'h':>6} {'n':>7} {'mean':>9} "
              f"{'median':>9} {'t':>7} {'CI95':>22} {'/day':>7}")
        rows = sorted(rows, key=lambda kv: -sign * kv[1]["mean"])
        for key, r in rows:
            W, thr, d, h = key
            if r["n"] >= N_CI:
                tst, lo, hi = day_cluster_ci(r["vals"], r["days"], rng)
                ci = f"[{lo:+7.2f},{hi:+7.2f}]"
            else:
                tst, ci = float("nan"), "        (n<30)       "
            print(f"{W:>6} {int(thr):>4} {d:>4} {h:>6} {r['n']:>7} "
                  f"{r['mean']:>+9.2f} {r['med']:>+9.2f} {tst:>+7.2f} {ci:>22} "
                  f"{r['n']/days_span:>7.2f}")

    show("TREND region above the ROUND-TRIP taker line (+7.92 bps)", trend_rt, +1)
    show("TREND region above the ONE-WAY taker line only (+3.96 .. +7.92 bps)",
         trend_ow, +1)
    show("REVERSAL region below the ROUND-TRIP taker line (-7.92 bps)", rev_rt, -1)
    show("REVERSAL region below the ONE-WAY taker line only (-3.96 .. -7.92 bps)",
         rev_ow, -1)

    # ---------------- 4. maker realisation of the reversal region ---------
    header("4. MAKER REALISATION OF THE REVERSAL REGION")
    print("frozen selection rule: among (W,thr,d) triples with n >= 30, rank by "
          "min over h of mean drift")
    print(f"(most negative first); take the top {TOP_TRIPLES}.")
    triples: dict[tuple, float] = {}
    for (W, thr, d, h), r in surface.items():
        if r["n"] < N_CI:
            continue
        m = r["mean"]
        if not np.isfinite(m):
            continue
        k = (W, thr, d)
        triples[k] = min(triples.get(k, np.inf), m)
    ranked = sorted(triples.items(), key=lambda kv: kv[1])
    print(f"triples eligible: {len(ranked)}")
    sub("ranking (top 12 shown)")
    for k, v in ranked[:12]:
        print(f"   W={k[0]:>5} thr={int(k[1]):>3} d={k[2]:>4}   min_h mean drift "
              f"= {v:+8.2f} bps")
    chosen = [k for k, _ in ranked[:TOP_TRIPLES]]

    t_p, p_p, buy_p, lb_p, ls_p = D["t"], D["price"], D["buy"], D["lb"], D["ls"]

    def maker_fade(W: int, thr: float, d: int) -> None:
        i_arr, s_arr = trig[(W, thr)]
        t_ref = (g0 + i_arr + 1 + d).astype(np.float64)
        filled_t, filled_p, filled_s, filled_ref = [], [], [], []
        missed_t, missed_s = [], []
        for tr, sd in zip(t_ref, s_arr):
            k0 = int(np.searchsorted(t_p, tr, side="right")) - 1
            if k0 < 0:
                continue
            # fade side: after an UP trigger we SELL, after a DOWN we BUY
            fade = -sd
            L = ls_p[k0] if fade > 0 else lb_p[k0]
            if not np.isfinite(L):
                continue
            k1 = int(np.searchsorted(t_p, tr, side="right"))
            k2 = int(np.searchsorted(t_p, tr + FILL_WINDOW_S, side="right"))
            hit = -1
            for k in range(k1, k2):
                if fade > 0:                       # resting BUY at bid proxy
                    if (not buy_p[k]) and p_p[k] <= L:
                        hit = k
                        break
                else:                              # resting SELL at ask proxy
                    if buy_p[k] and p_p[k] >= L:
                        hit = k
                        break
            if hit >= 0:
                filled_t.append(t_p[hit])
                filled_p.append(L)
                filled_s.append(fade)
                filled_ref.append(tr)
            else:
                missed_t.append(tr)
                missed_s.append(fade)
        nf, nm = len(filled_t), len(missed_t)
        tot = nf + nm
        sub(f"W={W}s thr={int(thr)}bps d={d}s   fade limit, "
            f"fill window {FILL_WINDOW_S:.0f}s")
        if tot == 0:
            print("   no usable triggers")
            return
        print(f"   triggers {tot}  filled {nf} ({nf/tot*100:.1f}%)  "
              f"missed {nm} ({nm/tot*100:.1f}%)")
        if nf:
            lat = np.asarray(filled_t, float) - np.asarray(filled_ref, float)
            print(f"   fill latency (s)     : median {np.median(lat):.2f}  "
                  f"mean {lat.mean():.2f}  p90 {np.percentile(lat, 90):.2f}")

        # forward move of the FILLED group, in the fade direction
        def fwd(times, prices, sides, label, ref_is_price: bool) -> None:
            times = np.asarray(times, float)
            sides = np.asarray(sides, float)
            if len(times) == 0:
                print(f"   {label:<28} n=0")
                return
            gi = np.floor(times).astype(np.int64) - g0
            base = (np.asarray(prices, float) if ref_is_price
                    else gm[np.clip(gi, 0, n_grid - 1)])
            out = []
            for h in FADE_HORIZONS_S:
                e = gi + h
                ok = (e < n_grid) & (gi >= 0)
                if not ok.any():
                    out.append("     --")
                    continue
                v = sides[ok] * (gm[e[ok]] - base[ok]) / base[ok] * 1e4
                out.append(f"{v.mean():>+7.2f}")
            print(f"   {label:<28} n={len(times):>5}  " +
                  "  ".join(f"h={h}s {o}" for h, o in zip(FADE_HORIZONS_S, out)))

        print("   signed forward move in the FADE direction (bps, gross; "
              "maker entry = 0 bps):")
        fwd(filled_t, filled_p, filled_s, "FILLED (from fill price)", True)
        fwd(missed_t, None, missed_s, "MISSED (from t_ref mid)", False)
        print(f"   net for the filled group = gross - {TAKER_ONE_WAY} bps "
              f"(taker exit); maker exit would be 0.")

    for (W, thr, d) in chosen:
        maker_fade(W, thr, d)

    # ---------------- 5. clock window crossing ----------------------------
    header("5. CLOCK-WINDOW CROSSING (12:30-15:00 UTC, report h)")
    print("split on t_sig.  in-window duty of the day = "
          f"{(CLOCK_HI_S - CLOCK_LO_S)/86400*100:.1f}%")
    focus = sorted(
        [(k, r) for k, r in surface.items() if r["n"] >= N_CI],
        key=lambda kv: -abs(kv[1]["mean"]))[:15]
    print(f"{'W':>6} {'thr':>4} {'d':>4} {'h':>6} | {'n_in':>6} {'mean_in':>9} "
          f"| {'n_out':>7} {'mean_out':>9} | {'lift':>7}")
    for key, r in focus:
        W, thr, d, h = key
        tod = np.mod(r["tsig"], 86400.0)
        inw = (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)
        vi, vo = r["vals"][inw], r["vals"][~inw]
        mi = vi.mean() if len(vi) else float("nan")
        mo = vo.mean() if len(vo) else float("nan")
        lift = mi / mo if (len(vo) and mo != 0 and np.isfinite(mo)) else float("nan")
        print(f"{W:>6} {int(thr):>4} {d:>4} {h:>6} | {len(vi):>6} {mi:>+9.2f} "
              f"| {len(vo):>7} {mo:>+9.2f} | {lift:>+7.2f}")

    # ---------------- 6. plateau inspection --------------------------------
    header("6. PLATEAU INSPECTION of the extreme cells (neighbour W/thr, same d,h)")
    extremes = sorted(
        [(k, r) for k, r in surface.items() if r["n"] >= N_CI],
        key=lambda kv: -abs(kv[1]["mean"]))[:6]
    for key, r in extremes:
        W, thr, d, h = key
        sub(f"centre W={W} thr={int(thr)} d={d} h={h}  mean={r['mean']:+.2f} "
            f"n={r['n']}")
        wi, ti = WINDOWS_S.index(W), THRS_BPS.index(thr)
        for dw in (-1, 0, 1):
            row = []
            for dt in (-1, 0, 1):
                a, b = wi + dw, ti + dt
                if not (0 <= a < len(WINDOWS_S) and 0 <= b < len(THRS_BPS)):
                    row.append("      .   ")
                    continue
                rr = surface[(WINDOWS_S[a], THRS_BPS[b], d, h)]
                row.append(f"{rr['mean']:>+7.2f}/{rr['n']:<4}"
                           if rr["n"] else "     --   ")
            lbl = (f"W={WINDOWS_S[wi+dw]:>5}" if 0 <= wi + dw < len(WINDOWS_S)
                   else "  --  ")
            print(f"   {lbl}: " + " ".join(row))
        print("   (columns = thr one step down / centre / one step up)")

    # ---------------- 7. candidate stress test ------------------------------
    header("7. CANDIDATE STRESS TEST -- POST-HOC DIAGNOSTIC (MAY ONLY DEMOTE)")
    print("Added after reading sections 1-6.  It is a DIAGNOSTIC in the sense of")
    print("research-protocol §8.2: it can only kill a cell, never promote one, and")
    print("no cell may be adopted from it.  Focus set = the only cells whose day-")
    print("cluster CI excluded zero in section 3, plus their thr-neighbour.")
    focus_cells = [
        (60, 20.0, 0, 7200), (60, 20.0, 1, 7200), (60, 20.0, 5, 7200),
        (60, 20.0, 30, 7200), (60, 20.0, 0, 1800), (60, 20.0, 1, 1800),
        (30, 20.0, 0, 7200), (30, 20.0, 1, 7200),
        (60, 30.0, 0, 7200), (60, 30.0, 1, 7200), (60, 30.0, 0, 1800),
        (10, 20.0, 120, 600), (10, 20.0, 0, 600),
    ]
    print()
    print(f"{'W':>5} {'thr':>4} {'d':>4} {'h':>6} | {'n':>5} {'mean':>8} "
          f"{'net':>8} | {'n_fr':>5} {'mean_fr':>8} {'n_bk':>5} {'mean_bk':>8} "
          f"| {'n_no':>5} {'mean_no':>8} {'CI95_no':>20} | {'top1day%':>8} "
          f"{'in%':>6} {'mean_in':>8} {'mean_out':>9}")
    rng2 = np.random.default_rng(SEED)
    t_lo_all = float(g0)
    t_hi_all = float(g0 + n_grid)
    for key in focus_cells:
        r = surface.get(key)
        if r is None or r["n"] == 0:
            continue
        W, thr, d, h = key
        vals, days, tsig = r["vals"], r["days"], r["tsig"]
        mean = vals.mean()
        # front 60 / back 40 by time
        cut = t_lo_all + 0.60 * (t_hi_all - t_lo_all)
        fr, bk = tsig < cut, tsig >= cut
        # non-overlapping greedy subsample (no two forward windows overlap)
        keep = np.zeros(len(tsig), bool)
        last_end = -np.inf
        for q in np.argsort(tsig, kind="mergesort"):
            if tsig[q] >= last_end:
                keep[q] = True
                last_end = tsig[q] + h
        vno, dno = vals[keep], days[keep]
        if len(vno) >= 2 and len(np.unique(dno)) >= 2:
            _, lo, hi = day_cluster_ci(vno, dno, rng2)
            ci = f"[{lo:+7.2f},{hi:+7.2f}]"
        else:
            ci = "        --         "
        # per-day concentration
        uniq = np.unique(days)
        sums = np.array([vals[days == u].sum() for u in uniq])
        tot = vals.sum()
        top1 = (sums.max() / tot * 100.0) if tot > 0 else float("nan")
        tod = np.mod(tsig, 86400.0)
        inw = (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)
        mi = vals[inw].mean() if inw.any() else float("nan")
        mo = vals[~inw].mean() if (~inw).any() else float("nan")
        print(f"{W:>5} {int(thr):>4} {d:>4} {h:>6} | {r['n']:>5} {mean:>+8.2f} "
              f"{mean - TAKER_ROUND:>+8.2f} | {int(fr.sum()):>5} "
              f"{vals[fr].mean() if fr.any() else float('nan'):>+8.2f} "
              f"{int(bk.sum()):>5} "
              f"{vals[bk].mean() if bk.any() else float('nan'):>+8.2f} "
              f"| {len(vno):>5} "
              f"{vno.mean() if len(vno) else float('nan'):>+8.2f} {ci:>20} "
              f"| {top1:>8.1f} {inw.mean()*100:>6.1f} {mi:>+8.2f} {mo:>+9.2f}")
    print()
    print("net = mean - 7.92 (round-trip taker).  fr/bk = front 60% / back 40% of "
          "the span by t_sig.")
    print("no  = greedy non-overlapping subsample (no two h-windows overlap) -- the "
          "only sample a")
    print("      single-position bot could actually trade.  top1day% = share of the "
          "total signed sum")
    print("      contributed by the single largest UTC day.")

    sub("7b. clock-window x non-overlap (the only jointly-honest sample)")
    print(f"{'W':>5} {'thr':>4} {'d':>4} {'h':>6} | {'n_in_no':>7} {'mean':>8} "
          f"{'median':>8} {'net':>8} {'CI95':>22} {'top1day%':>9} {'days':>5} "
          f"{'/day':>6}")
    rng3 = np.random.default_rng(SEED)
    for key in focus_cells:
        r = surface.get(key)
        if r is None or r["n"] == 0:
            continue
        W, thr, d, h = key
        vals, days, tsig = r["vals"], r["days"], r["tsig"]
        tod = np.mod(tsig, 86400.0)
        inw = (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)
        vi, di, ti = vals[inw], days[inw], tsig[inw]
        keep = np.zeros(len(ti), bool)
        last_end = -np.inf
        for q in np.argsort(ti, kind="mergesort"):
            if ti[q] >= last_end:
                keep[q] = True
                last_end = ti[q] + h
        v, dd = vi[keep], di[keep]
        if len(v) < 2 or len(np.unique(dd)) < 2:
            print(f"{W:>5} {int(thr):>4} {d:>4} {h:>6} | {len(v):>7}  (too few)")
            continue
        _, lo, hi = day_cluster_ci(v, dd, rng3)
        uq = np.unique(dd)
        sums = np.array([v[dd == u].sum() for u in uq])
        tot = v.sum()
        top1 = (sums.max() / tot * 100.0) if tot > 0 else float("nan")
        print(f"{W:>5} {int(thr):>4} {d:>4} {h:>6} | {len(v):>7} {v.mean():>+8.2f} "
              f"{np.median(v):>+8.2f} {v.mean()-TAKER_ROUND:>+8.2f} "
              f"[{lo:+8.2f},{hi:+8.2f}] {top1:>9.1f} {len(uq):>5} "
              f"{len(v)/days_span:>6.2f}")
    print("   in-window = 12:30-15:00 UTC on t_sig; then the greedy non-overlap "
          "filter is applied.")

    sub("7c. plateau + half-split of the surviving region, IN THE HONEST SAMPLE")
    print("same treatment (clock window -> greedy non-overlap) applied across the "
          "whole neighbourhood.")
    print("A ridge that exists only at one (W,thr,h) is a fishing artifact; a real "
          "mechanism is a plateau.")

    def honest(W: int, thr: float, d: int, h: int):
        r = surface.get((W, thr, d, h))
        if r is None or r["n"] == 0:
            return None
        vals, days, tsig = r["vals"], r["days"], r["tsig"]
        tod = np.mod(tsig, 86400.0)
        inw = (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)
        vi, di, ti = vals[inw], days[inw], tsig[inw]
        keep = np.zeros(len(ti), bool)
        last_end = -np.inf
        for q in np.argsort(ti, kind="mergesort"):
            if ti[q] >= last_end:
                keep[q] = True
                last_end = ti[q] + h
        return vi[keep], di[keep], ti[keep]

    print()
    for h in (1800, 7200):
        print(f"   --- h = {h}s, d = 0 ---")
        print(f"   {'W':>6} | " + " | ".join(f"thr{int(x):>2}" for x in THRS_BPS))
        for W in WINDOWS_S:
            cells = []
            for thr in THRS_BPS:
                out = honest(W, thr, 0, h)
                if out is None or len(out[0]) < 5:
                    cells.append("    n<5 ")
                else:
                    cells.append(f"{out[0].mean():>+6.1f}/{len(out[0]):<2}")
            print(f"   {W:>6} | " + " | ".join(cells))
        print()

    print("   --- candidate profile: front 60% / back 40%, win rate, day list ---")
    rng4 = np.random.default_rng(SEED)
    for (W, thr, d, h) in ((60, 20.0, 0, 1800), (60, 20.0, 5, 1800),
                           (60, 20.0, 30, 1800), (60, 20.0, 0, 7200),
                           (30, 20.0, 0, 1800), (60, 15.0, 0, 1800),
                           (60, 30.0, 0, 1800), (300, 20.0, 0, 1800)):
        out = honest(W, thr, d, h)
        if out is None or len(out[0]) < 3:
            continue
        v, dd, ti = out
        cut = float(g0) + 0.60 * float(n_grid)
        fr, bk = ti < cut, ti >= cut
        _, lo, hi = day_cluster_ci(v, dd, rng4) if len(np.unique(dd)) >= 2 \
            else (0.0, float("nan"), float("nan"))
        print(f"   W={W:>5} thr={int(thr):>3} d={d:>4} h={h:>5} | n={len(v):>3} "
              f"mean{v.mean():>+7.2f} med{np.median(v):>+7.2f} "
              f"win{(v > 0).mean()*100:>5.1f}% | front n={int(fr.sum()):>3} "
              f"{v[fr].mean() if fr.any() else float('nan'):>+7.2f} | back "
              f"n={int(bk.sum()):>3} "
              f"{v[bk].mean() if bk.any() else float('nan'):>+7.2f} | "
              f"CI[{lo:+7.2f},{hi:+7.2f}]")

    sub("7d. side split + per-day ledger of the candidate (market-direction test)")
    print("If the edge lives on one side only it is the period's market direction, "
          "not a burst mechanism.")

    def honest_full(W: int, thr: float, d: int, h: int):
        """Same as honest() but also returns the trigger sides."""
        i_arr, s_arr = trig[(W, thr)]
        j = i_arr + 1 + d
        end = j + h
        ok = (end < n_grid) & (j < n_grid)
        jj, ee, ss, ii = j[ok], end[ok], s_arr[ok], i_arr[ok]
        m0, m1 = gm[jj], gm[ee]
        good = np.isfinite(m0) & np.isfinite(m1) & (m0 > 0)
        jj, ee, ss, ii, m0, m1 = (jj[good], ee[good], ss[good], ii[good],
                                  m0[good], m1[good])
        vals = ss * (m1 - m0) / m0 * 1e4
        tsig = (g0 + ii + 1).astype(np.float64)
        tod = np.mod(tsig, 86400.0)
        inw = (tod >= CLOCK_LO_S) & (tod < CLOCK_HI_S)
        v2, s2, t2 = vals[inw], ss[inw], tsig[inw]
        keep = np.zeros(len(t2), bool)
        last_end = -np.inf
        for q in np.argsort(t2, kind="mergesort"):
            if t2[q] >= last_end:
                keep[q] = True
                last_end = t2[q] + h
        return v2[keep], s2[keep], t2[keep]

    for (W, thr, d, h) in ((60, 20.0, 0, 1800), (60, 20.0, 0, 7200),
                           (30, 20.0, 0, 1800), (300, 20.0, 0, 1800),
                           (60, 30.0, 0, 1800)):
        v, s, t = honest_full(W, thr, d, h)
        up, dn = s > 0, s < 0
        print(f"   W={W:>5} thr={int(thr):>3} h={h:>5} | n={len(v):>3} "
              f"all {v.mean():>+7.2f} | UP n={int(up.sum()):>3} "
              f"{v[up].mean() if up.any() else float('nan'):>+7.2f} "
              f"med{np.median(v[up]) if up.any() else float('nan'):>+7.2f} | "
              f"DOWN n={int(dn.sum()):>3} "
              f"{v[dn].mean() if dn.any() else float('nan'):>+7.2f} "
              f"med{np.median(v[dn]) if dn.any() else float('nan'):>+7.2f}")
    print()
    print("   per-day ledger, candidate W=60 thr=20 d=0 h=1800 (clock window, "
          "non-overlap):")
    v, s, t = honest_full(60, 20.0, 0, 1800)
    dkeys = np.floor(t / 86400.0).astype(np.int64)
    for u in np.unique(dkeys):
        sel = dkeys == u
        dt = pd.Timestamp(float(u) * 86400.0, unit="s", tz="UTC").date()
        print(f"     {dt}  n={int(sel.sum()):>2}  sum{v[sel].sum():>+9.2f}  "
              f"mean{v[sel].mean():>+8.2f}  [" +
              " ".join(f"{x:+.0f}" for x in v[sel]) + "]")
    print(f"   total sum {v.sum():+.2f} bps over {len(np.unique(dkeys))} days, "
          f"n={len(v)}")
    pos_days = sum(1 for u in np.unique(dkeys) if v[dkeys == u].sum() > 0)
    print(f"   days with a positive sum: {pos_days} / {len(np.unique(dkeys))}")

    # ---------------- sanity ------------------------------------------------
    header("SANITY")
    print("look-ahead: r_W[i] uses grid mids at i-W..i only; the signal instant is "
          "g0+i+1 (end of second i);")
    print("            every reference index is i+1+d >= i+1 and every horizon end "
          "is j+h > j.  Nothing")
    print("            measured is inside the window that defined the trigger for "
          "d >= 0 by construction")
    print("            of the +1 offset; for W > d the trigger window and the "
          "forward window still do")
    print("            not overlap because the forward window starts strictly "
          "after the trigger window's")
    print("            last second.")
    print(f"epoch     : EPOCH-division idiom only; '.astype(\"int64\")' on datetimes "
          f"is not used anywhere")
    print("            (the only int64 casts are on already-divided float second "
          "counts).")
    print(f"seed      : {SEED} (numpy default_rng), bootstrap {BOOT_ITERS} "
          f"resamples over UTC days")
    print("network   : none.  writes: none (stdout only).")
    tot_fires = sum(len(v[0]) for v in trig.values())
    print(f"firings   : {tot_fires:,} across {len(trig)} trigger cells over "
          f"{days_span:.2f} days")
    print(f"surface   : {len(surface)} (W,thr,d,h) drift combos; "
          f"{n_eval} with n >= {N_REFERENCE_ONLY}")

    # digest for determinism
    hsh = hashlib.sha256()
    for key in sorted(surface):
        r = surface[key]
        hsh.update(f"{key}|{r['n']}|{r['mean']:.9f}|{r['med']:.9f}".encode())
    print(f"digest    : surface sha256 = {hsh.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
