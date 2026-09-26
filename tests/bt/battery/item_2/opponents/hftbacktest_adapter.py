"""Survey candidate 23 `hftbacktest` (PyPI 2.4.4, venv item_0/hftbacktest) for the item 2 battery.

Public API used: `BacktestAsset` builders (data, linear_asset, tick_size, lot_size,
constant_order_latency(entry, response), risk_adverse_queue_model /
power_prob_queue_model(n), partial_fill_exchange / no_partial_fill_exchange,
trading_value_fee_model(maker, taker), last_trades_capacity),
`HashMapMarketDepthBacktest`, `elapse`, `submit_buy_order` / `submit_sell_order`
(time in force GTC / GTX = post-only / FOK / IOC, order type LIMIT / MARKET),
`cancel`, `modify`, `orders`, `state_values`, `current_timestamp`.

Scene -> tool:
- book snapshots -> DEPTH_EVENT rows for the levels that changed (qty 0 = level gone);
  trades -> TRADE_EVENT with BUY/SELL (aggressor); exchange time = t, local time =
  t + feed latency. A no-op depth row at end_t keeps the data running to the end.
- queue models the tool has: risk_adverse (a depth decrease caps the queue ahead at
  the new depth) and power_prob(n) (the documented ProbQueueModel with f(x) = x^n).
  Scenes with no fill model use risk_adverse + partial_fill_exchange (the queue
  model and exchange of the tool's documented examples).
- The strategy loop elapses to every event / action / checkpoint time and in 1 ms
  steps after each action (so responses are seen at their arrival time), reading
  each order's cumulative executed quantity; a fill is the increase, stamped with
  the order's exchange timestamp and last execution price; its fee is the increase
  of `state_values.fee` in the same step (split by quantity when several orders
  filled in one step).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import hftbacktest as H  # noqa: E402
from hftbacktest import (BUY_EVENT, DEPTH_EVENT, EXCH_EVENT, LOCAL_EVENT, SELL_EVENT,  # noqa: E402
                         TRADE_EVENT)
from hftbacktest.order import (CANCELED, EXPIRED, FILLED, FOK, GTC, GTX, IOC, LIMIT, MARKET,  # noqa: E402
                               NEW, PARTIALLY_FILLED, REJECTED)

TOOL = "hftbacktest 2.4.4"
TIF = {"GTC": GTC, "IOC": IOC, "FOK": FOK}


def _fill_models(fm):
    if "range" in fm or "impact" in fm:
        return "市場影響の関数・楽観と悲観を同時に回す口が無い(待ち行列の模型と取引所の模型だけ)"
    if fm.get("tier") != 5:
        return f"段 {fm.get('tier')} の約定の模型が無い(列の模型 = 段 5 だけ)"
    if fm.get("cancel_stance") not in ("snapshot_cap", "prob"):
        if fm.get("cancel_stance") == "none" and _CTX.get("no_depth_change"):
            return None  # with no depth change after the order, risk_adverse keeps the queue ahead as displayed
        return f"先行の取消の扱い {fm.get('cancel_stance')} の列の模型が無い(risk_adverse = 写真で上限、prob = 確率型)"
    return None


_CTX = {}


def _rows(inp, feed):
    rows = []
    prev = {"bid": {}, "ask": {}}
    last_t = 0
    for e in inp["market"]:
        t = e["t"]
        last_t = max(last_t, t)
        if e["type"] == "trade":
            flag = BUY_EVENT if e["aggressor"] == "buy" else SELL_EVENT
            rows.append((EXCH_EVENT | LOCAL_EVENT | TRADE_EVENT | flag, t, t + feed, e["px"], e["qty"]))
        elif e["type"] == "book":
            for side, key, flag in (("bid", "bids", BUY_EVENT), ("ask", "asks", SELL_EVENT)):
                new = {float(p): float(q) for p, q in e[key]}
                for p in sorted(set(prev[side]) | set(new)):
                    if prev[side].get(p) != new.get(p, 0.0):
                        rows.append((EXCH_EVENT | LOCAL_EVENT | DEPTH_EVENT | flag, t, t + feed, p, new.get(p, 0.0)))
                prev[side] = new
    end = inp["end_t"]
    anchor = next(iter(prev["bid"]), None)
    if anchor is not None:
        rows.append((EXCH_EVENT | LOCAL_EVENT | DEPTH_EVENT | BUY_EVENT, end, end + feed, anchor, prev["bid"][anchor]))
    a = np.zeros(len(rows), dtype=H.event_dtype)
    for i, (ev, ex, lo, px, q) in enumerate(rows):
        a[i]["ev"], a[i]["exch_ts"], a[i]["local_ts"], a[i]["px"], a[i]["qty"] = ev, ex, lo, px, q
    return a


class Hftbacktest:
    name = "opp_hftbacktest"

    def run(self, inp):
        books = [e for e in inp["market"] if e["type"] == "book"]
        first_place = min((a["t"] for a in C.places(inp)), default=0)
        _CTX["no_depth_change"] = sum(1 for b in books if b["t"] > first_place) == 0
        C.gate(inp, tool=TOOL, orders=("market", "limit", "IOC", "FOK", "post_only", "cancel", "amend"),
               events=("book", "trade"), fill_models=_fill_models, latency=("feed", "order", "notice"),
               costs=("maker_rate", "taker_rate", "spread"), account=("cash",))
        if not books:
            raise NotExpressible(f"{TOOL}: 板の事象が無い場面は渡せない(約定は板の深さの事象と約定の事象から決まる)")
        lat = inp.get("latency") or {}
        g = lambda k: int((lat.get(k) or {}).get("ns", 0))  # noqa: E731
        if any(a["op"] == "cancel" for a in inp["actions"]) and g("cancel") != g("order"):
            raise NotExpressible(f"{TOOL}: 取消の遅れを発注の遅れと別に渡す口が無い(constant_order_latency(entry, response) は発注と取消に同じ entry を使う)")
        feed = g("feed")
        prod = inp["product"]
        c = inp["costs"]
        fm = inp.get("fill_model") or {}
        try:
            asset = (H.BacktestAsset().data([_rows(inp, feed)]).linear_asset(1.0)
                     .constant_order_latency(g("order"), g("notice"))
                     .tick_size(prod["tick"]).lot_size(prod["qty_step"]).last_trades_capacity(1000))
            if fm.get("cancel_stance") == "prob":
                asset = asset.power_prob_queue_model(float(fm.get("prob_n", 1)))
            else:
                asset = asset.risk_adverse_queue_model()
            asset = asset.partial_fill_exchange()
            asset = asset.trading_value_fee_model(float(c.get("maker_rate", 0.0)), float(c.get("taker_rate", 0.0)))
            hbt = H.HashMapMarketDepthBacktest([asset])
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        ids = {}
        refs = {}
        orders_rec = {}
        fills = []
        notices = {}
        seen = {}
        last = {}
        last_status = {}
        places = {a["ref"]: a for a in C.places(inp)}
        steps = set()
        for e in inp["market"]:
            steps.add(e["t"] + feed)
        for a in inp["actions"]:
            steps.add(a["t"])
            for k in range(1, 51):
                steps.add(a["t"] + k * 1_000_000)
        steps |= set(inp.get("checkpoints", {}).values())
        steps.add(inp["end_t"])
        steps = sorted(s for s in steps if s <= inp["end_t"])
        acts = sorted(inp["actions"], key=lambda a: a["t"])
        ai = 0
        fee_prev = 0.0
        bal_prev = float(hbt.state_values(0).balance)
        pos_prev = float(hbt.state_values(0).position)
        labels = [(e["t"] + feed, e["label"]) for e in inp["market"] if e.get("label")]
        data_start = min(e["t"] for e in inp["market"])  # the tool's clock starts at the first exchange time
        now = hbt.current_timestamp
        if now > inp["end_t"] + 10**15:  # the tool reports int64 max until the first elapse
            now = data_start
        for st in steps:
            if st > now:
                if hbt.elapse(st - now) != 0 and st < inp["end_t"]:
                    pass
                now = hbt.current_timestamp
            for lt, lab in labels:
                if lt <= now and lab not in seen:
                    seen[lab] = now
            while ai < len(acts) and acts[ai]["t"] <= now:
                a = acts[ai]
                ai += 1
                if a["op"] == "place":
                    oid = len(ids) + 1
                    ids[a["ref"]] = oid
                    refs[oid] = a["ref"]
                    tif = GTX if a["post_only"] else TIF[a["tif"]]
                    otype = MARKET if a["type"] == "market" else LIMIT
                    px = a["px"] if a["px"] is not None else (1e9 if a["side"] == "buy" else prod["tick"])
                    fn = hbt.submit_buy_order if a["side"] == "buy" else hbt.submit_sell_order
                    rc = fn(0, oid, px, a["qty"], tif, otype, False)
                    if rc != 0:
                        orders_rec[a["ref"]] = {"status": "rejected", "error": f"submit rc={rc}"}
                elif a["op"] == "cancel":
                    hbt.cancel(0, ids[a["ref"]], False)
                elif a["op"] == "amend":
                    o = hbt.orders(0).get(ids[a["ref"]])
                    hbt.modify(0, ids[a["ref"]], a["px"] if a["px"] is not None else o.price,
                               a["qty"] if a["qty"] is not None else o.qty, False)
            sv = hbt.state_values(0)
            fee_now = float(sv.fee)
            step_fills = []
            for oid, ref in refs.items():
                o = hbt.orders(0).get(oid)
                if o is None:
                    continue
                q = float(o.exec_qty) if o.status in (FILLED, PARTIALLY_FILLED) or o.exec_qty > 0 else 0.0
                cum = float(o.qty - o.leaves_qty) if o.status in (FILLED, PARTIALLY_FILLED, CANCELED, EXPIRED) else 0.0
                cum = max(cum, 0.0)
                if cum > last.get(ref, 0.0) + 1e-12:
                    step_fills.append({"ref": ref, "t": int(o.exch_timestamp), "px": float(o.exec_price),
                                       "qty": cum - last.get(ref, 0.0), "fee": 0.0, "liq": None})
                    last[ref] = cum
                if last_status.get(ref) != o.status:
                    n = notices.setdefault(ref, {})
                    kind = {NEW: "ack", REJECTED: "reject", EXPIRED: "cancel", CANCELED: "cancel",
                            FILLED: "fill", PARTIALLY_FILLED: "fill"}.get(o.status)
                    if kind and kind not in n:
                        n[kind] = int(now)  # the local time this loop first saw the new status
                    last_status[ref] = o.status
                del q
            dfee = fee_now - fee_prev
            bal_now = float(sv.balance)
            pos_now = float(sv.position)
            if step_fills:
                tot = sum(f["qty"] for f in step_fills)
                for f in step_fills:
                    f["fee"] = dfee * f["qty"] / tot
                if len(step_fills) == 1:
                    # one order filled in this step, possibly across several price levels: the tool's own
                    # balance change (cash moves by -price*qty for a buy, excluding the fee) gives its notional
                    f = step_fills[0]
                    sign = 1.0 if places[f["ref"]]["side"] == "buy" else -1.0
                    notional = -(bal_now - bal_prev) * sign
                    # only when the tool's own position moved by the same quantity (its accounts agree with
                    # its order record); otherwise the order record (last execution price) is reported as is
                    if notional > 0 and abs(abs(pos_now - pos_prev) - f["qty"]) <= 1e-9:
                        f["px"] = notional / f["qty"]
                fills.extend(step_fills)
            fee_prev = fee_now
            bal_prev, pos_prev = bal_now, pos_now
        for oid, ref in refs.items():
            if ref in orders_rec:
                continue
            o = hbt.orders(0).get(oid)
            if o is None:
                orders_rec[ref] = {"status": "canceled"}
                continue
            orders_rec[ref] = {"status": {FILLED: "filled", NEW: "open", PARTIALLY_FILLED: "open", CANCELED: "canceled",
                                          EXPIRED: "canceled", REJECTED: "rejected"}.get(o.status, f"code{o.status}")}
        sv = hbt.state_values(0)
        out = {"orders": orders_rec, "fills": fills, "notices": notices, "seen": seen,
               "account": {"position": float(sv.position)}}
        hbt.close()
        return out


TARGET = Hftbacktest()
