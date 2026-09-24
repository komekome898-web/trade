"""Survey candidate 121 `mhallsmoore/qstrader` (PyPI `qstrader` 0.3.0), run in its own venv.

Driven through its public API: `BacktestTradingSession(start, end, universe,
alpha_model, rebalance='daily', fee_model=, data_handler=)`, `StaticUniverse`,
`BacktestDataHandler` with `CSVDailyBarDataSource` (daily OHLCV CSV files, the
documented data source), an `AlphaModel` subclass (the strategy: called with
`dt` at each rebalance, returns target weights), and a `FeeModel` subclass.
QSTrader has no order API for the strategy: the strategy returns weights and
the portfolio construction turns them into orders.
The CSV files are written to a temporary directory in the scratchpad.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from qstrader import settings  # noqa: E402
from qstrader.alpha_model.alpha_model import AlphaModel  # noqa: E402
from qstrader.asset.equity import Equity  # noqa: E402
from qstrader.asset.universe.static import StaticUniverse  # noqa: E402
from qstrader.broker.fee_model.fee_model import FeeModel  # noqa: E402
from qstrader.data.backtest_data_handler import BacktestDataHandler  # noqa: E402
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource  # noqa: E402
from qstrader.trading.backtest import BacktestTradingSession  # noqa: E402

settings.PRINT_EVENTS = False
logging.disable(logging.CRITICAL)
SYM = "EQ:X"


def _write(bars: list[dict]) -> str:
    rows = [C.as_bar(b) for b in bars]
    d = tempfile.mkdtemp(prefix="qstrader_csv_")
    df = pd.DataFrame({"Date": [pd.Timestamp(b["ts_ns"], unit="ns").strftime("%Y-%m-%d") for b in rows],
                       "Open": [b["open"] for b in rows], "High": [b["high"] for b in rows], "Low": [b["low"] for b in rows],
                       "Close": [b["close"] for b in rows], "Adj Close": [b["close"] for b in rows],
                       "Volume": [b.get("volume", 1.0) for b in rows]})
    df.to_csv(os.path.join(d, "X.csv"), index=False)
    return d


def run(bars, alpha, fee_model=None, cash=1_000_000.0):
    d = _write(bars)
    universe = StaticUniverse([SYM])
    src = CSVDailyBarDataSource(d, Equity, csv_symbols=["X"])
    dh = BacktestDataHandler(universe, data_sources=[src])
    rows = [C.as_bar(b) for b in bars]
    start = pd.Timestamp(rows[0]["ts_ns"], unit="ns", tz="UTC").normalize()
    end = pd.Timestamp(rows[-1]["ts_ns"], unit="ns", tz="UTC").normalize() + pd.Timedelta(days=1)
    st = {"n": 0, "log": []}

    class A(AlphaModel):
        def __call__(self, dt, *args, **kw):
            st["n"] += 1
            return alpha(dt, dh, st["n"], st) or {}

    kw = {"fee_model": fee_model} if fee_model is not None else {}
    sess = BacktestTradingSession(start, end, universe, A(), initial_cash=cash, rebalance="daily",
                                  long_only=True, cash_buffer_percentage=0.01, data_handler=dh, **kw)
    sess.run(results=False)
    return st, sess


def _ns(dt) -> int:
    return int(pd.Timestamp(dt).value)


NON_BAR = "QSTrader のデータは日足の CSV(Date/Open/High/Low/Close/Adj Close/Volume)で、{k} の型は無い。試したこと: {err}"


def _try_non_bar(e: dict) -> str:
    d = tempfile.mkdtemp(prefix="qstrader_nonbar_")
    pd.DataFrame([{"Date": "2023-11-16", **{k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)}}]).to_csv(
        os.path.join(d, "X.csv"), index=False)
    try:
        CSVDailyBarDataSource(d, Equity, csv_symbols=["X"])
    except Exception as exc:  # noqa: BLE001
        return f"CSVDailyBarDataSource に {list(C.fields_of(e))} の列の CSV を読ませた -> {type(exc).__name__}: {str(exc)[:160]}"
    return "CSVDailyBarDataSource は例外なく読んだ"


def _no_kw(name: str) -> str:
    try:
        BacktestTradingSession(pd.Timestamp("2023-11-15", tz="UTC"), pd.Timestamp("2023-11-20", tz="UTC"), StaticUniverse([SYM]),
                               lambda dt: {}, **{name: object()})
    except TypeError as exc:
        return f"BacktestTradingSession(..., {name}=...) -> TypeError: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"BacktestTradingSession(..., {name}=...) -> {type(exc).__name__}: {str(exc)[:160]}(未知の引数は **kwargs で受けて使わない)"
    return f"BacktestTradingSession(..., {name}=...) は受け付けられた"


class QstraderAdapter(Adapter):
    name = "opp_qstrader"

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        st, _ = run(C.events(sc), lambda dt, dh, n, st: st["log"].append(["bar", _ns(dt)]))
        return ok({"sequence": st["log"]}, "日足 5 本、rebalance='daily'。AlphaModel の各回の dt")

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        return ok(int(pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value), "QSTrader の時刻は pandas の Timestamp(UTC)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0} for e in C.events(sc)]
        try:
            st, _ = run(evs, lambda dt, dh, n, st: st["log"].append(_ns(dt)))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"日足の CSV に書いて走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "日足の CSV(日付だけの列)に書いた。AlphaModel の dt")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        def f(dt, dh, n, st):
            st["log"].append(["bar", _ns(dt)])
            out["close"] = float(dh.get_asset_latest_mid_price(dt, SYM))

        st, _ = run([e], f)
        return ok({"sequence": st["log"], "fields": out}, "日足 1 本。戦略(AlphaModel)が読めるのは data_handler の bid/ask/mid と終値の範囲で、始値・高値・安値・出来高を読む口は無い")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def scene_p3_clock_timer(self, sc):
        return not_supported("時刻を頼む口は rebalance の暦の規則(buy_and_hold/daily/weekly/end_of_month)だけで、決まった時刻を 1 回頼む口が無い。試したこと: "
                             + _no_kw("timer"))

    def _notice(self, sc):
        return not_supported("戦略(AlphaModel)は目標の重みを返すだけで、注文の受付・拒否・約定・取消の知らせを受ける口が無い。試したこと: " + _no_kw("order_listener"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out = {}
        first = pd.Timestamp(sc.input["events"][0]["ts_ns"], unit="ns", tz="UTC")

        def f(dt, dh, n, st):
            st["log"].append(_ns(dt))
            if pd.Timestamp(dt).normalize() == pd.Timestamp(probe, unit="ns", tz="UTC"):
                s = dh.get_assets_historical_range_close_price(first, dt, [SYM])[SYM]
                out["visible_count"] = int(s.notna().sum())
                out["max_visible_close"] = float(s.max())

        st, _ = run(C.events(sc), f)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(out, f"T0 + 4 日の日の呼び出しで data_handler.get_assets_historical_range_close_price(最初の日, dt)。呼ばれた dt: {st['log']}")

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_try_non_bar({"ts_ns": 0, "Open": 1, "Close": 1, "recv_ns": 1})))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        nxt = pd.Timestamp(sc.input["future_ts_ns"], unit="ns", tz="UTC")
        att = C.Attempts()

        def f(dt, dh, n, st):
            if pd.Timestamp(dt).normalize() != pd.Timestamp(probe, unit="ns", tz="UTC") or att.items:
                return
            att.run("data_handler.get_asset_latest_mid_price(5 本目の日時, 銘柄)", "time",
                    lambda: dh.get_asset_latest_mid_price(nxt + pd.Timedelta(hours=21), SYM))
            att.run("data_handler.get_assets_historical_range_close_price(dt, 5 本目の日時)", "time",
                    lambda: list(dh.get_assets_historical_range_close_price(pd.Timestamp(dt), nxt + pd.Timedelta(hours=21), [SYM])[SYM]))

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の日の呼び出しで、戦略が持つ data_handler に先の日時を渡して試した: " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        try:
            st, _ = run([C.as_bar(e) for e in C.events(sc)], lambda dt, dh, n, st: st["log"].append(float(dh.get_asset_latest_mid_price(dt, SYM))))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ日の 3 行の CSV で走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "同じ日の 3 行を CSV に書いた")

    def _no_order_api(self, sc):
        return not_supported("戦略が注文を出す・取り消す・注文を読む口が無い(AlphaModel は目標の重みを返すだけ)。試したこと: " + _no_kw("order_api"))

    scene_p6_place_then_cancel = scene_p6_cancel_notice = scene_p6_fill_seen_by_strategy = _no_order_api

    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を渡す口が無い(SimulatedExchange / SimulatedBroker は内部で作られる)。試したこと: " + _no_kw("execution_handler"))

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い。試したこと: " + _no_kw("latency_model"))

    def _fee(self, sc, fee, per_unit: bool = False, weight: float = 1.0):
        def cost(quantity):
            return fee * abs(quantity) if per_unit else fee

        class Flat(FeeModel):
            def _calc_commission(self, asset, quantity, consideration, broker=None):
                return cost(quantity)

            def _calc_tax(self, asset, quantity, consideration, broker=None):
                return 0.0

            def calc_total_cost(self, asset, quantity, consideration, broker=None):
                return cost(quantity)

        st, sess = run([C.as_bar(e) for e in C.events(sc)], lambda dt, dh, n, st: {SYM: weight}, fee_model=Flat(), cash=100_000.0)
        port = sess.broker.portfolios[list(sess.broker.portfolios)[0]]
        hist = port.history_to_df()
        rows = hist.to_dict("records")
        comm = []
        for r in rows:
            if r.get("type") == "asset_transaction":
                parts = str(r["description"]).split()  # e.g. "LONG 989 EQ:X 100.00 17/11/2023"
                comm.append(round(float(r["debit"]) - int(parts[1]) * float(parts[3]), 10))
        return ok({"fee": float(comm[0]) if comm else None},
                  f"fee_model に FeeModel の子({'数量 1 単位あたり' if per_unit else '1 件'} {fee})。戦略は重み {weight} を返す(数量は重みから決まる)。ポートフォリオの履歴の最初の asset_transaction の debit − 数量 × 価格(description の値)を手数料とした。履歴: {rows[:3]}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        # QSTrader orders by target weight only. A weight that would be 2.5 units (0.002525 of 100,000 less the
        # 1 % cash buffer, at 100) was tried; the session scales the weights (measured: it bought 990 units), so
        # the scene's order of quantity 2 cannot be placed and the per-unit fee cannot be read for it.
        r = self._fee(sc, 0.375, per_unit=True, weight=0.002525)
        return not_supported("数量を指定した注文を出す口が無い(戦略は目標の重みを返すだけ)。試したこと: 数量 2.5 単位に当たる重み 0.002525 を返し、"
                             "fee_model に数量 1 単位あたり 0.375 円の FeeModel の子を渡した -> " + r.detail[:600])

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(SimulatedBroker / Portfolio)は BacktestTradingSession の中で作られ、差し替える口が無い。試したこと: " + _no_kw("broker"))
