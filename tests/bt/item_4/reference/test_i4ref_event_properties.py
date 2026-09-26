"""Property tests for the event reference on seeded random scenarios.

Inputs are drawn from a fixed grid of event kinds, times, latencies and
modes with the standard-library random module (fixed seeds); they are not
built from the reference's own branches. Properties checked:
  P1 no look-ahead: every item a strategy sees has t_recv <= now, and every
     item (market event or notification) with t_recv < now has already been
     delivered;
  P2 determinism and input-order independence (seq is the tie-breaker);
  P3 accounting identity: equity = initial + realized + unrealized - fees + funding,
     exactly (Fractions);
  P4 quantity conservation: sum of signed fills = position; per order,
     filled <= ordered;
  P5 a resting (maker) fill is always at the order's own limit price, and in
     strict mode never at a trade printed exactly at the limit;
  P6 latency: fill time >= submit time + order latency; note t_recv =
     t_exch + notify latency;
  P7 what the strategy is handed cannot be changed by the strategy.
Grid not covered (written here on purpose): bar events are delivered but not
matched; multiple instruments; partial cancel; order amendment.
"""
from __future__ import annotations

import dataclasses
import random
from fractions import Fraction as F

import pytest

from bot.bt.reference.event_sim import Cancel, Limit, Market, Note, make_event, simulate

SEEDS = list(range(40))
MODES = [(liq, cross, fq) for liq in ("book", "trades") for cross in ("strict", "touch")
         for fq in ("full", "trade_qty")]


def rand_events(rng: random.Random):
    evs, t, seq = [], 0, 0
    px = 1000
    order = list(range(60))
    rng.shuffle(order)  # seq values unrelated to position in time
    for i in range(60):
        t += rng.choice([0, 0, 1, 5, 10])  # repeated times on purpose
        recv = t + rng.choice([0, 0, 3, 20])
        k = rng.choices(["trade", "book", "funding", "clock", "bar"], [6, 3, 1, 1, 1])[0]
        s = order[i]
        if k == "trade":
            px = max(1, px + rng.randint(-3, 3))
            evs.append(make_event("trade", t, recv, s, price=px, qty=rng.choice(["0.5", 1, 2])))
        elif k == "book":
            evs.append(make_event("book", t, recv, s, bids=[(px - 1, 1), (px - 2, 2)],
                                  asks=[(px + 1, "0.5"), (px + 2, 2)]))
        elif k == "funding":
            evs.append(make_event("funding", t, recv, s, rate=rng.choice(["0.0001", "-0.0002"]),
                                  price=rng.choice([None, px])))
        elif k == "bar":
            evs.append(make_event("bar", t, recv, s, open=px, high=px + 2, low=px - 2, close=px))
        else:
            evs.append(make_event("clock", t, recv, s))
        seq += 1
    return evs


