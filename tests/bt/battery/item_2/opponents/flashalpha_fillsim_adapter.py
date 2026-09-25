"""Survey candidate 32 `FlashAlpha-lab/flashalpha-fill-simulator` (git clone src/c32, package fillsim, no runtime
dependencies; venv item_2/c32 with a .pth, install record venvs/item_2/logs/c32.log) for the item 2 battery.

What the tool is (README and fillsim/core.py): a per-bar fill check for limit orders on two-leg vertical option spreads
(`simulate_fill(bar_ts, chain: {(expiry, strike): (bid, ask)}, candidates: list[Spread], config)`, a Spread = short and
long Leg quotes + limit_credit + width + expiry).  The object it fills is a two-leg credit / debit spread against an
option chain; a single instrument's order, book or trade tape has no place in it, so no scene of this battery can be
handed to it.  Each scene reads the tool's signatures as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

import fillsim  # noqa: E402  (the tool)
from fillsim import core as _core  # noqa: E402


class Adapter(ProbeAdapter):
    name = "opp_flashalpha_fillsim"
    tool = "flashalpha-fill-simulator(f51de9f) fillsim"
    what = "口は 2 本の脚のオプションの垂直スプレッド(Spread = short / long の Leg と limit_credit)の指値の足ごとの約定判定だけ"

    def probe(self):
        return signature_probe(fillsim.simulate_fill, _core.Spread, _core.Leg)

    def why_not(self, inp):
        return "単一の銘柄の注文・板・約定の列を渡す口が無い(埋まりを判定する対象は 2 本の脚のスプレッドとオプションの気配の表だけ)"


TARGET = Adapter()
