#!/usr/bin/env python3
"""
S10 AVALANCHE FOLLOW (20bps-class, second-scale, TAKER entry) -- EXPLORATION.

PRE-REGISTRATION (verbatim, frozen before the first run; changing anything
below after the first run abandons this registration -- research-protocol §1).

    [BACKGROUND -- S10, registered pending in KNOWLEDGE §4]
    Report e's surviving fact: the second-scale Binance->bitFlyer lag beats
    cost ONLY in 20bps-class dislocations.  It differs from the REJECTED burst
    scalper (thr 10bps, maker entry, -3.83bps) on both axes: execution
    (taker = avoids the 9.3bps adverse-selection wall) and threshold class
    (>=20bps).  This task is the EXPLORATION of it (feasibility boundary on a
    mined tape, and narrowing of the family).  An adoption decision is made
    only later, on fresh data.

    [DATA]
    - bitFlyer trade tape:
      backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz
      (columns id, exec_date, price, size, side; `side` is the TAKER side).
      ONLY rows with exec_date < 2026-08-20T08:22:17Z are used.  Everything
      at or after that instant is FRESH territory and is not read at all.
    - Binance trigger: 1s spot klines BTCUSDT from data.binance.vision,
      daily archives 2026-07-23 .. 2026-08-19, downloaded to the scratchpad
      (never stored in the repository).  TIMESTAMPS ARE MICROSECONDS.
    - No USDJPY conversion: the trigger is defined purely as a bps change on
      the Binance side; execution and P&L are entirely on the bitFlyer side.

    [PRE-REGISTRATION -- NO DEVIATION]
    - Trigger: bounce-free change of the Binance 1s close.  Fire when the
      move over the last 2 seconds is >= +/-thr bps.  thr in {20, 30}.
      Same-direction re-fire cooldown 60 s.
    - Latency: the reference price is the FIRST bitFlyer print at or after
      t+1.0s, where t is the firing second; the position is opened there in
      the direction of the trigger (momentum) with taker cost 3.96 bps added.
      In addition a slippage sensitivity of +4 bps (7.96 bps total) is
      reported alongside for every cell (sensitivity to book thinning during
      an avalanche -- a reported sensitivity, NOT a design variable).
    - Exit (E2 family ONLY -- no surface is drawn): maker TP limit at
      entry + tp bps, tp in {10, 20} (print-level traded-through fill,
      cost 0).  If unfilled after 120 seconds, taker fallback (3.96 bps).
      No protective stop (the 120 s bounds the loss).
    - Family = thr {20,30} x tp {10,20} = 4 CELLS.  NOTHING ADDED.
    - One position at a time, 60 s cooldown after every exit.
    - Split: time-series 60/40 over the exploration span.  The front half is
      observed; the back half is read ONCE and reported.  IF ALL FOUR CELLS
      HAVE A NEGATIVE BACK-HALF NET, THE FAMILY IS REJECTED AT FEASIBILITY
      (no fresh-data judgment follows).  If a positive cell exists, propose
      to the lead that this cell and the judgment bar (fresh >=30 events,
      net >= +5bps/trade, day-cluster t >= 2.0, CI excluding 0) be frozen.
    - Frequency / power report: events per day per cell.  Check consistency
      with report 21's proxy measurement (dedup 2.8/day @ 20bps).

    [REQUIRED REPORT]
    1. All-4-cell table on the exploration interval (n, events/day, net
       bps/trade, median, win rate, TP fill rate, fallback rate, day-cluster
       t/CI, cumulative-bps maxDD, hold-time p50), under BOTH slippage
       assumptions (3.96 / 7.96 bps).
    2. Same table on the judgment interval (back 40%), stating explicitly
       whether the winner changes between halves.
    3. Adverse-selection counterfactual: signed forward move from entry
       (5s / 30s / 120s) for the TP-filled group vs the fallback group.
    4. Ablation: post-trigger conditional bitFlyer drift (pre-cost, 5s /
       30s / 60s / 120s) per cell -- does report e's "only the 20bps class
       is positive" reproduce on this tape?
    5. Sanity: zero lookahead (entry strictly after the fire, t+1.0s
       latency), zero overlapping positions, epoch conversion cross-check
       (EPOCH-division idiom, `.astype("int64")` FORBIDDEN, printed
       microsecond->second unit verification line), seed 20260825 fixed,
       re-run determinism.
    6. Caveats / limits (resolution limit of a 1s-kline trigger, the public
       tape's density being 1/3.7 of the WS feed, etc.).  A negative result
       is written up as negative.

    [CONSTRAINTS]
    - Script is scripts/research_avalanche.py.  The pre-registration is
      written verbatim at the top of its docstring.  Read-only, idempotent,
      fixed seed.  No network beyond the download.

STRUCTURAL CONSTANTS FIXED BY THE ABOVE (spelled out so the code has no
free choices left; every one of these follows from the text above and none
of them is swept):

  * "bounce-free change over the last 2 seconds" = the NET displacement of
    the 1s close over the 2-second window, r2[i] = 1e4*(c[i]-c[i-2])/c[i-2].
    Net displacement is bounce-free by construction: an up-then-down round
    trip cancels and does not fire.  A move inside a single second is still
    captured because it enters the 2-second net.
  * "the firing second t": a 1s kline with open_time T covers [T, T+1), so
    its close is knowable only at T+1.  t := T+1 is the instant the signal
    exists, and the pre-registered t+1.0s latency puts the entry reference
    at the first bitFlyer print at or after T+2.0 -- one full second after
    the signal could first have been seen.  (The alternative reading,
    entry at T+1.0 = zero reaction time, is printed as a labelled
    DIAGNOSTIC only and is never selectable.)
  * Entry fill price P_e = base * (1 + side * c_in/1e4), c_in in
    {3.96, 7.96}; base = that first print's price.  The taker cost is inside
    the fill, which is what an implementable bot experiences.
  * TP limit L = P_e * (1 + side * tp/1e4) -- "entry + tp bps" is measured
    from the fill, so the market must travel c_in + tp bps from base.  Fill
    rule = the repo's traded-through rule: a LONG's resting sell at L fills
    on a print with taker side BUY and price >= L; a SHORT's resting buy at
    L fills on a print with taker side SELL and price <= L.  The entry print
    itself can never fill the TP (scan starts at the next print).
  * Fallback: first print at or after t_e + 120 s, taker 3.96 bps.
  * net_bps per trade = side*(P_exit - P_e)/P_e*1e4 - exit_cost_bps
    (exit_cost 0 on a TP fill, 3.96 on the fallback).
  * Data-integrity guards (not design variables, counts reported): a
    trigger is dropped if no bitFlyer print exists within 10 s of the entry
    reference time, or if no print exists within 60 s of the fallback
    instant.  All prints used must lie strictly before the 2026-08-20
    cutoff.

Usage:  PYTHONPATH=src python scripts/research_avalanche.py \
            --binance-dir <scratchpad>/binance_1s
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE = os.path.join(ROOT, "backtest_data",
                    "executions_FX_BTC_JPY_31d_20260823.csv.gz")

EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
FRESH_CUTOFF_ISO = "2026-08-20T08:22:17Z"

# --- pre-registered family (enumerated; nothing added) ----------------------
THRS_BPS = (20.0, 30.0)
TPS_BPS = (10.0, 20.0)

# --- pre-registered structural constants -----------------------------------
TRIGGER_LOOKBACK_S = 2          # "within the last 2 seconds"
TRIGGER_COOLDOWN_S = 60.0       # same-direction re-fire cooldown
LATENCY_S = 1.0                 # entry reference at signal instant + 1.0 s
TAKER_BPS = 3.96                # burst-regime taker, KNOWLEDGE §1
SLIP_SENS_BPS = 4.0             # avalanche book-thinning sensitivity
COST_IN = (TAKER_BPS, TAKER_BPS + SLIP_SENS_BPS)   # 3.96 / 7.96
FALLBACK_S = 120.0              # E2 fallback horizon
POS_COOLDOWN_S = 60.0           # cooldown after every exit
SPLIT_FRAC = 0.60               # time-series 60/40

ENTRY_PRINT_GUARD_S = 10.0      # data-integrity guards
FALLBACK_PRINT_GUARD_S = 60.0

BOOT_ITERS = 2000
SEED = 20260825

DRIFT_HORIZONS = (5.0, 30.0, 60.0, 120.0)
CF_HORIZONS = (5.0, 30.0, 120.0)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def line(char: str = "-", n: int = 104) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


def sub(title: str) -> None:
    print()
    print("--- " + title + " " + "-" * max(0, 100 - len(title)))


def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap.

    Dividing a Timedelta by Timedelta('1s') is unit-agnostic by construction.
    `.astype("int64")` / `.view()` are forbidden here (research-protocol §6).
    """
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_alt(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return np.array([x.timestamp() for x in idx], dtype=float)


def iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").isoformat()


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_tape() -> dict:
    cutoff = float((pd.Timestamp(FRESH_CUTOFF_ISO) - EPOCH) / pd.Timedelta("1s"))
    ex = pd.read_csv(TAPE)
    t = epoch_seconds(ex["exec_date"])
    t_alt = epoch_seconds_alt(ex["exec_date"])
    dev = float(np.max(np.abs(t - t_alt)))
    print(f"tape epoch cross-check : max |impl_a - impl_b| = {dev:.9f} s "
          f"(must be ~0)")
    print(f"tape first row         : {ex['exec_date'].iloc[0]} -> "
          f"{t[0]:.3f} s -> {iso(t[0])}")
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
          f"kept {keep.sum():,} / {n_all:,} prints, dropped {n_all - keep.sum():,} "
          f"(never read again)")
    print(f"tape span used         : {iso(t[0])} .. {iso(t[-1])} "
          f"({(t[-1] - t[0]) / 86400.0:.2f} days)")
    assert t[-1] < cutoff
    return {"t": t, "price": price, "buy": buy, "cutoff": cutoff}


