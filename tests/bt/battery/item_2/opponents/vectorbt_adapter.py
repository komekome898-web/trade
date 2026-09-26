"""Survey candidate 73 `vectorbt` (PyPI 1.1.0, the venv item 1 installed: venvs/item_1/vectorbt, install record
tests/bt/battery/item_1/opponents/RUNNABILITY.tsv) for the item 2 battery.

The tool's own call used: `vbt.Portfolio.from_orders(close, size, price, fees, slippage, min_size, init_cash, ...)`
-- one order amount per bar, executed at the bar's given price -- and the portfolio's own records: `orders.records_readable`
(each fill's price, size, fees), `trades` / `positions` (`pnl` of closed and open trades) and the asset position.
Bars: i2_common.bar_rows (one bar per print unless the scene has bars).  An order goes on the first bar that starts after
the action's time (so no price from before the action fills it), with price = that bar's open.  vectorbt's orders are
amounts at a price: limit / stop / IOC / FOK / post-only / cancel / amend have no argument and are refused.  One fee rate
(`fees`, i2_common.single_fee_rate); a spread cost goes in as `slippage` = half the spread over the price (the tool's
slippage is a fraction of the price).  Account: realized = pnl of closed trades, unrealized = pnl of open trades (marked
at the last close), position = the asset's position after the last bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import vectorbt as vbt  # noqa: E402  (the tool)

TOOL = "vectorbt 1.1.0"


class Adapter:
    name = "opp_vectorbt"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market",), events=("book", "trade", "bar"),
               fill_models=lambda fm: C.bar_fill_models(fm), costs=("maker_rate", "taker_rate", "spread"),
               account=("cash",))
        bars, _src = C.bar_rows(inp)
        if not bars:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(from_orders は価格の列を取る)")
        rate = C.single_fee_rate(inp, TOOL)
        n = len(bars)
        size = np.full(n, np.nan)
        where = {}
        for a in sorted(C.places(inp), key=lambda x: x["t"]):
            k = next((i for i, b in enumerate(bars) if b["t"] - b["span_ns"] > a["t"]), None)
            if k is None:
                where[a["ref"]] = None
                continue
            if not np.isnan(size[k]):
                raise NotExpressible(f"{TOOL}: 同じ足に 2 つの注文を置く口が無い(from_orders は足ごとに数量 1 つ)")
            size[k] = a["qty"] if a["side"] == "buy" else -a["qty"]
            where[a["ref"]] = k
        close = pd.Series([float(b["c"]) for b in bars])
        price = pd.Series([float(b["o"]) for b in bars])
        c = inp.get("costs") or {}
        slip = 0.0
        if c.get("spread"):
            slip = float(c["spread"]) / 2 / float(price.iloc[0])
        try:
            pf = vbt.Portfolio.from_orders(close, size=size, price=price, fees=float(rate), slippage=slip,
                                           init_cash=float(inp["account"]["cash"]), freq="1s")
            recs = pf.orders.records_arr
            pos = float(pf.assets().iloc[-1])
            realized = float(pf.trades.closed.pnl.sum()) if pf.trades.closed.count() else 0.0
            unreal = float(pf.trades.open.pnl.sum()) if pf.trades.open.count() else 0.0
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        rec = {"orders": {}, "fills": [], "account": {"position": pos, "realized": realized, "unrealized": unreal}}
        by_idx = {int(r["idx"]): r for r in recs}
        for a in C.places(inp):
            k = where.get(a["ref"])
            r = by_idx.get(k) if k is not None else None
            if r is not None:
                rec["fills"].append({"ref": a["ref"], "t": bars[k]["t"] - bars[k]["span_ns"], "px": float(r["price"]),
                                     "qty": float(r["size"]), "fee": float(r["fees"]), "liq": None})
            got = float(r["size"]) if r is not None else 0.0
            rec["orders"][a["ref"]] = {"status": C.status_from(got, a["qty"], active=False, canceled=got < a["qty"])}
        return rec


TARGET = Adapter()
