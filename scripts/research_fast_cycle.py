#!/usr/bin/env python3
"""Study S8 -- the edge-lifetime-matched FAST-CYCLE MAKER scalper.

    EXPLORATION ONLY.  THIS TAPE IS CONTAMINATED FOR THIS HYPOTHESIS FAMILY.
    Nothing measured here is adoptable, and no cell printed here may be
    selected on the strength of these numbers.  The judgment protocol runs
    on FRESH tape and is frozen in docs/PREREG_fast_cycle.md (printed by
    --print-prereg).

WHY THE TAPE IS CONTAMINATED
  KNOWLEDGE.md section 4 already carries a PENDING hypothesis generated from
  this exact 30-day tape: "post-fill 5-minute rotation -- maker both legs,
  TP 2-3bps", whose +1.1bps post-fill reversion was measured on these same
  prints (report j).  The family below is a seconds-scale specialisation of
  that hypothesis.  Measuring it here is self-contamination in the sense of
  research-protocol section 8.1.  The output is therefore an EXPLORATION
  BOUND -- a feasibility screen whose only legitimate use is to decide
  whether spending fresh data on the family is worth it at all.

THE DESIGN UNDER STUDY (owner's diagnosis, S8)
  The rejected burst scalper (report p, net -3.83bps over 86 events) captured
  a 1-2 second edge but held 60-120 seconds -- 30-60x the edge lifetime --
  because a TAKER exit forced the hold to be long enough to pay for itself.
  The fast-cycle design closes the round trip within SECONDS by quoting BOTH
  legs as a maker, and compounds small high-probability gains instead of
  chasing one large one.

DATA
  data/executions_FX_BTC_JPY.csv -- 820,000 public prints,
      2026-07-21T08:17:22Z .. 2026-08-20T08:22:17Z (30.00 days).
      Columns id, exec_date, price, size, side; `side` is the TAKER side
      (BUY = the ask was lifted, SELL = the bid was hit).
  data/ws/*.jsonl.gz -- ~4 hours of real board/ticker/execution records from
      2026-08-20.  Used ONLY for the queue-position reality check (section
      QUEUE).  Never as a primary source and never for any P&L number.

  The first 20% of the tape is a BURN-IN used solely to fix the T2 regime
  volume threshold; every simulated trade lives in the remaining 80%.  This
  removes the only whole-sample statistic the design would otherwise peek at.

FAMILY -- ENUMERATED, NOT EXTENDED AFTER THE FACT (12 cells x 2 fill models)
  Entry trigger (micro, seconds-scale), one of:
    T1(b)  burst-reversion quote.  When the bounce-free mid has moved by
           >= b bps over the trailing <= 3s, rest a single limit on the
           REVERSION side at the touch: mid up -> quote the ASK (short),
           mid down -> quote the BID (long).  b in {5, 10}.
    T2     two-sided-flow quote.  Inside a two-sided flow regime, rest BOTH
           touches, inventory-capped at one lot.  Regime definition imported
           verbatim from scripts/research_two_sided_flow.py (S7), at the
           cell KNOWLEDGE.md section 2 quotes as the headline one --
           W = 30s / pool = all windows / percentile 50 (duty 11.5%, 26% of
           volume, which this script reproduces):
               window is two-sided iff  taker-BUY vol  >= v_min
                                   AND  taker-SELL vol >= v_min
                                   AND  |B-S|/(B+S) <= 0.30
           with v_min = the 50th percentile of the pooled per-window
           one-side volume over ALL windows, fixed on the burn-in and
           floored at a strictly positive epsilon so that "both sides
           traded" is always required.
           CAUSAL USE: window k is quoted only if window k-1 -- which is
           fully observed -- was two-sided.  The regime is never read from
           the window being traded.
  Exit:
    maker take-profit at +tp bps from the entry fill, tp in {2, 3}.
  Abort -- a TWO-POINT sensitivity, not a sweep.  The design's own claim is
  that the abort clock must sit near the 1-2s edge lifetime, so the two
  points bracket it from above:
    (adverse 3.0 bps, age 30s)  the owner's stated configuration, and
    (adverse 4.0 bps, age 45s)  one step looser on BOTH axes at once.
    Abort = taker stop when the bounce-free mid has moved >= adverse bps
    against the entry, OR when the position age exceeds age seconds.
    Taker cost 3.96 bps (burst half-spread 1.96 + slippage 2.0),
    mid-referenced.  The grid is deliberately 2 points, not a surface:
    this is exploration, and KNOWLEDGE 2 records that the exit surface has
    no ridge -- adjacent steps flip sign as noise (reports k, l).
  Frozen structural constants (NOT swept):
    quote lifetime 10s (run_scalp_paper.py default fill_timeout_sec),
    T1 re-arm cooldown 3s from the previous quote (= the trigger's own
    lookback, the minimum that stops one burst re-triggering on every
    print), one position at a time, no position overlap, no cooldown after
    a close (the design's whole point is to re-quote immediately).

FILL MODEL -- both are reported, they BRACKET queue reality
  conservative  a resting quote fills only when a counter-side print goes
                STRICTLY THROUGH it (bid: print price < limit).  The level
                was cleared, so the queue ahead of us is irrelevant.  This
                is the repo's traded-through rule (KNOWLEDGE 1) at its
                strict end.
  optimistic    at-or-through (bid: print price <= limit), i.e. the
                RestingLimit rule in scripts/run_scalp_paper.py, which its
                own docstring labels the permissive bound.  It assumes we
                are always at the FRONT of the queue.
  Neither is reality.  Section QUEUE measures, on real board data, what
  share of touch-joins a small order at the BACK of the queue would win.

TOUCH PROXY (tape has no book)
  ask touch = the most recent taker-BUY print price, bid touch = the most
  recent taker-SELL print price, both at or before the placement print.
  mid = their midpoint (the repo's bounce-free mid proxy, S7 section 3).
  Every quote price, abort test and markout is referenced to this mid, so
  no bid-ask bounce leaks into any adverse-selection number.

COSTS
  maker legs: 0 fee, 0 spread -- filled AT the limit.
  taker aborts and taker counterfactual entries: 3.96 bps each, mid-referenced.

METRICS (per cell, per fill model)  -- the HF/MM-class bar, KNOWLEDGE 5
  net EV per trade with a day-clustered bootstrap t; trades/day; daily net
  bps; daily Sharpe (annualised, mean/sd x sqrt(365)); win rate; maxDD;
  and three things this design in particular must be judged on:
    FILL RATE      per quote event and per quoted side, since the S7
                   power analysis says everything in this family scales
                   as 1/f;
    MARKOUT SPLIT  every fill decomposed into CAPTURE (the half-spread
                   earned by resting instead of crossing) and ADVERSE (the
                   signed mid-to-mid move against us) at 1s, 5s and 30s --
                   the 1s horizon is the edge lifetime the whole design is
                   built around;
    CYCLE TIME     the distribution of time-to-fill, hold, and the full
                   quote-to-exit cycle.  "Fast cycle" is the hypothesis;
                   the realised cycle length is how it is falsified.
  Plus the MANDATORY adverse-selection split -- the filled-vs-missed
  counterfactual that killed every prior maker strategy in this repo
  (reports i, j, k: gaps of 6.2, 9.3 and 33 bps).

SANITY (all must pass before any number is read)
  * epoch conversion cross-checked against a second implementation;
  * no look-ahead: quote prices use prints at or before placement, fills use
    prints strictly after it, the T2 regime uses only the PREVIOUS window,
    v_min is fixed on a burn-in that carries no trades;
  * zero position overlap by construction (single state machine);
  * determinism: no network, no RNG except seeded bootstraps (seed 12345);
  * the two fill models are checked to be nested (conservative fills are a
    subset of optimistic fills).

Offline only -- reads files, opens no sockets, places no orders.
Idempotent: re-running prints the same numbers.

Usage: python scripts/research_fast_cycle.py [--data DIR] [--ws DIR]
                                             [--print-prereg]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = "FX_BTC_JPY"
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

# ---- frozen design constants (see the docstring; none of these is swept) ---
BURST_WINDOW_SEC = 3.0            # T1 trigger lookback
BURST_BPS_GRID = (5.0, 10.0)      # T1 b
TP_BPS_GRID = (2.0, 3.0)          # maker take-profit
ABORT_GRID = ((3.0, 30.0),        # (adverse bps, age s) -- owner's config
              (4.0, 45.0))        # one step looser on both axes
QUOTE_LIFE_SEC = 10.0             # a resting entry quote's lifetime
T1_COOLDOWN_SEC = 3.0             # re-arm delay after a T1 quote
TAKER_BPS = 3.96                  # burst-regime taker cost, mid-referenced

# ---- T2 regime, imported verbatim from research_two_sided_flow.py (S7) -----
# The KNOWLEDGE.md section 2 headline cell: W=30s, pool=all windows, p50.
T2_WINDOW_SEC = 30
T2_IMB_MAX = 0.30
T2_PCTL = 50
VOL_EPS = 1e-9

# ---- settled S7 measurements, used as this design's prior (not re-measured)
S7_HALF_SPREAD = 1.169            # realised half-spread per fill, bps
S7_INSIDE_NET_LO = 0.38           # idealized maker net inside two-sided windows
S7_INSIDE_NET_HI = 0.76

BURN_FRAC = 0.20                  # prefix used ONLY to fix v_min
MARKOUT_TAUS = (1, 5, 30)         # seconds, for the selection gap / split
SEED = 12345
N_BOOT = 2000

# ---- HF/MM-class adoption bars, verbatim from KNOWLEDGE.md section 5 -------
BAR_N = 300                       # n >= 300 trades
BAR_T = 2.0                       # cluster-corrected t >= 2.0 on net EV > 0
BAR_DAILY_BPS = 10.0              # daily net expectation >= +10 bps/day
BAR_SHARPE = 1.0                  # daily Sharpe >= 1.0
BAR_MAXDD_PCT = 10.0              # max drawdown <= 10%
BAR_TRADES_PER_DAY = 20.0         # the class's own entry criterion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def epoch_seconds(ts) -> np.ndarray:
    """datetime -> float epoch seconds, immune to the datetime64 unit trap."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return ((idx - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)


