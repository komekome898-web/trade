"""Survey candidate `rqalpha` (PyPI `rqalpha` 6.4.0), run in its own venv.

Driven through its public API: `rqalpha.run_func(init=, handle_bar=, config=)`
in daily mode, a user mod (`config["mod"]["sk"] = {"enabled": True, "lib":
"rqalpha_adapter"}`, this module's `load_mod`) that brings the data in memory
with `env.set_data_source(...)` (the documented way to replace the bundle),
and inside the strategy `rqalpha.api` (`order_shares`, `cancel_order`,
`get_open_orders`, `history_bars`, `subscribe_event`, `scheduler`).

rqalpha takes daily bars per instrument from its data source. A bar whose
close is T0 + i DAY is the trading date of the day it covers (T0 + (i-1) DAY),
the way the zipline adapters date a daily bar. rqalpha calls the strategy at
15:00 of the trading date in exchange (Beijing, UTC+8) time; `context.now` is
naive and is read as Asia/Shanghai time when turned into UTC ns.

The in-memory data source reuses `BaseDataSource`'s own `get_bar` /
`history_bars` over one numpy array, with a calendar of every day (24/7).
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

sys.modules.setdefault("rqalpha_adapter", sys.modules[__name__])  # the mod lib and slippage path name this module

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

from rqalpha import run_func  # noqa: E402
from rqalpha.const import TRADING_CALENDAR_TYPE  # noqa: E402
from rqalpha.core.events import EVENT  # noqa: E402
from rqalpha.data.base_data_source import BaseDataSource  # noqa: E402
from rqalpha.interface import AbstractMod, AbstractTransactionCostDecider, TransactionCost  # noqa: E402
from rqalpha.model.instrument import Instrument  # noqa: E402
from rqalpha.utils.datetime_func import convert_date_to_int  # noqa: E402

DAY = 86_400 * 10**9
SH = ZoneInfo("Asia/Shanghai")
OID = "X.XSHE"
_ST: dict = {}
_DT = [("datetime", "<u8"), ("open", "<f8"), ("high", "<f8"), ("low", "<f8"), ("close", "<f8"), ("volume", "<f8"),
       ("total_turnover", "<f8"), ("limit_up", "<f8"), ("limit_down", "<f8"), ("prev_close", "<f8")]
_INS = Instrument({"order_book_id": OID, "symbol": "X", "type": "CS", "listed_date": "2000-01-01",
                   "de_listed_date": "0000-00-00", "exchange": "XSHE", "round_lot": 1.0, "board_type": "MainBoard",
                   "status": "Active", "special_type": "Normal", "trading_hours": "09:31-11:30,13:01-15:00",
                   "market_tplus": 0})


def _day_of(ts_ns: int) -> D.datetime:
    d = C.ns_to_dt(int(ts_ns) - DAY)
    return D.datetime(d.year, d.month, d.day)


class _Mem(BaseDataSource):
    def __init__(self, rows):
        self._arr = np.array([(convert_date_to_int(_day_of(b["ts_ns"])), b["open"], b["high"], b["low"], b["close"],
                               b.get("volume", 1.0), b.get("volume", 1.0) * b["close"], 1e15, 0.0, np.nan) for b in rows],
                             dtype=_DT)
        days = [_day_of(b["ts_ns"]) for b in rows]
        self._days = pd.date_range(min(days) - D.timedelta(days=30), max(days) + D.timedelta(days=30), freq="D")

    def _all_day_bars_of(self, instrument):
        return self._arr

    def _filtered_day_bars(self, instrument):
        return self._arr

    def get_trading_calendars(self):
        return {TRADING_CALENDAR_TYPE.EXCHANGE: self._days}

    def get_instruments(self, id_or_syms=None, types=None):
        return [_INS]

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


class _SkMod(AbstractMod):
    def start_up(self, env, mod_config):
        env.set_data_source((_ST.get("mem_cls") or _Mem)(_ST["rows"]))
        if _ST.get("decider") is not None:
            env.event_bus.add_listener(EVENT.POST_SYSTEM_INIT, lambda e: [
                env.set_transaction_cost_decider(t, _ST["decider"]) for t in _types()])
        if _ST.get("portfolio_cls") is not None:
            def init_pf(e):
                from rqalpha.portfolio import Portfolio  # noqa: F401
                c = env.config
                env.set_portfolio(_ST["portfolio_cls"](c.base.accounts, c.base.init_positions, c.mod.sys_accounts.financing_rate, env))
            env.event_bus.add_listener(EVENT.INIT_PORTFOLIO, init_pf)

    def tear_down(self, code, exception=None):
        return None


def _types():
    from rqalpha.const import INSTRUMENT_TYPE
    return [INSTRUMENT_TYPE.CS]


def load_mod():
    return _SkMod()


def _now(context) -> int:
    return C.dt_to_ns(context.now.replace(tzinfo=SH).astimezone(D.timezone.utc))


def run(bars, handle, init=None, cash=1_000_000.0, sim=None, decider=None, portfolio_cls=None, mem_cls=None):
    rows = [C.as_bar(b) for b in bars]
    _ST.clear()
    _ST.update(rows=rows, decider=decider, portfolio_cls=portfolio_cls, mem_cls=mem_cls)
    state = {"n": 0, "log": [], "calls_ns": [], "notices": []}
    days = [_day_of(b["ts_ns"]) for b in rows]

    def _init(context):
        context.st = state
        if init:
            init(context)

    def _hb(context, bar_dict):
        state["n"] += 1
        state["calls_ns"].append(_now(context))
        handle(context, bar_dict, state["n"])

    mods = {"sys_analyser": {"enabled": False}, "sys_progress": {"enabled": False},
            "sys_simulation": dict(sim or {}), "sk": {"enabled": True, "lib": "rqalpha_adapter"}}
    cfg = {"base": {"start_date": min(days).strftime("%Y-%m-%d"), "end_date": max(days).strftime("%Y-%m-%d"),
                    "frequency": "1d", "accounts": {"stock": cash}, "capital_gain_tax_rate": 0.0},
           "extra": {"log_level": "error"}, "mod": mods}
    state["result"] = run_func(init=_init, handle_bar=_hb, config=cfg)
    return state


NON_BAR = ("rqalpha の日足・分足の回の入力は、データ源の銘柄ごとの足(datetime/open/high/low/close/volume の配列)で、{k} を型として"
           "戦略に渡す口が無い(tick の回は tick だけを渡す別の頻度)。試したこと: データ源の配列に {k} の列だけを入れて run_func -> {err}")


def _try_non_bar(e: dict) -> str:
    try:
        class M(_Mem):
            def __init__(self, rows):
                super().__init__([{"ts_ns": e["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}])
                self._arr = np.array([(convert_date_to_int(_day_of(e["ts_ns"])),) + tuple(
                    float(v) for v in C.fields_of(e).values() if isinstance(v, (int, float)))],
                    dtype=[("datetime", "<u8")] + [(k, "<f8") for k, v in C.fields_of(e).items() if isinstance(v, (int, float))])
        run([{"ts_ns": e["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}], lambda c, b, n: b[OID].close, mem_cls=M)
    except BaseException as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return "例外なく走った"


def _api():
    import rqalpha.api as A
    return A


class RqalphaAdapter(Adapter):
    name = "opp_rqalpha"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def _seq(self, bars):
        def h(c, b, n):
            c.st["log"].append(["bar", _now(c)])
        return run(bars, h)["log"]

    def scene_p1_one_call_per_event(self, sc):
        return ok({"sequence": self._seq(C.events(sc))}, "日足 5 本。handle_bar の各回に context.now(北京時間)を UTC の ns にして記録")

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    # ---------------- P0-2
    def _iso(self, sc):
        return ok(int(pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value),
                  "rqalpha の日時は datetime / pandas(get_trading_dates は pandas.DatetimeIndex)。pd.Timestamp(iso).tz_convert('UTC').value")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        return ok({"observed_ts_ns": [t for _, t in self._seq(evs)]},
                  "足で渡した。データ源の datetime は YYYYMMDDhhmmss の整数(convert_date_to_int)で、日足は取引日に丸められる。"
                  "handle_bar の context.now")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        def h(c, b, n):
            c.st["log"].append(["bar", _now(c)])
            bar = b[OID]
            out.update({k: float(getattr(bar, k)) for k in ("open", "high", "low", "close", "volume")})

        st = run([e], h)
        return ok({"sequence": st["log"], "fields": out}, "日足 1 本。bar_dict['X.XSHE'] の open/high/low/close/volume")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        e = [x for x in C.events(sc) if x["kind"] != "bar"][0]
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(e)))

    def scene_p3_clock_timer(self, sc):
        calls = []
        A = _api()

        def h(c, b, n):
            if n == 1:
                try:
                    A.scheduler.run_daily(lambda ctx, bd: calls.append(_now(ctx)))
                except BaseException as exc:  # noqa: BLE001
                    c.st["err"] = f"handle_bar の中で scheduler.run_daily -> {type(exc).__name__}: {str(exc)[:120]}"

        def init(c):
            A.scheduler.run_daily(lambda ctx, bd: calls.append(_now(ctx)))

        st = run([C.as_bar(e) for e in C.events(sc)], h)
        if st.get("err") or not calls:
            calls.clear()
            run([C.as_bar(e) for e in C.events(sc)], lambda c, b, n: None, init)
            return ok({"clock_calls_ns": calls}, f"{st.get('err')}。scheduler は init でだけ登録でき、毎日・毎週・毎月の規則で頼む形で、"
                      "決まった時刻を 1 回だけ頼む口は無い。init で run_daily を頼み、呼ばれた時刻を全部記録した")
        return ok({"clock_calls_ns": calls}, "handle_bar の 1 回目で scheduler.run_daily を頼み、呼ばれた時刻を全部記録した")

    def _notice_run(self, sc, strategy, cash):
        A = _api()
        ev = {EVENT.ORDER_CREATION_PASS: "accepted", EVENT.ORDER_CREATION_REJECT: "rejected",
              EVENT.ORDER_CANCELLATION_PASS: "canceled"}

        def init(c):
            for k, name in ev.items():
                A.subscribe_event(k, lambda ctx, e, name=name: ctx.st["notices"].append(name))
            A.subscribe_event(EVENT.TRADE, lambda ctx, e: (ctx.st["notices"].append("filled"),
                                                           ctx.st.setdefault("fill_qty", []).append(float(e.trade.last_quantity))))

        return run([C.as_bar(e) for e in C.events(sc)], strategy, init, cash=cash)

    def scene_p3_notice_accepted(self, sc):
        A = _api()
        st = self._notice_run(sc, lambda c, b, n: n == 1 and A.order_shares(OID, 1, price_or_style=A.LimitOrder(90.0)), 1_000_000.0)
        return ok({"notices": st["notices"]}, "init で subscribe_event(ORDER_CREATION_PASS / ORDER_CREATION_REJECT / "
                  "ORDER_CANCELLATION_PASS / TRADE) を頼み、呼び戻しで記録")

    def scene_p3_notice_rejected(self, sc):
        A = _api()
        st = self._notice_run(sc, lambda c, b, n: n == 1 and A.order_shares(OID, 1), 1_000.0)
        return ok({"notices": st["notices"]}, "現金 1,000。subscribe_event の呼び戻しで記録")

    def scene_p3_notice_filled(self, sc):
        A = _api()
        st = self._notice_run(sc, lambda c, b, n: n == 1 and A.order_shares(OID, 1), 1_000_000.0)
        return ok({"filled_qty_in_notices": sum(st.get("fill_qty", [])), "notices": st["notices"]},
                  "TRADE の知らせの trade.last_quantity を足した")

    # ---------------- P0-4
    def _probe_calls(self, sc):
        st = run(C.events(sc), lambda c, b, n: None)
        return st["calls_ns"]

    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out, seen, tried = {}, [], []
        A = _api()

        def h(c, b, n):
            seen.append(float(b[OID].close))
            if _now(c) == probe:
                tried.append(f"history_bars(10) -> {list(A.history_bars(OID, 10, '1d', 'close'))}")
                out["visible_count"] = len(seen)
                out["max_visible_close"] = max(seen)

        st = run(C.events(sc), h)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日(UTC 0 時)の呼び出しが無かった。rqalpha の日足の回は取引日の 15:00(北京時間 = UTC 7:00)に"
                                 f"戦略を呼ぶ。呼び出しの時刻 {st['calls_ns']}、各回の bar_dict の close {seen}")
        return ok(out, f"各回の close {seen}。{tried}")

    def scene_p4_received_time(self, sc):
        return not_supported("足は 1 本に時刻 1 つ(datetime)で、受け取れる時刻を別に持たせる口が無い。試したこと: 配列に recv の列を足して渡す -> "
                             + _try_non_bar({"ts_ns": sc.input["events"][0]["ts_ns"], "recv_ns": 1.0}))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        tried, got = [], {"v": False}
        A = _api()

        def h(c, b, n):
            if _now(c) != probe:
                return
            for label, fn in [("history_bars(6)", lambda: list(A.history_bars(OID, 6, "1d", "close"))),
                              ("history_bars(6, include_now=True)", lambda: list(A.history_bars(OID, 6, "1d", "close", include_now=True))),
                              ("current_snapshot", lambda: A.current_snapshot(OID).last)]:
                try:
                    v = fn()
                    tried.append(f"{label} -> {v}")
                    if v == 104.0 or (isinstance(v, list) and 104.0 in v):
                        got["v"] = True
                except BaseException as exc:  # noqa: BLE001
                    tried.append(f"{label} -> {type(exc).__name__}: {str(exc)[:80]}")

        st = run(C.events(sc), h)
        if not tried:  # no_probe_call
            return not_supported("T0 + 4 日(UTC 0 時)の呼び出しが無かったので、先を読む試しができなかった(日足の回は取引日の 15:00 北京時間)。"
                                 f"呼び出しの時刻 {st['calls_ns']}")
        return ok({"future_value_obtained": got["v"]}, "T0 + 4 日の呼び出しに試した: " + " ; ".join(tried))

    # ---------------- P0-5
    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        seen = []

        def h(c, b, n):
            seen.append(float(b[OID].close))

        st = run([C.as_bar(e) for e in C.events(sc)], h)
        return ok({"prices": seen}, f"同じ時刻の 2 本(終値 100 と 101)をデータ源の配列に並べた。各回の bar_dict の close、呼び出し {st['calls_ns']}")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        A = _api()
        out = {}

        def h(c, b, n):
            if n == 1:
                c.o = A.order_shares(OID, 1, price_or_style=A.LimitOrder(90.0))
            elif n == 2:
                out["open_at_call2"] = len(A.get_open_orders())
                A.cancel_order(c.o)
            elif n == 3:
                out["open_at_call3"] = len(A.get_open_orders())

        run([C.as_bar(e) for e in C.events(sc)], h)
        return ok(out, "order_shares(LimitOrder(90)) / get_open_orders / cancel_order")

    def scene_p6_cancel_notice(self, sc):
        A = _api()

        def h(c, b, n):
            if n == 1:
                c.o = A.order_shares(OID, 1, price_or_style=A.LimitOrder(90.0))
            elif n == 2:
                A.cancel_order(c.o)

        st = self._notice_run(sc, h, 1_000_000.0)
        return ok({"cancel_notice_received": "canceled" in st["notices"], "notices": st["notices"]},
                  "subscribe_event(ORDER_CANCELLATION_PASS) の呼び戻しで記録")

    def scene_p6_fill_seen_by_strategy(self, sc):
        A = _api()
        out = {}

        def h(c, b, n):
            if n == 1:
                c.o = A.order_shares(OID, 1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(c.o.filled_quantity)

        run([C.as_bar(e) for e in C.events(sc)], h)
        return ok(out, "3 回目に order.filled_quantity")

    # ---------------- P0-7
    def _buy(self, sc, **kw):
        A = _api()
        out = {}

        def h(c, b, n):
            if n == 1:
                c.o = A.order_shares(OID, 1)
            out.update({"filled": float(c.o.filled_quantity), "avg_price": float(c.o.avg_price),
                        "transaction_cost": float(c.o.transaction_cost)})

        run([C.as_bar(e) for e in C.events(sc)], h, cash=100_000.0, **kw)
        return out

    def scene_p7_fill_model_swap(self, sc):
        out = self._buy(sc, sim={"slippage_model": "rqalpha_adapter.FixedSlippage", "slippage": 0.0})
        return ok({"fill_price": out.get("avg_price")}, "mod sys_simulation の slippage_model に BaseSlippage の子(get_trade_price が 12345.0 を返す)"
                  f"のクラスの道を渡した(マッチングは current_bar の終値)。order.avg_price: {out}")

    def scene_p7_latency_model_swap(self, sc):
        from rqalpha.mod.rqalpha_mod_sys_simulation import __config__ as simcfg
        return not_supported("発注の遅延の模型を渡す口が無い。sys_simulation の設定の鍵は "
                             f"{sorted(simcfg.keys())}(撮合の方式・滑り・出来高の制限で、遅延は無い)")

    def _fee(self, fee):
        class Flat(AbstractTransactionCostDecider):
            def calc(self, args):
                return TransactionCost(commission=fee, tax=0.0, other_fees=0.0)
        return Flat()

    def scene_p7_cost_model_swap(self, sc):
        out = self._buy(sc, decider=self._fee(0.5))
        return ok({"fee": out.get("transaction_cost")}, "mod から env.set_transaction_cost_decider(CS, <AbstractTransactionCostDecider の子: "
                  f"1 件 0.5>)。order.transaction_cost: {out}")

    def scene_p7_cost_zero(self, sc):
        out = self._buy(sc, decider=self._fee(0.0))
        return ok({"fee": out.get("transaction_cost")}, "mod から env.set_transaction_cost_decider(CS, <1 件 0.0>)。"
                  f"order.transaction_cost: {out}")

    def scene_p7_account_swap(self, sc):
        from rqalpha.portfolio import Portfolio
        rec = []

        class RecPortfolio(Portfolio):
            def _on_trade(self, event):
                rec.append(float(event.trade.last_quantity))
                return super()._on_trade(event)

        self._buy(sc, portfolio_cls=RecPortfolio)
        return ok({"account_recorded_fill_qty": rec}, "mod が EVENT.INIT_PORTFOLIO で env.set_portfolio(<Portfolio の子>) を登録した"
                  "(rqalpha は INIT_PORTFOLIO で mod が口座を登録でき、無ければ既定の Portfolio を作る。main.py 170-175 行)。"
                  "子の _on_trade で約定の数量を記録した")


from rqalpha.mod.rqalpha_mod_sys_simulation.slippage import BaseSlippage  # noqa: E402


class FixedSlippage(BaseSlippage):
    def __init__(self, rate=0.0):
        self.rate = rate

    def get_trade_price(self, order, price):
        return 12345.0
