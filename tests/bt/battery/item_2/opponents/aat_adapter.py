"""Survey candidate 65 `aat` (GitHub AsyncAlgoTrading/aat, commit c4a07d41; the clone in venvs/item_2/src/c65, run
with the dependencies installed in venv item_0/c65; install records item 0 survey_results/attempts/65.log and
venvs/item_2/logs/i2_r1_scenekeeper_install_65.log) for the item 2 battery.

The tool's own part used: its order book `aat.core.OrderBook(instrument)` (the pure-Python book; the C++ one is used
only with AAT_USE_CPP) with `add(Order)` and `cancel(Order)` / `change(Order)`, and its `Order(volume, price, side,
instrument, order_type=LIMIT / MARKET / STOP, flag=NONE / FILL_OR_KILL / IMMEDIATE_OR_CANCEL, stop_target=...)`.
The book matches price-time at the resting (maker) order's price; what each order filled is read from the tool's own
order records (`Order.filled` before and after each call), so a fill is (maker, taker, maker's price, maker's
increase).  The scene -> engine mapping is lob_common's.  As the tool's code does, an IOC limit order that fills
nothing is put on the book (order_book.py, the IMMEDIATE_OR_CANCEL branch with filled == 0), and a stop order is
held by the first price level it crosses (price_level.py cross() on OrderType.STOP) and sent as its stop_target (a
market order) when that level is crossed.  The book has no post-only flag, no self-trade prevention, no fee, no
latency and no account; `change` modifies an order's volume only (a price amend is refused).
Observed with the tool's Python book (checked by calling it directly with the tier-5 scene's orders): after an IOC
that partly takes a level, a later taker at that level skips the orders behind the first one (the level's staged
state is committed only when the level is cleared), so queue scenes come out differently from a price-time queue.
The C++ book (AAT_USE_CPP=1 with the binding built in item 0) was tried the same way: its Instrument takes positional
arguments only, and with those the orders' filled amounts read back from Python did not follow price-time either
(the order behind was reported filled first), so the Python book -- the tool's default -- is the one run here.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, "/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/item_2/src/c65")

import lob_common as L  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

from aat.config import InstrumentType, OrderFlag, OrderType, Side  # noqa: E402  (the tool)
from aat.core import ExchangeType, Instrument, Order, OrderBook  # noqa: E402

TOOL = "aat(c4a07d41) OrderBook"
EX = ExchangeType("scene")
INST = Instrument("X", InstrumentType.EQUITY, exchange=EX)
SIDE = {"buy": Side.BUY, "sell": Side.SELL}


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"market", "limit", "stop", "IOC", "FOK", "cancel", "amend", "l3"})
    int_units = False  # the tool's orders take float price / volume (rounded to 4 / 8 decimals)

    def start(self, inp):
        self.book = OrderBook(INST, EX, callback=lambda ev: None)
        self.orders = {}  # key -> Order
        self.key_of = {}  # id(Order) -> key

    def _new(self, key, side, px, qty, otype, flag=OrderFlag.NONE, stop_target=None):
        o = Order(float(qty), float(px), SIDE[side], INST, EX, order_type=otype, flag=flag, stop_target=stop_target)
        self.orders[key] = o
        self.key_of[id(o)] = key
        return o

    def _run(self, key, o):
        before = {k: x.filled for k, x in self.orders.items()}
        self.book.add(o)
        out = []
        for k, x in self.orders.items():
            d = x.filled - before.get(k, 0.0)
            if k != key and d > 1e-12:
                out.append((k, key, x.price, d))
        return out

    def limit(self, key, side, px, qty, mine, stp):
        return self._run(key, self._new(key, side, px, qty, OrderType.LIMIT))

    def market(self, key, side, qty, mine, stp):
        return self._run(key, self._new(key, side, 0.0, qty, OrderType.MARKET))

    def ioc(self, key, side, px, qty, mine, stp):
        return self._run(key, self._new(key, side, px, qty, OrderType.LIMIT, OrderFlag.IMMEDIATE_OR_CANCEL))

    def fok(self, key, side, px, qty, mine, stp):
        return self._run(key, self._new(key, side, px, qty, OrderType.LIMIT, OrderFlag.FILL_OR_KILL))

    def stop(self, key, side, stop_px, qty, mine, stp):
        target = self._new(key, side, 0.0, qty, OrderType.MARKET)
        holder = Order(float(qty), float(stop_px), SIDE[side], INST, EX, order_type=OrderType.STOP, stop_target=target)
        before = {k: x.filled for k, x in self.orders.items()}
        self.book.add(holder)
        return [(k, key, x.price, x.filled - before.get(k, 0.0)) for k, x in self.orders.items()
                if k != key and x.filled - before.get(k, 0.0) > 1e-12]

    def cancel(self, key):
        o = self.orders.get(key)
        if o is None or not self.resting(key):
            return False
        self.book.cancel(o)
        return not self.resting(key)

    def amend(self, key, px, new_left, left):
        o = self.orders[key]
        if abs(float(px) - o.price) > 1e-9:
            raise NotExpressible(f"{TOOL}: 価格の変更の口が無い(change は数量だけを変える)")
        if new_left is not None:
            o.volume = o.filled + float(new_left)
            self.book.change(o)
        return []

    def resting(self, key):
        o = self.orders.get(key)
        return o is not None and any(x is o for x in self.book)


class Adapter:
    name = "opp_aat"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
