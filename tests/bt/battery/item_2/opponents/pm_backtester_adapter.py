"""Survey candidate 92 `Quentin-Piot/prediction-market-backtester` (git clone src/c92, package pm_bt; venv item_2/c92 with
a .pth and the pyproject's dependencies, install record venvs/item_2/logs/c92.log) for the item 2 battery.

The tool's own part used: `ExecutionSimulator(ExecutionConfig(fee_bps, slippage_bps, slippage_volume_k, latency_bars),
initial_cash).execute_bar(bar_index, snapshot=MarketSnapshot(ts, market_id, outcome_id, mid_price, spread, recent_volume),
incoming_orders=[OrderIntent(...)])`, called the way its `BacktestEngine` calls it (backtest/engine.py 226-249): one
call per bar, the strategy's orders of that bar handed in with the bar, the snapshot's mid = the bar's close, spread None
(the simulator's default_spread), recent_volume = the bar's volume.  An order fills on the bar index + latency_bars at
mid +- spread / 2 +- slippage (slippage_bps, or slippage_volume_k x qty / recent_volume -- its impact term), with
fee_bps on the notional; OrderIntent.limit_price is not read by the simulator.
Bars: i2_common.bar_rows; orders go in with the bar chosen by i2_common.issue_schedule.  The tool's prices are
probabilities: MarketSnapshot refuses a mid outside [0, 1] (execution/simulator.py 55-57), and OrderIntent a limit outside
it; such a refusal is returned as the tool's refusal.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

from pm_bt.common.models import OrderIntent  # noqa: E402  (the tool)
from pm_bt.common.types import OrderSide  # noqa: E402
from pm_bt.execution.simulator import ExecutionConfig, ExecutionSimulator, MarketSnapshot  # noqa: E402

TOOL = "prediction-market-backtester(c77dff7) pm_bt"


def _ts(t):
    return D.datetime.fromtimestamp(t // 10**9, tz=D.timezone.utc) + D.timedelta(microseconds=(t % 10**9) // 1000)


def _fm(fm):
    if "range" in fm:
        return "楽観と悲観の両方を回す口が無い"
    imp = fm.get("impact") or {}
    if imp:
        return (f"市場影響 {imp.get('kind')} を渡す口が無い(この道具の影響は slippage_volume_k x 数量 / 足の出来高 の一時的な滑りだけ)")
    if fm.get("tier") in (None, 1):
        return None
    return f"段 {fm.get('tier')} を選ぶ口が無い(約定は足の終値 ± 広がりの半分 ± 滑りの 1 つだけ)"


class Adapter:
    name = "opp_pm_backtester"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit"), events=("book", "trade", "bar"), fill_models=_fm,
               costs=("maker_rate", "taker_rate"), account=("cash",))
        rate = C.single_fee_rate(inp, TOOL)
        if rate < 0:
            raise NotExpressible(f"{TOOL}: fee_bps は 0 以上だけ(負の率を渡す口が無い)")
        bars, _src = C.bar_rows(inp)
        if not bars:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(道具の入力は約定から作った足)")
        sched = C.issue_schedule(bars, inp["actions"])
        try:
            sim = ExecutionSimulator(ExecutionConfig(fee_bps=float(rate) * 1e4), initial_cash=float(inp["account"]["cash"]))
            rec = {"orders": {}, "fills": []}
            for k, b in enumerate(bars):
                orders = []
                for a in sched.get(k, []):
                    if a["op"] != "place":
                        raise NotExpressible(f"{TOOL}: 操作 {a['op']} の口が無い")
                    orders.append((a, OrderIntent(ts=_ts(a["t"]), market_id="X", outcome_id="yes", venue="kalshi",
                                                  side=OrderSide.BUY if a["side"] == "buy" else OrderSide.SELL, qty=a["qty"],
                                                  limit_price=a["px"], reason=a["ref"])))
                fills = sim.execute_bar(bar_index=k, snapshot=MarketSnapshot(ts=_ts(b["t"]), market_id="X", outcome_id="yes",
                                                                             mid_price=float(b["c"]), spread=None,
                                                                             recent_volume=float(b["v"])),
                                        incoming_orders=[o for _, o in orders])
                refs = [a["ref"] for a, _ in orders]
                for i, f in enumerate(fills):
                    ref = refs[i] if i < len(refs) else None
                    if ref:
                        rec["fills"].append({"ref": ref, "t": b["t"], "px": float(f.price_fill), "qty": float(f.qty_filled),
                                             "fee": float(f.fees), "liq": None})
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        for a in C.places(inp):
            got = sum(f["qty"] for f in rec["fills"] if f["ref"] == a["ref"])
            rec["orders"][a["ref"]] = {"status": C.status_from(got, a["qty"], active=False, canceled=got < a["qty"])}
        return rec


TARGET = Adapter()
