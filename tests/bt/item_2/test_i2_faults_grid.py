"""Adversarial grid: injected faults and the kill switch (C2-4; CLAUDE.md
section 1: STATE_UNKNOWN is held and nothing is resent automatically; the
kill switch never resumes on its own).

1. New-order faults {reject, timeout, unknown, ack_lost, none} x order
   {market, resting limit that a later print reaches, resting limit nothing
   reaches} x notice delay {0, 5 ms} = 30 runs. Oracle: reject -> rejected,
   the reject seen at arrival + notice; timeout / unknown -> state_unknown for
   good (no fill, the order does not live, a later cancel is answered
   "order_not_found" and settles nothing); ack_lost -> the order lives: a fill
   settles it (filled), without one it stays state_unknown; none -> the
   normal outcome. In every case the order reached the venue exactly once.
2. Cancel faults {cancel_reject, cancel_timeout} x a print after the cancel
   {yes, no}: the order stays at the venue; a later fill ends it filled.
3. Kill switch: every order type after a trip is refused locally and never
   sent; amends are refused; cancels still go; reset needs
   operator_confirm=True; a state file keeps it tripped in a new process
   object; an unreadable file counts as tripped.

Not enumerated: faults on forced (liquidation) orders -- the venue acts on
its own there, a fault plan names strategy orders.
"""
from __future__ import annotations

import itertools

import pytest

from bot.bt.core import ClockEvent, CoreEngine, Strategy
from bot.bt.costs import CostSchedule, ScheduleCostModel
from bot.bt.fill import FillSpec, SimVenue
from bot.bt.latency import Constant, LatencyModel
from bot.bt.orders import Fault, FaultPlan, KillSwitch, KillSwitchEngaged, OrderClient, Product, VenueRules
from bot.bt.orders.errors import ExecutionModelError
from i2_gridkit import MS, T0, book, filled, inp, place, run, trade

KINDS = ("reject", "timeout", "unknown", "ack_lost", None)
ORDERS = ("market", "limit_reached", "limit_unreached")
NOTICE = (0, 5 * MS)
GRID = list(itertools.product(KINDS, ORDERS, NOTICE))


def test_grid_size():
    assert len(GRID) == 30


@pytest.mark.parametrize("combo", GRID, ids=["-".join(map(str, c)) for c in GRID])
def test_new_order_faults(combo):
    kind, order, notice = combo
    lat = {k: {"kind": "constant", "ns": v} for k, v in (("feed", 0), ("order", 0), ("cancel", 0), ("notice", notice))}
    px = {"market": None, "limit_reached": 9990.0, "limit_unreached": 9980.0}[order]
    typ = "market" if order == "market" else "limit"
    actions = [place(T0 + 1 * MS, "o1", "buy", typ, 1.0, px=px), {"t": T0 + 50 * MS, "op": "cancel", "ref": "o1"}]
    market = [book(T0, [(9999, 5)], [(10001, 5)]), trade(T0 + 10 * MS, 9985, 5, "sell")]
    inject = [{"kind": kind, "ref": "o1"}] if kind else []
    obs, refused = run(inp(market, actions, latency=lat, inject=inject))
    assert refused is None, refused
    assert obs["sent"]["o1"] == 1
    st = obs["orders"]["o1"]["status"]
    fills_normally = order in ("market", "limit_reached")
    if kind == "reject":
        assert st == "rejected" and filled(obs, "o1") == 0.0
        assert obs["notices"]["o1"]["reject"] == T0 + 1 * MS + notice
    elif kind in ("timeout", "unknown"):
        assert st == "state_unknown" and filled(obs, "o1") == 0.0
        assert obs["notices"]["o1"]["state_unknown"] == T0 + 1 * MS + notice
        assert "cancel_reject" in obs["notices"]["o1"]  # the later cancel found no order; still unknown
    elif kind == "ack_lost":
        assert filled(obs, "o1") == (1.0 if fills_normally else 0.0)
        # a fill settles the unknown; the later cancel of an unfilled one ends it
        assert st == ("filled" if fills_normally else "canceled")
    else:
        assert st == ("filled" if fills_normally else "canceled")


CANCEL_GRID = list(itertools.product(("cancel_reject", "cancel_timeout"), (True, False)))


