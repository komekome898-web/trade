"""Adversarial grid (委任文 §3「提出前の吟味」(6)): the new engine's bar model
under the stated rules ("spec") against the slow reference of the same rule
text (bot.bt.reference.bar_rules: exact rationals, one plain loop, no engine
import), on every cell of the option grid.

The grid is the options' own space, not the engine's branches:
execution {taker, maker} x allow_short {no, yes} x protective exit {none, sl,
tp, sl+tp, maker_tp, sl+maker_tp, wick} x max_hold_bars {None, 3} x
entry_sides {both, long, short} x entry_mask {none, random} x daily carry
{0, +0.5, -0.3} = 1008 cells (tests/bt/compat/golden/compat_golden_scenes.py `grid()`),
each with its own seeded bars (integer ticks of 0.5, gaps of 0 / +-1 / +-4
ticks) and a seeded signal script (HOLD / BUY / SELL / CLOSE).

Not in the grid (named, per the rule): bars with non-integer-tick prices
(boundary ties are then rare; the decimal-level scenes of the battery
i4-12-touch-decimal cover a tie on a written decimal), costs as an axis
(each cell draws one of 3 cost sets), bar counts other than 40, the maker
timeout and wick window as axes (drawn 1..4 per cell).
Judged by the battery's judge with its tolerance (1e-9 relative): the
engine computes in floats, the reference in rationals.
"""
from __future__ import annotations

import copy

import pytest

import i4w_drive as drive
import i4_judge as J
import compat_golden_scenes as G

SPEC = {"fills": ["bar", "side", "price", "size"], "pnls": True, "equity": True, "metrics": True, "missed_fills": True}
T0 = 1767571200 * 10**9


def to_input(sc: dict) -> dict:
    o = sc["options"]
    cfg = {"initial_equity": o["initial_equity_jpy"], "order_notional": o["order_notional_jpy"], "costs": o["costs"],
           "execution": o["execution"], "maker_timeout_bars": o["maker_timeout_bars"], "allow_short": o["allow_short"],
           "swap_daily_pct": o["swap_daily_pct"], "stop_loss_pct": o["stop_loss_pct"],
           "take_profit_pct": o["take_profit_pct"], "max_hold_bars": o["max_hold_bars"],
           "exit_execution": o["exit_execution"], "maker_tp_pct": o["maker_tp_pct"], "entry_mask": o["entry_mask"],
           "entry_sides": o["entry_sides"], "stop_mode": o["stop_mode"], "stop_window_bars": o["stop_window_bars"]}
    bs = int(o["bar_seconds"])
    bars = [{"t_ns": T0 + i * bs * 10**9, "open": b[0], "high": b[1], "low": b[2], "close": b[3], "volume": 1.0}
            for i, b in enumerate(sc["bars"])]
    sig = [{"bar": i, "signal": {"B": "BUY", "S": "SELL", "C": "CLOSE"}[ch]}
           for i, ch in enumerate(sc["signals"]) if ch != "." and i >= sc["min_history"]]
    return {"op": "bars", "bars": bars, "bar_seconds": bs, "signals": sig, "config": cfg, "model": "spec",
            "want": list(drive.WANT_BARS)}


CELLS = G.scenes()
CHUNK = 72


def _one(inp, fn):
    try:
        return fn(copy.deepcopy(inp))
    except drive.Refused as exc:
        return {"refused": str(exc)[:0]}


@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_spec_engine_equals_the_rule_reference_on_every_cell(start):
    for sc in CELLS[start:start + CHUNK]:
        inp = to_input(sc)
        e, r = _one(inp, drive.run), _one(inp, drive.run_reference_bars)
        if "refused" in r or "refused" in e:
            assert ("refused" in r) == ("refused" in e), sc["cell"]
            continue
        d = J.judge_obs(r, e, SPEC)
        assert d is None, (sc["cell"], d)


def test_the_grid_is_not_vacuous():
    """Each protective exit, the time exit, the carry and missed limits occur in the grid's engine runs."""
    from bot.bt.compat import bar_events, options_from_mapping, run_bars
    reasons, missed, carry = set(), 0, 0.0
    for sc in CELLS[::7]:
        inp = to_input(sc)
        cfg = dict(inp["config"], bar_seconds=float(inp["bar_seconds"]))
        ev = bar_events(inp["bars"], [b["t_ns"] for b in inp["bars"]], inp["bar_seconds"] * 10**9)
        sig = {s["bar"]: s["signal"] for s in inp["signals"]}
        res = run_bars(ev, lambda k: sig.get(k - 1), options_from_mapping(cfg), "spec")
        reasons |= {f["reason"] for f in res.fills}
        missed += res.missed_fills
        carry += sum(1 for f in res.fills if f["reason"] != "open") if cfg["swap_daily_pct"] else 0
    assert {"signal", "stop_loss", "take_profit", "maker_tp", "time_exit", "wick_stop", "open"} <= reasons
    assert missed > 0 and carry > 0