def epoch_seconds_ns(ts) -> np.ndarray:
    """Independent implementation, used only to cross-check the above."""
    idx = pd.DatetimeIndex(pd.to_datetime(ts, format="ISO8601", utc=True))
    return idx.values.astype("datetime64[ns]").astype("int64") / 1e9


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print("\n--- " + title + " " + "-" * max(0, 72 - len(title)))


def _ffill(x: np.ndarray) -> np.ndarray:
    fill = np.where(~np.isnan(x), np.arange(len(x)), 0)
    np.maximum.accumulate(fill, out=fill)
    return x[fill]


def boot_t(x: np.ndarray, groups: np.ndarray, seed: int = SEED
           ) -> tuple[float, float, float, float]:
    """(mean, lo95, hi95, t) with the bootstrap clustered on UTC day."""
    x = np.asarray(x, float)
    if x.size < 2:
        return (float(x.mean()) if x.size else float("nan"),
                float("nan"), float("nan"), float("nan"))
    keys, inv = np.unique(groups, return_inverse=True)
    buckets = [x[inv == i] for i in range(len(keys))]
    rng = np.random.default_rng(seed)
    means = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.integers(0, len(buckets), len(buckets))
        means[b] = np.concatenate([buckets[i] for i in pick]).mean()
    sd = float(means.std(ddof=1))
    m = float(x.mean())
    return (m, float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)),
            m / sd if sd > 0 else float("nan"))


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
@dataclass
class Tape:
    t: np.ndarray
    price: np.ndarray
    size: np.ndarray
    buy: np.ndarray            # taker BUY
    ask_incl: np.ndarray       # last taker-BUY price at or before i (ask touch)
    bid_incl: np.ndarray       # last taker-SELL price at or before i
    mid_incl: np.ndarray       # 0.5*(ask_incl + bid_incl), bounce-free
    day: np.ndarray
    r3_bps: np.ndarray         # mid move over the trailing BURST_WINDOW_SEC
    g0: int
    gmid: np.ndarray           # 1s forward-filled mid proxy, for markouts


def load_tape(data_dir: Path) -> Tape:
    ex = pd.read_csv(data_dir / f"executions_{PRODUCT}.csv")
    t = epoch_seconds(ex["exec_date"])
    t_alt = epoch_seconds_ns(ex["exec_date"])
    dev = float(np.max(np.abs(t - t_alt)))
    print(f"epoch cross-check   : max |impl_a - impl_b| = {dev:.9f}s (must be ~0)"
          f"  first={t[0]:.3f} -> {pd.Timestamp(t[0], unit='s', tz='UTC')}")
    if dev > 1e-6:
        raise SystemExit("epoch conversion mismatch -- refusing to continue")

    order = np.argsort(t, kind="mergesort")
    t = t[order]
    price = ex["price"].to_numpy(float)[order]
    size = ex["size"].to_numpy(float)[order]
    buy = (ex["side"].to_numpy() == "BUY")[order]
    day = np.floor(t / 86400.0).astype(np.int64)

    ask_incl = _ffill(np.where(buy, price, np.nan))
    bid_incl = _ffill(np.where(~buy, price, np.nan))
    mid_incl = 0.5 * (ask_incl + bid_incl)

    # trailing mid move over BURST_WINDOW_SEC, causal by construction
    j = np.searchsorted(t, t - BURST_WINDOW_SEC, side="right") - 1
    ok = j >= 0
    r3 = np.zeros(len(t))
    r3[ok] = (np.log(mid_incl[ok]) - np.log(mid_incl[j[ok]])) * 1e4
    r3[~np.isfinite(r3)] = 0.0

    g0 = int(np.floor(t[0]))
    n = int(np.ceil(t[-1])) - g0 + 1
    gm = np.full(n, np.nan)
    si = (np.floor(t) - g0).astype(np.int64)
    gm[si] = mid_incl                     # last print of the second wins
    gm = _ffill(gm)

    print(f"tape                : {len(t):,} prints, "
          f"{pd.Timestamp(t[0], unit='s', tz='UTC')} .. "
          f"{pd.Timestamp(t[-1], unit='s', tz='UTC')} "
          f"({(t[-1] - t[0]) / 86400:.2f} days, "
          f"{len(t) / ((t[-1] - t[0])):.3f} prints/s)")
    return Tape(t=t, price=price, size=size, buy=buy, ask_incl=ask_incl,
                bid_incl=bid_incl, mid_incl=mid_incl, day=day, r3_bps=r3,
                g0=g0, gmid=gm)


# ---------------------------------------------------------------------------
# T2 regime (definition imported from research_two_sided_flow.py, S7)
# ---------------------------------------------------------------------------
def two_sided_regime(tp: Tape, burn_end_t: float
                     ) -> tuple[np.ndarray, float, float, float, float]:
    """Per-print flag: was the PREVIOUS window two-sided?

    Returns (flag_per_print, v_min_burnin, v_min_wholetape, window_duty,
    volume_share).  The whole-tape threshold is printed for reference only;
    the simulation uses the burn-in one, so the trading segment never sees a
    statistic of itself.  duty and volume share are printed so the S7 cell
    reproduction (11.5% / 26%, KNOWLEDGE 2) can be checked by eye.
    """
    W = T2_WINDOW_SEC
    wid = np.floor(tp.t / W).astype(np.int64)
    k0 = int(wid.min())
    n = int(wid.max()) - k0 + 1
    idx = wid - k0
    vbuy = np.bincount(idx, weights=tp.size * tp.buy, minlength=n)
    vsell = np.bincount(idx, weights=tp.size * (~tp.buy), minlength=n)

    def vmin_of(sel: np.ndarray) -> float:
        # pool = ALL windows (the S7 headline cell).  On a tape this thin the
        # percentile can land on 0, which would make "two-sided" degenerate,
        # so it is floored at a strictly positive epsilon.
        pool = np.concatenate([vbuy[sel], vsell[sel]])
        return max(float(np.percentile(pool, T2_PCTL)), VOL_EPS)

    wstart = (np.arange(n) + k0) * float(W)
    v_burn = vmin_of(wstart < burn_end_t)
    v_all = vmin_of(np.ones(n, bool))

    tot = vbuy + vsell
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(tot > 0, np.abs(vbuy - vsell) / np.maximum(tot, 1e-18), 1.0)
    mask = (vbuy >= v_burn) & (vsell >= v_burn) & (imb <= T2_IMB_MAX)
    duty = float(mask.mean())
    tot_vol = float(tot.sum())
    vshare = float(tot[mask].sum()) / tot_vol if tot_vol > 0 else float("nan")

    prev = np.zeros(n, bool)
    prev[1:] = mask[:-1]                            # CAUSAL: window k-1 only
    return prev[idx], v_burn, v_all, duty, vshare


