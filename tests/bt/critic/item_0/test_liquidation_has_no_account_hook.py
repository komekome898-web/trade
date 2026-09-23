"""Critic (item 0, round 1, i0-r1-04).

The committed item-0 row (REQUIREMENTS.md 1) names both funding and
liquidation as event types the core must carry, and interfaces.py's
`Account` protocol is item 0's declared "口座が差し込む口" (account
extension point). `CoreEngine.run` special-cases exactly one of the two
market-settlement event types for that socket:

    if event.EVENT_TYPE is EventType.FUNDING:
        self._account.apply_funding(event)

There is no equivalent call for EventType.LIQUIDATION, and `Account` (the
Protocol) has no `apply_liquidation` method at all. `LiquidationEvent`'s
own docstring says it can represent "ours" (our own forced liquidation),
not just a market-wide print -- exactly the case where the account socket
would need to react (close/mark the position). Right now a LiquidationEvent
reaches the strategy and the fill model, but has no path to the account,
unlike FundingEvent. This is an asymmetry in the extension-point design
item 0 is supposed to have finished: item 6 (portfolio/account) cannot
"differ into" liquidation handling the way it can for funding without
first getting engine.py and interfaces.py changed -- which breaks the
"pluggable without touching the core" promise interfaces.py's own
docstring makes for exactly this class of change.

Round-1 critic of run 5 (re-check under battery rule 8): the worker
reported this file's second test as failing through the test's own error.
Confirmed: (a) it built `LiquidationEvent(side="long")`, but the event's
`side` is the side of the liquidation ORDER ("buy"/"sell", events.py
276-291), so construction raised before the engine ran; (b) the recording
account lacked `apply_liquidation` (so nothing could ever append to
`liquidation_events`) and the socket methods `on_market_event` /
`check_order` that the Account protocol now requires. Both fixed below;
the claim tested (a liquidation reaches the account socket) is unchanged.
"""
from __future__ import annotations

import unittest

from bot.bt.core.engine import CoreEngine
from bot.bt.core.events import LiquidationEvent
from bot.bt.core.interfaces import Account, FillNotice
from bot.bt.core.strategy import Strategy
from bot.bt.core.time import to_nanos

T0 = to_nanos(1_700_000_000, "s")


class _NoOpStrategy(Strategy):
    def on_event(self, event, ctx) -> None:
        return None


class _RecordingAccount:
    def __init__(self) -> None:
        self.fills: list[FillNotice] = []
        self.funding_events: list = []
        self.liquidation_events: list = []

    def apply_fill(self, fill: FillNotice) -> None:
        self.fills.append(fill)

    def apply_funding(self, event) -> None:
        self.funding_events.append(event)

    def apply_liquidation(self, event) -> None:
        self.liquidation_events.append(event)

    def on_market_event(self, event, venue_time_ns):
        return ()

    def check_order(self, order, venue_time_ns):
        return None


class LiquidationReachesAccountTest(unittest.TestCase):
    def test_account_protocol_has_a_liquidation_hook(self):
        self.assertTrue(
            hasattr(Account, "apply_liquidation")
            or "apply_liquidation" in getattr(Account, "__protocol_attrs__", set())
            or "apply_liquidation" in dir(Account),
            "interfaces.Account has no apply_liquidation method -- "
            "LiquidationEvent has no declared account socket, unlike "
            "FundingEvent (apply_funding).",
        )

    def test_engine_notifies_the_account_of_a_liquidation_event(self):
        events = [
            LiquidationEvent(received_time_ns=T0, seq=0, price=100.0, size=1.0, side="sell")
        ]
        account = _RecordingAccount()
        engine = CoreEngine(strategy=_NoOpStrategy(), events=events, account=account)
        engine.run()
        self.assertEqual(
            len(account.liquidation_events),
            1,
            "CoreEngine.run special-cases FUNDING to call "
            "account.apply_funding but has no equivalent call for "
            "LIQUIDATION, even though LiquidationEvent can represent our "
            "own forced liquidation (see its docstring in events.py).",
        )


if __name__ == "__main__":
    unittest.main()
