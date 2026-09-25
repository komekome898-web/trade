"""Survey candidate 18 `zipline-reloaded` (PyPI 3.1.1, venv item_0/zipline-reloaded) for the item 2 battery.

Public API used: a custom bundle (`zipline.data.bundles.register` / `ingest`),
the `24/7` calendar, `zipline.run_algorithm` (daily), and in the algorithm
`zipline.api` (`order` with `limit_price` / `stop_price`, `cancel_order`,
`get_order`, `set_commission(commission.PerDollar)`, `set_slippage`), the
slippage models `FixedSlippage(spread)`, `VolumeShareSlippage(volume_limit,
price_impact)` and a user `SlippageModel` subclass (`process_order(data, order)
-> (price, amount)`, the documented plug for a market-impact function).

Scene -> tool: zipline takes OHLCV bars per session, not a book. Every trade of
the scene is one daily session in order (session k = the k-th trade; open =
high = low = close = its price, volume = its quantity); book snapshots are not
given. An action is issued in `handle_data` of the last session at or before
its time; zipline fills it on later sessions by its own rules. A fill's time is
the time of the trade whose session zipline filled it on. Zipline's amounts are
whole shares.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

_ROOT = tempfile.mkdtemp(prefix="i2_zipline_root_")
os.environ["ZIPLINE_ROOT"] = _ROOT

import zipline  # noqa: E402
from zipline import api as Z  # noqa: E402
from zipline.data import bundles  # noqa: E402
from zipline.finance import commission as zcomm, slippage as zslip  # noqa: E402
from zipline.finance.execution import LimitOrder, StopOrder  # noqa: E402
from zipline.utils.calendar_utils import get_calendar  # noqa: E402

TOOL = "zipline-reloaded 3.1.1"
CAL = get_calendar("24/7")
START = pd.Timestamp("2024-01-01")


def _fm(fm):
    if "range" in fm:
        return "楽観と悲観を同時に回す口が無い"
    if "impact" in fm:
        return None  # a user SlippageModel carries the scene's impact function
    if fm.get("tier") == 4 and fm.get("cancel_stance", "none") == "none":
        return None  # VolumeShareSlippage(volume_limit=1, price_impact=0): fills up to the bar's volume
    return f"段 {fm.get('tier')} / 取消の扱い {fm.get('cancel_stance')} の約定の模型が無い(slippage は価格と数量を足ごとに決める模型)"


class _Impact(zslip.SlippageModel):
    """The scene's impact function handed to zipline's slippage plug (reference price = the bar's close)."""

    def __init__(self, im):
        super().__init__()
        self.im = im
        self.shift = 0.0

    def process_order(self, data, order):
        px = float(data.current(order.asset, "close")) + self.shift
        q = abs(order.amount)
        sgn = 1 if order.amount > 0 else -1
        k = self.im["kind"]
        if k == "linear_temporary":
            p = px + sgn * self.im["k"] * q
        elif k == "sqrt_temporary":
            p = px * (1 + sgn * self.im["eta"] * math.sqrt(q / self.im["adv"]))
        else:  # linear_permanent
            p = px
            self.shift += sgn * self.im["gamma"] * q
        return p, order.amount


class ZiplineAdapter:
    name = "opp_zipline_reloaded"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "cancel"), events=("book", "trade"),
               fill_models=_fm, costs=("maker_rate", "taker_rate", "spread"), account=("cash",))
        c = inp["costs"]
        if c.get("maker_rate", 0.0) != c.get("taker_rate", 0.0) and any(a["type"] == "limit" for a in C.places(inp)):
            raise NotExpressible(f"{TOOL}: 手数料は commission の模型 1 つ(PerDollar(cost))で maker と taker を分けられない")
        tr = C.trades(inp)
        if not tr:
            raise NotExpressible(f"{TOOL}: 足にする約定が無い(zipline は足の bundle だけを取る)")
        bar_t = [e["t"] for e in tr]
        sessions = CAL.sessions_in_range(START, START + pd.Timedelta(days=len(tr) + 3))
        idx = sessions[: len(tr)]
        df = pd.DataFrame({"open": [e["px"] for e in tr], "high": [e["px"] for e in tr], "low": [e["px"] for e in tr],
                           "close": [e["px"] for e in tr], "volume": [e["qty"] for e in tr]}, index=idx)
        # measured on this install: the bar written at session label L is what handle_data reads on the NEXT
        # session (get_datetime() = L + 2 days), so the run covers sessions[1..n] and handle_data call j reads trade j
        run_start, end = sessions[1], sessions[len(tr)]
        name = "i2" + uuid.uuid4().hex[:8]

        def ingest(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar,
                   start_session, end_session, cache, show_progress, output_dir):
            full = df.reindex(calendar.sessions_in_range(idx[0], end))
            asset_db_writer.write(
                equities=pd.DataFrame({"symbol": ["X"], "asset_name": ["X"], "start_date": [idx[0]], "end_date": [end + pd.Timedelta(days=2)],
                                       "exchange": ["XX"]}),
                exchanges=pd.DataFrame({"exchange": ["XX"], "canonical_name": ["XX"], "country_code": ["US"]}))
            daily_bar_writer.write([(0, full)], show_progress=False)
            adjustment_writer.write()

        sched = C.issue_schedule(bar_t, inp["actions"])
        fm = inp.get("fill_model") or {}
        rec = {"ids": {}, "k": -1}

        def init(ctx):
            ctx.a = Z.symbol("X")
            Z.set_commission(zcomm.PerDollar(cost=float(c.get("taker_rate", 0.0))))
            if "impact" in fm:
                Z.set_slippage(_Impact(fm["impact"]))
            elif fm.get("tier") == 4:
                Z.set_slippage(zslip.VolumeShareSlippage(volume_limit=1.0, price_impact=0.0))
            else:
                Z.set_slippage(zslip.FixedSlippage(spread=float(c.get("spread", 0.0))))

        def hd(ctx, data):
            rec["k"] += 1
            k = rec["k"]
            rec.setdefault("dt2k", {})[pd.Timestamp(Z.get_datetime()).tz_localize(None).normalize()] = k
            for a in sched.get(k, []):
                if a["op"] == "cancel":
                    if a["ref"] in rec["ids"]:
                        Z.cancel_order(rec["ids"][a["ref"]])
                    continue
                amt = a["qty"] if a["side"] == "buy" else -a["qty"]
                style = None
                if a["type"] == "limit":
                    style = LimitOrder(a["px"])
                elif a["type"] == "stop":
                    style = StopOrder(a["stop_px"])
                try:
                    oid = Z.order(ctx.a, amt, style=style) if style else Z.order(ctx.a, amt)
                except Exception as exc:
                    rec.setdefault("rej", {})[a["ref"]] = f"{type(exc).__name__}: {exc}"[:200]
                    continue
                if oid is None:
                    rec.setdefault("rej", {})[a["ref"]] = "order() が None を返した"
                    continue
                rec["ids"][a["ref"]] = oid

        try:
            bundles.register(name, ingest, calendar_name="24/7", start_session=idx[0], end_session=end)
            bundles.ingest(name, os.environ, show_progress=False)
            perf = zipline.run_algorithm(start=run_start, end=end, initialize=init, handle_data=hd,
                                         capital_base=float(inp["account"]["cash"]), data_frequency="daily", bundle=name,
                                         trading_calendar=CAL,
                                         benchmark_returns=pd.Series(0.0, index=CAL.sessions_in_range(run_start, end).tz_localize("UTC")))
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}"[:400])
        sess_pos = rec.get("dt2k", {})
        fills, orders = [], {}
        for ref, msg in rec.get("rej", {}).items():
            orders[ref] = {"status": "rejected", "error": msg}
        txs = []
        for _, row in perf.iterrows():
            for tx in row["transactions"]:
                txs.append(tx)
        by_oid = {v: k for k, v in rec["ids"].items()}
        for tx in txs:
            ref = by_oid.get(tx["order_id"])
            if ref is None:
                continue
            d = pd.Timestamp(tx["dt"]).tz_localize(None).normalize()
            k = sess_pos.get(d)
            fills.append({"ref": ref, "t": bar_t[k] if k is not None else None, "px": float(tx["price"]),
                          "qty": abs(float(tx["amount"])), "fee": float(tx.get("commission") or 0.0), "liq": None})
        last_orders = {}
        for _, row in perf.iterrows():
            for o in row["orders"]:
                last_orders[o["id"]] = o
        for ref, oid in rec["ids"].items():
            o = last_orders.get(oid)
            if o is None:
                orders[ref] = {"status": "open"}
                continue
            st = int(o["status"])
            # zipline ORDER_STATUS: OPEN 0, FILLED 1, CANCELLED 2, REJECTED 3, HELD 4
            orders[ref] = {"status": {0: "open", 1: "filled", 2: "canceled", 3: "rejected", 4: "open"}.get(st, f"code{st}")}
        # commissions in zipline are booked on the order; spread them over its fills by quantity
        for ref, oid in rec["ids"].items():
            o = last_orders.get(oid)
            mine = [f for f in fills if f["ref"] == ref]
            if o is not None and mine and not any(f["fee"] for f in mine):
                tot = sum(f["qty"] for f in mine)
                for f in mine:
                    f["fee"] = float(o.get("commission") or 0.0) * f["qty"] / tot
        pos = 0.0
        last = perf.iloc[-1]
        for p in last["positions"]:
            pos += float(p["amount"])
        return {"orders": orders, "fills": fills, "account": {"position": pos}}


TARGET = ZiplineAdapter()
