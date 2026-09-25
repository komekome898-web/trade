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
    # round r8-1 (positive definition A): every setting through common.configure; start / end are the configured
    # target's chosen window, the same in every scene (until round r8-1: the scene's first and last bar)
    universe = C.configure(StaticUniverse, [SYM], what="StaticUniverse([銘柄])", decided_from=("場面の入力",))
    src = C.configure(CSVDailyBarDataSource, d, Equity, csv_symbols=["X"], what="CSVDailyBarDataSource(場面の足の CSV, Equity)",
                      decided_from=("場面の入力",))
    dh = C.configure(BacktestDataHandler, universe, data_sources=[src], what="BacktestDataHandler(universe, [source])",
                     decided_from=("場面の入力",))
    start, end = pd.Timestamp(C.FIXED_WINDOW[0], tz="UTC"), pd.Timestamp(C.FIXED_WINDOW[1], tz="UTC")
    st = {"n": 0, "log": []}

    class A(AlphaModel):
        def __call__(self, dt, *args, **kw):
            st["n"] += 1
            return alpha(dt, dh, st["n"], st) or {}

    kw = {"fee_model": fee_model} if fee_model is not None else {}
    sess = C.configure(BacktestTradingSession, start, end, universe, A(), initial_cash=cash, rebalance="daily",
                       long_only=True, cash_buffer_percentage=0.01, data_handler=dh, **kw,
                       what=f"BacktestTradingSession({start.date()}, {end.date()}, universe, 場面の AlphaModel, initial_cash={cash}, "
                            f"rebalance=daily, long_only, cash_buffer_percentage=0.01, data_handler"
                            f"{', fee_model=場面の費用の模型' if kw else ''})", decided_from=("選ぶ値", "場面の入力"))
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


def _mid(dt, dh, st, car) -> None:
    """The price the strategy reads at `dt`, through QSTrader's data_handler (round r6-3: the value
    returned by the tool's function is the carrier, returned_by = QSTrader's backtest_data_handler.py)."""
    v = C.read(dh.get_asset_latest_mid_price, dt, SYM)
    st["log"].append(float(v))
    car.append(C.carrier(v))


def _bar_like_classes() -> list[str]:
    """Every class of QSTrader's distribution whose name has Bar or Event (walked with pkgutil)."""
    import importlib
    import inspect
    import pkgutil
    import qstrader
    found = set()
    for m in pkgutil.walk_packages(qstrader.__path__, "qstrader."):
        try:
            mod = importlib.import_module(m.name)
        except Exception:  # noqa: BLE001
            continue
        for _, c in inspect.getmembers(mod, inspect.isclass):
            if c.__module__ == mod.__name__ and ("bar" in c.__name__.lower() or "event" in c.__name__.lower()):
                found.add(f"{c.__module__}.{c.__qualname__}")
    return sorted(found)


