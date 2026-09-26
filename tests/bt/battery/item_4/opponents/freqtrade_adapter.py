"""Survey candidate 75 `Freqtrade 2026.8` (venv item_3/freqtrade) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: Backtesting(config) は取引所の口を作り(optimize/backtesting.py 170 行 ExchangeResolver.load_exchange)、その初期化で ccxt の load_markets を呼ぶ(exchange/exchange.py 302・472・689-713 行 = ネットワーク)。外部に何も渡さない規則のもとで取引所の市場の情報なしに走らせる口を探したが無い
- op pipeline: dry-run も取引所の接続が前提(freqtradebot は Exchange を作る)で、宣言で複数の資産のファイルを読む口・目的つきの書き出しの口が無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import freqtrade  # noqa: F401,E402


class Light(Base):
    name = "opp_freqtrade"
    TOOL = "Freqtrade 2026.8"
    PIPELINE = "dry-run も取引所の接続が前提(freqtradebot は Exchange を作る)で、宣言で複数の資産のファイルを読む口・目的つきの書き出しの口が無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: Backtesting(config) は取引所の口を作り(optimize/backtesting.py 170 行 ExchangeResolver.load_exchange)、その初期化で ccxt の load_markets を呼ぶ(exchange/exchange.py 302・472・689-713 行 = ネットワーク)。外部に何も渡さない規則のもとで取引所の市場の情報なしに走らせる口を探したが無い")


TARGET = Light()
