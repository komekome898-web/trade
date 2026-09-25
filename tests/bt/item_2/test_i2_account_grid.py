"""Adversarial grid: the account (C2-11).

1. Ledger: 200 seeded random fill sequences (1-30 fills, either side, sizes
   and prices random) applied to MarginAccount; the oracle keeps a cost basis
   (total cost of the open position) instead of an average price: realised,
   position, average price, exposure time and unrealised at the end must
   agree.
2. Margin check: cash {1000, 5000} x leverage {1, 2, 5} x position
   {0, +0.2, -0.2} x live orders {none, buy 0.1, sell 0.3} x new market order
   {buy 0.1, buy 0.5, sell 0.1, sell 0.5} = 216 checks; the oracle is the
   documented worst-position rule.
3. Liquidation through the venue: maint ratio {0.3, 0.5, 0.8} x leverage
   {2, 5} x side {long, short} x 20 seeded price paths = 240 runs; the forced
   close happens at the first print whose ratio is below the maint ratio, at
   that print's price.
4. Corporate actions x position; funding and swap signs; realised P&L in the
   account currency at the realisation time's FX rate.

Not enumerated: cash-account buys beyond cash (one case below), marks by
"mid" (one case below), several products in one account (one product per
account by design).
"""
from __future__ import annotations

import itertools
import random

import pytest

from bot.bt.core import BookSnapshotEvent, FillNotice, FundingEvent, OrderRequest
from bot.bt.costs import CostSchedule, FundingRule, FxPoint, FxRates, SwapRule
from bot.bt.orders import Product
from bot.bt.portfolio import CorporateAction, MarginAccount, ReferenceSchedule, Rollover
from i2_gridkit import MS, SEC, T0, book, inp, place, run, trade

BTC = Product("FX_BTC_JPY", "bitflyer_cfd", 1.0, 0.01, 1e-8, "JPY", True)
COSTS = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="grid", funding=FundingRule("event_mark"),
                     swap=SwapRule(0.01, -0.02))


def account(product=BTC, cash=1e9, leverage=1.0, liquidation=None, fx=None, reference=None, open_orders=None,
            mark="last_trade"):
    return MarginAccount(product=product, currency="JPY", cash=cash, leverage=leverage, liquidation=liquidation,
                         mark=mark, costs=COSTS, fx=fx, reference=reference, open_orders=open_orders)


def fill(coid, side, size, price, t, fee=0.0):
    return FillNotice(client_order_id=coid, price=price, size=size, side=side, liquidity="taker", venue_time_ns=t,
                      fee=fee)


@pytest.mark.parametrize("seed", range(200))
def test_ledger_against_cost_basis(seed):
    rng = random.Random(seed)
    acc = account()
    pos, cost, realized, exposure = 0.0, 0.0, 0.0, 0
    t = T0
    last_t, last_px = T0, None
    for i in range(rng.randint(1, 30)):
        t += rng.randint(1, 5000) * MS
        side = rng.choice(("buy", "sell"))
        q = rng.choice([0.01, 0.1, 0.25, 0.5, 1.0, 2.0])
        p = float(rng.randint(9000, 11000))
        if pos != 0:
            exposure += t - last_t
        last_t = t
        s = 1 if side == "buy" else -1
        if pos == 0 or (pos > 0) == (s > 0):
            pos += s * q
            cost += p * q
        else:
            closing = min(q, abs(pos))
            avg = cost / abs(pos)
            realized += (p - avg) * closing * (1 if pos > 0 else -1)
            cost -= avg * closing
            pos += s * closing
            rest = q - closing
            if rest > 1e-12:
                pos, cost = s * rest, p * rest
            elif abs(pos) < 1e-12:
                pos, cost = 0.0, 0.0
        last_px = p
        acc.apply_fill(fill(f"o{i}", side, q, p, t))
    end = t + 7 * SEC
    if pos != 0:
        exposure += end - last_t
    snap = acc.finish(end)
    assert snap.position == pytest.approx(pos, abs=1e-9)
    assert snap.realized == pytest.approx(realized, rel=1e-9, abs=1e-6)
    assert snap.exposure_ns == exposure
    if pos != 0:
        assert snap.avg_px == pytest.approx(cost / abs(pos), rel=1e-12)
        assert snap.unrealized == pytest.approx((last_px - cost / abs(pos)) * pos, rel=1e-9, abs=1e-6)
    else:
        assert snap.avg_px is None and snap.unrealized == 0.0


