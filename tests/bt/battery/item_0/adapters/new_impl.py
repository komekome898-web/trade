"""Adapter for the new implementation (`src/bot/bt/core/`), item-0 battery.

Written by the materials person (not the scene keeper, not the worker).
Round 3: re-read against the round-3 core (`src/bot/bt/core/`); the public
names used below all still exist there, and a cancel still gets exactly one
venue answer from `_ArrivalFill.on_cancel` (the round-3 core requires that).
Round r4-1 (the scene keeper, because the scene outputs changed): the scenes
p4-future-read-attempt, p5-same-time-twice, p5-hand-over-order and
p7-cost-per-unit now report raw observations (each read and its exception;
the delivered order and the core's written same-time rule with its hand
application) and the runner grades them; the materials person re-reads this.
Round 4 (materials person): re-read against the round-4 core. History reads
now return `DeliveredEvents` (window.py), whose index and slice forms have
their own position rule, so p4-future-read-attempt also tries the slice
forms that start or end at the position after the newest ([4:5], [3:5],
[4:]) and the index on the typed read. Nothing else changed.
Round r5-1 (scene keeper): the P0-5 rule and its application moved to
stated_rules.py / run_battery.py; the P0-5 scenes here return only the
delivered order (the shape changed, nothing else; the materials person
re-reads this).
Round 5 (materials person): re-read against the round-5 core. The public
names used here all still exist (`CoreEngine` keeps its positional
sockets; `time_span_ns` is a new optional keyword, not passed here, so the
run is the same as before). History reads now check each slice bound by
its role (`POSITION_RULE`, window.py), so p4-future-read-attempt also
tries the remaining forms that name the position after the newest as a
bound of each role: a forward start with a step ([4::2]), an empty forward
slice starting there ([4:4]), a backward start ([4::-1]) and a backward
stop ([:4:-1]). Nothing else changed.
The engine is reached ONLY through the `core` object handed to
`make_adapter(core)` (protocol.py): no `import bot.bt.core...` here, so the
canary (`mutant.py`) can hand over a wrapped `core`.

What this adapter uses of the target, all public names of `bot.bt.core`:
  * `CoreEngine(strategy, events, fill_model, latency_model, cost_model,
    account)` and `.run()`; `events` is one iterable or a mapping of named
    streams (the scene's own grouping and hand-over order are kept; the
    adapter never sorts, merges or drops events);
  * `Strategy.on_event(event, ctx)` and `StrategyContext` (`now_ns`,
    `visible_events`, `last`, `order`, `open_orders`, `place_order`,
    `cancel_order`, `set_timer`);
  * the event classes and `EventType`; `to_nanos(value, "iso")`;
  * `OrderRequest`; the venue reports `Ack` / `Fill` / `Canceled` /
    `Reject`; `NullCostModel`; `ZeroLatency` (as the latency socket).

The core has no venue model of its own (a fill model is item 3's job; the
core ships `NullFillModel`, which never fills). Scenes whose strategy
trades therefore plug a small fill model, written here against the public
`FillModel` socket, as the scenes allow ("対象の公開の差し込み口"):
`_ArrivalFill` fills a market order in full at the last trade / bar price
the venue has seen when the order arrives, rests a limit order and fills it
only when a later trade crosses its price, and cancels live orders on
request. The same is done for the account socket (`_CashAccount`: cash
check without leverage) where a scene states an account. No attribute of
the target is assigned and none of its files is edited.

Call numbering: in scenes that say "1 回目 / 2 回目 / 3 回目の呼び出し", the
count is over calls for market-data events (the scene's input events);
calls for order notices and timers are recorded separately. `detail` says
so per scene.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from protocol import Adapter, SceneResult, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

# scene vocabulary <- engine field name, per event kind
_FIELD_NAMES = {
    "trade": {"price": "price", "qty": "size", "side": "side"},
    "book_snapshot": {"bids": "bids", "asks": "asks"},
    "book_delta": {"side": "side", "price": "price", "qty": "size"},
    "bar": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
    "funding": {"rate": "rate"},
    "liquidation": {"price": "price", "qty": "size", "side": "side"},
}
_NOTICE_WORD = {
    "ORDER_ACK": "accepted",
    "ORDER_REJECT": "rejected",
    "ORDER_FILL": "filled",
    "ORDER_CANCELED": "canceled",
    "ORDER_STATE_UNKNOWN": "state_unknown",
}


def _plain(v: Any) -> Any:
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    return v


def _kind(event) -> str:
    return event.EVENT_TYPE.value.lower()


class NewImplAdapter(Adapter):
    name = "new_impl"

    def __init__(self, core) -> None:
        self.core = core

    # ------------------------------------------------------------ helpers
    def _event(self, d: dict):
        """Scene dict -> the target's event object (field names translated)."""
        core = self.core
        kind = d.get("kind", "trade")
        common = {"exchange_time_ns": int(d["ts_ns"]), "received_time_ns": int(d.get("recv_ns", d["ts_ns"]))}
        if kind == "trade":
            return core.TradeEvent(price=d["price"], size=d["qty"], side=d["side"], **common)
        if kind == "book_snapshot":
            return core.BookSnapshotEvent(bids=tuple(tuple(x) for x in d["bids"]),
                                          asks=tuple(tuple(x) for x in d["asks"]), **common)
        if kind == "book_delta":
            return core.BookDeltaEvent(side=d["side"], price=d["price"], size=d["qty"], **common)
        if kind == "bar":
            return core.BarEvent(open=d["open"], high=d["high"], low=d["low"], close=d["close"],
                                 volume=d["volume"], **common)
        if kind == "funding":
            return core.FundingEvent(rate=d["rate"], **common)
        if kind == "liquidation":
            return core.LiquidationEvent(price=d["price"], size=d["qty"], side=d["side"], **common)
        raise ValueError(f"unknown scene event kind {kind!r}")

    def _events(self, dicts: list[dict]) -> list:
        return [self._event(d) for d in dicts]

    def _streams(self, sc, order: Optional[list[str]] = None) -> dict:
        """The scene's named streams, as a mapping built in the hand-over order."""
        return {name: self._events(evs) for name, evs in C.streams_in_order(sc, order)}

    def _strategy(self, fn: Callable[[Any, Any, dict], None]):
        """A Strategy subclass calling fn(event, ctx, state); `state` counts
        market-data calls in state['n'] and keeps everything the strategy records."""
        core = self.core
        market = set(core.MARKET_EVENT_TYPES)

        class _S(core.Strategy):
            def __init__(self) -> None:
                self.state: dict = {"n": 0, "seq": [], "carriers": [], "notices": [], "clock": [], "fills": []}

            def on_event(self, event, ctx) -> None:
                st = self.state
                st["seq"].append([_kind(event), int(event.exchange_time_ns)])
                st["carriers"].append(C.carrier(event))
                if event.EVENT_TYPE in market:
                    st["n"] += 1
                word = _NOTICE_WORD.get(event.EVENT_TYPE.value)
                if word is not None:
                    st["notices"].append(word)
                if event.EVENT_TYPE is core.EventType.ORDER_FILL:
                    st["fills"].append({"price": float(event.price), "size": float(event.size),
                                        "fee": float(event.fee), "venue_time_ns": int(event.exchange_time_ns),
                                        "received_time_ns": int(event.received_time_ns)})
                if event.EVENT_TYPE is core.EventType.CLOCK:
                    st["clock"].append(int(ctx.now_ns))
                fn(event, ctx, st)

        return _S()

    def _run(self, fn, events, *, fill_model=None, latency_model=None, cost_model=None, account=None):
        strat = self._strategy(fn)
        engine = self.core.CoreEngine(strat, events, fill_model, latency_model, cost_model, account)
        res = engine.run()
        return strat.state, res

    def _market_call(self, event, st, n: int) -> bool:
        return event.EVENT_TYPE in set(self.core.MARKET_EVENT_TYPES) and st["n"] == n

    # -- plug-ins written against the public sockets --------------------
    def _arrival_fill(self, fixed_price: Optional[float] = None):
        core = self.core

        class _ArrivalFill:
            """Market: fills in full at arrival at `fixed_price` or the last
            trade/bar price the venue has seen. Limit: rests; fills in full
            when a later trade crosses its price. Cancels succeed."""

            def __init__(self) -> None:
                self.last: Optional[float] = None
                self.resting: dict[str, Any] = {}

            def on_market_event(self, event, venue_time_ns):
                out = []
                if event.EVENT_TYPE is core.EventType.TRADE:
                    self.last = event.price
                    for coid, o in list(self.resting.items()):
                        crosses = event.price <= o.price if o.side == "buy" else event.price >= o.price
                        if crosses:
                            out.append(core.Fill(coid, o.price, o.size, "maker"))
                            del self.resting[coid]
                elif event.EVENT_TYPE is core.EventType.BAR:
                    self.last = event.close
                return out

            def on_order(self, order, venue_time_ns):
                coid = order.client_order_id
                if order.order_type == "market":
                    price = fixed_price if fixed_price is not None else self.last
                    if price is None:
                        return [core.Reject(coid, "no_price")]
                    return [core.Ack(coid, "v-" + coid), core.Fill(coid, price, order.size, "taker")]
                self.resting[coid] = order
                return [core.Ack(coid, "v-" + coid)]

            def on_cancel(self, request, venue_time_ns):
                self.resting.pop(request.client_order_id, None)
                return [core.Canceled(request.client_order_id)]

        return _ArrivalFill()

    def _cash_account(self, cash: float):
        core = self.core

        class _CashAccount:
            """Cash only, no leverage: a buy whose price x size exceeds the
            cash left is rejected when it reaches the venue."""

            def __init__(self) -> None:
                self.cash = float(cash)
                self.last: Optional[float] = None

            def apply_fill(self, fill) -> None:
                sign = -1.0 if fill.side == "buy" else 1.0
                self.cash += sign * fill.price * fill.size - fill.fee

            def apply_funding(self, event) -> None:
                return None

            def apply_liquidation(self, event) -> None:
                return None

            def on_market_event(self, event, venue_time_ns):
                if event.EVENT_TYPE is core.EventType.TRADE:
                    self.last = event.price
                return ()

            def check_order(self, order, venue_time_ns):
                price = order.price if order.price is not None else self.last
                if order.side == "buy" and price is not None and price * order.size > self.cash:
                    return f"insufficient_cash: need {price * order.size}, have {self.cash}"
                return None

        return _CashAccount()

    def _buy_market_at_first_call(self, sc, size: float = 1.0, **kw):
        core = self.core

        def fn(event, ctx, st):
            if self._market_call(event, st, 1) and "coid" not in st:
                st["coid"] = ctx.place_order(core.OrderRequest(side="buy", order_type="market", size=size))

        return self._run(fn, self._events(C.events(sc)), **kw)

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        st, _ = self._run(lambda e, c, s: None, self._streams(sc))
        return ok({"sequence": st["seq"]}, f"{len(sc.input['streams'])} つの入力を名前つきの流れ(辞書、渡した順に作成)で CoreEngine に渡し、"
                  "on_event の各呼び出しで(型, exchange_time_ns)を記録", {"carriers": st["carriers"]})

    def scene_p1_one_call_per_event(self, sc):
        st, _ = self._run(lambda e, c, s: None, self._events(C.events(sc)))
        return ok({"sequence": st["seq"]}, f"{len(C.events(sc))} 件を場面の型のまま 1 本の入力で渡し、on_event の各呼び出しで(型, exchange_time_ns)を記録",
                  {"carriers": st["carriers"]})

    def scene_p1_typed_events(self, sc):
        st, _ = self._run(lambda e, c, s: None, self._events(C.events(sc)))
        return ok({"sequence": st["seq"]}, "型の違う 2 件を 1 本の入力で渡し、戦略が event.EVENT_TYPE で型を判別して記録",
                  {"carriers": st["carriers"]})

    # ---------------- P0-2
    def scene_p2_iso_utc(self, sc):
        return ok(int(self.core.to_nanos(sc.input["iso"], "iso")), "core.to_nanos(iso, 'iso')",
                  {"reader": C.qualname(self.core.to_nanos)})

    def scene_p2_iso_offset(self, sc):
        return ok(int(self.core.to_nanos(sc.input["iso"], "iso")), "core.to_nanos(iso, 'iso')",
                  {"reader": C.qualname(self.core.to_nanos)})

    def _ts_scene(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01, "side": "buy"} for e in C.events(sc)]
        seen: list[int] = []
        carriers: list[str] = []

        def fn(e, c, s):
            seen.append(int(e.exchange_time_ns))
            carriers.append(C.carrier(e))

        self._run(fn, self._events(evs))
        return ok({"observed_ts_ns": seen}, "約定(価格 100.0 数量 0.01)で渡し、on_event で event.exchange_time_ns を記録",
                  {"carriers": carriers})

    def scene_p2_event_time_exact(self, sc):
        return self._ts_scene(sc)

    def scene_p2_one_ns_apart(self, sc):
        return self._ts_scene(sc)

    # ---------------- P0-3
    def _type_scene(self, sc):
        d = C.events(sc)[0]
        kind = d["kind"]
        got: dict = {}

        def fn(event, ctx, st):
            if not got:
                got.update({scene_name: _plain(getattr(event, attr)) for scene_name, attr in _FIELD_NAMES[kind].items()})

        st, _ = self._run(fn, self._events([d]))
        return ok({"sequence": st["seq"], "fields": got},
                  f"「{kind}」1 件を渡し、on_event で受け取った事象の型・時刻・中身(欄名は場面の語に読み替え)を記録",
                  {"carriers": st["carriers"]})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type_scene
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type_scene

    def scene_p3_mixed_one_run(self, sc):
        st, _ = self._run(lambda e, c, s: None, self._events(C.events(sc)))
        return ok({"sequence": st["seq"]}, "6 種を 1 本の入力で渡し、on_event の各呼び出しで(型, exchange_time_ns)を記録",
                  {"carriers": st["carriers"]})

    def scene_p3_clock_timer(self, sc):
        at = int(sc.input["timer_at_ns"])

        def fn(event, ctx, st):
            if self._market_call(event, st, 1) and not st.get("asked"):
                st["asked"] = True
                ctx.set_timer(at, "wake")

        st, _ = self._run(fn, self._events(C.events(sc)))
        return ok({"clock_calls_ns": st["clock"]}, "1 回目の呼び出しで ctx.set_timer(T0 + 4 日) を呼び、CLOCK の呼び出しの ctx.now_ns を記録")

    def scene_p3_notice_accepted(self, sc):
        core = self.core

        def fn(event, ctx, st):
            if self._market_call(event, st, 1) and "coid" not in st:
                st["coid"] = ctx.place_order(core.OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))

        st, _ = self._run(fn, self._events(C.events(sc)), fill_model=self._arrival_fill(),
                          cost_model=core.NullCostModel())
        return ok({"notices": st["notices"]}, "1 回目(市場の事象の呼び出しで数える)に指値 買い 1 @90 を place_order。"
                  "約定の模型は公開の FillModel の口に差した _ArrivalFill(本ファイル)。戦略に届いた注文の通知の種類を記録")

    def scene_p3_notice_rejected(self, sc):
        core = self.core
        st, _ = self._buy_market_at_first_call(sc, fill_model=self._arrival_fill(), cost_model=core.NullCostModel(),
                                               account=self._cash_account(1_000.0))
        return ok({"notices": st["notices"]}, "口座の口に現金 1,000 円・レバレッジ無しの _CashAccount(本ファイル)を差し、"
                  "1 回目に成行 買い 1 を place_order。戦略に届いた通知の種類を記録")

    def scene_p3_notice_filled(self, sc):
        core = self.core
        st, _ = self._buy_market_at_first_call(sc, fill_model=self._arrival_fill(), cost_model=core.NullCostModel(),
                                               account=self._cash_account(1_000_000.0))
        return ok({"filled_qty_in_notices": float(sum(f["size"] for f in st["fills"])), "fills": st["fills"]},
                  "現金 1,000,000 円の _CashAccount と _ArrivalFill を差し、1 回目に成行 買い 1。戦略に届いた ORDER_FILL の数量の合計")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = int(sc.input["probe_at_ns"])
        reads = C.Reads()

        def fn(event, ctx, st):
            if int(ctx.now_ns) == probe and not reads.items:
                reads.read("ctx.visible_events() の close", lambda: [e.close for e in ctx.visible_events()])

        self._run(fn, self._events(C.events(sc)))
        if not reads.items:
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(reads.output(), "T0 + 4 日の呼び出しで ctx.visible_events() を読んだ件数と close の最大", reads.provenance())

    def scene_p4_received_time(self, sc):
        day = 86_400 * 1_000_000_000
        t0 = min(int(e["ts_ns"]) for e in C.events(sc)) - day
        out: dict = {}

        def seen101(ctx) -> bool:
            return any(getattr(e, "price", None) == 101.0 for e in ctx.visible_events())

        def fn(event, ctx, st):
            now = int(ctx.now_ns)
            if getattr(event, "price", None) == 101.0 and event.EVENT_TYPE is self.core.EventType.TRADE:
                out["price101_delivered_at_ns"] = now
            if now == t0 + 2 * day:
                out["price101_visible_at_day2"] = seen101(ctx)
            if now == t0 + 4 * day:
                out["price101_visible_at_day4"] = seen101(ctx)

        self._run(fn, self._events(C.events(sc)))
        return ok(out, "受け取れる時刻は received_time_ns、取引所の時刻は exchange_time_ns として事象を作り 1 本の入力で渡した。"
                  "2 日後と 4 日後の呼び出しで ctx.visible_events() に 101 があるか、101 が届いた呼び出しの ctx.now_ns")

    def scene_p4_future_read_attempt(self, sc):
        core = self.core
        probe = int(sc.input["probe_at_ns"])
        att = C.Attempts()
        close = (lambda e: e.close)

        def fn(event, ctx, st):
            if int(ctx.now_ns) != probe or att.items:
                return
            # the namings are the fixed list of the scene (common.try_*_namings); this adapter names the means only
            C.try_time_namings(att, "ctx.visible_events(until_ns=…)", "time_until",
                               lambda t: [e.close for e in ctx.visible_events(until_ns=t)], sc)
            C.try_time_namings(att, "ctx.visible_events(since_ns=…)", "time_since",
                               lambda t: [e.close for e in ctx.visible_events(since_ns=t)], sc)
            n = len(ctx.visible_events())
            C.try_position_namings(att, "ctx.visible_events()", lambda: ctx.visible_events(), n, close)
            nb = len(ctx.visible_events(core.EventType.BAR))
            C.try_position_namings(att, "ctx.visible_events(BAR)", lambda: ctx.visible_events(core.EventType.BAR), nb, close)
            att.run("ctx.visible_events(BAR) の全部", "other", lambda: [e.close for e in ctx.visible_events(core.EventType.BAR)])
            att.run("ctx.last(BAR)", "other", lambda: ctx.last(core.EventType.BAR).close)

        self._run(fn, self._events(C.events(sc)))
        if not att.items:
            return not_supported("T0 + 4 日の呼び出しが無かった")
        return ok(att.output(), "T0 + 4 日の呼び出しの中で試した: " + att.summary())

    # ---------------- P0-5
    # The core's same-time rule is not written here: the scene keeper copied
    # it into stated_rules.py (by name, ORDERING_RULE["source_merge"]) and the
    # runner applies it (round r5-1, critic i0-r4-05). This adapter only
    # records the delivered order.
    def _order_of(self, sc, order=None) -> tuple[list, list]:
        st, _ = self._run(lambda e, c, s: None, self._streams(sc, order))
        return [[k, t] for k, t in st["seq"]], list(st["carriers"])

    def scene_p5_same_time_twice(self, sc):
        order, carriers = self._order_of(sc)
        return ok({"order": order},
                  f"{len(sc.input['streams'])} つの名前つきの流れを渡した順で辞書にして CoreEngine に渡し、戦略に届いた(型, exchange_time_ns)を記録",
                  {"carriers": carriers})

    def scene_p5_hand_over_order(self, sc):
        got = [(list(o), *self._order_of(sc, o)) for o in sc.input["hand_over_orders"]]
        runs = [{"hand_over": h, "order": order} for h, order, _ in got]
        return ok({"form": "multi_input", "runs": runs},
                  f"{len(runs)} 通りの渡す順で名前つきの流れの辞書を作って {len(runs)} 回走らせ、各回の(型, 時刻)の列を記録",
                  {"carriers": [c for _, _, c in got]})

    def scene_p5_same_stream_order(self, sc):
        prices: list[float] = []
        carriers: list[str] = []

        def fn(e, c, s):
            prices.append(float(e.price))
            carriers.append(C.carrier(e))

        self._run(fn, self._events(C.events(sc)))
        return ok({"prices": prices}, "同時刻の約定 3 件を 1 本の入力で渡し、on_event で価格を記録", {"carriers": carriers})

    # ---------------- P0-6
    def _place_then_cancel(self, sc):
        core = self.core

        def fn(event, ctx, st):
            if event.EVENT_TYPE not in set(core.MARKET_EVENT_TYPES):
                return
            if st["n"] == 1 and "coid" not in st:
                st["coid"] = ctx.place_order(core.OrderRequest(side="buy", order_type="limit", size=1.0, price=90.0))
            elif st["n"] == 2:
                st["open_at_call2"] = len(ctx.open_orders())
                ctx.cancel_order(st["coid"])
            elif st["n"] == 3:
                st["open_at_call3"] = len(ctx.open_orders())

        st, _ = self._run(fn, self._events(C.events(sc)), fill_model=self._arrival_fill(),
                          cost_model=core.NullCostModel())
        return st

    def scene_p6_place_then_cancel(self, sc):
        st = self._place_then_cancel(sc)
        return ok({"open_at_call2": st.get("open_at_call2"), "open_at_call3": st.get("open_at_call3")},
                  "市場の事象の呼び出しで数えて 1 回目に指値 買い 1 @90、2 回目に len(ctx.open_orders()) を記録して ctx.cancel_order、"
                  "3 回目に len(ctx.open_orders())。約定の模型は _ArrivalFill(本ファイル)")

    def scene_p6_cancel_notice(self, sc):
        st = self._place_then_cancel(sc)
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]},
                  "p6-place-then-cancel と同じ手順で、戦略に届いた注文の通知の種類を記録(ORDER_CANCELED があるか)")

    def scene_p6_fill_seen_by_strategy(self, sc):
        core = self.core

        def fn(event, ctx, st):
            if event.EVENT_TYPE not in set(core.MARKET_EVENT_TYPES):
                return
            if st["n"] == 1 and "coid" not in st:
                st["coid"] = ctx.place_order(core.OrderRequest(side="buy", order_type="market", size=1.0))
            elif st["n"] == 3:
                st["filled_at_call3"] = float(ctx.order(st["coid"]).filled_size)

        st, _ = self._run(fn, self._events(C.events(sc)), fill_model=self._arrival_fill(),
                          cost_model=core.NullCostModel(), account=self._cash_account(1_000_000.0))
        return ok({"filled_qty_at_call3": st.get("filled_at_call3")},
                  "1 回目に成行 買い 1、3 回目に ctx.order(id).filled_size を読んだ(_ArrivalFill と現金 1,000,000 円の _CashAccount)")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        core = self.core
        st, _ = self._buy_market_at_first_call(sc, fill_model=self._arrival_fill(fixed_price=12345.0),
                                               cost_model=core.NullCostModel(), account=self._cash_account(100_000.0))
        price = st["fills"][0]["price"] if st["fills"] else None
        return ok({"fill_price": price, "notices": st["notices"]},
                  "fill_model の口に、届いた成行をその場で全量 12345.0 で埋める模型を差し、戦略に届いた ORDER_FILL の価格を記録")

    def scene_p7_latency_model_swap(self, sc):
        core = self.core

        class _OrderDelay7ms(core.ZeroLatency):
            def order_delay_ns(self, order, sent_time_ns):
                return 7_000_000

        st, _ = self._buy_market_at_first_call(sc, fill_model=self._arrival_fill(), latency_model=_OrderDelay7ms(),
                                               cost_model=core.NullCostModel(), account=self._cash_account(100_000.0))
        t = st["fills"][0]["venue_time_ns"] if st["fills"] else None
        return ok({"fill_time_ns": t, "fills": st["fills"]},
                  "latency_model の口に発注の遅れ 7 ms(ほかは 0。ZeroLatency の子)を差し、約定の模型は着いた時点で埋める _ArrivalFill。"
                  "戦略に届いた ORDER_FILL の exchange_time_ns(取引所で埋まった時刻)を記録")

    def _fee(self, sc, cost_model, size: float = 1.0):
        st, _ = self._buy_market_at_first_call(sc, size=size, fill_model=self._arrival_fill(), cost_model=cost_model,
                                               account=self._cash_account(100_000.0))
        fee = sum(f["fee"] for f in st["fills"]) if st["fills"] else None
        return ok({"fee": fee, "fills": st["fills"]}, "cost_model の口に模型を差し、戦略に届いた ORDER_FILL の fee の合計を記録")

    def scene_p7_cost_model_swap(self, sc):
        class _PerFill:
            def cost(self, fill) -> float:
                return 0.5

        return self._fee(sc, _PerFill())

    def scene_p7_cost_per_unit(self, sc):
        class _PerUnit:
            def cost(self, fill) -> float:
                return 0.375 * float(fill.size)

        return self._fee(sc, _PerUnit(), size=2.0)

    def scene_p7_account_swap(self, sc):
        core = self.core

        class _RecordFills:
            def __init__(self) -> None:
                self.qty: list[float] = []

            def apply_fill(self, fill) -> None:
                self.qty.append(float(fill.size))

            def apply_funding(self, event) -> None:
                return None

            def apply_liquidation(self, event) -> None:
                return None

            def on_market_event(self, event, venue_time_ns):
                return ()

            def check_order(self, order, venue_time_ns):
                return None

        acct = _RecordFills()
        self._buy_market_at_first_call(sc, fill_model=self._arrival_fill(), cost_model=core.NullCostModel(), account=acct)
        return ok({"account_recorded_fill_qty": acct.qty}, "account の口に、渡された約定の数量を記録するだけの口座を差した")


def make_adapter(core) -> Adapter:
    return NewImplAdapter(core)
