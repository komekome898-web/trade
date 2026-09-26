"""Survey candidate 3 `PySystemtrade` (GitHub pst-group/pysystemtrade, commit 8958c49c, venv item_0/c3 with a .pth to
a sparse clone; install record: item 0 survey_results/attempts/3.log) for the item 2 battery.

What the tool has at the order level: `systems.accounts.order_simulator.fills_and_orders.fill_list_of_simple_orders(
list_of_orders, fill_datetime, market_price)` with `SimpleOrder(quantity: int, limit_price=None)`
(simple_orders.py 10-24): a market order fills at the market price; a limit buy fills at its limit when limit >
market price, a limit sell when limit < market price (fills_and_orders.py 64-89).  The tool's own order simulator
evaluates an order placed at one point against the price series' NEXT price only and does not keep an unfilled
order (pandl_order_simulator.py 221-235 `next_price = prices[idx + 1]`; hourly_limit_orders.py
`generate_order_and_fill_at_idx_point_for_limit_orders`).

Scene -> tool: the price series is the scene's trade prints; an order placed at t is handed to
fill_list_of_simple_orders with the first print after t (market_price, fill_datetime); unfilled -> canceled (the
tool keeps no order).  Quantities are integers in the tool: they are given in the scene's quantity unit (the largest
power of ten dividing every quantity, lob_common.qty_unit) and converted back.  Only market and plain limit (GTC)
orders, no fill model, no latency, no costs other than zero, no account limits: anything else is refused.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
import lob_common as LC  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402
from probe_base import ProbeAdapter, signature_probe  # noqa: E402

from systems.accounts.order_simulator.fills_and_orders import fill_list_of_simple_orders  # noqa: E402  (the tool)
from systems.accounts.order_simulator.simple_orders import ListOfSimpleOrders, SimpleOrder  # noqa: E402


def _dt(ns):
    return D.datetime(1970, 1, 1) + D.timedelta(microseconds=ns // 1000)


class Adapter(ProbeAdapter):
    name = "opp_pysystemtrade"
    tool = "PySystemtrade(8958c49c)"
    what = "注文の口は SimpleOrder(整数の数量・指値)を次の 1 つの市場の値に当てる fill_list_of_simple_orders だけ"

    def probe(self):
        return signature_probe(fill_list_of_simple_orders, SimpleOrder)

    def express(self, inp):
        try:
            C.gate(inp, tool=self.tool, orders=("market", "limit"), events=("book", "trade"), costs=(), account=("cash",))
        except NotExpressible as exc:
            self._why = str(exc).split(": ", 1)[-1]
            return None
        unit = LC.qty_unit(inp)
        trades = C.trades(inp)
        rec = {"orders": {}, "fills": []}
        for a in C.places(inp):
            nxt = next((e for e in trades if e["t"] > a["t"]), None)
            q = LC.lots(a["qty"], unit)
            q = int(q) if float(q).is_integer() else None
            if q is None:
                raise NotExpressible(f"{self.tool}: 数量 {a['qty']} を整数の枚数で渡せない")
            order = SimpleOrder(quantity=q if a["side"] == "buy" else -q,
                                limit_price=None if a["type"] == "market" else float(a["px"]))
            if nxt is None:
                rec["orders"][a["ref"]] = {"status": "canceled"}
                continue
            fill = fill_list_of_simple_orders(ListOfSimpleOrders([order]), fill_datetime=_dt(nxt["t"]),
                                              market_price=float(nxt["px"]))
            if not fill.qty:  # the tool's empty fill (sysobjects/fills.py 22: qty=0, price=nan)
                rec["orders"][a["ref"]] = {"status": "canceled"}
            else:
                rec["orders"][a["ref"]] = {"status": "filled"}
                rec["fills"].append({"ref": a["ref"], "t": int(nxt["t"]), "px": float(fill.price),
                                     "qty": abs(float(fill.qty)) * unit, "liq": None})
        return rec

    def why_not(self, inp):
        return getattr(self, "_why", "場面の注文を渡す口が無い")


TARGET = Adapter()
