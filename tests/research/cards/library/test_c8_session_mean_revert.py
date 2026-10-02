"""Card 8 of W4 (セッション内平均回帰): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c8_session_mean_revert/INTENT_MAP.md it checks.
Inputs: bitFlyer FX_BTC_JPY 1-minute bars [start, start + 1 min), received at their end. The card uses no
reference series. Test prices are whole numbers, so the session means below are exact in floating point (a test input;
whether the store's closes are whole yen is not verified, INTENT_MAP.md C-11).
"""
from __future__ import annotations

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.research.cards import run_card
from bot.research.cards.card import CardError
from bot.research.cards.library.c8_session_mean_revert import SESSIONS, SessionMeanRevert, session_index

NS = 1_000_000_000
M = 60 * NS
H = 60 * M
S_JST = 1_672_585_200 * NS  # 2023-01-01T15:00:00Z = 2023-01-02 00:00 JST (a jst_day session start; a test time)
S_BF = 1_672_599_600 * NS  # 2023-01-01T19:00:00Z = 2023-01-02 04:00 JST (a bf_maint session start)


def bar(start, o, c, volume=1.0):
    return BarEvent(received_time_ns=start + M, exchange_time_ns=start + M, start_time_ns=start, open=o, close=c,
                    high=max(o, c), low=min(o, c), volume=volume)


def path(start, closes, starts=None):
    """Bars from closes; bar i opens at the previous close. `starts` overrides the start times (gaps)."""
    out, prev = [], closes[0]
    for i, c in enumerate(closes):
        s = start + i * M if starts is None else starts[i]
        out.append(bar(s, prev, c))
        prev = c
    return out


