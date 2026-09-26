"""QSTrader (catalogue 121, SCAN 6325 行; installed by item 0 in venv item_0/qstrader).

Read in the installed code:
- `CSVDailyBarDataSource(csv_dir, asset_type, adjust_prices=True, csv_symbols=None)`
  (qstrader/data/daily_bar_csv.py:35) reads `<symbol>.csv` daily bars with fixed columns
  (Date, Open, High, Low, Close, Adj Close, Volume); an adjusted price is the file's
  `Adj Close` ratio, not computed from split events; no argument for a column map,
  an intraday time, a unit or a zone;
- `DynamicUniverse(asset_dates)` (qstrader/asset/universe/dynamic.py:18) holds only an
  entry date per asset; its docstring (lines 9-10): "This does not currently support
  removal of assets or sequences of additions/removals";
- one schedule-driven simulation path; no vector path.
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import qstrader  # noqa: F401
from qstrader.asset.universe.dynamic import DynamicUniverse  # noqa: F401


class T(ReasonTarget):
    name = "opp_qstrader"
    reasons = {
        "load": "QSTrader の読み口 CSVDailyBarDataSource は <銘柄>.csv の日足で列が固定(Date, Open, High, Low, Close, Adj Close, Volume)。列の対応・日中の時刻・単位・時間帯の引数が無い",
        "jpx": "QSTrader の調整はファイルの Adj Close の比を掛けるだけで分割・併合の事象から計算しない。DynamicUniverse は銘柄ごとの入る日だけを持ち、"
               "上場廃止(除く日)を渡す口が無い(dynamic.py の docstring 9-10 行「does not currently support removal of assets」)。コード変更の口も無い",
        "vector_vs_event": "QSTrader の模擬は日程で駆動する 1 経路だけで、近道(ベクトル化)の経路が無い",
    }


TARGET = T()
