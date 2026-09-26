"""Survey candidate 1 `Basana` (PyPI basana 1.11, venv item_0/basana) for the item 4 battery.

The tool's own calls used: `basana.backtesting_dispatcher()`, the backtesting `Exchange(dispatcher, initial_balances,
liquidity_strategy_factory=liquidity.InfiniteLiquidity, fee_strategy=fees.Percentage, default_pair_info)`,
`add_bar_source(FifoQueueEventSource)`, `subscribe_to_bar_events`, `create_market_order / create_limit_order /
create_stop_order / cancel_order / get_order_info`.  An order created in the bar handler of bar i is processed on the
next bar event: a market order at that bar's open (backtesting/orders.py 264 行), a limit order at the open when the
open is through the limit, else at the limit when the bar reaches it (292-310 行), a stop at the open or the stop price
(365-385 行).

Scene -> tool: long positions only (a spot balance; a short is a sale of base currency borrowed through the exchange's
lending, which this adapter does not set up -- allow_short -> NotExpressible); the entry is sized with the decision
bar's close (amount = notional / close[i]; the strategy cannot see the next open); one fee `Percentage`;
stop_loss -> a stop order and take_profit / maker_tp -> a limit order created in the handler of the entry's fill bar
(levels in the tool's Decimal: the exchange refuses a price with more than the pair's decimal digits);
execution "maker" -> a limit at the decision bar's close, cancelled by the strategy after maker_timeout_bars bars;
max_hold / wick / entry filters are strategy code.  Not expressible: allow_short, slippage / spread as a price
adjustment (the liquidity strategies model volume and impact), a maker fee different from the taker fee (one fee
strategy), swap, per-trade PnL, per-bar equity, metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import asyncio
import datetime as D
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

import basana as bs  # noqa: E402
from basana.backtesting import exchange as bex, fees as bfees, liquidity as bliq  # noqa: E402
from basana.core.bar import BarEvent  # noqa: E402

EPOCH = D.datetime(1970, 1, 1, tzinfo=D.timezone.utc)


class BasanaAdapter(Base):
    name = "opp_basana"
    TOOL = "Basana 1.11"
    SUPPORTS = {"taker_fee_pct", "maker_fee_pct", "execution", "stop_loss_pct", "take_profit_pct", "max_hold_bars",
                "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"allow_short": "空売りは Exchange の lending(create_loan で借りた base を売る: exchange.py 395-436 行)で、この "
                              "adapter は借入の段取りを書いていない(道具に売り建ての注文そのものは無い)",
               "slippage_pct": "値に率で掛ける滑りの口を探したが無い(liquidity は出来高の割合と価格の影響の模型)",
               "spread_pct": "スプレッドの口を探したが無い(足の値で約定する)",
               "swap_daily_pct": "建玉の持ち越しの口を探したが無い(lending の利息は借入に掛かる)"}
    METRICS = "12 の指標を出す口を探したが無い(Exchange は残高と注文だけ)"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = ("足(BarEvent)と約定の source を受けるが、宣言でファイルを読む口は足の CSV(external/*)だけで、気配の買い ask・売り bid、"
                "実行記録・目的つきの書き出し・ダッシュボードを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        if len(fee_kinds(cfg)) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: fee_strategy は 1 つ")
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い(残高の出入りだけ)"),
                       ("equity", "足ごとの資産の推移の口を探したが無い"), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        return out

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        sig = signal_map(inp)
        maker = cfg["execution"] == "maker"
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]
        dur = D.timedelta(seconds=int(inp["bar_seconds"]))
        pair = bs.Pair("BASE", "JPY")
        pinfo = bs.PairInfo(base_precision=8, quote_precision=8)
        fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]
        disp = bs.backtesting_dispatcher()
        ex = bex.Exchange(disp, {"JPY": Decimal(str(cfg["initial_equity"]))}, liquidity_strategy_factory=bliq.InfiniteLiquidity,
                          fee_strategy=bfees.Percentage(percentage=Decimal(str(fee))) if fee else bfees.NoFee(),
                          default_pair_info=pinfo)
        evs, when2k = [], {}
        for k, b in enumerate(bars):
            begin = EPOCH + D.timedelta(microseconds=b["t_ns"] // 1000)
            when2k[begin] = k  # a fill's `when` is the begin of the bar it filled on (orders.py: the bar's datetime)
            evs.append(BarEvent(begin + dur, bs.Bar(begin, pair, *(Decimal(str(b[x])) for x in
                                                                   ("open", "high", "low", "close", "volume")), dur)))
        ex.add_bar_source(bs.FifoQueueEventSource(events=evs))
        st = {"k": -1, "orders": [], "entry": None, "brackets": [], "limit": None, "missed": 0, "level": None,
              "entry_bar": None, "pos": Decimal(0)}

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        async def base_bal():
            return (await ex.get_balance("BASE")).available

        async def on_bar(be):
            st["k"] += 1
            k = st["k"]
            cl = float(be.bar.close)
            pos = await base_bal()
            if st["entry"] is not None:  # the entry order filled on this bar: send its exits
                info = await ex.get_order_info(st["entry"])
                if not info.is_open and info.amount_filled > 0:
                    st["entry"] = None
                    kb = k
                    px = Decimal(info.fill_price)
                    st["entry_bar"] = kb
                    if W is not None:
                        lo = max(0, kb - W)
                        st["level"] = min(bars[j]["low"] for j in range(lo, kb)) if kb > lo else None
                    if cfg["stop_loss_pct"]:
                        o = await ex.create_stop_order(bs.OrderOperation.SELL, pair, pos,
                                                       px * (1 - Decimal(str(cfg["stop_loss_pct"])) / 100))
                        st["brackets"].append(o.id); st["orders"].append((o.id, "CLOSE_LONG"))
                    for pct in (cfg["take_profit_pct"], cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None):
                        if pct:
                            o = await ex.create_limit_order(bs.OrderOperation.SELL, pair, pos, px * (1 + Decimal(str(pct)) / 100))
                            st["brackets"].append(o.id); st["orders"].append((o.id, "CLOSE_LONG"))
            if pos == 0 and st["brackets"]:  # an exit filled: cancel the other one
                for oid in st["brackets"]:
                    if (await ex.get_order_info(oid)).is_open:
                        await ex.cancel_order(oid)
                st["brackets"], st["entry_bar"], st["level"] = [], None, None

            async def flatten():
                for oid in st["brackets"]:
                    if (await ex.get_order_info(oid)).is_open:
                        await ex.cancel_order(oid)
                st["brackets"] = []
                o = await ex.create_market_order(bs.OrderOperation.SELL, pair, pos)
                st["orders"].append((o.id, "CLOSE_LONG"))

            if pos > 0 and st["entry_bar"] is not None:
                if N is not None and k + 1 - st["entry_bar"] >= N:
                    await flatten(); return
                if st["level"] is not None and cl < st["level"]:
                    await flatten(); return
            if maker and st["limit"] is not None:
                oid, side, placed = st["limit"]
                if not (await ex.get_order_info(oid)).is_open:
                    st["limit"] = None
                elif k - placed >= cfg["maker_timeout_bars"]:
                    await ex.cancel_order(oid); st["missed"] += 1; st["limit"] = None
            s = sig.get(k)
            if not s:
                return
            side = s if s != "CLOSE" else ("SELL" if pos > 0 else None)
            if side is None:
                return
            if not maker:
                if side == "SELL" and pos > 0:
                    await flatten()
                elif side == "BUY" and pos == 0 and st["entry"] is None and entry_ok(k, "BUY"):
                    o = await ex.create_market_order(bs.OrderOperation.BUY, pair, Decimal(str(round(notional / cl, 8))))
                    st["entry"] = o.id; st["orders"].append((o.id, "OPEN_LONG"))
                return
            actionable = pos == 0 if side == "BUY" else pos > 0
            if not (actionable or s == "CLOSE"):
                return
            if st["limit"] is not None:
                await ex.cancel_order(st["limit"][0])
                if st["limit"][1] != side:
                    st["missed"] += 1
                st["limit"] = None
            if side == "BUY" and not entry_ok(k, "BUY"):
                return
            amt = pos if side == "SELL" else Decimal(str(round(notional / cl, 8)))
            o = await ex.create_limit_order(bs.OrderOperation.BUY if side == "BUY" else bs.OrderOperation.SELL, pair, amt,
                                            Decimal(str(cl)))
            st["orders"].append((o.id, "OPEN_LONG" if side == "BUY" else "CLOSE_LONG"))
            st["limit"] = (o.id, side, k)
            if side == "BUY":
                st["entry"] = o.id

        ex.subscribe_to_bar_events(pair, on_bar)
        try:
            asyncio.run(disp.run())
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        fills = []

        async def collect():
            for oid, tag in st["orders"]:
                info = await ex.get_order_info(oid)
                for f in info.fills:
                    fills.append({"bar": when2k[f.when], "side": tag, "price": float(f.price),
                                  "size": abs(float(f.balance_updates.get("BASE", Decimal(0))))})
        asyncio.run(collect())
        fills.sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        return want(inp, {"fills": fills, "missed_fills": st["missed"]})


TARGET = BasanaAdapter()
