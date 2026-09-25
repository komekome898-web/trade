"""Reproduction of survey candidate 52 QuantConnect LEAN (round r6-3) -- the
scene-set side: builds LEAN's input objects from a scene, runs the
reproduced data path (`opponents/repro_engines/lean52.py`), and records what
the algorithm's OnData received.

Why a reproduction: LEAN does not run in this environment (the engine is C#
on .NET net10.0, not installed; the Python CLI needs the quantconnect/lean
Docker image, 14 GB compressed; record `survey_results/attempts/52.log`).
The review table (`opponents/CONSIDERED.md`, viewpoint P0-1) had skipped it
as contained by run candidates, but LEAN carries a funding-rate type
(`MarginInterestRate`) through the same synchroniser as bars and ticks: it is
not "clearly weaker" (critic br6-2-2; the round-r6-3 record is in the git
version named by ROOTCAUSE_r6-3.md). The scenes named in
`scenes.L438_2_SCENES` take their types from the configured target's own
(the runner builds them; the record of each run says which).

Scope of the rewrite = LEAN's data path: the types TradeBar, Tick (trade)
and MarginInterestRate, the subscriptions, the frontier time, the
synchroniser, the Slice and OnData. Scenes whose mechanism is outside it
(ISO parsing, lookahead guards of history requests, scheduled events,
orders / fills / fees / portfolio and their plug points) are "error" = 結果なし:
LEAN has those mechanisms, but they are not reproduced, so there is no result
(reporting 対応なし would say LEAN lacks them). Scenes that need a type LEAN's
Slice does not have (an order book with levels, a book delta, a liquidation)
are 対応なし, with the Slice's members (Common/Data/Slice.cs 86-166).

Settings (round r8-1, critic i0-r7-03, positive definition A): the
subscriptions are no longer built by the scene set from the scene's event
types. The scene's algorithm adds its security in `Initialize` through the
public `AddCryptoFuture(ticker, resolution, market, fillForward, leverage)`
(QCAlgorithm.cs 2621), recorded with `common.configure`; LEAN's own code
(`repro_engines/lean52.py`: DataManager.Add -> LookupSubscriptionConfigDataTypes
-> LeanData.GetDataType, the user-defined universe, the universe selection)
decides the configs and makes one subscription per config. The trade type is
a `Tick` only at the Tick resolution and a `TradeBar` only at a bar
resolution (LeanData.cs 488-494); a CryptoFuture always gets a
MarginInterestRate config (DataManager.cs 770-773).

Configured targets (`CONFIGS`): the values the user chooses are the list of
resolutions passed to AddCryptoFuture in Initialize (in that order) and, for
the scenes that leave the type open, which of the configured target's types
carries them (`one_type`). Run: each resolution alone (5), and Tick together
with one bar resolution (4 x one_type trade / bar). `fillForward` is false in
all (the FillForwardEnumerator is not rewritten; for Tick it is false anyway,
SubscriptionDataConfig.cs 242); `market` and `leverage` stay at their
defaults (nothing rewritten reads them). Not run: two or more bar
resolutions in one run -- the scene's bars name no bar length, so the user
would choose which resolution's file holds them; holding them in one file
gives the run of that one resolution plus subscriptions without data, and
holding them in several delivers each bar more than once; adding a security
while the algorithm runs (not rewritten, refused by the engine).

Inputs: each config's source is the file the user placed for it: the
scene's events of that config's (data type, tick type) in the scene's order
(streams concatenated in the hand-over order). A trade is a trade Tick
(Tick.cs 283-294), a bar a TradeBar whose Period is the config's Increment
(TradeBar.cs 248: `Period = config.Increment`; SubscriptionDataConfig.cs 240),
so a bar whose scene time is t has EndTime = t (LEAN emits a bar at its
EndTime, SubscriptionData.cs 73) and Time = t - Increment; a funding rate is
a MarginInterestRate (MarginInterestRate.cs 55-62). An event no config of the
configured target takes cannot be given to it: the scene is 対応なし. Times go
through `Time.UnixNanosecondTimeStampToDateTime` (100-ns ticks) and back
through `DateTimeToUnixTimeStampNanoseconds`.
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
NOT_REPRODUCED = ("再現の範囲外: 候補 52 は LEAN のデータの道(型・購読・frontier・同期・Slice・OnData)だけを一次資料どおりに"
                  "書き直した(opponents/repro_engines/lean52.py)。この場面の機構({what})は LEAN にあるが書き直していないので結果が無い")

KIND = {L.TradeBar: "bar", L.Tick: "trade", L.MarginInterestRate: "funding"}
_R = L.Resolution
_BAR_RESOLUTIONS = (_R.Second, _R.Minute, _R.Hour, _R.Daily)


def _configs() -> dict:
    out = {_R.Tick.lower(): {"AddCryptoFuture": [_R.Tick], "one_type": "trade"}}
    for r in _BAR_RESOLUTIONS:
        out[r.lower()] = {"AddCryptoFuture": [r], "one_type": "bar"}
    for r in _BAR_RESOLUTIONS:
        for one in ("trade", "bar"):
            out[f"tick+{r.lower()}:{one}"] = {"AddCryptoFuture": [_R.Tick, r], "one_type": one}
    return out


def _takes(cfg, e: dict) -> bool:
    """Whether this config's source holds the scene event (its data type and tick type)."""
    k = e.get("kind", "trade")
    return (k == "trade" and cfg.Type is L.Tick and cfg.TickType == L.TickType.Trade) or \
        (k == "bar" and cfg.Type is L.TradeBar) or (k == "funding" and cfg.Type is L.MarginInterestRate)


