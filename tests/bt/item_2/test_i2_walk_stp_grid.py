"""Adversarial grid: walking the book, self-trade prevention, post-only
(C2-7 walking market orders; C2-3 self-trade; C2-1 post-only).

1. Walk: 300 seeded random books (1-5 levels a side, random sizes) x side x
   order {market, limit at a random level or between levels} x size (random,
   sometimes above the whole side). Oracle: take levels best first, each up
   to its size, while the level reaches the limit; a market order's
   remainder is cancelled (market_remainder = cancel), a GTC limit's
   remainder rests; fills are taker fills at the level prices.
2. Self-trade: policy {cancel_taker, cancel_maker, cancel_both, not declared}
   x our resting order's price vs the external best {better, equal, worse}
   x incoming {market, marketable limit} x side = 48 runs. Oracle: the
   incoming order reaches our resting order when it is at or better than the
   external best (and within the limit); then cancel_taker cancels the
   incoming order (what it took before stays), cancel_maker cancels ours and
   goes on, cancel_both cancels both; not declared refuses the run.
3. Post-only: policy {reject_if_crossing, cancel_if_crossing, not declared} x
   what it would cross {the external book, our own resting order, nothing}
   x side = 18 runs.

Not enumerated: several of our resting orders in the walk path (one is
enough to decide the policy; the loop is the same), impact-priced walks
(tier 6 does not walk: tier grid and scenes).
"""
from __future__ import annotations

import itertools
import random

import pytest

from i2_gridkit import MS, T0, avg_px, book, filled, inp, place, run

RULES = {"off_tick": "reject", "below_min_qty": "reject", "post_only": "reject_if_crossing",
         "market_remainder": "cancel", "mark": "last_trade"}


def _book(rng):
    mid = 10000.0
    bids, asks = [], []
    p = mid - rng.randint(1, 3)
    for _ in range(rng.randint(1, 5)):
        bids.append((p, rng.choice([0.1, 0.3, 0.5, 1.0, 2.0])))
        p -= rng.randint(1, 4)
    p = mid + rng.randint(1, 3)
    for _ in range(rng.randint(1, 5)):
        asks.append((p, rng.choice([0.1, 0.3, 0.5, 1.0, 2.0])))
        p += rng.randint(1, 4)
    return bids, asks


@pytest.mark.parametrize("seed", range(300))
def test_walk(seed):
    rng = random.Random(seed)
    bids, asks = _book(rng)
    side = rng.choice(("buy", "sell"))
    levels = asks if side == "buy" else bids
    typ = rng.choice(("market", "limit"))
    size = round(rng.choice([0.05, 0.4, 1.3, 2.7, 9.0]), 2)
    limit = None
    if typ == "limit":
        k = rng.randrange(len(levels))
        limit = levels[k][0] + (rng.choice([0.0, 0.5]) * (1 if side == "buy" else -1))
        limit = float(round(limit))
    left, got, notional = size, 0.0, 0.0
    for px, sz in levels:
        if limit is not None and (px > limit if side == "buy" else px < limit):
            break
        take = min(left, sz)
        got += take
        notional += take * px
        left -= take
        if left <= 1e-12:
            break
    obs, refused = run(inp([book(T0, bids, asks)], [place(T0 + 1 * MS, "o1", side, typ, size, px=limit)], rules=RULES))
    assert refused is None, refused
    assert filled(obs, "o1") == pytest.approx(got, abs=1e-9)
    if got > 0:
        assert avg_px(obs, "o1") == pytest.approx(notional / got, rel=1e-12)
        assert all(f["liq"] == "taker" for f in obs["fills"])
    full = got >= size - 1e-9
    exp = "filled" if full else ("canceled" if typ == "market" else "open")
    assert obs["orders"]["o1"]["status"] == exp


STP = list(itertools.product(("cancel_taker", "cancel_maker", "cancel_both", None), ("better", "equal", "worse"),
                             ("market", "limit"), ("buy", "sell")))


def test_stp_grid_size():
    assert len(STP) == 48


