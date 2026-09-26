"""Survey candidate 53 `rqalpha` (PyPI rqalpha 6.4.0, venv item_4/rqalpha) for the item 4 battery.

The tool's own calls used (as item 2 found them): `rqalpha.run_func(init, handle_bar, config)` in daily frequency, a user
mod (the documented way to replace the bundle: `env.set_data_source(...)` with the tool's `BaseDataSource` over one numpy
array), and in the strategy `rqalpha.api.order_shares(id, amount, price_or_style=None | LimitOrder(px))`,
`cancel_order`, `subscribe_event`; config sys_simulation.matching_type = "next_bar" (the tool's NEXT_BAR_OPEN:
const.py 83-90 行) -- which the tool abandons in daily frequency and matches at the current bar's close instead
(mod/rqalpha_mod_sys_simulation/mod.py 60-62 行: "matching_type = 'next_bar' is abandoned when frequency == '1d'";
minute frequency needs the tool's minute bundle, which a BaseDataSource over day bars does not give), price_limit /
volume_limit off,
sys_transaction_cost (stock_commission_multiplier = rate / 0.0008 -- the tool's stock commission is 0.0008 x the
multiplier --, min commission 0, tax 0).

Scene -> tool: scene bar k = trading day k of a daily calendar (rqalpha has no 1-minute bars without its own bundle);
the instrument is a stock with round lot 1 (shares are whole: order_shares(int)), so an entry is
round(order_notional / close[i]) shares; a stock account holds long positions only.  Not expressible: allow_short
(stock account), slippage / spread as a price adjustment, a maker fee different from the taker fee, stop orders
(no stop order in the tool: item 2's reading), resting-limit take-profits and maker execution on top of the scene's
rules (the adapter sends market orders; LimitOrder exists and is not used here), swap, per-trade PnL, per-bar equity,
missed fills, metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.modules.setdefault("i4_rqalpha_adapter", sys.modules[__name__])  # the mod's `lib` names this module

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

from rqalpha import run_func  # noqa: E402
from rqalpha.const import TRADING_CALENDAR_TYPE  # noqa: E402
from rqalpha.core.events import EVENT  # noqa: E402
from rqalpha.data.base_data_source import BaseDataSource  # noqa: E402
from rqalpha.interface import AbstractMod  # noqa: E402
from rqalpha.model.instrument import Instrument  # noqa: E402
from rqalpha.utils.datetime_func import convert_date_to_int  # noqa: E402

OID = "X.XSHE"
DAY0 = D.datetime(2024, 1, 1)
_ST: dict = {}
_DT = [("datetime", "<u8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"), ("close", "<f8"), ("volume", "<f8"),
       ("total_turnover", "<f8"), ("limit_up", "<f8"), ("limit_down", "<f8"), ("prev_close", "<f8")]
NO_ORDER = ("この adapter は成行だけを送る(逆指値の注文は道具に無い。LimitOrder は在るが、決済の水準の管理と時間切れの取消を"
            "道具の口で書いていない)")


class _Mem(BaseDataSource):
    def __init__(self, bars):
        self._arr = np.array([(convert_date_to_int(DAY0 + D.timedelta(days=i)), b["open"], b["high"], b["low"], b["close"],
                               1e12, 1e12 * b["close"], 1e15, 0.0, np.nan) for i, b in enumerate(bars)], dtype=_DT)
        self._days = pd.date_range(DAY0, DAY0 + D.timedelta(days=len(bars) + 5), freq="D")
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
        env.set_data_source(_Mem(_ST["bars"]))
        env.event_bus.add_listener(EVENT.TRADE, lambda e: _ST["trades"].append(e.trade))

    def tear_down(self, code, exception=None):
        return None


def load_mod():
    return _Mod()


class RqalphaAdapter(Base):
    name = "opp_rqalpha"
    TOOL = "rqalpha 6.4.0"
    SUPPORTS = {"taker_fee_pct", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"allow_short": "株の口座は買い建てだけ(accounts は stock)", "slippage_pct": "率の滑りは道具にあるが(sys_simulation.slippage)、"
               "スプレッドの半分との和を 1 本の率として約定値に掛ける形とは別で、この adapter は写していない",
               "spread_pct": "スプレッドの口を探したが無い", "maker_fee_pct": NO_ORDER, "execution": NO_ORDER,
               "stop_loss_pct": NO_ORDER, "take_profit_pct": NO_ORDER, "exit_execution": NO_ORDER, "maker_tp_pct": NO_ORDER,
               "swap_daily_pct": "株の持ち越しの口を探したが無い"}
    METRICS = "12 の指標: sys_analyser は日次の成績(sharpe・max_drawdown など)で、決済ごとの損益・勝率・PF の口が無い"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "データは rqalpha の bundle(日足・分足の自前の形)で、宣言でファイルを読む口・約定/気配/板・目的つきの書き出し・ダッシュボードが無い"

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い(EVENT.TRADE は約定)"), ("equity", "足ごとの資産の推移をこの adapter は取り出していない"),
                       ("missed_fills", NO_ORDER), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        return out

    def bars(self, inp):
        from rqalpha import api as R
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        _ST.clear()
        _ST.update(bars=bars, trades=[])
        st = {"k": -1, "pos": 0, "entry_bar": None, "level": None, "tags": {}}

        def send(amt, tag):
            o = R.order_shares(OID, amt)
            if o is not None:
                st["tags"][o.order_id] = tag
            return o

        def hb(context, bar_dict):
            st["k"] += 1
            k = st["k"]
            pos = st["pos"]
            cl = bars[k]["close"]
            if pos and st["entry_bar"] is not None:
                if (N is not None and k + 1 - st["entry_bar"] >= N) or \
                        (st["level"] is not None and k >= st["entry_bar"] and cl < st["level"]):
                    send(-pos, "CLOSE_LONG"); st.update(pos=0, entry_bar=None, level=None)
                    return
            s = sig.get(k)
            if not s or k + 1 >= len(bars):
                return
            if s in ("SELL", "CLOSE"):
                if pos > 0:
                    send(-pos, "CLOSE_LONG"); st.update(pos=0, entry_bar=None, level=None)
                return
            if pos == 0 and cfg["entry_sides"] != "short" and (mask is None or mask[k]):
                q = round(cfg["order_notional"] / cl)
                if send(q, "OPEN_LONG") is not None:
                    st["pos"] = q
                    b = k + 1
                    st["entry_bar"] = b
                    if W is not None:
                        lo = max(0, b - W)
                        st["level"] = min(bars[j]["low"] for j in range(lo, b)) if b > lo else None

        mods = {"sys_analyser": {"enabled": False}, "sys_progress": {"enabled": False},
                "sys_simulation": {"price_limit": False, "volume_limit": False, "inactive_limit": False,
                                   "matching_type": "next_bar"},
                "sys_transaction_cost": {"stock_commission_multiplier": float(c["taker_fee_pct"]) / 100 / 0.0008,
                                         "stock_min_commission": 0, "tax_multiplier": 0},
                "sk": {"enabled": True, "lib": "i4_rqalpha_adapter"}}
        conf = {"base": {"start_date": DAY0.strftime("%Y-%m-%d"),
                         "end_date": (DAY0 + D.timedelta(days=len(bars) - 1)).strftime("%Y-%m-%d"),
                         "frequency": "1d", "accounts": {"stock": float(cfg["initial_equity"])}},
                "extra": {"log_level": "error"}, "mod": mods}
        try:
            run_func(init=lambda ctx: None, handle_bar=hb, config=conf)
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}"[:400]) from exc
        fills = []
        for tr in _ST["trades"]:
            k = (pd.Timestamp(tr.datetime).normalize() - pd.Timestamp(DAY0)).days
            fills.append({"bar": k, "side": st["tags"].get(tr.order_id), "price": float(tr.last_price),
                          "size": float(tr.last_quantity)})
        fills.sort(key=lambda f: (f["bar"], 0 if str(f["side"]).startswith("CLOSE") else 1))
        return want(inp, {"fills": fills})


TARGET = RqalphaAdapter()
