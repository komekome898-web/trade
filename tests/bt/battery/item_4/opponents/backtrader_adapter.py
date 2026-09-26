"""Survey candidate 2 `Backtrader` (PyPI backtrader 1.9.78.123, venv item_0/backtrader) for the item 4 battery.

Public API used: `Cerebro(cheat_on_open=True)`, `feeds.PandasData`, `Strategy` (`next_open`, `next`,
`notify_order`, `notify_trade`, `buy`, `sell`, `close`, `cancel`, `position`), `broker.setcash`,
`broker.setcommission(commission=)`, `broker.set_slippage_perc`, `Order.Market / Limit / Stop`, `oco=`.

Scene -> tool:
- the script's signal at bar i is acted on in `next_open` of bar i+1 (cheat-on-open: the order is sent
  before bar i+1 executes and fills at its open); an entry is sized size = notional / (open x (1 +- adj))
  from the declared cost rates, so that size x fill = notional (the strategy's own sizing);
- spread / 2 + slippage -> `set_slippage_perc(perc, slip_open=True, slip_limit=False, slip_out=True)`; the fee ->
  `setcommission(commission=pct/100)` (one rate per data feed: the taker rate, or the maker rate when every
  fill of the run is a maker fill);
- stop_loss_pct / take_profit_pct / maker_tp_pct -> a Stop and Limit order pair (oco) sent when the entry
  fills (Backtrader processes them from the next bar); the Stop is sent first;
- execution "maker" -> a Limit order at the decision bar's close, cancelled by the strategy when it has
  rested maker_timeout_bars bars; a resting order replaced by a signal of the other side is cancelled;
- max_hold_bars / stop_mode "wick_invalidation" / entry_mask / entry_sides -> strategy code (bar counting,
  the level from completed bars' lows / highs, a close beyond it -> market close at the next open; entry filters).
Not expressible (NotExpressible): swap_daily_pct, a maker fee different from the taker fee on a run that can
make both kinds of fill, the 12 metrics (want "metrics"), op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, adj, bars_frame, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

import backtrader as bt  # noqa: E402

BT_DIR = Path(bt.__file__).parent


class BacktraderAdapter(Base):
    name = "opp_backtrader"
    TOOL = "Backtrader 1.9.78.123"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct", "execution",
                "stop_loss_pct", "take_profit_pct", "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask",
                "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"swap_daily_pct": "持ち越しの口は CommInfoBase の interest だけで、暦日の差で数える"
                                 "(comminfo.py 92 行「days * price * abs(size) * (interest / 365)」、274 行 _get_credit_interest)。"
                                 "足ごとに前の足の終値で掛ける口は無い"}
    METRICS = ("指標は Cerebro の実行に付ける analyzer(analyzers/sharpe.py・drawdown.py・tradeanalyzer.py)で、"
               "外から与えた決済ごとの損益と資産の列を受ける関数の口を探したが無い")
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い(grep split・walk 0 件、backtrader/ の全体)"
    PIPELINE = ("宣言でファイルを読む口は GenericCSVData(feeds/csvgeneric.py)の足の CSV だけで、気配(買いは ask・売りは bid)の"
                "feed の型、板の feed の型、実行記録・指標の書き出しの目的・ダッシュボードの項目別タブを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        kinds = fee_kinds(cfg)
        if len(kinds) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: 手数料は data feed ごとに 1 つ(brokers/bbroker.py 703 行 "
                       "comminfo = self.getcommissioninfo(order.data))で、注文の種類で分ける口が無い")
        if "metrics" in (inp.get("want") or []):
            out.append("12 の指標: analyzer は総損益・回数・勝ち負けの数と平均・連敗・最大下落・シャープを出すが"
                       "(analyzers/tradeanalyzer.py 88-136 行、drawdown.py 58 行、sharpe.py 143-199 行)、勝率・PF・RR・期待値・"
                       "手数料の合計を出す口は無い(adapter は道具が出していない値を計算しない)")
        return out

    def delivery(self, inp):
        """What Backtrader hands Strategy.next: the data feed's lines up to the current bar (len, datetime[0], close[0])."""
        from _i4_base import ns_of
        df = bars_frame(inp, pd)
        df["openinterest"] = 0.0
        calls = []

        class S(bt.Strategy):
            def next(self):
                calls.append({"seen": len(self.data), "last_t_ns": ns_of(self.data.datetime.datetime(0)),
                              "last_close": float(self.data.close[0])})
        cer = bt.Cerebro(stdstats=False)
        cer.adddata(bt.feeds.PandasData(dataname=df))
        cer.addstrategy(S)
        cer.run()
        return {"calls": calls}

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        a = adj(c)
        df = bars_frame(inp, pd)
        df["openinterest"] = 0.0
        n = len(df)
        sig = signal_map(inp)
        num2k = {}
        rec = {"fills": [], "pnls": [], "equity": [], "missed": 0}
        maker = cfg["execution"] == "maker"
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            if mask is not None and not mask[db]:
                return False
            return True

        class S(bt.Strategy):
            def __init__(self):
                self.pending = None
                self.entry_bar = None
                self.brackets = []
                self.limit = None  # (order, side, placed_bar)
                self.level = None
                self.breach = False

            def _k(self):
                return len(self) - 1

            def _cancel_brackets(self):
                for o in self.brackets:
                    if o.alive():
                        self.cancel(o)
                self.brackets = []

            def _cancel_limit(self, count):
                if self.limit is not None and self.limit[0].alive():
                    self.cancel(self.limit[0])
                    if count:
                        rec["missed"] += 1
                self.limit = None

            def _flatten(self):
                self._cancel_brackets()
                pos = self.position.size
                if pos:
                    o = self.close()
                    o.addinfo(tag="CLOSE_LONG" if pos > 0 else "CLOSE_SHORT")

            def _open(self, d):
                px = self.data.open[0]
                size = notional / (px * (1 + a)) if d > 0 else notional / (px * (1 - a))
                o = (self.buy if d > 0 else self.sell)(size=size, exectype=bt.Order.Market)
                o.addinfo(tag="OPEN_LONG" if d > 0 else "OPEN_SHORT")

            def next_open(self):
                k = self._k()
                pos = self.position.size
                exited = False
                if pos and self.breach:
                    self._flatten(); exited = True
                elif pos and N is not None and self.entry_bar is not None and k - self.entry_bar >= N:
                    self._flatten(); exited = True
                self.breach = False
                if exited:
                    self.pending = None
                    self._cancel_limit(False)
                    return
                if self.pending is None or maker:
                    return
                s, db = self.pending
                self.pending = None
                if s == "CLOSE":
                    s = "SELL" if pos > 0 else "BUY" if pos < 0 else None
                if s == "BUY":
                    if pos < 0:
                        self._flatten()
                    elif pos == 0 and entry_ok(db, "BUY"):
                        self._open(+1)
                elif s == "SELL":
                    if pos > 0:
                        self._flatten()
                    elif pos == 0 and cfg["allow_short"] and entry_ok(db, "SELL"):
                        self._open(-1)

            def next(self):
                k = self._k()
                rec["equity"].append(float(self.broker.getvalue()))
                pos = self.position.size
                if self.level is not None and pos and self.entry_bar is not None and k >= self.entry_bar:
                    cl = self.data.close[0]
                    if (cl < self.level) if pos > 0 else (cl > self.level):
                        self.breach = True
                if maker and self.limit is not None and self.limit[0].alive() \
                        and k - self.limit[2] >= cfg["maker_timeout_bars"]:
                    self._cancel_limit(True)
                s = sig.get(k)
                if not s:
                    return
                if not maker:
                    if s == "CLOSE" and pos == 0:
                        return
                    self.pending = (s, k)
                    return
                side = s
                if s == "CLOSE":
                    side = "SELL" if pos > 0 else "BUY" if pos < 0 else None
                if side is None:
                    return
                actionable = pos <= 0 if side == "BUY" else (pos > 0 or (pos == 0 and cfg["allow_short"]))
                if not (actionable or s == "CLOSE"):
                    return
                if self.limit is not None and self.limit[0].alive():
                    self._cancel_limit(self.limit[1] != side)
                px = self.data.close[0]
                closing = (side == "BUY" and pos < 0) or (side == "SELL" and pos > 0)
                if not closing and not entry_ok(k, side):
                    return
                size = abs(pos) if closing else notional / px
                o = (self.buy if side == "BUY" else self.sell)(size=size, price=px, exectype=bt.Order.Limit)
                o.addinfo(tag=("CLOSE_SHORT" if side == "BUY" else "CLOSE_LONG") if closing else
                          ("OPEN_LONG" if side == "BUY" else "OPEN_SHORT"))
                self.limit = (o, side, k)

            def notify_order(self, o):
                if o.status == o.Completed and o.executed.size:
                    k = num2k[o.executed.dt]
                    tag = o.info.get("tag")
                    rec["fills"].append({"bar": k, "side": tag, "price": float(o.executed.price),
                                         "size": float(abs(o.executed.size))})
                    if self.limit is not None and o is self.limit[0]:
                        self.limit = None
                    if tag and tag.startswith("OPEN_"):
                        self._after_entry(k, float(o.executed.price), float(abs(o.executed.size)), tag == "OPEN_LONG")
                    elif tag and tag.startswith("CLOSE_"):
                        self._cancel_brackets()
                        self._cancel_limit(False)
                        self.entry_bar, self.level = None, None

            def _after_entry(self, k, px, size, long):
                self.entry_bar = k
                if W is not None:
                    lo = max(0, k - W)
                    ago = range(1, k - lo + 1)
                    self.level = (min(self.data.low[-j] for j in ago) if long else max(self.data.high[-j] for j in ago)) \
                        if k > lo else None
                exit_ = self.sell if long else self.buy
                tag = "CLOSE_LONG" if long else "CLOSE_SHORT"
                first = None
                if cfg["stop_loss_pct"]:
                    lvl = px * (1 - cfg["stop_loss_pct"] / 100) if long else px * (1 + cfg["stop_loss_pct"] / 100)
                    first = exit_(size=size, price=lvl, exectype=bt.Order.Stop)
                    first.addinfo(tag=tag)
                    self.brackets.append(first)
                for pct in (cfg["take_profit_pct"], cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None):
                    if pct is None:
                        continue
                    lvl = px * (1 + pct / 100) if long else px * (1 - pct / 100)
                    o = exit_(size=size, price=lvl, exectype=bt.Order.Limit, oco=first)
                    o.addinfo(tag=tag)
                    first = first or o
                    self.brackets.append(o)

            def notify_trade(self, trade):
                if trade.isclosed:
                    rec["pnls"].append(float(trade.pnlcomm))

        try:
            cer = bt.Cerebro(stdstats=False, cheat_on_open=True)
            data = bt.feeds.PandasData(dataname=df)
            cer.adddata(data)
            cer.broker.setcash(float(cfg["initial_equity"]))
            fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]
            cer.broker.setcommission(commission=float(fee) / 100)
            if a:  # the cost is a price adjustment, not bounded by the bar's range (slip_out=True)
                cer.broker.set_slippage_perc(a, slip_open=True, slip_limit=False, slip_match=True, slip_out=True)
            cer.addstrategy(S)
            for i, t in enumerate(df.index):
                num2k[bt.date2num(t.to_pydatetime())] = i
            cer.run()
        except NotExpressible:
            raise
        except KeyError as exc:
            raise NotExpressible(f"{self.TOOL}: 約定の時刻を足に対応づけられない: {exc}") from exc
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        if len(rec["equity"]) != n:
            raise NotExpressible(f"{self.TOOL}: next が {len(rec['equity'])} 回しか呼ばれなかった(足 {n} 本)")
        rec["fills"].sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        return want(inp, {"fills": rec["fills"], "pnls": rec["pnls"], "equity": rec["equity"],
                          "missed_fills": rec["missed"]})


TARGET = BacktraderAdapter()
