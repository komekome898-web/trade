"""Survey candidate 33 `SarthakDalmia1/backtesting_execution_simulator`
(C++, commit a0a5fcd2; not on PyPI), built here with its own CMake (library
`backtesting_engine`; install record `survey_results/attempts/33.log`) and
driven through a small C++ driver against its public C++ API
(`ExecutionSimulator(BacktestConfig)`, `set_event_callback`,
`set_slippage_model`, `set_cost_model`, `add_tick`, `submit_order`, `run`,
`matching_engine()`, `event_queue()`, `get_last_tick`). The driver
(`c33_driver`, source in the install record) sits in the venv `c33`'s `bin/`.
Until round r5-1 this candidate was reproduced in Python from its primary
source; now that it builds here, the tool itself is run and the
reproduction is retired (ROOTCAUSE_r5-1.md).

What the tool is: an event queue ordered by timestamp (`EventComparator`,
events/event.hpp) of MarketData (a Tick: bid / ask / last price and size),
OrderSubmit, OrderCancel, OrderFill, OrderReject, Trade, ... events; one
callback receives every processed event; orders are submitted with a
latency (`LatencyConfig`); fills go through the plugged slippage model and
cost model. Market data does not enter the matching engine, so -- as the
tool's own demo does -- one resting sell order at the first trade's price and
size is placed in the matching engine before the run. Tool defaults are kept
(LatencyConfig: submit 1000 ns, market data 500 ns, fill report 500 ns)
unless a scene states otherwise; where a scene measures time itself the
detail gives the run with the market-data latency the scene implies (0) and
the default run.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "c33_driver")


def drv(*args) -> list[list[str]]:
    r = subprocess.run([EXE, *map(str, args)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"c33_driver {args[:2]} rc={r.returncode} {r.stderr[:200]}")
    return [ln.split() for ln in r.stdout.splitlines() if ln.strip()]


def ticks(events: list[dict]) -> list[str]:
    out = []
    for e in events:
        b = C.as_bar(e)
        out.append(f"{int(b['ts_ns'])}:{float(b.get('close', 100.0))}:{float(e.get('qty', b.get('volume', 1.0)) or 1.0)}")
    return out


# what the driver's callback receives for market data: the tool's own event (events/event.hpp MarketData holding a Tick)
MD_CARRIER = "cpp:execution_simulator MarketData(Tick)(callback の引数)"
NO_TYPES = ("この道具の市場の事象は MarketData の Tick(買い気配・売り気配・最後の約定の値と数量)の 1 種だけで、{k} を別の型として渡す口が無い"
            "(events/event.hpp の Event は MarketData / OrderSubmit / OrderCancel / OrderFill / OrderReject / Trade / PositionUpdate / Session / EndOfDay)")


class SarthakExecsimAdapter(Adapter):
    name = "opp_sarthak_execsim"

    def _md(self, events):
        default = drv("md", *ticks(events))
        zero = drv("md0", *ticks(events))
        return zero, default

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        zero, default = self._md(C.events(sc))
        md = [r for r in zero if r[0] == "MD"]
        return ok({"sequence": [["tick", int(r[1])] for r in md]},
                  "足の型が無いので足を Tick(値 = 終値)にして add_tick、callback が受けた (道具の型 = MarketData の Tick、時刻)。LatencyConfig.market_data_latency_ns = 0 の走り。"
                  f"既定(500 ns)の走りの時刻: {[int(r[1]) for r in default if r[0] == 'MD']}", {"carriers": [MD_CARRIER] * len(md)})

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NO_TYPES.format(k="資金調達や約定と足"))

    def scene_p1_typed_events(self, sc):
        return not_supported(NO_TYPES.format(k="約定と足"))

    # ---------------- P0-2
    def _iso(self, sc):
        return not_supported("日時の文字列を読む口が無い(時刻は int64 のナノ秒 Timestamp。文字列を読むのは tick_reader の CSV で、"
                             "Python に出ている to_timestamp(year, month, day, hour, minute, second, nano) は数を受ける)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _obs(self, sc):
        zero, default = self._md([{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0,
                                   "volume": 1.0} for e in C.events(sc)])
        md = [r for r in zero if r[0] == "MD"]
        return ok({"observed_ts_ns": [int(r[1]) for r in md]},
                  "Tick の timestamp(int64 ns)で渡し、callback の MarketData の時刻。market_data_latency_ns = 0 の走り。"
                  f"既定(500 ns を足して Tick の時刻を書き換える、execution_simulator.cpp add_tick)の走り: {[int(r[1]) for r in default if r[0] == 'MD']}",
                  {"carriers": [MD_CARRIER] * len(md)})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        return not_supported(NO_TYPES.format(k=C.events(sc)[0]["kind"] + " の型"))

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = scene_p3_mixed_one_run = _type

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略が時刻を頼んで起こされる口が無い(事象の列に積めるのは add_tick・submit_order・cancel_order の事象だけ。"
                             "SessionStart / EndOfDay の事象型はあるが積む公開の口が無い)")

    def _orders(self, sc, kind, qty, capital, plug="none"):
        return drv("orders", kind, qty, capital, plug, *ticks(C.events(sc)))

    def scene_p3_notice_accepted(self, sc):
        out = self._orders(sc, "limit90", 1, 1_000_000)
        return ok({"notices": [r[1] for r in out if r[0] == "NOTICE"]}, f"1 回目に指値 買い 1 @90 を submit_order。callback が受けた事象: {out}")

    def scene_p3_notice_rejected(self, sc):
        out = self._orders(sc, "market", 1, 1000)
        notices = [r[1] for r in out if r[0] == "NOTICE"] + (["filled"] if any(r[0] == "FILL" for r in out) else [])
        return ok({"notices": notices}, f"BacktestConfig.initial_capital = 1000、1 回目に成行 買い 1。callback が受けた事象: {out}")

    def scene_p3_notice_filled(self, sc):
        out = self._orders(sc, "market", 1, 1_000_000)
        return ok({"filled_qty_in_notices": sum(float(r[3]) for r in out if r[0] == "FILL")}, f"1 回目に成行 買い 1。OrderFill の数量の合計。{out}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        return not_supported("戦略(callback)が過去の事象を読む口が無い(get_last_tick は銘柄の最後の Tick 1 本、event_queue は先の事象)。"
                             "過去の件数と最大の終値を読めない")

    def scene_p4_received_time(self, sc):
        return not_supported("事象ごとの受け取れる時刻を持つ口が無い(Tick の時刻は 1 つで、配信の遅れは LatencyConfig の全体で 1 つの定数)")

    def scene_p4_future_read_attempt(self, sc):
        out = drv("future", sc.input["probe_at_ns"], *ticks(C.events(sc)))
        att = C.Attempts()
        peek = next((r for r in out if r[0] == "PEEK"), None)
        last = next((r for r in out if r[0] == "LAST"), None)
        att.run("simulator.event_queue().peek()(次の事象)", "position",
                lambda: None if peek is None or peek[1] == "none" else {"timestamp": int(peek[1]), "close": float(peek[2])},
                shape="next_call", naming="next")
        att.run("simulator.get_last_tick('X')(最新の 1 本)", "other",
                lambda: None if last is None or last[1] == "none" else {"timestamp": int(last[1]), "close": float(last[2])})
        return ok(att.output(), f"T0 + 4 日の MarketData の callback の中で試した(driver の出力 {out}): " + att.summary())

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        return not_supported(NO_TYPES.format(k="約定・足・資金調達・清算"))

    scene_p5_hand_over_order = scene_p5_same_time_twice

    def scene_p5_same_stream_order(self, sc):
        zero, default = self._md(C.events(sc))
        md = [r for r in zero if r[0] == "MD"]
        return ok({"prices": [float(r[2]) for r in md]},
                  f"同じ時刻の 3 本を add_tick、callback の MarketData の値の順。既定の走り: {[float(r[2]) for r in default if r[0] == 'MD']}",
                  {"carriers": [MD_CARRIER] * len(md)})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = self._orders(sc, "limit90", 1, 1_000_000)
        return not_supported("取消には注文の id が要る(cancel_order(order_id))が、submit_order は nullptr を返し(execution_simulator.cpp submit_order)、"
                             f"OrderSubmit の事象も注文の依頼だけで id を持たないので、戦略が出した注文を取り消せない。試したこと: 指値 買い 1 @90 -> {out}")

    def scene_p6_cancel_notice(self, sc):
        return self.scene_p6_place_then_cancel(sc)

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = self._orders(sc, "market", 1, 1_000_000)
        v = next((float(r[1]) for r in out if r[0] == "FILLED_AT_3"), None)
        return ok({"filled_qty_at_call3": v}, "1 回目に成行 買い 1、3 回目に matching_engine().find_order(OrderFill の order_id)->filled_quantity。"
                  f"driver の出力 {out}")

    # ---------------- P0-7
    def _fill(self, sc, plug, qty=1):
        return self._orders(sc, "market", qty, 100_000, plug)

    def scene_p7_fill_model_swap(self, sc):
        out = self._fill(sc, "fill12345")
        f = next((r for r in out if r[0] == "FILL"), None)
        return ok({"fill_price": float(f[2]) if f else None},
                  f"set_slippage_model(<SlippageModel の子: 12345.0 − 基準の値を返す>)、1 回目に成行 買い 1。OrderFill の値。{out}")

    def scene_p7_latency_model_swap(self, sc):
        out = self._fill(sc, "latency7ms")
        f = next((r for r in out if r[0] == "FILL"), None)
        return ok({"fill_time_ns": int(f[1]) if f else None},
                  f"LatencyConfig(order_submit 7 ms、market data / cancel / fill report 0)、T0 に成行 買い 1。OrderFill の時刻。{out}")

    def scene_p7_cost_model_swap(self, sc):
        out = self._fill(sc, "cost05")
        f = [r for r in out if r[0] == "FILL"]
        return ok({"fee": sum(float(r[4]) for r in f) if f else None},
                  f"set_cost_model(<TransactionCostModel の子: 1 件 0.5>)、成行 買い 1。OrderFill の transaction_cost の合計。{out}")

    def scene_p7_cost_per_unit(self, sc):
        out = self._fill(sc, "cost0375unit", 2)
        f = [r for r in out if r[0] == "FILL"]
        return ok({"fee": sum(float(r[4]) for r in f) if f else None},
                  f"set_cost_model(<TransactionCostModel の子: 0.375 × 数量>)、成行 買い 2。OrderFill の transaction_cost の合計。{out}")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(PositionManager / PnLTracker)は ExecutionSimulator が config から作り(execution_simulator.cpp の構築子)、"
                             "差し替える setter が無い(execution_simulator.hpp の set_ は set_slippage_model・set_cost_model・set_event_callback の 3 つ)")
