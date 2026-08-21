"""Additive engine option used by scripts/research_legacy_elements.py (H2):

  * ``stop_mode="wick_invalidation"`` + ``stop_window_bars`` — a structural
    protective stop whose level is the extreme of the trailing N COMPLETED
    bars' wicks, frozen at the fill, breached only by a CLOSE beyond it and
    executed at the next bar's open with taker costs.

The option must be strictly additive: with its default (``stop_mode="fixed"``)
the engine has to produce bit-identical results to before, which the last test
in this file pins down.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.strategy.base import Signal, SignalType, Strategy

NO_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0)
FX_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0.02, spread_pct=0.0235)

FLAT = (100.0, 100.5, 99.5, 100.0)


def candles_from(rows):
    a = np.array(rows, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3], "volume": np.ones(len(a))})


class Scripted(Strategy):
    """Emits the scripted signal on the bar index given by the script key."""

    def __init__(self, params=None):
        super().__init__(params)
        self.script = params["script"]

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        sig = self.script.get(len(candles) - 1)
        return Signal(sig, "scripted") if sig else Signal(SignalType.HOLD, "")


def reasons(res):
    return [t["reason"] for t in res.trade_log if t["side"].startswith("CLOSE_")]


WICK = dict(stop_mode="wick_invalidation", stop_loss_pct=None)


# ---------------------------------------------------------------------------
# level construction
# ---------------------------------------------------------------------------
def test_long_level_is_the_min_low_of_the_n_bars_behind_the_fill():
    """N=3, fill on bar 3 -> level = min(low) over bars 0..2 = 98.0.

    Bar 4 closes at 98.5, still above the level -> hold. Bar 5 closes at 97.9,
    below it -> exit at bar 6's open.
    """
    candles = candles_from([
        (100, 100.5, 98.0, 100),     # bar 0  (low 98.0 = the deepest wick)
        (100, 100.5, 99.0, 100),     # bar 1
        (100, 100.5, 99.4, 100),     # bar 2: BUY signal (last completed bar)
        (100, 100.5, 99.5, 100),     # bar 3: fill at open 100
        (100, 100.5, 97.0, 98.5),    # bar 4: wick under the level, close above
        (98.5, 98.6, 97.5, 97.9),    # bar 5: CLOSE below 98.0 -> arms the stop
        (98.0, 98.2, 97.8, 98.0),    # bar 6: exit at open 98.0
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    assert reasons(res) == ["wick_stop"]
    closes = [t for t in res.trade_log if t["side"].startswith("CLOSE_")]
    assert closes[0]["bar"] == 6 and closes[0]["price"] == pytest.approx(98.0)
    assert res.trade_pnls[0] == pytest.approx(1000 * (98.0 - 100.0) / 100.0, rel=1e-9)


def test_short_level_is_the_max_high_of_the_n_bars_behind_the_fill():
    candles = candles_from([
        (100, 102.0, 99.5, 100),     # bar 0  (high 102.0 = the tallest wick)
        (100, 100.6, 99.5, 100),     # bar 1
        (100, 100.5, 99.5, 100),     # bar 2: SELL signal
        (100, 100.5, 99.5, 100),     # bar 3: short filled at open 100
        (100, 103.0, 99.5, 101.0),   # bar 4: wick over the level, close under
        (101, 102.5, 100.5, 102.1),  # bar 5: CLOSE above 102.0 -> arms the stop
        (102, 102.4, 101.8, 102.0),  # bar 6: cover at open 102.0
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.SELL}}), candles,
                       costs=NO_COST, allow_short=True, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    assert reasons(res) == ["wick_stop"]
    assert res.trade_pnls[0] == pytest.approx(1000 * (100.0 - 102.0) / 100.0, rel=1e-9)


def test_window_size_changes_the_level():
    """Same data, N=1 vs N=3: the shallower window stops out, the deeper does not."""
    rows = [
        (100, 100.5, 98.0, 100),     # bar 0: deep wick, only inside an N=3 window
        (100, 100.5, 99.6, 100),     # bar 1
        (100, 100.5, 99.4, 100),     # bar 2: BUY signal; N=1 level = 99.4
        (100, 100.5, 99.5, 100),     # bar 3: fill
        (100, 100.5, 99.0, 99.2),    # bar 4: close 99.2 < 99.4 but > 98.0
        (99.2, 99.3, 99.0, 99.2),    # bar 5: N=1 exits here at open 99.2
        FLAT, FLAT,
    ]
    candles = candles_from(rows)
    kw = dict(costs=NO_COST, order_notional_jpy=1000, **WICK)
    tight = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                         stop_window_bars=1, **kw)
    wide = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                        stop_window_bars=3, **kw)
    assert reasons(tight) == ["wick_stop"]
    assert wide.trade_pnls == []          # never breached, still open at the end


def test_window_never_reaches_bars_at_or_after_the_fill():
    """The fill bar's own (very deep) low must not become the level: bar 3's
    low 90 would put the stop far away, bars 0..2 put it at 99.4."""
    candles = candles_from([
        (100, 100.5, 99.4, 100),     # bar 0
        (100, 100.5, 99.6, 100),     # bar 1
        (100, 100.5, 99.9, 100),     # bar 2: BUY signal
        (100, 100.5, 90.0, 100),     # bar 3: fill; huge low, must be ignored
        (100, 100.5, 99.0, 99.3),    # bar 4: close 99.3 < 99.4 -> arms
        (99.3, 99.4, 99.0, 99.3),    # bar 5: exit at open 99.3
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    assert reasons(res) == ["wick_stop"]
    assert res.trade_pnls[0] == pytest.approx(1000 * (99.3 - 100.0) / 100.0, rel=1e-9)


def test_level_is_frozen_and_never_trails():
    """A new, much lower low after entry does not move the stop down."""
    candles = candles_from([
        (100, 100.5, 99.4, 100),     # bar 0
        (100, 100.5, 99.6, 100),     # bar 1
        (100, 100.5, 99.5, 100),     # bar 2: BUY signal -> level 99.4 (N=3)
        (100, 100.5, 99.5, 100),     # bar 3: fill at 100
        (100, 100.6, 95.0, 100.2),   # bar 4: new low 95 -- a trailing stop would move
        (100.2, 100.6, 99.0, 99.3),  # bar 5: close 99.3 < the FROZEN 99.4 -> arms
        (99.3, 99.4, 99.0, 99.3),    # bar 6: exit at open 99.3
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    closes = [t for t in res.trade_log if t["side"].startswith("CLOSE_")]
    assert reasons(res) == ["wick_stop"] and closes[0]["bar"] == 6


# ---------------------------------------------------------------------------
# breach semantics + execution
# ---------------------------------------------------------------------------
def test_a_wick_through_the_level_is_not_an_exit():
    """The construction's whole point: only a CLOSE beyond the level counts."""
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY signal -> level 99.4
        (100, 100.5, 99.5, 100),     # fill
        (100, 100.5, 95.0, 100.0),   # deep wick to 95, closes back at 100
        (100, 100.5, 96.0, 99.5),    # another wick, close 99.5 still above 99.4
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    assert res.trade_pnls == [] and reasons(res) == []


