"""Known-answer scenes for the event reference (bot.bt.reference.event_sim).

Every expected value is worked out by hand in the comment next to it from the
rules in src/bot/bt/reference/SPEC.md section 2; none is read back from a run.
"""
from __future__ import annotations

import pytest

from i4ref_kit import (F, Cancel, Limit, Market, Script, base_params, book, clock, make_event,
                       simulate, trade)


def test_market_next_trade_with_latency_and_taker_fee():
    # order sent at t=100 (delivery of seq 1), arrives at 150; the next trade
    # after arrival is t=200 @101 -> fill 1 @101, fee 101*0.001 = 0.101.
    # cash = -101 - 0.101 = -101.101; last mark 103 -> equity 1.899,
    # unrealized (103-101)*1 = 2. Notes arrive 10 ns after their exchange time.
    ev = [trade(100, 1, 100), trade(200, 2, 101), trade(300, 3, 103)]
    s = Script({("event", 1): [Market("m1", "buy", 1)]})
    r = simulate(ev, s, **base_params(taker_rate="0.001", order_latency_ns=50, notify_latency_ns=10))
    assert [(f.t_exch, f.t_recv, f.price, f.qty, f.fee, f.liquidity) for f in r.fills] == [
        (200, 210, F(101), F(1), F("0.101"), "taker")]
    assert r.cash == F("-101.101") and r.position == 1
    assert r.unrealized == 2 and r.equity == F("1.899") and r.fees == F("0.101")
    # delivery order: seq1@100, ack@160, seq2@200, fill@210, seq3@300
    assert [(t, k) for t, _w, _id, k in r.deliveries] == [
        (100, "trade"), (160, "ack"), (200, "trade"), (210, "fill"), (300, "trade")]


@pytest.mark.parametrize("cross,fill_t", [("strict", 30), ("touch", 20)])
def test_resting_limit_strict_vs_touch_fills_at_limit_with_rebate(cross, fill_t):
    # buy limit 100 rests from t=0. Trades 101 @10, 100 @20, 99 @30.
    # strict: needs a print < 100 -> t=30; touch: print <= 100 -> t=20.
    # Fill price is the limit 100 in both (never the better 99).
    # maker rate -0.0002 -> fee -0.02, cash = -100 + 0.02 = -99.98.
    ev = [clock(0, 0), trade(10, 1, 101), trade(20, 2, 100), trade(30, 3, 99)]
    s = Script({("event", 0): [Limit("l1", "buy", 1, 100, False)]})
    r = simulate(ev, s, **base_params(maker_rate="-0.0002", limit_cross=cross))
    assert [(f.t_exch, f.price, f.fee, f.liquidity) for f in r.fills] == [
        (fill_t, F(100), F("-0.02"), "maker")]
    assert r.cash == F("-99.98")


def test_post_only_rejected_when_crossing_book_and_rests_otherwise():
    # book bid 99 / ask 100. post-only buy @100 would take -> rejected.
    # post-only buy @99 does not cross -> ack and rests (no fill, no trade).
    ev = [book(0, 0, [(99, 1)], [(100, 1)])]
    s = Script({("event", 0): [Limit("a", "buy", 1, 100, True), Limit("b", "buy", 1, 99, True)]})
    r = simulate(ev, s, **base_params(liquidity="book"))
    kinds = [(n.cid, n.kind, n.reason) for n in r.notes]
    assert kinds == [("a", "reject", "post_only_would_cross"), ("b", "ack", None)]
    assert r.fills == [] and [o["cid"] for o in r.open_orders_at_end] == ["b"]


