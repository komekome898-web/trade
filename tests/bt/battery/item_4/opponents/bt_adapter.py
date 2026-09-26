"""Survey candidate 5 (the catalogue's name "Lean CLI"; the survey report's line for number 5, SCAN 6849 行, is the
PyPI package `bt`, as item 2 recorded) -- `bt` 1.2.3, venv item_2/bt -- for the item 4 battery.

The tool's own parts used: `bt.Strategy(name, [algos])` with one user Algo (the tool's plug: called with the strategy
on each date) that calls the strategy's `transact(q, child="X")` (a quantity traded at the date's price),
`bt.Backtest(strategy, data, initial_capital, commissions=f(q, p), integer_positions=False)`, `bt.run`, and the
result's `get_transactions()`.

Scene -> tool: the data is the bars' OPEN prices, one row per bar, so a trade on the row of bar i+1 is at bar i+1's
open: the Algo trades on the row after the decision bar (the date's price is known to the Algo, so an entry is
sized q = order_notional / that price).  BUY when short / SELL when long / CLOSE -> the opposite quantity; BUY / SELL
when flat -> an entry; max_hold_bars, wick_invalidation (the level from the scene bars the strategy has seen) and
entry filters are strategy code.  One commission function f(q, p) = rate x |q| x p.  Not expressible: slippage /
spread (bt has none), a maker fee different from the taker fee, stop / limit / maker orders (bt's trades are
quantities at the date's price), swap, per-trade PnL, an equity series at the bars' closes (the data given is the
open prices), metrics, op metrics / split / pipeline, reference, models.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import pandas as pd  # noqa: E402

from _i4_base import Base, NotExpressible, Refused, to_dt, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

import bt  # noqa: E402

NO_ORDER = "指値・逆指値の注文の口を探したが無い(bt の取引は日時の値での数量: Strategy.transact)"


class BtAdapter(Base):
    name = "opp_bt"
    TOOL = "bt 1.2.3"
    SUPPORTS = {"allow_short", "taker_fee_pct", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode",
                "stop_window_bars"}
    MISSING = {"slippage_pct": "滑りの口を探したが無い(Backtest の引数は commissions だけ)",
               "spread_pct": "スプレッドの口を探したが無い", "maker_fee_pct": NO_ORDER, "execution": NO_ORDER,
               "stop_loss_pct": NO_ORDER, "take_profit_pct": NO_ORDER, "exit_execution": NO_ORDER, "maker_tp_pct": NO_ORDER,
               "swap_daily_pct": "持ち越しの口を探したが無い"}
    METRICS = "12 の指標: 結果の stats(ffn)は値の系列の統計で、決済ごとの損益・勝率・PF の口が無い"
    SPLIT = "行の割合で分ける口を探したが無い"
    PIPELINE = "入力は価格の表(DataFrame)1 つで、宣言でファイルを読む口・約定/気配/板・実行記録・目的つきの書き出し・ダッシュボードが無い"

    def extra_gate(self, inp):
        out = []
        w = set(inp.get("want") or [])
        for k, why in (("pnls", "決済ごとの損益の口を探したが無い(get_transactions は約定の値と数量)"),
                       ("equity", "足の終値での資産の推移を出す口が無い(渡すのは始値の表で、values は始値での評価)"),
                       ("missed_fills", "待つ注文が無いので取り逃しも無い"), ("metrics", self.METRICS)):
            if k in w:
                out.append(why)
        return out

    def delivery(self, inp):
        """What bt hands an Algo: target.universe (the price table up to target.now).  bt takes one price per row, so
        the table is the closes."""
        from _i4_base import ns_of
        idx = pd.DatetimeIndex([to_dt(b["t_ns"]) for b in inp["bars"]])
        calls = []

        class Rec(bt.Algo):
            def __call__(self, target):
                u = target.universe["X"]
                calls.append({"seen": len(u), "last_t_ns": ns_of(u.index[-1]), "last_close": float(u.iloc[-1])})
                return True
        data = pd.DataFrame({"X": [float(b["close"]) for b in inp["bars"]]}, index=idx)
        bt.run(bt.Backtest(bt.Strategy("s", [Rec()]), data, initial_capital=6000.0, progress_bar=False))
        return {"calls": calls}

    def bars(self, inp):
        cfg, c = inp["config"], inp["config"]["costs"]
        bars = inp["bars"]
        sig = signal_map(inp)
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        mask = cfg["entry_mask"]
        notional = cfg["order_notional"]
        rate = c["taker_fee_pct"] / 100
        idx = pd.DatetimeIndex([to_dt(b["t_ns"]) for b in bars])
        d2k = {t: k for k, t in enumerate(idx)}
        st = {"pending": None, "entry_bar": None, "level": None, "tags": {}}

        def entry_ok(db, side):
            if cfg["entry_sides"] == "long" and side == "SELL":
                return False
            if cfg["entry_sides"] == "short" and side == "BUY":
                return False
            return mask is None or bool(mask[db])

        class Act(bt.Algo):
            def __call__(self, target):
                k = d2k[target.now]
                ch = target.children.get("X")
                pos = float(ch.position) if ch is not None else 0.0
                px = float(target.universe["X"].iloc[-1])
                act = st["pending"]
                st["pending"] = None
                exit_now = False
                if pos and st["entry_bar"] is not None:
                    if N is not None and k - st["entry_bar"] >= N:
                        exit_now = True
                    elif st["level"] is not None and k - 1 >= st["entry_bar"]:
                        cl = bars[k - 1]["close"]
                        exit_now = (cl < st["level"]) if pos > 0 else (cl > st["level"])
                if exit_now:
                    target.transact(-pos, child="X")
                    st["tags"][k] = "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT"
                    st["entry_bar"] = st["level"] = None
                elif act is not None:
                    s, db = act
                    if s == "CLOSE" or (s == "BUY" and pos < 0) or (s == "SELL" and pos > 0):
                        if pos:
                            target.transact(-pos, child="X")
                            st["tags"][k] = "CLOSE_LONG" if pos > 0 else "CLOSE_SHORT"
                            st["entry_bar"] = st["level"] = None
                    elif pos == 0 and entry_ok(db, s) and (s == "BUY" or cfg["allow_short"]):
                        q = notional / px
                        target.transact(q if s == "BUY" else -q, child="X")
                        st["tags"][k] = "OPEN_LONG" if s == "BUY" else "OPEN_SHORT"
                        st["entry_bar"] = k
                        if W is not None:
                            lo = max(0, k - W)
                            st["level"] = (min(bars[j]["low"] for j in range(lo, k)) if s == "BUY" else
                                           max(bars[j]["high"] for j in range(lo, k))) if k > lo else None
                if k in sig:
                    st["pending"] = (sig[k], k)
                return True

        data = pd.DataFrame({"X": [float(b["open"]) for b in bars]}, index=idx)
        try:
            s = bt.Strategy("s", [Act()])
            test = bt.Backtest(s, data, initial_capital=float(cfg["initial_equity"]),
                               commissions=lambda q, p: rate * abs(q) * p, integer_positions=False, progress_bar=False)
            res = bt.run(test)
            tx = res.get_transactions()
        except NotExpressible:
            raise
        except Exception as exc:
            raise Refused(f"{type(exc).__name__}: {str(exc)[:300]}") from exc
        fills = []
        for (ts, _sec), r in ([] if tx is None or len(tx) == 0 else tx.iterrows()):
            k = d2k[pd.Timestamp(ts)]
            fills.append({"bar": k, "side": st["tags"].get(k), "price": float(r["price"]),
                          "size": abs(float(r["quantity"]))})
        fills.sort(key=lambda f: (f["bar"], 0 if str(f["side"]).startswith("CLOSE") else 1))
        return want(inp, {"fills": fills})


TARGET = BtAdapter()
