"""Reproduction of candidate 33 `SarthakDalmia1/backtesting_execution_simulator`
(C++, not on PyPI) for viewpoint P0-7 (plug-in points for the fill / latency /
cost / account models), written as the smallest rewrite of its primary source.

Primary source (read only, fetched 2026-09-23 from
https://raw.githubusercontent.com/SarthakDalmia1/backtesting_execution_simulator/main/<path>):
  [ES.hpp]  cpp/execution/execution_simulator.hpp
  [ES.cpp]  cpp/execution/execution_simulator.cpp
  [SM.hpp]  cpp/execution/slippage_model.hpp
  [SM.cpp]  cpp/execution/slippage_model.cpp
  [TC.hpp]  cpp/execution/transaction_costs.hpp
  [EQ.hpp]  cpp/events/event_queue.hpp
  [EV.hpp]  cpp/events/event.hpp
  [ME.cpp]  cpp/orderbook/matching_engine.cpp
  [TY.hpp]  cpp/core/types.hpp
  [DEMO]    examples/demo.py
Also transcribed in docs/DATA/SCAN_2026-09-21_tools.md lines 7189, 7255, 9012.

Each piece below cites the source line it rewrites. Nothing is added that the
source does not have, and nothing is weakened. Only the P0-7 mechanism is
rewritten (event queue, submit/cancel latency, the slippage and cost model
setters, the fill path and the matching of a market order against resting
orders); the scenes of other viewpoints answer `not_supported` because this
candidate is in the pool for P0-7 only.

Values the source does not fix and how they are set here:
- equal timestamps in the event queue: [EV.hpp] 163-166 orders by timestamp
  only (a std::priority_queue, no tie rule). Here ties keep push order; the P0-7
  scenes do not depend on the tie (see each scene's detail).
- liquidity: [ES.cpp] 104-112 does not put market data into the matching
  engine; resting orders come only from `matching_engine().submit_order`
  ([DEMO] demo_order_submission puts a resting order in first). The adapter
  does the same: one resting sell order at the first trade's price and
  quantity before the run.
"""
from __future__ import annotations

import heapq
import itertools
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from protocol import SCENES, _Abstract, method_name, not_supported, ok  # noqa: E402
import common as C  # noqa: E402


# [TY.hpp] 336-343 LatencyConfig and its defaults
@dataclass
class LatencyConfig:
    order_submit_latency_ns: int = 1000
    order_cancel_latency_ns: int = 1000
    market_data_latency_ns: int = 500
    fill_report_latency_ns: int = 500


# [TY.hpp] 348-359 BacktestConfig (the fields the P0-7 path reads)
@dataclass
class BacktestConfig:
    start_time: int = 0
    initial_capital: float = 1_000_000.0
    latency: LatencyConfig = field(default_factory=LatencyConfig)
    enable_short_selling: bool = True
    max_position_size: float = 1_000_000.0
    enable_margin: bool = False
    margin_requirement: float = 0.5


# [SM.hpp] 11-33 SlippageModel: calculate_slippage is the plug, get_execution_price adds it
class SlippageModel:
    def calculate_slippage(self, base_price, order_qty, available_qty, side, volatility=0.0, avg_daily_volume=0.0):
        raise NotImplementedError

    def get_execution_price(self, base_price, order_qty, available_qty, side, volatility=0.0, avg_daily_volume=0.0):
        # [SM.cpp] 5-16: base_price + calculate_slippage(...)
        return base_price + self.calculate_slippage(base_price, order_qty, available_qty, side, volatility, avg_daily_volume)


class ZeroSlippageModel(SlippageModel):  # [SM.hpp] 39-49, [SM.cpp] 18-27
    def calculate_slippage(self, *a, **k):
        return 0.0


# [TC.hpp] 13-24 TransactionCostModel: calculate_cost(notional, quantity, is_maker, symbol)
class TransactionCostModel:
    def calculate_cost(self, notional, quantity, is_maker, symbol):
        raise NotImplementedError


class ZeroCostModel(TransactionCostModel):  # [ES.cpp] 9 default cost model
    def calculate_cost(self, notional, quantity, is_maker, symbol):
        return 0.0


