"""Adversarial grid: costs with no default (C2-10).

1. Required fields: every subset of {maker_rate, taker_rate, source} left out
   (8 subsets) x source in {"text", "", "   "}: the schedule is built only
   when all three are given and the source is not blank.
2. Met components: {spread, funding, swap} x declared / not declared x the run
   meets it / does not (12 runs): refused exactly when met and not declared.
3. Fee arithmetic: liquidity {maker, taker} x rate {-0.0002, 0, 0.0005} x
   price {10001, 9990.5} x size {0.01, 1, 3.7} (36 runs): the fee of the fill
   = rate * price * size, a rebate negative.
4. The tiered order fee: 300 seeded random splits of an order's notional into
   1-6 fills: the fees of the parts add up to the table's fee for the total.
5. A fee in a quote currency other than the account's is converted at the
   fill's time; without a rate the run is refused.

Not enumerated: funding / swap amounts (account grid), fee tables with more
tiers (the table logic is one lookup; the split test runs every tier).
"""
from __future__ import annotations

import itertools
import random

import pytest

from bot.bt.core import FillNotice
from bot.bt.costs import (
    CostNotDeclaredError,
    CostSchedule,
    FeeTable,
    FundingRule,
    FxPoint,
    FxRateMissingError,
    FxRates,
    ScheduleCostModel,
    SwapRule,
)
from bot.bt.orders import Product
from i2_gridkit import MS, SEC, T0, book, inp, place, run, trade

REQ = ("maker_rate", "taker_rate", "source")
SUBSETS = [frozenset(c) for n in range(4) for c in itertools.combinations(REQ, n)]
SOURCES = ("grid: stated", "", "   ")
GRID1 = list(itertools.product(SUBSETS, SOURCES))


def test_grid_sizes():
    assert len(GRID1) == 24


@pytest.mark.parametrize("combo", GRID1, ids=[f"{sorted(c[0])}-{c[1]!r}" for c in GRID1])
def test_required_fields(combo):
    missing, source = combo
    kw = {"maker_rate": 0.0002, "taker_rate": 0.0005, "source": source}
    for k in missing:
        del kw[k]
    if missing:
        with pytest.raises(TypeError):
            CostSchedule(**kw)
    elif not source.strip():
        with pytest.raises(CostNotDeclaredError):
            CostSchedule(**kw)
    else:
        s = CostSchedule(**kw)
        assert s.declared()["maker_rate"] == 0.0002


BASE_COSTS = {"maker_rate": 0.0, "taker_rate": 0.0, "source": "grid: stated"}
GRID2 = list(itertools.product(("spread", "funding", "swap"), (True, False), (True, False)))


@pytest.mark.parametrize("combo", GRID2, ids=["-".join(map(str, c)) for c in GRID2])
def test_met_components(combo):
    comp, declared, met = combo
    costs = dict(BASE_COSTS)
    rules = {"off_tick": "reject", "below_min_qty": "reject", "market_remainder": "cancel", "mark": "last_trade"}
    market = [trade(T0, 10000, 1, "buy")]
    if comp != "spread" or not met:
        market.insert(0, book(T0, [(9999, 5)], [(10001, 5)]))
    if comp == "spread":
        rules["market_ref"] = "last_trade"
        if declared:
            costs["spread"] = 2.0
    elif comp == "funding":
        if declared:
            costs["funding"] = "apply_events"
        if met:
            market.append({"t": T0 + 3600 * SEC, "type": "funding", "rate": 0.0001, "mark": 10000.0})
    else:
        if declared:
            costs["swap"] = {"long_credit_per_unit_per_day": 0.01, "short_credit_per_unit_per_day": -0.02}
        if met:
            market.append({"t": T0 + 3600 * SEC, "type": "rollover"})
    obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", "buy", "market", 1.0)], rules=rules, costs=costs,
                           end_t=T0 + 7200 * SEC))
    if met and not declared:
        assert obs is None and "CostNotDeclaredError" in refused and comp in refused, refused
    else:
        assert refused is None, refused


