"""Survey candidate 103 `IsaacCheng9/order-book-simulator` (git clone, venv item_0/c103 made with a Python 3.14
interpreter; install record: item 0 survey_results/attempts/103.log) for the item 2 battery.

The tool's own calls used: `order_book_simulator.matching.order_book.OrderBook(stock_id, ticker)`,
`add_order(dict: id, side BUY/SELL, order_type LIMIT/MARKET, price, quantity, created_at)` -> fills
(buyer_order_id / seller_order_id / price / quantity), `cancel_order(id)`.  Its SUPPORTED_ORDER_TYPES are
LIMIT and MARKET; no IOC, FOK, post-only, amend, fees, latency, notices or account in the book.  The scene ->
engine mapping is lob_common's (Decimal prices and sizes, so float ticks are passed as they are; a trade print
is a limit order at the print price followed at once by a cancel of what is left).
"""
from __future__ import annotations

import datetime as D
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import lob_common as L  # noqa: E402

from order_book_simulator.matching.order_book import OrderBook  # noqa: E402  (the tool, in its venv)

TOOL = "IsaacCheng9/order-book-simulator"
NS = uuid.UUID("00000000-0000-0000-0000-000000000000")


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"market", "limit", "cancel", "l3"})
    int_units = False

    def start(self, inp):
        self.b = OrderBook(uuid.uuid5(NS, "stock"), "SCENE")
        self.id2key, self.key2id = {}, {}
        self.n = 0

    def _go(self, key, side, typ, px, qty):
        self.n += 1
        oid = uuid.uuid5(NS, str(self.n))  # deterministic ids
        self.id2key[oid], self.key2id[key] = key, oid
        fills = self.b.add_order({"id": oid, "side": side.upper(), "order_type": typ, "price": px, "quantity": qty,
                                  "created_at": D.datetime(2026, 1, 1, tzinfo=D.timezone.utc)})
        out = []
        for f in fills:
            maker = f["seller_order_id"] if side == "buy" else f["buyer_order_id"]
            out.append((self.id2key.get(maker, f"?{maker}"), key, f["price"], f["quantity"]))
        return out

    def limit(self, key, side, px, qty, mine, stp):
        return self._go(key, side, "LIMIT", px, qty)

    def market(self, key, side, qty, mine, stp):
        return self._go(key, side, "MARKET", None, qty)

    def cancel(self, key):
        return self.b.cancel_order(self.key2id[key]) if key in self.key2id else False


class Adapter:
    name = "opp_isaaccheng_obsim"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
