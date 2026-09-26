"""Reproduction of survey candidate 11 `OctoBot` (the catalogue's name column says `python3`; SCAN 8452 行 names it
OctoBot) -- its backtesting fills from OHLCV -- for the item 4 battery.  Not runnable: its backtesting needs tentacles
that are distributed as a zip outside PyPI (tests/bt/battery/item_0/opponents/RUNNABILITY.tsv row 11).

Primary source (read only), OctoBot-Trading commit 1ad2f4d6d2961cd28d5405472c4d2cc81ddbcfa2:
  https://github.com/Drakkar-Software/OctoBot-Trading/tree/1ad2f4d6d2961cd28d5405472c4d2cc81ddbcfa2/octobot_trading
Rules taken:
- Without recorded trades, the backtest makes the "recent trades" of a completed candle from the NEXT candle: two
  trades, at that candle's low and then its high (exchange_data/recent_trades/channel/recent_trade_updater_simulator.py
  62-89: "Recent trades for this candle are between the next candle candle high price and the next candle low price").
- A market order fills at `created_last_price` (personal_data/orders/types/market/market_order.py 39-43): the price
  when it was created, i.e. the close of the candle the strategy acted on.
- A limit / stop / take-profit order waits for a price event (exchange_data/prices/price_events_manager.py 163-178):
  `trigger_above` orders (sell limit, take-profit sell, buy stop) fire when a price >= the order price, the others
  when a price <= it (inclusive); a limit order fills at its own price (limit_order.py 130-133
  `update_order_filled_values(self.origin_price)`), a stop loss at its stop price as a taker (stop_loss_order.py
  20-44).  Trades are checked in the order pushed: low, then high.
- The files read do not set the fee rate (fees come from the exchange's market status in the simulator: not read) --
  fees are not reproduced.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "OctoBot-Trading(1ad2f4d6)"


class OctoBot(RuleBroker):
    name = "opp_repro_11_octobot"
    TOOL = "OctoBot-Trading(1ad2f4d6)(再現)"
    MARKET = "same_close"
    PATH = staticmethod(lambda b: [b["low"], b["high"]])
    CHILD_ORDER = ("sl", "tp")
    FEES = None
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct"}
    MISSING = {
        "taker_fee_pct": f"再現していない: 模擬の手数料の率は取引所の市場の情報から来る({SRC} の読んだファイルは率を置かない。exchange_simulator の手数料の行は読んでいない)",
        "maker_fee_pct": f"再現していない: 模擬の手数料の率は取引所の市場の情報から来る({SRC} の読んだファイルは率を置かない)",
        "slippage_pct": f"滑り・スプレッドの口は読んだ範囲に無い(成行は作った時の値そのもの: market_order.py 39-43 行)",
        "spread_pct": f"滑り・スプレッドの口は読んだ範囲に無い(market_order.py 39-43 行)",
        "swap_daily_pct": "再現していない: 先物の資金調達の型は項目 0 の再現(資金調達の型)で読んだが、日率を足ごとに掛ける口は読んだ範囲に無い",
        "equity": "足ごとの資産の系列は読んだ範囲に無い"}
    METRICS = "12 の指標を出す口は読んだ範囲に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は足からの約定の規則だけ"

    def path_hit(self, o, prev, p):
        above = (o.typ == "limit" and o.side == "sell") or (o.typ == "stop" and o.side == "buy")
        hit = p >= o.level if above else p <= o.level
        return o.level if hit else None


TARGET = OctoBot()
