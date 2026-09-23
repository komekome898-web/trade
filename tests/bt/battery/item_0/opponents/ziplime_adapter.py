"""Survey candidate `ziplime` (PyPI `ziplime`), run in its own venv (Python 3.12).

Driven through its public API: `ziplime.core.ingest_data.get_asset_service`
(a temporary sqlite asset db in the scratchpad), `ziplime.core.run_simulation.
run_simulation` with the `24/7` calendar and daily emission, a market data
source that is a `ziplime.data.services.data_source.DataSource` holding a
polars DataFrame (date / sid / open / high / low / close / price / volume),
and an algorithm file whose `initialize` / `handle_data` forward to this
adapter. Inside the algorithm: `context.symbol`, `context.order`,
`context.cancel_order`, `context.get_open_orders`, `context.get_order`,
`context.get_datetime`, `context.add_event`, `data.current`, `data.history`.

ziplime (a fork of zipline) takes OHLCV bars per asset. A bar whose close is
T0 + i DAY is written as the row dated T0 + (i-1) DAY (the day it covers).

Getting a run to start needed three things found by running it (the attempt
log is in `opponents/CONSIDERED.md`): the equity must carry an `isin` and no
preset `id` (`save_exchange_assets` looks equities up by (isin, asset_name)),
a benchmark symbol given as `X@LIME` (with no benchmark `validate_benchmark`
is called on None), and the data source's `end_date` must lie after the last
simulated session (otherwise it calls `get_missing_data_by_limit`, which the
base class does not have).
"""
from __future__ import annotations

import asyncio
import datetime as D
import os
import sys
import tempfile
import types
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import logging  # noqa: E402

import polars as pl  # noqa: E402

from protocol import Adapter, SceneResult, not_supported, ok  # noqa: E402
import common as C  # noqa: E402

logging.disable(logging.CRITICAL)
import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))

from ziplime.assets.domain.asset_type import AssetType  # noqa: E402
from ziplime.assets.entities.asset_symbol import AssetSymbol  # noqa: E402
from ziplime.assets.entities.equity import Equity  # noqa: E402
from ziplime.assets.entities.exchange_asset import ExchangeAsset  # noqa: E402
from ziplime.assets.entities.exchange_info import ExchangeInfo  # noqa: E402
from ziplime.constants.data_type import DataType  # noqa: E402
from ziplime.core.ingest_data import get_asset_service  # noqa: E402
from ziplime.core.run_simulation import run_simulation  # noqa: E402
from ziplime.data.services.data_source import DataSource  # noqa: E402
from ziplime.exchanges.simulation_exchange import SimulationExchange  # noqa: E402
from ziplime.finance.commission.equity_commission_model import EquityCommissionModel  # noqa: E402
from ziplime.finance.execution import LimitOrder, MarketOrder  # noqa: E402
from ziplime.finance.slippage.equity_slippage_model import EquitySlippageModel  # noqa: E402
from ziplime.finance.slippage.fixed_basis_points_slippage import FixedBasisPointsSlippage  # noqa: E402
from ziplime.utils.events import EventRule  # noqa: E402

DAY = 86_400 * 10**9
TWO = "SimulationClock は 2 日以上の区間を要する(simulation_clock.py 33 行)ので、足が 1 日に収まる場面は 1 日多く走らせた"
_ROOT = tempfile.mkdtemp(prefix="ziplime_sk_")
_HOOKS = types.ModuleType("_zl_hooks")
sys.modules["_zl_hooks"] = _HOOKS
_ALGO = os.path.join(_ROOT, "algo.py")
with open(_ALGO, "w") as f:
    f.write("import sys\nH = sys.modules['_zl_hooks']\n"
            "async def initialize(context):\n    await H.initialize(context)\n"
            "async def handle_data(context, data):\n    await H.handle_data(context, data)\n")


def _utc(ns: int) -> D.datetime:
    return C.ns_to_dt(ns)


def _now(ctx) -> int:
    return C.dt_to_ns(ctx.get_datetime())


