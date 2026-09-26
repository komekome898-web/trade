"""Survey candidate 3 `PySystemtrade (commit 8958c49c)` (venv item_1/c3) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 注文の模擬は fill_list_of_simple_orders(list_of_orders, fill_datetime, market_price) に 1 つの値を渡す形(systems/accounts/order_simulator/fills_and_orders.py、SimpleOrder は整数の数量)で、足の OHLC を受けて次の足の始値で約定させる口・逆指値・時間切れの口を探したが無い(注文の模擬器は価格の系列 1 本の次の値で約定を決める: pandl_order_simulator.py 221-235 行)
- op pipeline: データは先物の価格の CSV(csvFuturesContractPriceData)と自前の保管で、約定/気配/板の入力・目的つきの書き出し・ダッシュボードの口を探したが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import systems  # noqa: F401,E402


class Light(Base):
    name = "opp_pysystemtrade"
    TOOL = "PySystemtrade (commit 8958c49c)"
    PIPELINE = "データは先物の価格の CSV(csvFuturesContractPriceData)と自前の保管で、約定/気配/板の入力・目的つきの書き出し・ダッシュボードの口を探したが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 注文の模擬は fill_list_of_simple_orders(list_of_orders, fill_datetime, market_price) に 1 つの値を渡す形(systems/accounts/order_simulator/fills_and_orders.py、SimpleOrder は整数の数量)で、足の OHLC を受けて次の足の始値で約定させる口・逆指値・時間切れの口を探したが無い(注文の模擬器は価格の系列 1 本の次の値で約定を決める: pandl_order_simulator.py 221-235 行)")


TARGET = Light()
