"""当方の現状 (the current environment) for the item 4 battery.

The current environment's bar backtest is `src/bot/backtest/` (engine.run_backtest,
engine.CostModel, metrics.compute_metrics, walk_forward.split_data), driven
through its public API only.  The scene's script is the strategy (a
bot.strategy.base.Strategy whose on_candles looks only at the slice it is given).

What the current environment has no public way to express raises NotExpressible:
- op "pipeline": no loader of files by a declared spec, no tick / quote / book input
  (run_backtest takes one OHLC DataFrame), no run record / export / dashboard run view.
- "reference": no independent reference implementation of the bar path
  (scripts/qa/maker_fill_ref.py simulates a tick queue from executions and a ticker, not bars).
- "models": it has ONE bar model; asked for two results of one strategy it runs
  that one model for each (the observation says so by being the same run).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from i4_protocol import NotExpressible, Refused  # noqa: E402

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.backtest.metrics import compute_metrics  # noqa: E402
from bot.backtest.walk_forward import split_data  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402


class _Script(Strategy):
    """The scene's script: at the close of bar i (the last row of the slice) say signals[i], else HOLD."""

    def __init__(self, signals: dict):
        super().__init__({})
        self._s = signals

    @property
    def min_history(self) -> int:
        return 0

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        s = self._s.get(len(candles) - 1)
        return Signal(SignalType[s]) if s else Signal(SignalType.HOLD)


def _frame(bars):
    return pd.DataFrame({k: [b[k] for b in bars] for k in ("open", "high", "low", "close", "volume")},
                        index=pd.to_datetime([b["t_ns"] for b in bars], unit="ns", utc=True))


def _call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as exc:  # the current environment's refusal of an option
        raise Refused(f"ValueError: {exc}") from exc


class CurrentImpl:
    name = "current_impl"

    def run(self, inp: dict) -> dict:
        op = inp.get("op")
        if op == "bars":
            if inp.get("reference"):
                raise NotExpressible("当方の現状に足の経路の独立の参照実装を探したが無い(scripts/qa/maker_fill_ref.py は約定と"
                                     "ティッカーから板の待ち行列を模す別の模型で、足を入力に取らない)")
            if "models" in inp:
                return {m: self._bars(inp) for m in inp["models"]}
            return self._bars(inp)
        if op == "delivery":
            return self._delivery(inp)
        if op == "metrics":
            m = _call(compute_metrics, list(inp["trade_pnls"]), pd.Series(inp["equity"], dtype=float),
                      inp["total_fees"], periods_per_year=inp["periods_per_year"])
            return {"metrics": m.as_dict()}
        if op == "split":
            if "models" in inp:
                return {m: self._split(inp) for m in inp["models"]}
            return self._split(inp)
        if op == "pipeline":
            raise NotExpressible("当方の現状の公開された口(src/bot/backtest/engine.run_backtest)は OHLC の DataFrame 1 本だけを取る。"
                                 "宣言でファイルを読む口・約定/気配/板の入力・実行記録・指標の書き出し・ダッシュボードの実行の表示を探したが無い")
        raise NotExpressible(f"op {op!r} に当たる口が無い")

    @staticmethod
    def _delivery(inp):
        """The current environment's event loop is run_backtest's bar loop: the strategy's on_candles gets the slice
        of the candles it may see; record that slice (its length, its last row's time and close)."""
        calls = []

        class Recorder(Strategy):
            def __init__(self):
                super().__init__({})

            @property
            def min_history(self) -> int:
                return 0

            def on_candles(self, candles: pd.DataFrame) -> Signal:
                calls.append({"seen": len(candles), "last_t_ns": int(candles.index[-1].value),
                              "last_close": float(candles["close"].iloc[-1])})
                return Signal(SignalType.HOLD)

        _call(run_backtest, Recorder(), _frame(inp["bars"]), bar_seconds=float(inp["bar_seconds"]))
        return {"calls": calls}

    @staticmethod
    def _split(inp):
        df = _frame(inp["bars"])
        sp = _call(split_data, df, train_frac=inp["train_frac"], val_frac=inp["val_frac"])
        pos = {t: i for i, t in enumerate(df.index)}
        return {"splits": {k: [pos[t] for t in getattr(sp, k).index] for k in ("training", "validation", "out_of_sample")}}

    @staticmethod
    def _bars(inp):
        c = inp["config"]
        sig = {int(s["bar"]): s["signal"] for s in inp["signals"]}
        costs = CostModel(**{k: c["costs"][k] for k in ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")})
        res = _call(run_backtest, _Script(sig), _frame(inp["bars"]),
                    initial_equity_jpy=c["initial_equity"], order_notional_jpy=c["order_notional"], costs=costs,
                    execution=c["execution"], maker_timeout_bars=c["maker_timeout_bars"], allow_short=c["allow_short"],
                    swap_daily_pct=c["swap_daily_pct"], bar_seconds=float(inp["bar_seconds"]),
                    stop_loss_pct=c["stop_loss_pct"], take_profit_pct=c["take_profit_pct"],
                    max_hold_bars=c["max_hold_bars"], exit_execution=c["exit_execution"], maker_tp_pct=c["maker_tp_pct"],
                    entry_mask=c["entry_mask"], entry_sides=c["entry_sides"], stop_mode=c["stop_mode"],
                    stop_window_bars=c["stop_window_bars"])
        want = set(inp.get("want") or [])
        obs = {}
        if "fills" in want:
            obs["fills"] = [{"bar": int(e["bar"]), "side": e["side"], "price": float(e["price"]), "size": float(e["size"])}
                            for e in res.trade_log if e["side"].startswith(("OPEN_", "CLOSE_"))]
        if "pnls" in want:
            obs["pnls"] = [float(p) for p in res.trade_pnls]
        if "equity" in want:
            obs["equity"] = [float(x) for x in res.equity_curve.tolist()]
        if "metrics" in want:
            obs["metrics"] = res.metrics.as_dict()
        if "missed_fills" in want:
            obs["missed_fills"] = int(res.missed_fills)
        return obs


TARGET = CurrentImpl()
