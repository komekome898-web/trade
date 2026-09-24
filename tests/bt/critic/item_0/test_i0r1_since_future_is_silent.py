"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-08.

Fixed requirement P0-4 (REQUIREMENTS.md line 20): "戦略側から未来時刻の事象を
読もうとするコードが、実行時エラーか型エラーで止まるかを見る(素通りしたら不合格)".

`StrategyContext.visible_events` refuses `until_ns > now_ns` with
`LookAheadError` (api.py 354-359) but answers `since_ns > now_ns` -- a
request for events at a future time -- with an empty tuple (api.py 362,
377-388): the future read passes through silently. The battery's own run of
the new implementation records it: "ctx.visible_events(since_ns=5 本目の時刻)
-> []" (round_1/materials/runs/new_impl.tsv, p4-future-read-attempt).
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, CoreEngine, LookAheadError, Strategy

T0 = 1_700_006_400_000_000_000
DAY = 86_400 * 1_000_000_000


class _ReadsFromTheFuture(Strategy):
    def __init__(self) -> None:
        self.outcome = None

    def on_event(self, event, ctx) -> None:
        if ctx.now_ns != T0 + 4 * DAY:
            return
        try:
            got = ctx.visible_events(since_ns=T0 + 5 * DAY)
            self.outcome = ("returned", got)
        except LookAheadError:
            self.outcome = ("stopped", None)


def test_since_ns_after_now_stops_instead_of_returning_empty():
    bars = [BarEvent(received_time_ns=T0 + (i + 1) * DAY, open=100.0 + i, high=100.0 + i,
                     low=100.0 + i, close=100.0 + i, volume=1.0) for i in range(6)]
    strat = _ReadsFromTheFuture()
    CoreEngine(strat, bars).run()
    assert strat.outcome is not None
    assert strat.outcome[0] == "stopped", (
        f"visible_events(since_ns=<future>) returned {strat.outcome[1]!r} instead of stopping "
        f"(P0-4: 素通りしたら不合格)"
    )
