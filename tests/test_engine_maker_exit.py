"""Additive engine options used by the strategy tournament
(scripts/research_tournament.py):

  * ``exit_execution="maker_tp"`` + ``maker_tp_pct`` — a resting maker
    take-profit with traded-through fill semantics and taker fallbacks.
  * ``entry_mask`` / ``entry_sides`` — entry-side-only restrictions.

Both must be strictly additive: with their defaults the engine has to produce
bit-identical results to before, which the last test in this file pins down.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bot.backtest.engine import CostModel, run_backtest
from bot.strategy.base import Signal, SignalType, Strategy

NO_COST = CostModel(taker_fee_pct=0, maker_fee_pct=0, slippage_pct=0, spread_pct=0)
# the tournament's real cost model: 0% fees, 3.2bps taker per side, maker free
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


# ---------------------------------------------------------------------------
# maker take-profit: fill semantics
# ---------------------------------------------------------------------------
def test_long_maker_tp_fills_at_level_when_traded_through():
    candles = candles_from([
        FLAT,
        FLAT,                        # bar 1: BUY signal
        FLAT,                        # bar 2: fill at open 100
        (100, 101.2, 99.9, 100),     # high 101.2 > TP 101 -> maker fill at 101
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)
    assert reasons(res) == ["maker_tp"]


def test_short_maker_tp_fills_on_the_downside():
    candles = candles_from([
        FLAT,
        FLAT,                        # bar 1: SELL signal (short)
        FLAT,                        # bar 2: short filled at open 100
        (100, 100.5, 98.8, 100),     # low 98.8 < TP 99 -> cover at 99
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.SELL}}), candles,
                       costs=NO_COST, allow_short=True, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)
    assert reasons(res) == ["maker_tp"]


def test_touching_the_level_is_not_a_fill():
    """Conservative traded-through rule: high == level must NOT fill."""
    candles = candles_from([
        FLAT,
        FLAT,
        FLAT,                        # long filled at 100
        (100, 101.0, 99.9, 100),     # high EXACTLY 101 == TP level -> no fill
        (100, 100.5, 99.5, 100),
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    assert res.trade_pnls == []          # still open at the end of the data
    assert reasons(res) == []


def test_maker_tp_pays_no_spread_or_slippage_but_entry_does():
    """The maker leg is free; only the taker entry pays the 3.2bps per side."""
    candles = candles_from([
        FLAT,
        FLAT,
        FLAT,                        # taker entry at buy_price(100)
        (100, 102.0, 99.9, 100),     # blows through TP -> maker fill at level
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=FX_COST, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    entry = FX_COST.buy_price(100.0)
    size = 1000 / entry
    assert res.trade_pnls[0] == pytest.approx((entry * 1.01 - entry) * size, rel=1e-9)
    assert res.metrics.total_fees_jpy == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# maker take-profit: no look-ahead, and interaction with the taker fallbacks
# ---------------------------------------------------------------------------
def test_maker_tp_never_fills_on_the_entry_bar():
    """The entry bar's own range must not close the position, even when that
    bar traded far through the TP level (fill is checked strictly after)."""
    candles = candles_from([
        FLAT,
        FLAT,                        # bar 1: BUY signal
        (100, 130.0, 99.9, 100),     # bar 2: entry bar, high 130 >> TP 101
        (100, 100.5, 99.9, 100),     # bar 3: nothing reaches 101
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    assert res.trade_pnls == []
    opens = [t for t in res.trade_log if t["side"].startswith("OPEN_")]
    assert len(opens) == 1 and opens[0]["bar"] == 2


def test_stop_loss_wins_when_both_levels_are_inside_one_bar():
    candles = candles_from([
        FLAT,
        FLAT,
        FLAT,                        # long filled at 100
        (100, 102.0, 98.0, 100),     # SL 99 and maker TP 101 both inside
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000, stop_loss_pct=1.0,
                       exit_execution="maker_tp", maker_tp_pct=1.0)
    assert res.trade_pnls[0] == pytest.approx(-1000 * 0.01, rel=1e-6)
    assert reasons(res) == ["stop_loss"]


def test_signal_exit_still_works_as_taker_fallback():
    """With the maker TP never reached, the strategy's own CLOSE still exits
    at the next bar's open with taker costs."""
    candles = candles_from([
        FLAT,
        FLAT,                        # BUY signal
        FLAT,                        # filled at 100
        FLAT,                        # bar 3: CLOSE signal
        (101, 101.5, 100.5, 101),    # bar 4: taker exit at open 101
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY, 3: SignalType.CLOSE}}),
                       candles, costs=NO_COST, order_notional_jpy=1000,
                       exit_execution="maker_tp", maker_tp_pct=5.0)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)
    assert reasons(res) == ["signal"]


def test_maker_tp_matches_take_profit_pct_when_maker_fee_is_zero():
    """Documented equivalence: at maker_fee 0 the new resting maker TP is the
    same object as the engine's existing take_profit_pct, differing only in the
    logged reason. Guards against the extension silently drifting."""
    rng = np.random.default_rng(20260821)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 400)))
    candles = candles_from([(p, p * 1.003, p * 0.997, p) for p in px])
    script = {i: SignalType.BUY for i in range(1, 400, 37)}
    kw = dict(costs=FX_COST, order_notional_jpy=1000, stop_loss_pct=0.5)
    a = run_backtest(Scripted({"script": script}), candles,
                     take_profit_pct=0.5, **kw)
    b = run_backtest(Scripted({"script": script}), candles,
                     exit_execution="maker_tp", maker_tp_pct=0.5, **kw)
    assert a.trade_pnls == b.trade_pnls
    assert [r.replace("maker_tp", "take_profit") for r in reasons(b)] == reasons(a)
    assert len(a.trade_pnls) > 3            # the fixture actually trades


