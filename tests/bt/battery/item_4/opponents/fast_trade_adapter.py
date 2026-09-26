"""Survey candidate 10 `fast-trade 2.1.0` (venv item_4/fast-trade) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: run_backtest(backtest, df=) は規則の表(enter / exit の条件)を OHLCV の表の全体に当てて評価し、取引は残高の全部を足の終値で行い、手数料は 1 つの comission の率(run_backtest.py 79・209 行、項目 2 の読み)。数量・名目額・注文の時刻・次の足の始値・指値・逆指値を渡す口を探したが無い
- op pipeline: 入力は OHLCV の DataFrame(または取引所からの取得)で、宣言でファイルを読む口・気配/板・目的つきの書き出し・ダッシュボードの口が無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

from fast_trade.run_backtest import run_backtest  # noqa: F401,E402


class Light(Base):
    name = "opp_fast_trade"
    TOOL = "fast-trade 2.1.0"
    PIPELINE = "入力は OHLCV の DataFrame(または取引所からの取得)で、宣言でファイルを読む口・気配/板・目的つきの書き出し・ダッシュボードの口が無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: run_backtest(backtest, df=) は規則の表(enter / exit の条件)を OHLCV の表の全体に当てて評価し、取引は残高の全部を足の終値で行い、手数料は 1 つの comission の率(run_backtest.py 79・209 行、項目 2 の読み)。数量・名目額・注文の時刻・次の足の始値・指値・逆指値を渡す口を探したが無い")


TARGET = Light()
