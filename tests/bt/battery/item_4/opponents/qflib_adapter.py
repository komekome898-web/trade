"""Survey candidate 62 `qf-lib` 4.0.7 (PyPI, venv item_4/qf-lib, install record
venvs/item_4/i4_r1_scenekeeper_install_qf-lib.log -- the package imports three modules it does not declare, PyJWT,
oauthlib and requests-oauthlib, through data_providers/__init__.py -> bloomberg_dl; they were added to the same venv
and logged) for the item 4 battery.

The tool's own parts used: `QFDataArray.create` + `PresetDataProvider(data, start, end, Frequency.MIN_1)` for the
scene's bars (ticker `BloombergTicker("X US Equity", SecurityType.STOCK, 1)`: a name only, nothing is fetched),
`BacktestTradingSessionBuilder(settings, PDFExporter, ExcelExporter)` with the package's own test settings
(qf_lib/tests/unit_tests/config/test_settings.py), `set_frequency(Frequency.MIN_1)`, market open 00:00 / close 23:59,
`set_commission_model(BpsTradeValueCommissionModel, commission=bps)`, `set_slippage_model(PriceBasedSlippage,
slippage_rate=...)`, a strategy subscribed to `CalculateAndPlaceOrdersPeriodicEvent` every minute of the scene,
`order_factory.orders({ticker: qty}, MarketOrder() | StopOrder(p), TimeInForce.GTC)`, `broker.place_orders`,
`broker.cancel_order`, and the monitor's `backtest_result.transactions` and the portfolio's `closed_positions()`
(`total_pnl`).

What the tool does (measured here with a probe, and read in execution_handler/market_orders_executor.py 71-109 and
stop_orders_executor.py 134-170): the strategy's event at minute t sees the bar that ended at t; a market order it
places is executed at the NEXT minute's processing, at the open of the bar that starts then (so a signal on bar k
fills at the open of bar k+2); a stop fills at the open when the open is already past it, else at the stop when the
bar's low (sell) / high (buy) reaches it.  There is no limit order type (order/execution_style.py: MarketOrder,
MarketOnCloseOrder, StopOrder).
Not expressible: limit orders (maker entries, take-profit, maker take-profit), bar_seconds other than 60 (the
adapter builds a 1-minute session), per-bar equity (portfolio_eod_series is end of day), swap, metrics,
op metrics / split / pipeline, reference, models.
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
os.environ.setdefault("QF_STARTING_DIRECTORY", tempfile.mkdtemp(prefix="i4_r1_scenekeeper_qf_", dir=os.environ.get("I4_TMP")))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TOOL = "qf-lib 4.0.7"
_NOLIMIT = "指値の注文の型を探したが無い(order/execution_style.py の型は MarketOrder・MarketOnCloseOrder・StopOrder の 3 つ)"


class QfLib(Base):
    name = "opp_qflib"
    TOOL = TOOL
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"}
    MISSING = {"execution": _NOLIMIT, "take_profit_pct": _NOLIMIT, "exit_execution": _NOLIMIT, "maker_tp_pct": _NOLIMIT,
               "swap_daily_pct": "持ち越しの口を探したが無い(費用は commission model と slippage model だけ)"}
    METRICS = "12 の指標を出す口を探したが無い(成績の文書は日次の系列から作る)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は DataProvider(Bloomberg・Haver・Quandl などの取得口か、用意した配列)で、約定/気配/板の宣言・目的つきの書き出し・ダッシュボードの口が無い"

    def extra_gate(self, inp):
        out = []
        cfg = inp["config"]
        c = cfg["costs"]
        if int(inp["bar_seconds"]) != 60:
            out.append("1 分以外の足: この adapter は Frequency.MIN_1 の会期だけを作る")
        kinds = fee_kinds(cfg)
        if len({c[f"{k}_fee_pct"] for k in kinds}) > 1:
            out.append("手数料の模型は 1 つだけで、maker と taker に別の率を置く口が無い")
        w = set(inp.get("want") or [])
        if "equity" in w:
            out.append("足ごとの資産の系列を探したが無い(portfolio_eod_series は日の終わりの値)")
        if "metrics" in w:
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        from qf_lib.backtesting.events.time_event.periodic_event.calculate_and_place_orders_event import \
            CalculateAndPlaceOrdersPeriodicEvent
        from qf_lib.backtesting.execution_handler.commission_models.bps_trade_value_commission_model import \
            BpsTradeValueCommissionModel
        from qf_lib.backtesting.execution_handler.slippage.price_based_slippage import PriceBasedSlippage
        from qf_lib.backtesting.monitoring.backtest_monitor import BacktestMonitorSettings
        from qf_lib.backtesting.order.execution_style import MarketOrder, StopOrder
        from qf_lib.backtesting.order.time_in_force import TimeInForce
        from qf_lib.backtesting.strategies.abstract_strategy import AbstractStrategy
        from qf_lib.backtesting.trading_session.backtest_trading_session_builder import BacktestTradingSessionBuilder
        from qf_lib.common.enums.frequency import Frequency
        from qf_lib.common.enums.price_field import PriceField
        from qf_lib.common.enums.security_type import SecurityType
        from qf_lib.common.tickers.tickers import BloombergTicker
        from qf_lib.containers.qf_data_array import QFDataArray
        from qf_lib.data_providers.preset_data_provider import PresetDataProvider
        from qf_lib.documents_utils.document_exporting.pdf_exporter import PDFExporter
        from qf_lib.documents_utils.excel.excel_exporter import ExcelExporter
        from qf_lib.tests.unit_tests.config.test_settings import get_test_settings

        T = BloombergTicker("X US Equity", SecurityType.STOCK, 1)
        dates = pd.DatetimeIndex([pd.Timestamp(b["t_ns"], unit="ns") for b in bars])
        if dates[0].normalize() != dates[-1].normalize():
            raise NotExpressible(f"{TOOL}: 場面の足が日をまたぐ(この adapter は 1 日の分足の会期だけを作る)")
        fields = PriceField.ohlcv()
        arr = np.zeros((n, 1, len(fields)))
        for i, b in enumerate(bars):
            arr[i, 0, :] = [b["open"], b["high"], b["low"], b["close"], 1e12]
        data = QFDataArray.create(dates, [T], fields, data=arr)
        dp = PresetDataProvider(data, dates[0], dates[-1] + pd.Timedelta(minutes=1), Frequency.MIN_1)
        settings = get_test_settings()
        b_ = BacktestTradingSessionBuilder(settings, PDFExporter(settings), ExcelExporter(settings))
        b_.set_frequency(Frequency.MIN_1)
        b_.set_market_open_and_close_time({"hour": 0, "minute": 0}, {"hour": 23, "minute": 59})
        b_.set_initial_cash(int(cfg["initial_equity"]))
        b_.set_data_provider(dp)
        b_.set_monitor_settings(BacktestMonitorSettings.no_stats())
        b_.set_commission_model(BpsTradeValueCommissionModel, commission=cfg["costs"]["taker_fee_pct"] * 100)
        a = adj(cfg["costs"])
        if a:
            b_.set_slippage_model(PriceBasedSlippage, slippage_rate=a)
        ts = b_.build(dates[0], dates[-1])
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        st = {"entry_bar": None, "lvl": None, "stop": None, "pos": 0.0}
        t0 = dates[0]

        class Scene(AbstractStrategy):
            def calculate_and_place_orders(self):
                now = ts.data_provider.timer.now()
                k = int((pd.Timestamp(now) - t0) / pd.Timedelta(minutes=1)) - 1
                if k < 0 or k >= n:
                    return
                p = ts.portfolio.open_positions_dict.get(T)
                pos = float(p.quantity()) if p is not None else 0.0
                if pos != 0 and st["pos"] == 0:          # the entry was filled since the last event
                    st["entry_bar"] = k + 1              # filled at this event's minute: the open of the bar that starts then
                    d = 1 if pos > 0 else -1
                    px = float(p.avg_price_per_unit()) if hasattr(p, "avg_price_per_unit") else None
                    if W:
                        eb = k + 1
                        win = bars[max(0, eb - W):eb]
                        st["lvl"] = (min(x["low"] for x in win) if d > 0 else max(x["high"] for x in win)) if win else None
                    if cfg["stop_loss_pct"] and px:
                        o = ts.order_factory.orders({T: -pos}, StopOrder(px * (1 - d * cfg["stop_loss_pct"] / 100)),
                                                    TimeInForce.GTC)
                        ts.broker.place_orders(o)
                        st["stop"] = o
                if pos == 0 and st["pos"] != 0:
                    ts.broker.cancel_all_open_orders()
                    st["entry_bar"] = st["lvl"] = st["stop"] = None
                st["pos"] = pos
                s = sig.get(k)
                cl = bars[k]["close"]

                def exit_now():
                    ts.broker.cancel_all_open_orders()
                    ts.broker.place_orders(ts.order_factory.orders({T: -pos}, MarketOrder(), TimeInForce.GTC))

                if pos != 0:
                    if N is not None and st["entry_bar"] is not None and k + 1 - st["entry_bar"] >= N:
                        exit_now(); return
                    if st["lvl"] is not None and ((cl < st["lvl"]) if pos > 0 else (cl > st["lvl"])):
                        exit_now(); return
                if not s:
                    return
                if pos != 0 and (s == "CLOSE" or (s == "BUY") != (pos > 0)):
                    exit_now(); return
                if pos != 0 or s == "CLOSE":
                    return
                if s == "SELL" and not cfg["allow_short"]:
                    return
                if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                    return
                if cfg["entry_mask"] is not None and not cfg["entry_mask"][k]:
                    return
                q = cfg["order_notional"] / cl
                ts.broker.place_orders(ts.order_factory.orders({T: q if s == "BUY" else -q}, MarketOrder(), TimeInForce.GTC))

        CalculateAndPlaceOrdersPeriodicEvent.set_frequency(Frequency.MIN_1)
        s1, s2 = dates[0] + pd.Timedelta(minutes=1), dates[-1]
        CalculateAndPlaceOrdersPeriodicEvent.set_start_and_end_time(
            {"hour": s1.hour, "minute": s1.minute}, {"hour": s2.hour, "minute": s2.minute})
        strat = Scene(ts)
        strat.subscribe(CalculateAndPlaceOrdersPeriodicEvent)
        try:
            ts.start_trading()
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        fills, pos = [], 0.0
        for t in ts.monitor.backtest_result.transactions:
            k = int((pd.Timestamp(t.transaction_fill_time) - t0) / pd.Timedelta(minutes=1))
            q = float(t.quantity)
            side = ("OPEN_LONG" if q > 0 else "OPEN_SHORT") if pos == 0 else ("CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
            fills.append({"bar": k, "side": side, "price": float(t.price), "size": abs(q)})
            pos = round(pos + q, 12)
        pnls = [float(p.total_pnl) for p in ts.portfolio.closed_positions()]
        return want(inp, {"fills": fills, "pnls": pnls})


TARGET = QfLib()
