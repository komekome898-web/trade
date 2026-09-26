"""Reproduction of survey candidate 94 `mote/backtest` (backtest.py, Python 2; there is no Python 2 interpreter here,
tests/bt/battery/item_2/opponents/RUNNABILITY.tsv row 94) -- its bar loop -- for the item 4 battery.

Primary source (read only, not executed): https://github.com/mote/backtest/blob/15bb9f1a14541d870444165cc92f1a7029695cc8/backtest.py
Rules taken:
- `next_bar` (798-850): a bar on a Saturday or Sunday is skipped entirely (801-802); otherwise the book's fills on this
  bar are taken first, then positions are marked, then the strategy's `bar_close` runs (850).  An order the strategy
  adds is looked at from the next bar.
- `OrderBook.get_fills` (427-456): a MARKET order fills on the bar; a LIMIT or STOP order fills when its level lies
  within the bar's low..high, for either side (445, inclusive).  The fill price is the order's level (Position.add,
  622); a MARKET order's level is what the strategy writes on it (436-442 name the close or the open): the close of
  the bar the strategy saw.
- An exit order that is `triggered` by its entry becomes active when the entry fills (OrderBook.fill 397-420); two
  fills on one bar that cancel each other are both cancelled (next_bar 806-826).
- A position's value is (mark - entry) x size (476): no fee, no slippage, no carry.
"""
from __future__ import annotations

import datetime as D
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _repro_bars import RuleBroker  # noqa: E402

SRC = "backtest.py(15bb9f1a)"


class Mote(RuleBroker):
    name = "opp_repro_94_mote"
    TOOL = "mote/backtest(15bb9f1a)(再現)"
    MARKET = "next_bar_prev_close"
    CHILD_ORDER = ("sl", "tp")
    SUPPORTS = {"allow_short", "max_hold_bars", "entry_mask", "entry_sides", "stop_mode", "stop_window_bars",
                "stop_loss_pct", "take_profit_pct", "execution", "exit_execution", "maker_tp_pct"}
    MISSING = {k: f"手数料の口が無い(建玉の値は (mark - entry) x size だけ: {SRC} 476 行)" for k in ("taker_fee_pct", "maker_fee_pct")}
    MISSING.update({k: f"滑り・スプレッドの口が無い(約定値は注文の level そのもの: {SRC} 622 行)" for k in ("slippage_pct", "spread_pct")})
    MISSING["swap_daily_pct"] = f"持ち越しの口が無い({SRC} 476 行)"
    MISSING["equity"] = "再現していない: 資産の記録 eqvals(update_eqvals 774-775 行 = 現金 + 建玉の値)は読んだが再現していない(この場面集で資産を求める場面は、どれも mote に無い口 = 手数料・持ち越し・指標 も求める)"
    METRICS = f"12 の指標を出す口が無い(print_summary は勝ち負けの数・平均・期待値を印字するだけ: {SRC} 862-895 行)"
    SPLIT = "行の割合で分ける口が無い"
    PIPELINE = "再現は足の約定の規則だけ"

    def bars(self, inp):
        self._wk = [D.datetime(1970, 1, 1) + D.timedelta(microseconds=b["t_ns"] // 1000) for b in inp["bars"]]
        wk = [d.weekday() >= 5 for d in self._wk]
        if any(wk):
            # the tool skips those bars: keep the reproduction honest by refusing rather than renumbering the scene
            from _repro_bars import NotExpressible
            raise NotExpressible(f"{self.TOOL}: 土日の足は飛ばす({SRC} 801-802 行)。場面の足に土日の足がある")
        return super().bars(inp)

    def limit_px(self, o, b):
        return o.level if b["low"] <= o.level <= b["high"] else None

    stop_px = limit_px

    def resolve(self, cands):
        out = []
        ids = {id(o) for o, _ in cands}
        for o, px in cands:
            if any(id(x) in ids for x in o.oco):
                o.status = "canceled"
                continue
            out.append((o, px))
        return out


TARGET = Mote()
