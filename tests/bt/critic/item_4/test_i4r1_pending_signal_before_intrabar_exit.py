"""Item 4 critic, round 1 (i4-r1-01 / i4-r1-02): a signal pending for bar j's OPEN versus the intrabar exits of bar j.

The stated rules (tests/bt/battery/item_4/DEFINITIONS.md):
  R-T1  the signal of bar i fills at bar i+1's open (taker).
  R-P3  the stop fills when bar j's range reaches its level; R-P4 / R-X1 the take-profits fill on a strict
        traded-through of bar j's range.
The open of bar j comes before the rest of bar j's range. When the strategy's signal at bar j-1 closes the
position at bar j's open, the position no longer exists during bar j's range, so no stop / take-profit of
bar j can fill; a take-profit booked at its level instead of the open uses the bar's later high (low) to
give a better exit than the open (optimistic), a stop booked at its level gives a worse one.
(The old engine's own docstring states "a signal at bar i executes at bar i+1's OPEN"; the old engine drops
the pending signal instead. The compatibility rule set keeps the old result; the native "spec" rule set and
the reference of the stated rules must follow R-T1.)

Grid (the rule's input space, not any engine's branches):
  exit kind {stop_loss, take_profit, maker_tp} x direction {long, short} x closing signal {opposite, CLOSE}
  -- bar j's open strictly between the stop and the take-profit levels, bar j's range reaching the level.
Control: the same bars without the closing signal must exit at the level (the grid is not vacuous).
Not in the grid (named): a bar j that OPENS beyond a level (both happen at the open), the maker execution
(its closing signal places a limit at the close, not an open fill), costs other than 0, the time exit and
the wick exit (the stated rules R-H2 / R-W3 already drop the pending signal and both fill at the open).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_4"
for p in (BATTERY, BATTERY / "adapters"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import i4_scenes as S  # noqa: E402


def _item4_adapter():
    """The item-4 adapter by its path: every battery item has an adapters/new_impl.py, so the bare name `new_impl`
    can already be bound to another item's adapter when the whole suite is collected (a collection error of the
    full run, 2026-09-26 close)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("i4_critic_new_impl", BATTERY / "adapters" / "new_impl.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TARGET


NEW = _item4_adapter()

EXITS = ("stop_loss", "take_profit", "maker_tp")
DIRS = ("long", "short")
CLOSERS = ("opposite", "CLOSE")


def _case(exit_kind: str, direction: str):
    """Entry at bar 2's open 100 (signal at bar 1); stop 2 %, take-profit 3 %; bar 4 opens between the levels
    and its range reaches the exit's level."""
    if direction == "long":
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101.5, 99.5, 101), (101, 102, 100, 101)]
        bar4 = (101, 101.5, 97, 98.5) if exit_kind == "stop_loss" else (101, 104, 100.5, 103.5)
        level = 98.0 if exit_kind == "stop_loss" else 103.0
        open4, entry_sig, opposite = 101.0, "BUY", "SELL"
    else:
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 100.5, 99, 99.5), (99.5, 100, 99, 99.5)]
        bar4 = (99.5, 103, 99, 101.5) if exit_kind == "stop_loss" else (99.5, 100, 96, 96.5)
        level = 102.0 if exit_kind == "stop_loss" else 97.0
        open4, entry_sig, opposite = 99.5, "SELL", "BUY"
    rows = rows + [bar4, (100, 100.5, 99.5, 100)]
    over = {"allow_short": direction == "short"}
    if exit_kind == "stop_loss":
        over["stop_loss_pct"] = 2.0
    elif exit_kind == "take_profit":
        over["take_profit_pct"] = 3.0
    else:
        over.update(exit_execution="maker_tp", maker_tp_pct=3.0)
    return S.mk_bars(rows), S.cfg(**over), entry_sig, opposite, open4, level


def _ref_options(cfg: dict, bar_seconds: int = 60) -> dict:
    """The battery config -> the independent reference's options (src/bot/bt/reference/SPEC.md §7). The two
    undecided points take the lead's values (VERDICTS 2026-09-26, U1 = use_available, U2 = keep)."""
    o = {k: v for k, v in cfg.items() if k not in ("initial_equity", "order_notional")}
    o.update(capital=cfg["initial_equity"], order_amount=cfg["order_notional"], bar_seconds=bar_seconds,
             undecided={"wick_short_history": "use_available", "same_side_exit_signal": "keep"})
    return o


def _fills(inp, model):
    i = dict(inp)
    i["model"] = model
    return [(f["bar"], f["side"], f["price"]) for f in NEW.run(i)["fills"]]


@pytest.mark.parametrize("closer", CLOSERS)
@pytest.mark.parametrize("direction", DIRS)
@pytest.mark.parametrize("exit_kind", EXITS)
def test_spec_model_closes_at_the_open_when_a_signal_is_pending(exit_kind, direction, closer):
    bars, cfg, entry, opposite, open4, _ = _case(exit_kind, direction)
    sig = [(1, entry), (3, opposite if closer == "opposite" else "CLOSE")]
    got = _fills(S.bars_input(bars, sig, cfg, want=("fills",)), "spec")
    side = "LONG" if direction == "long" else "SHORT"
    assert got == [(2, f"OPEN_{side}", 100.0), (4, f"CLOSE_{side}", open4)], (
        f"R-T1: the signal of bar 3 closes at bar 4's open {open4}; got {got}")


@pytest.mark.parametrize("direction", DIRS)
@pytest.mark.parametrize("exit_kind", EXITS)
def test_control_without_the_signal_exits_at_the_level(exit_kind, direction):
    bars, cfg, entry, _, _, level = _case(exit_kind, direction)
    got = _fills(S.bars_input(bars, [(1, entry)], cfg, want=("fills",)), "spec")
    side = "LONG" if direction == "long" else "SHORT"
    assert got == [(2, f"OPEN_{side}", 100.0), (4, f"CLOSE_{side}", level)], got


@pytest.mark.parametrize("closer", CLOSERS)
@pytest.mark.parametrize("direction", DIRS)
@pytest.mark.parametrize("exit_kind", EXITS)
def test_the_rule_reference_closes_at_the_open_when_a_signal_is_pending(exit_kind, direction, closer):
    """The independent reference of the stated rules (bot.bt.reference.bar_sim.run_bars; bar_rules.py was removed in
    the finishing stage) must give R-T1's answer too, not the old engine's documented behaviour."""
    from bot.bt.reference.bar_sim import run_bars
    bars, cfg, entry, opposite, open4, _ = _case(exit_kind, direction)
    sig = {1: entry, 3: opposite if closer == "opposite" else "CLOSE"}
    got = [(f["bar"], f["side"], f["price"]) for f in run_bars(bars, sig, _ref_options(cfg)).to_floats()["fills"]]
    side = "LONG" if direction == "long" else "SHORT"
    assert got == [(2, f"OPEN_{side}", 100.0), (4, f"CLOSE_{side}", open4)], got
