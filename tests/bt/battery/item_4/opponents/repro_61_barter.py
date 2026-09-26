"""Reproduction of survey candidate 61 `barter-rs` -- the backtest's mock exchange (`MockExchange`) -- for the item 4
battery.  Item 0 built it with a small Rust driver (tests/bt/battery/item_0/opponents/RUNNABILITY.tsv row 61); that
build (venv item_0/c61) is gone from the scratchpad.  A new cargo build was not attempted in this round: the scratchpad
had 2.3 GB free (df, 2026-09-26 04:4x UTC) and item 0's cargo build of candidate 107 alone took 2.0 GB
(tests/bt/battery/item_0/survey_results/attempts/107.log), so the mock's rules are rewritten here instead.

Primary source (read only), commit 9770b27a83f844472b93b593b08063affc974b0d:
  https://github.com/barter-rs/barter-rs/blob/9770b27a83f844472b93b593b08063affc974b0d/barter-execution/src/exchange/mock/mod.rs
Rules taken (mod.rs):
- Only MARKET orders (`validate_order_kind_supported` 396-407; a cancel request is answered "only Market orders are
  supported", 119): no limit or stop order.
- `open_order` (269-395) fills the whole order at once at the price written on the request (`request.state.price`,
  298 and 367-387): the strategy writes the last price it saw, the close of the bar it acted on.
- Fee = order value x `fees_percent` (299, 326-341): one rate.
- The mock account holds balances only (283-340): no position with a side, no carry.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "barter-execution/src/exchange/mock/mod.rs(9770b27a)"


class Barter(RuleBroker):
    name = "opp_repro_61_barter"
    TOOL = "barter-rs MockExchange(9770b27a)(再現)"
    MARKET = "same_close"
    FEES = "single"
    SUPPORTS = {"max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "taker_fee_pct", "maker_fee_pct"}
    _nolim = f"成行しか無い(validate_order_kind_supported: {SRC} 396-407 行、取消の要求には「only Market orders are supported」: 119 行)"
    MISSING = {"execution": _nolim, "stop_loss_pct": _nolim, "take_profit_pct": _nolim, "exit_execution": _nolim,
               "maker_tp_pct": _nolim,
               "allow_short": f"売り建ての建玉の型が無い(模擬の口座は残高だけ: {SRC} 283-340 行)",
               "slippage_pct": f"滑り・スプレッドの口が無い(約定値は注文に書いた値そのもの: {SRC} 298・367-387 行)",
               "spread_pct": f"滑り・スプレッドの口が無い({SRC} 298 行)",
               "swap_daily_pct": f"持ち越しの口が無い(残高は約定と手数料だけで動く: {SRC} 283-340 行)",
               "equity": "足ごとの資産の系列は読んだ範囲(mock)に無い"}
    METRICS = "12 の指標を出す口は読んだ範囲(mock)に無い"
    SPLIT = "行の割合で分ける口は読んだ範囲に無い"
    PIPELINE = "再現は模擬の取引所の約定の規則だけ"


TARGET = Barter()