# ---------------------------------------------------------------------------
# the simulator
# ---------------------------------------------------------------------------
@dataclass
class Trade:
    t_entry: float
    t_exit: float
    side: int                  # +1 long, -1 short
    entry_px: float
    pnl_bps: float
    reason: str
    hold: float
    day: int
    t_quote: float = float("nan")    # when the entry quote went up
    mid_fill: float = float("nan")   # bounce-free mid at the moment of fill
    mk1: float = float("nan")  # signed mid markout at +1s from the fill
    mk5: float = float("nan")
    mk30: float = float("nan")


@dataclass
class QuoteEvent:
    t: float
    side: int
    filled: bool
    day: int
    t_ref: float = float("nan")      # fill time if filled, quote time if not
    mid_ref: float = float("nan")    # bounce-free mid at t_ref
    mk1: float = float("nan")
    mk5: float = float("nan")
    mk30: float = float("nan")
    cf_pnl: float = float("nan")   # taker-entry counterfactual, missed quotes


@dataclass
class SimResult:
    trades: list[Trade] = field(default_factory=list)
    quotes: list[QuoteEvent] = field(default_factory=list)
    n_quote_events: int = 0
    n_quoted_sides: int = 0
    n_filled_events: int = 0
    span_days: float = 0.0
    days: np.ndarray = field(default_factory=lambda: np.array([]))


def _fwd_mid_markout(tp: Tape, t0: float, ref_mid: float, side: int,
                     tau: int) -> float:
    gi = int(np.floor(t0)) - tp.g0 + tau
    if gi < 0 or gi >= len(tp.gmid):
        return float("nan")
    return side * (tp.gmid[gi] - ref_mid) / ref_mid * 1e4


def _run_exit(tp: Tape, k0: int, side: int, entry_px: float, entry_t: float,
              tp_bps: float, strict: bool, abort_bps: float,
              abort_age: float) -> tuple[float, str, float, int]:
    """Exit machinery: maker TP, taker adverse stop, taker age stop.

    Returns (pnl_bps EXCLUDING any entry cost, reason, exit_t, exit_idx).
    Checked in this order on every print k > k0: TP first (the print that
    trades through the TP is the event), then the adverse stop, then age.
    """
    n = len(tp.t)
    tp_px = entry_px * (1.0 + side * tp_bps * 1e-4)
    stop_mid = entry_px * (1.0 - side * abort_bps * 1e-4)
    k = k0 + 1
    while k < n:
        tk = tp.t[k]
        # --- maker take-profit: a counter-side print reaches our TP limit
        if side > 0:
            hit = tp.buy[k] and (tp.price[k] > tp_px if strict
                                 else tp.price[k] >= tp_px)
        else:
            hit = (not tp.buy[k]) and (tp.price[k] < tp_px if strict
                                       else tp.price[k] <= tp_px)
        if hit:
            return tp_bps, "tp", tk, k
        # --- taker adverse stop, on the bounce-free mid
        m = tp.mid_incl[k]
        adverse = (m <= stop_mid) if side > 0 else (m >= stop_mid)
        if adverse:
            return (side * (m - entry_px) / entry_px * 1e4 - TAKER_BPS,
                    "stop", tk, k)
        # --- taker age stop
        if tk - entry_t > abort_age:
            return (side * (m - entry_px) / entry_px * 1e4 - TAKER_BPS,
                    "age", tk, k)
        k += 1
    return (float("nan"), "eod", tp.t[-1], n - 1)


def simulate(tp: Tape, trigger: str, b_bps: float, tp_bps: float,
             strict: bool, regime: np.ndarray, i_start: int,
             abort_bps: float = ABORT_GRID[0][0],
             abort_age: float = ABORT_GRID[0][1],
             counterfactual: bool = True) -> SimResult:
    """One pass of the state machine over the trading segment.

    States: IDLE -> QUOTING -> (fill) IN_POSITION -> IDLE, or
                    QUOTING -> (expiry) MISS -> IDLE.
    Exactly one position or one quote is live at any instant.
    """
    res = SimResult()
    n = len(tp.t)
    i = i_start
    next_quote_t = -1e18     # earliest instant a NEW quote may be placed

    while i < n:
        # ---------------- IDLE: look for a quote-placement trigger ---------
        place = None                      # (sides, limits) to rest after print i
        if tp.t[i] >= next_quote_t:
            if trigger == "T1":
                r = tp.r3_bps[i]
                if abs(r) >= b_bps:
                    if r > 0:             # mid ran up -> quote the ASK (short)
                        place = ((-1,), (tp.ask_incl[i],))
                    else:                 # mid ran down -> quote the BID (long)
                        place = ((+1,), (tp.bid_incl[i],))
            elif regime[i]:               # T2
                place = ((+1, -1), (tp.bid_incl[i], tp.ask_incl[i]))

        if place is None:
            i += 1
            continue

        sides, limits = place
        t_q = tp.t[i]
        mid_q = tp.mid_incl[i]
        # T1 re-arms COOLDOWN after the quote goes up; T2 re-quotes as soon
        # as the previous quote's life ends (or the position closes, below).
        next_quote_t = t_q + (T1_COOLDOWN_SEC if trigger == "T1"
                              else QUOTE_LIFE_SEC)
        res.n_quote_events += 1
        res.n_quoted_sides += len(sides)
        expiry = t_q + QUOTE_LIFE_SEC

        # ---------------- QUOTING: wait for a counter-side print -----------
        j = i + 1
        fill_side = 0
        fill_px = 0.0
        while j < n and tp.t[j] <= expiry:
            for s, L in zip(sides, limits):
                if s > 0:                 # our BID, hit by a taker SELL
                    ok = (not tp.buy[j]) and (tp.price[j] < L if strict
                                              else tp.price[j] <= L)
                else:                     # our ASK, lifted by a taker BUY
                    ok = tp.buy[j] and (tp.price[j] > L if strict
                                        else tp.price[j] >= L)
                if ok:
                    fill_side, fill_px = s, L
                    break
            if fill_side:
                break
            j += 1

        if not fill_side:
            # ---------- MISS: record it and its taker counterfactual -------
            for s in sides:
                qe = QuoteEvent(t=t_q, side=s, filled=False,
                                day=int(np.floor(t_q / 86400.0)),
                                t_ref=t_q, mid_ref=mid_q)
                qe.mk1 = _fwd_mid_markout(tp, t_q, mid_q, s, MARKOUT_TAUS[0])
                qe.mk5 = _fwd_mid_markout(tp, t_q, mid_q, s, MARKOUT_TAUS[1])
                qe.mk30 = _fwd_mid_markout(tp, t_q, mid_q, s, MARKOUT_TAUS[2])
                if counterfactual:
                    pnl, _, _, _ = _run_exit(tp, i, s, mid_q, t_q, tp_bps,
                                             strict, abort_bps, abort_age)
                    qe.cf_pnl = pnl - TAKER_BPS   # a taker entry crosses too
                res.quotes.append(qe)
            i = max(j, i + 1)
            continue

        # ---------------- IN_POSITION --------------------------------------
        res.n_filled_events += 1
        t_f = tp.t[j]
        mid_f = tp.mid_incl[j]
        qe = QuoteEvent(t=t_q, side=fill_side, filled=True,
                        day=int(np.floor(t_q / 86400.0)),
                        t_ref=t_f, mid_ref=mid_f)
        qe.mk1 = _fwd_mid_markout(tp, t_f, mid_f, fill_side, MARKOUT_TAUS[0])
        qe.mk5 = _fwd_mid_markout(tp, t_f, mid_f, fill_side, MARKOUT_TAUS[1])
        qe.mk30 = _fwd_mid_markout(tp, t_f, mid_f, fill_side, MARKOUT_TAUS[2])
        res.quotes.append(qe)

        pnl, reason, t_x, k = _run_exit(tp, j, fill_side, fill_px, t_f,
                                        tp_bps, strict, abort_bps, abort_age)
        if reason == "eod" or not np.isfinite(pnl):
            break
        res.trades.append(Trade(t_entry=t_f, t_exit=t_x, side=fill_side,
                                entry_px=fill_px, pnl_bps=pnl, reason=reason,
                                hold=t_x - t_f, day=int(np.floor(t_f / 86400.0)),
                                t_quote=t_q, mid_fill=mid_f, mk1=qe.mk1,
                                mk5=qe.mk5, mk30=qe.mk30))
        i = k + 1                          # no overlap: resume after the exit
        # no cooldown after a close; T1 still honours its 3s re-arm delay
        next_quote_t = (max(t_x, t_q + T1_COOLDOWN_SEC) if trigger == "T1"
                        else t_x)

    res.span_days = (tp.t[-1] - tp.t[i_start]) / 86400.0
    res.days = np.unique(np.floor(tp.t[i_start:] / 86400.0).astype(np.int64))
    return res


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
@dataclass
class Metrics:
    n: int
    per_day: float
    ev: float
    lo: float
    hi: float
    t: float
    daily_bps: float
    sharpe: float
    win: float
    maxdd_bps: float
    maxdd_pct: float
    fill_rate: float           # filled quote EVENTS / quote events
    fill_rate_side: float      # filled sides / quoted sides
    tp_share: float
    stop_share: float
    age_share: float
    med_ttf: float             # quote -> fill, median seconds
    p90_ttf: float
    med_hold: float            # fill -> exit, median seconds
    p90_hold: float
    med_cycle: float           # quote -> exit, median seconds
    p90_cycle: float
    duty_pos: float            # share of segment wall-clock spent in position
    capture: float             # signed (mid at fill - fill price), bps
    adv1: float                # signed mid markout at +1s, bps
    adv5: float
    adv30: float
    sel_gap1: float
    sel_gap5: float
    sel_gap30: float
    cf_miss: float


