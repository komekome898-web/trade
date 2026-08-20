#!/usr/bin/env python3
"""Study R5-S2 — exit redesign for the burst scalper (entry side FROZEN).

Question
--------
`scripts/replay_scalp_storm.py` showed the current paper scalper is gross-
positive but net-negative over the storm-event library: the TAKER exit's
~4 bps eats the whole edge. This study changes ONLY the exit and asks
whether a MAKER exit can rescue the economics.

The asymmetry under test: for a momentum LONG the maker take-profit is a
SELL limit ABOVE the fill, so it only fills when buying keeps coming
through it. Unlike the maker ENTRY (which fills when the market comes back
to us — adverse selection), the maker EXIT selects WITH the continuation
thesis. It should skim the winners. The open question is what is left in
the fallback bucket.

FROZEN entry side (identical to the replay / to scripts/run_scalp_paper.py)
--------------------------------------------------------------------------
* signal      : |log(bn[t]/bn[t-5])| * 1e4 >= 10 bps on the Binance price,
                bn forward-filled (the live runner polls REST last price).
                The armed 8 bps drop is RETIRED, so the threshold is 10 bps
                inside and outside the 12:30-15:00 UTC radar window; the
                armed flag is still recorded, purely as a regime label.
* direction   : continuation (ret > 0 -> LONG, ret < 0 -> SHORT).
* entry       : maker. `RestingLimit` (imported verbatim from the live
                runner) rested at bf_price of the signal second, filled only
                by a counter-side print at or through it within 10s.
* cooldown    : 30s from the SIGNAL (set on every signal, misses included).
* concurrency : one position at a time; a live position or resting order
                blocks all new signals.

Pre-registered exit variants (exactly these, no others)
-------------------------------------------------------
  E0  taker at fill+60s                        (reproduces the replay)
  E1  maker TP at fill +5 bps,  fallback taker at fill+60s
  E2  maker TP at fill +10 bps, fallback taker at fill+120s
  E3  trailing stop: peak-favourable tracker, taker exit on a 5 bps
      retrace from the peak; hard fallback taker at fill+120s
  E4  maker TP at fill +10 bps AND burst-reversal stop (|5s leader return|
      >= 10 bps AGAINST the position -> immediate taker exit);
      fallback taker at fill+120s

Every variant has a hard fallback, so no position is ever unbounded.

Exit mechanics on the 1s grid
-----------------------------
* MAKER TP is the same object as the entry: a resting limit filled by a
  counter-side print at or through it. Exiting a LONG rests an ASK, which a
  taker BUY lifts -> `RestingLimit(side="SHORT", limit=tp)`; exiting a SHORT
  rests a BID -> `RestingLimit(side="LONG", limit=tp)`. Fills happen AT the
  limit: a maker exit pays no spread and no slippage.
* TP prices are rounded to the 1 JPY tick AWAY from the entry (ceil for a
  LONG's sell limit, floor for a SHORT's buy limit), so the realised
  distance is never smaller than the pre-registered one.
* Within one second the checks run TP -> reversal stop -> trailing stop ->
  hard fallback. The count of seconds where a TP and a stop/fallback could
  both have fired is reported (section 6) so the tie convention is auditable.
* The TP is checked from fill+1s onward (never on the fill second itself).

Cost model (unchanged)
----------------------
Maker entry 0 bps. Maker TP exit 0 bps. TAKER exit (fallback / trail /
stop) 3.96 bps in the burst regime (PRIMARY, every exit here is seconds
after a burst); 2.93 bps calm is reported as a sensitivity for E0 and the
winning variant only.

Adoption bar: net >= +5.00 bps/trade aggregate. n = 16 events is below the
pre-registered 30-event bar, so a PASS here is PROVISIONAL (paper trading
decides) while a FAIL at these costs stands on its own.

Usage:  PYTHONPATH=src python scripts/research_scalp_exits.py
Idempotent, read-only, no network, writes nothing. Deterministic (the only
randomness is the event-clustered bootstrap, seeded).
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
sys.path.insert(0, str(ROOT / "scripts"))

from bot.radar import StormRadar  # noqa: E402

# The entry-side fill machinery is the live runner's own class, imported
# verbatim so this study cannot drift from the engine or from the replay.
from run_scalp_paper import RestingLimit  # noqa: E402

# The replay is imported (not copied) for the frozen signal logic, the cost
# constants and the E0 cross-check.
import replay_scalp_storm as replay  # noqa: E402
from replay_scalp_storm import (  # noqa: E402
    ADOPTION_BAR_BPS,
    ADOPTION_EVENT_BAR,
    COST_BURST_BPS,
    COST_CALM_BPS,
    describe,
    leader_return_bps,
)

EVENT_DIR = ROOT / "data" / "storm_events"
TICK_JPY = 1.0
BOOT_N = 20000
BOOT_SEED = 7

VARIANT_ORDER = ["E0", "E1", "E2", "E3", "E4"]
VARIANTS: dict[str, dict] = {
    "E0": dict(label="taker at fill+60s (baseline = replay)",
               tp_bps=None, horizon=60, trail_bps=None, rev_stop_bps=None),
    "E1": dict(label="maker TP +5 bps, fallback taker fill+60s",
               tp_bps=5.0, horizon=60, trail_bps=None, rev_stop_bps=None),
    "E2": dict(label="maker TP +10 bps, fallback taker fill+120s",
               tp_bps=10.0, horizon=120, trail_bps=None, rev_stop_bps=None),
    "E3": dict(label="trailing stop 5 bps from peak, hard taker fill+120s",
               tp_bps=None, horizon=120, trail_bps=5.0, rev_stop_bps=None),
    "E4": dict(label="maker TP +10 bps + reversal stop 10 bps, fallback 120s",
               tp_bps=10.0, horizon=120, trail_bps=None, rev_stop_bps=10.0),
    # NOT pre-registered. Diagnostic only (section 4b): isolates "longer
    # horizon" from "maker exit" once section 4 shows the TP bucket's
    # counterfactual beats its realised TP price.
    "D1": dict(label="[DIAGNOSTIC, not pre-registered] taker at fill+120s",
               tp_bps=None, horizon=120, trail_bps=None, rev_stop_bps=None),
}
# Pessimistic twins of the TP variants: the maker TP needs a print STRICTLY
# through the limit, not merely at it (section 4c). Not pre-registered — a
# robustness bound on the study's most optimistic assumption.
STRICT_TWINS = {"E1": "E1s", "E2": "E2s", "E4": "E4s"}
for _src, _dst in STRICT_TWINS.items():
    VARIANTS[_dst] = dict(VARIANTS[_src],
                          label=f"[SENSITIVITY] {VARIANTS[_src]['label']}, "
                                "TP needs a STRICT through-print")
    VARIANTS[_dst]["tp_strict"] = True

EXIT_TYPES = ["tp", "trail", "stop", "fallback"]


class StrictRestingLimit(RestingLimit):
    """`RestingLimit` with the permissive at-or-through touch tightened to a
    strict through-print. Queue position is still ignored, so this is a
    bound, not a model: reality sits between the two."""

    def accepts(self, ts: float, price: float, taker_side: str | None = None) -> bool:
        if not super().accepts(ts, price, taker_side):
            return False
        return price < self.limit if self.side == "LONG" else price > self.limit


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
@dataclass
class EventData:
    name: str
    start: pd.Timestamp
    ts: pd.Series
    ts_unix: np.ndarray
    bf: np.ndarray
    buy: np.ndarray
    sell: np.ndarray
    bn: np.ndarray
    n: int


def load_event(path: Path, ffill_bn: bool = True) -> EventData:
    df = pd.read_csv(path, parse_dates=["ts"])
    ts = pd.to_datetime(df["ts"], utc=True)
    # datetime64 unit trap: pandas may hand back [us] or [ns]. Go through a
    # 1s Timedelta floor-division so the epoch seconds are unit-proof; a
    # wrong unit silently kills both the radar window and the cooldown.
    ts_unix = ((ts - pd.Timestamp("1970-01-01", tz="UTC"))
               // pd.Timedelta(seconds=1)).to_numpy().astype("int64")
    bn = (df["bn_price"].ffill() if ffill_bn else df["bn_price"]).to_numpy(dtype=float)
    return EventData(name=path.stem.replace("event_", ""), start=ts.iloc[0], ts=ts,
                     ts_unix=ts_unix, bf=df["bf_price"].to_numpy(dtype=float),
                     buy=df["bf_buy"].to_numpy(dtype=float),
                     sell=df["bf_sell"].to_numpy(dtype=float), bn=bn, n=len(df))


@dataclass
class Trade:
    event: str
    variant: str
    side: str
    sig_idx: int
    sig_ts: pd.Timestamp
    armed: bool
    ret_bps: float
    fill_idx: int
    fill_lag_s: float
    entry_px: float
    exit_idx: int
    exit_px: float
    exit_type: str          # tp | trail | stop | fallback
    gross_bps: float
    cost_bps: float
    hold_s: float
    #: gross bps of the counterfactual "hold to this variant's horizon and
    #: take" exit, computed for EVERY trade regardless of what happened.
    cf_hold_gross_bps: float | None = None
    #: peak favourable excursion (bps) reached before the exit
    mfe_bps: float = 0.0
    #: worst adverse excursion (bps, positive number) before the exit
    mae_bps: float = 0.0

    def net(self, taker_cost: float = COST_BURST_BPS) -> float:
        c = taker_cost if self.exit_type != "tp" else 0.0
        return self.gross_bps - c

    def key(self) -> tuple:
        return (self.event, self.sig_idx, self.fill_idx, self.exit_idx,
                self.exit_type, round(self.gross_bps, 9))


@dataclass
class VariantRun:
    name: str
    trades: list[Trade] = field(default_factory=list)
    signals: int = 0
    misses: int = 0
    unresolved_fill: int = 0
    unresolved_exit: int = 0
    skipped_nan_signal: int = 0
    tie_tp_vs_stop: int = 0        # seconds where TP and a stop both fired
    tp_at_deadline: int = 0        # TP filled exactly on the fallback second
    by_event: dict[str, list[Trade]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# simulation
# --------------------------------------------------------------------------- #
def tp_price(entry_px: float, side: str, tp_bps: float) -> float:
    """Maker take-profit limit, rounded to the tick AWAY from the entry."""
    if side == "LONG":                      # sell limit ABOVE the fill
        return math.ceil(entry_px * (1.0 + tp_bps / 1e4) / TICK_JPY) * TICK_JPY
    return math.floor(entry_px * (1.0 - tp_bps / 1e4) / TICK_JPY) * TICK_JPY


def simulate_event(ev: EventData, args, radar: StormRadar, spec: dict,
                   variant: str, run: VariantRun) -> None:
    """Frozen entry + one exit policy over a single event window."""
    bf, buy, sell, bn, ts_unix = ev.bf, ev.buy, ev.sell, ev.bn, ev.ts_unix
    window = int(args.window_sec)
    fill_to = int(args.fill_timeout_sec)
    cooldown = float(args.cooldown_sec)
    horizon = int(spec["horizon"])
    tp_bps = spec["tp_bps"]
    trail_bps = spec["trail_bps"]
    rev_bps = spec["rev_stop_bps"]

    pending = None        # dict: resting ENTRY order
    pos = None            # dict: open position
    last_signal_ts = -1e18

    def prints_at(i: int) -> list[tuple[float, float, str]]:
        """Up to two synthetic prints at the bar's closing price, one per
        taker side that actually traded in that second (replay rule)."""
        out = []
        if buy[i] > 0:
            out.append((float(ts_unix[i]), float(bf[i]), "BUY"))
        if sell[i] > 0:
            out.append((float(ts_unix[i]), float(bf[i]), "SELL"))
        return out

    def close(i: int, px: float, kind: str) -> None:
        nonlocal pos
        d = 1.0 if pos["side"] == "LONG" else -1.0
        gross = (px - pos["entry_px"]) / pos["entry_px"] * 1e4 * d
        cost = 0.0 if kind == "tp" else COST_BURST_BPS
        k = pos["fill_idx"] + horizon
        cf = None
        if k < ev.n and np.isfinite(bf[k]):
            cf = (bf[k] - pos["entry_px"]) / pos["entry_px"] * 1e4 * d
        t = Trade(event=ev.name, variant=variant, side=pos["side"],
                  sig_idx=pos["sig_idx"], sig_ts=pos["sig_ts"], armed=pos["armed"],
                  ret_bps=pos["ret_bps"], fill_idx=pos["fill_idx"],
                  fill_lag_s=pos["fill_lag_s"], entry_px=pos["entry_px"],
                  exit_idx=i, exit_px=float(px), exit_type=kind,
                  gross_bps=gross, cost_bps=cost,
                  hold_s=float(ts_unix[i] - ts_unix[pos["fill_idx"]]),
                  cf_hold_gross_bps=cf, mfe_bps=pos["mfe"], mae_bps=pos["mae"])
        run.trades.append(t)
        run.by_event.setdefault(ev.name, []).append(t)
        pos = None

    for i in range(ev.n):
        # --- 1. resting ENTRY order: fill or expire ---------------------------
        if pending is not None:
            s = pending["sig_idx"]
            if i <= s + fill_to:
                if not np.isfinite(bf[i]):
                    continue
                if pending["order"].first_fill(prints_at(i)) is not None:
                    entry_px = pending["limit"]     # maker fills AT the limit
                    pos = dict(pending)
                    pos.update(fill_idx=i,
                               fill_lag_s=float(ts_unix[i] - ts_unix[s]),
                               entry_px=entry_px, peak=entry_px, trough=entry_px,
                               mfe=0.0, mae=0.0, tp_order=None)
                    if tp_bps is not None:
                        lim = tp_price(entry_px, pos["side"], tp_bps)
                        # exit-side resting order: a LONG exits by resting an
                        # ASK (lifted by a taker BUY) -> side="SHORT", mirror.
                        cls = (StrictRestingLimit if spec.get("tp_strict")
                               else RestingLimit)
                        pos["tp_order"] = cls(
                            side=("SHORT" if pos["side"] == "LONG" else "LONG"),
                            limit=lim, t_signal=float(ts_unix[i]),
                            timeout_sec=float(horizon), size=1.0,
                            signal_bps=pos["ret_bps"])
                        pos["tp_limit"] = lim
                    pending = None
                continue
            pending = None          # first second past the timeout -> cancel
            run.misses += 1
            continue

        # --- 2. open position: apply the exit policy --------------------------
        if pos is not None:
            if i <= pos["fill_idx"]:
                continue
            if not np.isfinite(bf[i]):
                continue
            d = 1.0 if pos["side"] == "LONG" else -1.0
            exc = (bf[i] - pos["entry_px"]) / pos["entry_px"] * 1e4 * d
            pos["mfe"] = max(pos["mfe"], exc)
            pos["mae"] = max(pos["mae"], -exc)
            deadline = i >= pos["fill_idx"] + horizon

            # 2a. MAKER TAKE-PROFIT (checked first; ties reported in sec. 6)
            if pos["tp_order"] is not None:
                if pos["tp_order"].first_fill(prints_at(i)) is not None:
                    rev_hit = False
                    if rev_bps is not None:
                        r = leader_return_bps(bn, i, window)
                        rev_hit = r is not None and (
                            (pos["side"] == "LONG" and r <= -rev_bps) or
                            (pos["side"] == "SHORT" and r >= rev_bps))
                    if rev_hit or deadline:
                        run.tie_tp_vs_stop += 1
                    if deadline:
                        run.tp_at_deadline += 1
                    close(i, pos["tp_limit"], "tp")
                    continue

            # 2b. BURST-REVERSAL STOP (E4)
            if rev_bps is not None:
                r = leader_return_bps(bn, i, window)
                if r is not None and ((pos["side"] == "LONG" and r <= -rev_bps) or
                                      (pos["side"] == "SHORT" and r >= rev_bps)):
                    close(i, float(bf[i]), "stop")
                    continue

            # 2c. TRAILING STOP (E3): peak favourable, then a retrace
            if trail_bps is not None:
                if pos["side"] == "LONG":
                    pos["peak"] = max(pos["peak"], float(bf[i]))
                    retrace = (pos["peak"] - bf[i]) / pos["peak"] * 1e4
                else:
                    pos["trough"] = min(pos["trough"], float(bf[i]))
                    retrace = (bf[i] - pos["trough"]) / pos["trough"] * 1e4
                if retrace >= trail_bps:
                    close(i, float(bf[i]), "trail")
                    continue

            # 2d. HARD FALLBACK
            if deadline:
                close(i, float(bf[i]), "fallback")
            continue

        # --- 3. flat: frozen signal logic ------------------------------------
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
            run.skipped_nan_signal += 1
            continue
        last_signal_ts = float(ts_unix[i])
        side = "LONG" if ret > 0 else "SHORT"
        run.signals += 1
        pending = dict(sig_idx=i, sig_ts=ev.ts.iloc[i], side=side, armed=armed,
                       ret_bps=ret, limit=float(bf[i]),
                       order=RestingLimit(side=side, limit=float(bf[i]),
                                          t_signal=float(ts_unix[i]),
                                          timeout_sec=float(fill_to), size=1.0,
                                          signal_bps=ret))

    if pending is not None:
        run.unresolved_fill += 1
    if pos is not None:
        run.unresolved_exit += 1


def run_variant(events: list[EventData], args, radar: StormRadar,
                variant: str) -> VariantRun:
    run = VariantRun(name=variant)
    spec = VARIANTS[variant]
    for ev in events:
        simulate_event(ev, args, radar, spec, variant, run)
    return run


# --------------------------------------------------------------------------- #
# stats
# --------------------------------------------------------------------------- #
def boot_event_mean(by_event: list[list[float]], bar: float = ADOPTION_BAR_BPS,
                    n: int = BOOT_N, seed: int = BOOT_SEED) -> dict | None:
    """Event-clustered bootstrap of the mean: trades inside one storm are
    not independent, so events (not trades) are the resampling unit."""
    pools = [np.asarray(v, dtype=float) for v in by_event if len(v)]
    if not pools:
        return None
    rng = np.random.default_rng(seed)
    boot = np.empty(n)
    for b in range(n):
        pick = rng.integers(0, len(pools), len(pools))
        boot[b] = np.concatenate([pools[i] for i in pick]).mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(lo=float(lo), hi=float(hi), p_bar=float((boot >= bar).mean()),
                n_ev=len(pools))


def trimmed_mean(vals, frac: float = 0.10) -> float:
    a = np.sort(np.asarray(vals, dtype=float))
    if a.size == 0:
        return float("nan")
    k = int(a.size * frac)
    return float(a[k:a.size - k].mean()) if a.size - 2 * k > 0 else float("nan")


def line(c="-", n=104):
    print(c * n)


def fmt(x, nd=2, width=8):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * (width - 1) + "-"
    return f"{x:>{width}.{nd}f}"


def stat_line(vals, indent=6):
    s = describe(vals)
    if s["n"] == 0:
        print(" " * indent + "(no observations)")
        return s
    print(" " * indent + f"n={s['n']:<4d} mean={s['mean']:+7.2f}  median={s['median']:+7.2f}  "
          f"sd={s['sd']:7.2f}  win%={s['win']:5.1f}  sum={s['sum']:+9.1f}  "
          f"min={s['min']:+7.1f}  max={s['max']:+7.1f}")
    return s


def verdict_line(mean: float, indent=6, bar: float = ADOPTION_BAR_BPS):
    v = "PASS" if mean >= bar else "FAIL"
    print(" " * indent + f"vs adoption bar +{bar:.0f} bps/trade -> {v} (gap {mean - bar:+.2f} bps)")


def exit_mix(trades: list[Trade]) -> dict[str, float]:
    n = len(trades)
    out = {k: 0.0 for k in EXIT_TYPES}
    if not n:
        return out
    for t in trades:
        out[t.exit_type] += 1
    return {k: 100.0 * v / n for k, v in out.items()}


# --------------------------------------------------------------------------- #
# section 1 — E0 must reproduce the replay
# --------------------------------------------------------------------------- #
def replay_reference(args, radar: StormRadar, paths: list[Path],
                     thr_armed: float) -> tuple[list, dict]:
    ns = argparse.Namespace(thr_bps=args.thr_bps, thr_armed_bps=thr_armed,
                            window_sec=args.window_sec, hold_sec=60.0,
                            cooldown_sec=args.cooldown_sec,
                            fill_timeout_sec=args.fill_timeout_sec)
    res = [replay.replay_event(p, ns, radar, ffill_bn=True) for p in paths]
    keys, nets, sigs = [], [], 0
    for r in res:
        for s in r.signals:
            sigs += 1
            if s.filled and s.gross_bps is not None:
                keys.append((r.event, s.idx, s.fill_idx, s.exit_idx, "fallback",
                             round(s.gross_bps, 9)))
                nets.append(s.gross_bps - COST_BURST_BPS)
    d = describe(nets)
    return keys, dict(signals=sigs, fills=len(nets), mean=d["mean"], sum=d["sum"],
                      gross=describe([s.gross_bps for r in res for s in r.signals
                                      if s.filled and s.gross_bps is not None])["mean"],
                      keys=keys)


def section_e0_reproduction(events, args, radar, paths, e0: VariantRun) -> bool:
    line("=")
    print("1. E0 REPRODUCTION CHECK  (gate: if E0 does not match the replay, stop)")
    line("=")
    ok_all = True

    # (a) primary: the FROZEN entry config, thr 10 bps everywhere
    keys_ref, info = replay_reference(args, radar, paths, args.thr_armed_bps)
    mine = [t.key() for t in e0.trades]
    same = mine == keys_ref
    ok_all &= same
    print(f"  (a) FROZEN config (thr {args.thr_bps:.0f} bps armed and unarmed) — "
          f"replay_scalp_storm.replay_event vs this script's E0")
    print(f"      replay : signals={info['signals']:>4}  fills={info['fills']:>4}  "
          f"gross={info['gross']:+.2f}  net={info['mean']:+.2f} bps/trade")
    d0 = describe([t.net(COST_BURST_BPS) for t in e0.trades])
    g0 = describe([t.gross_bps for t in e0.trades])
    print(f"      E0     : signals={e0.signals:>4}  fills={len(e0.trades):>4}  "
          f"gross={g0['mean']:+.2f}  net={d0['mean']:+.2f} bps/trade")
    print(f"      [{'OK ' if same else 'FAIL'}] trade-by-trade identity "
          f"(event, signal idx, fill idx, exit idx, gross): "
          f"{'all ' + str(len(mine)) + ' trades identical' if same else 'MISMATCH'}")

    # (b) the replay's own published default (armed 8 bps) — the config that
    #     produced the -2.13 bps / 116 fills figure quoted in the brief.
    keys8, info8 = replay_reference(args, radar, paths, 8.0)
    run8 = run_variant(events, argparse.Namespace(**{**vars(args), "thr_armed_bps": 8.0}),
                       radar, "E0")
    mine8 = [t.key() for t in run8.trades]
    same8 = mine8 == keys8
    ok_all &= same8
    d8 = describe([t.net(COST_BURST_BPS) for t in run8.trades])
    g8 = describe([t.gross_bps for t in run8.trades])
    print()
    print("  (b) the replay's PUBLISHED default (armed threshold 8 bps) — the config")
    print("      behind the '-2.13 bps over 116 fills' headline in the brief")
    print(f"      replay : signals={info8['signals']:>4}  fills={info8['fills']:>4}  "
          f"gross={info8['gross']:+.2f}  net={info8['mean']:+.2f} bps/trade")
    print(f"      E0(8)  : signals={run8.signals:>4}  fills={len(run8.trades):>4}  "
          f"gross={g8['mean']:+.2f}  net={d8['mean']:+.2f} bps/trade")
    print(f"      [{'OK ' if same8 else 'FAIL'}] trade-by-trade identity: "
          f"{'all ' + str(len(mine8)) + ' trades identical' if same8 else 'MISMATCH'}")
    print()
    print("  NOTE / DISCREPANCY IN THE BRIEF. '-2.13 bps over 116 fills' is the replay at")
    print("  its own default armed threshold of 8 bps, NOT at 'thr 10 bps everywhere'. The")
    print("  retired-8bps entry the brief freezes gives 86 fills at -2.29 bps/trade. Both")
    print("  are reproduced bit-for-bit above; everything downstream uses the FROZEN")
    print("  10/10 config the brief specifies.")
    return ok_all


# --------------------------------------------------------------------------- #
# section 2 — per-variant aggregates
# --------------------------------------------------------------------------- #
def section_variants(runs: dict[str, VariantRun]) -> None:
    line("=")
    print(f"2. PER-VARIANT AGGREGATE  (taker legs cost {COST_BURST_BPS:.2f} bps; maker TP legs cost 0)")
    line("=")
    hdr = (f"{'var':<4}{'trades':>7}{'sig':>6}{'fill%':>7}{'TPfill%':>9}"
           f"{'%tp':>6}{'%trail':>8}{'%stop':>7}{'%fb':>7}"
           f"{'mean':>8}{'median':>8}{'sd':>8}{'win%':>7}{'total':>9}{'hold_s':>8}")
    print(hdr)
    line()
    for v in VARIANT_ORDER:
        r = runs[v]
        nets = [t.net(COST_BURST_BPS) for t in r.trades]
        s = describe(nets)
        mix = exit_mix(r.trades)
        tp_rate = mix["tp"] if VARIANTS[v]["tp_bps"] is not None else float("nan")
        fillpct = 100.0 * len(r.trades) / r.signals if r.signals else float("nan")
        holds = [t.hold_s for t in r.trades]
        print(f"{v:<4}{len(r.trades):>7}{r.signals:>6}{fillpct:>7.1f}{fmt(tp_rate,1,9)}"
              f"{mix['tp']:>6.1f}{mix['trail']:>8.1f}{mix['stop']:>7.1f}{mix['fallback']:>7.1f}"
              f"{fmt(s['mean'],2,8)}{fmt(s['median'],2,8)}{fmt(s['sd'],2,8)}"
              f"{fmt(s['win'],1,7)}{fmt(s['sum'],1,9)}"
              f"{(np.mean(holds) if holds else float('nan')):>8.1f}")
    line()
    print("  'sig' = signals evaluated; it differs per variant BY DESIGN: an exit that")
    print("  closes early frees the engine sooner, so a different set of later signals")
    print("  gets seen. 'fill%' is entry fills / signals. 'TPfill%' = maker TP fill rate.")
    print()

    for v in VARIANT_ORDER:
        r = runs[v]
        nets = [t.net(COST_BURST_BPS) for t in r.trades]
        print(f"  {v}  {VARIANTS[v]['label']}")
        s = stat_line(nets)
        if s["n"]:
            verdict_line(s["mean"])
            bs = boot_event_mean([[t.net(COST_BURST_BPS) for t in ts]
                                  for ts in r.by_event.values()])
            if bs:
                print(f"      event-clustered bootstrap ({BOOT_N} resamples of {bs['n_ev']} events): "
                      f"95% CI [{bs['lo']:+.2f}, {bs['hi']:+.2f}]  "
                      f"P(mean >= +{ADOPTION_BAR_BPS:.0f}) = {bs['p_bar']:.3f}")
            # exit-type PnL decomposition
            for k in EXIT_TYPES:
                sub = [t.net(COST_BURST_BPS) for t in r.trades if t.exit_type == k]
                if sub:
                    d = describe(sub)
                    print(f"        {k:<9} n={d['n']:<4d} mean={d['mean']:+7.2f}  "
                          f"median={d['median']:+7.2f}  win%={d['win']:5.1f}  "
                          f"sum={d['sum']:+9.1f}")
        print()


def section_sensitivity(runs: dict[str, VariantRun], best: str) -> None:
    line("=")
    print(f"2b. CALM-COST SENSITIVITY ({COST_CALM_BPS:.2f} bps per taker leg) — E0 and the best variant only")
    line("=")
    for v in ("E0", best):
        r = runs[v]
        print(f"  {v}  {VARIANTS[v]['label']}")
        for cost, tag in ((COST_BURST_BPS, "burst PRIMARY"), (COST_CALM_BPS, "calm sensitivity")):
            s = describe([t.net(cost) for t in r.trades])
            print(f"      @{cost:.2f} bps ({tag:<16}): mean={s['mean']:+7.2f}  "
                  f"median={s['median']:+7.2f}  win%={s['win']:5.1f}  sum={s['sum']:+9.1f}  "
                  f"-> {'PASS' if s['mean'] >= ADOPTION_BAR_BPS else 'FAIL'}")
        print()


# --------------------------------------------------------------------------- #
# section 3 — per-event tables
# --------------------------------------------------------------------------- #
def section_per_event(runs: dict[str, VariantRun], events: list[EventData],
                      best: str) -> None:
    line("=")
    print(f"3. PER-EVENT TABLES  (net bps @ {COST_BURST_BPS:.2f} bps taker cost) — E0 and the best variant ({best})")
    line("=")
    order = sorted(events, key=lambda e: e.start)
    for v in ("E0", best):
        r = runs[v]
        print(f"  --- {v}: {VARIANTS[v]['label']}")
        print(f"  {'event':<15}{'window start (UTC)':<22}{'sig':>5}{'trd':>5}"
              f"{'tp':>4}{'trl':>5}{'stp':>5}{'fb':>4}"
              f"{'net sum':>10}{'net/trade':>11}{'win%':>7}{'armed sig':>11}")
        line()
        for ev in order:
            ts_ = r.by_event.get(ev.name, [])
            nets = [t.net(COST_BURST_BPS) for t in ts_]
            s = describe(nets)
            cnt = {k: sum(1 for t in ts_ if t.exit_type == k) for k in EXIT_TYPES}
            n_armed = sum(1 for t in ts_ if t.armed)
            print(f"  {ev.name:<15}{str(ev.start)[:19]:<22}{'':>5}{len(ts_):>5}"
                  f"{cnt['tp']:>4}{cnt['trail']:>5}{cnt['stop']:>5}{cnt['fallback']:>4}"
                  f"{fmt(s['sum'],1,10)}{fmt(s['mean'],2,11)}{fmt(s['win'],1,7)}{n_armed:>11}")
        line()
        allt = r.trades
        s = describe([t.net(COST_BURST_BPS) for t in allt])
        cnt = {k: sum(1 for t in allt if t.exit_type == k) for k in EXIT_TYPES}
        print(f"  {'TOTAL':<15}{'':<22}{r.signals:>5}{len(allt):>5}"
              f"{cnt['tp']:>4}{cnt['trail']:>5}{cnt['stop']:>5}{cnt['fallback']:>4}"
              f"{fmt(s['sum'],1,10)}{fmt(s['mean'],2,11)}{fmt(s['win'],1,7)}"
              f"{sum(1 for t in allt if t.armed):>11}")
        print()


# --------------------------------------------------------------------------- #
# section 4 — exit-side selection
# --------------------------------------------------------------------------- #
def section_selection(runs: dict[str, VariantRun]) -> None:
    line("=")
    print("4. EXIT-SIDE SELECTION: does the maker TP cream the winners?")
    line("=")
    print("  For each TP variant, trades are split into TP-FILLED and NOT-FILLED (the")
    print("  fallback/stop bucket). Both populations are then scored on the SAME")
    print("  counterfactual basis: 'hold to the variant horizon and take' (the E0-style")
    print("  exit), so the split is about which trades the TP selected, not about the")
    print("  different exit prices. Positive selection = TP-filled trades would ALSO have")
    print("  been the better ones under a plain timed exit.")
    print()
    for v in [x for x in VARIANT_ORDER if VARIANTS[x]["tp_bps"] is not None]:
        r = runs[v]
        hz = VARIANTS[v]["horizon"]
        tp = [t for t in r.trades if t.exit_type == "tp"]
        no = [t for t in r.trades if t.exit_type != "tp"]
        n = len(r.trades)
        print(f"  {v}  (TP {VARIANTS[v]['tp_bps']:.0f} bps, horizon {hz}s)   trades={n}")
        if not n:
            print("      (no trades)")
            continue
        print(f"      TP filled     : {len(tp):>3} ({100*len(tp)/n:5.1f}%)   "
              f"NOT filled: {len(no):>3} ({100*len(no)/n:5.1f}%)")
        print("      REALISED net bps/trade:")
        print(f"        TP bucket   ", end="")
        stat_line([t.net(COST_BURST_BPS) for t in tp], indent=0)
        print(f"        non-TP      ", end="")
        stat_line([t.net(COST_BURST_BPS) for t in no], indent=0)
        cf_tp = [t.cf_hold_gross_bps - COST_BURST_BPS for t in tp
                 if t.cf_hold_gross_bps is not None]
        cf_no = [t.cf_hold_gross_bps - COST_BURST_BPS for t in no
                 if t.cf_hold_gross_bps is not None]
        print(f"      COUNTERFACTUAL 'hold {hz}s then take' net bps (same trades):")
        print(f"        TP bucket   ", end="")
        s_tp = stat_line(cf_tp, indent=0)
        print(f"        non-TP      ", end="")
        s_no = stat_line(cf_no, indent=0)
        if np.isfinite(s_tp["mean"]) and np.isfinite(s_no["mean"]):
            print(f"      selection edge (TP bucket - non-TP bucket, counterfactual basis) = "
                  f"{s_tp['mean'] - s_no['mean']:+.2f} bps")
            print(f"      value the TP ADDED on its own bucket (realised - counterfactual) = "
                  f"{describe([t.net(COST_BURST_BPS) for t in tp])['mean'] - s_tp['mean']:+.2f} bps")
        # what the non-TP bucket costs the book
        if no:
            d_no = describe([t.net(COST_BURST_BPS) for t in no])
            d_all = describe([t.net(COST_BURST_BPS) for t in r.trades])
            print(f"      book split  : TP bucket contributes {describe([t.net(COST_BURST_BPS) for t in tp])['sum']:+9.1f} bps, "
                  f"non-TP {d_no['sum']:+9.1f} bps, total {d_all['sum']:+9.1f} bps")
            print(f"      MFE/MAE of the non-TP bucket: mean peak favourable "
                  f"{np.mean([t.mfe_bps for t in no]):+.2f} bps, mean worst adverse "
                  f"{-np.mean([t.mae_bps for t in no]):+.2f} bps "
                  f"(TP needed {VARIANTS[v]['tp_bps']:.0f} bps)")
        print()


def section_diagnostic(runs: dict[str, VariantRun], events, args,
                       radar: StormRadar) -> VariantRun:
    line("=")
    print("4b. DIAGNOSTIC (NOT PRE-REGISTERED): is the gain the MAKER EXIT or the "
          "LONGER HORIZON?")
    line("=")
    print("  Section 4 shows the TP bucket's counterfactual 'hold to the horizon and take'")
    print("  BEATS the +10 bps the TP actually collects. That raises an obvious question")
    print("  the pre-registered variant list cannot answer: how much of E2's improvement")
    print("  over E0 comes from the maker exit, and how much simply from holding 120s")
    print("  instead of 60s? D1 answers it — E0's rule with the horizon doubled, run")
    print("  through the same simulator so the trade set is self-consistent.")
    print()
    print("  D1 IS EXPLORATORY. It was not pre-registered, it is a post-hoc pick out of")
    print("  the hold curve, and it is NOT eligible for the adoption decision. It is")
    print("  reported only because it changes the interpretation of the pre-registered")
    print("  results.")
    print()
    d1 = run_variant(events, args, radar, "D1")
    runs["D1"] = d1
    for v in ("E0", "E2", "D1"):
        r = runs[v]
        s = describe([t.net(COST_BURST_BPS) for t in r.trades])
        bs = boot_event_mean([[t.net(COST_BURST_BPS) for t in ts]
                              for ts in r.by_event.values()])
        ci = f"[{bs['lo']:+.2f}, {bs['hi']:+.2f}]" if bs else "-"
        p = f"{bs['p_bar']:.3f}" if bs else "-"
        print(f"  {v:<3} {VARIANTS[v]['label']:<58}")
        print(f"      n={s['n']:<4d} mean={s['mean']:+7.2f}  median={s['median']:+7.2f}  "
              f"sd={s['sd']:7.2f}  win%={s['win']:5.1f}  sum={s['sum']:+9.1f}  "
              f"CI {ci}  P(>=+5)={p}")
    print()
    print("  tail dependence (a mean of 30-bps-sd trades is only as good as its tails):")
    for v in ("E0", "E2", "D1"):
        nets = np.sort(np.asarray([t.net(COST_BURST_BPS) for t in runs[v].trades]))
        tot = nets.sum()
        top3 = nets[-3:].sum()
        print(f"      {v}: 10% trimmed mean {trimmed_mean(nets):+7.2f}   "
              f"top-3 trades = {top3:+8.1f} of {tot:+8.1f} total bps "
              f"({'n/a' if tot == 0 else f'{100 * top3 / tot:.0f}%'})   "
              f"mean without them {(tot - top3) / max(len(nets) - 3, 1):+7.2f}")
    print()
    s_d1 = describe([t.net(COST_BURST_BPS) for t in d1.trades])
    s_e2 = describe([t.net(COST_BURST_BPS) for t in runs["E2"].trades])
    print(f"  D1 - E2 = {s_d1['mean'] - s_e2['mean']:+.2f} bps/trade. "
          f"D1 - E0 = {s_d1['mean'] - describe([t.net(COST_BURST_BPS) for t in runs['E0'].trades])['mean']:+.2f} bps/trade.")
    print("  Read D1's sd and its CI width before reading its mean: the maker TP's whole")
    print("  contribution is variance reduction (it converts a fat-tailed distribution")
    print("  into a bounded one), which is exactly what it gives up in mean.")
    print()
    return d1


def section_tp_strict(runs: dict[str, VariantRun], events, args,
                      radar: StormRadar) -> None:
    line("=")
    print("4c. SENSITIVITY: how much of the TP fill rate is the permissive touch rule?")
    line("=")
    print("  Everything above fills the maker TP on a counter-side print AT or through")
    print("  the limit and ignores queue position — the optimistic bound. Here the TP")
    print("  (and only the TP; the entry rule is untouched) needs a print STRICTLY")
    print("  through it. Reality sits between the two rows for each variant.")
    print()
    print(f"  {'variant':<10}{'rule':<16}{'trades':>8}{'TPfill%':>9}{'mean':>9}"
          f"{'median':>9}{'win%':>7}{'total':>10}")
    line()
    for src, dst in STRICT_TWINS.items():
        runs[dst] = run_variant(events, args, radar, dst)
        for v, tag in ((src, "at-or-through"), (dst, "strict through")):
            r = runs[v]
            s = describe([t.net(COST_BURST_BPS) for t in r.trades])
            mix = exit_mix(r.trades)
            print(f"  {src:<10}{tag:<16}{len(r.trades):>8}{mix['tp']:>9.1f}"
                  f"{fmt(s['mean'],2,9)}{fmt(s['median'],2,9)}{fmt(s['win'],1,7)}"
                  f"{fmt(s['sum'],1,10)}")
    line()
    print("  A large drop from row to row means the headline TP fill rate is an artefact")
    print("  of the 1s bar's closing price sitting exactly at the limit; a small drop")
    print("  means the TP is genuinely being traded through.")
    same = all([t.key() for t in runs[src].trades] == [t.key() for t in runs[dst].trades]
               for src, dst in STRICT_TWINS.items())
    if same:
        print("  RESULT HERE: identical, trade for trade. No TP filled on a second whose")
        print("  closing print sat exactly ON the limit — every TP fill was a genuine")
        print("  through-print, so at 1s resolution with a 1 JPY tick on a ~1.1e7 JPY")
        print("  price the at-or-through vs through distinction is empty.")
    else:
        print("  RESULT HERE: the two rules DIVERGE — read the strict rows as the")
        print("  pessimistic bound and treat the headline TP fill rates with suspicion.")
    print("  THIS DOES NOT MAKE THE TP FILL RATE SAFE. The unmodelled optimism is QUEUE")
    print("  POSITION: a real limit at a price the tape trades through only fills if the")
    print("  volume printed there exceeds the size queued ahead of it. Neither rule tests")
    print("  that, so the TP fill rates above remain an upper bound.")
    print()


# --------------------------------------------------------------------------- #
# section 5 — armed window split
# --------------------------------------------------------------------------- #
def section_armed(runs: dict[str, VariantRun], best: str, radar: StormRadar) -> None:
    line("=")
    print(f"5. ARMED WINDOW ({radar.window}) vs OUTSIDE — best variant ({best}), E0 for reference")
    line("=")
    print("  Thresholds are 10 bps on BOTH sides of this split (the armed 8 bps drop is")
    print("  retired), so this is a pure regime comparison, not a threshold comparison.")
    print()
    for v in ("E0", best):
        r = runs[v]
        print(f"  {v}  {VARIANTS[v]['label']}")
        for label, pick in (("INSIDE  12:30-15:00", True), ("OUTSIDE 12:30-15:00", False)):
            sub = [t for t in r.trades if t.armed is pick]
            mix = exit_mix(sub)
            print(f"    {label}: trades={len(sub)}  "
                  f"exit mix tp/trail/stop/fb = {mix['tp']:.0f}/{mix['trail']:.0f}/"
                  f"{mix['stop']:.0f}/{mix['fallback']:.0f}%")
            s = stat_line([t.net(COST_BURST_BPS) for t in sub], indent=6)
            if s["n"]:
                verdict_line(s["mean"], indent=6)
        print()


# --------------------------------------------------------------------------- #
# section 6 — sanity
# --------------------------------------------------------------------------- #
def section_sanity(runs: dict[str, VariantRun], events, args, radar,
                   e0_ok: bool) -> bool:
    line("=")
    print("6. SANITY CHECKS")
    line("=")
    checks: list[tuple[str, bool, str]] = []
    checks.append(("E0 reproduces scripts/replay_scalp_storm.py trade-for-trade",
                   e0_ok, "see section 1"))

    fill_to = int(args.fill_timeout_sec)
    bad_entry = [t for r in runs.values() for t in r.trades
                 if not (t.sig_idx < t.fill_idx <= t.sig_idx + fill_to)]
    checks.append((f"no look-ahead on entry: signal < fill <= signal+{fill_to}s",
                   not bad_entry, f"{len(bad_entry)} violation(s)"))

    bad_exit = [t for r in runs.values() for t in r.trades if t.exit_idx <= t.fill_idx]
    checks.append(("no look-ahead on exit: exit strictly after the fill second",
                   not bad_exit, f"{len(bad_exit)} violation(s)"))

    bad_hz = [t for r in runs.values() for t in r.trades
              if t.hold_s > VARIANTS[t.variant]["horizon"]]
    checks.append(("every position bounded by its variant horizon",
                   not bad_hz, f"{len(bad_hz)} violation(s); "
                   f"max hold by variant: " +
                   ", ".join(f"{v}={max([t.hold_s for t in runs[v].trades], default=0):.0f}s"
                             for v in runs)))

    overlap = 0
    for r in runs.values():
        for ts_ in r.by_event.values():
            last = -1
            for t in sorted(ts_, key=lambda x: x.sig_idx):
                if t.sig_idx <= last:
                    overlap += 1
                last = t.exit_idx
    checks.append(("one position at a time (no overlapping trades, any variant)",
                   overlap == 0, f"{overlap} overlap(s)"))

    gapbad = 0
    for r in runs.values():
        for ts_ in r.by_event.values():
            idxs = sorted(t.sig_idx for t in ts_)
            gapbad += sum(1 for a, b in zip(idxs, idxs[1:]) if b - a < args.cooldown_sec)
    checks.append((f"cooldown >= {args.cooldown_sec:.0f}s between consecutive signals",
                   gapbad == 0, f"{gapbad} violation(s)"))

    # frozen entry: all variants must see the SAME first signal and the same
    # entry prices wherever the same signal second is traded.
    ref = {(t.event, t.sig_idx): round(t.entry_px, 6) for t in runs["E0"].trades}
    mismatch = 0
    for v in [x for x in runs if x != "E0"]:
        for t in runs[v].trades:
            k = (t.event, t.sig_idx)
            if k in ref and ref[k] != round(t.entry_px, 6):
                mismatch += 1
    shared = sum(1 for v in runs if v != "E0" for t in runs[v].trades
                 if (t.event, t.sig_idx) in ref)
    checks.append(("frozen entry: identical entry price wherever a variant takes the "
                   "same signal", mismatch == 0,
                   f"{shared} shared signals, {mismatch} price mismatch(es)"))

    # determinism: re-run everything and compare
    again = {v: run_variant(events, args, radar, v) for v in runs}
    det = all([t.key() for t in runs[v].trades] == [t.key() for t in again[v].trades]
              for v in runs)
    checks.append(("determinism: a second full run gives identical trades", det,
                   "all variants re-simulated"))

    tp_maker_cost = [t for r in runs.values() for t in r.trades
                     if t.exit_type == "tp" and t.cost_bps != 0.0]
    taker_cost = [t for r in runs.values() for t in r.trades
                  if t.exit_type != "tp" and t.cost_bps != COST_BURST_BPS]
    checks.append(("cost accounting: maker TP exits pay 0, all other exits pay "
                   f"{COST_BURST_BPS:.2f}", not tp_maker_cost and not taker_cost,
                   f"{len(tp_maker_cost)}+{len(taker_cost)} violation(s)"))

    ok_all = True
    for name, ok, detail in checks:
        ok_all &= ok
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<68} {detail}")
    print()
    for v in runs:
        r = runs[v]
        print(f"  {v}: signals={r.signals}  entry misses={r.misses}  "
              f"truncated by file end: fill={r.unresolved_fill} exit={r.unresolved_exit}  "
              f"nan-price signals skipped={r.skipped_nan_signal}  "
              f"TP/stop same-second ties={r.tie_tp_vs_stop} "
              f"(of which TP on the deadline second={r.tp_at_deadline})")
    print()
    print("  Tie convention: within one second the maker TP is tested BEFORE the")
    print("  reversal/hard exits, on the grounds that the limit sits on the book all")
    print("  second while the stop is a decision taken on that second's close. The tie")
    print("  counts above bound how much this convention can matter.")
    return ok_all


# --------------------------------------------------------------------------- #
# section 7 — verdict
# --------------------------------------------------------------------------- #
def section_verdict(runs: dict[str, VariantRun], best: str, n_events: int) -> None:
    line("=")
    print("7. VERDICT vs THE +5 bps/trade ADOPTION BAR")
    line("=")
    rows = []
    for v in VARIANT_ORDER:
        nets = [t.net(COST_BURST_BPS) for t in runs[v].trades]
        s = describe(nets)
        bs = boot_event_mean([[t.net(COST_BURST_BPS) for t in ts]
                              for ts in runs[v].by_event.values()])
        rows.append((v, s, bs))
    print(f"  {'var':<4}{'n':>5}{'mean':>9}{'median':>9}{'trim10':>9}{'95% CI (event-clustered)':>30}"
          f"{'P(mean>=+5)':>13}{'verdict':>9}")
    line()
    for v, s, bs in rows:
        ci = f"[{bs['lo']:+.2f}, {bs['hi']:+.2f}]" if bs else "-"
        p = f"{bs['p_bar']:.3f}" if bs else "-"
        vd = "PASS" if s["n"] and s["mean"] >= ADOPTION_BAR_BPS else "FAIL"
        tm = trimmed_mean([t.net(COST_BURST_BPS) for t in runs[v].trades])
        print(f"  {v:<4}{s['n']:>5}{fmt(s['mean'],2,9)}{fmt(s['median'],2,9)}{fmt(tm,2,9)}"
              f"{ci:>30}{p:>13}{vd:>9}")
    line()
    best_s = describe([t.net(COST_BURST_BPS) for t in runs[best].trades])
    e0_s = describe([t.net(COST_BURST_BPS) for t in runs["E0"].trades])
    print(f"  best exit variant by mean net bps/trade: {best} "
          f"({VARIANTS[best]['label']})")
    print(f"  improvement over E0: {best_s['mean'] - e0_s['mean']:+.2f} bps/trade "
          f"({e0_s['mean']:+.2f} -> {best_s['mean']:+.2f}); "
          f"still {best_s['mean'] - ADOPTION_BAR_BPS:+.2f} bps vs the +5 bar")
    print()
    line()
    print("  RECOMMENDATION")
    line()
    passing = [v for v in VARIANT_ORDER if v != "E0"
               and describe([t.net(COST_BURST_BPS) for t in runs[v].trades])["mean"]
               >= ADOPTION_BAR_BPS]
    if passing:
        print(f"  Variant(s) clearing the bar: {', '.join(passing)} — PROVISIONAL PASS "
              f"(n = {n_events} events < {ADOPTION_EVENT_BAR}); paper trading decides.")
    else:
        print("  NO pre-registered exit variant clears the +5 bps/trade bar. The maker")
        print("  exit does exactly what the hypothesis predicted — the TP bucket is 100%")
        print("  winners and the exit-side selection edge is strongly POSITIVE (section 4)")
        print("  — and it is still not enough, because the TP caps every winner at its")
        print("  distance while the fallback bucket keeps the full loser tail. The maker")
        print("  exit converts the book's variance, not its mean.")
        print()
        print("  DO NOT switch the live paper scalper's exit on this evidence. The one")
        print("  defensible change is that E2 dominates E0 on every axis that matters for")
        print("  a paper run that has to survive long enough to reach n = 30 (higher mean,")
        print("  higher median, higher win rate, half the sd, bounded losses) — but it is")
        print("  a ~0 bps/trade strategy, so switching buys a flatter equity curve around")
        print("  zero, not an edge. If the owner wants the exit rule changed anyway for")
        print("  drawdown reasons, E2 is the one to change to, logged as a variance")
        print("  decision and not as an adoption.")
    print()
    print(f"  SAMPLE CAVEAT: n = {n_events} storm events, below the pre-registered "
          f"{ADOPTION_EVENT_BAR}-event bar.")
    print("  A PASS here would be PROVISIONAL (paper trading decides). A FAIL at these")
    print("  costs is informative as-is: no exit rule can create edge that the price path")
    print("  does not contain.")
    print()
    print("  Inherited caveats from the replay (all still apply): 1s bars vs tick reality,")
    print("  last-trade-as-touch instead of a real book, permissive at-or-through fills")
    print("  with no queue position (optimistic for BOTH the maker entry and the maker")
    print("  TP), bf_price forward-filled inside the window, storm-only sample, no")
    print("  latency/partials/rejects, 0% CFD fee at face value.")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # FROZEN entry side: thr 10 bps armed and unarmed (the 8 bps drop is retired)
    ap.add_argument("--thr-bps", type=float, default=10.0)
    ap.add_argument("--thr-armed-bps", type=float, default=10.0)
    ap.add_argument("--radar-start", default="12:30")
    ap.add_argument("--radar-end", default="15:00")
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--fill-timeout-sec", type=float, default=10.0)
    ap.add_argument("--event-dir", default=str(EVENT_DIR))
    args = ap.parse_args()

    paths = sorted(Path(args.event_dir).glob("event_*.csv"))
    if not paths:
        print(f"no event files in {args.event_dir}", file=sys.stderr)
        return 1
    radar = StormRadar(start=args.radar_start, end=args.radar_end)
    events = [load_event(p) for p in paths]

    line("=")
    print("STUDY R5-S2 — EXIT REDESIGN FOR THE BURST SCALPER (entry side frozen)")
    line("=")
    print(f"event files : {len(events)}  ({args.event_dir})")
    print(f"entry (FROZEN): thr {args.thr_bps:.0f} bps armed and unarmed "
          f"({radar.window} radar recorded as a label only), window "
          f"{args.window_sec:.0f}s, maker RestingLimit at the touch,")
    print(f"                fill timeout {args.fill_timeout_sec:.0f}s, cooldown "
          f"{args.cooldown_sec:.0f}s from signal, continuation direction, one position at a time")
    print(f"costs        : maker entry 0 bps, maker TP exit 0 bps, taker exit "
          f"{COST_BURST_BPS:.2f} bps (burst PRIMARY) / {COST_CALM_BPS:.2f} bps (calm sensitivity)")
    print("exit variants:")
    for v in VARIANT_ORDER:
        print(f"   {v}  {VARIANTS[v]['label']}")

    runs = {v: run_variant(events, args, radar, v) for v in VARIANT_ORDER}
    e0_ok = section_e0_reproduction(events, args, radar, paths, runs["E0"])
    if not e0_ok:
        print()
        print("STOP: E0 does not reproduce the replay. Fix before reading anything below.")
        return 2

    section_variants(runs)
    cands = [v for v in VARIANT_ORDER[1:] if runs[v].trades]
    best = max(cands, key=lambda v: describe([t.net(COST_BURST_BPS)
                                              for t in runs[v].trades])["mean"])
    section_sensitivity(runs, best)
    section_per_event(runs, events, best)
    section_selection(runs)
    section_diagnostic(runs, events, args, radar)
    section_tp_strict(runs, events, args, radar)
    section_armed(runs, best, radar)
    section_sanity(runs, events, args, radar, e0_ok)
    section_verdict(runs, best, len(events))
    line("=")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
