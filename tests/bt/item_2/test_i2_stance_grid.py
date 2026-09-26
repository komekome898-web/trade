"""Adversarial grid: the stances on cancels ahead of us (C2-6; catalogue
section 2.2 and the probabilistic queue) in a queue tier.

1. Aggregate stances: {none, discount_at_entry r in (0, 0.25, 1), snapshot_cap,
   prob power n in (0.5, 1, 2), prob log} x 60 seeded random paths = 540 runs.
   A path: a book with a random size S0 at our bid 10000, our buy of 3 at
   T0+1ms, then 8 steps, each a new snapshot of the level (random size, up or
   down) or a print at 10000 (random size, sell aggressor) or a print
   through (9999). The oracle is the stance texts of bot.bt.fill.spec:
   ahead starts at the level size at rest (x (1 - r) for discount_at_entry);
   a snapshot: none / discount -> no change, snapshot_cap -> min(ahead, new),
   prob -> with d = prev - new > 0, front = ahead, back = prev - ahead,
   p = f(back) / (f(back) + f(front)), ahead = min(front - (1-p) d +
   min(back - p d, 0), new); prev = new after every snapshot; a print at our
   price consumes ahead first (prev falls by what it took from the others),
   the rest fills us; a print through fills the rest of us.
2. L3 stances: 40 seeded random per-order feeds (adds at our price before and
   after our order, cancels of any of them, prints) x {l3_advance, l3_mark}:
   the oracle keeps the ids in front of us in FIFO order; a cancelled one
   leaves; a print consumes them from the front, then us. Both stances must
   fill the same; `queue_ahead` shows a marked (cancelled, not yet passed)
   entry only under l3_mark.
3. Several of our orders at one price (the documented order: each of ours
   is behind the external size that was displayed when it rested).

Not enumerated: book deltas (a delta at our price is the same update as a
snapshot of that level; the scenes use snapshots), sell-side queues (the
tier grid runs both sides of the same code), stances under tier 6 (tier 6
uses tier 5's queue for resting orders, tier grid).
"""
from __future__ import annotations

import math
import random

import pytest

from bot.bt.core import BookSnapshotEvent, OrderRequest, TradeEvent
from bot.bt.costs import CostSchedule
from bot.bt.fill import FillSpec, L3Add, L3Cancel, L3Feed, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from i2_gridkit import MS, T0, book, filled, inp, place, run, trade

L = 10000.0
STANCES = [("none", {}), ("discount_at_entry", {"cancel_rate": 0.0}), ("discount_at_entry", {"cancel_rate": 0.25}),
           ("discount_at_entry", {"cancel_rate": 1.0}), ("snapshot_cap", {}),
           ("prob", {"prob_f": "power", "prob_n": 0.5}), ("prob", {"prob_f": "power", "prob_n": 1}),
           ("prob", {"prob_f": "power", "prob_n": 2}), ("prob", {"prob_f": "log"})]
SEEDS = range(60)
GRID = [(st, ex, seed) for st, ex in STANCES for seed in SEEDS]


def test_grid_sizes():
    assert len(GRID) == 540


def path(seed):
    rng = random.Random(seed)
    s0 = rng.choice([0.0, 1.0, 2.5, 5.0])
    steps = []
    for _ in range(8):
        k = rng.random()
        if k < 0.5:
            steps.append(("snap", rng.choice([0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0])))
        elif k < 0.9:
            steps.append(("print", rng.choice([0.2, 0.5, 1.0, 1.5, 3.0])))
        else:
            steps.append(("through", 1.0))
    return s0, steps


def weight(ex, x):
    x = max(x, 0.0)
    return math.log1p(x) if ex.get("prob_f") == "log" else x ** ex["prob_n"]


def oracle(stance, ex, s0, steps, size=3.0):
    ahead = s0 * (1.0 - ex["cancel_rate"]) if stance == "discount_at_entry" else s0
    prev = s0
    got = 0.0
    for kind, v in steps:
        if got >= size:
            break
        if kind == "snap":
            new = v
            if stance == "snapshot_cap":
                ahead = min(ahead, new)
            elif stance == "prob":
                d = prev - new
                if d > 0:
                    front, back = ahead, max(prev - ahead, 0.0)
                    wf, wb = weight(ex, front), weight(ex, back)
                    p = wb / (wb + wf) if wb + wf > 0 else 0.0
                    ahead = max(min(front - (1 - p) * d + min(back - p * d, 0.0), new), 0.0)
            prev = new
        elif kind == "print":
            use = min(ahead, v)
            ahead -= use
            prev = max(prev - use, 0.0)
            got += min(size - got, v - use)
        else:
            got = size
    return got


@pytest.mark.parametrize("combo", GRID, ids=[f"{c[0]}-{sorted(c[1].items())}-{c[2]}" for c in GRID])
def test_aggregate_stance_grid(combo):
    stance, ex, seed = combo
    s0, steps = path(seed)
    lvl = [(L, s0)] if s0 > 0 else []
    market = [book(T0, lvl + [(9990.0, 5)], [(10100.0, 5)])]
    for i, (kind, v) in enumerate(steps):
        t = T0 + (10 + 10 * i) * MS
        if kind == "snap":
            market.append(book(t, ([(L, v)] if v > 0 else []) + [(9990.0, 5)], [(10100.0, 5)]))
        elif kind == "print":
            market.append(trade(t, L, v, "sell"))
        else:
            market.append(trade(t, 9999.0, v, "sell"))
    fm = {"tier": 5, "cancel_stance": stance, **ex}
    obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", "buy", "limit", 3.0, px=L)], fill_model=fm))
    assert refused is None, refused
    assert filled(obs, "o1") == pytest.approx(oracle(stance, ex, s0, steps), abs=1e-9)


