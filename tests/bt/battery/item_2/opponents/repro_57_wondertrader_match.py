"""Reproduction of survey candidate 57 `WonderTrader`'s back-test matcher `MatchEngine` (src/WtBtCore/MatchEngine.cpp),
written line for line from the primary source for the item 2 battery (the tool itself could not be installed: item 0
survey_results/attempts/57.log; tests/bt/battery/item_0/opponents/RUNNABILITY.tsv).

Primary source (read only, nothing of it executed): https://github.com/wondertrader/wondertrader/blob/08b230dd05facf6d650d949bfe51054115a2ecb1/src/WtBtCore/MatchEngine.cpp
and MatchEngine.h, commit 08b230dd (2026-09-01), read 2026-09-25 from a sparse clone (venvs/item_2/logs/i2_r1_scenekeeper_read.log).
Survey report rows: SCAN 7852 行 (candidate 57), the tier table row SCAN 10516 行 (段 3・4・5, 取り消しの扱い 在る:
`ordInfo._queue -= (uint32_t)round(ordInfo._queue*_cancelrate);`).  Each rule below names its source line.

The matcher is driven by ticks (WTSTickData: last price, the tick's volume, bid / ask price and quantity by level).  The
scene's market events become ticks: a book snapshot -> a tick with the snapshot's levels, the last price unchanged and
volume 0; a trade print -> a tick with the current book, last price = the print's price, volume = the print's size.
Quantities are integer lots (the matcher's queue arithmetic casts to uint32, lines 251, 254); prices as given.
MatchEngine has buy / sell at a limit price and cancel (lines 229, 264, 328); no market, IOC, FOK, post-only, stop,
amend, fee, latency or account -- those are refused.  _cancelrate: the config value "cancelrate" (line 20), 0 when not
set (MatchEngine.h 57); the scene's cancel stance none -> 0, discount_at_entry -> the scene's cancel_rate.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
import lob_common as L  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

TOOL = "WonderTrader MatchEngine(08b230dd)(再現)"


def _fm(fm):
    if "range" in fm or "impact" in fm:
        return "市場影響の関数・楽観と悲観の両方を回す口が無い"
    if fm.get("tier") != 5:
        return f"段 {fm.get('tier')} を選ぶ口が無い(MatchEngine の受け身の注文は列の位置を追う型だけ)"
    if fm.get("cancel_stance") not in ("none", "discount_at_entry"):
        return f"先行の取消の扱い {fm.get('cancel_stance')} の口が無い(出した時に 1 回だけ cancelrate で割り引く型だけ, 254 行)"
    return None


class _Order:  # _OrderInfo, MatchEngine.h 83-101: every field starts at 0 (memset, line 99)
    def __init__(self):
        self.buy = False
        self.qty = self.left = self.traded = self.limit = self.price = 0.0
        self.state = 0
        self.queue = 0.0
        self.positive = False
        self.time = 0


class Adapter:
    name = "opp_repro_57_wondertrader"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("limit", "cancel"), events=("book", "trade"), fill_models=_fm, costs=(),
               account=("cash",))
        fm = inp.get("fill_model") or {}
        cancelrate = float(fm.get("cancel_rate", 0.0)) if fm.get("cancel_stance") == "discount_at_entry" else 0.0
        unit = L.qty_unit(inp)
        L.INT_ONLY[0] = True
        try:
            lot = lambda q: L.lots(q, unit)  # noqa: E731
            book = {"bids": [], "asks": []}
            last = {"px": 0.0}
            tick = None
            orders = {}
            fills = []

            def make_tick(e):
                if e["type"] == "book":
                    book["bids"], book["asks"] = sorted(e["bids"], reverse=True), sorted(e["asks"])
                    vol = 0
                else:
                    last["px"] = float(e["px"])
                    vol = lot(e["qty"])
                b0 = book["bids"][0] if book["bids"] else (0.0, 0)
                a0 = book["asks"][0] if book["asks"] else (0.0, 0)
                return {"price": last["px"], "volume": vol, "bidprice": float(b0[0]), "bidqty": lot(b0[1]) if b0[1] else 0,
                        "askprice": float(a0[0]), "askqty": lot(a0[1]) if a0[1] else 0}

            def handle_tick(tk, t):  # line 340: update_lob, fire_orders, match_orders, erase
                to_erase = []
                for o in orders.values():  # fire_orders, lines 28-42
                    if o.state == 0:
                        o.state = 1
                for ref, o in orders.items():  # match_orders, lines 44-185
                    if o.state == 9:  # line 54: cancel requested
                        o.state = 99
                        to_erase.append(ref)
                        o.left = 0
                        continue
                    if o.state != 1 or tk["volume"] == 0:  # line 66
                        continue
                    for side_buy in (True, False):
                        if o.buy != side_buy:
                            continue
                        if o.positive:  # lines 75-79 / 133-137: an aggressive order takes the opposite best
                            price, volume = (tk["askprice"], tk["askqty"]) if o.buy else (tk["bidprice"], tk["bidqty"])
                        else:  # lines 81-84: a passive one looks at the last trade
                            price, volume = tk["price"], tk["volume"]
                        crosses = price <= o.limit if o.buy else price >= o.limit  # lines 86 / 144
                        if not crosses:
                            continue
                        if not o.positive and price == o.limit:  # lines 89-105: at the limit, the queue ahead first
                            if volume <= o.queue:
                                o.queue -= volume
                                continue
                            elif o.queue != 0:
                                volume -= o.queue
                                o.queue = 0
                        elif not o.positive:  # lines 106-109: through the limit -> all that is left
                            volume = o.left
                        qty = min(volume, o.left)  # line 111
                        if qty == 0:  # lines 112-113
                            qty = 1
                        fills.append({"ref": ref, "t": int(t), "px": price, "qty": qty * unit, "liq": None})  # line 115
                        o.traded += qty
                        o.left -= qty
                        if o.left == 0:  # line 122
                            to_erase.append(ref)
                for ref in to_erase:
                    orders[ref].state = 100 if orders[ref].left == 0 and orders[ref].traded > 0 else orders[ref].state

            def place(a):  # buy / sell, lines 229-296
                if tick is None:  # lines 231-233: no last tick -> no order
                    return None
                o = _Order()
                o.buy = a["side"] == "buy"
                o.limit = float(a["px"])
                o.qty = o.left = lot(a["qty"])
                o.price = tick["price"]
                if o.buy:
                    if o.limit >= tick["askprice"]:  # line 246
                        o.positive = True
                    elif o.limit == tick["bidprice"]:  # line 248
                        o.queue = tick["bidqty"]
                else:
                    if o.limit == tick["askprice"]:  # line 281
                        o.queue = tick["askqty"]
                    elif o.limit <= tick["bidprice"]:  # line 283
                        o.positive = True
                if o.limit == tick["price"]:  # lines 250-251 / 285-286
                    den = tick["askprice"] + tick["bidprice"]
                    o.queue = float(int(round((tick["askqty"] * tick["askprice"] + tick["bidqty"] * tick["bidprice"]) / den))) if den else 0.0
                o.queue -= float(int(round(o.queue * cancelrate)))  # lines 254 / 288
                return o

            status = {}
            for t, kind, x in C.timeline(inp):
                if kind == "m":
                    tick = make_tick(x)
                    handle_tick(tick, t)
                    continue
                if x["op"] == "place":
                    if x["type"] != "limit" or x["tif"] != "GTC" or x["post_only"]:
                        raise NotExpressible(f"{TOOL}: 指値の買い・売り(buy / sell)だけで、{x['type']} / {x['tif']} の口が無い")
                    o = place(x)
                    if o is None:
                        status[x["ref"]] = "rejected"
                    else:
                        orders[x["ref"]] = o
                elif x["op"] == "cancel":
                    if x["ref"] in orders:
                        orders[x["ref"]].state = 9  # cancel(localid), lines 328-338
                else:
                    raise NotExpressible(f"{TOOL}: 操作 {x['op']} の口が無い")
        except L._OffGrid as exc:
            raise NotExpressible(f"{TOOL}: 数量 {exc} が整数の枚数に乗らない")
        rec = {"orders": {}, "fills": fills}
        for a in C.places(inp):
            ref = a["ref"]
            if status.get(ref) == "rejected":
                rec["orders"][ref] = {"status": "rejected", "error": "no last tick (MatchEngine.cpp 231-233)"}
                continue
            o = orders[ref]
            got = o.traded * unit
            rec["orders"][ref] = {"status": C.status_from(got, a["qty"], active=o.state in (0, 1, 9), canceled=o.state == 99)}
        return rec


TARGET = Adapter()
