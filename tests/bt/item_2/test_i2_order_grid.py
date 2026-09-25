"""Adversarial grid: order type x time in force x post-only x reduce-only x
side x position before x limit-price placement (C2-1, C2-3 reduce-only /
post-only rules). All 864 combinations run; the oracle is written from the
rule texts (bot.bt.orders.client / bot.bt.fill.venue docstrings), for a fixed
market: book bids 9999x5 / 9998x5, asks 10001x5 / 10002x5 (never updated),
then a buy-aggressor print 10006 x100 at T0+10ms and a sell-aggressor print
9994 x100 at T0+20ms; the fill model is tier 4 (each reaching print fills up
to its size).

Not enumerated here (other grids or scenes cover them): order sizes other
than 1 (the rules grid), OCO and amend (test_i2_oco_amend_grid.py), latency
(test_i2_latency_grid.py), queue tiers (test_i2_tier_grid.py), books that
move after the order.
"""
from __future__ import annotations

import itertools

import pytest

from i2_gridkit import MS, T0, book, filled, avg_px, inp, place, run, trade

SIDES = ("buy", "sell")
TYPES = ("market", "limit", "stop", "stop_limit")
TIFS = ("GTC", "IOC", "FOK")
FLAGS = (False, True)
POSITIONS = (0, 1, -1)
PLACEMENTS = ("marketable", "inside", "far")
GRID = list(itertools.product(SIDES, TYPES, TIFS, FLAGS, FLAGS, POSITIONS, PLACEMENTS))
LIMIT = {("buy", "marketable"): 10001.0, ("buy", "inside"): 10000.0, ("buy", "far"): 9990.0,
         ("sell", "marketable"): 9999.0, ("sell", "inside"): 10000.0, ("sell", "far"): 10010.0}
TRIGGER = {"buy": 10005.0, "sell": 9995.0}


def test_grid_size():
    assert len(GRID) == 864


def oracle(side, typ, tif, post, reduce, pos0, placement):
    """(status, filled, avg price or None, sent)."""
    s = 1 if side == "buy" else -1
    if typ in ("stop", "stop_limit") and tif != "GTC":
        return "rejected", 0.0, None, 0  # refused by the client before sending
    if post and typ != "limit":
        return "rejected", 0.0, None, 0
    if reduce and (pos0 == 0 or (pos0 > 0) == (s > 0)):
        return "rejected", 0.0, None, 1  # the venue refuses a reduce-only order that would grow
    best = 10001.0 if side == "buy" else 9999.0
    L = LIMIT[(side, placement)] if typ in ("limit", "stop_limit") else None

    def marketable(price):
        return price >= best if side == "buy" else price <= best

    if typ == "limit" and post and marketable(L):
        return "rejected", 0.0, None, 1
    if typ == "market":
        return "filled", 1.0, best, 1
    if typ == "limit":
        if marketable(L):
            return "filled", 1.0, best, 1
        if tif in ("IOC", "FOK"):
            return "canceled", 0.0, None, 1
        reaches = 9994.0 <= L if side == "buy" else 10006.0 >= L
        return ("filled", 1.0, L, 1) if reaches else ("open", 0.0, None, 1)
    # stops: a buy stop 10005 fires on the 10006 print (T0+10ms), a sell stop
    # 9995 on the 9994 print (T0+20ms)
    if typ == "stop":
        return "filled", 1.0, best, 1
    if marketable(L):
        return "filled", 1.0, best, 1
    if side == "buy" and 9994.0 <= L:  # rests after T0+10ms, the 9994 print reaches it
        return "filled", 1.0, L, 1
    return "open", 0.0, None, 1


@pytest.mark.parametrize("combo", GRID, ids=["-".join(map(str, c)) for c in GRID])
def test_order_grid(combo):
    side, typ, tif, post, reduce, pos0, placement = combo
    actions = []
    if pos0:
        actions.append(place(T0 + 1 * MS, "o0", "buy" if pos0 > 0 else "sell", "market", 1.0))
    L = LIMIT[(side, placement)] if typ in ("limit", "stop_limit") else None
    trig = TRIGGER[side] if typ in ("stop", "stop_limit") else None
    actions.append(place(T0 + 2 * MS, "o1", side, typ, 1.0, px=L, stop_px=trig, tif=tif, post_only=post,
                         reduce_only=reduce))
    market = [book(T0, [(9999, 5), (9998, 5)], [(10001, 5), (10002, 5)]),
              trade(T0 + 10 * MS, 10006, 100, "buy"), trade(T0 + 20 * MS, 9994, 100, "sell")]
    obs, refused = run(inp(market, actions))
    assert refused is None, refused
    status, qty, px, sent = oracle(*combo)
    assert obs["orders"]["o1"]["status"] == status
    assert filled(obs, "o1") == pytest.approx(qty, abs=1e-12)
    if px is not None:
        assert avg_px(obs, "o1") == pytest.approx(px, rel=1e-12)
    assert obs["sent"]["o1"] == sent
    s = 1 if side == "buy" else -1
    assert obs["account"]["position"] == pytest.approx(pos0 + s * qty, abs=1e-12)
