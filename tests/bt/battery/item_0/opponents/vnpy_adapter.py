"""Survey candidate 20 `VnPy` (PyPI `vnpy` 4.4.0 + `vnpy_ctastrategy` 1.4.1), run in its own venv.

vnpy's backtester is `vnpy_ctastrategy.backtesting.BacktestingEngine` (the
`vnpy` core package holds the trader objects; the CTA app holds the
backtester). Installed without the GUI dependencies (`pyside6`, `pyqtgraph`,
`qdarkstyle`): the full dependency set did not fit the free disk (the install
log has the measurement), and the backtester does not import the GUI.

Driven through its public API: `BacktestingEngine.set_parameters(...)`,
`add_strategy(CtaTemplate subclass, setting)`, `run_backtesting()`,
`calculate_result()`. The data is handed as the engine's `history_data` list
(what `load_data()` fills from vnpy's database; no database is installed),
`BarData` in bar mode or `TickData` in tick mode. The strategy callbacks are
`on_bar` / `on_tick` / `on_order` / `on_trade`; orders are
`buy(price, volume)` / `cancel_order(vt_orderid)`.

vnpy uses the datetime the data carries as the time of the call (the engine
has no clock of its own), so each event's `ts_ns` is the `datetime` of the bar
or tick handed in.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

NET_ATTEMPTS: list = []


def _guard(self, addr, *a, **k):
    NET_ATTEMPTS.append(str(addr))
    raise OSError(f"network blocked by the adapter guard: {addr}")


socket.socket.connect = _guard

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import datetime as D  # noqa: E402
import logging  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

logging.disable(logging.CRITICAL)

from vnpy.trader.constant import Exchange, Interval, Status  # noqa: E402
from vnpy.trader.object import BarData, TickData  # noqa: E402
from vnpy_ctastrategy import CtaTemplate  # noqa: E402
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode  # noqa: E402

UTC = D.timezone.utc


def _dt(ns: int) -> D.datetime:
    return C.ns_to_dt(int(ns))


def _ns(d: D.datetime) -> int:
    return C.dt_to_ns(d.astimezone(UTC))


def _bar(e: dict) -> BarData:
    b = C.as_bar(e)
    return BarData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(b["ts_ns"]), interval=Interval.DAILY,
                   volume=float(b.get("volume", 1.0)), open_price=float(b["open"]), high_price=float(b["high"]),
                   low_price=float(b["low"]), close_price=float(b["close"]), gateway_name="BACKTESTING")


class _Strat(CtaTemplate):
    hooks: dict = {}

    def on_init(self):
        return None

    def on_bar(self, bar):
        self.n = getattr(self, "n", 0) + 1
        f = self.hooks.get("bar")
        if f:
            f(self, bar, self.n)

    def on_tick(self, tick):
        self.n = getattr(self, "n", 0) + 1
        f = self.hooks.get("tick")
        if f:
            f(self, tick, self.n)

    def on_order(self, order):
        f = self.hooks.get("order")
        if f:
            f(self, order)

    def on_trade(self, trade):
        f = self.hooks.get("trade")
        if f:
            f(self, trade)


def run(data, hooks: dict, mode=BacktestingMode.BAR, capital=1_000_000, rate=0.0, engine_cls=BacktestingEngine, slippage=0.0):
    eng = engine_cls()
    eng.output = lambda msg: None
    start, end = data[0].datetime, data[-1].datetime
    eng.set_parameters(vt_symbol="X.LOCAL", interval=Interval.DAILY, start=start, end=end, rate=rate, slippage=slippage,
                       size=1, pricetick=0.01, capital=capital, mode=mode)

    class S(_Strat):
        pass

    S.hooks = hooks
    eng.add_strategy(S, {})
    eng.history_data = list(data)
    eng.run_backtesting()
    return eng


def _net() -> str:
    return f"接続の試み {len(NET_ATTEMPTS)} 件(adapter の socket の関門で数えた)"


def _kw(kw: str) -> str:
    try:
        BacktestingEngine().set_parameters(vt_symbol="X.LOCAL", interval=Interval.DAILY, start=_dt(0), rate=0.0, slippage=0.0,
                                           size=1, pricetick=0.01, **{kw: object()})
    except TypeError as exc:
        return f"BacktestingEngine.set_parameters(..., {kw}=...) -> TypeError: {str(exc)[:120]}"
    return f"BacktestingEngine.set_parameters(..., {kw}=...) は受け付けられた"


NON = ("vnpy の回は足の回(BarData)か tick の回(TickData: 最終約定と 5 段の板の写真を 1 つに持つ)のどちらか 1 つで、"
       "{k} を型として戦略に渡す口が無い(戦略の呼び口は on_bar / on_tick / on_order / on_trade / on_stop_order)。{t}")


class VnpyAdapter(Adapter):
    name = "opp_vnpy"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON.format(k="足と約定と資金調達を 1 つの回で", t="試したこと: 足と tick を 1 つの history_data に並べて足の回で走らせた -> "
                                         + self._mixed_try(sc)) + "。" + _net())

    def _mixed_try(self, sc):
        tr = sc.input["streams"]["trades"][0]
        data = [_bar(sc.input["streams"]["bars"][0]),
                TickData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(tr["ts_ns"]), last_price=tr["price"],
                         last_volume=tr["qty"], gateway_name="BACKTESTING")]
        got = []
        try:
            run(data, {"bar": lambda s, b, n: got.append(("bar", _ns(b.datetime))),
                       "tick": lambda s, t, n: got.append(("tick", _ns(t.datetime)))})
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {str(exc)[:120]}"
        return f"戦略が受けたもの {got}"

    def _seq(self, bars):
        log = []
        run([_bar(e) for e in bars], {"bar": lambda s, b, n: log.append(["bar", _ns(b.datetime)])})
        return log

    def scene_p1_one_call_per_event(self, sc):
        return ok({"sequence": self._seq(C.events(sc))}, "足の回。on_bar の各回に bar.datetime を記録。" + _net())

    def scene_p1_typed_events(self, sc):
        evs = C.events(sc)
        return not_supported(NON.format(k="足と約定を 1 つの回で", t="試したこと: 足と tick を 1 つの history_data にして足の回 -> "
                                         + self._typed_try(evs)) + "。" + _net())

    def _typed_try(self, evs):
        data = [_bar(evs[0]), TickData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(evs[1]["ts_ns"]),
                                       last_price=evs[1]["price"], last_volume=evs[1]["qty"], gateway_name="BACKTESTING")]
        got = []
        try:
            run(data, {"bar": lambda s, b, n: got.append(("bar", type(b).__name__)), "tick": lambda s, t, n: got.append(("tick", type(t).__name__))})
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {str(exc)[:120]}"
        return f"on_bar / on_tick が受けたもの {got}"

    # ---------------- P0-2
    def _iso(self, sc):
        import re
        m = re.fullmatch(r"(.*\.\d{6})\d*(.*)", sc.input["iso"])
        v = D.datetime.fromisoformat(m.group(1) + m.group(2).replace("Z", "+00:00"))
        return ok(_ns(v), "vnpy の時刻は datetime(マイクロ秒まで)。datetime.fromisoformat は小数 6 桁までなので、"
                  "ISO の小数 9 桁の下 3 桁を落として読んだ(vnpy の型が持てない部分)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        return ok({"observed_ts_ns": [t for _, t in self._seq(evs)]},
                  "足の datetime に事象の時刻を入れ、on_bar の bar.datetime を読んだ(datetime はマイクロ秒までで、下 3 桁は落ちる)。" + _net())

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def scene_p3_bar(self, sc):
        e = C.events(sc)[0]
        out, log = {}, []

        def h(s, b, n):
            log.append(["bar", _ns(b.datetime)])
            out.update({"open": b.open_price, "high": b.high_price, "low": b.low_price, "close": b.close_price, "volume": b.volume})

        run([_bar(e)], {"bar": h})
        return ok({"sequence": log, "fields": out}, "足の回。on_bar の BarData。" + _net())

    def scene_p3_trade(self, sc):
        e = C.events(sc)[0]
        out, log = {}, []

        def h(s, t, n):
            log.append(["trade", _ns(t.datetime)])
            out.update({"price": t.last_price, "qty": t.last_volume})

        tick = TickData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(e["ts_ns"]), last_price=e["price"],
                        last_volume=e["qty"], gateway_name="BACKTESTING")
        run([tick], {"tick": h}, mode=BacktestingMode.TICK)
        return ok({"sequence": log, "fields": out}, "tick の回。TickData の last_price / last_volume に約定を入れ、on_tick で読んだ。"
                  "TickData に約定の売り買いの向きの欄が無い。" + _net())

    def scene_p3_book_snapshot(self, sc):
        e = C.events(sc)[0]
        kw = {}
        for i, (p, q) in enumerate(e["bids"][:5], 1):
            kw[f"bid_price_{i}"], kw[f"bid_volume_{i}"] = p, q
        for i, (p, q) in enumerate(e["asks"][:5], 1):
            kw[f"ask_price_{i}"], kw[f"ask_volume_{i}"] = p, q
        out, log = {}, []

        def h(s, t, n):
            log.append(["book_snapshot", _ns(t.datetime)])
            out["bids"] = [[getattr(t, f"bid_price_{i}"), getattr(t, f"bid_volume_{i}")] for i in range(1, 6) if getattr(t, f"bid_price_{i}")]
            out["asks"] = [[getattr(t, f"ask_price_{i}"), getattr(t, f"ask_volume_{i}")] for i in range(1, 6) if getattr(t, f"ask_price_{i}")]

        run([TickData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(e["ts_ns"]), gateway_name="BACKTESTING", **kw)],
            {"tick": h}, mode=BacktestingMode.TICK)
        return ok({"sequence": log, "fields": out}, "tick の回。TickData の 5 段の板(bid/ask_price_1..5 と volume)に板の写真を入れ、"
                  "on_tick で読んだ(値が 0 の段は空の段)。" + _net())

    def _none(self, sc):
        e = C.events(sc)[0]
        return not_supported(NON.format(k=e["kind"], t="TickData の欄 " + str([f for f in TickData.__dataclass_fields__][:12]) + "…")
                             + "。" + _net())

    scene_p3_book_delta = scene_p3_funding = scene_p3_liquidation = _none

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON.format(k="6 種を 1 つの回で", t="試したこと: " + self._typed_try(
            [C.events(sc)[3], C.events(sc)[0]])) + "。" + _net())

    def scene_p3_clock_timer(self, sc):
        tried = []

        def h(s, b, n):
            if n == 1:
                for label, fn in [("self.cta_engine.put_timer(...)", lambda: s.cta_engine.put_timer(sc.input["timer_at_ns"])),
                                  ("self.on_timer", lambda: s.on_timer)]:
                    try:
                        fn()
                        tried.append(f"{label} -> 通った")
                    except Exception as exc:  # noqa: BLE001
                        tried.append(f"{label} -> {type(exc).__name__}: {str(exc)[:80]}")

        run([_bar(e) for e in C.events(sc)], {"bar": h})
        return not_supported(f"時刻を指定して戦略を起こす口が無い。1 回目の on_bar の中で試した: {tried}。{_net()}")

    def _notices(self, sc, capital, price):
        notes, fills = [], []

        def h(s, b, n):
            if n == 1:
                s.buy(price, 1)

        def o(s, order):
            notes.append({Status.NOTTRADED: "accepted", Status.ALLTRADED: "filled", Status.CANCELLED: "canceled",
                          Status.REJECTED: "rejected"}.get(order.status, str(order.status)))

        eng = run([_bar(e) for e in C.events(sc)], {"bar": h, "order": o, "trade": lambda s, t: fills.append(t.volume)}, capital=capital)
        return notes, fills

    def scene_p3_notice_accepted(self, sc):
        notes, _ = self._notices(sc, 1_000_000, 90.0)
        return ok({"notices": notes}, "1 回目の on_bar で buy(90, 1)。on_order の order.status を記録" + _net())

    def scene_p3_notice_rejected(self, sc):
        px = C.as_bar(C.events(sc)[0])["close"]
        notes, fills = self._notices(sc, 1_000, px * 1.01)
        return ok({"notices": notes}, "現金 1,000(set_parameters の capital)、1 回目の on_bar で成行に当たる buy(終値の 1.01 倍, 1)。"
                  f"on_order の order.status を記録。約定 {fills}。{_net()}")

    def scene_p3_notice_filled(self, sc):
        px = C.as_bar(C.events(sc)[0])["close"]
        notes, fills = self._notices(sc, 1_000_000, px * 1.01)
        return ok({"filled_qty_in_notices": float(sum(fills)), "notices": notes},
                  "vnpy に成行の型は無く、成行は相手の価格を越える指値で出す(buy(終値の 1.01 倍, 1))。on_trade の trade.volume を足した。" + _net())

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out, seen = {}, []

        def h(s, b, n):
            seen.append(b.close_price)
            if _ns(b.datetime) == probe:
                out.update({"visible_count": len(seen), "max_visible_close": max(seen)})

        run([_bar(e) for e in C.events(sc)], {"bar": h})
        if not out:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった。{_net()}")
        return ok(out, f"on_bar の各回の close を貯めた {seen}。{_net()}")

    def scene_p4_received_time(self, sc):
        return not_supported("BarData / TickData の時刻は datetime の 1 つで、受け取れる時刻を別に持たせる欄が無い。"
                             f"BarData の欄 {list(BarData.__dataclass_fields__)}。{_net()}")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def h(s, b, n):
            if _ns(b.datetime) != probe or att.items:
                return
            hist = s.cta_engine.history_data
            att.run("self.cta_engine.history_data[今の足の添字 + 1](最新の次の位置)", "position",
                    lambda: hist[[_ns(x.datetime) for x in hist].index(probe) + 1].close_price)
            att.run("self.cta_engine.history_data の close の全部", "other", lambda: [x.close_price for x in hist])
            att.run("self.load_bar(10)", "other", lambda: s.load_bar(10))

        run([_bar(e) for e in C.events(sc)], {"bar": h})
        if not att.items:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった。{_net()}")
        return ok(att.output(), "T0 + 4 日の on_bar の中で試した: " + att.summary() + "。" + _net())

    def _no_types(self, sc):
        return not_supported(NON.format(k="約定・足・資金調達・清算を 1 つの回で", t="試したこと: " + self._mixed_try(sc)) + "。" + _net())

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        seen = []
        run([_bar(e) for e in C.events(sc)], {"bar": lambda s, b, n: seen.append(b.close_price)})
        return ok({"prices": seen}, "同じ時刻の 3 本の足(終値 101・99・100)を history_data に並べた。on_bar の close。" + _net())

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def h(s, b, n):
            if n == 1:
                s.oid = s.buy(90.0, 1)[0]
            elif n == 2:
                out["open_at_call2"] = len(s.cta_engine.active_limit_orders)
                s.cancel_order(s.oid)
            elif n == 3:
                out["open_at_call3"] = len(s.cta_engine.active_limit_orders)

        run([_bar(e) for e in C.events(sc)], {"bar": h})
        return ok(out, "buy(90, 1) / cancel_order(vt_orderid)。未決の注文は cta_engine.active_limit_orders の数。" + _net())

    def scene_p6_cancel_notice(self, sc):
        notes = []

        def h(s, b, n):
            if n == 1:
                s.oid = s.buy(90.0, 1)[0]
            elif n == 2:
                s.cancel_order(s.oid)

        run([_bar(e) for e in C.events(sc)], {"bar": h, "order": lambda s, o: notes.append(str(o.status))})
        return ok({"cancel_notice_received": str(Status.CANCELLED) in notes, "notices": notes}, "on_order の order.status を記録。" + _net())

    def scene_p6_fill_seen_by_strategy(self, sc):
        out, px = {}, C.as_bar(C.events(sc)[0])["close"]

        def h(s, b, n):
            if n == 1:
                s.oid = s.buy(px * 1.01, 1)[0]
            elif n == 3:
                out["filled_qty_at_call3"] = float(s.pos)

        run([_bar(e) for e in C.events(sc)], {"bar": h})
        return ok(out, "1 回目に buy(終値の 1.01 倍, 1)(vnpy に成行の型は無い)。3 回目に strategy.pos を読んだ。" + _net())

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を差し込む口が無い(突き合わせは BacktestingEngine.cross_limit_order に固定。差し替えるには"
                             "核の関数を書き換えることになる)。試したこと: " + _kw("fill_model") + "。" + _net())

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("発注の遅延の模型を渡す口が無い(注文は次の足・tick で突き合わせる)。試したこと: " + _kw("latency_model") + "。" + _net())

    def _fee(self, sc, rate):
        px = C.as_bar(C.events(sc)[0])["close"]

        def h(s, b, n):
            if n == 1:
                s.buy(px * 1.01, 1)

        eng = run([_bar(e) for e in C.events(sc)], {"bar": h}, capital=100_000, rate=rate)
        df = eng.calculate_result()
        return float(df["commission"].sum()) if df is not None and len(df) and "commission" in df else None, eng

    def scene_p7_cost_model_swap(self, sc):
        fee, _ = self._fee(sc, 0.005)
        return not_supported("費用は set_parameters の rate(約定代金に掛ける率)と slippage(1 単位あたり)だけで、約定 1 件に決まった額を返す模型を"
                             f"差し込む口が無い。試したこと: {_kw('fee_model')}。rate=0.005 で走らせた手数料の合計 {fee}。{_net()}")

    def scene_p7_cost_per_unit(self, sc):
        px = C.as_bar(C.events(sc)[0])["close"]

        def h(s, b, n):
            if n == 1:
                s.buy(px * 1.01, 2)

        eng = run([_bar(e) for e in C.events(sc)], {"bar": h}, capital=100_000, rate=0.0, slippage=0.375)
        df = eng.calculate_result()
        if df is None or not len(df):
            return ok({"fee": None}, "約定が無かった。" + _net())
        fee = float(df["commission"].sum()) + float(df["slippage"].sum())
        return ok({"fee": fee}, "費用の口は set_parameters の rate(約定代金に掛ける率)と slippage(数量 1 単位あたりの額。日ごとの結果で費用として"
                  "差し引かれる)。rate=0、slippage=0.375 で数量 2 の買い。calculate_result() の commission と slippage の合計を費用とした。"
                  f"commission {df['commission'].tolist()} / slippage {df['slippage'].tolist()}。" + _net())

    def scene_p7_account_swap(self, sc):
        return not_supported("口座を差し込む口が無い(BacktestingEngine が capital と日ごとの損益を自分で持つ)。試したこと: " + _kw("account") + "。" + _net())
