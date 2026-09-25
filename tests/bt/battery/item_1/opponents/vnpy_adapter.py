"""VnPy (catalogue 20, SCAN 6896 行; installed by item 0 in venv item_0/vnpy: vnpy 4.4.0 + vnpy_ctastrategy).

Read in the installed code: `grep -rln "read_csv\\|DictReader\\|csv.reader" vnpy/ vnpy_ctastrategy/`
-> 0 files (the CSV importer lives in the separate vnpy_datamanager app, not installed and not
named by the survey); bars are built from ticks by `vnpy.trader.utility.BarGenerator.update_tick`
(one incremental path); the CTA backtester replays bars/ticks one by one; there is no
vector path, no duplicate / gap report, no hash, no allow-list, no corporate actions.
"""
from __future__ import annotations

from _i1_base import ReasonTarget

import vnpy  # noqa: F401
from vnpy.trader.utility import BarGenerator  # noqa: F401


class T(ReasonTarget):
    name = "opp_vnpy"
    reasons = {
        "load": "VnPy(本体と vnpy_ctastrategy)にファイルを読む口が無い(read_csv・csv.reader の当たりは 0 件。CSV の取り込みは別の部品 vnpy_datamanager で、調査報告に無く導入していない)",
        "jpx": "VnPy に分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い",
        "vector_vs_event": "VnPy の足づくり(BarGenerator.update_tick)と CTA の検証は 1 本ずつの事象駆動の経路だけで、突き合わせる近道(ベクトル化)の経路が無い",
    }


TARGET = T()
