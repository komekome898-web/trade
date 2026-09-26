"""Item 4 critic, round 1 (rewritten at the close, L-470): the compatibility mouth on DECIMAL prices against the
independent reference of the stated rules.

The engine-vs-reference grid (tests/bt/item_4/test_i4_engine_vs_independent_bar_sim.py) draws prices on 0.5 ticks
(exact floats). Here: the option grid of tests/bt/item_4/i4_option_grid.py (every cell) with 0.1-tick decimal
prices (inexact floats, so the float order of operations shows) and 0.3 / 0.7 / 1.1 % levels, and every other
maker_tp cell also given take_profit_pct = 0.5 -- run through the MOUTH (`bot.bt.compat.run_backtest` with
`CostModel` and the signal `Strategy` interface, as the research scripts call it) and through the independent
reference `bot.bt.reference.bar_sim.run_bars` (written from the rule text only). Compared with the scene set's
tolerance |a - b| <= 1e-9 x max(1, |a|, |b|): fills (bar, side exact; price, size), round-trip PnL, equity per
bar, missed fills. A difference is a defect of the engine; the reference is never fitted to it.

Not compared: the metrics (the reference has none, SPEC.md §8-4) and the scenes the reference refuses that the
mouth does not (or the other way): both must refuse together (checked).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd
import pytest

ITEM4 = Path(__file__).resolve().parents[2] / "item_4"
if str(ITEM4) not in sys.path:
    sys.path.insert(0, str(ITEM4))

import i4_option_grid as G  # noqa: E402
from bot.bt.compat import CostModel, run_backtest  # noqa: E402
from bot.bt.reference.bar_sim import run_bars as ref_run_bars  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402

UNDECIDED = {"wick_short_history": "use_available", "same_side_exit_signal": "keep"}  # the lead's values
_SIG = {".": SignalType.HOLD, "B": SignalType.BUY, "S": SignalType.SELL, "C": SignalType.CLOSE}


class Script(Strategy):
    def __init__(self, signals: str, min_history: int):
        super().__init__({})
        self._s = signals
        self._m = min_history

    @property
    def min_history(self) -> int:
        return self._m

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        return Signal(_SIG[self._s[len(candles) - 1]])


def _bars(rng, n):
    rows, c = [], 1234.5
    for _ in range(n):
        o = round(c + rng.choice((0, 0, 0.1, -0.1, 0.7, -0.7, 3.3)), 1)
        cl = round(o + rng.uniform(-2, 2), 1)
        rows.append([o, round(max(o, cl) + rng.uniform(0, 1.3), 1), round(min(o, cl) - rng.uniform(0, 1.3), 1), cl])
        c = cl
    return rows


def _scene(k, cell):
    sc = G.make_scene(555_000 + k, cell)
    rng = random.Random(k)
    sc["bars"] = _bars(rng, G.N_BARS)
    o = sc["options"]
    for key in ("stop_loss_pct", "take_profit_pct", "maker_tp_pct"):
        if o[key]:
            o[key] = rng.choice((0.3, 0.7, 1.1))
    if cell[2] == "maker_tp" and k % 2 == 0:
        o["take_profit_pct"] = 0.5
    return sc


def run_mouth(sc: dict) -> dict:
    o = dict(sc["options"])
    o["costs"] = CostModel(**o["costs"])
    bars = sc["bars"]
    df = pd.DataFrame({"open": [b[0] for b in bars], "high": [b[1] for b in bars], "low": [b[2] for b in bars],
                       "close": [b[3] for b in bars], "volume": [1.0] * len(bars)},
                      index=pd.date_range("2026-01-05", periods=len(bars), freq="min", tz="UTC"))
    res = run_backtest(Script(sc["signals"], sc["min_history"]), df, **o)
    fills = [{"bar": e["bar"], "side": e["side"], "price": e["price"], "size": e["size"]}
             for e in res.trade_log if not e["side"].startswith("CANCEL_")]
    return {"fills": fills, "pnls": [float(p) for p in res.trade_pnls],
            "equity": [float(x) for x in res.equity_curve.tolist()], "missed_fills": int(res.missed_fills)}


def run_reference(sc: dict) -> dict:
    o = sc["options"]
    ro = {"capital": o["initial_equity_jpy"], "order_amount": o["order_notional_jpy"],
          "bar_seconds": int(o["bar_seconds"]), "costs": dict(o["costs"]), "undecided": UNDECIDED}
    for k in ("execution", "maker_timeout_bars", "allow_short", "swap_daily_pct", "stop_loss_pct", "take_profit_pct",
              "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode",
              "stop_window_bars"):
        ro[k] = o[k]
    # the mouth asks the strategy from bar min_history on; the reference takes the signals it would see
    sig = {i: _SIG[ch].name for i, ch in enumerate(sc["signals"]) if ch != "." and i >= sc["min_history"]}
    return ref_run_bars([tuple(b) for b in sc["bars"]], sig, ro).to_floats()


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def diff(e: dict, r: dict) -> list:
    out = []
    if [(f["bar"], f["side"]) for f in e["fills"]] != [(f["bar"], f["side"]) for f in r["fills"]]:
        return [("fills", [(f["bar"], f["side"], f["price"]) for f in e["fills"]],
                 [(f["bar"], f["side"], f["price"]) for f in r["fills"]])]
    for fe, fr in zip(e["fills"], r["fills"]):
        if not (_close(fe["price"], fr["price"]) and _close(fe["size"], fr["size"])):
            out.append(("fill", fe, fr))
    if len(e["pnls"]) != len(r["pnls"]) or not all(_close(a, b) for a, b in zip(e["pnls"], r["pnls"])):
        out.append(("pnls", e["pnls"], r["pnls"]))
    if len(e["equity"]) != len(r["equity"]) or not all(_close(a, b) for a, b in zip(e["equity"], r["equity"])):
        out.append(("equity", e["equity"], r["equity"]))
    if e["missed_fills"] != r["missed_fills"]:
        out.append(("missed_fills", e["missed_fills"], r["missed_fills"]))
    return out


CELLS = list(G.grid())
CHUNK = 144


@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_decimal_price_cells_match_the_independent_reference(start):
    bad = []
    for k in range(start, min(start + CHUNK, len(CELLS))):
        sc = _scene(k, CELLS[k])
        try:
            e = run_mouth(sc)
        except ValueError as exc:
            e = {"refused": str(exc)}
        try:
            r = run_reference(sc)
        except Exception as exc:  # RefusedConfig and the reference's own bar check
            r = {"refused": str(exc)}
        if "refused" in e or "refused" in r:
            if ("refused" in e) != ("refused" in r):
                bad.append((CELLS[k], e.get("refused"), r.get("refused")))
            continue
        d = diff(e, r)
        if d:
            bad.append((CELLS[k], d[0]))
    assert not bad, f"{len(bad)} cells differ from the independent reference; first: {bad[:2]}"


def test_the_decimal_grid_is_not_vacuous():
    reasons, n_fill = set(), 0
    for k in range(0, len(CELLS), 9):
        sc = _scene(k, CELLS[k])
        r = run_reference(sc)
        n_fill += len(r["fills"])
    assert n_fill > 100
    from bot.bt.reference.bar_sim import run_bars as rb  # noqa: F401
    for k in range(0, len(CELLS), 9):
        sc = _scene(k, CELLS[k])
        o = sc["options"]
        ro = {"capital": o["initial_equity_jpy"], "order_amount": o["order_notional_jpy"],
              "bar_seconds": int(o["bar_seconds"]), "costs": dict(o["costs"]), "undecided": UNDECIDED}
        for key in ("execution", "maker_timeout_bars", "allow_short", "swap_daily_pct", "stop_loss_pct",
                    "take_profit_pct", "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides",
                    "stop_mode", "stop_window_bars"):
            ro[key] = o[key]
        sig = {i: _SIG[ch].name for i, ch in enumerate(sc["signals"]) if ch != "." and i >= sc["min_history"]}
        reasons |= {f.reason for f in rb([tuple(b) for b in sc["bars"]], sig, ro).fills}
    assert {"signal", "stop_loss", "take_profit", "maker_tp", "wick_invalidation", "max_hold"} <= reasons, reasons
