"""Critic, item 0, round 1 (resumed run 5), finding i0-r1-11.

events.py 24-27: "A BAR's timestamps are the time the bar became complete
(its close), never its open: delivering an open-labelled bar at its open
time would let a strategy see the bar's high/low/close before they
happened." The check behind it (events.py 254-261) only refuses
`start_time_ns > exchange_time_ns`. A bar stamped at its open with
`start_time_ns` equal to that stamp -- zero duration, yet high > low -- is
accepted and delivered at its open, which is exactly the look-ahead the
docstring says the core prevents (P0-4). A zero-length interval cannot hold
a price range; the core has every field it needs to refuse it.
"""
from __future__ import annotations

import pytest

from bot.bt.core import BarEvent, EventValidationError

T = 1_700_006_400_000_000_000


def test_zero_length_bar_with_a_price_range_is_refused():
    with pytest.raises(EventValidationError):
        BarEvent(received_time_ns=T, start_time_ns=T, open=100.0, high=110.0, low=90.0,
                 close=105.0, volume=12.0)
