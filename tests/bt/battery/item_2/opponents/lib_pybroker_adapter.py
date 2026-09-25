"""Survey candidate 4 `PyBroker` (PyPI lib-pybroker 2.0.1, venv item_0/lib-pybroker; install record: item 0
survey_results/attempts/4.log) for the item 2 battery.

The tool's own calls used: `pybroker.Strategy(DataFrame, start, end, StrategyConfig(initial_cash, fee_mode=
FeeMode.ORDER_PERCENT, fee_amount, enable_fractional_shares=True, leverage))`, `add_execution(fn, ["X"])`,
`backtest(warmup=None)`; inside fn the ExecContext `buy_shares / sell_shares`, `buy_limit_price /
sell_limit_price`, `pending_orders()`, `cancel_pending_order(id)`; the result's `orders` table (type, date,
created, order_type, shares, limit_price, fill_price, fees).  Orders fill `buy_delay` = 1 bar later (the tool's
default); one buy and one sell order per bar; no stop entry order, IOC, FOK, post-only, amend, latency, notices.

Scene -> tool: the DataFrame rows are i2_common.bar_rows (symbol X, date = the bar's end); actions are issued in
fn of the row chosen by i2_common.issue_schedule; fractional shares are the tool's option (needed for the scenes'
sizes).  Fee: ORDER_PERCENT with fee_amount = i2_common.single_fee_rate x 100.  Leverage: the account's.  A filled
row of `orders` is matched to our order by (created = the row the order was issued in, side).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import pybroker as pb  # noqa: E402  (the tool, in its venv)

pb.disable_logging()
pb.disable_progress_bar()
pb.disable_caches()
TOOL = "PyBroker 2.0.1"
EPOCH = pd.Timestamp("1970-01-01")


class Adapter:
    name = "opp_lib_pybroker"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "cancel"), events=("book", "trade", "bar"),
               fill_models=C.bar_fill_models, costs=("maker_rate", "taker_rate"), account=("cash", "leverage"))
        rate = C.single_fee_rate(inp, TOOL)
        rows, _src = C.bar_rows(inp)
        if not rows:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い")
        dates = [EPOCH + pd.Timedelta(int(b["t"]), "ns") for b in rows]
        df = pd.DataFrame({"symbol": "X", "date": dates, **{k: [float(b[x]) for b in rows] for k, x in
                                                            (("open", "o"), ("high", "h"), ("low", "l"), ("close", "c"))},
                           "volume": [float(b["v"]) for b in rows]})
        sched = C.issue_schedule(rows, inp["actions"])
        for k, acts in sched.items():
            for side in ("buy", "sell"):
                if sum(1 for a in acts if a["op"] == "place" and a["side"] == side) > 1:
                    raise NotExpressible(f"{TOOL}: 1 本の足で同じ向きの注文は 1 つだけ(ctx.buy_shares / sell_shares は 1 つの値)")
        st = {"k": -1, "created": {}, "pending_map": {}, "rej": {}}

        def fn(ctx):
            st["k"] += 1
            for a in sched.get(st["k"], []):
                if a["op"] == "cancel":
                    created = st["created"].get(a["ref"])
                    for o in ctx.pending_orders():
                        if created is not None and pd.Timestamp(o.created) == created[0] and o.type == created[1]:
                            ctx.cancel_pending_order(o.id)
                    continue
                try:
                    if a["side"] == "buy":
                        ctx.buy_shares = float(a["qty"])
                        if a["type"] == "limit":
                            ctx.buy_limit_price = float(a["px"])
                    else:
                        ctx.sell_shares = float(a["qty"])
                        if a["type"] == "limit":
                            ctx.sell_limit_price = float(a["px"])
                except Exception as exc:  # the tool refused this order
                    st["rej"][a["ref"]] = f"{type(exc).__name__}: {exc}"
                    continue
                st["created"][a["ref"]] = (pd.Timestamp(ctx.dt), a["side"])

        try:
            cfg = pb.StrategyConfig(initial_cash=float(inp["account"]["cash"]), enable_fractional_shares=True,
                                    fee_mode=pb.FeeMode.ORDER_PERCENT if rate else None, fee_amount=float(rate) * 100,
                                    leverage=float(inp["account"].get("leverage", 1.0)))
            s = pb.Strategy(df, dates[0], dates[-1] + pd.Timedelta(days=1), cfg)
            s.add_execution(fn, ["X"])
            res = s.backtest(warmup=None)
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}"[:400])
        rec = {"orders": {}, "fills": []}
        table = res.orders.to_dict("records") if res.orders is not None else []
        for ref, (created, side) in st["created"].items():
            mine = [r for r in table if pd.Timestamp(r["created"]) == created and r["type"] == side]
            for r in mine:
                rec["fills"].append({"ref": ref, "t": int((pd.Timestamp(r["date"]) - EPOCH).value), "px": float(r["fill_price"]),
                                     "qty": float(r["shares"]), "fee": float(r["fees"]), "liq": None})
            filled = sum(float(r["shares"]) for r in mine)
            want = float(next(a["qty"] for a in C.places(inp) if a["ref"] == ref))
            rec["orders"][ref] = {"status": "filled" if filled >= want - 1e-12 else "open" if filled == 0 else "canceled"}
        for ref, err in st["rej"].items():
            rec["orders"][ref] = {"status": "rejected", "error": err[:200]}
        return rec


TARGET = Adapter()
