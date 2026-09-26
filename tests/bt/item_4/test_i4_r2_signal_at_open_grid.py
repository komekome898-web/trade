"""Adversarial grid (委任文 §3「提出前の吟味」(6), round 2, i4-r1-01): the ORDER inside one bar.

The stated rules (tests/bt/battery/item_4/DEFINITIONS.md 「足の模型の仕様」): R-T1 the signal of bar i fills at
bar i+1's OPEN; R-P3 / R-P4 / R-X1 the stop / take-profit / maker take-profit fill on bar j's RANGE; R-H1 the time
exit fills at bar b+N's open, R-H2 dropping the signal pending for that bar; R-O1 puts the open's events before
the range's, so on bar b+N nothing of the range comes first (R-H3 is the order inside the range after the open:
finishing delegation i4-r2-02, which replaced the round-2 reading "the stop is looked at first"). The open of a bar comes before the rest of its range, so a signal pending for bar j's open acts
before bar j's range: when it closes the position at the open, no stop / take-profit of bar j can fill.

The oracle `expected_bar4` below is written from that rule text for ONE bar (bar 4), not from the engine's code
or branches. The grid is the rule's input space:

  direction {long, short} x signal pending for bar 4 {none, same way, opposite, CLOSE}
  x protective exits {sl, tp, maker_tp, sl+tp, sl+maker_tp}
  x bar 4's open {between the levels, beyond the stop (a gap), beyond the take-profit (a gap)}
  x bar 4's range reaching {nothing, the stop, the take-profit, both}
  x time exit due on bar 4 {no, yes (max_hold_bars = 2)} x costs {zero, non-zero}
  = 2 x 4 x 5 x 3 x 4 x 2 x 2 = 1920 cells, all run.

Checked on every cell: (1) the native model ("spec") gives the oracle's fills and PnL; (2) the reference of the
stated rules (the independent reference bot.bt.reference.bar_sim) gives the same; (3) the compatibility model ("legacy") gives the OLD
engine's output bit for bit (src/bot/backtest/engine.run_backtest on the same input: trade log, PnLs, equity,
metrics, missed fills).

Not in the grid (named): the maker execution (a signal places a limit at the signal bar's close; the limit and the
stop / take-profit are both inside bar j's range and the rule text does not order them -- asked to the lead,
ROOTCAUSE.md section 7-2); the wick stop (R-W3 fills at the open and drops the signal, like the time exit); a
signal pending while flat (no exit exists; covered by the battery's taker scenes); bars 0..3 other than the one
fixed entry path (entry at bar 2's open 100); bar counts other than 6.
"""
from __future__ import annotations

import itertools
import json
import math

import pandas as pd
import pytest

from bot.bt.compat import bar_events, options_from_mapping, run_bars

NS = 1_000_000_000
T0 = 1767571200 * NS
DIRS = ("long", "short")
PENDING = ("none", "same", "opposite", "CLOSE")
EXITS = ("sl", "tp", "mtp", "sl+tp", "sl+mtp")
OPENS = ("between", "beyond_stop", "beyond_tp")
REACH = ("nothing", "stop", "tp", "both")
TIME_DUE = (False, True)
COSTS = ({"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
         {"taker_fee_pct": 0.1, "maker_fee_pct": 0.02, "slippage_pct": 0.01, "spread_pct": 0.02})
SL_PCT, TP_PCT = 2.0, 3.0
CELLS = list(itertools.product(DIRS, PENDING, EXITS, OPENS, REACH, TIME_DUE, range(len(COSTS))))


def bars_of(direction: str, opn: str, reach: str) -> list[tuple]:
    """Bars 0..5: entry signal at bar 1 -> entry at bar 2's open 100; bar 3 quiet; bar 4 under test; bar 5 tail.
    Levels at zero cost: long stop 98 / take-profit 103; short stop 102 / take-profit 97."""
    if direction == "long":
        quiet = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100.5), (100.5, 101.5, 99.5, 100.5)]
        o = {"between": 100.5, "beyond_stop": 97.0, "beyond_tp": 104.0}[opn]
        c = 100.5
        lo = min(o, c, 97.0 if reach in ("stop", "both") else 98.5)
        hi = max(o, c, 104.0 if reach in ("tp", "both") else 102.5)
        if reach in ("stop", "both") and o <= 97.0:
            lo = o - 1.0
        if reach in ("tp", "both") and o >= 104.0:
            hi = o + 1.0
    else:
        quiet = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 99.5), (99.5, 100.5, 98.5, 99.5)]
        o = {"between": 99.5, "beyond_stop": 103.0, "beyond_tp": 96.0}[opn]
        c = 99.5
        hi = max(o, c, 103.0 if reach in ("stop", "both") else 101.5)
        lo = min(o, c, 96.0 if reach in ("tp", "both") else 97.5)
        if reach in ("stop", "both") and o >= 103.0:
            hi = o + 1.0
        if reach in ("tp", "both") and o <= 96.0:
            lo = o - 1.0
    return quiet + [(o, hi, lo, c), (100, 100.5, 99.5, 100)]


