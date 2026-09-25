"""Adversarial grid: OCO, amend, the range of two sides, data waits, bars.

1. OCO: pair {limit+stop, limit+limit} x what happens {the take-profit leg
   fills, the other leg fills / fires, nothing reaches, the strategy cancels
   one leg} x the fill is {partial, full} = 16 runs. Oracle (the client and
   venue docstrings): the first fill of either leg cancels the other ("oco");
   a strategy cancel of one leg cancels the other ("oco_partner_canceled").
2. Amend: tier {4, 5} x amend {price better, price worse, size down, size
   up above the first size, size to or below what already filled} x
   amend_qty_down {keep_priority, lose_priority} = 20 runs.
3. FillRange needs both sides; run_range runs each once; bounds.
4. data_wait_report / DataUnavailableError name the JPX board and ticks.
5. bars_from_trades: epoch-aligned, stamped at the close, OHLCV of the prints.

Not enumerated: an OCO whose legs are on the same side of the market (the
venue treats a pair symmetrically; the code path is the same).
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.core import BarEvent, TradeEvent
from bot.bt.fill import (
    DataUnavailableError,
    FillRange,
    FillSpec,
    FillSpecError,
    bars_from_trades,
    data_wait_report,
    run_range,
)
from i2_gridkit import MS, SEC, T0, book, filled, inp, place, run, trade

PAIRS = ("limit+stop", "limit+limit")
EVENTS = ("tp_fills", "other_fills", "nothing", "strategy_cancels")
AMOUNTS = ("partial", "full")
OCO_GRID = list(itertools.product(PAIRS, EVENTS, AMOUNTS))


def test_oco_grid_size():
    assert len(OCO_GRID) == 16


@pytest.mark.parametrize("combo", OCO_GRID, ids=["-".join(c) for c in OCO_GRID])
def test_oco_grid(combo):
    pair, event, amount = combo
    q = 0.4 if amount == "partial" else 5.0
    # long 1; o1 = take profit sell 10020; o2 = stop sell 9980 or limit sell 10040
    actions = [place(T0 + 1 * MS, "o0", "buy", "market", 1.0),
               place(T0 + 2 * MS, "o1", "sell", "limit", 1.0, px=10020.0, oco="o2")]
    if pair == "limit+stop":
        actions.append(place(T0 + 2 * MS, "o2", "sell", "stop", 1.0, stop_px=9980.0, oco="o1"))
    else:
        actions.append(place(T0 + 2 * MS, "o2", "sell", "limit", 1.0, px=10040.0, oco="o1"))
    market = [book(T0, [(9999, 50)], [(10001, 50)])]
    if event == "tp_fills":
        market.append(trade(T0 + 10 * MS, 10025, q, "buy"))
    elif event == "other_fills":
        if pair == "limit+stop":
            market.append(book(T0 + 9 * MS, [(9975, 50)], [(9977, 50)]))
            market.append(trade(T0 + 10 * MS, 9975, q, "sell"))
        else:
            # a print that reaches 10040 also reaches 10020: o1 (better price) fills first
            market.append(trade(T0 + 10 * MS, 10045, q, "buy"))
    elif event == "strategy_cancels":
        actions.append({"t": T0 + 5 * MS, "op": "cancel", "ref": "o1"})
    market.append(trade(T0 + 40 * MS, 10050, 50, "buy"))  # later: would fill any leg still resting
    market.append(trade(T0 + 50 * MS, 9950, 50, "sell"))
    obs, refused = run(inp(market, actions))
    assert refused is None, refused
    st1, st2 = obs["orders"]["o1"]["status"], obs["orders"]["o2"]["status"]
    f1, f2 = filled(obs, "o1"), filled(obs, "o2")
    if event == "tp_fills" or (event == "other_fills" and pair == "limit+limit"):
        # o1 gets the first fill (for limit+limit the 10045 print reaches o1's
        # better price first); that fill cancels o2; a partly filled o1 keeps
        # resting and the later 10050 print fills its rest
        first_leg = [f for f in obs["fills"] if f["ref"] == "o1"][0]
        assert first_leg["qty"] == pytest.approx(min(q, 1.0)) and first_leg["t"] == T0 + 10 * MS
        assert f1 == pytest.approx(1.0) and st1 == "filled"
        assert f2 == 0.0 and st2 == "canceled"
    elif event == "other_fills":
        assert f2 == 1.0 and f1 == 0.0 and st1 == "canceled" and st2 == "filled"
    elif event == "strategy_cancels":
        assert st1 == "canceled" and st2 == "canceled" and f1 == f2 == 0.0
    else:
        # nothing before T0+40ms: the 10050 print reaches o1 (and a 10040 limit o2 too); a sell at the
        # lower price comes first, so o1 fills and cancels o2
        assert f1 == 1.0 and st2 == "canceled" and f2 == 0.0


AMEND_GRID = list(itertools.product((4, 5), ("better", "worse", "down", "up_above_first", "to_filled"),
                                    ("keep_priority", "lose_priority")))


def test_amend_grid_size():
    assert len(AMEND_GRID) == 20


@pytest.mark.parametrize("combo", AMEND_GRID, ids=["-".join(map(str, c)) for c in AMEND_GRID])
def test_amend_grid(combo):
    tier, amend, qty_rule = combo
    L = 9990.0
    rules = {"off_tick": "reject", "below_min_qty": "reject", "post_only": "reject_if_crossing",
             "market_remainder": "cancel", "mark": "last_trade", "amend_qty_down": qty_rule}
    fm = {"tier": tier, "cancel_stance": "none"} if tier == 5 else {"tier": tier}
    # o1 buy 2 @9990 behind 3 displayed; a first print of 4 at 9990 (T0+10ms) fills 1 under tier 5
    # (4 - 3), 2 under tier 4; then the amend (T0+20ms); then a print of 3 at 9990 (T0+30ms)
    market = [book(T0, [(L, 3.0)], [(10001, 5)]), trade(T0 + 10 * MS, L, 4.0, "sell"),
              book(T0 + 15 * MS, [(L, 3.0), (9989.0, 5)], [(10001, 5)]),
              trade(T0 + 30 * MS, L, 3.0, "sell"), trade(T0 + 40 * MS, 9989, 3.0, "sell")]
    size, px = 2.0, None
    if amend == "better":
        px = 9991.0
    elif amend == "worse":
        px = 9989.0
    elif amend == "down":
        size = 1.5
    elif amend == "up_above_first":
        size = 3.0
    else:
        size = 1.0
    actions = [place(T0 + 1 * MS, "o1", "buy", "limit", 2.0, px=L),
               {"t": T0 + 20 * MS, "op": "amend", "ref": "o1", "px": px, "qty": size if px is None else None}]
    obs, refused = run(inp(market, actions, rules=rules, fill_model=fm))
    assert refused is None, refused
    first = 2.0 if tier == 4 else 1.0  # filled before the amend
    got = filled(obs, "o1")
    if tier == 4:
        # tier 4 filled the whole order at T0+10ms: the amend finds no resting order
        assert got == 2.0 and obs["orders"]["o1"]["status"] == "filled"
        return
    if amend in ("up_above_first", "to_filled"):
        # refused amends change nothing: the 9990 print of 3 at T0+30ms is behind 3 displayed... then
        # the 9989 print is through 9990 and fills the rest
        assert got == 2.0 and obs["orders"]["o1"]["status"] == "filled"
        return
    if amend == "better":
        # 9991 lost priority and nothing is displayed there: the 9990 print is through 9991 -> fills the rest
        assert got == 2.0
        return
    if amend == "worse":
        # 9989 with 5 displayed ahead: the 9990 print does not reach it; the 9989 print of 3 is at our
        # price with 5 ahead -> nothing
        assert got == first and obs["orders"]["o1"]["status"] == "open"
        return
    # size down to 1.5, 0.5 left: keep priority -> ahead was 3 - 3 = 0 after the first print, so the
    # 9990 print of 3 fills 0.5; lose priority -> 3 displayed ahead again, the print of 3 fills 0, the
    # through print at 9989 fills the rest. Either way it ends filled at the amended size.
    assert got == pytest.approx(1.5)
    assert obs["orders"]["o1"]["status"] == "filled"
    t_last = max(f["t"] for f in obs["fills"] if f["ref"] == "o1")
    assert t_last == (T0 + 30 * MS if qty_rule == "keep_priority" else T0 + 40 * MS)


def test_fill_range_needs_both_sides():
    a, b = FillSpec(tier=3), FillSpec(tier=1)
    for kw in ({"optimistic": a, "pessimistic": None}, {"optimistic": None, "pessimistic": b}):
        with pytest.raises(FillSpecError):
            FillRange(**kw)
    calls = []
    rr = run_range(lambda spec: calls.append(spec.tier) or float(spec.tier), FillRange(optimistic=a, pessimistic=b))
    assert calls == [3, 1] and rr.bounds(lambda x: x) == (1.0, 3.0)
    with pytest.raises(FillSpecError):
        run_range(lambda spec: 0.0, a)


def test_data_wait_named():
    rep = data_wait_report()
    assert {(r["venue"], r["layer"]) for r in rep} == {("jpx_equity", "book"), ("jpx_equity", "tick")}
    assert all("オーナー PC は未確認" in r["checked"] for r in rep)
    assert "データ待ち" in str(DataUnavailableError("jpx_equity", "book", "x"))
    assert "データ待ち" not in str(DataUnavailableError("bitflyer_cfd", "book", "x"))


def test_bars_from_trades():
    trades = [TradeEvent(received_time_ns=T0 + k, price=p, size=s, side="buy")
              for k, p, s in ((10, 100.0, 1.0), (SEC - 1, 103.0, 2.0), (SEC, 99.0, 1.0), (3 * SEC + 5, 101.0, 4.0))]
    bars = bars_from_trades(trades, SEC)
    assert [(b.start_time_ns, b.exchange_time_ns, b.open, b.high, b.low, b.close, b.volume) for b in bars] == [
        (T0, T0 + SEC, 100.0, 103.0, 100.0, 103.0, 3.0), (T0 + SEC, T0 + 2 * SEC, 99.0, 99.0, 99.0, 99.0, 1.0),
        (T0 + 3 * SEC, T0 + 4 * SEC, 101.0, 101.0, 101.0, 101.0, 4.0)]
    assert all(type(b) is BarEvent and b.received_time_ns == b.exchange_time_ns for b in bars)
    with pytest.raises(FillSpecError):
        bars_from_trades(list(reversed(trades)), SEC)
