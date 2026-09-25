"""Survey candidate 1 `Basana` (PyPI `basana` 1.11), run in its own venv.

Driven through its public API only: `basana.backtesting_dispatcher()` with
`FifoQueueEventSource` and `dispatcher.subscribe`, `dispatcher.schedule`
(timers), `dispatcher.now()`, and the backtesting `Exchange` (orders,
`subscribe_to_order_events`, and its plug points
`liquidity_strategy_factory` and `fee_strategy`).
Basana's time type is `datetime.datetime` (event `when`).

Event types (round r6-1, critic i0-r5-02): every event is carried in a class
that Basana's own distribution defines -- a bar in `basana.core.bar.BarEvent`,
a trade in `basana.external.bitstamp.trades.TradeEvent` (its Trade has
price, amount and the side as `operation`), a book snapshot in
`basana.external.binance.order_book.PartialOrderBookEvent`, a book delta in
`basana.external.binance.order_book_diff.OrderBookDiffEvent`. Funding and
liquidation have no class in the distribution (`_EVENT_CLASSES` lists every
subclass of `basana.Event` in it, walked with pkgutil); the P0-3 scenes of
those types are not supported, and the scenes of other viewpoints get their
types from Basana's own (round r7-1, runner). The adapter defines no event
class of its own.
"""
from __future__ import annotations

import asyncio
import datetime as D
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import basana as bs  # noqa: E402
from basana.backtesting import exchange as bex, fees as bfees, liquidity as bliq  # noqa: E402

PAIR = bs.Pair("BTC", "JPY")
PAIR_INFO = bs.PairInfo(base_precision=3, quote_precision=2)


from basana.core.bar import BarEvent  # noqa: E402
from basana.external.binance import order_book as bbook, order_book_diff as bdiff  # noqa: E402
from basana.external.bitstamp import trades as btrades  # noqa: E402


def _event_classes() -> list[str]:
    """Every subclass of basana.Event defined in Basana's distribution (what a
    type in a scene could be carried in)."""
    import importlib
    import inspect
    import pkgutil
    found = set()
    for m in pkgutil.walk_packages(bs.__path__, "basana."):
        try:
            mod = importlib.import_module(m.name)
        except Exception:  # noqa: BLE001 - optional extras (ccxt, charts) are not installed
            continue
        for _, c in inspect.getmembers(mod, inspect.isclass):
            if issubclass(c, bs.Event) and c.__module__ == mod.__name__:
                found.add(f"{c.__module__}.{c.__qualname__}")
    return sorted(found)


_EVENT_CLASSES = _event_classes()
NO_TYPE = ("Basana の配布物に「{k}」の事象の型が無い。配布物の basana.Event の子の全部(pkgutil で辿った): {classes}")


def _dec(x) -> str:
    return format(Decimal(str(x)), "f")


