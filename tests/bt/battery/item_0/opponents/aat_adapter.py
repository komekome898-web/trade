"""Survey candidate 65 `aat` (GitHub `AsyncAlgoTrading/aat`, commit c4a07d41,
version 0.1.0), run in its own venv `c65`. The wheel built from the clone
held only the C++ binding (`aat/binding*.so`), so the package is used in
place (a `.pth` to the clone, the built binding copied next to it, as
`build_ext --inplace` does); install record `survey_results/attempts/65.log`.

Driven the way the tool's own tests and harness drive it
(`aat/exchange/test/harness.py`): `TradingEngine(**parseConfig(["--trading_type",
"backtest", "--exchanges", "<module>:<Exchange class>", "--strategies",
"<module>::<Strategy class>"])).start()`. The exchange is the tool's plug-in
for the market and for executing orders (its `tick()` yields typed `Event`s:
TRADE with a `Trade`, OPEN / CANCEL / CHANGE / FILL with an `Order`, DATA with
a generic `Data`; its `newOrder` / `cancelOrder` receive the strategy's
orders); the strategy is called per event type (`onTrade`, `onOpen`,
`onData`, ...) and on its own orders (`onBought`, `onSold`, `onRejected`,
`onCanceled`); it trades with `newOrder` / `cancel` and reads `orders()`,
`positions()`, `trades()`. The exchange here is written by this adapter the
way the tool's CSV exchange (`aat/exchange/generic/csv.py`) is: it yields the
scene's events in the order given and fills a queued order on the next
event at the order's price (or at the plugged price).
"""
from __future__ import annotations

import asyncio
import datetime as D
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from aat import Order, OrderType, Side, Strategy, TradingEngine, parseConfig  # noqa: E402
from aat.config import EventType, InstrumentType  # noqa: E402
from aat.core import Data, Event, ExchangeType, Instrument, Trade  # noqa: E402
from aat.exchange import Exchange  # noqa: E402

logging.disable(logging.CRITICAL)
EXCH = ExchangeType("scene")
INST = Instrument("X", InstrumentType.EQUITY, exchange=EXCH)

# One scene run at a time: the engine instantiates the exchange and the strategy
# classes from the config strings, so the scene's data and hooks live here.
RUN: dict = {}


def _dt(ns: int) -> D.datetime:
    return C.ns_to_dt(ns).replace(tzinfo=None)


def _ns(dt) -> int:
    return C.dt_to_ns(dt.replace(tzinfo=D.timezone.utc) if dt.tzinfo is None else dt)


def _event(e: dict) -> Event:
    ts = _dt(int(e["ts_ns"]))
    if e["kind"] == "trade":
        side = Side.BUY if e.get("side", "buy") == "buy" else Side.SELL
        o = Order(float(e["qty"]), float(e["price"]), side, INST, EXCH, timestamp=ts, filled=float(e["qty"]))
        return Event(EventType.TRADE, Trade(volume=float(e["qty"]), price=float(e["price"]), maker_orders=[], taker_order=o))
    if e["kind"] == "book_delta":
        o = Order(float(e["qty"]), float(e["price"]), Side.BUY if e["side"] == "bid" else Side.SELL, INST, EXCH,
                  timestamp=ts, order_type=OrderType.LIMIT)
        return Event(EventType.OPEN, o)
    return Event(EventType.DATA, Data(instrument=INST, exchange=EXCH, data=dict(e), timestamp=ts))


