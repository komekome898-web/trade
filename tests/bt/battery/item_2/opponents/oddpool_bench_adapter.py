"""Survey candidate 90 `Oddpool/PredictionMarketBench` (git clone src/c90, package oddpool_bench, pure Python; venv
item_2/c90 with a .pth, install record venvs/item_2/logs/c90.log) for the item 2 battery.

The tool's own parts used: `ExecutionEngine(fee_model, execution_mode="maker_taker").execute_order(order, orderbook, ts)`
(taker fills against the snapshot's levels; POST_ONLY that would cross is rejected; IOC does not rest) and
`MakerQueueManager` (`place_order` = a resting order behind the snapshot's display at its level plus the agent's own
orders there, `process_trade` = a trade print consumes the queue at the trade's price: display ahead first, then the
agent's orders FIFO, `cancel_order`, and `update_env_from_snapshot(snapshot, mode)` with mode "trade_only" (display
decreases never move us up = the scene's cancel stance none; the tool's default, SimulatorConfig.maker_queue_mode) or
"reconciled" (the queue ahead is lowered to the level's new display when that is smaller = snapshot_cap)).  The order of
calls is the tool's `Simulator._place_order` / `_process_trade_print` (simulator.py 231-273, 308-325): execute, then a
GTC / POST_ONLY limit remainder that would not cross is placed in the maker queue.
The tool's contracts are binary (YES / NO, prices in cents, integer counts): the scene's instrument is the YES
contract, a buy is BUY YES at the price and a sell is SELL YES (the tool's canonical form: a NO bid at 100 - price), the
book's bids are YES bids and its asks are NO bids at 100 - price (so the tool's derived YES asks are the scene's asks),
a trade print with aggressor buy is a taker buying YES, with aggressor sell a taker buying NO at 100 - price; prices go
in as integer ticks and counts as integer lots (the arithmetic is the tool's, which has no range check).  Its fee
model is Kalshi's price-curve schedule in cents, which has no meaning for the scene's prices, so fees are not reported
and scenes with non-zero costs are refused.  No market-order sizing beyond the snapshot, no stop, no amend, no latency.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
import lob_common as L  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

from oddpool_bench.execution import ExecutionEngine  # noqa: E402  (the tool)
from oddpool_bench.maker_queue import MakerQueueManager  # noqa: E402
from oddpool_bench.types import (Action, Order, OrderbookLevel, OrderbookSnapshot, OrderType, Side,  # noqa: E402
                                 TimeInForce)

TOOL = "PredictionMarketBench(611d669) oddpool_bench"
TK = "X"


def _fm(fm):
    if "range" in fm or "impact" in fm:
        return "市場影響の関数・楽観と悲観の両方を回す口が無い"
    if fm.get("tier") != 5:
        return f"段 {fm.get('tier')} を選ぶ口が無い(埋まり方は自分の列の位置を追う型 = 段 5 だけ)"
    if fm.get("cancel_stance") not in ("none", "snapshot_cap"):
        return (f"先行の取消の扱い {fm.get('cancel_stance')} の口が無い(maker_queue_mode は trade_only = 見ない と "
                "reconciled = 写真の量で先行を下げる の 2 つ)")
    return None


def _ts(t):
    return D.datetime.fromtimestamp(t // 10**9, tz=D.timezone.utc) + D.timedelta(microseconds=(t % 10**9) // 1000)


class Adapter:
    name = "opp_oddpool_bench"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "IOC", "post_only", "cancel"), events=("book", "trade"),
               fill_models=_fm, costs=(), account=("cash",))
        fm = inp.get("fill_model") or {}
        mode = "reconciled" if fm.get("cancel_stance") == "snapshot_cap" else "trade_only"
        tick, step = inp["product"]["tick"], L.qty_unit(inp)
        L.INT_ONLY[0] = True
        tk = lambda p: L.ticks(p, tick)  # noqa: E731
        lt = lambda q: L.lots(q, step)  # noqa: E731
        fees = _NoFee()
        eng = ExecutionEngine(fee_model=fees, execution_mode="maker_taker")
        mq = MakerQueueManager(fees)
        rec = {"orders": {}, "fills": []}
        resting = {}
        seq = [0]

        def snap(e, t):
            seq[0] += 1
            try:
                return OrderbookSnapshot(ts=_ts(t), sequence_id=seq[0], ticker=TK,
                                         yes_bids=[OrderbookLevel(tk(p), lt(q)) for p, q in sorted(e["bids"], reverse=True)],
                                         no_bids=[OrderbookLevel(100 - tk(p), lt(q)) for p, q in sorted(e["asks"])])
            except L._OffGrid as exc:
                raise NotExpressible(f"{TOOL}: 値 {exc} が整数の刻みに乗らない")

        def add_fill(ref, f, liq, t):
            px = (f.price_cents if liq == "taker" or ref_side[ref] == "buy" else 100 - f.price_cents)
            rec["fills"].append({"ref": ref, "t": int(t), "px": px * tick, "qty": f.size * step, "liq": liq})

        ref_side = {}
        try:
            self._loop(inp, tk, lt, snap, add_fill, ref_side, eng, mq, mode, rec, resting, step, tick)
        except L._OffGrid as exc:
            raise NotExpressible(f"{TOOL}: 値 {exc} が整数の刻みに乗らない")
        for x in C.places(inp):
            ref = x["ref"]
            if ref in rec["orders"]:
                continue
            got = sum(f["qty"] for f in rec["fills"] if f["ref"] == ref)
            active = mq.get_order(ref) is not None and mq.get_order(ref).remaining_count > 0
            rec["orders"][ref] = {"status": C.status_from(got, x["qty"], active=active)}
        return rec

    @staticmethod
    def _loop(inp, tk, lt, snap, add_fill, ref_side, eng, mq, mode, rec, resting, step, tick):
        book = None
        for t, kind, x in C.timeline(inp):
            if kind == "m":
                if x["type"] == "book":
                    book = snap(x, t)
                    mq.update_env_from_snapshot(book, mode=mode)
                elif x["type"] == "trade":
                    p = tk(x["px"])
                    side, price = (Side.YES, p) if x["aggressor"] == "buy" else (Side.NO, 100 - p)
                    for r, f in mq.process_trade(ticker=TK, taker_side=side, trade_price_cents=price, volume=lt(x["qty"]),
                                                 ts=_ts(t)):
                        add_fill(r.order_id, f, "maker", t)
                continue
            if x["op"] == "cancel":
                if mq.cancel_order(x["ref"]) is not None:
                    rec["orders"][x["ref"]] = {"status": "canceled"}
                continue
            if x["op"] != "place":
                raise NotExpressible(f"{TOOL}: 操作 {x['op']} の口が無い")
            if book is None:
                raise NotExpressible(f"{TOOL}: 板の写真より前の注文を出す口が無い")
            ref_side[x["ref"]] = x["side"]
            tif = (TimeInForce.POST_ONLY if x["post_only"] else TimeInForce.IOC if x["tif"] == "IOC" or x["type"] == "market"
                   else TimeInForce.GTC)
            o = Order(ticker=TK, side=Side.YES, action=Action.BUY if x["side"] == "buy" else Action.SELL,
                      order_type=OrderType.MARKET if x["type"] == "market" else OrderType.LIMIT, count=lt(x["qty"]),
                      limit_price_cents=None if x["px"] is None else tk(x["px"]), time_in_force=tif, order_id=x["ref"])
            res = eng.execute_order(o, book, _ts(t))
            if res.rejected:
                rec["orders"][x["ref"]] = {"status": "rejected", "error": str(res.reject_reason)}
                continue
            for f in res.fills:
                rec["fills"].append({"ref": x["ref"], "t": int(t), "px": f.price_cents * tick, "qty": f.size * step,
                                     "liq": "taker"})
            rem = o.count - res.filled_count
            if rem > 0 and tif in (TimeInForce.GTC, TimeInForce.POST_ONLY) and o.order_type == OrderType.LIMIT:
                crosses = (book.yes_best_ask is not None and o.limit_price_cents >= book.yes_best_ask) if x["side"] == "buy" \
                    else (book.yes_best_bid is not None and o.limit_price_cents <= book.yes_best_bid)
                if not crosses:
                    r = mq.place_order(o, book, _ts(t))
                    r.remaining_count = rem
                    resting[x["ref"]] = r


class _NoFee:
    """Fees are not reported (see the module doc); the tool's engine asks a fee model for every fill."""

    def calculate_taker_fee(self, price_cents, count):
        return 0

    def calculate_maker_fee(self, price_cents, count):
        return 0


TARGET = Adapter()
