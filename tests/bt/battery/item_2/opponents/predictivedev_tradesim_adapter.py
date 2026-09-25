"""Survey candidate 37 `ThePredictiveDev/Automated-Financial-Market-Trading-System` (package trading_simulator 2.2.0,
venv item_0/c37; install record: item 0 survey_results/attempts/37.log) for the item 2 battery.

The tool's own calls used: `MatchingEngine(OrderBook())` with `submit_order(Order(...))` (limit / market, tif GTC /
IOC / FOK, post_only), `cancel_order`, `OrderBook.modify_order` (amend = remove and re-add), `subscribe_trades`
(its Execution records: price, quantity, taker / maker order and owner ids), its self-trade prevention (resting
orders of the incoming order's owner_id are skipped, always on), its latency (`latency_ms`, integer milliseconds:
an incoming order is held until set_time + latency and matched by `process_delayed_orders`), and its
`Portfolio(fee_bps, maker_rebate_bps, owner_id)` for the fee of each of our fills (fee = the portfolio's cash change
minus the fill's notional) and for our account (a Portfolio fed with our fills relabelled to one owner: position,
realized_pnl, and equity(prices) at the scene's last print minus cash minus position x avg_price = unrealized).
The scene -> engine mapping is lob_common's.  Owner ids: every external order has its own owner; our orders share
owner "me" when the scene asks for self-trade prevention, otherwise each has its own (so the tool's always-on
prevention acts only when the scene asks for it).  The tool's latency applies to every incoming order, so it is set to
0 while market events are entered and to the scene's order latency while our orders are entered.  The tool has no
feed / cancel / notice latency, no stop orders, and its instrument registry is left unconfigured (a configured symbol
gets session hours); prices go in as integer ticks, sizes as integer lots.  Impact: the tool's
`slippage_bps_per_100_shares` (fill price x (1 + bps x max(1, fill lots / 100) / 1e4), on our orders only) takes the
scene's linear temporary impact with basis best_ask: lots of 1/100 of the scene's unit and bps = k x unit x 1e4 /
best ask at our first action; other impact kinds are refused.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import lob_common as L  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

from trading_simulator.core.matching_engine import MatchingEngine  # noqa: E402  (the tool)
from trading_simulator.core.order import Order  # noqa: E402
from trading_simulator.core.order_book import OrderBook  # noqa: E402
from trading_simulator.portfolio.portfolio import Portfolio  # noqa: E402

TOOL = "trading_simulator 2.2.0"
SYM = "X"


class Eng(L.Engine):
    tool = TOOL
    features = frozenset({"market", "limit", "IOC", "FOK", "post_only", "cancel", "amend", "stp", "l3", "latency:order"})
    costs = ("maker_rate", "taker_rate")

    def fill_model_ok(self, fm, inp):
        imp = fm.get("impact") or {}
        if fm.get("tier") == 6 and "range" not in fm and imp.get("kind") == "linear_temporary" and imp.get("basis") == "best_ask":
            return None
        if "impact" in fm and "range" not in fm:
            return (f"市場影響 {imp.get('kind')}(基準 {imp.get('basis')})を渡す口が無い"
                    "(この道具の市場影響は約定値の bps × 量の一次の一時的な滑りだけで、恒久の影響も平方根の形も無い)")
        return super().fill_model_ok(fm, inp)

    def _impact(self, inp):
        fm = inp.get("fill_model") or {}
        return (fm.get("impact") or {}) if fm.get("tier") == 6 else {}

    def unit(self, inp):
        # the tool's slippage is bps_per_100_shares * max(1, fill_qty / 100): lots of 1/100 of the scene's unit keep
        # every fill at >= 100 lots, where it is linear in the fill size
        return L.qty_unit(inp) / 100 if self._impact(inp) else L.qty_unit(inp)

    def start(self, inp):
        self.book = OrderBook()
        self.me = MatchingEngine(self.book)
        self.buf = []
        self.me.subscribe_trades(self.buf.append)
        c = inp.get("costs") or {}
        self.rates = (float(c.get("taker_rate", 0.0)), float(c.get("maker_rate", 0.0)))
        self.pf = {}
        self.mine = set()
        self.acct = Portfolio(initial_cash=0.0, owner_id="me")  # our account: our fills relabelled to one owner
        ns = float(((inp.get("latency") or {}).get("order") or {}).get("ns", 0))
        if ns % 1_000_000:
            raise NotExpressible(f"{TOOL}: 遅延は整数ミリ秒だけ渡せる(latency_ms)。{ns} ns は渡せない")
        self.lat_ms = int(ns // 1_000_000)
        self.slip = 0.0
        imp = self._impact(inp)
        if imp:
            # the scene's impact k (JPY per unit of quantity, on top of the best ask) in the tool's unit
            # (bps of the fill's base price per 100 lots), with the base = the scene's best ask at our action
            ours = [a for a in inp["actions"] if a.get("op") == "place"]
            asks = [e for e in inp["market"] if e["type"] == "book" and e["t"] <= ours[0]["t"]][-1]["asks"]
            self.slip = imp["k"] * L.qty_unit(inp) * 1e4 / asks[0][0]

    def _owner(self, key, mine, stp):
        return "me" if (mine and stp) else f"o:{key}"

    def _fees(self, ex):
        out = {}
        for key, owner in ((ex.taker_order_id, ex.taker_owner_id), (ex.maker_order_id, ex.maker_owner_id)):
            if key not in self.mine:
                continue
            pf = self.pf.setdefault(owner, Portfolio(initial_cash=0.0, fee_bps=self.rates[0] * 1e4,
                                                     maker_rebate_bps=-self.rates[1] * 1e4, owner_id=owner))
            before = pf.cash
            pf.on_execution(ex)
            is_taker = key == ex.taker_order_id
            eff = ex.side if is_taker else ("sell" if ex.side == "buy" else "buy")
            signed = ex.quantity * ex.price if eff == "buy" else -ex.quantity * ex.price
            out[key] = -(pf.cash - before) - signed
            rel = {"taker_owner_id": "me", "maker_owner_id": "-"} if is_taker else {"taker_owner_id": "-", "maker_owner_id": "me"}
            self.acct.on_execution(dataclasses.replace(ex, **rel))
        return out

    def _drain(self):
        fl = [(ex.maker_order_id, ex.taker_order_id, ex.price, ex.quantity, self._fees(ex)) for ex in self.buf]
        self.buf.clear()
        return fl

    def _submit(self, key, side, typ, px, qty, mine, stp, tif="GTC", post=False):
        if mine:
            self.mine.add(key)
        self.me.latency_ms = self.lat_ms if mine else 0
        self.me.slippage_bps_per_100_shares = self.slip if mine else 0.0
        o = Order(id=key, price=float(px or 0.0), quantity=int(qty), side=side, type=typ, symbol=SYM, tif=tif,
                  post_only=post, owner_id=self._owner(key, mine, stp))
        self.me.submit_order(o)
        self.me.latency_ms = 0
        self.me.slippage_bps_per_100_shares = 0.0
        return self._drain()

    def limit(self, key, side, px, qty, mine, stp):
        return self._submit(key, side, "limit", px, qty, mine, stp)

    def market(self, key, side, qty, mine, stp):
        return self._submit(key, side, "market", None, qty, mine, stp)

    def ioc(self, key, side, px, qty, mine, stp):
        return self._submit(key, side, "limit", px, qty, mine, stp, tif="IOC")

    def fok(self, key, side, px, qty, mine, stp):
        return self._submit(key, side, "limit", px, qty, mine, stp, tif="FOK")

    def post_only(self, key, side, px, qty, mine, stp):
        return self._submit(key, side, "limit", px, qty, mine, stp, post=True)

    def cancel(self, key):
        had = key in self.book.order_map
        self.me.cancel_order(key)
        return had and key not in self.book.order_map

    def amend(self, key, px, new_left, left):
        self.book.modify_order(key, new_quantity=new_left, new_price=float(px))
        return self._drain()

    def account_out(self, inp, tick, step):
        if (inp.get("rules") or {}).get("mark", "last_trade") != "last_trade":
            return None
        prints = [e["px"] for e in inp["market"] if e["type"] == "trade"]
        pos = self.acct.positions.get(SYM, 0)
        out = {"position": pos * step, "realized": self.acct.realized_pnl * tick * step}
        if prints:
            mark = prints[-1] / tick  # the scene's last print (the tool's equity() takes the caller's prices)
            eq = self.acct.equity({SYM: mark})
            out["unrealized"] = (eq - self.acct.cash - pos * self.acct.avg_price.get(SYM, 0.0)) * tick * step
        return out

    def resting(self, key):
        return key in self.book.order_map

    def schedule(self, jobs, inp):
        ts = lambda t: pd.Timestamp(int(t), unit="ns", tz="UTC")  # noqa: E731

        def release(upto):
            while self.me._delayed_orders:
                at = min(a for a, _ in self.me._delayed_orders)
                if at > ts(upto):
                    break
                t_at = at.value
                self.me.set_time(at)
                self.me.process_delayed_orders(at)
                self.emit(self._drain(), t_at)

        for t, _who, fn in jobs:
            release(t)
            self.me.set_time(ts(t))
            fn(t)
        release(max(t for t, _, _ in jobs) + 10**15)


class Adapter:
    name = "opp_predictivedev_tradesim"

    def run(self, inp):
        return L.run_lob(inp, Eng())


TARGET = Adapter()
