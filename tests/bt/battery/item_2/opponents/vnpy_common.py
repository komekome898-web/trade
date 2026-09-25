"""Survey candidate 20 `VnPy` (PyPI vnpy 4.4.0 + vnpy_ctastrategy 1.4.1, venv item_0/vnpy; install record: item 0
survey_results/attempts/20.log) for the item 2 battery, in the tool's two backtesting modes (two targets).

The tool's own calls used: `vnpy_ctastrategy.backtesting.BacktestingEngine.set_parameters(vt_symbol, interval,
start, end, rate, slippage, size, pricetick, capital, mode)`, `add_strategy(CtaTemplate subclass, {})`,
`history_data` (what `load_data()` fills), `run_backtesting()`, `calculate_result()`; in the strategy
`buy / sell / short / cover(price, volume, stop=False|True)` and `cancel_order(vt_orderid)`.
What the engine has (backtesting.py): limit and stop orders only (send_limit_order / send_stop_order; no market,
IOC, FOK, post-only, amend, OCO, reduce-only), an order price rounded to `pricetick` (send_order 888 `round_to`),
one commission `rate` on turnover and a per-unit `slippage`, no latency, notices only as on_order / on_trade calls.
Crossing (cross_limit_order 671-723): TICK mode -- a buy limit fills when its price >= ask_price_1 at min(price,
ask_price_1); BAR mode -- when its price >= the bar's low at min(price, the bar's open).  Stop orders
(cross_stop_order 744-798): TICK -- when last_price reaches the stop; BAR -- when the bar's high / low reaches it.

Scene -> tool:
- TICK mode: every market event is one TickData: a book snapshot sets bid/ask price_1..5 and volume_1..5 (the
  current trade's last_price kept), a trade print sets last_price (and volume) with the current book's levels.
- BAR mode: i2_common.bar_rows (one bar per trade print, the scene's own bars, or the prints grouped into the
  tier-2 scene's declared bars) as BarData; tier 2 is the mode's own model, other fill models are refused.
- Actions are issued in on_tick / on_bar of the last event at or before their time (i2_common.issue_schedule).
- A sell while the strategy holds a long position is `sell` (close), otherwise `short` (open); buys likewise
  `cover` when short.  pricetick = the product's tick; size = 1; rate = i2_common.single_fee_rate; slippage 0;
  capital = the account's cash.  Market orders have no call in the engine and are refused.
Fills are the engine's `trades` (price, volume, datetime); a fill's fee is the day's commission from
calculate_result() only when it is the day's single trade (the engine gives commission per day, not per trade).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

from vnpy.trader.constant import Exchange, Interval, Status  # noqa: E402
from vnpy.trader.object import BarData, TickData  # noqa: E402
from vnpy_ctastrategy import CtaTemplate  # noqa: E402
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode  # noqa: E402

UTC = D.timezone.utc
EPOCH = D.datetime(1970, 1, 1, tzinfo=UTC)
STATUS = {Status.ALLTRADED: "filled", Status.CANCELLED: "canceled", Status.REJECTED: "rejected",
          Status.NOTTRADED: "open", Status.PARTTRADED: "open", Status.SUBMITTING: "open"}


def _dt(ns):
    return EPOCH + D.timedelta(microseconds=ns // 1000)


def _ns(dt):
    d = dt.astimezone(UTC) - EPOCH
    return (d.days * 86400 + d.seconds) * 10**9 + d.microseconds * 1000


def _ticks(inp):
    out, book, last = [], {"bids": [], "asks": []}, 0.0
    for e in inp["market"]:
        if e["type"] == "book":
            book = e
        elif e["type"] == "trade":
            last = float(e["px"])
        else:
            continue
        kw = {"last_price": last, "volume": float(e.get("qty", 0.0))}
        for i, (p, q) in enumerate(book["bids"][:5], 1):
            kw[f"bid_price_{i}"], kw[f"bid_volume_{i}"] = float(p), float(q)
        for i, (p, q) in enumerate(book["asks"][:5], 1):
            kw[f"ask_price_{i}"], kw[f"ask_volume_{i}"] = float(p), float(q)
        out.append((e["t"], TickData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(e["t"]), gateway_name="BACKTESTING", **kw)))
    return out


def _bars(inp):
    rows, _ = C.bar_rows(inp)
    return [(b["t"], BarData(symbol="X", exchange=Exchange.LOCAL, datetime=_dt(b["t"]), interval=Interval.MINUTE,
                             volume=float(b["v"]), open_price=float(b["o"]), high_price=float(b["h"]),
                             low_price=float(b["l"]), close_price=float(b["c"]), gateway_name="BACKTESTING")) for b in rows]


def run(inp, mode_name: str, tool: str):
    C.gate(inp, tool=tool, orders=("limit", "stop", "cancel"), events=("book", "trade") + (("bar",) if mode_name == "BAR" else ()),
           fill_models=(C.bar_fill_models if mode_name == "BAR" else None), costs=("maker_rate", "taker_rate"), account=("cash",))
    rate = C.single_fee_rate(inp, tool)
    data = _ticks(inp) if mode_name == "TICK" else _bars(inp)
    if not data:
        raise NotExpressible(f"{tool}: 渡せる {('tick' if mode_name == 'TICK' else '足')} が無い")
    sched = C.issue_schedule([t for t, _ in data], inp["actions"])
    st = {"k": -1, "oid": {}, "rejected": {}}

    class S(CtaTemplate):
        def on_init(self):
            return None

        def _step(self):
            st["k"] += 1
            for a in sched.get(st["k"], []):
                if a["op"] == "cancel":
                    for vid in st["oid"].get(a["ref"], []):
                        self.cancel_order(vid)
                    continue
                stop = a["type"] == "stop"
                px = float(a["stop_px"] if stop else a["px"])
                q = float(a["qty"])
                if a["side"] == "buy":
                    fn = self.cover if self.pos < 0 else self.buy
                else:
                    fn = self.sell if self.pos > 0 else self.short
                try:
                    ids = fn(px, q, stop=stop)
                except Exception as exc:  # the engine refused this order
                    st["rejected"][a["ref"]] = f"{type(exc).__name__}: {exc}"
                    continue
                st["oid"][a["ref"]] = list(ids or [])

        def on_tick(self, tick):
            self._step()

        def on_bar(self, bar):
            self._step()

    eng = BacktestingEngine()
    eng.output = lambda msg: None
    mode = BacktestingMode.TICK if mode_name == "TICK" else BacktestingMode.BAR
    try:
        eng.set_parameters(vt_symbol="X.LOCAL", interval=Interval.MINUTE, start=data[0][1].datetime,
                           end=data[-1][1].datetime + D.timedelta(days=1), rate=rate, slippage=0.0, size=1,
                           pricetick=float(inp["product"]["tick"]), capital=float(inp["account"]["cash"]), mode=mode)
        eng.add_strategy(S, {})
        eng.history_data = [x for _, x in data]
        eng.run_backtesting()
    except NotExpressible:
        raise
    except Exception as exc:
        raise Refused(f"{type(exc).__name__}: {exc}")
    rec = {"orders": {}, "fills": []}
    by_vid = {}
    for ref, vids in st["oid"].items():
        for v in vids:
            by_vid[v] = ref
    # a stop order's id maps to the limit order it sends when triggered
    for so in getattr(eng, "stop_orders", {}).values():
        ref = by_vid.get(so.stop_orderid)
        if ref:
            for v in so.vt_orderids:
                by_vid[v] = ref
    for tr in eng.trades.values():
        ref = by_vid.get(tr.vt_orderid)
        if ref:
            rec["fills"].append({"ref": ref, "t": _ns(tr.datetime), "px": float(tr.price), "qty": float(tr.volume), "liq": None})
    try:
        df = eng.calculate_result()
        per_day = {}
        for f in rec["fills"]:
            per_day.setdefault(_dt(f["t"]).date(), []).append(f)
        if df is not None and len(df):
            for day, fl in per_day.items():
                if len(fl) == 1 and day in df.index:
                    fl[0]["fee"] = float(df.loc[day, "commission"])
    except Exception:  # noqa: BLE001  (no result table -> fees are not reported)
        pass
    for ref, vids in st["oid"].items():
        sts = []
        for v in vids:
            o = eng.limit_orders.get(v)
            if o is not None:
                sts.append(STATUS.get(o.status, str(o.status)))
            else:
                so = eng.stop_orders.get(v) if hasattr(eng, "stop_orders") else None
                if so is not None:
                    sub = [eng.limit_orders[x] for x in so.vt_orderids if x in eng.limit_orders]
                    sts.append(STATUS.get(sub[-1].status, "open") if sub else "open")
        rec["orders"][ref] = {"status": sts[-1] if sts else "rejected"}
    for ref, err in st["rejected"].items():
        rec["orders"][ref] = {"status": "rejected", "error": err[:200]}
    return rec
