"""barter-rs (catalogue 61, SCAN 6926 行; git clone built with cargo by item 0, driver
`c61_driver` in venv item_0/c61).

Read in the clone (`_dl/c61`): the engine consumes typed `MarketEvent`s from an
iterator/stream (barter-data normalises exchange WebSocket messages; `Candle` carries
`close_time: DateTime<Utc>`, SCAN 6303 行); there is no reader of CSV market-data files
(`grep -rln "csv::Reader\\|ReaderBuilder" _dl/c61 --include=*.rs` -> 0 files), no duplicate /
gap / hash / allow-list, no corporate actions, one event-driven path.  The driver built
for item 0 dispatches only item 0's calls; nothing in the tool reaches a file scene.
"""
from __future__ import annotations

import os
import sys

from _i1_base import ReasonTarget

EXE = os.path.join(os.path.dirname(sys.executable), "c61_driver")
assert os.path.exists(EXE), "c61_driver is missing"


class T(ReasonTarget):
    name = "opp_barter"
    reasons = {
        "load": "barter にファイルの市場データを読む口が無い(エンジンは型つきの MarketEvent の列を受ける。barter-data の正規化は取引所の WebSocket の通知に掛かる。"
                "grep で csv::Reader・ReaderBuilder の当たりは 0 件)",
        "jpx": "barter に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い(暗号資産の道具)",
        "vector_vs_event": "barter の模擬は事象駆動の 1 経路だけで、近道(ベクトル化)の経路が無い",
    }


TARGET = T()
