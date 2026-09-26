"""Adversarial grid: the fill tiers 0-6 (C2-5; the catalogue section 2.1 one-line
definitions, made concrete in bot.bt.fill.spec) for one resting limit order.

tier (0-6) x side x print price vs the limit {through, at, away} x print size
{below what is ahead, between ahead and ahead + ours, above} x aggressor
{hits our side, same side as ours, unknown} x displayed size ahead {0, 2}
= 7 x 2 x 3 x 3 x 3 x 2 = 756 runs, all run.

Setup: book at T0 with the displayed size `ahead` at the limit 10000 (bids
for a buy / asks for a sell) and the other side far away; our limit order of
size 1 rests at T0+0.5s; one print at T0+2.5s. Tier 2 reads 1-second bars
built from the prints (the print's bar [2s, 3s) closes at T0+3s). Tier 6 =
tier 5 for a resting order (its impact function prices aggressive
executions only). The oracle below is written from the definitions:

  0 fills 1 at rest (T0+0.5s); 1 through -> 1; 2 through or at -> 1 at the
  bar's close; 3 through or at -> 1; 4 through or at -> min(1, print size);
  5/6 through -> 1; at -> if the aggressor hits our side or is unknown:
  min(1, max(print size - ahead, 0)), else 0; away -> 0.

Not enumerated: several prints (the scenes c2-5-* and the stance grid), our
own orders at the same level (test_i2_stance_grid.py), bars given by the data
(c2-12-jpx-bar-value), cancel stances (test_i2_stance_grid.py).
"""
from __future__ import annotations

import itertools

import pytest

from i2_gridkit import MS, SEC, T0, avg_px, book, filled, first_t, inp, place, run, trade

TIERS = range(7)
SIDES = ("buy", "sell")
WHERE = ("through", "at", "away")
SIZE = ("below_ahead", "between", "above")
AGGR = ("hits_us", "same_side", "unknown")
AHEAD = (0.0, 2.0)
GRID = list(itertools.product(TIERS, SIDES, WHERE, SIZE, AGGR, AHEAD))
L = 10000.0


def test_grid_size():
    assert len(GRID) == 756


def print_size(size_kind, ahead):
    return {"below_ahead": max(ahead - 0.5, 0.3), "between": ahead + 0.4, "above": ahead + 3.0}[size_kind]


def oracle(tier, side, where, size_kind, aggr, ahead):
    """(filled, fill time)."""
    q = print_size(size_kind, ahead)
    reaches = where in ("through", "at")
    t_print = T0 + 2500 * MS
    if tier == 0:
        return 1.0, T0 + 500 * MS
    if tier == 1:
        return (1.0, t_print) if where == "through" else (0.0, None)
    if tier == 2:
        return (1.0, T0 + 3 * SEC) if reaches else (0.0, None)
    if tier == 3:
        return (1.0, t_print) if reaches else (0.0, None)
    if tier == 4:
        return (min(1.0, q), t_print) if reaches else (0.0, None)
    if where == "through":
        return 1.0, t_print
    if where == "at" and aggr in ("hits_us", "unknown"):
        got = min(1.0, max(q - ahead, 0.0))
        return (got, t_print) if got > 0 else (0.0, None)
    return 0.0, None


@pytest.mark.parametrize("combo", GRID, ids=["-".join(map(str, c)) for c in GRID])
def test_tier_grid(combo):
    tier, side, where, size_kind, aggr, ahead = combo
    s = 1 if side == "buy" else -1
    px = {"through": L - s * 3, "at": L, "away": L + s * 3}[where]
    aggressor = {"hits_us": "sell" if side == "buy" else "buy", "same_side": side, "unknown": ""}[aggr]
    level = [(L, ahead)] if ahead > 0 else []
    if side == "buy":
        bk = book(T0, level + [(9900.0, 5)], [(10100.0, 5)])
    else:
        bk = book(T0, [(9900.0, 5)], level + [(10100.0, 5)])
    fm = {"tier": tier}
    if tier >= 5:
        fm["cancel_stance"] = "none"
    if tier == 6:
        fm["impact"] = {"kind": "linear_temporary", "k": 0.0, "basis": "opposite_best"}
    if tier == 2:
        fm["bar_ns"] = 1 * SEC
    market = [bk, trade(T0 + 2500 * MS, px, print_size(size_kind, ahead), aggressor)]
    obs, refused = run(inp(market, [place(T0 + 500 * MS, "o1", side, "limit", 1.0, px=L)], fill_model=fm,
                           end_t=T0 + 10 * SEC))
    assert refused is None, refused
    exp_q, exp_t = oracle(*combo)
    assert filled(obs, "o1") == pytest.approx(exp_q, abs=1e-12)
    if exp_q > 0:
        assert first_t(obs, "o1") == exp_t
        assert avg_px(obs, "o1") == L  # a resting order fills at its limit
        assert all(f["liq"] == "maker" for f in obs["fills"] if f["ref"] == "o1")
    expect_status = "filled" if exp_q >= 1.0 - 1e-12 else "open"
    assert obs["orders"]["o1"]["status"] == expect_status
