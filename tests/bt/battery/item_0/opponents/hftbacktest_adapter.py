"""Survey candidate 23 `hftbacktest` (PyPI `hftbacktest` 2.4.4), run in its own
venv. Driven only through its public Python API: `BacktestAsset` (data,
latency, fee, queue and exchange presets), `HashMapMarketDepthBacktest`,
`wait_next_feed` / `elapse` (the strategy's loop), `last_trades`, `depth`,
`orders`, `state_values`, `submit_*_order`, `cancel`, and the documented data
preparation `hftbacktest.data.validation.correct_event_order` /
`validate_event_order` (its data format requires rows ordered by exchange
and by local time; see https://hftbacktest.readthedocs.io/en/latest/data.html).

The strategy is the loop: each return of `wait_next_feed(include_order_resp=True)`
is one call; what the strategy saw is recorded there.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import numpy as np  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

import hftbacktest as H  # noqa: E402
from hftbacktest import (BUY_EVENT, DEPTH_EVENT, DEPTH_SNAPSHOT_EVENT, EXCH_EVENT, LOCAL_EVENT,  # noqa: E402
                         SELL_EVENT, TRADE_EVENT)
from hftbacktest.data.validation import correct_event_order, validate_event_order  # noqa: E402
from hftbacktest.order import CANCELED, EXPIRED, FILLED, GTC, LIMIT, MARKET, NEW  # noqa: E402

BOTH = EXCH_EVENT | LOCAL_EVENT
NOFLAG = 0  # rows are built without EXCH/LOCAL flags; correct_event_order adds them
TICK = 0.5
UNKNOWN_KIND_CODE = 99  # not one of the documented event codes in hftbacktest/types.py
STATUS = {NEW: "accepted", FILLED: "filled", CANCELED: "canceled", EXPIRED: "expired"}


def _rows(evs: list[dict]) -> list[tuple]:
    out = []
    for e in evs:
        k, ex, lo = e["kind"], int(e["ts_ns"]), C.recv(e)
        if k == "trade":
            out.append((NOFLAG | TRADE_EVENT | (BUY_EVENT if e["side"] == "buy" else SELL_EVENT), ex, lo, e["price"], e["qty"]))
        elif k == "book_snapshot":
            for p, q in e["bids"]:
                out.append((NOFLAG | DEPTH_SNAPSHOT_EVENT | BUY_EVENT, ex, lo, p, q))
            for p, q in e["asks"]:
                out.append((NOFLAG | DEPTH_SNAPSHOT_EVENT | SELL_EVENT, ex, lo, p, q))
        elif k == "book_delta":
            out.append((NOFLAG | DEPTH_EVENT | (BUY_EVENT if e["side"] == "bid" else SELL_EVENT), ex, lo, e["price"], e["qty"]))
        else:  # no documented code for bar / funding / liquidation: an unknown code is tried
            out.append((NOFLAG | UNKNOWN_KIND_CODE, ex, lo, float(e.get("close", e.get("price", e.get("rate", 0.0)))), 0.0))
    return out


def _array(rows: list[tuple]) -> np.ndarray:
    a = np.zeros(len(rows), dtype=H.event_dtype)
    for i, (ev, ex, lo, px, q) in enumerate(rows):
        a[i]["ev"], a[i]["exch_ts"], a[i]["local_ts"], a[i]["px"], a[i]["qty"] = ev, ex, lo, px, q
    return a


def _prepare(a: np.ndarray) -> np.ndarray:
    """The documented preparation (data.html): rows without EXCH/LOCAL flags go
    through correct_event_order with the exchange- and local-time orders, which
    adds EXCH_EVENT / LOCAL_EVENT and splits rows whose two orders differ."""
    ex = np.argsort(a["exch_ts"], kind="stable")
    lo = np.argsort(a["local_ts"], kind="stable")
    return correct_event_order(a, ex, lo)


def _flag_both(a: np.ndarray) -> np.ndarray:
    a = a.copy()
    a["ev"] = a["ev"] | BOTH
    return a


def _backtest(data: np.ndarray, entry_latency: int = 0, fee: tuple[str, float] = ("value", 0.0)):
    asset = (H.BacktestAsset().data([data]).linear_asset(1.0).constant_order_latency(entry_latency, 0)
             .risk_adverse_queue_model().no_partial_fill_exchange().tick_size(TICK).lot_size(0.001)
             .last_trades_capacity(1000))
    asset = asset.flat_per_trade_fee_model(fee[1], fee[1]) if fee[0] == "flat" else asset.trading_value_fee_model(fee[1], fee[1])
    return H.HashMapMarketDepthBacktest([asset])


def _levels(depth, side: str, limit: int = 20000) -> list[list[float]]:
    out = []
    best = depth.best_bid_tick if side == "bid" else depth.best_ask_tick
    if best in (-2147483648, 2147483647) or best <= 0 or best > 10**12:
        return out
    step = -1 if side == "bid" else 1
    for i in range(limit):
        t = best + step * i
        q = depth.bid_qty_at_tick(t) if side == "bid" else depth.ask_qty_at_tick(t)
        if q > 0:
            out.append([t * TICK, float(q)])
    return out


def run(evs: list[dict], on_call=None, entry_latency=0, fee=("value", 0.0), prepare=True, max_calls=100):
    """Run the loop. `on_call(hbt, n, code, now, trades)` is the strategy; returns calls:
    list of (code, now, trades)."""
    a = _array(_rows(evs))
    a = _prepare(a) if prepare else _flag_both(a)
    hbt = _backtest(a, entry_latency, fee)
    calls = []
    try:
        for n in range(1, max_calls + 1):
            code = hbt.wait_next_feed(True, 10**17)
            if code == 0:
                break
            now = int(hbt.current_timestamp)
            if code == 1:
                # At the end of the data the last feed is processed but current_timestamp is not
                # advanced (measured); the tool's own report of the last feed's receipt time is used.
                fl = hbt.feed_latency(0)
                if fl is not None:
                    now = max(now, int(fl[1]))
            trades = [{"exch_ts": int(t["exch_ts"]), "local_ts": int(t["local_ts"]), "price": float(t["px"]),
                       "qty": float(t["qty"]), "side": "buy" if int(t["ev"]) & BUY_EVENT else "sell"}
                      for t in hbt.last_trades(0)]
            hbt.clear_last_trades(0)
            if code == 1 and not trades and n > 1 and now == calls[-1][1]:
                break  # end of data with nothing new
            calls.append((2 if code == 1 else code, now, trades))
            if on_call:
                on_call(hbt, n, 2 if code == 1 else code, now, trades)
            if code == 1:
                break  # end of data: the last feed was processed, the strategy got control once more
    finally:
        hbt.close()
    return calls


def _orders(hbt) -> list:
    out = []
    vs = hbt.orders(0).values()
    while vs.has_next():
        o = vs.get()
        out.append({"id": int(o.order_id), "status": STATUS.get(int(o.status), int(o.status)),
                    "exec_qty": float(o.exec_qty), "exec_price": float(o.exec_price_tick) * TICK,
                    "exch_ts": int(o.exch_timestamp), "local_ts": int(o.local_timestamp)})
    return out


def _seq(calls) -> list:
    seq = []
    for code, now, trades in calls:
        if code != 2:
            continue
        if trades:
            seq += [["trade", now] for _ in trades]
        else:
            seq.append(["feed_without_trade", now])  # the strategy only sees that a feed arrived and the book state
    return seq


class HftbacktestAdapter(Adapter):
    name = "opp_hftbacktest"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        evs = C.concatenated(sc)
        a = _flag_both(_array(_rows(evs)))
        try:
            validate_event_order(a)
        except Exception as exc:  # noqa: BLE001
            return not_supported("入力は時刻順に並んだ 1 本の配列だけを受ける。渡した順に連結した配列を、この道具の検査 "
                                 f"validate_event_order に通すと {type(exc).__name__}: {exc}。足・資金調達に当たる事象の型も無い"
                                 "(hftbacktest/types.py の事象の型は DEPTH/TRADE/DEPTH_CLEAR/DEPTH_SNAPSHOT/DEPTH_BBO と注文の 4 種)")
        calls = run(evs, prepare=False)
        return ok({"sequence": _seq(calls)}, "検査を通ったので連結のまま渡した")

    def scene_p1_one_call_per_event(self, sc):
        evs = C.events(sc)
        calls = run(evs)
        return ok({"sequence": [["unknown", now] for code, now, _ in calls if code == 2]},
                  f"足に当たる型が無いので未定義の事象の型の番号 {UNKNOWN_KIND_CODE} で渡した。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    def scene_p1_typed_events(self, sc):
        evs = C.events(sc)
        calls = run(evs)
        return ok({"sequence": _seq(calls)},
                  f"足は未定義の番号 {UNKNOWN_KIND_CODE}、約定は TRADE_EVENT で渡した。呼ばれた回(code, 時刻, 約定): {calls}")

    # ---------------- P0-2
    def scene_p2_iso_utc(self, sc):
        return not_supported("この道具に文字列の時刻を変換する公開の関数は無い(data/utils の各取引所の変換器は取引所の生の書式だけを読む)。"
                             "試したこと: hftbacktest.data.utils の公開名を見て ISO を受ける関数が無いこと、"
                             "event_dtype の exch_ts/local_ts が i8 であること。変換は利用者の側")

    scene_p2_iso_offset = scene_p2_iso_utc

    def _ts(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": 100.0, "qty": 0.01, "side": "buy"} for e in C.events(sc)]
        calls = run(evs)
        obs = [t["local_ts"] for _, _, tr in calls for t in tr]
        return ok({"observed_ts_ns": obs}, f"約定で渡し、last_trades の local_ts を読んだ。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        k = e["kind"]
        captured = {}

        def on_call(hbt, n, code, now, trades):
            if code == 2 and not trades:
                d = hbt.depth(0)
                captured["bids"], captured["asks"] = _levels(d, "bid"), _levels(d, "ask")

        calls = run([e], on_call)
        seq = _seq(calls)
        if k == "trade":
            t = calls[0][2][0] if calls and calls[0][2] else {}
            return ok({"sequence": seq, "fields": {"price": t.get("price"), "qty": t.get("qty"), "side": t.get("side")}},
                      "TRADE_EVENT で渡し、last_trades を読んだ")
        if k == "book_snapshot":
            return ok({"sequence": seq, "fields": {"bids": captured.get("bids"), "asks": captured.get("asks")}},
                      "DEPTH_SNAPSHOT_EVENT(水準ごとの行)で渡した。戦略は知らせを受けたあと板の状態(depth)を読むだけで、"
                      "届いたのが写真か差分かは区別できないので型は feed_without_trade と記録")
        if k == "book_delta":
            bids = captured.get("bids") or []
            f = {"side": "bid", "price": bids[0][0], "qty": bids[0][1]} if bids else {}
            return ok({"sequence": seq, "fields": f}, "DEPTH_EVENT|BUY_EVENT で渡し、板の状態を読んだ。型は feed_without_trade と記録")
        return ok({"sequence": seq, "fields": {}},
                  f"「{k}」に当たる事象の型は無い。未定義の番号 {UNKNOWN_KIND_CODE} で渡した結果、戦略が呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        calls = run(C.events(sc))
        return ok({"sequence": _seq(calls)}, f"足・資金調達・清算は未定義の番号で渡した。呼ばれた回: {[(c, n, len(t)) for c, n, t in calls]}")

    def scene_p3_clock_timer(self, sc):
        evs = C.events(sc)
        a = _prepare(_array(_rows(evs)))  # noqa: F841 (flags added by the documented preparation)
        hbt = _backtest(a)
        clock = []
        try:
            code = hbt.wait_next_feed(True, 10**17)
            first = int(hbt.current_timestamp)
            target = sc.input["timer_at_ns"]
            if hbt.elapse(target - first) == 0:
                clock.append(int(hbt.current_timestamp))
        finally:
            hbt.close()
        return ok({"clock_calls_ns": clock}, f"1 回目(code={code}, {first})で elapse(頼む時刻 − 今) を呼び、戻ったときの current_timestamp を記録")

    def _notice_run(self, evs, place, extra=None, entry_latency=0, fee=("value", 0.0)):
        notices, snaps = [], {}

        def on_call(hbt, n, code, now, trades):
            if code == 3:
                for o in _orders(hbt):
                    if o["id"] == 1:
                        notices.append(o["status"])
            if n == 1:
                snaps["submit"] = place(hbt)
            if extra:
                extra(hbt, n, code, now, snaps)

        calls = run(evs, on_call, entry_latency=entry_latency, fee=fee)
        return notices, snaps, calls

    def scene_p3_notice_accepted(self, sc):
        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 90.0, 1.0, GTC, LIMIT, False))
        return ok({"notices": notices}, f"1 回目に指値 90 を出した(戻り値 {snaps.get('submit')})。order response の知らせ(code=3)で読んだ状態の列。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    def scene_p3_notice_rejected(self, sc):
        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 1_000_000.0, 1.0, GTC, MARKET, False))
        return ok({"notices": notices}, "現金の上限を与える公開の口が無い(state_values の balance は初期 0 から増減するだけ)。"
                  f"成行 1 を出した結果の知らせの列。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    def scene_p3_notice_filled(self, sc):
        fills = []

        def extra(hbt, n, code, now, snaps):
            if code == 3:
                for o in _orders(hbt):
                    if o["id"] == 1 and o["status"] == "filled" and not fills:
                        fills.append(o["exec_qty"])

        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 100.0, 1.0, GTC, MARKET, False), extra)
        return ok({"filled_qty_in_notices": sum(fills), "notices": notices},
                  f"成行 1(板の無い入力)。知らせの列 {notices}。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        evs = [C.as_bar(e) for e in C.events(sc)]
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": e["close"], "qty": 0.01, "side": "buy"} for e in evs]
        probe = sc.input["probe_at_ns"]
        seen = []
        out = {}

        def on_call(hbt, n, code, now, trades):
            seen.extend(trades)
            if now == probe:
                out["visible_count"] = len(seen)
                out["max_visible_close"] = max(t["price"] for t in seen)

        run(evs, on_call)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(out, "足の代わりに同じ時刻・価格=終値の約定で渡し(場面の注記どおり)、戦略が各回に last_trades から受け取った約定を貯めた")

    def scene_p4_received_time(self, sc):
        evs = C.events(sc)
        rec = {}

        def on_call(hbt, n, code, now, trades):
            for t in trades:
                if t["price"] == 101.0:
                    rec.setdefault("delivered", now)
            if now == evs[1]["ts_ns"]:
                rec["at2"] = "delivered" in rec
            if now == evs[2]["ts_ns"]:
                rec["at4"] = "delivered" in rec

        calls = run(evs, on_call)
        return ok({"price101_visible_at_day2": rec.get("at2"), "price101_delivered_at_ns": rec.get("delivered"),
                   "price101_visible_at_day4": rec.get("at4")},
                  "約定の exch_ts=T0+1 日・local_ts=T0+3 日で渡し、文書の手順(correct_event_order)で並べた。"
                  f"呼ばれた回(code, 時刻, 約定): {calls}")

    def scene_p4_future_read_attempt(self, sc):
        evs = [{"kind": "trade", "ts_ns": e["ts_ns"], "price": e["close"], "qty": 0.01, "side": "buy"} for e in C.events(sc)]
        probe = sc.input["probe_at_ns"]
        tried, got = [], {"v": False}

        def on_call(hbt, n, code, now, trades):
            if now != probe:
                return
            d = hbt.depth(0)
            tried.append(f"last_trades -> {trades}")
            tried.append(f"depth.best_bid={d.best_bid}")
            fl = hbt.feed_latency(0)
            tried.append(f"feed_latency -> {fl}")
            if any(t["price"] == 104.0 for t in trades):
                got["v"] = True

        run(evs, on_call)
        if not tried:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok({"future_value_obtained": got["v"]}, "足の代わりに約定で渡した。4 回目に戦略が読める公開の手段(last_trades・depth・feed_latency)を試した: "
                  + "; ".join(tried) + "。先の事象を添字や時刻で引く公開の手段は無い(binding.py の公開の方法の一覧)")

    # ---------------- P0-5
    def scene_p5_same_time_twice(self, sc):
        evs = C.concatenated(sc)
        orders = [_seq(run(evs)) for _ in range(2)]
        return ok({"same_order_in_two_runs": orders[0] == orders[1], "orders": orders},
                  "型ごとの 4 入力を渡した順に連結(同時刻なので時刻の順にも合う)。足・資金調達・清算は未定義の番号")

    def scene_p5_hand_over_order(self, sc):
        outs = set()
        for order in sc.input["hand_over_orders"]:
            outs.add(repr(_seq(run(C.concatenated(sc, order)))))
        return ok({"distinct_orders": len(outs)}, f"24 通りの連結で走らせた結果の列: {sorted(outs)[:3]}…")

    def scene_p5_same_stream_order(self, sc):
        calls = run(C.events(sc))
        return ok({"prices": [t["price"] for _, _, tr in calls for t in tr]}, f"呼ばれた回: {calls}")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}
        mk = {"n": 0}

        def extra(hbt, n, code, now, snaps):
            if code != 2:
                return
            mk["n"] += 1
            opens = [o for o in _orders(hbt) if o["status"] == "accepted"]
            if mk["n"] == 2:
                out["open_at_call2"] = len(opens)
                snaps["cancel"] = hbt.cancel(0, 1, False)
            elif mk["n"] == 3:
                out["open_at_call3"] = len(opens)

        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 90.0, 1.0, GTC, LIMIT, False), extra)
        return ok(out, "市場の知らせ(code=2)の回を 1・2・3 回目と数えた(注文の知らせ code=3 の回は数えない)。"
                  f"知らせの列 {notices}。呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    def scene_p6_cancel_notice(self, sc):
        mk = {"n": 0}

        def extra(hbt, n, code, now, snaps):
            if code == 2:
                mk["n"] += 1
                if mk["n"] == 2:
                    snaps["cancel"] = hbt.cancel(0, 1, False)

        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 90.0, 1.0, GTC, LIMIT, False), extra)
        return ok({"cancel_notice_received": "canceled" in notices, "notices": notices}, f"呼ばれた回: {[(c, n) for c, n, _ in calls]}")

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}
        mk = {"n": 0}

        def extra(hbt, n, code, now, snaps):
            if code == 2:
                mk["n"] += 1
                if mk["n"] == 3:
                    o = [x for x in _orders(hbt) if x["id"] == 1]
                    out["filled_qty_at_call3"] = o[0]["exec_qty"] if o else 0.0

        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 100.0, 1.0, GTC, MARKET, False), extra)
        return ok(out, f"板の無い入力で成行。知らせの列 {notices}")

    # ---------------- P0-7
    def scene_p7_fill_model_swap(self, sc):
        a = H.BacktestAsset()
        names = [n for n in dir(a) if n.endswith("_model") or n.endswith("_exchange")]
        try:
            a.queue_model(object())  # type: ignore[attr-defined]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("約定の模型は組み込みの選択肢(" + ", ".join(names) + ")から選ぶだけで、利用者の模型を渡す口が無い。"
                             f"試したこと: BacktestAsset().queue_model(<利用者の模型>) -> {r}")

    def scene_p7_latency_model_swap(self, sc):
        evs = C.events(sc)
        fills = []

        def extra(hbt, n, code, now, snaps):
            for o in _orders(hbt):
                if o["id"] == 1 and o["status"] == "filled" and not fills:
                    fills.append(o["exch_ts"])

        notices, snaps, calls = self._notice_run(evs, lambda h: h.submit_buy_order(0, 1, 100.0, 1.0, GTC, MARKET, False), extra,
                                                  entry_latency=7_000_000)
        return ok({"fill_time_ns": fills[0] if fills else None, "notices": notices},
                  "constant_order_latency(entry=7 ms, resp=0) を渡し、注文の exch_timestamp を読んだ(板の無い入力で成行)")

    def _fee(self, sc, fee):
        vals = {}

        def extra(hbt, n, code, now, snaps):
            vals["fee"] = float(hbt.state_values(0).fee)
            vals["num_trades"] = int(hbt.state_values(0).num_trades)

        notices, snaps, calls = self._notice_run(C.events(sc), lambda h: h.submit_buy_order(0, 1, 100.0, 1.0, GTC, MARKET, False), extra,
                                                  fee=("flat", fee))
        return ok({"fee": vals.get("fee") if vals.get("num_trades") else None, **vals, "notices": notices},
                  "flat_per_trade_fee_model(fee, fee) を渡し、state_values の fee を読んだ(約定が無ければ None)")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_zero(self, sc):
        return self._fee(sc, 0.0)

    def scene_p7_account_swap(self, sc):
        try:
            H.HashMapMarketDepthBacktest([H.BacktestAsset()], object())  # type: ignore[call-arg]
            r = "受け付けた"
        except Exception as exc:  # noqa: BLE001
            r = f"{type(exc).__name__}: {exc}"
        return not_supported("口座(建玉・残高)は道具の内部の状態(state_values)で、利用者の口座を渡す口が無い。"
                             f"試したこと: HashMapMarketDepthBacktest([asset], <口座>) -> {r}")
