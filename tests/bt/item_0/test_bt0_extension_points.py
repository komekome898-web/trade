"""The four sockets are swapped from outside the package, without editing it."""
import pytest

from bot.bt.core import (
    CORE_CONTRACT,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderRequest,
)
from bot.bt.core.testing import FixedRateCost, ImmediateFillModel, RecordingAccount

from bt0_util import T0, Recorder, trade


def _buy_once(ev, ctx):
    if ev.EVENT_TYPE is EventType.TRADE and not ctx.visible_events(EventType.ORDER_ACK):
        if not ctx.open_orders() and ctx.order("b") is None:
            ctx.place_order(OrderRequest("buy", "market", 1.0, client_order_id="b"))


@pytest.mark.parametrize("cost,fee", [(NullCostModel(), 0.0), (FixedRateCost(0.0015), 0.15)])
def test_cost_model_swap_changes_the_fee(cost, fee):
    res = CoreEngine(Recorder(_buy_once), [trade(T0, 100.0)], fill_model=ImmediateFillModel(),
                     cost_model=cost).run()
    assert res.fills[0].fee == pytest.approx(fee)  # 100 * 1 * rate, closed form
    assert res.orders["b"].fees == pytest.approx(fee)


class _Venue:  # a fill model written here, not in core
    def __init__(self):
        self.calls = []

    def on_market_event(self, e, t):
        self.calls.append("market")
        return ()

    def on_order(self, o, t):
        from bot.bt.core import Ack, Fill

        self.calls.append("order")
        return (Ack(o.client_order_id), Fill(o.client_order_id, 50.0, o.size, "maker"))

    def on_cancel(self, r, t):
        from bot.bt.core import Canceled

        return (Canceled(r.client_order_id),)


class _Lat:
    def __init__(self):
        self.calls = []

    def feed_delay_ns(self, e):
        self.calls.append("feed")
        return 0

    def order_delay_ns(self, o, t):
        self.calls.append("order")
        return 1

    def cancel_delay_ns(self, r, t):
        return 1

    def notice_delay_ns(self, r, t):
        self.calls.append("notice")
        return 1


def test_all_four_sockets_are_called_with_outside_implementations():
    venue, lat, cost, acct = _Venue(), _Lat(), FixedRateCost(0.01), RecordingAccount()
    res = CoreEngine(Recorder(_buy_once), [trade(T0, 100.0)], fill_model=venue, latency_model=lat,
                     cost_model=cost, account=acct).run()
    assert venue.calls == ["market", "order"]
    assert lat.calls == ["feed", "order", "notice", "notice"]
    # account: the order is checked at the venue before the fill model sees
    # it, then the fill is booked; the trade was marked before that.
    assert [k for k, _ in acct.calls] == ["market", "check_order", "fill"]
    fill = acct.calls[2][1]
    assert fill.liquidity == "maker" and fill.fee == pytest.approx(0.5)  # 50 * 1 * 0.01
    assert res.models["fill_model"].endswith("_Venue")
    assert res.defaults_used == []


def test_defaults_are_reported_not_hidden():
    res = CoreEngine(Recorder(), [trade(T0)]).run()
    assert sorted(res.defaults_used) == ["account", "cost_model", "fill_model", "latency_model"]
    assert res.models["cost_model"] == "none"


def test_incomplete_socket_is_refused_at_construction():
    class _NoLiquidation:
        def apply_fill(self, f):
            pass

        def apply_funding(self, e):
            pass

    with pytest.raises(TypeError, match="apply_liquidation"):
        CoreEngine(Recorder(), [], account=_NoLiquidation())


def test_account_without_the_mark_and_check_hooks_is_refused_at_construction():
    class _OldShape:
        def apply_fill(self, f):
            pass

        def apply_funding(self, e):
            pass

        def apply_liquidation(self, e):
            pass

    with pytest.raises(TypeError, match="check_order.*on_market_event|on_market_event.*check_order"):
        CoreEngine(Recorder(), [], account=_OldShape())


def test_contract_lists_the_four_sockets_from_the_protocols():
    assert set(CORE_CONTRACT["sockets"]) == {"fill_model", "latency_model", "cost_model", "account"}
    assert CORE_CONTRACT["sockets"]["fill_model"] == ["on_cancel", "on_market_event", "on_order"]
    assert CORE_CONTRACT["sockets"]["account"] == [
        "apply_fill", "apply_funding", "apply_liquidation", "check_order", "on_market_event",
    ]
