"""Survey candidate 91 `braedonsaunders/homerun` (commit 6cb8ea56), its backtester package `backend/services/backtest`
(venv item_2/c91 with a .pth to the clone's backend/; install record venvs/item_2/logs/i2_r1_scenekeeper_install_91.log)
for the item 2 battery.

The tool's own parts used: `MatchingEngine(venue, latency, fees, impact)` with `submit(BacktestOrder)`,
`cancel(order_id, requested_at)`, `advance_to(BookSnapshot)` and the orders' own records (`state`, `fills`: price,
size, fee_usd, occurred_at, notes maker); `BookSnapshot` (an L2 book at observed_at, which also carries a trade:
trade_price / trade_size / trade_side); `PolymarketVenue` with its `rules` set to the scene's product (an
`OrderRule`: tick = the product's tick, no minimum notional, price range tick .. 1e18, TIFs GTC / IOC / FOK,
post-only); `LatencyModel(submit, cancel)` of `LatencyProfile`s with sigma ~ 0 (the tool's constant form, as its
`deterministic()`; minimum 0 so a zero latency stays zero); `FeeModel(taker_bps, maker_bps / maker_rebate_bps,
per_fill_gas_usd=0, use_taker_fee_curve=False)`.

The run follows the tool's own `BacktestEngine.run` loop: for each market event in time order, our actions with time
<= the event's time are submitted (cancels requested), then the engine advances to the event's snapshot; one last
snapshot of the latest book at the scene's end_t closes the run.  A book
event is the snapshot; a trade print is a snapshot of the latest scene book carrying the print in its trade fields
(the tool's matcher reads only the book: it matches newly arrived orders against the snapshot's levels, and a resting
order fills when the other side of a later snapshot reaches its price once its queue estimate -- 0.65 x the
same-price display plus better-priced display at entry, reduced by later display decreases -- is used up).
What the tool has no call for is refused: market / stop / reduce-only / OCO orders (its orders are limit orders),
amend, feed and notice latency, a latency drawn from samples (it fits a log-normal), fill tiers other than its own
queue model, impact kinds other than its own square-root-of-share-of-visible-depth, and accounts.
"""
from __future__ import annotations

import datetime as D
import logging
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible  # noqa: E402

from services.backtest.book_replay import BookSnapshot, PriceLevel  # noqa: E402  (the tool)
from services.backtest.latency_model import LatencyModel, LatencyProfile  # noqa: E402
from services.backtest.matching_engine import BacktestOrder, FeeModel, MatchingEngine, OrderState  # noqa: E402
from services.backtest.venue_model import OrderRule, PolymarketVenue  # noqa: E402

logging.disable(logging.CRITICAL)
TOOL = "homerun(6cb8ea56) services.backtest"
TOK = "X"


def _fm(fm):
    if "range" in fm:
        return "楽観と悲観の両方を回す口が無い"
    if "impact" in fm:
        return (f"市場影響 {fm['impact'].get('kind')} を渡す口が無い(この道具の影響は 強さ x sqrt(自分の量 / 見えている板の量) の"
                "一時的な滑りだけ)")
    if fm.get("tier") != 5:
        return f"段 {fm.get('tier')} を選ぶ口が無い(この道具の埋まり方は自分の列の推定 1 つだけ)"
    if fm.get("cancel_stance") != "snapshot_cap":
        return (f"先行の取消の扱い {fm.get('cancel_stance')} を選ぶ口が無い(この道具の列は、表示の減りをすべて先行の消化に数える 1 つだけ)")
    return None


