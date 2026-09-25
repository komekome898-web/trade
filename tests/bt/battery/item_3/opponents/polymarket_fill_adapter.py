"""Survey candidate 95 `sacha9214/polymarket-fill-model` for the item 3 battery.

Install: the item 2 scene-keeper's venv item_2/c95 (--without-pip, a .pth to the clone;
record venvs/item_2/logs/c95.log).  Only fillmodel.markout is called (a pure function;
the recorder's network path, fillmodel --fetch, is never used).

What the tool models: buying one outcome token at its best bid; a fill is
(time s, price, wait s, queue at posting).  markout(ser, side, fills) returns, per horizon
in MARKOUTS = (60, 300, 1800) s, the pair (capture = mid(t) - price, drift = mid(t+h) - mid(t))
for every fill; the tool's docstring defines the total as their sum (fillmodel.py 257-259:
"total = mid(t+h) - prix payé  la somme des deux") and its report adds them (mc + md, 365).
The adapter reports that total per fill.  mid_at takes the first sample AT OR AFTER a time;
the scene puts a sample exactly at every time asked, so the rule does not matter.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base, NotExpressible  # noqa: E402

import fillmodel  # noqa: E402  (the tool)

NS = 1_000_000_000


class PolymarketFill(Base):
    name = "opp_polymarket_fill"
    WHAT = "候補 95 は Polymarket の指値の待ち行列の模型(fillmodel.py)。"
    NO = {"fill_metrics": "simulate(202 行)は自分で並べた指値の約定を返すだけで、与えた注文と約定から約定率・取り逃しを出す口が無い"}

    def op_markout(self, inp):
        if any(f["side"] != "buy" for f in inp["fills"]):
            raise NotExpressible("markout: 道具は結果の札を最良の買い気配で買うことだけを模す(simulate の説明 202-209 行、markout 254-262 行は"
                                 "mid − 約定の値の向きが固定)。売りの約定の向きを渡す口が無い")
        hs = inp["horizons_s"]
        if any(h not in fillmodel.MARKOUTS for h in hs):
            raise NotExpressible(f"markout: 時間窓は MARKOUTS = {fillmodel.MARKOUTS} 秒に固定(110 行)")
        # the mid series of the tool is (ts s, bid, ask, bid size); a mid is handed as bid = ask = mid
        ser = {"yes": [(t // NS, m, m, 0.0) for t, m in inp["mids"]]}
        fills = [(f["t_ns"] // NS, f["px"], 0, 0.0) for f in inp["fills"]]
        out = fillmodel.markout(ser, "yes", fills)
        return {"markout": {str(h): [a + b for a, b in out[h]] for h in hs},
                "note": "道具の返す (capture, dérive) の組を、道具の定義(total = 2 つの和)どおりに足した"}


TARGET = PolymarketFill()
