"""Item 4 critic, round 3 (i4-r3-01): the account socket of the integrated run must show each observation to
item 2's MarginAccount ONCE, and the core must receive what the account answered on it.

src/bot/bt/pipeline.py `DeferredMarginAccount` (the lead's I-2, answer (甲)) states: "each event reaches the
MarginAccount once" -- `observe` (called by the ArrivalGate when it prices a held market order) stores
(id(event), time, answer) and `on_market_event` returns that answer when the core delivers "the same event".
But the core hands every receiver ITS OWN COPY of an event (src/bot/bt/core/engine.py:1219 and :1222 both call
`copy_carrier(event)`; values.py:1935 "each receiver holds objects no one else holds"), so the id the gate saw is
never the id the account socket is given: the MarginAccount sees the observation twice, and the answer of the
first call (a LIQUIDATION order: account.py:339-354 sets `_forced_pending` and returns the forced order ONCE) is
dropped -- the second call returns [] because `_forced_pending` is already set, and no liquidation is ever
issued again for that account.

Grid: the observation {TradeEvent, BarEvent, BookSnapshotEvent} x how the core delivers it {a copy (the core's
way), the same object (control)}. The inner account is a stand-in that counts calls and answers a forced order on
the first call only (the shape of MarginAccount._maybe_liquidate); no real margin arithmetic is needed to show
the delivery count. Control: with the same object the socket returns the stored answer and the inner sees the
event once (the test is not vacuous).
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, BookSnapshotEvent, TradeEvent
from bot.bt.core.values import copy_carrier
from bot.bt.pipeline import DeferredMarginAccount

T = 1_000_000_000


def _event(kind: str):
    if kind == "trade":
        return TradeEvent(received_time_ns=T, exchange_time_ns=T, price=100.0, size=1.0, side="buy")
    if kind == "bar":
        return BarEvent(received_time_ns=T, exchange_time_ns=T, open=100.0, high=101.0, low=99.0, close=100.5,
                        volume=1.0, start_time_ns=T - 60_000_000_000)
    return BookSnapshotEvent(received_time_ns=T, exchange_time_ns=T, bids=((99.0, 1.0),), asks=((101.0, 1.0),))


class _Inner:
    """The shape of MarginAccount.on_market_event / _maybe_liquidate: the forced order comes out once."""

    def __init__(self):
        self.calls = 0
        self.forced_pending = False

    def on_market_event(self, event, t):
        self.calls += 1
        if self.forced_pending:
            return []
        self.forced_pending = True
        return ["LIQUIDATION"]


@pytest.mark.parametrize("kind", ["trade", "bar", "book"])
def test_the_core_delivers_a_copy_and_the_account_must_still_see_the_event_once(kind):
    inner = _Inner()
    acc = DeferredMarginAccount(inner)
    ev = _event(kind)
    acc.observe(ev, T)                                   # the gate prices a held order on this observation
    delivered = copy_carrier(ev)                         # what the core hands the account socket (engine.py:1222)
    assert delivered is not ev and delivered == ev
    answer = list(acc.on_market_event(delivered, T))
    assert inner.calls == 1, f"the MarginAccount saw the {kind} observation {inner.calls} times (stated: once)"
    assert answer == ["LIQUIDATION"], f"the account's answer on the observation was dropped: core got {answer}"


@pytest.mark.parametrize("kind", ["trade", "bar", "book"])
def test_control_same_object_is_seen_once_and_the_answer_reaches_the_core(kind):
    inner = _Inner()
    acc = DeferredMarginAccount(inner)
    ev = _event(kind)
    acc.observe(ev, T)
    answer = list(acc.on_market_event(ev, T))
    assert inner.calls == 1
    assert answer == ["LIQUIDATION"]