class RandStrategy:
    """Seeded random actions; records every context for later checks."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.n = 0
        self.log = []  # (now, visible)
        self.submitted = {}  # cid -> (now, action)

    def __call__(self, ctx):
        self.log.append((ctx.now, ctx.visible))
        last = [it for it in ctx.visible if not isinstance(it, Note) and it.kind == "trade"]
        ref = last[-1].price if last else F(1000)
        acts = []
        if self.rng.random() < 0.35:
            self.n += 1
            cid = f"o{self.n}"
            side = self.rng.choice(["buy", "sell"])
            qty = self.rng.choice(["0.5", 1, "1.5"])
            if self.rng.random() < 0.4:
                a = Market(cid, side, qty)
            else:
                off = self.rng.randint(-3, 3)
                a = Limit(cid, side, qty, int(ref) + off, self.rng.random() < 0.3)
            acts.append(a)
            self.submitted[cid] = (ctx.now, a)
        if self.submitted and self.rng.random() < 0.1:
            acts.append(Cancel(self.rng.choice(sorted(self.submitted))))
        return acts


def params(rng: random.Random, mode) -> dict:
    liq, cross, fq = mode
    return dict(initial_cash=rng.choice([0, 10000]), maker_rate=rng.choice(["-0.0002", "0", "0.0001"]),
                taker_rate=rng.choice(["0", "0.001"]), order_latency_ns=rng.choice([0, 2, 7]),
                cancel_latency_ns=rng.choice([0, 4]), notify_latency_ns=rng.choice([0, 1, 9]),
                tick_size=1, lot_size="0.5", min_qty="0.5", liquidity=liq, limit_cross=cross,
                limit_fill_qty=fq)


def run(seed: int, mode, shuffle: bool = False):
    rng = random.Random(seed)
    evs = rand_events(rng)
    p = params(rng, mode)
    if shuffle:
        evs = list(evs)
        random.Random(seed + 999).shuffle(evs)
    st = RandStrategy(seed)
    return simulate(evs, st, **p), st, evs, p


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("seed", SEEDS[:10])
def test_p1_no_lookahead_and_complete_delivery(seed, mode):
    r, st, evs, _p = run(seed, mode)
    all_items = [(t, w, i) for t, w, i, _k in r.deliveries]
    for now, vis in st.log:
        assert all(it.t_recv <= now for it in vis)
        # every market event with t_recv < now was delivered before this call
        seen = {it.seq for it in vis if not isinstance(it, Note)}
        assert {e.seq for e in evs if e.t_recv < now} <= seen
        seen_notes = {id(it) for it in vis if isinstance(it, Note)}
        assert {id(n) for n in r.notes if n.t_recv < now} <= seen_notes
    assert len(st.log) == len(all_items)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("seed", SEEDS[:10])
def test_p2_deterministic_and_input_order_free(seed, mode):
    a = run(seed, mode)[0].to_dict()
    b = run(seed, mode)[0].to_dict()
    c = run(seed, mode, shuffle=True)[0].to_dict()
    assert a == b == c


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("seed", SEEDS)
def test_p3_p4_p5_p6_accounting_quantities_prices_latency(seed, mode):
    r, st, _evs, p = run(seed, mode)
    # P3
    if r.last_mark is not None or r.position == 0:
        assert r.equity == r.initial_cash + r.realized + r.unrealized - r.fees + r.funding
    # P4
    assert sum((f.qty if f.side == "buy" else -f.qty) for f in r.fills) == r.position
    per = {}
    for f in r.fills:
        per[f.cid] = per.get(f.cid, 0) + f.qty
    for cid, got in per.items():
        assert got <= F(st.submitted[cid][1].qty)
    # P5
    trades_at = {}
    for e in _evs:
        if e.kind == "trade":
            trades_at.setdefault(e.t_exch, []).append(e.price)
    for f in r.fills:
        if f.liquidity == "maker":
            a = st.submitted[f.cid][1]
            assert isinstance(a, Limit) and f.price == F(a.price)
            if p["limit_cross"] == "strict":
                prints = trades_at[f.t_exch]
                better = [x for x in prints if (x < f.price if f.side == "buy" else x > f.price)]
                assert better, "strict maker fill without a print through the limit"
    # P6
    for f in r.fills:
        assert f.t_exch >= st.submitted[f.cid][0] + p["order_latency_ns"]
    for n in r.notes:
        assert n.t_recv == n.t_exch + p["notify_latency_ns"]


def test_p7_strategy_cannot_change_what_it_was_handed():
    evs = [make_event("trade", 1, 1, 1, price=100, qty=1), make_event("trade", 2, 2, 2, price=101, qty=1)]
    errors = []

    def meddler(ctx):
        try:
            ctx.visible[0].__setattr__("price", F(1))
        except dataclasses.FrozenInstanceError:
            errors.append("frozen")
        try:
            ctx.visible.append(None)  # type: ignore[attr-defined]
        except AttributeError:
            errors.append("tuple")
        return []

    r = simulate(evs, meddler, initial_cash=0, maker_rate=0, taker_rate=0, order_latency_ns=0,
                 cancel_latency_ns=0, notify_latency_ns=0, tick_size=1, lot_size=1, min_qty=1,
                 liquidity="trades", limit_cross="strict", limit_fill_qty="full")
    assert errors == ["frozen", "tuple"] * 2
    assert evs[0].price == 100 and r.equity_curve[-1][1] == 101