class SceneExchange(Exchange):
    def __init__(self, trading_type, verbose, stream: str = "events") -> None:
        super().__init__(EXCH)
        self._stream = stream
        self._queued: list = []
        self._oid = 0

    async def instruments(self):
        return [INST]

    async def connect(self) -> None:
        pass

    async def tick(self):
        for e in RUN["streams"][self._stream]:
            ev = _event(e)
            RUN.setdefault("now_ns", []).append(int(e["ts_ns"]))
            yield ev
            await asyncio.sleep(0)
            while self._queued:  # fill the queued orders at the order's price (or the plugged fill price), like csv.py
                o = self._queued.pop(0)
                if o.order_type == OrderType.LIMIT and RUN.get("rest_limits"):
                    RUN.setdefault("resting", []).append(o)
                    continue
                o.timestamp = _dt(int(e["ts_ns"]))
                o.filled = o.volume
                px = RUN.get("fill_price") or (o.price if o.order_type == OrderType.LIMIT else float(e.get("price", e.get("close", 0.0))))
                yield Event(EventType.TRADE, Trade(volume=o.volume, price=px, taker_order=o, maker_orders=[], my_order=o))

    async def newOrder(self, order) -> bool:
        self._oid += 1
        order.id = str(self._oid)
        self._queued.append(order)
        return True

    async def cancelOrder(self, order) -> bool:
        res = RUN.get("resting", [])
        for o in list(res):
            if o.id == order.id:
                res.remove(o)
                return True
        return False


class SceneStrategy(Strategy):
    async def _hook(self, kind: str, event) -> None:
        # round r6-2: the provenance of what the tool handed over, made when it is received (event and its own EventType)
        RUN["cars"].append(C.carrier_tag(event, event.type) if kind in ("trade", "open", "data") else None)
        RUN["calls"].append((kind, event))
        fn = RUN.get("fn")
        if fn is not None:
            r = fn(self, kind, event)
            if asyncio.iscoroutine(r):
                await r

    async def onTrade(self, event):
        await self._hook("trade", event)

    async def onOpen(self, event):
        await self._hook("open", event)

    async def onData(self, event):
        await self._hook("data", event)

    async def onBought(self, event):
        await self._hook("bought", event)

    async def onRejected(self, event):
        await self._hook("rejected", event)

    async def onCanceled(self, event):
        await self._hook("canceled", event)


def run(streams: dict, fn=None, **extra) -> dict:
    RUN.clear()
    RUN.update(streams=streams, fn=fn, calls=[], cars=[], **extra)
    args = ["--trading_type", "backtest", "--strategies", "opponents.aat_adapter:SceneStrategy"]
    for name in streams:  # one exchange per input stream, in the hand-over order (parser.py _args_to_dict: "mod:Class,arg")
        args += ["--exchanges", f"opponents.aat_adapter:SceneExchange,{name}"]
    # round r8-1 (positive definition A (1)): the settings -- trading type, the strategy, one exchange (the tool's
    # plug for a user exchange) per input stream -- made through aat's public parseConfig / TradingEngine
    cfg = C.configure(parseConfig, args, what="parseConfig(--trading_type backtest, --strategies 場面の戦略, "
                      f"--exchanges 入力ごとに 1 つ × {len(streams)})", decided_from=("場面の入力", "選ぶ値"))
    t = C.configure(TradingEngine, **cfg, what="TradingEngine(**config)", decided_from=("場面の入力",))
    t.start()
    return dict(RUN)


def _kind_of(kind, event) -> str:
    """The tool's own type of what the strategy received: TRADE -> trade, OPEN
    (an order entering the book) -> book_delta, DATA -> "data" (a generic Data:
    the tool has no type for bars, book snapshots, funding or liquidations;
    the payload's own label is not the tool's type and is not used)."""
    if kind == "trade":
        return "trade"
    if kind == "open":
        return "book_delta"
    return kind


def _ts_of(event) -> int:
    return _ns(event.target.timestamp)


def _try(fn) -> str:
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            return f"-> {fn()!r}"[:200]
    except BaseException as exc:  # noqa: BLE001 - argparse exits with SystemExit and prints its usage
        msg = err.getvalue().strip().splitlines()[-1:] if "err" in locals() else []
        return f"-> {type(exc).__name__}: {str(exc)[:80]} {' '.join(msg)[:160]}"


def _market_calls(out) -> list:
    return [[_kind_of(k, e), _ts_of(e)] for k, e in out["calls"] if k in ("trade", "open", "data")]


def _carriers(out, kinds=("trade", "open", "data")) -> list:
    """What each market call handed the strategy: aat's Event and its own EventType member (read from the event)."""
    return [c for (k, e), c in zip(out["calls"], out["cars"]) if k in kinds]


