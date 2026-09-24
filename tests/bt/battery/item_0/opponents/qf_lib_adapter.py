"""Survey candidate 62 `qf-lib` (PyPI `qf-lib` 4.0.7), run in its own venv.

Driven through its public API: `BacktestTradingSessionBuilder` (data provider,
frequency, cash, `set_commission_model`, `set_slippage_model`,
`set_monitor_settings(BacktestMonitorSettings.no_stats())`),
`PresetDataProvider` over a `QFDataArray` of daily OHLCV, an
`AbstractStrategy` subscribed to `CalculateAndPlaceOrdersRegularEvent`
(the strategy is called at the scheduled time and reads data through the
data provider), `OrderFactory` / `BacktestBroker` for orders, and a
`SingleTimeEvent` subclass for a one-off timer.

qf-lib makes a daily bar dated D available after D ends, so a bar whose close
is T0 + i DAY is dated T0 + (i-1) DAY, and the strategy is triggered at 00:00
each day. The data array starts 10 days earlier with no values (NaN): qf-lib's
execution handler reads 7 days of history before the start (measured:
"Requested start date ... is before data bundle start date").
Installing it needed PyJWT, oauthlib and requests-oauthlib (its import chain
loads the Bloomberg DL provider); see the install log.
"""
from __future__ import annotations

import datetime as D
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from qf_lib.backtesting.events.time_event.regular_time_event.calculate_and_place_orders_event import \
    CalculateAndPlaceOrdersRegularEvent  # noqa: E402
from qf_lib.backtesting.events.time_event.single_time_event.single_time_event import SingleTimeEvent  # noqa: E402
from qf_lib.backtesting.execution_handler.commission_models.commission_model import CommissionModel  # noqa: E402
from qf_lib.backtesting.execution_handler.slippage.base import Slippage  # noqa: E402
from qf_lib.backtesting.monitoring.backtest_monitor import BacktestMonitorSettings  # noqa: E402
from qf_lib.backtesting.order.execution_style import MarketOrder  # noqa: E402
from qf_lib.backtesting.order.time_in_force import TimeInForce  # noqa: E402
from qf_lib.backtesting.strategies.abstract_strategy import AbstractStrategy  # noqa: E402
from qf_lib.backtesting.trading_session.backtest_trading_session_builder import BacktestTradingSessionBuilder  # noqa: E402
from qf_lib.common.enums.frequency import Frequency  # noqa: E402
from qf_lib.common.enums.price_field import PriceField  # noqa: E402
from qf_lib.common.tickers.tickers import BloombergTicker  # noqa: E402
from qf_lib.containers.qf_data_array import QFDataArray  # noqa: E402
from qf_lib.data_providers.preset_data_provider import PresetDataProvider  # noqa: E402

logging.getLogger("qf").setLevel(logging.ERROR)
logging.disable(logging.WARNING)

TK = BloombergTicker("X Equity")
FIELDS = [PriceField.Open, PriceField.High, PriceField.Low, PriceField.Close, PriceField.Volume]
DAY = 86_400 * 10**9


def _date(ns: int) -> D.datetime:
    return C.ns_to_dt(ns - DAY).replace(tzinfo=None)


