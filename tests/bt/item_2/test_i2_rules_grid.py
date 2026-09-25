"""Adversarial grid: the size and price rules (C2-3) -- side x price offset
from the tick grid x off_tick policy x size x below_min_qty policy x off_step
policy: 2 x 5 x 3 x 5 x 2 x 3 = 900 runs, all run. The oracle is written from
the rule texts with `decimal` arithmetic on the numbers' shortest text: sizes
first (below the minimum, then off the step), then the price (off the tick);
a policy the situation needs and the run did not declare refuses the run; a
declared "reject" rejects the order; round_passive floors a buy / ceils a
sell to the tick; round_down floors the size to the step (below the minimum
after that: rejected), and the order that fills its floored size in full is
reported "filled" (the venue closes it with reason rounded_size_filled). An accepted order
rests (far from the book) and a later print at the expected price fills it,
so the fill shows the price and size the venue used.

Product: an FX-like tick 0.001, min size 1000, step 1 (floats whose binary
value is not the decimal one). Not enumerated here: trigger prices of stops
(covered for tick by the scenes and the order grid), price limits and hours
(test_i2_hours_grid.py).
"""
from __future__ import annotations

import itertools
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

import pytest

from i2_gridkit import MS, T0, avg_px, book, filled, inp, place, run, trade

FX = {"symbol": "USDJPY", "venue": "fx", "tick": 0.001, "min_qty": 1000.0, "qty_step": 1.0, "quote_ccy": "JPY",
      "margin": True}
SIDES = ("buy", "sell")
OFFSETS = ("0", "0.0003", "0.0005", "0.0007", "0.000999")
TICK_POLICY = ("reject", "round_passive", None)
SIZES = ("999", "1000", "1000.5", "2000", "999.5")
MIN_POLICY = ("reject", None)
STEP_POLICY = ("reject", "round_down", None)
GRID = list(itertools.product(SIDES, OFFSETS, TICK_POLICY, SIZES, MIN_POLICY, STEP_POLICY))
BASE = {"buy": Decimal("149.900"), "sell": Decimal("150.100")}


def test_grid_size():
    assert len(GRID) == 900


def oracle(side, off, tick_pol, size, min_pol, step_pol):
    """("refused", why) | ("rejected", why) | ("accepted", price, size)."""
    q = Decimal(size)
    if q < 1000:
        if min_pol is None:
            return ("refused", "below_min_qty")
        return ("rejected", "below_min_qty")
    if q % 1 != 0:
        if step_pol is None:
            return ("refused", "off_step")
        if step_pol == "reject":
            return ("rejected", "off_step")
        q = q.to_integral_value(rounding=ROUND_FLOOR)
        if q < 1000:
            return ("rejected", "below_min_qty_after_rounding")
    p = BASE[side] + Decimal(off)
    if p % Decimal("0.001") != 0:
        if tick_pol is None:
            return ("refused", "off_tick")
        if tick_pol == "reject":
            return ("rejected", "off_tick")
        n = (p / Decimal("0.001")).to_integral_value(rounding=ROUND_FLOOR if side == "buy" else ROUND_CEILING)
        p = n * Decimal("0.001")
    return ("accepted", float(p), float(q))


@pytest.mark.parametrize("combo", GRID, ids=["-".join(map(str, c)) for c in GRID])
def test_rules_grid(combo):
    side, off, tick_pol, size, min_pol, step_pol = combo
    rules = {"post_only": "reject_if_crossing", "market_remainder": "cancel", "mark": "last_trade"}
    if tick_pol:
        rules["off_tick"] = tick_pol
    if min_pol:
        rules["below_min_qty"] = min_pol
    if step_pol:
        rules["off_step"] = step_pol
    px = float(BASE[side] + Decimal(off))
    exp = oracle(*combo)
    fill_px = exp[1] if exp[0] == "accepted" else float(BASE[side])
    market = [book(T0, [(149.0, 1e6)], [(151.0, 1e6)]),
              trade(T0 + 10 * MS, fill_px, 1e6, "sell" if side == "buy" else "buy")]
    obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", side, "limit", float(size), px=px)], product=FX,
                           rules=rules))
    if exp[0] == "refused":
        assert obs is None and "RuleNotDeclaredError" in refused and exp[1] in refused, refused
        return
    assert refused is None, refused
    if exp[0] == "rejected":
        assert obs["orders"]["o1"]["status"] == "rejected"
        assert filled(obs, "o1") == 0.0
        return
    assert obs["orders"]["o1"]["status"] == "filled"
    assert filled(obs, "o1") == exp[2]
    assert avg_px(obs, "o1") == exp[1]
