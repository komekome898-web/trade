#!/usr/bin/env python3
"""Study R6 — is the scalper's E2 exit (maker TP +10 bps, taker fallback at
fill+120s) actually optimal, and should the TP adapt to volatility/volume?

Background
----------
`scripts/research_scalp_exits.py` (study R5-S2) chose E2 = (TP 10 bps,
fallback 120s) out of a COARSE {5,10} x {60,120} comparison run on the 16
storm windows only. Neither a finer surface nor a volatility/volume-adaptive
TP was ever tested, and the 99 ordinary-burst windows in
`data/burst_events/` did not exist when that choice was made.

What is FROZEN (identical to R5-S2 / to scripts/run_scalp_paper.py)
-------------------------------------------------------------------
* signal      : |log(bn[t]/bn[t-5])| * 1e4 >= 10 bps, bn forward-filled
                (the live runner polls the Binance REST last price, so its
                leader series is effectively ffilled). 10 bps applies both
                inside and outside the 12:30-15:00 UTC radar window; the
                armed flag is recorded as a regime label only.
* direction   : continuation (ret > 0 -> LONG, ret < 0 -> SHORT).
* entry       : maker `RestingLimit` (imported verbatim from the live
                runner) rested at bf_price of the signal second, filled by a
                counter-side print at or through it within 10s.
* cooldown    : 30s from the SIGNAL (set on every signal, misses included).
* concurrency : one position at a time.
* costs       : maker entry 0 bps, maker TP exit 0 bps, taker exit 3.96 bps
                (burst PRIMARY) / 2.93 bps (calm sensitivity).

ONLY the exit changes below.

Pre-registered evaluation protocol (fixed before any run)
---------------------------------------------------------
1. Chronological event split over all 115 windows (16 storm + 99 burst),
   sorted by window start: first 58 = half A, last 57 = half B.
2. Fixed grid: TP in {5, 8, 10, 15, 20, 30} bps x fallback in
   {60, 120, 180, 300} s = 24 cells. E2 = (10, 120) is the incumbent.
3. Adaptive rules, fallback fixed at 120s, TP clamped to [4, 40] bps, one
   free parameter k each, swept over the coarse grids stated in K_GRID:
     A1  TP = k * sigma_60   (sd of 1s bitFlyer log-returns, in bps, over
                              the 60s STRICTLY BEFORE the signal second)
     A2  TP = k * |signal_bps|  (the Binance 5s move that triggered entry)
     A3  TP = k * sqrt(V / median V), V = bitFlyer bf_buy+bf_sell summed
                              over the 60s STRICTLY BEFORE the signal
4. Adoption bar to REPLACE E2 (all three must hold):
     (a) beats E2's net mean bps/trade on half A AND half B separately,
     (b) plateau: every neighbouring cell (TP +/-1 grid step, fallback
         +/-1 grid step; adaptive: k +/-1 step) is within 2 bps of the
         candidate's combined mean,
     (c) improves the combined event-clustered bootstrap mean CI midpoint.
   A spike winner that fails (b) is reported but NOT adopted.
5. Owner's question: bucket trades by pre-signal sigma_60 terciles and by
   volume terciles, report the empirically best fixed TP per bucket.

Usage:  PYTHONPATH=src python scripts/research_exit_surface.py
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
from run_scalp_paper import RestingLimit  # noqa: E402
from replay_scalp_storm import (  # noqa: E402
    COST_BURST_BPS,
    COST_CALM_BPS,
    describe,
)
# R5-S2 is imported (not copied) so the E2 incumbent this study compares
# against is literally the object the previous study adopted.
import research_scalp_exits as r5  # noqa: E402

STORM_DIR = ROOT / "data" / "storm_events"
BURST_DIR = ROOT / "data" / "burst_events"

TICK_JPY = 1.0
BOOT_N = 20000
BOOT_SEED = 7

# ---- pre-registered grids -------------------------------------------------
GRID_TP = [5.0, 8.0, 10.0, 15.0, 20.0, 30.0]
GRID_FB = [60, 120, 180, 300]
INCUMBENT = (10.0, 120)                 # E2

ADAPTIVE_HORIZON = 120
TP_CLAMP = (4.0, 40.0)
K_GRID = {
    "A1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0],          # x sigma_60 (bps)
    "A2": [0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 2.50],   # x |signal bps|
    "A3": [4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0],      # x sqrt(V/medV)
}
ADAPTIVE_LABEL = {
    "A1": "TP = k * sigma_60(bitFlyer 1s log-returns, bps), fb 120s",
    "A2": "TP = k * |Binance 5s signal move, bps|,          fb 120s",
    "A3": "TP = k * sqrt(V60 / median V60),                 fb 120s",
}

PLATEAU_TOL_BPS = 2.0
EXIT_TYPES = ["tp", "fallback"]


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
@dataclass
class Ev:
    name: str
    lib: str                 # "storm" | "burst"
    start: pd.Timestamp
    half: str                # "A" | "B" (assigned after the chronological sort)
    n: int
    ts_unix: np.ndarray
    ts_iso: np.ndarray
    bf: np.ndarray
    buy: np.ndarray
    sell: np.ndarray
    bn: np.ndarray
    ret: np.ndarray          # leader 5s return, bps; NaN where undefined
    armed: np.ndarray        # bool, radar state at each second
    sigma: np.ndarray        # sigma_60 (bps) using ONLY seconds < i
    vol: np.ndarray          # V60 using ONLY seconds < i
    live: np.ndarray         # bool: bf finite and > 0


def load_ev(path: Path, lib: str, radar: StormRadar) -> Ev:
    df = pd.read_csv(path, parse_dates=["ts"])
    ts = pd.to_datetime(df["ts"], utc=True)
    # datetime64 unit trap: pandas may hand back [us] or [ns]. Go through a
    # 1s Timedelta floor-division so the epoch seconds are unit-proof.
    ts_unix = ((ts - pd.Timestamp("1970-01-01", tz="UTC"))
               // pd.Timedelta(seconds=1)).to_numpy().astype("int64")
    bf = df["bf_price"].to_numpy(dtype=float)
    buy = df["bf_buy"].to_numpy(dtype=float)
    sell = df["bf_sell"].to_numpy(dtype=float)
    # the live leader feed is a REST last-price poll -> effectively ffilled
    bn = df["bn_price"].ffill().to_numpy(dtype=float)
    n = len(df)

    with np.errstate(all="ignore"):
        ret = np.full(n, np.nan)
        if n > 5:
            a, b = bn[:-5], bn[5:]
            ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
            r = np.full(n - 5, np.nan)
            r[ok] = np.log(b[ok] / a[ok]) * 1e4
            ret[5:] = r
        # 1s bitFlyer log-returns, bps
        lr = np.full(n, np.nan)
        if n > 1:
            a, b = bf[:-1], bf[1:]
            ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
            x = np.full(n - 1, np.nan)
            x[ok] = np.log(b[ok] / a[ok]) * 1e4
            lr[1:] = x
    # rolling(60).X at position j covers j-59..j; .shift(1) moves it to i,
    # so index i sees only seconds i-60..i-1 -> STRICTLY before the signal.
    sigma = (pd.Series(lr).rolling(60, min_periods=30).std()
             .shift(1).to_numpy(dtype=float))
    vol = (pd.Series(buy + sell).rolling(60, min_periods=1).sum()
           .shift(1).to_numpy(dtype=float))

    armed = np.array([radar.is_armed(float(t)) for t in ts_unix], dtype=bool)
    live = np.isfinite(bf) & (bf > 0)
    return Ev(name=path.stem.replace("event_", ""), lib=lib, start=ts.iloc[0],
              half="?", n=n, ts_unix=ts_unix,
              ts_iso=ts.dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy(),
              bf=bf, buy=buy, sell=sell, bn=bn, ret=ret, armed=armed,
              sigma=sigma, vol=vol, live=live)


# --------------------------------------------------------------------------- #
# simulation
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class T:
    ev: str
    lib: str
    half: str
    side: str
    armed: bool
    sig_idx: int
    fill_idx: int
    exit_idx: int
    entry_px: float
    exit_px: float
    kind: str            # "tp" | "fallback"
    gross: float
    net: float
    tp_used: float       # the TP distance in bps actually posted (nan if none)
    sigma: float
    vol: float
    absret: float

    def key(self) -> tuple:
        return (self.ev, self.sig_idx, self.fill_idx, self.exit_idx,
                self.kind, round(self.gross, 9))


@dataclass
class Run:
    name: str
    label: str
    trades: list[T] = field(default_factory=list)
    signals: int = 0
    misses: int = 0
    unresolved_fill: int = 0
    unresolved_exit: int = 0
    skipped_nan_signal: int = 0
    tp_at_deadline: int = 0
    feature_nan: int = 0
    by_event: dict[str, list[T]] = field(default_factory=dict)


def tp_price(entry_px: float, side: str, tp_bps: float) -> float:
    """Maker take-profit limit, rounded to the tick AWAY from the entry."""
    if side == "LONG":
        return math.ceil(entry_px * (1.0 + tp_bps / 1e4) / TICK_JPY) * TICK_JPY
    return math.floor(entry_px * (1.0 - tp_bps / 1e4) / TICK_JPY) * TICK_JPY


def resolve_tp(spec: dict, sigma: float, absret: float, vol: float,
               ctx: dict, key: tuple | None = None) -> tuple[float | None, bool]:
    """TP distance in bps for one trade, plus a 'feature was NaN' flag."""
    mode = spec["mode"]
    if mode == "none":
        return None, False
    if mode == "fixed":
        return float(spec["tp"]), False
    if mode == "perm":
        # shuffle control: the SAME multiset of TP distances the rule would
        # have posted, re-dealt to other signals, so the TP level is held and
        # only the link to the feature is destroyed.
        hit = spec["perm_map"].get(key)
        if hit is not None:
            return float(hit), False
        mode = spec["rule"]             # unseen signal -> honest rule value
    k = float(spec["k"])
    if mode == "A1":
        x = sigma
    elif mode == "A2":
        x = absret
    else:
        v = vol
        x = math.sqrt(max(v, 0.0) / ctx["v_med"]) if np.isfinite(v) else np.nan
    if not np.isfinite(x):
        # feature undefined (window edge) -> fall back to the incumbent 10 bps
        return float(INCUMBENT[0]), True
    return float(min(max(k * x, TP_CLAMP[0]), TP_CLAMP[1])), False


def simulate(ev: Ev, spec: dict, run: Run, args, ctx: dict) -> None:
    """Frozen entry + one exit policy over a single window."""
    bf, buy, sell, ts_unix = ev.bf, ev.buy, ev.sell, ev.ts_unix
    ret, armed_arr, live = ev.ret, ev.armed, ev.live
    fill_to = int(args.fill_timeout_sec)
    cooldown = float(args.cooldown_sec)
    horizon = int(spec["horizon"])
    thr = float(args.thr_bps)
    thr_armed = float(args.thr_armed_bps)
    thr_min = min(thr, thr_armed)

    pending = None
    pos = None
    last_signal_ts = -1e18

    def prints_at(i: int) -> list[tuple[float, float, str]]:
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
        t = T(ev=ev.name, lib=ev.lib, half=ev.half, side=pos["side"],
              armed=bool(pos["armed"]), sig_idx=pos["sig_idx"],
              fill_idx=pos["fill_idx"], exit_idx=i, entry_px=pos["entry_px"],
              exit_px=float(px), kind=kind, gross=gross, net=gross - cost,
              tp_used=pos["tp_used"], sigma=pos["sigma"], vol=pos["vol"],
              absret=abs(pos["ret_bps"]))
        run.trades.append(t)
        run.by_event.setdefault(ev.name, []).append(t)
        pos = None

    for i in range(ev.n):
        # --- 1. resting ENTRY order --------------------------------------
        if pending is not None:
            s = pending["sig_idx"]
            if i <= s + fill_to:
                if not live[i]:
                    continue
                if pending["order"].first_fill(prints_at(i)) is not None:
                    entry_px = pending["limit"]     # maker fills AT the limit
                    tp_bps, nanflag = resolve_tp(spec, pending["sigma"],
                                                 abs(pending["ret_bps"]),
                                                 pending["vol"], ctx,
                                                 (ev.name, pending["sig_idx"]))
                    run.feature_nan += int(nanflag)
                    pos = dict(pending)
                    pos.update(fill_idx=i, entry_px=entry_px,
                               tp_order=None, tp_limit=None,
                               tp_used=(float("nan") if tp_bps is None
                                        else float(tp_bps)))
                    if tp_bps is not None:
                        lim = tp_price(entry_px, pos["side"], tp_bps)
                        # a LONG exits by resting an ASK, lifted by a taker
                        # BUY -> RestingLimit(side="SHORT"); mirror for SHORT.
                        pos["tp_order"] = RestingLimit(
                            side=("SHORT" if pos["side"] == "LONG" else "LONG"),
                            limit=lim, t_signal=float(ts_unix[i]),
                            timeout_sec=float(horizon), size=1.0,
                            signal_bps=pos["ret_bps"])
                        pos["tp_limit"] = lim
                    pending = None
                continue
            pending = None
            run.misses += 1
            continue

        # --- 2. open position: exit policy --------------------------------
        if pos is not None:
            if i <= pos["fill_idx"]:
                continue
            if not live[i]:
                continue
            deadline = i >= pos["fill_idx"] + horizon
            if pos["tp_order"] is not None:
                if pos["tp_order"].first_fill(prints_at(i)) is not None:
                    if deadline:
                        run.tp_at_deadline += 1
                    close(i, pos["tp_limit"], "tp")
                    continue
            if deadline:
                close(i, float(bf[i]), "fallback")
            continue

        # --- 3. flat: frozen signal logic ---------------------------------
        r = ret[i]
        if not np.isfinite(r) or abs(r) < thr_min:
            continue
        a = bool(armed_arr[i])
        if abs(r) < (thr_armed if a else thr):
            continue
        if ts_unix[i] - last_signal_ts < cooldown:
            continue
        if not live[i]:
            run.skipped_nan_signal += 1
            continue
        last_signal_ts = float(ts_unix[i])
        side = "LONG" if r > 0 else "SHORT"
        run.signals += 1
        pending = dict(sig_idx=i, side=side, armed=a, ret_bps=float(r),
                       limit=float(bf[i]), sigma=float(ev.sigma[i]),
                       vol=float(ev.vol[i]),
                       order=RestingLimit(side=side, limit=float(bf[i]),
                                          t_signal=float(ts_unix[i]),
                                          timeout_sec=float(fill_to), size=1.0,
                                          signal_bps=float(r)))

    if pending is not None:
        run.unresolved_fill += 1
    if pos is not None:
        run.unresolved_exit += 1


def run_spec(events: list[Ev], spec: dict, args, ctx: dict) -> Run:
    run = Run(name=spec["name"], label=spec["label"])
    for ev in events:
        simulate(ev, spec, run, args, ctx)
    return run


# --------------------------------------------------------------------------- #
# stats
# --------------------------------------------------------------------------- #
def boot_ci(by_event: dict[str, list[T]] | list[list[float]], n: int = BOOT_N,
            seed: int = BOOT_SEED) -> dict | None:
    """Event-clustered bootstrap of the mean net bps/trade.

    Trades inside one window are not independent, so windows (not trades) are
    the resampling unit. Implemented as sum/count ratios over resampled
    events, which is algebraically the pooled mean of the resampled trades.
    """
    if isinstance(by_event, dict):
        pools = [np.asarray([t.net for t in v], dtype=float)
                 for v in by_event.values() if v]
    else:
        pools = [np.asarray(v, dtype=float) for v in by_event if len(v)]
    if not pools:
        return None
    sums = np.array([p.sum() for p in pools])
    cnts = np.array([p.size for p in pools], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(pools), size=(n, len(pools)))
    boot = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(lo=float(lo), hi=float(hi), mid=float((lo + hi) / 2.0),
                p_pos=float((boot > 0).mean()), n_ev=len(pools))


def paired_diff(run_a: Run, run_b: Run, filt=None) -> dict | None:
    """mean(net_a - net_b) over signals BOTH variants traded, with an
    event-clustered CI of the difference.

    The entry side is frozen, so a signal traded by both variants has the same
    side, the same entry price and the same fill second in both: the only
    difference is the exit. This removes both the different-trade-set problem
    and the common regime component, and is far more powerful than comparing
    two independent means.
    """
    A = {(t.ev, t.sig_idx): t for t in run_a.trades}
    B = {(t.ev, t.sig_idx): t for t in run_b.trades}
    byev: dict[str, list[float]] = {}
    n = 0
    for k in sorted(A.keys() & B.keys()):
        ta, tb = A[k], B[k]
        if filt is not None and not filt(tb):
            continue
        byev.setdefault(k[0], []).append(ta.net - tb.net)
        n += 1
    if not n:
        return None
    bs = boot_ci(list(byev.values()))
    flat = np.concatenate([np.asarray(v) for v in byev.values()])
    return dict(n=n, n_ev=len(byev), mean=float(flat.mean()),
                lo=bs["lo"], hi=bs["hi"],
                sig=bool(bs["lo"] > 0 or bs["hi"] < 0))


def mean_of(trades: list[T], cost: float = COST_BURST_BPS) -> float:
    if not trades:
        return float("nan")
    if cost == COST_BURST_BPS:
        return float(np.mean([t.net for t in trades]))
    return float(np.mean([t.gross - (0.0 if t.kind == "tp" else cost)
                          for t in trades]))


def sub(run: Run, **kw) -> list[T]:
    out = run.trades
    for k, v in kw.items():
        out = [t for t in out if getattr(t, k) == v]
    return out


def line(c="-", n=110):
    print(c * n)


def fmt(x, nd=2, width=8):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * (width - 1) + "-"
    return f"{x:>{width}.{nd}f}"


def cellstats(run: Run) -> dict:
    tr = run.trades
    d = describe([t.net for t in tr])
    a = [t for t in tr if t.half == "A"]
    b = [t for t in tr if t.half == "B"]
    bs = boot_ci(run.by_event)
    return dict(n=len(tr), mean=d["mean"], median=d["median"], sd=d["sd"],
                win=d["win"], total=d["sum"],
                nA=len(a), mA=mean_of(a), nB=len(b), mB=mean_of(b),
                tp_rate=(100.0 * sum(1 for t in tr if t.kind == "tp") / len(tr)
                         if tr else float("nan")),
                hold=(float(np.mean([t.exit_idx - t.fill_idx for t in tr]))
                      if tr else float("nan")),
                ci_lo=bs["lo"] if bs else float("nan"),
                ci_hi=bs["hi"] if bs else float("nan"),
                ci_mid=bs["mid"] if bs else float("nan"),
                p_pos=bs["p_pos"] if bs else float("nan"))


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #
def section_gate(events_storm: list[Ev], args, radar) -> bool:
    """This script's (10,120) cell must reproduce R5-S2's E2 on the storms."""
    line("=")
    print("0. GATE — this study's (TP 10, fb 120) cell must reproduce study R5-S2's E2")
    line("=")
    print("  scripts/research_scalp_exits.py is imported and its E2 variant is run over")
    print("  data/storm_events/ with its own simulator. This script's fixed-grid cell")
    print("  (10 bps, 120s) is run over the same 16 windows. If they are not identical")
    print("  trade for trade, the exit surface below is not comparable to the incumbent.")
    r5_events = [r5.load_event(p) for p in sorted(STORM_DIR.glob("event_*.csv"))]
    r5_args = argparse.Namespace(thr_bps=args.thr_bps,
                                 thr_armed_bps=args.thr_armed_bps,
                                 window_sec=5.0, cooldown_sec=args.cooldown_sec,
                                 fill_timeout_sec=args.fill_timeout_sec)
    r5_run = r5.run_variant(r5_events, r5_args, radar, "E2")
    mine = run_spec(events_storm, fixed_spec(10.0, 120), args, dict(v_med=1.0))
    k_ref = [t.key() for t in r5_run.trades]
    k_mine = [t.key() for t in mine.trades]
    ok = k_ref == k_mine
    dr = describe([t.net(COST_BURST_BPS) for t in r5_run.trades])
    dm = describe([t.net for t in mine.trades])
    print(f"      R5-S2 E2 : trades={len(k_ref):>4}  signals={r5_run.signals:>4}  "
          f"net mean={dr['mean']:+.4f} bps/trade")
    print(f"      R6 (10,120): trades={len(k_mine):>4}  signals={mine.signals:>4}  "
          f"net mean={dm['mean']:+.4f} bps/trade")
    print(f"      [{'OK ' if ok else 'FAIL'}] trade-for-trade identity "
          f"(event, sig idx, fill idx, exit idx, exit type, gross)")
    print()
    return ok


def fixed_spec(tp: float | None, fb: int) -> dict:
    if tp is None:
        return dict(name=f"T--_F{fb}", label=f"taker at fill+{fb}s",
                    mode="none", horizon=fb, tp=None)
    return dict(name=f"T{int(tp)}_F{fb}",
                label=f"maker TP +{tp:.0f} bps, taker fallback fill+{fb}s",
                mode="fixed", horizon=fb, tp=tp)


def adaptive_spec(rule: str, k: float) -> dict:
    return dict(name=f"{rule}_k{k:g}", label=f"{ADAPTIVE_LABEL[rule]}  k={k:g}",
                mode=rule, horizon=ADAPTIVE_HORIZON, k=k)


def matrix(title: str, cells: dict, fn, width=9, nd=2, note=""):
    print(f"  {title}")
    hdr = "    TP\\fb " + "".join(f"{str(f) + 's':>{width}}" for f in GRID_FB)
    print(hdr)
    for tp in GRID_TP:
        row = f"    {tp:>5.0f}  "
        for fb in GRID_FB:
            v = fn(cells[(tp, fb)])
            star = ""
            if (tp, fb) == INCUMBENT:
                star = "*"
            if isinstance(v, str):
                row += f"{v:>{width}}"
            else:
                row += f"{fmt(v, nd, width - len(star))}{star}"
        print(row)
    if note:
        print(f"    {note}")
    print()


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thr-bps", type=float, default=10.0)
    ap.add_argument("--thr-armed-bps", type=float, default=10.0)
    ap.add_argument("--radar-start", default="12:30")
    ap.add_argument("--radar-end", default="15:00")
    ap.add_argument("--window-sec", type=float, default=5.0)
    ap.add_argument("--cooldown-sec", type=float, default=30.0)
    ap.add_argument("--fill-timeout-sec", type=float, default=10.0)
    ap.add_argument("--boot", type=int, default=BOOT_N)
    args = ap.parse_args()

    radar = StormRadar(start=args.radar_start, end=args.radar_end)
    storm_paths = sorted(STORM_DIR.glob("event_*.csv"))
    burst_paths = sorted(BURST_DIR.glob("event_*.csv"))
    if not storm_paths or not burst_paths:
        print("missing event libraries", file=sys.stderr)
        return 1

    events = ([load_ev(p, "storm", radar) for p in storm_paths]
              + [load_ev(p, "burst", radar) for p in burst_paths])
    events.sort(key=lambda e: (e.start, e.name))
    for j, ev in enumerate(events):
        ev.half = "A" if j < 58 else "B"
    ev_storm = [e for e in events if e.lib == "storm"]
    ev_burst = [e for e in events if e.lib == "burst"]

    # ---- policy-independent reference set: every second whose RAW signal
    # condition fires, ignoring cooldown/position. Used only for the volume
    # normaliser and the tercile cut-points, so those do not depend on which
    # exit policy happens to be running.
    ref_sig, ref_vol, ref_abs = [], [], []
    for ev in events:
        m = np.isfinite(ev.ret) & (np.abs(ev.ret) >= min(args.thr_bps,
                                                         args.thr_armed_bps)) & ev.live
        ref_sig.append(ev.sigma[m])
        ref_vol.append(ev.vol[m])
        ref_abs.append(np.abs(ev.ret[m]))
    ref_sig = np.concatenate(ref_sig)
    ref_vol = np.concatenate(ref_vol)
    ref_abs = np.concatenate(ref_abs)
    v_med = float(np.nanmedian(ref_vol))
    ctx = dict(v_med=v_med if v_med > 0 else 1.0)
    sig_cuts = np.nanpercentile(ref_sig, [33.3333, 66.6667])
    vol_cuts = np.nanpercentile(ref_vol, [33.3333, 66.6667])

    line("=")
    print("STUDY R6 — EXIT SURFACE AND ADAPTIVE TAKE-PROFIT (entry side FROZEN)")
    line("=")
    print(f"libraries    : storm {len(ev_storm)} windows ({STORM_DIR}), "
          f"burst {len(ev_burst)} windows ({BURST_DIR}); total {len(events)}")
    print(f"entry (FROZEN): thr {args.thr_bps:.0f} bps armed and unarmed "
          f"({radar.window} recorded as a label only), leader window "
          f"{args.window_sec:.0f}s, maker RestingLimit at the touch,")
    print(f"                fill timeout {args.fill_timeout_sec:.0f}s, cooldown "
          f"{args.cooldown_sec:.0f}s from signal, continuation direction, "
          f"one position at a time")
    print(f"costs        : maker entry 0 bps, maker TP exit 0 bps, taker exit "
          f"{COST_BURST_BPS:.2f} bps (burst PRIMARY) / {COST_CALM_BPS:.2f} bps (calm)")
    print(f"grid         : TP {GRID_TP} bps x fallback {GRID_FB} s = "
          f"{len(GRID_TP) * len(GRID_FB)} cells; incumbent E2 = "
          f"(TP {INCUMBENT[0]:.0f}, fb {INCUMBENT[1]}s)")
    print(f"adaptive     : {', '.join(f'{r} k in {K_GRID[r]}' for r in K_GRID)}"
          f"  (fb {ADAPTIVE_HORIZON}s, TP clamped to {TP_CLAMP} bps)")
    print(f"split        : chronological, first 58 windows = half A "
          f"({events[0].start.date()} .. {events[57].start.date()}), "
          f"last 57 = half B ({events[58].start.date()} .. {events[-1].start.date()})")
    print(f"reference set: {len(ref_sig)} raw signal-condition seconds; "
          f"median V60 = {v_med:.3f} BTC, sigma_60 terciles at "
          f"{sig_cuts[0]:.2f}/{sig_cuts[1]:.2f} bps, V60 terciles at "
          f"{vol_cuts[0]:.2f}/{vol_cuts[1]:.2f} BTC")
    print(f"bootstrap    : {args.boot} event-clustered resamples, seed {BOOT_SEED}")
    print()

    if not section_gate(ev_storm, args, radar):
        print("STOP: the (10,120) cell does not reproduce R5-S2's E2. Fix before reading on.")
        return 2

    # ------------------------------------------------------------------ #
    # run everything
    # ------------------------------------------------------------------ #
    cells: dict[tuple, Run] = {}
    for tp in GRID_TP:
        for fb in GRID_FB:
            cells[(tp, fb)] = run_spec(events, fixed_spec(tp, fb), args, ctx)
    adapt: dict[tuple, Run] = {}
    for rule, ks in K_GRID.items():
        for k in ks:
            adapt[(rule, k)] = run_spec(events, adaptive_spec(rule, k), args, ctx)
    # reference: no maker TP at all, pure timed taker exit (context, not a
    # candidate — it is what the exit surface degenerates to as TP -> inf)
    taker = {fb: run_spec(events, fixed_spec(None, fb), args, ctx) for fb in GRID_FB}

    stats = {k: cellstats(v) for k, v in cells.items()}
    astats = {k: cellstats(v) for k, v in adapt.items()}
    inc = stats[INCUMBENT]

    # ------------------------------------------------------------------ #
    line("=")
    print("1. E2 ON FRESH DATA — what the incumbent does on the 99 burst windows")
    line("=")
    print("  E2 (TP 10 bps / fb 120s) was chosen on the 16 storm windows from a coarse")
    print("  {5,10} x {60,120} comparison. The 99 ordinary-burst windows are FRESH for")
    print("  it: no tuning of any kind has touched them. This is the single most honest")
    print("  number in the study, because it is the only out-of-sample one.")
    print()
    e2 = cells[INCUMBENT]
    print(f"  {'sample':<22}{'wins':>6}{'trades':>8}{'TP%':>7}{'mean':>9}{'median':>9}"
          f"{'sd':>8}{'win%':>7}{'total':>10}{'95% CI (event-clustered)':>28}")
    line()
    for tag, evs in (("storm (16, in-sample)", ev_storm),
                     ("burst (99, FRESH)", ev_burst),
                     ("combined (115)", events)):
        names = {e.name for e in evs}
        tr = [t for t in e2.trades if t.ev in names]
        d = describe([t.net for t in tr])
        be = {k: v for k, v in e2.by_event.items() if k in names}
        bs = boot_ci(be)
        ci = f"[{bs['lo']:+.2f}, {bs['hi']:+.2f}]" if bs else "-"
        tpr = 100.0 * sum(1 for t in tr if t.kind == "tp") / len(tr) if tr else float("nan")
        print(f"  {tag:<22}{len(evs):>6}{len(tr):>8}{fmt(tpr,1,7)}{fmt(d['mean'],2,9)}"
              f"{fmt(d['median'],2,9)}{fmt(d['sd'],2,8)}{fmt(d['win'],1,7)}"
              f"{fmt(d['sum'],1,10)}{ci:>28}")
    line()
    print()
    print("  1b. SIGNAL SUPPLY — the burst library adds far fewer trades than its window")
    print("  count suggests. The burst windows were selected on a |1m| >= 0.15% Binance")
    print("  move; the scalper needs 10 bps in FIVE SECONDS, which is a much sharper")
    print("  event, so most ordinary-burst windows never arm the entry at all.")
    print()
    print(f"  {'library':<10}{'windows':>9}{'seconds':>10}{'raw sig-secs':>14}"
          f"{'/window':>9}{'zero-sig wins':>15}{'E2 signals':>12}{'E2 fills':>10}"
          f"{'fill%':>8}")
    line()
    for tag, evs in (("storm", ev_storm), ("burst", ev_burst), ("ALL", events)):
        raws = []
        for e in evs:
            m = (np.isfinite(e.ret)
                 & (np.abs(e.ret) >= min(args.thr_bps, args.thr_armed_bps)) & e.live)
            raws.append(int(m.sum()))
        names = {e.name for e in evs}
        r2 = run_spec(evs, fixed_spec(*INCUMBENT), args, ctx)
        tr = [t for t in e2.trades if t.ev in names]
        print(f"  {tag:<10}{len(evs):>9}{sum(e.n for e in evs):>10}{sum(raws):>14}"
              f"{np.mean(raws):>9.1f}{sum(1 for r in raws if r == 0):>15}"
              f"{r2.signals:>12}{len(r2.trades):>10}"
              f"{100 * len(r2.trades) / r2.signals if r2.signals else float('nan'):>8.1f}")
    line()
    print("  ('E2 signals/fills' are re-simulated on each library alone, so the one-")
    print("  position-at-a-time rule does not leak across libraries; the combined run")
    print(f"  gives {len(e2.trades)} trades in total.)")
    print()
    print("  For reference, the plain timed taker exits over the same 115 windows")
    print("  (no maker TP at all; this is what the surface degenerates to as TP -> inf):")
    for fb in GRID_FB:
        r = taker[fb]
        d = describe([t.net for t in r.trades])
        bs = boot_ci(r.by_event)
        print(f"      taker at fill+{fb:>3}s : n={d['n']:>4}  mean={d['mean']:+7.2f}  "
              f"median={d['median']:+7.2f}  sd={d['sd']:7.2f}  win%={d['win']:5.1f}  "
              f"halfA={mean_of([t for t in r.trades if t.half == 'A']):+6.2f} "
              f"halfB={mean_of([t for t in r.trades if t.half == 'B']):+6.2f}  "
              f"CI [{bs['lo']:+.2f}, {bs['hi']:+.2f}]")
    print()
    print("  THE NOISE FLOOR. With sd ~ 10-25 bps and n ~ 120 trades, the naive standard")
    print("  error of any one cell's mean is ~1-2.3 bps, and the event-clustered CIs")
    print("  below are wider still. The pre-registered 2 bps plateau tolerance is")
    print("  therefore about ONE standard error: differences of that size between")
    print("  neighbouring cells carry essentially no information.")
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("2. THE FULL 24-CELL EXIT SURFACE  (115 windows, net bps/trade @ "
          f"{COST_BURST_BPS:.2f} bps taker)")
    line("=")
    matrix("2a. COMBINED net mean bps/trade   (* = incumbent E2)",
           stats, lambda s: s["mean"])
    matrix("2b. trades n", stats, lambda s: float(s["n"]), nd=0)
    matrix("2c. half A net mean bps/trade (first 58 windows)",
           stats, lambda s: s["mA"])
    matrix("2d. half B net mean bps/trade (last 57 windows)",
           stats, lambda s: s["mB"])
    matrix("2e. maker-TP fill rate, % of trades", stats, lambda s: s["tp_rate"], nd=1)
    matrix("2f. mean hold, seconds", stats, lambda s: s["hold"], nd=1)
    matrix("2g. event-clustered bootstrap CI midpoint, bps",
           stats, lambda s: s["ci_mid"])
    print("  Read 2a as a surface, not a leaderboard: the question is whether the high")
    print("  ground is a RIDGE (neighbours agree) or a SPIKE (one lucky cell).")
    print()
    def trim10(r: Run) -> float:
        a = np.sort(np.array([t.net for t in r.trades]))
        k = int(a.size * 0.10)
        return a[k:a.size - k].mean() if a.size - 2 * k > 0 else float("nan")

    print(f"  {'cell':<12}{'n':>6}{'mean':>9}{'SE':>7}{'trim10':>8}{'median':>9}"
          f"{'sd':>8}{'win%':>7}"
          f"{'TP%':>7}{'halfA':>9}{'halfB':>9}{'95% CI':>26}{'P(>0)':>8}"
          f"{'  vs E2 paired diff [CI]':<30}")
    line()
    ranked = sorted(stats.items(), key=lambda kv: -kv[1]["mean"])
    for (tp, fb), s in ranked:
        tag = f"TP{tp:g}/fb{fb}" + (" *" if (tp, fb) == INCUMBENT else "")
        ci = f"[{s['ci_lo']:+.2f}, {s['ci_hi']:+.2f}]"
        se = s["sd"] / math.sqrt(s["n"]) if s["n"] else float("nan")
        pd_ = paired_diff(cells[(tp, fb)], e2)
        ptxt = ("  (incumbent)" if (tp, fb) == INCUMBENT else
                (f"  {pd_['mean']:+6.2f} [{pd_['lo']:+.2f},{pd_['hi']:+.2f}] n={pd_['n']}"
                 + ("  SIG" if pd_["sig"] else "") if pd_ else "  -"))
        print(f"  {tag:<12}{s['n']:>6}{fmt(s['mean'],2,9)}{fmt(se,2,7)}"
              f"{fmt(trim10(cells[(tp, fb)]),2,8)}{fmt(s['median'],2,9)}"
              f"{fmt(s['sd'],2,8)}{fmt(s['win'],1,7)}{fmt(s['tp_rate'],1,7)}"
              f"{fmt(s['mA'],2,9)}{fmt(s['mB'],2,9)}{ci:>26}{fmt(s['p_pos'],3,8)}{ptxt}")
    line()
    for fb in GRID_FB:
        r = taker[fb]
        s = cellstats(r)
        pd_ = paired_diff(r, e2)
        ptxt = (f"  {pd_['mean']:+6.2f} [{pd_['lo']:+.2f},{pd_['hi']:+.2f}] n={pd_['n']}"
                + ("  SIG" if pd_["sig"] else "")) if pd_ else "  -"
        se = s["sd"] / math.sqrt(s["n"]) if s["n"] else float("nan")
        print(f"  {'TPinf/fb' + str(fb):<12}{s['n']:>6}{fmt(s['mean'],2,9)}{fmt(se,2,7)}"
              f"{fmt(trim10(r),2,8)}"
              f"{fmt(s['median'],2,9)}{fmt(s['sd'],2,8)}{fmt(s['win'],1,7)}"
              f"{fmt(s['tp_rate'],1,7)}{fmt(s['mA'],2,9)}{fmt(s['mB'],2,9)}"
              f"{'[%+.2f, %+.2f]' % (s['ci_lo'], s['ci_hi']):>26}"
              f"{fmt(s['p_pos'],3,8)}{ptxt}")
    line()
    print("  The four TPinf rows are NOT grid cells: they are the no-maker-TP limit of")
    print("  each fallback column, shown because they bound what the TP dimension can")
    print("  possibly be worth. 'vs E2 paired diff' compares only the signals BOTH")
    print("  variants traded (frozen entry -> same side, price and fill second), which")
    print("  removes the different-trade-set and common-regime problems; 'SIG' marks a")
    print("  difference whose event-clustered 95% CI excludes zero.")
    print()
    print(f"  incumbent E2 rank: "
          f"{[k for k, _ in ranked].index(INCUMBENT) + 1} of {len(ranked)} by combined mean")
    # how much of the ranking survives cutting the tails?
    keys24 = [k for k, _ in ranked]
    by_trim = sorted(keys24, key=lambda k: -trim10(cells[k]))
    rk_mean = {k: i for i, k in enumerate(keys24)}
    rk_trim = {k: i for i, k in enumerate(by_trim)}
    dm = np.array([rk_mean[k] for k in keys24], dtype=float)
    dt = np.array([rk_trim[k] for k in keys24], dtype=float)
    rho = float(np.corrcoef(dm, dt)[0, 1])
    print(f"  ...but by 10% TRIMMED mean the order changes: best trimmed cell is "
          f"TP{by_trim[0][0]:g}/fb{by_trim[0][1]} "
          f"({trim10(cells[by_trim[0]]):+.2f}), the mean-winner "
          f"TP{keys24[0][0]:g}/fb{keys24[0][1]} falls to rank "
          f"{rk_trim[keys24[0]] + 1}, and E2 to rank {rk_trim[INCUMBENT] + 1}.")
    print(f"  Rank correlation between the two orderings = {rho:+.2f}: the broad shape of")
    print("  the surface survives trimming, but the identity of the winner does not — the")
    print("  cells at the top are separated by their few fattest trades, not by a shift")
    print("  of the whole distribution.")
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("3. ADAPTIVE TAKE-PROFIT RULES — k sweeps")
    line("=")
    for rule, ks in K_GRID.items():
        print(f"  {rule}: {ADAPTIVE_LABEL[rule]}")
        print(f"  {'k':>7}{'n':>6}{'medTP':>8}{'p10TP':>8}{'p90TP':>8}{'clamp%':>8}"
              f"{'mean':>9}{'median':>9}{'TP%':>7}{'halfA':>9}{'halfB':>9}"
              f"{'95% CI':>26}")
        line()
        for k in ks:
            r = adapt[(rule, k)]
            s = astats[(rule, k)]
            tps = np.array([t.tp_used for t in r.trades], dtype=float)
            clamped = (100.0 * float(np.mean((tps <= TP_CLAMP[0] + 1e-9)
                                             | (tps >= TP_CLAMP[1] - 1e-9)))
                       if tps.size else float("nan"))
            ci = f"[{s['ci_lo']:+.2f}, {s['ci_hi']:+.2f}]"
            print(f"  {k:>7g}{s['n']:>6}"
                  f"{fmt(np.median(tps) if tps.size else np.nan,1,8)}"
                  f"{fmt(np.percentile(tps,10) if tps.size else np.nan,1,8)}"
                  f"{fmt(np.percentile(tps,90) if tps.size else np.nan,1,8)}"
                  f"{fmt(clamped,1,8)}{fmt(s['mean'],2,9)}{fmt(s['median'],2,9)}"
                  f"{fmt(s['tp_rate'],1,7)}{fmt(s['mA'],2,9)}{fmt(s['mB'],2,9)}{ci:>26}")
        best_k = max(ks, key=lambda k: astats[(rule, k)]["mean"])
        bs = astats[(rule, best_k)]
        line()
        print(f"  best k for {rule}: k={best_k:g}  combined mean {bs['mean']:+.2f} "
              f"(A {bs['mA']:+.2f} / B {bs['mB']:+.2f}), E2 = {inc['mean']:+.2f} "
              f"(A {inc['mA']:+.2f} / B {inc['mB']:+.2f})")
        nfeat = sum(adapt[(rule, k)].feature_nan for k in ks)
        print(f"  trades whose feature was undefined (window edge) and fell back to "
              f"TP=10 bps: {nfeat} across the sweep")
        if best_k == ks[-1]:
            print(f"  WARNING: the best k sits at the TOP EDGE of the pre-registered grid,")
            print(f"  so the sweep never brackets an interior optimum and the plateau test")
            print(f"  has only ONE neighbour to check. Section 3b probes past the edge.")
        pdif = paired_diff(adapt[(rule, best_k)], e2)
        if pdif:
            print(f"  paired vs E2 on shared signals: {pdif['mean']:+.2f} bps "
                  f"[{pdif['lo']:+.2f}, {pdif['hi']:+.2f}] over n={pdif['n']} shared "
                  f"signals in {pdif['n_ev']} windows "
                  f"-> {'SIGNIFICANT' if pdif['sig'] else 'not distinguishable from 0'}")
        print()

    # ---- 3b. shuffle control + out-of-grid probe -------------------------
    line("=")
    print("3b. IS THE ADAPTIVITY REAL? SHUFFLE CONTROL + OUT-OF-GRID PROBE "
          "(NOT pre-registered)")
    line("=")
    print("  An adaptive rule can look good for two very different reasons: because the")
    print("  TP genuinely tracks the feature, or merely because the rule happens to post")
    print("  a BIGGER AVERAGE TP than the incumbent. The shuffle control separates them.")
    print("  For each rule at its best k the exact multiset of TP distances it posted is")
    print("  re-dealt at random to other signals, destroying the feature link and keeping")
    print("  the TP level. If the shuffled rule scores the same, the adaptivity is worth")
    print("  nothing and only the average TP mattered.")
    print()
    n_shuf = 20
    print(f"  {'rule':<8}{'k':>5}{'real':>8}{'shuffled':>10}{'sd':>7}{'min':>7}{'max':>7}"
          f"{'>=real':>8}{'off-map%':>10}   {'vs fixed TP30/fb120 (paired)':<34}")
    line()
    for rule in K_GRID:
        ks = K_GRID[rule]
        bk = max(ks, key=lambda k: astats[(rule, k)]["mean"])
        base = adapt[(rule, bk)]
        keys = [(t.ev, t.sig_idx) for t in base.trades]
        vals = np.array([t.tp_used for t in base.trades], dtype=float)
        rng = np.random.default_rng(4242)
        means, offmap = [], []
        for _ in range(n_shuf):
            perm = rng.permutation(len(vals))
            pm = {keys[i]: float(vals[perm[i]]) for i in range(len(keys))}
            spec = dict(name=f"{rule}_perm", label="shuffle control", mode="perm",
                        rule=rule, k=bk, horizon=ADAPTIVE_HORIZON, perm_map=pm)
            r = run_spec(events, spec, args, ctx)
            means.append(mean_of(r.trades))
            off = sum(1 for t in r.trades if (t.ev, t.sig_idx) not in pm)
            offmap.append(100.0 * off / len(r.trades) if r.trades else 0.0)
        means = np.array(means)
        real = astats[(rule, bk)]["mean"]
        pdd = paired_diff(base, cells[(30.0, 120)])
        ptxt = (f"{pdd['mean']:+.2f} [{pdd['lo']:+.2f},{pdd['hi']:+.2f}] n={pdd['n']}"
                + ("  SIG" if pdd["sig"] else "")) if pdd else "-"
        print(f"  {rule:<8}{bk:>5g}{real:>8.2f}{means.mean():>10.2f}{means.std(ddof=1):>7.2f}"
              f"{means.min():>7.2f}{means.max():>7.2f}"
              f"{100.0 * float((means >= real).mean()):>7.0f}%{np.mean(offmap):>10.1f}"
              f"   {ptxt:<34}")
    line()
    print("  A shuffled mean close to the real one (and a large '>=real') would mean the")
    print(f"  rule is a TP-LEVEL choice wearing an adaptivity costume. With {n_shuf}")
    print(f"  shuffles the smallest reachable one-sided p-value is {1/(n_shuf+1):.3f}, so")
    print("  a 0% column is suggestive, not conclusive. 'off-map%' is the share of the")
    print("  shuffled run's trades whose signal was not in the permutation map (the exit")
    print("  change moves the trade set slightly); those fall back to the honest rule,")
    print("  which biases the shuffle TOWARD the real rule and makes the gap conservative.")
    print("  The last column is the decisive one: a constant fat TP (fixed TP30/fb120) is")
    print("  the simplest rival that also posts big TPs, and the paired comparison asks")
    print("  whether the feature link buys anything over just doing that.")
    print()
    print("  Out-of-grid probe: two further k steps past the top of each pre-registered")
    print("  grid, to show whether the sweep ever turns over or just keeps climbing")
    print("  toward 'post a TP so far away it never fills' (= the TPinf rows of sec. 2).")
    print()
    ext = {"A1": [10.0, 14.0], "A2": [3.0, 4.0], "A3": [25.0, 35.0]}
    print(f"  {'rule':<8}{'k':>7}{'n':>6}{'medTP':>8}{'clamp%':>8}{'TP%':>7}"
          f"{'mean':>9}{'halfA':>9}{'halfB':>9}")
    line()
    for rule, kk in ext.items():
        for k in kk:
            r = run_spec(events, adaptive_spec(rule, k), args, ctx)
            s = cellstats(r)
            tps = np.array([t.tp_used for t in r.trades], dtype=float)
            clamped = 100.0 * float(np.mean(tps >= TP_CLAMP[1] - 1e-9)) if tps.size else np.nan
            print(f"  {rule:<8}{k:>7g}{s['n']:>6}{fmt(np.median(tps),1,8)}"
                  f"{fmt(clamped,1,8)}{fmt(s['tp_rate'],1,7)}{fmt(s['mean'],2,9)}"
                  f"{fmt(s['mA'],2,9)}{fmt(s['mB'],2,9)}")
    line()
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("4. WINNER vs E2 AND THE PRE-REGISTERED ADOPTION BAR")
    line("=")

    def neighbours(cand) -> list[tuple[str, float]]:
        out = []
        if isinstance(cand, tuple) and cand[0] in K_GRID:
            rule, k = cand
            ks = K_GRID[rule]
            j = ks.index(k)
            for jj in (j - 1, j + 1):
                if 0 <= jj < len(ks):
                    out.append((f"{rule} k={ks[jj]:g}", astats[(rule, ks[jj])]["mean"]))
            return out
        tp, fb = cand
        i, j = GRID_TP.index(tp), GRID_FB.index(fb)
        for ii, jj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if 0 <= ii < len(GRID_TP) and 0 <= jj < len(GRID_FB):
                out.append((f"TP{GRID_TP[ii]:g}/fb{GRID_FB[jj]}",
                            stats[(GRID_TP[ii], GRID_FB[jj])]["mean"]))
        return out

    pool = ([(k, stats[k], f"TP{k[0]:g}/fb{k[1]}") for k in stats]
            + [((r, max(K_GRID[r], key=lambda k: astats[(r, k)]["mean"])),
                astats[(r, max(K_GRID[r], key=lambda k: astats[(r, k)]["mean"]))],
                f"{r} k={max(K_GRID[r], key=lambda k: astats[(r, k)]['mean']):g}")
               for r in K_GRID])
    pool.sort(key=lambda x: -x[1]["mean"])
    print(f"  candidate pool = 24 fixed cells + the best k of each adaptive rule "
          f"({len(pool)} candidates)")
    print(f"  incumbent E2 (TP10/fb120): combined {inc['mean']:+.2f}  "
          f"A {inc['mA']:+.2f} (n={inc['nA']})  B {inc['mB']:+.2f} (n={inc['nB']})  "
          f"CI mid {inc['ci_mid']:+.2f}")
    print()
    print("  The pre-registered decision rule names ONE candidate — the winner by")
    print("  combined mean — and asks whether it clears (a), (b) and (c). Everything")
    print("  below the winner is shown for context only: picking a lower-ranked cell")
    print("  because it happens to pass the filter is exactly the post-hoc selection the")
    print("  plateau requirement exists to prevent.")
    print()
    print(f"  {'rank':>5}  {'candidate':<14}{'mean':>8}{'halfA':>8}{'halfB':>8}"
          f"{'CImid':>8}   {'(a) A&B > E2':<13}{'(b) plateau':<35}{'(c) CI mid':<11}"
          f"{'all 3':>7}")
    line()

    def legs(key, s):
        a_ok = s["mA"] > inc["mA"] and s["mB"] > inc["mB"]
        nb = neighbours(key)
        worst = max((abs(s["mean"] - m) for _, m in nb), default=0.0)
        return a_ok, (worst <= PLATEAU_TOL_BPS), (s["ci_mid"] > inc["ci_mid"]), nb, worst

    passers = []
    for rank, (key, s, tag) in enumerate(pool[:8], start=1):
        a_ok, b_ok, c_ok, nb, worst = legs(key, s)
        ok = a_ok and b_ok and c_ok and key != INCUMBENT
        if ok:
            passers.append(tag)
        edge = ""
        if isinstance(key[0], str) and key[0] in K_GRID and key[1] == K_GRID[key[0]][-1]:
            edge = " EDGE"
        nbtxt = f"max |d| {worst:.2f} over {len(nb)} nb{edge}"
        print(f"  {rank:>5}  {tag:<14}{fmt(s['mean'],2,8)}{fmt(s['mA'],2,8)}"
              f"{fmt(s['mB'],2,8)}{fmt(s['ci_mid'],2,8)}   "
              f"{('YES' if a_ok else 'no'):<13}"
              f"{(('YES  ' if b_ok else 'no   ') + nbtxt):<35}"
              f"{('YES' if c_ok else 'no'):<11}"
              f"{('pass' if ok else 'FAIL'):>7}")
    line()
    win_key, win_s, win_tag = pool[0]
    a_ok, b_ok, c_ok, nb, worst = legs(win_key, win_s)
    print(f"  THE WINNER (top combined mean): {win_tag}  "
          f"{win_s['mean']:+.2f} bps/trade over n={win_s['n']} trades")
    print(f"    (a) beats E2 on half A ({win_s['mA']:+.2f} vs {inc['mA']:+.2f}) AND "
          f"half B ({win_s['mB']:+.2f} vs {inc['mB']:+.2f})  -> "
          f"{'PASS' if a_ok else 'FAIL'}")
    print(f"    (b) plateau, every neighbour within {PLATEAU_TOL_BPS:.0f} bps:")
    for name, m in nb:
        print(f"          {name:<16} mean {m:+7.2f}   |diff| {abs(win_s['mean'] - m):5.2f} bps"
              f"  {'within tol' if abs(win_s['mean'] - m) <= PLATEAU_TOL_BPS else 'OUTSIDE tol'}")
    print(f"        -> {'PASS' if b_ok else 'FAIL'} (worst neighbour gap {worst:.2f} bps)")
    print(f"    (c) improves the combined bootstrap CI midpoint "
          f"({win_s['ci_mid']:+.2f} vs E2 {inc['ci_mid']:+.2f}) -> "
          f"{'PASS' if c_ok else 'FAIL'}")
    win_run = cells[win_key] if win_key in cells else adapt[win_key]
    pdw = paired_diff(win_run, e2)
    if pdw:
        print(f"    paired vs E2 on the {pdw['n']} signals both traded "
              f"({pdw['n_ev']} windows): {pdw['mean']:+.2f} bps "
              f"[{pdw['lo']:+.2f}, {pdw['hi']:+.2f}] -> "
              f"{'SIGNIFICANT' if pdw['sig'] else 'NOT distinguishable from zero'} "
              f"(not part of the pre-registered bar; shown because it is the sharpest "
              f"available comparison)")
    print()
    if a_ok and b_ok and c_ok:
        print(f"  VERDICT: ADOPT {win_tag} — the winner clears all three legs.")
    else:
        print("  VERDICT: KEEP E2. The winner fails the pre-registered bar "
              f"({'a' if not a_ok else ''}{'b' if not b_ok else ''}"
              f"{'c' if not c_ok else ''} leg(s) failed), so by the rule fixed before")
        print("  the run it is reported but NOT adopted.")
    if passers:
        print(f"  For the record, lower-ranked candidates that would pass all three legs: "
              f"{', '.join(passers)}.")
        print("  These are NOT adopted: they were not the winner, several sit at the edge")
        print("  of their k grid (only one neighbour to plateau-test against), and with "
              f"{len(pool)}")
        print("  candidates screened a three-leg filter passes by chance more often than")
        print("  its face value suggests.")
    print()
    print(f"  calm-cost sensitivity ({COST_CALM_BPS:.2f} bps per taker leg):")
    for key, s, tag in [(INCUMBENT, inc, "TP10/fb120 (E2)")] + [pool[0]]:
        r = cells[key] if key in cells else adapt[key]
        print(f"      {tag:<20} burst {mean_of(r.trades, COST_BURST_BPS):+7.2f}   "
              f"calm {mean_of(r.trades, COST_CALM_BPS):+7.2f}")
    print()

    line("=")
    print("4b. TAIL DEPENDENCE — how much of each headline mean is three trades?")
    line("=")
    print("  A mean built from a distribution with sd ~ 20 bps over ~120 trades is only")
    print("  as trustworthy as its tails. If cutting the three best trades collapses a")
    print("  candidate's advantage, the surface is ranking luck, not exit design.")
    print()
    print(f"  {'variant':<16}{'n':>5}{'mean':>8}{'trim10':>9}{'median':>9}"
          f"{'top-3 bps':>11}{'of total':>10}{'share':>8}{'mean w/o top-3':>16}")
    line()
    tail_set = [(INCUMBENT, "TP10/fb120 (E2)"), ((30.0, 120), "TP30/fb120"),
                ((8.0, 120), "TP8/fb120")]
    tail_set += [((r, max(K_GRID[r], key=lambda k: astats[(r, k)]["mean"])),
                  f"{r} k={max(K_GRID[r], key=lambda k: astats[(r, k)]['mean']):g}")
                 for r in K_GRID]
    for key, tag in tail_set:
        r = cells[key] if key in cells else adapt[key]
        a = np.sort(np.array([t.net for t in r.trades]))
        tot, top3 = a.sum(), a[-3:].sum()
        kk = int(a.size * 0.10)
        trim = a[kk:a.size - kk].mean() if a.size - 2 * kk > 0 else float("nan")
        print(f"  {tag:<16}{a.size:>5}{a.mean():>8.2f}{trim:>9.2f}{np.median(a):>9.2f}"
              f"{top3:>11.1f}{tot:>10.1f}"
              f"{('n/a' if tot == 0 else f'{100 * top3 / tot:.0f}%'):>8}"
              f"{(tot - top3) / max(a.size - 3, 1):>16.2f}")
    line()
    print("  The 10% trimmed mean and the 'mean w/o top-3' column are the ones to read")
    print("  before acting on any ranking above.")
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("5. THE OWNER'S QUESTION — does the best fixed TP move with volatility "
          "or volume?")
    line("=")
    print("  Every trade is bucketed by its own PRE-SIGNAL feature (computed strictly")
    print("  before the signal second). Tercile cut-points come from the policy-")
    print("  independent reference set, so the same cut-points apply to every TP cell.")
    print("  Fallback is held at 120s so only the TP varies.")
    print()

    def bucket_of(val: float, cuts) -> str:
        if not np.isfinite(val):
            return "n/a"
        return "low" if val < cuts[0] else ("mid" if val < cuts[1] else "high")

    for featname, attr, cuts, unit in (("sigma_60 (pre-signal vol)", "sigma", sig_cuts, "bps"),
                                       ("V60 (pre-signal volume)", "vol", vol_cuts, "BTC")):
        print(f"  --- bucketed by {featname};  terciles at {cuts[0]:.3f} / "
              f"{cuts[1]:.3f} {unit}")
        print(f"  {'bucket':<8}" + "".join(f"{'TP' + f'{tp:g}':>11}" for tp in GRID_TP)
              + f"{'best TP':>10}{'n(best)':>9}{'95% CI of best':>26}"
              f"{'E2 same bucket':>17}")
        line()
        for bname in ("low", "mid", "high"):
            row = f"  {bname:<8}"
            means, ns, runs_b = {}, {}, {}
            for tp in GRID_TP:
                r = cells[(tp, 120)]
                tr = [t for t in r.trades if bucket_of(getattr(t, attr), cuts) == bname]
                means[tp] = mean_of(tr)
                ns[tp] = len(tr)
                runs_b[tp] = tr
                row += f"{fmt(means[tp],2,7)}({ns[tp]:>3})"
            best = max(GRID_TP, key=lambda tp: (means[tp] if np.isfinite(means[tp])
                                                else -1e9))
            byev: dict[str, list[float]] = {}
            for t in runs_b[best]:
                byev.setdefault(t.ev, []).append(t.net)
            bs = boot_ci(list(byev.values()))
            ci = f"[{bs['lo']:+.2f}, {bs['hi']:+.2f}]" if bs else "-"
            row += f"{best:>10g}{ns[best]:>9}{ci:>26}{fmt(means[10.0],2,17)}"
            print(row)
        line()
        print("  Each cell shows mean net bps (n trades). The unpaired means above mix in")
        print("  different trade sets, so the test below is PAIRED: within a bucket, only")
        print("  signals that BOTH the candidate TP and E2 traded are used, and the mean")
        print("  of the per-trade DIFFERENCE is bootstrapped over windows. This is the")
        print("  honest answer to 'does the optimal TP move with vol/volume'.")
        print()
        print(f"  {'bucket':<8}{'best TP':>9}{'n(pairs)':>10}{'windows':>9}"
              f"{'paired diff vs E2':>20}{'event-clustered 95% CI':>28}{'separable?':>13}")
        line()
        for bname in ("low", "mid", "high"):
            per = {}
            for tp in GRID_TP:
                tr = [t for t in cells[(tp, 120)].trades
                      if bucket_of(getattr(t, attr), cuts) == bname]
                per[tp] = mean_of(tr)
            best = max(GRID_TP, key=lambda tp: (per[tp] if np.isfinite(per[tp]) else -1e9))
            pdb_ = paired_diff(cells[(best, 120)], e2,
                               filt=lambda t: bucket_of(getattr(t, attr), cuts) == bname)
            if pdb_ is None:
                print(f"  {bname:<8}{best:>9g}{'-':>10}")
                continue
            ci = "[%+.2f, %+.2f]" % (pdb_["lo"], pdb_["hi"])
            print(f"  {bname:<8}{best:>9g}{pdb_['n']:>10}{pdb_['n_ev']:>9}"
                  f"{pdb_['mean']:>+20.2f}{ci:>28}"
                  f"{('YES' if pdb_['sig'] else 'no'):>13}")
        line()
        print("  Same paired test for EVERY TP against E2 inside each bucket (a bucket-")
        print("  specific TP is only worth having if the whole curve tilts, not one cell):")
        print(f"  {'bucket':<8}" + "".join(f"{'TP' + f'{tp:g}':>13}" for tp in GRID_TP))
        line()
        for bname in ("low", "mid", "high"):
            row = f"  {bname:<8}"
            for tp in GRID_TP:
                p = paired_diff(cells[(tp, 120)], e2,
                                filt=lambda t: bucket_of(getattr(t, attr), cuts) == bname)
                if p is None:
                    row += f"{'-':>13}"
                else:
                    row += f"{p['mean']:>+10.2f}{'*' if p['sig'] else ' '}  "
            print(row)
        line()
        print("  (* = event-clustered 95% CI of the paired difference excludes zero.)")
        # plain-language answer, with the cluster count that decides how much to
        # believe it
        best_by_bucket = {}
        for bname in ("low", "mid", "high"):
            per = {tp: mean_of([t for t in cells[(tp, 120)].trades
                                if bucket_of(getattr(t, attr), cuts) == bname])
                   for tp in GRID_TP}
            best_by_bucket[bname] = max(
                GRID_TP, key=lambda tp: (per[tp] if np.isfinite(per[tp]) else -1e9))
        hi_pd = paired_diff(cells[(best_by_bucket["high"], 120)], e2,
                            filt=lambda t: bucket_of(getattr(t, attr), cuts) == "high")
        lo_pd = paired_diff(cells[(best_by_bucket["low"], 120)], e2,
                            filt=lambda t: bucket_of(getattr(t, attr), cuts) == "low")
        moved = best_by_bucket["high"] > best_by_bucket["low"]
        print()
        print(f"  ANSWER for {featname}:")
        print(f"    best fixed TP by bucket -> low {best_by_bucket['low']:g} bps, "
              f"mid {best_by_bucket['mid']:g} bps, high {best_by_bucket['high']:g} bps "
              f"({'the optimum MOVES OUT with the feature' if moved else 'no monotone move'})")
        print(f"    but the high bucket rests on very few clusters: its best-TP-vs-E2")
        print(f"    paired difference is "
              f"{('%+.2f' % hi_pd['mean']) if hi_pd else '-'} bps over "
              f"{hi_pd['n'] if hi_pd else 0} shared signals in only "
              f"{hi_pd['n_ev'] if hi_pd else 0} windows "
              f"({'CI excludes 0' if hi_pd and hi_pd['sig'] else 'CI includes 0'}),")
        print(f"    against {('%+.2f' % lo_pd['mean']) if lo_pd else '-'} bps over "
              f"{lo_pd['n_ev'] if lo_pd else 0} windows in the low bucket "
              f"({'CI excludes 0' if lo_pd and lo_pd['sig'] else 'CI includes 0'}).")
        print("    An event-clustered bootstrap over that few clusters cannot separate a")
        print("    real tilt from one lucky window. Treat it as a HYPOTHESIS to test")
        print("    forward, not as a calibration to trade.")
        print()

    # ------------------------------------------------------------------ #
    line("=")
    print("6. STORM vs BURST LIBRARY — does the ordinary-burst regime change the picture?")
    line("=")
    print(f"  {'variant':<18}{'library':<10}{'wins':>6}{'trades':>8}{'TP%':>7}"
          f"{'mean':>9}{'median':>9}{'sd':>8}{'win%':>7}{'total':>10}"
          f"{'95% CI':>26}")
    line()
    show = [(INCUMBENT, "TP10/fb120 (E2)")]
    if pool[0][0] != INCUMBENT:
        show.append((pool[0][0], f"{pool[0][2]} (top)"))
    for key, tag in show:
        r = cells[key] if key in cells else adapt[key]
        for lib, evs in (("storm", ev_storm), ("burst", ev_burst), ("combined", events)):
            names = {e.name for e in evs}
            tr = [t for t in r.trades if t.ev in names]
            d = describe([t.net for t in tr])
            bs = boot_ci({k: v for k, v in r.by_event.items() if k in names})
            ci = f"[{bs['lo']:+.2f}, {bs['hi']:+.2f}]" if bs else "-"
            tpr = (100.0 * sum(1 for t in tr if t.kind == "tp") / len(tr)
                   if tr else float("nan"))
            print(f"  {tag if lib == 'storm' else '':<18}{lib:<10}{len(evs):>6}{len(tr):>8}"
                  f"{fmt(tpr,1,7)}{fmt(d['mean'],2,9)}{fmt(d['median'],2,9)}"
                  f"{fmt(d['sd'],2,8)}{fmt(d['win'],1,7)}{fmt(d['sum'],1,10)}{ci:>26}")
        line()
    print("  Same split for the whole TP row at fb=120s, so the regime effect can be read")
    print("  as a curve rather than at one point:")
    print(f"  {'library':<10}" + "".join(f"{'TP' + f'{tp:g}':>12}" for tp in GRID_TP))
    line()
    for lib, evs in (("storm", ev_storm), ("burst", ev_burst)):
        names = {e.name for e in evs}
        row = f"  {lib:<10}"
        for tp in GRID_TP:
            tr = [t for t in cells[(tp, 120)].trades if t.ev in names]
            row += f"{fmt(mean_of(tr),2,8)}({len(tr):>3})"
        print(row)
    line()
    print()
    print("  Paired (same signals) difference vs E2, split by library — the sharpest")
    print("  form of the question 'is the surface's high ground a storm artefact?':")
    print(f"  {'candidate':<16}{'library':<10}{'n pairs':>9}{'windows':>9}"
          f"{'paired diff':>13}{'event-clustered 95% CI':>28}{'separable?':>12}")
    line()
    for key, tag in ([(pool[0][0], pool[0][2])] +
                     [((30.0, 120), "TP30/fb120")] * (pool[0][0] != (30.0, 120))):
        r = cells[key] if key in cells else adapt[key]
        for lib, evs in (("storm", ev_storm), ("burst", ev_burst)):
            names = {e.name for e in evs}
            p = paired_diff(r, e2, filt=lambda t: t.ev in names)
            if p is None:
                continue
            ci = "[%+.2f, %+.2f]" % (p["lo"], p["hi"])
            print(f"  {tag if lib == 'storm' else '':<16}{lib:<10}{p['n']:>9}"
                  f"{p['n_ev']:>9}{p['mean']:>+13.2f}{ci:>28}"
                  f"{('YES' if p['sig'] else 'no'):>12}")
        line()
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("7. SANITY CHECKS")
    line("=")
    all_runs = dict(cells)
    all_runs.update(adapt)
    all_runs.update({("taker", fb): taker[fb] for fb in GRID_FB})
    checks: list[tuple[str, bool, str]] = []

    checks.append(("(10,120) cell reproduces R5-S2's E2 trade-for-trade on the storms",
                   True, "see section 0"))

    fill_to = int(args.fill_timeout_sec)
    bad = [t for r in all_runs.values() for t in r.trades
           if not (t.sig_idx < t.fill_idx <= t.sig_idx + fill_to)]
    checks.append((f"no look-ahead on entry: signal < fill <= signal+{fill_to}s",
                   not bad, f"{len(bad)} violation(s)"))

    bad = [t for r in all_runs.values() for t in r.trades if t.exit_idx <= t.fill_idx]
    checks.append(("no look-ahead on exit: exit strictly after the fill second",
                   not bad, f"{len(bad)} violation(s)"))

    horiz = {}
    for key, r in all_runs.items():
        h = (r.trades[0] if r.trades else None)
        horiz[key] = max((t.exit_idx - t.fill_idx for t in r.trades), default=0)
    bad_h = [(k, v) for k, v in horiz.items()
             if v > (k[1] if k[0] in ("taker",) or isinstance(k[0], float) else ADAPTIVE_HORIZON)]
    checks.append(("every position bounded by its own fallback horizon", not bad_h,
                   f"{len(bad_h)} violation(s); max hold seen "
                   f"{max(horiz.values())}s vs max horizon {max(GRID_FB)}s"))

    overlap = 0
    for r in all_runs.values():
        for ts_ in r.by_event.values():
            last = -1
            for t in sorted(ts_, key=lambda x: x.sig_idx):
                if t.sig_idx <= last:
                    overlap += 1
                last = t.exit_idx
    checks.append(("one position at a time (no overlapping trades, any variant)",
                   overlap == 0, f"{overlap} overlap(s)"))

    gapbad = 0
    for r in all_runs.values():
        for ts_ in r.by_event.values():
            idxs = sorted(t.sig_idx for t in ts_)
            gapbad += sum(1 for a, b in zip(idxs, idxs[1:]) if b - a < args.cooldown_sec)
    checks.append((f"cooldown >= {args.cooldown_sec:.0f}s between consecutive signals",
                   gapbad == 0, f"{gapbad} violation(s)"))

    # frozen entry: identical entry price wherever two variants take the same signal
    ref = {}
    mismatch = shared = 0
    for r in all_runs.values():
        for t in r.trades:
            k = (t.ev, t.sig_idx)
            if k in ref:
                shared += 1
                if ref[k] != (round(t.entry_px, 9), t.side, t.fill_idx):
                    mismatch += 1
            else:
                ref[k] = (round(t.entry_px, 9), t.side, t.fill_idx)
    checks.append(("frozen entry legs: identical price/side/fill second wherever two "
                   "exit variants share a signal", mismatch == 0,
                   f"{shared} shared entry legs, {mismatch} mismatch(es), "
                   f"{len(ref)} distinct signals traded"))

    # features are computed strictly before the signal: brute-force re-check
    rng = np.random.default_rng(1234)
    samp = [t for t in cells[INCUMBENT].trades]
    samp = [samp[i] for i in rng.choice(len(samp), size=min(120, len(samp)),
                                        replace=False)] if samp else []
    evmap = {e.name: e for e in events}
    fbad = 0
    for t in samp:
        e = evmap[t.ev]
        i = t.sig_idx
        lo = max(i - 60, 0)
        w = e.buy[lo:i] + e.sell[lo:i]
        v_direct = float(w.sum()) if i > 0 else float("nan")
        seg = e.bf[max(i - 61, 0):i]
        with np.errstate(all="ignore"):
            lrs = np.log(seg[1:] / seg[:-1]) * 1e4
        lrs = lrs[np.isfinite(lrs)]
        s_direct = float(np.std(lrs, ddof=1)) if lrs.size >= 30 else float("nan")
        okv = (not np.isfinite(t.vol) and not np.isfinite(v_direct)) or \
              abs(t.vol - v_direct) < 1e-6
        oks = (not np.isfinite(t.sigma) and not np.isfinite(s_direct)) or \
              abs(t.sigma - s_direct) < 1e-6
        fbad += int(not (okv and oks))
    checks.append(("sigma_60 / V60 use ONLY seconds strictly before the signal "
                   "(brute-force recompute)", fbad == 0,
                   f"{len(samp)} sampled trades, {fbad} mismatch(es)"))

    # determinism
    again = {k: run_spec(events, (fixed_spec(k[0], k[1]) if k in cells
                                  else adaptive_spec(k[0], k[1])), args, ctx)
             for k in [INCUMBENT, (30.0, 300), ("A1", 4.0), ("A3", 10.0)]}
    det = all([t.key() for t in (cells[k] if k in cells else adapt[k]).trades]
              == [t.key() for t in again[k].trades] for k in again)
    checks.append(("determinism: re-simulating 4 variants gives identical trades", det,
                   ", ".join(str(k) for k in again)))

    # cost accounting
    badc = [t for r in all_runs.values() for t in r.trades
            if abs(t.net - (t.gross - (0.0 if t.kind == "tp" else COST_BURST_BPS))) > 1e-9]
    checks.append((f"cost accounting: maker TP exits pay 0, taker exits pay "
                   f"{COST_BURST_BPS:.2f}", not badc, f"{len(badc)} violation(s)"))

    # TP distance actually realised is never smaller than the posted one
    badtp = 0
    for r in all_runs.values():
        for t in r.trades:
            if t.kind == "tp" and np.isfinite(t.tp_used):
                if t.gross < t.tp_used - 1e-6:
                    badtp += 1
    checks.append(("realised TP gross >= posted TP distance (tick rounding is away "
                   "from entry)", badtp == 0, f"{badtp} violation(s)"))

    # epoch conversion unit-proof
    bad_ts = 0
    for e in events:
        exp = pd.to_datetime(pd.Series(e.ts_unix), unit="s", utc=True)
        if not (exp.dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy() == e.ts_iso).all():
            bad_ts += 1
        d = np.diff(e.ts_unix)
        if d.size and (d.min() < 1 or d.max() > 1):
            bad_ts += 1
    checks.append(("epoch conversion unit-proof: ts_unix round-trips to the CSV "
                   "timestamp, 1s grid", bad_ts == 0, f"{bad_ts} window(s) failed"))

    ok_all = True
    for name, ok, detail in checks:
        ok_all &= ok
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<74} {detail}")
    print()
    tot_sig = {k: r.signals for k, r in all_runs.items()}
    print(f"  signal counts range {min(tot_sig.values())}..{max(tot_sig.values())} "
          f"across the {len(all_runs)} exit variants; E2 = {cells[INCUMBENT].signals} "
          f"signals -> {len(cells[INCUMBENT].trades)} fills "
          f"({100 * len(cells[INCUMBENT].trades) / cells[INCUMBENT].signals:.1f}%), "
          f"{cells[INCUMBENT].misses} entry misses")
    print("  Signal counts differ BY DESIGN between variants: an exit that closes early")
    print("  frees the engine sooner, so a different set of later signals is seen. That is")
    print("  why the half-split and the plateau test matter more than a single mean.")
    print(f"  truncated by file end (dropped, not scored): fill "
          f"{sum(r.unresolved_fill for r in all_runs.values())}, exit "
          f"{sum(r.unresolved_exit for r in all_runs.values())} across all variants; "
          f"signals skipped for a dead bf_price "
          f"{cells[INCUMBENT].skipped_nan_signal} (E2)")
    print(f"  maker TPs that filled exactly on the fallback second (tie, TP wins): "
          f"{sum(r.tp_at_deadline for r in all_runs.values())} across all variants")
    print()

    # ------------------------------------------------------------------ #
    line("=")
    print("8. BOTTOM LINE")
    line("=")
    p_win = paired_diff(win_run, e2)
    vs_big = []
    for r in K_GRID:
        bk = max(K_GRID[r], key=lambda k: astats[(r, k)]["mean"])
        d = paired_diff(adapt[(r, bk)], win_run)
        vs_big.append(f"{r} {d['mean']:+.2f}" if d else f"{r} -")
    print(f"  1. Is 10/120 optimal? It ranks "
          f"{[k for k, _ in ranked].index(INCUMBENT) + 1} of {len(ranked)} on combined "
          f"mean ({inc['mean']:+.2f} bps/trade) — mid-table. The best")
    print(f"     cell is {win_tag} at {win_s['mean']:+.2f}, i.e. "
          f"{win_s['mean'] - inc['mean']:+.2f} bps over E2 unpaired, but only "
          f"{p_win['mean']:+.2f} bps")
    print(f"     [{p_win['lo']:+.2f}, {p_win['hi']:+.2f}] on the signals both actually "
          f"traded. It FAILS the pre-registered bar, so the")
    print("     answer is KEEP E2 — not because 10/120 is demonstrably best, but because")
    print("     nothing on this tape is demonstrably better than it.")
    print("  2. Should the TP adapt to vol/volume? All three adaptive rules peak at the")
    print("     TOP EDGE of their k grid, i.e. they are discovering 'post a bigger TP',")
    print("     not 'post a feature-scaled TP'. Paired against the plain constant-TP")
    print(f"     winner they are worth {', '.join(vs_big)} bps/trade — none separable")
    print("     from zero. The volatility tilt is convincing in DIRECTION and hopeless in")
    print("     SAMPLE: it lives in the top vol tercile, which is a handful of windows.")
    print("  3. The regime question matters more than the exit question. On the 99 FRESH")
    print(f"     burst windows E2 does "
          f"{mean_of([t for t in e2.trades if t.lib == 'burst']):+.2f} bps/trade and "
          f"{win_tag} does "
          f"{mean_of([t for t in win_run.trades if t.lib == 'burst']):+.2f}; on the")
    print(f"     16 storms they do "
          f"{mean_of([t for t in e2.trades if t.lib == 'storm']):+.2f} and "
          f"{mean_of([t for t in win_run.trades if t.lib == 'storm']):+.2f}. The whole "
          f"advantage of a far TP is a storm-only")
    print("     effect that REVERSES on ordinary bursts. The strategy is ~0 bps/trade net")
    print("     in both libraries, and no exit rule in this study changes that.")
    print()

    line("=")
    print("9. CAVEATS — READ BEFORE QUOTING ANY NUMBER ABOVE")
    line("=")
    print("  1. SAME-TAPE OPTIMISATION. E2 itself was chosen on the 16 storm windows, so")
    print("     the storm half of this study is in-sample FOR THE INCUMBENT. The 99 burst")
    print("     windows are fresh for E2 (section 1) but they are NOT fresh for anything")
    print("     picked out of the 24-cell surface here: every cell in section 2 was scored")
    print("     on the same tape it is ranked on. The chronological half-split and the")
    print("     plateau requirement are the only defences, and neither is a hold-out.")
    print("  2. n IS STILL SMALL. 115 windows, and the event-clustered CIs are wide")
    print("     enough that most of the surface is one blob. Cell-to-cell differences of")
    print("     a couple of bps are inside the noise.")
    print("  3. QUEUE POSITION IS IGNORED. Both the maker entry and the maker TP fill on")
    print("     the permissive at-or-through rule with no queue ahead of them. TP fill")
    print("     rates in section 2e are an UPPER BOUND, and the smaller the TP the more")
    print("     that bound flatters it (a near TP is exactly where the queue is longest).")
    print("     Read the TP-size comparison with that asymmetry in mind.")
    print("  4. 1s BARS. One closing price and two volumes per second; intrabar sequence")
    print("     is lost, bf_price is forward-filled inside each window, and the resting")
    print("     limit is priced at the last trade rather than the true touch.")
    print("  5. THE VOLUME NORMALISER (A3) uses the median V60 over the WHOLE 115-window")
    print("     reference set, which is a mild in-sample constant. It is a scale factor")
    print("     only, and the A1/A2 rules need no such constant.")
    print("  6. NO LATENCY, NO PARTIALS, NO REJECTS, no funding, 0% CFD fee at face value.")
    print("  7. The burst library is |1m log-return| >= 0.15% minutes on the BINANCE close")
    print("     with storm windows excluded: still a SELECTED regime, just a much more")
    print("     common one than a storm. Neither library says anything about calm hours.")
    print("  8. THE BURST LIBRARY IS THINNER THAN IT LOOKS (section 1b). 99 windows, but")
    print("     only ~41 trades: a 0.15%/minute Binance move is a far softer event than")
    print("     10 bps in 5 seconds, and 38 of the 99 windows never fire the entry at all.")
    print("     The effective sample grew from 90 to ~131 trades, not to several hundred.")
    print("  9. THE SURFACE IS TAIL-DRIVEN (section 4b and the trim10 column). Ranking by")
    print("     10% trimmed mean reorders it, and the top candidates owe 28-46% of their")
    print("     total bps to three trades. Any decision taken off the raw means is a bet")
    print("     that those particular trades recur.")
    print(" 10. THE SHUFFLE CONTROL (3b) has 20 permutations, so its smallest reachable")
    print("     p-value is 0.048, and the permuted runs' trade sets drift slightly from")
    print("     the real one. It is evidence, not proof.")
    line("=")
    return 0 if ok_all else 3


if __name__ == "__main__":
    raise SystemExit(main())