@pytest.mark.parametrize("combo", STP, ids=["-".join(map(str, c)) for c in STP])
def test_self_trade(combo):
    policy, where, incoming, side = combo
    s = 1 if side == "buy" else -1
    ext_best = 10001.0 if side == "buy" else 9999.0
    own_px = {"better": ext_best - s * 1, "equal": ext_best, "worse": ext_best + s * 1}[where]
    rules = dict(RULES)
    if policy:
        rules["self_trade"] = policy
    other = "sell" if side == "buy" else "buy"
    # our resting order on the other side; it must not cross the external book itself
    bk = book(T0, [(9999.0, 1.0), (9990.0, 5)], [(10001.0, 1.0), (10010.0, 5)])
    # the grid's prices never let our resting order cross the external book itself
    assert not ((other == "sell" and own_px <= 9999.0) or (other == "buy" and own_px >= 10001.0))
    limit = (10005.0 if side == "buy" else 9995.0) if incoming == "limit" else None
    actions = [place(T0 + 1 * MS, "mine", other, "limit", 1.0, px=own_px),
               place(T0 + 2 * MS, "in", side, incoming, 1.5, px=limit)]
    obs, refused = run(inp([bk], actions, rules=rules))
    # oracle: walk the external levels and our own order, best first (ours first at an equal price)
    ext = [[10001.0, 1.0], [10010.0, 5.0]] if side == "buy" else [[9999.0, 1.0], [9990.0, 5.0]]
    within = (lambda p: limit is None or (p <= limit if side == "buy" else p >= limit))  # noqa: E731
    better_eq = (lambda a, b: a <= b if side == "buy" else a >= b)  # noqa: E731
    left, got, mine_live, in_status, mine_status, meets_own = 1.5, 0.0, True, None, "open", False
    while left > 1e-12:
        lvl = next((x for x in ext if x[1] > 1e-12), None)
        if mine_live and within(own_px) and (lvl is None or better_eq(own_px, lvl[0])):
            meets_own = True
            if policy is None:
                break
            if policy in ("cancel_maker", "cancel_both"):
                mine_live, mine_status = False, "canceled"
            if policy in ("cancel_taker", "cancel_both"):
                in_status = "canceled"
                break
            continue
        if lvl is None or not within(lvl[0]):
            break
        take = min(left, lvl[1])
        lvl[1] -= take
        got += take
        left -= take
    if meets_own and policy is None:
        assert obs is None and "self_trade" in refused
        return
    assert refused is None, refused
    if in_status is None:
        in_status = "filled" if left <= 1e-12 else ("canceled" if incoming == "market" else "open")
    assert filled(obs, "in") == pytest.approx(got, abs=1e-12)
    assert obs["orders"]["in"]["status"] == in_status
    assert obs["orders"]["mine"]["status"] == mine_status


POST = list(itertools.product(("reject_if_crossing", "cancel_if_crossing", None), ("external", "own", "nothing"),
                              ("buy", "sell")))


@pytest.mark.parametrize("combo", POST, ids=["-".join(map(str, c)) for c in POST])
def test_post_only(combo):
    policy, crosses, side = combo
    rules = {k: v for k, v in RULES.items() if k != "post_only"}
    if policy:
        rules["post_only"] = policy
    other = "sell" if side == "buy" else "buy"
    actions = []
    if crosses == "own":
        actions.append(place(T0 + 1 * MS, "mine", other, "limit", 1.0, px=10000.0))
        px = 10000.0
    elif crosses == "external":
        px = 10001.0 if side == "buy" else 9999.0
    else:
        px = 9995.0 if side == "buy" else 10005.0
    actions.append(place(T0 + 2 * MS, "p", side, "limit", 1.0, px=px, post_only=True))
    obs, refused = run(inp([book(T0, [(9999.0, 5)], [(10001.0, 5)])], actions, rules=rules))
    if crosses != "nothing" and policy is None:
        assert obs is None and "post_only" in refused
        return
    assert refused is None, refused
    st = obs["orders"]["p"]["status"]
    if crosses == "nothing":
        assert st == "open"
    else:
        assert st == ("rejected" if policy == "reject_if_crossing" else "canceled")
        assert filled(obs, "p") == 0.0
