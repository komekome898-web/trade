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


# round r8-1: the configured target's fixed window (common.FIXED_WINDOW) as aware datetimes, for the trials
_W0 = D.datetime.fromisoformat(C.FIXED_WINDOW[0]).replace(tzinfo=D.timezone.utc)
_W1 = D.datetime.fromisoformat(C.FIXED_WINDOW[1]).replace(tzinfo=D.timezone.utc)


def _utc(ns: int) -> D.datetime:
    return C.ns_to_dt(ns)


def _now(ctx) -> int:
    return C.dt_to_ns(ctx.get_datetime())


_CHOSEN = {"label": "start"}  # the configured target's chosen bar-date convention (round r8-1); set by the adapter


def run(bars, handle, initialize=None, capital=1_000_000.0, ns_dates=True, label=None, **sim_kw):
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
    label = _CHOSEN["label"] if label is None else label
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
        del days
        # round r8-1 (positive definition A): the simulated sessions are the configured target's chosen window, the same
        # in every scene (until round r8-1: the scene's first and last bar day, a setting fitted to input not yet delivered)
        first = D.datetime.fromisoformat(C.FIXED_WINDOW[0]).replace(tzinfo=D.timezone.utc)
        last = D.datetime.fromisoformat(C.FIXED_WINDOW[1]).replace(tzinfo=D.timezone.utc)
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
        plugs = sorted(set(sim_kw) | ({"exchange", "clock"} & set(kw)))
        state["result"] = await C.configure(run_simulation, **kw,
                                            what=f"run_simulation(start_date={first.date()}, end_date={last.date()}, trading_calendar 24/7, "
                                                 f"emission_rate 1 日, total_cash={capital}, market_data_source=場面の足, "
                                                 f"benchmark B{', ' + ', '.join(plugs) if plugs else ''})",
                                            decided_from=("選ぶ値", "場面の入力"))

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
                    # round r8-1: the trial uses the same fixed window as every run (not the event's own day)
                    super().__init__(name="m", start_date=_W0, end_date=_W1 + D.timedelta(days=30),
                                     frequency=D.timedelta(days=1), original_frequency=D.timedelta(days=1),
                                     data_type=DataType.MARKET_DATA)
                    self.data = df

            _HOOKS.initialize = _noop_init
            _HOOKS.handle_data = _noop_hd
            await run_simulation(start_date=_W0, end_date=_W1, trading_calendar="24/7",
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
    # round r8-1 (positive definition A): the values this configured target chooses, the same in every scene. The
    # bar-date convention is one of two (start = the day a bar covers, ziplime's usual daily label / close = the
    # bar's close time), each its own configured target; the window is fixed.
    CONFIGS = {"label=start": {"label": "start", "window": list(C.FIXED_WINDOW), "calendar": "24/7", "emission_rate": "1 日",
                               "date_column": "ns"},
               "label=close": {"label": "close", "window": list(C.FIXED_WINDOW), "calendar": "24/7", "emission_rate": "1 日",
                               "date_column": "ns"}}

    def __init__(self, config: str = "label=start") -> None:
        super().__init__(config or "label=start")
        _CHOSEN["label"] = self.choose["label"]
    name = "opp_ziplime"

    # ---------------- P0-1
    def scene_p1_merge_by_time(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    def _seq(self, bars, **kw):
        car = []

        async def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now(ctx)])
            car.append(C.carrier(data))
        return run(bars, h, **kw)["log"], car

    def scene_p1_one_call_per_event(self, sc):
        log, car = self._seq(C.events(sc))
        return ok({"sequence": log}, "日足 5 本を渡し、handle_data の各回に context.get_datetime() を記録", {"carriers": car})

    def scene_p1_typed_events(self, sc):
        return not_supported(NON_BAR.format(k="約定", err=_try_non_bar(C.events(sc)[1])))

    # ---------------- P0-2
    def _iso(self, sc):
        """The ISO string written as it is into a CSV read by ziplime's own CSVDataSource (its reader
        parses the date column with the date_format it is given; both ISO forms of the format are tried)."""
        from ziplime.data.services.csv_data_source import CSVDataSource
        from ziplime.utils.calendar_utils import get_calendar
        iso = sc.input["iso"]
        d = tempfile.mkdtemp(prefix="iso_", dir=_ROOT)
        path = os.path.join(d, "x.csv")
        Path(path).write_text("date,symbol,open,high,low,close,volume\n"
                              + "".join(f"{iso.replace('-01T', f'-0{i}T')},X,1,1,1,1,1\n" for i in (1, 2, 3)), encoding="utf-8")
        tried = {}

        async def main():
            svc = get_asset_service(db_path=os.path.join(d, "assets.sqlite"), clear_asset_db=True)
            ex = ExchangeInfo(mic="XNGS", name="XNGS", canonical_name="XNGS", country_code="US")  # the CSV reader looks symbols up on XNGS
            await svc.save_exchanges([ex])
            eq = Equity(id=None, isin="XX0000000001", asset_name="X", start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1),
                        first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1))
            await svc.save_exchange_assets([ExchangeAsset(
                sid=None, symbol="X", start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1), first_traded=D.date(2020, 1, 1),
                auto_close_date=D.date(2030, 1, 1), external_id="X", exchange=ex, asset=eq)])
            for fmt in ("%Y-%m-%dT%H:%M:%S%.fZ", "%Y-%m-%dT%H:%M:%S%.f%:z"):
                src = CSVDataSource(name="csv", csv_file_name=path, column_mapping={}, frequency=D.timedelta(days=1),
                                    date_column_name="date", date_format=fmt, data_frequency_use_window_end=False, symbols=["X"],
                                    asset_service=svc, trading_calendar=get_calendar("24/7"), data_type=DataType.MARKET_DATA)
                try:
                    await src.load_data_in_memory()
                    col = src.data.sort("date")["date"]
                    tried[fmt] = (str(col.dtype), int(col.dt.cast_time_unit("ns").cast(pl.Int64)[0]))
                except Exception as exc:  # noqa: BLE001
                    tried[fmt] = f"{type(exc).__name__}: {str(exc)[:120]}"

        asyncio.run(main())
        got = [v for v in tried.values() if isinstance(v, tuple)]
        if not got:
            return not_supported(f"ISO の文字列を date の列に書いた CSV を ziplime の CSVDataSource で読んだ(date_format を 2 通り)-> {tried}")
        return ok(got[0][1], f"ISO の文字列を date の列に書いた CSV を ziplime の CSVDataSource で読み、読んだ date の最初(型 {got[0][0]})。"
                  f"date_format の試し: {tried}", {"reader": C.qualname(CSVDataSource.load_data_in_memory)})

    scene_p2_iso_utc = scene_p2_iso_offset = _iso

    def _ts(self, sc):
        evs = [{"kind": "bar", "ts_ns": e["ts_ns"], "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0}
               for e in C.events(sc)]
        try:
            log, car = self._seq(evs, ns_dates=True)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"ナノ秒の時刻の足(polars Datetime ns)を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        return ok({"observed_ts_ns": [t for _, t in log]},
                  "足を polars の Datetime('ns') で渡した。handle_data の context.get_datetime()(呼び出しは暦の日ごと)。" + TWO,
                  {"carriers": car})

    scene_p2_event_time_exact = scene_p2_one_ns_apart = _ts

    # ---------------- P0-3
    def _type(self, sc):
        e = C.events(sc)[0]
        if e["kind"] != "bar":
            return not_supported(NON_BAR.format(k=e["kind"], err=_try_non_bar(e)))
        out = {}
        car = []

        async def h(ctx, data, n):
            ctx.st["log"].append(["bar", _now(ctx)])
            car.append(C.carrier(data))
            df = await data.current(assets=[ctx.a], fields=["open", "high", "low", "close", "volume"])
            out.update({k: float(df[k][0]) for k in ("open", "high", "low", "close", "volume") if len(df)})

        st = run([e], h)
        return ok({"sequence": st["log"], "fields": out}, "日足 1 本。data.current で読んだ。" + TWO, {"carriers": car})

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
        reads, tried = C.Reads(), []

        async def h(ctx, data, n):
            if _now(ctx) != probe or reads.items:
                return
            try:
                hist = (await data.history(assets=[ctx.a], bar_count=10, fields=["close"]))["close"].to_list()
            except Exception as exc:  # noqa: BLE001
                tried.append(f"data.history(bar_count=10) -> {type(exc).__name__}: {str(exc)[:100]}")
                return
            # round r6-2: of = the BarData the tool passed to handle_data (its history is awaited above)
            reads.read("data.history(assets, bar_count=10, fields=['close'])(null の行は足が無い)",
                       lambda: [x for x in hist if x is not None and x == x], of=data)

        st = run(C.events(sc), h, label=label)
        return reads, f"日付={label}: 呼び出しの時刻 {st['calls_ns']}、{tried or [r['means'] for r in reads.items]}"

    def scene_p4_visible_at_step(self, sc):
        # round r8-1: the configured target's one bar-date convention (until round r8-1 both were run and one picked)
        reads, note = self._visible(sc, self.choose["label"])
        if not reads.items:  # no_probe_call or no read
            return not_supported(f"T0 + 4 日の呼び出しで過去を読めなかった。{note}")
        return ok(reads.output(), f"T0 + 4 日の呼び出しに data.history を読んだ。{note}", reads.provenance())

    def scene_p4_received_time(self, sc):
        return not_supported("足は 1 本に時刻 1 つ(date の列)で、受け取れる時刻を別に持たせる口が無い。試したこと: "
                             + _no_kw("received_time") + " / 足に recv の列を足して渡す -> "
                             + _try_non_bar({"ts_ns": sc.input["events"][0]["ts_ns"], "open": 1.0, "high": 1.0, "low": 1.0,
                                             "close": 1.0, "volume": 1.0, "recv_ns": 1}))

    def _future(self, sc, label):
        probe = sc.input["probe_at_ns"]
        att = C.Attempts()

        def closes(v):
            return v["close"].to_list() if hasattr(v, "columns") and "close" in v.columns else v

        async def h(ctx, data, n):
            if _now(ctx) != probe or att.items:
                return
            ex = await ctx.exchange_repository.get_default_exchange()
            # namings: the scene's fixed list; the bar convention decides which row a time names (_utc of the time)
            await C.try_time_namings_async(att, "exchange.get_spot_value(dt=時刻)", "time_at", lambda t: _then(ex.get_spot_value(
                assets=frozenset({ctx.a}), fields=frozenset({"close"}), dt=t, data_frequency=D.timedelta(days=1)), closes), sc, _utc)
            await C.try_time_namings_async(att, "exchange.get_data_by_limit(end_date=時刻)", "time_until", lambda t: _then(
                ex.get_data_by_limit(fields=frozenset({"close"}), limit=6, end_date=t, frequency=D.timedelta(days=1),
                                     assets=frozenset({ctx.a}), include_end_date=True), closes), sc, _utc)
            await att.run_async("data.history(bar_count=6)(件数)", "other",
                                lambda: _then(data.history(assets=[ctx.a], bar_count=6, fields=["close"]), closes))
            await att.run_async("data.current(close)", "other", lambda: _then(data.current(assets=[ctx.a], fields=["close"]), closes))

        run(C.events(sc), h, label=label)
        return att

    def scene_p4_future_read_attempt(self, sc):
        att = self._future(sc, self.choose["label"])  # round r8-1: the configured target's one convention
        if not att.items:  # no_probe_call
            return not_supported("T0 + 4 日の呼び出しが無かったので、先を読む試しができなかった")
        return ok(att.output(), f"T0 + 4 日の呼び出しに試した(足の日付={self.choose['label']}): {att.summary()}")

    # ---------------- P0-5
    def _no_types(self, sc):
        return not_supported(NON_BAR.format(k="約定・資金調達・清算", err=_try_non_bar(sc.input["streams"]["trades"][0])))

    scene_p5_same_time_twice = scene_p5_hand_over_order = _no_types

    def scene_p5_same_stream_order(self, sc):
        rows = [C.as_bar(e) for e in C.events(sc)]
        seen, car = [], []

        async def h(ctx, data, n):
            df = await data.current(assets=[ctx.a], fields=["close"])
            seen.append(df["close"].to_list())
            car.append(C.carrier(data))

        try:
            st = run(rows, h)
        except Exception as exc:  # noqa: BLE001
            return not_supported(f"同じ時刻の 3 本を渡して走らせた -> {type(exc).__name__}: {str(exc)[:200]}")
        flat = [float(x) for v in seen for x in v if x is not None]
        flat_car = [c for v, c in zip(seen, car) for x in v if x is not None]
        return ok({"prices": flat}, TWO + f"。同じ時刻の 3 本(終値 101・99・100)を渡した。各回の data.current(close) {seen}、呼び出し {st['calls_ns']}",
                  {"carriers": flat_car})

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
    def _buy(self, sc, capital=100_000.0, qty: int = 1, **kw):
        out = {}

        async def h(ctx, data, n):
            if n == 1:
                ctx.o = await ctx.order(ctx.a, qty, style=MarketOrder())
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

    def scene_p7_cost_per_unit(self, sc):
        out, _ = self._buy(sc, qty=2, equity_commission=_PerUnit(0.375))
        return ok({"fee": out.get("commission")}, "run_simulation(equity_commission=<EquityCommissionModel の子: 0.375 × |transaction.amount|>)、"
                  f"数量 2 の成行。最後の呼び出しの get_order: {out}")

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


async def _then(coro, f):
    return f(await coro)


class _PerUnit(EquityCommissionModel):
    """0.375 per unit of each transaction (the equity_commission socket)."""

    def __init__(self, per_unit: float):
        super().__init__()
        self.per_unit = per_unit

    def calculate(self, order, transaction):
        return self.per_unit * abs(float(transaction.amount))

    def calculate_for_asset(self, asset, quantity, transaction_amount):
        return self.per_unit * abs(float(quantity))


class _Flat(EquityCommissionModel):
    def __init__(self, fee: float):
        super().__init__()
        self.fee = fee

    def calculate(self, order, transaction):
        return 0.0 if order.commission else self.fee

    def calculate_for_asset(self, asset, quantity, transaction_amount):
        return self.fee
