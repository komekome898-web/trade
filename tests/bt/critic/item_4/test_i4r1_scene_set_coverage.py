"""Item 4 critic, round 1: what the item-4 scene set must hold (the scene-keeper's side; i4-r1-02, 05, 06).

(a) i4-r1-05: a viewpoint of the old bar engine's behaviour (I4-8 .. I4-17) must have at least one value scene
    that a bar tool can be handed without an incidental barrier -- no signal on bar 0 (a common tool, e.g.
    backtesting.py, never calls the strategy on the first bar: survey_results/opp_backtesting.tsv), and for I4-10
    (the stop-first priority; the fee is not the viewpoint) equal maker and taker fee rates (Backtrader,
    backtesting.py, vectorbt, VnPy, PyBroker, zipline-reloaded have one fee rate and are 「結果なし」 on
    i4-10-priority for that reason only: materials/survey_breakdown.tsv).
(b) i4-r1-06: the I4-2 property grid must reach the paths whose invariants matter most (stop, take-profit,
    maker entry, carry, time exit, wick exit): today every case is taker-only (i4_scenes.taker_rule), where the
    invariants follow from the exact expected answer already judged.
(c) i4-r1-02: a scene must pin the stated rules' answer when a signal is pending for bar j's open and bar j's
    range also reaches a stop / take-profit level of the open position (R-T1 against R-P3 / R-P4 / R-X1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_4"
if str(BATTERY) not in sys.path:
    sys.path.insert(0, str(BATTERY))

import i4_scenes as S  # noqa: E402

BAR_VIEWPOINTS = [f"I4-{k}" for k in range(8, 18)]


def _bar_value_scenes(vp):
    return [s for s in S.SCENES if s["viewpoint"] == vp and s["kind"] == "値" and "input" in s
            and s["input"].get("op") == "bars"]


@pytest.mark.parametrize("vp", BAR_VIEWPOINTS)
def test_a_value_scene_without_a_bar_0_signal(vp):
    scenes = _bar_value_scenes(vp)
    if not scenes:
        pytest.skip(f"{vp} has no bar value scene (op metrics / split)")
    assert any(all(x["bar"] >= 1 for x in s["input"]["signals"]) for s in scenes), [s["id"] for s in scenes]


def test_the_stop_priority_viewpoint_has_a_scene_with_one_fee_rate():
    scenes = _bar_value_scenes("I4-10")
    assert any(s["input"]["config"]["costs"]["taker_fee_pct"] == s["input"]["config"]["costs"]["maker_fee_pct"]
               for s in scenes), [(s["id"], s["input"]["config"]["costs"]) for s in scenes]


@pytest.mark.parametrize("path", ["stop_loss_pct", "take_profit_pct", "maker", "swap", "max_hold_bars", "wick"])
def test_the_property_grid_reaches_the_path(path):
    grid = next(s for s in S.SCENES if s["viewpoint"] == "I4-2")
    cfgs = [c["config"] for c in grid["cases"]]
    has = {"stop_loss_pct": lambda c: c["stop_loss_pct"], "take_profit_pct": lambda c: c["take_profit_pct"],
           "maker": lambda c: c["execution"] == "maker", "swap": lambda c: c["swap_daily_pct"],
           "max_hold_bars": lambda c: c["max_hold_bars"], "wick": lambda c: c["stop_mode"] == "wick_invalidation"}[path]
    assert any(has(c) for c in cfgs), f"no I4-2 case has {path}"


def _levels(cfg, entry, d):
    out = []
    if cfg["stop_loss_pct"]:
        out.append(("stop", entry * (1 - d * cfg["stop_loss_pct"] / 100)))
    if cfg["take_profit_pct"]:
        out.append(("tp", entry * (1 + d * cfg["take_profit_pct"] / 100)))
    if cfg["exit_execution"] == "maker_tp":
        out.append(("tp", entry * (1 + d * cfg["maker_tp_pct"] / 100)))
    return out


def test_a_scene_pins_a_pending_signal_against_an_intrabar_exit():
    """Some scene's input has, for an open position (from its expected fills), a signal at bar j-1 that would
    close it at bar j's open while bar j's range also reaches one of its stop / take-profit levels."""
    found = []
    for s in S.SCENES:
        inp = s.get("input")
        if not inp or inp.get("op") != "bars" or inp["config"]["execution"] != "taker":
            continue
        exp = s["expect"].get("spec", s["expect"]) if "models" in inp else s["expect"]
        exp = exp.get("engine", exp)
        fills, bars, cfg = exp.get("fills") or [], inp["bars"], inp["config"]
        sig = {x["bar"]: x["signal"] for x in inp["signals"]}
        for o in fills:
            if not o["side"].startswith("OPEN"):
                continue
            d = 1 if o["side"] == "OPEN_LONG" else -1
            closer = "SELL" if d > 0 else "BUY"
            for j in range(o["bar"] + 1, len(bars)):
                if sig.get(j - 1) not in (closer, "CLOSE"):
                    continue
                b = bars[j]
                for kind, lv in _levels(cfg, o["price"], d):
                    hit = (b["low"] <= lv if d > 0 else b["high"] >= lv) if kind == "stop" else \
                          (b["high"] > lv if d > 0 else b["low"] < lv)
                    if hit:
                        found.append((s["id"], j, kind))
                break
    assert found, "no scene pins R-T1 against R-P3 / R-P4 / R-X1 on the same bar"
