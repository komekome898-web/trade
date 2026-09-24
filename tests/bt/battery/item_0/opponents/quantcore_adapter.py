"""Survey candidate 34 `SLMolenaar/QuantCore` (PyPI `quantcore` 1.0.0, C++20 core with a
Python interface), run in its own venv.

Driven through its public API: `BacktestEngine(capital, ExecutionConfig)`
(`maker_fee`, `taker_fee`, `latency_ns`, `slippage_pct`), `add_data` (bars:
`BarData(symbol, timestamp_ns, o, h, l, c, v)`) / `add_tick_data` (trades:
`TickData(symbol, timestamp_ns, price, quantity, aggressor_side)`),
`set_position_sizer(FixedShares(1))`, `set_strategy`, `run()`, and a
`Strategy` subclass (`on_data(MarketDataEvent)`, `on_fill(FillEvent)`,
`on_rejected`, `generate_signal(symbol, SignalType, strength, timestamp_ns)`).
The strategy emits signals; the engine turns them into orders sized by the
position sizer.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import quantcore as qc  # noqa: E402


def _cfg(latency_ns=0, fee=0.0):
    ec = qc.ExecutionConfig()
    ec.maker_fee = fee
    ec.taker_fee = fee
    ec.latency_ns = latency_ns
    ec.slippage_pct = 0.0
    return ec


def run(events: list[dict], fn, cash=1_000_000.0, latency_ns=0, fee=0.0, ticks=False):
    eng = qc.BacktestEngine(cash, _cfg(latency_ns, fee))
    if ticks:
        eng.add_tick_data("X", [qc.TickData("X", int(e["ts_ns"]), float(e["price"]), float(e.get("qty", 1.0)),
                                            qc.Side.BUY if e.get("side", "buy") == "buy" else qc.Side.SELL) for e in events])
    else:
        rows = [C.as_bar(e) for e in events]
        eng.add_data("X", [qc.BarData("X", int(b["ts_ns"]), float(b["open"]), float(b["high"]), float(b["low"]),
                                      float(b["close"]), float(b.get("volume", 1.0))) for b in rows])
    eng.set_position_sizer(qc.FixedShares(1))
    # The tool's own risk limits are left at their defaults (RiskLimits(): enabled=True, max_leverage=2.0,
    # max_loss_pct=0.5, max_order_value=0.0, max_position_pct=0.2 -- measured). Round r4-1: an earlier version
    # switched them off here for every scene (critic i0-r2-04 / i0-r3-05); a protective default of a survey
    # tool is not taken away (protocol.py, "Rules for adapter authors").
    st = {"n": 0, "log": [], "notices": [], "fills": []}

    class S(qc.Strategy):
        def __init__(self):
            super().__init__("s")

        def on_data(self, ev):
            st["n"] += 1
            fn(self, ev, st["n"], st)

        def on_fill(self, f):
            st["notices"].append("filled")
            st["fills"].append({"price": f.price, "qty": f.quantity, "commission": f.commission, "ts": f.timestamp_ns})

        def on_rejected(self, *a):
            st["notices"].append("rejected")

    s = S()
    eng.set_strategy(s)
    eng.run()
    return st, eng


def _buy(s, ev):
    s.generate_signal("X", qc.SignalType.BUY, 1.0, ev.timestamp_ns)


def _kinds_attempt(kind: str) -> str:
    names = [n for n in dir(qc) if kind.lower() in n.lower()]
    try:
        qc.BacktestEngine(1.0).add_event_data("X", [])  # type: ignore[attr-defined]
        r = "受け付けた"
    except Exception as exc:  # noqa: BLE001
        r = f"{type(exc).__name__}: {exc}"
    return f"quantcore の公開の名前で「{kind}」を含むもの: {names}。BacktestEngine().add_event_data(...) -> {r}"


NON = "QuantCore が受ける事象は足(BarData)と約定のティック(TickData)の 2 種だけで、{k} を入れる口が無い。試したこと: {err}"


class QuantcoreAdapter(Adapter):
    name = "opp_quantcore"

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON.format(k="資金調達", err=_kinds_attempt("funding"))
                             + "(足と約定は add_data と add_tick_data の別々の口で、同じ実行に混ぜる口も無い: engine.has_tick_data で片方の型に切り替わる)")

    def scene_p1_one_call_per_event(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: st["log"].append(["bar", int(ev.timestamp_ns)]))
        return ok({"sequence": st["log"]}, "足 5 本。on_data の各回に ev.timestamp_ns")

    def scene_p1_typed_events(self, sc):
        evs = C.events(sc)
        eng = qc.BacktestEngine(1.0, _cfg())
        eng.add_data("X", [qc.BarData("X", int(evs[0]["ts_ns"]), 1.0, 1.0, 1.0, 1.0, 1.0)])
        eng.add_tick_data("X", [qc.TickData("X", int(evs[1]["ts_ns"]), 100.5, 0.01, qc.Side.BUY)])
        seen = []

        class S(qc.Strategy):
            def on_data(self, ev):
                seen.append([type(ev).__name__, int(ev.timestamp_ns)])

        eng.set_strategy(S("s"))
        eng.run()
        return ok({"sequence": seen}, f"add_data(足) と add_tick_data(約定) を同じ BacktestEngine に入れて走らせた。on_data に届いた事象の型と時刻: {seen}"
                  "(戦略に届く型は MarketDataEvent の 1 種で、足と約定を見分ける欄は無い)")

    def _iso(self, sc):
        try:
            v = qc.TradingCalendar("NYSE").parse(sc.input["iso"])  # type: ignore[attr-defined]
            return ok(int(v), "TradingCalendar.parse")
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"QuantCore の時刻は int のナノ秒(timestamp_ns)で、文字列の時刻を変換する公開の関数が無い。"
                                 f"試したこと: TradingCalendar('NYSE').parse(iso) -> {type(exc).__name__}: {str(exc)[:120]}")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01} for e in C.events(sc)]
        st, _ = run(evs, lambda s, ev, n, st: st["log"].append(int(ev.timestamp_ns)), ticks=True)
        return ok({"observed_ts_ns": st["log"]}, "約定のティックで渡し、on_data の ev.timestamp_ns")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] == "bar":
            out = {}

            def f(s, ev, n, st):
                st["log"].append(["bar", int(ev.timestamp_ns)])
                out.update({"open": ev.open, "high": ev.high, "low": ev.low, "close": ev.close, "volume": ev.volume})

            st, _ = run([e], f)
            return ok({"sequence": st["log"], "fields": out}, "足 1 本(add_data)。on_data の MarketDataEvent")
        if e["kind"] == "trade":
            out = {}

            def f(s, ev, n, st):
                st["log"].append(["trade", int(ev.timestamp_ns)])
                out.update({"price": ev.close, "qty": ev.volume, "side": None})

            st, _ = run([e], f, ticks=True)
            return ok({"sequence": st["log"], "fields": out},
                      "約定 1 件(add_tick_data)。on_data に届くのは MarketDataEvent(open/high/low/close/volume)で、約定の向きの欄が無い")
        return not_supported(NON.format(k=e["kind"], err=_kinds_attempt(e["kind"].split("_")[-1])))

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NON.format(k="板・資金調達・清算", err=_kinds_attempt("book")))

    def scene_p3_clock_timer(self, sc):
        return not_supported("時刻を頼んで呼ばれる口が無い。試したこと: " + _kinds_attempt("timer"))

    def scene_p3_notice_accepted(self, sc):
        return not_supported("受付の知らせの呼び出しが無い(Strategy の呼び出しは on_data / on_fill / on_rejected)。試したこと: 指値の注文を出す口も無い("
                             + _kinds_attempt("limit") + ")")

    def scene_p3_notice_rejected(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: _buy(s, ev) if n == 1 else None, cash=1_000.0, ticks=True)
        return ok({"notices": st["notices"]}, f"現金 1,000、約定の価格 1,000,000。1 回目に BUY の信号(FixedShares(1))。on_fill/on_rejected の列。fills={st['fills']}")

    def scene_p3_notice_filled(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: _buy(s, ev) if n == 1 else None, ticks=True)
        return ok({"filled_qty_in_notices": float(sum(f["qty"] for f in st["fills"])), "notices": st["notices"]}, f"on_fill: {st['fills']}")

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out = {}
        seen = []

        def f(s, ev, n, st):
            seen.append(ev.close)
            if int(ev.timestamp_ns) == probe:
                out["visible_count"] = len(seen)
                out["max_visible_close"] = max(seen)

        run(C.events(sc), f)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(out, "戦略に履歴を渡す口が無いので、戦略が受け取った事象を戦略自身が貯めた")

    def scene_p4_received_time(self, sc):
        try:
            qc.TickData("X", 1, 1.0, 1.0, qc.Side.BUY, 3)  # type: ignore[call-arg]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {str(exc)[:160]}"
        return not_supported(f"事象は時刻を 1 つ(timestamp_ns)だけ持つ。試したこと: TickData(..., 受け取れる時刻) -> {r}")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        fut = int(sc.input["future_ts_ns"])
        att = C.Attempts()

        def f(s, ev, n, st):
            if int(ev.timestamp_ns) != probe or att.items:
                return
            # Strategy's public methods (dir(quantcore.Strategy)): generate_*, get_name, get_portfolio,
            # get_position, get_signals, has_position, has_signals, on_*, reset, set_position -- none reads
            # market data by time or position. The calls a strategy would write are made as written:
            att.run("self.get_position('X', 5 本目の時刻)", "time", lambda: s.get_position("X", fut))
            att.run("受け取った事象の [1](次の足)", "position", lambda: ev[1])
            att.run("self.get_signals()", "other", lambda: [str(x) for x in s.get_signals()])

        run(C.events(sc), f)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の on_data で試した: " + att.summary())

    def scene_p5_same_time_twice(self, sc):
        return not_supported(NON.format(k="資金調達・清算", err=_kinds_attempt("liquidation")))

    scene_p5_hand_over_order = scene_p5_same_time_twice

    def scene_p5_same_stream_order(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: st["log"].append(ev.close), ticks=True)
        return ok({"prices": st["log"]}, "同じ時刻の約定 3 件をティックで渡した")

    def scene_p6_place_then_cancel(self, sc):
        return not_supported("戦略が指値を出す・取り消す・未決の注文を読む口が無い(戦略は信号を出し、注文は engine が作る)。試したこと: " + _kinds_attempt("cancel"))

    def scene_p6_cancel_notice(self, sc):
        return self.scene_p6_place_then_cancel(sc)

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def f(s, ev, n, st):
            if n == 1:
                _buy(s, ev)
            elif n == 3:
                out["filled_qty_at_call3"] = float(s.get_position("X")) if hasattr(s, "get_position") else None

        run(C.events(sc), f, ticks=True)
        return ok(out, "3 回目に self.get_position('X')")

    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型を渡す口が無い(ExecutionConfig の slippage_pct などの値だけ)。試したこと: "
                             + _kinds_attempt("fill_model"))

    def scene_p7_latency_model_swap(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: _buy(s, ev) if n == 1 else None, latency_ns=7_000_000, ticks=True)
        return ok({"fill_time_ns": st["fills"][0]["ts"] if st["fills"] else None},
                  f"ExecutionConfig.latency_ns = 7,000,000。on_fill の timestamp_ns。fills={st['fills']}")

    def scene_p7_cost_model_swap(self, sc):
        return not_supported("費用は ExecutionConfig の maker_fee / taker_fee(率)だけで、1 件あたり定額の模型に差し替える口が無い。試したこと: "
                             + _kinds_attempt("commission"))

    def scene_p7_cost_per_unit(self, sc):
        st, _ = run(C.events(sc), lambda s, ev, n, st: _buy(s, ev) if n == 1 else None, fee=0.001, ticks=True)
        return not_supported("費用の口は ExecutionConfig の maker_fee / taker_fee(約定代金に掛ける率)だけで、数量 1 単位あたりの模型を書けない。"
                             f"試したこと: maker_fee = taker_fee = 0.001 で成行 -> on_fill の commission は約定代金 × 率。fills={st['fills']}")
    def scene_p7_account_swap(self, sc):
        return not_supported("口座は engine の中にあり、差し替える口が無い(get_portfolio_context は読むだけ)。試したこと: " + _kinds_attempt("account"))
