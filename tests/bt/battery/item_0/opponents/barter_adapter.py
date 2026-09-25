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
# round r8-1 (positive definition A): the engine's start time is the configured target's chosen value, the same in
# every scene; until round r8-1 the driver took the first event's time (`time_first_event`), a setting fitted to
# input not yet delivered. The driver was rebuilt to read it from the input (survey_results/attempts/61.log, round r8-1)
ENGINE_START = C.FIXED_WINDOW[0] + "T00:00:00Z"
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


# The driver's match arms (survey_results/attempts/61.log, fn label, lines 131-138) name each scene kind from the
# tool's own enum variant the event came in; `variant` is the tool's own DataKind::kind_name() printed by the driver.
_VARIANT = {"trade": "DataKind::Trade", "book_l1": "DataKind::OrderBookL1", "book_snapshot": "DataKind::OrderBook(OrderBookEvent::Snapshot)",
            "book_delta": "DataKind::OrderBook(OrderBookEvent::Update)", "bar": "DataKind::Candle", "liquidation": "DataKind::Liquidation"}


def carriers(rows):
    return [C.compiled(f"rust:barter_data::event::{_VARIANT.get(r['event']['kind'], r['event']['kind'])} (kind_name {r['event'].get('variant')})")
            for r in calls(rows)]