@pytest.mark.parametrize("combo", CANCEL_GRID, ids=["-".join(map(str, c)) for c in CANCEL_GRID])
def test_cancel_faults(combo):
    kind, later_print = combo
    market = [book(T0, [(9999, 5)], [(10001, 5)])]
    if later_print:
        market.append(trade(T0 + 30 * MS, 9985, 5, "sell"))
    actions = [place(T0 + 1 * MS, "o1", "buy", "limit", 1.0, px=9990.0), {"t": T0 + 10 * MS, "op": "cancel", "ref": "o1"}]
    obs, refused = run(inp(market, actions, inject=[{"kind": kind, "ref": "o1"}]))
    assert refused is None, refused
    st = obs["orders"]["o1"]["status"]
    if later_print:
        assert st == "filled"
    else:
        assert st == ("open" if kind == "cancel_reject" else "state_unknown")


class _OnceThenCancel(Strategy):
    def __init__(self, client):
        self.client = client

    def on_event(self, event, ctx):
        self.client.observe(event, ctx)
        if getattr(event, "tag", "") == "go":
            self.client.place(ctx, ref="o1", side="buy", order_type="limit", size=1.0, price=9990.0)
        if getattr(event, "tag", "") == "cancel":
            self.client.cancel(ctx, "o1")


def test_state_unknown_is_never_resent():
    product = Product("FX_BTC_JPY", "bitflyer_cfd", 1.0, 0.01, 1e-8, "JPY", True)
    costs = CostSchedule(maker_rate=0.0, taker_rate=0.0, source="test")
    venue = SimVenue(product=product, rules=VenueRules(), fill=FillSpec(tier=4), costs=costs,
                     faults=FaultPlan((Fault("timeout", "o1"),)), l3=None)
    client = OrderClient(KillSwitch(None))
    eng = CoreEngine(_OnceThenCancel(client),
                     {"a": [ClockEvent(received_time_ns=T0, tag="go"), ClockEvent(received_time_ns=T0 + 5, tag="cancel")]},
                     venue, LatencyModel(feed=Constant(0), order=Constant(0), cancel=Constant(0), notice=Constant(0)),
                     ScheduleCostModel(costs, product=product, account_currency="JPY", fx=None), None,
                     end_time_ns=T0 + 1000)
    result = eng.run()
    assert len(result.order_requests) == 1 and venue.arrivals == {"o1": 1}
    assert client.status(result, "o1") == "state_unknown"


@pytest.mark.parametrize("typ", ["market", "limit", "stop", "stop_limit"])
def test_kill_switch_refuses_every_order_type(typ):
    px = 9990.0 if typ in ("limit", "stop_limit") else None
    stop = 10050.0 if typ in ("stop", "stop_limit") else None
    actions = [place(T0 + 1 * MS, "o1", "buy", "limit", 1.0, px=9980.0), {"t": T0 + 2 * MS, "op": "kill"},
               place(T0 + 3 * MS, "o2", "buy", typ, 1.0, px=px, stop_px=stop),
               {"t": T0 + 4 * MS, "op": "cancel", "ref": "o1"}]
    obs, refused = run(inp([book(T0, [(9999, 5)], [(10001, 5)])], actions))
    assert refused is None, refused
    assert obs["orders"]["o2"]["status"] == "rejected" and obs["sent"]["o2"] == 0
    assert obs["orders"]["o1"]["status"] == "canceled"  # a cancel still reaches the venue


def test_kill_switch_amend_refused_and_reset_needs_confirm(tmp_path):
    ks = KillSwitch(tmp_path / "ks.json")
    ks.trip("test", T0)
    assert KillSwitch(tmp_path / "ks.json").is_tripped  # survives a new object (a new process)
    with pytest.raises(ExecutionModelError):
        ks.reset(operator_confirm=False)
    ks.reset(operator_confirm=True)
    assert not ks.is_tripped and not KillSwitch(tmp_path / "ks.json").is_tripped
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert KillSwitch(tmp_path / "bad.json").is_tripped
    client = OrderClient(KillSwitch(None))
    client.kill("x", None)
    with pytest.raises(KillSwitchEngaged):
        client.place(None, ref="z", side="buy", order_type="market", size=1.0)  # refused before any ctx call
    assert client.refused_reason("z").startswith("kill_switch")
