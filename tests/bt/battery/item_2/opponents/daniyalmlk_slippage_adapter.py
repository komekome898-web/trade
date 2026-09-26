"""Survey candidate 105 `DaniyalMlk/slippage` (distribution slippage-tca 0.1.0 built from the GitHub clone,
commit 6985edb; venv item_0/c105; install record: item 0 survey_results/attempts/105.log) for the item 2 battery.

What the tool has for execution: impact models `LinearImpact(gamma, eta, epsilon)` (Almgren-Chriss: permanent
g(v) = gamma v, temporary h(v) = epsilon + eta v, src/slippage/impact.py 90-119), `SquareRootLaw(y, delta)`
(`peak_impact(Q, V, sigma) = y sigma (Q/V)**delta`, a fraction of price, 207-234), and
`simulate_prices(impact, trades, arrival_price, tau, volatility, ...)` -> the execution price of each trade
of a schedule (simulate.py 135-179: fill_k = mid_k - h(n_k / tau); mid_{k+1} = mid_k + drift tau +
volatility sqrt(tau) xi_k - gamma n_k).  It has no order, book, event loop, fee, latency or account.

Scene -> tool (only scenes whose every action is a market order and whose fill model is an impact function):
- linear_temporary (k, basis best_ask): LinearImpact(gamma=0, eta=k), arrival = the basis price, tau = 1,
  volatility = 0, drift = 0, two paths (the tool requires at least 2; with volatility 0 they are equal, path 0 is read); the schedule = the scene's market orders in time order.
- linear_permanent (gamma, k): LinearImpact(gamma, eta=k), same schedule.
- sqrt_temporary (eta, adv, basis mid): SquareRootLaw(y=eta, delta=0.5).peak_impact(Q, V=adv, sigma=1)
  (the scene's eta is the product y * sigma); price = mid * (1 + impact).
- The tool simulates a SALE (fills below the arrival price, mid falling by gamma n).  A buy is given as the
  sale of the same size and the price change is reflected about the arrival price (h and g take unsigned
  rates, so this is the same model with the trade's sign reversed).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

from slippage.impact import LinearImpact, SquareRootLaw  # noqa: E402  (the tool, in its venv)
from slippage.simulate import simulate_prices  # noqa: E402

TOOL = "DaniyalMlk/slippage(6985edb)"
KINDS = ("linear_temporary", "linear_permanent", "sqrt_temporary")


def _fm(fm):
    im = fm.get("impact")
    if fm.get("tier") != 6 or not im:
        return "約定の模型は市場影響の関数だけ(段 6 以外の埋まり方・列・楽観と悲観の両方を回す口が無い)"
    if im.get("kind") not in KINDS:
        return f"影響の関数 {im.get('kind')} が無い"
    return None


class Adapter:
    name = "opp_daniyalmlk_slippage"

    def run(self, inp):
        if not inp.get("fill_model"):
            raise NotExpressible(f"{TOOL}: 注文・板・約定の口が無く、影響の関数を選ばない場面を渡せない(影響の関数と執行の予定の費用の模擬だけ)")
        C.gate(inp, tool=TOOL, orders=("market",), events=("book", "trade"), fill_models=_fm, costs=(), account=("cash",))
        im = inp["fill_model"]["impact"]
        acts = sorted(C.places(inp), key=lambda a: a["t"])
        sides = {a["side"] for a in acts}
        if len(sides) != 1:
            raise NotExpressible(f"{TOOL}: 執行の予定は一方向(売り)の数量の列だけで、買いと売りを混ぜる口が無い")
        side = sides.pop()
        book = None
        for e in inp["market"]:
            if e["type"] == "book" and e["t"] <= acts[0]["t"]:
                book = e
        if book is None:
            raise NotExpressible(f"{TOOL}: 到着の値の元になる板が無い")
        bid, ask = book["bids"][0][0], book["asks"][0][0]
        basis = {"best_ask": ask if side == "buy" else bid, "mid": (bid + ask) / 2}.get(im.get("basis"))
        if basis is None:
            raise NotExpressible(f"{TOOL}: 到着の値の基準 {im.get('basis')} を渡せない")
        qty = [float(a["qty"]) for a in acts]
        if im["kind"] == "sqrt_temporary":
            if len(acts) != 1:
                raise NotExpressible(f"{TOOL}: 平方根則は 1 本の親注文の山の影響だけ")
            frac = SquareRootLaw(y=float(im["eta"]), delta=0.5).peak_impact(qty[0], float(im["adv"]), 1.0)
            pxs = [basis * (1 + frac) if side == "buy" else basis * (1 - frac)]
        else:
            model = LinearImpact(gamma=float(im.get("gamma", 0.0)), eta=float(im.get("k", 0.0)))
            _mid, fills = simulate_prices(model, qty, arrival_price=float(basis), tau=1.0, volatility=0.0,
                                          drift=0.0, paths=2, rng=np.random.default_rng(0))  # the tool needs >= 2 paths; volatility 0 makes them equal
            sale = [float(x) for x in fills[0]]
            pxs = [2 * basis - p for p in sale] if side == "buy" else sale
        fills = [{"ref": a["ref"], "px": p, "qty": q, "liq": "taker"} for a, p, q in zip(acts, pxs, qty)]
        return {"orders": {a["ref"]: {"status": "filled"} for a in acts}, "fills": fills}


TARGET = Adapter()