def run(bars, handle, initialize=None, capital=1_000_000.0, ns_dates=False, label="start", **sim_kw):
    """Run `bars` (dicts with ts_ns / OHLC / volume). `handle(ctx, data, n)` is an
    async function called from handle_data; `initialize(ctx)` an async one.

    label="start": a row is dated with the day the bar covers (ts - DAY), the
    usual daily-bar label. label="close": a row is dated with the bar's close
    time (ts). The simulated sessions are the same in both: from the first
    bar's day to the last bar's day; ziplime's SimulationClock needs at least
    two sessions, so a run whose bars all fall on one day gets one more session.
    A second asset "B" with a row on every session is the benchmark (ziplime
    validates a benchmark asset even when none is wanted, and its benchmark
    metric indexes one benchmark row per session)."""
    rows = [C.as_bar(b) for b in bars]
    d = tempfile.mkdtemp(prefix="run_", dir=_ROOT)
    state = {"n": 0, "log": [], "calls_ns": []}

    async def main():
        svc = get_asset_service(db_path=os.path.join(d, "assets.sqlite"), clear_asset_db=True)
        ex = ExchangeInfo(mic="LIME", name="LIME", canonical_name="LIME", country_code="US")
        await svc.save_exchanges([ex])
        eq = Equity(id=None, isin="XX0000000001", asset_name="X", start_date=D.date(2020, 1, 1),
                    end_date=D.date(2030, 1, 1), first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1))
        await svc.save_exchange_assets([ExchangeAsset(
            sid=None, symbol="X", start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1),
            first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1), external_id="X", exchange=ex, asset=eq)])
        beq = Equity(id=None, isin="XX0000000002", asset_name="B", start_date=D.date(2020, 1, 1),
                     end_date=D.date(2030, 1, 1), first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1))
        await svc.save_exchange_assets([ExchangeAsset(
            sid=None, symbol="B", start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1),
            first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1), external_id="B", exchange=ex, asset=beq)])
        a = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="X", mic="LIME"), asset_type=AssetType.EQUITY)
        b_ = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="B", mic="LIME"), asset_type=AssetType.EQUITY)
        days = [(int(b["ts_ns"]) - DAY) // DAY * DAY for b in rows]
        stamps = [int(b["ts_ns"]) - (DAY if label == "start" else 0) for b in rows]
        date = pl.Series("date", stamps, dtype=pl.Int64).cast(pl.Datetime("ns", "UTC")) if ns_dates else \
            pl.Series("date", [_utc(s) for s in stamps]).cast(pl.Datetime("ns", "UTC"))
        df = pl.DataFrame({"date": date, "sid": [a.sid] * len(rows),
                           **{k: [float(b[k]) for b in rows] for k in ("open", "high", "low", "close")},
                           "price": [float(b["close"]) for b in rows],
                           "volume": [float(b.get("volume", 1.0)) for b in rows]})
        first, last = _utc(min(days)), _utc(max(days))
        if last <= first:
            last = first + D.timedelta(days=1)
        state["sessions"] = [C.dt_to_ns(first), C.dt_to_ns(last)]
        bdays = [first + D.timedelta(days=i) for i in range(0, (last - first).days + 1)]
        bdf = pl.DataFrame({"date": pl.Series("date", bdays).cast(pl.Datetime("ns", "UTC")), "sid": [b_.sid] * len(bdays),
                            **{k: [1.0] * len(bdays) for k in ("open", "high", "low", "close", "price")},
                            "volume": [1.0] * len(bdays)})
        df = pl.concat([df, bdf])

        class Mem(DataSource):
            def __init__(self):
                super().__init__(name="mem", start_date=first, end_date=last + D.timedelta(days=30),
                                 frequency=D.timedelta(days=1), original_frequency=D.timedelta(days=1),
                                 data_type=DataType.MARKET_DATA)
                self.data = df

            def get_dataframe(self):
                return self.data

        async def init(ctx):
            ctx.a = await ctx.symbol("X")
            ctx.st = state
            if initialize:
                await initialize(ctx)

        async def hd(ctx, data):
            state["n"] += 1
            state["calls_ns"].append(_now(ctx))
            await handle(ctx, data, state["n"])

        _HOOKS.initialize, _HOOKS.handle_data = init, hd
        kw = dict(start_date=first, end_date=last, trading_calendar="24/7", emission_rate=D.timedelta(days=1),
                  total_cash=capital, market_data_source=Mem(), custom_data_sources=[], algorithm_file=_ALGO,
                  stop_on_error=True, asset_service=svc, benchmark_asset_symbol="B@LIME")
        if "exchange" in sim_kw:
            from ziplime.gens.domain.simulation_clock import SimulationClock
            from ziplime.utils.calendar_utils import get_calendar
            clock = SimulationClock(trading_calendar=get_calendar("24/7"), start_date=first, end_date=last,
                                    emission_rate=D.timedelta(days=1))
            kw["clock"] = clock
            kw["exchange"] = sim_kw.pop("exchange")(kw["market_data_source"], capital, clock)
        kw.update(sim_kw)
        state["result"] = await run_simulation(**kw)

    asyncio.run(main())
    return state


async def _close(ctx, data) -> float:
    df = await data.current(assets=[ctx.a], fields=["close"])
    v = df["close"].to_list()
    return float(v[0]) if v and v[0] is not None else float("nan")


def _no_kw(kw: str) -> str:
    try:
        asyncio.run(run_simulation(**{kw: object()}))  # type: ignore[call-arg]
    except TypeError as exc:
        return f"run_simulation(..., {kw}=...) -> TypeError: {str(exc)[:140]}"
    except Exception as exc:  # noqa: BLE001
        return f"run_simulation(..., {kw}=...) -> {type(exc).__name__}: {str(exc)[:140]}"
    return f"run_simulation(..., {kw}=...) は受け付けられた"


def _try_non_bar(e: dict) -> str:
    """Hand a DataFrame with only the non-bar event's columns to a run."""
    try:
        cols = C.fields_of(e)
        df = pl.DataFrame({"date": [_utc(int(e["ts_ns"]))], "sid": [1],
                           **{k: [v if not isinstance(v, list) else str(v)] for k, v in cols.items()}})

        async def go():
            svc = get_asset_service(db_path=os.path.join(tempfile.mkdtemp(dir=_ROOT), "a.sqlite"), clear_asset_db=True)

            class Mem(DataSource):
                def __init__(self):
                    super().__init__(name="m", start_date=_utc(int(e["ts_ns"])), end_date=_utc(int(e["ts_ns"]) + 30 * DAY),
                                     frequency=D.timedelta(days=1), original_frequency=D.timedelta(days=1),
                                     data_type=DataType.MARKET_DATA)
                    self.data = df

            _HOOKS.initialize = _noop_init
            _HOOKS.handle_data = _noop_hd
            await run_simulation(start_date=_utc(int(e["ts_ns"])), end_date=_utc(int(e["ts_ns"]) + DAY), trading_calendar="24/7",
                                 emission_rate=D.timedelta(days=1), total_cash=1.0, market_data_source=Mem(), custom_data_sources=[],
                                 algorithm_file=_ALGO, stop_on_error=True, asset_service=svc)
        asyncio.run(go())
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return "例外なく走った"


async def _noop_init(ctx):
    return None


async def _noop_hd(ctx, data):
    return None


NON_BAR = ("ziplime の市場データは資産ごとの OHLCV の足(market_data_source の DataFrame の date/sid/open/high/low/close/"
           "price/volume)で、{k} を型として戦略に渡す口が無い(DataType は MARKET_DATA と CUSTOM の 2 つ)。"
           "試したこと: {k} の列だけの DataFrame を market_data_source にして run_simulation -> {err}")


async def _open_count(ctx) -> int:
    return sum(len(v) for v in ctx.get_open_orders().values())


class ZiplimeAdapter(Adapter):
    name = "opp_ziplime"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def _seq(self, bars, **kw):
        async def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now(ctx)])
        return run(bars, h, **kw)["log"]

    def scene_p1_one_call_per_event(self, sc):
        return ok({"sequence": self._seq(C.events(sc))}, "日足 5 本を渡し、handle_data の各回に context.get_datetime() を記録")

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    # ---------------- P0-2
    def _iso(self, sc):
        v = pl.Series([sc.input["iso"]]).str.to_datetime(time_unit="ns", time_zone="UTC")
        return ok(int(v.cast(pl.Int64)[0]), "ziplime のデータの日時は polars の Datetime。"
                  "pl.Series([iso]).str.to_datetime(time_unit='ns', time_zone='UTC') を整数にした")

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        try:
            log = self._seq(evs, ns_dates=True)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ナノ秒の時刻の足(polars Datetime ns)を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": [t for _, t in log]},
                  "足を polars の Datetime('ns') で渡した。handle_data の context.get_datetime()(呼び出しは暦の日ごと)。" + TWO)

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}

        async def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now(ctx)])
            df = await data.current(assets=[ctx.a], fields=["open", "high", "low", "close", "volume"])
            out.update({k: float(df[k][0]) for k in ("open", "high", "low", "close", "volume") if len(df)})

        st = run([e], h)
        return ok({"sequence": st["log"], "fields": out}, "日足 1 本。data.current で読んだ。" + TWO)

    scene_p3_trade = scene_p3_book_snapshot = scene_p3_book_delta = _type
    scene_p3_bar = scene_p3_funding = scene_p3_liquidation = _type

    def scene_p3_mixed_one_run(self, sc):
        e = [x for x in C.events(sc) if x["kind"] != "bar"][0]
        return not_supported(NON_BAR.format(k="足以外の 5 種", err=_try_non_bar(e)))

    def scene_p3_clock_timer(self, sc):
        target = int(sc.input["timer_at_ns"])
        calls = []

        class At(EventRule):
            def should_trigger(self, dt):
                return C.dt_to_ns(dt) == target

        async def cb(ctx, data):
            calls.append(_now(ctx))

        async def h(ctx, data, n):
            if n == 1:
                ctx.add_event(At(), cb)

        st = run([C.as_bar(e) for e in C.events(sc)], h)
        return ok({"clock_calls_ns": calls}, "1 回目の呼び出しで context.add_event(EventRule の子: should_trigger が "
                  f"dt == T0+4 日, 呼び戻し) を頼んだ。handle_data の時刻 {st['calls_ns']}")

    def _notice(self, sc):
        return not_supported("注文の受付・拒否・約定を戦略に知らせる呼び出しが無い(戦略は get_order / get_open_orders で問い合わせる。"
                             "algorithm file から読む関数は initialize / handle_data / before_trading_start / analyze)。"
                             "試したこと: " + _no_kw("on_order") + " / " + _no_kw("order_callback"))

    scene_p3_notice_accepted = scene_p3_notice_rejected = scene_p3_notice_filled = _notice

    # ---------------- P0-4
    def _visible(self, sc, label):
        probe = sc.input["probe_at_ns"]
        out, seen, tried = {}, [], []

        async def h(ctx, data, n):
            seen.append(await _close(ctx, data))
            if _now(ctx) == probe:
                try:
                    hist = (await data.history(assets=[ctx.a], bar_count=10, fields=["close"]))["close"].to_list()
                    tried.append(f"data.history(bar_count=10) -> {hist}")
                except Exception as exc:  # noqa: BLE001
                    tried.append(f"data.history(bar_count=10) -> {type(exc).__name__}: {str(exc)[:100]}")
                vis = [x for x in seen if x == x]
                out["visible_count"] = len(vis)
                out["max_visible_close"] = max(vis) if vis else None

        st = run(C.events(sc), h, label=label)
        return out, f"日付={label}: 各回の data.current(close) {seen}、呼び出しの時刻 {st['calls_ns']}、{tried}"

    def scene_p4_visible_at_step(self, sc):
        res = {lab: self._visible(sc, lab) for lab in ("start", "close")}
        got = [r for r in res.values() if r[0]]
        if not got:  # no_probe_call
            return not_supported(f"T0 + 4 日の呼び出しが無かった(対象がその時刻に戦略を呼ばない)。{res}")
        best = min(got, key=lambda r: (r[0]["max_visible_close"] is None, r[0]["max_visible_close"] or 0))
        return ok(best[0], "戦略が各回に data.current(close) を読んで貯めた(NaN は数えない)。足の日付を 2 通りで渡した"
                  "(start = 足が覆う日、ziplime の日足の通常の付け方 / close = 足の終わりの時刻)。先の値が見えにくい方を結果にした。"
                  + " / ".join(r[1] for r in res.values()))

    def scene_p4_received_time(self, sc):
        return not_supported("足は 1 本に時刻 1 つ(date の列)で、受け取れる時刻を別に持たせる口が無い。試したこと: "
                             + _no_kw("received_time") + " / 足に recv の列を足して渡す -> "
                             + _try_non_bar({"ts_ns": sc.input["events"][0]["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0,
                                             "close": 1.0, "volume": 1.0, "recv_ns": 1}))

    def _future(self, sc, label):
        probe = sc.input["probe_at_ns"]
        nxt_ns = [e for e in sc.input["events"] if e["ts_ns"] > probe][0]["ts_ns"]
        tried, got = [], {"v": False}

        async def h(ctx, data, n):
            if _now(ctx) != probe:
                return
            ex = await ctx.exchange_repository.get_default_exchange()
            for label, fn in [
                ("data.history(bar_count=6)", lambda: data.history(assets=[ctx.a], bar_count=6, fields=["close"])),
                ("data.current(close)", lambda: data.current(assets=[ctx.a], fields=["close"])),
                ("exchange.get_spot_value(dt=5 本目の日)", lambda: ex.get_spot_value(assets=frozenset({ctx.a}), fields=frozenset({"close"}),
                                                                             dt=_utc(nxt_ns), data_frequency=D.timedelta(days=1))),
                ("exchange.get_data_by_limit(end_date=5 本目の日)", lambda: ex.get_data_by_limit(
                    fields=frozenset({"close"}), limit=6, end_date=_utc(nxt_ns), frequency=D.timedelta(days=1),
                    assets=frozenset({ctx.a}), include_end_date=True)),
            ]:
                try:
                    v = await fn()
                    vals = v["close"].to_list() if hasattr(v, "columns") and "close" in v.columns else v
                    tried.append(f"{label} -> {vals}")
                    if isinstance(vals, list) and 104.0 in vals:
                        got["v"] = True
                except Exception as exc:  # noqa: BLE001
                    tried.append(f"{label} -> {type(exc).__name__}: {str(exc)[:80]}")

        run(C.events(sc), h, label=label)
        return got["v"], tried

    def scene_p4_future_read_attempt(self, sc):
        res = {lab: self._future(sc, lab) for lab in ("start", "close")}
        if not any(r[1] for r in res.values()):  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かったので、先を読む試しができなかった")
        best = min(r[0] for r in res.values() if r[1])
        return ok({"future_value_obtained": best}, "T0 + 4 日の呼び出しに試した(足の日付を 2 通り、良い方を結果にした): "
                  + " / ".join(f"日付={k}: " + " ; ".join(v[1]) for k, v in res.items()))

    # ---------------- P0-5
    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]
        seen = []

        async def h(ctx, data, n):
            df = await data.current(assets=[ctx.a], fields=["close"])
            seen.append(df["close"].to_list())

        try:
            st = run(rows, h)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 2 本を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        flat = [float(x) for v in seen for x in v if x is not None]
        return ok({"prices": flat}, TWO + f"。同じ時刻の 2 本(終値 100 と 101)を渡した。各回の data.current(close) {seen}、呼び出し {st['calls_ns']}")

    # ---------------- P0-6
    def scene_p6_place_then_cancel(self, sc):
        out, errs = {}, []

        async def h(ctx, data, n):
            if n == 1:
                ctx.o = await ctx.order(ctx.a, 1, style=LimitOrder(90.0))
            elif n == 2:
                out["open_at_call2"] = await _open_count(ctx)
                try:
                    await ctx.cancel_order(ctx.o.id, "LIME")
                except Exception as exc:  # noqa: BLE001
                    errs.append(f"cancel_order(id, 'LIME') -> {type(exc).__name__}: {str(exc)[:160]}")
            elif n == 3:
                out["open_at_call3"] = await _open_count(ctx)

        try:
            run([C.as_bar(e) for e in C.events(sc)], h)
        except Exception as exc:  # noqa: BLE001
            return SceneResult("error", output=out, detail=(
                "取消のあと、走行が止まった。context.cancel_order は blotter.order_cancelled を呼び、これが未決の注文の辞書を"
                "資産ではなく資産の番号(order.asset.sid)で引くので(in_memory_blotter.py 74 行、登録は 69 行で資産で引く)、"
                "辞書に番号の鍵が足され、次の足で SimulationExchange.get_transactions が番号を資産として扱って落ちた。"
                f"取消の呼び出しで起きたこと: {errs or 'なし'}。走行の例外: {type(exc).__name__}: {str(exc)[:160]}。"
                f"それまでに記録した値: {out}"))
        return ok(out, "約定を日足に代えた(any_type)。order(style=LimitOrder(90)) / get_open_orders / cancel_order。"
                  f"取消の呼び出しで起きたこと: {errs or 'なし'}")

    def scene_p6_cancel_notice(self, sc):
        return not_supported("取消の成立を戦略に知らせる呼び出しが無い。試したこと: " + _no_kw("on_cancel"))

    def scene_p6_fill_seen_by_strategy(self, sc):
        out = {}

        async def h(ctx, data, n):
            if n == 1:
                ctx.o = await ctx.order(ctx.a, 1, style=MarketOrder())
            elif n == 3:
                out["filled_qty_at_call3"] = float(ctx.get_order(ctx.o.id, "LIME").filled)

        run([C.as_bar(e) for e in C.events(sc)], h)
        return ok(out, "3 回目に get_order(id, 'LIME').filled")

    # ---------------- P0-7
    def _buy(self, sc, capital=100_000.0, **kw):
        out = {}

        async def h(ctx, data, n):
            if n == 1:
                ctx.o = await ctx.order(ctx.a, 1, style=MarketOrder())
            o = ctx.get_order(ctx.o.id, "LIME")
            pos = ctx.portfolio.positions.get("LIME", {}).get("simulation_account", {}).get(ctx.a)
            out.update({"filled": float(o.filled), "commission": float(o.commission), "n": n,
                        "cost_basis": float(pos.cost_basis) if pos is not None else None})

        st = run([C.as_bar(e) for e in C.events(sc)], h, capital=capital, **kw)
        return out, st

    @staticmethod
    def _exchange(slippage=None, commission=None, cls=SimulationExchange):
        from ziplime.finance.commission.per_contract import PerContract
        from ziplime.finance.slippage.volatility_volume_share import VolatilityVolumeShare
        from ziplime.utils.calendar_utils import get_calendar

        def make(src, capital, clock):
            return cls(name="LIME", country_code="US", trading_calendar=get_calendar("24/7"), data_source=src,
                       equity_slippage=slippage or FixedBasisPointsSlippage(), equity_commission=commission or _Flat(0.0),
                       future_slippage=VolatilityVolumeShare(volume_limit=0.05), future_commission=PerContract(cost=0.85, exchange_fee=0.0, min_trade_cost=0.0),
                       cash_balance=capital, clock=clock, price_used_in_order_execution="close",
                       account_id="simulation_account", is_default=True)
        return make

    def scene_p7_fill_model_swap(self, sc):
        class Fixed(EquitySlippageModel):
            async def process_order(self, exchange, dt, order, price=None):
                return 12345.0, order.amount

        prices = []

        class Rec(SimulationExchange):
            async def get_transactions(self, orders, current_dt, same_bar_execution):
                t, c, closed = await super().get_transactions(orders, current_dt, same_bar_execution)
                prices.extend(float(x.price) for x in t)
                return t, c, closed

        via_param, _ = self._buy(sc, equity_slippage=Fixed(), equity_commission=_Flat(0.0))
        out, _ = self._buy(sc, exchange=self._exchange(slippage=Fixed(), cls=Rec))
        return ok({"fill_price": prices[0] if prices else None},
                  "run_simulation(equity_slippage=<process_order が (12345.0, 全量) を返す子>) の引数では、戦略が読んだ建玉の取得単価 "
                  f"{via_param.get('cost_basis')}(run_simulation.py はこの引数を SimulationExchange に渡さず FixedBasisPointsSlippage() を渡す)。"
                  "run_simulation(exchange=SimulationExchange(equity_slippage=<同じ子>)) で差し込んだ。"
                  f"約定の価格は Exchange.get_transactions の返り値 {prices}、戦略が読んだ取得単価 {out.get('cost_basis')}")

    def scene_p7_latency_model_swap(self, sc):
        return not_supported("発注の遅延の模型を渡す口が無い(注文は足の処理の中で埋める。run_simulation の same_bar_execution は同じ足か次の足かの切り替えだけ)。試したこと: " + _no_kw("latency_model"))

    def _fee(self, sc, fee):
        out, _ = self._buy(sc, equity_commission=_Flat(fee))
        return ok({"fee": out.get("commission")}, f"run_simulation(equity_commission=<EquityCommissionModel の子: 1 件 {fee}>)。"
                  f"最後の呼び出しの get_order: {out}")

    def scene_p7_cost_model_swap(self, sc):
        return self._fee(sc, 0.5)

    def scene_p7_cost_zero(self, sc):
        return self._fee(sc, 0.0)

    def scene_p7_account_swap(self, sc):
        rec = []

        class RecExchange(SimulationExchange):
            async def get_transactions(self, orders, current_dt, same_bar_execution):
                t, c, closed = await super().get_transactions(orders, current_dt, same_bar_execution)
                rec.extend(float(x.amount) for x in t)
                return t, c, closed

        self._buy(sc, exchange=self._exchange(cls=RecExchange))
        return ok({"account_recorded_fill_qty": rec}, "run_simulation(exchange=<SimulationExchange の子>)。ziplime の Exchange は"
                  "口座(cash_balance / get_account / get_positions)と約定を 1 つで持つ。子の get_transactions で約定の数量を記録した")


class _Flat(EquityCommissionModel):
    def __init__(self, fee: float):
        super().__init__()
        self.fee = fee

    def calculate(self, order, transaction):
        return 0.0 if order.commission else self.fee

    def calculate_for_asset(self, asset, quantity, transaction_amount):
        return self.fee