def load_binance(dirpath: str) -> dict:
    paths = sorted(glob.glob(os.path.join(dirpath, "BTCUSDT-1s-*.csv")))
    if not paths:
        raise SystemExit(f"no Binance 1s files in {dirpath}")
    ot_list, close_list = [], []
    for p in paths:
        # open_time is read as float64 directly (no .astype("int64") anywhere);
        # 1.78e15 < 2^53 so microsecond integers are exact in float64.
        df = pd.read_csv(p, header=None, usecols=[0, 4],
                         names=["open_time", "close"], dtype=np.float64)
        ot_list.append(df["open_time"].to_numpy())
        close_list.append(df["close"].to_numpy())
    ot_us = np.concatenate(ot_list)
    close = np.concatenate(close_list)
    order = np.argsort(ot_us, kind="mergesort")
    ot_us, close = ot_us[order], close[order]

    # --- microsecond -> second unit verification (printed, protocol §6) ----
    t_bar = ot_us / 1e6
    d_us = float(np.median(np.diff(ot_us)))
    d_s = float(np.median(np.diff(t_bar)))
    as_ms = pd.Timestamp(float(ot_us[0]) / 1e3, unit="s", tz="UTC")
    print(f"binance files          : {len(paths)} "
          f"({os.path.basename(paths[0])} .. {os.path.basename(paths[-1])}), "
          f"{len(ot_us):,} 1s bars")
    print(f"UNIT CHECK us->s       : raw open_time[0]={ot_us[0]:.0f}; "
          f"median step = {d_us:.0f} raw units = {d_s:.3f} s "
          f"(1.000 confirms MICROseconds)")
    print(f"UNIT CHECK us->s       : /1e6 -> {iso(t_bar[0])}  |  "
          f"if it were milliseconds -> {as_ms.isoformat()} (absurd -> us is right)")
    if abs(d_s - 1.0) > 1e-9:
        raise SystemExit("Binance 1s spacing is not 1.000 s -- unit mismatch")
    # cross-check against the EPOCH-division idiom on the same instant
    t_chk = float((pd.Timestamp(iso(t_bar[0])) - EPOCH) / pd.Timedelta("1s"))
    print(f"UNIT CHECK us->s       : EPOCH-division round trip {t_chk:.3f} vs "
          f"{t_bar[0]:.3f} (delta {abs(t_chk - t_bar[0]):.9f})")
    if abs(t_chk - t_bar[0]) > 1e-6:
        raise SystemExit("binance epoch round trip mismatch")
    gaps = int(np.sum(np.diff(t_bar) != 1.0))
    print(f"binance continuity     : {gaps} non-1s steps; span "
          f"{iso(t_bar[0])} .. {iso(t_bar[-1] + 1.0)}")
    return {"t_bar": t_bar, "close": close}


