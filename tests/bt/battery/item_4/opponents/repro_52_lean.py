"""Reproduction of survey candidate 52 `QuantConnect` (LEAN) -- its default fill model on trade bars -- for the item 4
battery.  LEAN is C#/.NET and was not built here (tests/bt/battery/item_0/opponents/RUNNABILITY.tsv row 52; item 0
reproduced its data path only: tests/bt/battery/item_0/opponents/repro_lean52.py).

Primary source (read only), commit b1337938bacbdcdf7327ba4c6a10ffa89ffac403:
  https://github.com/QuantConnect/Lean/blob/b1337938bacbdcdf7327ba4c6a10ffa89ffac403/Common/Orders/Fills/FillModel.cs
Rules taken (FillModel.cs):
- MarketFill (273-340) fills at `GetMarketFillPrice` (1106-1119): the bar's current price (its close) for an order
  placed during the bar; for hour / daily data (`ShouldWaitForFreshData`, "Coarse resolutions (hour/daily) always
  wait", 1060-1071) an order that predates the bar fills at the bar's OPEN.  Here: minute bars -> the signal bar's
  close; bar_seconds >= 3600 -> the next bar's open.
- LimitFill (697-760): not on the bar it was placed (`pricesEndTime <= order.Time`, 725); a buy fills when
  Low < limit (strict) at min(High, limit), a sell when High > limit at max(Low, limit).
- StopMarketFill (347-400): a sell stop fills when Low < stop at min(stop, current - slip), a buy stop when
  High > stop at max(stop, current + slip); the default slippage is 0 (the slippage model is not in the files read,
  so slippage is not reproduced).
- MarketOnOpen (766-800) throws for a market that never closes (crypto): not used.
- Not read: the order in which the backtesting brokerage scans several open orders of one security on one bar.  The
  exit orders are scanned here in the order the strategy sent them (stop, then take-profit) -- UNVERIFIED; the scenes
  where both are hit on one bar (I4-10) depend on it.
- Fees: a user fee model (IFeeModel) may charge by order type; here maker percent on limit fills, taker otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "Common/Orders/Fills/FillModel.cs(b1337938)"


class Lean(RuleBroker):
    name = "opp_repro_52_lean"
    TOOL = "QuantConnect LEAN FillModel(b1337938)(再現)"
    MARKET = "same_close"
    CHILD_ORDER = ("sl", "tp")
    FEES = "by_type"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct",
                "taker_fee_pct", "maker_fee_pct"}
    MISSING = {"slippage_pct": f"再現していない: 滑りは slippage model の値で({SRC} 378・390 行)、その模型の行は読んでいない",
               "spread_pct": f"再現していない: 気配の買い・売りの値は足(TradeBar)の外({SRC} は TradeBar の値で約定する)",
               "swap_daily_pct": "再現していない: 持ち越し(margin interest)の模型は読んだ範囲に無い",
               "equity": "再現していない: 足ごとの資産は SecurityPortfolioManager の外の結果の処理にあり、読んでいない"}
    METRICS = "再現していない: 統計の出力(Statistics)は読んでいない"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は約定の模型だけ(データの道筋は項目 0 の再現 repro_lean52.py)"

    def bars(self, inp):
        self.MARKET = "next_open" if int(inp["bar_seconds"]) >= 3600 else "same_close"
        return super().bars(inp)

    def limit_px(self, o, b):
        if o.side == "buy":
            return min(b["high"], o.level) if b["low"] < o.level else None
        return max(b["low"], o.level) if b["high"] > o.level else None

    def stop_px(self, o, b):
        if o.side == "sell":
            return min(o.level, b["close"]) if b["low"] < o.level else None
        return max(o.level, b["close"]) if b["high"] > o.level else None


TARGET = Lean()
