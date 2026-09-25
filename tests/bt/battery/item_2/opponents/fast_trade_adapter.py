"""Survey candidate 10 `fast-trade` (PyPI 2.1.0, venv item_0/fast-trade-r17; install record: item 0
survey_results/attempts/10.log) for the item 2 battery.

What the tool is: `run_backtest(backtest, df=)` evaluates a rule table (`enter` / `exit` conditions over OHLCV
columns and indicator datapoints) over a whole OHLCV DataFrame; a trade takes the whole balance (no quantity),
at the bar's close, with one `comission` percentage.  There is no order type, limit price, quantity, time of an
order, book, latency, notice or account, so no scene of this battery can be handed to it; each scene reads the
tool's own run_backtest / validate_backtest signatures as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

import fast_trade  # noqa: E402  (the tool, in its venv)


class Adapter(ProbeAdapter):
    name = "opp_fast_trade"
    tool = "fast-trade 2.1.0"
    what = "口は OHLCV の表に入りと出の条件の表を当てる run_backtest だけで、注文の種類・値・数量・時刻・遅延・口座の口が無い"

    def probe(self):
        return signature_probe(fast_trade.run_backtest, fast_trade.validate_backtest)

    def why_not(self, inp):
        return "注文(種類・値・数量・時刻)・板・約定の列を渡す口が無い(条件の表で残高の全部を足の終値で売買する)"


TARGET = Adapter()