def run(bars: list[dict], on_call, cash=1_000_000.0, setup=None, timer_at=None):
    rows = [C.as_bar(b) for b in bars]
    first = _date(rows[0]["ts_ns"])
    last = _date(rows[-1]["ts_ns"])
    dates = pd.DatetimeIndex([first + D.timedelta(days=i) for i in range(-10, (last - first).days + 1)])
    by_date = {_date(b["ts_ns"]): b for b in rows}
    if len(by_date) != len(rows):
        raise ValueError("two bars on the same day: a daily data array has one row per day")
    vals = np.array([[[float(by_date[d.to_pydatetime()][k]) if d.to_pydatetime() in by_date else np.nan
                       for k in ("open", "high", "low", "close", "volume")]] for d in dates], dtype=float)
    arr = QFDataArray.create(dates, [TK], FIELDS, vals)
    dp = PresetDataProvider(arr, dates[0], dates[-1] + D.timedelta(days=2), Frequency.DAILY)
    b = BacktestTradingSessionBuilder(None, None, None)
    b.set_monitor_settings(BacktestMonitorSettings.no_stats())
    b.set_data_provider(dp)
    b.set_frequency(Frequency.DAILY)
    b.set_initial_cash(int(cash))
    b.set_market_open_and_close_time({"hour": 0, "minute": 1}, {"hour": 23, "minute": 0})
    if setup:
        setup(b)
    start = first + D.timedelta(days=1) - D.timedelta(minutes=1)
    ts = b.build(start, last + D.timedelta(days=1))
    st = {"n": 0, "log": [], "clock": []}

    class Timer(SingleTimeEvent):
        def notify(self, listener):
            st["clock"].append(C.dt_to_ns(listener.timer.now().replace(tzinfo=D.timezone.utc)))

    class S(AbstractStrategy):
        def __init__(self, ts):
            super().__init__(ts)
            self.ts = ts

        def calculate_and_place_orders(self):
            st["n"] += 1
            if st["n"] == 1 and timer_at is not None:
                Timer.schedule_new_event(C.ns_to_dt(timer_at).replace(tzinfo=None), None)
            on_call(self, st["n"], st)

    CalculateAndPlaceOrdersRegularEvent.set_trigger_time({"hour": 0, "minute": 0, "second": 0, "microsecond": 0})
    s = S(ts)
    s.subscribe(CalculateAndPlaceOrdersRegularEvent)
    if timer_at is not None:
        ts.notifiers.scheduler.subscribe(Timer, listener=s)
    ts.start_trading()
    Timer._datetimes_to_data.clear()
    return st, ts


def _now(s) -> int:
    return C.dt_to_ns(s.timer.now().replace(tzinfo=D.timezone.utc))


def _bar_read(s, start):
    """What the strategy reads for the bars up to now (qf-lib hands the strategy no event object; the
    data provider's read is how a bar reaches it). Its class is the carrier of the bar."""
    return C.read(s.ts.data_provider.get_price, TK, PriceField.Close, start, s.timer.now())  # round r6-2: a read of the tool


def _closes(s, start):
    try:
        v = s.ts.data_provider.get_price(TK, PriceField.Close, start, s.timer.now())
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"
    if isinstance(v, float):
        return [v] if v == v else []
    return [float(x) for x in v.values if x == x]


NON_BAR = ("qf-lib のデータは data provider が返す銘柄ごとの価格の列(PriceField: Open/High/Low/Close/Volume)で、{k} の型は無い。"
           "試したこと: PriceField に {k} に当たる名前があるかを PriceField[...] で引いた -> {err}")


def _pricefield(name: str) -> str:
    try:
        PriceField[name]
    except KeyError as exc:
        return f"KeyError: {exc}"
    return "見つかった"


