"""P0-3 / P0-6: the notice types (accepted / rejected / filled, plus
canceled and state unknown) reach the strategy with the right content.
Checked by behaviour: the strategy places an order and the notice it
receives is compared with values fixed before the run (hand-computed)."""
from bot.bt.core import (
    Ack,
    Canceled,
    ClockEvent,
    CoreEngine,
    EventType,
    NullCostModel,
    OrderRequest,
    Reject,
    StateUnknown,
)

from bt0_util import Recorder

TS = 1_700_000_000_123_456_789


class _Scripted:
    """Answers each order with a fixed list of reports."""

    def __init__(self, reports_for):
        self.reports_for = reports_for

    def on_market_event(self, e, t):
        return ()

    def on_order(self, o, t):
        return self.reports_for(o)

    def on_cancel(self, r, t):
        return (Canceled(r.client_order_id),)


def _run(reports_for, act_extra=None):
    got = []

    def act(ev, ctx):
        if ev.EVENT_TYPE is EventType.CLOCK and not got:
            ctx.place_order(OrderRequest("buy", "limit", 0.01, price=5012345.0, client_order_id="synthetic-1"))
        if ev.EVENT_TYPE is not EventType.CLOCK:
            got.append(ev.to_dict())
        if act_extra is not None:
            act_extra(ev, ctx)

    CoreEngine(Recorder(act), [ClockEvent(received_time_ns=TS)], fill_model=_Scripted(reports_for),
               cost_model=NullCostModel()).run()
    return got


def test_accepted_notice_known_answer():
    got = _run(lambda o: (Ack(o.client_order_id, "v-1"),))
    assert got == [{
        "type": "ORDER_ACK", "received_time_ns": TS, "exchange_time_ns": TS, "seq": got[0]["seq"],
        "client_order_id": "synthetic-1", "venue_order_id": "v-1",
    }]


def test_rejected_notice_known_answer():
    got = _run(lambda o: (Reject(o.client_order_id, "price_out_of_band"),))
    assert [(g["type"], g["received_time_ns"], g["client_order_id"], g["reason"], g["request_kind"]) for g in got] == [
        ("ORDER_REJECT", TS, "synthetic-1", "price_out_of_band", "new"),
    ]


def test_filled_notice_known_answer():
    from bot.bt.core import Fill

    got = _run(lambda o: (Ack(o.client_order_id), Fill(o.client_order_id, 5012345.0, 0.004, "maker"),
                          Fill(o.client_order_id, 5012340.0, 0.006, "maker")))
    fills = [(g["price"], g["size"], g["side"], g["liquidity"], g["fee"]) for g in got if g["type"] == "ORDER_FILL"]
    assert fills == [(5012345.0, 0.004, "buy", "maker", 0.0), (5012340.0, 0.006, "buy", "maker", 0.0)]
    assert [g["type"] for g in got] == ["ORDER_ACK", "ORDER_FILL", "ORDER_FILL"]


def test_state_unknown_notice_is_held_and_nothing_is_resent():
    calls = []

    def reports(o):
        calls.append(o.client_order_id)
        return (StateUnknown(o.client_order_id, "timeout"),)

    got = _run(reports)
    assert calls == ["synthetic-1"]  # one send, no automatic resend
    assert [(g["type"], g["detail"]) for g in got] == [("ORDER_STATE_UNKNOWN", "timeout")]