MARGIN_GRID = list(itertools.product((1000.0, 5000.0), (1.0, 2.0, 5.0), (0.0, 0.2, -0.2),
                                     ("none", "buy0.1", "sell0.3"), ("buy0.1", "buy0.5", "sell0.1", "sell0.5")))


def test_margin_grid_size():
    assert len(MARGIN_GRID) == 216


@pytest.mark.parametrize("combo", MARGIN_GRID, ids=["-".join(map(str, c)) for c in MARGIN_GRID])
def test_margin_check(combo):
    cash, lev, pos, live, new = combo
    live_orders = [] if live == "none" else [(live[:-3] if live.startswith("buy") else live[:4],
                                              float(live[3:] if live.startswith("buy") else live[4:]))]
    acc = account(cash=cash, leverage=lev, open_orders=lambda: live_orders)
    acc.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(9999.0, 9)], asks=[(10001.0, 9)]), T0)
    if pos:
        acc.apply_fill(fill("p", "buy" if pos > 0 else "sell", abs(pos), 10000.0, T0 + 1))
    side = "buy" if new.startswith("buy") else "sell"
    size = float(new[3:] if side == "buy" else new[4:])
    reason = acc.check_order(OrderRequest(side=side, order_type="market", size=size, client_order_id="n"), T0 + 2)
    buys = sum(q for s, q in live_orders if s == "buy")
    sells = sum(q for s, q in live_orders if s == "sell")
    without = max(abs(pos + buys), abs(pos - sells))
    with_new = max(abs(pos + buys + (size if side == "buy" else 0)), abs(pos - sells - (size if side == "sell" else 0)))
    equity = cash + 0.0  # mark = the last fill 10000 = the average: no unrealised P&L
    price = 10001.0 if side == "buy" else 9999.0
    expect_refused = with_new > without * (1 + 1e-12) and with_new * price / lev > equity + 1e-12
    assert (reason == "insufficient_margin") == expect_refused, (reason, with_new, without)
    assert reason in (None, "insufficient_margin")


LIQ_GRID = list(itertools.product((0.3, 0.5, 0.8), (2.0, 5.0), ("long", "short"), range(20)))


def test_liquidation_grid_size():
    assert len(LIQ_GRID) == 240


@pytest.mark.parametrize("combo", LIQ_GRID, ids=["-".join(map(str, c)) for c in LIQ_GRID])
def test_liquidation_path(combo):
    maint, lev, side, seed = combo
    rng = random.Random(seed)
    cash, entry_ask, entry_bid = 1000.0, 10001.0, 9999.0
    size = round(0.9 * cash * lev / entry_ask, 2)  # within the margin at entry
    entry = entry_ask if side == "long" else entry_bid
    sign = 1 if side == "long" else -1
    prices, p = [], entry
    for _ in range(12):
        p = max(1.0, p + rng.choice([-1, 1]) * rng.choice([100.0, 250.0, 400.0]) - sign * 150.0)
        prices.append(p)
    market = [book(T0, [(entry_bid, 9)], [(entry_ask, 9)])]
    market += [trade(T0 + (k + 1) * SEC, px, 1.0, "sell" if sign > 0 else "buy") for k, px in enumerate(prices)]
    acc_d = {"currency": "JPY", "cash": cash, "leverage": lev, "maint_ratio": maint, "liquidation_price": "mark",
             "source": "grid: synthetic rule"}
    obs, refused = run(inp(market, [place(T0 + 1 * MS, "o1", "buy" if sign > 0 else "sell", "market", size)],
                           account=acc_d, end_t=T0 + 30 * SEC))
    assert refused is None, refused
    exp_t, exp_real = None, 0.0
    for k, px in enumerate(prices):
        equity = cash + (px - entry) * size * sign
        ratio = equity / (size * px / lev)
        if ratio < maint:
            exp_t, exp_real = T0 + (k + 1) * SEC, (px - entry) * size * sign
            break
    assert obs["account"]["liquidated_t"] == exp_t
    if exp_t is None:
        assert obs["account"]["position"] == pytest.approx(sign * size)
    else:
        assert obs["account"]["position"] == 0.0
        assert obs["account"]["realized"] == pytest.approx(exp_real, rel=1e-12, abs=1e-9)


