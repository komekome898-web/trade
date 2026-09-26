"""The mouth's signatures (item 4 close, delegation 20260926_backtest_env_item4_close.md §2 condition 3): the names,
arguments and return types the research scripts import from `bot.backtest` (`run_backtest`, `CostModel`,
`BacktestResult`, `compute_metrics`, `Metrics`, `split_data`, `evaluate_on_splits`) are those of
`bot.bt.compat`, with these parameters and defaults; every refusal is a ValueError; the defaults equal the
same values passed explicitly; nothing of the old arithmetic is left in `bot.backtest`.
"""
from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

import bot.backtest.engine as E
import bot.backtest.metrics as M
import bot.backtest.walk_forward as W
from bot.bt import compat
from bot.strategy.base import Signal, SignalType, Strategy

RUN_BACKTEST_PARAMS = {
    "strategy": inspect.Parameter.empty, "candles": inspect.Parameter.empty,
    "initial_equity_jpy": 6000.0, "order_notional_jpy": 3000.0, "costs": None, "execution": "taker",
    "maker_timeout_bars": 5, "allow_short": False, "swap_daily_pct": 0.0, "bar_seconds": 60.0,
    "stop_loss_pct": None, "take_profit_pct": None, "max_hold_bars": None, "exit_execution": "signal",
    "maker_tp_pct": None, "entry_mask": None, "entry_sides": "both", "stop_mode": "fixed", "stop_window_bars": None,
}
COST_FIELDS = {"taker_fee_pct": 0.15, "maker_fee_pct": 0.15, "slippage_pct": 0.05, "spread_pct": 0.10}
RESULT_FIELDS = ("metrics", "equity_curve", "trade_pnls", "trade_log", "missed_fills")
METRIC_FIELDS = ("total_pnl_jpy", "num_trades", "win_rate_pct", "profit_factor", "sharpe_ratio", "max_drawdown_pct",
                 "max_consecutive_losses", "avg_win_jpy", "avg_loss_jpy", "risk_reward_ratio",
                 "expectancy_per_trade_jpy", "total_fees_jpy")
FLAT = (100.0, 100.5, 99.5, 100.0)


def candles_from(rows):
    a = np.array(rows, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3], "volume": np.ones(len(a))})


