"""Survey candidate 68 `quanttrader 0.5.5` (venv item_4/quanttrader) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 成行は送った時刻の値(DataBoard.get_current_price = その tick の値、足の終値)で即時に約定する(brokerage/backtest_brokerage.py 131-157 行「Market order is immediately filled」)。次の足の始値で約定させる口を探したが無い(84-89 行の注記は「保存して翌日の始値で約定させることもできる」と書くが実装は無い)。手数料は銘柄の型ごとの固定の式(30-49 行、IB の料金)で率を渡す口が無い
- op pipeline: 入力は銘柄ごとの DataFrame(add_data)で、宣言でファイルを読む口・気配の買い ask・売り bid(fill は「TODO: use bid/ask」: 113・155 行)・目的つきの書き出し・ダッシュボードの口が無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

from quanttrader.backtest_engine import BacktestEngine  # noqa: F401,E402


class Light(Base):
    name = "opp_quanttrader"
    TOOL = "quanttrader 0.5.5"
    PIPELINE = "入力は銘柄ごとの DataFrame(add_data)で、宣言でファイルを読む口・気配の買い ask・売り bid(fill は「TODO: use bid/ask」: 113・155 行)・目的つきの書き出し・ダッシュボードの口が無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 成行は送った時刻の値(DataBoard.get_current_price = その tick の値、足の終値)で即時に約定する(brokerage/backtest_brokerage.py 131-157 行「Market order is immediately filled」)。次の足の始値で約定させる口を探したが無い(84-89 行の注記は「保存して翌日の始値で約定させることもできる」と書くが実装は無い)。手数料は銘柄の型ごとの固定の式(30-49 行、IB の料金)で率を渡す口が無い")


TARGET = Light()
