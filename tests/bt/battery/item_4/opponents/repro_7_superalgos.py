"""Reproduction of survey candidate 7 `Superalgos` -- the low-frequency trading bot's order and stage simulation --
for the item 4 battery.  Not installed: a Node.js platform with its own data mining and UI (catalogue row 7); nothing
of it was run.

Primary source (read only), commit 9f0fb59edd4bae7afa08d06c366e0bcb48103aec, under
https://github.com/Superalgos/Superalgos/tree/9f0fb59edd4bae7afa08d06c366e0bcb48103aec/Projects/Algorithmic-Trading/TS/Bot-Modules/Trading-Bot/Low-Frequency-Trading
Rules taken:
- The engine runs once per candle on the candle just closed (`tradingEpisode.candle`); an order's rate is the user's
  formula (here: the candle's close) and a MARKET order is filled on that candle (OrdersSimulations.js 401-409
  `orderWasHit = true`), at the rate moved by the session's market slippage percent (82-140) and kept inside the
  candle's max / min (205-260).
- A LIMIT buy is hit when the candle's min <= its rate, a sell when max >= its rate (383-399), at its rate with no
  slippage (146-148).  Fees: taker percent on market orders, maker percent on limit orders (348-373, 438-485).
- Stop loss and take profit are stage checks, not orders (TradingStages.js 830-876): on a later candle, the stop loss
  is hit when the candle's min <= it (below a long) / max >= it (above a short), checked BEFORE the take profit
  (max >= it / min <= it); then the close stage sends its (market) order on that candle.
- No carry cost in the files read.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import BUY, RuleBroker  # noqa: E402

SRC = "Superalgos Low-Frequency-Trading(9f0fb59e)"


class Superalgos(RuleBroker):
    name = "opp_repro_7_superalgos"
    TOOL = "Superalgos(9f0fb59e)(再現)"
    MARKET = "same_close"
    CHILD_ORDER = ("sl", "tp")
    FEES = "by_type"
    SLIP = "market"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct",
                "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"}
    MISSING = {"swap_daily_pct": f"持ち越しの口は読んだ範囲に無い({SRC} の OrdersSimulations.js・TradingStages.js・TradingPosition.js)",
               "equity": "足ごとの資産の系列は読んだ範囲に無い"}
    METRICS = "12 の指標を出す口は読んだ範囲に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は注文と段の模擬の規則だけ"

    def slip_px(self, o, px, a, b):
        px = px * (1 + a) if o.side == BUY else px * (1 - a)
        return min(px, b["high"]) if o.side == BUY else max(px, b["low"])

    def limit_px(self, o, b):
        if o.kind == "tp":   # a stage check: exits with a market order at the close (sent as a stop-type order here)
            return None
        if o.side == BUY:
            return o.level if b["low"] <= o.level else None
        return o.level if b["high"] >= o.level else None

    def stop_px(self, o, b):
        long_pos = o.side != BUY
        if o.kind == "sl":
            hit = b["low"] <= o.level if long_pos else b["high"] >= o.level
        else:  # take profit stage check
            hit = b["high"] >= o.level if long_pos else b["low"] <= o.level
        return b["close"] if hit else None

    def after_entry(self, st, cfg, bars, i):
        super().after_entry(st, cfg, bars, i)
        for o in st["orders"]:
            if o.status == "open" and o.kind == "tp":
                o.typ = "stop"


TARGET = Superalgos()
