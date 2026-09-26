"""Reproduction of survey candidate 60 `Hikyuu` -- the trading system `System` with its default delayed trading --
for the item 4 battery.  Not installed: 104 distributions (PySide6 and others; dry run in
opponents/attempts/i4_r1_scenekeeper_dryrun_resolution.log and item 2's RUNNABILITY row 60).

Primary source (read only), commit 5a1dedbd6934c48278cd23bb36fc838da8e67439:
  https://github.com/fasiondog/hikyuu/blob/5a1dedbd6934c48278cd23bb36fc838da8e67439/hikyuu_cpp/hikyuu/trade_sys/system/System.cpp
  .../hikyuu_cpp/hikyuu/trade_manage/TradeManager.cpp, .../trade_sys/stoploss/imp/FixedPercentStoploss.cpp,
  .../trade_sys/profitgoal/imp/FixedPercentProfitGoal.cpp, .../hikyuu_cpp/hikyuu/Stock.cpp
Rules taken (System.cpp unless named):
- Parameters `buy_delay` and `sell_delay` default to true (initParam 94-112): a buy or sell decided at a bar's close
  is sent as a request and executed at the NEXT bar's open (`_runMoment` = on-open then on-close, 497-501;
  `_processRequest` 1456-1462; `_buyDelay` planPrice = open, 777-849; `_sellDelay` 998-1068).
- On the close of a bar (`_runMomentOnClose` 528-687): a buy signal first (-> buy request), else a sell signal (->
  sell request), else, while holding: close <= the position's stop loss -> sell request (651-655), else close >=
  the profit goal -> sell request (657-663).  A signal on the last bar leaves a request no bar executes.
- With `delay_use_current_price` true (108), the stop loss, the goal and the number are computed at the open where
  the buy executes (809-818): stop loss = FixedPercentStoploss(p): roundEx(price x (1 - p), precision)
  (FixedPercentStoploss.cpp 29-33); goal while holding = buyMoney / number x (1 + p) (FixedPercentProfitGoal.cpp
  36-42); the number from the money manager (here the strategy's MM: order notional / price), cut to whole
  multiples of the stock's minTradeNumber (831-832; a user stock sets it, Stock.cpp 178-180: here 1).
- A bar with high == low delays the request when it is the first bar or its close is above (buy) / below (sell) the
  previous close (788-803, 1007-1022); a bar with zero amount or count delays it (782-786, 1001-1005).
- Cash: buy money = price x number, cash -= money + cost; sell cash += money - cost (TradeManager.cpp 856, 949),
  rounded to the manager's `precision` (a parameter the user sets; here 8).  The cost is the user's trade-cost part
  (here rate x money on each side).
- Not reproduced: short selling (the short paths 1098-1250 were not read in full), the slippage part (SP: not read).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i4_base import Base, want  # noqa: E402
from i4_protocol import signal_map  # noqa: E402

SRC = "hikyuu_cpp/hikyuu/trade_sys/system/System.cpp(5a1dedbd)"
PREC = 8


def round_ex(x, d=PREC):
    return round(x, d)


class Hikyuu(Base):
    name = "opp_repro_60_hikyuu"
    TOOL = "Hikyuu System(5a1dedbd)(再現)"
    SUPPORTS = {"max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars", "stop_loss_pct",
                "take_profit_pct", "taker_fee_pct", "maker_fee_pct"}
    MISSING = {
        "allow_short": f"再現していない: 空売りの経路(_sellShort・_buyShort、{SRC} 1098-1250 行)は全部は読んでいない",
        "execution": f"指値の注文が無い(System は合図・逆指値・目標で翌足の始値に売買する要求だけ: {SRC} 689-733・919-962 行)",
        "exit_execution": f"指値の注文が無い({SRC} 919-962 行)",
        "maker_tp_pct": f"指値の注文が無い({SRC} 919-962 行)",
        "slippage_pct": "再現していない: 滑りの部品(SP)は読んでいない(約定値は _getRealBuyPrice / _getRealSellPrice を通る: 835・979 行)",
        "spread_pct": "再現していない: 滑りの部品(SP)は読んでいない",
        "swap_daily_pct": "持ち越しの口は読んだ範囲に無い(TradeManager.cpp の現金は売買・入出金・借入で動く)"}
    METRICS = "再現していない: 成績の集計(Performance)は読んでいない"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は System の遅延の売買の規則だけ"

    def extra_gate(self, inp):
        out = []
        cfg = inp["config"]
        c = cfg["costs"]
        if c["maker_fee_pct"] != c["taker_fee_pct"] and cfg["take_profit_pct"]:
            out.append("費用の部品は売りと買いの 2 つで(TradeManager.cpp 856・949 行)、maker と taker を分ける口が無い")
        w = set(inp.get("want") or [])
        if "equity" in w:
            out.append("再現していない: 資産の曲線(getFundsCurve)は読んでいない")
        if "metrics" in w:
            out.append(self.METRICS)
        return out

    def bars(self, inp):
        cfg = inp["config"]
        bars = inp["bars"]
        n = len(bars)
        sig = signal_map(inp)
        rate = cfg["costs"]["taker_fee_pct"] / 100
        slp = cfg["stop_loss_pct"] / 100 if cfg["stop_loss_pct"] else None
        pg = cfg["take_profit_pct"] / 100 if cfg["take_profit_pct"] else None
        N = cfg["max_hold_bars"]
        W = cfg["stop_window_bars"] if cfg["stop_mode"] == "wick_invalidation" else None
        cash = float(cfg["initial_equity"])
        pos = None     # dict(number, price, buy_money, cost, stoploss, bar)
        buy_req = sell_req = None
        fills, pnls = [], []
        plan_pos = False   # the strategy's own view (its signal generator does not see the tool's exits)
        plan_entry = None

        def delayed(i, buy):
            b = bars[i]
            if b["volume"] * b["close"] == 0 or b["volume"] == 0:
                return True
            if b["high"] == b["low"]:
                if i == 0:
                    return True
                return b["close"] > bars[i - 1]["close"] if buy else b["close"] < bars[i - 1]["close"]
            return False

        def stoploss_for(i, price):
            if W:
                win = bars[max(0, i - W):i]
                return min(x["low"] for x in win) if win else 0.0
            if slp is None:
                return 0.0
            b = bars[i]
            if b["high"] == b["low"]:
                return b["low"]
            return round_ex(price * (1 - slp))

        for i in range(n):
            b = bars[i]
            # on open: the pending request
            if buy_req is not None:
                if delayed(i, True):
                    buy_req["count"] += 1
                    if buy_req["count"] > 3 + 1:
                        buy_req = None
                else:
                    plan = b["open"]
                    st = stoploss_for(i, plan)
                    number = math.floor(cfg["order_notional"] / plan)
                    if plan > st and number > 0:
                        money = plan * number
                        cost = round_ex(money * rate)
                        cash = round_ex(cash - money - cost)
                        pos = {"number": number, "price": plan, "buy_money": money, "cost": cost,
                               "stoploss": st, "bar": i}
                        fills.append({"bar": i, "side": "OPEN_LONG", "price": plan, "size": float(number)})
                    buy_req = None
            elif sell_req is not None and pos is not None:
                if delayed(i, False):
                    sell_req["count"] += 1
                    if sell_req["count"] > 3 + 1:
                        sell_req = None
                else:
                    plan = b["open"]
                    money = plan * pos["number"]
                    cost = round_ex(money * rate)
                    cash = round_ex(cash + money - cost)
                    fills.append({"bar": i, "side": "CLOSE_LONG", "price": plan, "size": float(pos["number"])})
                    pnls.append(round_ex(money - pos["buy_money"] - pos["cost"] - cost))
                    pos = None
                    sell_req = None
            # on close: the strategy's signal generator, then stop loss, then the profit goal
            s = sig.get(i)
            want_buy = want_sell = False
            if plan_pos and N is not None and plan_entry is not None and i + 1 - plan_entry >= N:
                want_sell = True
            elif s == "BUY" and not plan_pos:
                ok = cfg["entry_sides"] != "short" and (cfg["entry_mask"] is None or cfg["entry_mask"][i])
                want_buy = ok
            elif s in ("SELL", "CLOSE") and plan_pos:
                want_sell = True
            if want_buy:
                buy_req = {"count": 1}
                plan_pos, plan_entry = True, i + 1
                continue
            if want_sell:
                if pos is not None:
                    sell_req = {"count": 1}
                plan_pos, plan_entry = False, None
                continue
            if pos is not None and sell_req is None:
                if b["close"] <= pos["stoploss"]:
                    sell_req = {"count": 1}
                elif pg is not None and b["close"] >= pos["buy_money"] / pos["number"] * (1 + pg):
                    sell_req = {"count": 1}
        return want(inp, {"fills": fills, "pnls": pnls})


TARGET = Hikyuu()
