"""Reproduction of survey candidate 52 QuantConnect LEAN (round r6-3) -- the
scene-set side: builds LEAN's input objects from a scene, runs the
reproduced data path (`opponents/repro_engines/lean52.py`), and records what
the algorithm's OnData received.

Why a reproduction: LEAN does not run in this environment (the engine is C#
on .NET net10.0, not installed; the Python CLI needs the quantconnect/lean
Docker image, 14 GB compressed; record `survey_results/attempts/52.log`).
The review table (`opponents/CONSIDERED.md`, viewpoint P0-1) had skipped it
as contained by run candidates, but LEAN carries a funding-rate type
(`MarginInterestRate`) through the same synchroniser as bars and ticks, so
the scene p1-merge-by-time (then bar, trade and funding merged by time), which
no run candidate passed in round r6-3, could be passed by LEAN: it is not
"clearly weaker" (critic br6-2-2, ROOTCAUSE_r6-3.md). Since round r7-1 the
scenes of other viewpoints than P0-3 take their types from the target's own
(the runner builds them from LEAN's types: trade, bar, funding).

Scope of the rewrite = LEAN's data path: the types TradeBar, Tick (trade)
and MarginInterestRate, the subscriptions, the frontier time, the
synchroniser, the Slice and OnData. Scenes whose mechanism is outside it
(ISO parsing, lookahead guards of history requests, scheduled events,
orders / fills / fees / portfolio and their plug points) are "error" = 結果なし:
LEAN has those mechanisms, but they are not reproduced, so there is no result
(reporting 対応なし would say LEAN lacks them). Scenes that need a type LEAN's
Slice does not have (an order book with levels, a book delta, a liquidation)
are 対応なし, with the Slice's members (Common/Data/Slice.cs 86-166).

Settings the scene set chooses through LEAN's public arguments (round r7-1):
the security is a CryptoFuture added with `fillForward: false`
(QCAlgorithm.cs 2621 AddCryptoFuture), so the subscriptions are not
internal (DataManager.cs 720-721 with AddSecurity's defaults) and carry no
fill-forward data (FileSystemDataFeed.cs 274-277); see
`repro_engines/lean52.py` for the lines.

Inputs: LEAN takes one subscription per (symbol, data type) (a subscription
has one `Configuration.Type`), so events of one scene stream are handed to
the subscription of their type, in their given order; the synchroniser
merges subscriptions by time. Values the primary source leaves open use the
source's defaults: a TradeBar's Period is `Time.OneMinute`
(TradeBar.cs 182), so a bar whose scene time is t has EndTime = t (LEAN
emits a bar at its EndTime, SubscriptionData.cs 73) and Time = t - 1 min.
Times go through `Time.UnixNanosecondTimeStampToDateTime` (100-ns ticks)
and back through `DateTimeToUnixTimeStampNanoseconds`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import Adapter, SceneResult, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from opponents.repro_engines import lean52 as L  # noqa: E402

SYM = "BTCJPY"
SLICE_MEMBERS = ("Bars", "QuoteBars", "Ticks", "OptionChains", "FuturesChains", "Splits", "Dividends", "Delistings",
                 "SymbolChangedEvents", "MarginInterestRates")
NO_TYPE = ("LEAN の Slice が戦略に渡す型の集まりは {m}(Common/Data/Slice.cs 86-166、版 856327ff)で、{k} を運ぶ型が無い"
           "(板は Tick の気配(最良の売り買い 1 段、Tick.cs 140-146)と QuoteBar だけ)。再現の Slice の欄: {have}")
NOT_REPRODUCED = ("再現の範囲外: 候補 52 は LEAN のデータの道(型・購読・frontier・同期・Slice・OnData)だけを一次資料どおりに"
                  "書き直した(opponents/repro_engines/lean52.py)。この場面の機構({what})は LEAN にあるが書き直していないので結果が無い")

KIND = {L.TradeBar: "bar", L.Tick: "trade", L.MarginInterestRate: "funding"}


def _obj(e: dict) -> L.BaseData:
    """A scene event as the LEAN data object of its type (None when LEAN has no such type)."""
    t = L.unix_ns_to_datetime(int(e["ts_ns"]))
    k = e.get("kind", "trade")
    if k == "bar":
        b = C.as_bar(e)
        return L.TradeBar(t - L.TradeBar.ONE_MINUTE, SYM, float(b["open"]), float(b["high"]), float(b["low"]),
                          float(b["close"]), float(b.get("volume", 1.0)))
    if k == "trade":
        return L.Tick(t, SYM, "", "", float(e.get("qty", 0.01)), float(e.get("price", 100.0)))
    if k == "funding":
        m = L.MarginInterestRate()  # MarginInterestRate.cs 60-65: new MarginInterestRate { Time, InterestRate = Value = rate, Symbol }
        m.Time, m.Symbol = t, SYM
        m.InterestRate = m.Value = float(e["rate"])
        return m
    return None


# round r7-1: each subscription carries its configuration as LEAN makes it for a user's security
# (DataManager.cs 720-721, via QCAlgorithm.AddSecurity with the defaults; lean52.data_manager_add):
# the data type and its TickType (TradeBar and a trade Tick: Trade; MarginInterestRate: Quote,
# DataManager.cs 763-773, SubscriptionManager.cs 361), the CryptoFuture security type.
_TICK_TYPE = {L.TradeBar: L.TickType.Trade, L.Tick: L.TickType.Trade, L.MarginInterestRate: L.TickType.Quote}


def _sources(streams: list[tuple[str, list[dict]]], reverse_ties: bool = False) -> list:
    """One subscription per data type, in the order the types first appear
    (LEAN keeps one subscription per (symbol, data type): a config equal to
    an existing one returns that config, DataManager.cs 503-525 called at 731); each
    keeps its events' given order. `reverse_ties` hands them to the collection
    in the reverse order: the order of subscriptions with the same sort key is
    not fixed by the source (lean52.sort_subscriptions)."""
    subs: dict[type, list] = {}
    for _, evs in streams:
        for e in evs:
            o = _obj(e)
            subs.setdefault(type(o), []).append(o)
    out = []
    for t, data in subs.items():
        (cfg,) = L.data_manager_add(SYM, L.SecurityType.CryptoFuture, [(t, _TICK_TYPE[t])])
        out.append(L.Subscription(data, cfg, utc_start_time=0))
    return list(reversed(out)) if reverse_ties else out


def _missing(evs: list[dict]) -> list[str]:
    return sorted({e.get("kind", "trade") for e in evs if _obj(e) is None})


def _slice_has() -> list[str]:
    s = L.time_slice_create(0, [])
    return sorted(k for k in vars(s) if not k.startswith("_"))


class _Algo(L.QCAlgorithm):
    """The scene's algorithm: OnData records each datum of the Slice with its type."""

    def __init__(self) -> None:
        super().__init__()
        self.calls, self.seen, self.car = 0, [], []

    def OnData(self, slice_):  # noqa: N802
        # round r7-1: the data of the call in the Slice's own order, Slice.AllData (Slice.cs 57 / 305 = the
        # factory's allDataForAlgorithm), not in an order of reading the typed collections chosen here
        self.calls += 1
        for d in slice_.AllData:
            self.car.append(C.carrier(d))
            self.seen.append((self.calls, d))


