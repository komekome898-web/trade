"""Survey candidate 87 `PyTrendFollow (commit 439232ae)` (venv item_1/c87) for the item 4 battery -- a tool that cannot take this battery's inputs.

The adapter loads the tool in its venv (so the runner records that it runs) and answers every input with what was
looked for and not found:
- op bars: trading.accountcurve.accountCurve(instruments, positions=..., panama_prices=...) は建玉の系列と価格の系列から収益の式 4 本を出す形で(項目 2 の記録)、注文・約定の記録・決済ごとの損益を返す口を探したが無い
- op pipeline: データは IB と Quandl からの取得を自前で保管する形(config/currencies.py 9-12 行、項目 1 の記録)で、ファイルを宣言で読む口・目的つきの書き出し・ダッシュボードが無い
- op metrics / split / reference / models: see _i4_base (METRICS / SPLIT below).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _i4_base import Base, NotExpressible  # noqa: E402

import trading  # noqa: F401,E402


class Light(Base):
    name = "opp_pytrendfollow"
    TOOL = "PyTrendFollow (commit 439232ae)"
    PIPELINE = "データは IB と Quandl からの取得を自前で保管する形(config/currencies.py 9-12 行、項目 1 の記録)で、ファイルを宣言で読む口・目的つきの書き出し・ダッシュボードが無い"
    METRICS = "外から与えた決済ごとの損益と資産の列から 12 の指標を出す口を探したが無い"
    SPLIT = "行の割合で学習・検証・検証外に分ける口を探したが無い"

    def gate(self, inp):
        raise NotExpressible(f"{self.TOOL}: trading.accountcurve.accountCurve(instruments, positions=..., panama_prices=...) は建玉の系列と価格の系列から収益の式 4 本を出す形で(項目 2 の記録)、注文・約定の記録・決済ごとの損益を返す口を探したが無い")


TARGET = Light()
