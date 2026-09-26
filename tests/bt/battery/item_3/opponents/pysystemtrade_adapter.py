"""Survey candidate 3 `PySystemtrade` for the item 3 battery.

Install: item 1's venv item_1/c3 (a sparse clone read through a .pth; record
tests/bt/battery/item_1/opponents/RUNNABILITY.tsv, candidate 3).  Only
syscore.pandas.strategy_functions.drawdown is called.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _i3_base import Base  # noqa: E402

import pandas as pd  # noqa: E402
from syscore.pandas.strategy_functions import drawdown  # noqa: E402


class PySystemtrade(Base):
    name = "opp_pysystemtrade"
    WHAT = "PySystemtrade は先物の系統的な売買の枠組み(予測値 → 建玉 → 口座の曲線)。"
    NO = {
        "calendar_split": "当たりは docs の文だけ(docs/introduction.md・backtesting.md)。Train / Val / OOS を日付で切る関数が無い",
        "walk_forward": "sysquant/fitting_dates.py の generate_fitting_dates(57 行)は期間の区切りが interval_frequency(既定 12M)、転がる窓の長さが"
                        "rollyears(整数の年、60 行)で、日単位の学習の窓を渡せない。当たりのほかは account_curve の rolling の統計",
        "block_bootstrap": "bootstrap の当たりは sysquant/optimisation の重みの推定(SR_adjustment.py・full_handcrafting.py)で、系列の平均の"
                           "信頼区間をブロックの再抽出で出す口ではない",
        "dsr": "当たり(optimised_positions_stage.py)は別の語で、deflated Sharpe の関数が無い",
        "run": "当たりは本番の工程の制御(process_control.py)の識別子で、バックテストの実行の記録(git・データの sha256・種)の口が無い",
        "trade_metrics": "当たりは口座の曲線の統計(account_curve.py)と取引時間の表で、与えた往復から 1 件ごとの bp・分位・露出あたりを出す口が無い",
        "fill_metrics": "当たりは本番の価格の更新の工程(update_historical_prices.py)の文",
        "dashboard": "dashboard/app.py は本番の報告の画面(口座・注文の状態)で、バックテストの実行の一覧・項目別タブの画面ではない",
    }

    def op_drawdown(self, inp):
        dd = drawdown(pd.Series(inp["equity"], dtype=float))
        return {"max_dd_abs": float(-dd.min()), "note": "drawdown()(syscore/pandas/strategy_functions.py 70 行)は額の系列だけを返す。率の口は無い"}


TARGET = PySystemtrade()
