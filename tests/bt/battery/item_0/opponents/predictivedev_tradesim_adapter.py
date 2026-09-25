"""Survey candidate 37 `ThePredictiveDev/Automated-Financial-Market-Trading-System`
(distribution `trading-simulator` 2.2.0, built from the GitHub clone, commit
7482b362; core dependencies numpy, pandas, requests only; install record
`survey_results/attempts/37.log`), run in its own venv `c37`.

Driven through its public API: `trading_simulator.backtest.runner.run_backtest(
historical_data, market_maker, matching_engine, traders)` -- a loop over the
rows of a DataFrame with the columns Date and Close: per row it sets the
engine's time, releases delayed orders (`process_delayed_orders`), gives the
row to the market maker (which quotes liquidity around the price) and to
each trader (`on_market_data(data)` then `trade()`). Traders are
`strategies.base.AlgorithmicTrader` subclasses; orders go to
`MatchingEngine.submit_order(Order(...))`, cancels to `cancel_order(id)`, fills
come back through `MatchingEngine.subscribe_trades(callback)` (Execution).
Engine settings used by the scenes: `latency_ms` (int milliseconds),
`slippage_bps_per_100_shares`, `taker_fee_bps`. The market data a row carries
is `{"symbol", "price", "timestamp"}`: a price, not a typed event.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from trading_simulator.backtest.runner import run_backtest  # noqa: E402
from trading_simulator.core.matching_engine import MatchingEngine  # noqa: E402
from trading_simulator.core.order import Order  # noqa: E402
from trading_simulator.core.order_book import OrderBook  # noqa: E402
from trading_simulator.marketmaker.market_maker import MarketMaker  # noqa: E402
from trading_simulator.strategies.base import AlgorithmicTrader  # noqa: E402

logging.disable(logging.CRITICAL)
SYM = "X"


def _df(events: list[dict]) -> pd.DataFrame:
    rows = [C.as_bar(e) for e in events]
    return pd.DataFrame({"Date": pd.to_datetime([int(r["ts_ns"]) for r in rows], unit="ns", utc=True),
                         "Close": [float(r["close"]) for r in rows]})


def run(events: list[dict], fn, setup=None, df=None):
    # round r8-1 (positive definition A (1)): the settings through common.configure
    me = C.configure(MatchingEngine, OrderBook(), what="MatchingEngine(OrderBook())", decided_from=("公開の既定",))
    if setup:
        setup(me)
    mm = C.configure(MarketMaker, SYM, me, what="MarketMaker(銘柄, engine)", decided_from=("選ぶ値",))
    st = {"n": 0, "log": [], "fills": [], "oid": 0}
    me.subscribe_trades(lambda ex: st["fills"].append(ex) if ex.taker_owner_id == "strategy" else None)

    class T(AlgorithmicTrader):
        def on_market_data(self, data):
            super().on_market_data(data)
            st["n"] += 1
            fn(self, data, st)

    C.configure(run_backtest, _df(events) if df is None else df, mm, me, traders=[T(SYM, me)],
                what="run_backtest(場面の事象の表(Date, Close), market_maker, engine, traders=[場面の戦略])", decided_from=("場面の入力",))
    return st, me


def order(st, side: str, qty: int, typ: str = "market", price: float = 0.0) -> Order:
    st["oid"] += 1
    return Order(id=f"s{st['oid']}", price=price, quantity=qty, side=side, type=typ, symbol=SYM, owner_id="strategy")


def _ts(data) -> int:
    return int(pd.Timestamp(data["timestamp"]).value)


NON = "この道具の入力は Date と Close の列の表で、行ごとに戦略に渡るのは {{symbol, price, timestamp}} だけ。{k} を渡す口が無い。試したこと: {err}"


def _attempt_df(cols: dict) -> str:
    df = pd.DataFrame({"Date": pd.to_datetime([1_700_092_800_000_000_000], unit="ns", utc=True), **{k: [v] for k, v in cols.items()}})
    try:
        run([], lambda s, d, st: None, df=df)
    except Exception as exc:  # noqa: BLE001
        return f"run_backtest(<列 {list(df.columns)} の表>, ...) -> {type(exc).__name__}: {str(exc)[:140]}"
    return f"run_backtest(<列 {list(df.columns)} の表>, ...) は例外なく終わった"


def _attempt_call(fn_desc: str, fn) -> str:
    try:
        r = fn()
    except Exception as exc:  # noqa: BLE001
        return f"{fn_desc} -> {type(exc).__name__}: {str(exc)[:140]}"
    return f"{fn_desc} -> {r!r}"[:200]


class PredictivedevTradesimAdapter(Adapter):
    name = "opp_predictivedev_tradesim"
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"market_maker": "MarketMaker(銘柄)", "latency_ms": "既定(場面が遅れを名指さないとき)"}}

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda s, d, st: (st["log"].append(["price", _ts(d)]), car.append(C.carrier(d))))
        return ok({"sequence": st["log"]}, "足の終値を Close にした表を run_backtest に渡し、on_market_data の各回に (道具の型 = 値の行 price、data['timestamp'])。"
                  "戦略に渡る data は {symbol, price, timestamp} で、足の型ではない", {"carriers": car})

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON.format(k="約定・資金調達を別の入力として", err=_attempt_df({"rate": 0.0001})))

    def scene_p1_typed_events(self, sc):
        return not_supported(NON.format(k="型の違う事象", err=_attempt_df({"price": 101.0, "qty": 0.01})))

    # ---------------- P0-2
    def _iso(self, sc):
        df = pd.DataFrame({"Date": [sc.input["iso"]], "Close": [100.0]})
        st, _ = run([], lambda s, d, st: st["log"].append(_ts(d)), df=df)
        return ok(st["log"][0] if st["log"] else None, "Date に ISO の文字列を入れて run_backtest に渡した(道具が pd.to_datetime(utc=True) で読む)。"
                  "戦略に届いた data['timestamp'] の ns", {"reader": C.qualname(run_backtest)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _obs(self, sc):
        rows = [C.substitute(e, "bar", open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
                for e in C.events(sc)]
        car = []
        st, _ = run(rows, lambda s, d, st: (st["log"].append(_ts(d)), car.append(C.carrier(d))))
        return ok({"observed_ts_ns": st["log"]}, "足(終値 100)で渡し、on_market_data の data['timestamp'] を ns に", {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON.format(k=e["kind"], err=_attempt_df({k: v for k, v in C.fields_of(e).items() if not isinstance(v, list)})))
        out = {}
        car = []

        def f(s, d, st):
            st["log"].append(["price", _ts(d)])
            car.append(C.carrier(d))
            out.update({k: d.get(k) for k in ("open", "high", "low", "close", "volume")})
            out["price"] = d.get("price")

        st, _ = run([e], f)
        return ok({"sequence": st["log"], "fields": {k: out.get(k) for k in ("open", "high", "low", "close", "volume")}},
                  f"足 1 本(Close = 終値)を渡した。戦略に届いた data: price={out.get('price')}(始値・高値・安値・出来高の欄は無い)",
                  {"carriers": car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON.format(k="足以外の型", err=_attempt_df({"price": 101.0, "qty": 0.01})))

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略を頼んだ時刻に呼ぶ口が無い(呼ばれるのは表の行ごと)。試したこと: "
                             + _attempt_call("MatchingEngine.set_timer(4 日後)", lambda: MatchingEngine(OrderBook()).set_timer(sc.input["timer_at_ns"])))

    def scene_p3_notice_accepted(self, sc):
        return not_supported("注文の受付を戦略に知らせる口が無い(subscribe_trades が渡すのは約定 Execution だけ)。試したこと: "
                             + _attempt_call("MatchingEngine.subscribe_orders(cb)", lambda: MatchingEngine(OrderBook()).subscribe_orders(print)))

    def scene_p3_notice_rejected(self, sc):
        notices = []

        def f(s, d, st):
            if st["n"] == 1:
                s.matching_engine.submit_order(order(st, "buy", 10_000_000))  # above the engine's own safety limit
                notices.extend("filled" for _ in st["fills"])

        st, _ = run([C.as_bar(e) for e in C.events(sc)], f)
        return ok({"notices": notices}, "1 回目に数量 10,000,000 の成行を submit_order(道具は数量 1,000,000 超を log の警告だけで捨て、戻り値も通知も無い)。"
                  f"戦略に届いた約定 {len(st['fills'])} 件")

    def scene_p3_notice_filled(self, sc):
        def f(s, d, st):
            if st["n"] == 1:
                s.matching_engine.submit_order(order(st, "buy", 1))

        st, _ = run([C.as_bar(e) for e in C.events(sc)], f)
        return ok({"filled_qty_in_notices": float(sum(ex.quantity for ex in st["fills"]))},
                  f"1 回目に成行 買い 1、subscribe_trades で受けた当方の Execution の数量の合計。{[(ex.price, ex.quantity) for ex in st['fills']]}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        return not_supported("戦略が過去の事象を読む口が無い(on_market_data は今の行の price と timestamp だけを渡す)。試したこと: "
                             + _attempt_call("AlgorithmicTrader.history()", lambda: AlgorithmicTrader(SYM, None).history()))

    def scene_p4_received_time(self, sc):
        return not_supported(NON.format(k="受け取れる時刻", err=_attempt_df({"Close": 101.0, "recv_ns": 1})))

    def scene_p4_future_read_attempt(self, sc):
        probe, fut = sc.input["probe_at_ns"], pd.Timestamp(sc.input["future_ts_ns"], unit="ns", tz="UTC")
        att = C.Attempts()

        def f(s, d, st):
            if _ts(d) != probe or att.items:
                return
            # The trader's public reads: current_price, and through its engine get_last_trade_price(symbol),
            # order_book.get_best_bid/ask, depth_snapshot; none takes a time or a position. The calls a
            # strategy would write to reach the 5th bar are made as written:
            att.run("data['history'][4](次の位置)", "position", lambda: d["history"][4], shape="no_means", naming="written_call",
                    via=d)
            att.run("matching_engine.get_last_trade_price(symbol, 5 本目の時刻)", "time",
                    lambda: s.matching_engine.get_last_trade_price(SYM, fut), shape="no_means", naming="written_call",
                    via=s.matching_engine.get_last_trade_price)
            att.run("self.current_price", "other", lambda: s.current_price)

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の on_market_data で試した: " + att.summary())

    # ---------------- P0-5
    def _no_types(self, sc):
        return not_supported(NON.format(k="型ごとの入力", err=_attempt_df({"rate": 0.0001})))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        car = []
        st, _ = run(C.events(sc), lambda s, d, st: (st["log"].append(float(d["price"])), car.append(C.carrier(d))))
        return ok({"prices": st["log"]}, "同じ時刻の 3 行(Close = 価格)を 1 つの表で渡した", {"carriers": car})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def f(s, d, st):
            ob = s.matching_engine.order_book
            if st["n"] == 1:
                st["lim"] = order(st, "buy", 1, "limit", 90.0)
                s.matching_engine.submit_order(st["lim"])
            elif st["n"] == 2:
                out["open_at_call2"] = int(st["lim"].id in ob.order_map)
                s.matching_engine.cancel_order(st["lim"].id)
            elif st["n"] == 3:
                out["open_at_call3"] = int(st["lim"].id in ob.order_map)

        run([C.as_bar(e) for e in C.events(sc)], f)
        return ok(out, "1 回目 submit_order(指値 買い 1 @90)、2 回目 order_book.order_map に当方の注文があるか(未決の数を読む口は無く、"
                  "板の注文の辞書を当方の id で引いた)と cancel_order(id)、3 回目 同じく")

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消を戦略に知らせる口が無い(cancel_order の戻り値は None、subscribe_trades は約定だけ)。試したこと: "
                             + _attempt_call("MatchingEngine.cancel_order('s1')", lambda: MatchingEngine(OrderBook()).cancel_order("s1")))

    def scene_p6_fill_seen_by_strategy(self, sc):
        from trading_simulator.portfolio.portfolio import Portfolio
        out = {}
        pf = Portfolio(initial_cash=1_000_000.0, owner_id="strategy")  # the tool's own account, wired as its CLI does

        def f(s, d, st):
            if st["n"] == 1:
                s.matching_engine.submit_order(order(st, "buy", 1))
            elif st["n"] == 3:
                out["filled_qty_at_call3"] = float(pf.positions.get(SYM, 0))

        run([C.as_bar(e) for e in C.events(sc)], f, setup=lambda me: C.configure(me.subscribe_trades, pf.on_execution, what="engine.subscribe_trades(場面の口座)"))
        return ok(out, "1 回目 成行 買い 1。3 回目に道具の Portfolio(owner_id='strategy'、道具の CLI と同じく engine.subscribe_trades(portfolio.on_execution) で"
                  "つないだ)の positions[銘柄](注文から約定済み数量を読む口は無い)")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を渡す口が無い(照合は板、埋まる値は置かれた注文の値 + slippage_bps_per_100_shares の式)。試したこと: "
                             + _attempt_call("MatchingEngine(OrderBook(), fill_model=...)", lambda: MatchingEngine(OrderBook(), fill_model=object())))

    def scene_p7_latency_model_swap(self, sc):
        out = {}

        def f(s, d, st):
            if st["n"] == 1:
                s.matching_engine.submit_order(order(st, "buy", 1))
            if st["fills"] and "fill_time_ns" not in out:
                out["fill_time_ns"] = int(pd.Timestamp(st["fills"][0].timestamp).value)
                out["row_time_when_filled_ns"] = _ts(d)

        run(C.events(sc), f, setup=lambda me: C.configure_attr(me, "latency_ms", 7, what="MatchingEngine.latency_ms = 7(場面の遅れ)",
                                                                decided_from=("場面の入力",)))
        return ok({"fill_time_ns": out.get("fill_time_ns")},
                  "MatchingEngine.latency_ms = 7(道具の遅延の設定)、1 回目(T0)に成行 買い 1。Execution.timestamp を約定の時刻として読んだ"
                  f"(道具は pd.Timestamp.now(tz='UTC') を入れる)。約定が見えた行の時刻 {out.get('row_time_when_filled_ns')}")

    def _fee(self, sc, what):
        return not_supported(f"{what}。費用の設定は MatchingEngine.taker_fee_bps / maker_rebate_bps と Portfolio(fee_bps=) の率(約定代金の bp)で、"
                             "約定 1 件の定額や数量あたりの額を渡す模型の口が無い。試したこと: "
                             + _attempt_call("MatchingEngine(OrderBook(), cost_model=...)", lambda: MatchingEngine(OrderBook(), cost_model=object())))

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, "約定 1 件 0.5 円の模型を差し込めない")

    def scene_p7_cost_per_unit(self, sc):
        return self._fee(sc, "数量 1 単位 0.375 円の模型を差し込めない")

    def scene_p7_account_swap(self, sc):
        recorded = []

        class RecordingAccount:
            def on_execution(self, ex):  # the shape the tool's own Portfolio has (portfolio.py on_execution)
                if ex.taker_owner_id == "strategy":
                    recorded.append(float(ex.quantity))

        def f(s, d, st):
            if st["n"] == 1:
                s.matching_engine.submit_order(order(st, "buy", 1))

        run([C.as_bar(e) for e in C.events(sc)], f, setup=lambda me: C.configure(me.subscribe_trades, RecordingAccount().on_execution, what="engine.subscribe_trades(場面の口座)"))
        return ok({"account_recorded_fill_qty": recorded},
                  "道具の CLI が Portfolio をつなぐのと同じ形(engine.subscribe_trades(portfolio.on_execution)、cli/main.py)で、記録するだけの口座をつないだ")
