"""PyTrendFollow (catalogue 87, SCAN 7857 行; git clone at 439232a read through a .pth; venv item_1/c87,
re-cloned 2026-09-25 after item 0's clone and venv were removed).

Read in the clone (`item_1/_dl/c87`): data comes from its own downloaders/stores (Quandl,
IB) into its HDF store; `grep -rln "read_csv\\|DictReader\\|csv.reader" item_1/_dl/c87 --include=*.py`
-> 0 files; the account curve (`trading/accountcurve.py`) is a vectorised
computation over position and price series; no event path, no corporate actions,
no universe by date.
"""
from __future__ import annotations

import os
import sys

from _i1_base import ReasonTarget

import trading.accountcurve  # noqa: E402,F401  (the clone, through the venv .pth)


class T(ReasonTarget):
    name = "opp_pytrendfollow"
    reasons = {
        "load": "PyTrendFollow に任意の CSV の市場データを読む口が無い(データは自前の取得器から自前の保管へ。grep で read_csv・csv.reader の当たりは 0 件)",
        "jpx": "PyTrendFollow は先物の連続足を扱い、個別株の分割・併合・コード変更の調整と日付ごとの銘柄集合の口が無い",
        "vector_vs_event": "PyTrendFollow の損益の計算(accountCurve)はベクトル化の 1 経路だけで、突き合わせる事象駆動の経路が無い",
    }


TARGET = T()
