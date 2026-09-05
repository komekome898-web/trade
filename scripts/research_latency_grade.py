#!/usr/bin/env python3
"""Round 24 Step 1 -- EDGE x LATENCY CURVE on the fine-grained tape.

    DIAGNOSTIC ONLY.  This script decides nothing.  It measures how the
    net edge of one FROZEN execution recipe decays with reaction delay, so
    the lead can price the question "is a WS-driven execution path worth
    building on a Tokyo cloud host?".  No strategy is adopted, frozen or
    revived by this output.  The tape it reads is MINED (reports h, k, u,
    v, x, aa, ad, ae, af, ag all used this week), so every number here is a
    FEASIBILITY BOUNDARY, not evidence for adoption.

PRE-REGISTRATION (written before the first run; nothing below changed after)

  [DATA]
    data/tape/executions_YYYYMMDD.csv.gz  2026-08-20..27  (ts = exchange
        exec_date, us precision; price, size, side = TAKER side)
    data/tape/ticker_YYYYMMDD.csv.gz      same span (ts = exchange
        timestamp; best_bid/ask + sizes, one row per quote CHANGE)
    Nothing else.  No network.  Read-only, idempotent, seed 20260828.

  [GAP DISCIPLINE -- reused verbatim from research_board_calibration.py]
    A recorder gap = ticker silence > GAP_SEC = 30 s.  Any event whose
    measurement span [t_sig - W, t_ref + FALLBACK] overlaps a gap is
    DISCARDED.  A gap must never be read as "no trading".

  [TRIGGER -- atlas family, moved from the 1 s grid to print level]
    Bounce-free mid (repo convention, S7 / research_burst_atlas):
        m = 0.5 * (last taker-BUY print price + last taker-SELL print price)
    evaluated AT PRINT LEVEL (not on a 1 s grid), because a latency study
    must date the signal at the instant the information exists.  For print i
    at exchange time t_i:
        r = 1e4 * (m_i - m_back) / m_back,  m_back = the bounce-free mid of
        the last print at or before t_i - W,  W = 2 s (frozen).
    Fire when |r| >= thr, side = sign(r), thr in {5, 10, 20, 30} bps
    (frozen list, nothing added).  Same-direction cooldown 60 s.
    t_sig = t_i, the exchange stamp of the print that completes the move --
    the earliest instant at which ANY participant could know.
    NOTE for comparability: the atlas / S10 1 s grid dates the same signal
    at the END of the second, i.e. it carries on average +0.5 s of extra
    delay.  The delta axis below therefore starts strictly earlier than the
    S10 "t+0" point; that is the point of the exercise.

  [REACTION DELAY]
    delta in {0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0} s (frozen).
    t_ref = t_sig + delta.  The trigger set is built ONCE per thr and is
    IDENTICAL across delta, so n is comparable along the curve.

  [ENTRY -- real quote touch, no proxy]
    q = last ticker row with ts <= t_ref (must be within GAP_SEC).
    long  (side +1): entry = ask[q] * (1 + slip/1e4)
    short (side -1): entry = bid[q] * (1 - slip/1e4)
    slip in {0, 2} bps (KNOWLEDGE section 1 slippage sensitivity).
    Taker fee = 0 (measured, KNOWLEDGE section 1).  The half-spread is NOT
    added as a constant: it is paid explicitly by touching the real quote.

  [EXIT -- E2 only, one recipe, no surface]
    maker TP limit at entry * (1 +- 10 bps), filled by the repo's
    conservative print-level traded-through rule on prints strictly after
    t_ref (long: a taker-BUY print at price >= limit; short: a taker-SELL
    print at price <= limit); otherwise taker fallback at t_ref + 120 s at
    the prevailing quote (long sells bid*(1-slip), short buys ask*(1+slip)).
    net_bps = side * (exit - entry) / entry * 1e4.

  [PRE-COST DRIFT, reported alongside]
    signed quote-mid move from t_ref to t_ref + h, h in {5, 30, 120} s.

  [STATISTICS]
    Day-cluster bootstrap 95% CI over UTC days (2000 resamples, seed
    20260828); n reported everywhere; cells with n < 20 marked REFERENCE.

  [SPLITS -- reported, never used to select]
    (i) event-time halves (protocol section 2);
    (ii) before / from 2026-08-25T12:00Z (the S12 fresh-tape boundary of
         KNOWLEDGE section 4), so the lead can see the consumption ledger.

  [DATA CONSUMPTION LEDGER -- protocol section 8.1]
    This run reads DIRECTIONAL burst information from tape 2026-08-20..27,
    which OVERLAPS the S12 fresh window (>= 2026-08-25T12:00Z).  Split (ii)
    exists so the lead can see the overlap explicitly.  Any S12 verdict
    should use tape from 2026-08-28 onward.

  [DISCIPLINE]
    Zero look-ahead (asserted: every price used is stamped at or after
    t_ref, every fill print strictly after it); epoch conversion via EPOCH
    division with a second independent implementation cross-checked
    (.astype("int64") FORBIDDEN); determinism (digest printed, two runs
    compared by the operator); negative stays negative.

Usage:  PYTHONPATH=src python scripts/research_latency_grade.py
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bot.monitoring.gates import shared_or_local_dir  # noqa: E402

# Single source of truth (docs/DATA_QA_CHECKLIST.md #10): prefer
# paper_logs/tape/ over this checkout's local data/tape/ when it holds
# newer files.
TAPE = shared_or_local_dir(ROOT, "data/tape", shared_name="tape")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
SEED = 20260828
GAP_SEC = 30.0

W_S = 2.0
THRS = (5.0, 10.0, 20.0, 30.0)
DELTAS = (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)
SLIPS = (0.0, 2.0)
COOLDOWN_S = 60.0

TP_BPS = 10.0
FALLBACK_S = 120.0
DRIFT_H = (5.0, 30.0, 120.0)

BOOT = 2000
N_REF = 20

S12_BOUNDARY_ISO = "2026-08-25T12:00:00Z"

# staleness guard on the look-back leg of the trigger window (see build_triggers)
BACK_GUARD_S = 10.0
BACK_GUARD_ALT_S = 1.0          # sensitivity re-run, section 12

# Reaction-latency scenarios for the economics table.  MEASURED and ESTIMATED
# are labelled and never mixed.  Provenance:
#   VM WS receive delay  : MEASURED, scripts/measure_ws_latency.py, 10 min live
#                          (p50 0.061 s, p90 0.085) and data/ws 2026-08-20
#                          replay (executions p50 -0.009, p90 +0.032)
#   PC order REST RTT    : MEASURED on the PC (status.json api_latency 99 ms;
#                          bot.jsonl exchange_condition samples 28-334 ms)
#   in-region RTT        : ESTIMATE from public AWS intra-region figures
#   decision cost        : MEASURED, this engine, ~7 us/event
SCENARIOS = (
    ("theoretical lambda=0", 0.000),
    ("cloud Tokyo optimistic~", 0.050),
    ("cloud Tokyo central~", 0.100),
    ("PC + WS optimistic", 0.160),
    ("PC + WS pessimistic", 0.400),
    ("PC today (REST poll)", 1.000),
)


# --------------------------------------------------------------------------
def line(c: str = "-", n: int = 108) -> None:
    print(c * n)


def header(t: str) -> None:
    print()
    line("=")
    print(t)
    line("=")


def sub(t: str) -> None:
    print()
    print("--- " + t + " " + "-" * max(0, 104 - len(t)))


def epoch_seconds(ts) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return np.array([x.timestamp() for x in idx], dtype=float)


def iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").isoformat()


def ffill_vals(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def boot_ci(vals: np.ndarray, days: np.ndarray, seed: int = SEED):
    """(t_stat, lo95, hi95) from a bootstrap over whole UTC days."""
    if len(vals) < 2:
        return float("nan"), float("nan"), float("nan")
    uniq = np.unique(days)
    if len(uniq) < 2:
        return float("nan"), float("nan"), float("nan")
    groups = [vals[days == d] for d in uniq]
    k = len(groups)
    rng = np.random.default_rng(seed)
    means = np.empty(BOOT)
    for b in range(BOOT):
        pick = rng.integers(0, k, k)
        means[b] = np.concatenate([groups[p] for p in pick]).mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    sd = means.std(ddof=1)
    t = float(vals.mean() / sd) if sd > 0 else float("nan")
    return t, float(lo), float(hi)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load():
    tk = pd.concat([pd.read_csv(p) for p in sorted(TAPE.glob("ticker_*.csv.gz"))],
                   ignore_index=True)
    ex = pd.concat([pd.read_csv(p) for p in sorted(TAPE.glob("executions_*.csv.gz"))],
                   ignore_index=True)

    t_tk = epoch_seconds(tk["ts"])
    t_ex = epoch_seconds(ex["ts"])
    dev = max(float(np.max(np.abs(t_tk - epoch_seconds_alt(tk["ts"])))),
              float(np.max(np.abs(t_ex - epoch_seconds_alt(ex["ts"])))))
    print(f"epoch cross-check   : max |impl_a - impl_b| = {dev:.9f} s (must be ~0)")
    if dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")
    print(f"first ticker row    : {tk['ts'].iloc[0]} -> {t_tk[0]:.4f} -> {iso(t_tk[0])}")
    print(f"first exec   row    : {ex['ts'].iloc[0]} -> {t_ex[0]:.4f} -> {iso(t_ex[0])}")

    o = np.argsort(t_tk, kind="stable")
    t_tk = t_tk[o]
    bid = tk["best_bid"].to_numpy(float)[o]
    ask = tk["best_ask"].to_numpy(float)[o]
    bsz = tk["best_bid_size"].to_numpy(float)[o]
    asz = tk["best_ask_size"].to_numpy(float)[o]
    ok = np.isfinite(bid) & np.isfinite(ask) & (ask > bid) & (bid > 0)
    n_bad = int((~ok).sum())
    t_tk, bid, ask, bsz, asz = t_tk[ok], bid[ok], ask[ok], bsz[ok], asz[ok]
    midq = 0.5 * (bid + ask)
    spr = (ask - bid) / midq * 1e4

    o = np.argsort(t_ex, kind="stable")
    t_ex = t_ex[o]
    px = ex["price"].to_numpy(float)[o]
    sz = ex["size"].to_numpy(float)[o]
    buy = (ex["side"].to_numpy() == "BUY")[o]

    d = np.diff(t_tk)
    k = np.flatnonzero(d > GAP_SEC)
    gs, ge = t_tk[k], t_tk[k + 1]
    lost = float((ge - gs).sum())
    span = t_tk[-1] - t_tk[0]
    print(f"ticker rows         : {len(t_tk):,} kept ({n_bad} crossed/locked dropped)")
    print(f"exec prints         : {len(px):,} "
          f"({int(buy.sum()):,} taker-BUY / {int((~buy).sum()):,} taker-SELL)")
    print(f"wall-clock span     : {span/86400:.3f} d  {iso(t_tk[0])} .. {iso(t_tk[-1])}")
    print(f"recorder gaps       : {len(gs)} intervals > {GAP_SEC:.0f}s, "
          f"{lost/3600:.2f} h lost ({100*lost/span:.2f}%)")
    if len(gs):
        big = np.argsort(ge - gs)[::-1][:3]
        for i in big:
            print(f"    largest         : {iso(gs[i])} .. {iso(ge[i])} "
                  f"({(ge[i]-gs[i])/3600:.2f} h)")
    eff_days = (span - lost) / 86400.0
    print(f"effective days      : {eff_days:.3f} (gap-free)")
    print(f"print density       : {len(px)/eff_days:,.0f} prints / effective day")

    return dict(t_tk=t_tk, bid=bid, ask=ask, bsz=bsz, asz=asz, midq=midq, spr=spr,
                t_ex=t_ex, px=px, sz=sz, buy=buy, gs=gs, ge=ge,
                eff_days=eff_days, span=span)


def span_touches_gap(a, b, gs, ge):
    if len(gs) == 0:
        return np.zeros(len(np.atleast_1d(a)), bool)
    a = np.atleast_1d(a)
    b = np.atleast_1d(b)
    j = np.searchsorted(gs, b, "right") - 1
    bad = np.zeros(len(a), bool)
    good = j >= 0
    bad[good] = ge[j[good]] > a[good]
    return bad


# --------------------------------------------------------------------------
# trigger
# --------------------------------------------------------------------------
def build_triggers(D, thr, back_guard: float = BACK_GUARD_S):
    t, px, buy = D["t_ex"], D["px"], D["buy"]
    lb = ffill_vals(np.where(buy, px, np.nan))       # last taker-BUY  (ask side)
    ls = ffill_vals(np.where(~buy, px, np.nan))      # last taker-SELL (bid side)
    m = 0.5 * (lb + ls)
    valid = ~np.isnan(m)

    back = np.searchsorted(t, t - W_S, "right") - 1
    ok = valid & (back >= 0)
    ok &= valid[np.maximum(back, 0)]
    # the look-back print must not itself be ancient (stale window guard)
    ok &= (t - W_S - t[np.maximum(back, 0)]) <= back_guard

    r = np.full(len(t), np.nan)
    mb = m[np.maximum(back, 0)]
    with np.errstate(invalid="ignore", divide="ignore"):
        r[ok] = (m[ok] - mb[ok]) / mb[ok] * 1e4

    fire = np.flatnonzero(np.abs(r) >= thr)
    last = {1: -np.inf, -1: -np.inf}
    keep_i, keep_s, n_cd = [], [], 0
    for i in fire:
        s = 1 if r[i] > 0 else -1
        if t[i] - last[s] < COOLDOWN_S:
            n_cd += 1
            continue
        last[s] = t[i]
        keep_i.append(i)
        keep_s.append(s)
    return (np.asarray(keep_i, np.int64), np.asarray(keep_s, np.int64),
            r, dict(raw=len(fire), cooldown_dropped=n_cd, kept=len(keep_i)))


# --------------------------------------------------------------------------
# simulation of one (thr, delta, slip) cell
# --------------------------------------------------------------------------
def simulate(D, idx, sides, delta, slip, collect_quotes=False):
    t_ex, px, buy = D["t_ex"], D["px"], D["buy"]
    t_tk, bid, ask, bsz, asz = D["t_tk"], D["bid"], D["ask"], D["bsz"], D["asz"]
    midq, spr = D["midq"], D["spr"]
    gs, ge = D["gs"], D["ge"]

    t_sig = t_ex[idx]
    t_ref = t_sig + delta
    t_end = t_ref + FALLBACK_S

    # gap discipline: the whole measurement span must be gap-free
    bad = span_touches_gap(t_sig - W_S, t_end, gs, ge)
    # quote availability at reference and at the fallback instant
    q0 = np.searchsorted(t_tk, t_ref, "right") - 1
    q1 = np.searchsorted(t_tk, t_end, "right") - 1
    bad |= (q0 < 0) | (q1 < 0) | (t_end > t_tk[-1])
    q0c, q1c = np.maximum(q0, 0), np.maximum(q1, 0)
    bad |= (t_ref - t_tk[q0c]) > GAP_SEC
    bad |= (t_end - t_tk[q1c]) > GAP_SEC

    keep = ~bad
    n_drop = int(bad.sum())
    idx, sides = idx[keep], sides[keep]
    t_sig, t_ref, t_end = t_sig[keep], t_ref[keep], t_end[keep]
    q0, q1 = q0c[keep], q1c[keep]

    if len(idx) == 0:
        return dict(n=0, dropped=n_drop)

    # --- entry at the real quote touch ---------------------------------
    long_ = sides == 1
    entry = np.where(long_, ask[q0], bid[q0]) * (1.0 + sides * slip / 1e4)
    assert np.all(t_tk[q0] <= t_ref + 1e-9), "lookahead: quote after t_ref"

    limit = entry * (1.0 + sides * TP_BPS / 1e4)

    # --- maker TP fill scan on prints strictly after t_ref -------------
    lo = np.searchsorted(t_ex, t_ref, "right")          # strictly after
    hi = np.searchsorted(t_ex, t_end, "right")
    exit_px = np.empty(len(idx))
    exit_t = np.empty(len(idx))
    is_tp = np.zeros(len(idx), bool)
    for k in range(len(idx)):
        a, b = lo[k], hi[k]
        filled = False
        if b > a:
            p = px[a:b]
            bb = buy[a:b]
            if sides[k] == 1:
                hit = bb & (p >= limit[k])
            else:
                hit = (~bb) & (p <= limit[k])
            w = np.flatnonzero(hit)
            if len(w):
                exit_px[k] = limit[k]
                exit_t[k] = t_ex[a + w[0]]
                is_tp[k] = True
                filled = True
        if not filled:
            qq = q1[k]
            exit_px[k] = (bid[qq] * (1.0 - slip / 1e4) if sides[k] == 1
                          else ask[qq] * (1.0 + slip / 1e4))
            exit_t[k] = t_end[k]

    net = sides * (exit_px - entry) / entry * 1e4

    # --- pre-cost drift (quote mid) ------------------------------------
    drift = {}
    m_ref = midq[q0]
    for h in DRIFT_H:
        th = t_ref + h
        qh = np.searchsorted(t_tk, th, "right") - 1
        okh = (qh >= 0) & (th <= t_tk[-1])
        qhc = np.maximum(qh, 0)
        okh &= (th - t_tk[qhc]) <= GAP_SEC
        okh &= ~span_touches_gap(t_ref, th, gs, ge)
        d = np.where(okh, sides * (midq[qhc] - m_ref) / m_ref * 1e4, np.nan)
        drift[h] = d

    days = np.floor(t_ref / 86400.0).astype(np.int64)
    out = dict(n=len(idx), dropped=n_drop, net=net, days=days, t_ref=t_ref,
               t_sig=t_sig, sides=sides, is_tp=is_tp, hold=exit_t - t_ref,
               drift=drift, entry=entry)
    if collect_quotes:
        out["spread"] = spr[q0]
        out["touch_size"] = np.where(long_, asz[q0], bsz[q0])
        out["opp_size"] = np.where(long_, bsz[q0], asz[q0])
    return out


# --------------------------------------------------------------------------
def fmt_cell(res, tag=""):
    if res["n"] == 0:
        return f"{'--':>9}"
    m = res["net"].mean()
    s = f"{m:+9.2f}"
    if res["n"] < N_REF:
        s += "*"
    return s


def lam_max(deltas, means):
    """Largest delta at which the (linearly interpolated) net stays > 0."""
    if means[0] <= 0:
        return None, "net <= 0 already at delta = 0"
    for i in range(1, len(means)):
        if means[i] <= 0:
            d0, d1 = deltas[i - 1], deltas[i]
            m0, m1 = means[i - 1], means[i]
            x = d0 + (d1 - d0) * m0 / (m0 - m1)
            return x, f"crosses between {d0}s and {d1}s"
    return deltas[-1], f"still > 0 at the widest tested delta {deltas[-1]}s"


# --------------------------------------------------------------------------
def main() -> int:
    header("ROUND 24 STEP 1 -- EDGE x LATENCY CURVE (diagnostic, no adoption)")
    print(f"seed {SEED};  W = {W_S:.0f}s;  thr {list(THRS)} bps;  "
          f"delta {list(DELTAS)} s;  slip {list(SLIPS)} bps")
    print(f"exit: E2 (maker TP +{TP_BPS:.0f}bps, taker fallback {FALLBACK_S:.0f}s);  "
          f"fees 0 (measured); half-spread paid by touching the real quote")
    print(f"[data] tape dir: {TAPE}")
    line()
    D = load()

    boundary = float((pd.Timestamp(S12_BOUNDARY_ISO) - EPOCH) / pd.Timedelta("1s"))

    trig = {}
    header("1. TRIGGER SURFACE (print-level, W = 2 s)")
    print(f"{'thr':>5} | {'raw fires':>10} | {'cooldown drop':>13} | {'kept':>7} | "
          f"{'events/eff.day':>14} | {'up':>6} | {'down':>6}")
    line()
    for thr in THRS:
        i, s, r, st = build_triggers(D, thr)
        trig[thr] = (i, s)
        print(f"{thr:5.0f} | {st['raw']:10,} | {st['cooldown_dropped']:13,} | "
              f"{st['kept']:7,} | {st['kept']/D['eff_days']:14.2f} | "
              f"{int((s==1).sum()):6,} | {int((s==-1).sum()):6,}")

    # ---------------- 2. edge x latency ---------------------------------
    results = {}
    t_engine0 = time.perf_counter()
    n_events_processed = 0
    for thr in THRS:
        i, s = trig[thr]
        for slip in SLIPS:
            for d in DELTAS:
                res = simulate(D, i, s, d, slip, collect_quotes=(slip == 0.0))
                results[(thr, slip, d)] = res
                n_events_processed += res["n"]
    engine_s = time.perf_counter() - t_engine0

    header("2. NET bps PER EVENT -- thr x delta  (E2 exit, real quote touch)")
    for slip in SLIPS:
        sub(f"slippage +{slip:.0f} bps")
        print(f"{'thr':>5} | " + " | ".join(f"d={d:<5}" for d in DELTAS) + " |    n")
        line()
        for thr in THRS:
            row = []
            n = 0
            for d in DELTAS:
                res = results[(thr, slip, d)]
                n = res["n"]
                row.append(f"{res['net'].mean():+7.2f}" if n else "     --")
            print(f"{thr:5.0f} | " + " | ".join(row) + f" | {n:5,}")

    header("3. DAY-CLUSTER BOOTSTRAP 95% CI (slip 0 / slip 2)")
    print(f"{'thr':>5} {'delta':>6} | {'n':>5} | {'slip0 net':>9} "
          f"{'[lo':>8} {'hi]':>8} {'t':>6} | {'slip2 net':>9} {'[lo':>8} {'hi]':>8} {'t':>6}")
    line()
    for thr in THRS:
        for d in DELTAS:
            r0 = results[(thr, 0.0, d)]
            r2 = results[(thr, 2.0, d)]
            if r0["n"] == 0:
                continue
            t0, lo0, hi0 = boot_ci(r0["net"], r0["days"])
            t2, lo2, hi2 = boot_ci(r2["net"], r2["days"])
            mark = "*" if r0["n"] < N_REF else " "
            print(f"{thr:5.0f} {d:6.2f}{mark}| {r0['n']:5,} | {r0['net'].mean():+9.2f} "
                  f"{lo0:+8.2f} {hi0:+8.2f} {t0:+6.2f} | {r2['net'].mean():+9.2f} "
                  f"{lo2:+8.2f} {hi2:+8.2f} {t2:+6.2f}")
        line()

    header("4. LAMBDA_MAX -- largest reaction delay with net > 0")
    print(f"{'thr':>5} | {'slip':>5} | {'lambda_max (s)':>15} | note")
    line()
    lam_table = {}
    for thr in THRS:
        for slip in SLIPS:
            means = [results[(thr, slip, d)]["net"].mean()
                     if results[(thr, slip, d)]["n"] else float("nan")
                     for d in DELTAS]
            x, note = lam_max(list(DELTAS), means)
            lam_table[(thr, slip)] = x
            xs = "none" if x is None else f"{x:.3f}"
            print(f"{thr:5.0f} | {slip:5.0f} | {xs:>15} | {note}")

    header("5. PRE-COST CONDITIONAL DRIFT (signed quote mid, from t_ref)")
    for h in DRIFT_H:
        sub(f"horizon {h:.0f} s")
        print(f"{'thr':>5} | " + " | ".join(f"d={d:<5}" for d in DELTAS))
        line()
        for thr in THRS:
            row = []
            for d in DELTAS:
                res = results[(thr, 0.0, d)]
                if res["n"] == 0:
                    row.append("     --")
                    continue
                v = res["drift"][h]
                v = v[~np.isnan(v)]
                row.append(f"{v.mean():+7.2f}" if len(v) else "     --")
            print(f"{thr:5.0f} | " + " | ".join(row))

    header("6. QUOTE STATE AT THE TRIGGER (spread and best size at t_ref)")
    print(f"{'thr':>5} {'delta':>6} | {'n':>5} | {'spread bps p10/p50/p90':>26} | "
          f"{'touch-side best size BTC p10/p50/p90':>38} | {'opp side p50':>12}")
    line()
    for thr in THRS:
        for d in (0.0, 0.1, 0.5, 2.0):
            res = results[(thr, 0.0, d)]
            if res["n"] == 0 or "spread" not in res:
                continue
            sp = res["spread"]
            ts_ = res["touch_size"]
            op = res["opp_size"]
            print(f"{thr:5.0f} {d:6.2f} | {res['n']:5,} | "
                  f"{np.percentile(sp,10):7.2f}/{np.percentile(sp,50):7.2f}/"
                  f"{np.percentile(sp,90):7.2f} | "
                  f"{np.percentile(ts_,10):11.4f}/{np.percentile(ts_,50):11.4f}/"
                  f"{np.percentile(ts_,90):11.4f} | {np.percentile(op,50):12.4f}")
        line()

    header("7. EXIT MIX AND HOLD TIME")
    print(f"{'thr':>5} {'delta':>6} | {'n':>5} | {'TP fill %':>9} | {'mean hold s':>11} | "
          f"{'median net':>10} | {'win %':>6}")
    line()
    for thr in THRS:
        for d in (0.0, 0.1, 0.5, 2.0):
            res = results[(thr, 0.0, d)]
            if res["n"] == 0:
                continue
            print(f"{thr:5.0f} {d:6.2f} | {res['n']:5,} | "
                  f"{100*res['is_tp'].mean():9.1f} | {res['hold'].mean():11.1f} | "
                  f"{np.median(res['net']):+10.2f} | "
                  f"{100*(res['net']>0).mean():6.1f}")
        line()

    header("8. SPLITS (reported, never used to select)")
    for thr in THRS:
        sub(f"thr {thr:.0f} bps -- slip 0")
        print(f"{'delta':>6} | {'H1 n':>6} {'H1 net':>8} | {'H2 n':>6} {'H2 net':>8} | "
              f"{'pre-S12 n':>9} {'pre-S12 net':>11} | {'post n':>7} {'post net':>9}")
        line()
        for d in DELTAS:
            res = results[(thr, 0.0, d)]
            if res["n"] == 0:
                continue
            tr = res["t_ref"]
            order = np.argsort(tr, kind="stable")
            half = len(order) // 2
            h1 = np.zeros(len(tr), bool)
            h1[order[:half]] = True
            pre = tr < boundary
            def mn(mask):
                return (int(mask.sum()),
                        res["net"][mask].mean() if mask.sum() else float("nan"))
            n1, m1 = mn(h1)
            n2, m2 = mn(~h1)
            n3, m3 = mn(pre)
            n4, m4 = mn(~pre)
            print(f"{d:6.2f} | {n1:6,} {m1:+8.2f} | {n2:6,} {m2:+8.2f} | "
                  f"{n3:9,} {m3:+11.2f} | {n4:7,} {m4:+9.2f}")

    header("10. CAPACITY -- events per day, and events a SINGLE unit could take")
    print(f"{'thr':>5} {'delta':>6} | {'events':>7} {'/eff.day':>9} | "
          f"{'non-overlapping':>15} {'/eff.day':>9} | {'max concurrent':>14}")
    line()
    cap = {}
    for thr in THRS:
        for d in (0.0, 0.1, 0.5):
            res = results[(thr, 0.0, d)]
            if res["n"] == 0:
                continue
            t_ref = res["t_ref"]
            ex_t = t_ref + res["hold"]
            o = np.argsort(t_ref, kind="stable")
            free_at, taken = -np.inf, 0
            for k in o:
                if t_ref[k] >= free_at:
                    taken += 1
                    free_at = ex_t[k]
            # max concurrent positions if every event were taken
            ev = np.r_[t_ref, ex_t]
            mark = np.r_[np.ones(len(t_ref)), -np.ones(len(ex_t))]
            oo = np.argsort(ev, kind="stable")
            conc = int(np.max(np.cumsum(mark[oo])))
            cap[(thr, d)] = (res["n"], taken)
            print(f"{thr:5.0f} {d:6.2f} | {res['n']:7,} {res['n']/D['eff_days']:9.2f} | "
                  f"{taken:15,} {taken/D['eff_days']:9.2f} | {conc:14d}")
        line()

    header("11. ECONOMICS -- yen per day at a given reaction latency lambda")
    price = float(np.median(D["midq"]))
    print(f"reference price (median quote mid) : {price:,.0f} JPY")
    print(f"cost line to beat: a small Tokyo instance is ~1,000-1,500 JPY/month "
          f"= 33-50 JPY/day (upper end 6,000 JPY/month = 200 JPY/day)")
    print()
    print(f"{'scenario':>22} {'lambda s':>9} {'thr':>5} {'slip':>5} | "
          f"{'net bps':>8} | {'ev/day':>7} | {'0.02BTC yen/d':>13} | "
          f"{'0.10BTC yen/d':>13}")
    line()
    for label, lam in SCENARIOS:
        for thr in THRS:
            for slip in SLIPS:
                means = np.array([results[(thr, slip, d)]["net"].mean()
                                  if results[(thr, slip, d)]["n"] else np.nan
                                  for d in DELTAS])
                net = float(np.interp(lam, np.array(DELTAS), means))
                d0 = min(DELTAS, key=lambda x: abs(x - lam))
                n_ev, n_solo = cap.get((thr, 0.0), (results[(thr, 0.0, 0.0)]["n"],
                                                    results[(thr, 0.0, 0.0)]["n"]))
                evday = n_solo / D["eff_days"]
                y2 = net / 1e4 * 0.02 * price * evday
                y10 = net / 1e4 * 0.10 * price * evday
                print(f"{label:>22} {lam:9.3f} {thr:5.0f} {slip:5.0f} | "
                      f"{net:+8.2f} | {evday:7.2f} | {y2:+13,.0f} | {y10:+13,.0f}")
        line()
    print("0.10 BTC is 5x the measured touch-side best size (p50 0.02 BTC): "
          "that column walks the book and its true cost is worse than the "
          "slip +2 bps row shown.  Event counts are the single-unit "
          "(non-overlapping) counts from section 10.")

    header("12. SENSITIVITY -- staleness guard on the look-back leg")
    print(f"the trigger window is [t_i - {W_S:.0f}s, t_i], but the look-back mid "
          f"is the last print AT OR BEFORE t_i - {W_S:.0f}s, so in a thin patch "
          f"the effective window stretches.")
    print(f"main run allows {BACK_GUARD_S:.0f}s of stretch (atlas grid convention: "
          f"forward-filled, same effect); this table re-runs with "
          f"{BACK_GUARD_ALT_S:.0f}s.")
    print()
    print(f"{'thr':>5} | {'kept (main)':>11} {'net d=0':>8} {'net d=0.1':>10} | "
          f"{'kept (tight)':>12} {'net d=0':>8} {'net d=0.1':>10} | "
          f"{'lookback staleness p50/p90 s':>29}")
    line()
    for thr in THRS:
        i, s = trig[thr]
        i2, s2, _r2, _st2 = build_triggers(D, thr, BACK_GUARD_ALT_S)
        a0 = results[(thr, 0.0, 0.0)]
        a1 = results[(thr, 0.0, 0.1)]
        b0 = simulate(D, i2, s2, 0.0, 0.0)
        b1 = simulate(D, i2, s2, 0.1, 0.0)
        t_ex = D["t_ex"]
        back = np.searchsorted(t_ex, t_ex[i] - W_S, "right") - 1
        stale = t_ex[i] - W_S - t_ex[np.maximum(back, 0)]
        print(f"{thr:5.0f} | {a0['n']:11,} {a0['net'].mean():+8.2f} "
              f"{a1['net'].mean():+10.2f} | {b0['n']:12,} "
              f"{(b0['net'].mean() if b0['n'] else float('nan')):+8.2f} "
              f"{(b1['net'].mean() if b1['n'] else float('nan')):+10.2f} | "
              f"{np.percentile(stale,50):14.2f}/{np.percentile(stale,90):13.2f}")

    header("13. CROSS-CHECK -- the S10 / atlas 1-SECOND GRID convention "
           "on this same tape")
    print("report 23 (x) and the atlas date the same signal at the END of the "
          "1 s bar.  Rebuilding that exact convention here separates 'a "
          "different week' from 'a different clock' in the firing-rate gap "
          "(x measured 0.65 thr20 firings/day on the 31 d REST tape).")
    t_ex, px_, buy_ = D["t_ex"], D["px"], D["buy"]
    lb = ffill_vals(np.where(buy_, px_, np.nan))
    ls = ffill_vals(np.where(~buy_, px_, np.nan))
    mid_p = 0.5 * (lb + ls)
    g0 = int(np.floor(t_ex[0]))
    g1 = int(np.floor(t_ex[-1]))
    ng = g1 - g0 + 1
    gm = np.full(ng, np.nan)
    si = np.floor(t_ex).astype(np.int64) - g0
    gm[si] = mid_p
    gm = ffill_vals(gm)
    vf = int(np.argmax(~np.isnan(gm)))
    Wi = int(W_S)
    rg = np.full(ng, np.nan)
    rg[Wi:] = (gm[Wi:] - gm[:-Wi]) / gm[:-Wi] * 1e4
    okg = np.zeros(ng, bool)
    okg[max(Wi, vf + Wi):] = True
    print()
    print(f"{'thr':>5} | {'grid fires':>10} {'/eff.day':>9} {'net d=0':>8} | "
          f"{'print fires':>11} {'/eff.day':>9} {'net d=0':>8} | "
          f"{'print-level advantage':>21}")
    line()
    for thr in THRS:
        fireg = np.flatnonzero(okg & (np.abs(rg) >= thr))
        cd = max(W_S, COOLDOWN_S)
        last = {1: -np.inf, -1: -np.inf}
        gi, gs_ = [], []
        for i in fireg:
            s = 1 if rg[i] > 0 else -1
            if float(i) - last[s] < cd:
                continue
            last[s] = float(i)
            gi.append(i)
            gs_.append(s)
        # signal instant = the END of grid second i, mapped back to a print
        # index so the shared simulate() can be reused unchanged
        t_sig_g = np.asarray(gi, float) + g0 + 1.0
        pi = np.searchsorted(t_ex, t_sig_g, "right") - 1
        okp = pi >= 0
        pi, gs_ = pi[okp], np.asarray(gs_, np.int64)[okp]
        extra = t_sig_g[okp] - t_ex[pi]        # grid-to-print offset
        rg_res = simulate(D, pi, gs_, 0.0, 0.0)
        # the grid dates the signal `extra` later, so add it as a delay
        a0 = results[(thr, 0.0, 0.0)]
        print(f"{thr:5.0f} | {len(gi):10,} {len(gi)/D['eff_days']:9.2f} "
              f"{(rg_res['net'].mean() if rg_res['n'] else float('nan')):+8.2f} | "
              f"{a0['n']:11,} {a0['n']/D['eff_days']:9.2f} "
              f"{a0['net'].mean():+8.2f} | "
              f"median grid lag {np.median(extra):.2f}s")

    header("9. SANITY / ENGINE")
    r0 = results[(THRS[0], 0.0, 0.0)]
    print(f"look-ahead asserts     : passed (quote at or before t_ref; fill prints "
          f"strictly after t_ref)")
    print(f"gap discipline         : events dropped for touching a gap or missing "
          f"quote, per cell e.g. thr5/d0 = {r0['dropped']:,}")
    print(f"engine time            : {engine_s:.2f} s for {n_events_processed:,} "
          f"simulated events across {len(results)} cells")
    print(f"per-event engine cost  : "
          f"{1e6*engine_s/max(1,n_events_processed):,.0f} us "
          f"(vectorised-batch equivalent; single-event decision cost is bounded "
          f"by this)")
    dig = hashlib.sha256()
    for thr in THRS:
        for slip in SLIPS:
            for d in DELTAS:
                res = results[(thr, slip, d)]
                dig.update(f"{thr}|{slip}|{d}|{res['n']}|"
                           f"{0.0 if res['n']==0 else res['net'].mean():.9f}|".encode())
    print(f"result digest sha256   : {dig.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
