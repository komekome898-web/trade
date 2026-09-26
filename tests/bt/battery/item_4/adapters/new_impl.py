"""新実装 (the new engine, item 4: integration, reference, compatibility).

The body below was written by the table-maker (資料係, item 4 round 1).  The table-maker writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i4_protocol.py)

- op "bars"     -- drive the new engine's bar model with the scene's script as
                   the strategy and every config key translated into the engine's
                   own options.  `model: "spec"` names the one answer: the result of
                   the stated rules R-* (DEFINITIONS.md).  `reference: true` -> the
                   same input through the engine AND through the independent
                   reference implementation (src/bot/bt/reference/), returned as
                   {"engine": obs, "reference": obs}.
- op "delivery" -- the core granularity: the bars as the core's bar events, a strategy on
                   the core's Strategy interface that records, at each call, what the
                   core's context lets it see (visible bar events: count, last start
                   time, last close).
- op "metrics"  -- the engine's metric function(s) on the given PnLs / equity.
- op "split"    -- the engine's row-fraction split (D-1 / D-2).
- op "pipeline" -- the scene's files under `root` handed BY PATH with each
                   dataset's declarative spec (and `origin`) translated into the
                   engine's data options; the instruments, the strategy (schedule /
                   price_rule), the fill rule, the costs, the purpose and the
                   prereg hash handed to ONE run; report per `want`: fills /
                   pnl per instrument, events_read per dataset, the run record
                   (purpose, data sha256 by the scene path), the metric export
                   (purpose, round trips per instrument) and the dashboard
                   (every tab of the run's view as {"label", "text"}, read from
                   what the dashboard renders).
- If the engine refuses (raises / reports an error for the run): raise
  i4_protocol.Refused(reason).
- If the engine's public API has no way to express the input: raise
  i4_protocol.NotExpressible(what was tried).
- Never compute an answer the engine did not produce, never read the scene's
  expected answer (i4_scenes.expected / scene["expect"]), never special-case a
  scene id.  The mutant (mutant.py) wraps this module as it is.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i4_protocol import NotExpressible, Refused  # noqa: E402

# The new implementation's public API only (src/bot/bt/compat/__init__.__all__, src/bot/bt/pipeline.py,
# src/bot/bt/reference/, src/bot/bt/report/exports.py, src/bot/monitoring/backtest_view.py).
from bot.bt.compat import bar_events, compute_metrics_values, options_from_mapping, run_bars, split_rows  # noqa: E402

NS = 1_000_000_000
WANT_BARS = ("fills", "pnls", "equity", "metrics", "missed_fills")
# The engine's refusals are ValueError subclasses (BarModelError, SplitError, PipelineError, DataError).
RULES = "spec"            # the engine's rule set = the stated rules R-* (the one answer of every scene)
SPLIT_ARITH = "decimal"   # D-1: the fractions as written


def _engine(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as exc:
        raise Refused(f"{type(exc).__name__}: {exc}") from None


def _bars_obs(res, want) -> dict:
    out = {}
    if "fills" in want:
        out["fills"] = [{"bar": int(f["bar"]), "side": f["side"], "price": float(f["price"]), "size": float(f["size"])}
                        for f in res.fills]
    if "pnls" in want:
        out["pnls"] = [float(x) for x in res.trade_pnls]
    if "equity" in want:
        out["equity"] = [float(x) for x in res.equity]
    if "metrics" in want:
        out["metrics"] = dict(res.metrics)
    if "missed_fills" in want:
        out["missed_fills"] = int(res.missed_fills)
    return out


def _run_engine(inp: dict) -> dict:
    """One run of the engine's bar model (the stated rules) with the scene's script as the strategy."""
    cfg = dict(inp["config"])
    cfg["bar_seconds"] = float(inp["bar_seconds"])
    by_bar = {int(s["bar"]): s["signal"] for s in inp.get("signals", [])}

    def decide(k):  # k bars delivered so far: the latest is bar k - 1 (the strategy sees bars 0..k-1 only)
        return by_bar.get(k - 1)

    def go():
        opts = options_from_mapping(cfg)
        bar_ns = int(round(float(inp["bar_seconds"]) * NS))
        events = bar_events(inp["bars"], [b["t_ns"] for b in inp["bars"]], bar_ns)
        return run_bars(events, decide, opts, RULES, start=0)
    return _bars_obs(_engine(go), inp.get("want") or WANT_BARS)




def _delivery(inp: dict) -> dict:
    """The core granularity: the core's own event loop and strategy context."""
    from bot.bt.core import BarEvent, CoreEngine, EventType, Strategy, ZeroLatency
    from bot.bt.core.testing import FixedRateCost, ImmediateFillModel, RecordingAccount
    bar_ns = int(round(float(inp["bar_seconds"]) * NS))
    rows = inp["bars"]
    events = [BarEvent(received_time_ns=b["t_ns"] + bar_ns, start_time_ns=b["t_ns"], open=b["open"], high=b["high"],
                       low=b["low"], close=b["close"], volume=b.get("volume", 0.0)) for b in rows]
    calls = []

    class Recorder(Strategy):
        def on_event(self, event, ctx):
            if type(event) is not BarEvent:
                return
            seen = ctx.visible_events(EventType.BAR)
            last = seen[len(seen) - 1]
            calls.append({"seen": len(seen), "last_t_ns": int(last.start_time_ns), "last_close": float(last.close)})

    def go():
        span = (events[0].exchange_time_ns, events[-1].received_time_ns)
        CoreEngine(Recorder(), {"bars": events}, ImmediateFillModel(), ZeroLatency(), FixedRateCost(0.0),
                   RecordingAccount(), time_span_ns=span).run()
    _engine(go)
    return {"calls": calls}