def test_close_exactly_at_the_level_is_not_a_breach():
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY -> level 99.4
        (100, 100.5, 99.5, 100),     # fill
        (100, 100.5, 99.0, 99.4),    # close EXACTLY 99.4 -> not "beyond"
        (99.4, 99.5, 99.3, 99.4),
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    assert res.trade_pnls == []


def test_the_entry_bars_own_close_can_arm_the_stop():
    """Entry fills at the open of bar 3; bar 3's close is later information and
    is allowed to breach, exiting at bar 4's open."""
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY -> level 99.4
        (100, 100.5, 99.0, 99.1),    # bar 3: fill at open 100, closes below 99.4
        (99.1, 99.2, 98.9, 99.0),    # bar 4: exit at open 99.1
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    closes = [t for t in res.trade_log if t["side"].startswith("CLOSE_")]
    assert reasons(res) == ["wick_stop"]
    assert closes[0]["bar"] == 4 and closes[0]["price"] == pytest.approx(99.1)


def test_wick_stop_exit_pays_taker_costs():
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY -> level 99.4
        (100, 100.5, 99.5, 100),     # fill at buy_price(100)
        (100, 100.5, 99.0, 99.3),    # arms
        (99.3, 99.4, 99.0, 99.3),    # exit at sell_price(99.3)
        FLAT,
    ])
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=FX_COST, order_notional_jpy=1000,
                       stop_window_bars=3, **WICK)
    entry = FX_COST.buy_price(100.0)
    exit_px = FX_COST.sell_price(99.3)
    size = 1000 / entry
    assert res.trade_pnls[0] == pytest.approx((exit_px - entry) * size, rel=1e-9)


