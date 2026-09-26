"""Survey candidate 72 `QTradeX` (PyPI QTradeX 1.8.0, venv item_2/qtradex) for the item 4 battery.

What the tool's execution is (read in the installed code, qtradex/core/backtest.py 15-127・130-352 行): per candle the
bot's `strategy(state, indicators)` returns Buy / Sell (optionally with a price) or Hold; `trade` fills at the candle's
close, or at the signal's price when the blended range ((min(open, close) + low) / 2 .. (max(open, close) + high) / 2)
passes it (55-96 行), clamped to [low, high]; a Buy spends min(wallet[currency], maxvolume) of the currency and
receives volume / price x (1 - fee) of the asset, a Sell sells min(wallet[asset], maxvolume) (99-127 行); the wallet
is spot (no negative balance); consecutive signals of the same type are dropped (230-233 行).  Data is built without
fetching (`Data(..., placeholder=True)` and the candles set in `raw_candles`, public/data.py 53-110 行).

Scene -> tool: the bot acts on the decision of candle i at candle i+1 and asks for that candle's OPEN as the signal's
price (Buy(maxvolume=order_notional, price=open) / Sell(maxvolume=the asset held, price=open)); long positions only;
one fee (`PaperWallet(fee=)`, taken from what is received); max_hold / wick / entry filters are strategy code.
Fills are the states' trades (price, unix).  Not expressible: allow_short (spot wallet), slippage / spread, a maker
fee different from the taker fee, stop / limit / maker orders (no resting order: a signal lives one candle), swap,
per-trade PnL, per-bar equity, missed fills, metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import qtradex as qx  # noqa: E402
    from qtradex.core.backtest import backtest as qx_backtest  # noqa: E402
    from qtradex.private.signals import Buy, Hold, Sell  # noqa: E402
    from qtradex.private.wallet import PaperWallet  # noqa: E402
    from qtradex.public.data import Data  # noqa: E402

NO_ORDER = "待つ注文(指値・逆指値)の口を探したが無い(合図は 1 本の足でだけ効く: backtest.py 55-96 行)"


class QTradeXAdapter(Base):
    name = "opp_qtradex"
    TOOL = "QTradeX 1.8.0"
    SUPPORTS = {"taker_fee_pct", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"allow_short": "売り建ての口を探したが無い(PaperWallet は現物の残高: perform_trade 99-127 行)",
               "slippage_pct": "滑りの口を探したが無い", "spread_pct": "スプレッドの口を探したが無い",
               "maker_fee_pct": NO_ORDER, "execution": NO_ORDER, "stop_loss_pct": NO_ORDER, "take_profit_pct": NO_ORDER,
               "exit_execution": NO_ORDER, "maker_tp_pct": NO_ORDER, "swap_daily_pct": "持ち越しの口を探したが無い"}
    METRICS = "12 の指標: fitness は roi・sortino などで、決済ごとの損益・勝率・PF の口が無い"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "Data は取引所から取得した足(または placeholder)で、宣言でファイルを読む口・約定/気配/板・実行記録・書き出し・ダッシュボードが無い"

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い(operation.profit は財布の価値の比)"),
                       ("equity", "足ごとの資産の推移を出す口が無い(states の balances は残高)"),
                       ("missed_fills", "待つ注文が無いので取り逃しも無い"), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        return out

    def delivery(self, inp):
        """What QTradeX hands BaseBot.strategy: `state` (the one candle of this step: its unix time and prices), so
        the bars the strategy has seen are the steps handed so far."""
        bars = inp["bars"]
        unix = np.array([b["t_ns"] // 10**9 for b in bars], dtype=float)
        calls = []

        class Bot(qx.BaseBot):
            def __init__(self):
                self.tune = {}

            def autorange(self):
                return 0

            def reset(self):
                return None

            def indicators(self, data):
                return {}

            def fitness(self, states, raw_states, asset, currency):
                return ["roi"], {}

            def plot(self, *a, **k):
                return None

            def strategy(self, state, indicators):
                calls.append({"seen": len(calls) + 1, "last_t_ns": int(state["unix"]) * 10**9,
                              "last_close": float(state["close"])})
                return Hold()
        with contextlib.redirect_stdout(io.StringIO()):
            data = Data("synthetic", "BASE", "JPY", int(unix[0]), end=int(unix[-1]), candle_size=int(inp["bar_seconds"]),
                        placeholder=True)
            data.raw_candles = {"unix": unix, "open": np.array([b["open"] for b in bars]),
                                "high": np.array([b["high"] for b in bars]), "low": np.array([b["low"] for b in bars]),
                                "close": np.array([b["close"] for b in bars]), "volume": np.array([b["volume"] for b in bars])}
            data.begin, data.end = int(unix[0]), int(unix[-1])
            qx_backtest(Bot(), data, wallet=PaperWallet({"BASE": 0, "JPY": 6000.0}, fee=0.0), plot=False, show=False,
                        return_states=True, range_periods=False)
        return {"calls": calls}

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        cs = int(inp["bar_seconds"])
        unix = np.array([b["t_ns"] // 10**9 for b in bars], dtype=float)
        u2k = {int(u): k for k, u in enumerate(unix)}
        st = {"entry_bar": None, "level": None, "tags": {}}

        def entry_ok(db):
            return cfg["entry_sides"] != "short" and (mask is None or bool(mask[db]))

        class Bot(qx.BaseBot):
            def __init__(self):
                self.tune = {}

            def autorange(self):
                return 0

            def reset(self):
                return None

            def indicators(self, data):
                return {}

            def fitness(self, states, raw_states, asset, currency):
                return ["roi"], {}

            def plot(self, *a, **k):
                return None

            def strategy(self, state, indicators):
                k = u2k[int(state["unix"])]
                held = state["wallet"]["BASE"]
                opn = float(state["open"])
                if held and st["entry_bar"] is not None:
                    prev = k - 1
                    if N is not None and k - st["entry_bar"] >= N:
                        st["tags"][k] = "CLOSE_LONG"; st["entry_bar"] = st["level"] = None
                        return Sell(maxvolume=held, price=opn)
                    if st["level"] is not None and prev >= st["entry_bar"] and bars[prev]["close"] < st["level"]:
                        st["tags"][k] = "CLOSE_LONG"; st["entry_bar"] = st["level"] = None
                        return Sell(maxvolume=held, price=opn)
                s = sig.get(k - 1)
                if s in ("SELL", "CLOSE") and held:
                    st["tags"][k] = "CLOSE_LONG"; st["entry_bar"] = st["level"] = None
                    return Sell(maxvolume=held, price=opn)
                if s == "BUY" and not held and entry_ok(k - 1):
                    st["tags"][k] = "OPEN_LONG"; st["entry_bar"] = k
                    if W is not None:
                        lo = max(0, k - W)
                        st["level"] = min(bars[j]["low"] for j in range(lo, k)) if k > lo else None
                    return Buy(maxvolume=float(cfg["order_notional"]), price=opn)
                return Hold()

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                data = Data("synthetic", "BASE", "JPY", int(unix[0]), end=int(unix[-1]), candle_size=cs, placeholder=True)
                data.raw_candles = {"unix": unix, "open": np.array([b["open"] for b in bars]),
                                    "high": np.array([b["high"] for b in bars]), "low": np.array([b["low"] for b in bars]),
                                    "close": np.array([b["close"] for b in bars]), "volume": np.array([b["volume"] for b in bars])}
                data.begin, data.end = int(unix[0]), int(unix[-1])
                wallet = PaperWallet({"BASE": 0, "JPY": float(cfg["initial_equity"])}, fee=float(c["taker_fee_pct"]))
                res = qx_backtest(Bot(), data, wallet=wallet, plot=False, show=False, return_states=True, range_periods=False)
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:300]}") from exc
        raw = res[1]
        fills = []
        for op in raw["trades"]:
            k = u2k[int(op.unix)]
            fills.append({"bar": k, "side": st["tags"].get(k), "price": float(op.price),
                          "size": float(op.maxvolume) / float(op.price) if isinstance(op, Buy) else float(op.maxvolume)})
        return want(inp, {"fills": fills})


TARGET = QTradeXAdapter()
