"""Survey candidate 35 `thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator-`, run in its own venv
(round r13-1, LEAD_DESIGN.md section 9.2 item 36).

Source: GitHub clone at commit 794fa647f8c8168a6f30338ea0987d26124d6101 (cloned 2026-09-24,
`survey_results/attempts/35.log`). The published tree has no src/ directory: its 8 modules are files named
'src <name>.py' at the top, so `main.py` stops at `from src.models import` (ModuleNotFoundError). The lead's three
steps, repeated by the scene keeper on 2026-09-25 (the same log): (1) a copy of the clone with the 8 files moved into
src/ under their own names (no byte of them changed), (2) `python3 -m venv --system-site-packages .venv` and
`pip install matplotlib`, (3) the published `outputs` (a 1,139-byte file) renamed so `main.py` can make the
directory -- then `main.py` ran to the end (rc=0). This adapter imports the copy's `src` package (a .pth file in that
venv points at the copy).

What the tool is (read in the copy, the same bytes as the clone): an execution-cost simulator. `src.execution.
execute_order(prices, schedule, market_parameters, side)` fills a fixed schedule against a price path with the
impact functions it imports directly (`src.impact.temporary_market_impact` / `permanent_market_impact` /
`execution_price`); `src.simulator.monte_carlo_execution` draws geometric Brownian price paths; `src.strategies`
makes TWAP / front-loaded / optimal schedules. There is no event, event loop, strategy callback, order object,
cancel, notice, clock, latency or account. The P0-7 row of opponents/CONSIDERED.md (removed in round r13-1 when the
tool ran; its judgment was 持たないと確認した) gave, per capability of the viewpoint, in the clone's file names:
  (1) fill model: execute_order calls the impact functions it imports directly ('src execution.py' lines 1-7, 34-57);
      no argument takes a function;
  (2) latency: 'src simulator.py', 'src execution.py', 'src impact.py' grepped for latency / delay: 0 hits; there is
      no order object, the schedule's quantity fills at that period's price ('src execution.py' lines 10-60);
  (3) cost: the same 3 files grepped for fee / commission: 0 hits; the only cost is the impact formula
      ('src impact.py' lines 4, 27, 39);
  (4) account: the same 3 files grepped for cash / account: 0 hits.
Every scene is answered by a real call into the tool (`attempt`), never by reading the text alone.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

from _vector_base import VectorBase  # noqa: E402

import numpy as np  # noqa: E402
from src import execution as X  # noqa: E402
from src import models as M  # noqa: E402

PLUG_KW = {"p7-fill-model-swap": "fill_model", "p7-latency-model-swap": "latency_model",
           "p7-cost-model-swap": "cost_model", "p7-cost-per-unit": "cost_model", "p7-account-swap": "account"}


def _market():
    return M.MarketParameters(initial_price=100.0, volatility=0.0, temporary_impact=0.0, permanent_impact=0.0,
                              impact_exponent=1.0, volume_per_period=100.0)


def _call(**extra) -> str:
    """execute_order on a 3-step flat price path (100) and a 1-unit schedule, with extra keyword arguments."""
    try:
        r = X.execute_order(np.array([100.0, 100.0, 100.0]), np.array([1.0, 0.0, 0.0]), _market(), side="buy", **extra)
        return f"-> 平均の執行価格 {float(r['average_execution_price'])}"
    except Exception as exc:  # noqa: BLE001
        return f"-> {type(exc).__name__}: {str(exc)[:160]}"


class ThirupathikannanExecsimAdapter(VectorBase):
    name = "opp_thirupathikannan_execsim"
    what = ("この道具は決めた発注の計画を価格の道に当てて執行の費用を出す模擬器で、事象を流して戦略を呼ぶ機関・注文の物・取消・通知・"
            "時計・遅延・口座が無い")

    def attempt(self, scene_id: str) -> str:
        sig = str(inspect.signature(X.execute_order))
        if scene_id in PLUG_KW:
            kw = PLUG_KW[scene_id]
            return (f"src.execution.execute_order{sig} に、差し込みの物を {kw}= で渡した "
                    + _call(**{kw: object()}) + "(関数や物を渡す引数が無い)")
        names = sorted(n for n in dir(X) if not n.startswith("_"))
        return (f"src.execution.execute_order{sig} を 3 期の平らな価格の道と 1 単位の計画で呼んだ " + _call()
                + f"。src.execution の公開の名前 {names}(事象・戦略・注文を受ける名前が無い)")
