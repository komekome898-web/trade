"""Survey candidate 53 `rqalpha` (PyPI 6.4.0, venv item_0/rqalpha; install record: item 0
survey_results/attempts/53.log) for the item 2 battery.

The tool's own calls used: `rqalpha.run_func(init, handle_bar, config)` in daily frequency, a user mod (the documented
way to replace the bundle: `env.set_data_source(...)` with the tool's `BaseDataSource` over one numpy array), and in the
strategy `rqalpha.api`: `order_shares(id, amount, price_or_style=LimitOrder(px) | None)`, `cancel_order(order)`,
`get_open_orders()`, `subscribe_event(EVENT.TRADE, ...)`.  Config used: sys_simulation (matching_type None = the tool's
default for daily bars: current_bar = the bar's close; price_limit False -- the scenes' bars carry no limit prices;
volume_limit False, or True with volume_percent 1.0 for a tier-4 scene), sys_transaction_cost
(stock_commission_multiplier = rate / 0.0008 -- the tool's stock commission is 0.0008 times this multiplier --,
stock_min_commission 0, tax_multiplier 0).  No stop order, IOC, FOK, post-only, amend, latency, notices; a stock
account cannot sell short.

Scene -> tool: i2_common.bar_rows, bar k = trading day k of a daily calendar (rqalpha has daily bars); actions are
issued in handle_bar of the bar chosen by i2_common.issue_schedule; a fill's time = the end time of its bar.  The
instrument is a stock with round lot 1 (the tool needs an integer lot: a fractional round_lot fails with
DivisionByZero in order_shares); one share = the scene's quantity unit (lob_common.qty_unit), prices and volumes
are given per share and converted back.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.modules.setdefault("i2_rqalpha_adapter", sys.modules[__name__])  # the mod's `lib` names this module

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import i2_common as C  # noqa: E402
import lob_common as LC  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

from rqalpha import run_func  # noqa: E402  (the tool, in its venv)
from rqalpha.const import TRADING_CALENDAR_TYPE  # noqa: E402
from rqalpha.core.events import EVENT  # noqa: E402
from rqalpha.data.base_data_source import BaseDataSource  # noqa: E402
from rqalpha.interface import AbstractMod  # noqa: E402
from rqalpha.model.instrument import Instrument  # noqa: E402
from rqalpha.utils.datetime_func import convert_date_to_int  # noqa: E402

TOOL = "rqalpha 6.4.0"
OID = "X.XSHE"
DAY0 = D.datetime(2024, 1, 1)
_ST: dict = {}
_DT = [("datetime", "<u8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"), ("close", "<f8"), ("volume", "<f8"),
       ("total_turnover", "<f8"), ("limit_up", "<f8"), ("limit_down", "<f8"), ("prev_close", "<f8")]


class _Mem(BaseDataSource):
    def __init__(self, rows, unit):
        self._arr = np.array([(convert_date_to_int(DAY0 + D.timedelta(days=i)), b["o"] * unit, b["h"] * unit, b["l"] * unit,
                               b["c"] * unit, b["v"] / unit, b["v"] * b["c"], 1e15, 0.0, np.nan) for i, b in enumerate(rows)],
                             dtype=_DT)
        self._days = pd.date_range(DAY0, DAY0 + D.timedelta(days=len(rows) + 5), freq="D")
        self._ins = Instrument({"order_book_id": OID, "symbol": "X", "type": "CS", "listed_date": "2000-01-01",
                                "de_listed_date": "0000-00-00", "exchange": "XSHE", "round_lot": 1.0,
                                "board_type": "MainBoard", "status": "Active", "special_type": "Normal",
                                "trading_hours": "09:31-11:30,13:01-15:00", "market_tplus": 0})

    def _all_day_bars_of(self, instrument):
        return self._arr

    def _filtered_day_bars(self, instrument):
        return self._arr

    def get_trading_calendars(self):
        return {TRADING_CALENDAR_TYPE.EXCHANGE: self._days}

    def get_instruments(self, id_or_syms=None, types=None):
        return [self._ins]

    def get_dividend(self, instrument):
        return None

    def get_split(self, instrument):
        return None

    def get_ex_cum_factor(self, instrument):
        return None

    def is_suspended(self, order_book_id, dates):
        return [False] * len(dates)

    def is_st_stock(self, order_book_id, dates):
        return [False] * len(dates)

    def get_yield_curve(self, start_date, end_date, tenor=None):
        return None

    def available_data_range(self, frequency):
        return self._days[0].date(), self._days[-1].date()

    def get_share_transformation(self, order_book_id):
        return None

    def get_futures_trading_parameters(self, instrument, dt):
        return None


class _Mod(AbstractMod):
    def start_up(self, env, mod_config):
        env.set_data_source(_Mem(_ST["rows"], _ST["unit"]))
        env.event_bus.add_listener(EVENT.TRADE, lambda e: _ST["trades"].append(e.trade))

    def tear_down(self, code, exception=None):
        return None


def load_mod():
    return _Mod()


class Adapter:
    name = "opp_rqalpha"

    def run(self, inp):
        from rqalpha import api as R
        C.gate(inp, tool=TOOL, orders=("market", "limit", "cancel"), events=("book", "trade", "bar"),
               fill_models=lambda fm: None if fm.get("tier") == 4 and not fm.get("impact") and "range" not in fm
               else C.bar_fill_models(fm), costs=("maker_rate", "taker_rate"), account=("cash",))
        rate = C.single_fee_rate(inp, TOOL)
        rows, _src = C.bar_rows(inp)
        if not rows:
            raise NotExpressible(f"{TOOL}: 足にする約定も足も無い")
        unit = LC.qty_unit(inp)
        sched = C.issue_schedule(rows, inp["actions"])
        _ST.clear()
        _ST.update(rows=rows, unit=unit, trades=[])
        st = {"k": -1, "orders": {}, "rej": {}}

        def hb(context, bar_dict):
            st["k"] += 1
            for a in sched.get(st["k"], []):
                if a["op"] == "cancel":
                    o = st["orders"].get(a["ref"])
                    if o is not None:
                        R.cancel_order(o)
                    continue
                shares = round(float(a["qty"]) / unit)
                amt = shares if a["side"] == "buy" else -shares
                try:
                    o = R.order_shares(OID, amt, price_or_style=R.LimitOrder(float(a["px"]) * unit) if a["type"] == "limit" else None)
                except Exception as exc:  # the tool refused this order
                    st["rej"][a["ref"]] = f"{type(exc).__name__}: {exc}"
                    continue
                if o is None:
                    st["rej"][a["ref"]] = "order_shares returned None (the tool's risk checks rejected the order)"
                    continue
                st["orders"][a["ref"]] = o

        fm = inp.get("fill_model") or {}
        mods = {"sys_analyser": {"enabled": False}, "sys_progress": {"enabled": False},
                "sys_simulation": {"price_limit": False, "volume_limit": fm.get("tier") == 4, "volume_percent": 1.0,
                                   "inactive_limit": False},
                "sys_transaction_cost": {"stock_commission_multiplier": float(rate) / 0.0008, "stock_min_commission": 0,
                                         "tax_multiplier": 0},
                "sk": {"enabled": True, "lib": "i2_rqalpha_adapter"}}
        cfg = {"base": {"start_date": DAY0.strftime("%Y-%m-%d"),
                        "end_date": (DAY0 + D.timedelta(days=len(rows) - 1)).strftime("%Y-%m-%d"),
                        "frequency": "1d", "accounts": {"stock": float(inp["account"]["cash"])}},
               "extra": {"log_level": "error"}, "mod": mods}
        try:
            run_func(init=lambda ctx: None, handle_bar=hb, config=cfg)
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}"[:400])
        rec = {"orders": {}, "fills": []}
        by_id = {o.order_id: ref for ref, o in st["orders"].items()}
        for tr in _ST["trades"]:
            ref = by_id.get(tr.order_id)
            if ref is None:
                continue
            k = (pd.Timestamp(tr.datetime).normalize() - pd.Timestamp(DAY0)).days
            rec["fills"].append({"ref": ref, "t": int(rows[k]["t"]) if 0 <= k < len(rows) else None,
                                 "px": float(tr.last_price) / unit, "qty": float(tr.last_quantity) * unit,
                                 "fee": float(tr.transaction_cost), "liq": None})
        for ref, o in st["orders"].items():
            s = str(o.status).split(".")[-1]
            rec["orders"][ref] = {"status": {"FILLED": "filled", "ACTIVE": "open", "PENDING_NEW": "open",
                                             "CANCELLED": "canceled", "REJECTED": "rejected"}.get(s, s.lower())}
        for ref, err in st["rej"].items():
            rec["orders"][ref] = {"status": "rejected", "error": err[:200]}
        return rec


TARGET = Adapter()