# --------------------------------------------------------------------------
# trigger stream
# --------------------------------------------------------------------------
def build_triggers(bn: dict, thr: float, t_lo: float, t_hi: float) -> list[dict]:
    """Bounce-free 2s net move >= thr bps; 60 s same-direction cooldown.

    Returns dicts with t_sig (instant the signal exists = bar close) and
    t_entry_ref (t_sig + LATENCY_S).  Lookahead is structurally impossible:
    every quantity is built from closes at or before the bar, and the entry
    reference lies strictly after the bar's close.
    """
    t_bar, close = bn["t_bar"], bn["close"]
    k = TRIGGER_LOOKBACK_S
    r2 = np.full(len(close), np.nan)
    r2[k:] = (close[k:] - close[:-k]) / close[:-k] * 1e4
    # only bars whose 2s window is contiguous
    ok = np.zeros(len(close), bool)
    ok[k:] = (t_bar[k:] - t_bar[:-k]) == float(k)
    fire = ok & (np.abs(r2) >= thr)

    out: list[dict] = []
    dropped = {"cooldown": 0, "outside_span": 0}
    last = {1: -np.inf, -1: -np.inf}
    for i in np.flatnonzero(fire):
        side = 1 if r2[i] > 0 else -1
        tb = t_bar[i]
        if tb - last[side] < TRIGGER_COOLDOWN_S:
            dropped["cooldown"] += 1
            continue
        last[side] = tb
        t_sig = tb + 1.0                     # bar [tb, tb+1) closes at tb+1
        t_ref = t_sig + LATENCY_S
        if not (t_lo <= t_ref <= t_hi):
            dropped["outside_span"] += 1
            continue
        out.append({"t_bar": tb, "t_sig": t_sig, "t_ref": t_ref,
                    "side": side, "r2": float(r2[i])})
    out_stats = {"raw_fires": int(fire.sum()), **dropped}
    return out, out_stats


