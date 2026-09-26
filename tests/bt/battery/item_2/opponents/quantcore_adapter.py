"""Survey candidate 34 `SLMolenaar/QuantCore` (PyPI quantcore 1.0.0, C++20 core with a Python interface, venv
item_0/quantcore; install record: item 0 survey_results/attempts/34.log) for the item 2 battery.

The tool's own calls used: `BacktestEngine(initial_capital, ExecutionConfig{maker_fee, taker_fee, latency_ns,
slippage_pct})`, `add_tick_data(symbol, [TickData(symbol, timestamp_ns, price, quantity, aggressor_side)])`,
`set_position_sizer(FixedShares(n))`, `set_strategy`, `run()`; a `Strategy` subclass with `on_data`, `on_fill`
(FillEvent: order_id, side, quantity, price, commission, timestamp_ns), `on_rejected`, and the order calls
`generate_signal(symbol, SignalType.BUY/SELL, strength, ts)` (sized by the engine's position sizer) and
`generate_stop(symbol, side, stop_price, quantity, ts)`.  No limit order call (OrderType has MARKET, STOP,
STOP_LIMIT and time-in-force values; the strategy API has no limit order), no cancel, amend, post-only, IOC/FOK
call, notice, funding, swap, liquidation.

Scene -> tool: every trade print is a TickData (book snapshots have no tick form); actions are issued in on_data
of the tick chosen by i2_common.issue_schedule.  A market order: set_position_sizer(FixedShares(qty)) then
generate_signal(BUY / SELL, strength 1.0); a stop order: generate_stop(side, stop_px, qty).  latency_ns = the
scene's order latency (one latency; other latencies refused); maker_fee / taker_fee = the scene's rates;
slippage_pct 0.  Fills are the engine's FillEvents, attributed to the order whose call came in the same on_data
call order (order ids count up from 1 in call order).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import quantcore as qc  # noqa: E402  (the tool, in its venv)

TOOL = "QuantCore 1.0.0"


class Adapter:
    name = "opp_quantcore"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "stop"), events=("book", "trade"), latency=("order",),
               costs=("maker_rate", "taker_rate"), account=("cash",))
        lat = inp.get("latency") or {}
        c = inp["costs"]
        ec = qc.ExecutionConfig()
        ec.maker_fee = float(c.get("maker_rate", 0.0))
        ec.taker_fee = float(c.get("taker_rate", 0.0))
        ec.latency_ns = int((lat.get("order") or {}).get("ns", 0))
        ec.slippage_pct = 0.0
        trades = C.trades(inp)
        if not trades:
            raise NotExpressible(f"{TOOL}: tick にする約定が無い(板の写真は TickData に形が無い)")
        sched = C.issue_schedule([e["t"] for e in trades], inp["actions"])
        st = {"k": -1, "calls": [], "fills": [], "rej": []}
        try:
            eng = qc.BacktestEngine(float(inp["account"]["cash"]), ec)
            eng.add_tick_data("X", [qc.TickData("X", int(e["t"]), float(e["px"]), float(e["qty"]),
                                                qc.Side.BUY if e["aggressor"] == "buy" else qc.Side.SELL) for e in trades])
            eng.set_position_sizer(qc.FixedShares(1))

            class S(qc.Strategy):
                def on_data(self, ev):
                    st["k"] += 1
                    for a in sched.get(st["k"], []):
                        if a["type"] == "market":
                            eng.set_position_sizer(qc.FixedShares(float(a["qty"])))
                            self.generate_signal("X", qc.SignalType.BUY if a["side"] == "buy" else qc.SignalType.SELL,
                                                 1.0, ev.timestamp_ns)
                        else:
                            self.generate_stop("X", qc.Side.BUY if a["side"] == "buy" else qc.Side.SELL,
                                               float(a["stop_px"]), float(a["qty"]), ev.timestamp_ns)
                        st["calls"].append(a["ref"])

                def on_fill(self, f):
                    st["fills"].append(f)

                def on_rejected(self, *args):
                    st["rej"].append(args)

            eng.set_strategy(S("s"))
            eng.run()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        rec = {"orders": {}, "fills": []}
        for f in st["fills"]:
            i = int(f.order_id) - 1
            if 0 <= i < len(st["calls"]):
                ref = st["calls"][i]
                rec["fills"].append({"ref": ref, "t": int(f.timestamp_ns), "px": float(f.price), "qty": float(f.quantity),
                                     "fee": float(f.commission), "liq": None})
        for ref in st["calls"]:
            q = sum(x["qty"] for x in rec["fills"] if x["ref"] == ref)
            want = float(next(a["qty"] for a in C.places(inp) if a["ref"] == ref))
            rec["orders"][ref] = {"status": "filled" if q >= want - 1e-12 else ("open" if q == 0 else "canceled")}
        return rec


TARGET = Adapter()
