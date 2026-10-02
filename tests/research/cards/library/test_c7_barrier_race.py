"""Card 7 of W4 (バリアレース逆張り): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c7_barrier_race/INTENT_MAP.md it checks.
Inputs: bitFlyer FX_BTC_JPY 1-minute bars [start, start + 1 min), received at their end. The card uses no
reference series. Prices are given as log closes so that the widths can be computed by hand.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.research.cards import run_card
from bot.research.cards.card import CardError
from bot.research.cards.library.c7_barrier_race import WINDOWS, BarrierRace

NS = 1_000_000_000
M = 60 * NS
H = 60 * M
T0 = 1_672_617_600 * NS  # 2023-01-02T00:00:00Z (a test time)
A = 0.001  # size of the warm-up's alternating log returns (a test input, not a card value)
W0 = A * math.sqrt(60)  # the first race's width: 60 returns of size A in the 1-hour window


def bar(start, o, c, volume=1.0):
    return BarEvent(received_time_ns=start + M, exchange_time_ns=start + M, start_time_ns=start, open=o, close=c,
                    high=max(o, c), low=min(o, c), volume=volume)


def path(start, logs, starts=None):
    """Bars from log closes; bar i opens at the previous close. `starts` overrides the start times (gaps)."""
    out, prev = [], math.exp(logs[0])
    for i, x in enumerate(logs):
        s = start + i * M if starts is None else starts[i]
        c = math.exp(x)
        out.append(bar(s, prev, c))
        prev = c
    return out


def run(bars, window="1h"):
    r = run_card(BarrierRace(window), bars, references={}, declarations={}, venue="bitflyer", symbol="FX_BTC_JPY")
    return [float(e) for e in r.exposure]


def warm_logs():
    """61 bars (index 0..60) alternating +-A, ending at log 0. The bar of index 60 ends at T0 + 61 min, the first
    time the 1-hour window has elapsed since the first call (end T0 + 1 min): the first race starts there with
    anchor 0 and width W0 (returns of index 1..60, 60 of them, all of size A)."""
    return [0.0 if i % 2 == 0 else A for i in range(61)]


def test_mouth():
    c = BarrierRace("1h")
    assert c.name == "c7_barrier_race"
    assert tuple(c.requires) == ()
    assert WINDOWS == {"1h": H, "1d": 24 * H, "1w": 7 * 24 * H}
    for bad in (None, "", "2h", 60, "1H"):
        with pytest.raises(CardError):
            BarrierRace(bad)
    with pytest.raises(TypeError):
        BarrierRace()  # no default window: the source has none


def test_i1_i4_upper_hit_sells_lower_hit_buys():
    """I-1・I-4: a move of at least the width up from the anchor -> -1 (bet on the reversal); a move of at least
    the (new) width down from the new anchor -> +1."""
    logs = warm_logs() + [0.02, 0.02, 0.019, -0.03]
    ex = run(path(T0, logs))
    assert ex[:61] == [0.0] * 61  # warm-up and the race start: no hit yet
    assert ex[61] == -1.0  # 0.02 - 0 >= W0 (0.00775)
    assert ex[62] == -1.0 and ex[63] == -1.0  # no new hit: held
    # the race started at index 61 has anchor 0.02 and width sqrt(59 A^2 + 0.02^2) ~ 0.0215 (window of index 2..61)
    w1 = math.sqrt(59 * A * A + 0.02 ** 2)
    assert -0.03 - 0.02 <= -w1
    assert ex[64] == 1.0


def test_i1_hit_is_measured_from_the_anchor_not_bar_by_bar():
    """I-1: steps each smaller than the width add up; the hit is at the first close at or beyond anchor + w."""
    step = W0 / 3.5
    logs = warm_logs() + [step * (i + 1) for i in range(4)]
    ex = run(path(T0, logs))
    assert ex[61:64] == [0.0, 0.0, 0.0]  # 1, 2, 3 steps < W0
    assert ex[64] == -1.0  # 4 steps = 1.14 W0


def test_i2_width_is_fixed_within_a_race_and_set_again_at_each_hit():
    """I-2: the width does not follow the window while a race runs (the window here goes flat, so a width
    recomputed each bar would be 0.003 and hit at once); at a hit the next race takes the window's width then."""
    logs = warm_logs() + [0.0] * 61 + [0.003, 0.009, 0.009 - 0.0072]
    ex = run(path(T0, logs))
    assert all(e == 0.0 for e in ex[:123])
    assert ex[122] == 0.0  # move 0.003 < W0: no hit with the race's own width
    assert ex[123] == -1.0  # move 0.009 >= W0
    w1 = math.sqrt(0.003 ** 2 + 0.006 ** 2)  # the window at index 123 holds only these two non-zero returns
    assert w1 <= 0.0072 < W0  # so the next move hits with w1 and would not with the first race's width
    assert ex[124] == 1.0


