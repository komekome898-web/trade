"""Reproduction of survey candidate 67 `lumibot` (Lumiwealth) -- its backtesting broker's bar fills -- for the item 4
battery.  The tool itself is not installed here: its dependency set is 320 distributions (item 2's dry run,
tests/bt/battery/item_2/opponents/RUNNABILITY.tsv row 67).

Primary source (read only, nothing of it executed), commit 6b4ebedae2e34df79148bd0b60ac24b716fab95e:
  https://github.com/Lumiwealth/lumibot/blob/6b4ebedae2e34df79148bd0b60ac24b716fab95e/lumibot/backtesting/backtesting_broker.py
  https://github.com/Lumiwealth/lumibot/blob/6b4ebedae2e34df79148bd0b60ac24b716fab95e/lumibot/entities/order.py
Rules taken, each with its lines:
- An order sent in an iteration is looked at by `process_pending_orders` at the start of a later bar, on that bar's
  OHLC (backtesting_broker.py 938-948, 1147-1180: the bar at or after the current time).  MARKET fills at the bar's
  open (1193-1194).
- LIMIT (1241-1256): a sell whose limit <= open, or a buy whose limit >= open, fills at the open; otherwise it fills at
  the limit when low <= limit <= high (touch, inclusive).  STOP (1258-1273): a sell stop >= open or a buy stop <= open
  fills at the open; otherwise at the stop when low <= stop <= high.
- Fees (912-936): a TradingFee with `taker=True` is charged on MARKET and STOP fills, one with `maker=True` on LIMIT
  fills, `percent_fee` x price x quantity.
- A bracket's children are the LIMIT (take-profit) first, then the STOP (order.py 776-800), and the first child
  cancels the second (order.py 806-808 `dependent_order`); a child sent when its parent fills is processed from the
  next bar (children are appended to `_new_orders`, backtesting_broker.py 838-846, after this bar's list was taken,
  954-963).  The scene's strategy sends the two exit orders after its entry fills, in that order.
- backtesting_broker.py has no slippage, spread, funding, interest or borrow term (grep of the 1395 lines: 0 hits),
  and the files read have no per-bar equity output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "lumibot/backtesting/backtesting_broker.py(6b4ebeda)"


class Lumibot(RuleBroker):
    name = "opp_repro_67_lumibot"
    TOOL = "lumibot(6b4ebeda)(再現)"
    MARKET = "next_open"
    CHILD_ORDER = ("tp", "sl")
    FEES = "by_type"
    SLIP = None
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct",
                "taker_fee_pct", "maker_fee_pct"}
    MISSING = {
        "slippage_pct": f"滑り・スプレッドの口を探したが無い({SRC} の約定値は 1193-1215 行で始値・指値・逆指値そのもので、"
                        "slippage・spread の語は 0 件)",
        "spread_pct": f"滑り・スプレッドの口を探したが無い({SRC} に slippage・spread の語は 0 件)",
        "swap_daily_pct": f"持ち越しの口を探したが無い({SRC} に funding・interest・borrow・swap の語は 0 件)",
        "equity": "足ごとの資産の系列を出す口は読んだ範囲(backtesting_broker.py・order.py)に無い",
    }
    METRICS = "12 の指標を出す口は読んだ範囲(backtesting_broker.py・order.py)に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は足の約定の規則だけ(宣言でファイルを読む口・目的つきの書き出し・ダッシュボードは再現していない)"

    def limit_px(self, o, b):
        lim = o.level
        if o.side == "sell" and lim <= b["open"]:
            return b["open"]
        if o.side == "buy" and lim >= b["open"]:
            return b["open"]
        if b["low"] <= lim <= b["high"]:
            return lim
        return None

    def stop_px(self, o, b):
        stp = o.level
        if o.side == "sell" and stp >= b["open"]:
            return b["open"]
        if o.side == "buy" and stp <= b["open"]:
            return b["open"]
        if b["low"] <= stp <= b["high"]:
            return stp
        return None


TARGET = Lumibot()
