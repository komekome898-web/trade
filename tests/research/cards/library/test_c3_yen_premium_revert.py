"""Card 3 of W4 (円の上乗せの戻り): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c3_yen_premium_revert/INTENT_MAP.md it checks.
Inputs: bitFlyer 1-minute bars [T0 + i min, T0 + (i+1) min); the reference rows (Binance close, USDJPY close)
stamped at the START of their minute, T0 + i min, with lag 60 s (as in the stores: open_time, not shifted;
CARD.md 測定の設定), so the row of minute i becomes available at the end of bar i. Binance is read for the
same minute only; USDJPY as-of (the newest row available at t; the lead's answer of 2026-10-02).
"""
from __future__ import annotations

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import SeriesSpec, run_card
from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS, WINDOWS, YenPremiumRevert

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z (a test time; the card has no calendar)
DECL = {OVERSEAS: {"lag_ns": 60 * NS, "source": "試験の入力"}, FX: {"lag_ns": 60 * NS, "source": "試験の入力"}}

# 60 earlier premiums (bars 0..59) of ln(1 + (i % 10) * 1e-4): digits 0..9, then the bar under test (60).
BASE = [(i % 10) * 1e-4 for i in range(60)]


def run(eps, *, bf_scale=1.0, ov=None, fx=None, opens=None, missing_fx=(), missing_ov=(), window="1h"):
    """bitFlyer close_i = 100 * bf_scale * (1 + eps_i), Binance close 1.0 * bf_scale, USDJPY 100.0 unless
    given; so the premium is ln(1 + eps_i). Returns the exposures per bar."""
    n = len(eps)
    ov = [1.0 * bf_scale] * n if ov is None else ov
    fx = [100.0] * n if fx is None else fx
    bars = []
    for i, e in enumerate(eps):
        c = 100.0 * bf_scale * (1.0 + e)
        o = c if opens is None else opens[i]
        bars.append(BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M,
                             start_time_ns=T0 + i * M, open=o, close=c, high=max(o, c), low=min(o, c), volume=1.0))
    ends = [T0 + i * M for i in range(n)]  # row times: the start of each minute
    refs = {OVERSEAS: reference_series(OVERSEAS, [(t, v) for k, (t, v) in enumerate(zip(ends, ov))
                                                  if k not in set(missing_ov)], declarations=DECL),
            FX: reference_series(FX, [(t, v) for k, (t, v) in enumerate(zip(ends, fx)) if k not in set(missing_fx)],
                                 declarations=DECL)}
    r = run_card(YenPremiumRevert(window), bars, references=refs, declarations=DECL, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return r.exposure


def test_mouth():
    c = YenPremiumRevert("1d")
    assert c.name == "c3_yen_premium_revert_1d"
    assert tuple(c.requires) == (SeriesSpec(OVERSEAS, 60 * NS), SeriesSpec(FX, 60 * NS))
    assert set(WINDOWS) == {"1h", "1d", "1w"}
    for bad in ("2h", "60m", 3600 * NS):
        with pytest.raises(ValueError):
            YenPremiumRevert(bad)


def test_i6a_high_premium_sells_low_premium_buys():
    """I-6a: the direction is the one that closes the premium."""
    assert run(BASE + [5e-3])[-1] == -1.0
    assert run(BASE + [-5e-3])[-1] == 1.0


def test_i7_size_grows_with_distance_and_matches_hand_count():
    """I-7: the further outside the recent distribution, the larger the exposure; exact value by hand.
    Window of bar 60 (1h): bars 1..59 (bar 0 ends exactly at t - 1h and is out). Their digits: 0 five times,
    1..9 six times each (n = 59). A premium between 4e-4 and 5e-4 has the digits 0..4 below it:
    5 + 6*4 = 29; q = 29/59; e = 1 - 58/59 = 1/59."""
    e = run(BASE + [4.5e-4])[-1]
    assert e == pytest.approx(1.0 - 2.0 * 29 / 59, abs=1e-12)
    xs = [run(BASE + [x])[-1] for x in (-1e-3, 1.5e-4, 4.5e-4, 7.5e-4, 2e-3)]
    assert all(a > b for a, b in zip(xs, xs[1:]))


def test_ties_take_half():
    """＋ (ties): a premium equal to values in the window counts them as half below."""
    e = run(BASE + [4e-4])[-1]  # digits 0..3 below (5 + 6*3 = 23), the six 4s equal: q = (23 + 3) / 59
    assert e == pytest.approx(1.0 - 2.0 * 26 / 59, abs=1e-12)


def test_i3a_window_is_the_trailing_one():
    """I-3a: only premiums of (t - W, t) make the distribution. An extreme premium at bar 1 (end T0 + 2 min)
    is inside the window of bar 60 and outside that of bar 61."""
    eps = list(BASE)
    eps[1] = 1e-2
    assert run(eps + [5e-3])[-1] == pytest.approx(1.0 - 2.0 * 58 / 59, abs=1e-12)  # one value above
    assert run(eps + [0.0, 5e-3])[-1] == -1.0  # bar 61: bar 1 has left the window


def test_warm_up_and_no_earlier_value_hold_zero():
    """＋ (warm-up): until W has elapsed since the first premium, the card holds 0."""
    x = run(BASE + [5e-3])
    assert np.all(x[:60] == 0.0)
    x = run([0.0, 5e-3], window="1h")
    assert np.all(x == 0.0)


def test_i1a_premium_is_a_ratio():
    """I-1a: the premium is bitFlyer / (Binance x USDJPY): scaling bitFlyer and Binance together, or bitFlyer
    and USDJPY together, leaves every exposure unchanged."""
    eps = BASE + [5e-3, 2e-4, -3e-3]
    a = run(eps)
    np.testing.assert_array_equal(run(eps, bf_scale=2.0), a)
    n = len(eps)
    b = run([2.0 * (1 + e) - 1 for e in eps], fx=[200.0] * n)
    np.testing.assert_allclose(b, a, rtol=0, atol=1e-12)


def test_i1b_i2_usdjpy_and_binance_enter_the_premium():
    """I-1b / I-2: with bitFlyer flat, a cheaper yen-converted overseas price (USDJPY or Binance lower) is a
    higher premium and so a sale of bitFlyer; a dearer one a purchase."""
    n = 61
    flat = [0.0] * n
    fx = [100.0 * (1 - e) for e in BASE] + [100.0 * (1 - 5e-3)]
    assert run(flat, fx=fx)[-1] == -1.0
    fx[-1] = 100.0 * (1 + 5e-3)
    assert run(flat, fx=fx)[-1] == 1.0
    ov = [1.0 - e for e in BASE] + [1.0 + 5e-3]
    assert run(flat, ov=ov)[-1] == 1.0


def test_i1c_uses_the_bitflyer_close():
    """I-1c: the bitFlyer price is the close of the bar that just ended; its open does not enter."""
    eps = BASE + [5e-3, 2e-4]
    a = run(eps)
    b = run(eps, opens=[1.0 + k for k in range(len(eps))])
    np.testing.assert_array_equal(a, b)


def test_binance_same_minute_only():
    """C-4 ＋ (Binance): when Binance has no row for the minute ending at t, the card holds 0 and keeps no
    premium for that minute (an older Binance row is not used)."""
    eps = BASE + [5e-3, 5e-3]
    x = run(eps, missing_ov=(60,))
    assert x[60] == 0.0
    assert x[61] == -1.0  # bar 61 still sees bars 2..59 only below it; bar 60 left nothing in the window
    y = run(BASE + [9e-4, 9e-4], missing_ov=(60,))
    z = run(BASE + [8e-4, 9e-4])
    assert y[61] != z[61]  # with bar 60 kept, its 8e-4 would have been one more value below


def test_usdjpy_as_of_uses_the_last_row_while_the_market_is_shut():
    """I-1b / C-4 (USDJPY as-of): with no USDJPY row for bars 60 and 61 (a closed FX market), the premium is
    formed with the last row (bar 59's 100.0): bitFlyer up 5e-3, then 6e-3 -> premium above the window -> -1.
    The rows that never arrived (here they would have made the premium low) are not read."""
    eps = BASE + [5e-3, 6e-3]
    fx = [100.0] * 60 + [100.0 * (1 + 1e-2)] * 2
    x = run(eps, fx=fx, missing_fx=(60, 61))
    assert x[60] == -1.0 and x[61] == -1.0
    np.testing.assert_array_equal(x, run(eps, fx=[100.0] * 62))  # same as if the last value had been repeated
    assert run(eps, fx=fx)[60] == 1.0  # with the rows present, the dearer yen price makes the premium low


def test_usdjpy_as_of_under_the_60s_lag():
    """C-2 / C-4: under the 60 s lag, the USDJPY row of the minute that ends at t (stamped t - 60 s) is the
    newest available at t and is used; the row of the next minute (stamped t, available t + 60 s) is not."""
    eps = BASE + [0.0, 0.0]
    base = [100.0] * 62
    cheap = list(base)
    cheap[60] = 100.0 * (1 - 5e-3)  # the row of bar 60's own minute: a higher premium at bar 60
    assert run(eps, fx=cheap)[60] == -1.0
    later = list(base)
    later[61] = 100.0 * (1 - 5e-3)  # the row of the next minute: not yet available at the end of bar 60
    np.testing.assert_array_equal(run(eps, fx=later)[:61], run(eps, fx=base)[:61])


def test_rows_with_another_lag_are_refused():
    """C-2: a run whose reference series are declared with a lag other than the card's 60 s is refused."""
    from bot.research.cards import CardError
    decl0 = {OVERSEAS: {"lag_ns": 0, "source": "試験の入力"}, FX: {"lag_ns": 0, "source": "試験の入力"}}
    bars = [BarEvent(received_time_ns=T0 + M, exchange_time_ns=T0 + M, start_time_ns=T0, open=100.0, close=100.0,
                     high=100.0, low=100.0, volume=1.0)]
    refs = {OVERSEAS: reference_series(OVERSEAS, [(T0 + M, 1.0)], declarations=decl0),
            FX: reference_series(FX, [(T0 + M, 100.0)], declarations=decl0)}
    with pytest.raises(CardError):
        run_card(YenPremiumRevert("1h"), bars, references=refs, declarations=decl0, venue="bitflyer",
                 symbol="FX_BTC_JPY")


def test_usdjpy_before_its_first_row_holds_zero():
    """C-4: before any USDJPY row has arrived there is no premium (0, nothing kept); the warm-up (C-7) counts
    from the first premium formed (bar 5 here)."""
    eps = BASE + [5e-3] * 5 + [6e-3]  # bars 0..65
    x = run(eps, missing_fx=tuple(range(5)))
    assert np.all(x[:65] == 0.0)  # bars 0..4: no USDJPY yet; bars 5..64: t - first < 1 h
    assert x[65] == -1.0


def test_no_look_ahead():
    """The rows of a later minute (available only at its end) do not change any earlier exposure."""
    eps = BASE + [5e-3, -4e-3, 2e-4]
    n = len(eps)
    a = run(eps)
    ov = [1.0] * n
    ov[-1] = 0.5  # only the last minute's Binance row differs
    b = run(eps, ov=ov)
    np.testing.assert_array_equal(a[:-1], b[:-1])
    assert a[-1] != b[-1]


def test_same_input_same_output_and_bounds():
    rng = np.random.default_rng(20261002)  # a test input, not a measurement setting
    eps = list(rng.normal(0.0, 1e-3, 400))
    a, b = run(eps), run(eps)
    np.testing.assert_array_equal(a, b)
    assert np.all((a >= -1.0) & (a <= 1.0))
    assert np.any(a != 0.0)


def test_non_positive_price_is_refused():
    with pytest.raises(ValueError):
        run(BASE + [0.0], fx=[100.0] * 60 + [0.0])
