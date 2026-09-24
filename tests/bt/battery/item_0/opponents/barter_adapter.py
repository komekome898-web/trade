"""Survey candidate 61 `barter-rs` (GitHub `barter-rs/barter-rs`; Rust crates barter
0.14 / barter-data 0.13 / barter-execution 0.9), built here with cargo (install
record `survey_results/attempts/61.log`) and driven through a small Rust
program that is a member of the tool's own workspace (`battery61`, source in
the install record; binary `c61_driver` in the venv `c61`'s `bin/`). The
program uses the tool's public API: `backtest::backtest` with
`MarketDataInMemory` (the market events handed in the given order),
`EngineStateBuilder`, a user `InstrumentDataState` (the tool's plug that
receives every `MarketEvent` and `AccountEvent` for an instrument), a user
strategy (`AlgoStrategy::generate_algo_orders(&EngineState)`, called by the
engine after each event it processes), `DefaultRiskManager`, and the mock
execution (`ExecutionConfig::Mock`: `latency_ms`, `fees_percent`, balances).

What the tool is: an engine over one stream of `MarketEvent`s (time_exchange
and time_received, both `DateTime<Utc>` with nanoseconds; kind = `DataKind`:
Trade, OrderBookL1, OrderBook (snapshot / update), Candle, Liquidation) and
account events from the execution; the engine's clock follows each event's
time_exchange. There is no funding type and no timer.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

EXE = str(Path(sys.prefix) / "bin" / "c61_driver")
NO_TYPE = ("この道具の市場の事象の型は DataKind の Trade・OrderBookL1・OrderBook(Snapshot / Update)・Candle・Liquidation の 5 つで"
           "(barter-data/src/event.rs)、{k} を渡す型が無い")


ASYNC_NOTE = ("(模擬の取引所は別の非同期の仕事で、注文の応答と約定は AccountEvent として engine の入力に合流する。市場の事象の再生は壁時計で"
              "間を置かないので、この短い走りでは応答が engine の停止までに届かなかった。道具の記録(RUST_LOG=debug)で、注文を出したあと "
              "Engine shutting down まで AccountEvent の処理が無いことを見た。3000 件の約定で走らせても同じ)")


def drv(payload: dict) -> list[dict]:
    r = subprocess.run([EXE], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"c61_driver rc={r.returncode} {r.stderr[-300:]}")
    return [json.loads(ln) for ln in r.stdout.splitlines() if ln.startswith("{")]


def ev(e: dict) -> dict:
    out = {k: v for k, v in e.items() if k in ("kind", "ts_ns", "price", "qty", "side", "open", "high", "low", "close", "volume",
                                                  "bids", "asks")}
    if "recv_ns" in e:
        out["recv_ns"] = e["recv_ns"]
    return out


def calls(rows):
    return [r for r in rows if "call" in r]


def seq(rows):
    return [[r["event"]["kind"], r["event"]["ts"]] for r in calls(rows)]


class BarterAdapter(Adapter):
    name = "opp_barter"

    def _run(self, events, **cfg):
        return drv({"cfg": cfg, "events": [ev(e) for e in events]})

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        rows = self._run(C.events(sc))
        return ok({"sequence": seq(rows)}, "足を Candle の MarketEvent にして 1 本の流れで渡し、戦略の各回に InstrumentDataState が受けた (型, time_exchange)")

    def scene_p1_merge_by_time(self, sc):
        return not_supported(NO_TYPE.format(k="資金調達"))

    def scene_p1_typed_events(self, sc):
        rows = self._run(C.events(sc))
        return ok({"sequence": seq(rows)}, "足は Candle、約定は Trade(PublicTrade)の MarketEvent。戦略の各回に受けた (型, time_exchange)")

    # ---------------- P0-2
    def _iso(self, sc):
        line = json.dumps({"Item": {"time_exchange": sc.input["iso"], "time_received": sc.input["iso"], "exchange": "binance_spot",
                                    "instrument": 0, "kind": {"Trade": {"id": "1", "price": 100.0, "amount": 1.0, "side": "Buy"}}}})
        rows = drv({"parse": line})
        r = rows[0] if rows else {}
        return ok(r.get("parsed_ns"), "道具の市場の事象の記録(MarketStreamEvent の JSON。道具の例の資料と同じ形)の time_exchange に ISO の文字列を書き、"
                  f"道具の読み込み(serde + chrono の DateTime<Utc>)で読んだ時刻。{r}")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _obs(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01, "side": "buy"} for e in C.events(sc)]
        rows = self._run(evs)
        return ok({"observed_ts_ns": [r["event"]["ts"] for r in calls(rows)]}, "約定(Trade)の time_exchange(DateTime<Utc>、ナノ秒)で渡し、戦略の各回に受けた時刻")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] == "funding":
            return not_supported(NO_TYPE.format(k="資金調達"))
        rows = self._run([e])
        c = calls(rows)
        f = dict(c[0]["event"]["fields"]) if c else {}
        if e["kind"] == "bar":
            f = {k: f.get(k) for k in ("open", "high", "low", "close", "volume")}
        elif e["kind"] in ("trade", "liquidation"):
            f = {k: f.get(k) for k in ("price", "qty", "side")}
        elif e["kind"] == "book_snapshot":
            f = {s: [[float(p), float(q)] for p, q in f.get(s, [])] for s in ("bids", "asks")}
        elif e["kind"] == "book_delta":
            side = "bid" if f.get("bids") else "ask"
            p, q = (f.get("bids") or f.get("asks") or [[None, None]])[0]
            f = {"side": side, "price": float(p) if p is not None else None, "qty": float(q) if q is not None else None}
        return ok({"sequence": seq(rows), "fields": f},
                  "1 件を道具の型(Trade = PublicTrade / OrderBook::Snapshot / OrderBook::Update / Candle / Liquidation)の MarketEvent で渡し、"
                  f"戦略の回に InstrumentDataState が受けた型・時刻・欄(板の値と量は Decimal の文字列を数に)。道具の型名 {c[0]['event']['variant'] if c else None}")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return not_supported(NO_TYPE.format(k="資金調達") + "(この場面の 6 件は資金調達を含む)")

    def scene_p3_clock_timer(self, sc):
        return not_supported("戦略が時刻を頼んで起こされる口が無い(generate_algo_orders は engine が事象を 1 件処理するたびに呼ぶ。時計 HistoricalClock は"
                             "事象の time_exchange を追うだけで、頼んだ時刻の事象を作らない)")

    def _orders(self, sc, **cfg):
        return self._run(C.events(sc), **cfg)

    @staticmethod
    def _seen(rows):
        return [r["seen"] for r in rows if "seen" in r]

    @staticmethod
    def _trail(rows):
        return [r for r in rows if "call" not in r]

    def scene_p3_notice_accepted(self, sc):
        rows = self._orders(sc, buy_at=1, limit=True, price=90.0, qty=1.0)
        return ok({"notices": [s["notice"] for s in self._seen(rows)]},
                  "1 回目の generate_algo_orders で指値 買い 1 @90(OrderRequestOpen、OrderKind::Limit)。戦略は各回に InstrumentDataState が受けた "
                  f"AccountEvent を記録した。driver の出力(市場の事象の行を除く) {self._trail(rows)}" + ASYNC_NOTE)

    def scene_p3_notice_rejected(self, sc):
        rows = self._orders(sc, buy_at=1, price=1_000_000.0, qty=1.0, usdt=1000.0)
        return ok({"notices": [s["notice"] for s in self._seen(rows)]},
                  "模擬の取引所の残高 usdt 1000(現物)、1 回目に成行 買い 1(値 1,000,000)。戦略が受けた AccountEvent。"
                  f"driver の出力(市場の事象の行を除く) {self._trail(rows)}" + ASYNC_NOTE)

    def scene_p3_notice_filled(self, sc):
        rows = self._orders(sc, buy_at=1, price=100.0, qty=1.0)
        return ok({"filled_qty_in_notices": sum(float(s["qty"]) for s in self._seen(rows) if s["notice"] == "trade")},
                  "1 回目に成行 買い 1(値 100)。戦略が受けた AccountEvent の Trade の数量の合計。"
                  f"driver の出力(市場の事象の行を除く) {self._trail(rows)}" + ASYNC_NOTE)

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        return not_supported("戦略に渡るのは EngineState(銘柄ごとの InstrumentDataState・注文・建玉など)で、過去の事象の列を読む口が無い"
                             "(過去を持つのは利用者が InstrumentDataState に自分で書いた分だけ)")

    def scene_p4_received_time(self, sc):
        evs = C.events(sc)
        rows = self._run(evs)
        rec = {}
        for r in calls(rows):
            now = r["event"]["ts"]  # the engine's HistoricalClock follows time_exchange
            if r["event"]["fields"].get("price") == 101.0:
                rec.setdefault("delivered", now)
            if now == evs[1]["ts_ns"]:
                rec["at2"] = "delivered" in rec
            if now == evs[2]["ts_ns"]:
                rec["at4"] = "delivered" in rec
        return ok({"price101_visible_at_day2": rec.get("at2"), "price101_delivered_at_ns": rec.get("delivered"),
                   "price101_visible_at_day4": rec.get("at4")},
                  "約定の time_exchange=T0+1 日・time_received=T0+3 日(MarketEvent の 2 つの時刻)で、取引所の時刻の順の 1 本の流れで渡した。"
                  "engine の時計は time_exchange を追う(engine/clock.rs HistoricalClock)。"
                  f"戦略の各回(型, time_exchange, time_received): {[(r['event']['kind'], r['event']['ts'], r['event']['recv']) for r in calls(rows)]}")

    def scene_p4_future_read_attempt(self, sc):
        return not_supported("戦略が市場の事象を時刻や位置で読む口が無い(generate_algo_orders に渡るのは EngineState だけで、市場の事象の流れ "
                             "MarketDataInMemory は engine の入力で戦略からは見えない)")

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        return not_supported(NO_TYPE.format(k="資金調達"))

    scene_p5_hand_over_order = scene_p5_same_time_twice

    def scene_p5_same_stream_order(self, sc):
        rows = self._run(C.events(sc))
        return ok({"prices": [r["event"]["fields"]["price"] for r in calls(rows)]}, "同じ時刻の約定 3 件を 1 本の流れで渡し、戦略の各回に受けた値の順")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        rows = self._orders(sc, buy_at=1, limit=True, price=90.0, qty=1.0, read_at=2)
        return not_supported("模擬の取引所(backtest の唯一の執行 ExecutionConfig::Mock)は指値を受けず(MockExchange::validate_order_kind_supported は "
                             "Market だけ)、取消は unimplemented!()(barter-execution/src/exchange/mock/mod.rs の cancel_order)。"
                             f"試したこと: 1 回目に指値 買い 1 @90、2 回目に注文の数を読んだ -> {self._trail(rows)}")

    scene_p6_cancel_notice = scene_p6_place_then_cancel

    def scene_p6_fill_seen_by_strategy(self, sc):
        rows = self._orders(sc, buy_at=1, price=100.0, qty=1.0, read_at=3)
        r = next((x for x in rows if "read_at" in x), {})
        q = r.get("position_qty")
        return ok({"filled_qty_at_call3": float(q) if q is not None else None},
                  "1 回目に成行 買い 1、3 回目に EngineState の銘柄の position.current の quantity_abs(注文ごとの約定済み数量の欄は注文の状態に無い)。"
                  f"driver の出力(市場の事象の行を除く) {self._trail(rows)}" + ASYNC_NOTE)

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        return not_supported("約定の模型の口が無い(backtest の執行は ExecutionConfig::Mock だけで、MockExchange は成行を注文の値でその場で埋める。"
                             "設定は latency_ms・fees_percent・残高)")

    def scene_p7_latency_model_swap(self, sc):
        rows = self._orders(sc, buy_at=1, price=100.0, qty=1.0, latency_ms=14)
        t = [s for s in self._seen(rows) if s["notice"] == "trade"]
        return ok({"fill_time_ns": t[0]["time"] if t else None},
                  "MockExecutionConfig.latency_ms = 14(往復。取引所に届くのは半分の 7 ms、MockExchange::update_time_exchange)、T0 に成行 買い 1。"
                  f"戦略が受けた Trade の time_exchange。driver の出力(市場の事象の行を除く) {self._trail(rows)}" + ASYNC_NOTE)

    def scene_p7_cost_model_swap(self, sc):
        return not_supported("費用の口は MockExecutionConfig.fees_percent(約定の値 × 数量 × 率)の 1 つで、約定 1 件の定額を渡す口が無い")

    def scene_p7_cost_per_unit(self, sc):
        return not_supported("費用の口は MockExecutionConfig.fees_percent(約定の値 × 数量 × 率)の 1 つで、価格によらない数量あたりの額を渡す口が無い")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座を差し替える口が無い(模擬の取引所の口座 MockExchange.account は initial_state の残高から作られ、EngineState の "
                             "建玉・残高は engine が AccountEvent から更新する)")
