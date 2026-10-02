"""Card c9 of W4 (清算の連鎖): hand-made small inputs whose exposures are known.

Each test names the item of docs/RESEARCH/cards/c9_liquidation_cascade/INTENT_MAP.md it checks.
Inputs: bitFlyer 1-minute bars [T0 + i min, T0 + (i+1) min) (bar i ends at T0 + (i+1) min); the liquidation
rows (BUY = shorts liquidated, SELL = longs liquidated, per minute) stamped at the START of their minute,
T0 + i min, with lag 60 s (CARD.md 測定の設定), so the row of minute i becomes available at the end of bar i.
"""
from __future__ import annotations

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import SeriesSpec, run_card
from bot.research.cards.library.c9_liquidation_cascade import BUY, HOLDS, MODES, SELL, LiquidationCascade

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z (a test time; the card has no calendar)
DECL = {BUY: {"lag_ns": 60 * NS, "source": "試験の入力"}, SELL: {"lag_ns": 60 * NS, "source": "試験の入力"}}


def run(buy, sell, mode, hold, *, missing=(), no_bar=(), prices=None, extra_rows=None):
    """buy[i], sell[i]: the liquidation quantities of minute i. `missing`: minutes with no row (unknown).
    `no_bar`: minutes with no bitFlyer bar (the card is not called there). Returns {bar index: exposure}."""
    n = len(buy)
    assert len(sell) == n
    idx = [i for i in range(n) if i not in set(no_bar)]
    bars = []
    for i in idx:
        c = 100.0 + i if prices is None else prices[i]
        bars.append(BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M,
                             start_time_ns=T0 + i * M, open=c, close=c, high=c, low=c, volume=1.0))
    rows_b = [(T0 + i * M, float(buy[i])) for i in range(n) if i not in set(missing)]
    rows_s = [(T0 + i * M, float(sell[i])) for i in range(n) if i not in set(missing)]
    if extra_rows is not None:  # rows after the last bar (never available inside the run)
        rows_b += [(T0 + (n + k) * M, float(v)) for k, v in enumerate(extra_rows)]
        rows_s += [(T0 + (n + k) * M, float(v)) for k, v in enumerate(extra_rows)]
    refs = {BUY: reference_series(BUY, rows_b, declarations=DECL),
            SELL: reference_series(SELL, rows_s, declarations=DECL)}
    r = run_card(LiquidationCascade(mode, hold), bars, references=refs, declarations=DECL, venue="bitflyer",
                 symbol="FX_BTC_JPY")
    return dict(zip(idx, (float(x) for x in r.exposure)))


def z(n):
    return [0.0] * n


def test_mouth():
    c = LiquidationCascade("ride_fade", "1h")
    assert c.name == "c9_liquidation_cascade_ride_fade_1h"
    assert tuple(c.requires) == (SeriesSpec(BUY, 60 * NS), SeriesSpec(SELL, 60 * NS))
    assert set(MODES) == {"ride", "fade", "ride_fade"}
    assert set(HOLDS) == {"1m", "1h", "1d", "1w"}
    for bad_mode in ("", "both", None):
        with pytest.raises(ValueError):
            LiquidationCascade(bad_mode, "1h")
    for bad_hold in ("2h", "60s", 3600 * NS):
        with pytest.raises(ValueError):
            LiquidationCascade("ride", bad_hold)


def test_i1_no_liquidation_holds_zero():
    """I-1 (the signal is the forced flow itself): with no liquidation at all, every variant holds 0, whatever
    bitFlyer does."""
    for mode in MODES:
        x = run(z(10), z(10), mode, "1h", prices=[100.0, 120.0, 80.0, 150.0, 60.0, 100.0, 90.0, 300.0, 1.0, 5.0])
        assert set(x.values()) == {0.0}


