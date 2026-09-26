"""Survey candidate 6 `Ziplime` (PyPI ziplime 1.19.16, the version item 0 checked; venv item_2/ziplime, install record
venvs/item_2/logs/i2_r1_scenekeeper_install_6.log) for the item 2 battery.

The tool's own calls used (as item 0 found them, tests/bt/battery/item_0/opponents/ziplime_adapter.py): an asset db
from `get_asset_service`, a `DataSource` holding a polars frame (date / sid / open / high / low / close / price / volume),
`run_simulation(trading_calendar="24/7", emission_rate=..., total_cash=..., exchange=...)` with an algorithm file whose
handle_data forwards here, and inside it `context.order(asset, amount, style=MarketOrder() / LimitOrder(px) /
StopOrder(px))` and `context.cancel_order`.  The exchange is the tool's `SimulationExchange` built with the same
defaults run_simulation uses (FixedBasisPointsSlippage(), PerShare default commission unless the scene gives one rate:
then `PerDollar(rate)`, price_used_in_order_execution "close"); a subclass only records what its own
`get_transactions` returned (each transaction's dt, price and amount, and the order's commission increase).

The tool takes bars on its emission grid.  Bars come from i2_common.bar_rows, each row dated with the bar's end; only
bars of one minute (emission 1 minute) or one day (emission 1 day) are run.  Tried and not run: bars of one second
(emission 1 second over the tool's minimum two sessions, i.e. 172,801 bars per asset, did not finish in 240 s:
scratchpad bt/item_2/zl/i2_r1_scenekeeper_zl_probe.py 1 under `timeout 240`), and a bar per trade print (the prints are
not on an emission grid).  An action is sent in the first handle_data call whose time is at or after the action's time.
"""
from __future__ import annotations

import asyncio
import datetime as D
import logging
import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import i2_common as C  # noqa: E402
from i2_protocol import NotExpressible, Refused  # noqa: E402

logging.disable(logging.CRITICAL)
import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))

import polars as pl  # noqa: E402

from ziplime.assets.domain.asset_type import AssetType  # noqa: E402  (the tool)
from ziplime.assets.entities.asset_symbol import AssetSymbol  # noqa: E402
from ziplime.assets.entities.equity import Equity  # noqa: E402
from ziplime.assets.entities.exchange_asset import ExchangeAsset  # noqa: E402
from ziplime.assets.entities.exchange_info import ExchangeInfo  # noqa: E402
from ziplime.constants.data_type import DataType  # noqa: E402
from ziplime.core.ingest_data import get_asset_service  # noqa: E402
from ziplime.core.run_simulation import run_simulation  # noqa: E402
from ziplime.data.services.data_source import DataSource  # noqa: E402
from ziplime.exchanges.simulation_exchange import SimulationExchange  # noqa: E402
from ziplime.finance.commission import DEFAULT_MINIMUM_COST_PER_EQUITY_TRADE, DEFAULT_PER_SHARE_COST, PerShare  # noqa: E402
from ziplime.finance.commission.per_contract import PerContract  # noqa: E402
from ziplime.finance.commission.per_dolar import PerDollar  # noqa: E402
from ziplime.finance.execution import LimitOrder, MarketOrder, StopOrder  # noqa: E402
from ziplime.finance.slippage.fixed_basis_points_slippage import FixedBasisPointsSlippage  # noqa: E402
from ziplime.finance.slippage.slippage_model import DEFAULT_FUTURE_VOLUME_SLIPPAGE_BAR_LIMIT  # noqa: E402
from ziplime.finance.slippage.volatility_volume_share import VolatilityVolumeShare  # noqa: E402
from ziplime.utils.calendar_utils import get_calendar  # noqa: E402

