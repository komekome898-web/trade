"""DaniyalMlk/slippage (catalogue 105, SCAN 5243 行; git clone installed by item 0 in venv item_0/c105).

Read in the installed code (slippage/io.py):
- `load_bars(path)` (io.py:126) reads a CSV whose header must contain the FIXED columns
  symbol, timestamp, open, high, low, close, volume (BAR_COLUMNS, io.py:44; a missing
  column raises InputError, io.py:57-59); timestamps are `datetime.fromisoformat` (io.py:133,
  module docstring "Timestamps are ISO 8601"); there is no argument for a column map,
  a unit or a zone;
- `BarSeries` sorts the bars by time and raises on a duplicated bar timestamp
  (slippage/series.py:35-41) -- a refusal, not a report; no backward / gap / conflict kind;
- orders / fills loaders have the same fixed-column form; no trades loader, no hash,
  no allow-list, no corporate actions, no vector-vs-event pair.
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import slippage  # noqa: F401
from slippage import io as sio  # noqa: F401


class T(ReasonTarget):
    name = "opp_slippage"
    reasons = {
        "load": "slippage の読み口(io.load_bars・load_orders)は列が固定(足は symbol,timestamp,open,high,low,close,volume。io.py:44)で、場面のファイルの列(symbol の列が無い・名前が違う)を渡す引数が無い。約定を読む口は無い",
        "jpx": "slippage に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い(執行費用の分析の道具)",
        "vector_vs_event": "slippage に同じ足を 2 つの経路で回して突き合わせる口が無い",
    }


TARGET = T()