# --------------------------------------------------------------------------
# tape lookups
# --------------------------------------------------------------------------
def first_print_at_or_after(tp: dict, t: float) -> int:
    return int(np.searchsorted(tp["t"], t, side="left"))


def price_at(tp: dict, t: float, guard: float) -> tuple[float, float]:
    """(price, print time) of the first print at or after t; nan if outside guard."""
    j = first_print_at_or_after(tp, t)
    if j >= len(tp["t"]) or tp["t"][j] - t > guard:
        return float("nan"), float("nan")
    return float(tp["price"][j]), float(tp["t"][j])


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
def simulate(tp: dict, trigs: list[dict], tp_bps: float, c_in: float) -> dict:
    t_arr, p_arr, buy_arr = tp["t"], tp["price"], tp["buy"]
    n = len(t_arr)
    trades: list[dict] = []
    next_ok = -np.inf
    skipped_cooldown = 0
    skipped_no_entry_print = 0
    skipped_no_fallback_print = 0
    skipped_cutoff = 0

    for tr in trigs:
        if tr["t_ref"] < next_ok:
            skipped_cooldown += 1
            continue
        i = first_print_at_or_after(tp, tr["t_ref"])
        if i >= n or t_arr[i] - tr["t_ref"] > ENTRY_PRINT_GUARD_S:
            skipped_no_entry_print += 1
            continue
        t_e = float(t_arr[i])
        base = float(p_arr[i])
        # zero-lookahead invariant: the entry print is at or after the
        # pre-registered reference instant, which itself is >= the instant
        # the 1s bar closed (t_sig).  Both legs asserted.
        assert tr["t_ref"] >= tr["t_sig"] - 1e-9, "lookahead: ref before signal"
        assert t_e >= tr["t_ref"] - 1e-9, "lookahead: entry before reference"
        side = tr["side"]
        p_e = base * (1.0 + side * c_in / 1e4)
        limit = p_e * (1.0 + side * tp_bps / 1e4)

        # ---- scan for a traded-through TP fill inside 120 s ---------------
        t_deadline = t_e + FALLBACK_S
        j = i + 1                                   # entry print cannot fill
        fill_t = None
        while j < n and t_arr[j] < t_deadline:
            if side == 1:
                if buy_arr[j] and p_arr[j] >= limit:
                    fill_t = float(t_arr[j])
                    break
            else:
                if (not buy_arr[j]) and p_arr[j] <= limit:
                    fill_t = float(t_arr[j])
                    break
            j += 1

        if fill_t is not None:
            exit_px, exit_t, exit_kind, exit_cost = limit, fill_t, "tp", 0.0
        else:
            px, pt = price_at(tp, t_deadline, FALLBACK_PRINT_GUARD_S)
            if not np.isfinite(px):
                skipped_no_fallback_print += 1
                continue
            exit_px, exit_t, exit_kind, exit_cost = px, pt, "fb", TAKER_BPS

        if exit_t >= tp["cutoff"]:
            skipped_cutoff += 1
            continue

        net = side * (exit_px - p_e) / p_e * 1e4 - exit_cost
        fwd = {}
        for h in CF_HORIZONS:
            px, _ = price_at(tp, t_e + h, FALLBACK_PRINT_GUARD_S)
            fwd[h] = (side * (px - base) / base * 1e4
                      if np.isfinite(px) else float("nan"))
        trades.append({
            "t": t_e, "day": int(t_e // 86400), "side": side,
            "net_bps": net, "exit": exit_kind, "hold_s": exit_t - t_e,
            "fwd": fwd, "r2": tr["r2"],
        })
        next_ok = exit_t + POS_COOLDOWN_S

    return {"trades": trades,
            "skipped_cooldown": skipped_cooldown,
            "skipped_no_entry_print": skipped_no_entry_print,
            "skipped_no_fallback_print": skipped_no_fallback_print,
            "skipped_cutoff": skipped_cutoff}


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def day_cluster_boot(trades: list[dict]) -> tuple[float, float, float] | None:
    by_day: dict[int, list[float]] = {}
    for tr in trades:
        by_day.setdefault(tr["day"], []).append(tr["net_bps"])
    days = list(by_day)
    if len(days) < 2:
        return None
    rng = random.Random(SEED)
    means = []
    for _ in range(BOOT_ITERS):
        pool: list[float] = []
        for _ in range(len(days)):
            pool.extend(by_day[days[rng.randrange(len(days))]])
        if pool:
            means.append(sum(pool) / len(pool))
    means.sort()
    mu = float(np.mean([tr["net_bps"] for tr in trades]))
    sd = float(np.std(means))
    lo = means[int(0.025 * len(means))]
    hi = means[min(len(means) - 1, int(0.975 * len(means)))]
    # sd == 0 means every resample gave the same mean (degenerate: too few
    # distinct days / identical outcomes).  A t of 1e13 is not a signal.
    return lo, hi, (mu / sd if sd > 1e-9 else float("nan"))


def max_dd_bps(trades: list[dict]) -> float:
    cum = peak = worst = 0.0
    for tr in trades:
        cum += tr["net_bps"]
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst


def cell_row(name: str, trades: list[dict], days: float) -> str:
    if not trades:
        return f"{name:<16}{0:>5}"
    nets = np.array([t["net_bps"] for t in trades])
    tps = sum(1 for t in trades if t["exit"] == "tp")
    boot = day_cluster_boot(trades)
    ci = f"[{boot[0]:+.2f},{boot[1]:+.2f}]" if boot else "n/a"
    tstat = (f"{boot[2]:+.2f}" if boot and np.isfinite(boot[2]) else "degen")
    holds = np.array([t["hold_s"] for t in trades])
    return (f"{name:<16}{len(trades):>5}{len(trades) / days:>8.2f}"
            f"{nets.mean():>10.2f}{np.median(nets):>9.2f}"
            f"{100 * np.mean(nets > 0):>7.1f}"
            f"{100 * tps / len(trades):>7.1f}"
            f"{100 * (len(trades) - tps) / len(trades):>7.1f}"
            f"{tstat:>7}  {ci:<20}{max_dd_bps(trades):>8.0f}"
            f"{np.median(holds):>9.1f}")


def cell_header() -> None:
    print(f"{'cell':<16}{'n':>5}{'ev/day':>8}{'net bps':>10}{'median':>9}"
          f"{'win%':>7}{'TP%':>7}{'fb%':>7}{'t':>7}  {'95% CI':<20}"
          f"{'maxDD':>8}{'holdp50':>9}")
    line()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binance-dir", required=True)
    args = ap.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)

    header("S10 AVALANCHE FOLLOW -- EXPLORATION ONLY "
           "(mined tape; adoption impossible from this run)")
    print(f"seed {SEED}; family = thr {THRS_BPS} x tp {TPS_BPS} = "
          f"{len(THRS_BPS) * len(TPS_BPS)} cells (frozen)")

    sub("0. data + epoch / unit sanity")
    tp = load_tape()
    bn = load_binance(args.binance_dir)

    # exploration span = overlap of (tape usable) and (binance bars + latency)
    t_lo = max(tp["t"][0], bn["t_bar"][0] + 1.0 + LATENCY_S)
    t_hi = min(tp["cutoff"], bn["t_bar"][-1] + 1.0 + LATENCY_S)
    span_days = (t_hi - t_lo) / 86400.0
    split_t = t_lo + SPLIT_FRAC * (t_hi - t_lo)
    print(f"exploration span       : {iso(t_lo)} .. {iso(t_hi)} "
          f"({span_days:.2f} days)")
    print(f"60/40 split boundary   : {iso(split_t)}  "
          f"(front {(split_t - t_lo) / 86400.0:.2f} d / "
          f"back {(t_hi - split_t) / 86400.0:.2f} d)")

    trig, tstats = {}, {}
    for thr in THRS_BPS:
        trig[thr], tstats[thr] = build_triggers(bn, thr, t_lo, t_hi)
    for thr in THRS_BPS:
        ts, st = trig[thr], tstats[thr]
        up = sum(1 for x in ts if x["side"] == 1)
        print(f"triggers thr={thr:.0f}bps  : {len(ts):>5} "
              f"({len(ts) / span_days:.2f}/day)  up {up} / down {len(ts) - up}"
              f"   [raw 1s-bar fires {st['raw_fires']}, "
              f"dropped by 60s same-dir cooldown {st['cooldown']}, "
              f"outside span {st['outside_span']}]")

    sub("POWER: what the pre-registered bar (>=30 events) costs at this rate")
    for thr in THRS_BPS:
        rate = len(trig[thr]) / span_days
        need = 30.0 / rate if rate > 0 else float("inf")
        print(f"  thr={thr:.0f}bps: {rate:.2f} triggers/day -> "
              f"{need:.0f} calendar days of fresh data for n=30 "
              f"({need / 7:.1f} weeks)")

    # ---------------- 1/2. cell tables -----------------------------------
    results: dict[tuple, dict] = {}
    for c_in in COST_IN:
        header(f"1-2. CELL TABLES -- entry taker cost {c_in:.2f} bps"
               + ("   [PRIMARY 3.96]" if c_in == TAKER_BPS
                  else "   [SENSITIVITY +4bps book thinning]"))
        for label, lo, hi, days in (
                ("FULL exploration span", t_lo, t_hi, span_days),
                ("FRONT 60% (observation)", t_lo, split_t,
                 (split_t - t_lo) / 86400.0),
                ("BACK 40% (judgment -- read once)", split_t, t_hi,
                 (t_hi - split_t) / 86400.0)):
            sub(label)
            cell_header()
            for thr in THRS_BPS:
                for tpb in TPS_BPS:
                    key = (c_in, thr, tpb)
                    if key not in results:
                        results[key] = simulate(tp, trig[thr], tpb, c_in)
                    tr = [x for x in results[key]["trades"] if lo <= x["t"] < hi]
                    print(cell_row(f"thr{thr:.0f}/tp{tpb:.0f}", tr, days))

    # ---------------- guards / sanity counters ---------------------------
    header("5. SANITY")
    print("lookahead: asserted per trade (entry print time >= signal instant "
          "+ 1.0 s); signal instant = 1s bar close = open_time + 1 s")
    print(f"seed fixed at {SEED}; bootstrap iterations {BOOT_ITERS}; "
          "no network access inside this script")
    print()
    print(f"{'cell (c_in)':<22}{'entries':>9}{'skip:cooldown':>15}"
          f"{'skip:no-entry-print':>21}{'skip:no-fb-print':>18}{'skip:cutoff':>13}")
    line()
    for (c_in, thr, tpb), r in sorted(results.items()):
        print(f"{f'{c_in:.2f}/thr{thr:.0f}/tp{tpb:.0f}':<22}"
              f"{len(r['trades']):>9}{r['skipped_cooldown']:>15}"
              f"{r['skipped_no_entry_print']:>21}"
              f"{r['skipped_no_fallback_print']:>18}{r['skipped_cutoff']:>13}")

    # overlap check
    worst_overlap = 0
    for key, r in results.items():
        trs = r["trades"]
        for a, b in zip(trs, trs[1:]):
            if b["t"] < a["t"] + a["hold_s"]:
                worst_overlap += 1
    print(f"\noverlapping positions across all cells: {worst_overlap} "
          "(must be 0)")

    # latency diagnostic (never selectable)
    sub("latency reading DIAGNOSTIC (never selectable): entry at bar close "
        "+0.0s instead of +1.0s")
    cell_header()
    for thr in THRS_BPS:
        alt = []
        for x in trig[thr]:
            y = dict(x)
            y["t_ref"] = x["t_sig"]
            alt.append(y)
        for tpb in TPS_BPS:
            r = simulate(tp, alt, tpb, TAKER_BPS)
            print(cell_row(f"thr{thr:.0f}/tp{tpb:.0f}", r["trades"], span_days))

    # ---------------- 3. adverse-selection counterfactual ----------------
    header("3. ADVERSE-SELECTION COUNTERFACTUAL "
           "(signed forward move from the entry reference price, pre-cost)")
    print("TP-filled trades vs fallback trades: where did the market actually")
    print("go?  The TP group should be the one the market carried; a maker TP")
    print("in a momentum exit is the FRIENDLY side of the selection wall "
          "(KNOWLEDGE §2).")
    for c_in in COST_IN:
        sub(f"entry cost {c_in:.2f} bps")
        print(f"{'cell':<16}{'group':<10}{'n':>5}"
              + "".join(f"{f'+{h:.0f}s':>10}" for h in CF_HORIZONS))
        line()
        for thr in THRS_BPS:
            for tpb in TPS_BPS:
                trs = results[(c_in, thr, tpb)]["trades"]
                for grp in ("tp", "fb"):
                    g = [x for x in trs if x["exit"] == grp]
                    if not g:
                        continue
                    row = "".join(
                        f"{np.nanmean([x['fwd'][h] for x in g]):>+10.2f}"
                        for h in CF_HORIZONS)
                    print(f"{f'thr{thr:.0f}/tp{tpb:.0f}':<16}"
                          f"{'TP fill' if grp == 'tp' else 'fallback':<10}"
                          f"{len(g):>5}{row}")

    # ---------------- 4. ablation: conditional drift ----------------------
    header("4. ABLATION -- post-trigger conditional bitFlyer drift, PRE-COST")
    print("Signed move from the entry reference price (first print at "
          "t_sig+1.0s) in the trigger direction.")
    print("Round-trip taker reference line: 2 x 3.96 = 7.92 bps "
          "(one-way 3.96).")

    def drift_table(trigs: list[dict], lo: float, hi: float, label: str) -> None:
        rows = [x for x in trigs if lo <= x["t_ref"] < hi]
        vals = {h: [] for h in DRIFT_HORIZONS}
        n_ok = 0
        for x in rows:
            base, t_e = price_at(tp, x["t_ref"], ENTRY_PRINT_GUARD_S)
            if not np.isfinite(base):
                continue
            n_ok += 1
            for h in DRIFT_HORIZONS:
                px, _ = price_at(tp, t_e + h, FALLBACK_PRINT_GUARD_S)
                if np.isfinite(px):
                    vals[h].append(x["side"] * (px - base) / base * 1e4)
        cells = "".join(
            f"{np.mean(vals[h]):>+10.2f}" if vals[h] else f"{'n/a':>10}"
            for h in DRIFT_HORIZONS)
        med = "".join(
            f"{np.median(vals[h]):>+10.2f}" if vals[h] else f"{'n/a':>10}"
            for h in DRIFT_HORIZONS)
        print(f"{label:<34}{n_ok:>6}{cells}   | med {med}")

    print(f"\n{'universe (all triggers)':<34}{'n':>6}"
          + "".join(f"{f'+{h:.0f}s':>10}" for h in DRIFT_HORIZONS)
          + "   | medians")
    line()
    for thr in THRS_BPS:
        drift_table(trig[thr], t_lo, t_hi, f"thr={thr:.0f}bps  full span")
        drift_table(trig[thr], t_lo, split_t, f"thr={thr:.0f}bps  front 60%")
        drift_table(trig[thr], split_t, t_hi, f"thr={thr:.0f}bps  back 40%")

    print(f"\n{'entered events only (per cell)':<34}{'n':>6}"
          + "".join(f"{f'+{h:.0f}s':>10}" for h in CF_HORIZONS))
    line()
    for thr in THRS_BPS:
        for tpb in TPS_BPS:
            trs = results[(TAKER_BPS, thr, tpb)]["trades"]
            row = "".join(
                f"{np.nanmean([x['fwd'][h] for x in trs]):>+10.2f}"
                for h in CF_HORIZONS) if trs else ""
            print(f"{f'thr{thr:.0f}/tp{tpb:.0f} (c_in 3.96)':<34}"
                  f"{len(trs):>6}{row}")

    # report-e style threshold ladder (diagnostic, never selectable)
    sub("report-e replication ladder (DIAGNOSTIC, outside the frozen family): "
        "same 2s trigger at thr 5/10/20/30 bps")
    print(f"{'thr':<34}{'n':>6}"
          + "".join(f"{f'+{h:.0f}s':>10}" for h in DRIFT_HORIZONS)
          + "   | medians")
    line()
    for thr in (5.0, 10.0, 20.0, 30.0):
        tg = trig.get(thr)
        if tg is None:
            tg, _ = build_triggers(bn, thr, t_lo, t_hi)
        drift_table(tg, t_lo, t_hi, f"thr={thr:.0f}bps ({len(tg)} trig)")

    # ---------------- frequency cross-check ------------------------------
    header("FREQUENCY CROSS-CHECK vs report 21 proxy (|1m| >= 20bps, "
           "dedup 5min -> 2.8/day)")
    for src, tt, pp in (("binance 1s->1m", bn["t_bar"] + 1.0, bn["close"]),
                        ("bitflyer tape->1m", tp["t"], tp["price"])):
        m = np.floor(tt / 60.0)
        idx = np.flatnonzero(np.r_[np.diff(m) != 0, True])   # last print of min
        mt, mp = tt[idx], pp[idx]
        keep = (mt >= t_lo) & (mt < t_hi)
        mt, mp = mt[keep], mp[keep]
        for thr in (20.0, 30.0):
            r1 = np.full(len(mp), np.nan)
            r1[1:] = (mp[1:] - mp[:-1]) / mp[:-1] * 1e4
            hit = np.flatnonzero(np.abs(r1) >= thr)
            last = -np.inf
            ded = 0
            for i in hit:
                if mt[i] - last >= 300.0:
                    ded += 1
                    last = mt[i]
            print(f"{src:<20} |1m|>={thr:.0f}bps : raw {len(hit):>4} "
                  f"({len(hit) / span_days:.2f}/day)  dedup5m {ded:>4} "
                  f"({ded / span_days:.2f}/day)")

    header("END -- exploration output only.  Selection rule: if ALL FOUR "
           "back-40% nets are negative, the family is rejected at feasibility.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