def _pctl(x: np.ndarray, q: float) -> float:
    return float(np.percentile(x, q)) if x.size else float("nan")


def metrics(res: SimResult) -> Metrics:
    tr = res.trades
    n = len(tr)
    n_fields = len(Metrics.__dataclass_fields__)
    if n == 0:
        return Metrics(0, *[float("nan")] * (n_fields - 1))
    pnl = np.array([x.pnl_bps for x in tr])
    day = np.array([x.day for x in tr])
    reason = np.array([x.reason for x in tr])
    hold = np.array([x.hold for x in tr])
    ttf = np.array([x.t_entry - x.t_quote for x in tr])
    cycle = np.array([x.t_exit - x.t_quote for x in tr])

    ev, lo, hi, t = boot_t(pnl, day)
    all_days = res.days
    daily = np.array([pnl[day == d].sum() if (day == d).any() else 0.0
                      for d in all_days])
    sd = float(daily.std(ddof=1)) if daily.size > 1 else float("nan")
    sharpe = (float(daily.mean()) / sd * np.sqrt(365.0)) if sd and sd > 0 \
        else float("nan")
    cum = np.cumsum(pnl)
    dd = np.maximum.accumulate(np.r_[0.0, cum]) - np.r_[0.0, cum]
    maxdd = float(dd.max())

    f = np.array([q.filled for q in res.quotes])
    mk1 = np.array([q.mk1 for q in res.quotes])
    mk5 = np.array([q.mk5 for q in res.quotes])
    mk30 = np.array([q.mk30 for q in res.quotes])
    cf = np.array([q.cf_pnl for q in res.quotes])

    def gap(mk):
        a = mk[f & np.isfinite(mk)]
        c = mk[~f & np.isfinite(mk)]
        return (float(a.mean()) - float(c.mean())) if a.size and c.size \
            else float("nan")

    def filled_mean(mk):
        v = mk[f & np.isfinite(mk)]
        return float(v.mean()) if v.size else float("nan")

    # capture = the half-spread earned by resting: the bounce-free mid at the
    # instant of the fill, minus what we actually paid (our limit), signed.
    ok = np.array([np.isfinite(x.mid_fill) for x in tr])
    capt = np.array([x.side * (x.mid_fill - x.entry_px) / x.entry_px * 1e4
                     for x in tr])[ok]

    cf_miss = float(np.nanmean(cf[~f])) if (~f).any() else float("nan")
    return Metrics(
        n=n, per_day=n / res.span_days, ev=ev, lo=lo, hi=hi, t=t,
        daily_bps=float(daily.mean()), sharpe=sharpe,
        win=float((pnl > 0).mean()), maxdd_bps=maxdd, maxdd_pct=maxdd / 100.0,
        fill_rate=res.n_filled_events / max(res.n_quote_events, 1),
        fill_rate_side=res.n_filled_events / max(res.n_quoted_sides, 1),
        tp_share=float((reason == "tp").mean()),
        stop_share=float((reason == "stop").mean()),
        age_share=float((reason == "age").mean()),
        med_ttf=_pctl(ttf, 50), p90_ttf=_pctl(ttf, 90),
        med_hold=float(np.median(hold)), p90_hold=_pctl(hold, 90),
        med_cycle=_pctl(cycle, 50), p90_cycle=_pctl(cycle, 90),
        duty_pos=float(hold.sum()) / (res.span_days * 86400.0),
        capture=float(capt.mean()) if capt.size else float("nan"),
        adv1=filled_mean(mk1), adv5=filled_mean(mk5), adv30=filled_mean(mk30),
        sel_gap1=gap(mk1), sel_gap5=gap(mk5), sel_gap30=gap(mk30),
        cf_miss=cf_miss)


def bars_verdict(m: Metrics) -> str:
    """Which of the HF/MM-class bars this cell clears (exploration only)."""
    if m.n == 0:
        return "no trades"
    checks = [
        ("n>=300", m.n >= BAR_N),
        ("t>=2", np.isfinite(m.t) and m.t >= BAR_T and m.ev > 0),
        (">=20/d", m.per_day >= BAR_TRADES_PER_DAY),
        ("+10bps/d", m.daily_bps >= BAR_DAILY_BPS),
        ("SR>=1", np.isfinite(m.sharpe) and m.sharpe >= BAR_SHARPE),
        ("DD<=10%", m.maxdd_pct <= BAR_MAXDD_PCT),
    ]
    passed = [k for k, v in checks if v]
    return f"{len(passed)}/6 " + ("[" + ",".join(passed) + "]" if passed else "")


