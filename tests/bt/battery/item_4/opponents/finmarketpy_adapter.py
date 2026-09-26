"""Survey candidate 54 `finmarketpy 0.11.19` (venv item_1/finmarketpy) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: Backtest.calculate_trading_PnL(br, asset_a_df, signal_df, contract_value_df, run_in_parallel)(backtest/backtestengine.py 121 行)は価格の表と建玉の割合の表から収益率の系列を出す形で、注文(種類・値・数量・時刻)・約定の記録・決済ごとの損益を返す口を探したが無い
- op pipeline: 入力は価格と合図の DataFrame で、宣言でファイルを読む口・約定/気配/板・目的つきの書き出し・ダッシュボードの口を探したが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

from finmarketpy.backtest.backtestengine import Backtest  # noqa: F401,E402


class Light(Base):
    name = "opp_finmarketpy"
    TOOL = "finmarketpy 0.11.19"
    PIPELINE = "入力は価格と合図の DataFrame で、宣言でファイルを読む口・約定/気配/板・目的つきの書き出し・ダッシュボードの口を探したが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: Backtest.calculate_trading_PnL(br, asset_a_df, signal_df, contract_value_df, run_in_parallel)(backtest/backtestengine.py 121 行)は価格の表と建玉の割合の表から収益率の系列を出す形で、注文(種類・値・数量・時刻)・約定の記録・決済ごとの損益を返す口を探したが無い")


TARGET = Light()
