"""Reproduction of survey candidate 69 `gobacktest` (dirkolbrich) for the item 4 battery.  Item 0 built it with a small
Go driver (tests/bt/battery/item_0/opponents/RUNNABILITY.tsv row 69); that build (venv item_0/c69) is gone from the
scratchpad, and that driver took item 0's inputs, so the rules are rewritten here instead.

Primary source (read only), commit 719cff68de8ad45c45be4c68df6e6f31e5e64305:
  https://github.com/dirkolbrich/gobacktest/tree/719cff68de8ad45c45be4c68df6e6f31e5e64305
Rules taken:
- The event loop (backtest.go 85-120, 167-205): a data event goes to the strategy (OnData), its signals to the
  portfolio (OnSignal -> an order), the order to the exchange (OnOrder -> a fill), all before the next bar is read.
- `Exchange.OnOrder` (execution.go 34-60) fills the whole order at `data.Latest(symbol).Price()`, and a bar's Price()
  is its Close (data.go 162-164): the signal bar's close.  The exchange's OnData does nothing (execution.go 29-32):
  no resting limit or stop orders (the order's limit price is never read).
- `Size.SizeOrder` (size.go 20-52): BOT and SLD get `min(DefaultSize, floor(DefaultValue / price))` whole units
  (setDefaultSize 55-61); EXT closes the position.  Here DefaultValue = the scene's order notional and DefaultSize is
  set large enough not to bind.
- `PercentageCommission.Calculate` (commission.go 47-63) = qty x price x rate: one rate for every fill.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "gobacktest(719cff68)"


class GoBacktest(RuleBroker):
    name = "opp_repro_69_gobacktest"
    TOOL = "gobacktest(719cff68)(再現)"
    MARKET = "same_close"
    FEES = "single"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "taker_fee_pct", "maker_fee_pct"}
    _nolim = f"待つ注文(指値・逆指値)が無い(Exchange.OnData は何もしない: {SRC} execution.go 29-32 行、注文の指値は読まれない)"
    MISSING = {"execution": _nolim, "stop_loss_pct": _nolim, "take_profit_pct": _nolim, "exit_execution": _nolim,
               "maker_tp_pct": _nolim,
               "slippage_pct": f"滑り・スプレッドの口が無い(約定値は最新の足の終値そのもの: {SRC} execution.go 41-47 行)",
               "spread_pct": f"滑り・スプレッドの口が無い({SRC} execution.go 41-47 行)",
               "swap_daily_pct": f"持ち越しの口が無い(費用は Commission と ExchangeFee だけ: {SRC} execution.go 50-60 行)",
               "equity": "足ごとの資産(statistic.go 71 行 Update)は再現していない(この場面集で資産を求める場面は、どれも gobacktest に無い口 = 逆指値・持ち越し・指標 も求める)"}
    METRICS = "12 の指標を出す口が無い(statistic.go 141-205 行は資産の系列から総収益・最大ドローダウン・Sharpe・Sortino を出す形で、決済ごとの損益から勝率・PF などを出す口は無い)"
    SPLIT = "行の割合で分ける口が無い"
    PIPELINE = "再現は足の約定の規則だけ(データは CSV の読み口 1 本、目的つきの書き出し・ダッシュボードは無い)"

    def qty_for(self, notional, ref_px):
        return float(math.floor(notional / ref_px))


TARGET = GoBacktest()