def config(direction: str, exits: str, time_due: bool, k: int) -> dict:
    return {"initial_equity": 10000.0, "order_notional": 3000.0, "costs": dict(COSTS[k]), "execution": "taker",
            "maker_timeout_bars": 3, "allow_short": True, "swap_daily_pct": 0.0, "bar_seconds": 60.0,
            "stop_loss_pct": SL_PCT if "sl" in exits else None,
            "take_profit_pct": TP_PCT if exits.endswith("tp") and "mtp" not in exits else None,
            "max_hold_bars": 2 if time_due else None,
            "exit_execution": "maker_tp" if "mtp" in exits else "signal",
            "maker_tp_pct": TP_PCT if "mtp" in exits else None,
            "entry_mask": None, "entry_sides": "both", "stop_mode": "fixed", "stop_window_bars": None}


def signals(direction: str, pending: str) -> dict:
    entry = "BUY" if direction == "long" else "SELL"
    opposite = "SELL" if direction == "long" else "BUY"
    out = {1: entry}
    if pending != "none":
        out[3] = {"same": entry, "opposite": opposite, "CLOSE": "CLOSE"}[pending]
    return out


# --------------------------------------------------------------------------- the oracle (rule text, bar 4 only)
def expected_bar4(direction: str, pending: str, exits: str, time_due: bool, k: int, bars: list) -> dict:
    """What the stated rules give: the entry at bar 2 and what bar 4 does. Returns {"fills": [(bar, side, price)],
    "pnl": float}. Written from R-C1, R-A1..A3, R-T1, R-T3, R-P1, R-P3, R-P4, R-X1, R-H1..H3 only."""
    c = COSTS[k]
    s = 1 if direction == "long" else -1
    adj = (c["spread_pct"] / 2 + c["slippage_pct"]) / 100

    def taker(ref: float, buy: bool) -> float:  # R-C1
        return ref * (1 + adj) if buy else ref * (1 - adj)

    entry = taker(100.0, s > 0)  # bar 2's open, R-T1
    qty = 3000.0 / entry  # R-A1
    entry_fee = qty * entry * c["taker_fee_pct"] / 100  # R-A2
    o, h, lo, _ = bars[4]
    stop = entry * (1 - s * SL_PCT / 100) if "sl" in exits else None  # R-P1
    tp = entry * (1 + s * TP_PCT / 100) if "tp" in exits else None  # take_profit or maker_tp: the same level
    side = "LONG" if s > 0 else "SHORT"

    def stop_reached() -> bool:  # R-P3: the range reaches the level
        return stop is not None and (lo <= stop if s > 0 else h >= stop)

    def tp_through() -> bool:  # R-P4 / R-X1: strict traded-through
        return tp is not None and (h > tp if s > 0 else lo < tp)

    close = None  # (price, fee pct)
    if time_due:  # R-H1 / R-H2 / R-O1: at bar 4's OPEN, before anything of bar 4's range (R-H3 orders the range,
        # after the open -- finishing delegation i4-r2-02); the pending signal is dropped
        close = (taker(o, s < 0), c["taker_fee_pct"])
    else:
        if pending in ("opposite", "CLOSE"):  # R-T1 / R-T3: closes at bar 4's OPEN, before bar 4's range
            close = (taker(o, s < 0), c["taker_fee_pct"])
        elif stop_reached():  # the position lives through bar 4's range: the stop first (R-P3)
            close = (taker(min(o, stop) if s > 0 else max(o, stop), s < 0), c["taker_fee_pct"])
        elif tp_through():
            close = (tp, c["maker_fee_pct"])
    fills = [(2, f"OPEN_{side}", entry)]
    pnl = None
    if close is not None:
        px, pct = close
        fills.append((4, f"CLOSE_{side}", px))
        pnl = (px - entry) * qty * s - qty * px * pct / 100 - entry_fee  # R-A3
    return {"fills": fills, "pnl": pnl}


