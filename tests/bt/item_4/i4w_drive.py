"""The item-4 worker's own driver: hands a battery scene input
(tests/bt/battery/item_4/i4_protocol.py) to the new engine's PUBLIC API and
returns the observation. Used by this directory's tests to run every scene
of the battery against the new engine (the table-maker writes the battery's
own adapter; this driver is not it).

Never reads a scene's expected answer; never looks at a scene id.
"""
from __future__ import annotations

from typing import Any

from bot.bt.compat import (BarModelError, SplitError, bar_events, compute_metrics_values, options_from_mapping, run_bars,
                           split_rows)

NS = 1_000_000_000
WANT_BARS = ("fills", "pnls", "equity", "metrics", "missed_fills")


class Refused(Exception):
    """The engine refused the input."""


def _options(inp: dict) -> Any:
    c = dict(inp["config"])
    c["bar_seconds"] = float(inp["bar_seconds"])
    return options_from_mapping(c)


def _decider(signals: list):
    by_bar = {int(s["bar"]): s["signal"] for s in signals}
    return lambda k: by_bar.get(k - 1)  # k bars delivered: the latest is bar k - 1


def _obs(res, want) -> dict:
    out = {}
    if "fills" in want:
        out["fills"] = [{"bar": f["bar"], "side": f["side"], "price": f["price"], "size": f["size"]} for f in res.fills]
    if "pnls" in want:
        out["pnls"] = list(res.trade_pnls)
    if "equity" in want:
        out["equity"] = list(res.equity)
    if "metrics" in want:
        out["metrics"] = dict(res.metrics)
    if "missed_fills" in want:
        out["missed_fills"] = int(res.missed_fills)
    return out


def run_engine_bars(inp: dict, rules: str) -> dict:
    try:
        opts = _options(inp)
        bar_ns = int(round(float(inp["bar_seconds"]) * NS))
        events = bar_events(inp["bars"], [b["t_ns"] for b in inp["bars"]], bar_ns)
        res = run_bars(events, _decider(inp["signals"]), opts, rules, start=0)
    except BarModelError as exc:
        raise Refused(str(exc)) from None
    return _obs(res, inp.get("want") or WANT_BARS)


REF_UNDECIDED = {"wick_short_history": "use_available", "same_side_exit_signal": "keep"}  # the lead's values
REF_KEYS = ("fills", "pnls", "equity", "missed_fills")  # the independent reference has no metrics (its SPEC.md §8-4)


def reference_options(config: dict, bar_seconds) -> dict:
    """The battery's config -> the independent reference's options (src/bot/bt/reference/SPEC.md §7)."""
    o = {k: v for k, v in config.items() if k not in ("initial_equity", "order_notional")}
    o.update(capital=config["initial_equity"], order_amount=config["order_notional"], bar_seconds=int(bar_seconds),
             undecided=REF_UNDECIDED)
    return o


def run_reference_bars(inp: dict) -> dict:
    """The same bars input through the INDEPENDENT reference of the stated rules (bot.bt.reference.bar_sim, written
    without reading the core or the new engine). Only the keys the reference has (REF_KEYS)."""
    from bot.bt.reference.bar_sim import run_bars as ref_run_bars
    bars = [(b["open"], b["high"], b["low"], b["close"]) for b in inp["bars"]]
    try:
        out = ref_run_bars(bars, {int(s["bar"]): s["signal"] for s in inp["signals"]},
                           reference_options(inp["config"], inp["bar_seconds"])).to_floats()
    except Exception as exc:  # the reference's refusal (RefusedConfig and its bar check)
        raise Refused(str(exc)) from None
    want = inp.get("want") or WANT_BARS
    return {k: out[k] for k in want if k in REF_KEYS}


def run(inp: dict, reference=run_reference_bars) -> dict:
    op = inp.get("op")
    if op == "bars":
        if "models" in inp:
            return {m: run_engine_bars(inp, m) for m in inp["models"]}
        if inp.get("reference"):
            if reference is None:
                raise NotImplementedError("no reference driver given")
            return {"engine": run_engine_bars(inp, inp.get("model", "spec")), "reference": reference(inp)}
        return run_engine_bars(inp, inp.get("model", "spec"))
    if op == "metrics":
        return {"metrics": compute_metrics_values(inp["trade_pnls"], inp["equity"], inp["total_fees"],
                                                  inp["periods_per_year"])}
    if op == "split":
        n = len(inp["bars"])

        def one(arith):
            try:
                return {"splits": split_rows(n, inp["train_frac"], inp["val_frac"], arith)}
            except SplitError as exc:
                raise Refused(str(exc)) from None
        if "models" in inp:
            return {m: one({"legacy": "binary", "spec": "decimal"}[m]) for m in inp["models"]}
        return one("decimal")
    if op == "pipeline":
        return run_pipeline_scene(inp)
    if op == "delivery":
        return run_delivery(inp)
    raise NotImplementedError(op)