def test_wick_stop_overrides_a_pending_signal_on_the_same_bar():
    """Bar 4 both breaches (via its close) and carries a CLOSE signal; the two
    would fill on bar 5 at the same open, so the logged reason decides. The
    structural stop is the one that fires."""
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY -> level 99.4
        (100, 100.5, 99.5, 100),     # fill
        (100, 100.5, 99.0, 99.3),    # bar 4: breach AND a CLOSE signal
        (99.3, 99.4, 99.0, 99.3),    # bar 5
        FLAT,
    ])
    res = run_backtest(
        Scripted({"script": {2: SignalType.BUY, 4: SignalType.CLOSE}}), candles,
        costs=NO_COST, order_notional_jpy=1000, stop_window_bars=3, **WICK)
    assert reasons(res) == ["wick_stop"]
    assert len(res.trade_pnls) == 1


def test_signal_exit_still_works_when_the_level_is_never_breached():
    candles = candles_from([
        (100, 100.5, 99.4, 100),
        (100, 100.5, 99.6, 100),
        (100, 100.5, 99.5, 100),     # BUY -> level 99.4
        (100, 100.5, 99.5, 100),     # fill at 100
        (100, 100.5, 99.5, 100),     # bar 4: CLOSE signal
        (101, 101.5, 100.5, 101),    # bar 5: taker exit at open 101
        FLAT,
    ])
    res = run_backtest(
        Scripted({"script": {2: SignalType.BUY, 4: SignalType.CLOSE}}), candles,
        costs=NO_COST, order_notional_jpy=1000, stop_window_bars=3, **WICK)
    assert reasons(res) == ["signal"]
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)


def test_time_exit_still_applies_in_wick_mode():
    candles = candles_from([FLAT] * 3 + [FLAT] * 6)
    res = run_backtest(Scripted({"script": {2: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       stop_window_bars=3, max_hold_bars=2, **WICK)
    assert reasons(res) == ["time_exit"]


# ---------------------------------------------------------------------------
# validation + the additivity guarantee
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kwargs", [
    {"stop_mode": "nonsense"},
    {"stop_mode": "wick_invalidation"},                          # no window
    {"stop_mode": "wick_invalidation", "stop_window_bars": 0},   # non-positive
    {"stop_mode": "wick_invalidation", "stop_window_bars": 3,
     "stop_loss_pct": 0.5},                                      # stacked stops
    {"stop_window_bars": 3},                                     # without opting in
])
def test_invalid_options_are_rejected(kwargs):
    candles = candles_from([FLAT] * 5)
    with pytest.raises(ValueError):
        run_backtest(Scripted({"script": {}}), candles, **kwargs)


def test_defaults_are_bit_identical_to_passing_nothing():
    """The additivity guarantee every existing caller depends on."""
    rng = np.random.default_rng(20260821)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 300)))
    candles = candles_from([(p, p * 1.004, p * 0.996, p) for p in px])
    script = {i: (SignalType.BUY if i % 2 else SignalType.SELL)
              for i in range(1, 300, 23)}
    kw = dict(costs=FX_COST, allow_short=True, order_notional_jpy=1000,
              stop_loss_pct=0.5, swap_daily_pct=0.06)
    base = run_backtest(Scripted({"script": script}), candles, **kw)
    explicit = run_backtest(Scripted({"script": script}), candles,
                            stop_mode="fixed", stop_window_bars=None, **kw)
    assert base.metrics.as_dict() == explicit.metrics.as_dict()
    assert base.trade_pnls == explicit.trade_pnls
    assert base.trade_log == explicit.trade_log
    assert len(base.trade_pnls) > 5


def test_wick_mode_actually_changes_the_outcome_on_the_same_fixture():
    """Guards against the option being silently inert."""
    rng = np.random.default_rng(11)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 300)))
    candles = candles_from([(p, p * 1.004, p * 0.996, p) for p in px])
    script = {i: (SignalType.BUY if i % 2 else SignalType.SELL)
              for i in range(1, 300, 23)}
    kw = dict(costs=FX_COST, allow_short=True, order_notional_jpy=1000,
              swap_daily_pct=0.06)
    fixed = run_backtest(Scripted({"script": script}), candles,
                         stop_loss_pct=0.5, **kw)
    wick = run_backtest(Scripted({"script": script}), candles,
                        stop_window_bars=6, **WICK, **kw)
    assert wick.trade_pnls != fixed.trade_pnls
    assert "wick_stop" in reasons(wick)
    assert "stop_loss" not in reasons(wick)
