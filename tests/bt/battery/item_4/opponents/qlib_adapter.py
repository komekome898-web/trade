"""Survey candidate 21 `Qlib (pyqlib 0.9.7)` (venv item_1/qlib) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 注文は qlib.backtest.decision.Order(stock_id, amount, direction, start_time, end_time)(decision.py 37-62 行)で値・逆指値・時間切れの欄が無く、足は qlib の自前のデータの形(dump_bin で作る bin。配布物に CSV の読み口が無い: 項目 1 の記録)からしか読まない。メモリ上の足を渡す口を探したが無い
- op pipeline: データは qlib の自前の形(provider_uri の bin)で、CSV を宣言で読む口・気配/板・目的つきの書き出し・ダッシュボードの口を探したが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

from qlib.backtest.decision import Order  # noqa: F401,E402


class Light(Base):
    name = "opp_qlib"
    TOOL = "Qlib (pyqlib 0.9.7)"
    PIPELINE = "データは qlib の自前の形(provider_uri の bin)で、CSV を宣言で読む口・気配/板・目的つきの書き出し・ダッシュボードの口を探したが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 注文は qlib.backtest.decision.Order(stock_id, amount, direction, start_time, end_time)(decision.py 37-62 行)で値・逆指値・時間切れの欄が無く、足は qlib の自前のデータの形(dump_bin で作る bin。配布物に CSV の読み口が無い: 項目 1 の記録)からしか読まない。メモリ上の足を渡す口を探したが無い")


TARGET = Light()
