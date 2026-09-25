"""Survey candidate 95 `sacha9214/polymarket-fill-model` (git clone src/c95, fillmodel.py, standard library only; venv
item_2/c95 with a .pth, install record venvs/item_2/logs/c95.log) for the item 2 battery.

What the tool is (fillmodel.py docstring and `simulate`, lines 202-252): a maker fill model for one fixed quoting policy
-- the strategy always joins the best bid with a clip of CLIP = 5 shares, re-posts (back of the queue) whenever the best
bid moves, and is filled once the trades that hit its level (a SELL of the same outcome at or below the price, or a BUY
of the other outcome at or above 1 - price) have used up the display that was ahead of it plus its clip; cancellations
ahead are never counted.  `simulate(ser, trades, side, ignore_queue)` takes the book series and the trade tape and
returns the policy's fills; there is no argument for an order of the caller's (its price, size, time or cancel), so no
scene of this battery can be handed to it.  Each scene reads the function's signature as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

import fillmodel  # noqa: E402  (the tool; importing it does not fetch anything)


class Adapter(ProbeAdapter):
    name = "opp_polymarket_fillmodel"
    tool = "polymarket-fill-model(dec7f0f) fillmodel.py"
    what = ("口は固定の出し方(最良の買い気配に 5 株で並び、気配が動けば並び直す)の埋まりを板と約定の列から数える simulate だけ"
            "(fillmodel.py 202-252 行)")

    def probe(self):
        return signature_probe(fillmodel.simulate, fillmodel.hits) + f" / CLIP={fillmodel.CLIP}"

    def why_not(self, inp):
        return "場面の注文(値・数量・時刻・取消)を渡す口が無い(出し方は道具の中で固定)"


TARGET = Adapter()