def _obj(e: dict, cfg) -> L.BaseData:
    """A scene event as the LEAN data object of the config that holds it."""
    t = L.unix_ns_to_datetime(int(e["ts_ns"]))
    k = e.get("kind", "trade")
    if k == "bar":
        b = C.as_bar(e)
        return L.TradeBar(t - cfg.Increment, SYM, float(b["open"]), float(b["high"]), float(b["low"]),
                          float(b["close"]), float(b.get("volume", 1.0)), period=cfg.Increment)
    if k == "trade":
        return L.Tick(t, SYM, "", "", float(e.get("qty", 0.01)), float(e.get("price", 100.0)))
    m = L.MarginInterestRate()  # MarginInterestRate.cs 55-62: new MarginInterestRate { Time, InterestRate = Value = rate, Symbol }
    m.Time, m.Symbol = t, SYM
    m.InterestRate = m.Value = float(e["rate"])
    return m


def _as_one_type(e: dict, one: str) -> dict:
    """A scene that leaves the type open, in the configured target's `one_type`
    (the scene's notes: a bar has OHLC = its close, a trade price = the close, qty 0.01)."""
    k = e.get("kind", "trade")
    if one == "bar":
        if k == "bar":
            return dict(e)
        price = float(e.get("price", 100.0))
        return C.substitute(e, "bar", open=price, high=price, low=price, close=price, volume=1.0)
    if k == "trade":
        return dict(e, price=float(e.get("price", 100.0)), qty=float(e.get("qty", 0.01)))
    return C.substitute(e, "trade", price=float(e.get("close", 100.0)), qty=0.01, side="buy")


def _slice_has() -> list[str]:
    sl = L.time_slice_create(0, [])
    return sorted(k for k in vars(sl) if not k.startswith("_"))


class _Algo(L.QCAlgorithm):
    """The scene's algorithm: Initialize adds the security with the configured
    target's resolutions (recorded settings); OnData records each datum of the
    Slice with its type."""

    def __init__(self, resolutions: list[str]) -> None:
        super().__init__()
        self._resolutions = list(resolutions)
        self.calls, self.seen, self.car = 0, [], []

    def Initialize(self) -> None:  # noqa: N802
        for r in self._resolutions:
            C.configure(self.AddCryptoFuture, SYM, r, None, False,
                        what=f"AddCryptoFuture({SYM}, resolution={r}, market=既定, fillForward=false, leverage=既定)",
                        when="開始前", decided_from=("選ぶ値",))

    def OnData(self, slice_):  # noqa: N802
        # round r7-1: the data of the call in the Slice's own order, Slice.AllData (Slice.cs 57 / 305 = the
        # factory's allDataForAlgorithm), not in an order of reading the typed collections chosen here
        self.calls += 1
        for d in slice_.AllData:
            self.car.append(C.carrier(d))
            self.seen.append((self.calls, d))


