"""Reproduction of survey candidate 80 `Hummingbot` -- the strategy-v2 backtesting engine's position executor
simulation -- for the item 4 battery.  Not installed: `pip install hummingbot` failed to build (dry run:
opponents/attempts/i4_r1_scenekeeper_dryrun_resolution.log).

Primary source (read only), commit 9af100d6822da7d2d0291a906c730ef172284ee2:
  https://github.com/hummingbot/hummingbot/blob/9af100d6822da7d2d0291a906c730ef172284ee2/hummingbot/strategy_v2/backtesting/backtesting_engine_base.py
  https://github.com/hummingbot/hummingbot/blob/9af100d6822da7d2d0291a906c730ef172284ee2/hummingbot/strategy_v2/backtesting/executors_simulator/position_executor_simulator.py
Rules taken:
- `simulate_execution` (backtesting_engine_base.py 269-298): on each row the controller's actions are applied; a
  CreateExecutorAction is simulated on the rows from THIS row on (`processed_features.loc[i:max_ts]`, 287); a
  StopExecutorAction ends the executor at this row (handle_stop_action 568-600: EARLY_STOP, its net PnL at this row).
- PositionExecutorSimulator.simulate (position_executor_simulator.py 10-88): a market entry starts at the first row
  (its CLOSE is the entry price, 37); a limit entry starts at the first row whose close <= the entry price for a buy
  (>= for a sell) and still takes that row's close (12-14, 37).  From there net_pnl_pct = cumulative close-to-close
  return x side - 2 x trade_cost (41-44).  Take profit: the first row with net_pnl_pct > tp (57); stop loss: the first
  row whose low <= entry x (1 - sl) (high >= entry x (1 + sl) for a sell) (59-63); time limit: the row at
  timestamp + time_limit (24, 28); the earliest of them closes (66), ties go to take profit, then stop loss (68-76).
  The result is net_pnl_quote = net_pnl_pct x amount x entry price (45-47), i.e. an exit at that row's close.
- One `trade_cost` for every trade (run_backtesting 225, simulate 10).
Observed here: `pnls` = the executor's net_pnl_quote at its close row (an output of the tool); `fills` are the entry
row's close and the close row's close, the prices the simulation's PnL is built on (37, 41-47) -- the executor
simulation has no fill list, so they are an instrumentation of the rewrite, not an output of the tool.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i4_base import Base, NotExpressible, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

SRC = "strategy_v2/backtesting(9af100d6)"


class Hummingbot(Base):
    name = "opp_repro_80_hummingbot"
    TOOL = "Hummingbot strategy_v2 backtesting(9af100d6)(再現)"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_loss_pct", "take_profit_pct",
                "execution", "taker_fee_pct", "maker_fee_pct"}
    MISSING = {
        "slippage_pct": f"滑り・スプレッドの口が無い(損益は終値の比と trade_cost だけ: {SRC} position_executor_simulator.py 41-47 行)",
        "spread_pct": f"滑り・スプレッドの口が無い(position_executor_simulator.py 41-47 行)",
        "swap_daily_pct": "持ち越しの口が無い(position_executor_simulator.py 41-47 行)",
        "stop_mode": "足の安値の窓で置く逆指値の型が無い(三重の障壁は率の逆指値・利確・時間・追いかけの逆指値だけ: 17-24 行)",
        "stop_window_bars": "足の安値の窓で置く逆指値の型が無い(17-24 行)",
        "exit_execution": "決済を指値で置く口が無い(決済は障壁に当たった行の終値: 45-47・78-80 行)",
        "maker_tp_pct": "決済を指値で置く口が無い(45-47 行)"}
    METRICS = "再現していない: summarize_results(602 行〜)は読み始めたが、12 の指標と同じ形の出力は無い(総損益・手数料の集計)"
    SPLIT = "行の割合で分ける口が無い"
    PIPELINE = "再現は位置の executor の模擬だけ"

    def extra_gate(self, inp):
        out = []
        cfg = inp["config"]
        c = cfg["costs"]
        if cfg["execution"] == "maker" and c["maker_fee_pct"] != c["taker_fee_pct"]:
            out.append("trade_cost は 1 つだけで、maker と taker に別の率を置く口が無い(run_backtesting 225 行)")
        w = set(inp.get("want") or [])
        if "equity" in w:
            out.append("再現していない: 行ごとの net_pnl_quote(45 行)から資産の系列を作る結果の処理は読んでいない")
        if "metrics" in w:
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        cost = (cfg["costs"]["maker_fee_pct"] if cfg["execution"] == "maker" else cfg["costs"]["taker_fee_pct"]) / 100
        tp = cfg["take_profit_pct"] / 100 if cfg["take_profit_pct"] else None
        sl = cfg["stop_loss_pct"] / 100 if cfg["stop_loss_pct"] else None
        N = cfg["max_hold_bars"]
        fills, pnls, missed = [], [], 0
        ex = None      # the active executor: dict(created, side, amount, start, close_row, close_type)
        i = 0

        def simulate(created, side, amount, limit_px):
            if limit_px is not None:
                cond = (lambda k: bars[k]["close"] <= limit_px) if side > 0 else (lambda k: bars[k]["close"] >= limit_px)
                start = next((k for k in range(created, n) if cond(k)), None)
            else:
                start = created
            last = n - 1
            tl = created + N if N is not None else last
            tl = min(tl, last)
            if start is None or start > tl:
                return {"created": created, "side": side, "amount": amount, "start": None, "close": tl}
            entry = bars[start]["close"]
            cum, prod = [], 1.0
            for k in range(start, tl + 1):
                if k > start:
                    prod *= 1 + (bars[k]["close"] / bars[k - 1]["close"] - 1)
                cum.append(((prod - 1) * side) - 2 * cost)
            rows = list(range(start, tl + 1))
            first_tp = next((k for k, v in zip(rows, cum) if tp is not None and v > tp), None)
            first_sl = None
            if sl is not None:
                slp = entry * (1 - sl * side)
                first_sl = next((k for k in rows if (bars[k]["low"] <= slp if side > 0 else bars[k]["high"] >= slp)), None)
            close = min(x for x in (first_tp, first_sl, tl) if x is not None)
            return {"created": created, "side": side, "amount": amount, "start": start, "entry": entry,
                    "close": close, "cum": dict(zip(rows, cum))}

        def book(e, row):
            if e["start"] is None or row < e["start"]:
                return False
            d = e["side"]
            fills.append({"bar": e["start"], "side": "OPEN_LONG" if d > 0 else "OPEN_SHORT", "price": e["entry"], "size": e["amount"]})
            fills.append({"bar": row, "side": "CLOSE_LONG" if d > 0 else "CLOSE_SHORT", "price": bars[row]["close"], "size": e["amount"]})
            pnls.append(e["cum"][row] * e["amount"] * e["entry"])
            return True

        for i in range(n):
            if ex is not None and ex["close"] <= i and (ex["start"] is not None or ex["close"] < i):
                if not book(ex, ex["close"]) and cfg["execution"] == "maker":
                    missed += 1
                ex = None
            s = sig.get(i)
            if ex is not None:
                if ex["start"] is None and cfg["execution"] == "maker" and i >= ex["created"] + cfg["maker_timeout_bars"]:
                    missed += 1
                    ex = None
                elif ex["start"] is not None and ex["start"] <= i and ex["close"] >= i and s and (
                        s == "CLOSE" or (s == "BUY") != (ex["side"] > 0)):
                    book(ex, i)      # StopExecutorAction: EARLY_STOP at this row
                    ex = None
                    continue
                elif ex["start"] is None and s and s != ("BUY" if ex["side"] > 0 else "SELL"):
                    missed += 1
                    ex = None
            if ex is not None or not s or s == "CLOSE":
                continue
            if s == "SELL" and not cfg["allow_short"]:
                continue
            if cfg["entry_sides"] == "long" and s == "SELL" or cfg["entry_sides"] == "short" and s == "BUY":
                continue
            if cfg["entry_mask"] is not None and not cfg["entry_mask"][i]:
                continue
            side = 1 if s == "BUY" else -1
            ref = bars[i]["close"]
            ex = simulate(i, side, cfg["order_notional"] / ref, ref if cfg["execution"] == "maker" else None)
        if ex is not None:
            if ex["start"] is not None:
                book(ex, ex["close"])
            elif cfg["execution"] == "maker":
                missed += 1
        return want(inp, {"fills": fills, "pnls": pnls, "missed_fills": missed})


TARGET = Hummingbot()