GRID3 = list(itertools.product(("maker", "taker"), (-0.0002, 0.0, 0.0005), (10001.0, 9990.5), (0.01, 1.0, 3.7)))
BTC = Product("FX_BTC_JPY", "bitflyer_cfd", 0.5, 0.01, 1e-8, "JPY", True)


@pytest.mark.parametrize("combo", GRID3, ids=["-".join(map(str, c)) for c in GRID3])
def test_fee_arithmetic(combo):
    liq, rate, px, size = combo
    s = CostSchedule(maker_rate=rate if liq == "maker" else 0.0003, taker_rate=rate if liq == "taker" else 0.0003,
                     source="grid")
    m = ScheduleCostModel(s, product=BTC, account_currency="JPY", fx=None)
    fee = m.cost(FillNotice(client_order_id="o", price=px, size=size, side="buy", liquidity=liq, venue_time_ns=T0))
    assert fee == pytest.approx(rate * px * size, rel=1e-15, abs=1e-15)


TABLE = FeeTable(((50000, 55), (100000, 99), (200000, 115), (500000, 275), (None, 535)))


def table_fee(n):
    for up, f in ((50000, 55), (100000, 99), (200000, 115), (500000, 275)):
        if n <= up:
            return f
    return 535


@pytest.mark.parametrize("seed", range(300))
def test_tiered_fee_split_invariance(seed):
    rng = random.Random(seed)
    parts = [rng.choice([100, 200, 300, 500, 1000]) for _ in range(rng.randint(1, 6))]
    px = rng.choice([150.0, 480.0, 1500.0])
    s = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="grid", fee_table=TABLE)
    m = ScheduleCostModel(s, product=BTC, account_currency="JPY", fx=None)
    total = sum(m.cost(FillNotice(client_order_id="o", price=px, size=float(q), side="buy", liquidity="taker",
                                  venue_time_ns=T0 + i)) for i, q in enumerate(parts))
    assert total == table_fee(px * sum(parts))


def test_fee_converted_to_account_currency():
    eur = Product("EURUSD", "fx", 1e-5, 1000.0, 1.0, "USD", True)
    s = CostSchedule(maker_rate=0.0, taker_rate=0.001, source="grid")
    fx = FxRates([FxPoint(T0, "USDJPY", 150.0), FxPoint(T0 + 10, "USDJPY", 160.0)])
    m = ScheduleCostModel(s, product=eur, account_currency="JPY", fx=fx)
    fee = m.cost(FillNotice(client_order_id="o", price=1.1, size=1000.0, side="buy", liquidity="taker",
                            venue_time_ns=T0 + 5))
    assert fee == pytest.approx(0.001 * 1.1 * 1000.0 * 150.0)
    m2 = ScheduleCostModel(s, product=eur, account_currency="JPY", fx=None)
    with pytest.raises(FxRateMissingError):
        m2.cost(FillNotice(client_order_id="o", price=1.1, size=1000.0, side="buy", liquidity="taker",
                           venue_time_ns=T0))
    with pytest.raises(FxRateMissingError):
        FxRates([FxPoint(T0 + 100, "USDJPY", 150.0)]).rate("USDJPY", T0)


def test_components_have_no_value_until_declared():
    s = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="grid")
    for comp in ("spread", "funding", "swap", "fee_table"):
        with pytest.raises(CostNotDeclaredError):
            s.need(comp)
    s2 = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="grid", spread=0.0, funding=FundingRule("event_mark"),
                      swap=SwapRule(0.0, 0.0), fee_table=FeeTable(((None, 0.0),)))
    assert s2.need("spread") == 0.0


@pytest.mark.parametrize("bad", [1.0, -1.0, float("nan"), float("inf"), True, "0.001"])
def test_bad_rates_refused(bad):
    with pytest.raises(CostNotDeclaredError):
        CostSchedule(maker_rate=bad, taker_rate=0.0, source="grid")
