"""G-1 of K1 stage G (delegation docs/DATA/delegations/20261001_k1_stage_g_close.md §2-1), the fill side: before the
fix `SimVenue.last_bar_close` was one value overwritten by every bar of every stream (venue.py `on_market_event`), so
in a run reading two markets the market order's price was the close of whichever bar the merge order delivered last.
Rule after the fix (venue.py module docstring): `SimVenue(streams=(...))` takes market data of the named streams only;
with streams None a second stream of the same kind of price source (bar / trade / book) is refused.
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, CoreEngine, NullAccount, OrderRequest, Strategy, TradeEvent, ZeroLatency
from bot.bt.core.testing import FixedRateCost
from bot.bt.costs import CostSchedule
from bot.bt.fill import FillSpec, SimVenue
from bot.bt.orders import FaultPlan, Product, VenueRules
from bot.bt.orders.errors import ExecutionModelError

NS = 1_000_000_000
T0 = 1_700_000_000 * NS
PRODUCT = {"symbol": "P", "venue": "test", "tick": 1.0, "min_qty": 1.0, "qty_step": 1.0, "quote_ccy": "JPY",
           "margin": True}


def venue(streams=None) -> SimVenue:
    return SimVenue(product=Product(**PRODUCT), rules=VenueRules(market_ref="last_bar_close"), fill=FillSpec(tier=2),
                    costs=CostSchedule(maker_rate=0.0, taker_rate=0.0, source="test", spread=0.0),
                    faults=FaultPlan(()), l3=None, streams=streams)


def bar(i: int, px: float) -> BarEvent:
    return BarEvent(received_time_ns=T0 + (i + 1) * 60 * NS, start_time_ns=T0 + i * 60 * NS,
                    open=px, high=px, low=px, close=px, volume=1.0)


class OrderOnEveryBarOf(Strategy):
    """One market order on every bar of `name`, placed once both bars of the window have arrived."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.n = 0
        self.seen: dict[int, set] = {}

    def on_event(self, event, ctx) -> None:
        if type(event) is not BarEvent:
            return
        w = self.seen.setdefault(int(event.start_time_ns), set())
        w.add(event.stream)
        if len(w) == 2:
            self.n += 1
            ctx.place_order(OrderRequest(side="buy" if self.n % 2 else "sell", order_type="market", size=1.0,
                                         client_order_id=f"o{self.n}"))


def _fills(price_name: str, signal_name: str, streams):
    v = venue(streams)
    eng = CoreEngine(OrderOnEveryBarOf(price_name),
                     {signal_name: [bar(i, 10.0 + i) for i in range(4)], price_name: [bar(i, 1000.0 + i) for i in range(4)]},
                     v, ZeroLatency(), FixedRateCost(0.0), NullAccount())
    return [f.price for f in eng.run().fills]


@pytest.mark.parametrize("price_name,signal_name", [("d1", "d0"), ("a", "z"), ("price", "signal")])
def test_the_venue_prices_by_its_own_streams_bars_whatever_the_merge_order(price_name, signal_name):
    assert _fills(price_name, signal_name, (price_name,)) == [1000.0, 1001.0, 1002.0, 1003.0]


def test_two_bar_streams_into_an_undeclared_venue_are_refused_not_overwritten():
    with pytest.raises(ExecutionModelError, match="bar events from two streams"):
        _fills("d1", "d0", None)


def test_an_undeclared_venue_takes_one_stream_per_kind():
    trades = [TradeEvent(received_time_ns=T0 + 30 * NS, price=500.0, size=1.0, side="")]
    v = venue(None)
    eng = CoreEngine(OrderOnEveryBarOf("x"), {"bars": [bar(i, 1000.0 + i) for i in range(2)], "trades": trades},
                     v, ZeroLatency(), FixedRateCost(0.0), NullAccount())
    eng.run()
    assert v.source_by_kind == {"bar": "bars", "trade": "trades"} and v.last_bar_close == 1001.0


def test_events_of_other_streams_do_not_reach_a_declared_venue():
    v = venue(("p",))
    assert v.on_market_event(BarEvent(received_time_ns=T0 + 60 * NS, start_time_ns=T0, open=5.0, high=5.0, low=5.0,
                                      close=5.0, volume=1.0, stream="s"), T0 + 60 * NS) == []
    assert v.last_bar_close is None
    v.on_market_event(BarEvent(received_time_ns=T0 + 60 * NS, start_time_ns=T0, open=7.0, high=7.0, low=7.0,
                               close=7.0, volume=1.0, stream="p"), T0 + 60 * NS)
    assert v.last_bar_close == 7.0


@pytest.mark.parametrize("bad", [(), ("",), ("a", "a"), ["a"], "a", (1,)])
def test_streams_must_be_a_tuple_of_distinct_names(bad):
    with pytest.raises(ExecutionModelError, match="streams"):
        venue(bad)
