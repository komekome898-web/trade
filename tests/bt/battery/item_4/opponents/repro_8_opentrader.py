"""Reproduction of survey candidate 8 `OpenTrader` -- its backtest's market simulator -- for the item 4 battery.  Not
installed: the install was stopped by the pre-install check (tools survey delegation §6-1; item 3 CONSIDERED row 8).

Primary source (read only, nothing executed), commit 8b8e24599599df214b12b4263553885854015b4b:
  https://github.com/Open-Trader/opentrader/blob/8b8e24599599df214b12b4263553885854015b4b/packages/backtesting/src/backtesting.ts
  https://github.com/Open-Trader/opentrader/blob/8b8e24599599df214b12b4263553885854015b4b/packages/backtesting/src/market-simulator.ts
  https://github.com/Open-Trader/opentrader/blob/8b8e24599599df214b12b4263553885854015b4b/packages/backtesting/src/exchange/memory-exchange.ts
Rules taken:
- The loop per candle (backtesting.ts 54-83): `nextCandle`, then `fulfillOrders` on this candle, then the bot's
  processor (`start` on the first candle, `stop` on the last, `process` on the others -- so the strategy is not called
  on the first and the last candle), then `placeOrders` (idle -> placed).  An order sent while candle i is processed
  is placed at the end of candle i and filled from candle i+1.
- A placed market order fills at the candle's CLOSE (market-simulator.ts 108-121, 138-150); a placed limit buy fills at
  its price when close <= price (122-135), a limit sell (the take-profit) when close >= price (151-166).
- A smart trade is an entry BUY and a take-profit SELL (market-simulator.ts 71-91): long only, no stop order.
- Fees: memory-exchange.ts 149-152 returns makerFee 0 / takerFee 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "packages/backtesting/src/market-simulator.ts(8b8e2459)"


class OpenTrader(RuleBroker):
    name = "opp_repro_8_opentrader"
    TOOL = "OpenTrader(8b8e2459)(再現)"
    MARKET = "next_close"
    SKIP_SIGNAL_BARS = ("first", "last")
    STOP_TYPES = False
    SUPPORTS = {"max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars", "take_profit_pct",
                "execution", "exit_execution", "maker_tp_pct"}
    MISSING = {
        "allow_short": f"売り建ての口が無い(smart trade は entry の買いと take-profit の売りだけ: {SRC} 71-91 行)",
        "stop_loss_pct": f"逆指値の注文の型が無い({SRC} の約定は Market と Limit だけ: 108-166 行)",
        "taker_fee_pct": "手数料は 0 に固定(memory-exchange.ts 149-152 行 makerFee 0・takerFee 0)",
        "maker_fee_pct": "手数料は 0 に固定(memory-exchange.ts 149-152 行)",
        "slippage_pct": f"滑り・スプレッドの口が無い(成行は足の終値そのもの: {SRC} 114 行)",
        "spread_pct": f"滑り・スプレッドの口が無い({SRC} 114 行)",
        "swap_daily_pct": "持ち越しの口が無い(読んだ 4 つのファイルに funding・interest・swap の語は 0 件)",
        "equity": "足ごとの資産の系列を出す口が無い(報告は注文の表と合計の損益: backtesting-report.ts 24-75 行)",
    }
    METRICS = "12 の指標を出す口が無い(報告は注文の表と合計の損益: backtesting-report.ts 24-75 行)"
    SPLIT = "行の割合で分ける口が無い"
    PIPELINE = "再現は足の約定の規則だけ(宣言でファイルを読む口・目的つきの書き出し・ダッシュボードは再現していない)"

    def limit_px(self, o, b):
        if o.side == "buy":
            return o.level if b["close"] <= o.level else None
        return o.level if b["close"] >= o.level else None


TARGET = OpenTrader()
