"""Critic, item 0, round 3.

1. Shift invariance (re-check of i0-r2-01 from the other side). Time is an
   int64 of ns over its whole range (time.py, `validate_nanos` takes 0 and
   negatives). Nothing in the core may treat one instant as special, so the
   same run with every input time shifted by a constant K must produce the
   same deliveries, the same notices and the same order views, shifted by K.
   Shifts: to the epoch, across the epoch (times go from negative to
   positive during the run), and deep before 1970. Random venue answers,
   random latencies, cancels sent twice and after final states.

2. Cancel counting (re-check of i0-r2-02). At every callback, for every
   order, `cancels_in_flight` must equal (cancels the strategy sent) minus
   (notices delivered that answer one of its cancels), counted independently
   from the notices' public fields; after the run every count is 0 and the
   strategy's view of every order agrees with the venue ledger.
"""
from __future__ import annotations

import random

import pytest

from bot.bt.core import CoreEngine, NullCostModel

from i0r3_harness import SEC, RandomLatency, RandomTrader, RandomVenue, random_input

BASE = 1_700_006_400_000_000_000
VIEW_OF_VENUE = {"FILLED": "FILLED", "CANCELED": "CANCELED", "REJECTED": "REJECTED",
                 "STATE_UNKNOWN": "STATE_UNKNOWN", "LIVE": "OPEN"}


def _run(seed: int, shift: int):
    rng_in = random.Random(seed)
    events = random_input(rng_in, BASE + shift)
    trader = RandomTrader(random.Random(seed + 1), shift)
    res = CoreEngine(trader, events, RandomVenue(random.Random(seed + 2)), RandomLatency(random.Random(seed + 3)),
                     NullCostModel()).run()
    fills = [(f.client_order_id, f.price, f.size, f.venue_time_ns - shift) for f in res.fills]
    return trader, res, fills


@pytest.mark.parametrize("shift", [-BASE, -BASE - 50_000_000, -BASE - 3 * SEC, -2 * BASE])
def test_run_is_invariant_under_shifting_every_time(shift):
    diffs = []
    for seed in range(15):
        t0, r0, f0 = _run(seed, 0)
        t1, r1, f1 = _run(seed, shift)
        if t0.trace != t1.trace or f0 != f1 or r0.venue_states != r1.venue_states:
            first = next((i for i, (a, b) in enumerate(zip(t0.trace, t1.trace)) if a != b), None)
            diffs.append((seed, first, None if first is None else (t0.trace[first], t1.trace[first])))
    assert diffs == [], f"shift {shift}: {len(diffs)} of 15 seeds differ; first: {diffs[0]}"


def test_cancel_count_equals_cancels_sent_minus_answers_delivered():
    bad, total_cancels, double = [], 0, 0
    for seed in range(100):
        trader, res, _ = _run(seed, 0)
        total_cancels += sum(trader.sent_cancels.values())
        double += sum(1 for v in trader.sent_cancels.values() if v >= 2)
        if trader.count_mismatch:
            bad.append((seed, trader.count_mismatch[0]))
            continue
        for c, v in res.orders.items():
            if v.cancels_in_flight != 0:
                bad.append((seed, "left in flight", c, v.cancels_in_flight))
            if v.state.value != VIEW_OF_VENUE[res.venue_states[c]]:
                bad.append((seed, "view != ledger", c, v.state.value, res.venue_states[c]))
    assert total_cancels > 300 and double > 30  # the runs do exercise what is tested
    assert bad == [], f"{len(bad)} problems; first: {bad[:3]}"
