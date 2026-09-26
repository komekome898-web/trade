"""Survey candidate 121 `QSTrader 0.3.0` (venv item_0/qstrader) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 戦略は AlphaModel が日付ごとに目標の重みを返す形で(qstrader/alpha_model/alpha_model.py 13・22 行)、合図の足の次の始値に注文を送る口・数量や名目額で建てる口・逆指値や指値の口を探したが無い。データは日足の CSV(CSVDailyBarDataSource)で、1 分・1 時間の足を受けない
- op pipeline: 入力は銘柄ごとの日足の CSV で、約定・気配・板の入力、目的つきの書き出し・ダッシュボードの口を探したが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import qstrader  # noqa: F401,E402


class Light(Base):
    name = "opp_qstrader"
    TOOL = "QSTrader 0.3.0"
    PIPELINE = "入力は銘柄ごとの日足の CSV で、約定・気配・板の入力、目的つきの書き出し・ダッシュボードの口を探したが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 戦略は AlphaModel が日付ごとに目標の重みを返す形で(qstrader/alpha_model/alpha_model.py 13・22 行)、合図の足の次の始値に注文を送る口・数量や名目額で建てる口・逆指値や指値の口を探したが無い。データは日足の CSV(CSVDailyBarDataSource)で、1 分・1 時間の足を受けない")


TARGET = Light()
