"""pybotters (catalogue 12, SCAN 6871 行; installed by item 0 in venv item_0/pybotters).

Read in the installed code: an HTTP / WebSocket client with DataStores fed by
exchange messages; `grep -rln "read_csv\\|DictReader\\|csv.reader" pybotters/` -> 0 files.
The time strings of a message are kept as given (SCAN 2788 行: 「UTC / ミリ秒への正規化は道具の側でしない」).
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import pybotters  # noqa: F401


class T(ReasonTarget):
    name = "opp_pybotters"
    reasons = {
        "load": "pybotters にファイルを読む口が無い(取引所への HTTP / WebSocket の通信と、受けた通知を貯める DataStore だけ。read_csv・csv.reader の当たりは 0 件)。"
                "時刻の文字列は変換せずそのまま持つ(SCAN 2788 行)",
        "jpx": "pybotters に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い",
        "vector_vs_event": "pybotters に模擬の経路が無い(通信の道具)",
    }


TARGET = T()