L3_SEEDS = range(40)


def l3_path(seed):
    rng = random.Random(1000 + seed)
    before = [(f"a{i}", rng.choice([0.5, 1.0, 2.0])) for i in range(rng.randint(0, 5))]
    after = [(f"b{i}", rng.choice([0.5, 1.0, 2.0])) for i in range(rng.randint(0 if before else 1, 4))]
    ids = [i for i, _ in before + after]
    cancels = rng.sample(ids, k=rng.randint(0, len(ids))) if ids else []
    prints = [rng.choice([0.5, 1.0, 2.0, 3.0]) for _ in range(rng.randint(1, 4))]
    return before, after, cancels, prints


def l3_oracle(before, cancels, prints, size=3.0):
    front = [[i, q] for i, q in before if i not in cancels]
    got = 0.0
    for q in prints:
        budget = q
        while budget > 1e-12 and front:
            take = min(front[0][1], budget)
            front[0][1] -= take
            budget -= take
            if front[0][1] <= 1e-12:
                front.pop(0)
        got += min(size - got, budget)
    return got


@pytest.mark.parametrize("seed", L3_SEEDS)
def test_l3_stances_grid(seed):
    before, after, cancels, prints = l3_path(seed)
    market = [{"t": T0, "type": "l3_add", "id": i, "side": "bid", "px": L, "qty": q} for i, q in before]
    total_before = sum(q for _, q in before)
    market.append(book(T0, ([(L, total_before)] if total_before else []) + [(9990.0, 5)], [(10100.0, 5)]))
    market += [{"t": T0 + 2 * MS, "type": "l3_add", "id": i, "side": "bid", "px": L, "qty": q} for i, q in after]
    market += [{"t": T0 + 3 * MS, "type": "l3_cancel", "id": i} for i in cancels]
    market += [trade(T0 + (10 + 10 * k) * MS, L, q, "sell") for k, q in enumerate(prints)]
    results = {}
    for stance in ("l3_advance", "l3_mark"):
        # the driver maps the scene's "l3" to l3_advance; here each stance is named
        fm = {"tier": 5, "cancel_stance": "l3"} if stance == "l3_advance" else {"tier": 5, "cancel_stance": stance}
        obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", "buy", "limit", 3.0, px=L)], fill_model=fm))
        assert refused is None, refused
        results[stance] = filled(obs, "o1")
    exp = l3_oracle(before, set(cancels), prints)
    assert results["l3_advance"] == pytest.approx(exp, abs=1e-12)
    assert results["l3_mark"] == pytest.approx(exp, abs=1e-12)


def test_l3_stance_without_a_feed_is_refused():
    market = [book(T0, [(L, 2.0)], [(10100.0, 5)]), trade(T0 + 10 * MS, L, 3.0, "sell")]
    obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", "buy", "limit", 1.0, px=L)],
                           fill_model={"tier": 5, "cancel_stance": "l3_mark"}))
    assert obs is None and "reads a per-order feed" in refused


def _venue(stance, feed):
    product = Product("X", "test", 1.0, 0.01, 0.01, "JPY", True)
    return SimVenue(product=product, rules=VenueRules(), fill=FillSpec(tier=5, cancel_stance=stance),
                    costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="test"), faults=FaultPlan(()),
                    l3=feed)


def test_l3_mark_keeps_a_cancelled_entry_until_reached():
    feed_items = [L3Add(T0, "e1", "bid", L, 1.0), L3Add(T0, "e2", "bid", L, 1.0), L3Cancel(T0 + 5, "e1")]
    shown = {}
    for stance in ("l3_advance", "l3_mark"):
        v = _venue(stance, L3Feed(feed_items))
        v.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(L, 2.0)], asks=[(10100.0, 5)]), T0)
        v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=L, client_order_id="o1"), T0 + 1)
        v.on_market_event(TradeEvent(received_time_ns=T0 + 9, price=10050.0, size=1.0, side="buy"), T0 + 9)
        shown[stance] = v.queue_ahead("o1")
    assert shown["l3_advance"] == {"size": 1.0, "entries": 1}
    assert shown["l3_mark"] == {"size": 1.0, "entries": 2}


def test_two_of_our_orders_at_one_price():
    """o1 rests behind 2; one more joins; o2 rests behind the 3 displayed.
    A print of 4 fills o1 (1) and not o2; a print of 5 more... see oracle."""
    market = [book(T0, [(L, 2.0)], [(10100.0, 5)]), book(T0 + 2 * MS, [(L, 3.0)], [(10100.0, 5)]),
              trade(T0 + 10 * MS, L, 4.0, "sell"), trade(T0 + 20 * MS, L, 1.0, "sell")]
    actions = [place(T0 + 1 * MS, "o1", "buy", "limit", 1.0, px=L), place(T0 + 3 * MS, "o2", "buy", "limit", 1.0, px=L)]
    obs, refused = run(inp(market, actions, fill_model={"tier": 5, "cancel_stance": "none"}))
    assert refused is None, refused
    # FIFO: [ext 2, o1 1, ext 1, o2 1]; the print of 4 reaches o1 fully and the
    # external 1 behind it, o2 gets 0; the next print of 1 fills o2
    assert filled(obs, "o1") == 1.0
    assert [f["t"] for f in obs["fills"] if f["ref"] == "o2"] == [T0 + 20 * MS]
    assert filled(obs, "o2") == 1.0