def _event(e: dict):
    """A scene event in the Basana class for its type (None when the distribution has none)."""
    when = C.ns_to_dt(e["ts_ns"])
    k = e["kind"]
    if k == "bar":
        return BarEvent(when, bs.Bar(when - D.timedelta(seconds=1), PAIR, Decimal(str(e["open"])), Decimal(str(e["high"])),
                                     Decimal(str(e["low"])), Decimal(str(e["close"])), Decimal(str(e["volume"])),
                                     D.timedelta(seconds=1)))
    if k == "trade":
        return btrades.TradeEvent(when, btrades.Trade(PAIR, {
            "id": 1, "microtimestamp": str(int(e["ts_ns"]) // 1000), "amount_str": _dec(e["qty"]), "price_str": _dec(e["price"]),
            "type": 0 if e["side"] == "buy" else 1, "buy_order_id": 1, "sell_order_id": 2}))
    if k == "book_snapshot":
        return bbook.PartialOrderBookEvent(when, bbook.PartialOrderBook(PAIR, {
            "lastUpdateId": 1, "bids": [[_dec(p), _dec(q)] for p, q in e["bids"]], "asks": [[_dec(p), _dec(q)] for p, q in e["asks"]]}))
    if k == "book_delta":
        lvl = [[_dec(e["price"]), _dec(e["qty"])]]
        return bdiff.OrderBookDiffEvent(when, bdiff.OrderBookDiff(PAIR, {
            "e": "depthUpdate", "E": int(e["ts_ns"]) // 1_000_000, "s": "BTCJPY", "U": 1, "u": 1,
            "b": lvl if e["side"] == "bid" else [], "a": lvl if e["side"] == "ask" else []}))
    return None


def _missing(evs: list[dict]) -> list[str]:
    return sorted({e["kind"] for e in evs if _event(e) is None})


def _kind(ev) -> str:
    """The scene word for the Basana class the strategy received."""
    return {BarEvent: "bar", btrades.TradeEvent: "trade", bbook.PartialOrderBookEvent: "book_snapshot",
            bdiff.OrderBookDiffEvent: "book_delta"}.get(type(ev), type(ev).__name__)


def _fields(ev) -> dict:
    if isinstance(ev, BarEvent):
        b = ev.bar
        return {"open": float(b.open), "high": float(b.high), "low": float(b.low), "close": float(b.close), "volume": float(b.volume)}
    if isinstance(ev, btrades.TradeEvent):
        t = ev.trade
        return {"price": float(t.price), "qty": float(t.amount), "side": t.operation.name.lower()}
    if isinstance(ev, bbook.PartialOrderBookEvent):
        ob = ev.order_book
        return {"bids": [[float(x.price), float(x.volume)] for x in ob.bids], "asks": [[float(x.price), float(x.volume)] for x in ob.asks]}
    if isinstance(ev, bdiff.OrderBookDiffEvent):
        d = ev.order_book_diff
        side, lv = ("bid", d.bids[0]) if d.bids else ("ask", d.asks[0])
        return {"side": side, "price": float(lv.price), "qty": float(lv.volume)}
    return {}


from stated_rules import TYPE_PRIORITY  # noqa: E402  (the setting the stated rule is written for)


def run_streams(streams: list[list[dict]], on_event=None, timer_at=None, priorities=True):
    """Each stream becomes one event source; returns records (kind, now_ns, when_ns, fields).
    Each source gets the documented `priority` (EventSource, core/event.py) by the
    type of its events -- the configured target's chosen value, the same in every
    scene (round r8-1, positive definition A; until round r8-1 only
    p5-hand-over-order set it). Settings are made through common.configure."""
    disp = C.configure(bs.backtesting_dispatcher, what="backtesting_dispatcher()", decided_from=("公開の既定",))
    recs = []

    async def handler(ev):
        recs.append((_kind(ev), C.dt_to_ns(disp.now()), C.dt_to_ns(ev.when), _fields(ev), C.carrier(ev)))
        if on_event:
            on_event(disp, len(recs), ev)
        if timer_at is not None and len(recs) == 1:
            async def job():
                recs.append(("clock", C.dt_to_ns(disp.now()), None, {}, None))
            disp.schedule(C.ns_to_dt(timer_at), job)

    for evs in streams:
        kw = {"priority": TYPE_PRIORITY[evs[0]["kind"]]} if priorities and evs else {}
        src = C.configure(bs.FifoQueueEventSource, events=[_event(e) for e in evs], **kw,
                          what=f"FifoQueueEventSource(events=場面の入力の 1 つ{', priority=' + str(kw['priority']) if kw else ''})",
                          decided_from=("場面の入力", "選ぶ値") if kw else ("場面の入力",))
        C.configure(disp.subscribe, src, handler, what="dispatcher.subscribe(source, handler)", decided_from=("場面の入力",))
    asyncio.run(disp.run())
    return recs


class _FixedPrice(bliq.LiquidityStrategy):
    """Liquidity model plugged through `liquidity_strategy_factory`: infinite
    amount, and a price impact that puts every fill at 12345.0 (Basana applies
    it as price * (1 + impact) to the bar's open, backtesting/orders.py 570-580)."""

    def __init__(self):
        self._ref = Decimal(1)

    def on_bar(self, bar):
        self._ref = bar.open

    @property
    def available_liquidity(self) -> Decimal:
        return Decimal("1e9")

    def take_liquidity(self, amount: Decimal) -> Decimal:
        return Decimal(0)

    def calculate_price_impact(self, amount: Decimal) -> Decimal:
        return Decimal("12345") / self._ref - 1  # slipped_price: price * (1 + impact), orders.py 575-578

    def calculate_amount(self, price_impact: Decimal) -> Decimal:
        return Decimal("1e9")


class _PerUnitFee(bfees.FeeStrategy):
    """0.375 JPY per unit of the base symbol filled (the fee_strategy socket;
    total over the order minus what was already charged, as Basana's own
    Percentage strategy does, backtesting/fees.py 83-91)."""

    def __init__(self, per_unit: Decimal):
        self.per_unit = per_unit

    def calculate_fees(self, order, balance_updates):
        charged = order.fees.get("JPY", Decimal(0))
        base = abs(order.balance_updates.get("BTC", Decimal(0)) + balance_updates.get("BTC", Decimal(0)))
        pending = -self.per_unit * base - charged
        return {"JPY": pending} if pending != 0 else {}


class _FlatFee(bfees.FeeStrategy):
    def __init__(self, fee: Decimal):
        self.fee = fee

    def calculate_fees(self, order, balance_updates):
        charged = order.fees.get("JPY", Decimal(0))
        return {"JPY": -self.fee - charged} if -self.fee - charged != 0 else {}


def run_exchange(bars: list[dict], cash: float, plan, liquidity=None, fee=None):
    """Bars go through the backtesting Exchange; `plan(ex, n, st)` is the strategy
    (async, called on the n-th bar). Returns (log of notices, state)."""
    disp = C.configure(bs.backtesting_dispatcher, what="backtesting_dispatcher()", decided_from=("公開の既定",))
    kw = {}
    if liquidity is not None:
        kw["liquidity_strategy_factory"] = liquidity
    else:
        kw["liquidity_strategy_factory"] = bliq.InfiniteLiquidity
    if fee is not None:
        kw["fee_strategy"] = fee
    ex = C.configure(bex.Exchange, disp, {"JPY": Decimal(str(cash))}, default_pair_info=PAIR_INFO, **kw,
                     what="backtesting Exchange(dispatcher, 場面の口座の残高, default_pair_info, "
                          f"liquidity_strategy_factory={'場面の模型' if liquidity is not None else 'InfiniteLiquidity'}"
                          f"{', fee_strategy=場面の模型' if fee is not None else ''})",
                     decided_from=("場面の入力", "公開の既定") if liquidity is None else ("場面の入力",))
    src = C.configure(bs.FifoQueueEventSource, events=[_event(b) for b in bars], what="FifoQueueEventSource(events=場面の足)",
                      decided_from=("場面の入力",))
    C.configure(ex.add_bar_source, src, what="Exchange.add_bar_source(source)", decided_from=("場面の入力",))
    st = {"notices": [], "n": 0, "events": [], "disp": disp}

    async def on_bar(be):
        st["n"] += 1
        st["bar_event"] = be
        await plan(ex, st["n"], st)

    async def on_order(oe):
        o = oe.order
        if o.id != st.get("id"):
            return
        st["events"].append({"is_open": o.is_open, "filled": float(o.amount_filled), "fees": {k: float(v) for k, v in o.fees.items()},
                             "fills": [(C.dt_to_ns(f.when), float(f.balance_updates.get("JPY", 0))) for f in getattr(o, "fills", [])],
                             "now": C.dt_to_ns(disp.now())})
        prev = st["events"][-2]["filled"] if len(st["events"]) > 1 else 0.0
        if o.is_open and float(o.amount_filled) == 0 and len(st["events"]) == 1:
            st["notices"].append("accepted")
        elif float(o.amount_filled) > prev:
            st["notices"].append("filled")
            st.setdefault("fill_qty", 0.0)
            st["fill_qty"] += float(o.amount_filled) - prev
        elif not o.is_open:
            st["notices"].append("canceled")

    C.configure(ex.subscribe_to_bar_events, PAIR, on_bar, what="Exchange.subscribe_to_bar_events(pair, handler)",
                decided_from=("場面の入力",))
    C.configure(ex.subscribe_to_order_events, on_order, what="Exchange.subscribe_to_order_events(handler)",
                decided_from=("場面の入力",))
    asyncio.run(disp.run())
    return st


async def _place(ex, st, fn):
    try:
        o = await fn()
        st["id"] = o.id
        st["created"] = o
    except Exception as exc:  # noqa: BLE001
        st["notices"].append("rejected")
        st["reject_error"] = f"{type(exc).__name__}: {exc}"


class BasanaAdapter(Adapter):
    # round r8-1 (positive definition A): the one configured target -- each event source's `priority`
    # by the type of its events (stated_rules.TYPE_PRIORITY), in every scene
    CONFIGS = {"": {"priority": {"bar": 60, "trade": 50, "book_snapshot": 45, "book_delta": 40, "funding": 30,
                                 "liquidation": 20}}}
    name = "opp_basana"

    # ---------------- P0-1
    def _typed_run(self, streams: list[list[dict]], what: str, **kw):
        miss = _missing([e for evs in streams for e in evs])
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss), classes=_EVENT_CLASSES)), None
        recs = run_streams(streams, **kw)
        return None, recs

    def scene_p1_merge_by_time(self, sc):
        bad, recs = self._typed_run([evs for _, evs in C.streams_in_order(sc)], "")
        if bad:
            return bad
        return ok({"sequence": [[r[0], r[1]] for r in recs]}, "型ごとの入力を渡した順に event source にして subscribe",
                  {"carriers": [r[4] for r in recs]})

    def scene_p1_one_call_per_event(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"sequence": [[r[0], r[1]] for r in recs]}, "BarEvent 5 件を 1 つの source で渡した",
                  {"carriers": [r[4] for r in recs]})

    def scene_p1_typed_events(self, sc):
        bad, recs = self._typed_run([C.events(sc)], "")
        if bad:
            return bad
        return ok({"sequence": [[r[0], r[1]] for r in recs]},
                  "型の違う 2 件を Basana の配布物の class(" + "・".join(sorted({r[4]["type"] for r in recs if isinstance(r[4], dict)}))
                  + ")で 1 つの source に入れた。戦略は受け取った物の class で型を見分けた", {"carriers": [r[4] for r in recs]})

    # ---------------- P0-2
    def _iso(self, sc):
        from basana.external.common.csv import bars as csv_bars
        row = {"datetime": sc.input["iso"], "open": "1", "high": "1", "low": "1", "close": "1", "volume": "1"}
        parser = csv_bars.RowParser(PAIR, D.timezone.utc, D.timedelta(days=1))
        try:
            evs = parser.parse_row(row)
        except Exception as exc:  # noqa: BLE001
            return not_supported("Basana が時刻の文字列を読む入口は CSV の足の読み(basana.external.common.csv.bars.RowParser.parse_row、"
                                 "strptime('%Y-%m-%d %H:%M:%S'))で、ISO の文字列を渡すと "
                                 f"{type(exc).__name__}: {str(exc)[:120]}。ほかに時刻の文字列を受ける公開の関数は無い"
                                 "(binance の helpers.timestamp_to_datetime はミリ秒の整数を受ける)")
        return ok(C.dt_to_ns(evs[0].bar.datetime), "RowParser.parse_row が読んだ足の datetime",
                  {"reader": C.qualname(csv_bars.RowParser.parse_row)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [C.substitute(e, "bar", open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
               for e in C.events(sc)]
        recs = run_streams([evs])
        return ok({"observed_ts_ns": [r[2] for r in recs]}, "足(basana.core.bar.BarEvent)で渡し、ev.when を ns にした値",
                  {"carriers": [r[4] for r in recs]})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        bad, recs = self._typed_run([C.events(sc)], "")
        if bad:
            return bad
        return ok({"sequence": [[r[0], r[1]] for r in recs], "fields": recs[0][3] if recs else None},
                  "Basana の配布物のその型の class で渡し、戦略が受け取った物の欄を読んだ", {"carriers": [r[4] for r in recs]})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        bad, recs = self._typed_run([C.events(sc)], "")
        if bad:
            return bad
        return ok({"sequence": [[r[0], r[1]] for r in recs]}, "1 つの source で 6 種", {"carriers": [r[4] for r in recs]})

    def scene_p3_clock_timer(self, sc):
        evs = C.events(sc)
        recs = run_streams([evs], timer_at=sc.input["timer_at_ns"])
        return ok({"clock_calls_ns": [r[1] for r in recs if r[0] == "clock"]}, "1 回目に dispatcher.schedule(頼む時刻, job)")

    def _bars(self, sc):
        return [C.as_bar(e) for e in C.events(sc)]

    def scene_p3_notice_accepted(self, sc):
        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_limit_order(bs.OrderOperation.BUY, PAIR, Decimal("1"), Decimal("90")))

        st = run_exchange(self._bars(sc), 1_000_000, plan)
        return ok({"notices": st["notices"]}, f"約定を足に代えた(any_type)。order events: {st['events']}")

    def scene_p3_notice_rejected(self, sc):
        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_market_order(bs.OrderOperation.BUY, PAIR, Decimal("1")))

        st = run_exchange(self._bars(sc), 1_000, plan)
        return ok({"notices": st["notices"]}, f"現金 1,000 円。order events: {st['events']} / 発注の例外: {st.get('reject_error')}")

    def scene_p3_notice_filled(self, sc):
        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_market_order(bs.OrderOperation.BUY, PAIR, Decimal("1")))

        st = run_exchange(self._bars(sc), 1_000_000, plan)
        return ok({"filled_qty_in_notices": st.get("fill_qty", 0.0), "notices": st["notices"]}, f"order events: {st['events']}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        tried = {}

        async def plan(ex, n, st):
            if C.dt_to_ns(st["disp"].now()) != probe or tried:
                return
            tried["public"] = sorted(m for m in dir(ex) if not m.startswith("_"))
            for name in ("get_bars", "get_bar_history", "get_candles"):
                try:
                    getattr(ex, name)(PAIR)
                    tried[name] = "呼べた"
                except Exception as exc:  # noqa: BLE001
                    tried[name] = f"{type(exc).__name__}: {exc}"

        run_exchange(C.events(sc), 1_000_000, plan)
        if not tried:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return not_supported("Basana は戦略に過去の事象を読む公開の手段を渡さない(戦略が受け取るのは各回の BarEvent だけ)。"
                             f"試したこと: T0 + 4 日の呼び出しで検証の取引所の公開の名前 {tried['public']} を見て、過去の足を読む名前を呼んだ -> "
                             + " / ".join(f"{k}: {v}" for k, v in tried.items() if k != "public"))

    def scene_p4_received_time(self, sc):
        try:
            bs.Event(C.ns_to_dt(0), received=C.ns_to_dt(1))  # type: ignore[call-arg]
            r = "受け付けた"
        except TypeError as exc:
            r = f"TypeError: {exc}"
        return not_supported("事象は時刻を 1 つ(when)しか持たない。受け取れる時刻を別に渡す口が無い。"
                             f"試したこと: basana.Event(when, received=...) -> {r}")

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        fut = C.ns_to_dt(sc.input["future_ts_ns"])
        att = C.Attempts()

        async def plan(ex, n, st):
            if C.dt_to_ns(st["disp"].now()) != probe or att.items:
                return
            # Basana hands the strategy no read that takes a time or a position (the Exchange's public
            # methods: get_bid_ask(pair), get_balance(s), get_open_orders, get_order_info, ...; BarEvent
            # has `bar` only). The calls a strategy would write to reach the 5th bar are made as written:
            await att.run_async("exchange.get_bid_ask(pair, 5 本目の時刻)", "time", lambda: ex.get_bid_ask(PAIR, fut),
                                shape="no_means", naming="written_call", via=ex.get_bid_ask)
            att.run("受け取った BarEvent の bar[1](次の足)", "position", lambda: st["bar_event"].bar[1],
                    shape="no_means", naming="written_call", via=st["bar_event"].bar)
            await att.run_async("exchange.get_bid_ask(pair)(今の値)", "other", lambda: ex.get_bid_ask(PAIR))

        run_exchange(C.events(sc), 1_000_000, plan)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の呼び出しで試した: " + att.summary())

    # ---------------- P0-5
    # Basana's written same-time rule (the dispatcher's heap key and the sources'
    # `priority`) is fixed in stated_rules.py. Round r7-1: the P0-5 inputs are
    # built by the runner from Basana's own types (scenes.for_target_types), one
    # type per input; each input becomes one event source whose public
    # `priority` argument is the setting the stated rule is written for
    # (stated_rules.TYPE_PRIORITY), subscribed in the hand-over order.
    def _p5_once(self, sc, hand_over):
        recs = run_streams([sc.input["streams"][k] for k in hand_over])
        return [[r[0], r[2]] for r in recs], [r[4] for r in recs]

    def scene_p5_same_time_twice(self, sc):
        miss = _missing(C.concatenated(sc))
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss), classes=_EVENT_CLASSES))
        order, car = self._p5_once(sc, sc.input["hand_over_order"])
        return ok({"order": order}, f"型ごとの {len(sc.input['streams'])} つの入力を 1 つずつ event source にし(source の公開の引数 priority に"
                  "場面集の側で固定した値)、渡した順に dispatcher.subscribe した。戦略に届いた(型, 事象の時刻 when)",
                  {"carriers": car})

    def scene_p5_hand_over_order(self, sc):
        miss = _missing(C.concatenated(sc, sc.input["hand_over_orders"][0]))
        if miss:
            return not_supported(NO_TYPE.format(k="・".join(miss), classes=_EVENT_CLASSES))
        runs, cars = [], []
        for o in sc.input["hand_over_orders"]:
            order, car = self._p5_once(sc, o)
            runs.append({"hand_over": list(o), "order": order})
            cars.append(car)
        return ok({"form": "multi_input", "runs": runs},
                  f"{len(runs)} 通りの渡す順で、型ごとの入力を event source にして subscribe し(priority は同じ固定の値)、各回の(型, 時刻)を記録",
                  {"carriers": cars})

    def scene_p5_same_stream_order(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"prices": [r[3].get("price") for r in recs]},
                  "1 つの source で同時刻の約定 3 件(basana.external.bitstamp.trades.TradeEvent)", {"carriers": [r[4] for r in recs]})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}

        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_limit_order(bs.OrderOperation.BUY, PAIR, Decimal("1"), Decimal("90")))
            elif n == 2:
                out["open_at_call2"] = len(await ex.get_open_orders())
                await ex.cancel_order(st["id"])
            elif n == 3:
                out["open_at_call3"] = len(await ex.get_open_orders())

        st = run_exchange(self._bars(sc), 1_000_000, plan)
        return ok(out, f"約定を足に代えた。order events: {st['events']}")

    def scene_p6_cancel_notice(self, sc):
        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_limit_order(bs.OrderOperation.BUY, PAIR, Decimal("1"), Decimal("90")))
            elif n == 2:
                await ex.cancel_order(st["id"])

        st = run_exchange(self._bars(sc), 1_000_000, plan)
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]}, f"order events: {st['events']}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_market_order(bs.OrderOperation.BUY, PAIR, Decimal("1")))
            elif n == 3:
                info = await ex.get_order_info(st["id"])
                out["filled_qty_at_call3"] = float(info.amount_filled)

        run_exchange(self._bars(sc), 1_000_000, plan)
        return ok(out, "3 回目に exchange.get_order_info(id).amount_filled")

    # ---------------- P0-7
    def _market_buy(self, sc, amount: str = "1", **kw):
        async def plan(ex, n, st):
            if n == 1:
                await _place(ex, st, lambda: ex.create_market_order(bs.OrderOperation.BUY, PAIR, Decimal(amount)))

        return run_exchange(self._bars(sc), 100_000, plan, **kw)

    def scene_p7_fill_model_swap(self, sc):
        st = self._market_buy(sc, liquidity=_FixedPrice)
        ev = [e for e in st["events"] if e["filled"] > 0]
        price = -ev[0]["fills"][0][1] if ev and ev[0]["fills"] else None
        return ok({"fill_price": price}, "liquidity_strategy_factory に、価格の影響で 12345 に埋める模型を渡した。"
                  f"約定の JPY の増減から価格を読んだ。order events: {st['events']}")

    def scene_p7_latency_model_swap(self, sc):
        try:
            bex.Exchange(bs.backtesting_dispatcher(), {}, order_latency=D.timedelta(milliseconds=7))  # type: ignore[call-arg]
            r = "受け付けた"
        except TypeError as exc:
            r = f"TypeError: {exc}"
        return not_supported(f"遅延の模型を渡す口が無い。試したこと: Exchange(..., order_latency=...) -> {r}")

    def _fee(self, sc, fee):
        st = self._market_buy(sc, fee=_FlatFee(Decimal(str(fee))))
        ev = [e for e in st["events"] if e["filled"] > 0]
        f = abs(ev[-1]["fees"].get("JPY", 0.0)) if ev else None
        return ok({"fee": f}, f"fee_strategy に 1 件 {fee} 円の模型を渡した。order events: {st['events']}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_per_unit(self, sc):
        st = self._market_buy(sc, amount="2", fee=_PerUnitFee(Decimal("0.375")))
        ev = [e for e in st["events"] if e["filled"] > 0]
        f = abs(ev[-1]["fees"].get("JPY", 0.0)) if ev else None
        return ok({"fee": f}, f"fee_strategy に数量 1 単位あたり 0.375 円の模型を渡し、数量 2 の成行。order events: {st['events']}")

    def scene_p7_account_swap(self, sc):
        try:
            bex.Exchange(bs.backtesting_dispatcher(), {}, account_balances=object())  # type: ignore[call-arg]
            r = "受け付けた"
        except TypeError as exc:
            r = f"TypeError: {exc}"
        return not_supported("口座(AccountBalances)は Exchange の中で作られ、差し替える口が無い(exchange.py 108 行)。"
                             f"試したこと: Exchange(..., account_balances=...) -> {r}")


C_S = 1_000_000_000
