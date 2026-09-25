"""Survey candidate 1 `Basana` (PyPI basana 1.11, venv item_0/basana; install record: item 0
survey_results/attempts/1.log) for the item 2 battery.

The tool's own calls used: `basana.backtesting_dispatcher()`, the backtesting `Exchange(dispatcher,
initial_balances, liquidity_strategy_factory, fee_strategy, default_pair_info)`, `create_market_order /
create_limit_order / create_stop_order / cancel_order / get_order_info`, `add_bar_source(FifoQueueEventSource)`,
`subscribe_to_bar_events`, `subscribe_to_order_events`; `liquidity.InfiniteLiquidity`, `liquidity.
VolumeShareImpact(volume_limit_pct, price_impact)`, `fees.Percentage(percentage)`.  The exchange fills orders
against bars (`basana.core.bar.BarEvent`); it has no book, IOC, FOK, post-only, amend, OCO, reduce-only,
latency, notice latency, funding, swap or liquidation.

Scene -> tool: bars from i2_common.bar_rows (one bar per trade print, or the scene's own bars); a scene bar's event
`when` is its end and `begin` = end - span; a print's bar begins at the print and lasts 1 microsecond (Basana's
datetime resolution), its event `when` = begin + 1 microsecond.  Product: PairInfo in TICK_SIZE mode with the
product's tick and qty_step.  Actions are issued in the bar handler of the last bar at or before their
time (i2_common.issue_schedule; actions before the first bar in the first bar's handler).  Fill model: none ->
InfiniteLiquidity (no volume limit; Basana's default VolumeShareImpact(25, 10) is a volume / impact model the
scene does not ask for), tier 4 -> VolumeShareImpact(volume_limit_pct=100, price_impact=0) (fills up to the bar's
volume), other tiers / impact / range -> refused.  Fee: Percentage(rate x 100) with i2_common.single_fee_rate.
Account: initial JPY balance = cash; leverage != 1 or liquidation -> refused.
Fills are the order's own `fills` (when, balance updates, fees, price); status from get_order_info.
"""
from __future__ import annotations

import asyncio
import datetime as D
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
import lob_common as LC  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import basana as bs  # noqa: E402
from basana.backtesting import exchange as bex, fees as bfees, liquidity as bliq  # noqa: E402
from basana.core.bar import BarEvent  # noqa: E402

TOOL = "Basana 1.11"
EPOCH = D.datetime(1970, 1, 1, tzinfo=D.timezone.utc)


