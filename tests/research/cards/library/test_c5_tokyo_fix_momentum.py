"""Card 5 of W4 (東京仲値・前モメンタム): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c5_tokyo_fix_momentum/INTENT_MAP.md it checks.
Inputs: bitFlyer FX_BTC_JPY 1-minute bars [start, start + 1 min), received at their end. The card uses no
reference series. D0 below is a JST midnight on a Tuesday, so the JST weekday gate is open unless a test
moves to a weekend.
"""
from __future__ import annotations

import numpy as np

from bot.bt.core import BarEvent
from bot.research.cards import run_card
from bot.research.cards.library.c5_tokyo_fix_momentum import (FIX_TOD_NS, TokyoFixMomentum, jst_day_index,
                                                              jst_weekday)

NS = 1_000_000_000
M = 60 * NS
H = 60 * M
D0 = 1_672_671_600 * NS  # 2023-01-02T15:00:00Z = JST 2023-01-03 (Tue) 00:00 (a test time)
FIX = D0 + FIX_TOD_NS  # JST 09:55 of that date = 2023-01-03T00:55:00Z


def bar(start, o, c, volume=1.0):
    return BarEvent(received_time_ns=start + M, exchange_time_ns=start + M, start_time_ns=start, open=o, close=c,
                    high=max(o, c), low=min(o, c), volume=volume)


def run(bars):
    r = run_card(TokyoFixMomentum(), bars, references={}, declarations={}, venue="bitflyer", symbol="FX_BTC_JPY")
    return {int(t): float(e) for t, e in zip(r.end_ns, r.exposure)}


def path(start, n, closes, first_open=100.0, volumes=None):
    """n consecutive bars from `start`; bar i opens at the previous close (first_open for i = 0)."""
    out, prev = [], first_open
    for i in range(n):
        v = 1.0 if volumes is None else volumes[i]
        out.append(bar(start + i * M, prev, closes[i], v))
        prev = closes[i]
    return out


def test_mouth_and_clock():
    c = TokyoFixMomentum()
    assert c.name == "c5_tokyo_fix_momentum"
    assert tuple(c.requires) == ()
    day = jst_day_index(D0)
    assert jst_weekday(day) == 1  # Tuesday
    assert FIX == 1_672_707_300 * NS  # 2023-01-03T00:55:00Z = JST 09:55
    assert jst_weekday(jst_day_index(D0 + 4 * 24 * H)) == 5  # Saturday


def test_i1a_held_only_before_the_fix_and_flat_from_the_bar_ending_at_the_fix():
    """I-1a: hold for bar ends D0 < t < F (the last held bar ends at 09:54 JST); 0 at t = F and after.
    The measurement fills the exposure of t at the next bar's open, so the 0 of t = F is filled at the fix."""
    n = 11 * 60
    ex = run(path(D0, n, [100.0 + 0.01 * (i + 1) for i in range(n)]))
    assert ex[D0 + M] == 1.0
    assert ex[FIX - M] == 1.0
    assert ex[FIX] == 0.0
    assert all(e == 0.0 for t, e in ex.items() if t >= FIX)
    assert all(e == 1.0 for t, e in ex.items() if D0 < t < FIX)


def test_i2_i3_follow_the_move_since_the_day_start():
    """I-2・I-3: the sign of (close - the day's first open) is the exposure; it flips when the price crosses the
    anchor and is 0 when it sits on it."""
    closes = [101.0, 102.0, 99.0, 100.0, 98.5]
    ex = run(path(D0, 5, closes, first_open=100.0))
    assert [ex[D0 + (i + 1) * M] for i in range(5)] == [1.0, 1.0, -1.0, 0.0, -1.0]


def test_size_is_the_sign_only():
    """＋ (C-6): a tiny and a huge move give the same exposure."""
    a = run(path(D0, 2, [100.0001, 100.0002]))
    b = run(path(D0, 2, [150.0, 200.0]))
    assert a[D0 + 2 * M] == b[D0 + 2 * M] == 1.0


def test_i1b_anchor_is_the_first_bar_of_the_jst_date_not_the_previous_day():
    """I-1b・C-4: the bar ending exactly at D0 belongs to the previous JST date (0, and no anchor for today);
    today's anchor is the open of the bar starting at D0."""
    prev = bar(D0 - M, 50.0, 200.0)  # previous date's last bar: a far-off open must not be the anchor
    today = path(D0, 3, [100.5, 99.5, 101.0], first_open=100.0)
    ex = run([prev] + today)
    assert ex[D0] == 0.0
    assert [ex[D0 + (i + 1) * M] for i in range(3)] == [1.0, -1.0, 1.0]


def test_anchor_when_the_first_minute_has_no_trade():
    """C-4: when the bar starting at D0 is empty (volume 0, the card is not called), the anchor is the open of
    the first later bar the card is called on."""
    bars = [bar(D0, 100.0, 100.0, volume=0.0), bar(D0 + M, 110.0, 111.0), bar(D0 + 2 * M, 111.0, 109.0)]
    ex = run(bars)
    assert ex[D0 + 2 * M] == 1.0  # 111 > 110 (anchor = 110, not 100)
    assert ex[D0 + 3 * M] == -1.0  # 109 < 110


def test_i1c_weekend_holds_zero():
    """I-1c: no fix on Saturday and Sunday (JST); the card holds 0 all day."""
    sat = D0 + 4 * 24 * H
    sun = sat + 24 * H
    for d in (sat, sun):
        ex = run(path(d, 120, [100.0 + 0.1 * (i + 1) for i in range(120)]))
        assert all(e == 0.0 for e in ex.values())
    mon = sun + 24 * H
    ex = run(path(mon, 3, [101.0, 102.0, 103.0]))
    assert ex[mon + M] == 1.0


def test_new_day_resets_the_anchor():
    """I-1b: each JST date has its own anchor (the next day's first open, not the previous day's)."""
    day1 = path(D0, 3, [101.0, 102.0, 103.0], first_open=100.0)
    d1 = D0 + 24 * H
    day2 = path(d1, 2, [119.0, 121.0], first_open=120.0)
    ex = run(day1 + day2)
    assert ex[d1 + M] == -1.0  # 119 < 120 (vs the day-1 anchor 100 it would be +1)
    assert ex[d1 + 2 * M] == 1.0


def test_no_look_ahead():
    """Changing only later bars leaves every earlier exposure unchanged."""
    rng = np.random.default_rng(5)
    n = 700
    closes = list(100.0 + np.cumsum(rng.normal(0.0, 0.1, n)))
    base = run(path(D0, n, closes))
    cut = 300
    changed = closes[:cut] + [c + 50.0 * (-1) ** i for i, c in enumerate(closes[cut:])]
    alt = run(path(D0, n, changed))
    for t in sorted(base):
        if t <= D0 + cut * M:
            assert alt[t] == base[t]
    assert any(alt[t] != base[t] for t in base if t > D0 + cut * M)


def test_same_input_same_output_and_bounds():
    rng = np.random.default_rng(11)
    n = 3 * 24 * 60
    closes = list(100.0 + np.cumsum(rng.normal(0.0, 0.1, n)))
    a = run(path(D0, n, closes))
    b = run(path(D0, n, closes))
    assert a == b
    assert set(a.values()) <= {-1.0, 0.0, 1.0}
    held = [t for t, e in a.items() if e != 0.0]
    assert held and all(0 < (t + 9 * H) % (24 * H) < FIX_TOD_NS for t in held)
