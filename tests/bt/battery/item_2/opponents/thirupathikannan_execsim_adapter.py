"""Survey candidate 35 `thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator-` (clone at commit
794fa64; item 0's runnable copy c35_run with the 8 'src <name>.py' files moved into src/ unchanged, venv
c35_run/.venv; install record: item 0 survey_results/attempts/35.log) for the item 2 battery.

The tool's execution API: `src.execution.execute_order(prices, schedule, market_parameters, side)` fills a fixed
schedule against a price path with `src.impact.temporary_market_impact(price, quantity, volume, coefficient,
exponent) = price * coefficient * (|quantity| / volume) ** exponent`, `permanent_market_impact(price,
cumulative_quantity, coefficient) = price * coefficient * |cumulative_quantity|` (the cumulative quantity
includes the current trade) and `execution_price(...) = price +/- (temporary + permanent)` (src/impact.py).
It has no order, book, event, fee, latency, notice or account.

Only the square-root scene is the tool's form: execute_order([mid], [Q], params(volume_per_period=adv,
temporary_impact=eta, impact_exponent=0.5, permanent_impact=0), side).  The linear forms of the scenes (an
impact of k x quantity in price units, a permanent move after the own fill) are not the tool's forms (its
impact is proportional to the price and its permanent term includes the current trade).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

import i2_common as C  # noqa: E402
from probe_base import ProbeAdapter, signature_probe  # noqa: E402

from src.execution import execute_order  # noqa: E402  (the tool, via the venv's .pth)
from src.impact import permanent_market_impact, temporary_market_impact  # noqa: E402


class Adapter(ProbeAdapter):
    name = "opp_thirupathikannan_execsim"
    tool = "thirupathikannan-ai/Optimal-Execution-And-Market-Impact-Simulator(794fa64)"
    what = "執行の口は予定の数量の列を値の列に当てる execute_order と、値に比例する影響の関数だけ"

    def probe(self):
        return signature_probe(execute_order, temporary_market_impact, permanent_market_impact)

    def why_not(self, inp):
        fm = inp.get("fill_model") or {}
        im = fm.get("impact") or {}
        if im.get("kind") in ("linear_temporary", "linear_permanent"):
            return (f"影響の形 {im['kind']}(値に依らない係数 × 数量)を渡す口が無い: 道具の影響は値 × 係数 × 参加率^指数で、"
                    "恒久の影響は今回の約定を含む累計の数量に掛かる")
        return "注文・板・約定・取消・遅延・費用・口座の口が無く、影響の関数を選ばない場面を渡せない"

    def express(self, inp):
        im = (inp.get("fill_model") or {}).get("impact") or {}
        if im.get("kind") != "sqrt_temporary" or im.get("basis") != "mid":
            return None
        acts = C.places(inp)
        if len(acts) != 1 or acts[0]["type"] != "market" or inp["actions"] != acts:
            return None
        a = acts[0]
        book = [e for e in inp["market"] if e["type"] == "book" and e["t"] <= a["t"]][-1]
        mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
        params = SimpleNamespace(volume_per_period=float(im["adv"]), temporary_impact=float(im["eta"]),
                                 impact_exponent=0.5, permanent_impact=0.0)
        res = execute_order(np.array([mid]), np.array([float(a["qty"])]), params, side=a["side"])
        px = float(res["execution_prices"][0]) if isinstance(res, dict) and "execution_prices" in res else float(np.asarray(res["execution_price"])[0])
        return {"orders": {a["ref"]: {"status": "filled"}}, "fills": [{"ref": a["ref"], "px": px, "qty": float(a["qty"]), "liq": "taker"}]}


TARGET = Adapter()
