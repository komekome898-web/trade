"""Survey candidate 87 `PyTrendFollow` (GitHub chrism2671/PyTrendFollow, commit 439232ae, venv item_0/c87 with a .pth
to the clone; install record: item 0 survey_results/attempts/87.log) for the item 2 battery.

What the tool is: `trading.accountcurve.accountCurve(instruments, positions=..., panama_prices=...)` whose returns are
four fixed formulas over whole series (positions shifted 2 periods x price change x point value, half the price change
on traded quantity, traded quantity x the instrument's per-contract commission, spreads).  It takes no order (type,
price, time), book, latency, notice or account and no realized / unrealized split, so no scene of this battery can be
handed to it; each scene reads the tool's own accountCurve signature as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

from trading.accountcurve import accountCurve  # noqa: E402  (the tool, via the venv's .pth)


class Adapter(ProbeAdapter):
    name = "opp_pytrendfollow"
    tool = "PyTrendFollow(439232ae)"
    what = "口は建玉と値の系列を丸ごと受ける accountCurve だけで、注文・約定・遅延・口座の口が無い"

    def probe(self):
        return signature_probe(accountCurve.__init__)

    def why_not(self, inp):
        return "注文(種類・値・数量・時刻)・板・約定の列を渡す口が無い(建玉の系列と値の系列だけを受け、手数料は枚数あたりの定数)"


TARGET = Adapter()
