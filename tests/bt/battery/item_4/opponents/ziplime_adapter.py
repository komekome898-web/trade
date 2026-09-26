"""Survey candidate 6 `Ziplime` (PyPI ziplime 1.19.16, venv item_2/ziplime) for the item 4 battery.

The tool's own calls used (as items 0 / 2 found them): an asset db from `get_asset_service`, a `DataSource` holding a
polars frame (date / sid / open / high / low / close / price / volume), `run_simulation(trading_calendar="24/7",
emission_rate=..., total_cash=..., exchange=..., same_bar_execution=False)` (the tool's default True executes an order
on the bar it was sent in: run_simulation.py 56 行, trading_algorithm.py 2054-2102 行) with an algorithm file whose handle_data forwards here, the tool's
`SimulationExchange(..., equity_slippage=NoSlippage() | FixedBasisPointsSlippage(bp, volume_limit),
equity_commission=PerDollar(rate), price_used_in_order_execution="open")` (subclassed only to record what its own
`get_transactions` returned), and inside handle_data `context.order(asset, amount, style=MarketOrder())`.

Scene -> tool: one emission per scene bar (1 minute or 1 hour); an order sent in handle_data of bar i is executed by the
tool on bar i+1 at that bar's OPEN (price_used_in_order_execution="open"); `order(amount: int)` takes whole shares, so
an entry is int(order_notional / close[i]) shares (the strategy cannot see the next open); spread / 2 + slippage ->
FixedBasisPointsSlippage(basis points, volume_limit=1e9) (zero -> 1e-8 bp: the tool's NoSlippage raised TypeError
with the exchange and 0 bp is refused); one PerDollar commission; long and
short; max_hold / wick / entry filters are strategy code.  Not expressible: a maker fee different from the taker
fee, stop / limit / maker orders on top of the scene's rules (the adapter sends market orders only; LimitOrder /
StopOrder exist in ziplime.finance.execution and are not used here), swap, per-trade PnL, per-bar equity,
missed fills, metrics, op metrics / split / pipeline, reference, models.
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, adj, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

logging.disable(logging.CRITICAL)
import structlog  # noqa: E402

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))

import polars as pl  # noqa: E402

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
from ziplime.finance.commission.per_contract import PerContract  # noqa: E402
from ziplime.finance.commission.per_dolar import PerDollar  # noqa: E402
from ziplime.finance.execution import MarketOrder  # noqa: E402
from ziplime.finance.slippage.fixed_basis_points_slippage import FixedBasisPointsSlippage  # noqa: E402
from ziplime.finance.slippage.slippage_model import DEFAULT_FUTURE_VOLUME_SLIPPAGE_BAR_LIMIT  # noqa: E402
from ziplime.finance.slippage.volatility_volume_share import VolatilityVolumeShare  # noqa: E402
from ziplime.gens.domain.simulation_clock import SimulationClock  # noqa: E402
from ziplime.utils.calendar_utils import get_calendar  # noqa: E402

_ROOT = tempfile.mkdtemp(prefix="i4_ziplime_")
_HOOKS = types.ModuleType("_zl_hooks_i4")
sys.modules["_zl_hooks_i4"] = _HOOKS
_ALGO = os.path.join(_ROOT, "algo.py")
with open(_ALGO, "w") as f:
    f.write("import sys\nH = sys.modules['_zl_hooks_i4']\n"
            "async def initialize(context):\n    await H.initialize(context)\n"
            "async def handle_data(context, data):\n    await H.handle_data(context, data)\n")
NO_ORDER = ("この adapter は成行だけを送る(ziplime.finance.execution の LimitOrder / StopOrder は在るが、決済の水準の管理と"
            "時間切れの取消を道具の口で書いていない)")


def _dt(ns):
    return D.datetime.fromtimestamp(ns // 10**9, tz=D.timezone.utc)


class ZiplimeAdapter(Base):
    name = "opp_ziplime"
    TOOL = "ziplime 1.19.16"
    SUPPORTS = {"allow_short", "taker_fee_pct", "slippage_pct", "spread_pct", "max_hold_bars", "entry_mask",
                "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"maker_fee_pct": NO_ORDER, "execution": NO_ORDER, "stop_loss_pct": NO_ORDER, "take_profit_pct": NO_ORDER,
               "exit_execution": NO_ORDER, "maker_tp_pct": NO_ORDER,
               "swap_daily_pct": "持ち越しの口を探したが無い(SimulationExchange の引数は slippage・commission・cash)"}
    METRICS = "12 の指標を 1 つずつ出す口を探したが無い(結果は周期ごとの成績の表)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は DataSource の足の表で、気配の買い ask・売り bid、板、目的つきの書き出し・ダッシュボードの口を探したが無い"

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い"), ("equity", "足ごとの資産の推移をこの adapter は取り出していない"),
                       ("missed_fills", NO_ORDER), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        if int(inp["bar_seconds"]) not in (60, 3600):
            out.append("足の幅: 1 分・1 時間の emission だけを回す")
        return out

    def delivery(self, inp):
        """What ziplime hands handle_data: `data` (BarData), whose async history(assets, bar_count, frequency, fields)
        gives the bars up to the simulation's now.  Runs the same simulation as bars with no signal and records instead
        of trading."""
        from _i4_base import _plain_config
        calls = []
        self.bars({"op": "bars", "bars": inp["bars"], "bar_seconds": inp["bar_seconds"], "signals": [],
                   "config": _plain_config(), "want": [], "_delivery_calls": calls})
        return {"calls": calls[:50]}  # (the tool's clock steps through the whole day; 50 calls are enough to judge)

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        step = D.timedelta(seconds=int(inp["bar_seconds"]))
        t2k = {_dt(b["t_ns"]): k for k, b in enumerate(bars)}
        a = adj(c)
        fills, st = [], {"k": -1, "pos": 0, "entry_bar": None, "level": None, "tags": {}}

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        class Rec(SimulationExchange):
            async def get_transactions(self, orders, current_dt, same_bar_execution):
                t, cm, closed = await super().get_transactions(orders, current_dt, same_bar_execution)
                for txn in t:
                    k = t2k.get(txn.dt.astimezone(D.timezone.utc).replace(second=0, microsecond=0)
                                if step.total_seconds() == 60 else txn.dt.astimezone(D.timezone.utc))
                    tag = st["tags"].get(getattr(txn, "order_id", None))
                    fills.append({"bar": k, "side": tag, "price": float(txn.price), "size": abs(float(txn.amount))})
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
            ax = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="X", mic="LIME"), asset_type=AssetType.EQUITY)
            bx = await svc.get_exchange_asset_by_symbol(symbol=AssetSymbol(symbol="B", mic="LIME"), asset_type=AssetType.EQUITY)
            first = _dt(bars[0]["t_ns"] // (86400 * 10**9) * 86400 * 10**9)
            last = _dt((bars[-1]["t_ns"] // (86400 * 10**9) + 1) * 86400 * 10**9)
            df = pl.DataFrame({"date": pl.Series("date", [_dt(x["t_ns"]) for x in bars]).cast(pl.Datetime("ns", "UTC")),
                               "sid": [ax.sid] * len(bars), "open": [x["open"] for x in bars], "high": [x["high"] for x in bars],
                               "low": [x["low"] for x in bars], "close": [x["close"] for x in bars],
                               "price": [x["close"] for x in bars], "volume": [1e9 for _ in bars]})
            n = int((last - first) / step) + 1
            bdf = pl.DataFrame({"date": pl.Series("date", [first + i * step for i in range(n)]).cast(pl.Datetime("ns", "UTC")),
                                "sid": pl.Series("sid", [bx.sid] * n, dtype=df["sid"].dtype),
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
            clock = SimulationClock(trading_calendar=get_calendar("24/7"), start_date=first, end_date=last, emission_rate=step)
            # zero cost: the tool's NoSlippage does not take the exchange's `price` argument (no_slippage.py 18 行 vs
            # simulation_exchange's call; TypeError when tried) and FixedBasisPointsSlippage refuses 0 bp
            # (fixed_basis_points_slippage.py 49-50 行), so zero is sent as 1e-8 bp = 1e-12 relative (under the judge's 1e-9)
            slip = FixedBasisPointsSlippage(basis_points=max(a * 1e4, 1e-8), volume_limit=1e9)
            exch = Rec(name="LIME", country_code="US", trading_calendar=get_calendar("24/7"), data_source=src,
                       equity_slippage=slip, equity_commission=PerDollar(cost=c["taker_fee_pct"] / 100),
                       future_slippage=VolatilityVolumeShare(volume_limit=DEFAULT_FUTURE_VOLUME_SLIPPAGE_BAR_LIMIT),
                       future_commission=PerContract(cost=0.85, exchange_fee=0.0, min_trade_cost=0.0),
                       cash_balance=float(cfg["initial_equity"]), clock=clock, price_used_in_order_execution="open",
                       account_id="simulation_account", is_default=True)

            async def init(ctx):
                ctx.a = await ctx.symbol("X")

            async def send(ctx, amt, tag):
                o = await ctx.order(ctx.a, amt, style=MarketOrder())
                if o is not None:
                    st["tags"][o.id] = tag
                return o

            async def hd(ctx, data_):
                rec_calls = inp.get("_delivery_calls")
                if rec_calls is not None:  # op "delivery": record what the tool hands (data_.history up to now)
                    now = ctx.get_datetime().astimezone(D.timezone.utc)
                    m = int((now - first) / step) + 1
                    h = await data_.history([ctx.a], bar_count=max(1, m), frequency=step, fields=["close"])
                    rows = [r for r in h.iter_rows(named=True) if r.get("close") is not None]
                    if rows:
                        lt = rows[-1]["date"]
                        rec_calls.append({"seen": len(rows), "last_t_ns": int(lt.timestamp()) * 10**9,
                                          "last_close": float(rows[-1]["close"])})
                    else:
                        rec_calls.append({"seen": 0, "last_t_ns": None, "last_close": None})
                    return
                k = t2k.get(ctx.get_datetime().astimezone(D.timezone.utc))
                if k is None:
                    return
                pos = st["pos"]
                cl = bars[k]["close"]
                if pos and st["entry_bar"] is not None:
                    ex_ = (N is not None and k + 1 - st["entry_bar"] >= N) or \
                          (st["level"] is not None and k >= st["entry_bar"] and ((cl < st["level"]) if pos > 0 else (cl > st["level"])))
                    if ex_:
                        await send(ctx, -pos, "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
                        st.update(pos=0, entry_bar=None, level=None)
                        return
                s = sig.get(k)
                if not s or k + 1 >= len(bars):
                    return
                if s == "CLOSE" or (s == "BUY" and pos < 0) or (s == "SELL" and pos > 0):
                    if pos:
                        await send(ctx, -pos, "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")
                        st.update(pos=0, entry_bar=None, level=None)
                    return
                if pos == 0 and entry_ok(k, s) and (s == "BUY" or cfg["allow_short"]):
                    q = int(cfg["order_notional"] / cl)
                    await send(ctx, q if s == "BUY" else -q, "OPEN_LONG" if s == "BUY" else "OPEN_SHORT")
                    st["pos"] = q if s == "BUY" else -q
                    b = k + 1
                    st["entry_bar"] = b
                    if W is not None:
                        lo = max(0, b - W)
                        st["level"] = (min(bars[j]["low"] for j in range(lo, b)) if s == "BUY" else
                                       max(bars[j]["high"] for j in range(lo, b))) if b > lo else None

            _HOOKS.initialize, _HOOKS.handle_data = init, hd
            await run_simulation(start_date=first, end_date=last, trading_calendar="24/7", emission_rate=step,
                                 total_cash=float(cfg["initial_equity"]), market_data_source=src, custom_data_sources=[],
                                 algorithm_file=_ALGO, stop_on_error=True, asset_service=svc, benchmark_asset_symbol="B@LIME",
                                 exchange=exch, clock=clock, same_bar_execution=False)

        try:
            asyncio.run(main())
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:300]}") from exc
        fills.sort(key=lambda f: (f["bar"] if f["bar"] is not None else -1, 0 if str(f["side"]).startswith("CLOSE") else 1))
        return want(inp, {"fills": fills})


TARGET = ZiplimeAdapter()
