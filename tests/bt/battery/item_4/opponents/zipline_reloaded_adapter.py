"""Survey candidate 18 `zipline-reloaded` 3.1.1 (PyPI, venv item_4/zipline-reloaded, install record
venvs/item_4/i4_r1_scenekeeper_install_zipline-reloaded.log) for the item 4 battery.

The tool's own parts used: a data bundle registered with `zipline.data.bundles.register` and the tool's own
`csvdir_equities(["minute"], dir)` reader, on the `24/7` calendar, ingested with `ingest` into a scratch ZIPLINE_ROOT;
`run_algorithm(..., data_frequency="minute", bundle=..., trading_calendar=<zipline's cached 24/7 calendar>)` with
`initialize` / `handle_data`; inside, `set_slippage(slippage.FixedBasisPointsSlippage(basis_points, volume_limit))`,
`set_commission(commission.PerDollar(cost))`, `sid(0)`, `order(asset, amount, style=MarketOrder() | LimitOrder(p) |
StopOrder(p))`, `cancel_order`, and the result frame's `transactions` and `portfolio_value`.

What the tool does with a bar (read from its installed code): an order sent in handle_data of minute k is processed
at minute k+1, at that minute's CLOSE (slippage.py SlippageModel.simulate 160-185: `price = data.current(asset,
"close")`; FixedBasisPointsSlippage moves it by the basis points); a limit / stop order is triggered by that close
(order.py check_order_triggers 160-200) and a limit fill worse than the limit is not made (slippage.py 48-78).
`order(amount)` takes whole shares.  There is no one-cancels-other: the strategy cancels the other exit order when it
sees one filled (next handle_data).  A CSV row is written with the bar's END time (the minute bar reader labels a
minute by its end).  Only 1-minute bars (the minute bundle); one commission rate.
Not expressible: bar_seconds other than 60, a maker fee different from the taker fee, swap, per-trade PnL (the tool
records transactions and portfolio values, not closed round trips), metrics, op metrics / split / pipeline,
reference, models.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, adj, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

import pandas as pd  # noqa: E402

TOOL = "zipline-reloaded 3.1.1"


class ZiplineReloaded(Base):
    name = "opp_zipline_reloaded"
    TOOL = TOOL
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct",
                "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"}
    MISSING = {"swap_daily_pct": "持ち越しの口を探したが無い(株の模型: commission と slippage だけ。先物の模型にも日率の持ち越しは無い)"}
    METRICS = "12 の指標を出す口を探したが無い(結果の表は日ごとの収益・Sharpe などの列で、決済ごとの損益からの指標ではない)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は bundle(ingest した分足・日足)で、約定/気配/板の宣言・目的つきの書き出し・ダッシュボードの口が無い"

    def extra_gate(self, inp):
        out = []
        cfg = inp["config"]
        c = cfg["costs"]
        if int(inp["bar_seconds"]) != 60:
            out.append("1 分以外の足を渡す口を探したが無い(bundle は minute と daily だけ)")
        kinds = fee_kinds(cfg)
        if len({c[f"{k}_fee_pct"] for k in kinds}) > 1:
            out.append("手数料は set_commission の 1 つだけで、maker と taker に別の率を置く口が無い")
        w = set(inp.get("want") or [])
        if "pnls" in w:
            out.append("決済ごとの損益を出す口を探したが無い(結果は transactions と portfolio_value)")
        if "metrics" in w:
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        t0 = pd.Timestamp(bars[0]["t_ns"], unit="ns")
        work = tempfile.mkdtemp(prefix="i4_r1_scenekeeper_zl_", dir=os.environ.get("I4_TMP"))
        os.environ["ZIPLINE_ROOT"] = os.path.join(work, "root")
        os.makedirs(os.path.join(work, "csv", "minute"))
        idx = pd.DatetimeIndex([pd.Timestamp(b["t_ns"], unit="ns") + pd.Timedelta(seconds=60) for b in bars], name="date")
        pd.DataFrame({"open": [b["open"] for b in bars], "high": [b["high"] for b in bars],
                      "low": [b["low"] for b in bars], "close": [b["close"] for b in bars],
                      "volume": [1e9] * n, "dividend": 0.0, "split": 1.0}, index=idx).to_csv(
            os.path.join(work, "csv", "minute", "X.csv"))
        from zipline import run_algorithm
        from zipline.api import (cancel_order, get_datetime, get_open_orders, order, set_commission, set_slippage,
                                 sid)
        from zipline.data.bundles import ingest, register
        from zipline.data.bundles.csvdir import csvdir_equities
        from zipline.finance import commission, slippage
        from zipline.finance.execution import LimitOrder, MarketOrder, StopOrder
        from zipline.utils.calendar_utils import get_calendar
        day = t0.normalize()
        end_day = (idx[-1] - pd.Timedelta(seconds=1)).normalize()
        register("scene", csvdir_equities(["minute"], os.path.join(work, "csv")), calendar_name="24/7",
                 start_session=day, end_session=end_day, minutes_per_day=1440)
        ingest("scene", show_progress=False)
        bps = adj(cfg["costs"]) * 10000
        rate = (cfg["costs"]["maker_fee_pct"] if cfg["execution"] == "maker" and not cfg["stop_loss_pct"]
                else cfg["costs"]["taker_fee_pct"]) / 100
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        st = {"k": -1, "entry_bar": None, "lvl": None, "exits": [], "entry_oid": None, "entry_placed": None,
              "missed": 0, "pos": 0}

        def initialize(ctx):
            ctx.a = sid(0)   # the only asset of the bundle (symbol() looks up as of the session start, before its first minute)
            set_slippage(slippage.FixedBasisPointsSlippage(basis_points=bps, volume_limit=1.0))
            set_commission(commission.PerDollar(cost=rate))

        def handle_data(ctx, data):
            k = int((get_datetime().tz_localize(None) - t0) / pd.Timedelta(seconds=60)) - 1
            if k < 0 or k >= n:
                return
            a = ctx.a
            pos = ctx.portfolio.positions[a].amount if a in ctx.portfolio.positions else 0
            if pos != 0 and st["pos"] == 0:      # the entry was filled on this bar
                st["entry_bar"] = k
                d = 1 if pos > 0 else -1
                px = ctx.portfolio.positions[a].cost_basis
                if W:
                    win = bars[max(0, k - W):k]
                    st["lvl"] = (min(x["low"] for x in win) if d > 0 else max(x["high"] for x in win)) if win else None
                ex = []
                if cfg["stop_loss_pct"]:
                    ex.append(order(a, -pos, style=StopOrder(px * (1 - d * cfg["stop_loss_pct"] / 100))))
                if cfg["take_profit_pct"]:
                    ex.append(order(a, -pos, style=LimitOrder(px * (1 + d * cfg["take_profit_pct"] / 100))))
                if cfg["exit_execution"] == "maker_tp":
                    ex.append(order(a, -pos, style=LimitOrder(px * (1 + d * cfg["maker_tp_pct"] / 100))))
                st["exits"] = [o for o in ex if o]
            if pos == 0 and st["pos"] != 0:      # an exit was filled: cancel the other exit order
                for o in st["exits"]:
                    cancel_order(o)
                st["exits"], st["entry_bar"], st["lvl"] = [], None, None
            st["pos"] = pos
            opens = {o.id for o in get_open_orders(a)} if get_open_orders(a) else set()
            if st["entry_oid"] is not None and st["entry_oid"] in opens and k >= st["entry_placed"] + cfg["maker_timeout_bars"]:
                cancel_order(st["entry_oid"]); st["missed"] += 1; st["entry_oid"] = None
            s = sig.get(k)
            cl = bars[k]["close"]

            def exit_now():
                for o in st["exits"]:
                    cancel_order(o)
                st["exits"] = []
                order(a, -pos, style=MarketOrder())

            if pos != 0:
                if N is not None and k + 1 - st["entry_bar"] >= N:
                    exit_now(); return
                if st["lvl"] is not None and ((cl < st["lvl"]) if pos > 0 else (cl > st["lvl"])):
                    exit_now(); return
            if not s:
                return
            if pos != 0 and (s == "CLOSE" or (s == "BUY") != (pos > 0)):
                if cfg["execution"] == "maker":
                    for o in st["exits"]:
                        cancel_order(o)
                    st["exits"] = [order(a, -pos, style=LimitOrder(cl))]
                else:
                    exit_now()
                return
            if pos != 0 or s == "CLOSE":
                return
            if s == "SELL" and not cfg["allow_short"]:
                return
            if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                return
            if cfg["entry_mask"] is not None and not cfg["entry_mask"][k]:
                return
            if st["entry_oid"] is not None and st["entry_oid"] in opens:
                cancel_order(st["entry_oid"]); st["missed"] += 1
            q = int(cfg["order_notional"] / cl)
            if q <= 0:
                return
            amt = q if s == "BUY" else -q
            if cfg["execution"] == "maker":
                st["entry_oid"] = order(a, amt, style=LimitOrder(cl)); st["entry_placed"] = k
            else:
                order(a, amt, style=MarketOrder())

        try:
            res = run_algorithm(start=day, end=end_day, initialize=initialize, handle_data=handle_data,
                                capital_base=float(cfg["initial_equity"]), data_frequency="minute", bundle="scene",
                                trading_calendar=get_calendar("24/7"))
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        fills, pos = [], 0
        for txs in res["transactions"]:
            for t in txs:
                k = int((pd.Timestamp(t["dt"]).tz_localize(None) - t0) / pd.Timedelta(seconds=60)) - 1
                amt = int(t["amount"])
                if pos == 0:
                    side = "OPEN_LONG" if amt > 0 else "OPEN_SHORT"
                else:
                    side = "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT"
                fills.append({"bar": k, "side": side, "price": float(t["price"]), "size": float(abs(amt))})
                pos += amt
        pv = res["portfolio_value"]
        equity = []
        for b in bars:
            ts = (pd.Timestamp(b["t_ns"], unit="ns") + pd.Timedelta(seconds=60)).tz_localize("UTC")
            equity.append(float(pv.loc[ts]) if ts in pv.index else None)
        if any(e is None for e in equity):
            equity = None
        obs = {"fills": fills, "missed_fills": st["missed"]}
        if equity is not None:
            obs["equity"] = equity
        return want(inp, obs)


TARGET = ZiplineReloaded()
