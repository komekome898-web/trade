#!/usr/bin/env python3
"""Generation-3 sealed KNOWN-ANSWER QA packet for maker fill-model claims.

Fixes the two flaws that made generation-2 unusable as an audit test
(docs/QA/known_answer_results_2026-09-05.md §2):
  1. price now lives on an explicit tick grid (tick = 10 on a ~100,000
     instrument = 1 bp), not a continuous log-price path;
  2. the truth is no longer "whatever a separately-coded reference
     simulator decides to compute" -- it is determined BY CONSTRUCTION,
     inside a single event-driven limit-order-book simulation in which our
     own resting orders are real participants of a real per-price-level
     FIFO queue (background limit joins, cancellations at a random queue
     position, and market orders that walk the queue in FIFO order).

Architecture (see generate() for the full pipeline):

  Phase 1 -- `simulate_background()` runs ONE background LOB for the whole
  tape: two sides, each a real FIFO list of background orders (size only;
  owner is implicitly "bg"), price/size distributions calibrated against
  real bitFlyer touch sizes (see CALIBRATION_NOTES below). A market order
  consumes the opposite side's queue front-to-back; if it exhausts the
  level, price steps by one tick ("walk") and a fresh queue is seeded.
  Cancellations remove one background order at a uniformly random queue
  position. A fraction of market orders are flagged "informed": they kick
  a decaying `impulse` variable that biases the direction of SUBSEQUENT
  order flow (both market-order side and limit-improve side), which is
  what mechanically manufactures a permanent-ish post-trade price drift
  and therefore genuine adverse selection on resting orders -- nothing is
  added after the fact. This phase returns one flat, time-ordered event
  log (`events` DataFrame) plus a full touch-state timeline (bid/ask price
  and BACKGROUND-ONLY depth at every event).

  Phase 2 -- `run_strategy()` replays that SAME event log once per
  strategy (S1 = at-best symmetric quoting, S2 = one-tick-inside
  quoting when spread >= 2 ticks). Each pass is NON-INTERACTING: our own
  clip (0.05 units) is treated as a silent tap on the precomputed
  background flow rather than a real participant that could itself change
  when a level depletes or a cancellation lands. This is what guarantees
  S1 and S2 (and the naive-fill comparison pass) see a byte-identical
  background stream -- none of them ever writes back into `events`; they
  only read it. It is a deliberate, documented approximation, defensible
  because our clip is small relative to the touch (5-20x smaller), so its
  own liquidity-consumption effect on the shared book is second-order.
  Concretely: a resting order's "queue-ahead" is the background depth on
  its side/price measured at the instant it joins (fixed, per the exact
  claim wording); it fills once the CUMULATIVE background execution
  volume on that side/price since insertion exceeds queue-ahead +
  own-size (own-size = 0.05); touch moves invalidate it (re-quote, back
  of the new queue). The 300s cap forces a taker exit at the then-current
  touch. This is precisely the fill rule stated verbatim to auditors in
  claims_for_auditors_maker3.md, so there is no room for "several
  reasonable rules disagree" (the gen-2 failure mode).

  A third, `naive=True` pass answers "what would fill-on-first-print
  (queue-blind) say" by replaying the exact same PUBLIC executions file
  with the rule "filled at the first print on our side/episode after
  insertion, ignoring queue-ahead entirely."

v2 (docs/QA/known_answer_results_2026-09-05.md, "第3世代...第1版" §1-4) fixes
the v1 flaw: forced-cap taker exits were silently charged an extra, UNSTATED
TAKER_SLIPPAGE_TICKS=12 beyond the displayed touch -- never in the manifest
or claim text, not observable from the public tape, and the entire reason
S1 came out negative (three blind auditors who replayed the STATED rule got
+0.75..+1.25bps). v2 removes that lever: a forced exit crosses EXACTLY at
the displayed public touch, asserted against the WRITTEN ticker file in
run_self_checks(). v2 also (a) states three rule ambiguities the v1
auditors flagged (post-fill exit-order queue position, no position-netting/
one-open-position-per-side, ticker-rows-are-post-trade) explicitly in
FILL_RULE_TEXT/manifest instead of leaving them for auditors to guess; (b)
raises informed-flow strength so S1 entry-fill adverse selection at 5s is
real and observable (target band, not the S1 sign or forced fraction --
see SEEDS_TRIED); (c) adds independent_public_replay(), a SECOND,
separately-written replay that reconstructs S1/S2 from ONLY the two public
files + the stated rule and must match the hidden-log truth exactly
(verify_independent_replay(), called from generate()) -- this is precisely
the check three blind auditors would perform by hand, so it fails loudly
here first.

Files written to backtest_data/qa_known_answer_maker3_v2_<date>/:
  ticker_qa_maker3_v2_tape.csv.gz      ts,best_bid,best_ask,best_bid_size,best_ask_size
  executions_qa_maker3_v2_tape.csv.gz  id,ts,price,size,side
  manifest.md                          (full fill rule incl. the 3 stated
                                        ambiguities; no planted numbers)

Hidden ground truth (never shown to an auditor):
  docs/QA/hidden_maker3_v2/s1_positions.csv.gz
  docs/QA/hidden_maker3_v2/s2_positions.csv.gz
Sealed summary -> docs/QA/answers_sealed_maker3_v2.json
Claims         -> docs/QA/claims_for_auditors_maker3_v2.md (6 claims, 3 true
                  / 3 false, each stating the exact fill rule + population).

Determinism: a single seed drives every draw via independent
np.random.default_rng(seed).integers()-reseeded sub-streams (background
LOB, tape-writing/crossed-row injection); re-running with the same
--seed/--date reproduces byte-identical tape/hidden files (only
`generated_utc` in the sealed json and manifest changes).

CALIBRATION_NOTES (own_size = 0.05 units):
  Real bitFlyer FX_BTC_JPY best-bid/best-ask displayed sizes, sampled from
  backtest_data/venue_survey_20260827/bf_fxbtc_book.jsonl.gz (n=14,400
  touch-side observations; `b`/`a` arrays are [price, size] sorted by
  priority, so b[0]/a[0] are exactly the best-bid/best-ask size fields
  schema/venues.json documents for this venue's book snapshots): median
  0.0186 BTC, IQR [0.0050, 0.0453] -> IQR/median ratio ~= 2.15. We do not
  reuse the raw BTC-denominated scale (this synthetic instrument is priced
  at ~100,000, not bitFlyer's ~12.5M, so absolute size units are not
  comparable); instead we match the *shape* -- a lognormal join-size
  distribution solved so IQR/median ~= 2.15 -- and set its scale so the
  resulting median touch depth lands at ~10x own_size (within the
  requested 5-20x band). Solving IQR/median = exp(0.6745 sigma) -
  exp(-0.6745 sigma) = 2.15 gives sigma ~= 1.38 (see JOIN_SIGMA below).
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
# v2 seed choice (docs/QA/known_answer_results_2026-09-05.md item 3 of the
# fix spec): the informed-flow parameters below (RATE_MARKET, P_INFORMED,
# IMPULSE_WALK_TICKS_MEAN) were tuned FIRST against the ONE required target
# -- S1 entry-fill adverse selection at 5s in [0.5, 1.5]bps with t>=5 --
# then, with those fixed, <=5 seeds were tried and measured (full 5-day
# tape, no other post-hoc tuning). S1's net sign/magnitude and the
# forced-exit fraction were NOT targeted; they are whatever the chosen
# seed's hidden logs produce. Realized adverse_selection_bps_at_5s_mean
# (t-stat) per seed -- all five landed in-band at this parameter setting
# (an earlier, since-abandoned attempt reached the target by making each
# informed print's own price impact large instead of the market busier,
# which destabilized the shared background price process for a nontrivial
# fraction of seeds; see MAX_TICKS_ABS/MAX_SPREAD_TICKS below):
#   20260907  0.7423 (15.83)
#   20260908  0.7260 (16.34)
#   20260909  0.7200 (15.53)
#   20260910  0.7371 (16.16)  -- SELECTED (first seed tried, already in-band)
#   20260911  0.7153 (15.64)
# All five are recorded verbatim in SEEDS_TRIED and echoed into the sealed
# json's "seed_selection" field.
SEED = 20260910
SEEDS_TRIED = {
    20260907: {"adverse_selection_bps_at_5s_mean": 0.7423, "adverse_selection_t_stat": 15.83, "in_band": True},
    20260908: {"adverse_selection_bps_at_5s_mean": 0.7260, "adverse_selection_t_stat": 16.34, "in_band": True},
    20260909: {"adverse_selection_bps_at_5s_mean": 0.7200, "adverse_selection_t_stat": 15.53, "in_band": True},
    20260910: {"adverse_selection_bps_at_5s_mean": 0.7371, "adverse_selection_t_stat": 16.16, "in_band": True},
    20260911: {"adverse_selection_bps_at_5s_mean": 0.7153, "adverse_selection_t_stat": 15.64, "in_band": True},
}
SEED_SELECTION_NOTE = (
    "criterion = S1 adverse_selection_bps_at_5s_mean in [0.5,1.5] with t>=5, measured "
    "BEFORE picking a seed, with informed-flow parameters fixed first; S1's net sign/"
    "magnitude and forced_exit_fraction were not targeted at any seed and are read off "
    "whichever seed satisfied the adverse-selection criterion"
)

# --------------------------------------------------------------------- #
# instrument / tick
# --------------------------------------------------------------------- #
PRICE0 = 100_000.0
TICK = 10.0
TICK_BPS = TICK / PRICE0 * 1e4          # = 1.0 bp exactly

TAPE_DAYS = 5.0
TAPE_START = "2026-08-03T00:00:00+00:00"

OWN_SIZE = 0.05
CAP_SECONDS = 300.0
# v2 (docs/QA/known_answer_results_2026-09-05.md sec "第3世代...第1版" §1-4):
# generation-3-v1 charged forced-cap taker exits an extra, UNSTATED
# TAKER_SLIPPAGE_TICKS=12 beyond the displayed touch. That hidden constant
# (never in the manifest or claim text, not observable from the public
# tape) was the entire reason S1 looked negative; three blind auditors who
# replayed the STATED rule got +0.75..+1.25bps. There is no such lever any
# more: a forced exit crosses EXACTLY at the displayed public touch at exit
# time, full stop. See run_self_checks() for the assertion that enforces
# this against the actual written ticker file, not an internal lookup.
MARKOUT_HORIZONS = (5.0, 30.0, 300.0)
CROSSED_BOOK_FRACTION = 0.001

# --------------------------------------------------------------------- #
# background LOB process rates (per second; tuned by simulate-and-measure,
# see the report for the tuning trace -- NOT solved analytically)
# --------------------------------------------------------------------- #
# v2: RATE_MARKET raised 0.075 -> 0.15 alongside the informed-flow knobs
# below (item 3 of the fix spec) -- a busier market means more informed
# prints can land inside any given 5s post-fill window, which is what
# actually moves the average adverse-selection markout (the alternative of
# raising per-print walk SIZE further, tried first, pushed the shared
# background price process into instability -- see MAX_TICKS_ABS/
# MAX_SPREAD_TICKS below for the circuit breakers that resulted).
RATE_MARKET = 0.15
RATE_JOIN = 0.230
# Cancellation is modeled as a per-order hazard (each resting background
# order independently cancels at this rate), not a flat Poisson process --
# a constant cancel rate let join arrivals (size/sec) outrun cancel
# removals (size/sec) with no restoring force, so depth random-walked to
# unbounded values over a multi-day run (found during tuning). A per-order
# hazard makes the number of resting orders a stable birth-death process:
# equilibrium order count = order-arrival-rate / CANCEL_HAZARD_PER_ORDER.
CANCEL_HAZARD_PER_ORDER = 0.028

P_IMPROVE_BASE = 0.05    # spread == 2 ticks: prob. a join event improves instead (rare -> occasional 1)
P_IMPROVE_WIDE_BASE = 0.30  # spread == 3 ticks: prob. pulled back toward 2

# size distributions (lognormal(mu, sigma), units = own-size multiples of 0.05)
JOIN_MU, JOIN_SIGMA = math.log(0.10), 1.38      # background limit-join clip
INIT_MU, INIT_SIGMA = math.log(0.25), 0.9       # seed order for a fresh level (bigger =
                                                  # less vulnerable to an immediate re-walk)
PRINT_MU, PRINT_SIGMA = math.log(0.06), 1.05    # market-order (taker) size


def _p_improve(spread_ticks: int) -> float:
    """Prob. a limit-join event improves the price instead of joining the
    back of the current level. Pulls a wide spread back toward 2 ticks
    increasingly hard; cannot improve at spread==1."""
    if spread_ticks <= 1:
        return 0.0
    if spread_ticks == 2:
        return P_IMPROVE_BASE
    return min(0.92, P_IMPROVE_WIDE_BASE + 0.20 * (spread_ticks - 3))

# v2: informed-flow strength raised (item 3 of the fix spec) so adverse
# selection is REAL and OBSERVABLE rather than a token 0.06bps/t~6 effect
# (v1's value, measured before this change). Two knobs raised together:
# P_INFORMED (how often a print carries information) and
# IMPULSE_WALK_TICKS_MEAN (how MANY ticks its immediate mechanical impact
# walks, Poisson-distributed, replacing v1's fixed single-tick coin flip --
# a single extra tick saturates near ~0.28bps/5s even at P_INFORMED,
# P_INFORMED_WALK -> ~1, since expected market-order arrivals in a 5s
# window are only RATE_MARKET*5 =~ 0.4; letting an informed print's impact
# span several ticks removes that ceiling without changing arrival rates,
# spread dynamics, or anything else in the shared background process).
P_INFORMED = 0.6          # prob. a market order carries information
P_INFORMED_WALK = 0.97    # prob. an informed print also forces an immediate
                          # mechanical impact walk (see simulate_background)
IMPULSE_WALK_TICKS_MEAN = 6.0  # mean extra ticks (Poisson) of that impact walk
IMPULSE_KICK = 1.35       # size of the flow-direction bias kick per informed print
IMPULSE_TAU = 20.0       # seconds, exponential decay of the informed impulse
IMPULSE_BETA = 1.5       # sigmoid steepness on market-order side probability
REVERSION_KAPPA = 0.016  # mean-reversion pull (in ticks of mid offset) keeping
                          # the multi-day price path range-bound around PRICE0
                          # while still letting short-horizon informed impulses
                          # create real (but bounded) adverse-selection drift

MAX_WALK_LEVELS = 6      # safety cap on levels a single market order can cross
MAX_TICKS_ABS = 150      # circuit breaker: price stays within +-1.5% of PRICE0
                          # (bid_ticks/ask_ticks each clamped to this band) --
                          # see the comment at the clamp site in
                          # simulate_background for why v2 needs this
MAX_SPREAD_TICKS = 40    # second circuit breaker: caps the SPREAD itself
                          # (see the comment at its clamp site) -- generous
                          # vs. the normal 1-3 tick spread, only binds when
                          # bid/ask have independently run away from each
                          # other
RATE_SPREAD1_DECAY = 0.05  # extra hazard, active only while spread==1 ticks: a
                            # one-tick spread is fragile (a single improved
                            # quote) and reverts toward 2 on its own, not only
                            # via full-level depletion by a market order


def gzip_write_text(path: Path, text: str) -> None:
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(text.encode("utf-8"))


def to_iso_row(sec: np.ndarray, start: pd.Timestamp) -> pd.Series:
    # v2: full microsecond precision (v1 truncated %f to milliseconds,
    # which -- given ~1-10 background events/sec across a 5-day tape --
    # produced enough same-millisecond ties between adjacent ticker rows
    # to make an exact ticker<->execution row join ambiguous; needed for
    # independent_public_replay() below to unambiguously pair each
    # execution with its ticker row by exact ts string match).
    ts = start + pd.to_timedelta(sec, unit="s")
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


# ======================================================================= #
# Phase 1: background event-driven LOB (shared, non-interacting, stream)
# ======================================================================= #
def simulate_background(rng: np.random.Generator, span_sec: float) -> pd.DataFrame:
    """One event-driven limit-order-book simulation. Returns a flat,
    time-ordered DataFrame, one row per elementary book event, carrying the
    FULL touch state (both sides) after that event so downstream replay
    never needs to touch the underlying per-side order lists again.

    Columns: t, side ('bid'/'ask' -- which side's queue this event acted
    on), etype ('join'/'cancel'/'exec'/'improve'), size, informed (bool,
    exec rows only), exec_id (execution id, exec rows only),
    bid_price, ask_price, bid_depth, ask_depth, bid_epi, ask_epi.
    """
    next_id = [0]

    def new_id() -> int:
        next_id[0] += 1
        return next_id[0]

    bid_ticks, ask_ticks = -1, 1     # start at spread = 2 ticks
    bid_epi, ask_epi = 0, 0
    bid_orders: list[list] = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
    ask_orders: list[list] = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
    impulse = 0.0

    t = 0.0
    exec_counter = 3_300_000_000

    rows_t, rows_side, rows_etype, rows_size = [], [], [], []
    rows_informed, rows_exec_id = [], []
    rows_bid_price, rows_ask_price = [], []
    rows_bid_depth, rows_ask_depth = [], []
    rows_bid_epi, rows_ask_epi = [], []

    def depth(orders: list[list]) -> float:
        return sum(o[1] for o in orders)

    def record(side, etype, size, informed=False, exec_id=None):
        rows_t.append(t)
        rows_side.append(side)
        rows_etype.append(etype)
        rows_size.append(size)
        rows_informed.append(informed)
        rows_exec_id.append(exec_id)
        rows_bid_price.append(PRICE0 + bid_ticks * TICK)
        rows_ask_price.append(PRICE0 + ask_ticks * TICK)
        rows_bid_depth.append(depth(bid_orders))
        rows_ask_depth.append(depth(ask_orders))
        rows_bid_epi.append(bid_epi)
        rows_ask_epi.append(ask_epi)

    while t < span_sec:
        # Circuit breaker: clamp each side's tick offset to +-MAX_TICKS_ABS
        # from PRICE0. The v2 informed-flow strength increase (item 3 of
        # the fix spec) drives price with multi-tick walks whose direction
        # is reinforced by the SAME impulse that made them likely (a real,
        # if extreme, feedback loop) -- rare tail draws could otherwise let
        # price wander to a level where net_bps = pnl/entry_price blows up
        # arithmetically. A wide (+-20%) band is standard exchange-circuit-
        # breaker realism, not a hidden thumb on the scale: it only ever
        # binds in the tail, and like every other walk it emits its own
        # ticker row (etype="walk") so it is never an invisible move.
        # NOTE: every branch below bumps epi/reseeds/records a side ONLY IF
        # its tick value actually changes. An unconditional bump (this
        # generator's own first attempt) is a PHANTOM episode change: a
        # resting order's epi-based staleness check (run_strategy) would
        # invalidate/reset an order whose price never actually moved, while
        # this replay's PRICE-based staleness check would not -- silently
        # desyncing hidden truth from the independent public replay (caught
        # by verify_independent_replay(), which is the entire point of it).
        if bid_ticks < -MAX_TICKS_ABS:
            bid_ticks = -MAX_TICKS_ABS
            bid_epi += 1
            bid_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
            record("bid", "walk", 0.0)
        if ask_ticks > MAX_TICKS_ABS:
            ask_ticks = MAX_TICKS_ABS
            ask_epi += 1
            ask_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
            record("ask", "walk", 0.0)
        # Second circuit breaker, on the SPREAD itself: REVERSION_KAPPA only
        # pulls the MID back toward PRICE0 -- it applies no restoring force
        # to bid_ticks and ask_ticks independently drifting APART (a BUY-
        # informed print only ever pushes ask up, a SELL-informed print
        # only ever pushes bid down), so an unlucky/reinforced run of
        # same-side informed walks can blow the SPREAD out with the MID
        # barely moving. Symmetric pull-in (mid-preserving) once spread
        # exceeds MAX_SPREAD_TICKS -- found necessary once per-event walk
        # size stopped being a single tick (v2): net_bps = pnl/entry_price
        # was coming out in the hundreds of bps from spread blowouts alone.
        spread_now_pre = ask_ticks - bid_ticks
        if spread_now_pre > MAX_SPREAD_TICKS:
            mid_ticks_now = (bid_ticks + ask_ticks) / 2.0
            new_bid_ticks = int(round(mid_ticks_now - MAX_SPREAD_TICKS / 2.0))
            new_ask_ticks = int(round(mid_ticks_now + MAX_SPREAD_TICKS / 2.0))
            if new_bid_ticks != bid_ticks:
                bid_ticks = new_bid_ticks
                bid_epi += 1
                bid_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                record("bid", "walk", 0.0)
            if new_ask_ticks != ask_ticks:
                ask_ticks = new_ask_ticks
                ask_epi += 1
                ask_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                record("ask", "walk", 0.0)

        n_orders = len(bid_orders) + len(ask_orders)
        rate_cancel = CANCEL_HAZARD_PER_ORDER * n_orders
        spread_now = ask_ticks - bid_ticks
        rate_decay = RATE_SPREAD1_DECAY if spread_now <= 1 else 0.0
        rate_total = RATE_MARKET + RATE_JOIN + rate_cancel + rate_decay
        dt = rng.exponential(1.0 / rate_total)
        t += dt
        if t >= span_sec:
            break
        impulse *= math.exp(-dt / IMPULSE_TAU)

        r = rng.random() * rate_total
        if r < rate_decay:
            # ---- spread-1 decay: the tight quote pulls back on its own ----
            if rng.random() < 0.5:
                bid_ticks -= 1
                bid_epi += 1
                bid_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                record("bid", "cancel", 0.0)
            else:
                ask_ticks += 1
                ask_epi += 1
                ask_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                record("ask", "cancel", 0.0)
            continue
        r -= rate_decay
        if r < RATE_MARKET:
            # ---- market order (taker) ----
            mid_ticks = (bid_ticks + ask_ticks) / 2.0
            p_buy = 1.0 / (1.0 + math.exp(-(IMPULSE_BETA * impulse - REVERSION_KAPPA * mid_ticks)))
            side_buy = rng.random() < p_buy
            size = float(rng.lognormal(PRINT_MU, PRINT_SIGMA))
            informed = rng.random() < P_INFORMED
            taker_side = "bid" if side_buy else "ask"  # queue CONSUMED
            remaining = size
            levels_walked = 0
            while remaining > 1e-9 and levels_walked < MAX_WALK_LEVELS:
                orders = ask_orders if side_buy else bid_orders
                consumed = 0.0
                while remaining > 1e-9 and orders:
                    front = orders[0]
                    take = min(front[1], remaining)
                    front[1] -= take
                    remaining -= take
                    consumed += take
                    if front[1] <= 1e-9:
                        orders.pop(0)
                if consumed > 0:
                    exec_counter += 1
                    record("ask" if side_buy else "bid", "exec", consumed,
                           informed=informed, exec_id=exec_counter)
                if remaining > 1e-9:
                    # level fully depleted -> walk one tick, reseed
                    if side_buy:
                        ask_ticks += 1
                        ask_epi += 1
                        ask_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                    else:
                        bid_ticks -= 1
                        bid_epi += 1
                        bid_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                    levels_walked += 1
                else:
                    break
            if informed:
                impulse += IMPULSE_KICK * (1.0 if side_buy else -1.0)
                # An informed print carries real information beyond the
                # size it happens to trade: it also has a chance of an
                # immediate extra one-tick impact (a genuine, mechanical
                # source of the required "fair value drifts permanently in
                # the informed direction" -- organic full-level depletion
                # alone was too rare within a 5s window to produce a
                # detectable markout, found in tuning).
                if levels_walked == 0 and rng.random() < P_INFORMED_WALK:
                    # v2: the impact is now a Poisson-distributed NUMBER of
                    # ticks (mean IMPULSE_WALK_TICKS_MEAN), not a fixed
                    # single tick -- see the IMPULSE_WALK_TICKS_MEAN
                    # comment above for why this was needed to reach a
                    # realistic 5s markout magnitude. Each tick gets its OWN
                    # record() row (etype="walk", zero size, no exec_id): a
                    # multi-tick move that skipped intermediate rows would
                    # be exactly the v1 failure mode transplanted into the
                    # BACKGROUND process itself -- a price change nothing in
                    # the public ticker shows, silently relied on by the
                    # NEXT event's epi/staleness bookkeeping. Every level
                    # this walk crosses must be a real, printed ticker row
                    # (found via the independent-replay cross-check: without
                    # this, a resting order's own staleness check can miss
                    # an epi change that never got a row, since two or more
                    # DISTINCT price levels would otherwise collapse onto
                    # one observed row).
                    n_extra = 1 + int(rng.poisson(IMPULSE_WALK_TICKS_MEAN - 1.0)) \
                        if IMPULSE_WALK_TICKS_MEAN > 1.0 else 1
                    n_extra = min(n_extra, MAX_WALK_LEVELS)
                    for _ in range(n_extra):
                        if side_buy:
                            ask_ticks += 1
                            ask_epi += 1
                            ask_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                            record("ask", "walk", 0.0)
                        else:
                            bid_ticks -= 1
                            bid_epi += 1
                            bid_orders = [[new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))]]
                            record("bid", "walk", 0.0)

        elif r < RATE_MARKET + RATE_JOIN:
            # ---- background limit order arrival ----
            side_buy = rng.random() < 0.5
            spread_ticks = ask_ticks - bid_ticks
            p_improve = _p_improve(spread_ticks)
            if rng.random() < p_improve:
                size = float(rng.lognormal(INIT_MU, INIT_SIGMA))
                if side_buy:
                    bid_ticks += 1
                    bid_epi += 1
                    bid_orders = [[new_id(), size]]
                else:
                    ask_ticks -= 1
                    ask_epi += 1
                    ask_orders = [[new_id(), size]]
                record("bid" if side_buy else "ask", "improve", size)
            else:
                size = float(rng.lognormal(JOIN_MU, JOIN_SIGMA))
                if side_buy:
                    bid_orders.append([new_id(), size])
                else:
                    ask_orders.append([new_id(), size])
                record("bid" if side_buy else "ask", "join", size)

        else:
            # ---- cancellation: each resting order cancels at a constant
            # per-order hazard (CANCEL_HAZARD_PER_ORDER), so the order
            # picked is uniform across ALL currently-resting background
            # orders on both sides combined -- this is what keeps total
            # depth a stable (mean-reverting) birth-death process instead
            # of a runaway queue (a flat per-second cancel rate let join
            # arrivals outrun it with no restoring force; found in tuning).
            # NOTE: only a market-order-driven depletion walks the price
            # (genuine liquidity consumption); a cancellation that empties a
            # level just reseeds the SAME level/episode in place -- a
            # freshly-walked single-order level being one random cancel
            # away from an immediate second walk produced an unbounded,
            # monotonic spread blow-out during tuning.
            n_bid = len(bid_orders)
            idx = int(rng.integers(0, n_orders)) if n_orders else 0
            if n_orders:
                if idx < n_bid:
                    side_buy, orders, oidx = True, bid_orders, idx
                else:
                    side_buy, orders, oidx = False, ask_orders, idx - n_bid
                removed = orders.pop(oidx)
                if not orders:
                    orders.append([new_id(), float(rng.lognormal(INIT_MU, INIT_SIGMA))])
                record("bid" if side_buy else "ask", "cancel", removed[1])

    df = pd.DataFrame({
        "t": rows_t, "side": rows_side, "etype": rows_etype, "size": rows_size,
        "informed": rows_informed, "exec_id": rows_exec_id,
        "bid_price": rows_bid_price, "ask_price": rows_ask_price,
        "bid_depth": rows_bid_depth, "ask_depth": rows_ask_depth,
        "bid_epi": rows_bid_epi, "ask_epi": rows_ask_epi,
    })
    return df


# ======================================================================= #
# Phase 2: strategy replay (non-interacting tap on the shared event log)
# ======================================================================= #
class MidLookup:
    """Piecewise-constant (bid+ask)/2 lookup against the background event
    log, used for markouts and forced-exit pricing."""

    def __init__(self, events: pd.DataFrame):
        self.t = events["t"].to_numpy()
        self.bid = events["bid_price"].to_numpy()
        self.ask = events["ask_price"].to_numpy()

    def at(self, t: float) -> tuple[float, float]:
        i = np.searchsorted(self.t, t, side="right") - 1
        if i < 0:
            return (PRICE0 - TICK, PRICE0 + TICK)
        return float(self.bid[i]), float(self.ask[i])

    def mid_at(self, t: float) -> float:
        b, a = self.at(t)
        return (b + a) / 2.0


class Order:
    __slots__ = ("side", "epi", "ahead", "cum_exec", "inside", "ref_bid", "ref_ask", "price")

    def __init__(self, side, epi, ahead, inside, ref_bid, ref_ask, price):
        self.side = side
        self.epi = epi
        self.ahead = ahead
        self.cum_exec = 0.0
        self.inside = inside
        self.ref_bid = ref_bid
        self.ref_ask = ref_ask
        self.price = price


def _make_order(side: str, row, inside_mode: bool) -> Order:
    """Instantiate/re-instantiate a resting order at the CURRENT touch
    described by `row` (a namedtuple from events.itertuples())."""
    spread_ticks = round((row.ask_price - row.bid_price) / TICK)
    if inside_mode and spread_ticks >= 2:
        if side == "bid":
            price = row.bid_price + TICK
        else:
            price = row.ask_price - TICK
        return Order(side, None, 0.0, True, row.bid_price, row.ask_price, price)
    price = row.bid_price if side == "bid" else row.ask_price
    epi = row.bid_epi if side == "bid" else row.ask_epi
    ahead = row.bid_depth if side == "bid" else row.ask_depth
    return Order(side, epi, ahead, False, row.bid_price, row.ask_price, price)


def _order_stale(order: Order, row) -> bool:
    """True if the touch has moved away from where `order` is resting ->
    must cancel and re-join at the new best (back of the new queue)."""
    if order.inside:
        return row.bid_price != order.ref_bid or row.ask_price != order.ref_ask
    cur_epi = row.bid_epi if order.side == "bid" else row.ask_epi
    return cur_epi != order.epi


def run_strategy(events: pd.DataFrame, mid: MidLookup, inside_mode: bool,
                  naive: bool = False) -> list[dict]:
    """Replay `events` once (non-interacting: never mutates it) simulating
    a continuous sequence of symmetric two-sided-quote round trips.
    naive=True switches the MAKER fill rule to "filled at the first print
    on our side/episode after insertion" (queue-blind comparison model);
    the 300s cap / forced-taker-exit machinery is identical either way."""
    positions: list[dict] = []
    state = "seek_entry"
    pending: dict[str, Order] = {}
    exit_order: Order | None = None
    entry_time = entry_price = None
    direction = None
    entry_exec_id = None
    cap_time = None

    rows = list(events.itertuples(index=False))
    if not rows:
        return positions
    pending["bid"] = _make_order("bid", rows[0], inside_mode)
    pending["ask"] = _make_order("ask", rows[0], inside_mode)

    i = 0
    n = len(rows)
    while i < n:
        row = rows[i]
        if state == "seek_entry":
            for side in ("bid", "ask"):
                o = pending[side]
                if _order_stale(o, row):
                    pending[side] = _make_order(side, row, inside_mode)
                    o = pending[side]
                if row.etype == "exec" and row.side == side:
                    if o.inside or row.bid_epi == o.epi or row.ask_epi == o.epi:
                        # inside orders: any exec on our side counts (we are
                        # first in queue by construction); at-best orders:
                        # only exec events within the SAME episode we joined
                        matches_epi = o.inside or (
                            (side == "bid" and row.bid_epi == o.epi) or
                            (side == "ask" and row.ask_epi == o.epi)
                        )
                        if matches_epi:
                            o.cum_exec += row.size
                            threshold = OWN_SIZE if naive else (o.ahead + OWN_SIZE)
                            filled = (o.cum_exec > 1e-9) if naive else (o.cum_exec >= threshold)
                            if filled:
                                entry_time = row.t
                                entry_row_idx = i
                                entry_price = o.price
                                entry_exec_id = row.exec_id
                                direction = "long" if side == "bid" else "short"
                                exit_side = "ask" if side == "bid" else "bid"
                                # Ambiguity (a) (see FILL_RULE_TEXT / manifest):
                                # after our own fill, the OPPOSITE-side exit
                                # quote is a FRESH order inserted at the back
                                # of the displayed queue AT THAT MOMENT --
                                # queue-ahead = displayed (background) size on
                                # that side at insertion -- not whatever stale
                                # queue position `pending[exit_side]` happened
                                # to be resting at since it was last (re)made.
                                exit_order = _make_order(exit_side, row, inside_mode)
                                pending[exit_side] = exit_order
                                cap_time = entry_time + CAP_SECONDS
                                state = "seek_exit"
                                break
            i += 1
            continue

        # state == "seek_exit"
        if row.t > cap_time:
            fb, fa = mid.at(cap_time)
            # v2: forced taker exit crosses EXACTLY at the displayed public
            # touch at exit time -- a long position exits by SELLING at the
            # (lower) bid, a short position exits by BUYING at the (higher)
            # ask. NO additional slippage is modelled (see the note by
            # MARKOUT_HORIZONS for why v1's hidden TAKER_SLIPPAGE_TICKS was
            # removed). mid.at() reads the exact same events timeline the
            # public ticker file is built from, so this IS the touch that
            # ends up written to ticker_qa_maker3_v2_tape.csv.gz at/just
            # before this timestamp -- asserted equal in run_self_checks().
            exit_price = fb if direction == "long" else fa
            pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            # exit_row_idx = i-1 (NOT i): row i is the first row with
            # t > cap_time -- it belongs to the NEXT (post-close) footprint,
            # since the cap deadline, unlike every other transition here, is
            # a clock event that is NOT "caused by" processing row i (row i
            # gets REPROCESSED under seek_entry below via `continue`,
            # without ever being treated as part of the closing position's
            # own-size footprint). See _reconstruct_own_add / the own-size
            # interval construction in build_public_tape for why exact row
            # boundaries (not timestamps) matter here: two or more events
            # can share the identical timestamp (a market order walking
            # multiple price levels in one step advances the level without
            # advancing simulated time), which a timestamp-based interval
            # cannot resolve but a row index always can.
            positions.append({
                "direction": direction, "entry_time": entry_time, "entry_row_idx": entry_row_idx,
                "entry_price": entry_price, "entry_exec_id": entry_exec_id,
                "exit_time": cap_time, "exit_row_idx": max(i - 1, 0), "exit_price": exit_price,
                "exit_exec_id": None, "forced": True, "net_bps": pnl / entry_price * 1e4,
            })
            state = "seek_entry"
            pending["bid"] = _make_order("bid", row, inside_mode)
            pending["ask"] = _make_order("ask", row, inside_mode)
            continue  # reprocess this row under seek_entry

        exit_side = exit_order.side
        if _order_stale(exit_order, row):
            exit_order = _make_order(exit_side, row, inside_mode)
        if row.etype == "exec" and row.side == exit_side:
            matches_epi = exit_order.inside or (
                (exit_side == "bid" and row.bid_epi == exit_order.epi) or
                (exit_side == "ask" and row.ask_epi == exit_order.epi)
            )
            if matches_epi:
                exit_order.cum_exec += row.size
                threshold = OWN_SIZE if naive else (exit_order.ahead + OWN_SIZE)
                filled = (exit_order.cum_exec > 1e-9) if naive else (exit_order.cum_exec >= threshold)
                if filled:
                    exit_price = exit_order.price
                    pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                    positions.append({
                        "direction": direction, "entry_time": entry_time, "entry_row_idx": entry_row_idx,
                        "entry_price": entry_price, "entry_exec_id": entry_exec_id,
                        "exit_time": row.t, "exit_row_idx": i, "exit_price": exit_price,
                        "exit_exec_id": row.exec_id, "forced": False, "net_bps": pnl / entry_price * 1e4,
                    })
                    state = "seek_entry"
                    pending["bid"] = _make_order("bid", row, inside_mode)
                    pending["ask"] = _make_order("ask", row, inside_mode)
        i += 1
    return positions


def markouts(positions: list[dict], mid: MidLookup) -> None:
    """Adds adverse-selection markouts (bps, positive = bad for the maker)
    on the ENTRY fill at each horizon in MARKOUT_HORIZONS, in place."""
    for p in positions:
        m0 = mid.mid_at(p["entry_time"])
        for h in MARKOUT_HORIZONS:
            m1 = mid.mid_at(p["entry_time"] + h)
            drift = (m1 - m0) / m0 * 1e4
            adverse = -drift if p["direction"] == "long" else drift
            p[f"markout_{int(h)}s_bps"] = adverse


def _mean_t(values) -> tuple[float, float, int]:
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    n = arr.size
    if n < 2:
        return (float(arr.mean()) if n else float("nan")), float("nan"), n
    mean = float(arr.mean())
    se = float(arr.std(ddof=1) / math.sqrt(n))
    t = mean / se if se else float("nan")
    return mean, t, n


def summarize(positions: list[dict], label: str, markout_key: str = "markout_5s_bps") -> dict:
    net_mean, net_t, n = _mean_t([p["net_bps"] for p in positions])
    mo_mean, mo_t, mo_n = _mean_t([p.get(markout_key) for p in positions])
    forced = sum(1 for p in positions if p["forced"])
    kept = [p for p in positions if not p["forced"]]
    dropped_mean, _, dropped_n = _mean_t([p["net_bps"] for p in kept])
    return {
        "label": label, "n_positions": n,
        "net_bps_mean": round(net_mean, 4), "net_bps_t_stat": round(net_t, 3),
        "adverse_selection_bps_at_5s_mean": round(mo_mean, 4),
        "adverse_selection_t_stat": round(mo_t, 3), "adverse_selection_n": mo_n,
        "forced_exit_count": forced,
        "forced_exit_fraction": round(forced / n, 4) if n else None,
        "survivorship_biased_net_bps_if_forced_dropped": round(dropped_mean, 4),
        "n_positions_if_dropped": dropped_n,
    }


# ======================================================================= #
# tape writing
# ======================================================================= #
def build_public_tape(events: pd.DataFrame, s1_positions: list[dict], s2_positions: list[dict],
                       rng: np.random.Generator, out_dir: Path) -> dict:
    start = pd.Timestamp(TAPE_START)

    # executions: one row per exec event in the background log, PLUS one
    # extra row per S1/S2 forced-taker exit (a genuine new print we caused;
    # maker fills are already background prints and need no extra row).
    exec_rows = events[events["etype"] == "exec"].copy()
    # side='bid' event = a SELL hit (consumed) the bid queue -> trade price = bid_price
    # side='ask' event = a BUY hit (consumed) the ask queue -> trade price = ask_price
    exec_rows["price"] = np.where(exec_rows["side"] == "ask", exec_rows["ask_price"], exec_rows["bid_price"])
    exec_rows["taker_side"] = np.where(exec_rows["side"] == "bid", "SELL", "BUY")
    ex = pd.DataFrame({
        "id": exec_rows["exec_id"].astype(np.int64),
        "t": exec_rows["t"], "price": exec_rows["price"], "size": exec_rows["size"],
        "side": exec_rows["taker_side"],
    })

    forced_rows = []
    next_forced_id = int(ex["id"].max()) + 1 if len(ex) else 3_400_000_000
    for p in s1_positions + s2_positions:
        if p["forced"]:
            forced_rows.append({
                "id": next_forced_id, "t": p["exit_time"], "price": p["exit_price"],
                "size": OWN_SIZE, "side": "BUY" if p["direction"] == "short" else "SELL",
            })
            p["exit_exec_id"] = next_forced_id
            next_forced_id += 1
    if forced_rows:
        ex = pd.concat([ex, pd.DataFrame(forced_rows)], ignore_index=True)
    ex = ex.sort_values(["t", "id"]).reset_index(drop=True)
    ex_out = pd.DataFrame({
        "id": ex["id"], "ts": to_iso_row(ex["t"].to_numpy(), start),
        "price": ex["price"], "size": ex["size"], "side": ex["side"],
    })
    efile = "executions_qa_maker3_v2_tape.csv.gz"
    gzip_write_text(out_dir / efile, ex_out.to_csv(index=False))

    # ticker: one row per background event, sizes include S1's own resting
    # order while it is on the book. Model: EACH SIDE is active (own_size
    # added) by DEFAULT on every row, except during an explicit IDLE GAP --
    # a side goes idle exactly on [entry_row_idx, exit_row_idx) of any
    # position it was the ENTRY side for (its resting order was consumed by
    # that entry fill, and only the OPPOSITE side gets a fresh order "at
    # that moment" per ambiguity (a); the entry side stays idle until the
    # position closes, becoming active again -- a fresh order, same rule --
    # starting AT exit_row_idx inclusive, since ticker rows are written
    # POST-TRADE (c), so the row of the closing trade already reflects the
    # re-quote). The EXIT side of a position needs no special-casing: it is
    # continuously active before, during, and after the position (same
    # resting clip, just re-priced/re-queued on staleness), so it is never
    # part of an idle gap. Boundaries are ROW INDICES (entry_row_idx/
    # exit_row_idx, recorded by run_strategy), NOT timestamps: a single
    # market order can walk MULTIPLE price levels without simulated time
    # advancing (see simulate_background's per-order while-loop), so two or
    # more DISTINCT rows can share the exact same timestamp with a real
    # state transition (an entry/exit fill) happening strictly between them
    # -- only a row index can resolve which of the tied rows is "before" vs
    # "after" the transition (found via the independent-replay cross-check
    # below disagreeing with the sealed truth on exactly the positions
    # following a multi-level-walk tie / an entry-fill-then-idle-side gap).
    n = len(events)
    own_bid_add = np.full(n, OWN_SIZE)
    own_ask_add = np.full(n, OWN_SIZE)
    for p in s1_positions:
        entry_side = "bid" if p["direction"] == "long" else "ask"
        lo, hi = p["entry_row_idx"], p["exit_row_idx"]
        if hi > lo:
            (own_bid_add if entry_side == "bid" else own_ask_add)[lo:hi] = 0.0

    bid_size = events["bid_depth"].to_numpy() + own_bid_add
    ask_size = events["ask_depth"].to_numpy() + own_ask_add
    t_arr = events["t"].to_numpy()
    ticks = pd.DataFrame({
        "t": t_arr, "best_bid": events["bid_price"].to_numpy(), "best_ask": events["ask_price"].to_numpy(),
        "best_bid_size": bid_size, "best_ask_size": ask_size,
    })

    crossed = rng.random(len(ticks)) < CROSSED_BOOK_FRACTION
    crossed_idx = np.where(crossed)[0].tolist()
    bb = ticks["best_bid"].to_numpy().copy()
    ba = ticks["best_ask"].to_numpy().copy()
    if len(crossed_idx):
        bb2, ba2 = bb.copy(), ba.copy()
        bb2[crossed_idx] = ba[crossed_idx]
        ba2[crossed_idx] = bb[crossed_idx]
        bb, ba = bb2, ba2

    tick_out = pd.DataFrame({
        "ts": to_iso_row(ticks["t"].to_numpy(), start),
        "best_bid": bb, "best_ask": ba,
        "best_bid_size": ticks["best_bid_size"], "best_ask_size": ticks["best_ask_size"],
    })
    qfile = "ticker_qa_maker3_v2_tape.csv.gz"
    gzip_write_text(out_dir / qfile, tick_out.to_csv(index=False))

    return {
        "quote_file": qfile, "execution_file": efile,
        "n_quote_rows": int(len(tick_out)), "n_execution_rows": int(len(ex_out)),
        "tick": TICK, "tick_bps": TICK_BPS,
        "crossed_book_fraction_target": CROSSED_BOOK_FRACTION,
        "crossed_book_rows_idx": crossed_idx,
        "crossed_book_fraction_realized": round(len(crossed_idx) / len(ticks), 6) if len(ticks) else None,
        "date_range_utc": [str(start), str(start + pd.to_timedelta(t_arr[-1] if n else 0, unit="s"))],
    }


# ======================================================================= #
# self-checks (assert BY CONSTRUCTION -- run every generate() call)
# ======================================================================= #
def run_self_checks(events: pd.DataFrame, tape_info: dict, out_dir: Path,
                     s1_positions: list[dict], s2_positions: list[dict]) -> None:
    tol = 1e-6
    bp = events["bid_price"].to_numpy()
    ap = events["ask_price"].to_numpy()
    assert np.all(np.abs(((bp - PRICE0) / TICK) - np.round((bp - PRICE0) / TICK)) < tol), \
        "best_bid off the tick grid"
    assert np.all(np.abs(((ap - PRICE0) / TICK) - np.round((ap - PRICE0) / TICK)) < tol), \
        "best_ask off the tick grid"

    with gzip.open(out_dir / tape_info["quote_file"], "rt") as f:
        tdf = pd.read_csv(f)
    med_touch = pd.concat([tdf["best_bid_size"], tdf["best_ask_size"]]).median()
    assert med_touch >= 5 * OWN_SIZE, f"median touch size {med_touch} < 5x own size"

    with gzip.open(out_dir / tape_info["execution_file"], "rt") as f:
        edf = pd.read_csv(f)
    exec_ids = set(edf["id"].astype(np.int64))
    exec_by_id = edf.set_index("id")

    assert med_touch >= 5 * OWN_SIZE and med_touch <= 20 * OWN_SIZE, \
        f"median touch size {med_touch} outside the 5-20x own-size band"

    # ---- item 1: forced exits cross EXACTLY at the displayed public touch
    # -- read straight back off the WRITTEN ticker file (tdf, already
    # loaded above), same as any auditor would, not the in-memory events
    # array. Crossed-book trap rows (best_bid > best_ask there -- a
    # physically impossible quote, injected on purpose, see
    # CROSSED_BOOK_FRACTION) carry EXACTLY-SWAPPED prices, so they are
    # un-swapped here rather than skipped -- see the identical, more-
    # detailed comment on this in _independent_replay_one (an earlier
    # skip-the-row approach could land on the wrong PRECEDING row instead
    # of recovering the true touch at the exact row).
    t_arr = events["t"].to_numpy()
    raw_bid = tdf["best_bid"].to_numpy()
    raw_ask = tdf["best_ask"].to_numpy()
    valid = raw_bid <= raw_ask
    tick_bid = np.where(valid, raw_bid, raw_ask)
    tick_ask = np.where(valid, raw_ask, raw_bid)
    for p in s1_positions + s2_positions:
        if not p["forced"]:
            continue
        j = int(np.searchsorted(t_arr, p["exit_time"], side="right")) - 1
        j = max(j, 0)
        touch = tick_bid[j] if p["direction"] == "long" else tick_ask[j]
        assert abs(float(touch) - p["exit_price"]) < 1e-6, (
            f"forced exit price {p['exit_price']} != public touch {touch} "
            f"at exit_time={p['exit_time']} (row {j})"
        )

    # ---- item 4a: mean-decomposition identity (overall mean == weighted
    # combination of the forced-only and non-forced-only subset means),
    # checked directly off the raw position lists, not the rounded summary
    # dict. ----
    for label, positions in (("S1", s1_positions), ("S2", s2_positions)):
        if not positions:
            continue
        all_net = np.asarray([q["net_bps"] for q in positions], dtype=float)
        forced_mask = np.asarray([q["forced"] for q in positions], dtype=bool)
        n = len(positions)
        n_forced = int(forced_mask.sum())
        frac = n_forced / n
        forced_mean = float(all_net[forced_mask].mean()) if n_forced else 0.0
        nonforced_mean = float(all_net[~forced_mask].mean()) if n_forced < n else 0.0
        recombined = frac * forced_mean + (1 - frac) * nonforced_mean
        assert abs(recombined - float(all_net.mean())) < 1e-9, \
            f"{label}: mean decomposition identity failed"

    # ---- item 4b: every own fill (entry AND exit, both forced and
    # non-forced, S1 and S2) maps to a public print at the same ts/price/
    # side-consistency. Forced exits are checked against the touch above
    # (their price is DEFINED as the touch, no exec-row lookup needed for
    # price -- but their (ts, size, side) must still appear as a genuine
    # print, checked here by exec_id). Non-forced maker fills at-best (S1
    # always; S2 whenever spread==1 forces it back to an at-best quote)
    # must match the print's PRICE exactly; S2's genuinely one-tick-inside
    # fills are a real, disclosed, non-interacting-clip approximation (see
    # manifest) where our own resting price is better than the background
    # print it silently taps, so price identity is not required there --
    # only ts/side-consistency (the print exists, on the correct side, at
    # the fill instant) is. ----
    for is_s1, p in [(True, p) for p in s1_positions] + [(False, p) for p in s2_positions]:
        for key_p, key_id in (("entry_price", "entry_exec_id"), ("exit_price", "exit_exec_id")):
            assert p.get(key_id) is not None, f"own fill missing {key_id}"
            assert int(p[key_id]) in exec_ids, f"own fill {key_id}={p[key_id]} missing from public tape"
            row = exec_by_id.loc[int(p[key_id])]
            long_ = p["direction"] == "long"
            if key_p == "exit_price" and p["forced"]:
                # forced exit: WE are the taker (crossing the spread
                # ourselves), so the print's side is OUR OWN action --
                # SELL to close a long, BUY to close a short.
                want_taker_side = "SELL" if long_ else "BUY"
            elif key_p == "entry_price":
                # entry: a background taker consumes OUR resting order --
                # our bid (long) is consumed by a SELL, our ask (short) by
                # a BUY.
                want_taker_side = "SELL" if long_ else "BUY"
            else:
                # non-forced exit: a background taker consumes our resting
                # CLOSING order on the OPPOSITE side from entry -- our ask
                # (closing a long) is consumed by a BUY, our bid (closing a
                # short) by a SELL.
                want_taker_side = "BUY" if long_ else "SELL"
            assert row["side"] == want_taker_side, f"own fill {key_id} side inconsistent with public print"
            # S1 never improves (always at-best) so its price must exactly
            # equal the print's price at every fill, forced or not. S2's
            # forced exits also cross at the touch (price-equal too); only
            # S2's genuinely one-tick-inside NON-forced fills are exempt
            # (documented non-interacting-clip approximation, see manifest).
            if is_s1 or (key_p == "exit_price" and p["forced"]):
                assert abs(float(row["price"]) - p[key_p]) < 1e-6, f"own fill {key_id} price mismatch vs public tape"


# ======================================================================= #
# independent public-only replay (item 4: a SECOND, separately-written
# re-derivation that reads ONLY the two public files + the stated rule --
# no access to `events`, epi ids, or anything else internal. If this
# disagrees with the hidden-log-derived S1/S2 net/n/forced-fraction, the
# packet is broken exactly the way generation-3-v1 was (docs/QA/
# known_answer_results_2026-09-05.md) and generate() must fail loudly
# rather than seal a mismatched answer -- this is precisely the check
# three blind auditors would perform by hand.
# ======================================================================= #
class _PubOrder:
    __slots__ = ("side", "price", "ahead", "cum_exec", "inside", "ref_bid", "ref_ask")

    def __init__(self, side, price, ahead, inside, ref_bid, ref_ask):
        self.side = side
        self.price = price
        self.ahead = ahead
        self.cum_exec = 0.0
        self.inside = inside
        self.ref_bid = ref_bid
        self.ref_ask = ref_ask


def _reconstruct_own_add(positions: list[dict], n: int) -> tuple[np.ndarray, np.ndarray]:
    """Mirrors build_public_tape()'s own-size idle-gap logic EXACTLY (see
    the detailed comment there): each side is active by default, idle only
    on [entry_row_idx, exit_row_idx) of a position it was the ENTRY side
    for. Driven off a POSITIONS LIST carrying entry_row_idx/exit_row_idx
    (recorded during the replay that produced it, hidden or public -- see
    _independent_replay_one)."""
    bid_add = np.full(n, OWN_SIZE)
    ask_add = np.full(n, OWN_SIZE)
    for p in positions:
        entry_side = "bid" if p["direction"] == "long" else "ask"
        lo, hi = p["entry_row_idx"], p["exit_row_idx"]
        if hi > lo:
            (bid_add if entry_side == "bid" else ask_add)[lo:hi] = 0.0
    return bid_add, ask_add


def _independent_replay_one(ticker_df: pd.DataFrame, exec_df: pd.DataFrame, inside_mode: bool,
                             bg_bid: np.ndarray | None, bg_ask: np.ndarray | None) -> tuple[list[dict], np.ndarray]:
    """Replays ONE strategy (S1 if inside_mode=False, else S2) using only
    the public ticker/execution DataFrames + the rule stated verbatim in
    FILL_RULE_TEXT. `bg_bid`/`bg_ask` (background-only displayed size,
    already purified of any earlier pass's own-size contribution) are used
    for queue-ahead whenever an at-best price applies; pass None on the
    FIRST call (S1: the ticker's own-size annotations ARE S1's, so
    ticker-size - own_size recovers it directly). Returns (positions,
    own_add_bid) so a second call (S2) can be told what background depth
    really was, purified of S1's own footprint."""
    bp_raw = ticker_df["best_bid"].to_numpy(dtype=float)
    ap_raw = ticker_df["best_ask"].to_numpy(dtype=float)
    bs = ticker_df["best_bid_size"].to_numpy(dtype=float)
    asz = ticker_df["best_ask_size"].to_numpy(dtype=float)
    t_dt = pd.to_datetime(ticker_df["ts"]).to_numpy()
    n = len(ticker_df)

    # Crossed-book trap rows (best_bid > best_ask -- physically impossible,
    # a deliberate injected corruption, see CROSSED_BOOK_FRACTION) carry
    # EXACTLY-SWAPPED bid/ask prices and otherwise-untouched sizes -- the
    # injection is a pure relabel, not noise, so it is exactly reversible:
    # a competent auditor who notices "bid > ask" concludes the two got
    # swapped and swaps them back, rather than discarding the row (an
    # earlier forward-fill attempt here masked a genuine price move that
    # happened to land exactly on a crossed row, delaying a re-quote/
    # queue-ahead read by one row and desyncing this replay from the
    # sealed truth -- found via the independent-replay cross-check).
    valid = bp_raw <= ap_raw
    bp = np.where(valid, bp_raw, ap_raw)
    ap = np.where(valid, ap_raw, bp_raw)

    if bg_bid is None:
        bg_bid = bs - OWN_SIZE
        bg_ask = asz - OWN_SIZE

    # A single background market order can walk MULTIPLE price levels in one
    # step (t does not advance between levels -- see the while-loop in
    # simulate_background), producing several DISTINCT exec/ticker rows that
    # share the EXACT SAME timestamp. So this must be ts -> an ORDERED queue
    # of exec rows, popped from the front once per matching ticker row, not
    # a plain ts -> one-row dict (which silently dropped the 2nd+ exec at a
    # tied ts -- found via the independent-replay cross-check itself, this
    # generator's whole point).
    exec_at_ts: dict[str, deque] = defaultdict(deque)
    for row in exec_df.itertuples(index=False):
        exec_at_ts[row.ts].append(row)

    def make_order(side: str, i: int) -> _PubOrder:
        spread_ticks = round((ap[i] - bp[i]) / TICK)
        if inside_mode and spread_ticks >= 2:
            price = bp[i] + TICK if side == "bid" else ap[i] - TICK
            return _PubOrder(side, price, 0.0, True, bp[i], ap[i])
        price = bp[i] if side == "bid" else ap[i]
        ahead = bg_bid[i] if side == "bid" else bg_ask[i]
        return _PubOrder(side, price, ahead, False, bp[i], ap[i])

    def stale(o: _PubOrder, i: int) -> bool:
        if o.inside:
            return bp[i] != o.ref_bid or ap[i] != o.ref_ask
        cur = bp[i] if o.side == "bid" else ap[i]
        return cur != o.price

    def asof_touch(cap_time) -> tuple[float, float]:
        j = int(np.searchsorted(t_dt, cap_time, side="right")) - 1
        j = max(j, 0)
        return float(bp[j]), float(ap[j])

    positions: list[dict] = []
    if n == 0:
        return positions, np.zeros(0)
    state = "seek_entry"
    pending = {"bid": make_order("bid", 0), "ask": make_order("ask", 0)}
    exit_order = None
    entry_time = entry_price = None
    direction = None
    cap_time = None

    entry_row_idx = None
    i = 0
    while i < n:
        if state == "seek_exit" and t_dt[i] > cap_time:
            fb, fa = asof_touch(cap_time)
            exit_price = fb if direction == "long" else fa
            pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            # exit_row_idx = i-1: row i is the first row past the cap
            # deadline and gets reprocessed under seek_entry below -- see
            # the identical comment on the hidden-side forced-exit branch
            # in run_strategy for why this must be a row index, not i.
            positions.append({
                "direction": direction, "entry_time": entry_time, "entry_row_idx": entry_row_idx,
                "entry_price": entry_price, "exit_time": cap_time, "exit_row_idx": max(i - 1, 0),
                "exit_price": exit_price, "forced": True, "net_bps": pnl / entry_price * 1e4,
            })
            state = "seek_entry"
            pending = {"bid": make_order("bid", i), "ask": make_order("ask", i)}
            continue

        dq = exec_at_ts.get(ticker_df["ts"].iat[i])
        e = dq.popleft() if dq else None
        hit_side = None
        if e is not None:
            hit_side = "bid" if e.side == "SELL" else "ask"

        if state == "seek_entry":
            filled_side = None
            for side in ("bid", "ask"):
                o = pending[side]
                if stale(o, i):
                    pending[side] = make_order(side, i)
                    o = pending[side]
                if hit_side == side:
                    o.cum_exec += float(e.size)
                    if o.cum_exec >= o.ahead + OWN_SIZE - 1e-9:
                        filled_side = side
                        break
            if filled_side:
                side = filled_side
                o = pending[side]
                entry_time = t_dt[i]
                entry_row_idx = i
                entry_price = o.price
                direction = "long" if side == "bid" else "short"
                exit_side = "ask" if side == "bid" else "bid"
                exit_order = make_order(exit_side, i)
                pending[exit_side] = exit_order
                cap_time = entry_time + np.timedelta64(int(CAP_SECONDS * 1e9), "ns")
                state = "seek_exit"
            i += 1
            continue

        # state == "seek_exit", not forced this row
        exit_side = exit_order.side
        if stale(exit_order, i):
            exit_order = make_order(exit_side, i)
            pending[exit_side] = exit_order
        if hit_side == exit_side:
            exit_order.cum_exec += float(e.size)
            if exit_order.cum_exec >= exit_order.ahead + OWN_SIZE - 1e-9:
                exit_price = exit_order.price
                pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                positions.append({
                    "direction": direction, "entry_time": entry_time, "entry_row_idx": entry_row_idx,
                    "entry_price": entry_price, "exit_time": t_dt[i], "exit_row_idx": i,
                    "exit_price": exit_price, "forced": False, "net_bps": pnl / entry_price * 1e4,
                })
                state = "seek_entry"
                pending = {"bid": make_order("bid", i), "ask": make_order("ask", i)}
        i += 1

    own_bid_add, _own_ask_add = _reconstruct_own_add(positions, n)
    return positions, own_bid_add


def independent_public_replay(ticker_df: pd.DataFrame, exec_df: pd.DataFrame) -> dict:
    """Public-only re-derivation of S1 and S2. Returns a dict with the same
    net_bps_mean/net_bps_t_stat/n_positions/forced_exit_fraction shape as
    summarize() for both, via the SAME summarize() function (it only looks
    at 'net_bps'/'forced', both present here)."""
    s1_pub, _ = _independent_replay_one(ticker_df, exec_df, inside_mode=False, bg_bid=None, bg_ask=None)
    # S2 needs BACKGROUND-ONLY depth (purified of S1's own footprint, which
    # is what the ticker's size columns actually carry -- see the
    # _independent_replay_one docstring) for its rare at-best fallback
    # (spread==1, where an inside improve is impossible).
    s1_bid_add, s1_ask_add = _reconstruct_own_add(s1_pub, len(ticker_df))
    bg_bid = ticker_df["best_bid_size"].to_numpy(dtype=float) - s1_bid_add
    bg_ask = ticker_df["best_ask_size"].to_numpy(dtype=float) - s1_ask_add
    s2_pub, _ = _independent_replay_one(ticker_df, exec_df, inside_mode=True, bg_bid=bg_bid, bg_ask=bg_ask)
    return {
        "S1_symmetric_at_best": summarize(s1_pub, "S1_independent_replay"),
        "S2_inside_one_tick": summarize(s2_pub, "S2_independent_replay"),
    }


def verify_independent_replay(out_dir: Path, tape_info: dict, s1_summary: dict, s2_summary: dict) -> dict:
    with gzip.open(out_dir / tape_info["quote_file"], "rt") as f:
        ticker_df = pd.read_csv(f)
    with gzip.open(out_dir / tape_info["execution_file"], "rt") as f:
        exec_df = pd.read_csv(f)
    pub = independent_public_replay(ticker_df, exec_df)
    for label, hidden in (("S1_symmetric_at_best", s1_summary), ("S2_inside_one_tick", s2_summary)):
        got = pub[label]
        for field in ("n_positions", "forced_exit_fraction"):
            assert got[field] == hidden[field], (
                f"INDEPENDENT PUBLIC-ONLY REPLAY DISAGREES WITH SEALED TRUTH ({label}.{field}): "
                f"public-only replay={got[field]!r} hidden-log truth={hidden[field]!r} -- "
                f"this is the generation-3-v1 failure mode (a rule ambiguity three blind "
                f"auditors would ALSO hit); do not seal this packet."
            )
        assert abs(got["net_bps_mean"] - hidden["net_bps_mean"]) < 1e-6, (
            f"INDEPENDENT PUBLIC-ONLY REPLAY DISAGREES WITH SEALED TRUTH ({label}.net_bps_mean): "
            f"public-only replay={got['net_bps_mean']!r} hidden-log truth={hidden['net_bps_mean']!r}"
        )
    return pub


# ======================================================================= #
# naive comparison
# ======================================================================= #
def naive_net(events: pd.DataFrame, mid: MidLookup) -> dict:
    positions = run_strategy(events, mid, inside_mode=False, naive=True)
    return summarize(positions, "naive_fill_on_print_at_best")


# ======================================================================= #
# manifest + claims
# ======================================================================= #
MANIFEST_TEMPLATE = """# QA known-answer packet (generation 3, v2) -- maker fill model -- manifest

Synthetic data generated by `scripts/qa/make_known_answer_maker3.py` (fixed
seed). Nothing here is real market data.

Do not open `docs/QA/answers_sealed_maker3_v2.json` before completing an
audit of this packet.

## Synthetic tape ({tape_days:.0f} days)

| file | columns | rows |
|---|---|---|
| `{quote_file}` | ts,best_bid,best_ask,best_bid_size,best_ask_size | {n_quote_rows} |
| `{execution_file}` | id,ts,price,size,side | {n_execution_rows} |

`side` in the execution file is the TAKER's side (BUY/SELL). `best_bid_size`
/`best_ask_size` are the DISPLAYED sizes at the touch at quote time, and
ALWAYS include our own resting clip's size while it is on the book for
whichever maker strategy this packet's ticker reflects (S1; see the fill
rule below). Ticker rows are written AFTER the execution(s) sharing that
same timestamp are applied (post-trade state), so a row's sizes/prices are
the book AS IT STOOD immediately after anything that happened at that
instant, own fill included.

## Fill rule (applies to every claim; population is defined in each claim)

{fill_rule_text}.

Own order size for any maker strategy under test: {own_size} units. An
order that improves the touch (quotes inside the current best) has
queue-ahead = 0 by construction (nothing can be ahead of a brand-new best
price).

## Notes

- Instrument tick: {tick} (price units). Fee: 0 bps maker and taker.
- Sizes in both files are displayed/executed totals, not per-order detail.
- The ticker (quote) file and the execution file are separate update
  streams with their own timestamps.
- Generated: {generated_utc} (seed {seed}).
"""


def build_manifest(tape_info: dict, seed: int) -> str:
    return MANIFEST_TEMPLATE.format(
        tape_days=TAPE_DAYS, quote_file=tape_info["quote_file"], execution_file=tape_info["execution_file"],
        n_quote_rows=tape_info["n_quote_rows"], n_execution_rows=tape_info["n_execution_rows"],
        tick=TICK, own_size=OWN_SIZE, generated_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
        fill_rule_text=FILL_RULE_TEXT,
    )


FILL_RULE_TEXT = (
    "resting order joins the back of the displayed queue at insertion; it fills when "
    "cumulative executions at its price on its side since insertion exceed queue-ahead + "
    "own size, or partially per FIFO; cancelled and re-joined at the new best when the "
    "touch moves away; after our own fill, the OPPOSITE-side exit order is a NEW order "
    "inserted at the back of the displayed queue AT THAT MOMENT (queue-ahead = displayed "
    "size at insertion, minus own size, since the displayed size at insertion already "
    "includes our own just-joined clip -- see the ticker-timing rule below); each entry "
    "has its own exit order, there is no netting across positions, and at most one open "
    "position per side at a time (a new entry quote on a side is placed only when that "
    "side has no open position); ticker rows are written AFTER the execution(s) at that "
    "same timestamp are applied (post-trade); positions = completed entry fills; forced "
    "exits at the 300 s cap cross EXACTLY at the displayed public touch at exit time -- "
    "no additional slippage is modelled"
)


def _sign_significance_ja(mean: float, t_stat: float, alpha_t: float = 2.0) -> str:
    """Describes a realized mean/t-stat truthfully -- used so claim text is
    never hardcoded to an assumed sign (v1's bug: QA3-1/QA3-3 text hardcoded
    'negative, significant' / 'no significant difference from 0' regardless
    of what the hidden logs actually produced). Written from whatever the
    number IS, per the fix spec's "do not target the sign" instruction."""
    if not math.isfinite(t_stat) or abs(t_stat) < alpha_t:
        return "0 との有意差はない"
    return ("正" if mean > 0 else "負") + "かつ有意である"


def build_claims(s1: dict, s2: dict, naive: dict) -> tuple[str, list[dict]]:
    # item 5-(2) stop condition: the naive (queue-blind) fill model must be
    # MORE OPTIMISTIC than the true, stated rule by >= 1bps, or wrong-signed
    # relative to it -- otherwise QA3-2 cannot honestly be marked "false"
    # and generation must fail loudly rather than seal a broken claim.
    gap = naive["net_bps_mean"] - s1["net_bps_mean"]
    wrong_sign = (naive["net_bps_mean"] > 0) != (s1["net_bps_mean"] > 0)
    if not (gap >= 1.0 or wrong_sign):
        raise RuntimeError(
            f"QA3-2 stop condition failed: naive net_bps_mean={naive['net_bps_mean']:.4f} is not "
            f">=1bps more optimistic than the true-rule S1 net_bps_mean={s1['net_bps_mean']:.4f} "
            f"(gap={gap:.4f}) and is not wrong-signed relative to it -- per the fix spec, "
            f"generation must stop here rather than seal a false QA3-2."
        )

    claims = [
        {
            "id": "QA3-1", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉。約定規則: {FILL_RULE_TEXT}。"
                     f"この規則の下でネット = {s1['net_bps_mean']:+.2f}bps/往復 (t={s1['net_bps_t_stat']:.2f})。"
                     f"{_sign_significance_ja(s1['net_bps_mean'], s1['net_bps_t_stat'])}。"),
        },
        {
            "id": "QA3-2", "category": "naive_bias", "truth_class": "naive_model_bias", "claim_correct": False,
            "text": (f"母集団=S1と同じ建玉群だが、約定規則を『挿入後に自分の価格・サイドで最初に印字された"
                     f"執行を無条件に約定とみなす(キュー先行量を無視)』に置き換えて PUBLIC テープを再生した"
                     f"場合、ネット = {naive['net_bps_mean']:+.2f}bps/往復 (t={naive['net_bps_t_stat']:.2f}) と"
                     f"なり、正しい規則({s1['net_bps_mean']:+.2f}bps)より楽観的であり、したがってこの"
                     f"素朴な計算だけからでも取引可能なエッジの存在が結論できる。"),
        },
        {
            "id": "QA3-3", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、"
                     f"それ以外は最良気配、300秒 cap)の完了建玉。同じ約定規則: {FILL_RULE_TEXT}。"
                     f"ネット = {s2['net_bps_mean']:+.2f}bps/往復 (t={s2['net_bps_t_stat']:.2f})。"
                     f"{_sign_significance_ja(s2['net_bps_mean'], s2['net_bps_t_stat'])}。"),
        },
        {
            "id": "QA3-4", "category": "adverse_selection", "truth_class": "adverse_selection_magnitude",
            "claim_correct": False,
            "text": (f"母集団=S1(約定規則: {FILL_RULE_TEXT})のエントリー約定(参入 leg のみ)。5秒地点の"
                     f"逆選択(adverse selection、エントリー約定直後の mid の変化を符号調整したもの)は"
                     f"ゼロと統計的に区別できない。"),
        },
        {
            "id": "QA3-5", "category": "survivorship", "truth_class": "survivorship_and_reference_trap",
            "claim_correct": False,
            "text": (f"母集団=S1(約定規則: {FILL_RULE_TEXT})の完了建玉のうち、300秒 cap で taker 決済"
                     f"(forced exit)になったものを除外した部分集合。この部分集合の平均ネットは "
                     f"{s1['survivorship_biased_net_bps_if_forced_dropped']:+.2f}bps であり、"
                     f"これが戦略の正しい期待値の推定である。"),
        },
        {
            "id": "QA3-6", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S1(約定規則: {FILL_RULE_TEXT})の完了建玉。300秒 cap に到達し taker として"
                     f"決済された(forced exit)建玉の比率は {s1['forced_exit_fraction'] * 100:.1f}% である。"),
        },
    ]
    lines = ["# QA known-answer packet (generation 3, v2, maker fill model) -- claims for auditors", "",
             "## 約定規則 (すべての主張に共通)", "", FILL_RULE_TEXT, "",
             "母集団の定義は各主張の本文中に明記する。以下 6 件を判定せよ。番号 (QA3-1..QA3-6) を報告の"
             "見出しに使うこと。", ""]
    for c in claims:
        lines.append(f"## {c['id']}\n\n{c['text']}\n")
    return "\n".join(lines), claims


