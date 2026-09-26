"""Survey candidate 4 `PyBroker` (PyPI lib-pybroker 2.0.1, venv item_4/pybroker) for the item 4 battery.

Public API used: `pybroker.Strategy(DataFrame, start, end, StrategyConfig(initial_cash, fee_mode=FeeMode.ORDER_PERCENT,
fee_amount, enable_fractional_shares=True, round_fill_price=False, buy_delay=1, sell_delay=1, round_test_result=False))`,
`add_execution(fn, ["X"])`, `backtest(calc_bootstrap=False)`; in fn the ExecContext
`buy_shares / sell_shares`, `buy_fill_price / sell_fill_price = PriceType.OPEN`, `buy_limit_price / sell_limit_price`,
`stop_loss_pct`, `stop_profit_pct`, `hold_bars`, `sell_all_shares()`, `cover_all_shares()`, `long_pos()`,
`short_pos()`, `pending_orders()`, `cancel_pending_order(id)`; the result's `orders`, `trades` and `portfolio`.

Scene -> tool: an order set in fn of bar i is placed `buy_delay` = 1 bar later and filled at that bar's open
(`PriceType.OPEN`).  fn cannot see bar i+1's open, so an entry is sized with the decision bar's close
(buy_shares = notional / close[i]; the tool has no value-sized order).  stop_loss_pct / take_profit_pct /
maker_tp_pct / max_hold_bars -> the tool's own `stop_loss_pct` / `stop_profit_pct` / `hold_bars` set with the
entry; execution "maker" -> `buy_limit_price` / `sell_limit_price` = the decision bar's close with the tool's own
`buy_timeout_bars` / `sell_timeout_bars` = maker_timeout_bars (the tool fills a limit order at the bar's fill
price type when that price is within the limit: portfolio.py 1019・1227 行; PriceType.OPEN is used); a signal of
the other side cancels the waiting order; wick_invalidation / entry filters -> strategy code.
Not expressible: slippage / spread (the tool's slippage model changes the number of shares, not the price:
slippage.py `SlippageModel.apply_slippage(ctx, buy_shares, sell_shares)`), swap_daily_pct (the tool's
interest_rate accrues on the net cash balance, not on the position: config.py 78-83 行), a maker fee different
from the taker fee (FeeInfo has no order kind: common.py 249-262 行), the 12 metrics (EvalMetrics has no
risk-reward ratio and computes profit_factor per bar: eval.py 1295-1365 行), op metrics / split / pipeline,
reference, models.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, fee_kinds, to_dt, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

import pybroker  # noqa: E402
from pybroker import FeeMode, PriceType, Strategy, StrategyConfig  # noqa: E402


class PyBrokerAdapter(Base):
    name = "opp_pybroker"
    TOOL = "PyBroker 2.0.1"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "execution", "stop_loss_pct", "take_profit_pct",
                "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode",
                "stop_window_bars"}
    MISSING = {"slippage_pct": "値に掛ける滑りの口を探したが無い(slippage.py の SlippageModel.apply_slippage は株数を変える)",
               "spread_pct": "スプレッドの口を探したが無い(fill price は PriceType か値の指定だけ)",
               "swap_daily_pct": "建玉に掛かる持ち越しの口を探したが無い(interest_rate は現金の残高に掛かる: config.py 78-83 行)"}
    METRICS = ("12 の指標: EvalMetrics に RR が無く、profit_factor は足ごとの計算(eval.py 1345 行)。adapter は道具が出していない値を"
               "計算しない")
    SPLIT = ("行の割合で 3 つに分ける口を探したが無い(walkforward は windows と train_size で窓を切る: strategy.py walkforward。"
             "学習・検証・検証外の 3 分割は無い)")
    PIPELINE = ("入力は DataFrame(date・symbol・OHLCV)と DataSource(Alpaca・Yahoo などの取得)で、宣言でファイルを読む口・約定/気配/板・"
                "実行記録・目的つきの書き出し・ダッシュボードを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        if len(fee_kinds(cfg)) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: fee_mode の関数が受ける FeeInfo は symbol・shares・fill_price・order_type"
                       "(buy/sell)だけで、指値か成行かを受けない(common.py 249-262 行)")
        if "metrics" in (inp.get("want") or []):
            out.append(self.METRICS)
        if "missed_fills" in (inp.get("want") or []):
            out.append("取り逃しの数: 時間切れ(buy_timeout_bars)で消えた指値を数えて返す口を探したが無い(result.orders は約定した"
                       "注文の表、pending_orders は待っている注文だけ)")
        return out

    def delivery(self, inp):
        """What PyBroker hands the execution function: the ExecContext's arrays (ctx.date, ctx.close) up to the bar."""
        from _i4_base import ns_of
        bars = inp["bars"]
        dates = [pd.Timestamp(to_dt(b["t_ns"])) for b in bars]
        df = pd.DataFrame({"date": dates, "symbol": "X", "open": [b["open"] for b in bars],
                           "high": [b["high"] for b in bars], "low": [b["low"] for b in bars],
                           "close": [b["close"] for b in bars], "volume": [b["volume"] for b in bars]})
        calls = []

        def fn(ctx):
            calls.append({"seen": len(ctx.close), "last_t_ns": ns_of(pd.Timestamp(ctx.date[-1])),
                          "last_close": float(ctx.close[-1])})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pybroker.disable_logging()
            strat = Strategy(df, dates[0], dates[-1], StrategyConfig(initial_cash=6000.0))
            strat.add_execution(fn, ["X"])
            strat.backtest(calc_bootstrap=False, warmup=None)
        return {"calls": calls}

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        maker = cfg["execution"] == "maker"
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]
        dates = [pd.Timestamp(to_dt(b["t_ns"])) for b in bars]
        d2k = {d: k for k, d in enumerate(dates)}
        df = pd.DataFrame({"date": dates, "symbol": "X", "open": [b["open"] for b in bars],
                           "high": [b["high"] for b in bars], "low": [b["low"] for b in bars],
                           "close": [b["close"] for b in bars], "volume": [b["volume"] for b in bars]})
        st = {"limit": None, "missed": 0, "level": None, "entry_date": None}
        fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        def set_exits(ctx):
            if cfg["stop_loss_pct"]:
                ctx.stop_loss_pct = cfg["stop_loss_pct"]
            tp = cfg["take_profit_pct"] or (cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None)
            if tp:
                ctx.stop_profit_pct = tp
            if cfg["max_hold_bars"] is not None:
                ctx.hold_bars = cfg["max_hold_bars"]
                if ctx.buy_shares is not None:
                    ctx.sell_fill_price = PriceType.OPEN  # the hold exit fills at the open
                else:
                    ctx.buy_fill_price = PriceType.OPEN

        def fn(ctx):
            k = d2k[pd.Timestamp(ctx.dt)]
            lp, sp = ctx.long_pos(), ctx.short_pos()
            pos = float(lp.shares) if lp else (-float(sp.shares) if sp else 0.0)
            cl = float(ctx.close[-1])
            if W is not None and pos:
                ent = (lp or sp).entries[0].date
                if st["entry_date"] != ent:
                    b = d2k[pd.Timestamp(ent)]
                    lo = max(0, b - W)
                    st["level"] = (min(bars[j]["low"] for j in range(lo, b)) if pos > 0 else
                                   max(bars[j]["high"] for j in range(lo, b))) if b > lo else None
                    st["entry_date"] = ent
                if st["level"] is not None and ((cl < st["level"]) if pos > 0 else (cl > st["level"])):
                    if pos > 0:
                        ctx.sell_all_shares(); ctx.sell_fill_price = PriceType.OPEN
                    else:
                        ctx.cover_all_shares(); ctx.buy_fill_price = PriceType.OPEN
                    return
            s = sig.get(k)
            if not s:
                return
            side = s if s != "CLOSE" else ("SELL" if pos > 0 else "BUY" if pos < 0 else None)
            if side is None:
                return
            closing = (side == "BUY" and pos < 0) or (side == "SELL" and pos > 0)
            if not maker:
                if closing:
                    if side == "BUY":
                        ctx.cover_all_shares(); ctx.buy_fill_price = PriceType.OPEN
                    else:
                        ctx.sell_all_shares(); ctx.sell_fill_price = PriceType.OPEN
                elif s != "CLOSE" and pos == 0 and entry_ok(k, side) and (side == "BUY" or cfg["allow_short"]):
                    if side == "BUY":
                        ctx.buy_shares = notional / cl; ctx.buy_fill_price = PriceType.OPEN
                    else:
                        ctx.sell_shares = notional / cl; ctx.sell_fill_price = PriceType.OPEN
                    set_exits(ctx)
                return
            actionable = pos <= 0 if side == "BUY" else (pos > 0 or (pos == 0 and cfg["allow_short"]))
            if not (actionable or s == "CLOSE"):
                return
            for o in ctx.pending_orders():  # a resting order of the other side is replaced
                ctx.cancel_pending_order(o.id)
            if not closing and not entry_ok(k, side):
                return
            T = cfg["maker_timeout_bars"]
            if side == "BUY":
                ctx.buy_shares = abs(pos) if closing else notional / cl
                ctx.buy_limit_price = cl; ctx.buy_timeout_bars = T; ctx.buy_fill_price = PriceType.OPEN
            else:
                ctx.sell_shares = abs(pos) if closing else notional / cl
                ctx.sell_limit_price = cl; ctx.sell_timeout_bars = T; ctx.sell_fill_price = PriceType.OPEN
            if not closing:
                set_exits(ctx)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pybroker.disable_logging()
                cfg_ = StrategyConfig(initial_cash=float(cfg["initial_equity"]), fee_mode=FeeMode.ORDER_PERCENT,
                                      fee_amount=float(fee), enable_fractional_shares=True, round_fill_price=False,
                                      buy_delay=1, sell_delay=1, round_test_result=False, exit_on_last_bar=False)
                strat = Strategy(df, dates[0], dates[-1], cfg_)

                strat.add_execution(fn, ["X"])
                res = strat.backtest(calc_bootstrap=False, warmup=None)
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        fills, pnls = [], []
        for _, t in res.trades.iterrows():
            d = "LONG" if str(t["type"]) == "long" else "SHORT"
            eb, xb = d2k[pd.Timestamp(t["entry_date"])], d2k[pd.Timestamp(t["exit_date"])]
            fills.append({"bar": eb, "side": f"OPEN_{d}", "price": float(t["entry"]), "size": float(t["shares"])})
            fills.append({"bar": xb, "side": f"CLOSE_{d}", "price": float(t["exit"]), "size": float(t["shares"])})
            pnls.append((xb, float(t["pnl"])))
        eq = [float(x) for x in res.portfolio["equity"].tolist()]
        fills.sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        return want(inp, {"fills": fills, "pnls": [p for _, p in sorted(pnls, key=lambda x: x[0])], "equity": eq})


TARGET = PyBrokerAdapter()