@dataclass
class Event:
    ts: int
    kind: str
    data: dict


class EventQueue:
    """[EQ.hpp] 17-56 time-ordered priority queue (min-heap on the timestamp, [EV.hpp] 163-166)."""

    def __init__(self):
        self._h, self._n = [], itertools.count()

    def push(self, ev: Event):
        heapq.heappush(self._h, (ev.ts, next(self._n), ev))

    def pop(self):
        return heapq.heappop(self._h)[2] if self._h else None

    def empty(self):
        return not self._h


class MatchingEngine:
    """[ME.cpp] 16-50 submit_order, 105-116 market order, 183-250 match against the book at the passive price."""

    def __init__(self):
        self.asks: list[dict] = []   # resting sell orders, price-time priority
        self.bids: list[dict] = []
        self.orders: dict[int, dict] = {}
        self.ids = itertools.count(1)
        self.now = 0
        self.fill_callback = None

    def submit_order(self, req: dict) -> dict:
        o = {"id": next(self.ids), **req, "remaining": req["quantity"], "status": "New", "submit_time": self.now}
        self.orders[o["id"]] = o
        if o["type"] == "Market":           # [ME.cpp] 40-41, 105-116
            self._match(o, self.asks if o["side"] == "Buy" else self.bids)
            if o["remaining"] > 0:
                o["status"] = "Cancelled"      # [ME.cpp] 112-115
        else:                                # Limit: [ME.cpp] 118-135 (match, then rest)
            self._match(o, self.asks if o["side"] == "Buy" else self.bids)
            if o["remaining"] > 0:
                book = self.bids if o["side"] == "Buy" else self.asks
                book.append(o)
                book.sort(key=lambda x: (-x["price"] if x["side"] == "Buy" else x["price"], x["submit_time"]))
        return o

    def cancel_order(self, oid: int) -> bool:
        o = self.orders.get(oid)
        if not o or o["remaining"] <= 0 or o["status"] == "Cancelled":
            return False
        for book in (self.asks, self.bids):
            if o in book:
                book.remove(o)
        o["status"] = "Cancelled"
        return True

    def _match(self, agg: dict, side: list[dict]):
        while agg["remaining"] > 0 and side:
            passive = side[0]
            if agg["type"] == "Limit" and ((agg["side"] == "Buy" and agg["price"] < passive["price"]) or
                                           (agg["side"] == "Sell" and agg["price"] > passive["price"])):
                break                          # [ME.cpp] 189-201
            q = min(agg["remaining"], passive["remaining"])
            px = passive["price"]              # [ME.cpp] 210 "Price-time priority"
            agg["remaining"] -= q
            passive["remaining"] -= q
            if self.fill_callback:             # [ME.cpp] 238-241 aggressor fill, then passive fill
                self.fill_callback({"order_id": agg["id"], "timestamp": self.now, "fill_price": px, "fill_quantity": q,
                                    "side": agg["side"], "is_maker": False})
                self.fill_callback({"order_id": passive["id"], "timestamp": self.now, "fill_price": px, "fill_quantity": q,
                                    "side": passive["side"], "is_maker": True})
            if passive["remaining"] <= 0:
                side.pop(0)


