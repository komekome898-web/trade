"""Survey candidate 33 `SarthakDalmia1/backtesting_execution_simulator` (C++, commit a0a5fcd2, library built with
its own CMake in item 0's _dl/c33/build/libbacktesting_engine.a; install record: item 0
survey_results/attempts/33.log) for the item 2 battery.

Driven through a script driver (venvs/item_2/drivers/i2drv33.cpp) against the tool's public C++ API:
ExecutionSimulator(BacktestConfig{latency: order_submit / order_cancel / market_data / fill_report (ns),
initial_capital, max_position_size, enable_margin, margin_requirement}), set_cost_model(PercentageCostModel(
maker_bps, taker_bps)), set_event_callback, clock(), submit_order / cancel_order (the tool adds its latency),
add_tick, run_until, matching_engine().  Order types the tool has: Market, Limit, StopMarket, StopLimit, IOC,
FOK (core/types.hpp 173-181); no post-only, reduce-only, OCO or amend; no funding, swap, fee table, liquidation.

Scene -> tool:
- external liquidity goes into the tool's matching engine directly (the engine takes no market data; the tool's
  own demo seeds it the same way): lob_common's rule -- a level's external quantity is brought to the snapshot's
  (a shrinking level that stays is refused), a trade print is an external IOC at its price and size;
- our orders: submit_order at the scene time (clock().set_time), so the tool's order_submit latency applies;
  cancels: cancel_order (order_cancel latency) of the order the engine holds under our ref (strategy_id);
- latency: feed -> market_data_latency_ns, order -> order_submit_latency_ns, cancel -> order_cancel_latency_ns,
  notice -> fill_report_latency_ns (the tool reports only fills with a latency); no latency = 0 (the scene
  declares none; the tool's own defaults are 1000 / 1000 / 500 / 500 ns);
- costs: maker_rate / taker_rate as PercentageCostModel bps (rate x 10,000), none = the tool's zero cost model;
- account: initial_capital = cash, max_position_size = cash x leverage (the scene's buying power; the tool's
  default 1,000,000 is a limit the scene does not state), margin on with margin_requirement = 1 / leverage when
  leverage != 1.  The tool's position manager also takes the external orders' fills (one book, one account per
  symbol), so its position and P&L are not reported.
Observations are the tool's callback events: fills (price, size, cost, maker flag; time = the fill's own
timestamp), notices (ack = the OrderSubmit event, reject = OrderReject, fill = OrderFill event time, cancel =
OrderCancel), and each order's final status from the engine.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
import lob_common as L  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402
from i2_targets import VENV_ROOT  # noqa: E402

TOOL = "SarthakDalmia1/backtesting_execution_simulator(a0a5fcd2)"
EXE = os.path.join(VENV_ROOT, "item_2/drivers/i2drv33")
STATUS = {"0": "open", "1": "open", "2": "filled", "3": "canceled", "4": "rejected", "5": "canceled"}


class _E(L.Engine):
    tool = TOOL


class Adapter:
    name = "opp_sarthak_execsim"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "IOC", "FOK", "cancel"), events=("book", "trade"),
               fill_models=lambda fm: L._fill_model_ok(fm, inp, _E()), latency=("feed", "order", "cancel", "notice"),
               costs=("maker_rate", "taker_rate"), account=("cash", "leverage"))
        lat = inp.get("latency") or {}
        g = lambda k: int((lat.get(k) or {}).get("ns", 0))  # noqa: E731
        c, acc = inp["costs"], inp["account"]
        lev = float(acc.get("leverage", 1.0))
        cash = float(acc["cash"])
        lines = [f"CFG {g('order')} {g('cancel')} {g('feed')} {g('notice')} {float(c.get('maker_rate', 0.0)) * 1e4!r} "
                 f"{float(c.get('taker_rate', 0.0)) * 1e4!r} {cash!r} {cash * lev!r} {int(lev != 1.0)} {1.0 / lev!r}"]
        labels = []
        ext = {"b": {}, "s": {}}
        for t, kind, x in C.timeline(inp):
            if kind == "m":
                if x["type"] == "book":
                    for side, key in (("b", "bids"), ("s", "asks")):
                        new = {float(p): float(q) for p, q in x[key]}
                        for p in sorted(set(ext[side]) | set(new)):
                            lines.append(f"BOOK {t} {side} {p!r} {new.get(p, 0.0)!r}")
                        ext[side] = new
                elif x["type"] == "trade":
                    lines.append(f"EXTIOC {t} {x['aggressor'][0]} {float(x['px'])!r} {float(x['qty'])!r}")
                if x.get("label"):
                    lines.append(f"TICK {t}")
                    labels.append(x["label"])
            elif x["op"] == "place":
                typ = {"market": "M", "limit": "L", "stop": "SM"}[x["type"]]
                if x["tif"] in ("IOC", "FOK"):
                    typ = x["tif"]
                px = x["px"] if x["px"] is not None else 0.0
                stop = x["stop_px"] if x["stop_px"] is not None else 0.0
                lines.append(f"PLACE {t} {x['ref']} {x['side'][0]} {typ} {float(px)!r} {float(stop)!r} {float(x['qty'])!r}")
            elif x["op"] == "cancel":
                lines.append(f"CANCEL {t} {x['ref']}")
        lines.append(f"END {inp['end_t']}")
        try:
            r = subprocess.run([EXE], input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=60)
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        out = r.stdout.splitlines()
        if any(ln.startswith("ERR partial") for ln in out):
            ln = next(ln for ln in out if ln.startswith("ERR"))
            raise NotExpressible(f"{TOOL}: 板の写真で値位の量が減った({ln})。どの注文が抜けたかを写真は言わず、照合の機関は名指しの取消しか受けない")
        if r.returncode != 0:
            raise Refused(f"driver rc={r.returncode}: {r.stderr[-300:]}")
        rec = {"orders": {}, "fills": [], "notices": {}, "seen": {}}
        mds = [ln for ln in out if ln.startswith("MD ")]
        for lab, ln in zip(labels, mds):
            rec["seen"][lab] = int(ln.split()[1])
        pending = [a["ref"] for a in sorted(C.places(inp), key=lambda a: a["t"])]
        subs = {}
        for ln in out:
            p = ln.split()
            if p[0] == "SUB":
                subs[p[2]] = int(p[1])
                rec["notices"].setdefault(p[2], {}).setdefault("ack", int(p[1]))
            elif p[0] == "FILL":
                ref = p[2]
                rec["fills"].append({"ref": ref, "t": int(p[7]), "px": float(p[3]), "qty": float(p[4]), "fee": float(p[5]),
                                     "liq": "maker" if p[6] == "1" else "taker"})
                rec["notices"].setdefault(ref, {}).setdefault("fill", int(p[1]))
            elif p[0] == "REJ":
                # the tool's reject event carries order id 0; it is raised while the submit that arrives at that
                # time is processed, so it belongs to the one order whose submit has not been acknowledged
                cand = [x for x in pending if x not in subs and x not in rec["orders"]]
                if cand:
                    rec["orders"][cand[0]] = {"status": "rejected"}
                    rec["notices"].setdefault(cand[0], {})["reject"] = int(p[1])
            elif p[0] == "ORD":
                ref = p[1]
                if ref not in rec["orders"]:
                    rec["orders"][ref] = {"status": STATUS.get(p[2], "rejected" if p[2] == "none" else p[2])}
        return rec


TARGET = Adapter()
