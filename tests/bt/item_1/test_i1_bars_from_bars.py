"""`bars_from_bars` (K1 stage A, 2026-09-27): finer bars folded to coarser bars
by the rule of docs/PHASE2/K1/RESULT.md 1.2 (UTC wall clock, open = first,
high = max, low = min, close = last, volume = sum in delivered order, an
interval with no fine bar has no coarse bar). Expected values are hand
computed from that rule text; the fold of a two-level chain (1 s -> 3 s -> 6 s)
must equal the direct fold (1 s -> 6 s)."""
from __future__ import annotations

import pytest

from bot.bt.data import VectorError
from bot.bt.vector import bars_from_bars

NS = 10**9


def test_hand_scene_60s():
    # 1-second bars: 00:00:03, 00:00:04, 00:00:59, 00:02:00 (minute 00:01 has no bar)
    st = [3 * NS, 4 * NS, 59 * NS, 120 * NS]
    o, h, l, c, v = [10.0, 11.0, 9.5, 20.0], [12.0, 11.5, 9.6, 21.0], [9.0, 10.5, 9.4, 19.0], [11.0, 10.6, 9.5, 20.5], [1.0, 2.0, 3.0, 4.0]
    out = bars_from_bars(st, o, h, l, c, v, 60)
    assert out == [
        {"start_ns": 0, "open": 10.0, "high": 12.0, "low": 9.0, "close": 9.5, "volume": 6.0},  # (1 + 2) + 3
        {"start_ns": 120 * NS, "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.5, "volume": 4.0},
    ]


def test_chain_equals_direct():
    st = [k * NS for k in (0, 1, 2, 4, 5, 7, 8, 11, 12, 13, 17)]
    o = [float(100 + k) for k in range(len(st))]
    h = [x + 0.5 for x in o]
    l = [x - 0.25 for x in o]
    c = [x + 0.125 for x in o]
    v = [0.1, 0.2, 0.7, 1e-8, 1e8, 0.3, 1.0, 0.125, 0.1, 0.2, 0.7]
    mid = bars_from_bars(st, o, h, l, c, v, 3)
    chain = bars_from_bars([b["start_ns"] for b in mid], [b["open"] for b in mid], [b["high"] for b in mid],
                           [b["low"] for b in mid], [b["close"] for b in mid], [b["volume"] for b in mid], 6)
    direct = bars_from_bars(st, o, h, l, c, v, 6)
    assert [b["start_ns"] for b in chain] == [b["start_ns"] for b in direct]
    for a, b in zip(chain, direct):
        for k in ("open", "high", "low", "close"):
            assert a[k] == b[k]
        assert a["volume"] == pytest.approx(b["volume"], rel=1e-12)  # the float sum order differs between the paths


def test_empty_and_unsorted():
    assert bars_from_bars([], [], [], [], [], [], 60) == []
    with pytest.raises(VectorError):
        bars_from_bars([2 * NS, NS], [1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [1.0, 1.0], 60)