def run_delivery(inp: dict) -> dict:
    """op "delivery" (the core granularity): the bars through the core's event loop one by one; at each bar the
    strategy records what the CORE hands it (its delivered history, read with ctx.visible_events), not a copy of
    the input."""
    from bot.bt.core import CoreEngine, NullAccount, NullFillModel, Strategy, ZeroLatency
    from bot.bt.core.events import BarEvent, EventType

    class _NoCost:
        def cost(self, fill) -> float:  # no order is ever placed: never called
            raise AssertionError("no fill is expected in a delivery scene")

    calls: list = []

    class Recorder(Strategy):
        def on_event(self, event, ctx) -> None:
            if type(event) is not BarEvent:
                return
            seen = ctx.visible_events(EventType.BAR)
            last = seen[-1]
            calls.append({"seen": len(seen), "last_t_ns": int(last.start_time_ns), "last_close": float(last.close)})

    bar_ns = int(round(float(inp["bar_seconds"]) * NS))
    try:
        events = bar_events(inp["bars"], [b["t_ns"] for b in inp["bars"]], bar_ns)
    except BarModelError as exc:
        raise Refused(str(exc)) from None
    span = (events[0].exchange_time_ns, events[-1].received_time_ns)
    CoreEngine(Recorder(), {"bars": list(events)}, NullFillModel(), ZeroLatency(), _NoCost(), NullAccount(),
               time_span_ns=span).run()
    return {"calls": calls}


def run_pipeline_scene(inp: dict) -> dict:
    """op "pipeline": the scene's files must already be under inp["root"]."""
    import os
    import tempfile

    from bot.bt.pipeline import PipelineError, plan_pipeline, run_pipeline
    from bot.bt.report.exports import read_export
    from bot.monitoring.backtest_view import run_view
    runs_dir = inp.get("runs_dir") or tempfile.mkdtemp(prefix="i4_runs_")
    try:
        # the declaration of the integrated run (finishing stage i4-r2-03 / 05 / 06): datasets (files or seeded
        # generators), instruments with product / rules, the fill range (both sides), latency distributions,
        # costs (CostSchedule), account, purpose, the pre-registration FILE under root. A key the scene does not
        # carry is not supplied here (the pipeline refuses what is missing; nothing is defaulted by the driver)
        kw = {k: inp[k] for k in ("fill", "latency", "costs", "account", "prereg", "prereg_sha256") if k in inp}
        plan = plan_pipeline(root=inp["root"], datasets=inp["datasets"], instruments=inp["instruments"],
                             strategy=inp["strategy"], purpose=inp.get("purpose"), **kw)
        res = run_pipeline(plan, runs_dir=runs_dir)
    except PipelineError as exc:
        raise Refused(str(exc)) from None
    want = set(inp.get("want") or [])
    obs = {}
    if "fills" in want:
        obs["fills"] = {n: [{"t_ns": f["t_ns"], "side": f["side"], "px": f["px"], "qty": f["qty"]} for f in r.fills]
                        for n, r in res.instruments.items()}
    if "pnl" in want:
        obs["pnl"] = {n: sum(t["pnl"] for t in r.trades) for n, r in res.instruments.items()}
    if "events_read" in want:
        obs["events_read"] = dict(res.events_read)
    if "run_record" in want:
        obs["run_record"] = {"purpose": res.record["purpose"], "data_sha256": dict(res.record["data_sha256"])}
    if "export" in want:
        m = read_export(os.path.join(res.run_dir, "metrics.json"))
        obs["export"] = {"purpose": m["purpose"],
                         "num_trades": {n: v["num_trades"] for n, v in m["data"]["by_instrument"].items()}}
    if "dashboard" in want:
        v = run_view(runs_dir, res.run_id)
        obs["dashboard"] = {"tabs": [{"label": t["label"], "text": t["text"]} for t in v["tabs"]]}
    return obs