def _ts(t):
    return D.datetime.fromtimestamp(t // 10**9, tz=D.timezone.utc) + D.timedelta(microseconds=(t % 10**9) / 1000)


def _const(ns):
    ms = float(ns) / 1e6
    return LatencyProfile(mu_ms=math.log(ms) if ms > 0 else float("-inf"), sigma_ms=1e-12, minimum_ms=0.0)


class Adapter:
    name = "opp_homerun"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("limit", "IOC", "FOK", "post_only", "cancel"), events=("book", "trade"),
               fill_models=_fm, latency=("order", "cancel"), costs=("maker_rate", "taker_rate"), account=("cash",))
        prod = inp["product"]
        lat = inp.get("latency") or {}
        latency = LatencyModel(submit=_const((lat.get("order") or {}).get("ns", 0)),
                               cancel=_const((lat.get("cancel") or {}).get("ns", 0)))
        c = inp.get("costs") or {}
        mk, tk = float(c.get("maker_rate", 0.0)), float(c.get("taker_rate", 0.0))
        fees = FeeModel(taker_bps=tk * 1e4, maker_bps=max(mk, 0.0) * 1e4, maker_rebate_bps=max(-mk, 0.0) * 1e4,
                        maker_rebate_max_spread_bps=1e18, per_fill_gas_usd=0.0, negrisk_conversion_gas_usd=0.0,
                        use_taker_fee_curve=False)
        venue = PolymarketVenue()
        venue.rules = OrderRule(tick_size=float(prod["tick"]), min_notional_usd=0.0, max_price=1e18,
                                min_price=float(prod["tick"]), valid_tifs=frozenset({"GTC", "IOC", "FOK"}),
                                supports_post_only=True, supports_partial_fills=True, fok_atomicity=True)
        me = MatchingEngine(venue=venue, latency=latency, fees=fees)
        acts = sorted(inp["actions"], key=lambda a: a["t"])
        k = 0
        book = {"bids": [], "asks": []}
        seq = 0
        for e in sorted(inp["market"], key=lambda e: e["t"]):  # stable: same-time events keep list order
            t = e["t"]
            while k < len(acts) and acts[k]["t"] <= t:
                self._act(me, acts[k])
                k += 1
            if e["type"] == "book":
                book = {"bids": e["bids"], "asks": e["asks"]}
                extra = {}
            else:
                extra = {"trade_price": float(e["px"]), "trade_size": float(e["qty"]), "trade_side": e["aggressor"].upper()}
            seq += 1
            snap = BookSnapshot(token_id=TOK, observed_at=_ts(t),
                                bids=tuple(PriceLevel(float(p), float(q)) for p, q in book["bids"]),
                                asks=tuple(PriceLevel(float(p), float(q)) for p, q in book["asks"]), sequence=seq, **extra)
            me.advance_to(snap)
        # the scene's book stays as it is until end_t: one more snapshot of it at end_t (no trade) lets the loop admit
        # what was sent after the last market event (the same no-op row the hftbacktest adapter adds)
        end_t = inp.get("end_t") or max([e["t"] for e in inp["market"]] + [a["t"] for a in acts])
        while k < len(acts) and acts[k]["t"] <= end_t:
            self._act(me, acts[k])
            k += 1
        me.advance_to(BookSnapshot(token_id=TOK, observed_at=_ts(end_t), sequence=seq + 1,
                                   bids=tuple(PriceLevel(float(p), float(q)) for p, q in book["bids"]),
                                   asks=tuple(PriceLevel(float(p), float(q)) for p, q in book["asks"])))
        rec = {"orders": {}, "fills": []}
        for a in C.places(inp):
            o = me.order(a["ref"])
            for f in o.fills:
                ot = f.occurred_at
                t_ns = int(ot.timestamp()) * 10**9 + ot.microsecond * 1000
                rec["fills"].append({"ref": a["ref"], "t": t_ns, "px": float(f.price), "qty": float(f.size),
                                     "fee": float(f.fee_usd), "liq": "maker" if f.notes.get("maker") else "taker"})
            st = {OrderState.FILLED: "filled", OrderState.CANCELLED: "canceled", OrderState.REJECTED: "rejected"}.get(o.state, "open")
            rec["orders"][a["ref"]] = {"status": st} if st != "rejected" else {"status": st, "error": str(o.reject_reason)}
        return rec

    def _act(self, me, a):
        if a["op"] == "place":
            tif = "IOC" if a["tif"] == "IOC" else "FOK" if a["tif"] == "FOK" else "GTC"
            me.submit(BacktestOrder(order_id=a["ref"], token_id=TOK, side=a["side"].upper(), price=float(a["px"]),
                                    size=float(a["qty"]), tif=tif, post_only=bool(a["post_only"]), submitted_at=_ts(a["t"])))
        elif a["op"] == "cancel":
            me.cancel(order_id=a["ref"], requested_at=_ts(a["t"]))
        else:
            raise NotExpressible(f"{TOOL}: 操作 {a['op']} の口が無い")


TARGET = Adapter()
