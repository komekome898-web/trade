#!/usr/bin/env python3
"""
STORM-CLOCK BRACKET (S9) -- exploration / feasibility boundary. EXPLORATION ONLY.

PRE-REGISTRATION (frozen before first run; changing anything below after the
first run is an abandonment of this registration -- research-protocol §1).

Hypothesis
----------
Composite of three independently established laws (docs/KNOWLEDGE.md §2):
  (1) range-edge trade-through is a continuation event (breakout 61.4% vs
      revert 31.7% at 10bps; survives regimes and markets -- reports k, o, s);
      the resting fader on the other side measurably loses ~6.5bps after fill,
      so the through-going TAKER is the conjugate of a measured loser;
  (2) storms (|30m return| >= 0.8%) concentrate in the UTC 12:30-15:00 clock
      window, lift 2.23, the ONLY surviving precursor (report h);
  (3) storm direction is unpredictable (report i) -- so the entry must be
      direction-agnostic (whichever side trades through first).
Strategy: inside the clock window, taker-enter in the direction of the first
trade-through of the prior 30-minute extreme; protective stop only; NO take
profit (the champion's expectancy is one fat right tail -- TP caps were
rejected mechanically, tournament T); time exit as backstop.

Data (this run -- ALREADY MINED, so adoption is impossible from it)
------------------------------------------------------------------
backtest_data/candles_FX_BTC_JPY_30d_20260820.csv  (1m, 43,206 rows,
2026-07-21 .. 2026-08-20). Reports h/k were generated from overlapping data:
this run is a FEASIBILITY BOUNDARY in the sense of PREREG_fast_cycle §0, not
a judgment. The judgment data (fresh candles strictly after
2026-08-22T12:00:00Z, >= 14 clock-window days) must not be touched here.

Configuration family -- enumerated; nothing added later
-------------------------------------------------------
6 cells = stop distance X in {10, 15, 20} bps  x  time exit T in {30, 60} min.
Fixed structure (not swept, not changed after judgment):
  * touch: bar t with high[t] > max(high[t-30..t-1])  -> LONG, or
           low[t]  < min(low[t-30..t-1])              -> SHORT;
           both in the same bar -> skip (ambiguous).
  * entry price ref: long max(open[t], H30), short min(open[t], L30).
  * costs: taker 3.96 bps per side (burst regime, KNOWLEDGE §1), charged on
    entry AND on every exit (stop and time exit alike; conservative).
  * stop: X bps adverse from entry ref, checked from the entry bar onward
    (entry bar itself can stop out); exit at the stop level.
  * time exit: close of the T-th bar after entry.
  * one position at a time; 30 min cooldown after every exit;
    max 2 entries per clock-window day.
  * primary universe: entries inside UTC [12:30, 15:00) only.
    The all-day run of the same 6 cells is a DIAGNOSTIC (printed, never
    selectable) to show whether the clock matters.
  * candle-gap handling: a touch is only valid if the prior 30 rows span
    exactly 30 minutes; a trade whose exit path crosses a data gap is
    counted but flagged unmeasured, not repaired.

Selection rule (frozen NOW, applied to this exploration output)
---------------------------------------------------------------
Among the 6 clock-window cells: keep cells with net EV > 0 AND n >= 30.
If none survive -> the family is REJECTED AT FEASIBILITY and no fresh data is
consumed (PREREG_fast_cycle §0 precedent). Otherwise select the single cell
with the highest day-clustered bootstrap t (stability, not mean), subject to
the plateau condition: the X-adjacent cells (same T) must not fall below 50%
of the selected cell's net EV. The selected cell is then judged ONCE on fresh
data against the pre-registered bar (>= 30 events AND net >= +5 bps/trade AND
day-clustered CI excluding 0 AND cumulative-bps maxDD <= 1000 bps), written
into the S9 report before any fresh data exists. A fresh-data winner different
from the frozen cell = overfitting flag = rejection.

Sanity (all must pass before results are read)
----------------------------------------------
lookahead zero (extremes exclude the current bar); one position at a time;
deterministic bootstrap (seed 20260822, no network); epoch conversion
cross-check printed; touch->entry ratio printed (order-of-magnitude check).

Usage:  PYTHONPATH=src python scripts/research_storm_bracket.py
"""
from __future__ import annotations

import os
import random
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "backtest_data", "candles_FX_BTC_JPY_30d_20260820.csv")

LOOKBACK_MIN = 30                  # prior-extreme window (matches storm window)
STOPS_BPS = (10.0, 15.0, 20.0)     # X: the only swept axis (with T)
TIME_EXITS_MIN = (30, 60)          # T
TAKER_BPS = 3.96                   # burst-regime taker cost, per side
WINDOW_START = (12, 30)            # UTC clock window (report h)
WINDOW_END = (15, 0)
COOLDOWN_MIN = 30
MAX_ENTRIES_PER_WINDOW_DAY = 2
BOOT_ITERS = 2000
BOOT_SEED = 20260822

