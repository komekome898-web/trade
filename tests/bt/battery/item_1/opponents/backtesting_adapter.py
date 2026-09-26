"""backtesting.py (catalogue 55, SCAN 6344 行; installed by item 0 in venv item_0/backtesting).

Read in the installed code (backtesting 0.x, backtesting/backtesting.py):
- `Backtest(data, strategy)` takes an in-memory OHLC DataFrame; the package reads
  no market-data file (`grep -rln "read_csv\\|DictReader" backtesting/` -> only test/__init__.py,
  which loads its bundled example data);
- it checks only that the index is increasing (backtesting.py:1252 `is_monotonic_increasing`,
  a warning/sort), no duplicate / gap / generation report, no hash, no allow-list,
  no corporate actions;
- one simulation path (Strategy.next bar by bar); no vector path to agree with.
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import backtesting  # noqa: F401


class T(ReasonTarget):
    name = "opp_backtesting"
    reasons = {
        "load": "backtesting.py に市場データのファイルを読む口が無い(Backtest はメモリ上の OHLC の DataFrame を取る。read_csv の当たりは同梱の例のデータを読む test/__init__.py だけ)",
        "jpx": "backtesting.py に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い(1 銘柄の OHLC だけを取る)",
        "vector_vs_event": "backtesting.py の模擬は Strategy.next を足ごとに呼ぶ 1 経路だけで、突き合わせる近道(ベクトル化)の経路が無い",
    }


TARGET = T()
