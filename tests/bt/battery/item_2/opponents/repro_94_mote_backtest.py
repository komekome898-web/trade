"""Reproduction of survey candidate 94 `mote/backtest` (backtest.py, Python 2; the tool cannot run here: this environment
has no Python 2 interpreter, and the file is Python 2 syntax -- `print "..."` statements, e.g. line 356), written line
for line from the primary source for the item 2 battery.

Primary source (read only, not executed): https://github.com/mote/backtest/blob/15bb9f1a14541d870444165cc92f1a7029695cc8/backtest.py
(commit 15bb9f1a, 2012-09-14; the clone venvs/item_2/src/c94, log venvs/item_2/logs/c94.log), read 2026-09-25.
Survey report rows: SCAN 4874 行 (limit / stop order based), 10065・10066 行 (stops fill within the bar's high-low range,
unfilled orders carry to the next bar; `cancel` is the order's own cancel and OCO `o1.cancel(o2)`).

What is reproduced (with the source line of each rule):
- Order types LIMIT / STOP / MARKET (86-91); an order added to the book is ACTIVE (336-340) and is looked at from the
  next bar the strategy sees (the strategy handler runs after a bar's fills, 804-837).
- `OrderBook.get_fills(bar)` (427-457): a MARKET order fills on the bar; a LIMIT or STOP order fills when its level
  lies within the bar's low..high (`o.level >= bar.lo and o.level <= bar.hi`, 445), for either side.
- The fill price is the order's level (`final_level = order.level`, 621-622).  A MARKET order's level is whatever the
  user set; the comment at 436-442 names the bar's close or open as the choices.  Every bar here is one print (open =
  close) or a scene bar with no market order, so the two choices give the same value: the close is used.
- OCO (`OCO(o1, o2)`, 256-261: each cancels the other): on a fill, the orders it cancels are cancelled (`fill`, 414-417);
  when two orders that cancel each other are both hit on the same bar, both are cancelled (807-826).
- `OrderBook.cancel` (363-395) cancels an active order.
Bars: i2_common.bar_rows (one bar per print unless the scene has bars); actions go in the handler of the bar chosen by
i2_common.issue_schedule.  No IOC / FOK / post-only / reduce-only / amend, fee, latency or account (the file has no
word for latency, slippage, fee or volume: SCAN 10066 行) -- refused.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

TOOL = "mote/backtest(15bb9f1a)(再現)"


class _O:
    def __init__(self, a):
        self.ref = a["ref"]
        self.type = a["type"]
        self.level = a["px"] if a["type"] == "limit" else a["stop_px"] if a["type"] == "stop" else None
        self.cancels = []
        self.state = "ACTIVE"


class Adapter:
    name = "opp_repro_94_mote"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "oco", "cancel"), events=("book", "trade", "bar"),
               fill_models=lambda fm: C.bar_fill_models(fm), costs=(), account=("cash",))
        bars, _src = C.bar_rows(inp)
        if not bars:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(入力は足の列)")
        sched = C.issue_schedule(bars, inp["actions"])
        book = {}
        rec = {"orders": {}, "fills": []}
        for k, b in enumerate(bars):
            # fills of this bar first (804-837), then the strategy's handler (the actions of this bar)
            hits = [o for o in book.values() if o.state == "ACTIVE" and
                    (o.type == "market" or (b["l"] <= o.level <= b["h"]))]
            for o in hits[:]:
                dups = [x for x in hits if o.ref in x.cancels]
                if dups:  # 807-826: two hit orders that cancel each other -> both cancelled
                    o.state = "CANCELLED"
                    hits.remove(o)
                    for d in dups:
                        d.state = "CANCELLED"
                        if d in hits:
                            hits.remove(d)
            for o in hits:
                if o.state != "ACTIVE":
                    continue
                px = o.level if o.level is not None else b["c"]
                rec["fills"].append({"ref": o.ref, "t": b["t"], "px": float(px), "qty": o.qty, "liq": None})
                o.state = "FILLED"
                for c in o.cancels:  # 414-417
                    if book[c].state == "ACTIVE":
                        book[c].state = "CANCELLED"
            for a in sched.get(k, []):
                if a["op"] == "cancel":
                    if a["ref"] in book and book[a["ref"]].state == "ACTIVE":
                        book[a["ref"]].state = "CANCELLED"
                    continue
                if a["op"] != "place":
                    raise NotExpressible(f"{TOOL}: 操作 {a['op']} の口が無い")
                o = _O(a)
                o.qty = a["qty"]
                book[a["ref"]] = o
                if a.get("oco"):
                    other = book.get(a["oco"])
                    if other is not None:  # OCO(o1, o2), 256-261
                        o.cancels.append(other.ref)
                        other.cancels.append(o.ref)
        for a in C.places(inp):
            o = book.get(a["ref"])
            st = {"FILLED": "filled", "CANCELLED": "canceled", "ACTIVE": "open"}[o.state] if o else "open"
            rec["orders"][a["ref"]] = {"status": st}
        return rec


TARGET = Adapter()
