"""Survey candidate 16 `Luczinsritter/event_driven_backtesting_engine` (git clone read in item 3, venv item_3/c16
with a .pth to the clone venvs/item_3/_dl/c16) for the item 4 battery.

What the tool is (backtest_engine.py): `EventBased(FinancialData)` holds cash and ONE position; the order calls are
`enter_long / enter_short(ind_nbr, units=None, amount=None)` and `close_position(ind_nbr)`, all executed at the NEXT
row's open (`get_execution_price`, 59-63 行); with `amount` the units are `int(amount / price)` at that open (80-81 行);
`close_position` books `PnL` into `trade_performance` (110-140 行).  `FinancialData.add_log_returns` drops the first
row (25-28 行).  No fee, spread, slippage, limit / stop order, carry, equity series.

Scene -> tool: `get_data` is overridden in a subclass to hand the scene's bars as the OHLCV table (the tool's own
extension point; no network); the loop is the tool's example loop over rows 0 .. len - 2 of the table the tool kept
(scene bar = row + 1).  BUY when short / SELL when long / CLOSE -> close_position; BUY / SELL when flat ->
enter_long / enter_short(amount = order_notional); max_hold_bars, wick_invalidation and entry filters are strategy
code over the same calls.  Not expressible: a signal at bar 0 (the tool drops that row), any fee / spread / slippage,
stop_loss / take_profit / maker execution / maker take-profit (no such order), swap, equity, missed fills, metrics,
op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import contextlib
import datetime as D
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, to_dt, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import backtest_engine as BE  # noqa: E402


class LuczinsritterAdapter(Base):
    name = "opp_luczinsritter"
    TOOL = "Luczinsritter/event_driven_backtesting_engine (commit 2092992)"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {k: "手数料・スプレッド・滑りの口を探したが無い(backtest_engine.py の enter_long / enter_short / close_position は"
                  "次の行の始値そのもので、費用の引数も属性も無い)" for k in ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")}
    MISSING.update({k: "指値・逆指値の注文の口を探したが無い(注文は enter_long / enter_short / close_position の 3 つだけ: "
                       "backtest_engine.py 74・92・110 行)" for k in ("execution", "stop_loss_pct", "take_profit_pct",
                                                                    "exit_execution", "maker_tp_pct")})
    MISSING["swap_daily_pct"] = "持ち越しの口を探したが無い(残高は約定の値だけで動く: 82・100・118・123 行)"
    METRICS = "12 の指標を出す口を探したが無い(tradeanalysis.py は trade_performance の表から別の指標を計算する)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は get_data の OHLCV の表 1 本(yfinance の取得)で、宣言でファイルを読む口・約定/気配/板・実行記録・書き出し・ダッシュボードが無い"
    DELIVERY = ("道具の EventBased は足ごとに戦略を呼ぶ口を持たない: 足の輪は使い手が self.data の行を for 文で回して "
                "enter_long / enter_short / close_position を呼ぶ形(この adapter の bars の for 文)で、道具が戦略に足を渡す口を探したが無い")

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("equity", "資産の推移を出す口を探したが無い(print_wealth は印字だけ: 69-72 行)"),
                       ("missed_fills", "待つ注文が無いので取り逃しの数も無い"),
                       ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        if any(int(x["bar"]) == 0 for x in inp.get("signals", [])):
            out.append("足 0 の合図: 道具は最初の行を落とす(add_log_returns の dropna: 25-28 行)")
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        df = pd.DataFrame({"Open": [b["open"] for b in bars], "High": [b["high"] for b in bars],
                           "Low": [b["low"] for b in bars], "Close": [b["close"] for b in bars],
                           "Volume": [b["volume"] for b in bars]},
                          index=pd.DatetimeIndex([to_dt(b["t_ns"]) for b in bars]))
        d2k = {t: k for k, t in enumerate(df.index)}

        class Scene(BE.EventBased):
            def get_data(self, ticker, end_date, interval):
                return df.copy()

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        fills = []
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                eb = Scene("X", D.date(2026, 1, 1), 1, "1m", float(cfg["initial_equity"]), True)
                data = eb.data
                st = {"entry_bar": None, "level": None}
                for i in range(len(data) - 1):
                    k = d2k[data.index[i]]
                    side = eb.position["side"]

                    def close():
                        units, px = eb.position["units"], None
                        eb.close_position(i)
                        fills.append({"bar": d2k[eb.closing_date], "side": f"CLOSE_{side.upper()}",
                                      "price": float(eb.closing_price), "size": float(units)})
                        st["entry_bar"] = st["level"] = None

                    if side and st["entry_bar"] is not None:
                        if N is not None and k + 1 - st["entry_bar"] >= N:
                            close(); continue
                        cl = bars[k]["close"]
                        if st["level"] is not None and ((cl < st["level"]) if side == "long" else (cl > st["level"])):
                            close(); continue
                    s = sig.get(k)
                    if not s:
                        continue
                    if s == "CLOSE" or (s == "BUY" and side == "short") or (s == "SELL" and side == "long"):
                        if side:
                            close()
                        continue
                    if side is None and entry_ok(k, s) and (s == "BUY" or cfg["allow_short"]):
                        (eb.enter_long if s == "BUY" else eb.enter_short)(i, amount=float(cfg["order_notional"]))
                        if eb.position["side"]:
                            b = d2k[eb.position["entry_date"]]
                            st["entry_bar"] = b
                            fills.append({"bar": b, "side": f"OPEN_{eb.position['side'].upper()}",
                                          "price": float(eb.position["entry_price"]), "size": float(eb.position["units"])})
                            if W is not None:
                                lo = max(0, b - W)
                                st["level"] = (min(bars[j]["low"] for j in range(lo, b)) if s == "BUY" else
                                               max(bars[j]["high"] for j in range(lo, b))) if b > lo else None
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        pnls = [float(v["PnL"]) for _, v in sorted(eb.trade_performance.items(), key=lambda kv: kv[0])]
        return want(inp, {"fills": fills, "pnls": pnls})


TARGET = LuczinsritterAdapter()