# --------------------------------------------------------------------------- the engines
def _rows(bars):
    return [{"t_ns": T0 + i * 60 * NS, "open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0}
            for i, b in enumerate(bars)]


def run_new(bars, sig, cfg, rules):
    rows = _rows(bars)
    ev = bar_events(rows, [r["t_ns"] for r in rows], 60 * NS)
    return run_bars(ev, lambda n: sig.get(n - 1), options_from_mapping(cfg), rules, start=0)


def run_rule_reference(bars, sig, cfg):
    """The independent reference (bot.bt.reference.bar_sim; bar_rules.py was removed in the finishing stage)."""
    from bot.bt.reference.bar_sim import run_bars as ref_run_bars
    import i4w_drive as drive
    c = {k: v for k, v in cfg.items() if k != "bar_seconds"}
    return ref_run_bars(list(bars), sig, drive.reference_options(c, 60)).to_floats()


def run_old(bars, sig, cfg):
    from bot.backtest.engine import CostModel, run_backtest
    from bot.strategy.base import Signal, SignalType, Strategy

    class Script(Strategy):
        def __init__(self):
            super().__init__({})

        @property
        def min_history(self):
            return 0

        def on_candles(self, candles):
            v = sig.get(len(candles) - 1)
            return Signal(SignalType[v]) if v else Signal(SignalType.HOLD)

    df = pd.DataFrame({"open": [b[0] for b in bars], "high": [b[1] for b in bars], "low": [b[2] for b in bars],
                       "close": [b[3] for b in bars], "volume": [1.0] * len(bars)},
                      index=pd.date_range("2026-01-05", periods=len(bars), freq="min", tz="UTC"))
    kw = {k: v for k, v in cfg.items() if k not in ("costs", "initial_equity", "order_notional")}
    return run_backtest(Script(), df, initial_equity_jpy=cfg["initial_equity"], order_notional_jpy=cfg["order_notional"],
                        costs=CostModel(**cfg["costs"]), **kw)


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _same_fills(got, want) -> bool:
    return len(got) == len(want) and all(g[0] == w[0] and g[1] == w[1] and _close(g[2], w[2]) for g, w in zip(got, want))


CHUNK = 160


@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_spec_and_rule_reference_follow_the_open_then_range_order(start):
    bad = []
    for cell in CELLS[start:start + CHUNK]:
        d, p, ex, op, re_, td, k = cell
        bars = bars_of(d, op, re_)
        cfg = config(d, ex, td, k)
        sig = signals(d, p)
        want = expected_bar4(d, p, ex, td, k, bars)
        res = run_new(bars, sig, cfg, "spec")
        got = [(f["bar"], f["side"], f["price"]) for f in res.fills]
        ok = _same_fills(got, want["fills"]) and (
            (want["pnl"] is None and res.trade_pnls == []) or
            (want["pnl"] is not None and len(res.trade_pnls) == 1 and _close(res.trade_pnls[0], want["pnl"])))
        ref = run_rule_reference(bars, sig, cfg)
        rgot = [(f["bar"], f["side"], f["price"]) for f in ref["fills"]]
        rok = _same_fills(rgot, want["fills"]) and (
            (want["pnl"] is None and ref["pnls"] == []) or
            (want["pnl"] is not None and len(ref["pnls"]) == 1 and _close(ref["pnls"][0], want["pnl"])))
        if not (ok and rok):
            bad.append((cell, "spec" if not ok else "", got, "reference" if not rok else "", rgot, want["fills"]))
    assert not bad, f"{len(bad)} cells differ from the rule text; first: {bad[:3]}"


@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_legacy_keeps_the_old_engine_bit_for_bit(start):
    bad = []
    for cell in CELLS[start:start + CHUNK]:
        d, p, ex, op, re_, td, k = cell
        bars = bars_of(d, op, re_)
        cfg = config(d, ex, td, k)
        sig = signals(d, p)
        new = run_new(bars, sig, cfg, "legacy")
        old = run_old(bars, sig, cfg)
        o = ([dict(e) for e in old.trade_log], [float(x) for x in old.trade_pnls],
             [float(x) for x in old.equity_curve.tolist()], dict(old.metrics.as_dict()), int(old.missed_fills))
        n = (new.trade_log, list(new.trade_pnls), list(new.equity), dict(new.metrics), int(new.missed_fills))
        if json.dumps(o) != json.dumps(n):  # np.float64 is a float: json writes each float's repr (its exact bits)
            bad.append(cell)
    assert not bad, f"{len(bad)} cells: legacy differs from the old engine; first: {bad[:3]}"


def test_the_grid_is_not_vacuous():
    """The cells reach every kind of bar-4 outcome the rule separates, including the one the fix is about: a
    closing signal at the open while bar 4's range reaches a level (the old order would exit at the level)."""
    kinds = set()
    for cell in CELLS:
        d, p, ex, op, re_, td, k = cell
        bars = bars_of(d, op, re_)
        want = expected_bar4(d, p, ex, td, k, bars)
        s = 1 if d == "long" else -1
        o, h, lo, _ = bars[4]
        reaches = (lo < 98.5 or h > 102.5) if s > 0 else (h > 101.5 or lo < 97.5)
        if len(want["fills"]) == 1:
            kinds.add("no_exit")
        elif td:
            kinds.add("time_exit_or_stop_on_time_bar")
        elif p in ("opposite", "CLOSE"):
            kinds.add("signal_at_open_with_level_in_range" if reaches else "signal_at_open")
        else:
            kinds.add("range_exit")
    assert kinds == {"no_exit", "time_exit_or_stop_on_time_bar", "signal_at_open_with_level_in_range",
                     "signal_at_open", "range_exit"}, kinds