# ---------------------------------------------------------------------------
# entry restrictions
# ---------------------------------------------------------------------------
def test_entry_mask_blocks_the_open_but_not_the_close():
    """Bar 1's decision is masked off, so no position is ever opened."""
    candles = candles_from([FLAT, FLAT, FLAT, FLAT])
    mask = np.array([True, False, True, True])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000, entry_mask=mask)
    assert res.trade_log == []


def test_entry_mask_is_read_at_the_decision_bar_not_the_fill_bar():
    """Decision on bar 1 (allowed) fills on bar 2 (masked off) -> still opens."""
    candles = candles_from([FLAT, FLAT, FLAT, FLAT])
    mask = np.array([True, True, False, False])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY}}), candles,
                       costs=NO_COST, order_notional_jpy=1000, entry_mask=mask)
    opens = [t for t in res.trade_log if t["side"].startswith("OPEN_")]
    assert len(opens) == 1 and opens[0]["bar"] == 2


def test_masked_entry_does_not_block_exiting_an_open_position():
    candles = candles_from([
        FLAT,
        FLAT,                        # bar 1: BUY (allowed)
        FLAT,                        # bar 2: filled
        FLAT,                        # bar 3: CLOSE, on a masked bar
        (101, 101.5, 100.5, 101),    # bar 4: exit fills at open 101
    ])
    mask = np.array([True, True, True, False, False])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY, 3: SignalType.CLOSE}}),
                       candles, costs=NO_COST, order_notional_jpy=1000, entry_mask=mask)
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)
    assert reasons(res) == ["signal"]


def test_entry_sides_long_only_drops_short_entries_but_keeps_long_exits():
    candles = candles_from([
        FLAT,
        FLAT,                        # bar 1: BUY
        FLAT,                        # bar 2: long filled at 100
        (101, 101.5, 100.5, 101),    # bar 3: SELL -> closes the long
        (101, 101.5, 100.5, 101),    # bar 4: exit at open 101, no short opened
        (101, 101.5, 100.5, 101),
    ])
    res = run_backtest(Scripted({"script": {1: SignalType.BUY, 3: SignalType.SELL}}),
                       candles, costs=NO_COST, allow_short=True,
                       order_notional_jpy=1000, entry_sides="long")
    sides = [t["side"] for t in res.trade_log]
    assert sides == ["OPEN_LONG", "CLOSE_LONG"]
    assert res.trade_pnls[0] == pytest.approx(+1000 * 0.01, rel=1e-6)


def test_entry_sides_long_only_equals_allow_short_false_for_a_flat_book():
    candles = candles_from([FLAT] * 6)
    script = {1: SignalType.SELL}
    a = run_backtest(Scripted({"script": script}), candles, costs=NO_COST,
                     allow_short=True, order_notional_jpy=1000, entry_sides="long")
    b = run_backtest(Scripted({"script": script}), candles, costs=NO_COST,
                     allow_short=False, order_notional_jpy=1000)
    assert a.trade_log == b.trade_log == []


# ---------------------------------------------------------------------------
# validation + the additivity guarantee
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kwargs", [
    {"exit_execution": "nonsense"},
    {"exit_execution": "maker_tp"},                     # missing maker_tp_pct
    {"exit_execution": "maker_tp", "maker_tp_pct": 0},  # non-positive
    {"maker_tp_pct": 1.0},                              # without opting in
    {"entry_sides": "sideways"},
    {"entry_mask": np.ones(3, dtype=bool)},             # wrong length
])
def test_invalid_options_are_rejected(kwargs):
    candles = candles_from([FLAT] * 5)
    with pytest.raises(ValueError):
        run_backtest(Scripted({"script": {}}), candles, **kwargs)


def test_defaults_are_bit_identical_to_passing_nothing():
    """The additivity guarantee every existing caller depends on."""
    rng = np.random.default_rng(7)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 300)))
    candles = candles_from([(p, p * 1.004, p * 0.996, p) for p in px])
    script = {i: (SignalType.BUY if i % 2 else SignalType.SELL)
              for i in range(1, 300, 23)}
    base = run_backtest(Scripted({"script": script}), candles, costs=FX_COST,
                        allow_short=True, order_notional_jpy=1000,
                        stop_loss_pct=0.5, swap_daily_pct=0.06)
    explicit = run_backtest(Scripted({"script": script}), candles, costs=FX_COST,
                            allow_short=True, order_notional_jpy=1000,
                            stop_loss_pct=0.5, swap_daily_pct=0.06,
                            exit_execution="signal", maker_tp_pct=None,
                            entry_mask=None, entry_sides="both")
    assert base.metrics.as_dict() == explicit.metrics.as_dict()
    assert base.trade_pnls == explicit.trade_pnls
    assert base.trade_log == explicit.trade_log
    assert len(base.trade_pnls) > 5
