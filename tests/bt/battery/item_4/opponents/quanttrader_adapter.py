"""Survey candidate 68 `quanttrader` 0.5.5 (PyPI, venv item_4/quanttrader, install record
venvs/item_4/i4_r1_scenekeeper_install_quanttrader.log; the package's code uses `np.str` and `DataFrame.append`
(performance/performance_manager.py 39, 44), so numpy 1.23.5 / pandas 1.5.3 / matplotlib 3.7.5 were pinned inside its
venv and logged) for the item 4 battery.

The tool's own parts used: `BacktestEngine(start, end)`, `set_capital`, `add_data("X", DataFrame of Open/High/Low/
Close/Volume)`, a `StrategyBase` subclass whose `on_tick` sends `OrderEvent`s (order_type MARKET / STOP / LIMIT) with
`place_order`, and the engine's result `df_trades` (fill time, amount, price).

What the tool does (read in its installed code): a MARKET order is filled at once at `DataBoard.get_current_price`
= the Close of the current bar (brokerage/backtest_brokerage.py place_order 131-157: "Market order is immediately
filled"); a resting LIMIT / STOP order is kept in `_active_orders`, and the next `on_tick` rebuilds that dict with
`{k: v for k, v in self._active_orders if ...}` (125) -- iterating a dict of int keys, which raises: the tool fails
on any resting order.  The commission is a fixed formula per symbol type, 1 bp of the value for a symbol without
STK / FUT / OPT / CASH (30-49), with no parameter.  `df_trades` keeps `int(fill_size)` (performance_manager.py 45).
Not expressible: a fee rate or slippage / spread (fixed 1 bp, no parameter), swap, per-trade PnL, per-bar equity at
the close (update_performance runs before the strategy on each tick: backtest_engine.py 109-111), metrics,
op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, to_dt, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

warnings.filterwarnings("ignore")
import pandas as pd  # noqa: E402

from quanttrader.backtest_engine import BacktestEngine  # noqa: E402
from quanttrader.order.order_event import OrderEvent  # noqa: E402
from quanttrader.order.order_type import OrderType  # noqa: E402
from quanttrader.strategy.strategy_base import StrategyBase  # noqa: E402

TOOL = "quanttrader 0.5.5"
_FEE = "手数料・滑りの率を渡す口を探したが無い(backtest_brokerage.py 30-49 行: 銘柄の型ごとの固定の式、型の無い銘柄は価値の 1 bp)"


class QuantTrader(Base):
    name = "opp_quanttrader"
    TOOL = TOOL
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct"}
    MISSING = {k: _FEE for k in ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")}
    MISSING["swap_daily_pct"] = "持ち越しの口を探したが無い(費用は _calculate_commission だけ)"
    PIPELINE = "入力は銘柄ごとの DataFrame(add_data)で、宣言でファイルを読む口・気配の買い ask・売り bid(fill は「TODO: use bid/ask」: 113・155 行)・目的つきの書き出し・ダッシュボードの口が無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def extra_gate(self, inp):
        w = set(inp.get("want") or [])
        out = []
        if "pnls" in w:
            out.append("決済ごとの損益を出す口を探したが無い(結果は df_trades の約定と df_positions)")
        if "equity" in w:
            out.append("足の終値での資産を出す口を探したが無い(_equity は各足の注文の前に記録: backtest_engine.py 109-111 行)")
        if "metrics" in w:
            out.append(self.METRICS)
        return out

    def delivery(self, inp):
        """What quanttrader hands StrategyBase.on_tick: the tick of this bar and the data board (history up to the
        tick's timestamp)."""
        from _i4_base import ns_of
        bars = inp["bars"]
        n = len(bars)
        idx = pd.DatetimeIndex([to_dt(b["t_ns"]) for b in bars])
        df = pd.DataFrame({"Open": [b["open"] for b in bars], "High": [b["high"] for b in bars],
                           "Low": [b["low"] for b in bars], "Close": [b["close"] for b in bars],
                           "Volume": [1.0] * n}, index=idx)
        calls = []

        class Rec(StrategyBase):
            def on_tick(self, tick):
                # the tick of a bar backtest carries no price (price 0.0); the strategy reads prices from the data
                # board it is given (StrategyBase._data_board, get_hist_price: rows up to the timestamp inclusive)
                h = self._data_board.get_hist_price("X", tick.timestamp)
                calls.append({"seen": len(h), "last_t_ns": ns_of(pd.Timestamp(h.index[-1])),
                              "last_close": float(h["Close"].iloc[-1])})
        eng = BacktestEngine(idx[0].normalize(), idx[-1].normalize() + pd.Timedelta(days=1))
        eng.set_capital(6000.0)
        eng.set_strategy(Rec())
        eng.add_data("X", df)
        eng.run()
        return {"calls": calls}

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        idx = pd.DatetimeIndex([to_dt(b["t_ns"]) for b in bars])
        k_of = {t: k for k, t in enumerate(idx)}
        df = pd.DataFrame({"Open": [b["open"] for b in bars], "High": [b["high"] for b in bars],
                           "Low": [b["low"] for b in bars], "Close": [b["close"] for b in bars],
                           "Volume": [1.0] * n}, index=idx)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        st = {"pos": 0, "entry_bar": None, "lvl": None, "missed": 0}
        eng = BacktestEngine(idx[0].normalize(), idx[-1].normalize() + pd.Timedelta(days=1))

        def send(strat, size, typ, t, level=None):
            o = OrderEvent()
            o.full_symbol = "X"
            o.order_type = typ
            o.order_size = size
            o.create_time = t
            if typ == OrderType.LIMIT:
                o.limit_price = level
            if typ == OrderType.STOP:
                o.stop_price = level
            strat.place_order(o)

        class Scene(StrategyBase):
            def on_fill(self, fill_event):
                super().on_fill(fill_event)
                was = st["pos"]
                st["pos"] += int(fill_event.fill_size)
                if was == 0 and st["pos"] != 0:          # the entry: the strategy sends its exit orders now
                    k = k_of[pd.Timestamp(fill_event.fill_time)]
                    st["entry_bar"] = k
                    d = 1 if st["pos"] > 0 else -1
                    px = float(fill_event.fill_price)
                    if W:
                        win = bars[max(0, k - W):k]
                        st["lvl"] = (min(x["low"] for x in win) if d > 0 else max(x["high"] for x in win)) if win else None
                    t = fill_event.fill_time
                    if cfg["stop_loss_pct"]:
                        send(self, -st["pos"], OrderType.STOP, t, px * (1 - d * cfg["stop_loss_pct"] / 100))
                    if cfg["take_profit_pct"] or cfg["exit_execution"] == "maker_tp":
                        pct = cfg["take_profit_pct"] or cfg["maker_tp_pct"]
                        send(self, -st["pos"], OrderType.LIMIT, t, px * (1 + d * pct / 100))
                elif st["pos"] == 0:
                    st["entry_bar"] = st["lvl"] = None

            def on_tick(self, tick):
                k = k_of.get(tick.timestamp)
                if k is None:
                    return
                t = tick.timestamp
                pos = st["pos"]
                cl = bars[k]["close"]
                if pos != 0:
                    if N is not None and k + 1 - st["entry_bar"] >= N:
                        send(self, -pos, OrderType.MARKET, t); return
                    if st["lvl"] is not None and ((cl < st["lvl"]) if pos > 0 else (cl > st["lvl"])):
                        send(self, -pos, OrderType.MARKET, t); return
                s = sig.get(k)
                if not s:
                    return
                if pos != 0 and (s == "CLOSE" or (s == "BUY") != (pos > 0)):
                    if cfg["execution"] == "maker":
                        send(self, -pos, OrderType.LIMIT, t, cl)
                    else:
                        send(self, -pos, OrderType.MARKET, t)
                    return
                if pos != 0 or s == "CLOSE":
                    return
                if s == "SELL" and not cfg["allow_short"]:
                    return
                if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                    return
                if cfg["entry_mask"] is not None and not cfg["entry_mask"][k]:
                    return
                q = int(cfg["order_notional"] / cl)
                if q <= 0:
                    return
                size = q if s == "BUY" else -q
                if cfg["execution"] == "maker":
                    send(self, size, OrderType.LIMIT, t, cl)
                    return
                send(self, size, OrderType.MARKET, t)

        eng.set_capital(float(cfg["initial_equity"]))
        eng.set_strategy(Scene())
        eng.add_data("X", df)
        try:
            _eq, _pos, trades = eng.run()
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        fills, pos = [], 0
        for t, row in trades.iterrows():
            amt = int(row["amount"])
            side = ("OPEN_LONG" if amt > 0 else "OPEN_SHORT") if pos == 0 else ("CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
            fills.append({"bar": k_of[pd.Timestamp(t)], "side": side, "price": float(row["price"]), "size": float(abs(amt))})
            pos += amt
        return want(inp, {"fills": fills, "missed_fills": st["missed"]})


TARGET = QuantTrader()
