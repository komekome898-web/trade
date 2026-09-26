"""Survey candidate 55 `backtesting.py` (PyPI backtesting 0.6.6, venv item_0/backtesting) for the item 4 battery.

Public API used: `Backtest(data, Strategy, cash=, commission=, spread=, trade_on_close=False, hedging=False,
exclusive_orders=False)`, `Strategy.next`, `buy/sell(size=, limit=)`, `position.close()`, `Order.cancel()`,
`Trade.sl` / `Trade.tp` setters, `trades` / `closed_trades` (entry_bar, exit_bar, entry_price, exit_price,
size, pl), `stats._equity_curve`.

Scene -> tool:
- market orders sent in `next()` of bar i fill at bar i+1's open (trade_on_close=False, the tool's default);
- size: the tool takes whole units or a fraction of the available margin (backtesting.py 966-981 行: a
  fraction becomes int(margin x fraction // (adjusted price + commission per unit)); `assert size == round(size)`);
  an entry is sent as the fraction order_notional / equity (the only way to size at the fill price);
- fee -> `commission=pct/100` (relative, charged at entry and at exit); spread / 2 + slippage -> `spread=`
  (the tool adjusts the ENTRY price only, 838-843 行);
- stop_loss / take_profit / maker_tp -> `Trade.sl` / `Trade.tp` set in `next()` of the entry bar (active from
  the next bar); execution "maker" -> `buy/sell(limit=close)` cancelled by the strategy after
  maker_timeout_bars bars; max_hold_bars / wick_invalidation / entry filters -> strategy code.
Not expressible: a signal at bar 0 (next() is first called at bar 1: 1333 行), swap_daily_pct (no carry / financing in the tool: grep swap|financ|interest 0 件),
different maker / taker fees on a run with both kinds, the 12 metrics, op metrics / split / pipeline,
reference, models.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, adj, bars_frame, fee_kinds, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

from backtesting import Backtest, Strategy  # noqa: E402


class BacktestingAdapter(Base):
    name = "opp_backtesting"
    TOOL = "backtesting.py 0.6.6"
    SUPPORTS = {"allow_short", "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct", "execution",
                "stop_loss_pct", "take_profit_pct", "max_hold_bars", "exit_execution", "maker_tp_pct", "entry_mask",
                "entry_sides", "stop_mode", "stop_window_bars"}
    MISSING = {"swap_daily_pct": "持ち越し・資金調達・金利の口を探したが無い(backtesting/ の grep swap・financ・interest・borrow 0 件)"}
    METRICS = ("指標は Backtest.run の結果(_stats.compute_stats)で、12 の指標のうち平均勝ち・平均負け・RR・手数料の合計を"
               "円で出す口が無い(出るのは Win Rate・Profit Factor・Expectancy [%]・Sharpe(日次の年率)・Max. Drawdown ほか)")
    SPLIT = "行の割合で分ける口を探したが無い(backtesting/lib.py の関数は resample_apply・crossover・barssince ほかで分割は無い)"
    PIPELINE = ("入力はメモリ上の OHLC の DataFrame 1 本(Backtest(data=...))で、ファイルを宣言で読む口・約定/気配/板の入力・"
                "実行記録・指標の書き出しの目的・ダッシュボードを探したが無い")

    def extra_gate(self, inp):
        out = []
        cfg, c = inp["config"], inp["config"]["costs"]
        if len(fee_kinds(cfg)) == 2 and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("maker と taker で違う手数料: commission は 1 つ(Backtest(commission=)、_Broker の _commission)で、"
                       "注文の種類で分ける口が無い")
        if "metrics" in (inp.get("want") or []):
            out.append(self.METRICS)
        if any(int(x["bar"]) == 0 for x in inp.get("signals", [])):
            out.append("足 0 の合図: 道具は最初の足で Strategy.next を呼ばない(backtesting.py 1333 行 start = 1 + "
                       "_indicator_warmup_nbars、1339 行 range(start, len(data)))")
        return out

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        a = adj(c)
        df = bars_frame(inp, pd).rename(columns=str.capitalize)
        sig = signal_map(inp)
        maker = cfg["execution"] == "maker"
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]
        rec = {"missed": 0}

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        class S(Strategy):
            def init(self):
                self.limit = None  # (order, side, placed)
                self.seen = set()
                self.level = None

            def next(self):
                k = len(self.data) - 1
                pos = self.position.size
                for t in self.trades:  # a new trade (filled at this bar's open or earlier this bar): set its exits
                    if id(t) in self.seen:
                        continue
                    self.seen.add(id(t))
                    long, px = t.is_long, t.entry_price
                    if cfg["stop_loss_pct"]:
                        t.sl = px * (1 - cfg["stop_loss_pct"] / 100) if long else px * (1 + cfg["stop_loss_pct"] / 100)
                    tp = cfg["take_profit_pct"] or (cfg["maker_tp_pct"] if cfg["exit_execution"] == "maker_tp" else None)
                    if tp:
                        t.tp = px * (1 + tp / 100) if long else px * (1 - tp / 100)
                    if W is not None:
                        b = t.entry_bar
                        lo = max(0, b - W)
                        self.level = (float(min(self.data.Low[lo:b])) if long else float(max(self.data.High[lo:b]))) \
                            if b > lo else None
                if not self.trades:
                    self.level = None
                if maker and self.limit is not None:
                    o = self.limit[0]
                    if o not in self.orders:
                        self.limit = None
                    elif k - self.limit[2] >= cfg["maker_timeout_bars"]:
                        o.cancel(); rec["missed"] += 1; self.limit = None
                if pos and self.trades:
                    t = self.trades[-1]
                    if N is not None and k + 1 - t.entry_bar >= N:
                        self.position.close()  # fills at the next open = bar entry + N
                        return self._decide(k, pos, blocked=True)
                    if self.level is not None and k >= t.entry_bar:
                        cl = self.data.Close[-1]
                        if (cl < self.level) if pos > 0 else (cl > self.level):
                            self.position.close()
                            return self._decide(k, pos, blocked=True)
                self._decide(k, pos)

            def _frac(self):
                return min(notional / self.equity, 0.999999)

            def _decide(self, k, pos, blocked=False):
                s = sig.get(k)
                if not s or blocked:
                    return
                if not maker:
                    if s == "CLOSE":
                        if pos:
                            self.position.close()
                        return
                    if s == "BUY":
                        if pos < 0:
                            self.position.close()
                        elif pos == 0 and entry_ok(k, "BUY"):
                            self.buy(size=self._frac())
                    else:
                        if pos > 0:
                            self.position.close()
                        elif pos == 0 and cfg["allow_short"] and entry_ok(k, "SELL"):
                            self.sell(size=self._frac())
                    return
                side = s if s != "CLOSE" else ("SELL" if pos > 0 else "BUY" if pos < 0 else None)
                if side is None:
                    return
                actionable = pos <= 0 if side == "BUY" else (pos > 0 or (pos == 0 and cfg["allow_short"]))
                if not (actionable or s == "CLOSE"):
                    return
                if self.limit is not None:
                    self.limit[0].cancel()
                    if self.limit[1] != side:
                        rec["missed"] += 1
                    self.limit = None
                px = float(self.data.Close[-1])
                closing = (side == "BUY" and pos < 0) or (side == "SELL" and pos > 0)
                if not closing and not entry_ok(k, side):
                    return
                size = abs(pos) if closing else self._frac()
                o = (self.buy if side == "BUY" else self.sell)(size=size, limit=px)
                self.limit = (o, side, k)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fee = c["taker_fee_pct"] if "taker" in fee_kinds(cfg) else c["maker_fee_pct"]
                bt = Backtest(df, S, cash=float(cfg["initial_equity"]), commission=float(fee) / 100, spread=a,
                              trade_on_close=False, hedging=False, exclusive_orders=False)
                st = bt.run()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {exc}") from exc
        strat = st._strategy
        fills, pnls = [], []
        for t in list(strat.closed_trades) + list(strat.trades):
            d = "LONG" if t.is_long else "SHORT"
            fills.append({"bar": int(t.entry_bar), "side": f"OPEN_{d}", "price": float(t.entry_price),
                          "size": float(abs(t.size))})
            if t.exit_bar is not None:
                fills.append({"bar": int(t.exit_bar), "side": f"CLOSE_{d}", "price": float(t.exit_price),
                              "size": float(abs(t.size))})
                pnls.append((int(t.exit_bar), float(t.pl)))
        fills.sort(key=lambda f: (f["bar"], 0 if f["side"].startswith("CLOSE") else 1))
        eq = [float(x) for x in st._equity_curve["Equity"].tolist()]
        return want(inp, {"fills": fills, "pnls": [p for _, p in sorted(pnls, key=lambda x: x[0])], "equity": eq,
                          "missed_fills": rec["missed"]})


TARGET = BacktestingAdapter()