def test_market_walks_book_and_depth_is_consumed_within_a_snapshot():
    # asks 0.5@100, 1@101. m1 buy 1 -> 0.5@100 + 0.5@101 (avg 100.5).
    # m2 buy 1 on the same snapshot -> remaining 0.5@101, then 0.5 expires.
    ev = [book(0, 0, [(99, 1)], [(100, "0.5"), (101, 1)])]
    s = Script({("event", 0): [Market("m1", "buy", 1), Market("m2", "buy", 1)]})
    r = simulate(ev, s, **base_params(liquidity="book"))
    assert [(f.cid, f.price, f.qty) for f in r.fills] == [
        ("m1", F(100), F("0.5")), ("m1", F(101), F("0.5")), ("m2", F(101), F("0.5"))]
    exp = [n for n in r.notes if n.kind == "expired"]
    assert [(n.cid, n.qty, n.reason) for n in exp] == [("m2", F("0.5"), "insufficient_depth")]
    assert r.position == F("1.5") and r.avg_cost == F("302") / 3  # (50+50.5+50.5)/1.5


def test_marketable_limit_takes_up_to_limit_then_rests():
    # asks 1@100, 1@102. buy limit 2 @101: takes 1@100 (taker), rest 1 rests @101.
    ev = [book(0, 0, [(99, 1)], [(100, 1), (102, 1)]), trade(10, 1, 100, 5)]
    s = Script({("event", 0): [Limit("x", "buy", 2, 101, False)]})
    r = simulate(ev, s, **base_params(liquidity="book"))
    # then the trade @100 (< 101, strict) fills the resting 1 @101 as maker
    assert [(f.price, f.qty, f.liquidity) for f in r.fills] == [
        (F(100), F(1), "taker"), (F(101), F(1), "maker")]


@pytest.mark.parametrize("trade_t,expect", [(50, "filled"), (150, "cancelled")])
def test_cancel_race_decided_by_arrival_time(trade_t, expect):
    # limit buy 100 at t=0 (arrives 0). cancel sent at t=10 arrives at 110.
    # trade @99 at t=50 fills before the cancel -> cancel_reject(not_open);
    # trade at t=150 comes after -> cancel_ack at 110, no fill.
    ev = [clock(0, 0), clock(10, 1), trade(trade_t, 2, 99)]
    s = Script({("event", 0): [Limit("l", "buy", 1, 100, False)], ("event", 1): [Cancel("l")]})
    r = simulate(ev, s, **base_params(cancel_latency_ns=100))
    kinds = [n.kind for n in r.notes]
    if expect == "filled":
        assert kinds == ["ack", "fill", "cancel_reject"] and r.position == 1
    else:
        assert kinds == ["ack", "cancel_ack"] and r.position == 0 and r.fills == []


@pytest.mark.parametrize("side,pay", [("buy", "-2.2"), ("sell", "2.2")])
def test_funding_paid_by_long_received_by_short(side, pay):
    # 2 units filled @100 at t=10; funding at t=20, rate 0.01, mark 110:
    # payment = -position*110*0.01 -> long pays 2.2, short receives 2.2.
    ev = [clock(0, 0), trade(10, 1, 100, 5),
          make_event("funding", 20, 20, 2, rate="0.01", price=110)]
    s = Script({("event", 0): [Market("m", side, 2)]})
    r = simulate(ev, s, **base_params())
    assert r.funding == F(pay)
    assert r.funding_payments == [(20, F(110), F("0.01"), F(pay))]


def test_order_rule_rejections():
    ev = [clock(0, 0), trade(10, 1, 100)]
    s = Script({("event", 0): [
        Limit("tick", "buy", 1, "100.5", False),   # tick 1 -> price_off_tick
        Market("lot", "buy", "0.015"),            # lot 0.01 -> qty_off_lot
        Market("min", "buy", "0.005"),            # lot 0.001, min 0.01 below -> see below
        Market("ok", "buy", 1),
        Market("ok", "buy", 1),                   # same cid again -> duplicate_cid
    ]})
    r = simulate(ev, s, **base_params(lot_size="0.001", min_qty="0.01"))
    rej = [(n.cid, n.reason) for n in r.notes if n.kind == "reject"]
    # with lot 0.001: 0.015 is on the lot grid and >= 0.01 -> accepted;
    # 0.005 is on the grid but below min -> qty_below_min.
    assert rej == [("tick", "price_off_tick"), ("min", "qty_below_min"), ("ok", "duplicate_cid")]
    r2 = simulate(ev, Script({("event", 0): [Market("lot", "buy", "0.015")]}), **base_params())
    assert [(n.cid, n.reason) for n in r2.notes] == [("lot", "qty_off_lot")]