class QfLibAdapter(Adapter):
    name = "opp_qf_lib"

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="Trade・Funding", err=_pricefield("Trade") + " / " + _pricefield("Funding")))

    def scene_p1_one_call_per_event(self, sc):
        first = _date(sc.input["events"][0]["ts_ns"])
        car = []
        st, _ = run(C.events(sc), lambda s, n, st: (st["log"].append(["bar", _now(s)]), car.append(C.carrier(_bar_read(s, first)))))
        return ok({"sequence": st["log"]}, "日足 5 本。毎日 0 時の CalculateAndPlaceOrdersRegularEvent の各回に timer.now()"
                  "(carrier は各回に data_provider.get_price で読んだ物の class)", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="Trade", err=_pricefield("Trade")))

    def _iso(self, sc):
        """The ISO string written as it is into a CSV file read by qf-lib's own CSVDataProvider (its
        reader converts the date column); the value is the date it made (data_bundle.dates)."""
        import tempfile
        from qf_lib.data_providers.csv.csv_data_provider import CSVDataProvider
        iso = sc.input["iso"]
        rows = [iso] + [iso.replace("2024-01-01", f"2024-01-0{i}") for i in (2, 3)]  # 3 daily rows: the reader infers the frequency
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / f"{TK.as_string()}.csv").write_text("Dates,Close\n" + "\n".join(f"{r},1" for r in rows) + "\n", encoding="utf-8")
            try:
                dp = CSVDataProvider(d, TK, "Dates", {"Close": PriceField.Close}, frequency=Frequency.DAILY)
                v = dp.data_bundle.dates.values[0]
            except Exception as exc:  # noqa: BLE001
                return not_supported(f"ISO の文字列を日付の列に書いた CSV を CSVDataProvider で読んだ -> {type(exc).__name__}: {str(exc)[:200]}")
        t = pd.Timestamp(v)
        return ok(int((t if t.tzinfo is None else t.tz_convert("UTC")).value),
                  f"ISO の文字列を日付の列に書いた CSV を qf-lib の CSVDataProvider で読み、data_bundle.dates の最初 {v!r}",
                  {"reader": C.qualname(CSVDataProvider)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        first = _date(evs[0]["ts_ns"])
        car = []
        try:
            st, _ = run(evs, lambda s, n, st: (st["log"].append(_now(s)), car.append(C.carrier(_bar_read(s, first)))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ナノ秒の時刻の足を日足の配列に入れて走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "日足で渡し(日付に丸められる)、timer.now()", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_pricefield(e["kind"].capitalize())))
        out = {}
        car = []

        def f(s, n, st):
            st["log"].append(["bar", _now(s)])
            px = s.ts.data_provider.get_last_available_price(TK)
            row = C.read(s.ts.data_provider.get_price, TK, FIELDS, _date(e["ts_ns"]), s.timer.now())  # a read of the tool
            car.append(C.carrier(row))
            out.update({"open": float(row.iloc[-1][PriceField.Open]), "high": float(row.iloc[-1][PriceField.High]),
                        "low": float(row.iloc[-1][PriceField.Low]), "close": float(row.iloc[-1][PriceField.Close]),
                        "volume": float(row.iloc[-1][PriceField.Volume]), "last_available": float(px)})

        st, _ = run([e], f)
        return ok({"sequence": st["log"], "fields": {k: v for k, v in out.items() if k != "last_available"}},
                  f"日足 1 本。data_provider.get_price(ticker, OHLCV, 日付, now) の最後の行。get_last_available_price={out.get('last_available')}",
                  {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="Trade・Funding・Liquidation", err=_pricefield("Liquidation")))

    def scene_p3_clock_timer(self, sc):
        st, _ = run([C.as_bar(e) for e in C.events(sc)], lambda s, n, st: None, timer_at=sc.input["timer_at_ns"])
        return ok({"clock_calls_ns": st["clock"]}, "1 回目に SingleTimeEvent の子を schedule_new_event(頼む時刻)。呼ばれた時刻の列")

    def _notice(self, sc):
        from qf_lib.backtesting.broker import backtest_broker as bb
        names = [n for n in dir(bb.BacktestBroker) if "notif" in n.lower() or "callback" in n.lower() or "listener" in n.lower()]
        try:
            BacktestTradingSessionBuilder(None, None, None).add_order_listener(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("注文の受付・拒否・約定・取消を戦略に知らせる呼び出しが無い(戦略は broker.get_open_orders / get_positions で問い合わせる)。"
                             f"試したこと: BacktestTradingSessionBuilder().add_order_listener(...) -> {r}。BacktestBroker の名前で通知に当たるもの: {names}")

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()
        first = _date(sc.input["events"][0]["ts_ns"])

        def f(s, n, st):
            if _now(s) == probe and not reads.items:
                reads.read("data_provider.get_price(ticker, Close, 最初の日, now)",
                           lambda: [x for x in getattr(_bar_read(s, first), "values", []) if x == x])

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(reads.output(), "T0 + 4 日の呼び出しに data_provider.get_price(ticker, Close, 最初の日, now) を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_pricefield("ReceivedTime")) + "(1 行に日付は 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def vals(v):
            return [float(x) for x in getattr(v, "values", [v])]

        def f(s, n, st):
            if _now(s) != probe or att.items:
                return
            dp = s.ts.data_provider
            # namings: the scene's fixed list; a bar closing at t is dated t - 1 day in qf-lib (_date)
            C.try_time_namings(att, "data_provider.get_price(ticker, Close, 始, 終)", "time_range",
                               lambda a, b: vals(dp.get_price(TK, PriceField.Close, a, b)), sc, _date)
            att.run("historical_price(ticker, Close, 6)(件数)", "other", lambda: vals(dp.historical_price(TK, PriceField.Close, 6)))

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の呼び出しに試した: " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="Trade・Funding・Liquidation", err=_pricefield("Funding")))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        try:
            run([C.as_bar(e) for e in C.events(sc)], lambda s, n, st: None)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ日の 3 本を日足の配列に入れようとした -> {type(exc).__name__}: {exc}")
        return ok({"prices": []}, "例外は出なかった", {"carriers": []})

    def _order(self, s, qty):
        orders = s.ts.order_factory.orders({TK: qty}, MarketOrder(), TimeInForce.GTC)
        return s.ts.broker.place_orders(orders)

    def scene_p6_place_then_cancel(self, sc):
        from qf_lib.backtesting.order import execution_style as es
        return not_supported("指値の注文の型が無い(execution_style の型は "
                             + ", ".join(n for n in dir(es) if n.endswith("Order")) + ")。試したこと: execution_style.LimitOrder を引いた -> "
                             + ("見つかった" if hasattr(es, "LimitOrder") else "AttributeError"))

    def scene_p6_cancel_notice(self, sc):
        return self._notice(sc)

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, n, st):
            if n == 1:
                self._order(s, 1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(sum(p.quantity() for p in s.ts.broker.get_positions()))

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "3 回目に broker.get_positions() の数量(注文の約定済み数量を注文から読む口は無い)")

    def _buy(self, sc, setup, qty: int = 1):
        def f(s, n, st):
            if n == 1:
                self._order(s, qty)

        st, ts = run([C.as_bar(e) for e in C.events(sc)], f, cash=100_000.0, setup=setup)
        pos = ts.broker.get_positions()
        if not pos:
            return None
        p = pos[0]
        qty = float(p.quantity())
        comm = float(p.total_commission())
        price = (float(ts.portfolio.initial_cash) - float(ts.portfolio.current_cash) - comm) / qty
        return {"qty": qty, "commission": comm, "price": price}

    def scene_p7_fill_model_swap(self, sc):
        class Fixed(Slippage):
            def _get_fill_prices(self, date, orders, no_slippage_fill_prices, fill_volumes):
                return np.array([12345.0 for _ in orders])

        r = self._buy(sc, lambda b: b.set_slippage_model(Fixed))
        return ok({"fill_price": r["price"] if r else None},
                  "set_slippage_model(Slippage の子: _get_fill_prices が 12345 を返す)。約定の価格は "
                  f"(初めの現金 − 今の現金 − 手数料) ÷ 数量 で読んだ(Portfolio の公開の値): {r}")

    def scene_p7_latency_model_swap(self, sc):
        try:
            BacktestTradingSessionBuilder(None, None, None).set_latency_model(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("遅延の模型を渡す口が無い(set_scheduling_time_delay は約定の予定の時刻をずらす設定で、発注の遅延の模型ではない)。"
                             f"試したこと: builder.set_latency_model(...) -> {r}")

    def _fee(self, sc, fee):
        class Flat(CommissionModel):
            def calculate_commission(self, fill_quantity, fill_price):
                return fee

        r = self._buy(sc, lambda b: b.set_commission_model(Flat))
        return ok({"fee": r["commission"] if r else None}, f"set_commission_model(CommissionModel の子: 1 件 {fee})。建玉の total_commission(): {r}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        class PerUnit(CommissionModel):
            def calculate_commission(self, fill_quantity, fill_price):
                return 0.375 * abs(fill_quantity)

        r = self._buy(sc, lambda b: b.set_commission_model(PerUnit), qty=2)
        return ok({"fee": r["commission"] if r else None},
                  f"set_commission_model(CommissionModel の子: 0.375 × |fill_quantity|)、数量 2 の成行。建玉の total_commission(): {r}")

    def scene_p7_account_swap(self, sc):
        try:
            BacktestTradingSessionBuilder(None, None, None).set_portfolio(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("口座(Portfolio)は build() の中で作られ、差し替える口が無い(backtest_trading_session_builder.py の build)。"
                             f"試したこと: builder.set_portfolio(...) -> {r}")