STORM_WINDOW_MIN = 30              # report-h storm definition (diagnostic)
STORM_THRESHOLD = 0.008


def line(char: str = "-", n: int = 96) -> None:
    print(char * n)


def header(title: str) -> None:
    print()
    line("=")
    print(title)
    line("=")


def load_candles() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    # pandas datetime64 unit trap (research-protocol §6): divide by Timedelta.
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    df["t"] = ((df["ts"] - epoch) / pd.Timedelta("1s")).to_numpy(dtype=float)
    # cross-check one row
    ts0, t0 = df["ts"].iloc[0], df["t"].iloc[0]
    assert abs(ts0.timestamp() - t0) < 1e-6, "epoch conversion mismatch"
    print(f"epoch cross-check: {ts0.isoformat()} -> {t0:.0f} "
          f"(datetime.timestamp {ts0.timestamp():.0f}) OK")
    return df


def in_window(ts: pd.Timestamp) -> bool:
    hm = (ts.hour, ts.minute)
    return WINDOW_START <= hm < WINDOW_END


def simulate(df: pd.DataFrame, stop_bps: float, texit_min: int,
             clock_only: bool) -> dict:
    """Single-pass, one position at a time, lookahead-free."""
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    open_ = df["open"].to_numpy(float)
    close = df["close"].to_numpy(float)
    t = df["t"].to_numpy(float)
    ts = df["ts"]

    n = len(df)
    trades: list[dict] = []
    touches = 0
    skipped_gap = 0
    skipped_both = 0
    unmeasured = 0
    i = LOOKBACK_MIN
    next_ok_i = 0
    entries_by_day: dict[str, int] = {}

    while i < n:
        if i < next_ok_i:
            i += 1
            continue
        # prior-extreme window must be contiguous (no candle gaps)
        if t[i] - t[i - LOOKBACK_MIN] != LOOKBACK_MIN * 60.0:
            i += 1
            continue
        h30 = high[i - LOOKBACK_MIN:i].max()
        l30 = low[i - LOOKBACK_MIN:i].min()
        up = high[i] > h30
        dn = low[i] < l30
        if not (up or dn):
            i += 1
            continue
        touches += 1
        if clock_only and not in_window(ts.iloc[i]):
            i += 1
            continue
        if up and dn:
            skipped_both += 1
            i += 1
            continue
        day = ts.iloc[i].strftime("%Y-%m-%d")
        if entries_by_day.get(day, 0) >= MAX_ENTRIES_PER_WINDOW_DAY:
            i += 1
            continue

        side = 1 if up else -1
        entry = max(open_[i], h30) if up else min(open_[i], l30)
        stop = entry * (1 - side * stop_bps / 1e4)

        # walk forward from the entry bar itself
        exit_px = None
        exit_kind = None
        j = i
        while j < n and j <= i + texit_min:
            if t[j] - t[i] > texit_min * 60.0 + 60.0:
                break                                    # data gap: give up
            hit = (low[j] <= stop) if side == 1 else (high[j] >= stop)
            if hit:
                exit_px, exit_kind, j_exit = stop, "stop", j
                break
            if j == i + texit_min:
                exit_px, exit_kind, j_exit = close[j], "time", j
                break
            j += 1
        if exit_px is None:
            unmeasured += 1
            skipped_gap += 1
            i += 1
            continue

        gross = side * (exit_px - entry) / entry * 1e4
        net = gross - 2 * TAKER_BPS
        entries_by_day[day] = entries_by_day.get(day, 0) + 1
        trades.append({"ts": ts.iloc[i], "day": day, "side": side,
                       "net_bps": net, "exit": exit_kind,
                       "hold_min": (t[j_exit] - t[i]) / 60.0})
        next_ok_i = j_exit + COOLDOWN_MIN
        i = j_exit + 1

    return {"trades": trades, "touches": touches, "skipped_both": skipped_both,
            "unmeasured": unmeasured}


def day_cluster_boot(trades: list[dict]) -> tuple[float, float, float] | None:
    """(lo, hi, t) of the mean net bps, resampling whole UTC days."""
    by_day: dict[str, list[float]] = {}
    for tr in trades:
        by_day.setdefault(tr["day"], []).append(tr["net_bps"])
    days = list(by_day)
    if len(days) < 2:
        return None
    rng = random.Random(BOOT_SEED)
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
    t_stat = mu / sd if sd > 0 else float("nan")
    return lo, hi, t_stat


def max_dd_bps(trades: list[dict]) -> float:
    cum = peak = worst = 0.0
    for tr in trades:
        cum += tr["net_bps"]
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst


