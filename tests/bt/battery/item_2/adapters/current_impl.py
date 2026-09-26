"""当方の現状 (the current state) for the item 2 battery.

What the current state has for order execution (read 2026-09-25):
- `bot.execution.paper.PaperExecutor` -- the only order-level simulator in the
  repository: `submit_order(symbol, side, size, order_type, price)` fills a
  MARKET order at once at best ask / best bid (+ slippage_pct) from a quote
  callback, fills a LIMIT order at once at its limit when marketable and
  otherwise leaves it ACTIVE (it has no later fill path), `cancel_order`,
  margin mode (`allow_short=True`) with a `balance * leverage` notional cap that
  raises, one `taker_fee_pct` charged on every fill.
- `bot.backtest.engine.run_backtest` -- a bar backtest driven by a strategy's
  BUY/SELL/CLOSE signals (size = order_notional_jpy / price, limit = the decision
  bar's close); it has no parameter for an order's price, quantity, type or time,
  so no scene of this battery can be handed to it.
- `bot.research.board.walk_book` and `scripts/qa/maker_fill_ref.simulate` are
  research helpers that no execution path calls (`paper.py` fills at the best
  quote; `engine.py` never imports either); `simulate` quotes by its own
  strategy (S1/S2) and takes no order.

So this adapter drives PaperExecutor over the scene's events, exactly through
its public methods.  Whatever PaperExecutor has no argument for (time in force,
post-only, stop, reduce-only, OCO, latency, maker fee, funding, swap, rules of
a venue, liquidation, ...) is NotExpressible with the argument that is missing.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from i2_protocol import NotExpressible, need  # noqa: E402

from bot.execution.paper import PaperExecutor  # noqa: E402


def _check_expressible(inp: dict) -> None:
    need(inp.get("fill_model") in (None, {}), "PaperExecutor に約定の模型を選ぶ引数が無い(submit_order の引数は symbol・side・size・order_type・price)")
    lat = inp.get("latency")
    need(not lat or all(v.get("kind") == "constant" and v.get("ns", 0) == 0 for v in lat.values()),
         "PaperExecutor に遅延の引数が無い")
    need(not inp.get("inject"), "PaperExecutor に拒否・時間切れ・状態不明を注入する口が無い")
    c = inp.get("costs") or {}
    need(not any(k in c for k in ("funding", "swap", "fee_table")), "PaperExecutor の費用は taker_fee_pct と slippage_pct だけ")
    need(c.get("maker_rate", 0.0) == 0.0 or not any(a.get("type") == "limit" for a in inp["actions"] if a.get("op") == "place"),
         "PaperExecutor に maker の手数料の引数が無い(taker_fee_pct が全約定に掛かる)")
    acc = inp.get("account") or {}
    need("maint_ratio" not in acc, "PaperExecutor に強制決済が無い")
    need(inp["product"].get("quote_ccy", "JPY") == "JPY", "PaperExecutor は残高を円の 1 本で持ち、為替の換算が無い")
    for e in inp["market"]:
        need(e["type"] in ("book", "trade", "label"), f"PaperExecutor に事象 {e['type']} を渡す口が無い")
    for a in inp["actions"]:
        if a["op"] == "amend":
            raise NotExpressible("PaperExecutor に訂正のメソッドが無い(submit_order・cancel_order・fetch_order_status だけ)")
        if a["op"] == "kill":
            raise NotExpressible("PaperExecutor に Kill Switch の口が無い")
        if a["op"] == "place":
            need(a["type"] in ("market", "limit"), f"PaperExecutor の order_type に {a['type']} が無い(MARKET と LIMIT だけ)")
            need(a["tif"] == "GTC", f"PaperExecutor に time in force({a['tif']})の引数が無い")
            need(not a["post_only"], "PaperExecutor に post-only の引数が無い")
            need(not a["reduce_only"], "PaperExecutor に reduce-only の引数が無い")
            need(not a["oco"], "PaperExecutor に OCO の引数が無い")


class CurrentImpl:
    name = "current_impl"

    def run(self, inp: dict) -> dict:
        _check_expressible(inp)
        c = inp["costs"]
        acc = inp["account"]
        state = {"bid": None, "ask": None}

        def quote(_symbol):
            return state["bid"], state["ask"]

        px = PaperExecutor(quote_fn=quote, balance_jpy=float(acc["cash"]),
                           taker_fee_pct=float(c.get("taker_rate", 0.0)) * 100.0,
                           slippage_pct=0.0, allow_short=True, leverage=float(acc.get("leverage", 1.0)))
        start_balance = px.balance_jpy
        timeline = [(e["t"], 0, i, "m", e) for i, e in enumerate(inp["market"])]
        timeline += [(a["t"], 1, i, "a", a) for i, a in enumerate(inp["actions"])]
        timeline.sort(key=lambda x: (x[0], x[1], x[2]))
        orders, fills, seen, ids = {}, [], {}, {}
        sym = inp["product"]["symbol"]
        for t, _, _, kind, x in timeline:
            if kind == "m":
                if x["type"] == "book":
                    state["bid"] = x["bids"][0][0] if x["bids"] else None
                    state["ask"] = x["asks"][0][0] if x["asks"] else None
                elif x["type"] == "trade" and state["bid"] is None:
                    state["bid"] = state["ask"] = x["px"]
                if x.get("label"):
                    seen[x["label"]] = t
                continue
            if x["op"] == "cancel":
                if x["ref"] in ids:
                    px.cancel_order(symbol=sym, acceptance_id=ids[x["ref"]])
                continue
            n_before = len(px.fills)
            try:
                res = px.submit_order(symbol=sym, side=x["side"].upper(), size=x["qty"],
                                      order_type=x["type"].upper(), price=x["px"])
            except Exception as exc:  # PaperExecutor refused this order (margin / balance)
                orders[x["ref"]] = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"[:200]}
                continue
            ids[x["ref"]] = res.acceptance_id
            for f in px.fills[n_before:]:
                fills.append({"ref": x["ref"], "t": t, "px": f.price, "qty": f.size, "fee": f.fee_jpy, "liq": "taker"})
        for ref, aid in ids.items():
            st = px.fetch_order_status(symbol=sym, acceptance_id=aid)
            orders[ref] = {"status": {"COMPLETED": "filled", "ACTIVE": "open", "CANCELED": "canceled"}.get(st.state, st.state)}
        pos = px.positions.get(sym, 0.0)
        fee_sum = sum(f["fee"] for f in fills)
        return {"orders": orders, "fills": fills, "seen": seen,
                "account": {"position": pos, "realized": px.balance_jpy - start_balance + fee_sum}}


TARGET = CurrentImpl()
