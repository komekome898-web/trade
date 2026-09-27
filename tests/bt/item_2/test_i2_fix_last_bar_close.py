"""D-1 (K1 stage A, 2026-09-27): the venue rule market_ref = "last_bar_close".

Rule (bot.bt.fill.venue, bot.bt.orders.rules): with no book, a market order is priced at the close of the last
bar the venue has seen when the order arrives, +/- half the declared spread, filled in full as taker; no bar
yet -> Canceled "no_price_yet". Every expected value below is written from that rule text."""
from __future__ import annotations

import pytest

from bot.bt.core import Ack, BarEvent, Canceled, Fill, OrderRequest
from bot.bt.costs import CostSchedule
from bot.bt.fill import FillSpec, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.orders.errors import RuleNotDeclaredError, RuleValueError
from bot.bt.orders.rules import POLICY_VALUES

NS = 10**9


def venue(spread=0.0, ref="last_bar_close", tier=2):
    return SimVenue(product=Product("X", "v", 0.5, 1.0, 1.0, "USD", True), rules=VenueRules(market_ref=ref),
                    fill=FillSpec(tier=tier), costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="test",
                                                                 spread=spread),
                    faults=FaultPlan(()), l3=None)


def bar(i, o, h, l, c):
    return BarEvent(received_time_ns=(i + 1) * 60 * NS, start_time_ns=i * 60 * NS, open=o, high=h, low=l, close=c,
                    volume=1.0)


def market(coid, side, size=1.0):
    return OrderRequest(side=side, order_type="market", size=size, client_order_id=coid)


def test_the_rule_is_declarable_and_other_values_are_refused():
    assert "last_bar_close" in POLICY_VALUES["market_ref"]
    VenueRules(market_ref="last_bar_close")
    with pytest.raises(RuleValueError):
        VenueRules(market_ref="bar_close")


def test_no_bar_yet_cancels():
    v = venue()
    out = v.on_order(market("a", "buy"), 5 * NS)
    assert [type(r) for r in out] == [Ack, Canceled] and out[1].reason == "no_price_yet"


def test_close_of_the_last_bar_seen_plus_half_the_spread():
    v = venue(spread=2.0)
    assert v.on_market_event(bar(0, 100, 103, 99, 101.5), 60 * NS) == []
    out = v.on_order(market("b1", "buy", 3.0), 60 * NS)  # the same instant as the bar: priced by that bar
    assert [type(r) for r in out] == [Ack, Fill]
    assert (out[1].price, out[1].size, out[1].liquidity) == (102.5, 3.0, "taker")  # 101.5 + 2/2
    out = v.on_order(market("s1", "sell"), 90 * NS)  # later, no new bar: still the last bar seen
    assert out[1].price == 100.5  # 101.5 - 2/2
    v.on_market_event(bar(1, 101.5, 110, 101, 108.0), 120 * NS)
    out = v.on_order(market("b2", "buy"), 120 * NS)
    assert out[1].price == 109.0  # the new bar's close 108 + 1
    assert v.used["spread"] == 3


def test_the_order_does_not_wait_for_the_next_bar():
    # next_bar_open would hold the order for the NEXT bar's open; last_bar_close fills at the arrival
    v = venue(ref="next_bar_open")
    v.on_market_event(bar(0, 100, 103, 99, 101.5), 60 * NS)
    out = v.on_order(market("a", "buy"), 60 * NS)
    assert [type(r) for r in out] == [Ack]
    assert v.on_market_event(bar(1, 102, 104, 101, 103), 120 * NS) == []  # starts AT the arrival: not after it
    got = v.on_market_event(bar(2, 105, 106, 104, 105.5), 180 * NS)
    assert [(type(r), r.price) for r in got] == [(Fill, 105.0)]  # the open of the first bar starting after it
    w = venue()
    w.on_market_event(bar(0, 100, 103, 99, 101.5), 60 * NS)
    out = w.on_order(market("a", "buy"), 60 * NS)
    assert [(type(r), getattr(r, "price", None)) for r in out] == [(Ack, None), (Fill, 101.5)]
    assert w.on_market_event(bar(1, 102, 104, 101, 103), 120 * NS) == []


def test_undeclared_spread_stops_the_run():
    v = SimVenue(product=Product("X", "v", 0.5, 1.0, 1.0, "USD", True), rules=VenueRules(market_ref="last_bar_close"),
                 fill=FillSpec(tier=2), costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="test"),
                 faults=FaultPlan(()), l3=None)
    v.on_market_event(bar(0, 100, 103, 99, 101.5), 60 * NS)
    with pytest.raises(Exception, match="spread"):
        v.on_order(market("a", "buy"), 60 * NS)


def test_undeclared_rule_stops_the_run():
    v = SimVenue(product=Product("X", "v", 0.5, 1.0, 1.0, "USD", True), rules=VenueRules(),
                 fill=FillSpec(tier=2), costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="t", spread=0.0),
                 faults=FaultPlan(()), l3=None)
    v.on_market_event(bar(0, 100, 103, 99, 101.5), 60 * NS)
    with pytest.raises(RuleNotDeclaredError):
        v.on_order(market("a", "buy"), 60 * NS)
