"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-13.

P0-2 (REQUIREMENTS.md line 18): every time inside the core is an int64 of
UTC nanoseconds and no other representation mixes in. time.py calls
`validate_nanos` "the choke point every event timestamp passes through", and
`set_timer` goes through it (api.py 213), but `CoreEngine(end_time_ns=...)`
does not (engine.py 347): a float is kept and compared against queue times
as a float (engine.py 430). `history_limit` is also not checked for being an
int (engine.py 348) and a float fails in the middle of the run, after
events were already delivered (engine.py 528), not at construction.
"""
from __future__ import annotations

import pytest

from bot.bt.core import CoreEngine, Strategy, TimestampUnitError, TradeEvent

T0 = 1_700_006_400_000_000_000


class _Quiet(Strategy):
    def on_event(self, event, ctx) -> None:
        return None


def _trades():
    return [TradeEvent(received_time_ns=T0 + i, price=100.0, size=1.0, side="buy") for i in range(10)]


def test_float_end_time_is_refused_at_construction():
    with pytest.raises(TimestampUnitError):
        CoreEngine(_Quiet(), _trades(), end_time_ns=float(T0 + 5))


def test_non_int_history_limit_is_refused_at_construction():
    with pytest.raises((TypeError, ValueError)):
        CoreEngine(_Quiet(), _trades(), history_limit=2.5)