TOOL = "ziplime 1.19.16"
MIN, DAY = 60 * 10**9, 86_400 * 10**9
_ROOT = tempfile.mkdtemp(prefix="i2_ziplime_")
_HOOKS = types.ModuleType("_zl_hooks")
sys.modules["_zl_hooks"] = _HOOKS
_ALGO = os.path.join(_ROOT, "algo.py")
with open(_ALGO, "w") as f:
    f.write("import sys\nH = sys.modules['_zl_hooks']\n"
            "async def initialize(context):\n    await H.initialize(context)\n"
            "async def handle_data(context, data):\n    await H.handle_data(context, data)\n")


def _dt(ns):
    return D.datetime.fromtimestamp(ns // 10**9, tz=D.timezone.utc) + D.timedelta(microseconds=(ns % 10**9) // 1000)


def _ns(dt):
    return int(dt.timestamp()) * 10**9 + dt.microsecond * 1000


class Adapter:
    name = "opp_ziplime"

    def run(self, inp):
        C.gate(inp, tool=TOOL, orders=("market", "limit", "stop", "cancel"), events=("book", "trade", "bar"),
               fill_models=C.bar_fill_models, costs=("maker_rate", "taker_rate"), account=("cash",))
        bars, _src = C.bar_rows(inp)
        spans = {b["span_ns"] for b in bars}
        if not bars or spans - {MIN, DAY} or len(spans) != 1:
            raise NotExpressible(f"{TOOL}: 足の幅 {sorted(spans)} ns を回す口が無い。回したのは 1 分と 1 日の emission_rate だけ"
                                 "(1 秒は最小の 2 日の区間で 240 秒以内に終わらなかった。約定 1 件ごとの足は emission の格子に乗らない)")
        span = next(iter(spans))
        rate = C.single_fee_rate(inp, TOOL)
        c = inp.get("costs") or {}
        commission = PerDollar(cost=float(rate)) if "maker_rate" in c else PerShare(
            cost=DEFAULT_PER_SHARE_COST, min_trade_cost=DEFAULT_MINIMUM_COST_PER_EQUITY_TRADE)
        acts = sorted(inp["actions"], key=lambda a: a["t"])
        rec = {"orders": {}, "fills": []}
        oid2ref, ref2o, done = {}, {}, set()
        last_comm = {}

        class Rec(SimulationExchange):
            async def get_transactions(self, orders, current_dt, same_bar_execution):
                t, cm, closed = await super().get_transactions(orders, current_dt, same_bar_execution)
                for txn in t:
                    ref = oid2ref.get(getattr(txn, "order_id", None))
                    if ref is None:
                        continue
                    o = ref2o[ref]
                    fee = float(o.commission) - last_comm.get(ref, 0.0)
                    last_comm[ref] = float(o.commission)
                    rec["fills"].append({"ref": ref, "t": _ns(txn.dt), "px": float(txn.price),
                                         "qty": abs(float(txn.amount)), "fee": fee, "liq": None})
                return t, cm, closed

        async def main():
            svc = get_asset_service(db_path=os.path.join(tempfile.mkdtemp(dir=_ROOT), "a.sqlite"), clear_asset_db=True)
            ex = ExchangeInfo(mic="LIME", name="LIME", canonical_name="LIME", country_code="US")
            await svc.save_exchanges([ex])
            for sym, isin in (("X", "XX0000000001"), ("B", "XX0000000002")):
                eq = Equity(id=None, isin=isin, asset_name=sym, start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1),
                            first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1))
                await svc.save_exchange_assets([ExchangeAsset(
                    sid=None, symbol=sym, start_date=D.date(2020, 1, 1), end_date=D.date(2030, 1, 1),
                    first_traded=D.date(2020, 1, 1), auto_close_date=D.date(2030, 1, 1), external_id=sym, exchange=ex,
                    asset=eq)])
            a = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="X", mic="LIME"), asset_type=AssetType.EQUITY)
            b = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="B", mic="LIME"), asset_type=AssetType.EQUITY)
            first = _dt(bars[0]["t"] // DAY * DAY)
            last = _dt((bars[-1]["t"] // DAY + 1) * DAY)
            step = D.timedelta(microseconds=span // 1000)
            df = pl.DataFrame({"date": pl.Series("date", [_dt(x["t"]) for x in bars]).cast(pl.Datetime("ns", "UTC")),
                               "sid": [a.sid] * len(bars), "open": [float(x["o"]) for x in bars],
                               "high": [float(x["h"]) for x in bars], "low": [float(x["l"]) for x in bars],
                               "close": [float(x["c"]) for x in bars], "price": [float(x["c"]) for x in bars],
                               "volume": [float(x["v"]) for x in bars]})
            n = int((last - first) / step) + 1
            bdf = pl.DataFrame({"date": pl.Series("date", [first + i * step for i in range(n)]).cast(pl.Datetime("ns", "UTC")),
                                "sid": pl.Series("sid", [b.sid] * n, dtype=df["sid"].dtype),
                                **{k: [1.0] * n for k in ("open", "high", "low", "close", "price", "volume")}})
            data = pl.concat([df, bdf])

            class Mem(DataSource):
                def __init__(self):
                    super().__init__(name="mem", start_date=first, end_date=last + D.timedelta(days=30), frequency=step,
                                     original_frequency=step, data_type=DataType.MARKET_DATA)
                    self.data = data

                def get_dataframe(self):
                    return self.data

            src = Mem()
            from ziplime.gens.domain.simulation_clock import SimulationClock
            clock = SimulationClock(trading_calendar=get_calendar("24/7"), start_date=first, end_date=last, emission_rate=step)
            exch = Rec(name="LIME", country_code="US", trading_calendar=get_calendar("24/7"), data_source=src,
                       equity_slippage=FixedBasisPointsSlippage(), equity_commission=commission,
                       future_slippage=VolatilityVolumeShare(volume_limit=DEFAULT_FUTURE_VOLUME_SLIPPAGE_BAR_LIMIT),
                       future_commission=PerContract(cost=0.85, exchange_fee=0.0, min_trade_cost=0.0),
                       cash_balance=float(inp["account"]["cash"]), clock=clock, price_used_in_order_execution="close",
                       account_id="simulation_account", is_default=True)

            async def init(ctx):
                ctx.a = await ctx.symbol("X")

            async def hd(ctx, data_):
                now = _ns(ctx.get_datetime())
                for x in acts:
                    if id(x) in done or x["t"] > now:
                        continue
                    done.add(id(x))
                    if x["op"] == "cancel":
                        o = ref2o.get(x["ref"])
                        if o is not None:
                            await ctx.cancel_order(o.id, "LIME")
                        continue
                    if x["op"] != "place":
                        raise NotExpressible(f"{TOOL}: 操作 {x['op']} の口が無い")
                    style = {"market": lambda: MarketOrder(), "limit": lambda: LimitOrder(x["px"]),
                             "stop": lambda: StopOrder(x["stop_px"])}[x["type"]]()
                    amt = x["qty"] if x["side"] == "buy" else -x["qty"]
                    o = await ctx.order(ctx.a, amt, style=style)
                    if o is None:
                        rec["orders"][x["ref"]] = {"status": "rejected", "error": "order() returned None"}
                        continue
                    oid2ref[o.id] = x["ref"]
                    ref2o[x["ref"]] = o

            _HOOKS.initialize, _HOOKS.handle_data = init, hd
            await run_simulation(start_date=first, end_date=last, trading_calendar="24/7", emission_rate=step,
                                 total_cash=float(inp["account"]["cash"]), market_data_source=src, custom_data_sources=[],
                                 algorithm_file=_ALGO, stop_on_error=True, asset_service=svc, benchmark_asset_symbol="B@LIME",
                                 exchange=exch, clock=clock)

        try:
            asyncio.run(main())
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:200]}")
        for x in C.places(inp):
            ref = x["ref"]
            if ref in rec["orders"]:
                continue
            got = sum(f["qty"] for f in rec["fills"] if f["ref"] == ref)
            o = ref2o.get(ref)
            rec["orders"][ref] = {"status": C.status_from(got, x["qty"], active=o is not None and bool(o.open))}
        return rec


TARGET = Adapter()
