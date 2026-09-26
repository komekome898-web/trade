"""新実装 (the new engine, item 4: integration, reference, compatibility).

The body below was written by the table-maker (資料係, item 4 round 1).  The table-maker writes the body of this adapter every round, calling
only the new implementation's public API (委任文 §3; the scene-keeper fixes
the mouth, not the body).  The contract the body must keep:

  TARGET.run(scene_input: dict) -> observation dict      (i4_protocol.py)

- op "bars"     -- drive the new engine's bar model(s) with the scene's script as
                   the strategy and every config key translated into the engine's
                   own options.  `model: "spec"` -> the engine's own (native) bar
                   model; `models: ["legacy", "spec"]` -> BOTH the compatibility
                   mouth -- "legacy" is ALWAYS taken from the old names with the old
                   arguments (bot.bt.compat.run_backtest / CostModel with the old
                   Strategy interface; split_data for op "split"), never from the
                   engine's rule set directly (委任文 §3 「互換の口(旧と同じ名前・同じ
                   引数)と本来の模型の両方を持つもの全体」, i4-r1-10) --
                   and the native model, from the one scene input, returned as
                   {"legacy": obs, "spec": obs}.  `reference: true` -> the same
                   input through the engine AND through the independent reference
                   implementation (src/bot/bt/reference/), returned as
                   {"engine": obs, "reference": obs}.
- op "delivery" -- the core granularity: the bars as the core's bar events, a strategy on
                   the core's Strategy interface that records, at each call, what the
                   core's context lets it see (visible bar events: count, last start
                   time, last close).
- op "metrics"  -- the engine's metric function(s) on the given PnLs / equity.
- op "split"    -- the engine's row-fraction split (native; `models` as above).
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
from bot.bt.compat import (CostModel, bar_events, compute_metrics_values, options_from_mapping, run_backtest,  # noqa: E402
                           run_bars, split_data, split_rows)

NS = 1_000_000_000
WANT_BARS = ("fills", "pnls", "equity", "metrics", "missed_fills")
# The engine's refusals are ValueError subclasses (BarModelError, SplitError, PipelineError, DataError);
# the same rule as the current environment's adapter (adapters/current_impl.py `_call`).
_SPLIT_ARITH = {"legacy": "binary", "spec": "decimal"}


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


def _run_engine(inp: dict, rules: str) -> dict:
    """One run of the engine's bar model (rule set `rules`) with the scene's script as the strategy."""
    cfg = dict(inp["config"])
    cfg["bar_seconds"] = float(inp["bar_seconds"])
    by_bar = {int(s["bar"]): s["signal"] for s in inp.get("signals", [])}

    def decide(k):  # k bars delivered so far: the latest is bar k - 1 (the strategy sees bars 0..k-1 only)
        return by_bar.get(k - 1)

    def go():
        opts = options_from_mapping(cfg)
        bar_ns = int(round(float(inp["bar_seconds"]) * NS))
        events = bar_events(inp["bars"], [b["t_ns"] for b in inp["bars"]], bar_ns)
        return run_bars(events, decide, opts, rules, start=0)
    return _bars_obs(_engine(go), inp.get("want") or WANT_BARS)


def _legacy_bars(inp: dict) -> dict:
    """The compatibility mouth: the old name run_backtest with the old arguments and the old Strategy interface
    (i4-r1-10), exactly as a caller of the old engine would call it."""
    import pandas as pd
    from bot.strategy.base import Signal, SignalType, Strategy

    by_bar = {int(s["bar"]): s["signal"] for s in inp.get("signals", [])}

    class Script(Strategy):
        def __init__(self):
            super().__init__({})

        @property
        def min_history(self) -> int:
            return 0

        def on_candles(self, candles):
            s = by_bar.get(len(candles) - 1)
            return Signal(SignalType[s]) if s else Signal(SignalType.HOLD)

    c = inp["config"]
    frame = pd.DataFrame({k: [b[k] for b in inp["bars"]] for k in ("open", "high", "low", "close", "volume")},
                         index=pd.to_datetime([b["t_ns"] for b in inp["bars"]], unit="ns", utc=True))
    costs = CostModel(**{k: c["costs"][k] for k in ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")})
    res = _engine(run_backtest, Script(), frame, initial_equity_jpy=c["initial_equity"], order_notional_jpy=c["order_notional"],
                  costs=costs, execution=c["execution"], maker_timeout_bars=c["maker_timeout_bars"],
                  allow_short=c["allow_short"], swap_daily_pct=c["swap_daily_pct"], bar_seconds=float(inp["bar_seconds"]),
                  stop_loss_pct=c["stop_loss_pct"], take_profit_pct=c["take_profit_pct"], max_hold_bars=c["max_hold_bars"],
                  exit_execution=c["exit_execution"], maker_tp_pct=c["maker_tp_pct"], entry_mask=c["entry_mask"],
                  entry_sides=c["entry_sides"], stop_mode=c["stop_mode"], stop_window_bars=c["stop_window_bars"])
    want = set(inp.get("want") or WANT_BARS)
    out = {}
    if "fills" in want:
        out["fills"] = [{"bar": int(e["bar"]), "side": e["side"], "price": float(e["price"]), "size": float(e["size"])}
                        for e in res.trade_log if e["side"].startswith(("OPEN_", "CLOSE_"))]
    if "pnls" in want:
        out["pnls"] = [float(x) for x in res.trade_pnls]
    if "equity" in want:
        out["equity"] = [float(x) for x in res.equity_curve.tolist()]
    if "metrics" in want:
        out["metrics"] = res.metrics.as_dict()
    if "missed_fills" in want:
        out["missed_fills"] = int(res.missed_fills)
    return out


def _legacy_split(inp: dict) -> dict:
    """The compatibility mouth split_data (old name, old arguments) on the scene's rows."""
    import pandas as pd
    frame = pd.DataFrame({k: [b[k] for b in inp["bars"]] for k in ("open", "high", "low", "close", "volume")},
                         index=pd.to_datetime([b["t_ns"] for b in inp["bars"]], unit="ns", utc=True))
    sp = _engine(split_data, frame, train_frac=inp["train_frac"], val_frac=inp["val_frac"])
    pos = {t: i for i, t in enumerate(frame.index)}
    return {"splits": {k: [pos[t] for t in getattr(sp, k).index] for k in ("training", "validation", "out_of_sample")}}


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