class Scripted(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.script = params["script"]

    @property
    def min_history(self):
        return 1

    def on_candles(self, candles):
        sig = self.script.get(len(candles) - 1)
        return Signal(sig, "scripted") if sig else Signal(SignalType.HOLD, "")


# --------------------------------------------------------------------------- the names are the mouth's
def test_bot_backtest_names_are_the_compat_mouths():
    assert E.run_backtest is compat.run_backtest and E.CostModel is compat.CostModel
    assert E.BacktestResult is compat.BacktestResult
    assert M.compute_metrics is compat.compute_metrics and M.Metrics is compat.Metrics
    assert W.split_data is compat.split_data and W.evaluate_on_splits is compat.evaluate_on_splits
    assert W.Splits is compat.Splits


def test_bot_backtest_holds_no_arithmetic():
    """The three modules are import lines only: no function or class is DEFINED in them."""
    for mod in (E, M, W):
        src = inspect.getsource(mod)
        assert "def " not in src and "class " not in src, mod.__name__
        for name, obj in vars(mod).items():
            if inspect.isfunction(obj) or inspect.isclass(obj):
                assert obj.__module__.startswith("bot.bt.compat."), (mod.__name__, name, obj.__module__)


# --------------------------------------------------------------------------- run_backtest / CostModel / BacktestResult
def test_run_backtest_signature():
    sig = inspect.signature(E.run_backtest)
    assert list(sig.parameters) == list(RUN_BACKTEST_PARAMS)
    for name, p in sig.parameters.items():
        assert p.default == RUN_BACKTEST_PARAMS[name], name
        if name in ("strategy", "candles"):
            assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        else:
            assert p.kind is inspect.Parameter.KEYWORD_ONLY, name


def test_cost_model_fields_and_methods():
    sig = inspect.signature(E.CostModel)
    assert {k: p.default for k, p in sig.parameters.items()} == COST_FIELDS
    c = E.CostModel(taker_fee_pct=0.1, maker_fee_pct=0.02, slippage_pct=0.03, spread_pct=0.04)
    # R-C1: the taker price = the reference x (1 +- (spread / 2 + slippage) / 100); R-A2: fee = notional x pct / 100
    assert c.buy_price(200.0) == 200.0 * (1 + (0.04 / 2 + 0.03) / 100)
    assert c.sell_price(200.0) == 200.0 * (1 - (0.04 / 2 + 0.03) / 100)
    assert c.fee(1000.0) == 1000.0 * 0.1 / 100 and c.maker_fee(1000.0) == 1000.0 * 0.02 / 100


def test_run_backtest_returns_a_backtest_result_of_the_stated_shape():
    candles = candles_from([FLAT] * 6)
    res = E.run_backtest(Scripted({"script": {1: SignalType.BUY, 3: SignalType.SELL}}), candles,
                         costs=E.CostModel(0, 0, 0, 0))
    assert isinstance(res, E.BacktestResult)
    assert tuple(f for f in res.__dataclass_fields__) == RESULT_FIELDS
    assert isinstance(res.metrics, M.Metrics)
    assert isinstance(res.equity_curve, pd.Series) and len(res.equity_curve) == len(candles)
    assert res.equity_curve.index.equals(candles.index)
    assert isinstance(res.trade_pnls, list) and all(isinstance(p, float) for p in res.trade_pnls)
    assert isinstance(res.trade_log, list) and all(isinstance(e, dict) for e in res.trade_log)
    assert isinstance(res.missed_fills, int)
    opens = [e for e in res.trade_log if e["side"].startswith("OPEN_")]
    closes = [e for e in res.trade_log if e["side"].startswith("CLOSE_")]
    assert set(opens[0]) == {"bar", "side", "price", "size"}
    assert set(closes[0]) == {"bar", "side", "price", "size", "pnl", "reason"}
    assert closes[0]["reason"] in {"signal", "stop_loss", "take_profit", "maker_tp", "time_exit", "wick_stop"}


def test_run_backtest_on_no_bars_returns_an_empty_result():
    candles = pd.DataFrame({k: pd.Series([], dtype=float) for k in ("open", "high", "low", "close", "volume")})
    res = E.run_backtest(Scripted({"script": {}}), candles)
    assert res.trade_pnls == [] and res.trade_log == [] and res.missed_fills == 0 and len(res.equity_curve) == 0
    assert res.metrics.num_trades == 0


def test_defaults_equal_the_same_values_passed_explicitly():
    """The mouth's defaults are the stated values: passing them explicitly changes nothing."""
    rng = np.random.default_rng(7)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 300)))
    candles = candles_from([(p, p * 1.004, p * 0.996, p) for p in px])
    script = {i: (SignalType.BUY if i % 2 else SignalType.SELL) for i in range(1, 300, 23)}
    kw = dict(costs=E.CostModel(0, 0, 0.02, 0.0235), allow_short=True, order_notional_jpy=1000,
              stop_loss_pct=0.5, swap_daily_pct=0.06)
    base = E.run_backtest(Scripted({"script": script}), candles, **kw)
    explicit = E.run_backtest(Scripted({"script": script}), candles, initial_equity_jpy=6000.0, execution="taker",
                              maker_timeout_bars=5, bar_seconds=60.0, take_profit_pct=None, max_hold_bars=None,
                              exit_execution="signal", maker_tp_pct=None, entry_mask=None, entry_sides="both",
                              stop_mode="fixed", stop_window_bars=None, **kw)
    assert base.metrics.as_dict() == explicit.metrics.as_dict()
    assert base.trade_pnls == explicit.trade_pnls and base.trade_log == explicit.trade_log
    assert len(base.trade_pnls) > 5


@pytest.mark.parametrize("kwargs", [
    {"execution": "nonsense"},
    {"stop_mode": "nonsense"},
    {"stop_mode": "wick_invalidation"},                                               # no window
    {"stop_mode": "wick_invalidation", "stop_window_bars": 0},                        # R-V2
    {"stop_mode": "wick_invalidation", "stop_window_bars": 3, "stop_loss_pct": 0.5},  # R-W4: no stacking
    {"stop_window_bars": 3},                                                          # without opting in
    {"exit_execution": "nonsense"},
    {"exit_execution": "maker_tp"},                                                   # R-X3: no rate
    {"exit_execution": "maker_tp", "maker_tp_pct": 0},                                # R-X3
    {"maker_tp_pct": 1.0},                                                            # without opting in
    {"entry_sides": "sideways"},
    {"entry_mask": np.ones(3, dtype=bool)},                                           # wrong length
    {"max_hold_bars": 0},                                                             # R-V2
    {"stop_loss_pct": 0.0},                                                           # R-V2: 0 is not "off"
    {"take_profit_pct": -1.0},                                                        # R-V2
    {"execution": "maker", "maker_timeout_bars": 0},                                  # R-V4
])
def test_every_option_refusal_is_a_value_error(kwargs):
    candles = candles_from([FLAT] * 5)
    with pytest.raises(ValueError):
        E.run_backtest(Scripted({"script": {}}), candles, **kwargs)