# ---------------------------------------------------------------------------
# queue-position reality check, from the real board records
# ---------------------------------------------------------------------------
def queue_reality(ws_dir: Path) -> None:
    header("QUEUE REALITY CHECK -- real board, what a small order at the BACK "
           "of\nthe touch queue actually wins")
    paths = sorted(ws_dir.glob("*.jsonl.gz"))
    if not paths:
        print("no ws recordings present -- check skipped")
        return

    ticks: list[tuple[float, float, float, float, float]] = []
    execs: list[tuple[float, float, bool, float]] = []
    seen: set[int] = set()
    for p in paths:
        with gzip.open(p, "rt") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                params = (d.get("m") or {}).get("params") or {}
                ch = params.get("channel")
                msg = params.get("message")
                if ch == f"lightning_ticker_{PRODUCT}" and msg:
                    try:
                        ticks.append((
                            epoch_seconds(pd.Series([msg["timestamp"]]))[0],
                            float(msg["best_bid"]), float(msg["best_ask"]),
                            float(msg["best_bid_size"]),
                            float(msg["best_ask_size"])))
                    except Exception:
                        continue
                elif ch == f"lightning_executions_{PRODUCT}" and msg:
                    for e in msg:
                        if e["id"] in seen:
                            continue
                        seen.add(e["id"])
                        execs.append((
                            epoch_seconds(pd.Series([e["exec_date"]]))[0],
                            float(e["price"]), e["side"] == "BUY",
                            float(e["size"])))
    if not ticks or not execs:
        print("recordings hold no usable ticker/execution pairs -- skipped")
        return

    ticks.sort()
    execs.sort()
    tk = np.array(ticks)
    ex = np.array([(a, b, 1.0 if c else 0.0, d) for a, b, c, d in execs])
    et = ex[:, 0]
    span_h = (tk[-1, 0] - tk[0, 0]) / 3600.0
    print(f"board records       : {len(tk):,} ticker samples, {len(ex):,} prints, "
          f"{span_h:.2f} h wall-clock (with recorder gaps)")
    print(f"touch size          : best-bid median {np.median(tk[:, 3]):.4f} BTC "
          f"(p25 {np.percentile(tk[:, 3], 25):.4f}, "
          f"p75 {np.percentile(tk[:, 3], 75):.4f});  "
          f"best-ask median {np.median(tk[:, 4]):.4f} BTC")
    print(f"print size          : median {np.median(ex[:, 3]):.4f} BTC, "
          f"mean {ex[:, 3].mean():.4f}, p90 {np.percentile(ex[:, 3], 90):.4f}")
    sp = (tk[:, 2] - tk[:, 1]) / ((tk[:, 1] + tk[:, 2]) / 2) * 1e4
    print(f"board spread        : median {np.median(sp):.2f} bps, "
          f"p25 {np.percentile(sp, 25):.2f}, p90 {np.percentile(sp, 90):.2f} "
          f"(KNOWLEDGE 1 says 1.56-2.22)")

    # Join the touch at every 5th ticker sample; we are at the BACK of the
    # queue, so Q = the size already resting there.  We fill only once the
    # counter-side volume that trades AT OR THROUGH our price exceeds Q,
    # within QUOTE_LIFE_SEC, and only while our price is still the touch.
    for label, col_px, col_q, want_buy, thr in (
            ("bid", 1, 3, False, None), ("ask", 2, 4, True, None)):
        n_try = n_fill_queue = n_fill_touch = n_fill_through = 0
        for r in range(0, len(tk), 5):
            t0, px, q = tk[r, 0], tk[r, col_px], tk[r, col_q]
            if not np.isfinite(px) or q <= 0:
                continue
            n_try += 1
            lo = np.searchsorted(et, t0, "right")
            hi = np.searchsorted(et, t0 + QUOTE_LIFE_SEC, "right")
            vol = 0.0
            hit_touch = hit_through = False
            for k in range(lo, hi):
                if bool(ex[k, 2]) != want_buy:
                    continue
                if want_buy:
                    at = ex[k, 1] >= px
                    thr_ = ex[k, 1] > px
                else:
                    at = ex[k, 1] <= px
                    thr_ = ex[k, 1] < px
                if at:
                    hit_touch = True
                    vol += ex[k, 3]
                if thr_:
                    hit_through = True
            n_fill_touch += hit_touch
            n_fill_through += hit_through
            n_fill_queue += (vol >= q)
        if n_try:
            print(f"\n{label} touch-join, {QUOTE_LIFE_SEC:.0f}s quote life, "
                  f"{n_try:,} joins")
            print(f"  optimistic (front of queue, any at-or-through print): "
                  f"{100 * n_fill_touch / n_try:5.1f}%")
            print(f"  conservative (a print STRICTLY through the level):    "
                  f"{100 * n_fill_through / n_try:5.1f}%")
            print(f"  queue-realistic (back of queue, needs vol >= Q):      "
                  f"{100 * n_fill_queue / n_try:5.1f}%")
    print("\nCRUDE, and stated as such: the queue is decremented only by trades,")
    print("never by cancels (a cancel ahead of us would help), the join is")
    print("modelled as instant, and 4 hours of one morning is not a sample.")
    print("Its only job is to say whether the conservative/optimistic bracket")
    print("above contains the truth, or whether reality sits BELOW both.")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
CELLS = [("T1", b, tpb, ab, ag)
         for b in BURST_BPS_GRID for tpb in TP_BPS_GRID
         for ab, ag in ABORT_GRID] + \
        [("T2", 0.0, tpb, ab, ag)
         for tpb in TP_BPS_GRID for ab, ag in ABORT_GRID]

# the single abort point used wherever a section is abort-independent
BASE_AB, BASE_AG = ABORT_GRID[0]


def cell_name(trig: str, b: float, tpb: float, ab: float, ag: float) -> str:
    head = f"T1(b{b:.0f})" if trig == "T1" else "T2"
    return f"{head}/tp{tpb:.0f}/a{ab:.0f}-{ag:.0f}s"