class _NotTaken(Exception):
    pass


def _run(resolutions: list[str], evs: list[dict], reverse_ties: bool = False) -> _Algo:
    """Run LEAN with the scene's events as the configs' sources; raise _NotTaken
    naming the events no config takes."""
    a = _Algo(resolutions)
    taken: set = set()

    def reader(cfg):
        out = []
        for i, e in enumerate(evs):
            if _takes(cfg, e):
                taken.add(i)
                out.append(_obj(e, cfg))
        return out

    L.run(a, reader, reverse_ties)
    left = sorted({evs[i].get("kind", "trade") for i in range(len(evs)) if i not in taken})
    if left:
        cfgs = [f"{c.Type.__name__}/{c.TickType}/{c.Resolution}" for c in a._user_defined_universe.GetSubscriptionRequests(SYM)]
        raise _NotTaken(f"{'・'.join(left)} の事象を持てる購読が無い。AddCryptoFuture({resolutions}) から LEAN が作った購読: {cfgs}"
                        f"(DataManager.cs 747-773 / LeanData.cs 488-494)。LEAN の Slice の型の集まり: {', '.join(SLICE_MEMBERS)}"
                        f"(Common/Data/Slice.cs 86-166。板は Tick の気配(最良の売り買い 1 段、Tick.cs 140-146)と QuoteBar だけ)。"
                        f"再現の Slice の欄: {_slice_has()}")
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
    CONFIGS = {'tick': {'AddCryptoFuture': ['Tick'], 'one_type': 'trade'},
               'second': {'AddCryptoFuture': ['Second'], 'one_type': 'bar'},
               'minute': {'AddCryptoFuture': ['Minute'], 'one_type': 'bar'},
               'hour': {'AddCryptoFuture': ['Hour'], 'one_type': 'bar'},
               'daily': {'AddCryptoFuture': ['Daily'], 'one_type': 'bar'},
               'tick+second:trade': {'AddCryptoFuture': ['Tick', 'Second'], 'one_type': 'trade'},
               'tick+second:bar': {'AddCryptoFuture': ['Tick', 'Second'], 'one_type': 'bar'},
               'tick+minute:trade': {'AddCryptoFuture': ['Tick', 'Minute'], 'one_type': 'trade'},
               'tick+minute:bar': {'AddCryptoFuture': ['Tick', 'Minute'], 'one_type': 'bar'},
               'tick+hour:trade': {'AddCryptoFuture': ['Tick', 'Hour'], 'one_type': 'trade'},
               'tick+hour:bar': {'AddCryptoFuture': ['Tick', 'Hour'], 'one_type': 'bar'},
               'tick+daily:trade': {'AddCryptoFuture': ['Tick', 'Daily'], 'one_type': 'trade'},
               'tick+daily:bar': {'AddCryptoFuture': ['Tick', 'Daily'], 'one_type': 'bar'}}

    def __init__(self, config: str = "tick") -> None:
        super().__init__(config or "tick")
        assert self.CONFIGS == _configs(), "CONFIGS must be the list _configs() makes"

    @property
    def _res(self) -> list[str]:
        return self.choose["AddCryptoFuture"]

    def _go(self, evs, reverse_ties=False):
        a = _run(self._res, evs, reverse_ties)
        return a, [[KIND[type(d)], _ns(d)] for _, d in a.seen]

    def _typed(self, sc, evs):
        try:
            a, seq = self._go(evs)
        except _NotTaken as e:
            return not_supported(str(e))
        return ok({"sequence": seq}, f"AddCryptoFuture({self._res})。OnData の呼び出し {a.calls} 回。各回の Slice.AllData の中身を順に記録",
                  {"carriers": a.car})

    def _one(self, sc):
        return [_as_one_type(e, self.choose["one_type"]) for e in C.events(sc)]

    def scene_p1_merge_by_time(self, sc):
        return self._typed(sc, C.concatenated(sc))

    def scene_p1_one_call_per_event(self, sc):
        return self._typed(sc, self._one(sc))

    def scene_p1_typed_events(self, sc):
        return self._typed(sc, C.events(sc))

    def scene_p2_iso_utc(self, sc):
        return _no_result("ISO 8601 の文字列の読み")

    scene_p2_iso_offset = scene_p2_iso_utc

    def _ts(self, sc):
        evs = [_as_one_type(C.substitute(e, "trade", price=100.0, qty=0.01), self.choose["one_type"])
               for e in C.events(sc)]
        try:
            a, _ = self._go(evs)
        except _NotTaken as e:
            return not_supported(str(e))
        return ok({"observed_ts_ns": [_ns(d) for _, d in a.seen]},
                  f"AddCryptoFuture({self._res})。{self.choose['one_type']} で渡した。OnData {a.calls} 回で受けた物の時刻"
                  "(DateTime は 100 ns 刻み)を ns に直した", {"carriers": a.car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    def _type(self, sc):
        try:
            a, seq = self._go(C.events(sc))
        except _NotTaken as e:
            return not_supported(str(e))
        f = _fields(a.seen[0][1]) if a.seen else {}
        return ok({"sequence": seq, "fields": f}, f"AddCryptoFuture({self._res})。OnData {a.calls} 回。受けた物の欄を読んだ",
                  {"carriers": a.car})

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = scene_p3_bar = _type
    scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        return self._typed(sc, C.events(sc))

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

    # ---------------- P0-5 (the input is built from the configured target's own types by the runner)
    def _p5_once(self, sc, hand_over, reverse_ties=False):
        a, seq = self._go(C.concatenated(sc, list(hand_over)), reverse_ties)
        return seq, a.car, a.calls

    def scene_p5_same_time_twice(self, sc):
        try:
            order, car, calls = self._p5_once(sc, sc.input["hand_over_order"])
            other, _, _ = self._p5_once(sc, sc.input["hand_over_order"], reverse_ties=True)
        except _NotTaken as e:
            return not_supported(str(e))
        return ok({"order": order}, f"AddCryptoFuture({self._res})。各入力の事象をその型の購読の源に、渡した順に書いた。OnData {calls} 回、"
                  "Slice.AllData の順を記録。購読の並べ替え(SubscriptionCollection.SortSubscriptions の鍵 SecurityType・TickType・Symbol)で"
                  f"鍵が同じ購読の順は一次資料で決まらないので、逆の順でも走らせた: {other}", {"carriers": car})

    def scene_p5_hand_over_order(self, sc):
        runs, cars, others = [], [], []
        try:
            for o in sc.input["hand_over_orders"]:
                order, car, _ = self._p5_once(sc, o)
                runs.append({"hand_over": list(o), "order": order})
                cars.append(car)
                others.append(self._p5_once(sc, o, reverse_ties=True)[0])
        except _NotTaken as e:
            return not_supported(str(e))
        return ok({"form": "multi_input", "runs": runs},
                  f"AddCryptoFuture({self._res})。{len(runs)} 通りの渡す順で、各入力の事象をその型の購読の源に書いた。"
                  f"各回の Slice.AllData の順を記録。鍵が同じ購読の順を逆にした走り: {others}",
                  {"carriers": cars})

    def scene_p5_same_stream_order(self, sc):
        try:
            a, _ = self._go(self._one(sc))
        except _NotTaken as e:
            return not_supported(str(e))
        return ok({"prices": [d.Price if isinstance(d, L.Tick) else d.Close for _, d in a.seen]},
                  f"AddCryptoFuture({self._res})。同じ時刻の 3 件を {self.choose['one_type']} の 1 つの購読で渡した。OnData {a.calls} 回",
                  {"carriers": a.car})

    def scene_p6_place_then_cancel(self, sc):
        return _no_result("注文・取消")

    scene_p6_cancel_notice = scene_p6_fill_seen_by_strategy = scene_p6_place_then_cancel

    def scene_p7_fill_model_swap(self, sc):
        return _no_result("約定・遅延・費用・口座の模型の口")

    scene_p7_latency_model_swap = scene_p7_cost_model_swap = scene_p7_cost_per_unit = scene_p7_account_swap = scene_p7_fill_model_swap