def run(bars, session="jst_day"):
    r = run_card(SessionMeanRevert(session), bars, references={}, declarations={}, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return [float(e) for e in r.exposure]


def test_mouth():
    """I-1 (variants of the session clock), I-6: name, no reference series, no default session."""
    c = SessionMeanRevert("jst_day")
    assert c.name == "c8_session_mean_revert_jst_day"
    assert SessionMeanRevert("bf_maint").name == "c8_session_mean_revert_bf_maint"
    assert tuple(c.requires) == ()
    assert SESSIONS == {"jst_day": 9 * H, "bf_maint": 5 * H}
    for bad in (None, "", "jst", "JST_DAY", 1, "1d"):
        with pytest.raises(CardError):
            SessionMeanRevert(bad)
    with pytest.raises(TypeError):
        SessionMeanRevert()  # no default session: the source has none


def test_session_index_puts_the_start_in_the_new_session():
    """I-1: jst_day sessions start at 15:00 UTC, bf_maint sessions at 19:00 UTC."""
    for name, s in (("jst_day", S_JST), ("bf_maint", S_BF)):
        off = SESSIONS[name]
        assert session_index(s, off) == session_index(s - 1, off) + 1
        assert session_index(s + 24 * H - 1, off) == session_index(s, off)
        assert session_index(s + 24 * H, off) == session_index(s, off) + 1


def test_i4_holds_against_the_deviation_from_the_session_mean():
    """I-4・I-3: below the session's mean -> +1 (back up to it), above -> -1."""
    ex = run(path(S_JST, [100, 104, 98, 101, 99]))
    # means: 100, 102, 100.67, 100.75, 100.4
    assert ex == [0.0, -1.0, 1.0, -1.0, 1.0]


def test_i3_level_is_the_mean_of_the_session_so_far():
    """I-3: an earlier move in the session moves the level (100, 200, then 150 sits on the mean 150 -> 0), and
    the level is the mean, not the session's first price (150 is above 100) nor the last price."""
    ex = run(path(S_JST, [100, 200, 150, 140]))
    assert ex[2] == 0.0  # (100 + 200 + 150) / 3 = 150
    assert ex[3] == 1.0  # 140 < (100 + 200 + 150 + 140) / 4 = 147.5, though above the session's first price 100


def test_i2_level_starts_again_at_each_session():
    """I-2: prices of the previous session do not enter the level of this one; the same session gives the same
    exposures with or without a different previous session before it."""
    prev = [1000] * 30  # a previous session far above (bars ending S_JST - 29 min .. S_JST)
    this = [100, 104, 98, 101, 99]
    alone = run(path(S_JST, this))
    starts = [S_JST - (30 - i) * M for i in range(30)] + [S_JST + i * M for i in range(5)]
    both = run(path(S_JST, prev + this, starts))
    assert both[30:] == alone


def test_first_bar_of_a_session_and_a_close_on_the_mean_give_zero():
    """C-6: the first bar's mean is its own close; a close exactly on the mean gives 0 (no sign)."""
    ex = run(path(S_JST, [100, 100, 100, 103, 97, 100]))
    assert ex[:3] == [0.0, 0.0, 0.0]
    assert ex[3] == -1.0 and ex[4] == 1.0
    assert ex[5] == 0.0  # mean (100 * 4 + 103 + 97) / 6 = 100


@pytest.mark.parametrize("session,s,other", [("jst_day", S_JST, S_BF), ("bf_maint", S_BF, S_JST)])
def test_i5_no_holding_across_the_session_end(session, s, other):
    """I-5 (「セッション内」): the bar ending exactly at the session end gives 0 (its fill would lie in the next
    session); the next bar is the first of a new session (its own mean). The other variant's boundary is no
    boundary for this one."""
    closes = [100, 100, 100, 110, 120, 120]
    starts = [s - (4 - i) * M for i in range(6)]  # ends s - 3 min .. s + 2 min; the bar of index 3 ends at s
    ex = run(path(s, closes, starts), session)
    assert ex[2] == 0.0  # mean 100
    assert ex[3] == 0.0  # 110 > mean 102.5, but the bar ends at the session end
    assert ex[4] == 0.0  # the first bar of the new session: mean = 120
    assert ex[5] == 0.0  # mean 120
    # the same closes across the other variant's boundary: one session, so the bar ending there is not forced to 0
    starts_o = [other - (4 - i) * M for i in range(6)]
    ex_o = run(path(other, closes, starts_o), session)
    assert ex_o[3] == -1.0  # 110 > 102.5
    assert ex_o[4] == -1.0 and ex_o[5] == -1.0  # 120 > 106, 120 > 108.33: the level was not reset


def test_bar_belongs_to_the_session_of_its_start():
    """C-4: the bar [s - 1 min, s) is the last of the old session (its close enters the old mean), the bar
    [s, s + 1 min) the first of the new one."""
    closes = [100, 90, 200]
    starts = [S_JST - 2 * M, S_JST - M, S_JST]
    ex = run(path(S_JST, closes, starts))
    assert ex[0] == 0.0
    assert ex[1] == 0.0  # ends at S_JST: the session end
    assert ex[2] == 0.0  # 200 alone in the new session (the old prices 100, 90 would make it -1)


def test_empty_minutes_do_not_enter_the_mean():
    """C-7: the level is the mean over the bars the card is called on (bars with a trade), not over time: over the 5 bars with a trade the mean is 108, so 110 is above it -> -1. A mean that filled the
    56 empty minutes with the last price 130 would be far above 110 and give +1."""
    closes = [100, 100, 100, 130, 110]
    starts = [S_JST + i * M for i in range(4)] + [S_JST + 60 * M]
    ex = run(path(S_JST, closes, starts))
    assert ex[3] == -1.0  # 130 > 107.5
    assert ex[4] == -1.0


def test_card_refuses_a_bar_not_ending_at_t():
    """C-2: the card reads the bar ending at t; anything else stops it."""

    class View:
        now_ns = S_JST + 2 * M

        def bars(self, n):
            return [bar(S_JST, 100.0, 100.0)]  # ends at S_JST + 1 min

    with pytest.raises(ValueError):
        SessionMeanRevert("jst_day").exposure(View())


def test_no_look_ahead():
    """Changing only later bars leaves every earlier exposure unchanged (within the same session too)."""
    rng = np.random.default_rng(7)
    n = 600
    closes = list(np.round(100_000 + np.cumsum(rng.normal(0.0, 50.0, n))))
    base = run(path(S_JST, closes))
    cut = 300
    changed = closes[:cut] + [x + 5_000.0 * (-1) ** i for i, x in enumerate(closes[cut:])]
    alt = run(path(S_JST, changed))
    assert alt[:cut] == base[:cut]
    assert alt[cut:] != base[cut:]


@pytest.mark.parametrize("session", ["jst_day", "bf_maint"])
def test_same_input_same_output_and_bounds(session):
    rng = np.random.default_rng(11)
    n = 2 * 24 * 60
    closes = list(np.round(3_000_000 + np.cumsum(rng.normal(0.0, 1_000.0, n))))
    a = run(path(S_JST - 7 * H, closes), session)
    b = run(path(S_JST - 7 * H, closes), session)
    assert a == b
    assert set(a) <= {-1.0, 0.0, 1.0}
    assert -1.0 in a and 1.0 in a
