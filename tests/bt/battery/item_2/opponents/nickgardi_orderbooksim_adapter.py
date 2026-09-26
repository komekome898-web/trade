"""Survey candidate 99 `NickGardi/orderbooksim` (git clone, venv item_0/c99 with a .pth to the clone;
install record: item 0 survey_results/attempts/99.log) for the item 2 battery.

The tool's own calls used: `MatchingEngine.submit_order(Order)` (a limit order: matches what crosses,
rests the rest; returns the trades), `cancel_order(id)`, `get_order(id)`; `models.Order.create`.
The tool has limit orders only (no market, IOC, FOK, post-only, stop, amend), no fees, no latency,
no notices, no account.  The scene -> engine mapping is lob_common's (a trade print is the tool's
limit order at the print price followed at once by `cancel_order` of what is left).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import lob_common as L  # noqa: E402

from matching_engine import MatchingEngine  # noqa: E402  (the tool, via the venv's .pth)
from models import Order, Side  # noqa: E402

TOOL = "NickGardi/orderbooksim"
SIDE = {"buy": Side.BUY, "sell": Side.SELL}


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"limit", "cancel", "l3"})
    int_units = False

    def start(self, inp):
        self.m = MatchingEngine()
        self.id2key, self.key2id = {}, {}

    def limit(self, key, side, px, qty, mine, stp):
        oid = self.m.next_order_id()
        self.id2key[oid], self.key2id[key] = key, oid
        trades = self.m.submit_order(Order.create(oid, SIDE[side], px, qty, timestamp=0.0))
        out = []
        for t in trades:
            maker = t.sell_order_id if side == "buy" else t.buy_order_id
            out.append((self.id2key.get(maker, f"?{maker}"), key, t.price, t.quantity))
        return out

    def cancel(self, key):
        return self.m.cancel_order(self.key2id[key]) if key in self.key2id else False

    def resting(self, key):
        return self.m.get_order(self.key2id[key]) is not None if key in self.key2id else False


class Adapter:
    name = "opp_nickgardi_orderbooksim"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
