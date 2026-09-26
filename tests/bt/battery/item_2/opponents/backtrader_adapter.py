"""Survey candidate 2 `Backtrader` (PyPI 1.9.78.123, venv item_0/backtrader) for the item 2 battery.

Public API used: `Cerebro`, `feeds.PandasData`, `Strategy` (`next`,
`notify_order`, `notify_trade`, `buy`, `sell`, `cancel`, `position`),
`broker.setcash`, `broker.setcommission(commission, leverage)`,
`Order.Market / Limit / Stop`, the `oco=` argument.

Scene -> tool: Backtrader takes bars, not a book.  The bars are i2_common.bar_rows (one bar per trade print,
the scene's own bars, or the prints grouped into a tier-2 scene's declared bars); book snapshots have no feed
type in Backtrader and are not given.  Actions are issued in `next()` of the bar chosen by
i2_common.issue_schedule (Backtrader then executes them on the following bars by its own rules).  A fill's time
is the end time of the bar Backtrader executed it on.  Fill model: none / tier 2 -> the broker's default; tier 4
-> the tool's `broker.fillers.FixedBarPerc(perc=100)` (fills up to the bar's volume).  One commission rate
(`setcommission(commission=)`, i2_common.single_fee_rate); a spread cost -> the tool's
`set_slippage_fixed(spread / 2)`.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

import backtrader as bt  # noqa: E402

TOOL = "Backtrader 1.9.78.123"


def _dt(ns: int) -> D.datetime:
    return D.datetime(1970, 1, 1) + D.timedelta(microseconds=ns // 1000)


class BacktraderAdapter:
    name = "opp_backtrader"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "oco", "cancel"), events=("book", "trade", "bar"),
               fill_models=lambda fm: C.bar_fill_models(fm, extra=lambda f: None if f.get("tier") == 4 and "range" not in f
                                                        and not f.get("impact") else C.bar_fill_models({})),
               costs=("maker_rate", "taker_rate", "spread"), account=("cash", "leverage"))
        c = inp["costs"]
        rate = C.single_fee_rate(inp, TOOL)
        tr, _src = C.bar_rows(inp)
        if not tr:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い(Backtrader は足の feed だけを取る)")
        bar_t = [b["t"] for b in tr]
        df = pd.DataFrame({"open": [b["o"] for b in tr], "high": [b["h"] for b in tr], "low": [b["l"] for b in tr],
                           "close": [b["c"] for b in tr], "volume": [b["v"] for b in tr], "openinterest": 0.0},
                          index=pd.DatetimeIndex([_dt(t) for t in bar_t]))
        sched = C.issue_schedule(tr, inp["actions"])
        fm = inp.get("fill_model") or {}
        rec = {"orders": {}, "fills": [], "o": {}, "realized": 0.0}

        class S(bt.Strategy):
            def next(self):
                for a in sched.get(len(self.data) - 1, []):
                    self._act(a)

            def _act(self, a):
                if a["op"] == "cancel":
                    o = rec["o"].get(a["ref"])
                    if o is not None:
                        self.cancel(o)
                    return
                kw = {"size": a["qty"]}
                if a["type"] == "market":
                    kw["exectype"] = bt.Order.Market
                elif a["type"] == "limit":
                    kw.update(exectype=bt.Order.Limit, price=a["px"])
                else:
                    kw.update(exectype=bt.Order.Stop, price=a["stop_px"])
                if a["oco"] and a["oco"] in rec["o"]:
                    kw["oco"] = rec["o"][a["oco"]]
                try:
                    o = (self.buy if a["side"] == "buy" else self.sell)(**kw)
                except Exception as exc:
                    rec["orders"][a["ref"]] = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"[:200]}
                    return
                o.addinfo(ref=a["ref"])
                rec["o"][a["ref"]] = o
                rec["orders"][a["ref"]] = {"status": "open"}

            def notify_order(self, o):
                ref = o.info.get("ref")
                if ref is None:
                    return
                if o.status in (o.Completed, o.Partial) and o.executed.size:
                    k = len(self.data) - 1
                    done = sum(f["qty"] for f in rec["fills"] if f["ref"] == ref)
                    q = abs(o.executed.size) - done
                    if q > 1e-12:
                        comm = o.executed.comm - sum(f["fee"] for f in rec["fills"] if f["ref"] == ref)
                        rec["fills"].append({"ref": ref, "t": bar_t[k], "px": float(o.executed.price), "qty": q,
                                             "fee": float(comm), "liq": None})
                st = {o.Completed: "filled", o.Partial: "open", o.Canceled: "canceled", o.Expired: "canceled",
                      o.Margin: "rejected", o.Rejected: "rejected", o.Accepted: "open", o.Submitted: "open"}.get(o.status)
                if st:
                    rec["orders"][ref] = {"status": st}

            def notify_trade(self, trade):
                rec.setdefault("trades", {})[id(trade)] = trade

        try:
            cer = bt.Cerebro(stdstats=False)
            cer.adddata(bt.feeds.PandasData(dataname=df))
            cer.broker.setcash(float(inp["account"]["cash"]))
            cer.broker.setcommission(commission=float(rate), leverage=float(inp["account"].get("leverage", 1.0)))
            if fm.get("tier") == 4:
                cer.broker.set_filler(bt.broker.fillers.FixedBarPerc(perc=100.0))
            if c.get("spread"):  # half the spread as a fixed slippage on market orders (Backtrader has no spread argument)
                cer.broker.set_slippage_fixed(float(c["spread"]) / 2, slip_open=True, slip_limit=False, slip_match=True)
            cer.addstrategy(S)
            strat = cer.run()[0]
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}")
        realized = sum(t.pnl for t in rec.get("trades", {}).values())
        return {"orders": rec["orders"], "fills": rec["fills"],
                "account": {"position": float(strat.position.size), "realized": float(realized)}}


TARGET = BacktraderAdapter()
