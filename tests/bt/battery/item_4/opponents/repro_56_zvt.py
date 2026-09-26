"""Reproduction of survey candidate 56 `zvt` -- its simulated account (SimAccountService) -- for the item 4 battery.
Not installed: 57 distributions, and the account reads its bars from zvt's own database through `get_kdata`
(dry run: opponents/attempts/i4_r1_scenekeeper_dryrun_resolution.log).

Primary source (read only), commit 8509990e6608750d0c08fa748682cc997d2813cc:
  https://github.com/zvtvz/zvt/blob/8509990e6608750d0c08fa748682cc997d2813cc/src/zvt/trader/sim_account.py
Rules taken:
- A trading signal is filled at the CLOSE of the bar of its `happen_timestamp` (handle_trading_signal 169-205:
  `get_kdata(... start_timestamp=happen_timestamp, end_timestamp=happen_timestamp, limit=1)`, `the_price =
  kdata["close"][0]`) -- the bar the strategy saw.
- `order_by_money` (500-512) buys `order_money // (price x (1 + slippage + buy_cost))` units (a whole number,
  cal_amount_by_money 431-442); the order record keeps `order_price` = the close (update_position 410-428).
- Cash (update_position 353-408): open = amount x price x (1 + slippage + buy_cost); close long = amount x price x
  (1 - slippage - sell_cost); close short = 2 x amount x average_short_price - amount x price x (1 + slippage +
  sell_cost).  The round trip's result is the change of cash.
- Opening long while short (or short while long) raises InvalidOrderError (514-534).  One buy_cost, one sell_cost,
  one slippage (constructor 30-50); no limit or stop order (order types: long / short / close_long / close_short).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker, adj  # noqa: E402

SRC = "src/zvt/trader/sim_account.py(8509990e)"


class Zvt(RuleBroker):
    name = "opp_repro_56_zvt"
    TOOL = "zvt(8509990e)(再現)"
    MARKET = "same_close"
    FEES = "single"
    SLIP = "cost"
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"}
    _nolim = f"指値・逆指値の注文の型が無い(注文は long / short / close_long / close_short だけ: {SRC} 514-540 行)"
    MISSING = {"execution": _nolim, "stop_loss_pct": _nolim, "take_profit_pct": _nolim, "exit_execution": _nolim,
               "maker_tp_pct": _nolim,
               "swap_daily_pct": f"持ち越しの口が無い({SRC} の現金は約定のときだけ動く: 353-408 行)",
               "equity": "足ごとの資産の系列は読んだ範囲(sim_account.py)に無い(on_trading_close は日足の終値で建玉を評価する: 235-300 行)"}
    METRICS = "12 の指標を出す口は読んだ範囲に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は模擬の口座の規則だけ(道具は足を自前のデータベースから読む: get_kdata 176-185 行)"

    def book_price(self, o, px):
        return px

    def qty_for(self, notional, ref_px):
        c = self._cfg["costs"]
        return float(notional // (ref_px * (1 + self._slip() + c["taker_fee_pct"] / 100)))

    def _slip(self):
        return adj(self._cfg["costs"])

    def trade_pnl(self, pos, px, exit_fee, cfg):
        s, cost = self._slip(), cfg["costs"]["taker_fee_pct"] / 100
        q, e = pos["qty"], pos["px"]
        if pos["dir"] > 0:
            return q * px * (1 - s - cost) - q * e * (1 + s + cost)
        return 2 * q * e - q * px * (1 + s + cost) - q * e * (1 + s + cost)

    def bars(self, inp):
        self._cfg = inp["config"]
        return super().bars(inp)

    def fee_rate(self, cfg, liq):
        return 0.0   # costs are in trade_pnl (cash), the order record keeps the close


TARGET = Zvt()
