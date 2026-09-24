"""Survey candidate 98 `mihircoding/limitOrderBook`, run in its own venv.

Source: GitHub `mihircoding/limitOrderBook`, commit
6cc053660c1499e4948e7fc759d8c283c9c3d3b1 (cloned 2026-09-24; not on PyPI,
SCAN 5120 行). The venv `c98` has numpy and a `.pth` pointing at the clone,
so `import src.latency` / `src.orderbook` / `src.fees` are the tool's own
modules (install record `survey_results/attempts/98.log`).

What the tool is: `src/orderbook.py` LimitOrderBook (price-time matching,
add_limit_order / add_ioc_order / add_fok_order / market_order / cancel /
depth), `src/latency.py` MessageBus ("a priority queue keyed by (arrival,
sequence)"; `send(sent_at_us, participant, action)` runs `action` at
`sent_at_us + latency(participant)`, `deliver_until(t)` runs what has
arrived, oldest first) with a per-participant `LatencyModel` (anything
with `.sample()` in microseconds), and `src/fees.py` FeeSchedule (a per-share
rate table the book does not apply; the tool's latency_study.py applies it
itself after the run).

How this adapter drives it: the MessageBus is the tool's only scheduler, so
each scene event is sent on the bus from participant "feed" (no latency) at
its time (float microseconds, the bus's time unit) with an action that calls
the scene's strategy; the book is the venue. Where the scene has a market
that our order trades against, each market trade (price p, qty q) is sent
as a resting sell of q at p from participant "market" at its time -- the
book learns about a market only through orders. The tool has no event
types, so the scenes that measure types are not supported.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402
from protocol import not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from src.fees import FeeSchedule  # noqa: E402  (the tool's modules, from the clone via a .pth)
from src.latency import LatencyModel, MessageBus  # noqa: E402
from src.order import Side  # noqa: E402
from src.orderbook import LimitOrderBook  # noqa: E402


def us(ns: int) -> float:
    return int(ns) / 1000.0


def ns(us_: float) -> int:
    """The bus's float microseconds as int ns, exactly (Fraction of the float:
    the only loss is the tool's own float, not this conversion)."""
    return round(Fraction(us_) * 1000)


def feed(bus: MessageBus, events: list[dict], on_event) -> None:
    for e in events:
        bus.send(us(e["ts_ns"]), "feed", lambda e=e: on_event(e, bus.now_us))


# The bus hands the strategy nothing but the call of an action it was given (MessageBus.send(t, participant, action)):
# the only type the tool has for what arrives is "an action" (a callable). Its class, read from the object:
ACTION = C.carrier(lambda: None)


def _attempt() -> str:
    book = LimitOrderBook()
    oid, t0 = book.add_limit_order(Side.SELL, 100.0, 100)
    trades = book.market_order(Side.BUY, 1)
    return (f"LimitOrderBook().add_limit_order(SELL, 100.0, 100) -> id {oid}; market_order(BUY, 1) -> {trades}; "
            f"LimitOrderBook の公開の名前 {[n for n in dir(LimitOrderBook) if not n.startswith('_')]}")


def _attempt_kw(cls, **kw) -> str:
    try:
        cls(**kw)
    except Exception as exc:  # noqa: BLE001
        return f"{cls.__name__}({', '.join(kw)}=...) -> {type(exc).__name__}: {str(exc)[:140]}"
    return f"{cls.__name__}({', '.join(kw)}=...) は受け付けられた"


