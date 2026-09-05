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
  real bitFlyer touch sizes (see CALIBRATION_NOTES below). A market order's
  side is an UNBIASED coin flip (no memory of past order flow at all -- see
  the v3 note below); its size is a small FRACTION of the CURRENT displayed
  depth on the side it consumes (PRINT_FRAC_MU/SIGMA). It consumes that
  side's queue front-to-back; if it exhausts the level, price steps by one
  tick ("walk") and a fresh queue is seeded. Cancellations remove one
  background order at a uniformly random queue position. A fraction of
  market orders are flagged "informed": each such print is ALSO followed
  by a small, permanent, ONE-TIME price shift (INFORMED_SHIFT_TICKS_MEAN
  ticks) in its own direction -- nothing is added after the fact, and this
  shift has no effect on any FUTURE order's direction (that would be v2's
  feedback bug). This phase returns one flat, time-ordered event log
  (`events` DataFrame) plus a full touch-state timeline (bid/ask price and
  BACKGROUND-ONLY depth at every event).

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

v3 (coordinator review of v2): v2's circuit breakers (MAX_TICKS_ABS,
MAX_SPREAD_TICKS -- both DELETED) were masking a degenerate book: spread
sat pinned at the breaker on the large majority of ticker rows, letting a
maker earn tens of bps/round-trip on an instrument whose resting spread is
supposed to be ~2 ticks. v3 removes the breakers AND their actual root
cause -- v2's "impulse" mechanism, where an informed print biased the
DIRECTION of subsequent order flow, which could then itself be informed
and biased further: a real, unbounded positive-feedback loop, and mean
reversion (REVERSION_KAPPA) only ever pulled the MID back toward PRICE0,
applying zero restoring force to bid/ask independently drifting apart
(which is what actually blew the spread out once per-event walk size grew
in v2). v3's market-order side is an unbiased coin (P_BUY_BASELINE) with
no memory of past order flow at all; "informed" only ever adds a bounded,
ONE-TIME permanent shift (INFORMED_SHIFT_TICKS_MEAN, Poisson mean 1.3) in
that one order's own direction. Liquidity replenishment (_join_rate) now
runs FASTER the wider the spread already is -- an arrival-RATE effect, not
just a higher per-join improve probability -- which is the sole (and, per
run_self_checks' hard acceptance asserts, sufficient) restoring force on
the spread. A 2nd coordinator round then fixed market-order SIZE (see
PRINT_FRAC_MU/SIGMA): absolute sizes comparable to the touch made most
prints sweep whole levels, defeating queue position; sizes are now a small
fraction of touch depth, as on the real venue. See the longer v3 comments
above RATE_MARKET/JOIN_RATE_SLOPE for the full reasoning trace, including
the reported-but-not-fully-resolved tension the STOP note there covers
(resolved by the lead's NAIVE_GAP_CRITERION_REVISION, not by relaxing the
spread/adverse-selection/forced-fraction criteria).

Files written to backtest_data/qa_known_answer_maker3_v3_<date>/:
  ticker_qa_maker3_v3_tape.csv.gz      ts,best_bid,best_ask,best_bid_size,best_ask_size
  executions_qa_maker3_v3_tape.csv.gz  id,ts,price,size,side
  manifest.md                          (full fill rule incl. the 3 stated
                                        ambiguities; no planted numbers)

Hidden ground truth (never shown to an auditor):
  docs/QA/hidden_maker3_v3/s1_positions.csv.gz
  docs/QA/hidden_maker3_v3/s2_positions.csv.gz
Sealed summary -> docs/QA/answers_sealed_maker3_v3.json
Claims         -> docs/QA/claims_for_auditors_maker3_v3.md (6 claims, 3 true
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
# v3 seed choice, final (docs/QA/known_answer_results_2026-09-05.md, two
# rounds of coordinator review): RATE_MARKET, JOIN_RATE_SLOPE, P_INFORMED,
# INFORMED_SHIFT_TICKS_MEAN, and PRINT_FRAC_MU/SIGMA (market-order size as
# a fraction of touch depth, round 2's fix) were tuned FIRST against the
# full set of hard acceptance criteria in run_self_checks() -- spread
# stability, adverse selection in [0.3,1.0]bps at t>=5, forced_exit_fraction
# in [0.15,0.45], S1 |net| p95<=8bps, price range +-5%, mid-move p99<=3bps,
# and the revised naive-gap criterion (NAIVE_GAP_CRITERION_REVISION) -- then,
# with those fixed, <=5 seeds were tried and measured (full 5-day tape, no
# other post-hoc tuning). S1's net sign/magnitude were NOT targeted at any
# seed. Per-seed results at the final parameter setting (all rounded to the
# same precision generate() seals):
#   seed      S1net(t)      naive(t)       gap    forced  adv5s(t)      maxspr frac123 p95net
#   20260907  0.215(1.88)   0.831(71.30)  0.616   0.463*  0.415(16.51)  7      0.941   7.96*
#   20260908  0.334(3.16)   0.842(73.27)  0.507   0.446   0.480(18.09)  7      0.942   7.04
#   20260909  0.160(1.42)   0.873(75.34)  0.713   0.453*  0.485(18.37)  7      0.942   8.03*
#   20260910  0.305(2.80)   0.836(74.63)  0.531   0.446   0.454(18.39)  7      0.944   6.98  <- SELECTED
#   20260911  0.234(2.10)   0.849(75.61)  0.615   0.447   0.493(18.38)  8      0.942   7.02
# (* = fails forced_exit_fraction<=0.45 and/or S1 |net| p95<=8bps -- 20260907
# and 20260909 are excluded on those grounds, unrelated to the naive-gap
# revision). 20260908 and 20260911 also satisfy every criterion; 20260910
# was used per the coordinator's explicit instruction (it is the seed the
# criterion revision was evaluated against). All five are recorded verbatim
# in SEEDS_TRIED and echoed into the sealed json's "seed_selection" field.
SEED = 20260910
SEEDS_TRIED = {
    20260907: {"S1_net_bps_mean": 0.215, "S1_net_bps_t_stat": 1.879, "naive_net_bps_mean": 0.8311,
               "naive_net_bps_t_stat": 71.299, "gap": 0.6161, "forced_exit_fraction": 0.4626,
               "adverse_selection_bps_at_5s_mean": 0.4145, "adverse_selection_t_stat": 16.506,
               "max_spread_ticks": 7, "frac_spread_1_2_3": 0.9413, "s1_abs_net_p95_bps": 7.958,
               "meets_all_criteria": False, "excluded_for": "forced_exit_fraction>0.45; S1 |net| p95>8bps"},
    20260908: {"S1_net_bps_mean": 0.3344, "S1_net_bps_t_stat": 3.164, "naive_net_bps_mean": 0.8417,
               "naive_net_bps_t_stat": 73.269, "gap": 0.5073, "forced_exit_fraction": 0.4458,
               "adverse_selection_bps_at_5s_mean": 0.4804, "adverse_selection_t_stat": 18.091,
               "max_spread_ticks": 7, "frac_spread_1_2_3": 0.9419, "s1_abs_net_p95_bps": 7.035,
               "meets_all_criteria": True, "excluded_for": None},
    20260909: {"S1_net_bps_mean": 0.1603, "S1_net_bps_t_stat": 1.421, "naive_net_bps_mean": 0.8732,
               "naive_net_bps_t_stat": 75.335, "gap": 0.7129, "forced_exit_fraction": 0.4533,
               "adverse_selection_bps_at_5s_mean": 0.4851, "adverse_selection_t_stat": 18.372,
               "max_spread_ticks": 7, "frac_spread_1_2_3": 0.9423, "s1_abs_net_p95_bps": 8.035,
               "meets_all_criteria": False, "excluded_for": "forced_exit_fraction>0.45; S1 |net| p95>8bps"},
    20260910: {"S1_net_bps_mean": 0.3046, "S1_net_bps_t_stat": 2.795, "naive_net_bps_mean": 0.8357,
               "naive_net_bps_t_stat": 74.631, "gap": 0.5311, "forced_exit_fraction": 0.446,
               "adverse_selection_bps_at_5s_mean": 0.4542, "adverse_selection_t_stat": 18.391,
               "max_spread_ticks": 7, "frac_spread_1_2_3": 0.9435, "s1_abs_net_p95_bps": 6.978,
               "meets_all_criteria": True, "excluded_for": None, "selected": True},
    20260911: {"S1_net_bps_mean": 0.2342, "S1_net_bps_t_stat": 2.097, "naive_net_bps_mean": 0.8487,
               "naive_net_bps_t_stat": 75.614, "gap": 0.6145, "forced_exit_fraction": 0.4472,
               "adverse_selection_bps_at_5s_mean": 0.493, "adverse_selection_t_stat": 18.376,
               "max_spread_ticks": 8, "frac_spread_1_2_3": 0.9422, "s1_abs_net_p95_bps": 7.018,
               "meets_all_criteria": True, "excluded_for": None},
}
SEED_SELECTION_NOTE = (
    "criterion = S1 adverse_selection_bps_at_5s_mean in [0.3,1.0] with t>=5, PLUS spread "
    "in {1,2,3} ticks in >=85% of ticker rows (max<=8), forced_exit_fraction in [0.15,0.45], "
    "S1 |net| p95<=8bps, 5-day price range within +-5%, mid-move p99<=3bps, and the revised "
    "naive-gap criterion (see NAIVE_GAP_CRITERION_REVISION) -- all measured BEFORE picking a "
    "seed, with informed-flow/replenishment/market-order-size parameters fixed first (see the "
    "v3 comments above RATE_MARKET, JOIN_RATE_SLOPE, P_INFORMED, PRINT_FRAC_MU for the tuning "
    "trace across two coordinator review rounds); S1's net sign/magnitude were not targeted at "
    "any seed. 20260910 was selected per the coordinator's explicit instruction (it was the "
    "seed used to evaluate the criterion revision); 20260908 and 20260911 also satisfy every "
    "criterion at this parameter setting, 20260907 and 20260909 do not (forced_exit_fraction "
    "and/or S1 |net| p95 out of band)."
)
# Lead decision, recorded verbatim (coordinator message, criterion revision
# for item 2's naive-vs-true-rule requirement): the original ">=1.0bps gap"
# threshold was arbitrary; the actual purpose is that the naive fill-on-
# print model reaches a DIFFERENT CONCLUSION from the true rule. Revised
# criterion applied below and asserted in run_self_checks() /
# build_claims(): naive net >= 2x true net, AND naive net is statistically
# significant (t>=3), AND gap (naive - true) >= 0.5bps.
NAIVE_GAP_CRITERION_REVISION = (
    "Lead decision (recorded in the results doc as a criterion revision, with reason): the "
    "1.0 bps gap threshold was an arbitrary number; the purpose of the criterion is that the "
    "naive fill-on-print model reaches a DIFFERENT CONCLUSION from the true rule. Revised "
    "criterion: naive net >= 2 x true net AND naive net is statistically significant (t >= 3) "
    "AND gap >= 0.5 bps."
)


def _naive_gap_criterion_met(naive_summary: dict, s1_summary: dict) -> tuple[bool, float]:
    """The revised naive-vs-true-rule criterion (NAIVE_GAP_CRITERION_REVISION),
    shared by run_self_checks() (fails loudly) and build_claims() (decides
    whether QA3-2's 'therefore a tradable edge exists' claim can honestly be
    marked false). Returns (meets, gap)."""
    naive_net = naive_summary["net_bps_mean"]
    s1_net = s1_summary["net_bps_mean"]
    gap = naive_net - s1_net
    meets = (naive_net >= 2.0 * s1_net) and (naive_summary["net_bps_t_stat"] >= 3.0) and (gap >= 0.5)
    return meets, gap

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
# background LOB process rates (per second; tuned by simulate-and-measure)
# --------------------------------------------------------------------- #
# v3 (coordinator review of v2, docs/QA/known_answer_results_2026-09-05.md):
# v2's circuit breakers (MAX_TICKS_ABS / MAX_SPREAD_TICKS, now DELETED) were
# masking a book that was unstable BY CONSTRUCTION -- spread sat pinned at
# the breaker most of the time, giving a maker "edge" of tens of bps on an
# instrument whose resting spread is supposed to be ~2 ticks. v3 removes
# both the breakers AND their root cause:
#   1. the v2 "impulse" feedback (an informed print biased the DIRECTION of
#      subsequent order flow, which could then itself be informed and
#      biased further -- a real, unbounded positive-feedback loop) is
#      GONE. Every market order's side is an unbiased coin flip
#      (P_BUY_BASELINE); "informed" only ever adds a bounded, ONE-TIME
#      permanent tick shift, with no effect on any FUTURE order's
#      direction. This is the entire fix -- nothing else in v2 was
#      actually unstable on its own.
#   2. mean reversion of the price level (v2's REVERSION_KAPPA) is GONE per
#      spec ("no mean reversion of fair value, no bounds"): with the
#      feedback loop removed, an unbiased informed random walk stays
#      comfortably inside a +-5% band over 5 days on its own (variance
#      accumulates as sqrt(n_informed_events), never linearly).
#   3. liquidity replenishment (limit-order arrivals AT the touch and ONE
#      TICK INSIDE) now runs FASTER the wider the spread already is
#      (_join_rate below): baseline RATE_JOIN at spread<=2, scaling up
#      (quadratically in the excess) beyond that. This is what keeps the
#      SPREAD itself stable by construction (REVERSION_KAPPA only ever
#      pulled the MID back toward PRICE0 -- it applied zero restoring
#      force to bid/ask independently drifting apart, which is what
#      actually blew the spread out in v2 once per-event walk size grew).
#
# v3, 2nd round (coordinator diagnosis): market orders were an ABSOLUTE
# size comparable to the touch, so most prints swept whole levels --
# "first print at my price" (naive) was then ~= "level consumed"
# regardless of queue-ahead, which is why the naive-vs-true-rule gap stuck
# near 0.18bps no matter how hard informed-flow strength was pushed. Round
# 2 makes EVERY market order (informed or not) a small FRACTION of the
# CURRENT touch (PRINT_FRAC_MU/SIGMA below), which is what actually moves
# the gap. RATE_MARKET/JOIN_RATE_SLOPE were then retuned by the ACTUAL
# acceptance criteria (gap, forced_exit_fraction, S1 |net| p95), landing
# well below a pure volume-per-hour-matching estimate -- see the STOP
# note further below (by JOIN_RATE_SLOPE) for the final, reported,
# not-fully-resolved tension between these criteria.
RATE_MARKET = 0.082
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
# v3 (coordinator, 2nd round): market-order size (informed or not) is now
# drawn as a FRACTION of the CURRENT displayed touch size on the side being
# consumed (median 5%, p95 60% -- real bitFlyer prints are median
# ~0.01-0.03 vs a ~0.5 touch, i.e. a small fraction of the level, so queue
# position is normally decisive; v3's first round used an ABSOLUTE size
# distribution comparable to the touch itself, which made most prints
# sweep whole levels -- "first print at my price" was then ~= "level
# consumed" regardless of queue-ahead, collapsing the naive-vs-true-rule
# gap this fixes). Non-informed draws are HARD-CAPPED at 100% of the level
# (so they can never need a second one, by construction, not by a separate
# walk cap); informed draws are the SAME distribution UNCAPPED, so an
# occasional large tail draw can still exceed the level and walk
# (MAX_WALK_LEVELS) -- multi-level sweeps are an informed-only phenomenon,
# per the coordinator, but a TYPICAL informed print is just as small as a
# typical non-informed one (being informed is about carrying information,
# not about size). Median picked at the LOW end of the coordinator's 5-8%
# band -- it gave the widest naive-vs-true gap in the sweep.
# Solve lognormal(mu,sigma) for median=0.05, p95=0.60:
# mu = ln(0.05); p95 = exp(mu + 1.6449 sigma) = 0.60 =>
# sigma = (ln(0.60) - mu) / 1.6449.
PRINT_FRAC_MU = math.log(0.05)
PRINT_FRAC_SIGMA = (math.log(0.60) - PRINT_FRAC_MU) / 1.6449


def _p_improve(spread_ticks: int) -> float:
    """Prob. a limit-join event improves the price instead of joining the
    back of the current level. Pulls a wide spread back toward 2 ticks
    increasingly hard; cannot improve at spread==1."""
    if spread_ticks <= 1:
        return 0.0
    if spread_ticks == 2:
        return P_IMPROVE_BASE
    return min(0.92, P_IMPROVE_WIDE_BASE + 0.20 * (spread_ticks - 3))


# v3: replenishment-intensity multiplier -- the coordinator's specified
# mechanism ("arrival rate x spread_ticks"), floored at spread<=2 so the
# baseline RATE_JOIN is unaffected at the target spread. JOIN_RATE_SLOPE is
# the one replenishment-strength knob item 3 allows tuning.
#
# STOP -- reported to the coordinator, not fully resolved (see the session
# report): even after round 2's market-order-size fix raised the naive-vs-
# true gap from +0.18bps to +0.51..+0.83bps across the 5 seeds (still
# checked against the ORIGINAL >=1bps threshold at the time), the lead then
# revised the acceptance criterion itself (NAIVE_GAP_CRITERION_REVISION) --
# naive net >= 2x true net AND naive t>=3 AND gap>=0.5bps -- which seed
# 20260910 satisfies (naive=0.836 >= 2*0.305=0.610; t=74.6; gap=0.531). This
# JOIN_RATE_SLOPE/RATE_MARKET pair is the closest point found where that
# revised gap criterion, forced_exit_fraction<=0.45, and S1 |net| p95<=8bps
# all hold simultaneously; pushing the gap further (seen up to ~0.7-0.8 in
# the sweep) pushes forced_fraction past 0.45 and/or p95 past 8bps.
JOIN_RATE_SLOPE = 28.0


def _join_rate(spread_ticks: int) -> float:
    """Effective background limit-join ARRIVAL rate (not just the
    probability that a given join improves, see _p_improve): rises with
    the SQUARE of how far spread has widened past 2 ticks, so a widening
    spread pulls in replenishment faster in real time, not just more
    probably per join. This -- not mean-reversion of the price level -- is
    what keeps the SPREAD itself stable by construction. Quadratic (not
    linear) in the excess: a mild, common 3-tick widening barely needs
    extra replenishment (letting normal short-lived episodes still form,
    which is what the naive-vs-true-rule fill gap depends on), while a
    rare, large excursion gets pulled back MUCH harder -- found necessary
    to keep max spread bounded without flattening ordinary spread
    dynamics into permanent fast-reformation mode."""
    if spread_ticks <= 2:
        return RATE_JOIN
    excess = spread_ticks - 2
    return RATE_JOIN * (1.0 + JOIN_RATE_SLOPE * excess * excess)


# v3: informed flow = an UNBIASED market order (P_BUY_BASELINE, no
# direction feedback of any kind) that, with probability P_INFORMED, is
# ALSO followed by a permanent one-time fair-value shift of
# INFORMED_SHIFT_TICKS_MEAN ticks (Poisson, floor 1) in its own direction
# -- applied unconditionally on an informed print whose OWN mechanical
# consumption did not already deplete a level (levels_walked==0 -- see the
# gate at the call site: stacking a separate shift on an already-multi-
# level-walking print produced the spread>8 tail an earlier attempt hit).
# P_INFORMED and INFORMED_SHIFT_TICKS_MEAN are the only informed-flow knobs
# item 3 allows tuning (mean held at the specified 1.3; P_INFORMED held at
# the coordinator's specified 0.85 -- "keep all other parameters as in
# your passing config" -- not retuned in round 2).
P_BUY_BASELINE = 0.5
P_INFORMED = 0.85
INFORMED_SHIFT_TICKS_MEAN = 1.3   # = 1 + Poisson(0.3): floor 1 tick, occasionally 2+

MAX_WALK_LEVELS = 3      # safety cap on levels a single market order's OWN
                          # mechanical consumption can cross in ONE event --
                          # an occasional oversized print sweeping many thin
                          # freshly-reseeded levels in one shot is what could
                          # still spike the spread past the max-8 acceptance
                          # bound even with the informed-shift gated off that
                          # same event (levels_walked==0); a normal print
                          # rarely exceeds one level's depth at all, so this
                          # only ever trims the extreme tail, never the
                          # typical case. Non-informed orders are separately
                          # limited to 1 level by their own size cap (see
                          # PRINT_FRAC_MU/SIGMA); only informed orders can
                          # reach this cap at all.
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
        n_orders = len(bid_orders) + len(ask_orders)
        rate_cancel = CANCEL_HAZARD_PER_ORDER * n_orders
        spread_now = ask_ticks - bid_ticks
        rate_decay = RATE_SPREAD1_DECAY if spread_now <= 1 else 0.0
        # v3: replenishment intensity itself (not just P(improve|join))
        # rises with spread -- see _join_rate. This is the sole restoring
        # force on the spread now that REVERSION_KAPPA is gone; there is no
        # breaker downstream, so if this is too weak the self-checks below
        # fail loudly rather than a clamp silently papering over it.
        rate_join_now = _join_rate(spread_now)
        rate_total = RATE_MARKET + rate_join_now + rate_cancel + rate_decay
        dt = rng.exponential(1.0 / rate_total)
        t += dt
        if t >= span_sec:
            break

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
            # v3: side is an UNBIASED coin, full stop -- no impulse, no
            # mean-reversion pull. This is the actual fix (see the module
            # docstring / the v3 comment above RATE_MARKET): v2's feedback
            # loop (informed prints biasing the direction of FUTURE order
            # flow, which could then itself be informed) was the sole
            # source of the runaway instability the circuit breakers were
            # papering over. Nothing here can reinforce itself.
            side_buy = rng.random() < P_BUY_BASELINE
            informed = rng.random() < P_INFORMED
            # v3 (2nd round, coordinator): EVERY market order -- informed
            # or not -- draws its size as a FRACTION of the CURRENT
            # displayed depth on the side about to be consumed (median 5%,
            # p95 60%; PRINT_FRAC_MU/SIGMA), matching real bitFlyer prints
            # being a small fraction of the touch (so queue position is
            # normally decisive). Being "informed" is about carrying
            # information, not about size: a small informed print still
            # triggers the permanent fair-value shift below. Non-informed
            # orders are HARD-CAPPED at 100% of the level (can never need a
            # second one); informed orders draw from the SAME distribution
            # UNCAPPED, so an occasional large tail draw can still exceed
            # the level and walk (MAX_WALK_LEVELS) -- multi-level sweeps
            # are an informed-only phenomenon, per the coordinator, but a
            # TYPICAL informed print is just as small as a typical
            # non-informed one.
            touch_depth = depth(ask_orders if side_buy else bid_orders)
            frac = float(rng.lognormal(PRINT_FRAC_MU, PRINT_FRAC_SIGMA))
            if not informed:
                frac = min(1.0, frac)
            size = frac * touch_depth
            remaining = size
            levels_walked = 0
            max_levels_this_order = MAX_WALK_LEVELS if informed else 1
            while remaining > 1e-9 and levels_walked < max_levels_this_order:
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
            if informed and levels_walked == 0:
                # v3: informed flow = a market order followed by a
                # PERMANENT, bounded fair-value shift (Poisson,
                # INFORMED_SHIFT_TICKS_MEAN, floor 1 tick) in its own
                # direction, with NO effect on any future order's direction
                # (that coupling -- not the shift itself -- was v2's actual
                # bug). Gated on levels_walked==0: an occasional oversized
                # print that ALREADY mechanically swept several levels has
                # already moved price by that much and revealed its
                # information through the walk itself; stacking a SEPARATE
                # shift on top of that (both within the same event, hence
                # the same instant, before any replenishment can react) is
                # what produced the spread>8 tail this gate removes -- found
                # via the max-spread acceptance check, not assumed.
                # Each shift tick gets its own record() row (etype="walk",
                # zero size, no exec_id): a multi-tick move that skipped
                # intermediate rows would be exactly the v1 failure mode
                # (an unobservable thing that decides outcomes) transplanted
                # into the background process itself -- found via the
                # independent-replay cross-check, which is the entire point
                # of having a second, separately-written replay.
                n_shift = 1 + int(rng.poisson(INFORMED_SHIFT_TICKS_MEAN - 1.0))
                for _ in range(n_shift):
                    # Advance t by a tiny epsilon (not a real inter-arrival
                    # draw) so the shift's own ticker rows carry a STRICTLY
                    # LATER timestamp than the triggering print, not a tied
                    # one. Needed for markouts(): MidLookup.at() resolves a
                    # tie by landing on the LAST same-timestamp row, so a
                    # same-tick shift was silently already baked into the
                    # entry-fill markout's OWN baseline (m0) and therefore
                    # invisible to the 5s-forward adverse-selection measure
                    # -- found empirically (adverse selection stayed
                    # ~0.06bps regardless of P_INFORMED/shift size until
                    # this was separated out).
                    t += 1e-3
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

        elif r < RATE_MARKET + rate_join_now:
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
            # ends up written to ticker_qa_maker3_v3_tape.csv.gz at/just
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
    efile = "executions_qa_maker3_v3_tape.csv.gz"
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
    qfile = "ticker_qa_maker3_v3_tape.csv.gz"
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
                     s1_positions: list[dict], s2_positions: list[dict],
                     s1_summary: dict, s2_summary: dict, naive_summary: dict,
                     tape_days: float = TAPE_DAYS) -> None:
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

    # ---- v3 hard acceptance criteria (coordinator round-2/round-3/round-4
    # review of v2/v3). These assert the BOOK ITSELF is stable BY
    # CONSTRUCTION (no circuit breakers -- MAX_TICKS_ABS/MAX_SPREAD_TICKS
    # were deleted, not tightened) and that the economics of the packet
    # (adverse selection, forced-exit fraction, S1 net) sit in a realistic
    # band. Any failure here means the parameters need to change -- it is
    # NOT permitted to relax a threshold to make a failure disappear.
    #
    # These bands were tuned/measured against the FULL 5-day tape only (see
    # SEEDS_TRIED / SEED_SELECTION_NOTE: "all measured ... full 5-day
    # tape"). A short tape (e.g. tests calling generate() with a small
    # tape_days for speed) has far fewer own-position samples, so
    # t-statistics that comfortably clear their threshold at full length
    # (adverse selection t=18, naive t=75) mechanically shrink by roughly
    # sqrt(scale) and can legitimately miss a threshold like t>=5 even
    # though the underlying per-event process is identical -- that is a
    # sample-size artifact of the shortened tape, not an instability, so
    # these checks only run once the tape is at (or effectively at) full
    # length. The process-shape checks just above (tick grid, median touch,
    # forced-exit price, mean-decomposition identity, fill consistency)
    # still run unconditionally at any tape_days.
    if tape_days < TAPE_DAYS * 0.9:
        return

    # spread distribution: >=85% of ticker rows at spread in {1,2,3} ticks,
    # and spread must never exceed 8 ticks (no unbounded blow-ups).
    spread_ticks = np.round((tick_ask - tick_bid) / TICK).astype(np.int64)
    frac_123 = float(np.mean(np.isin(spread_ticks, [1, 2, 3])))
    max_spread = int(spread_ticks.max())
    assert frac_123 >= 0.85, f"spread in {{1,2,3}} ticks only {frac_123:.3f} of rows, need >=0.85"
    assert max_spread <= 8, f"max spread {max_spread} ticks exceeds 8"

    # |mid move| per row, p99 <= 3bps (no per-tick jump instability).
    mid = (tick_bid + tick_ask) / 2.0
    mid_move_bps = np.abs(np.diff(mid)) / mid[:-1] * 1e4
    p99_move = float(np.percentile(mid_move_bps, 99)) if len(mid_move_bps) else 0.0
    assert p99_move <= 3.0, f"|mid move| p99 {p99_move:.3f}bps exceeds 3bps"

    # 5-day price range within +-5% of PRICE0 (no unbounded drift -- the
    # informed shift is a one-time bounded kick with NO mean reversion and
    # NO explicit bound, so this is checked empirically, not enforced by a
    # breaker).
    lo_px, hi_px = float(mid.min()), float(mid.max())
    assert lo_px >= PRICE0 * 0.95 and hi_px <= PRICE0 * 1.05, \
        f"5-day price range [{lo_px}, {hi_px}] outside +-5% of {PRICE0}"

    # S1 |net| p95 <= 8bps (realistic maker per-position P&L, not the
    # degenerate +-30-60bps of the void v2 packet).
    s1_abs_net_p95 = float(np.percentile(np.abs([p["net_bps"] for p in s1_positions]), 95)) if s1_positions else 0.0
    assert s1_abs_net_p95 <= 8.0, f"S1 |net| p95 {s1_abs_net_p95:.3f}bps exceeds 8bps"

    # forced_exit_fraction in [0.15, 0.45] for S1 (not near-zero, not
    # dominating the sample).
    s1_forced_frac = s1_summary["forced_exit_fraction"]
    assert 0.15 <= s1_forced_frac <= 0.45, f"S1 forced_exit_fraction {s1_forced_frac:.3f} outside [0.15,0.45]"

    # adverse selection at 5s in [0.3, 1.0]bps with t>=5 (a real, but not
    # exaggerated, informed-flow signature).
    adv_mean = s1_summary["adverse_selection_bps_at_5s_mean"]
    adv_t = s1_summary["adverse_selection_t_stat"]
    assert 0.3 <= adv_mean <= 1.0, f"adverse selection at 5s {adv_mean:.4f}bps outside [0.3,1.0]"
    assert adv_t >= 5.0, f"adverse selection t-stat {adv_t:.3f} < 5"

    # naive (queue-blind, fill-on-first-print) comparison model must reach
    # a DIFFERENT ECONOMIC CONCLUSION from the true queue-aware rule --
    # see NAIVE_GAP_CRITERION_REVISION for the exact, coordinator-revised
    # form of this criterion (recorded verbatim in the sealed json).
    meets_gap, gap_val = _naive_gap_criterion_met(naive_summary, s1_summary)
    assert meets_gap, (
        f"naive-gap criterion not met: naive_net={naive_summary['net_bps_mean']:.4f}bps "
        f"(t={naive_summary['net_bps_t_stat']:.3f}) vs S1 net={s1_summary['net_bps_mean']:.4f}bps, "
        f"gap={gap_val:.4f}bps -- see NAIVE_GAP_CRITERION_REVISION"
    )


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
MANIFEST_TEMPLATE = """# QA known-answer packet (generation 3, v3) -- maker fill model -- manifest

Synthetic data generated by `scripts/qa/make_known_answer_maker3.py` (fixed
seed). Nothing here is real market data.

Do not open `docs/QA/answers_sealed_maker3_v3.json` before completing an
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
    # item 5-(2) stop condition, REVISED (round-4 lead decision -- see
    # NAIVE_GAP_CRITERION_REVISION, also recorded verbatim in the sealed
    # json): the original ">=1bps or wrong-sign" threshold was arbitrary;
    # what actually matters is that the naive (queue-blind) fill model
    # reaches a DIFFERENT ECONOMIC CONCLUSION from the true, stated rule.
    # Replaced with _naive_gap_criterion_met (naive_net >= 2x true_net AND
    # naive_t>=3 AND gap>=0.5bps). If it is not met, generation must stop
    # here rather than seal a false QA3-2.
    meets_gap, gap = _naive_gap_criterion_met(naive, s1)
    if not meets_gap:
        raise RuntimeError(
            f"QA3-2 stop condition failed (revised criterion): naive net_bps_mean="
            f"{naive['net_bps_mean']:.4f} (t={naive['net_bps_t_stat']:.3f}) vs true-rule S1 "
            f"net_bps_mean={s1['net_bps_mean']:.4f} (gap={gap:.4f}) does not satisfy "
            f"naive>=2x*S1 AND naive_t>=3 AND gap>=0.5bps -- see NAIVE_GAP_CRITERION_REVISION. "
            f"Per the fix spec, generation must stop here rather than seal a false QA3-2."
        )

    claims = [
        {
            "id": "QA3-1", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S1(最良気配で対称的に両建て quote、300秒 cap)の完了建玉。上記の約定規則の下で"
                     f"ネット = {s1['net_bps_mean']:+.2f}bps/往復 (t={s1['net_bps_t_stat']:.2f})。"
                     f"{_sign_significance_ja(s1['net_bps_mean'], s1['net_bps_t_stat'])}。"),
        },
        {
            "id": "QA3-2", "category": "naive_bias", "truth_class": "naive_model_bias", "claim_correct": False,
            "text": (f"母集団=S1と同じ建玉群だが、約定規則を『挿入後に自分の価格・サイドで最初に印字された"
                     f"執行を無条件に約定とみなす(キュー先行量を無視)』に置き換えて PUBLIC テープを再生した"
                     f"場合、ネット = {naive['net_bps_mean']:+.2f}bps/往復 (t={naive['net_bps_t_stat']:.2f}) と"
                     f"なる。これは上記の約定規則(正しい規則)の下でのネット {s1['net_bps_mean']:+.2f}bps/往復"
                     f"(t={s1['net_bps_t_stat']:.2f})より大幅に楽観的であり、したがってこの素朴な計算だけからでも"
                     f"取引可能なエッジが存在すると結論できる。"),
        },
        {
            "id": "QA3-3", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S2(スプレッド2tick以上のとき最良気配より1tick内側に improve して両建て quote、"
                     f"それ以外は最良気配、300秒 cap)の完了建玉。上記と同じ約定規則の下でネット = "
                     f"{s2['net_bps_mean']:+.2f}bps/往復 (t={s2['net_bps_t_stat']:.2f})。"
                     f"{_sign_significance_ja(s2['net_bps_mean'], s2['net_bps_t_stat'])}。"),
        },
        {
            "id": "QA3-4", "category": "adverse_selection", "truth_class": "adverse_selection_magnitude",
            "claim_correct": False,
            "text": (f"母集団=S1(上記の約定規則)のエントリー約定(参入 leg のみ)。5秒地点の逆選択"
                     f"(adverse selection、エントリー約定直後の mid の変化を符号調整したもの)は"
                     f"ゼロと統計的に区別できない。"),
        },
        {
            "id": "QA3-5", "category": "survivorship", "truth_class": "survivorship_and_reference_trap",
            "claim_correct": False,
            "text": (f"母集団=S1(上記の約定規則)の完了建玉のうち、300秒 cap で taker 決済(forced exit)"
                     f"になったものを除外した部分集合。この部分集合の平均ネットは "
                     f"{s1['survivorship_biased_net_bps_if_forced_dropped']:+.2f}bps であり、"
                     f"これが戦略の正しい期待値の推定である。"),
        },
        {
            "id": "QA3-6", "category": "maker_fill", "truth_class": "true_effect", "claim_correct": True,
            "text": (f"母集団=S1(上記の約定規則)の完了建玉。300秒 cap に到達し taker として決済された"
                     f"(forced exit)建玉の比率は {s1['forced_exit_fraction'] * 100:.1f}% である。"),
        },
    ]
    lines = ["# QA known-answer packet (generation 3, v3, maker fill model) -- claims for auditors", "",
             "## 約定規則 (すべての主張に共通。以下、各主張本文の「上記の約定規則」はこれを指す)", "",
             FILL_RULE_TEXT, "",
             "母集団の定義(戦略 S1/S2 の別、cap 秒数など)は各主張の本文中に明記する。以下 6 件を判定せよ。"
             "番号 (QA3-1..QA3-6) を報告の見出しに使うこと。", ""]
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

    run_self_checks(events, tape_info, out_dir, s1_positions, s2_positions, s1_summary, s2_summary, naive,
                     tape_days=tape_days)
    independent = verify_independent_replay(out_dir, tape_info, s1_summary, s2_summary)

    manifest = build_manifest(tape_info, seed)
    (out_dir / "manifest.md").write_text(manifest)
    claims_md, claims = build_claims(s1_summary, s2_summary, naive)

    if hidden_dir is None:
        hidden_dir = REPO_ROOT / "docs" / "QA" / "hidden_maker3_v3"
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
        "seed_selection": {
            "seeds_tried": SEEDS_TRIED, "selected_seed": SEED, "note": SEED_SELECTION_NOTE,
            "naive_gap_criterion_revision": NAIVE_GAP_CRITERION_REVISION,
        },
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

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_known_answer_maker3_v3_{args.date}"
    answers_out = Path(args.answers_out) if args.answers_out else REPO_ROOT / "docs" / "QA" / "answers_sealed_maker3_v3.json"
    claims_out = Path(args.claims_out) if args.claims_out else REPO_ROOT / "docs" / "QA" / "claims_for_auditors_maker3_v3.md"
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
