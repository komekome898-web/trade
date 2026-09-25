"""Survey candidate 61 `barter-rs` (crates barter 0.14 / barter-data 0.13 / barter-execution 0.9) for the item 2
battery, through the Rust driver item 0 built as a member of the tool's workspace (venv item_0/c61, binary
bin/c61_driver; its source and build record: tests/bt/battery/item_0/survey_results/attempts/61.log).

The driver runs the tool's `backtest::backtest` over `MarketDataInMemory` (the scene's trade prints as
DataKind::Trade, book snapshots as DataKind::OrderBook(Snapshot)), with the mock execution
(`ExecutionConfig::Mock`: latency_ms, fees_percent, a USDT balance) and a strategy whose generate_algo_orders sends one
buy at the call chosen by `buy_at` (OrderKind::Market with TimeInForce::ImmediateOrCancel) and reads the position and
the open orders at the call `read_at`.  So the driver can pass only a scene whose actions are one market buy; the
tool's mock exchange itself accepts Market orders only and its cancel_order is `unimplemented!()` (item 0 read
barter-execution/src/exchange/mock/mod.rs, 61.log).  Position read at the last call = the tool's own record of what
filled.  Observed (i2_r1_scenekeeper_barter_probe.log in the scratchpad): the order is submitted, and at the last
call the position is null with 1 open order -- the mock exchange's answer does not reach the engine before the
replay ends (the same as item 0 recorded with 3000 prints).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

TOOL = "barter-rs(barter 0.14) backtest + ExecutionConfig::Mock"
EXE = str(Path(sys.prefix) / "bin" / "c61_driver")


class Adapter:
    name = "opp_barter"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market",), events=("book", "trade"), latency=("order",),
               costs=("maker_rate", "taker_rate"), account=("cash",))
        acts = inp["actions"]
        if len(acts) != 1 or acts[0]["op"] != "place" or acts[0]["side"] != "buy":
            raise NotExpressible(f"{TOOL}: 渡せるのは成行の買い 1 本だけ(項目0 の driver の戦略が出す注文。道具の模擬の取引所は成行だけを受け、"
                                 "取消は unimplemented!())")
        a = acts[0]
        ev = []
        for e in sorted(inp["market"], key=lambda e: e["t"]):
            if e["type"] == "trade":
                ev.append({"kind": "trade", "ts_ns": e["t"], "price": e["px"], "qty": e["qty"], "side": e["aggressor"]})
            else:
                ev.append({"kind": "book_snapshot", "ts_ns": e["t"], "bids": e["bids"], "asks": e["asks"]})
        k = sum(1 for e in inp["market"] if e["t"] <= a["t"])  # the strategy call after the last event at or before the action
        if k == 0:
            raise NotExpressible(f"{TOOL}: 事象より前の注文を出す口が無い(戦略は事象ごとに呼ばれる)")
        c = inp.get("costs") or {}
        lat = ((inp.get("latency") or {}).get("order") or {}).get("ns", 0)
        cfg = {"buy_at": k, "qty": a["qty"], "price": 0.0, "read_at": len(ev), "latency_ms": int(lat // 1_000_000),
               "fees_percent": float(c.get("taker_rate", 0.0)) * 100, "usdt": float(inp["account"]["cash"]),
               "engine_start": "2026-01-01T00:00:00Z"}
        r = subprocess.run([EXE], input=json.dumps({"cfg": cfg, "events": ev}), capture_output=True, text=True, timeout=60)
        rows = [json.loads(ln) for ln in r.stdout.splitlines() if ln.startswith("{")]
        read = next((x for x in rows if "read_at" in x), {})
        pos = float(read.get("position_qty") or 0.0)
        fills = [{"ref": a["ref"], "t": inp["market"][-1]["t"], "px": None, "qty": pos, "liq": "taker"}] if pos > 0 else []
        st = C.status_from(pos, a["qty"], active=bool(read.get("orders")))
        return {"orders": {a["ref"]: {"status": st}}, "fills": fills}


TARGET = Adapter()