def _run(streams, reverse_ties: bool = False) -> _Algo:
    a = _Algo()
    L.run(a, _sources(streams, reverse_ties))
    return a


def _fields(d) -> dict:
    if isinstance(d, L.TradeBar):
        return {"open": d.Open, "high": d.High, "low": d.Low, "close": d.Close, "volume": d.Volume}
    if isinstance(d, L.Tick):
        return {"price": d.Price, "qty": d.Quantity}  # a LEAN trade tick has no side field (Tick.cs 40-172)
    if isinstance(d, L.MarginInterestRate):
        return {"rate": d.InterestRate}
    return {}


def _ns(d) -> int:
    return L.datetime_to_unix_ns(d.EndTime)


def _no_result(what: str) -> SceneResult:
    return SceneResult("error", detail=NOT_REPRODUCED.format(what=what))


class Adapter(Adapter):  # noqa: F811 - run_battery loads `Adapter` from a repro_* module
    name = "repro_lean52"

    def _seq(self, streams, reverse_ties=False):
        a = _run(streams, reverse_ties)
        return a, [[KIND[type(d)], _ns(d)] for _, d in a.seen]

    def _typed(self, sc, streams):
        evs = [e for _, s in streams for e in s]
        miss = _missing(evs)
        if miss:
            return not_supported(NO_TYPE.format(m=", ".join(SLICE_MEMBERS), k="・".join(miss), have=_slice_has()))
        a, seq = self._seq(streams)
        return ok({"sequence": seq}, f"OnData の呼び出し {a.calls} 回。各回の Slice.AllData の中身を順に記録",
                  {"carriers": a.car})

    def scene_p1_merge_by_time(self, sc):
        return self._typed(sc, C.streams_in_order(sc))

    def scene_p1_one_call_per_event(self, sc):
        return self._typed(sc, [("events", C.events(sc))])

    def scene_p1_typed_events(self, sc):
        return self._typed(sc, [("events", C.events(sc))])

    def scene_p2_iso_utc(self, sc):
        return _no_result("ISO 8601 の文字列の読み")

    scene_p2_iso_offset = scene_p2_iso_utc

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01} for e in C.events(sc)]
        a = _run([("events", evs)])
        return ok({"observed_ts_ns": [_ns(d) for _, d in a.seen]},
                  f"約定のティックで渡した。OnData {a.calls} 回で受けた Tick の時刻(DateTime は 100 ns 刻み)を ns に直した",
                  {"carriers": a.car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        evs = C.events(sc)
        miss = _missing(evs)
        if miss:
            return not_supported(NO_TYPE.format(m=", ".join(SLICE_MEMBERS), k="・".join(miss), have=_slice_has()))
        a, seq = self._seq([("events", evs)])
        f = _fields(a.seen[0][1]) if a.seen else {}
        return ok({"sequence": seq, "fields": f}, f"OnData {a.calls} 回。受けた物の欄を読んだ", {"carriers": a.car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = scene_p3_bar = _type
    scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return self._typed(sc, [("events", C.events(sc))])

    def scene_p3_clock_timer(self, sc):
        return _no_result("予定の事象(Schedule.On)")

    def scene_p3_notice_accepted(self, sc):
        return _no_result("注文と注文の事象(OnOrderEvent)")

    scene_p3_notice_rejected = scene_p3_notice_filled = scene_p3_notice_accepted

    def scene_p4_visible_at_step(self, sc):
        return _no_result("履歴の読み(History)")

    def scene_p4_received_time(self, sc):
        return _no_result("受け取りの時刻の模型")

    def scene_p4_future_read_attempt(self, sc):
        return _no_result("履歴の読み(History)と先読みの止め")

    # ---------------- P0-5 (round r7-1: the input is built from LEAN's own types by the runner)
    def _p5_once(self, sc, hand_over, reverse_ties=False):
        a, seq = self._seq([(k, sc.input["streams"][k]) for k in hand_over], reverse_ties)
        return seq, a.car, a.calls

    def scene_p5_same_time_twice(self, sc):
        evs = [e for s in sc.input["streams"].values() for e in s]
        miss = _missing(evs)
        if miss:
            return not_supported(NO_TYPE.format(m=", ".join(SLICE_MEMBERS), k="・".join(miss), have=_slice_has()))
        order, car, calls = self._p5_once(sc, sc.input["hand_over_order"])
        other, _, _ = self._p5_once(sc, sc.input["hand_over_order"], reverse_ties=True)
        return ok({"order": order}, f"型ごとの入力を 1 つずつ購読(SubscriptionDataConfig)にして渡した順に足した。OnData {calls} 回、"
                  "Slice.AllData の順を記録。購読の並べ替え(SubscriptionCollection.SortSubscriptions の鍵 SecurityType・TickType・Symbol)で"
                  f"鍵が同じ購読の順は一次資料で決まらないので、逆の順でも走らせた: {other}", {"carriers": car})

    def scene_p5_hand_over_order(self, sc):
        evs = [e for s in sc.input["streams"].values() for e in s]
        miss = _missing(evs)
        if miss:
            return not_supported(NO_TYPE.format(m=", ".join(SLICE_MEMBERS), k="・".join(miss), have=_slice_has()))
        runs, cars, others = [], [], []
        for o in sc.input["hand_over_orders"]:
            order, car, _ = self._p5_once(sc, o)
            runs.append({"hand_over": list(o), "order": order})
            cars.append(car)
            others.append(self._p5_once(sc, o, reverse_ties=True)[0])
        return ok({"form": "multi_input", "runs": runs},
                  f"{len(runs)} 通りの渡す順で購読を足し、各回の Slice.AllData の順を記録。鍵が同じ購読の順を逆にした走り: {others}",
                  {"carriers": cars})

    def scene_p5_same_stream_order(self, sc):
        a = _run([("events", C.events(sc))])
        return ok({"prices": [d.Price for _, d in a.seen]}, f"同じ時刻の約定 3 件を 1 つの Tick の購読で渡した。OnData {a.calls} 回",
                  {"carriers": a.car})

    def scene_p6_place_then_cancel(self, sc):
        return _no_result("注文・取消")

    scene_p6_cancel_notice = scene_p6_fill_seen_by_strategy = scene_p6_place_then_cancel

    def scene_p7_fill_model_swap(self, sc):
        return _no_result("約定・遅延・費用・口座の模型の口")

    scene_p7_latency_model_swap = scene_p7_cost_model_swap = scene_p7_cost_per_unit = scene_p7_account_swap = scene_p7_fill_model_swap
