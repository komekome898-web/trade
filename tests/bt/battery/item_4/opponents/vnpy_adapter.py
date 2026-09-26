"""Survey candidate 20 `VnPy` (PyPI vnpy 4.4.0 + vnpy_ctastrategy 1.4.1, venv item_0/vnpy) for the item 4 battery,
BAR mode.

The tool's own calls used: `vnpy_ctastrategy.backtesting.BacktestingEngine.set_parameters(vt_symbol, interval, start,
end, rate, slippage=0, size=1, pricetick, capital, mode=BAR)`, `add_strategy(CtaTemplate subclass, {})`,
`history_data`, `run_backtesting()`, the engine's `trades`; in the strategy `buy / sell / short / cover(price, volume,
stop=False|True)` and `cancel_order`.  The engine has limit and stop orders only (no market order); in BAR mode an
order sent in on_bar of bar i is crossed against bar i+1: a buy limit fills when its price >= the bar's low at
min(price, the bar's open), a sell limit when its price <= the high at max(price, open) (backtesting.py
cross_limit_order); a stop when the bar's high / low reaches it at max / min(stop, open) (cross_stop_order).

Scene -> tool: a market order of the scene is the tool's marketable limit (a buy at 10 x the decision bar's close,
a sell at a tenth of it), which the engine fills at the next bar's open; the entry is sized with the decision bar's
close (volume = notional / close[i]: the tool has no value-sized order and the strategy cannot see the next open);
one commission `rate` (on turnover); `pricetick` 1e-8 (no rounding of the scene's prices); stop_loss -> a stop order
and take_profit / maker_tp -> a limit order sent when the entry fills; execution "maker" -> a limit at the decision
bar's close, cancelled by the strategy after maker_timeout_bars bars; max_hold / wick / entry filters are strategy
code.  Not expressible: slippage / spread as a percentage (the engine's `slippage` is an amount per unit), a maker fee
different from the taker fee (one `rate`), swap, per-trade PnL and a per-bar equity (the engine gives trades and
daily results: calculate_result), metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

from vnpy.trader.constant import Direction, Exchange, Interval, Offset  # noqa: E402
from vnpy.trader.object import BarData  # noqa: E402
from vnpy_ctastrategy import CtaTemplate  # noqa: E402
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode  # noqa: E402

UTC = D.timezone.utc
EPOCH = D.datetime(1970, 1, 1, tzinfo=UTC)


class VnpyAdapter(Base):
    name = "opp_vnpy"
    TOOL = "VnPy 4.4.0 + vnpy_ctastrategy 1.4.1 (BAR)"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "execution", "stop_loss_pct", "take_profit_pct",
                "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask", "entry_sides", "stop_mode",
                "stop_window_bars"}
    MISSING = {"slippage_pct": "率の滑りの口を探したが無い(set_parameters の slippage は 1 単位あたりの額)",
               "spread_pct": "スプレッドの口を探したが無い(BAR mode は足の OHLC で交差を決める)",
               "swap_daily_pct": "持ち越しの口を探したが無い(set_parameters の引数は rate・slippage・size・pricetick・capital)"}
    METRICS = "12 の指標: calculate_statistics は日次の結果から出し(日ごとの損益)、決済ごとの損益・勝率の口が無い"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = ("history_data は BarData か TickData の列で、宣言でファイルを読む口(データはデータベースから load_data)・目的つきの"
                "書き出し・ダッシュボードの項目別タブを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        if len(fee_kinds(cfg)) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: set_parameters の rate は 1 つ")
        w = set(inp.get("want") or [])
        if "pnls" in w:
            out.append("決済ごとの損益の口を探したが無い(engine.trades は約定、calculate_result は日次の損益)")
        if "equity" in w:
            out.append("足ごとの資産の推移の口を探したが無い(DailyResult は日次)")
        if "metrics" in w:
            out.append(self.METRICS)
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
        data = [BarData(symbol="X", exchange=Exchange.LOCAL, datetime=EPOCH + D.timedelta(microseconds=b["t_ns"] // 1000),
                        interval=Interval.MINUTE, volume=float(b["volume"]), open_price=float(b["open"]),
                        high_price=float(b["high"]), low_price=float(b["low"]), close_price=float(b["close"]),
                        gateway_name="BACKTESTING") for b in bars]
        dt2k = {d.datetime: k for k, d in enumerate(data)}
        st = {"k": -1, "missed": 0, "limit": None, "brackets": [], "entry_bar": None, "level": None, "seen": 0}

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        class S(CtaTemplate):
            def on_init(self):
                return None

            def on_trade(self, trade):
                k = dt2k[trade.datetime]
                if trade.offset == Offset.OPEN:
                    st["entry_bar"] = k
                    long = trade.direction == Direction.LONG
                    px, q = trade.price, trade.volume
                    if W is not None:
                        lo = max(0, k - W)
                        st["level"] = (min(bars[j]["low"] for j in range(lo, k)) if long else
                                       max(bars[j]["high"] for j in range(lo, k))) if k > lo else None
                    ex = self.sell if long else self.cover
                    if cfg["stop_loss_pct"]:
                        lvl = px * (1 - cfg["stop_loss_pct"] / 100) if long else px * (1 + cfg["stop_loss_pct"] / 100)
                        st["brackets"] += list(ex(lvl, q, stop=True) or [])
                    for pct in (cfg["take_profit_pct"], cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None):
                        if pct:
                            lvl = px * (1 + pct / 100) if long else px * (1 - pct / 100)
                            st["brackets"] += list(ex(lvl, q) or [])
                else:
                    for vid in st["brackets"]:
                        self.cancel_order(vid)
                    st["brackets"], st["entry_bar"], st["level"] = [], None, None
                if st["limit"] is not None and trade.vt_orderid in st["limit"][0]:
                    st["limit"] = None

            def _mkt(self, side, qty, cl):
                if side == "BUY":
                    return (self.cover if self.pos < 0 else self.buy)(cl * 10, qty)
                return (self.sell if self.pos > 0 else self.short)(cl / 10, qty)

            def _flatten(self, cl):
                for vid in st["brackets"]:
                    self.cancel_order(vid)
                st["brackets"] = []
                if self.pos:
                    self._mkt("SELL" if self.pos > 0 else "BUY", abs(self.pos), cl)

            def on_bar(self, bar):
                st["k"] += 1
                k = st["k"]
                cl = bar.close_price
                pos = self.pos
                if pos and st["entry_bar"] is not None:
                    if N is not None and k + 1 - st["entry_bar"] >= N:
                        self._flatten(cl); return
                    if st["level"] is not None and ((cl < st["level"]) if pos > 0 else (cl > st["level"])):
                        self._flatten(cl); return
                if maker and st["limit"] is not None and k - st["limit"][2] >= cfg["maker_timeout_bars"]:
                    for vid in st["limit"][0]:
                        self.cancel_order(vid)
                    st["missed"] += 1; st["limit"] = None
                s = sig.get(k)
                if not s:
                    return
                side = s if s != "CLOSE" else ("SELL" if pos > 0 else "BUY" if pos < 0 else None)
                if side is None:
                    return
                closing = (side == "BUY" and pos < 0) or (side == "SELL" and pos > 0)
                if not maker:
                    if closing:
                        self._flatten(cl)
                    elif s != "CLOSE" and pos == 0 and entry_ok(k, side) and (side == "BUY" or cfg["allow_short"]):
                        self._mkt(side, notional / cl, cl)
                    return
                actionable = pos <= 0 if side == "BUY" else (pos > 0 or (pos == 0 and cfg["allow_short"]))
                if not (actionable or s == "CLOSE"):
                    return
                if st["limit"] is not None:
                    for vid in st["limit"][0]:
                        self.cancel_order(vid)
                    if st["limit"][1] != side:
                        st["missed"] += 1
                    st["limit"] = None
                if not closing and not entry_ok(k, side):
                    return
                qty = abs(pos) if closing else notional / cl
                if side == "BUY":
                    ids = (self.cover if pos < 0 else self.buy)(cl, qty)
                else:
                    ids = (self.sell if pos > 0 else self.short)(cl, qty)
                st["limit"] = (list(ids or []), side, k)

        eng = BacktestingEngine()
        eng.output = lambda msg: None
        fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]
        try:
            eng.set_parameters(vt_symbol="X.LOCAL", interval=Interval.MINUTE, start=data[0].datetime,
                               end=data[-1].datetime + D.timedelta(days=1), rate=float(fee) / 100, slippage=0.0, size=1,
                               pricetick=1e-8, capital=float(cfg["initial_equity"]), mode=BacktestingMode.BAR)
            eng.add_strategy(S, {})
            eng.history_data = list(data)
            eng.run_backtesting()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        fills = []
        for t in eng.trades.values():
            d = "LONG" if (t.direction == Direction.LONG) == (t.offset == Offset.OPEN) else "SHORT"
            fills.append({"bar": dt2k[t.datetime], "side": f"{'OPEN' if t.offset == Offset.OPEN else 'CLOSE'}_{d}",
                          "price": float(t.price), "size": float(t.volume)})
        fills.sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        return want(inp, {"fills": fills, "missed_fills": st["missed"]})


TARGET = VnpyAdapter()