def _run_reference(inp: dict) -> dict:
    """The same input through the independent reference of the stated rules (src/bot/bt/reference/bar_rules.py)."""
    from bot.bt.reference.bar_rules import run_rules
    out = _engine(run_rules, inp["bars"], inp["bar_seconds"], {int(s["bar"]): s["signal"] for s in inp["signals"]},
                  inp["config"])
    return {k: out[k] for k in (inp.get("want") or WANT_BARS)}


def _split(inp: dict, model: str) -> dict:
    return {"splits": _engine(split_rows, len(inp["bars"]), inp["train_frac"], inp["val_frac"], _SPLIT_ARITH[model])}


def _pipeline(inp: dict) -> dict:
    from bot.bt.pipeline import plan_pipeline, run_pipeline
    from bot.bt.report.exports import read_export
    from bot.monitoring.backtest_view import run_view
    runs_dir = tempfile.mkdtemp(prefix="i4_new_runs_")
    try:
        plan = _engine(plan_pipeline, root=inp["root"], datasets=inp["datasets"], instruments=inp["instruments"],
                       strategy=inp["strategy"], fill=inp["fill"], costs=inp["costs"], purpose=inp.get("purpose"),
                       prereg_sha256=inp.get("prereg_sha256"))
        res = _engine(run_pipeline, plan, runs_dir=runs_dir)
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
    finally:
        shutil.rmtree(runs_dir, ignore_errors=True)


class NewImpl:
    name = "new_impl"

    def run(self, inp: dict) -> dict:
        op = inp.get("op")
        if op == "bars":
            if "models" in inp:
                return {m: (_legacy_bars(inp) if m == "legacy" else _run_engine(inp, m)) for m in inp["models"]}
            if inp.get("model") == "legacy":
                return _legacy_bars(inp)
            if inp.get("reference"):
                return {"engine": _run_engine(inp, inp.get("model", "spec")), "reference": _run_reference(inp)}
            return _run_engine(inp, inp.get("model", "spec"))
        if op == "metrics":
            return {"metrics": _engine(compute_metrics_values, inp["trade_pnls"], inp["equity"], inp["total_fees"],
                                       inp["periods_per_year"])}
        if op == "split":
            if "models" in inp:
                return {m: (_legacy_split(inp) if m == "legacy" else _split(inp, m)) for m in inp["models"]}
            return _split(inp, "spec")
        if op == "delivery":
            return _delivery(inp)
        if op == "pipeline":
            return _pipeline(inp)
        raise NotExpressible(f"op {op!r} に当たる口を新実装の公開された口に探したが無い")


TARGET = NewImpl()