class ExecutionSimulator:
    """[ES.hpp] 26-113 / [ES.cpp] 1-262."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.now = config.start_time                         # [ES.cpp] 7 clock_(config.start_time)
        self.slippage_model: SlippageModel = ZeroSlippageModel()   # [ES.cpp] 8
        self.cost_model: TransactionCostModel = ZeroCostModel()    # [ES.cpp] 9
        self.cash = config.initial_capital                   # [ES.cpp] 10 position_manager_(initial_capital)
        self.positions: dict[str, float] = {}
        self.event_queue = EventQueue()
        self.matching_engine = MatchingEngine()
        self.matching_engine.fill_callback = self._on_fill    # [ES.cpp] 16-17
        self.event_callback = None

    # [ES.hpp] 33-44 the three setters: the only plug-in points
    def set_slippage_model(self, model: SlippageModel):
        self.slippage_model = model

    def set_cost_model(self, model: TransactionCostModel):
        self.cost_model = model

    def set_event_callback(self, cb):
        self.event_callback = cb

    def submit_order(self, request: dict):
        # [ES.cpp] 24-33: the order becomes an event at now + order_submit_latency_ns
        self.event_queue.push(Event(self.now + self.config.latency.order_submit_latency_ns, "OrderSubmit", {"request": request}))
        return None

    def cancel_order(self, order_id: int) -> bool:
        # [ES.cpp] 35-43
        self.event_queue.push(Event(self.now + self.config.latency.order_cancel_latency_ns, "OrderCancel", {"order_id": order_id}))
        return True

    def add_tick(self, tick: dict):
        # [ES.cpp] 45-57: market data arrives at timestamp + market_data_latency_ns
        self.event_queue.push(Event(tick["timestamp"] + self.config.latency.market_data_latency_ns, "MarketData", {"tick": tick}))

    def process_next_event(self) -> bool:
        # [ES.cpp] 59-77
        ev = self.event_queue.pop()
        if ev is None:
            return False
        self.now = ev.ts
        self.matching_engine.now = ev.ts
        getattr(self, "_process_" + ev.kind)(ev)
        return True

    def run(self):
        # [ES.cpp] 94-102
        while not self.event_queue.empty():
            self.process_next_event()

    def _notify(self, ev: Event):
        if self.event_callback:
            self.event_callback(ev)

    def _process_MarketData(self, ev):        # [ES.cpp] 104-112
        self._notify(ev)

    def _process_OrderSubmit(self, ev):       # [ES.cpp] 114-133
        req = ev.data["request"]
        if not self._validate(req):
            self._notify(Event(self.now, "OrderReject", {"reason": "Order validation failed"}))
            return
        order = self.matching_engine.submit_order(req)
        ev.data["order_id"] = order["id"]
        self._notify(ev)

    def _process_OrderCancel(self, ev):       # [ES.cpp] 135-143
        ev.data["success"] = self.matching_engine.cancel_order(ev.data["order_id"])
        self._notify(ev)

    def _process_OrderFill(self, ev):         # [ES.cpp] 145-149
        self._notify(ev)

    def _on_fill(self, fill: dict):
        # [ES.cpp] 187-224
        price = self.slippage_model.get_execution_price(fill["fill_price"], fill["fill_quantity"], 10000, fill["side"], 0.02, 1_000_000.0)
        notional = price * fill["fill_quantity"]
        cost = self.cost_model.calculate_cost(notional, fill["fill_quantity"], fill["is_maker"], "")
        sign = 1 if fill["side"] == "Buy" else -1
        sym = self.matching_engine.orders[fill["order_id"]]["symbol"]
        self.positions[sym] = self.positions.get(sym, 0.0) + sign * fill["fill_quantity"]
        self.cash -= sign * notional + cost
        adjusted = dict(fill, fill_price=price)
        self.event_queue.push(Event(self.now + self.config.latency.fill_report_latency_ns, "OrderFill",
                                    {"fill": adjusted, "cost": cost}))

    def _validate(self, req) -> bool:
        # [ES.cpp] 235-260
        notional = req.get("price", 0.0) * req["quantity"]
        if notional > self.config.max_position_size:
            return False
        if not self.config.enable_short_selling and req["side"] == "Sell" and req["quantity"] > self.positions.get(req["symbol"], 0.0):
            return False
        if self.config.enable_margin and notional * self.config.margin_requirement > self.cash:
            return False
        return True


# ---------------------------------------------------------------- the adapter

OUT_OF_SCOPE = ("再現の範囲外: 候補 33 は P0-7 の候補(pool.tsv)で、この再現は P0-7 の機構(事象の列・発注と取消の遅延・"
                "滑りと費用の模型の setter・約定の道)だけを一次資料から書き直した")


def _market_run(sc, *, latency=None, slippage=None, cost=None, capital=100_000.0):
    """Run the scene: seed one resting sell order at the first trade's price and
    size ([DEMO] demo_order_submission), hand every trade to add_tick, and on the
    first MarketData event submit a market buy of quantity 1."""
    evs = C.events(sc)
    sim = ExecutionSimulator(BacktestConfig(start_time=evs[0]["ts_ns"], initial_capital=capital,
                                            latency=latency or LatencyConfig()))
    if slippage is not None:
        sim.set_slippage_model(slippage)
    if cost is not None:
        sim.set_cost_model(cost)
    sim.matching_engine.submit_order({"symbol": "X", "side": "Sell", "type": "Limit", "price": float(evs[0]["price"]),
                                      "quantity": float(evs[0]["qty"])})
    seen, state = [], {"sent": False, "mine": None}

    def cb(ev):
        seen.append((ev.kind, ev.ts))
        if ev.kind == "MarketData" and not state["sent"]:
            state["sent"] = True
            sim.submit_order({"symbol": "X", "side": "Buy", "type": "Market", "price": 0.0, "quantity": 1.0})
        if ev.kind == "OrderSubmit":
            state["mine"] = ev.data["order_id"]
        if ev.kind == "OrderFill" and ev.data["fill"]["order_id"] == state["mine"]:
            state.setdefault("fills", []).append((ev.ts, ev.data["fill"], ev.data["cost"]))

    sim.set_event_callback(cb)
    for e in evs:
        sim.add_tick({"symbol": "X", "timestamp": int(e["ts_ns"]), "price": float(e["price"]), "qty": float(e["qty"])})
    sim.run()
    return sim, state, seen


class Adapter(_Abstract):
    name = "repro_33_execution_simulator"

    def _out(self, sc):
        return not_supported(OUT_OF_SCOPE)

    def scene_p7_fill_model_swap(self, sc):
        class Fixed(SlippageModel):
            def calculate_slippage(self, base_price, *a, **k):
                return 12345.0 - base_price

        _, st, _ = _market_run(sc, slippage=Fixed())
        f = st.get("fills", [])
        return ok({"fill_price": f[0][1]["fill_price"] if f else None},
                  "set_slippage_model(<SlippageModel の子: calculate_slippage が 12345 - base_price>)。get_execution_price = "
                  f"base + slippage([SM.cpp] 5-16)。遅延は既定の値([TY.hpp] 337-340)。自分の注文の約定 {f}")

    def scene_p7_latency_model_swap(self, sc):
        _, st, seen = _market_run(sc, latency=LatencyConfig(order_submit_latency_ns=7_000_000, order_cancel_latency_ns=0,
                                                            market_data_latency_ns=0, fill_report_latency_ns=0))
        f = st.get("fills", [])
        return ok({"fill_time_ns": f[0][1]["timestamp"] if f else None},
                  "BacktestConfig.latency(order_submit_latency_ns=7,000,000、ほかは 0)。遅延は模型の差し替えではなく設定の値"
                  "([TY.hpp] 336-343。deterministic の旗と latency_stddev_factor は在るが、[ES.cpp] 26 は平均の値だけを足す)。"
                  f"約定の時刻は Fill.timestamp。自分の注文の約定 {f}。事象の列 {seen[:6]}…")

    def _fee(self, sc, fee):
        class Flat(TransactionCostModel):
            def calculate_cost(self, notional, quantity, is_maker, symbol):
                return fee

        _, st, _ = _market_run(sc, cost=Flat())
        f = st.get("fills", [])
        return ok({"fee": f[0][2] if f else None}, f"set_cost_model(<TransactionCostModel の子: 1 件 {fee}>)。OrderFillEvent の cost "
                  f"([ES.cpp] 198-221)。遅延は既定の値。自分の注文の約定 {f}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_zero(self, sc):
        return self._fee(sc, 0.0)

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(PositionManager / PnLTracker)は ExecutionSimulator の中で config から作られ([ES.cpp] 10-11)、"
                             "差し替える setter が無い(setter は set_slippage_model / set_cost_model / set_event_callback の 3 つだけ、"
                             "[ES.hpp] 33-44)")


for _s in SCENES:
    if not _s.id.startswith("p7-"):
        setattr(Adapter, method_name(_s.id), Adapter._out)
