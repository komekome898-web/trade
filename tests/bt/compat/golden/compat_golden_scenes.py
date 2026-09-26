"""Seeded scenes for the golden files of the old bar engine (item 4, old item 14).

Every scene is made from (seed, grid cell) by `make_scene` with the standard
library's random only, and its inputs are also written into the golden file,
so a test can check that the generator still makes the same inputs.

The grid (every combination, 2 x 2 x 7 x 2 x 3 x 2 x 3 = 1008 cells) is built from the old engine's
options, not from any engine's branches: execution x allow_short x
protective exit x max_hold_bars x entry_sides x entry_mask x swap sign.
Not in the grid (named here, per the adversarial-test rule): take_profit_pct
together with maker_tp (the combination the old engine allows is covered by
"sl+tp" and "maker_tp" separately), costs as a grid axis (each cell draws
its costs from COST_SETS by its seed), stop_window_bars and maker_timeout_bars
as axes (drawn 1..4 by the seed), bar counts other than N_BARS (edge scenes:
0 bars, 1 bar, min_history >= bars are in EDGE_SCENES).
"""
from __future__ import annotations

import itertools
import random

N_BARS = 40
GOLDEN_SEED = 20260926
EXECUTIONS = ("taker", "maker")
SHORTS = (False, True)
PROTECT = ("none", "sl", "tp", "sl+tp", "maker_tp", "sl+maker_tp", "wick")
MAX_HOLD = (None, 3)
SIDES = ("both", "long", "short")
MASKS = ("none", "random")
SWAPS = (0.0, 0.5, -0.3)
COST_SETS = (
    {"taker_fee_pct": 0.0, "maker_fee_pct": 0.0, "slippage_pct": 0.0, "spread_pct": 0.0},
    {"taker_fee_pct": 0.15, "maker_fee_pct": 0.15, "slippage_pct": 0.05, "spread_pct": 0.1},
    {"taker_fee_pct": 0.1, "maker_fee_pct": -0.01, "slippage_pct": 0.02, "spread_pct": 0.04},
)


def grid():
    return list(itertools.product(EXECUTIONS, SHORTS, PROTECT, MAX_HOLD, SIDES, MASKS, SWAPS))


def make_bars(rng: random.Random, n: int):
    """Integer-tick OHLC (tick 0.5, so every price is an exact float)."""
    rows = []
    close = 200
    for _ in range(n):
        gap = rng.choice((0, 0, 0, 1, -1, 4, -4))
        o = max(20, close + gap)
        c = max(20, o + rng.randint(-6, 6))
        h = max(o, c) + rng.randint(0, 4)
        lo = max(10, min(o, c) - rng.randint(0, 4))
        rows.append((o, h, lo, c))
        close = c
    return [[x * 0.5 for x in r] for r in rows]


def make_scene(seed: int, cell) -> dict:
    execution, short, protect, max_hold, sides, mask, swap = cell
    rng = random.Random(seed)
    bars = make_bars(rng, N_BARS)
    sig = "".join(rng.choices("..BSC", weights=(35, 25, 15, 15, 10), k=N_BARS))
    opts = {"initial_equity_jpy": 6000.0, "order_notional_jpy": 3000.0, "costs": dict(rng.choice(COST_SETS)),
            "execution": execution, "maker_timeout_bars": rng.randint(1, 4), "allow_short": short,
            "swap_daily_pct": swap, "bar_seconds": rng.choice((60.0, 3600.0)), "stop_loss_pct": None,
            "take_profit_pct": None, "max_hold_bars": max_hold, "exit_execution": "signal", "maker_tp_pct": None,
            "entry_mask": None, "entry_sides": sides, "stop_mode": "fixed", "stop_window_bars": None}
    if "sl" in protect.split("+"):
        opts["stop_loss_pct"] = rng.choice((1.0, 2.5))
    if "tp" in protect.split("+"):
        opts["take_profit_pct"] = rng.choice((1.0, 3.0))
    if "maker_tp" in protect.split("+"):
        opts["exit_execution"], opts["maker_tp_pct"] = "maker_tp", rng.choice((1.5, 2.0))
    if protect == "wick":
        opts["stop_mode"], opts["stop_window_bars"] = "wick_invalidation", rng.randint(1, 4)
    if mask == "random":
        opts["entry_mask"] = [rng.random() < 0.7 for _ in range(N_BARS)]
    return {"seed": seed, "cell": list(cell), "bars": bars, "signals": sig, "min_history": rng.randint(0, 3),
            "options": opts}


def scenes():
    out = []
    for k, cell in enumerate(grid()):
        out.append(make_scene(GOLDEN_SEED + k, cell))
    return out


EDGE_SCENES = [
    {"seed": None, "cell": ["edge", "no bars"], "bars": [], "signals": "", "min_history": 0,
     "options": {"initial_equity_jpy": 6000.0, "order_notional_jpy": 3000.0}},
    {"seed": None, "cell": ["edge", "one bar"], "bars": [[100.0, 101.0, 99.0, 100.5]], "signals": "B",
     "min_history": 0, "options": {}},
    {"seed": None, "cell": ["edge", "min_history beyond the bars"], "bars": [[100.0, 101.0, 99.0, 100.5]] * 5,
     "signals": "BBBBB", "min_history": 9, "options": {}},
]