class AatAdapter(Adapter):
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene
    CONFIGS = {"": {"trading_type": "backtest", "exchange": "利用者の Exchange(aat の口)を入力 1 つに 1 つ"}}
    name = "opp_aat"

    # ---------------- P0-1
    def scene_p1_one_call_per_event(self, sc):
        out = run({"events": C.events(sc)})
        return ok({"sequence": _market_calls(out)},
                  "足の型が無いので足を DATA の事象(道具の型の無い Data)として 1 つの取引所から流し、onData の各回に (道具の型 data, 事象の時刻)"
                  "(この場面は型を採点しない)",
                  {"carriers": _carriers(out)})

    def scene_p1_merge_by_time(self, sc):
        streams = {name: sc.input["streams"][name] for name in sc.input["hand_over_order"]}
        out = run(streams)
        return ok({"sequence": _market_calls(out)},
                  f"{len(streams)} つの入力を {len(streams)} つの取引所(SceneExchange)にし、渡す順に --exchanges に並べた。約定は TRADE、"
                  "板の差分は OPEN(板に入る注文)。戦略が受けた (型, 時刻) の順(道具は取引所の tick を aiostream の merge で 1 本にする)",
                  {"carriers": _carriers(out)})

    def scene_p1_typed_events(self, sc):
        out = run({"events": C.events(sc)})
        return ok({"sequence": _market_calls(out)},
                  "約定は TRADE(Trade)、板の差分は OPEN(板に入る注文)で 1 つの取引所から流し、戦略が受けた道具の型と時刻",
                  {"carriers": _carriers(out)})

    # ---------------- P0-2
    # Round r16-1 (ROOTCAUSE_r16-1.md section 6): the tool's own reader of times in files is its CSV exchange
    # (`aat.exchange.generic.csv.CSV.connect`, lines 45-50 of the clone's aat/exchange/generic/csv.py: a row's "time" by
    # `datetime.fromtimestamp(float(row["time"]))` = seconds, naive local time; "date" / "datetime" by
    # `datetime.fromisoformat`). The ISO scenes and the unit scenes both go through it (until round r16-1 the ISO scenes
    # did not, calling it one exchange among others; the same entry is now used for every P0-2 scene that hands a time).
    @staticmethod
    def _csv_time(column: str, text: str):
        """The tool's CSV exchange reading one row whose `column` holds `text`: the timestamp of the first event it yields."""
        import csv as _csv
        import tempfile
        from aat.config import TradingType
        from aat.exchange.generic.csv import CSV
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rows.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=["symbol", "volume", "close", column])
                w.writeheader()
                w.writerow({"symbol": "X-equity", "volume": "1", "close": "1", column: text})
            ex = CSV(TradingType.BACKTEST, False, str(path))

            async def first():
                await ex.connect()
                async for event in ex.tick():
                    return event.target.timestamp
            # a loop of its own, never made the thread's current loop: asyncio.run would leave the thread without a current
            # loop and the tool's TradingEngine of the later scenes asks for one (measured: RuntimeError in every later scene)
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(first())
            finally:
                loop.close()

    def _iso(self, sc):
        from aat.exchange.generic.csv import CSV
        try:
            got = self._csv_time("datetime", sc.input["iso"])
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"道具の CSV の取引所(CSV.connect、datetime の欄を datetime.fromisoformat で読む)に ISO の文字列を 1 行書いた -> "
                                 f"{type(exc).__name__}: {str(exc)[:160]}")
        return ok(_ns(got), f"道具の CSV の取引所(CSV.connect、datetime の欄を datetime.fromisoformat で読む)に ISO の文字列を 1 行書き、"
                  f"tick が出した最初の事象の時刻 {got!r}", {"reader": C.qualname(CSV.connect)})

    def _units(self, sc):
        import time as _time
        from aat.exchange.generic.csv import CSV
        # the CSV cell is text: a text as it is, an int in decimal, a float as its repr (float() of it is the same float)
        text = lambda v: v if isinstance(v, str) else repr(v)  # noqa: E731
        return C.unit_time(sc, [{"unit": "s", "forms": ("str", "int", "float"),
                                 "how": f"道具の CSV の取引所(CSV.connect、time の欄を datetime.fromtimestamp(float(…)) で読む。地方時の tz 無し、"
                                        f"この環境の地方時 {_time.tzname})",
                                 "reader": CSV.connect, "call": lambda v: self._csv_time("time", text(v))}],
                           tried="この道具が時刻を読む入口は CSV の取引所の time(秒)と date / datetime(ISO)の欄だけ")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso
    scene_p2_s_text = scene_p2_s_text_subns = scene_p2_s_int = scene_p2_s_float_held = scene_p2_s_float_subns = \
        scene_p2_ms_text = scene_p2_ms_text_subns = scene_p2_ms_int = scene_p2_ms_float_held = scene_p2_ms_float_subns = \
        scene_p2_us_text = scene_p2_us_text_subns = scene_p2_us_int = scene_p2_us_float_held = _units  # round r16-1

    def _obs(self, sc):
        evs = [C.substitute(e, "trade", price=100.0, qty=0.01, side="buy") for e in C.events(sc)]
        out = run({"events": evs})
        return ok({"observed_ts_ns": [_ts_of(e) for k, e in out["calls"] if k == "trade"]},
                  "約定を TRADE で流し、onTrade の event.target.timestamp(datetime、マイクロ秒まで)を ns に",
                  {"carriers": _carriers(out, ("trade",))})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        out = run({"events": [e]})
        if e["kind"] not in ("trade", "book_delta"):
            got = [(k, str(ev.target.type)) for k, ev in out["calls"]]
            return not_supported(f"{e['kind']} の型が無い(事象の型は TRADE・OPEN / CANCEL / CHANGE / FILL(注文)・DATA(型の無い汎用のデータ))。"
                                 f"試したこと: DATA で流した -> 戦略が受けた {got}(型の無い Data として届く)")
        calls = [(k, ev, c) for (k, ev), c in zip(out["calls"], out["cars"]) if k in ("trade", "open")]
        if not calls:
            return ok({"sequence": [], "fields": {}}, f"戦略に届かなかった。呼ばれた口 {[k for k, _ in out['calls']]}", {"carriers": []})
        k, ev, car = calls[0]
        t = ev.target
        if k == "trade":
            fields = {"price": float(t.price), "qty": float(t.volume), "side": "buy" if t.side == Side.BUY else "sell"}
        else:
            fields = {"side": "bid" if t.side == Side.BUY else "ask", "price": float(t.price), "qty": float(t.volume)}
        return ok({"sequence": [[_kind_of(k, ev), _ts_of(ev)]], "fields": fields},
                  "約定は TRADE(Trade)、板の差分は OPEN(板に入る注文 Order)で流し、戦略が受けた事象の中身", {"carriers": [car]})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        out = run({"events": C.events(sc)})
        return ok({"sequence": _market_calls(out)},
                  "約定は TRADE、板の差分は OPEN、ほか(板の写真・足・資金調達・清算)は DATA(型の無い Data)で流し、戦略が受けた道具の型と時刻",
                  {"carriers": _carriers(out)})

    def scene_p3_clock_timer(self, sc):
        calls: list = []
        st = {"n": 0}

        async def wake(**kw):
            calls.append(len(RUN.get("now_ns", [])))

        def fn(s, kind, ev):
            if kind != "data":
                return
            st["n"] += 1
            if st["n"] == 1:
                st["p"] = s.at(wake, second=0, minute=0, hour=0)

        out = run({"events": [C.as_bar(e) for e in C.events(sc)]}, fn)
        return ok({"clock_calls_ns": [out["now_ns"][i - 1] if 0 < i <= len(out["now_ns"]) else None for i in calls]},
                  "1 回目の onData で self.at(起こされる関数, second=0, minute=0, hour=0)(時刻の指定は秒・分・時の周期だけで、ある日の 1 回を頼む口は無い。"
                  f"道具の説明: precise timing is NOT guaranteed)。起こされた時点で流れていた事象の時刻。起こされた回数 {len(calls)}")

    def _notice(self, sc, order_kind: str, qty: float):
        def fn(s, kind, ev):
            if kind == "data" and not RUN.get("sent"):
                RUN["sent"] = True
                o = Order(qty, 90.0 if order_kind == "limit" else 0.0, Side.BUY, INST, EXCH,
                          order_type=OrderType.LIMIT if order_kind == "limit" else OrderType.MARKET)
                return s.newOrder(o)
            return None

        return run({"events": [C.as_bar(e) for e in C.events(sc)]}, fn, rest_limits=True)

    def scene_p3_notice_accepted(self, sc):
        out = self._notice(sc, "limit", 1.0)
        notices = [k for k, _ in out["calls"] if k in ("bought", "rejected", "canceled")]
        return ok({"notices": notices}, "1 回目に指値 買い 1 @90 を newOrder。受付を知らせる口(onReceived など)は Strategy に無く、戦略が受けた自分の注文の知らせは "
                  f"{notices}(onBought / onRejected / onCanceled)")

    def scene_p3_notice_rejected(self, sc):
        out = self._notice(sc, "market", 1.0)
        notices = ["filled" if k == "bought" else k for k, _ in out["calls"] if k in ("bought", "rejected", "canceled")]
        return ok({"notices": notices}, "現金を与える設定は取引所の実装の側にあり、この取引所(道具の CSV の取引所と同じ形)は現金を見ない。1 回目に成行 買い 1。"
                  f"戦略が受けた自分の注文の知らせ {notices}")

    def scene_p3_notice_filled(self, sc):
        out = self._notice(sc, "market", 1.0)
        return ok({"filled_qty_in_notices": float(sum(float(ev.target.volume) for k, ev in out["calls"] if k == "bought"))},
                  "1 回目に成行 買い 1、onBought の事象の Trade の数量の合計")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        return not_supported("戦略が過去の相場の事象を読む口が無い(Strategy の読み出しは orders()・positions()・trades()(自分の約定)・"
                             "instruments()・lookup())。試したこと: Strategy.history " + _try(lambda: Strategy.history))

    def scene_p4_received_time(self, sc):
        return not_supported("事象に受け取れる時刻を持たせる口が無い(Trade / Order / Data の時刻は timestamp の 1 つ)")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def fn(s, kind, ev):
            if kind != "data" or _ts_of(ev) != probe or att.items:
                return
            # aat hands the strategy no read of market data by time or position (orders / positions / trades are
            # its own); the calls a strategy would write are made as written
            att.run("self.trades(5 本目の時刻)", "time", lambda: s.trades(_dt(sc.input["future_ts_ns"])), shape="no_means",
                    naming="written_call", via=s.trades)
            att.run("event.target.data['next'](次の位置)", "position", lambda: ev.target.data["next"], shape="no_means",
                    naming="written_call", via=ev)
            att.run("self.positions()", "other", lambda: [str(p) for p in s.positions()])

        run({"events": C.events(sc)}, fn)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の onData で試した: " + att.summary())

    # ---------------- P0-5
    def _tie(self, sc, order):
        out = run({name: sc.input["streams"][name] for name in order})
        return _market_calls(out), _carriers(out)

    def scene_p5_same_time_twice(self, sc):
        order, car = self._tie(sc, sc.input["hand_over_order"])
        return ok({"order": order},
                  f"型ごとの {len(sc.input['streams'])} 入力を {len(sc.input['streams'])} つの取引所にし、渡す順に --exchanges に並べた。"
                  "約定は TRADE、板の差分は OPEN。戦略に届いた (型, 時刻)。"
                  "同じ時刻の並べ方を書いた規則は見つからなかった(engine.py は取引所の tick を aiostream.stream.merge で 1 本にし、時刻では並べない)",
                  {"carriers": car})

    def scene_p5_hand_over_order(self, sc):
        got = [(list(o), *self._tie(sc, o)) for o in sc.input["hand_over_orders"]]
        runs = [{"hand_over": h, "order": order} for h, order, _ in got]
        return ok({"form": "multi_input", "runs": runs}, f"{len(runs)} 通りの --exchanges の並びで各 1 回", {"carriers": [c for _, _, c in got]})

    def scene_p5_same_stream_order(self, sc):
        out = run({"events": C.events(sc)})
        return ok({"prices": [float(e.target.price) for k, e in out["calls"] if k == "trade"]}, "同じ時刻の約定 3 件を 1 つの取引所から TRADE で流した",
                  {"carriers": _carriers(out, ("trade",))})

    # ---------------- P0-6
    def _p6(self, sc, read: bool):
        res = {}

        def fn(s, kind, ev):
            if kind != "data":
                return None
            RUN["n"] = RUN.get("n", 0) + 1
            if RUN["n"] == 1:
                RUN["mine"] = Order(1.0, 90.0, Side.BUY, INST, EXCH, order_type=OrderType.LIMIT)
                return s.newOrder(RUN["mine"])
            if RUN["n"] == 2:
                if read:
                    res["open_at_call2"] = len(s.orders())
                return s.cancel(RUN["mine"])
            if RUN["n"] == 3 and read:
                res["open_at_call3"] = len(s.orders())
            return None

        out = run({"events": [C.as_bar(e) for e in C.events(sc)]}, fn, rest_limits=True)
        return res, out

    def scene_p6_place_then_cancel(self, sc):
        res, out = self._p6(sc, True)
        return ok(res, f"1 回目 newOrder(指値 買い 1 @90)、2 回目 len(self.orders()) と cancel(注文)、3 回目 len(self.orders())。呼ばれた口 {[k for k, _ in out['calls']]}")

    def scene_p6_cancel_notice(self, sc):
        _, out = self._p6(sc, False)
        return ok({"cancel_notice_received": any(k == "canceled" for k, _ in out["calls"])}, f"呼ばれた口 {[k for k, _ in out['calls']]}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        res = {}

        def fn(s, kind, ev):
            if kind != "data":
                return None
            RUN["n"] = RUN.get("n", 0) + 1
            if RUN["n"] == 1:
                RUN["mine"] = Order(1.0, 0.0, Side.BUY, INST, EXCH, order_type=OrderType.MARKET)
                return s.newOrder(RUN["mine"])
            if RUN["n"] == 3:
                res["filled_qty_at_call3"] = float(RUN["mine"].filled)
            return None

        run({"events": [C.as_bar(e) for e in C.events(sc)]}, fn)
        return ok(res, "1 回目 newOrder(成行 買い 1)、3 回目にその Order の filled")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        def fn(s, kind, ev):
            if kind == "data" and not RUN.get("sent"):
                RUN["sent"] = True
                return s.newOrder(Order(1.0, 0.0, Side.BUY, INST, EXCH, order_type=OrderType.MARKET))
            return None

        out = run({"events": [C.as_bar(e) for e in C.events(sc)]}, fn, fill_price=12345.0)
        bought = [float(ev.target.price) for k, ev in out["calls"] if k == "bought"]
        return ok({"fill_price": bought[0] if bought else None},
                  "約定の模型 = 取引所(--exchanges に渡す Exchange の子。道具の CSV の取引所と同じ形で、待っている注文を次の事象で埋める)。"
                  "埋める値を 12345.0 にした取引所を差し込み、1 回目に成行 買い 1、onBought の値")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("遅延の模型を渡す口が無い(TradingEngine の設定に遅延は無く、注文は取引所の newOrder に直に渡る。遅らせるなら取引所そのものを書き直す)。"
                             "試したこと: parseConfig([..., '--latency', '7ms']) " + _try(lambda: parseConfig(["--trading_type", "backtest", "--latency", "7ms"])))

    def _fee(self, sc):
        return not_supported("費用の模型を渡す口が無い(TradingEngine と Strategy に費用の設定が無い。Trade と Order に費用の欄が無い)。"
                             "試したこと: parseConfig([..., '--fees', '0.5']) " + _try(lambda: parseConfig(["--trading_type", "backtest", "--fees", "0.5"])))

    scene_p7_cost_model_swap = scene_p7_cost_per_unit = _fee

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(PortfolioManager)は TradingEngine の trait で、設定から差し替える口が無い。試したこと: parseConfig([..., '--portfolio_manager', ..]) "
                             + _try(lambda: parseConfig(["--trading_type", "backtest", "--portfolio_manager", "x:y"])))
