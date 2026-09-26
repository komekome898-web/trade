"""Item 4 battery (統合と答え合わせ): the protocol between the runner and a target adapter.

A target adapter is a module that defines ``TARGET`` (an object with a ``name``
string and a ``run(scene_input: dict) -> dict`` method).  The runner hands the
adapter ONE input at a time (a plain JSON-able dict; the forms are in
DEFINITIONS.md「入力の形」) and gets back an observation dict.  Only the keys
the scene's `judge` names are read.

Input ops
---------
op "bars"      -- a bar backtest.  Keys:
    bars        [{"t_ns", "open", "high", "low", "close", "volume"}, ...]  (bar START times, UTC ns)
    bar_seconds int
    signals     [{"bar": i, "signal": "BUY"|"SELL"|"CLOSE"}]  -- the strategy: at the close of
                bar i, having seen bars 0..i only, it says `signal`; every other bar is HOLD.
    config      every option of the bar model, ALL keys always present (no defaults):
                initial_equity, order_notional, costs{taker_fee_pct, maker_fee_pct,
                slippage_pct, spread_pct}, execution ("taker"|"maker"), maker_timeout_bars,
                allow_short, swap_daily_pct, stop_loss_pct, take_profit_pct, max_hold_bars,
                exit_execution ("signal"|"maker_tp"), maker_tp_pct, entry_mask (null|[bool]),
                entry_sides ("both"|"long"|"short"), stop_mode ("fixed"|"wick_invalidation"),
                stop_window_bars
    model       "spec"  -- the result of the stated bar-model rules (DEFINITIONS.md「足の模型の仕様」)
    models      ["legacy", "spec"] instead of `model`: return BOTH results of ONE strategy run
                description, {"legacy": obs, "spec": obs}
    reference   true -> return {"engine": obs, "reference": obs}: the same input through the
                target's main engine AND through an independent reference implementation
    want        subset of ["fills", "pnls", "equity", "metrics", "missed_fills"]
op "delivery"  -- bars, bar_seconds, want ["calls"]: the core granularity (I4-3).  The bars are handed
                  to the target's event loop one by one (bar i starts at t_ns and is complete at
                  t_ns + bar_seconds); the strategy does nothing but record, at each call, what the
                  target handed it -> {"calls": [{"seen": number of bars it can see, "last_t_ns":
                  the start time of the last bar it can see (UTC ns), "last_close": its close}]}.
                  Read what the TARGET handed the strategy (its data object / history), never the
                  adapter's own copy of the input.
op "metrics"   -- trade_pnls, equity, total_fees, periods_per_year -> {"metrics": {...}}
op "split"     -- bars, train_frac, val_frac -> {"splits": {"training": [row positions],
                  "validation": [...], "out_of_sample": [...]}}
op "pipeline"  -- files under `root` (added by the runner), datasets (name, paths, spec,
                  origin), instruments (name, price dataset, riding datasets), strategy,
                  fill, costs, purpose, prereg_sha256, want -> see DEFINITIONS.md「統合の場面」

Observation forms (op "bars")
    fills        [{"bar": int, "side": "OPEN_LONG"|"OPEN_SHORT"|"CLOSE_LONG"|"CLOSE_SHORT",
                   "price": float, "size": float}]   (fills only; cancellations are not fills)
    pnls         [float]  realized PnL per closed round trip, in close order
    equity       [float]  equity at each bar's close, one per bar
    metrics      {"total_pnl_jpy", "num_trades", "win_rate_pct", "profit_factor", "sharpe_ratio",
                  "max_drawdown_pct", "max_consecutive_losses", "avg_win_jpy", "avg_loss_jpy",
                  "risk_reward_ratio", "expectancy_per_trade_jpy", "total_fees_jpy"}
    missed_fills int      resting orders counted as missed by R-M2 (timeout) and R-M3 (replaced by an
                          opposite signal) only; a limit dropped because the position closed (R-M5) or
                          still resting at the end is not counted (DEFINITIONS.md「足の模型の仕様」)

Rules for every adapter (the scene-keeper's fixed mouth; 委任文 §3):
- Translate the scene's declarative input into the target's own PUBLIC options and API.
  The strategy (`signals`) is user code in every target and may be written on top of the
  target's strategy API.  Never compute a value the target did not produce, never read the
  expected answer (i4_scenes.expected / scene["expect"]), never special-case a scene id.
- A scene with a variant may carry ``more_controls``: further inputs handed exactly like ``input``
  (their expected answers stay with the runner).
- ``Refused``: the TARGET refused (raised, or returned an explicit error) -- 「対応なし」.
- ``NotExpressible``: the ADAPTER found no public way to hand this input (or one of its
  options) to the target -- 「結果なし」 with the reason (what was looked for, where).
- any other exception escaping the adapter -- 「結果なし」 with the traceback tail.
"""
from __future__ import annotations

import os

CONFIG_KEYS = ("initial_equity", "order_notional", "costs", "execution", "maker_timeout_bars", "allow_short",
               "swap_daily_pct", "stop_loss_pct", "take_profit_pct", "max_hold_bars", "exit_execution",
               "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars")
COST_KEYS = ("taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct")
METRIC_KEYS = ("total_pnl_jpy", "num_trades", "win_rate_pct", "profit_factor", "sharpe_ratio", "max_drawdown_pct",
               "max_consecutive_losses", "avg_win_jpy", "avg_loss_jpy", "risk_reward_ratio",
               "expectancy_per_trade_jpy", "total_fees_jpy")


class Refused(Exception):
    """The target itself refused the run (exception or explicit error)."""


class NotExpressible(Exception):
    """The adapter has no public way to give this input to the target."""


def need(cond: bool, what: str) -> None:
    """Raise NotExpressible(what) unless cond."""
    if not cond:
        raise NotExpressible(what)


def signal_map(inp: dict) -> dict:
    """{bar index: "BUY"|"SELL"|"CLOSE"} of a bars input (the strategy's script)."""
    return {int(s["bar"]): s["signal"] for s in inp.get("signals", [])}


def non_default(cfg: dict) -> list[str]:
    """Options of a bars config that ask for more than a plain next-bar-open market-order run
    (used by adapters to name what they could not express)."""
    out = []
    if cfg["execution"] != "taker":
        out.append(f"execution={cfg['execution']}")
    for k in ("stop_loss_pct", "take_profit_pct", "max_hold_bars", "maker_tp_pct", "stop_window_bars", "entry_mask"):
        if cfg.get(k) is not None:
            out.append(k)
    if cfg["exit_execution"] != "signal":
        out.append(f"exit_execution={cfg['exit_execution']}")
    if cfg["stop_mode"] != "fixed":
        out.append(f"stop_mode={cfg['stop_mode']}")
    if cfg["entry_sides"] != "both":
        out.append(f"entry_sides={cfg['entry_sides']}")
    if cfg["swap_daily_pct"]:
        out.append("swap_daily_pct")
    return out


def dataset_paths(inp: dict, ds: dict) -> list[str]:
    """Absolute paths of one dataset's files (joined to the scene root, not resolved)."""
    return [os.path.join(inp["root"], p) for p in ds["paths"]]
