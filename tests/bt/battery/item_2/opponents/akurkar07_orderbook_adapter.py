"""Survey candidate 101 `akurkar07/OrderBook` (git clone, commit 5673f66a, the library built with its own
CMake into item 0's _dl/c101/build/liborderbook_lib.a; install record: item 0 survey_results/attempts/101.log)
for the item 2 battery.

Driven through a line-command driver (venvs/item_2/drivers/i2drv101.cpp, compiled against that library) that
calls only `OrderBook::place_limit_order / place_market_order / cancel_order` and prints the returned `Fills`
(buy_order_id, sell_order_id, price, quantity).  The library has limit and market orders and cancel only
(no IOC, FOK, post-only, stop, amend, fees, latency, notices or account); Quantity is an unsigned integer.
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
    tool = "akurkar07/OrderBook(5673f66a)"
    features = frozenset({"market", "limit", "cancel", "l3"})
    int_units = True
    exe = os.path.join(VENV_ROOT, "item_2/drivers/i2drv101")


class Adapter:
    name = "opp_akurkar07_orderbook"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
