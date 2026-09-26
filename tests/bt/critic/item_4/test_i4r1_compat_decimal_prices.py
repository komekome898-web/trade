"""Item 4 critic, round 1: the compatibility mouth against the LIVE old engine on prices the golden grid leaves out.

The worker's golden grid (tests/bt/compat/golden/compat_golden_scenes.py) draws prices on 0.5 ticks (exact
floats) and names "take_profit_pct together with maker_tp" as not in the grid. Here: the same option grid
(every cell) with 0.1-tick decimal prices (inexact floats, so the float order of operations shows) and
0.3 / 0.7 / 1.1 % levels, and every other maker_tp cell also given take_profit_pct = 0.5. Bit for bit (JSON text of
the whole output), as the mouth's docstring claims. Runs only while the old engine is in src/bot/backtest/.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

GOLDEN = Path(__file__).resolve().parents[2] / "compat" / "golden"
if str(GOLDEN) not in sys.path:
    sys.path.insert(0, str(GOLDEN))

import compat_golden_scenes as G  # noqa: E402
from compat_golden_run import run  # noqa: E402


def _old_engine_present() -> bool:
    import bot.backtest.engine as E
    return E.run_backtest.__module__ == "bot.backtest.engine"


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


CELLS = list(G.grid())
CHUNK = 144


@pytest.mark.skipif(not _old_engine_present(), reason="the old engine has been replaced")
@pytest.mark.parametrize("start", range(0, len(CELLS), CHUNK))
def test_decimal_price_cells_match_the_live_old_engine(start):
    import bot.backtest.engine as OLD
    import bot.bt.compat.engine as NEW
    for k in range(start, min(start + CHUNK, len(CELLS))):
        sc = _scene(k, CELLS[k])
        outs = []
        for eng in (OLD, NEW):
            try:
                outs.append(json.dumps(run(eng, sc), sort_keys=True))
            except ValueError as exc:
                outs.append(json.dumps({"refused": str(exc)}))
        assert outs[0] == outs[1], CELLS[k]
