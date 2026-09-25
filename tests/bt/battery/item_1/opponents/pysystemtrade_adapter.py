"""PySystemtrade (catalogue 3, SCAN 9401 行; git clone read through a .pth in venv item_0/c3).

Read in the clone (`_dl/c3`, sysdata/csv/):
- `csvFuturesContractPriceData(datapath, config=ConfigCsvFuturesPrices(input_date_index_name,
  input_skiprows, input_skipfooter, input_date_format, input_column_mapping))` reads
  per-contract price files named `<INSTRUMENT>_<YYYYMMDD>.csv` with ONE date index
  column and OPEN/HIGH/LOW/CLOSE(/VOLUME) columns; no time zone, no epoch unit, no
  two-column date+time, no trade / quote rows;
- duplicates are dropped silently where frames are merged
  (sysdata/futures/futures_per_contract_prices.py:381 `index.duplicated(keep="first")`) -- no report;
- the simulation is a vectorised pandas pipeline; no event path; futures only (no
  split / reverse split / code change / delisting of stocks).
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import sysdata  # noqa: F401


class T(ReasonTarget):
    name = "opp_pysystemtrade"
    reasons = {
        "load": "PySystemtrade の CSV の読み口(csvFuturesContractPriceData)は <銘柄>_<限月>.csv の先物の足を 1 列の日付の索引で読む。約定・気配の行、時刻の単位・時間帯、"
                "date と time の 2 列の口が無い。重複は結合のときに黙って落とす(futures_per_contract_prices.py:381)ので、異常を報せる口も無い",
        "jpx": "PySystemtrade は先物の道具で、個別株の分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い",
        "vector_vs_event": "PySystemtrade の模擬は pandas のベクトル化の 1 経路だけで、突き合わせる事象駆動の経路が無い",
    }


TARGET = T()
