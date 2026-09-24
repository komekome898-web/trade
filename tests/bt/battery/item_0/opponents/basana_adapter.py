"""Survey candidate 1 `Basana` (PyPI `basana` 1.11), run in its own venv.

Driven through its public API only: `basana.backtesting_dispatcher()`,
`basana.Event` (the documented base class for events: "There are many
different types of events: an update to an order book, a new trade, an
order update, a new bar", core/event.py) with `FifoQueueEventSource` and
`dispatcher.subscribe` for event types it has no class for, `BarEvent` /
`Bar`, `dispatcher.schedule` (timers), `dispatcher.now()`, and the
backtesting `Exchange` (orders, `subscribe_to_order_events`, and its plug
points `liquidity_strategy_factory` and `fee_strategy`).
Basana's time type is `datetime.datetime` (event `when`).
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


class Generic(bs.Event):
    """A market event of a type Basana has no class for, carried as a subclass of basana.Event."""

    def __init__(self, when, kind: str, fields: dict):
        super().__init__(when)
        self.kind = kind
        self.fields = fields


def _event(e: dict):
    when = C.ns_to_dt(e["ts_ns"])
    if e["kind"] == "bar":
        return bs.BarEvent(when, bs.Bar(when - D.timedelta(seconds=1), PAIR, Decimal(str(e["open"])), Decimal(str(e["high"])),
                                        Decimal(str(e["low"])), Decimal(str(e["close"])), Decimal(str(e["volume"])),
                                        D.timedelta(seconds=1)))
    return Generic(when, e["kind"], C.fields_of(e))


def _kind(ev) -> str:
    return "bar" if isinstance(ev, bs.BarEvent) else getattr(ev, "kind", type(ev).__name__)


def _fields(ev) -> dict:
    if isinstance(ev, bs.BarEvent):
        b = ev.bar
        return {"open": float(b.open), "high": float(b.high), "low": float(b.low), "close": float(b.close), "volume": float(b.volume)}
    return dict(ev.fields)


from stated_rules import TYPE_PRIORITY  # noqa: E402  (the setting the stated rule is written for)


def run_streams(streams: list[list[dict]], on_event=None, timer_at=None, priorities=False):
    """Each stream becomes one event source; returns records (kind, now_ns, when_ns, fields).
    `priorities=True` gives each source the documented `priority` (EventSource,
    core/event.py) by the type of its events; otherwise every source has the default."""
    disp = bs.backtesting_dispatcher()
    recs = []

    async def handler(ev):
        recs.append((_kind(ev), C.dt_to_ns(disp.now()), C.dt_to_ns(ev.when), _fields(ev)))
        if on_event:
            on_event(disp, len(recs), ev)
        if timer_at is not None and len(recs) == 1:
            async def job():
                recs.append(("clock", C.dt_to_ns(disp.now()), None, {}))
            disp.schedule(C.ns_to_dt(timer_at), job)

    for evs in streams:
        kw = {"priority": TYPE_PRIORITY[evs[0]["kind"]]} if priorities and evs else {}
        src = bs.FifoQueueEventSource(events=[_event(e) for e in evs], **kw)
        disp.subscribe(src, handler)
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
    disp = bs.backtesting_dispatcher()
    kw = {}
    if liquidity is not None:
        kw["liquidity_strategy_factory"] = liquidity
    else:
        kw["liquidity_strategy_factory"] = bliq.InfiniteLiquidity
    if fee is not None:
        kw["fee_strategy"] = fee
    ex = bex.Exchange(disp, {"JPY": Decimal(str(cash))}, default_pair_info=PAIR_INFO, **kw)
    src = bs.FifoQueueEventSource(events=[_event(b) for b in bars])
    ex.add_bar_source(src)
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

    ex.subscribe_to_bar_events(PAIR, on_bar)
    ex.subscribe_to_order_events(on_order)
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
    name = "opp_basana"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        recs = run_streams([evs for _, evs in C.streams_in_order(sc)], priorities=True)
        return ok({"sequence": [[k, now] for k, now, _, _ in recs]}, "型ごとの 3 入力を渡した順に 3 つの event source にして subscribe(priority は型ごと)")

    def scene_p1_one_call_per_event(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"sequence": [[k, now] for k, now, _, _ in recs]}, "BarEvent 5 件を 1 つの source で渡した")

    def scene_p1_typed_events(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"sequence": [[k, now] for k, now, _, _ in recs]}, "足は BarEvent、約定は basana.Event の子で 1 つの source")

    # ---------------- P0-2
    def _iso(self, sc):
        try:
            d = D.datetime.fromisoformat(sc.input["iso"])
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"datetime.fromisoformat -> {type(exc).__name__}: {exc}")
        return ok(C.dt_to_ns(d.astimezone(D.timezone.utc)),
                  f"Basana の時刻の型 datetime に標準の fromisoformat で入れた値 {d!r}(Basana 自身は ISO の変換を持たない。"
                  "付属の CSV 読みは strptime('%Y-%m-%d %H:%M:%S') で小数秒を受けない: external/common/csv/bars.py 44 行)")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01, "side": "buy"} for e in C.events(sc)]
        recs = run_streams([evs])
        return ok({"observed_ts_ns": [w for _, _, w, _ in recs]}, "約定(basana.Event の子)で渡し、ev.when を ns にした値")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"sequence": [[k, now] for k, now, _, _ in recs], "fields": recs[0][3] if recs else None},
                  "足は BarEvent、それ以外は basana.Event の子(Basana に無い型)で渡した")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"sequence": [[k, now] for k, now, _, _ in recs]}, "1 つの source で 6 種")

    def scene_p3_clock_timer(self, sc):
        evs = C.events(sc)
        recs = run_streams([evs], timer_at=sc.input["timer_at_ns"])
        return ok({"clock_calls_ns": [now for k, now, _, _ in recs if k == "clock"]}, "1 回目に dispatcher.schedule(頼む時刻, job)")

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
        out = {}
        seen = []

        def on_event(disp, n, ev):
            seen.append(ev)
            if C.dt_to_ns(disp.now()) == probe:
                out["visible_count"] = len(seen)
                out["max_visible_close"] = max(float(e.bar.close) for e in seen)

        run_streams([C.events(sc)], on_event)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(out, "Basana は戦略に履歴を渡さないので、戦略が受け取った BarEvent を戦略自身が貯めて数えた")

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
            await att.run_async("exchange.get_bid_ask(pair, 5 本目の時刻)", "time", lambda: ex.get_bid_ask(PAIR, fut))
            att.run("受け取った BarEvent の bar[1](次の足)", "position", lambda: st["bar_event"].bar[1])
            await att.run_async("exchange.get_bid_ask(pair)(今の値)", "other", lambda: ex.get_bid_ask(PAIR))

        run_exchange(C.events(sc), 1_000_000, plan)
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok(att.output(), "T0 + 4 日の呼び出しで試した: " + att.summary())

    # ---------------- P0-5
    def _tie(self, sc, order, priorities):
        streams = [evs for _, evs in C.streams_in_order(sc, order)]
        return [[k, when] for k, _now, when, _f in run_streams(streams, priorities=priorities)]

    # Basana's written same-time rule (the dispatcher's heap key and the sources'
    # `priority`) and its application are fixed in stated_rules.py and applied by
    # the runner (round r5-1, critic i0-r4-05); TYPE_PRIORITY is read from there.

    def scene_p5_same_time_twice(self, sc):
        dflt = [self._tie(sc, None, False) for _ in range(2)]
        return ok({"order": self._tie(sc, None, True)},
                  "型ごとの 4 入力を 4 つの source にし、source の priority(公開の引数)を型ごとに与えた(TYPE_PRIORITY)。"
                  f"priority を与えない既定では同時刻の並びは id(source) で決まり、2 回の並びは {dflt}")

    def scene_p5_hand_over_order(self, sc):
        runs = [{"hand_over": list(o), "order": self._tie(sc, o, True)} for o in sc.input["hand_over_orders"]]
        dflt = {repr(self._tie(sc, o, False)) for o in sc.input["hand_over_orders"]}
        return ok({"form": "multi_input", "runs": runs},
                  f"priority を型ごとに与えて 24 通りの subscribe の順で走らせた。priority を与えない既定では {len(dflt)} 通り")

    def scene_p5_same_stream_order(self, sc):
        recs = run_streams([C.events(sc)])
        return ok({"prices": [r[3].get("price") for r in recs]}, "1 つの source で同時刻の約定 3 件")

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
