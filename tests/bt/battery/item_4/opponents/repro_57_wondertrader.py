"""Reproduction of survey candidate 57 `WonderTrader` -- the CTA back-test mocker on bars with simulated ticks -- for
the item 4 battery.  Not installed (item 0 record: tests/bt/battery/item_0/opponents/RUNNABILITY.tsv row 57; item 2
reproduced its tick matcher: tests/bt/battery/item_2/opponents/repro_57_wondertrader_match.py).

Primary source (read only), commit 08b230dd05facf6d650d949bfe51054115a2ecb1:
  https://github.com/wondertrader/wondertrader/blob/08b230dd05facf6d650d949bfe51054115a2ecb1/src/WtBtCore/CtaMocker.cpp
  https://github.com/wondertrader/wondertrader/blob/08b230dd05facf6d650d949bfe51054115a2ecb1/src/WtBtCore/HisDataReplayer.cpp
Rules taken:
- A bar is replayed as four simulated ticks: open, high, low, close (HisDataReplayer.cpp simTicks 1222-1282,
  pxType 0..3).  A signal set when a bar closes (CTA on_bar, `append_signal` 1584-1599 with `_sig_map`) is executed
  by `proc_tick` (693-714) at the next tick's price: the next bar's open.
- A condition order (the CTA's price-conditioned entry / exit) is checked on every simulated tick with left =
  min(last, current), right = max(last, current) (743-744): ">=" matches when right >= target and executes at
  max(left, target); "<=" matches when left <= target and executes at min(right, target) (777-830); it is executed on
  that tick (proc_tick is called again, 936-937).  The first order matched in a tick wins (800-806).
- Every execution moves by the ratio slippage (1635-1648: slippage x price / 10000, in basis points, rounded to the
  price tick -- the tick here is set so small that the rounding does not bind) and pays the fee of the commodity's
  fee template: rate x amount for open and for close, rounded to 0.01 (HisDataReplayer.cpp 2930-2958).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "WtBtCore/CtaMocker.cpp(08b230dd)"


class WonderTrader(RuleBroker):
    name = "opp_repro_57_wondertrader"
    TOOL = "WonderTrader CtaMocker(08b230dd)(再現)"
    MARKET = "next_open"
    PATH = staticmethod(lambda b: [b["open"], b["high"], b["low"], b["close"]])
    CHILD_ORDER = ("sl", "tp")
    FEES = "single"
    SLIP = "market"
    SLIP_ALL = True
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct",
                "taker_fee_pct", "maker_fee_pct", "slippage_pct", "spread_pct"}
    MISSING = {"swap_daily_pct": f"持ち越しの口は読んだ範囲に無い({SRC} の費用は手数料と滑りだけ)",
               "equity": "再現していない: 足ごとの資産(動的損益の記録)は読んでいない"}
    METRICS = "12 の指標を出す口は読んだ範囲に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は CTA の模擬の約定の規則だけ"

    def bars(self, inp):
        self._last = None
        return super().bars(inp)

    def path_hit(self, o, prev, p):
        last = prev if prev is not None else self._prev_close
        left, right = min(last, p), max(last, p)
        ge = (o.typ == "limit" and o.side == "sell") or (o.typ == "stop" and o.side == "buy")
        if ge:
            return max(left, o.level) if right >= o.level else None
        return min(right, o.level) if left <= o.level else None

    def fee_amount(self, qty, px, rate_pct):
        return int(qty * px * rate_pct / 100 * 100 + 0.5) / 100.0


TARGET = WonderTrader()