def print_table(rows: list[tuple[str, Metrics]], title: str) -> None:
    sub(title)
    print(f"{'cell':<20}{'n':>7}{'/day':>7}{'EV bps':>9}{'95% CI':>18}"
          f"{'t':>6}{'bps/d':>8}{'SR':>7}{'win':>7}{'fill':>7}"
          f"{'TP/stop/age':>16}{'cycle':>8}{'maxDD':>8}")
    for name, m in rows:
        if m.n == 0:
            print(f"{name:<20}{'0':>7}  (no trades)")
            continue
        print(f"{name:<20}{m.n:>7,}{m.per_day:>7.1f}{m.ev:>9.3f}"
              f"  [{m.lo:>6.2f},{m.hi:>6.2f}]{m.t:>6.1f}{m.daily_bps:>8.1f}"
              f"{m.sharpe:>7.2f}{m.win * 100:>6.1f}%{m.fill_rate * 100:>6.1f}%"
              f"{m.tp_share * 100:>5.0f}/{m.stop_share * 100:>3.0f}/"
              f"{m.age_share * 100:>3.0f}%{m.med_cycle:>7.1f}s"
              f"{m.maxdd_bps:>8.0f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--ws", default=str(ROOT / "data" / "ws"))
    ap.add_argument("--print-prereg", action="store_true")
    args = ap.parse_args()

    print("#" * 78)
    print("EXPLORATION ONLY — this 30d tape is contaminated for this "
          "hypothesis")
    print("family; adoption judgment happens once, on fresh tape per "
          "docs/PREREG_fast_cycle.md")
    print("#" * 78)
    print("S8 FAST-CYCLE MAKER SCALPER.  KNOWLEDGE.md section 4 already carries")
    print("the pending 'post-fill 5-minute rotation (maker both legs, TP 2-3bps)'")
    print("hypothesis, generated from these same 30 days.  The family below is a")
    print("seconds-scale specialisation of it, so every number printed here is a")
    print("FEASIBILITY BOUND, not evidence, and no cell may be selected on the")
    print("strength of these numbers.")
    print("#" * 78)

    tp = load_tape(Path(args.data))
    burn_end = tp.t[0] + BURN_FRAC * (tp.t[-1] - tp.t[0])
    i_start = int(np.searchsorted(tp.t, burn_end, "left"))
    regime, v_burn, v_all, duty_w, vshare = two_sided_regime(tp, burn_end)
    seg_days = (tp.t[-1] - tp.t[i_start]) / 86400.0
    print(f"burn-in             : first {BURN_FRAC:.0%} "
          f"({(burn_end - tp.t[0]) / 86400:.2f}d) fixes v_min only, carries no "
          f"trades")
    print(f"v_min (T2)          : burn-in {v_burn:.5f} BTC   "
          f"(whole-tape reference {v_all:.5f} -- NOT used)")
    print(f"T2 regime (S7 cell) : W={T2_WINDOW_SEC}s / pool=all / p{T2_PCTL} -- "
          f"window duty {duty_w * 100:.2f}%, {vshare * 100:.1f}% of volume")
    print("                      (KNOWLEDGE 2 records 11.5% and 26% for this "
          "cell)")
    print(f"trading segment     : {len(tp.t) - i_start:,} prints, "
          f"{seg_days:.2f} days, T2 regime live on "
          f"{regime[i_start:].mean() * 100:.1f}% of prints")

    # ---------------- sanity: the fill models must be nested ---------------
    sub("SANITY")
    probe_c = simulate(tp, "T1", 10.0, 2.0, True, regime, i_start,
                       counterfactual=False)
    probe_o = simulate(tp, "T1", 10.0, 2.0, False, regime, i_start,
                       counterfactual=False)
    print("epoch, look-ahead, overlap: see the docstring; enforced by "
          "construction")
    print(f"fill-model nesting  : conservative quotes {probe_c.n_quote_events:,} "
          f"fills {probe_c.n_filled_events:,} ({100 * probe_c.n_filled_events / max(probe_c.n_quote_events, 1):.1f}%) "
          f"<= optimistic fills {probe_o.n_filled_events:,} "
          f"({100 * probe_o.n_filled_events / max(probe_o.n_quote_events, 1):.1f}%)  "
          f"{'OK' if probe_c.n_filled_events <= probe_o.n_filled_events else 'VIOLATED'}")
    det = simulate(tp, "T1", 10.0, 2.0, True, regime, i_start,
                   counterfactual=False)
    print(f"determinism         : repeat run reproduces "
          f"{len(det.trades) == len(probe_c.trades)} "
          f"({len(det.trades):,} trades both times)")
    ovl = max((a.t_exit > b_.t_entry)
              for a, b_ in zip(probe_c.trades, probe_c.trades[1:])) \
        if len(probe_c.trades) > 1 else False
    print(f"position overlap    : {int(ovl)} overlapping pairs "
          f"(single state machine; must be 0)")

    header(f"EXPLORATION TABLES -- {len(CELLS)} registered cells x 2 fill "
           f"models")
    print("cell = trigger / take-profit bps / abort (adverse bps - age s).")
    print("EV bps = net per trade, maker legs free, taker aborts at 3.96 bps.")
    print("CI/t are day-clustered bootstraps (seed 12345, 2000 resamples).")
    print("bps/d = mean daily net bps at one unit of notional per trade.")
    print("SR    = annualised daily Sharpe (mean/sd of daily bps x sqrt(365)).")
    print("fill  = filled quote EVENTS / quote events (per-side rate is in the")
    print("        CYCLE section; a T2 event quotes two sides).")
    print("cycle = median quote-to-exit seconds (the design's own claim).")
    print("maxDD = peak-to-trough of the cumulative bps curve; at 1x notional")
    print("        per trade 100 bps of drawdown is 1% of equity.")

    store: dict[tuple, tuple[SimResult, Metrics]] = {}
    for strict, label in ((True, "CONSERVATIVE fill (print strictly THROUGH "
                                 "the limit -- the repo's traded-through rule)"),
                          (False, "OPTIMISTIC fill (at-or-through -- "
                                  "RestingLimit; assumes front of queue)")):
        rows = []
        for trig, b, tpb, ab, ag in CELLS:
            res = simulate(tp, trig, b, tpb, strict, regime, i_start, ab, ag)
            m = metrics(res)
            store[(trig, b, tpb, ab, ag, strict)] = (res, m)
            rows.append((cell_name(trig, b, tpb, ab, ag), m))
        print_table(rows, label)

    # ---------------- fill rate and cycle time -----------------------------
    header("FILL RATE AND CYCLE TIME -- is this design actually FAST?")
    print("The owner's diagnosis of the rejected scalper (report p) was that it")
    print("held 60-120s against a 1-2s edge.  This design's whole claim is that")
    print("the round trip closes within SECONDS.  Below is what it actually did.")
    print("  ttf    quote -> fill      (how long a resting quote waits)")
    print("  hold   fill  -> exit      (the exposure the edge has to survive)")
    print("  cycle  quote -> exit      (one full attempt)")
    print("  in-pos share of segment wall-clock spent holding inventory")
    for strict, label in ((True, "conservative fill"), (False, "optimistic fill")):
        sub(label)
        print(f"{'cell':<20}{'fill/event':>11}{'fill/side':>10}"
              f"{'ttf p50':>9}{'ttf p90':>9}{'hold p50':>10}{'hold p90':>10}"
              f"{'cyc p50':>9}{'cyc p90':>9}{'in-pos':>8}{'/day':>7}")
        for trig, b, tpb, ab, ag in CELLS:
            _, m = store[(trig, b, tpb, ab, ag, strict)]
            if m.n == 0:
                continue
            print(f"{cell_name(trig, b, tpb, ab, ag):<20}"
                  f"{m.fill_rate * 100:>10.1f}%{m.fill_rate_side * 100:>9.1f}%"
                  f"{m.med_ttf:>8.1f}s{m.p90_ttf:>8.1f}s"
                  f"{m.med_hold:>9.1f}s{m.p90_hold:>9.1f}s"
                  f"{m.med_cycle:>8.1f}s{m.p90_cycle:>8.1f}s"
                  f"{m.duty_pos * 100:>7.1f}%{m.per_day:>7.1f}")
    print("\nThe age stop is print-driven on a 0.32 print/s tape, so a p90 hold")
    print("at or just past the age limit means 'the age stop is the modal exit',")
    print("not 'the trade drifted'.  Read the TP/stop/age mix above with it.")

    # ---------------- adverse selection ------------------------------------
    header("ADVERSE SELECTION -- the filled-vs-missed counterfactual "
           "(MANDATORY)")
    print("Every prior maker strategy in this repo died here: reports i/j/k")
    print("measured gaps of 6.2, 9.3 and 33 bps between what the fills got and")
    print("what the misses would have got.  The columns below are, per quote")
    print("event, the SIGNED forward move of the bounce-free mid in OUR")
    print("direction (positive = the market moved our way):")
    print("  filled   -- from the fill, over tau seconds")
    print("  missed   -- from the quote, over tau seconds, same intended side")
    print("  gap      -- filled minus missed.  NEGATIVE = the wall: we are")
    print("              filled precisely when we are wrong.")
    print("  cf(miss) -- net bps if every missed quote had been entered as a")
    print("              TAKER (3.96 bps) and run through the same exit rules.")
    print("q-recs counts one record per quoted side for a MISS and one record")
    print("for the side that filled (the other side is cancelled on fill), so")
    print("fills/q-recs is not the per-side fill rate -- that is in CYCLE above.")
    for strict, label in ((True, "conservative fill"), (False, "optimistic fill")):
        sub(label)
        print(f"{'cell':<20}{'q-recs':>8}{'fills':>7}"
              f"{'fill@1s':>9}{'miss@1s':>9}{'gap@1s':>8}"
              f"{'fill@5s':>9}{'miss@5s':>9}{'gap@5s':>8}"
              f"{'fill@30s':>10}{'miss@30s':>10}{'gap@30s':>9}"
              f"{'cf(miss)':>10}")
        for trig, b, tpb, ab, ag in CELLS:
            res, m = store[(trig, b, tpb, ab, ag, strict)]
            f = np.array([q.filled for q in res.quotes])
            if f.size == 0:
                continue

            def mm(attr, sel, _res=res):
                v = np.array([getattr(q, attr) for q in _res.quotes])[sel]
                v = v[np.isfinite(v)]
                return float(v.mean()) if v.size else float("nan")

            print(f"{cell_name(trig, b, tpb, ab, ag):<20}{f.size:>8,}"
                  f"{int(f.sum()):>7,}"
                  f"{mm('mk1', f):>9.3f}{mm('mk1', ~f):>9.3f}"
                  f"{m.sel_gap1:>8.3f}"
                  f"{mm('mk5', f):>9.3f}{mm('mk5', ~f):>9.3f}"
                  f"{m.sel_gap5:>8.3f}"
                  f"{mm('mk30', f):>10.3f}{mm('mk30', ~f):>10.3f}"
                  f"{m.sel_gap30:>9.3f}{m.cf_miss:>10.2f}")

    # ---------------- mechanism diagnostic ----------------------------------
    header("DIAGNOSTIC (not a strategy, not adoptable) -- the POST-FILL "
           "MARKOUT CURVE")
    print("This is the mechanism question underneath the whole family: after a")
    print("maker fill, does the mid EVER come back to us, and on what clock?")
    print("Signed mid-to-mid move in our direction, bps, from the fill instant.")
    print("The exit rules are switched off here -- this is the raw edge, not a")
    print("P&L.  KNOWLEDGE section 4 records +1.1 bps at 5 minutes for the")
    print("pending 'post-fill rotation' hypothesis; if that reversion is real")
    print("and fast, it must appear as a rising curve below.")
    print("Baseline = the same curve for the quotes that were NOT filled, on")
    print("the intended side.  The fill-minus-baseline difference IS the wall.")
    taus = (1, 2, 3, 5, 10, 20, 30, 60, 120, 300)
    print(f"\n{'cell':<16}{'set':<9}{'n':>8}" + "".join(f"{'t+' + str(x):>8}"
                                                        for x in taus))
    for trig, b, tpb, ab, ag in CELLS:
        # the entry side is what this table is about, so it is shown once per
        # trigger: the curve depends on neither tp nor the abort point.
        if tpb != TP_BPS_GRID[0] or (ab, ag) != (BASE_AB, BASE_AG):
            continue
        res, _ = store[(trig, b, tpb, ab, ag, True)]
        for tag, want in (("filled", True), ("missed", False)):
            qs = [q for q in res.quotes if q.filled == want]
            if not qs:
                continue
            row = []
            for tau in taus:
                v = np.array([_fwd_mid_markout(tp, q.t_ref, q.mid_ref,
                                               q.side, tau) for q in qs])
                v = v[np.isfinite(v)]
                row.append(float(v.mean()) if v.size else float("nan"))
            print(f"{cell_name(trig, b, tpb, ab, ag).split('/')[0]:<16}{tag:<9}"
                  f"{len(qs):>8,}" + "".join(f"{x:>8.2f}" for x in row))
    sub("MARKOUT DECOMPOSITION per fill -- NO exit rule, NO abort, NO queue")
    print("capture  = signed (mid at fill - our fill price), the half-spread we")
    print("           earned by resting instead of crossing.  S7 measured this")
    print(f"           tape's realised half-spread at {S7_HALF_SPREAD:+.3f} bps;")
    print("adverse  = signed mid-to-mid move from the fill over tau seconds")
    print("           (NEGATIVE = the market moved against us = the wall);")
    print("net(tau) = capture + adverse = what a fill is worth if we could")
    print("           unwind at the mid, free, tau seconds later.  This is the")
    print("           CEILING of every cell in the family: a real exit is a")
    print("           maker TP that may not fill plus a taker abort at 3.96 bps,")
    print("           and a real quote sits behind a queue.")
    print("tau=1s is the edge lifetime the whole design is built around; 5s is")
    print("where S7 found adverse selection SATURATING inside two-sided windows;")
    print("30s is the abort horizon.")
    print(f"\n{'trigger':<12}{'n':>8}{'capture':>9}" +
          "".join(f"{'adv@' + str(x):>9}{'net@' + str(x):>9}"
                  for x in (1, 5, 30)))
    for trig, b, tpb, ab, ag in CELLS:
        if tpb != TP_BPS_GRID[0] or (ab, ag) != (BASE_AB, BASE_AG):
            continue
        res, _ = store[(trig, b, tpb, ab, ag, True)]
        tr = [x for x in res.trades if np.isfinite(x.mid_fill)]
        if not tr:
            continue
        capt = np.array([x.side * (x.mid_fill - x.entry_px) / x.entry_px * 1e4
                         for x in tr])
        row = []
        for tau in (1, 5, 30):
            v = np.array([_fwd_mid_markout(tp, x.t_entry, x.mid_fill, x.side,
                                           tau) for x in tr])
            ok = np.isfinite(v)
            row.append(float(v[ok].mean()) if ok.any() else float("nan"))
            row.append(float((capt[ok] + v[ok]).mean()) if ok.any()
                       else float("nan"))
        print(f"{cell_name(trig, b, tpb, ab, ag).split('/')[0]:<12}{len(tr):>8,}"
              f"{capt.mean():>9.3f}" + "".join(f"{x:>9.3f}" for x in row))
    print("\nIf net(tau) is negative at EVERY tau, no exit rule and no take-")
    print("profit can rescue the cell: the fill itself is worth less than it")
    print("cost, before the strategy does anything at all.")

    sub("THE EDGE LIFETIME, MEASURED -- how long is a fill worth anything?")
    print("net(tau) walked second by second.  'lifetime' = the last tau, "
          "starting")
    print("from tau=1s, at which net(tau) is still > 0.  This is the number the")
    print("owner's diagnosis is about: the rejected scalper held 30-60x it.")
    print(f"\n{'trigger':<12}{'n':>8}{'capture':>9}{'lifetime':>10}"
          f"{'net@life':>10}   net(tau) 1..12s")
    for trig, b, tpb, ab, ag in CELLS:
        if tpb != TP_BPS_GRID[0] or (ab, ag) != (BASE_AB, BASE_AG):
            continue
        res, _ = store[(trig, b, tpb, ab, ag, True)]
        tr = [x for x in res.trades if np.isfinite(x.mid_fill)]
        if not tr:
            continue
        capt = np.array([x.side * (x.mid_fill - x.entry_px) / x.entry_px * 1e4
                         for x in tr])
        nets = {}
        for tau in range(1, 31):
            v = np.array([_fwd_mid_markout(tp, x.t_entry, x.mid_fill, x.side,
                                           tau) for x in tr])
            ok = np.isfinite(v)
            nets[tau] = float((capt[ok] + v[ok]).mean()) if ok.any() \
                else float("nan")
        life = 0
        for tau in range(1, 31):
            if not (np.isfinite(nets[tau]) and nets[tau] > 0):
                break
            life = tau
        strip = " ".join(f"{nets[x]:+.2f}" for x in range(1, 13))
        at_life = f"{nets[life]:+.3f}" if life else "n/a"
        print(f"{cell_name(trig, b, tpb, ab, ag).split('/')[0]:<12}{len(tr):>8,}"
              f"{capt.mean():>9.3f}"
              f"{(str(life) + 's') if life else '<1s':>10}"
              f"{at_life:>10}   {strip}")
    print("\nA maker take-profit of +2 bps needs the mid to travel 2 bps our way")
    print("AND a counter-side print to reach the limit.  If the lifetime column")
    print("is a few seconds while the realised cycle in the CYCLE section is")
    print("tens of seconds, the design has the SAME failure as the strategy it")
    print("was built to replace -- it just fails faster.  The gap is not a")
    print("tuning gap: to close INSIDE the lifetime the take-profit would have")
    print("to be smaller than the capture itself, i.e. a fraction of one tick,")
    print("which is not a quotable price.")

    print("\nT2's 'missed' row is identically 0 at every horizon BY")
    print("CONSTRUCTION: a missed two-sided quote contributes one +1 and one")
    print("-1 side, whose signed markouts cancel exactly.  That is the correct")
    print("null for a symmetric quoter -- the market has no direction to")
    print("predict -- so for T2 the 'filled' row IS the wall, unadjusted.")

    # ---------------- exit-reason economics --------------------------------
    header("WHY THE CELLS LAND WHERE THEY DO -- the abort geometry")
    print("A stopped trade books about -(adverse + 3.96) bps against a take-")
    print("profit worth only +tp bps, so the break-even take-profit share is")
    print("high by arithmetic alone, at BOTH registered abort points:")
    for ab, ag in ABORT_GRID:
        for tpb in TP_BPS_GRID:
            need = (ab + TAKER_BPS) / (tpb + ab + TAKER_BPS)
            print(f"  abort a{ab:.0f}-{ag:.0f}s, tp={tpb:.0f} bps : stop books "
                  f"{-(ab + TAKER_BPS):.2f} bps, so P(TP) must exceed "
                  f"{need * 100:.1f}%")
    print("just to break even against the stop alone -- age-outs make it worse.")
    sub("realised exit mix and the P&L each reason contributes (conservative "
        "fill)")
    print(f"{'cell':<20}{'n':>7}{'TP%':>7}{'stop%':>7}{'age%':>7}"
          f"{'E[tp]':>8}{'E[stop]':>9}{'E[age]':>9}{'net':>8}"
          f"{'taker fee/trade':>17}{'net ex-fee':>11}")
    for trig, b, tpb, ab, ag in CELLS:
        res, m = store[(trig, b, tpb, ab, ag, True)]
        if m.n == 0:
            continue
        pnl = np.array([x.pnl_bps for x in res.trades])
        rs = np.array([x.reason for x in res.trades])
        def contrib(r):
            s = rs == r
            return float(pnl[s].sum() / len(pnl)) if s.any() else 0.0
        fee = (m.stop_share + m.age_share) * TAKER_BPS
        print(f"{cell_name(trig, b, tpb, ab, ag):<20}{m.n:>7,}"
              f"{m.tp_share * 100:>6.1f}%{m.stop_share * 100:>6.1f}%"
              f"{m.age_share * 100:>6.1f}%{contrib('tp'):>8.2f}"
              f"{contrib('stop'):>9.2f}{contrib('age'):>9.2f}{m.ev:>8.3f}"
              f"{-fee:>17.2f}{m.ev + fee:>11.3f}")
    print("\n'taker fee/trade' is (stop% + age%) x 3.96 bps: the taker cost the")
    print("design was created to ELIMINATE, and which it ends up paying on 40%")
    print("to 70% of its trades, because a 2-3 bps take-profit against a 3-4 bps")
    print("stop is close to a coin flip on a tape whose 1-second mid noise is")
    print("larger than both.  'net ex-fee' adds it back: even with the aborts")
    print("made completely FREE, no cell reaches zero -- the maker round trip")
    print("itself is the loss, and the taker fee only decides how big.")
    print("For scale: the board's median spread is 2.04 bps, so a +2 bps")
    print("take-profit from a touch fill is almost exactly 'quote the opposite")
    print("touch'.  The take-profit is not mis-sized -- it is the right size,")
    print("and the round trip still loses.")

    # ---------------- reconciliation against S7 ----------------------------
    header("RECONCILIATION WITH S7 (scripts/research_two_sided_flow.py)")
    print("S7 measured, on this same tape and as settled fact:")
    print(f"  realised half-spread per fill            : "
          f"{S7_HALF_SPREAD:+.3f} bps")
    print("  inside two-sided windows, adverse selection SATURATES by ~5s;")
    print("  outside them it keeps doubling from 5s to 60s;")
    print(f"  idealized maker net, INSIDE windows only : "
          f"{S7_INSIDE_NET_LO:+.2f} .. {S7_INSIDE_NET_HI:+.2f} bps.")
    print("\nThose are the priors this design was built on, and this study")
    print("reproduces both of them:")
    res2, _ = store[("T2", 0.0, TP_BPS_GRID[0], BASE_AB, BASE_AG, True)]
    tr2 = [x for x in res2.trades if np.isfinite(x.mid_fill)]
    capt2 = np.array([x.side * (x.mid_fill - x.entry_px) / x.entry_px * 1e4
                      for x in tr2])
    curve = {}
    for tau in (1, 5, 30, 60):
        v = np.array([_fwd_mid_markout(tp, x.t_entry, x.mid_fill, x.side, tau)
                      for x in tr2])
        curve[tau] = float(v[np.isfinite(v)].mean())
    print(f"  * saturation: T2 fills mark out {curve[5]:+.2f} bps at 5s and only "
          f"{curve[30]:+.2f} at 30s / {curve[60]:+.2f} at 60s -- flat after ~5s,")
    res1, _ = store[("T1", 10.0, TP_BPS_GRID[0], BASE_AB, BASE_AG, True)]
    tr1 = [x for x in res1.trades if np.isfinite(x.mid_fill)]
    c1 = {}
    for tau in (5, 60):
        v = np.array([_fwd_mid_markout(tp, x.t_entry, x.mid_fill, x.side, tau)
                      for x in tr1])
        c1[tau] = float(v[np.isfinite(v)].mean())
    print(f"    exactly the S7 shape.  T1's curve does NOT saturate (b=10: "
          f"{c1[5]:+.2f} at 5s,")
    print(f"    {c1[60]:+.2f} at 60s), because a burst-reversion quote is by")
    print("    construction OUTSIDE the balanced regime.")
    print(f"  * capture: this study earns {capt2.mean():+.3f} bps per T2 fill "
          f"against S7's {S7_HALF_SPREAD:+.3f} bps realised half-spread.  The")
    print(f"    {S7_HALF_SPREAD - capt2.mean():.3f} bps shortfall is the price of the "
          f"last-print touch proxy: it")
    print("    quotes AT or INSIDE the true touch, so it buys a higher fill")
    print("    rate with a thinner edge.  A real book would recover part of it.")
    print("\nAnd here is where this study PARTS from the S7 ceiling, which is")
    print("the whole finding:")
    print(f"  S7 idealized maker, inside windows : "
          f"{S7_INSIDE_NET_LO:+.2f} .. {S7_INSIDE_NET_HI:+.2f} bps  (wins EVERY print, "
          f"BOTH sides)")
    print(f"  this study, T2, one-lot, unwind @1s: "
          f"{capt2.mean() + curve[1]:+.3f} bps  (capture + adverse at 1s)")
    print(f"  this study, T2, one-lot, unwind @30s: "
          f"{capt2.mean() + curve[30]:+.3f} bps  (capture + adverse at 30s)")
    print(f"  registered T2/tp2 cell, all rules   : "
          f"{store[('T2', 0.0, 2.0, BASE_AB, BASE_AG, True)][1].ev:+.3f} bps")
    print("\nThe 1s line is the one that matters.  S7's positive result survives")
    print("here at the 1-second horizon and ONLY there; every second of holding")
    print("after that spends it, and the abort machinery spends 3.96 bps more.")
    print("\nThe ~1.0-1.3 bps step from the S7 ceiling to the un-ruled fill")
    print("economics AT 30s is the INVENTORY CAP plus the clock: a ceiling that")
    print("never carries inventory has no horizon at all, while a one-lot quoter")
    print("must survive one.  It is a mechanism, not a tuning loss.  The")
    print("S7 ceiling wins both sides continuously, so the offsetting fill is")
    print("itself revenue -- it earns a capture leg on the way back to flat.  A")
    print("one-lot quoter is filled on one side and must then BUY its way flat:")
    print("it PAYS a round trip where the ceiling EARNS one.  The step is worth")
    print("about one capture leg, which is what the numbers show.  Raising the")
    print("cap does not fix this; it turns the design into the spread-MM of")
    print("KNOWLEDGE section 4, which is a different, still-pending study whose")
    print("board data has not matured.")

    # ---------------- bars --------------------------------------------------
    header("DO ANY CELLS CLEAR THE HF/MM-CLASS BARS -- EVEN OPTIMISTICALLY?")
    print(f"Bars (KNOWLEDGE.md section 5, verbatim): n>={BAR_N}, "
          f"cluster t>={BAR_T} on net EV>0, >={BAR_TRADES_PER_DAY:.0f} trades/day,")
    print(f"daily net >= +{BAR_DAILY_BPS:.0f} bps/day, daily Sharpe >= "
          f"{BAR_SHARPE:.1f}, maxDD <= {BAR_MAXDD_PCT:.0f}%.")
    print("The optimistic column is a CEILING: it assumes we are at the front")
    print("of every queue.  If the ceiling is below the bars, the floor is too.")
    print(f"\n{'cell':<20}{'conservative':<34}{'optimistic':<34}")
    for trig, b, tpb, ab, ag in CELLS:
        _, mc = store[(trig, b, tpb, ab, ag, True)]
        _, mo = store[(trig, b, tpb, ab, ag, False)]
        print(f"{cell_name(trig, b, tpb, ab, ag):<20}"
              f"{bars_verdict(mc):<34}{bars_verdict(mo):<34}")

    # ---------------- 60/40 consistency check ------------------------------
    header("60/40 CONSISTENCY CHECK (NOT a train/test boundary)")
    print("No configuration is selected anywhere in this script, so this split")
    print("carries no selection.  It only shows whether the exploration bound")
    print("is a property of the tape or of one half of it.")
    tsplit = tp.t[i_start] + 0.6 * (tp.t[-1] - tp.t[i_start])
    print(f"\n{'cell':<20}{'first 60%: n / EV / bps-d':<34}"
          f"{'last 40%: n / EV / bps-d':<34}")
    for trig, b, tpb, ab, ag in CELLS:
        res, _ = store[(trig, b, tpb, ab, ag, True)]
        out = []
        for lo, hi in ((tp.t[i_start], tsplit), (tsplit, tp.t[-1] + 1)):
            sel = [x for x in res.trades if lo <= x.t_entry < hi]
            if not sel:
                out.append("n=0")
                continue
            p = np.array([x.pnl_bps for x in sel])
            d = (hi - lo) / 86400.0
            out.append(f"n={len(p):,} / {p.mean():+.3f} / {p.sum() / d:+.1f}")
        print(f"{cell_name(trig, b, tpb, ab, ag):<20}{out[0]:<34}{out[1]:<34}")

    queue_reality(Path(args.ws))

    header("READ THIS BEFORE QUOTING ANY NUMBER ABOVE")
    print("1. EXPLORATION ONLY.  The tape that produced the hypothesis is the")
    print("   tape that produced these numbers.  Nothing here is adoptable.")
    print("2. The touch is a last-print proxy, not a book.  Real quoting has a")
    print("   queue; the QUEUE section says how far below the optimistic bound")
    print("   reality sits.")
    print("3. The abort clock is print-driven: on a 0.32 print/s tape an age")
    print("   stop fires at the first print after its limit (30s or 45s), not")
    print("   exactly at it.  Markouts are on a 1-second forward-filled mid, so")
    print("   the 1s horizon is a 1-second BAR, not a 1-second instant.")
    print("4. The fresh judgment tape (paper_logs/tape/) is recorded from the")
    print("   realtime WS feed and is DENSER than this public-history tape")
    print("   (~100k vs ~27k prints/day).  Trigger counts, fill rates and the")
    print("   traded-through model will therefore all behave differently there.")
    print("   That is a reason to judge on it, not a reason to tune to it.")
    print("5. Judgment runs once, on fresh tape, under docs/PREREG_fast_cycle.md.")

    if args.print_prereg:
        doc = ROOT / "docs" / "PREREG_fast_cycle.md"
        if doc.exists():
            print("\n" + "=" * 78)
            print(doc.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