def test_i3_reversal_and_continuation_take_opposite_sides_of_the_next_race():
    """I-3: after the same first hit (-1), a reversal (the lower barrier next) turns the card to +1, while a
    continuation (the upper barrier again) keeps it at -1: the measured mean of the -1 race is the reversal's
    gain or the continuation's loss."""
    head = warm_logs() + [0.02]
    rev = run(path(T0, head + [0.02 - 0.03]))
    cont = run(path(T0, head + [0.02 + 0.03]))
    assert rev[61] == cont[61] == -1.0
    assert rev[62] == 1.0
    assert cont[62] == -1.0


def test_warm_up_holds_zero():
    """C-5: no race starts until the window has elapsed since the first call; a big move inside it is no hit."""
    logs = [0.0, A] * 20 + [0.5] + [0.5 + (A if i % 2 else 0.0) for i in range(19)] + [0.5, 0.5]
    ex = run(path(T0, logs))
    assert len(ex) == 62 and all(e == 0.0 for e in ex)


def test_zero_width_starts_no_race_until_the_window_moves():
    """C-6: a flat window gives w = 0: no race (exposure kept); the first bar with a move in the window starts it."""
    logs = [0.0] * 61 + [0.01, 0.01 + 0.0101 * math.sqrt(2) + 1e-9]
    ex = run(path(T0, logs))
    assert ex[60] == 0.0  # w = 0 at the first eligible bar
    assert ex[61] == 0.0  # the race starts here (anchor 0.01, w = 0.01): no hit at its own start
    assert ex[62] == -1.0  # 0.0101 * sqrt(2) >= 0.01


def test_window_is_time_not_bar_count():
    """C-2: after a 2-hour gap, the window holds only the return across the gap (older bars fell out), so the
    next race's width is that return alone; a window of the last 60 bars would also hold 59 warm-up returns."""
    logs = warm_logs() + [0.02, 0.02 - 0.0205]
    starts = [T0 + i * M for i in range(61)] + [T0 + (61 + 120 + i) * M for i in range(2)]
    ex = run(path(T0, logs, starts))
    assert ex[61] == -1.0  # 0.02 >= W0: the race started at index 60 ends; the next width is 0.02 (time window)
    w_count = math.sqrt(59 * A * A + 0.02 ** 2)  # what a 60-bar window would give
    assert 0.02 <= 0.0205 < w_count
    assert ex[62] == 1.0  # hit with the time window's width, not with the bar-count one


def test_one_day_variant_warms_up_for_a_day():
    """C-1: the 1-day variant starts its first race only once a day has elapsed since the first call."""
    n = 24 * 60 + 1
    logs = [0.0 if i % 2 == 0 else A for i in range(n)] + [0.1]
    ex = run(path(T0, logs), window="1d")
    assert all(e == 0.0 for e in ex[:n])
    assert ex[n] == -1.0  # 0.1 >= A * sqrt(1440) = 0.0379


def test_card_refuses_a_bar_not_ending_at_t():
    """C-3: the card reads the bar ending at t; anything else stops it."""

    class View:
        now_ns = T0 + 2 * M

        def bars(self, n):
            return [bar(T0, 100.0, 100.0)]  # ends at T0 + 1 min

    with pytest.raises(ValueError):
        BarrierRace("1h").exposure(View())


def test_no_look_ahead():
    """Changing only later bars leaves every earlier exposure unchanged."""
    rng = np.random.default_rng(7)
    n = 400
    logs = list(np.cumsum(rng.normal(0.0, 0.002, n)))
    base = run(path(T0, logs))
    cut = 250
    changed = logs[:cut] + [x + 0.05 * (-1) ** i for i, x in enumerate(logs[cut:])]
    alt = run(path(T0, changed))
    assert alt[:cut] == base[:cut]
    assert alt[cut:] != base[cut:]


def test_same_input_same_output_and_bounds():
    rng = np.random.default_rng(11)
    n = 2 * 24 * 60
    logs = list(np.cumsum(rng.normal(0.0, 0.001, n)))
    a = run(path(T0, logs))
    b = run(path(T0, logs))
    assert a == b
    assert set(a) <= {-1.0, 0.0, 1.0}
    assert all(e == 0.0 for e in a[:60])
    assert -1.0 in a and 1.0 in a
