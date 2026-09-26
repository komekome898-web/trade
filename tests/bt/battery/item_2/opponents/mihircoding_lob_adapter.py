"""Survey candidate 98 `mihircoding/limitOrderBook` (git clone, commit 6cc0536, venv item_0/c98 with a .pth
to the clone; install record: item 0 survey_results/attempts/98.log) for the item 2 battery.

The tool's own calls used: `LimitOrderBook.add_limit_order / add_ioc_order / add_fok_order / market_order /
cancel` (price-time matching, trades printed at the maker's price), `StpPolicy` (self-trade prevention by
participant_id), `MessageBus` + `LatencyModel(base_us)` (actions run at sent + latency of the sender).
The scene -> engine mapping is lob_common's.  Latency: our orders are sent as participant "order", our cancels
as "cancel", the strategy's view of a labelled market event as "seen" (latency = the scene's feed latency),
market events as "market" (no latency); each with a constant LatencyModel.  The tool has no post-only,
no stop, no amend, no fee applied to trades (its FeeSchedule is per share and the book does not call it),
no notices, no account.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import lob_common as L  # noqa: E402

from src.latency import LatencyModel, MessageBus  # noqa: E402  (the tool, via the venv's .pth)
from src.order import Side, StpPolicy  # noqa: E402
from src.orderbook import LimitOrderBook  # noqa: E402

TOOL = "mihircoding/limitOrderBook(6cc0536)"
SIDE = {"buy": Side.BUY, "sell": Side.SELL}


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"market", "limit", "IOC", "FOK", "cancel", "stp", "l3",
                          "latency:order", "latency:cancel", "latency:feed"})
    int_units = False  # the book takes float prices (snapped to its 0.01 grid) and numeric sizes

    def start(self, inp):
        self.b = LimitOrderBook()
        self.id2key, self.key2id = {}, {}

    def _kw(self, mine, stp):
        if mine and stp:
            return {"participant_id": "me", "stp_policy": StpPolicy.CANCEL_NEWEST}
        return {"participant_id": "me" if mine else None}

    def _tr(self, trades, key):
        return [(self.id2key.get(t.maker_id, f"?{t.maker_id}"), key, t.price, t.quantity) for t in trades]

    def limit(self, key, side, px, qty, mine, stp):
        oid, trades = self.b.add_limit_order(SIDE[side], px, qty, **self._kw(mine, stp))
        self.id2key[oid], self.key2id[key] = key, oid
        return self._tr(trades, key)

    def ioc(self, key, side, px, qty, mine, stp):
        return self._tr(self.b.add_ioc_order(SIDE[side], px, qty, **self._kw(mine, stp)), key)

    def fok(self, key, side, px, qty, mine, stp):
        return self._tr(self.b.add_fok_order(SIDE[side], px, qty, **self._kw(mine, stp)), key)

    def market(self, key, side, qty, mine, stp):
        return self._tr(self.b.market_order(SIDE[side], qty, **self._kw(mine, stp)), key)

    def cancel(self, key):
        return self.b.cancel(self.key2id[key]) if key in self.key2id else False

    def schedule(self, jobs, inp):
        lat = inp.get("latency") or {}
        g = lambda k: float((lat.get(k) or {}).get("ns", 0)) / 1000.0  # noqa: E731
        bus = MessageBus({"order": LatencyModel(g("order")), "cancel": LatencyModel(g("cancel")),
                          "seen": LatencyModel(g("feed")), "market": LatencyModel(0.0)})
        base = min(t for t, _, _ in jobs)
        for t, who, fn in jobs:
            bus.send((t - base) / 1000.0, who, lambda fn=fn: fn(base + round(bus.now_us * 1000)))
        bus.drain()


class Adapter:
    name = "opp_mihircoding_lob"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