def test_a_row_the_core_cannot_take_as_a_bar_is_refused():
    rows = [list(FLAT) for _ in range(5)]
    rows[2] = [100.0, 99.0, 99.5, 100.0]  # high below the open (R-V1)
    with pytest.raises(ValueError):
        E.run_backtest(Scripted({"script": {}}), candles_from(rows))
    rows[2] = [100.0, float("nan"), 99.5, 100.0]
    with pytest.raises(ValueError):
        E.run_backtest(Scripted({"script": {}}), candles_from(rows))


# --------------------------------------------------------------------------- compute_metrics / Metrics
def test_compute_metrics_signature_and_metrics_fields():
    sig = inspect.signature(M.compute_metrics)
    assert list(sig.parameters) == ["trade_pnls", "equity_curve", "total_fees_jpy", "periods_per_year"]
    assert sig.parameters["total_fees_jpy"].default == 0.0
    assert sig.parameters["periods_per_year"].default == 365 * 86400 / 60  # M-5 for the mouth's 60-second bars
    assert tuple(M.Metrics.__dataclass_fields__) == METRIC_FIELDS
    m = M.compute_metrics([1.0, -2.0], pd.Series([100.0, 101.0, 99.0]), 0.5)
    assert isinstance(m, M.Metrics) and set(m.as_dict()) == set(METRIC_FIELDS)
    assert isinstance(m.num_trades, int) and isinstance(m.max_consecutive_losses, int)
    assert m.total_fees_jpy == 0.5


def test_run_backtest_metrics_use_the_bar_frequency():
    """M-5: the Sharpe ratio of a run is annualised by 365 * 86400 / bar_seconds."""
    rng = np.random.default_rng(3)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, 120)))
    candles = candles_from([(p, p * 1.004, p * 0.996, p) for p in px])
    script = {i: (SignalType.BUY if i % 2 else SignalType.SELL) for i in range(1, 120, 11)}
    for bar_seconds in (60.0, 3600.0):
        res = E.run_backtest(Scripted({"script": script}), candles, allow_short=True, bar_seconds=bar_seconds)
        want = M.compute_metrics(res.trade_pnls, res.equity_curve, res.metrics.total_fees_jpy,
                                 periods_per_year=365 * 86400 / bar_seconds)
        assert res.metrics.as_dict() == want.as_dict()
        assert res.metrics.sharpe_ratio != 0.0


# --------------------------------------------------------------------------- split_data / evaluate_on_splits
def test_split_data_signature_and_return():
    sig = inspect.signature(W.split_data)
    assert list(sig.parameters) == ["candles", "train_frac", "val_frac"]
    assert sig.parameters["train_frac"].default == 0.6 and sig.parameters["val_frac"].default == 0.2
    candles = candles_from([FLAT] * 100)
    s = W.split_data(candles, 0.7, 0.2)
    assert isinstance(s, W.Splits) and tuple(s.__dataclass_fields__) == ("training", "validation", "out_of_sample")
    # D-1: the fractions as written: floor(100 * 0.7) = 70, floor(100 * 0.9) = 90 -> 70 / 20 / 10
    assert (len(s.training), len(s.validation), len(s.out_of_sample)) == (70, 20, 10)
    assert s.training.index.tolist() + s.validation.index.tolist() + s.out_of_sample.index.tolist() == list(range(100))
    for bad in ((0.0, 0.2), (0.6, 0.4), (1.0, 0.1), (0.5, -0.1)):
        with pytest.raises(ValueError):
            W.split_data(candles, *bad)


def test_evaluate_on_splits_signature_and_return():
    sig = inspect.signature(W.evaluate_on_splits)
    assert list(sig.parameters) == ["strategy_cls", "params", "candles", "initial_equity_jpy", "order_notional_jpy", "costs"]
    for name in ("initial_equity_jpy", "order_notional_jpy", "costs"):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["initial_equity_jpy"].default == 6000.0
    assert sig.parameters["order_notional_jpy"].default == 3000.0
    assert sig.parameters["costs"].default is None
    candles = candles_from([FLAT] * 50)
    out = W.evaluate_on_splits(Scripted, {"script": {1: SignalType.BUY, 3: SignalType.SELL}}, candles,
                               costs=E.CostModel(0, 0, 0, 0))
    assert list(out) == ["training", "validation", "out_of_sample"]
    assert all(isinstance(r, E.BacktestResult) for r in out.values())
    assert [len(r.equity_curve) for r in out.values()] == [30, 10, 10]  # D-1: 0.6 / 0.2 of 50 as written
