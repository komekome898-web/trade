"""Test helper (not a test module): drive one item-1 battery scene input
through the new data layer's and vector path's PUBLIC API only, and return
the observation in the battery's forms (tests/bt/battery/item_1/i1_protocol.py).

It opens no data file itself and computes no value the API did not
produce; it only calls the API and renames nothing but containers. A
`DataError` from the API propagates (the scene's "refused").
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

BATTERY = Path(__file__).resolve().parents[1] / "battery" / "item_1"
if str(BATTERY) not in sys.path:
    sys.path.insert(0, str(BATTERY))

from bot.bt.data import adjust_daily, load, universe  # noqa: E402
from bot.bt.vector import (bars_from_trades, rule_from_mapping, run_event_bars, run_event_rule,  # noqa: E402
                           run_vector_rule)


def run(inp: dict) -> dict:
    op = inp["op"]
    if op == "load":
        root = inp["root"]
        ds = []
        for d in inp["datasets"]:
            x = {"name": d["name"], "paths": [os.path.join(root, p) for p in d["paths"]], "spec": d["spec"]}
            if "range_ns" in d:
                x["range_ns"] = d["range_ns"]
            ds.append(x)
        res = load(root, ds)
        obs: dict = {}
        want = set(inp["want"])
        if want & {"events", "times"}:
            obs["events"] = {n: res.records(n) for n in res.names()}
        if "anomalies" in want:
            obs["anomalies"] = {n: res.anomalies(n) for n in res.names()}
        if "hashes" in want:
            obs["hashes"] = {os.path.relpath(p, root): h for p, h in res.hashes().items()}
        return obs
    if op == "jpx":
        return {"adjusted": adjust_daily(inp["bars"], inp["actions"], inp["listings"], inp["as_of"]),
                "universe": universe(inp["listings"], inp["actions"], inp["universe_dates"])}
    if op == "vector_vs_event":
        iv = inp["interval_s"]
        paths: dict = {"event": {}, "vector": {}}
        timing = {}
        if inp.get("trades") is not None:
            tr = inp["trades"]
            t0 = time.perf_counter()
            paths["event"]["bars"] = run_event_bars(tr, iv)
            t1 = time.perf_counter()
            paths["vector"]["bars"] = bars_from_trades([x["t_ns"] for x in tr], [x["px"] for x in tr],
                                                       [x["qty"] for x in tr], iv)
            t2 = time.perf_counter()
            timing = {"event_s": t1 - t0, "vector_s": t2 - t1}
        if inp.get("rule") is not None:
            rule = rule_from_mapping(inp["rule"])
            bars = inp["bars"]
            t0 = time.perf_counter()
            ev = run_event_rule(bars, iv, rule)
            t1 = time.perf_counter()
            vc = run_vector_rule(bars, rule)
            t2 = time.perf_counter()
            paths["event"].update(ev)
            paths["vector"].update(vc)
            timing = {"event_s": t1 - t0, "vector_s": t2 - t1}
        return {"paths": paths, "timing": timing}
    raise ValueError(f"unknown op {op!r}")