CORP = list(itertools.product((2.0, 3.0, 0.5, 0.1), (100.0, -100.0, 300.0)))


@pytest.mark.parametrize("combo", CORP, ids=["-".join(map(str, c)) for c in CORP])
def test_corporate_actions(combo):
    ratio, pos = combo
    acc = account(reference=ReferenceSchedule([CorporateAction(T0 + 10 * SEC, ratio)]))
    acc.apply_fill(fill("p", "buy" if pos > 0 else "sell", abs(pos), 1500.0, T0))
    snap = acc.finish(T0 + 20 * SEC)
    assert snap.position == pytest.approx(pos * ratio)
    assert snap.avg_px == pytest.approx(1500.0 / ratio)
    assert snap.unrealized == pytest.approx(0.0, abs=1e-9)  # the mark is adjusted by the same ratio


FUND = list(itertools.product((0.0001, -0.0001), (1.0, -1.0, 0.0)))


@pytest.mark.parametrize("combo", FUND, ids=["-".join(map(str, c)) for c in FUND])
def test_funding_and_swap_signs(combo):
    rate, pos = combo
    acc = account(reference=ReferenceSchedule([Rollover(T0 + 5 * SEC)]))
    if pos:
        acc.apply_fill(fill("p", "buy" if pos > 0 else "sell", abs(pos), 10000.0, T0))
    acc.apply_funding(FundingEvent(received_time_ns=T0 + 3 * SEC, rate=rate, mark_price=10000.0))
    snap = acc.finish(T0 + 10 * SEC)
    assert snap.funding_paid == pytest.approx(pos * 10000.0 * rate)  # the long pays a positive rate
    exp_swap = -0.01 * pos if pos > 0 else (-(-0.02) * abs(pos) if pos < 0 else 0.0)
    assert snap.swap_paid == pytest.approx(exp_swap)


def test_realised_in_account_currency_at_realisation_time():
    eur = Product("EURUSD", "fx", 1e-5, 1000.0, 1.0, "USD", True)
    fx = FxRates([FxPoint(T0, "USDJPY", 150.0), FxPoint(T0 + 5 * SEC, "USDJPY", 160.0)])
    acc = MarginAccount(product=eur, currency="JPY", cash=1e9, leverage=10.0, liquidation=None, mark="last_trade",
                        costs=COSTS, fx=fx, reference=None, open_orders=None)
    acc.apply_fill(fill("a", "buy", 10000.0, 1.1000, T0 + 1))
    acc.apply_fill(fill("b", "sell", 5000.0, 1.1010, T0 + 2))  # at 150
    acc.apply_fill(fill("c", "sell", 5000.0, 1.1020, T0 + 6 * SEC))  # at 160
    snap = acc.finish(T0 + 7 * SEC)
    assert snap.realized == pytest.approx(5000 * 0.0010 + 5000 * 0.0020)
    assert snap.realized_account == pytest.approx(5000 * 0.0010 * 150 + 5000 * 0.0020 * 160)


def test_cash_account_rules_and_mid_mark():
    jpx = Product("JPX_A", "jpx_equity", 1.0, 100.0, 100.0, "JPY", False)
    acc = account(product=jpx, cash=200_000.0, mark="mid")
    acc.on_market_event(BookSnapshotEvent(received_time_ns=T0, bids=[(1499.0, 1e4)], asks=[(1501.0, 1e4)]), T0)
    assert acc.check_order(OrderRequest(side="sell", order_type="market", size=100.0), T0) == "no_short_in_cash_account"
    assert acc.check_order(OrderRequest(side="buy", order_type="market", size=200.0), T0) == "insufficient_cash"
    assert acc.check_order(OrderRequest(side="buy", order_type="market", size=100.0), T0) is None
    acc.apply_fill(fill("b", "buy", 100.0, 1501.0, T0 + 1))
    assert acc.unrealized() == pytest.approx((1500.0 - 1501.0) * 100)
    with pytest.raises(Exception):
        account(product=jpx, leverage=2.0)
