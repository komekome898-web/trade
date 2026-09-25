"""Survey candidate 21 `Qlib` (pyqlib 0.9.7, the venv item 1 installed: venvs/item_1/qlib, install record
tests/bt/battery/item_1/opponents/RUNNABILITY.tsv) for the item 2 battery.

What the tool's execution is (read in the installed code at run time): `qlib.backtest.exchange.Exchange(freq, ...,
deal_price, limit_threshold, volume_threshold, open_cost, close_cost, min_cost, impact_cost, ...)` fills an
`qlib.backtest.decision.Order(stock_id, amount, direction, start_time, end_time, ...)` -- an amount to trade over a
time step at the step's deal price, with the quadratic impact cost `impact_cost * (trade_val / total_trade_val) ** 2`
(SCAN 7253 行).  The Order has no limit / stop / time-in-force field (the fields are read from the dataclass below), and
the steps are the calendar's frequencies (qlib.utils.time.Freq: minute, day, week, month), so an order of the scene
at a print's millisecond time, a limit price, a cancel or a latency has no place in it.  The one scene with one-minute
bars (c2-12-jpx-bar-value) is a limit order.  Each scene reads the Order fields and the frequency units as what was
tried.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

os.environ.setdefault("DO_NOT_TRACK", "1")

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

from qlib.backtest.decision import Order  # noqa: E402  (the tool)
from qlib.backtest.exchange import Exchange  # noqa: E402
from qlib.utils.time import Freq  # noqa: E402


class Adapter(ProbeAdapter):
    name = "opp_qlib"
    tool = "Qlib(pyqlib 0.9.7) qlib.backtest"
    what = ("口は時間枠(分・日・週・月)の区切りごとに、数量と向きだけの Order をその区切りの約定値で埋める Exchange で、"
            "市場影響は impact_cost × (約定額 / 区切りの総約定額)^2 の費用")

    def probe(self):
        return (f"Order の欄 {[f for f in Order.__dataclass_fields__]} / 時間枠の単位 "
                f"{[Freq.NORM_FREQ_MINUTE, Freq.NORM_FREQ_DAY, Freq.NORM_FREQ_WEEK, Freq.NORM_FREQ_MONTH]} / "
                + signature_probe(Exchange.__init__))

    def why_not(self, inp):
        kinds = sorted({a.get("type") for a in inp["actions"] if a.get("op") == "place"} - {None})
        if any(k != "market" for k in kinds) or any(a.get("op") != "place" for a in inp["actions"]):
            return f"注文の型 {kinds}・取消・訂正を渡す口が無い(Order は数量と向きと区切りの時刻だけ)"
        return "約定の時刻(ミリ秒)で注文を埋める口が無い(区切りは分・日・週・月の暦だけ)"


TARGET = Adapter()