def test_trade_qty_shared_by_price_then_time_priority():
    # buy limits a@101 (1) and b@100 (1); trade @99 qty 1.5:
    # a first (better price) takes 1, b takes the remaining 0.5.
    ev = [clock(0, 0), trade(10, 1, 99, "1.5")]
    s = Script({("event", 0): [Limit("b", "buy", 1, 100, False), Limit("a", "buy", 1, 101, False)]})
    r = simulate(ev, s, **base_params(limit_fill_qty="trade_qty"))
    assert [(f.cid, f.price, f.qty) for f in r.fills] == [("a", F(101), F(1)), ("b", F(100), F("0.5"))]
    r2 = simulate(ev, Script({("event", 0): [Limit("b", "buy", 1, 100, False),
                                             Limit("a", "buy", 1, 101, False)]}),
                  **base_params(limit_fill_qty="full"))
    assert [(f.cid, f.qty) for f in r2.fills] == [("a", F(1)), ("b", F(1))]


def test_position_flip_average_cost_and_realized():
    # buy 1 @100, sell 3 @110 -> realized (110-100)*1 = 10, position -2, avg 110.
    # buy 2 @105 -> realized += (105-110)*2*(-1) = 10 -> 20, flat.
    ev = [clock(0, 0), trade(10, 1, 100), clock(20, 2), trade(30, 3, 110), clock(40, 4), trade(50, 5, 105)]
    s = Script({("event", 0): [Market("a", "buy", 1)], ("event", 2): [Market("b", "sell", 3)],
                ("event", 4): [Market("c", "buy", 2)]})
    r = simulate(ev, s, **base_params())
    assert r.realized == 20 and r.position == 0 and r.avg_cost is None
    assert r.cash == F(-100 + 330 - 210)


def test_same_time_trade_does_not_fill_an_order_arriving_at_that_time():
    # seq 1 and seq 2 are both at exchange time 100 (seq 2 delivered at 105).
    # The order sent on delivery of seq 1 at t=100 arrives at 100, after all
    # exchange events at 100 -> it cannot fill on seq 2 (@90); it fills on
    # the next trade at 200 (@95).
    ev = [trade(100, 1, 100), trade(100, 2, 90, recv=105), trade(200, 3, 95)]
    s = Script({("event", 1): [Market("m", "buy", 1)]})
    r = simulate(ev, s, **base_params())
    assert [(f.t_exch, f.price) for f in r.fills] == [(200, F(95))]


def test_required_parameters_have_no_defaults():
    ev = [trade(1, 1, 100)]
    p = base_params()
    for k in list(p):
        q = dict(p)
        del q[k]
        with pytest.raises(TypeError):
            simulate(ev, lambda c: None, **q)


@pytest.mark.parametrize("bad", [1.0, True, "5"])
def test_times_must_be_int_nanoseconds(bad):
    with pytest.raises(TypeError):
        trade(bad, 1, 100)


def test_refuses_recv_before_exch_and_crossed_book():
    with pytest.raises(ValueError):
        trade(10, 1, 100, recv=9)
    with pytest.raises(ValueError):
        book(0, 0, [(100, 1)], [(100, 1)])


def test_arrival_at_the_time_of_a_trade_comes_after_that_trade():
    # order sent at t=90 with latency 10 arrives at 100; a trade @95 prints at
    # exchange time 100. Exchange events at 100 are processed before arrivals
    # at 100, so the market order fills on the next trade (t=110 @97).
    ev = [clock(90, 0), trade(100, 1, 95), trade(110, 2, 97)]
    s = Script({("event", 0): [Market("m", "buy", 1)]})
    r = simulate(ev, s, **base_params(order_latency_ns=10))
    assert [(f.t_exch, f.price) for f in r.fills] == [(110, F(97))]
