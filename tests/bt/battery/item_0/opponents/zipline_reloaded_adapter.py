"""Survey candidate 18 `zipline-reloaded` (PyPI 3.1.1), run in its own venv.

Driven through its public API: a custom data bundle (`zipline.data.bundles.
register` / `ingest`, the documented way to bring one's own data), the
`24/7` trading calendar (`zipline.utils.calendar_utils.get_calendar`),
`zipline.run_algorithm` in daily mode, and inside the algorithm
`zipline.api` (`order`, `cancel_order`, `get_open_orders`, `get_order`,
`get_datetime`, `schedule_function`, `set_commission`, `set_slippage`) and the
`BarData` (`data.current`, `data.history`).

Zipline takes one kind of market data, OHLCV bars per asset per calendar
session, from a bundle written before the run. A bar whose close is
T0 + i DAY is the session of the day it covers (T0 + (i-1) DAY). The
bundle directory is a temporary directory in the scratchpad.
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import pandas as pd  # noqa: E402

from protocol import Adapter, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

_ROOT = tempfile.mkdtemp(prefix="zipline_root_")
os.environ["ZIPLINE_ROOT"] = _ROOT

import zipline  # noqa: E402
from zipline import api as Z  # noqa: E402
from zipline.data import bundles  # noqa: E402
from zipline.finance import commission as zcomm, slippage as zslip  # noqa: E402
from zipline.utils.calendar_utils import get_calendar  # noqa: E402

CAL = get_calendar("24/7")
DAY = 86_400 * 10**9


def _session(e: dict) -> pd.Timestamp:
    return pd.Timestamp(int(e["ts_ns"]) - DAY, unit="ns").normalize()


def run(bars: list[dict], handle, initialize=None, capital=1_000_000.0):
    """Write `bars` into a bundle and run. `handle(ctx, data, n)` is handle_data."""
    rows = [C.as_bar(b) for b in bars]
    idx = pd.DatetimeIndex([_session(b) for b in rows])
    df = pd.DataFrame({k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close")}, index=idx)
    df["volume"] = [float(b.get("volume", 1.0)) for b in rows]
    start, end = idx.min(), idx.max()
    name = "sk" + uuid.uuid4().hex[:8]

    def ingest(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar,
               start_session, end_session, cache, show_progress, output_dir):
        full = df.reindex(calendar.sessions_in_range(start, end))
        asset_db_writer.write(
            equities=pd.DataFrame({"symbol": ["X"], "asset_name": ["X"], "start_date": [start], "end_date": [end],
                                   "exchange": ["XX"]}),
            exchanges=pd.DataFrame({"exchange": ["XX"], "canonical_name": ["XX"], "country_code": ["US"]}))
        daily_bar_writer.write([(0, full)], show_progress=False)
        adjustment_writer.write()

    bundles.register(name, ingest, calendar_name="24/7", start_session=start - pd.Timedelta(days=1), end_session=end)
    bundles.ingest(name, os.environ, show_progress=False)
    state = {"n": 0, "log": []}

    def init(ctx):
        ctx.a = Z.symbol("X")
        ctx.st = state
        if initialize:
            initialize(ctx)

    def hd(ctx, data):
        state["n"] += 1
        handle(ctx, data, state["n"])

    res = zipline.run_algorithm(start=start, end=end, initialize=init, handle_data=hd, capital_base=capital,
                                data_frequency="daily", bundle=name, trading_calendar=CAL,
                                benchmark_returns=pd.Series(0.0, index=CAL.sessions_in_range(start, end).tz_localize("UTC")))
    return state, res


def _now():
    return int(Z.get_datetime().value)


def _no_kw(kw: str) -> str:
    try:
        zipline.run_algorithm(start=pd.Timestamp("2023-11-15"), end=pd.Timestamp("2023-11-16"), initialize=lambda c: None,
                              capital_base=1.0, **{kw: object()})
    except TypeError as exc:
        return f"run_algorithm(..., {kw}=...) -> TypeError: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"run_algorithm(..., {kw}=...) -> {type(exc).__name__}: {exc}"
    return f"run_algorithm(..., {kw}=...) は受け付けられた"


NON_BAR = ("zipline の入力は bundle に書いた資産ごとの OHLCV の足(日足・分足)だけで、{k} を入れる口が無い。"
           "試したこと: bundle の daily_bar_writer.write に {k} の列だけの DataFrame を渡した -> {err}")


def _try_non_bar(e: dict) -> str:
    try:
        from zipline.data.bcolz_daily_bars import BcolzDailyBarWriter
        d = tempfile.mkdtemp(prefix="zl_nonbar_")
        w = BcolzDailyBarWriter(os.path.join(d, "x.bcolz"), CAL, pd.Timestamp("2023-11-15"), pd.Timestamp("2023-11-15"))
        w.write([(0, pd.DataFrame([C.fields_of(e)], index=pd.DatetimeIndex([pd.Timestamp("2023-11-15")])))], show_progress=False)
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return "例外なく書けた"


class ZiplineReloadedAdapter(Adapter):
    name = "opp_zipline_reloaded"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        e = sc.input["streams"]["trades"][0]
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(e)))

    def _seq_run(self, bars):
        def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now()])
        st, _ = run(bars, h)
        return st["log"]

    def scene_p1_one_call_per_event(self, sc):
        return ok({"sequence": self._seq_run(C.events(sc))}, "日足 5 本を bundle に書き、handle_data の各回に get_datetime() を記録")

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    # ---------------- P0-2
    def _iso(self, sc):
        v = pd.Timestamp(sc.input["iso"]).tz_convert("UTC").value
        return ok(int(v), "zipline の時刻は pandas.Timestamp(get_datetime の型)。pd.Timestamp(iso).tz_convert('UTC').value")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        try:
            log = self._seq_run(evs)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ナノ秒の時刻の足を bundle に書いて走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": [t for _, t in log]}, "足で渡した(日足は暦の日に丸めて書かれる)。handle_data の get_datetime()")

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now()])
            out.update({k: float(data.current(ctx.a, k)) for k in ("open", "high", "low", "close")})
            out["volume"] = float(data.current(ctx.a, "volume"))

        st, _ = run([e], h)
        return ok({"sequence": st["log"], "fields": out}, "日足 1 本。data.current で読んだ")

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        e = [x for x in C.events(sc) if x["kind"] != "bar"][0]
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(e)))

    def scene_p3_clock_timer(self, sc):
        calls = []

        def initialize(ctx):
            Z.schedule_function(lambda c, d: calls.append(_now()), Z.date_rules.every_day(), Z.time_rules.market_open())

        run([C.as_bar(e) for e in C.events(sc)], lambda c, d, n: None, initialize)
        return ok({"clock_calls_ns": calls}, "schedule_function は暦の規則(毎日・毎週…と寄り付きからの分)で頼む形で、"
                  "決まった時刻を 1 回だけ頼む口は無い。毎日の規則で頼み、呼ばれた時刻を全部記録した")

    def _notice(self, sc):
        return not_supported("注文の受付・拒否・約定を戦略に知らせる呼び出しが無い(戦略は get_order / get_open_orders で問い合わせる)。"
                             "試したこと: " + _no_kw("on_order") + " / " + _no_kw("order_callback"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    # ---------------- P0-4
    def scene_p4_visible_at_step(self, sc):
        probe = sc.input["probe_at_ns"]
        out, seen, tried = {}, [], []

        def h(ctx, data, n):
            seen.append(float(data.current(ctx.a, "close")))
            if _now() == probe:
                try:
                    hist = list(data.history(ctx.a, "close", n, "1d"))
                    tried.append(f"data.history(n={n}) -> {hist}")
                except Exception as exc:  # noqa: BLE001
                    tried.append(f"data.history(n={n}) -> {type(exc).__name__}: {str(exc)[:100]}")
                vis = [x for x in seen if x == x]
                out["visible_count"] = len(vis)
                out["max_visible_close"] = max(vis) if vis else None

        run(C.events(sc), h)
        if not out:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)")
        return ok(out, f"戦略が各回に data.current(asset,'close') を読んで貯めた(NaN は数えない)。各回の値 {seen}。{tried}。"
                  "24/7 の暦では 1 日の終わりと次の日の始まりが同じ 0 時で、data.current は 1 回目に NaN、以後 1 日前の足を返した(実測)")

    def scene_p4_received_time(self, sc):
        return not_supported("足は暦の日に 1 本で、1 本に時刻は 1 つ。受け取れる時刻を別に持たせる口が無い。試したこと: "
                             + _no_kw("received_time") + " / bundle の足に recv の列を足す -> "
                             + _try_non_bar({"open": 1, "high": 1, "low": 1, "close": 1, "volume": 1, "recv_ns": 1}))

    def scene_p4_future_read_attempt(self, sc):
        probe = sc.input["probe_at_ns"]
        tried, got = [], {"v": False}

        def h(ctx, data, n):
            if _now() != probe:
                return
            nxt = pd.Timestamp(int([e for e in sc.input["events"] if e["ts_ns"] > probe][0]["ts_ns"]) - DAY, unit="ns").tz_localize("UTC")
            for label, fn in [("data.history(asset,'close',6,'1d')", lambda: list(data.history(ctx.a, "close", 6, "1d"))),
                              ("data.current(asset,'close')", lambda: data.current(ctx.a, "close")),
                              ("data_portal.get_spot_value(5 本目の日)", lambda: ctx.data_portal.get_spot_value(ctx.a, "close", nxt, "daily")),
                              ("data.history の窓を 5 本目の日まで伸ばす", lambda: list(ctx.data_portal.get_history_window([ctx.a], nxt, 1, "1d", "close", "daily")[ctx.a]))]:
                try:
                    v = fn()
                    tried.append(f"{label} -> {v}")
                    if (isinstance(v, list) and 104.0 in v) or v == 104.0:
                        got["v"] = True
                except Exception as exc:  # noqa: BLE001
                    tried.append(f"{label} -> {type(exc).__name__}: {str(exc)[:80]}")

        run(C.events(sc), h)
        if not tried:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)ので、先を読む試しができなかった")
        return ok({"future_value_obtained": got["v"]}, f"T0 + 4 日の呼び出しに試した: " + " ; ".join(tried))

    # ---------------- P0-5
    def _no_types(self, sc):
        e = sc.input["streams"]["trades"][0]
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(e)))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]
        try:
            run(rows, lambda c, d, n: None)
        except Exception as exc:  # noqa: BLE001
            return not_supported("同じ日に 2 本の足を書く口が無い(日足は 1 日 1 本)。試したこと: 同じ日の 2 本を bundle に書いて走らせた -> "
                                 f"{type(exc).__name__}: {str(exc)[:200]}")
        return ok({"prices": []}, "同じ日の 2 本を書いて走らせたが例外は出なかった")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out = {}

        def h(ctx, data, n):
            if n == 1:
                ctx.oid = Z.order(ctx.a, 1, limit_price=90.0)
            elif n == 2:
                out["open_at_call2"] = sum(len(v) for v in Z.get_open_orders().values())
                Z.cancel_order(ctx.oid)
            elif n == 3:
                out["open_at_call3"] = sum(len(v) for v in Z.get_open_orders().values())

        run([C.as_bar(e) for e in C.events(sc)], h)
        return ok(out, "約定を日足に代えた(any_type)。order(limit_price=90) / get_open_orders / cancel_order")

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消の成立を戦略に知らせる呼び出しが無い。試したこと: " + _no_kw("on_cancel"))

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        def h(ctx, data, n):
            if n == 1:
                ctx.oid = Z.order(ctx.a, 1)
            elif n == 3:
                out["filled_qty_at_call3"] = float(Z.get_order(ctx.oid).filled)

        run([C.as_bar(e) for e in C.events(sc)], h)
        return ok(out, "3 回目に get_order(id).filled")

    # ---------------- P0-7
    def _buy(self, sc, init):
        fills = []

        def h(ctx, data, n):
            if n == 1:
                ctx.oid = Z.order(ctx.a, 1)

        st, res = run([C.as_bar(e) for e in C.events(sc)], h, init, capital=100_000.0)
        for day in res["transactions"]:
            fills.extend(day)
        orders = [o for day in res["orders"] for o in day]
        return fills, orders

    def scene_p7_fill_model_swap(self, sc):
        class Fixed(zslip.SlippageModel):
            def process_order(self, data, order):
                return 12345.0, order.amount

        fills, _ = self._buy(sc, lambda ctx: Z.set_slippage(us_equities=Fixed()))
        return ok({"fill_price": float(fills[0]["price"]) if fills else None},
                  f"set_slippage(SlippageModel の子: process_order が (12345.0, 全量) を返す)。transactions: {fills}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("発注の遅延の模型を渡す口が無い(日足・分足の次の足で埋める)。試したこと: " + _no_kw("latency_model"))

    def _fee(self, sc, fee):
        class Flat(zcomm.CommissionModel):
            def calculate(self, order, transaction):
                return 0.0 if order.commission else fee

        fills, orders = self._buy(sc, lambda ctx: (Z.set_commission(us_equities=Flat()),
                                                    Z.set_slippage(us_equities=zslip.NoSlippage())))
        comm = [o["commission"] for o in orders if o.get("filled")]
        return ok({"fee": float(comm[-1]) if comm else None}, f"set_commission(CommissionModel の子: 1 件 {fee})。orders: {orders}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_zero(self, sc):
        return self._fee(sc, 0.0)

    def scene_p7_account_swap(self, sc):
        return not_supported("口座(Portfolio / Ledger)は run_algorithm の中で作られ、差し替える口が無い。試したこと: "
                             + _no_kw("ledger") + " / " + _no_kw("portfolio"))