def test_i2_ride_right_after_a_liquidation_minute():
    """I-2 (直後) and I-6a (乗る): the bar that ends with a liquidation minute holds the push; with hold 1m,
    only that bar (its exposure is carried into the next bar by the execution model, W1 C2)."""
    buy = z(6)
    buy[2] = 5.0
    x = run(buy, z(6), "ride", "1m")
    assert [x[i] for i in range(6)] == [0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    x = run(z(6), buy, "ride", "1m")  # the same quantity as SELL (longs liquidated, forced selling)
    assert [x[i] for i in range(6)] == [0.0, 0.0, -1.0, 0.0, 0.0, 0.0]


def test_i4_direction_is_the_sign_of_the_chain_net():
    """I-4: the push of a chain is sign(sum over the chain of BUY - SELL), not of the latest minute alone."""
    buy, sell = z(7), z(7)
    buy[2], sell[3], sell[4] = 5.0, 3.0, 4.0  # cumulative net: +5, +2, -2
    x = run(buy, sell, "ride", "1m")
    assert [x[i] for i in range(7)] == [0.0, 0.0, 1.0, 1.0, -1.0, 0.0, 0.0]


def test_i3_chain_is_consecutive_minutes_and_ends_at_the_first_quiet_minute():
    """I-3 (連鎖) and I-5 (燃料が尽きた = the chain ends): minutes 2, 3 form one chain; minute 4 is quiet, so the
    chain ends at the end of bar 4 and the fade starts there. A later liquidation (minute 6) starts a new chain
    whose net does not carry the first one's."""
    buy, sell = z(9), z(9)
    buy[2], buy[3], sell[6] = 2.0, 2.0, 1.0
    x = run(buy, sell, "fade", "1m")
    assert [x[i] for i in range(9)] == [0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0]


def test_i6b_fade_holds_for_the_hold_and_not_during_the_chain():
    """I-6b (燃料が尽きた後は転換の側に持つ) and the hold variants: hold 1h after the end at T0 + 5 min holds bars
    4..63 (t - end < 1 h) and drops at bar 64."""
    n = 70
    buy = z(n)
    buy[2] = 1.0
    buy[3] = 1.0
    x = run(buy, z(n), "fade", "1h")
    assert x[2] == 0.0 and x[3] == 0.0  # nothing while the chain runs
    assert all(x[i] == -1.0 for i in range(4, 64))
    assert all(x[i] == 0.0 for i in range(64, n))


def test_i6c_ride_fade_is_the_owner_sentence():
    """I-6c (L-262: 続くなら乗る、続かないなら逆張り): +push while the chain runs, -push from its end."""
    buy = z(8)
    buy[2] = buy[3] = 3.0
    x = run(buy, z(8), "ride_fade", "1m")
    assert [x[i] for i in range(8)] == [0.0, 0.0, 1.0, 1.0, -1.0, 0.0, 0.0, 0.0]


def test_new_chain_ends_the_fade_hold():
    """＋ (a new chain ends the hold after the previous one): fade 1h after chain A (minute 2), chain B at
    minute 6: fade mode drops to 0 while B runs, then fades B."""
    buy, sell = z(10), z(10)
    buy[2] = 1.0
    sell[6] = 1.0
    x = run(buy, sell, "fade", "1h")
    assert [x[i] for i in range(10)] == [0.0, 0.0, 0.0, -1.0, -1.0, -1.0, 0.0, 1.0, 1.0, 1.0]


def test_tie_holds_zero():
    """＋ (tie): a chain whose net is 0 has no push; every variant holds 0."""
    buy, sell = z(6), z(6)
    buy[2], sell[2] = 4.0, 4.0
    for mode in MODES:
        x = run(buy, sell, mode, "1h")
        assert set(x.values()) == {0.0}


def test_unknown_minute_clears_the_chain():
    """＋ (unknown minute): a minute with no row clears the chain and holds; the end that follows it is not a
    known end, so no fade."""
    buy = z(8)
    buy[2] = buy[3] = 1.0
    x = run(buy, z(8), "ride_fade", "1h", missing=(4,))
    assert [x[i] for i in range(8)] == [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    x = run(buy, z(8), "ride", "1h", missing=(4,))
    assert x[4] == 0.0 and x[5] == 0.0


def test_gap_in_bitflyer_bars_does_not_skip_liquidation_minutes():
    """＋ (walk every minute): the chain at minute 3 and its end at minute 4 fall in a gap of the bitFlyer bars
    (no bars 3, 4). At bar 5 the card has walked both minutes: the fade started at T0 + 5 min holds."""
    buy = z(8)
    buy[3] = 2.0
    x = run(buy, z(8), "fade", "1h", no_bar=(3, 4))
    assert 3 not in x and 4 not in x
    assert x[5] == -1.0 and x[6] == -1.0
    x = run(buy, z(8), "ride", "1h", no_bar=(3, 4))
    assert x[5] == 1.0


def test_no_lookahead_rows_after_t_change_nothing_before():
    """未来を読まない: changing the rows of minutes k.. (available at the end of bar k at the earliest) leaves
    the exposures of bars 0..k-1 unchanged, for every variant; rows after the last bar never matter."""
    rng = np.random.default_rng(7)
    n = 40
    base_b = [float(v) for v in rng.integers(0, 3, n) * (rng.random(n) < 0.4)]
    base_s = [float(v) for v in rng.integers(0, 3, n) * (rng.random(n) < 0.4)]
    for mode in MODES:
        for hold in ("1m", "1h"):
            a = run(base_b, base_s, mode, hold)
            for k in (5, 17, 30):
                b2 = base_b[:k] + [9.0 - v for v in base_b[k:]]
                s2 = base_s[:k] + [0.0] * (n - k)
                c = run(b2, s2, mode, hold)
                assert [c[i] for i in range(k)] == [a[i] for i in range(k)]
            d = run(base_b, base_s, mode, hold, extra_rows=[50.0, 0.0, 7.0])
            assert d == a


def test_same_input_same_output():
    """W1 C1: no random numbers inside the card."""
    buy, sell = z(12), z(12)
    buy[1], sell[2], buy[5], sell[9] = 1.0, 3.0, 2.0, 1.0
    for mode in MODES:
        assert run(buy, sell, mode, "1h") == run(buy, sell, mode, "1h")


def test_negative_quantity_is_refused():
    buy = z(4)
    buy[1] = -1.0
    with pytest.raises(Exception):
        run(buy, z(4), "ride", "1m")