class QstraderAdapter(Adapter):
    name = "opp_qstrader"
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"window": list(C.FIXED_WINDOW), "rebalance": "daily", "long_only": True, "cash_buffer_percentage": 0.01}}

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda dt, dh, n, st: (st["log"].append(["bar", _ns(dt)]), car.append(C.carrier(dt))) and None)
        return ok({"sequence": st["log"]}, "日足 5 本、rebalance='daily'。AlphaModel の各回の dt(round r6-3: carrier は QSTrader が "
                  "AlphaModel の呼び出しに渡す dt そのもの。足の物は戦略に届かず、値は data_handler の読み出しで得る)", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        """The ISO string written as it is into the Date column of a CSV read by QSTrader's own CSVDailyBarDataSource."""
        d = tempfile.mkdtemp(prefix="qstrader_iso_")
        pd.DataFrame({"Date": [sc.input["iso"]], "Open": [1], "High": [1], "Low": [1], "Close": [1], "Adj Close": [1],
                      "Volume": [1]}).to_csv(os.path.join(d, "X.csv"), index=False)
        try:
            src = CSVDailyBarDataSource(d, Equity, csv_symbols=["X"])
            v = src.asset_bar_frames[SYM].index[0]
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ISO の文字列を Date の列に書いた CSV を CSVDailyBarDataSource で読んだ -> {type(exc).__name__}: {str(exc)[:160]}")
        t = pd.Timestamp(v)
        return ok(int((t if t.tzinfo is None else t.tz_convert("UTC")).value), f"CSVDailyBarDataSource が読んだ Date {v!r}",
                  {"reader": C.qualname(CSVDailyBarDataSource)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): no entry that reads a time in a unit
    def _units(self, sc):
        return C.unit_time(sc, [], tried='時刻の入口は CSVDailyBarDataSource の Date の欄だけで、単位を受ける引数が無い' + '(r16-1 の場面係が道具の配布物を fromtimestamp・unit=・timestamp_to_datetime・datetime64[s/ms/us]・/1000・*1000・epoch で検索した範囲。記録 survey_results/attempts/r16-1_unit_entries.txt)' + "。" + C.iso_entry_tried(self._iso, sc))

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _ts(self, sc):
        evs = [C.substitute(e, "trade", price=100.0) for e in C.events(sc)]
        car = []
        try:
            st, _ = run(evs, lambda dt, dh, n, st: (st["log"].append(_ns(dt)), car.append(C.carrier(dt))) and None)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"日足の CSV に書いて走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": st["log"]}, "日足の CSV(日付だけの列)に書いた。AlphaModel の dt", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        # round r6-3: QSTrader hands the AlphaModel only `dt` (the ts of its SimulationEvent); no bar object
        # reaches the strategy (the earlier record carried the data_handler the adapter built and kept).
        seen = []

        def f(dt, dh, n, st):
            seen.append((type(dt).__name__, _ns(dt), float(dh.get_asset_latest_mid_price(dt, SYM))))

        run([e], f)
        return not_supported("QSTrader が戦略(AlphaModel.__call__)に渡すのは dt(SimulationEvent の ts)だけで、足の型の物は届かない。"
                             f"配布物の class は {_bar_like_classes()} で、足を運ぶ事象の型が無い。日足 1 本を CSV で渡して試した: "
                             f"呼び出しで受けた (dt の型, 時刻, data_handler の mid) = {seen}(始値・高値・安値・出来高を読む口も無い)")

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
        reads = C.Reads()
        first = pd.Timestamp(sc.input["events"][0]["ts_ns"], unit="ns", tz="UTC")

        def f(dt, dh, n, st):
            st["log"].append(_ns(dt))
            if pd.Timestamp(dt).normalize() == pd.Timestamp(probe, unit="ns", tz="UTC") and not reads.items:
                reads.read("data_handler.get_assets_historical_range_close_price(最初の日, dt)(NaN の行は足が無い)",
                           lambda: [x for x in dh.get_assets_historical_range_close_price(first, dt, [SYM])[SYM] if x == x])

        st, _ = run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(reads.output(), f"T0 + 4 日の日の呼び出しで data_handler.get_assets_historical_range_close_price(最初の日, dt)。呼ばれた dt: {st['log']}",
                  reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_try_non_bar({"ts_ns": 0, "Open": 1, "Close": 1, "recv_ns": 1})))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(dt, dh, n, st):
            if pd.Timestamp(dt).normalize() != pd.Timestamp(probe, unit="ns", tz="UTC") or att.items:
                return
            # namings: the scene's fixed list; the adapter's CSV dates a bar by the day of its close (the scene's times, at 21:00)
            ts = (lambda ns: pd.Timestamp(int(ns), unit="ns", tz="UTC") + pd.Timedelta(hours=21))
            C.try_time_namings(att, "data_handler.get_asset_latest_mid_price(時刻, 銘柄)", "time_at",
                               lambda t: dh.get_asset_latest_mid_price(t, SYM), sc, ts)
            C.try_time_namings(att, "data_handler.get_assets_historical_range_close_price(始, 終, [銘柄])", "time_range",
                               lambda a, b: list(dh.get_assets_historical_range_close_price(a, b, [SYM])[SYM]), sc, ts)

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の日の呼び出しで、戦略が持つ data_handler に先の日時を渡して試した: " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        car = []
        try:
            st, _ = run([C.as_bar(e) for e in C.events(sc)],
                        lambda dt, dh, n, st: _mid(dt, dh, st, car))
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ日の 3 行の CSV で走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "同じ日の 3 行を CSV に書いた", {"carriers": car})

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