# ======================================================================= #
# orchestration
# ======================================================================= #
def generate(out_dir: Path, seed: int, tape_days: float = TAPE_DAYS, hidden_dir: Path | None = None) -> dict:
    """hidden_dir defaults to the real docs/QA/hidden_maker3 location; tests
    and ad hoc runs MUST pass their own tmp hidden_dir so they never
    clobber the sealed ground truth that goes with the real published
    tape (a fixed default here previously let a test run silently
    overwrite the real hidden files -- found while finishing this
    generator; always pass hidden_dir explicitly outside of main())."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    span_sec = tape_days * 86400.0

    bg_rng = np.random.default_rng(rng.integers(0, 2**63 - 1))
    events = simulate_background(bg_rng, span_sec)
    mid = MidLookup(events)

    s1_positions = run_strategy(events, mid, inside_mode=False)
    s2_positions = run_strategy(events, mid, inside_mode=True)
    markouts(s1_positions, mid)
    markouts(s2_positions, mid)

    tape_rng = np.random.default_rng(rng.integers(0, 2**63 - 1))
    tape_info = build_public_tape(events, s1_positions, s2_positions, tape_rng, out_dir)
    crossed_idx = tape_info.pop("crossed_book_rows_idx")

    naive = naive_net(events, mid)
    s1_summary = summarize(s1_positions, "S1_symmetric_at_best")
    s2_summary = summarize(s2_positions, "S2_inside_one_tick")

    run_self_checks(events, tape_info, out_dir, s1_positions, s2_positions)
    independent = verify_independent_replay(out_dir, tape_info, s1_summary, s2_summary)

    manifest = build_manifest(tape_info, seed)
    (out_dir / "manifest.md").write_text(manifest)
    claims_md, claims = build_claims(s1_summary, s2_summary, naive)

    if hidden_dir is None:
        hidden_dir = REPO_ROOT / "docs" / "QA" / "hidden_maker3_v2"
    hidden_dir.mkdir(parents=True, exist_ok=True)
    s1_file = hidden_dir / "s1_positions.csv.gz"
    s2_file = hidden_dir / "s2_positions.csv.gz"
    gzip_write_text(s1_file, pd.DataFrame(s1_positions).to_csv(index=False))
    gzip_write_text(s2_file, pd.DataFrame(s2_positions).to_csv(index=False))

    answers = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "dataset_dir": str(out_dir.relative_to(REPO_ROOT)) if out_dir.is_relative_to(REPO_ROOT) else str(out_dir),
        "hidden_dir": str(hidden_dir.relative_to(REPO_ROOT)) if hidden_dir.is_relative_to(REPO_ROOT) else str(hidden_dir),
        "tape": tape_info,
        "own_size": OWN_SIZE, "cap_seconds": CAP_SECONDS, "tick": TICK, "tick_bps": TICK_BPS,
        "fill_rule": FILL_RULE_TEXT,
        "S1_symmetric_at_best": s1_summary,
        "S2_inside_one_tick": s2_summary,
        "naive_fill_on_print_at_best": naive,
        "independent_public_only_replay": {
            "note": "second, separately-written replay reading ONLY the two public files + "
                     "FILL_RULE_TEXT (see independent_public_replay() in this script) -- "
                     "verified to match S1/S2 net_bps_mean/n_positions/forced_exit_fraction "
                     "exactly in verify_independent_replay() before this json is written",
            "S1_symmetric_at_best": independent["S1_symmetric_at_best"],
            "S2_inside_one_tick": independent["S2_inside_one_tick"],
        },
        "seed_selection": {"seeds_tried": SEEDS_TRIED, "selected_seed": SEED, "note": SEED_SELECTION_NOTE},
        "traps": {
            "crossed_book_rows": {
                "file": tape_info["quote_file"], "fraction_target": CROSSED_BOOK_FRACTION,
                "row_indices": crossed_idx, "n_rows": len(crossed_idx),
            },
            "survivorship_bias_if_forced_exits_dropped": {
                "scenario": "S1_symmetric_at_best",
                "fraction_forced": s1_summary["forced_exit_fraction"],
                "correct_net_bps_all_positions": s1_summary["net_bps_mean"],
                "biased_net_bps_if_dropped": s1_summary["survivorship_biased_net_bps_if_forced_dropped"],
            },
        },
        "claims": claims,
    }
    return {"manifest": manifest, "claims_md": claims_md, "answers": answers,
            "events": events, "s1_positions": s1_positions, "s2_positions": s2_positions}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--answers-out", default=None)
    ap.add_argument("--claims-out", default=None)
    ap.add_argument("--tape-days", type=float, default=TAPE_DAYS)
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_known_answer_maker3_v2_{args.date}"
    answers_out = Path(args.answers_out) if args.answers_out else REPO_ROOT / "docs" / "QA" / "answers_sealed_maker3_v2.json"
    claims_out = Path(args.claims_out) if args.claims_out else REPO_ROOT / "docs" / "QA" / "claims_for_auditors_maker3_v2.md"
    answers_out.parent.mkdir(parents=True, exist_ok=True)
    claims_out.parent.mkdir(parents=True, exist_ok=True)

    result = generate(out_dir, args.seed, args.tape_days)
    answers_out.write_text(json.dumps(result["answers"], indent=2, ensure_ascii=False, sort_keys=False))
    claims_out.write_text(result["claims_md"])

    print(f"wrote dataset -> {out_dir}")
    print(f"wrote sealed answers -> {answers_out}")
    print(f"wrote claims -> {claims_out}")
    s1 = result["answers"]["S1_symmetric_at_best"]
    s2 = result["answers"]["S2_inside_one_tick"]
    naive = result["answers"]["naive_fill_on_print_at_best"]
    print(f"S1 net={s1['net_bps_mean']:.3f}bps t={s1['net_bps_t_stat']:.2f} n={s1['n_positions']} "
          f"forced={s1['forced_exit_fraction']:.3f} adv5s={s1['adverse_selection_bps_at_5s_mean']:.3f} "
          f"t={s1['adverse_selection_t_stat']:.2f}")
    print(f"S2 net={s2['net_bps_mean']:+.3f}bps t={s2['net_bps_t_stat']:.2f} n={s2['n_positions']}")
    print(f"naive net={naive['net_bps_mean']:+.3f}bps t={naive['net_bps_t_stat']:.2f} n={naive['n_positions']}")
    print(f"seed={args.seed} (seeds tried: {sorted(SEEDS_TRIED)})")
    print("independent public-only replay matched sealed S1/S2 net/n/forced_fraction exactly")


if __name__ == "__main__":
    main()
