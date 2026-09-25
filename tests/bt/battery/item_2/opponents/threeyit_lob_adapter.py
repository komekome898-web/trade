"""Survey candidate 102 `3yit/Limit-Order-Book-Simulator` (git clone, commit 8e5e9d24, built with the
repository's LOB_BUILD_PYTHON option into venv item_0/c102; install record: item 0 survey_results/attempts/102.log)
for the item 2 battery.

The tool's own calls used (its pybind11 module `lob_cpp`): `MatchingEngine.process(Order)` -> MatchResult
(trades with incoming/resting order ids, residual = the resting remainder), `cancel(id)`, `modify(id, price,
qty)`; `Order` (id, side, type LIMIT / MARKET, integer price, integer quantity).  No IOC, FOK, post-only,
stop, fees, latency, notices or account.  The scene -> engine mapping is lob_common's (integer ticks / lots;
a trade print is a limit order at the print price followed at once by a cancel of what is left).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import lob_common as L  # noqa: E402

import lob_cpp  # noqa: E402  (the tool's binding, built into the venv)

TOOL = "3yit/Limit-Order-Book-Simulator(8e5e9d24)"
SIDE = {"buy": lob_cpp.Side.BUY, "sell": lob_cpp.Side.SELL}


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"market", "limit", "cancel", "amend", "l3"})
    int_units = True

    def start(self, inp):
        self.me = lob_cpp.MatchingEngine()
        self.id2key, self.key2id = {}, {}
        self.n = 0

    def _go(self, key, side, typ, px, qty):
        self.n += 1
        o = lob_cpp.Order()
        o.id, o.side, o.type, o.price, o.quantity = self.n, SIDE[side], typ, int(px), int(qty)
        self.id2key[self.n], self.key2id[key] = key, self.n
        r = self.me.process(o)
        return [(self.id2key.get(t.resting_order, f"?{t.resting_order}"), key, t.price, t.quantity) for t in r.trades]

    def limit(self, key, side, px, qty, mine, stp):
        return self._go(key, side, lob_cpp.OrderType.LIMIT, px, qty)

    def market(self, key, side, qty, mine, stp):
        return self._go(key, side, lob_cpp.OrderType.MARKET, 0, qty)

    def cancel(self, key):
        return self.me.cancel(self.key2id[key]) if key in self.key2id else False

    def amend(self, key, px, new_left, left):
        # MatchingEngine::modify(id, new_quantity, optional new_price) (src/matching_engine.cpp 23) sets the resting
        # quantity (order_book.cpp 78); the quantity is required, so a price-only amend passes the quantity left now
        new_q = int(left) if new_left is None else int(new_left)
        if not self.me.modify(self.key2id[key], new_q, int(px)):
            raise RuntimeError("modify returned False")
        return []


class Adapter:
    name = "opp_3yit_lob"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
