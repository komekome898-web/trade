"""Survey candidate 23 `hftbacktest 2.4.4` (venv item_1/hftbacktest) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: 入力は板の深さと約定の事象(BacktestAsset.data、HashMapMarketDepthBacktest: hftbacktest/__init__.py 118・189 行)で、足(OHLC)を受ける口を探したが無い。足を事象に作り直すのは adapter の計算になる
- op pipeline: 入力は自前の npz の事象の形(tardis などの変換器は取引所ごとに固定)で、足・気配の買い ask・売り bid の宣言、目的つきの書き出し・ダッシュボードの口を探したが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import hftbacktest  # noqa: F401,E402


class Light(Base):
    name = "opp_hftbacktest"
    TOOL = "hftbacktest 2.4.4"
    PIPELINE = "入力は自前の npz の事象の形(tardis などの変換器は取引所ごとに固定)で、足・気配の買い ask・売り bid の宣言、目的つきの書き出し・ダッシュボードの口を探したが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: 入力は板の深さと約定の事象(BacktestAsset.data、HashMapMarketDepthBacktest: hftbacktest/__init__.py 118・189 行)で、足(OHLC)を受ける口を探したが無い。足を事象に作り直すのは adapter の計算になる")


TARGET = Light()
