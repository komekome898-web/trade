"""Survey candidate 54 `finmarketpy` (PyPI 0.11.19, venv item_0/finmarketpy; install record: item 0
survey_results/attempts/54.log) for the item 2 battery.

What the tool is: `finmarketpy.backtest.Backtest.calculate_trading_PnL(br, asset_a_df, signal_df, contract_value_df,
run_in_parallel)` over a whole price DataFrame and a whole signal DataFrame (spread costs in bp on signal changes).
It takes no order (type, price, quantity, time), book, latency, notice or account, so no scene of this battery can be
handed to it; each scene reads the tool's own signature as what was tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_base import ProbeAdapter, signature_probe  # noqa: E402

from finmarketpy.backtest import Backtest  # noqa: E402  (the tool, in its venv)


class Adapter(ProbeAdapter):
    name = "opp_finmarketpy"
    tool = "finmarketpy 0.11.19"
    what = "口は価格の表と信号の表を丸ごと受ける Backtest.calculate_trading_PnL だけで、注文・約定・遅延・口座の口が無い"

    def probe(self):
        return signature_probe(Backtest.calculate_trading_PnL)

    def why_not(self, inp):
        return "注文(種類・値・数量・時刻)・板・約定の列を渡す口が無い(信号の表の変化に bp の費用を掛けるだけ)"


TARGET = Adapter()
