#!/usr/bin/env python3
"""Replay the CURRENT paper scalper's exact rules over the storm-event library.

Purpose
-------
`scripts/run_scalp_paper.py` is running forward in wall-clock time and needs
weeks to reach the pre-registered sample bar. This script runs the *same*
decision rules over the 16 recorded storm windows in `data/storm_events/`
(each [onset-30min, onset+90min] on a 1s grid) so we get directional evidence
in seconds instead of weeks. It is pre-validation, NOT a replacement for the
paper run.

Rules mirrored from scripts/run_scalp_paper.py (defaults, unchanged)
--------------------------------------------------------------------
* signal      : |log(bn[t] / bn[t - window_sec])| * 1e4 >= threshold, on the
                BINANCE price (`leader_return_bps`, window_sec = 5).
                `past` is the first leader sample at or after t - window_sec,
                which on a 1s grid is exactly bn[t-5].
* threshold   : 10 bps normally, 8 bps while the storm radar is armed
                (clock window 12:30-15:00 UTC, src/bot/radar.py). The armed
                flag is evaluated per signal timestamp, as the live engine
                re-evaluates it on every tick.
* direction   : continuation (ret > 0 -> LONG, ret < 0 -> SHORT).
* entry       : maker. A virtual limit is rested at the near touch at the
                signal second; it fills only on a counter-side print at or
                through the limit within fill_timeout_sec (10s). Otherwise
                the entry is a MISS (no position, no PnL).
* hold        : 60s measured FROM THE FILL, not from the signal.
* exit        : taker.
* cooldown    : 30s measured from the SIGNAL (set on every signal, including
                ones that end up missed); signals arriving inside the cooldown
                are skipped and do NOT extend it.
* concurrency : one position at a time; while a position or a resting order
                is live, no new signal is evaluated.

1s-data approximation rules (the library has no book data)
----------------------------------------------------------
1. ENTRY LIMIT PRICE = `bf_price` at the signal second. The live scalper
   posts at the near touch (best bid for LONG, best ask for SHORT); the last
   trade price is the conservative proxy for the touch we can build from
   trade data alone. For a LONG this is typically >= the true best bid, so
   the fill test is somewhat *easier* than reality; for a SHORT typically
   <= the true best ask, likewise. Direction of the resulting bias is not
   uniform - treat fill rates here as indicative, not exact.
2. FILL CHECK on 1s bars. A LONG limit L placed at second t fills at the
   first second s in (t, t + fill_timeout_sec] with `bf_sell > 0` AND
   `bf_price[s] <= L` (a taker sell print landing at or through a resting
   bid). Mirror for SHORT (`bf_buy > 0` and `bf_price[s] >= L`). This is
   coarse: `bf_price` is the LAST print of that second, so a second whose
   low traded through L but closed above it is scored as no-fill (pessimistic),
   while a second that both bought and sold is scored on its closing print
   regardless of which side printed last (can go either way). The live
   engine tests every individual print with its own taker side.
3. EXIT at the first second >= fill + hold_sec, price = `bf_price` there,
   minus taker cost (signed by side).
4. RADAR armed state is read from the row's own UTC timestamp.
5. bn_price gaps: the live scalper polls the Binance REST last-price endpoint
   once a second, which returns the last trade price whether or not a trade
   happened in that second - i.e. the live leader series is effectively
   forward-filled. The replay therefore ffills `bn_price` for signal purposes
   to match live behaviour, and reports a no-ffill sensitivity (signals only
   when both bn[t] and bn[t-5] are real prints) in section 7.

Cost model (established in docs/RESEARCH_REPORT_* and stated by the lead)
-------------------------------------------------------------------------
FX/CFD trading fee is 0%. A MAKER entry pays no fee and no spread: it fills
at the limit. The TAKER exit pays half-spread + slippage:
    burst regime (PRIMARY): 1.96 + 2.0 = 3.96 ~ 4 bps per taker side
    calm  regime (sensitivity): 0.93 + 2.0 = 2.93 ~ 3 bps per taker side
The primary number is the burst one because every exit here happens ~60s
after a burst. Missed-entry counterfactuals pay the taker cost TWICE (entry
and exit), since a taker entry crosses the spread too.

Usage:  PYTHONPATH=src python scripts/replay_scalp_storm.py
Idempotent, read-only, no network. Writes nothing.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bot.radar import StormRadar  # noqa: E402

# The fill decision is taken by the SAME class the live paper runner uses, so
# this replay cannot drift from it: scripts/run_scalp_paper.py::RestingLimit.
sys.path.insert(0, str(ROOT / "scripts"))
from run_scalp_paper import RestingLimit  # noqa: E402

EVENT_DIR = ROOT / "data" / "storm_events"

# taker cost per side, bps: half-spread + slippage
COST_BURST_BPS = 1.96 + 2.0
COST_CALM_BPS = 0.93 + 2.0
ADOPTION_BAR_BPS = 5.0          # pre-registered: >= +5 bps/trade net
ADOPTION_EVENT_BAR = 30         # pre-registered: >= 30 events


# --------------------------------------------------------------------------- #
# data structures
# --------------------------------------------------------------------------- #
@dataclass
class Signal:
    event: str
    idx: int                 # row index of the signal second
    ts: pd.Timestamp
    side: str                # LONG / SHORT
    ret_bps: float
    thr_bps: float
    armed: bool
    limit: float
    #: the live runner's own order object, used verbatim for the fill test
    order: RestingLimit | None = None
    # fill outcome
    filled: bool = False
    fill_idx: int | None = None
    fill_lag_s: float | None = None
    exit_idx: int | None = None
    entry_px: float | None = None
    exit_px: float | None = None
    gross_bps: float | None = None          # filled maker trade, pre-cost
    # counterfactual: taker entry at the signal second, same 60s hold
    cf_exit_idx: int | None = None
    cf_gross_bps: float | None = None       # pre-cost, entry at bf[signal]
    unresolved: str | None = None           # window ended before fill/exit


@dataclass
class EventResult:
    event: str
    start: pd.Timestamp
    signals: list[Signal] = field(default_factory=list)
    n_rows: int = 0
    bn_nan: int = 0
    bf_nan: int = 0
    skipped_nan_signal: int = 0


# --------------------------------------------------------------------------- #
# core replay
# --------------------------------------------------------------------------- #
def leader_return_bps(bn: np.ndarray, i: int, window: int) -> float | None:
    """Mirror of ScalpPaper.leader_return_bps on a 1s grid."""
    j = i - window
    if j < 0:
        return None
    a, b = bn[j], bn[i]
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0 or b <= 0:
        return None
    return math.log(b / a) * 1e4


def replay_event(path: Path, args, radar: StormRadar, ffill_bn: bool) -> EventResult:
    df = pd.read_csv(path, parse_dates=["ts"])
    ts = pd.to_datetime(df["ts"], utc=True)
    bf = df["bf_price"].to_numpy(dtype=float)
    buy = df["bf_buy"].to_numpy(dtype=float)
    sell = df["bf_sell"].to_numpy(dtype=float)
    bn_raw = df["bn_price"].to_numpy(dtype=float)
    bn = df["bn_price"].ffill().to_numpy(dtype=float) if ffill_bn else bn_raw

    res = EventResult(event=path.stem.replace("event_", ""), start=ts.iloc[0],
                      n_rows=len(df),
                      bn_nan=int(np.isnan(bn_raw).sum()),
                      bf_nan=int(np.isnan(bf).sum()))

    n = len(df)
    # NB: pandas may hand back datetime64[us] or [ns]; go through [s] so the
    # epoch conversion is unit-proof (a wrong unit silently kills both the
    # radar window and the cooldown).
    ts_unix = ((ts - pd.Timestamp("1970-01-01", tz="UTC"))
               // pd.Timedelta(seconds=1)).to_numpy().astype("int64")
    window = int(args.window_sec)
    hold = int(args.hold_sec)
    fill_to = int(args.fill_timeout_sec)
    cooldown = float(args.cooldown_sec)

    pending: Signal | None = None
    position: Signal | None = None
    last_signal_ts = -1e18

    for i in range(n):
        # --- 1. resting order: fill or expire (engine checks pending first) --
        if pending is not None:
            s = pending.idx
            if i <= s + fill_to:
                if not np.isfinite(bf[i]):
                    continue
                # one 1s bar -> up to two synthetic prints at the bar's closing
                # price, one per taker side that actually traded that second.
                prints = []
                if buy[i] > 0:
                    prints.append((float(ts_unix[i]), float(bf[i]), "BUY"))
                if sell[i] > 0:
                    prints.append((float(ts_unix[i]), float(bf[i]), "SELL"))
                hit = pending.order.first_fill(prints) is not None
                if hit:
                    pending.filled = True
                    pending.fill_idx = i
                    pending.fill_lag_s = float(ts_unix[i] - ts_unix[s])
                    pending.entry_px = pending.limit   # maker fills AT the limit
                    position, pending = pending, None
                continue
            # first second strictly past the timeout -> cancel, count the miss
            pending = None
            continue

        # --- 2. open position: exit hold_sec after the FILL -------------------
        if position is not None:
            if i >= position.fill_idx + hold:
                if not np.isfinite(bf[i]):
                    continue
                position.exit_idx = i
                position.exit_px = float(bf[i])
                d = 1.0 if position.side == "LONG" else -1.0
                position.gross_bps = ((position.exit_px - position.entry_px)
                                      / position.entry_px * 1e4 * d)
                position = None
            continue

        # --- 3. flat: look for a signal --------------------------------------
        ret = leader_return_bps(bn, i, window)
        if ret is None:
            continue
        armed = radar.is_armed(float(ts_unix[i]))
        thr = args.thr_armed_bps if armed else args.thr_bps
        if abs(ret) < thr:
            continue
        if ts_unix[i] - last_signal_ts < cooldown:
            continue
        if not np.isfinite(bf[i]) or bf[i] <= 0:
            res.skipped_nan_signal += 1
            continue
        last_signal_ts = float(ts_unix[i])
        side = "LONG" if ret > 0 else "SHORT"
        sig = Signal(event=res.event, idx=i, ts=ts.iloc[i], side=side,
                     ret_bps=ret, thr_bps=thr, armed=armed, limit=float(bf[i]),
                     order=RestingLimit(side=side, limit=float(bf[i]),
                                        t_signal=float(ts_unix[i]),
                                        timeout_sec=float(fill_to),
                                        size=1.0, signal_bps=ret))
        res.signals.append(sig)
        pending = sig

    # window truncation bookkeeping
    if pending is not None:
        pending.unresolved = "fill window ran past end of event file"
    if position is not None:
        position.unresolved = "hold ran past end of event file"

    # --- counterfactual: taker entry at the signal second, 60s hold ----------
    for sig in res.signals:
        k = sig.idx + hold
        if k >= n or not np.isfinite(bf[k]):
            continue
        d = 1.0 if sig.side == "LONG" else -1.0
        sig.cf_exit_idx = k
        sig.cf_gross_bps = (bf[k] - sig.limit) / sig.limit * 1e4 * d
    return res


# --------------------------------------------------------------------------- #
# stats helpers
# --------------------------------------------------------------------------- #
def net_bps(sig: Signal, cost: float) -> float:
    """Net bps of a FILLED maker trade: maker entry free, taker exit costs."""
    return sig.gross_bps - cost


def cf_net_bps(sig: Signal, cost: float) -> float:
    """Net bps of a taker entry at the signal + taker exit: pays cost twice."""
    return sig.cf_gross_bps - 2 * cost


def describe(vals: list[float]) -> dict:
    a = np.asarray(vals, dtype=float)
    if a.size == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "sd": np.nan,
                "win": np.nan, "sum": 0.0, "min": np.nan, "max": np.nan}
    return {"n": int(a.size), "mean": float(a.mean()),
            "median": float(np.median(a)),
            "sd": float(a.std(ddof=1)) if a.size > 1 else float("nan"),
            "win": float((a > 0).mean() * 100), "sum": float(a.sum()),
            "min": float(a.min()), "max": float(a.max())}


def fmt(x, nd=2, width=8):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * (width - 1) + "-"
    return f"{x:>{width}.{nd}f}"


def line(c="-", n=100):
    print(c * n)


def stat_block(title: str, vals: list[float], bar: float | None = None):
    s = describe(vals)
    print(f"  {title}")
    if s["n"] == 0:
        print("      (no observations)")
        return
    print(f"      n={s['n']:<4d} mean={s['mean']:+7.2f}  median={s['median']:+7.2f}  "
          f"sd={s['sd']:7.2f}  win%={s['win']:5.1f}  sum={s['sum']:+9.1f}  "
          f"min={s['min']:+7.1f}  max={s['max']:+7.1f}")
    if bar is not None:
        verdict = "PASS" if s["mean"] >= bar else "FAIL"
        print(f"      vs adoption bar +{bar:.0f} bps/trade -> {verdict} "
              f"(gap {s['mean'] - bar:+.2f} bps)")


# --------------------------------------------------------------------------- #
# sanity checks
# --------------------------------------------------------------------------- #
def sanity_checks(results: list[EventResult], args) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    hold = int(args.hold_sec)
    fill_to = int(args.fill_timeout_sec)

    bad_fill = [s for r in results for s in r.signals
                if s.filled and not (s.idx < s.fill_idx <= s.idx + fill_to)]
    checks.append(("no look-ahead on entry: signal < fill <= signal+%ds" % fill_to,
                   not bad_fill, f"{len(bad_fill)} violation(s)"))

    bad_exit = [s for r in results for s in r.signals
                if s.exit_idx is not None and s.exit_idx < s.fill_idx + hold]
    checks.append((f"no look-ahead on exit: exit >= fill+{hold}s",
                   not bad_exit, f"{len(bad_exit)} violation(s)"))

    gaps = []
    for r in results:
        idxs = [s.idx for s in r.signals]
        gaps += [b - a for a, b in zip(idxs, idxs[1:])]
    min_gap = min(gaps) if gaps else None
    checks.append((f"cooldown enforced: min gap between signals >= {args.cooldown_sec:.0f}s",
                   min_gap is None or min_gap >= args.cooldown_sec,
                   f"min gap = {min_gap}s" if min_gap is not None else "n/a"))

    per_ev = [len(r.signals) for r in results]
    worst = max(per_ev) if per_ev else 0
    checks.append(("plausible signal counts (a 2h storm window should give a "
                   "handful, not hundreds)", worst < 60,
                   f"max per event = {worst}, mean = {np.mean(per_ev):.1f}"))

    overlap = []
    for r in results:
        last_end = -1
        for s in r.signals:
            if s.filled and s.exit_idx is not None:
                if s.idx <= last_end:
                    overlap.append(s)
                last_end = s.exit_idx
    checks.append(("one position at a time (no overlapping trades)",
                   not overlap, f"{len(overlap)} overlap(s)"))

    unres = [s for r in results for s in r.signals if s.unresolved]
    checks.append(("window truncation (dropped, not counted as trades)",
                   True, f"{len(unres)} signal(s) truncated by file end"))
    return checks


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def report(results: list[EventResult], args, radar: StormRadar) -> None:
    all_sigs = [s for r in results for s in r.signals]
    filled = [s for s in all_sigs if s.filled and s.gross_bps is not None]
    missed = [s for s in all_sigs if not s.filled and not s.unresolved]

    line("=")
    print("REPLAY OF THE LIVE PAPER SCALPER OVER THE STORM EVENT LIBRARY")
    line("=")
    print(f"event files          : {len(results)}  ({EVENT_DIR})")
    print(f"rules                : thr {args.thr_bps:.0f} bps / armed {args.thr_armed_bps:.0f} bps"
          f" ({radar.window}), window {args.window_sec:.0f}s, maker entry,"
          f" fill timeout {args.fill_timeout_sec:.0f}s,")
    print(f"                       hold {args.hold_sec:.0f}s from fill, taker exit,"
          f" cooldown {args.cooldown_sec:.0f}s from signal, direction = continuation")
    print(f"costs                : maker entry 0 bps; taker exit "
          f"{COST_BURST_BPS:.2f} bps (burst, PRIMARY) / {COST_CALM_BPS:.2f} bps (calm, sensitivity)")

    # ---------------- per-event table ---------------------------------------
    line("=")
    print("1. PER-EVENT TABLE   (net bps at the PRIMARY burst cost of "
          f"{COST_BURST_BPS:.2f} bps per taker side)")
    line("=")
    hdr = (f"{'event':<15}{'window start (UTC)':<22}{'sig':>5}{'fill':>6}{'miss':>6}"
           f"{'fill%':>7}{'net sum':>10}{'net/trade':>11}{'win%':>7}{'armed sig':>11}{'armed?':>8}")
    print(hdr)
    line()
    for r in sorted(results, key=lambda x: x.start):
        sg = r.signals
        f_ = [s for s in sg if s.filled and s.gross_bps is not None]
        m_ = [s for s in sg if not s.filled and not s.unresolved]
        nets = [net_bps(s, COST_BURST_BPS) for s in f_]
        st = describe(nets)
        n_armed = sum(1 for s in sg if s.armed)
        armed_tag = ("all" if n_armed == len(sg) and sg else
                     ("none" if n_armed == 0 else "mixed"))
        print(f"{r.event:<15}{str(r.start)[:19]:<22}{len(sg):>5}{len(f_):>6}{len(m_):>6}"
              f"{(100*len(f_)/len(sg) if sg else float('nan')):>7.1f}"
              f"{fmt(st['sum'], 1, 10)}{fmt(st['mean'], 2, 11)}{fmt(st['win'], 1, 7)}"
              f"{n_armed:>11}{armed_tag:>8}")
    line()
    tot_f = len(filled)
    tot_m = len(missed)
    print(f"{'TOTAL':<15}{'':<22}{len(all_sigs):>5}{tot_f:>6}{tot_m:>6}"
          f"{(100*tot_f/len(all_sigs) if all_sigs else float('nan')):>7.1f}")

    # ---------------- aggregate ---------------------------------------------
    line("=")
    print("2. AGGREGATE EXPECTANCY (filled maker trades only)")
    line("=")
    print(f"  signals={len(all_sigs)}   fills={tot_f}   missed={tot_m}   "
          f"fill rate={100*tot_f/len(all_sigs) if all_sigs else float('nan'):.1f}%")
    lags = [s.fill_lag_s for s in filled if s.fill_lag_s is not None]
    if lags:
        print(f"  fill latency: mean {np.mean(lags):.2f}s  median {np.median(lags):.1f}s  "
              f"max {max(lags):.0f}s")
    print()
    stat_block("GROSS bps/trade (no costs)", [s.gross_bps for s in filled])
    print()
    stat_block(f"NET bps/trade @ burst cost {COST_BURST_BPS:.2f} bps taker exit  [PRIMARY]",
               [net_bps(s, COST_BURST_BPS) for s in filled], bar=ADOPTION_BAR_BPS)
    print()
    stat_block(f"NET bps/trade @ calm cost {COST_CALM_BPS:.2f} bps taker exit  [sensitivity]",
               [net_bps(s, COST_CALM_BPS) for s in filled], bar=ADOPTION_BAR_BPS)
    print()
    # tail-robustness + clustering: trades inside one storm are not independent,
    # so the CI is bootstrapped over EVENTS, not over trades.
    nets = [net_bps(s, COST_BURST_BPS) for s in filled]
    if nets:
        a = np.sort(np.asarray(nets))
        k = int(len(a) * 0.10)
        trimmed = a[k:len(a) - k].mean() if len(a) - 2 * k > 0 else float("nan")
        print(f"  10% trimmed mean (both tails, {k} trades cut per side): "
              f"{trimmed:+.2f} bps/trade")
        by_ev = [[net_bps(s, COST_BURST_BPS) for s in r.signals
                  if s.filled and s.gross_bps is not None] for r in results]
        by_ev = [v for v in by_ev if v]
        rng = np.random.default_rng(7)
        boot = []
        for _ in range(20000):
            pick = rng.integers(0, len(by_ev), len(by_ev))
            pool = np.concatenate([by_ev[i] for i in pick])
            boot.append(pool.mean())
        lo, hi = np.percentile(boot, [2.5, 97.5])
        p_above = float(np.mean(np.asarray(boot) >= ADOPTION_BAR_BPS))
        print(f"  event-clustered bootstrap of the mean (20k resamples of the "
              f"{len(by_ev)} events):")
        print(f"      95% CI [{lo:+.2f}, {hi:+.2f}] bps/trade   "
              f"P(mean >= +{ADOPTION_BAR_BPS:.0f} bps) = {p_above:.3f}")
    print()
    print("  per-SIGNAL expectancy (misses counted as 0 - what the strategy earns")
    print("  per opportunity, since a miss consumes the cooldown but pays nothing):")
    per_signal = [net_bps(s, COST_BURST_BPS) if s.filled and s.gross_bps is not None else 0.0
                  for s in all_sigs if not s.unresolved]
    stat_block(f"NET bps/signal @ {COST_BURST_BPS:.2f} bps", per_signal)

    # ---------------- armed split -------------------------------------------
    line("=")
    print(f"3. ARMED ({radar.window}) vs UNARMED SPLIT")
    line("=")
    for label, pick in (("ARMED   (thr 8 bps)", True), ("UNARMED (thr 10 bps)", False)):
        sg = [s for s in all_sigs if s.armed is pick]
        f_ = [s for s in sg if s.filled and s.gross_bps is not None]
        m_ = [s for s in sg if not s.filled and not s.unresolved]
        print(f"  {label}: signals={len(sg)}  fills={len(f_)}  missed={len(m_)}  "
              f"fill rate={100*len(f_)/len(sg) if sg else float('nan'):.1f}%")
        stat_block(f"    net bps/trade @ {COST_BURST_BPS:.2f}",
                   [net_bps(s, COST_BURST_BPS) for s in f_], bar=ADOPTION_BAR_BPS)
        stat_block(f"    net bps/trade @ {COST_CALM_BPS:.2f}",
                   [net_bps(s, COST_CALM_BPS) for s in f_])
        print()
    n_ev_armed = sum(1 for r in results if any(s.armed for s in r.signals))
    print(f"  events containing at least one armed signal: {n_ev_armed}/{len(results)}")

    # ---------------- missed-entry counterfactual ---------------------------
    line("=")
    print("4. MISSED-ENTRY COUNTERFACTUAL (adverse selection of maker entry)")
    line("=")
    print("  For every MISSED signal: what a TAKER entry at the signal second would")
    print("  have earned over the same 60s hold, paying the taker cost on BOTH legs.")
    print("  Maker-filled trades are shown on the same taker basis for comparison.")
    print()
    cf_missed = [cf_net_bps(s, COST_BURST_BPS) for s in missed if s.cf_gross_bps is not None]
    cf_filled = [cf_net_bps(s, COST_BURST_BPS) for s in filled if s.cf_gross_bps is not None]
    cf_all = [cf_net_bps(s, COST_BURST_BPS) for s in all_sigs
              if s.cf_gross_bps is not None and not s.unresolved]
    stat_block(f"MISSED signals, as taker @ {COST_BURST_BPS:.2f} bps x2", cf_missed)
    print()
    stat_block(f"FILLED signals, as taker @ {COST_BURST_BPS:.2f} bps x2 (same trades, taker basis)",
               cf_filled)
    print()
    stat_block(f"ALL signals, taker-entry strategy @ {COST_BURST_BPS:.2f} bps x2",
               cf_all, bar=ADOPTION_BAR_BPS)
    print()
    m_mean = describe(cf_missed)["mean"]
    f_mean = describe(cf_filled)["mean"]
    if np.isfinite(m_mean) and np.isfinite(f_mean):
        print(f"  adverse selection = filled - missed (taker basis) = "
              f"{f_mean - m_mean:+.2f} bps")
        print("  A negative number means the fills we DO get are the worse half of the")
        print("  opportunity set: the market came back to our limit precisely when it was")
        print("  about to keep going against us, while the runners left us behind.")
    print()
    stat_block(f"MAKER (as executed) net @ {COST_BURST_BPS:.2f} vs TAKER-all above",
               [net_bps(s, COST_BURST_BPS) for s in filled])

    # ---------------- side / direction breakdown ----------------------------
    line("=")
    print("5. BREAKDOWN BY SIDE")
    line("=")
    for side in ("LONG", "SHORT"):
        f_ = [s for s in filled if s.side == side]
        sg = [s for s in all_sigs if s.side == side]
        print(f"  {side}: signals={len(sg)}  fills={len(f_)}  "
              f"fill rate={100*len(f_)/len(sg) if sg else float('nan'):.1f}%")
        stat_block(f"    net bps/trade @ {COST_BURST_BPS:.2f}",
                   [net_bps(s, COST_BURST_BPS) for s in f_])
    print()
    print("  breakeven taker cost (net mean = 0) for the maker book:")
    g = describe([s.gross_bps for s in filled])["mean"]
    if np.isfinite(g):
        print(f"    gross mean {g:+.2f} bps -> breaks even at a taker exit cost of "
              f"{g:.2f} bps (we assume {COST_BURST_BPS:.2f}); "
              f"needs <= {g - ADOPTION_BAR_BPS:.2f} bps to clear the +5 bar")

    # ---------------- sanity checks -----------------------------------------
    line("=")
    print("6. SANITY CHECKS")
    line("=")
    for name, ok, detail in sanity_checks(results, args):
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<62} {detail}")
    nan_sig = sum(r.skipped_nan_signal for r in results)
    print(f"  [OK ] signals skipped for missing bf_price                     {nan_sig}")


def sensitivity_no_ffill(args, radar: StormRadar, paths: list[Path]) -> None:
    line("=")
    print("7. SENSITIVITY: no forward-fill of bn_price")
    line("=")
    print("  Primary run ffills bn_price because the live scalper polls the Binance")
    print("  REST last-price endpoint every second (it always returns a price).")
    print("  Here a signal is only allowed when bn[t] and bn[t-5] are both real prints.")
    res = [replay_event(p, args, radar, ffill_bn=False) for p in paths]
    sigs = [s for r in res for s in r.signals]
    fl = [s for s in sigs if s.filled and s.gross_bps is not None]
    print(f"  signals={len(sigs)}  fills={len(fl)}  "
          f"fill rate={100*len(fl)/len(sigs) if sigs else float('nan'):.1f}%")
    stat_block(f"  net bps/trade @ {COST_BURST_BPS:.2f}",
               [net_bps(s, COST_BURST_BPS) for s in fl], bar=ADOPTION_BAR_BPS)


def caveats(results: list[EventResult]) -> None:
    line("=")
    print("8. CAVEATS - READ BEFORE QUOTING ANY NUMBER ABOVE")
    line("=")
    n = len(results)
    print(f"  1. SAMPLE. n = {n} storm events, below the pre-registered "
          f"{ADOPTION_EVENT_BAR}-event bar.")
    print("     This replay is DIRECTIONAL EVIDENCE ONLY. The pre-registered decision")
    print("     rule is the forward paper run; nothing here promotes or rejects the")
    print("     strategy on its own.")
    print("  2. 1s BARS vs TICK REALITY. The live engine sees every print with its own")
    print("     taker side and ticks at 250ms. Here one bar carries one closing price,")
    print("     one buy volume and one sell volume per second: intrabar sequence is lost,")
    print("     so both fills and misses are approximations.")
    print("  3. LAST-TRADE-AS-TOUCH. There is no book history, so the resting limit is")
    print("     priced at the last trade rather than the best bid/ask. Real limits sit")
    print("     inside/at the spread; fill rates and entry prices are proxies.")
    print("  4. bf_price IS FORWARD-FILLED within each window by the library builder, so")
    print("     an exit or fill test in a quiet second reuses a stale print.")
    print("  5. QUEUE POSITION IS IGNORED (permissive at-or-through rule, the optimistic")
    print("     bound of scripts/research_scalp_opt.py). A strict through-rule would fill")
    print("     less often and, per that study, differently selected.")
    print("  6. WINDOW EDGES. Signals whose fill window or 60s hold ran past the end of an")
    print("     event file are dropped, not scored.")
    print("  7. NO LATENCY, NO PARTIALS, NO REJECTS, no funding/holding cost, and the")
    print("     0% CFD fee is taken at face value.")
    print("  8. STORM-ONLY SAMPLE. Every window is [onset-30m, onset+90m] of a detected")
    print("     storm, so this is the strategy's best regime by construction. Live, the")
    print("     scalper also runs through calm hours where bursts are rarer and thinner.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # defaults deliberately identical to scripts/run_scalp_paper.py
    ap.add_argument("--thr-bps", type=float, default=10.0)
    ap.add_argument("--thr-armed-bps", type=float, default=8.0)
    ap.add_argument("--radar-start", default="12:30")
    ap.add_argument("--radar-end", default="15:00")
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--hold-sec", type=float, default=60.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--fill-timeout-sec", type=float, default=10.0)
    ap.add_argument("--event-dir", default=str(EVENT_DIR))
    args = ap.parse_args()

    paths = sorted(Path(args.event_dir).glob("event_*.csv"))
    if not paths:
        print(f"no event files in {args.event_dir}", file=sys.stderr)
        return 1
    radar = StormRadar(start=args.radar_start, end=args.radar_end)
    results = [replay_event(p, args, radar, ffill_bn=True) for p in paths]

    report(results, args, radar)
    sensitivity_no_ffill(args, radar, paths)
    caveats(results)
    line("=")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