class MihircodingLobAdapter(VectorBase):
    name = "opp_mihircoding_lob"
    what = ("この道具は照合の機関(LimitOrderBook)と、到着の順に動作を配る MessageBus と、手数料の表(FeeSchedule)で、"
            "相場の事象の型(約定・足・板・資金調達・清算)も、注文の受付・拒否・約定・取消を戦略に知らせる事象も持たない")

    def attempt(self, scene_id: str) -> str:
        return _attempt()

    # ---------------- P0-1 (the bus orders by arrival time)
    def scene_p1_one_call_per_event(self, sc):
        bus, seen = MessageBus(), []
        feed(bus, C.events(sc), lambda e, now: seen.append(["action", ns(now)]))
        bus.drain()
        return ok({"sequence": seen}, "各足を MessageBus.send(時刻 µs, 'feed', 戦略を呼ぶ動作) で積み、drain()。記録は (道具の型 = 動作(action)、bus.now_us を ns に)。"
                  "MessageBus は型の無い動作を配るだけで、足という型を持たない", {"carriers": [ACTION] * len(seen)})

    def scene_p1_merge_by_time(self, sc):
        bus, seen = MessageBus(), []
        for _, evs in C.streams_in_order(sc):
            feed(bus, evs, lambda e, now: seen.append(["action", ns(now)]))
        bus.drain()
        return ok({"sequence": seen}, "3 つの入力を渡す順に MessageBus.send で積み、drain()(bus は (到着, 積んだ順) で配る)。記録は (道具の型 = 動作(action)、時刻)",
                  {"carriers": [ACTION] * len(seen)})

    # ---------------- P0-2 (the bus's time is float microseconds)
    def _obs(self, sc):
        bus, seen = MessageBus(), []
        feed(bus, C.events(sc), lambda e, now: seen.append(ns(now)))
        bus.drain()
        return ok({"observed_ts_ns": seen}, "MessageBus の時刻は float のマイクロ秒(send の sent_at_us、bus.now_us)。ns を µs の float にして積み、"
                  "配られた時の bus.now_us を ns に戻した", {"carriers": [ACTION] * len(seen)})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _obs

    def _iso(self, sc):
        bus = MessageBus()
        try:
            bus.send(sc.input["iso"], "feed", None)
            bus.drain()
            r = f"MessageBus.send('{sc.input['iso']}', ...) は受け付けられ、bus.now_us = {bus.now_us!r}"
        except Exception as exc:  # noqa: BLE001
            r = f"MessageBus.send('{sc.input['iso']}', ...) -> {type(exc).__name__}: {str(exc)[:120]}"
        return not_supported("この道具に日時の文字列を読む変換が無い(時刻は float のマイクロ秒、注文の timestamp は通し番号)。試したこと: " + r)

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    # ---------------- P0-3 clock (the bus runs an action at a requested time)
    def scene_p3_clock_timer(self, sc):
        bus, calls, st = MessageBus(), [], {"n": 0}

        def on_event(e, now):
            st["n"] += 1
            if st["n"] == 1:
                bus.send(us(sc.input["timer_at_ns"]), "strategy", lambda: calls.append(ns(bus.now_us)))

        feed(bus, [C.as_bar(e) for e in C.events(sc)], on_event)
        bus.drain()
        return ok({"clock_calls_ns": calls}, "1 回目の動作の中で MessageBus.send(4 日後の µs, 'strategy', 起こされる動作) を積んだ。起こされた時の bus.now_us を ns に")

    # ---------------- P0-4
    def scene_p4_future_read_attempt(self, sc):
        probe, fut = sc.input["probe_at_ns"], sc.input["future_ts_ns"]
        bus, att, seen = MessageBus(), C.Attempts(), []

        def on_event(e, now):
            seen.append(float(C.as_bar(e)["close"]))
            if ns(now) != probe or att.items:
                return
            att.run("bus.pending()(まだ届いていない数)", "other", lambda: bus.pending())
            # namings: the scene's fixed list for a read that takes only an end time (the bus runs every action
            # arrived by then, so what reached the strategy's calls afterwards is what the call let through)
            C.try_time_namings(att, "bus.deliver_until(終わりの時刻 µs) を呼び、その後に戦略の呼び出しに届いた終値", "time_until",
                               lambda t: (bus.deliver_until(t), list(seen))[1], sc, us)

        feed(bus, C.events(sc), on_event)
        bus.drain()
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日に届いた動作の中で試した(戦略が持つのは bus への参照だけ。過去の事象を読む口は無い): " + att.summary())

    # ---------------- P0-5 (ties are broken by the order sent: "(arrival, sequence)")
    def _tie(self, sc, order):
        bus, seen = MessageBus(), []
        for _, evs in C.streams_in_order(sc, order):
            feed(bus, evs, lambda e, now: seen.append([e["kind"], ns(now)]))
        bus.drain()
        return seen

    def scene_p5_same_time_twice(self, sc):
        # round r6-1 (critic i0-r5-02, same root): the bus has no event types; the kinds the earlier version
        # reported were read from the scene's own dicts inside the adapter's actions, not from the tool
        got = self._tie(sc, sc.input.get("hand_over_order") or sc.input["hand_over_orders"][0])
        return not_supported("約定・足・資金調達・清算を型として持たない(MessageBus が配るのは動作(action)だけで、届いたものの型を戦略が読める物が無い)。"
                             f"試したこと: 4 つの入力を渡す順に MessageBus.send で積んで drain() -> 戦略の呼び出しの時刻 {[t for _, t in got]}"
                             f"(呼ばれた物の型は {ACTION})")

    def scene_p5_hand_over_order(self, sc):
        return self.scene_p5_same_time_twice(sc)

    def scene_p5_same_stream_order(self, sc):
        bus, seen = MessageBus(), []
        feed(bus, C.events(sc), lambda e, now: seen.append(float(e["price"])))
        bus.drain()
        return ok({"prices": seen}, "同じ時刻の約定 3 件を 1 本で MessageBus.send に積み、drain()(値は各動作が運んだもの。道具が決めるのは呼ぶ順)",
                  {"carriers": [ACTION] * len(seen)})

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        bus, book, st, out = MessageBus(), LimitOrderBook(), {"n": 0}, {}

        def on_event(e, now):
            st["n"] += 1
            if st["n"] == 1:
                st["id"], _ = book.add_limit_order(Side.BUY, 90.0, 1)
            elif st["n"] == 2:
                out["open_at_call2"] = len(book.depth(Side.BUY))
                st["cancel"] = book.cancel(st["id"])
            elif st["n"] == 3:
                out["open_at_call3"] = len(book.depth(Side.BUY))

        feed(bus, [C.as_bar(e) for e in C.events(sc)], on_event)
        bus.drain()
        return ok(out, "bus が配る動作を戦略の呼び出しにし、1 回目 add_limit_order(BUY, 90.0, 1)、2 回目 len(book.depth(BUY))(板の買いの段の数。"
                  f"注文の数を読む口は無い)と cancel(id) -> {st.get('cancel')}、3 回目 len(book.depth(BUY))。相場の約定は板に入れていない(買い 90 と交わらない)")

    def scene_p6_cancel_notice(self, sc):
        book = LimitOrderBook()
        oid, _ = book.add_limit_order(Side.BUY, 90.0, 1)
        r = book.cancel(oid)
        return not_supported(f"取消の成否は cancel(order_id) の戻り値(bool)だけで、戦略に届く事象が無い。試したこと: add_limit_order(BUY, 90.0, 1) -> id {oid}; "
                             f"cancel({oid}) -> {r}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        book = LimitOrderBook()
        book.add_limit_order(Side.SELL, 100.0, 100)
        trades = book.market_order(Side.BUY, 1)
        return not_supported("約定は market_order などの戻り値(Trade の list)で渡るだけで、あとの呼び出しで注文の約定済み数量を読む口が無い"
                             f"(公開の名前に注文の照会が無い: {[n for n in dir(LimitOrderBook) if not n.startswith('_')]})。試したこと: 売り 100@100 を置いて "
                             f"market_order(BUY, 1) -> {trades}")

    # ---------------- P0-7
    def scene_p7_latency_model_swap(self, sc):
        lat_us = 7_000.0  # the scene's plug: order latency 7 ms
        bus = MessageBus({"strategy": LatencyModel(base_us=lat_us)})
        book, st, out = LimitOrderBook(), {"n": 0}, {}

        def buy():
            trades = book.market_order(Side.BUY, 1)
            if trades:
                out.setdefault("fill_time_ns", ns(bus.now_us))
                out.setdefault("fill_price", float(trades[0].price))

        def on_event(e, now):
            book.add_limit_order(Side.SELL, float(e["price"]), int(e["qty"]))  # the market's liquidity at this trade
            st["n"] += 1
            if st["n"] == 1:
                bus.send(now, "strategy", buy)

        feed(bus, C.events(sc), on_event)
        bus.drain()
        return ok({"fill_time_ns": out.get("fill_time_ns")},
                  "MessageBus({'strategy': LatencyModel(base_us=7000)}) を差し込み、相場の約定(100@100)を届いた時刻に売りの指値として板に置き、"
                  f"1 回目(T0)に成行の買い 1 を bus.send(now, 'strategy', ...) で送った。埋まった時の bus.now_us を ns に。{out}")

    def scene_p7_fill_model_swap(self, sc):
        return not_supported("照合(値段と時刻の優先、Trade は置かれた注文の値)を差し替える口が無い。試したこと: "
                             + _attempt_kw(LimitOrderBook, fill_model=object()))

    def _fees(self, sc, what):
        book = LimitOrderBook()
        book.add_limit_order(Side.SELL, 100.0, 100)
        trades = book.market_order(Side.BUY, 2)
        return not_supported(f"{what}。FeeSchedule(name, maker, taker) は 1 株あたりの率の表で、照合(LimitOrderBook)も MessageBus も読まない"
                             "(道具の latency_study.py が走らせたあとに自分で掛けている)。約定(Trade)に費用の欄が無い。"
                             f"試したこと: FeeSchedule('x', maker=0.0, taker=-0.375) を作り、売り 100@100 に market_order(BUY, 2) -> {trades}; "
                             + _attempt_kw(LimitOrderBook, fees=FeeSchedule("x", maker=0.0, taker=-0.375)))

    def scene_p7_cost_model_swap(self, sc):
        return self._fees(sc, "約定に費用を付ける口が無い")

    def scene_p7_cost_per_unit(self, sc):
        return self._fees(sc, "約定に費用を付ける口が無い")

    def scene_p7_account_swap(self, sc):
        return not_supported("口座の物が無い(建玉・現金を持たない)。試したこと: " + _attempt_kw(LimitOrderBook, account=object()))
