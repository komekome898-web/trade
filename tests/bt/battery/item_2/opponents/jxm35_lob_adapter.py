"""Survey candidates 104 `jxm35/LimitOrderBook-MatchingEngine` (git clone, commit b5984aac, item 0's _dl/c104)
and 96 `sashankzade/limit-order-book-matching-engine` (git clone, commit 0adba7b, venvs/item_2/src/c96; its
matching core lib/OrderBook/src/core/OrderBook.cpp is byte-identical to 104's, `cmp` 2026-09-25) for the
item 2 battery.

Driven through a line-command driver (venvs/item_2/drivers/i2drv104.cpp) compiled from each tool's own sources
(OrderBook, OrderBookEntry, Order, OrderCore, Security, MDFeed MarketDataPublisher) with the real spdlog headers
(gabime/spdlog, commit 5b63780, header only) and one substitute header for boost::lockfree::spsc_queue (the
market-data ring buffer type; the matching core never uses the buffer) plus item 0's boost::optional =
std::optional substitute.  The driver calls only `OrderBook::AddOrder / PlaceMarketBuyOrder /
PlaceMarketSellOrder / RemoveOrder / AmendOrder`; a match is read from the tool's own spdlog::debug lines
("<side> order <id> filled @ <price> pence", incoming then resting) and the resting order's quantity drop
through the public `GetOrders()`.  The tool has limit, market, cancel and amend (AmendOrder = RemoveOrder +
AddOrder); no IOC, FOK, post-only, stop, fees, latency, notices or account; integer prices and uint32 sizes.
The scene -> engine mapping is lob_common's.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import lob_common as L  # noqa: E402
from i2_targets import VENV_ROOT  # noqa: E402


class Eng(L.PipeEngine):
    features = frozenset({"market", "limit", "cancel", "amend", "l3"})
    int_units = True

    def __init__(self, tool, exe):
        self.tool, self.exe = tool, exe

    def amend(self, key, px, new_left, left):
        # AmendOrder(orderId, Order(core, price, quantity, isBuy)) (OrderBook.cpp) = RemoveOrder + AddOrder; the
        # new order's quantity is what should rest: the new size left, or what is left now for a price-only amend
        side = self._side[key]
        q = int(left if new_left is None else new_left)
        return [] if self._cmd(f"A {self.key2id[key]} {side[0]} {int(px)} {q}")[1] == "1" else _raise()

    def limit(self, key, side, px, qty, mine, stp):
        self._side = getattr(self, "_side", {})
        self._side[key] = side
        return super().limit(key, side, px, qty, mine, stp)


def _raise():
    raise RuntimeError("AmendOrder threw (order id not found)")


class Adapter104:
    name = "opp_jxm35_lob"

    def run(self, inp):
        return L.run_lob(inp, Eng("jxm35/LimitOrderBook-MatchingEngine(b5984aac)",
                                  os.path.join(VENV_ROOT, "item_2/drivers/i2drv104")))


class Adapter96:
    name = "opp_sashankzade_lob"

    def run(self, inp):
        return L.run_lob(inp, Eng("sashankzade/limit-order-book-matching-engine(0adba7b)",
                                  os.path.join(VENV_ROOT, "item_2/drivers/i2drv96")))


TARGET = Adapter104()
TARGET_96 = Adapter96()