class BarterAdapter(Adapter):
    name = "opp_barter"
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    # (the driver's source: survey_results/attempts/61.log, fn main after `let cfg = &input["cfg"]`)
    CONFIGS = {"": {"instrument": "binance_spot BTCUSDT spot", "execution": "ExecutionConfig::Mock",
                    "latency_ms": "0(場面が遅れを名指さないとき)", "fees_percent": "0(場面が費用を名指さないとき)",
                    "balances": "usdt 1,000,000(場面が口座を名指さないとき)", "risk": "DefaultRiskManager",
                    "summary_interval": "Daily", "trading_state": "Enabled", "engine_start": C.FIXED_WINDOW[0] + "T00:00:00Z"}}

    def _run(self, events, **cfg):
        # round r8-1 (positive definition A (1)): the settings the driver makes through the tool's public API, in
        # the order it makes them (the driver's source, survey_results/attempts/61.log, fn main)
        scene = ("場面の入力",)
        C.configure_compiled("rust:barter::system::config::InstrumentConfig", what="InstrumentConfig(binance_spot BTCUSDT spot)",
                             decided_from=("選ぶ値",))
        C.configure_compiled("rust:barter::system::config::ExecutionConfig::Mock",
                             what=f"ExecutionConfig::Mock(latency_ms={cfg.get('latency_ms', 0)}, fees_percent={cfg.get('fees_percent', 0.0)}, "
                                  f"balances usdt={cfg.get('usdt', 1_000_000.0)})",
                             decided_from=scene if {"latency_ms", "fees_percent", "usdt"} & set(cfg) else ("選ぶ値",))
        C.configure_compiled("rust:barter::backtest::market_data::MarketDataInMemory::new",
                             what="MarketDataInMemory::new(場面の事象の 1 本の流れ)", decided_from=scene)
        C.configure_compiled("rust:barter::engine::state::builder::EngineStateBuilder",
                             what=f"EngineStateBuilder::new(instruments, DefaultGlobalData, 利用者の InstrumentDataState)"
                                  f".time_engine_start({ENGINE_START}).trading_state(Enabled).build()",
                             decided_from=("選ぶ値", "公開の既定"))
        C.configure_compiled("rust:barter::risk::DefaultRiskManager", what="BacktestArgsDynamic(risk = DefaultRiskManager::default())",
                             decided_from=("公開の既定",))
        C.configure_compiled("rust:barter::backtest::backtest", what="backtest(args_constant(summary_interval Daily), args_dynamic)",
                             decided_from=("選ぶ値",))
        return drv({"cfg": {**cfg, "engine_start": ENGINE_START}, "events": [ev(e) for e in events]})

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        rows = self._run(C.events(sc))
        return ok({"sequence": seq(rows)}, "足を Candle の MarketEvent にして 1 本の流れで渡し、戦略の各回に InstrumentDataState が受けた (型, time_exchange)",
                  {"carriers": carriers(rows)})

    def scene_p1_merge_by_time(self, sc):
        # the backtest takes ONE stream of market events (MarketDataInMemory::new(Vec<MarketStreamEvent>),
        # barter/src/backtest/market_data.rs 61-70): the inputs are concatenated in the hand-over order
        miss = sorted({e["kind"] for e in C.concatenated(sc)} - set(_VARIANT))
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss)))
        rows = self._run(C.concatenated(sc))
        return ok({"sequence": seq(rows)}, "市場の事象の入力は 1 本(MarketDataInMemory の Vec)なので、入力を渡す順に連結して渡した。"
                  "戦略の各回に InstrumentDataState が受けた (型, time_exchange)", {"carriers": carriers(rows)})

    def scene_p1_typed_events(self, sc):
        rows = self._run(C.events(sc))
        return ok({"sequence": seq(rows)}, "型の違う 2 件を道具の型(DataKind)の MarketEvent で 1 本の流れにして渡した。戦略の各回に受けた (型, time_exchange)",
                  {"carriers": carriers(rows)})

    # ---------------- P0-2
    def _iso(self, sc):
        line = json.dumps({"Item": {"time_exchange": sc.input["iso"], "time_received": sc.input["iso"], "exchange": "binance_spot",
                                    "instrument": 0, "kind": {"Trade": {"id": "1", "price": 100.0, "amount": 1.0, "side": "Buy"}}}})
        rows = drv({"parse": line})
        r = rows[0] if rows else {}
        return ok(r.get("parsed_ns"), "道具の市場の事象の記録(MarketStreamEvent の JSON。道具の例の資料と同じ形)の time_exchange に ISO の文字列を書き、"
                  f"道具の読み込み(serde + chrono の DateTime<Utc>)で読んだ時刻。{r}",
                  {"reader": C.compiled("rust:barter_data::streams::consumer::MarketStreamEvent (serde の Deserialize、time_exchange: chrono::DateTime<Utc>)")})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-2 unit scenes (round r16-1): the tool's own epoch deserializers, barter_integration::serde::de
    # (barter-integration/src/serde/de/util.rs of the clone): de_u64_epoch_ms_as_datetime_utc (a u64 of ms),
    # de_str_f64_epoch_ms_as_datetime_utc (a text of an f64 of ms, `as u64`), de_str_f64_epoch_s_as_datetime_utc (a text
    # of an f64 of s, Duration::from_secs_f64). The driver calls them on the value (survey_results/attempts/61.log, round
    # r16-1) and reads the DateTime<Utc> with chrono's timestamp_nanos_opt. A float for a text deserializer is written as
    # its repr (parsing it as f64 gives the same float). None reads microseconds.
    @staticmethod
    def _de(name: str, value):
        r = drv({"de": name, "value": value})
        row = r[0] if r else {}
        if "de_error" in row:  # round r17-1: the tool's own `Err`, as the driver printed it
            raise C.CompiledRefusal(row["de_error"])
        if "de_ns" not in row:
            raise ValueError(f"no output: {r}")  # the driver printed nothing: not the tool's refusal
        return int(row["de_ns"])

    def _units(self, sc):
        text = lambda v: v if isinstance(v, str) else repr(v)  # noqa: E731
        de = "rust:barter_integration::serde::de::"
        return C.unit_time(sc, [
            {"unit": "s", "forms": ("str", "float"), "how": "barter_integration::serde::de::de_str_f64_epoch_s_as_datetime_utc(秒の f64 の文字)",
             "reader": C.compiled(de + "de_str_f64_epoch_s_as_datetime_utc"),
             "call": lambda v: self._de("de_str_f64_epoch_s_as_datetime_utc", text(v))},
            {"unit": "ms", "forms": ("int",), "how": "barter_integration::serde::de::de_u64_epoch_ms_as_datetime_utc(ミリ秒の u64)",
             "reader": C.compiled(de + "de_u64_epoch_ms_as_datetime_utc"),
             "call": lambda v: self._de("de_u64_epoch_ms_as_datetime_utc", v)},
            {"unit": "ms", "forms": ("str", "float"), "how": "barter_integration::serde::de::de_str_f64_epoch_ms_as_datetime_utc(ミリ秒の f64 の文字)",
             "reader": C.compiled(de + "de_str_f64_epoch_ms_as_datetime_utc"),
             "call": lambda v: self._de("de_str_f64_epoch_ms_as_datetime_utc", text(v))}],
            tried="マイクロ秒を読む変換は無い(barter_integration::serde::de の時刻の変換は秒とミリ秒だけ)")

    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _obs(self, sc):
        evs = [C.substitute(e, "trade", price=100.0, qty=0.01, side="buy") for e in C.events(sc)]
        rows = self._run(evs)
        return ok({"observed_ts_ns": [r["event"]["ts"] for r in calls(rows)]}, "約定(Trade)の time_exchange(DateTime<Utc>、ナノ秒)で渡し、戦略の各回に受けた時刻",
                  {"carriers": carriers(rows)})

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
                  f"戦略の回に InstrumentDataState が受けた型・時刻・欄(板の値と量は Decimal の文字列を数に)。道具の型名 {c[0]['event']['variant'] if c else None}",
                  {"carriers": carriers(rows)})

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
    # One input only (MarketDataInMemory, barter/src/backtest/market_data.rs 28-31: "Stores all market
    # events in memory and generates a Stream of MarketStreamEvent by lazy cloning the data as it's
    # required"). No written rule for events of one time was found in the crate (the doc above and the
    # engine's HistoricalClock, engine/clock.rs, which follows each event's time_exchange); the scene
    # set has no stated rule for this tool (stated_rules.py).
    def _p5_once(self, sc, hand_over):
        rows = self._run(C.concatenated(sc, list(hand_over)))
        return seq(rows), carriers(rows)

    def scene_p5_same_time_twice(self, sc):
        miss = sorted({e["kind"] for e in C.concatenated(sc)} - set(_VARIANT))
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss)))
        order, car = self._p5_once(sc, sc.input["hand_over_order"])
        return ok({"order": order}, "市場の事象の入力は 1 本なので、型ごとの入力を渡す順に連結した 1 本を渡した。戦略に届いた (型, time_exchange)。"
                  "同じ時刻の並べ方を書いた規則は crate に見つからなかった(backtest/market_data.rs の MarketDataInMemory の説明・engine/clock.rs)",
                  {"carriers": car})

    def scene_p5_hand_over_order(self, sc):
        miss = sorted({e["kind"] for e in C.concatenated(sc, sc.input["hand_over_orders"][0])} - set(_VARIANT))
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss)))
        runs, cars = [], []
        for o in sc.input["hand_over_orders"]:
            order, car = self._p5_once(sc, o)
            runs.append({"hand_over": list(o), "order": order})
            cars.append(car)
        return ok({"form": "single_input", "runs": runs}, f"{len(runs)} 通りの渡す順それぞれで連結した 1 本を渡し、各回の (型, time_exchange) を記録",
                  {"carriers": cars})

    def scene_p5_same_stream_order(self, sc):
        rows = self._run(C.events(sc))
        return ok({"prices": [r["event"]["fields"]["price"] for r in calls(rows)]}, "同じ時刻の約定 3 件を 1 本の流れで渡し、戦略の各回に受けた値の順",
                  {"carriers": carriers(rows)})

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