# The lead's values for the two points the rule text left open (SPEC.md §4 U1 / U2; finishing delegation, stage 2).
REF_UNDECIDED = {"wick_short_history": "use_available", "same_side_exit_signal": "keep"}
REF_KEYS = ("costs", "execution", "maker_timeout_bars", "allow_short", "swap_daily_pct", "stop_loss_pct", "take_profit_pct",
            "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars")


def _run_reference(inp: dict) -> dict:
    """The same input through the independent reference of the stated rules (src/bot/bt/reference/bar_sim.py,
    entry point run_bars(bars, signals, options) = SPEC.md §7; written from DEFINITIONS.md only, not from the engine)."""
    from bot.bt.reference.bar_sim import run_bars as ref_run_bars
    cfg = inp["config"]
    options = {k: cfg[k] for k in REF_KEYS}
    options.update(capital=cfg["initial_equity"], order_amount=cfg["order_notional"],
                   bar_seconds=int(inp["bar_seconds"]), undecided=dict(REF_UNDECIDED))
    bars = [(b["open"], b["high"], b["low"], b["close"]) for b in inp["bars"]]
    signals = {int(s["bar"]): s["signal"] for s in inp["signals"]}
    run = _engine(ref_run_bars, bars, signals, options)
    f = run.to_floats()
    want = inp.get("want") or WANT_BARS
    out = {}
    if "fills" in want:
        out["fills"] = [{"bar": int(x["bar"]), "side": x["side"], "price": float(x["price"]), "size": float(x["size"])}
                        for x in f["fills"]]
    for k in ("pnls", "equity"):
        if k in want:
            out[k] = [float(x) for x in f[k]]
    if "missed_fills" in want:
        out["missed_fills"] = int(f["missed_fills"])
    return out  # no "metrics": the reference holds no metric formulas (SPEC.md §4); the scene judges it on the engine side


def _split(inp: dict) -> dict:
    return {"splits": _engine(split_rows, len(inp["bars"]), inp["train_frac"], inp["val_frac"], SPLIT_ARITH)}


def _pipeline(inp: dict) -> dict:
    from bot.bt.pipeline import plan_pipeline, run_pipeline
    from bot.bt.report.exports import read_export
    from bot.monitoring.backtest_view import run_view
    runs_dir = tempfile.mkdtemp(prefix="i4_new_runs_")
    try:
        plan = _engine(plan_pipeline, root=inp["root"], datasets=inp["datasets"], instruments=inp["instruments"],
                       strategy=inp["strategy"], fill=inp["fill"], latency=inp["latency"], costs=inp["costs"],
                       account=inp["account"], purpose=inp.get("purpose"), prereg=inp.get("prereg"))
        res = _engine(run_pipeline, plan, runs_dir=runs_dir)
        want = set(inp.get("want") or [])
        obs = {}
        # both sides of the fill range, keyed "<side>:<instrument>" (the scene's answer holds both sides)
        if "fills" in want:
            obs["fills"] = {f"{side}:{n}": [{"t_ns": f["t_ns"], "side": f["side"], "px": f["px"], "qty": f["qty"]}
                                            for f in r.fills]
                            for side, by in res.range.items() for n, r in by.items()}
        if "pnl" in want:
            obs["pnl"] = {f"{side}:{n}": sum(t["pnl"] for t in r.trades) for side, by in res.range.items()
                          for n, r in by.items()}
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
    finally:
        shutil.rmtree(runs_dir, ignore_errors=True)


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        op = inp.get("op")
        if op == "bars":
            if inp.get("model", "spec") != "spec":
                raise NotExpressible(f"model {inp.get('model')!r}: 場面の答えは仕様の規則の 1 通り(model \"spec\")だけ")
            if inp.get("reference"):
                return {"engine": _run_engine(inp), "reference": _run_reference(inp)}
            return _run_engine(inp)
        if op == "metrics":
            return {"metrics": _engine(compute_metrics_values, inp["trade_pnls"], inp["equity"], inp["total_fees"],
                                       inp["periods_per_year"])}
        if op == "split":
            return _split(inp)
        if op == "delivery":
            return _delivery(inp)
        if op == "pipeline":
            return _pipeline(inp)
        raise NotExpressible(f"op {op!r} に当たる口を新実装の公開された口に探したが無い")


TARGET = NewImpl()