def storm_minutes(df: pd.DataFrame) -> np.ndarray:
    logc = np.log(df["close"].to_numpy(float))
    r30 = np.full(len(df), np.nan)
    r30[STORM_WINDOW_MIN:] = logc[STORM_WINDOW_MIN:] - logc[:-STORM_WINDOW_MIN]
    return np.abs(r30) >= STORM_THRESHOLD


def forward_drift(df: pd.DataFrame, clock_only: bool) -> None:
    """Diagnostic: signed drift after a touch, in touch direction (report-k link)."""
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    close = df["close"].to_numpy(float)
    t = df["t"].to_numpy(float)
    ts = df["ts"]
    out = {5: [], 15: [], 30: []}
    for i in range(LOOKBACK_MIN, len(df) - 31):
        if t[i] - t[i - LOOKBACK_MIN] != LOOKBACK_MIN * 60.0:
            continue
        if t[i + 30] - t[i] != 30 * 60.0:
            continue
        h30 = high[i - LOOKBACK_MIN:i].max()
        l30 = low[i - LOOKBACK_MIN:i].min()
        up = high[i] > h30
        dn = low[i] < l30
        if up == dn:
            continue
        if clock_only and not in_window(ts.iloc[i]):
            continue
        side = 1 if up else -1
        ref = h30 if up else l30
        for hz in out:
            out[hz].append(side * (close[i + hz] - ref) / ref * 1e4)
    label = "clock window" if clock_only else "all day"
    row = ", ".join(f"+{hz}m {np.mean(v):+.2f}bps (n={len(v)})"
                    for hz, v in out.items())
    print(f"  touch->forward signed drift [{label}]: {row}")


def main() -> int:
    header("S9 STORM-CLOCK BRACKET -- EXPLORATION ONLY (mined 30d candles; "
           "adoption impossible from this run)")
    df = load_candles()
    print(f"rows {len(df)}, span {df['ts'].iloc[0]} .. {df['ts'].iloc[-1]}")
    storms = storm_minutes(df)
    print(f"storm minutes (|r30|>=0.8%): {int(storms.sum())} "
          f"({storms.mean() * 100:.2f}% of minutes)")

    header("touch diagnostics (the conjugate-of-the-fader check)")
    forward_drift(df, clock_only=False)
    forward_drift(df, clock_only=True)

    for clock_only in (True, False):
        title = ("PRIMARY: clock window 12:30-15:00 UTC" if clock_only
                 else "DIAGNOSTIC: all day (never selectable)")
        header(title)
        print(f"{'cell':<16}{'n':>4}{'net bps':>9}{'median':>9}{'win%':>7}"
              f"{'stop%':>7}{'t':>7}  {'95% CI':<20}{'maxDD':>7}{'hold p50':>9}")
        line()
        for x in STOPS_BPS:
            for te in TIME_EXITS_MIN:
                r = simulate(df, x, te, clock_only)
                tr = r["trades"]
                if not tr:
                    print(f"X{x:>4.0f}/T{te:<8} {'0':>4}")
                    continue
                nets = [q["net_bps"] for q in tr]
                stops = sum(1 for q in tr if q["exit"] == "stop")
                boot = day_cluster_boot(tr)
                ci = (f"[{boot[0]:+.2f},{boot[1]:+.2f}]" if boot else "n/a")
                t_stat = f"{boot[2]:+.2f}" if boot else "-"
                holds = sorted(q["hold_min"] for q in tr)
                print(f"X{x:>4.0f}/T{te:<8}{len(tr):>4}{np.mean(nets):>9.2f}"
                      f"{np.median(nets):>9.2f}"
                      f"{100 * np.mean([q > 0 for q in nets]):>7.1f}"
                      f"{100 * stops / len(tr):>7.1f}{t_stat:>7}  {ci:<20}"
                      f"{max_dd_bps(tr):>7.0f}"
                      f"{holds[len(holds) // 2]:>9.1f}")
        r = simulate(df, STOPS_BPS[0], TIME_EXITS_MIN[0], clock_only)
        print(f"\n  touches seen: {r['touches']}, ambiguous both-side bars "
              f"skipped: {r['skipped_both']}, unmeasured (gap): "
              f"{r['unmeasured']}")

    header("frozen next step")
    print("Selection rule (docstring) applied by the S9 report, not by eye.\n"
          "If no clock cell has net>0 and n>=30: REJECT AT FEASIBILITY,\n"
          "consume no fresh data. Otherwise: freeze the max-t cell (plateau\n"
          "condition on X) and judge ONCE on candles strictly after\n"
          "2026-08-22T12:00:00Z with >= 14 clock-window days, bar:\n"
          "n>=30 AND net>=+5bps AND day-cluster CI>0 AND maxDD<=1000bps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
