"""The venue's remaining paths, each with its expected outcome written from
the venue docstring: book deltas, the next-bar-open reference, bar-triggered
stops (tier 2), amends that post-only forbids, reduce-only at fill time,
venue-only order types, unknown extra keys, IOC / FOK without a book, OCO
partners that arrive after the other leg filled, the numeric tier report
(C2-5), and the socket's refusals of malformed construction.

Not enumerated: every delta sequence (a delta at our price goes through the
same stance update as a snapshot of that level: test_i2_stance_grid.py).
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, BookDeltaEvent, BookSnapshotEvent, OrderRequest
from bot.bt.costs import CostSchedule
from bot.bt.fill import FillSpec, ImpactSpec, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.orders.errors import ExecutionModelError
from i2_gridkit import MS, SEC, T0, avg_px, book, filled, first_t, inp, place, run, trade

PRODUCT = Product("FX_BTC_JPY", "bitflyer_cfd", 1.0, 0.01, 1e-8, "JPY", True)
COSTS = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="edge tests", spread=2.0)
RULES = VenueRules(off_tick="reject", below_min_qty="reject", post_only="reject_if_crossing",
                   market_remainder="cancel", market_ref="next_bar_open")


def venue(fill, rules=RULES):
    return SimVenue(product=PRODUCT, rules=rules, fill=fill, costs=COSTS, faults=FaultPlan(()), l3=None)


def names(reports):
    return [(type(r).__name__, r.client_order_id, getattr(r, "reason", None)) for r in reports]


def test_book_delta_updates_the_level_and_the_cap():
    v = venue(FillSpec(tier=5, cancel_stance="snapshot_cap"))
    v.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(100.0, 5.0)], asks=[(110.0, 5.0)]), T0)
    v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=100.0, client_order_id="o"), T0 + 1)
    assert v.queue_ahead("o")["size"] == 5.0
    v.on_market_event(BookDeltaEvent(received_time_ns=T0 + 2, side="bid", price=99.0, size=3.0), T0 + 2)
    assert v.queue_ahead("o")["size"] == 5.0  # another level: no change
    v.on_market_event(BookDeltaEvent(received_time_ns=T0 + 3, side="bid", price=100.0, size=2.0), T0 + 3)
    assert v.queue_ahead("o")["size"] == 2.0
    assert v.book.bids == [[100.0, 2.0], [99.0, 3.0]]
    v.on_market_event(BookDeltaEvent(received_time_ns=T0 + 4, side="bid", price=100.0, size=0.0), T0 + 4)
    assert v.book.bids == [[99.0, 3.0]] and v.queue_ahead("o")["size"] == 0.0


def test_next_bar_open_prices_a_market_order_from_the_next_bar():
    bar = lambda end, o: {"t": end, "type": "bar", "span_ns": SEC, "o": o, "h": o + 5, "l": o - 5, "c": o, "v": 1.0}  # noqa: E731
    market = [bar(T0 + 1 * SEC, 100.0), bar(T0 + 2 * SEC, 104.0), bar(T0 + 3 * SEC, 108.0)]
    rules = {"off_tick": "reject", "below_min_qty": "reject", "market_remainder": "cancel", "mark": "last_trade",
             "market_ref": "next_bar_open"}
    costs = {"maker_rate": 0.0, "taker_rate": 0.0, "source": "edge", "spread": 2.0}
    # sent exactly at a bar's start (T0+1s): that bar's prints came first, so the next bar (start 2s) prices it
    obs, refused = run(inp(market, [place(T0 + 1 * SEC, "o1", "buy", "market", 1.0)], rules=rules, costs=costs,
                           fill_model={"tier": 4}, end_t=T0 + 5 * SEC))
    assert refused is None, refused
    assert avg_px(obs, "o1") == 108.0 + 1.0 and first_t(obs, "o1") == T0 + 3 * SEC
    obs, _ = run(inp(market, [place(T0 + 1 * SEC + 1, "o1", "sell", "market", 1.0)], rules=rules, costs=costs,
                     fill_model={"tier": 4}, end_t=T0 + 5 * SEC))
    assert avg_px(obs, "o1") == 108.0 - 1.0


def test_bar_triggered_stop_fills_at_trigger_or_gap_open():
    v = venue(FillSpec(tier=2, bar_ns=SEC))
    v.on_order(OrderRequest(side="buy", order_type="stop", size=1.0, trigger_price=105.0, client_order_id="s1"), T0)
    v.on_order(OrderRequest(side="buy", order_type="stop", size=1.0, trigger_price=103.0, client_order_id="s2"), T0)
    rep = v.on_market_event(BarEvent(received_time_ns=T0 + 2 * SEC, start_time_ns=T0 + SEC, open=104.0, high=107.0,
                                     low=103.0, close=106.0, volume=1.0), T0 + 2 * SEC)
    fills = {r.client_order_id: r.price for r in rep if type(r).__name__ == "Fill"}
    assert fills == {"s1": 105.0, "s2": 104.0}  # s2: the bar opened above its trigger


def test_post_only_amend_that_would_take_is_rejected():
    rules = {"off_tick": "reject", "below_min_qty": "reject", "post_only": "reject_if_crossing",
             "market_remainder": "cancel", "mark": "last_trade"}
    actions = [place(T0 + 1 * MS, "o1", "buy", "limit", 1.0, px=9990.0, post_only=True),
               {"t": T0 + 2 * MS, "op": "amend", "ref": "o1", "px": 10001.0, "qty": None}]
    obs, refused = run(inp([book(T0, [(9999, 5)], [(10001, 5)])], actions, rules=rules))
    assert refused is None, refused
    assert obs["orders"]["o1"]["status"] == "open" and filled(obs, "o1") == 0.0


def test_reduce_only_resting_order_cancelled_when_the_position_is_gone():
    actions = [place(T0 + 1 * MS, "o0", "buy", "market", 1.0),
               place(T0 + 2 * MS, "o1", "sell", "limit", 1.0, px=10050.0, reduce_only=True),
               place(T0 + 3 * MS, "o2", "sell", "market", 1.0)]  # closes the position first
    market = [book(T0, [(9999, 5)], [(10001, 5)]), trade(T0 + 10 * MS, 10060, 5, "buy")]
    obs, refused = run(inp(market, actions))
    assert refused is None, refused
    assert obs["orders"]["o1"]["status"] == "canceled" and filled(obs, "o1") == 0.0
    assert obs["account"]["position"] == 0.0


@pytest.mark.parametrize("otype,extra,expect", [
    ("liquidation", (), "liquidation_is_venue_only"),
    ("teleport", (), "unknown_order_type:teleport"),
    ("limit", (("weird", 1),), "unknown_extra:['weird']"),
])
def test_venue_refuses_malformed_requests(otype, extra, expect):
    v = venue(FillSpec(tier=4))
    v.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(100.0, 5.0)], asks=[(110.0, 5.0)]), T0)
    rep = v.on_order(OrderRequest(side="buy", order_type=otype, size=1.0, price=100.0, client_order_id="x",
                                  extra=extra), T0 + 1)
    assert names(rep) == [("Reject", "x", expect)]


def test_ioc_fok_without_a_book_are_rejected():
    v = venue(FillSpec(tier=4))
    for tif in ("IOC", "FOK"):
        rep = v.on_order(OrderRequest(side="buy", order_type="limit", size=1.0, price=100.0, client_order_id=tif,
                                      time_in_force=tif), T0)
        assert names(rep) == [("Reject", tif, "ioc_fok_need_a_book")]


def test_oco_partner_arriving_after_the_other_filled_is_rejected():
    v = venue(FillSpec(tier=4))
    v.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(100.0, 5.0)], asks=[(110.0, 5.0)]), T0)
    rep = v.on_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id="a",
                                  extra=(("oco", "b"),)), T0 + 1)
    assert [n[0] for n in names(rep)] == ["Ack", "Fill"]
    rep = v.on_order(OrderRequest(side="sell", order_type="limit", size=1.0, price=120.0, client_order_id="b",
                                  extra=(("oco", "a"),)), T0 + 2)
    assert names(rep) == [("Reject", "b", "oco_partner_filled")]


def test_tier_numbers():
    for tier in range(7):
        spec = FillSpec(tier=tier, cancel_stance="none" if tier >= 5 else None,
                        impact=None if tier != 6 else ImpactSpec(kind="linear_temporary", basis="mid", k=0.0))
        assert venue(spec).tier_numbers() == {"mechanism": 6, "selected": tier}


def test_construction_refusals():
    with pytest.raises(ExecutionModelError):
        SimVenue(product=PRODUCT, rules=RULES, fill=FillSpec(tier=4), costs=COSTS, faults=(), l3=None)
    with pytest.raises(TypeError):
        SimVenue(product=PRODUCT, rules=RULES, fill=FillSpec(tier=4), costs=COSTS, l3=None)  # faults required
    with pytest.raises(ExecutionModelError):
        FillSpec(tier=5)  # a queue tier needs its stance
    with pytest.raises(ExecutionModelError):
        FillSpec(tier=3, cancel_stance="snapshot_cap")  # a stance other than "none" claims an effect tier 3 lacks
    with pytest.raises(ExecutionModelError):
        FillSpec(tier=6)  # an impact tier needs its function
