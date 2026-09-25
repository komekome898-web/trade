"""Survey candidate 16 `Luczinsritter/event_driven_backtesting_engine` for the item 3 battery.

Install: venv item_3/c16 = a clone of commit 20929924 (the one item 0 used) read through a .pth,
its requirements.txt pins from PyPI; record venvs/item_3/logs/i3_r1_scenekeeper_install_c16.log.
Only tradeanalysis.TradeAnalysis.max_drawdown is called (the tool's metrics module); the
engine's own data path (yfinance download, backtest_engine.py 15) is never called.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402

import pandas as pd  # noqa: E402
from tradeanalysis import TradeAnalysis  # noqa: E402


class Luczinsritter(Base):
    name = "opp_luczinsritter"
    WHAT = "候補 16 は yfinance の足の上の小さな事象駆動のバックテストと、その取引の分析(tradeanalysis.py)。"
    NO = {
        "trade_metrics": "tradeanalysis.py の df_analysis(34 行)は件数・平均の損益・保有の平均だけで、1 件ごとの bp の分布・分位・露出あたりが無い",
    }

    def op_drawdown(self, inp):
        ta = TradeAnalysis(pd.DataFrame({"Capital After Trade": inp["equity"]}), capital=int(inp["equity"][0]),
                           cost_per_trade=0.0, slippage=0.0, price_series=pd.Series(dtype=float))
        max_dd, _rec = ta.max_drawdown()
        return {"max_dd_pct": -float(max_dd) * 100.0,
                "note": "max_drawdown(tradeanalysis.py 54 行)は (資産 / 最高値) − 1 の最小(負の割合)を返す。符号と単位(% )だけ直した。額の口は無い"}


TARGET = Luczinsritter()
