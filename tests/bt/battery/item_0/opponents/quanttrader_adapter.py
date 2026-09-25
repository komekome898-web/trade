"""Survey candidate 68 `quanttrader` (PyPI `quanttrader` 0.5.5), run in its own venv.

Driven through its public API: `BacktestEngine(start, end)`, `set_capital`,
`add_data(symbol, DataFrame)`, `set_strategy`, `run()`, and a `StrategyBase`
subclass (`on_tick`, `on_order_status`, `on_fill`, `place_order(OrderEvent)`,
`cancel_order`), reading prices through the engine's `DataBoard`
(`get_hist_price`, `get_current_price`). The engine emits one tick per
DataFrame index entry; the tick carries only the time (the price is read from
the data board, backtest_data_feed.py 1-10).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from quanttrader.backtest_engine import BacktestEngine  # noqa: E402
from quanttrader.order.order_event import OrderEvent  # noqa: E402
from quanttrader.order.order_status import OrderStatus  # noqa: E402
from quanttrader.order.order_type import OrderType  # noqa: E402
from quanttrader.strategy.strategy_base import StrategyBase  # noqa: E402

logging.disable(logging.CRITICAL)
SYM = "X STK SMART"
STATUS = {OrderStatus.ACKNOWLEDGED: "accepted", OrderStatus.SUBMITTED: "accepted", OrderStatus.FILLED: "filled",
          OrderStatus.CANCELED: "canceled", OrderStatus.ERROR: "rejected"}


def _df(bars: list[dict]) -> pd.DataFrame:
    rows = [C.as_bar(b) for b in bars]
    idx = pd.to_datetime([b["ts_ns"] for b in rows], unit="ns")
    return pd.DataFrame({"Open": [float(b["open"]) for b in rows], "High": [float(b["high"]) for b in rows],
                         "Low": [float(b["low"]) for b in rows], "Close": [float(b["close"]) for b in rows],
                         "Volume": [float(b.get("volume", 1.0)) for b in rows]}, index=idx)


def run(bars, fn, cash=1_000_000.0):
    df = _df(bars)
    st = {"n": 0, "log": [], "notices": [], "fills": []}

    class S(StrategyBase):
        def __init__(self):
            super().__init__()
            self.name = "s"

        def on_tick(self, tick):
            super().on_tick(tick)
            st["n"] += 1
            fn(self, tick, st["n"], st)

        def on_order_status(self, oe):
            super().on_order_status(oe)
            st.setdefault("raw_status", []).append(str(oe.order_status))
            name = STATUS.get(oe.order_status)
            if name and name != "filled":  # a fill is counted once, from on_fill
                st["notices"].append(name)

        def on_fill(self, fe):
            super().on_fill(fe)
            st["notices"].append("filled")
            st["fills"].append({"price": fe.fill_price, "size": fe.fill_size, "commission": fe.commission,
                                "time": str(fe.fill_time)})

    # round r8-1 (positive definition A): every setting through common.configure; the engine's start and end are the
    # configured target's chosen window, the same in every scene (until round r8-1: the scene's first and last time)
    start, end = pd.Timestamp(C.FIXED_WINDOW[0]), pd.Timestamp(C.FIXED_WINDOW[1])
    eng = C.configure(BacktestEngine, start, end, what=f"BacktestEngine({start.date()}, {end.date()})", decided_from=("選ぶ値",))
    C.configure(eng.set_capital, cash, what=f"engine.set_capital({cash})", decided_from=("場面の入力",))
    s = S()
    C.configure(s.set_capital, cash, what=f"strategy.set_capital({cash})", decided_from=("場面の入力",))
    C.configure(s.set_symbols, [SYM], what="strategy.set_symbols([銘柄])", decided_from=("場面の入力",))
    C.configure(eng.set_strategy, s, what="engine.set_strategy(場面の戦略)", decided_from=("場面の入力",))
    C.configure(eng.add_data, SYM, df, what="engine.add_data(銘柄, 場面の足の DataFrame)", decided_from=("場面の入力",))
    eng.run()
    return st, eng


def _now(tick) -> int:
    return int(pd.Timestamp(tick.timestamp).value)


def _order(s, size, limit=None, ts=None):
    o = OrderEvent()
    o.create_time = ts  # the backtest brokerage prices the order at create_time (backtest_brokerage.py 142-143)
    o.full_symbol = SYM
    o.order_type = OrderType.LIMIT if limit is not None else OrderType.MARKET
    o.order_size = size
    if limit is not None:
        o.limit_price = limit
    s.place_order(o)
    return o


NON_BAR = ("quanttrader の入力は add_data に渡す銘柄ごとの DataFrame(時刻の index)で、刻みはその index の時刻だけ(tick は時刻しか持たない)。"
           "{k} の型は無い。試したこと: {err}")


def _try_non_bar(e: dict) -> str:
    df = pd.DataFrame([{k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)}], index=pd.to_datetime([e["ts_ns"]], unit="ns"))
    got = []

    class S(StrategyBase):
        def __init__(self):
            super().__init__()
            self.name = "s"

        def on_tick(self, tick):
            got.append((tick.full_symbol, str(tick.timestamp), tick.price))

    try:
        eng = BacktestEngine(df.index[0], df.index[-1])
        s = S()
        s.set_symbols([SYM])
        eng.set_strategy(s)
        eng.add_data(SYM, df)
        eng.run()
    except Exception as exc:  # noqa: BLE001
        return f"add_data(<{list(df.columns)} の DataFrame>) で走らせた -> {type(exc).__name__}: {str(exc)[:160]}"
    return f"add_data(<{list(df.columns)} の DataFrame>) で走らせた。on_tick が受け取ったのは (銘柄, 時刻, 価格) = {got} で、型と中身は届かない"


class QuanttraderAdapter(Adapter):
    name = "opp_quanttrader"
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"window": list(C.FIXED_WINDOW)}}

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda s, t, n, st: (st["log"].append(["bar", _now(t)]), car.append(C.carrier(t))))
        return ok({"sequence": st["log"]}, "足 5 本。on_tick の各回に tick.timestamp", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    def _iso(self, sc):
        """The ISO string written as it is into the first column of a CSV read by quanttrader's own
        reader `quanttrader.util.util_func.read_ohlcv_csv`."""
        import tempfile
        from quanttrader.util.util_func import read_ohlcv_csv
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "X.csv"
            path.write_text(f"Date,Open,High,Low,Close,Adj Close,Volume\n{sc.input['iso']},1,1,1,1,1,1\n", encoding="utf-8")
            try:
                df = read_ohlcv_csv(str(path), adjust=False)
                v = df.index[0]
            except Exception as exc:  # noqa: BLE001
                return not_supported(f"ISO の文字列を最初の列に書いた CSV を read_ohlcv_csv で読んだ -> {type(exc).__name__}: {str(exc)[:160]}")
        t = pd.Timestamp(v)
        return ok(int((t if t.tzinfo is None else t.tz_convert("UTC")).value), f"read_ohlcv_csv が読んだ添字 {v!r}",
                  {"reader": C.qualname(read_ohlcv_csv)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): no entry that reads a time in a unit
    def _units(self, sc):
        return C.unit_time(sc, [], tried='時刻の入口は read_ohlcv_csv の最初の欄だけで、単位を受ける引数が無い(ib_brokerage の fromtimestamp はネットワークの道で、§4 により使わない)' + '(r16-1 の場面係が道具の配布物を fromtimestamp・unit=・timestamp_to_datetime・datetime64[s/ms/us]・/1000・*1000・epoch で検索した範囲。記録 survey_results/attempts/r16-1_unit_entries.txt)' + "。" + C.iso_entry_tried(self._iso, sc))

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _ts(self, sc):
        evs = [C.substitute(e, "trade", price=100.0) for e in C.events(sc)]
        car = []
        st, _ = run(evs, lambda s, t, n, st: (st["log"].append(_now(t)), car.append(C.carrier(t))))
        return ok({"observed_ts_ns": st["log"]}, "足で渡し、on_tick の tick.timestamp", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}
        car = []

        def f(s, t, n, st):
            st["log"].append(["bar", _now(t)])
            car.append(C.carrier(t))
            row = s._data_board.get_hist_price(SYM, t.timestamp).iloc[-1]
            out.update({"open": float(row["Open"]), "high": float(row["High"]), "low": float(row["Low"]),
                        "close": float(row["Close"]), "volume": float(row["Volume"])})

        st, _ = run([e], f)
        return ok({"sequence": st["log"], "fields": out}, "足 1 本。data_board.get_hist_price(銘柄, 時刻) の最後の行", {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(C.events(sc)[0])))

    def scene_p3_clock_timer(self, sc):
        names = [n for n in dir(StrategyBase) if "timer" in n.lower() or "schedule" in n.lower()]
        try:
            BacktestEngine().add_timer(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported(f"時刻を頼んで呼ばれる口が無い(StrategyBase の timer/schedule の名前: {names})。試したこと: BacktestEngine().add_timer(...) -> {r}")

    def _notice_run(self, sc, fn, cash):
        return run([C.as_bar(e) for e in C.events(sc)], fn, cash=cash)

    def scene_p3_notice_accepted(self, sc):
        st, _ = self._notice_run(sc, lambda s, t, n, st: _order(s, 1, 90.0, t.timestamp) if n == 1 else None, 1_000_000)
        return ok({"notices": st["notices"]}, f"約定を足に代えた(any_type)。on_order_status / on_fill の列。on_order_status の生の状態: {st.get('raw_status')}")

    def scene_p3_notice_rejected(self, sc):
        st, _ = self._notice_run(sc, lambda s, t, n, st: _order(s, 1, None, t.timestamp) if n == 1 else None, 1_000)
        return ok({"notices": st["notices"]}, f"現金 1,000。成行 1。fills={st['fills']}")

    def scene_p3_notice_filled(self, sc):
        st, _ = self._notice_run(sc, lambda s, t, n, st: _order(s, 1, None, t.timestamp) if n == 1 else None, 1_000_000)
        return ok({"filled_qty_in_notices": float(sum(f["size"] for f in st["fills"])), "notices": st["notices"]}, f"on_fill: {st['fills']}")

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        reads = C.Reads()

        def f(s, t, n, st):
            if _now(t) == probe and not reads.items:
                reads.read("data_board.get_hist_price(銘柄, 今の時刻) の Close", lambda: list(s._data_board.get_hist_price(SYM, t.timestamp)["Close"]))

        run(C.events(sc), f)
        if not reads.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(reads.output(), "T0 + 4 日の on_tick で data_board.get_hist_price(銘柄, 時刻) を読んだ", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported(NON_BAR.format(k="受け取れる時刻", err=_try_non_bar(
            {"ts_ns": 1_700_006_400_000_000_000, "Close": 1.0, "recv_ns": 1})))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def f(s, t, n, st):
            if _now(t) != probe or att.items:
                return
            db = s._data_board  # the data board quanttrader hands every strategy (StrategyBase)
            # namings: the scene's fixed list
            ts = (lambda ns: pd.Timestamp(int(ns), unit="ns"))
            C.try_time_namings(att, "data_board.get_hist_price(銘柄, 終わりの時刻) の Close", "time_until",
                               lambda x: list(db.get_hist_price(SYM, x)["Close"]), sc, ts)
            C.try_time_namings(att, "data_board.get_current_price(銘柄, 時刻)", "time_at", lambda x: db.get_current_price(SYM, x), sc, ts)
            att.run("data_board.get_current_price(銘柄, 今の時刻)", "other", lambda: db.get_current_price(SYM, t.timestamp))

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の on_tick で試した(戦略が持つ data_board の公開の方法): " + att.summary())

    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]

        car = []

        def f(s, t, n, st):
            st["log"].append(float(s._data_board.get_current_price(SYM, t.timestamp)))
            car.append(C.carrier(t))

        try:
            st, _ = run(rows, f)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 行を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": st["log"]}, "約定を足に代え、同じ時刻の 3 行を渡した。on_tick ごとに data_board.get_current_price",
                  {"carriers": car})

    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(s, t, n, st):
            if n == 1:
                st["o"] = _order(s, 1, 90.0, t.timestamp)
            elif n == 2:
                out["open_at_call2"] = len(s._order_manager.standing_order_set)
                s.cancel_order(st["o"].order_id)
            elif n == 3:
                out["open_at_call3"] = len(s._order_manager.standing_order_set)

        try:
            run([C.as_bar(e) for e in C.events(sc)], f)
        except Exception as exc:  # noqa: BLE001
            return ok({**out, "error": f"{type(exc).__name__}: {exc}"}, f"指値 90 を出して走らせた途中で例外: {type(exc).__name__}: {str(exc)[:200]}")
        return ok(out, "指値 90 / order_manager.standing_order_set / cancel_order")

    def scene_p6_cancel_notice(self, sc):
        def f(s, t, n, st):
            if n == 1:
                st["o"] = _order(s, 1, 90.0, t.timestamp)
            elif n == 2:
                s.cancel_order(st["o"].order_id)

        try:
            st, _ = run([C.as_bar(e) for e in C.events(sc)], f)
        except Exception as exc:  # noqa: BLE001
            return ok({"cancel_notice_received": False, "error": f"{type(exc).__name__}: {exc}"}, f"走らせた途中で例外: {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]}, "on_order_status の列")

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, t, n, st):
            if n == 1:
                st["o"] = _order(s, 1, None, t.timestamp)
            elif n == 3:
                out["filled_qty_at_call3"] = float(s._position_manager.get_position_size(SYM))

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "3 回目に、戦略の position manager の get_position_size(銘柄)(quanttrader の StrategyBase が戦略に持たせる建玉の記録。"
                  "注文ごとの約定済み数量を戦略が読む公開の口は無い)")

    def scene_p7_fill_model_swap(self, sc):
        try:
            BacktestEngine().set_fill_model(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported(f"約定の模型を渡す口が無い(BacktestBrokerage が成行を今の価格で即時に埋める。backtest_brokerage.py)。試したこと: BacktestEngine().set_fill_model(...) -> {r}")

    def scene_p7_latency_model_swap(self, sc):
        try:
            BacktestEngine().set_latency(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported(f"遅延の模型を渡す口が無い(文書: Market order is immediately filled, no latency)。試したこと: BacktestEngine().set_latency(...) -> {r}")

    def _fee(self, sc):
        try:
            BacktestEngine().set_commission_model(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("費用の模型を渡す口が無い(手数料は BacktestBrokerage._calculate_commission に銘柄の種類ごとに固定で書かれている)。"
                             f"試したこと: BacktestEngine().set_commission_model(...) -> {r}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc)

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc)

    def scene_p7_account_swap(self, sc):
        try:
            BacktestEngine().set_position_manager(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported(f"口座(PositionManager)は BacktestEngine の中で作られ、差し替える口が無い。試したこと: BacktestEngine().set_position_manager(...) -> {r}")