def _dt(ns):
    return EPOCH + D.timedelta(microseconds=ns // 1000)


def _ns(dt):
    d = dt - EPOCH
    return (d.days * 86400 + d.seconds) * 10**9 + d.microseconds * 1000


def _places(x) -> int:
    f = Fraction(str(x))
    k = 0
    while f.denominator != 1:
        f *= 10
        k += 1
    return k


def _fm(fm):
    if fm.get("tier") == 4 and not fm.get("impact") and "range" not in fm:
        return None
    return "約定の模型は流動性の戦略(無限 / 足の出来高の割合と価格の影響)だけで、段 4 以外の段・列・市場影響の関数・楽観と悲観の両方を回す口が無い"


class Adapter:
    name = "opp_basana"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "cancel"), events=("book", "trade", "bar"),
               fill_models=_fm, costs=("maker_rate", "taker_rate"), account=("cash",))
        rate = C.single_fee_rate(inp, TOOL)
        bars, _src = C.bar_rows(inp)
        if not bars:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(取引所は足で約定を決め、板の写真を受けない)")
        prod = inp["product"]
        base = prod["symbol"].split("_")[0][:6] or "BASE"
        pair = bs.Pair("BASE", "JPY") if prod.get("quote_ccy", "JPY") == "JPY" else bs.Pair("BASE", prod["quote_ccy"])
        unit = LC.qty_unit(inp)
        # the product's own tick and size step in the tool's tick-size mode (PairInfo docs: "The tick size for the
        # quote symbol, if precision_mode is TICK_SIZE"); the precisions are the digits those steps need
        pinfo = bs.PairInfo(base_precision=_places(prod["qty_step"]), quote_precision=_places(prod["tick"]),
                            precision_mode=bs.PrecisionMode.TICK_SIZE,
                            base_tick_size=Decimal(str(prod["qty_step"])), quote_tick_size=Decimal(str(prod["tick"])))
        fm = inp.get("fill_model") or {}
        liq = (lambda: bliq.VolumeShareImpact(volume_limit_pct=Decimal(100), price_impact=Decimal(0))) \
            if fm.get("tier") == 4 else bliq.InfiniteLiquidity
        try:
            fee = bfees.Percentage(percentage=Decimal(str(rate * 100))) if rate else bfees.NoFee()
        except Exception as exc:  # the tool refuses the rate (e.g. a negative percentage = a rebate)
            raise Refused(f"fees.Percentage({rate * 100}) -> {type(exc).__name__}: {exc}")
        disp = bs.backtesting_dispatcher()
        ex = bex.Exchange(disp, {pair.quote_symbol: Decimal(str(inp["account"]["cash"]))}, liquidity_strategy_factory=liq,
                          fee_strategy=fee, default_pair_info=pinfo)
        evs = []
        for b in bars:
            if b["span_ns"]:  # the scene's own bar: known at its end
                dur = D.timedelta(microseconds=b["span_ns"] // 1000)
                begin, when = _dt(b["t"]) - dur, _dt(b["t"])
            else:  # a print: the bar begins at the print and lasts Basana's smallest step (1 microsecond)
                dur = D.timedelta(microseconds=1)
                begin, when = _dt(b["t"]), _dt(b["t"]) + dur
            evs.append(BarEvent(when, bs.Bar(begin, pair, *(Decimal(str(b[k])) for k in ("o", "h", "l", "c", "v")), dur)))
        ex.add_bar_source(bs.FifoQueueEventSource(events=evs))
        sched = C.issue_schedule([b["t"] for b in bars], inp["actions"])
        st = {"k": -1, "ids": {}, "orders": {}}

        async def on_bar(be):
            st["k"] += 1
            for a in sched.get(st["k"], []):
                if a["op"] == "cancel":
                    oid = st["ids"].get(a["ref"])
                    if oid is not None:
                        try:
                            await ex.cancel_order(oid)
                        except Exception as exc:  # the tool refused the cancel (e.g. order already closed)
                            st.setdefault("cancel_errors", []).append(f"{type(exc).__name__}: {exc}")
                    continue
                op = bs.OrderOperation.BUY if a["side"] == "buy" else bs.OrderOperation.SELL
                amt = Decimal(str(a["qty"]))
                try:
                    if a["type"] == "market":
                        o = await ex.create_market_order(op, pair, amt)
                    elif a["type"] == "limit":
                        o = await ex.create_limit_order(op, pair, amt, Decimal(str(a["px"])))
                    else:
                        o = await ex.create_stop_order(op, pair, amt, Decimal(str(a["stop_px"])))
                except Exception as exc:  # the tool refused this order
                    st["orders"][a["ref"]] = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"[:200]}
                    continue
                st["ids"][a["ref"]] = o.id

        ex.subscribe_to_bar_events(pair, on_bar)
        try:
            asyncio.run(disp.run())
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        rec = {"orders": dict(st["orders"]), "fills": []}

        async def collect():
            for ref, oid in st["ids"].items():
                info = await ex.get_order_info(pair, oid) if _takes_pair() else await ex.get_order_info(oid)
                rec["orders"][ref] = {"status": "open" if info.is_open else
                                      ("filled" if info.amount_remaining == 0 else "canceled")}
                for f in info.fills:
                    q = abs(float(f.balance_updates.get(pair.base_symbol, Decimal(0))))
                    fee = -float(sum(v for v in f.fees.values())) if f.fees else 0.0
                    rec["fills"].append({"ref": ref, "t": _ns(f.when), "px": float(f.price), "qty": q, "fee": fee, "liq": None})
        asyncio.run(collect())
        return rec


def _takes_pair():
    import inspect
    return "pair" in inspect.signature(bex.Exchange.get_order_info).parameters


TARGET = Adapter()
