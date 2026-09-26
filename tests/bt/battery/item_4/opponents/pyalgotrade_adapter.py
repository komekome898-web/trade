"""Survey candidate 122 `gbeced/pyalgotrade` (PyPI pyalgotrade 0.20, venv item_4/pyalgotrade) for the item 4 battery.

Public API used: `barfeed.membf.BarFeed` + `bar.BasicBar`, `broker.backtesting.Broker` (subclassed only at
its plug point `getInstrumentTraits`, so quantities are not rounded to integers), `broker.backtesting.Commission`
(subclassed: `calculate(order, price, quantity)` receives the order, so a resting limit order pays the maker
rate and a market / stop order the taker rate), `broker.fillstrategy.DefaultStrategy(volumeLimit=None)` with a
`broker.slippage.SlippageModel` subclass (price x (1 +- (spread/2 + slippage)) on market and stop fills;
fillstrategy.py 318-340・360-398 行: limit fills are not slipped), `strategy.BacktestingStrategy`
(`onBars`, `onOrderUpdated`), `broker.createMarketOrder / createLimitOrder / createStopOrder`,
`submitOrder`, `cancelOrder`, `getEquity`, `stratanalyzer.trades.Trades`.

Scene -> tool: a market order sent in `onBars` of bar i fills at bar i+1's open (fillstrategy.py 330-335 行).
The strategy cannot see bar i+1's open when it sends the order, so an entry is sized with the decision bar's
close: quantity = notional / close[i] (the tool has no value-sized order).  Exits (stop / take-profit / maker
take-profit) are sent when the entry fills; execution "maker" -> a GTC limit at the decision bar's close,
cancelled by the strategy after maker_timeout_bars bars; max_hold_bars / wick_invalidation / entry filters are
strategy code.  Not expressible: swap_daily_pct (grep swap|carry|interest|financ 0 件 in pyalgotrade/broker),
the 12 metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import datetime as D
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible, Refused, adj, to_dt, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

from pyalgotrade import bar, strategy  # noqa: E402
from pyalgotrade import broker as pbroker  # noqa: E402
from pyalgotrade.barfeed import membf  # noqa: E402
from pyalgotrade.broker import backtesting, fillstrategy, slippage  # noqa: E402
from pyalgotrade.stratanalyzer import trades as tradesan  # noqa: E402

logging.disable(logging.CRITICAL)
INST = "X"
A = pbroker.Order.Action


class _Feed(membf.BarFeed):
    def barsHaveAdjClose(self):
        return True


class _FloatTraits(pbroker.InstrumentTraits):
    def roundQuantity(self, quantity):
        return quantity


class _Broker(backtesting.Broker):
    def getInstrumentTraits(self, instrument):
        return _FloatTraits()


class PyAlgoTradeAdapter(Base):
    name = "opp_pyalgotrade"
    TOOL = "PyAlgoTrade 0.20"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct", "execution",
                "stop_loss_pct", "take_profit_pct", "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask",
                "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"swap_daily_pct": "持ち越し・金利の口を探したが無い(pyalgotrade/broker の grep swap・carry・interest・financ 0 件)"}
    METRICS = ("12 の指標を出す口を探したが無い(stratanalyzer は returns・sharpe・drawdown・trades で、trades は損益の配列と勝ち負けの数、"
               "sharpe は日次の年率。外から与えた損益と資産の列を受ける関数も無い)")
    SPLIT = "行の割合で分ける口を探したが無い(pyalgotrade の grep split・walk 0 件、optimizer は引数の総当たり)"
    PIPELINE = ("足の feed(csvfeed・membf)と約定の足(Frequency.TRADE)だけで、気配の買い ask・売り bid、板、実行記録、目的つきの書き出し、"
                "ダッシュボードの口を探したが無い")

    def extra_gate(self, inp):
        if "metrics" in (inp.get("want") or []):
            return [self.METRICS]
        return []

    def delivery(self, inp):
        """What PyAlgoTrade hands onBars: the bar feed's data series of the instrument (every bar dispatched so far)."""
        from _i4_base import ns_of
        feed = _Feed(bar.Frequency.MINUTE)
        feed.addBarsFromSequence(INST, [bar.BasicBar(to_dt(b["t_ns"]), b["open"], b["high"], b["low"], b["close"],
                                                     b["volume"], b["close"], bar.Frequency.MINUTE) for b in inp["bars"]])
        brk = _Broker(6000.0, feed)
        calls = []

        class S(strategy.BacktestingStrategy):
            def __init__(self):
                super().__init__(feed, brk)

            def onBars(self, bars_):
                ds = self.getFeed()[INST]
                last = ds[-1]
                calls.append({"seen": len(ds), "last_t_ns": ns_of(last.getDateTime()), "last_close": float(last.getClose())})
        S().run()
        return {"calls": calls}

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        a = adj(c)
        sig = signal_map(inp)
        maker = cfg["execution"] == "maker"
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]
        bars = inp["bars"]
        dt2k = {}
        feed = _Feed(bar.Frequency.MINUTE)
        seq = []
        for k, b in enumerate(bars):
            t = to_dt(b["t_ns"])
            dt2k[t] = k
            seq.append(bar.BasicBar(t, b["open"], b["high"], b["low"], b["close"], b["volume"], b["close"],
                                    bar.Frequency.MINUTE))
        feed.addBarsFromSequence(INST, seq)
        rec = {"fills": [], "equity": [], "missed": 0}

        class Fee(backtesting.Commission):
            def calculate(self, order, price, quantity):
                pct = c["maker_fee_pct"] if order.getType() == pbroker.Order.Type.LIMIT else c["taker_fee_pct"]
                return price * quantity * pct / 100

        class Slip(slippage.SlippageModel):
            def calculatePrice(self, order, price, quantity, bar_, volumeUsed):
                return price * (1 + a) if order.isBuy() else price * (1 - a)

        brk = _Broker(float(cfg["initial_equity"]), feed, Fee())
        fs = fillstrategy.DefaultStrategy(volumeLimit=None)
        fs.setSlippageModel(Slip())
        brk.setFillStrategy(fs)

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        class S(strategy.BacktestingStrategy):
            def __init__(self):
                super().__init__(feed, brk)
                self.tags = {}
                self.brackets = []
                self.limit = None
                self.entry_bar = None
                self.level = None
                self.k = -1

            def _pos(self):
                return self.getBroker().getShares(INST)

            def _submit(self, o, tag):
                self.tags[id(o)] = tag
                self.getBroker().submitOrder(o)
                return o

            def _mkt(self, action, qty, tag):
                o = self.getBroker().createMarketOrder(action, INST, qty)
                return self._submit(o, tag)

            def _flatten(self):
                for o in self.brackets:
                    if o.isActive():
                        self.getBroker().cancelOrder(o)
                self.brackets = []
                p = self._pos()
                if p > 0:
                    self._mkt(A.SELL, p, "CLOSE_LONG")
                elif p < 0:
                    self._mkt(A.BUY_TO_COVER, -p, "CLOSE_SHORT")

            def onBars(self, bars_):
                self.k += 1
                k = self.k
                rec["equity"].append(float(self.getBroker().getEquity()))
                pos = self._pos()
                cl = bars_[INST].getClose()
                if pos and self.entry_bar is not None:
                    if N is not None and k + 1 - self.entry_bar >= N:
                        self._flatten()
                        return
                    if self.level is not None and k >= self.entry_bar and \
                            ((cl < self.level) if pos > 0 else (cl > self.level)):
                        self._flatten()
                        return
                if maker and self.limit is not None:
                    o, side, placed = self.limit
                    if not o.isActive():
                        self.limit = None
                    elif k - placed >= cfg["maker_timeout_bars"]:
                        self.getBroker().cancelOrder(o); rec["missed"] += 1; self.limit = None
                s = sig.get(k)
                if not s:
                    return
                if not maker:
                    if s == "CLOSE":
                        self._flatten() if pos else None
                        return
                    if s == "BUY":
                        if pos < 0:
                            self._flatten()
                        elif pos == 0 and entry_ok(k, "BUY"):
                            self._mkt(A.BUY, notional / cl, "OPEN_LONG")
                    else:
                        if pos > 0:
                            self._flatten()
                        elif pos == 0 and cfg["allow_short"] and entry_ok(k, "SELL"):
                            self._mkt(A.SELL_SHORT, notional / cl, "OPEN_SHORT")
                    return
                side = s if s != "CLOSE" else ("SELL" if pos > 0 else "BUY" if pos < 0 else None)
                if side is None:
                    return
                actionable = pos <= 0 if side == "BUY" else (pos > 0 or (pos == 0 and cfg["allow_short"]))
                if not (actionable or s == "CLOSE"):
                    return
                if self.limit is not None and self.limit[0].isActive():
                    self.getBroker().cancelOrder(self.limit[0])
                    if self.limit[1] != side:
                        rec["missed"] += 1
                self.limit = None
                closing = (side == "BUY" and pos < 0) or (side == "SELL" and pos > 0)
                if not closing and not entry_ok(k, side):
                    return
                if closing:
                    act, qty, tag = (A.BUY_TO_COVER, -pos, "CLOSE_SHORT") if side == "BUY" else (A.SELL, pos, "CLOSE_LONG")
                else:
                    act, qty, tag = (A.BUY, notional / cl, "OPEN_LONG") if side == "BUY" else (A.SELL_SHORT, notional / cl, "OPEN_SHORT")
                o = self.getBroker().createLimitOrder(act, INST, cl, qty)
                o.setGoodTillCanceled(True)
                self.limit = (self._submit(o, tag), side, k)

            def onOrderUpdated(self, o):
                ex = o.getExecutionInfo()
                if o.getState() != pbroker.Order.State.FILLED or ex is None:
                    return
                k = dt2k[ex.getDateTime()]
                tag = self.tags.get(id(o))
                rec["fills"].append({"bar": k, "side": tag, "price": float(ex.getPrice()), "size": float(ex.getQuantity())})
                if tag and tag.startswith("OPEN_"):
                    self._after_entry(k, float(ex.getPrice()), float(ex.getQuantity()), tag == "OPEN_LONG")
                else:
                    for b in self.brackets:
                        if b is not o and b.isActive():
                            self.getBroker().cancelOrder(b)
                    self.brackets, self.entry_bar, self.level = [], None, None

            def _after_entry(self, k, px, qty, long):
                self.entry_bar = k
                if W is not None:
                    lo = max(0, k - W)
                    self.level = (min(bars[j]["low"] for j in range(lo, k)) if long else
                                  max(bars[j]["high"] for j in range(lo, k))) if k > lo else None
                act = A.SELL if long else A.BUY_TO_COVER
                tag = "CLOSE_LONG" if long else "CLOSE_SHORT"
                brk_ = self.getBroker()
                if cfg["stop_loss_pct"]:
                    lvl = px * (1 - cfg["stop_loss_pct"] / 100) if long else px * (1 + cfg["stop_loss_pct"] / 100)
                    o = brk_.createStopOrder(act, INST, lvl, qty); o.setGoodTillCanceled(True)
                    self.brackets.append(self._submit(o, tag))
                for pct in (cfg["take_profit_pct"], cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None):
                    if pct:
                        lvl = px * (1 + pct / 100) if long else px * (1 - pct / 100)
                        o = brk_.createLimitOrder(act, INST, lvl, qty); o.setGoodTillCanceled(True)
                        self.brackets.append(self._submit(o, tag))

        try:
            st = S()
            ta = tradesan.Trades()
            st.attachAnalyzer(ta)
            st.run()
        except NotExpressible:
            raise
        except KeyError as exc:
            raise NotExpressible(f"{self.TOOL}: 約定の時刻を足に対応づけられない: {exc}") from exc
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        fills = sorted(rec["fills"], key=lambda f: (f["bar"], 0 if str(f["side"]).startswith("CLOSE") else 1))
        return want(inp, {"fills": fills, "pnls": [float(x) for x in ta.getAll()], "equity": rec["equity"],
                          "missed_fills": rec["missed"]})


TARGET = PyAlgoTradeAdapter()
